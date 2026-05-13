# SPDX-License-Identifier: Apache-2.0
"""mindX skills — procedural memory in the SKILL.md format.

A skill is a named, retrievable, refinable BDI Intention template. The schema
mirrors Hermes Agent's `~/.hermes/skills/<category>/<slug>/SKILL.md` shape
(YAML frontmatter + Markdown body) so any skill written by an OpenClaw or
Hermes agent migrates trivially. Skills live at
``$MINDX_SKILLS_DIR/<category>/<slug>/SKILL.md`` (default
``~/.mindx/skills/``).

Day-1 surface (this module):
  * ``skill_schema`` — Pydantic v2 schema for the frontmatter + Skill object,
    plus the read/write codec (front-matter-fenced ``---`` YAML, Markdown body).
  * ``scanner`` — screen-before-persist gate: prompt-injection patterns,
    data-exfil patterns, destructive commands, size cap. Refuses to land an
    agent-authored skill that fails the scan.
  * ``store`` — SkillStore: read/write/list/search/archive on disk. Archive
    is the maximum destructive action (no delete) — matches the Hermes
    Curator's authority model.

Deferred (subsequent passes):
  * `skill_distill` action on the BDI action set (compose a SKILL.md draft
    after a successful intention completed in ≥N steps and surface to
    MASTERMIND for ratification).
  * Curator background job — MASTERMIND-scheduled, 7-day cadence, auxiliary
    LLM only, archive-only authority on ``created_by=agent`` skills.
  * Hybrid retrieval (vector + FTS5) at intention-compilation time.
  * DSPy + GEPA evolutionary optimizer in a separate ``mindx-self-evolution``
    repo.

Source-of-truth reference:
``docs/operations/Hermes Agent Integration Patterns for mindX_…md`` §8.1.

License: Apache-2.0. Hermes Agent is MIT.
"""

from agents.skills.skill_schema import (
    Skill,
    SkillFrontmatter,
    parse_skill_md,
    serialize_skill_md,
)
from agents.skills.scanner import (
    SkillFinding,
    SkillScanResult,
    scan_skill,
)
from agents.skills.store import SkillRef, SkillStore
from agents.skills.learning_log import (
    LOG_FILES,
    LearningEntry,
    LearningLog,
)

# Hybrid 70/30 BM25 + vector retrieval lives in `index`. Lazy import — the
# rest of the module is useable even if sqlite3 / httpx are missing.
try:
    from agents.skills.index import (
        CANDIDATE_MULTIPLIER,
        DEFAULT_VECTOR_WEIGHT,
        SkillIndex,
    )
except Exception:  # pragma: no cover
    SkillIndex = None  # type: ignore
    DEFAULT_VECTOR_WEIGHT = 0.7
    CANDIDATE_MULTIPLIER = 4

__all__ = [
    "Skill",
    "SkillFrontmatter",
    "parse_skill_md",
    "serialize_skill_md",
    "SkillFinding",
    "SkillScanResult",
    "scan_skill",
    "SkillRef",
    "SkillStore",
    "SkillIndex",
    "DEFAULT_VECTOR_WEIGHT",
    "CANDIDATE_MULTIPLIER",
    "LearningLog",
    "LearningEntry",
    "LOG_FILES",
]
