# SPDX-License-Identifier: Apache-2.0
"""Curator — archive-only audit job for the SkillStore.

Fourth concrete absorption from the Hermes/OpenClaw research stack. The
Hermes Curator (``hermes curator``, expanded in v0.13.0 "Tenacity") runs on
a 7-day cadence using the **auxiliary** LLM client so it doesn't invalidate
the main session's prompt cache. Its maximum destructive action is
**archive** — never delete. Pinned and human-authored skills are
**untouchable**. Per-run reports land at ``logs/curator/run.json``.

mindX inherits the contract verbatim. The first iteration in this codebase
runs **without an LLM** — it audits the SkillStore for objective signals
(name collisions, near-duplicate embeddings, scanner re-checks against
stricter rules) and flags candidates. Subsequent passes can layer an
auxiliary-LLM judgment step on top.

What this iteration does:

  1. List every skill the SkillStore knows about.
  2. For each agent-authored, non-pinned skill, score it against four
     signals:
       a. **scanner re-run**         — has the policy tightened? If the
                                       skill now fails the scanner, archive.
       b. **near-duplicate detector**— two agent-authored skills whose
                                       embedding cosine ≥ 0.985 → archive
                                       the older.
       c. **emptiness**              — body ≤ 40 chars or no postconditions.
       d. **staleness**              — neither updated nor accessed in the
                                       last ``stale_days`` (default 90).
                                       (Access counters land in a Day-4 pass;
                                       for now we use ``updated_at``.)
  3. Build an ``AuditReport``. With ``apply=False`` (default), nothing on
     disk changes; the operator inspects the report. With ``apply=True``,
     each flagged skill is archived via ``SkillStore.archive(actor='curator', ...)``
     — which already refuses pinned and human-authored.
  4. Write a JSON report to ``data/learnings/curator/<timestamp>.json``.

The Curator is a **library**, not a process — the periodic scheduler (a
``CronTab``-style entry in MASTERMIND or a systemd timer) is one line of
configuration that's intentionally left to the operator.
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from agents.skills.scanner import scan_skill
from agents.skills.skill_schema import Skill, parse_skill_md

logger = logging.getLogger("agents.skills.curator")

NEAR_DUPE_COSINE = 0.985  # archive the older of two skills with cosine ≥ this
DEFAULT_STALE_DAYS = 90
DEFAULT_MIN_BODY_BYTES = 40


@dataclass
class AuditFinding:
    """One Curator audit finding."""
    category: str
    slug: str
    reasons: list[str] = field(default_factory=list)
    duplicate_of: Optional[str] = None  # "<category>/<slug>"

    def to_dict(self) -> dict:
        return {
            "category": self.category, "slug": self.slug,
            "reasons": list(self.reasons),
            "duplicate_of": self.duplicate_of,
        }


@dataclass
class AuditReport:
    started_at: float
    finished_at: Optional[float] = None
    actor: str = "curator"
    apply: bool = False
    inspected: int = 0
    flagged: list[AuditFinding] = field(default_factory=list)
    archived: list[str] = field(default_factory=list)   # "<category>/<slug>"
    skipped: list[dict] = field(default_factory=list)    # protected/pinned/human + reason

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": (self.finished_at or time.time()) - self.started_at,
            "actor": self.actor,
            "apply": self.apply,
            "inspected": self.inspected,
            "flagged_count": len(self.flagged),
            "archived_count": len(self.archived),
            "skipped_count": len(self.skipped),
            "flagged": [f.to_dict() for f in self.flagged],
            "archived": list(self.archived),
            "skipped": list(self.skipped),
        }


def _cosine(a: list[float], b: list[float]) -> float:
    """Same cosine helper used by SkillIndex. Inlined to avoid the circular dep."""
    import math
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class Curator:
    """Archive-only audit job over a :class:`SkillStore`.

    Pinned + human-authored skills are off-limits. Maximum destructive
    action: ``archive`` (move to ``.archive/<timestamp>/…``).
    """

    def __init__(
        self,
        store,
        *,
        report_dir: Optional[Path | str] = None,
        stale_days: int = DEFAULT_STALE_DAYS,
        min_body_bytes: int = DEFAULT_MIN_BODY_BYTES,
        near_dupe_cosine: float = NEAR_DUPE_COSINE,
    ):
        self.store = store
        if report_dir is None:
            try:
                from utils.config import PROJECT_ROOT as _PR
                base = Path(_PR)
            except Exception:
                base = Path.cwd()
            report_dir = base / "data" / "learnings" / "curator"
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.stale_days = stale_days
        self.min_body_bytes = min_body_bytes
        self.near_dupe_cosine = near_dupe_cosine

    # ── audit ─────────────────────────────────────────────────
    def audit(self) -> AuditReport:
        """Run all signals, return an :class:`AuditReport`. Does not mutate disk."""
        report = AuditReport(started_at=time.time())

        refs = list(self.store.list())
        report.inspected = len(refs)

        # Cache parsed skills for the per-ref signals.
        parsed: list[tuple] = []  # (ref, skill)
        for r in refs:
            try:
                sk = parse_skill_md(r.path)
            except Exception as e:
                logger.warning(f"curator: cannot parse {r.path}: {e}")
                continue
            parsed.append((r, sk))

        # Signal 1: scanner re-run on every agent-authored, non-pinned skill.
        # Signal 3: emptiness — body too short.
        # Signal 4: staleness — updated_at older than `stale_days`.
        now = time.time()
        stale_cut = now - (self.stale_days * 86400)
        for r, sk in parsed:
            if sk.frontmatter.pinned or sk.frontmatter.created_by == "human":
                report.skipped.append({
                    "category": r.category, "slug": r.slug,
                    "reason": "pinned" if sk.frontmatter.pinned else "human-authored",
                })
                continue
            reasons: list[str] = []

            res = scan_skill(sk)
            if not res.safe:
                blocks = "; ".join(res.block_reasons())
                reasons.append(f"scanner re-run failed: {blocks}")

            if len(sk.body.encode("utf-8")) < self.min_body_bytes:
                reasons.append(f"empty body ({len(sk.body)} chars < {self.min_body_bytes})")

            if not sk.frontmatter.postconditions:
                reasons.append("no postconditions declared")

            if sk.frontmatter.updated_at < stale_cut:
                age_days = int((now - sk.frontmatter.updated_at) / 86400)
                reasons.append(f"stale ({age_days}d since updated_at, cutoff {self.stale_days}d)")

            if reasons:
                report.flagged.append(AuditFinding(
                    category=r.category, slug=r.slug, reasons=reasons,
                ))

        # Signal 2: near-duplicates by embedding cosine. Only between
        # agent-authored, non-pinned candidates. Older (lower updated_at) loses.
        # Best-effort: requires the SkillIndex with a vector column.
        try:
            vecs = self._collect_vectors()
            agent_keys = [
                (r.category, r.slug, sk.frontmatter.updated_at)
                for r, sk in parsed
                if not sk.frontmatter.pinned and sk.frontmatter.created_by != "human"
            ]
            for i, (ca, sa, ua) in enumerate(agent_keys):
                vec_a = vecs.get((ca, sa))
                if not vec_a:
                    continue
                for cb, sb, ub in agent_keys[i + 1:]:
                    vec_b = vecs.get((cb, sb))
                    if not vec_b:
                        continue
                    cos = _cosine(vec_a, vec_b)
                    if cos >= self.near_dupe_cosine:
                        loser = (ca, sa) if ua <= ub else (cb, sb)
                        winner = (cb, sb) if loser == (ca, sa) else (ca, sa)
                        # avoid double-adding
                        if not any(f.category == loser[0] and f.slug == loser[1] and f.duplicate_of for f in report.flagged):
                            f = AuditFinding(
                                category=loser[0], slug=loser[1],
                                reasons=[f"near-duplicate (cos={cos:.3f}) of {winner[0]}/{winner[1]}"],
                                duplicate_of=f"{winner[0]}/{winner[1]}",
                            )
                            # If this slug already flagged for other reasons, merge.
                            existing = next(
                                (x for x in report.flagged if x.category == loser[0] and x.slug == loser[1]),
                                None,
                            )
                            if existing:
                                existing.reasons.extend(f.reasons)
                                existing.duplicate_of = f.duplicate_of
                            else:
                                report.flagged.append(f)
        except Exception as e:  # pragma: no cover — best-effort
            logger.debug(f"curator: near-duplicate pass skipped: {e}")

        report.finished_at = time.time()
        return report

    # ── apply ────────────────────────────────────────────────
    def apply_archive(self, report: AuditReport) -> AuditReport:
        """Archive every flagged finding via ``store.archive(actor='curator')``.

        ``store.archive`` already refuses pinned + human-authored entries —
        the policy enforcement is single-sourced there. Any refusal lands as
        a ``skipped`` entry in the report.
        """
        report.apply = True
        for f in report.flagged:
            reason = "; ".join(f.reasons)
            try:
                dst = self.store.archive(f.category, f.slug, reason=reason, actor="curator")
                if dst is not None:
                    report.archived.append(f"{f.category}/{f.slug}")
            except Exception as e:
                report.skipped.append({
                    "category": f.category, "slug": f.slug,
                    "reason": f"archive refused: {e}",
                })
        report.finished_at = time.time()
        return report

    # ── run + report ─────────────────────────────────────────
    def run(self, *, apply: bool = False) -> AuditReport:
        """Convenience: audit() + optionally apply_archive() + persist a report."""
        report = self.audit()
        if apply:
            self.apply_archive(report)
        self._persist(report)
        return report

    def _persist(self, report: AuditReport) -> Path:
        ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime(report.started_at))
        path = self.report_dir / f"{ts}.json"
        try:
            path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        except Exception:
            pass
        return path

    # ── helpers ──────────────────────────────────────────────
    def _collect_vectors(self) -> dict:
        """Pull the vector index out of the store as a dict keyed by (category, slug)."""
        idx = getattr(self.store, "_index", None)
        if idx is None:
            return {}
        out: dict[tuple[str, str], list[float]] = {}
        try:
            with idx._lock:
                rows = idx._conn.execute("SELECT category, slug, vec_json FROM skill_vec").fetchall()
            for category, slug, vec_json in rows:
                try:
                    out[(category, slug)] = json.loads(vec_json)
                except Exception:
                    continue
        except Exception as e:  # pragma: no cover
            logger.debug(f"_collect_vectors failed: {e}")
        return out


__all__ = ["Curator", "AuditReport", "AuditFinding"]
