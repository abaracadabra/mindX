# SPDX-License-Identifier: Apache-2.0
"""LearningLog — structured `LEARNINGS.md` / `ERRORS.md` / `FEATURE_REQUESTS.md`.

Third concrete absorption from the Hermes/OpenClaw research stack. The
``self-improving-agent`` skill (Peter Skoett, widely-forked OpenClaw skill;
see ``docs/operations/openclaw_mindx_research.md`` §3.1) captures three
distinct signal classes into three append-only markdown logs and tracks each
entry through ``pending → promoted`` status. mindX inherits the pattern
verbatim, but routes the writes through the existing memory infrastructure
so the entries are catalogued and (eventually) eligible for promotion to
``SOUL.md`` / ``SKILL.md``.

The six triggers from the OpenClaw skill (§3.1, mapped onto mindX):

  1. Tool / command fails unexpectedly         ⇒ ``ERRORS.md``
  2. User corrects the agent                   ⇒ ``LEARNINGS.md``
  3. User requests a capability that doesn't exist  ⇒ ``FEATURE_REQUESTS.md``
  4. External API / tool fails                 ⇒ ``ERRORS.md``
  5. Agent realises its knowledge is outdated  ⇒ ``LEARNINGS.md``
  6. Better approach discovered for a recurring task ⇒ ``LEARNINGS.md``

Promotion: when a learning is **validated** (cross-referenced against ≥N
subsequent runs, no contradictions in the catalogue), an operator (or the
deferred MASTERMIND Curator) can mark it ``status: promoted`` and emit a
``Skill`` draft into the ``SkillStore``. The scanner runs on every promotion.

Storage: ``$MINDX_LEARNINGS_DIR`` (default ``data/learnings/`` so it sits
next to ``data/memory/``). Files are append-only markdown with entries
delimited by ``---\\n## <kind>:<id>\\n`` headers and per-entry YAML
frontmatter.

The first-person voice in the body matches the rest of mindX's writing:
*"I tried X. It failed because Y. Next time I will Z."*
"""
from __future__ import annotations

import json
import logging
import os
import re
import secrets
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

logger = logging.getLogger("agents.skills.learning_log")

# The three log kinds — file basenames live as a dict so future kinds can
# slot in without touching call sites.
LOG_FILES = {
    "learning": "LEARNINGS.md",
    "error": "ERRORS.md",
    "feature_request": "FEATURE_REQUESTS.md",
}

Kind = Literal["learning", "error", "feature_request"]
Status = Literal["pending", "validated", "promoted", "withdrawn"]

# Trigger taxonomy — from the OpenClaw self-improving-agent skill (§3.1)
# minus the agent-loop-specific cases that don't map onto mindX yet.
Trigger = Literal[
    "tool_failed",
    "user_correction",
    "missing_capability",
    "external_api_failed",
    "knowledge_stale",
    "better_approach_found",
]


# Entry id: short, sortable, collision-resistant (timestamp + 4 hex chars).
def _new_entry_id() -> str:
    return f"{int(time.time())}-{secrets.token_hex(2)}"


@dataclass
class LearningEntry:
    """One row in a learning log. The Markdown body carries the narrative;
    the frontmatter carries the bookkeeping the Curator / MASTERMIND need.
    """
    id: str
    kind: Kind
    trigger: Trigger
    status: Status = "pending"
    title: str = ""
    body: str = ""
    agent_id: Optional[str] = None
    related_skill: Optional[str] = None        # set when promoted into a SkillStore entry
    promoted_at: Optional[float] = None
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())

    def to_md_block(self) -> str:
        """Render the entry as a single self-contained markdown block."""
        import yaml
        fm = {
            "id": self.id,
            "kind": self.kind,
            "trigger": self.trigger,
            "status": self.status,
            "agent_id": self.agent_id,
            "related_skill": self.related_skill,
            "promoted_at": self.promoted_at,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        fm = {k: v for k, v in fm.items() if v not in (None, [])}
        yaml_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).rstrip()
        title = self.title.strip() or f"untitled-{self.id}"
        body = (self.body or "").rstrip()
        return f"---\n## {self.kind}:{self.id}\n```yaml\n{yaml_text}\n```\n\n### {title}\n\n{body}\n"


_ENTRY_RE = re.compile(
    r"^---\s*\n## (?P<kind>\w+):(?P<id>[\w\-]+)\s*\n```yaml\s*\n(?P<yaml>.*?)\n```\s*\n\n### (?P<title>.+?)\n\n(?P<body>.*?)(?=\n---\n|$)",
    re.MULTILINE | re.DOTALL,
)


def _parse_entries(text: str) -> list[LearningEntry]:
    import yaml as _yaml
    out: list[LearningEntry] = []
    for m in _ENTRY_RE.finditer(text):
        try:
            fm = _yaml.safe_load(m.group("yaml")) or {}
            if not isinstance(fm, dict):
                continue
        except _yaml.YAMLError:
            continue
        out.append(LearningEntry(
            id=fm.get("id", m.group("id")),
            kind=fm.get("kind", m.group("kind")),
            trigger=fm.get("trigger", "tool_failed"),
            status=fm.get("status", "pending"),
            title=m.group("title").strip(),
            body=m.group("body").rstrip(),
            agent_id=fm.get("agent_id"),
            related_skill=fm.get("related_skill"),
            promoted_at=fm.get("promoted_at"),
            tags=list(fm.get("tags", []) or []),
            created_at=float(fm.get("created_at", time.time())),
            updated_at=float(fm.get("updated_at", time.time())),
        ))
    return out


class LearningLog:
    """Append-only logs of learnings/errors/feature-requests.

    Thread-safe (a single ``RLock`` guards the file). Append-only on disk;
    updates (e.g. status changes) are written by replacing the file with a
    re-serialised version of all entries, atomically.
    """

    def __init__(self, root: Optional[Path | str] = None):
        if root is None:
            env = os.environ.get("MINDX_LEARNINGS_DIR")
            # Default colocates with data/ so it shares the existing backup posture.
            try:
                from utils.config import PROJECT_ROOT as _PR
                default = Path(_PR) / "data" / "learnings"
            except Exception:
                default = Path.cwd() / "data" / "learnings"
            root = Path(env) if env else default
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _path(self, kind: Kind) -> Path:
        return self.root / LOG_FILES[kind]

    # ── core write ─────────────────────────────────────────────
    def append(
        self,
        *,
        kind: Kind,
        trigger: Trigger,
        title: str,
        body: str,
        agent_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> LearningEntry:
        """Append a new entry. Returns the persisted :class:`LearningEntry`."""
        entry = LearningEntry(
            id=_new_entry_id(),
            kind=kind,
            trigger=trigger,
            status="pending",
            title=title.strip(),
            body=body.strip(),
            agent_id=agent_id,
            tags=list(tags or []),
        )
        with self._lock:
            path = self._path(kind)
            block = entry.to_md_block()
            if path.exists():
                with path.open("a", encoding="utf-8") as fh:
                    fh.write(block)
            else:
                header = f"# {kind.replace('_', ' ').title()}\n\n*Append-only log. One entry per `---` block. Status: pending → validated → promoted.*\n\n"
                path.write_text(header + block, encoding="utf-8")
        return entry

    # ── read / search ──────────────────────────────────────────
    def list(self, kind: Optional[Kind] = None, *, status: Optional[Status] = None) -> list[LearningEntry]:
        kinds: list[Kind] = [kind] if kind else list(LOG_FILES.keys())  # type: ignore[list-item]
        out: list[LearningEntry] = []
        with self._lock:
            for k in kinds:
                p = self._path(k)
                if not p.exists():
                    continue
                for e in _parse_entries(p.read_text(encoding="utf-8")):
                    if status is None or e.status == status:
                        out.append(e)
        out.sort(key=lambda e: e.created_at, reverse=True)
        return out

    def get(self, kind: Kind, entry_id: str) -> Optional[LearningEntry]:
        with self._lock:
            for e in self.list(kind=kind):
                if e.id == entry_id:
                    return e
        return None

    # ── status transitions ────────────────────────────────────
    def update_status(self, kind: Kind, entry_id: str, new_status: Status) -> bool:
        """In-place status update. Returns True on success, False if missing."""
        with self._lock:
            path = self._path(kind)
            if not path.exists():
                return False
            entries = _parse_entries(path.read_text(encoding="utf-8"))
            for e in entries:
                if e.id == entry_id:
                    e.status = new_status
                    e.updated_at = time.time()
                    if new_status == "promoted":
                        e.promoted_at = time.time()
                    break
            else:
                return False
            self._rewrite(kind, entries)
            return True

    def _rewrite(self, kind: Kind, entries: list[LearningEntry]) -> None:
        """Atomically rewrite the file with the given entries."""
        path = self._path(kind)
        header = f"# {kind.replace('_', ' ').title()}\n\n*Append-only log. One entry per `---` block. Status: pending → validated → promoted.*\n\n"
        text = header + "".join(e.to_md_block() for e in entries)
        tmp = path.with_suffix(".md.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)

    # ── promotion to a skill ─────────────────────────────────
    def promote_to_skill(
        self,
        kind: Kind,
        entry_id: str,
        *,
        store,
        category: str = "promoted-learnings",
        intention_template: Optional[str] = None,
        preconditions: Optional[list[str]] = None,
        postconditions: Optional[list[str]] = None,
        created_by: Literal["agent", "human"] = "human",
    ):
        """Promote an entry to a :class:`Skill` in the given :class:`SkillStore`.

        Workflow (matches the Hermes Curator policy + the OpenClaw §3.1
        promotion criteria):

          1. Read the entry.
          2. Build a Skill whose body is the entry's body, frontmatter draws
             from the entry's title/tags/agent_id and the caller-supplied
             BDI fields.
          3. Run it through ``store.write()`` — the scanner gate applies as
             usual; a learning that contains prompt-injection or destructive
             commands cannot become a skill.
          4. On success, mark the entry ``promoted`` and record the new
             skill's slug in ``related_skill``.

        Returns the persisted Skill on success, raises on scanner refusal.
        """
        # Lazy import — avoids a circular dep at module load.
        from agents.skills.skill_schema import Skill, SkillFrontmatter

        entry = self.get(kind, entry_id)
        if entry is None:
            raise ValueError(f"no entry {kind}/{entry_id}")

        sk = Skill(
            frontmatter=SkillFrontmatter(
                name=entry.title or f"learning-{entry.id}",
                description=(entry.body[:160].splitlines() or [""])[0].strip() or f"Promoted from {kind}/{entry.id}",
                category=category,
                tags=list(entry.tags),
                created_by=created_by,
                intention_template=intention_template,
                preconditions=list(preconditions or []),
                postconditions=list(postconditions or []),
                source=f"learning_log:{kind}:{entry_id}",
            ),
            body=entry.body,
        )
        path, _scan = store.write(sk)

        # Update the log entry on successful promotion.
        with self._lock:
            entries = _parse_entries(self._path(kind).read_text(encoding="utf-8"))
            for e in entries:
                if e.id == entry_id:
                    e.status = "promoted"
                    e.promoted_at = time.time()
                    e.updated_at = time.time()
                    e.related_skill = f"{sk.frontmatter.category}/{sk.slug}"
                    break
            self._rewrite(kind, entries)
        return sk

    # ── audit summary ────────────────────────────────────────
    def summary(self) -> dict:
        """Return a small JSON dict of counts by kind × status. Useful for
        the diagnostics dashboard."""
        out = {k: {"pending": 0, "validated": 0, "promoted": 0, "withdrawn": 0, "total": 0} for k in LOG_FILES}
        for e in self.list():
            kind = e.kind
            if kind in out:
                out[kind][e.status] = out[kind].get(e.status, 0) + 1
                out[kind]["total"] += 1
        return out


__all__ = ["LearningLog", "LearningEntry", "Kind", "Status", "Trigger", "LOG_FILES"]
