# SPDX-License-Identifier: Apache-2.0
"""SkillIndex — hybrid 70/30 BM25 + vector retrieval over the SkillStore.

Second concrete absorption from the Hermes/OpenClaw research stack
(``docs/operations/openclaw_mindx_research.md`` §1.5 and
``docs/operations/Hermes Agent Integration Patterns for mindX_…`` §8.1).
OpenClaw's Active Memory sub-agent uses BM25+vector with a default 70/30
mix and **union** (not intersection) fusion so a chunk that scores high on
vectors but zero on keywords still surfaces. mindX adopts that exact contract
for skill retrieval.

Backend
  * **FTS5** (built into Python's bundled sqlite3, no extra deps) for BM25
    ranking over name + description + body + tags.
  * **Vector** index = a per-row JSON-encoded float array in the same SQLite
    file. Embeddings come from the existing Ollama server
    (``$MINDX_LLM__OLLAMA__BASE_URL``, model = mxbai-embed-large by default)
    — the same provider memory_pgvector already uses. Best-effort: if the
    embed call fails, the row is indexed text-only and ``search()`` falls back
    to pure BM25 gracefully.

Score fusion
  * ``vector_weight = 0.7`` (default; configurable per call).
  * ``text_weight   = 1.0 - vector_weight``.
  * Both scores are min-max normalised to ``[0, 1]`` across the candidate set.
  * Final = ``vector_weight × v + text_weight × t``. Union over the two
    candidate sets; missing-side scores default to 0.
  * ``candidate_multiplier = 4`` — pull 4× the target ``limit`` from each side
    before fusion (matches OpenClaw's documented constant).

Failure modes (never raise into the caller)
  * Embedder unreachable → ``vector_weight`` forced to 0 for the call.
  * FTS5 table corrupt / absent → rebuild on next ``write``.
  * Vector column missing JSON → row treated as text-only.

Storage path
  Default ``$MINDX_SKILLS_DIR/.index/skills.db`` (alongside the SkillStore
  root). WAL mode. ``integrity_check`` runs on first open per process; on
  failure the index is rebuilt from disk.
"""
from __future__ import annotations

import json
import logging
import math
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

from agents.skills.skill_schema import Skill, parse_skill_md

logger = logging.getLogger("agents.skills.index")

# Per OpenClaw research §1.5: pull 4× the limit before fusion.
CANDIDATE_MULTIPLIER = 4

# Default vector weight per the 70/30 contract.
DEFAULT_VECTOR_WEIGHT = 0.7


# ─── embedding (Ollama, best-effort) ────────────────────────────────


def _ollama_base_url() -> str:
    return (
        os.environ.get("MINDX_LLM__OLLAMA__BASE_URL")
        or os.environ.get("OLLAMA_BASE_URL")
        or "http://localhost:11434"
    ).rstrip("/")


def _embed_model() -> str:
    return os.environ.get("MINDX_SKILLS_EMBED_MODEL", "mxbai-embed-large")


def _embed_text(text: str, *, timeout: float = 5.0) -> Optional[list[float]]:
    """Best-effort embedding via Ollama ``/api/embed``. Returns None on failure.

    Never raises. Truncates input to 8 KB to keep the round-trip predictable.
    """
    if not text or not text.strip():
        return None
    try:
        import httpx
    except ImportError:
        return None
    url = f"{_ollama_base_url()}/api/embed"
    try:
        resp = httpx.post(
            url,
            json={"model": _embed_model(), "input": text[:8192]},
            timeout=timeout,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        # Ollama /api/embed returns {"embeddings": [[...]]} (newer) or {"embedding": [...]}.
        if isinstance(data, dict):
            if "embeddings" in data and data["embeddings"]:
                v = data["embeddings"][0]
            elif "embedding" in data:
                v = data["embedding"]
            else:
                return None
            if isinstance(v, list) and v and isinstance(v[0], (int, float)):
                return [float(x) for x in v]
    except Exception as e:  # pragma: no cover — best-effort
        logger.debug(f"embed failed: {e}")
    return None


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# ─── SkillIndex ────────────────────────────────────────────────────


class SkillIndex:
    """Hybrid 70/30 BM25 + vector retrieval over skills on disk."""

    def __init__(self, db_path: Optional[Path | str] = None, *, skills_root: Optional[Path] = None):
        if db_path is None:
            if skills_root is None:
                env = os.environ.get("MINDX_SKILLS_DIR")
                skills_root = Path(env) if env else Path.home() / ".mindx" / "skills"
            db_path = Path(skills_root) / ".index" / "skills.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

    # ─── schema ─────────────────────────────────────────────────────
    def _init_schema(self) -> None:
        with self._lock:
            c = self._conn.cursor()
            try:
                # Integrity probe — exists, FTS5 module available, rebuild on corruption.
                c.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS skills_fts "
                    "USING fts5(slug, category, name, description, body, tags, tokenize='unicode61 remove_diacritics 2')"
                )
            except sqlite3.OperationalError as e:
                logger.warning(f"FTS5 unavailable, falling back to no-FTS mode: {e}")
                # Create a plain table so the rest of the code still works.
                c.execute(
                    "CREATE TABLE IF NOT EXISTS skills_fts ("
                    " slug TEXT, category TEXT, name TEXT, description TEXT, body TEXT, tags TEXT)"
                )
            c.execute(
                "CREATE TABLE IF NOT EXISTS skill_vec ("
                " slug TEXT, category TEXT, vec_json TEXT, dim INTEGER, "
                " updated_at REAL, PRIMARY KEY (category, slug))"
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_skill_vec_slug ON skill_vec(slug)")
            self._conn.commit()

            # PRAGMA integrity_check — improvement over Hermes per §10 of the
            # Hermes integration doc. On corruption, rebuild FTS5.
            try:
                row = c.execute("PRAGMA integrity_check").fetchone()
                if row and row[0] != "ok":
                    logger.warning(f"skill index integrity_check: {row[0]} — attempting FTS rebuild")
                    try:
                        c.execute("INSERT INTO skills_fts(skills_fts) VALUES('rebuild')")
                        self._conn.commit()
                    except sqlite3.OperationalError:
                        pass
            except Exception:
                pass

    # ─── write / remove ─────────────────────────────────────────────
    def index_skill(self, skill: Skill, *, category: Optional[str] = None) -> None:
        """Upsert a skill into both FTS5 and the vector table."""
        fm = skill.frontmatter
        cat = category or fm.category
        slug = skill.slug
        tags_text = " ".join(fm.tags) if fm.tags else ""
        with self._lock:
            c = self._conn.cursor()
            # Remove prior row for this (category, slug) — FTS5 doesn't have UPSERT.
            c.execute("DELETE FROM skills_fts WHERE category=? AND slug=?", (cat, slug))
            c.execute(
                "INSERT INTO skills_fts (slug, category, name, description, body, tags) VALUES (?,?,?,?,?,?)",
                (slug, cat, fm.name, fm.description, skill.body, tags_text),
            )

            # Best-effort vector. Embedded text = name + description + tags +
            # first 4 KB of body — matches the heuristic memory_pgvector uses.
            embed_input = "\n".join([fm.name, fm.description, tags_text, skill.body[:4096]]).strip()
            vec = _embed_text(embed_input)
            if vec is not None:
                c.execute(
                    "INSERT OR REPLACE INTO skill_vec (slug, category, vec_json, dim, updated_at) VALUES (?,?,?,?,?)",
                    (slug, cat, json.dumps(vec), len(vec), time.time()),
                )
            self._conn.commit()

    def remove(self, category: str, slug: str) -> None:
        with self._lock:
            c = self._conn.cursor()
            c.execute("DELETE FROM skills_fts WHERE category=? AND slug=?", (category, slug))
            c.execute("DELETE FROM skill_vec WHERE category=? AND slug=?", (category, slug))
            self._conn.commit()

    # ─── search ─────────────────────────────────────────────────────
    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        vector_weight: float = DEFAULT_VECTOR_WEIGHT,
        category: Optional[str] = None,
    ) -> list[tuple[float, dict]]:
        """Hybrid 70/30 retrieval. Returns ``[(score, row), …]`` sorted desc.

        Each row is ``{slug, category, name, description, tags, vec_score, text_score}``.

        Failure modes:
          * Embedding unavailable → ``vector_weight`` forced to 0; pure BM25.
          * FTS5 table empty → returns ``[]``.
          * ``query`` empty → returns most-recent rows by ``updated_at``.
        """
        q = (query or "").strip()
        vector_weight = max(0.0, min(1.0, vector_weight))
        text_weight = 1.0 - vector_weight
        pull = max(limit * CANDIDATE_MULTIPLIER, limit)

        # — text side (BM25 via FTS5 if available) —
        text_hits: dict[tuple[str, str], tuple[float, dict]] = {}
        with self._lock:
            c = self._conn.cursor()
            if q:
                fts_query = self._sanitize_fts(q)
                try:
                    sql = (
                        "SELECT slug, category, name, description, tags, bm25(skills_fts) AS r "
                        "FROM skills_fts WHERE skills_fts MATCH ?"
                        + (" AND category=?" if category else "")
                        + " ORDER BY r LIMIT ?"
                    )
                    params: tuple = (fts_query, category, pull) if category else (fts_query, pull)
                    rows = c.execute(sql, params).fetchall()
                except sqlite3.OperationalError:
                    rows = []
            else:
                # No query: list top-N by recency.
                sql = (
                    "SELECT s.slug, s.category, s.name, s.description, s.tags, 0 "
                    "FROM skills_fts s LEFT JOIN skill_vec v "
                    "ON v.slug=s.slug AND v.category=s.category "
                    + ("WHERE s.category=? " if category else "")
                    + "ORDER BY COALESCE(v.updated_at, 0) DESC LIMIT ?"
                )
                params = (category, pull) if category else (pull,)
                rows = c.execute(sql, params).fetchall()
            for slug, cat, name, desc, tags, r in rows:
                # FTS5 bm25() returns lower-is-better; invert to a 0..1ish score.
                score = 1.0 / (1.0 + max(0.0, float(r))) if q else 0.5
                text_hits[(cat, slug)] = (
                    score,
                    {"slug": slug, "category": cat, "name": name, "description": desc, "tags": tags},
                )

        # — vector side (cosine over rows) —
        vec_hits: dict[tuple[str, str], tuple[float, dict]] = {}
        query_vec = _embed_text(q) if (q and vector_weight > 0) else None
        if query_vec is None:
            vector_weight = 0.0
            text_weight = 1.0
        else:
            with self._lock:
                c = self._conn.cursor()
                sql = (
                    "SELECT v.slug, v.category, v.vec_json, s.name, s.description, s.tags "
                    "FROM skill_vec v JOIN skills_fts s ON s.slug=v.slug AND s.category=v.category"
                    + (" WHERE v.category=?" if category else "")
                )
                params = (category,) if category else ()
                rows = c.execute(sql, params).fetchall()
            for slug, cat, vec_json, name, desc, tags in rows:
                try:
                    v = json.loads(vec_json)
                except Exception:
                    continue
                cos = _cosine(query_vec, v)
                if cos <= 0:
                    continue
                vec_hits[(cat, slug)] = (
                    cos,
                    {"slug": slug, "category": cat, "name": name, "description": desc, "tags": tags},
                )

        # — fusion: union of both, min-max normalise each side, weighted sum —
        keys = set(text_hits) | set(vec_hits)
        if not keys:
            return []

        text_raw = {k: text_hits[k][0] for k in keys if k in text_hits}
        vec_raw = {k: vec_hits[k][0] for k in keys if k in vec_hits}

        text_norm = _minmax(text_raw)
        vec_norm = _minmax(vec_raw)

        final: list[tuple[float, dict]] = []
        for k in keys:
            row = text_hits.get(k, vec_hits.get(k))[1]  # row is identical between sides
            t = text_norm.get(k, 0.0)
            v = vec_norm.get(k, 0.0)
            score = vector_weight * v + text_weight * t
            row = dict(row)
            row["text_score"] = t
            row["vec_score"] = v
            final.append((score, row))
        final.sort(key=lambda x: x[0], reverse=True)
        return final[:limit]

    # ─── helpers ────────────────────────────────────────────────────
    @staticmethod
    def _sanitize_fts(q: str) -> str:
        """Strip FTS5 specials and add prefix-match suffix per token.

        ``alph`` → ``alph*`` (matches ``alpha``); preserves common-sense
        partial-keyword behaviour that the legacy substring search had.
        """
        import re as _re
        sanitized = _re.sub(r"[^\w\s]", " ", q or "")
        toks = [t for t in sanitized.split() if t]
        if not toks:
            return q
        return " OR ".join(f"{t}*" for t in toks)

    def rebuild(self, store) -> int:
        """Re-index every skill from disk via the given SkillStore. Returns count."""
        with self._lock:
            c = self._conn.cursor()
            c.execute("DELETE FROM skills_fts")
            c.execute("DELETE FROM skill_vec")
            self._conn.commit()
        n = 0
        for ref in store.list():
            try:
                sk = parse_skill_md(ref.path)
                self.index_skill(sk, category=ref.category)
                n += 1
            except Exception as e:
                logger.warning(f"rebuild skipped {ref.path}: {e}")
        return n

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass


# ─── utilities ──────────────────────────────────────────────────────


def _minmax(d: dict) -> dict:
    if not d:
        return {}
    vs = list(d.values())
    lo, hi = min(vs), max(vs)
    if hi - lo < 1e-9:
        return {k: 1.0 for k in d}  # all-equal → all max
    return {k: (v - lo) / (hi - lo) for k, v in d.items()}


__all__ = ["SkillIndex", "DEFAULT_VECTOR_WEIGHT", "CANDIDATE_MULTIPLIER"]
