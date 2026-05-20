# SPDX-License-Identifier: Apache-2.0
"""SKILL.md frontmatter + body schema.

The on-disk shape matches Hermes Agent's
``~/.hermes/skills/<category>/<slug>/SKILL.md`` (YAML frontmatter fenced by
``---``, then Markdown body) so a skill written by Hermes / OpenClaw / Claude
Code / Cursor / Codex is import-compatible without translation.

mindX adds three frontmatter fields the BDI compiler will use:
  * ``intention_template`` — id of the BDI Intention template this skill
    instantiates. Empty for skills that don't bind to a specific template.
  * ``preconditions`` — list of belief keys that must hold before the skill
    can be selected. Each key references a key in the agent's Belief store.
  * ``postconditions`` — list of belief keys the skill is expected to assert
    on completion. Used by the MASTERMIND hallucination gate (§8.3 of the
    Hermes integration doc) to verify a subagent's claim of completion.

Plus ``created_by`` (``agent`` | ``human``) which scopes the Curator's
archive authority — pinned + human-authored skills are off-limits, matching
Hermes' policy.
"""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field

# Sentinel size used by the scanner; documented here so both schema + scanner
# agree.
MAX_SKILL_BYTES = 15 * 1024  # 15 KB — Hermes constraint, see §2.6 of the doc.

# A loose slug pattern — lowercase alphanumerics, dashes, underscores. Allows
# nested categories via path separators in the SkillStore (not here).
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]{0,63}$")


class SkillFrontmatter(BaseModel):
    """YAML frontmatter block for a SKILL.md."""

    model_config = ConfigDict(extra="allow")   # keep forward-compat with Hermes additions

    # — Hermes-compatible core fields —
    name: str
    description: str
    version: str = "0.1.0"
    author: str = "mindX"

    # — Agent provenance (governs Curator authority) —
    created_by: Literal["agent", "human"] = "agent"
    pinned: bool = False

    # — mindX BDI additions —
    intention_template: Optional[str] = None
    preconditions: list[str] = Field(default_factory=list)
    postconditions: list[str] = Field(default_factory=list)

    # — Discovery / activation (Hermes shape) —
    category: str = "general"
    tags: list[str] = Field(default_factory=list)
    related_skills: list[str] = Field(default_factory=list)
    requires_tools: list[str] = Field(default_factory=list)
    requires_toolsets: list[str] = Field(default_factory=list)
    fallback_for_tools: list[str] = Field(default_factory=list)
    fallback_for_toolsets: list[str] = Field(default_factory=list)

    # — Bookkeeping —
    created_at: float = Field(default_factory=lambda: time.time())
    updated_at: float = Field(default_factory=lambda: time.time())

    # — Optional provenance: who/what produced this skill (audit only) —
    source: Optional[str] = None  # e.g. "mastermind.skill_distill", "imported:openclaw"


class Skill(BaseModel):
    """A full skill — frontmatter + Markdown body."""
    frontmatter: SkillFrontmatter
    body: str = ""

    @property
    def slug(self) -> str:
        """Conventional slug from name (kebab-case)."""
        s = self.frontmatter.name.lower().strip()
        s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
        return s[:64] or "unnamed-skill"

    @property
    def total_bytes(self) -> int:
        return len(serialize_skill_md(self).encode("utf-8"))


# ─── codec ────────────────────────────────────────────────────────


_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<yaml>.*?)\n---\s*\n?(?P<body>.*)\Z", re.DOTALL
)


def parse_skill_md(text_or_path) -> Skill:
    """Parse a SKILL.md from a path or a string.

    Raises ``ValueError`` for malformed input (no frontmatter, bad YAML,
    schema validation failure).
    """
    if isinstance(text_or_path, Path):
        text = text_or_path.read_text(encoding="utf-8")
    elif isinstance(text_or_path, str):
        # Treat as a file path only if it's short, single-line, and the file exists.
        # Long multi-line strings (the typical SKILL.md text) skip the path check.
        is_path_like = len(text_or_path) < 4096 and "\n" not in text_or_path
        if is_path_like:
            try:
                p = Path(text_or_path)
                if p.exists() and p.is_file():
                    text = p.read_text(encoding="utf-8")
                else:
                    text = text_or_path
            except OSError:
                text = text_or_path
        else:
            text = text_or_path
    else:
        text = str(text_or_path)

    m = _FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError("SKILL.md must start with --- YAML frontmatter --- followed by Markdown body")

    try:
        raw = yaml.safe_load(m.group("yaml")) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"invalid YAML frontmatter: {e}") from e
    if not isinstance(raw, dict):
        raise ValueError("frontmatter must be a YAML mapping (key: value)")

    fm = SkillFrontmatter.model_validate(raw)
    body = m.group("body").lstrip("\n")
    return Skill(frontmatter=fm, body=body)


def serialize_skill_md(skill: Skill) -> str:
    """Render a Skill as a SKILL.md string (---YAML---\\nbody)."""
    fm_dict = skill.frontmatter.model_dump(exclude_none=True)
    yaml_text = yaml.safe_dump(fm_dict, sort_keys=False, allow_unicode=True).rstrip()
    body = skill.body.rstrip() + "\n" if skill.body else ""
    return f"---\n{yaml_text}\n---\n{body}"


__all__ = [
    "MAX_SKILL_BYTES",
    "SLUG_RE",
    "SkillFrontmatter",
    "Skill",
    "parse_skill_md",
    "serialize_skill_md",
]
