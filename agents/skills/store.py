# SPDX-License-Identifier: Apache-2.0
"""SkillStore — on-disk read/write/list/search/archive for SKILL.md files.

Layout (default ``$MINDX_SKILLS_DIR`` or ``~/.mindx/skills``)::

    <root>/<category>/<slug>/SKILL.md
    <root>/.archive/<YYYYmmdd_HHMMSS>/<category>/<slug>/...

The Curator (deferred; will be a MASTERMIND-scheduled background job) only
ever **archives** — never deletes. Pinned (``frontmatter.pinned: true``) and
human-authored (``created_by: "human"``) skills are off-limits to the Curator;
``SkillStore.archive`` enforces this for ``actor="curator"``.

Search is substring-match across name + description + tags on Day-1. Hybrid
vector+FTS5 retrieval lands in a subsequent pass (see ``__init__.py``).
"""
from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from agents.skills.scanner import SkillScanResult, scan_skill
from agents.skills.skill_schema import (
    SLUG_RE,
    Skill,
    SkillFrontmatter,
    parse_skill_md,
    serialize_skill_md,
)


@dataclass(frozen=True)
class SkillRef:
    """Lightweight pointer — used by ``list()`` / search results."""
    category: str
    slug: str
    name: str
    description: str
    created_by: str
    pinned: bool
    path: Path


class SkillStoreError(Exception):
    """Raised when a skill cannot be written (blocked by the scanner, etc.)."""


class SkillStore:
    """On-disk repository of SKILL.md files."""

    def __init__(self, root: Optional[Path | str] = None):
        if root is None:
            env = os.environ.get("MINDX_SKILLS_DIR")
            root = Path(env) if env else Path.home() / ".mindx" / "skills"
        self.root = Path(root)
        self.archive_root = self.root / ".archive"
        self.root.mkdir(parents=True, exist_ok=True)

    # ─── path helpers ──────────────────────────────────────────────
    def _path_for(self, category: str, slug: str) -> Path:
        if not SLUG_RE.match(slug):
            raise ValueError(f"invalid slug {slug!r}")
        if not SLUG_RE.match(category):
            raise ValueError(f"invalid category {category!r}")
        return self.root / category / slug / "SKILL.md"

    # ─── read / write ──────────────────────────────────────────────
    def read(self, category: str, slug: str) -> Optional[Skill]:
        p = self._path_for(category, slug)
        if not p.exists():
            return None
        return parse_skill_md(p)

    def write(self, skill: Skill, *, actor: str = "agent") -> tuple[Path, SkillScanResult]:
        """Persist ``skill``. Returns ``(path, scan_result)``.

        Policy:
          * Skill must pass the scanner (``scan_result.safe`` is True),
            otherwise raises :class:`SkillStoreError` listing the blocks.
          * If the scanner returns warnings (e.g. data-exfiltration patterns),
            agent-authored skills are blocked; human-authored & pinned skills
            are allowed (operator override) but the warnings are returned.
        """
        scan = scan_skill(skill)

        if not scan.safe:
            raise SkillStoreError("skill blocked by scanner: " + "; ".join(scan.block_reasons()))

        # Operator override for warnings: human + pinned only.
        warnings = [f for f in scan.findings if f.severity == "warning"]
        fm = skill.frontmatter
        if warnings and not (fm.created_by == "human" and fm.pinned):
            raise SkillStoreError(
                "skill has warnings the scanner won't pass unattended: "
                + "; ".join(f.short() for f in warnings)
                + " (set created_by='human' AND pinned=true to override)"
            )

        # Touch updated_at (preserve created_at if writing an update)
        fm.updated_at = time.time()

        slug = skill.slug
        if not SLUG_RE.match(slug):
            raise ValueError(f"computed slug {slug!r} is invalid")
        path = self._path_for(fm.category, slug)
        path.parent.mkdir(parents=True, exist_ok=True)

        text = serialize_skill_md(skill)
        tmp = path.with_suffix(".md.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
        try:
            os.chmod(path, 0o600)
        except Exception:
            pass

        return path, scan

    # ─── list / search ──────────────────────────────────────────────
    def list(self, category: Optional[str] = None) -> list[SkillRef]:
        refs: list[SkillRef] = []
        roots = [self.root / category] if category else [self.root]
        for r in roots:
            if not r.exists():
                continue
            for p in sorted(r.glob("*/SKILL.md")) if category else sorted(r.glob("*/*/SKILL.md")):
                if ".archive" in p.parts:
                    continue
                try:
                    sk = parse_skill_md(p)
                except Exception:
                    continue
                cat = category or p.parents[1].name
                refs.append(SkillRef(
                    category=cat,
                    slug=p.parent.name,
                    name=sk.frontmatter.name,
                    description=sk.frontmatter.description,
                    created_by=sk.frontmatter.created_by,
                    pinned=sk.frontmatter.pinned,
                    path=p,
                ))
        return refs

    def search(self, query: str, limit: int = 10) -> list[SkillRef]:
        """Substring-match across name + description + tags + intention_template."""
        q = (query or "").strip().lower()
        if not q:
            return self.list()[:limit]
        hits: list[SkillRef] = []
        for ref in self.list():
            try:
                sk = parse_skill_md(ref.path)
            except Exception:
                continue
            hay = " ".join([
                sk.frontmatter.name.lower(),
                sk.frontmatter.description.lower(),
                " ".join(sk.frontmatter.tags).lower(),
                (sk.frontmatter.intention_template or "").lower(),
            ])
            if q in hay:
                hits.append(ref)
            if len(hits) >= limit:
                break
        return hits

    # ─── archive (Curator-friendly) ────────────────────────────────
    def archive(
        self,
        category: str,
        slug: str,
        *,
        reason: str,
        actor: str = "human",
    ) -> Optional[Path]:
        """Move a skill into ``.archive/<timestamp>/<category>/<slug>/``.

        Returns the new path, or ``None`` if the skill doesn't exist.

        When ``actor == "curator"``, refuses to archive pinned or
        human-authored skills (matches Hermes' Curator policy).
        """
        src = self._path_for(category, slug).parent
        if not src.exists():
            return None

        sk = self.read(category, slug)
        if sk is not None and actor == "curator":
            if sk.frontmatter.pinned:
                raise SkillStoreError(f"refuse to archive pinned skill {category}/{slug} as curator")
            if sk.frontmatter.created_by == "human":
                raise SkillStoreError(f"refuse to archive human-authored skill {category}/{slug} as curator")

        ts = time.strftime("%Y%m%d_%H%M%S")
        dst_root = self.archive_root / ts / category
        dst_root.mkdir(parents=True, exist_ok=True)
        dst = dst_root / slug
        shutil.move(str(src), str(dst))

        meta = {
            "archived_at": time.time(),
            "actor": actor,
            "reason": reason,
            "original_path": str(src),
        }
        try:
            (dst / "_archive.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        except Exception:
            pass
        return dst


__all__ = ["SkillStore", "SkillRef", "SkillStoreError"]
