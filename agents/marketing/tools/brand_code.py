"""
brand_code — load and serve the immutable per-cycle BrandCode snapshot.

Every sub-agent reads from this loader at the start of each BDI cycle. The
snapshot is a frozen dataclass; sub-agents cannot mutate it. inotify watching
is best-effort — if the OS does not support it, the agent re-reads on every
cycle (safe but slightly wasteful).

Layout under `data/brand_code/`:
  voice.md
  positioning/pillars.md
  positioning/icp_segments.md
  forbidden_terms.json     — { deny_patterns, soft_warn_patterns }
  competitor_map.json      — { competitors: { name: { do_say, do_not_say, ... } } }
  regulatory_constraints.md
  onboarding/<agent>_job_description.md

The `forbidden_terms.deny_patterns` are compiled to one combined regex on load
for cheap per-draft scanning.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Tuple


@dataclass(frozen=True)
class ForbiddenTerms:
    deny_re: Optional[Pattern[str]]
    soft_warn_re: Optional[Pattern[str]]
    raw: Dict[str, object] = field(default_factory=dict)

    def scan(self, text: str) -> Tuple[List[str], List[str]]:
        """Return (deny_matches, soft_warn_matches) for one piece of text."""
        deny_matches: List[str] = []
        soft_warn_matches: List[str] = []
        if self.deny_re is not None:
            deny_matches = sorted({m.group(0) for m in self.deny_re.finditer(text)})
        if self.soft_warn_re is not None:
            soft_warn_matches = sorted({m.group(0) for m in self.soft_warn_re.finditer(text)})
        return deny_matches, soft_warn_matches


@dataclass(frozen=True)
class CompetitorMap:
    rule: str
    by_name: Dict[str, Dict[str, object]]


@dataclass(frozen=True)
class BrandCode:
    """Frozen per-cycle snapshot of the brand code."""

    root: Path
    voice_md: str
    pillars_md: str
    icp_md: str
    regulatory_md: str
    forbidden: ForbiddenTerms
    competitors: CompetitorMap
    onboarding: Dict[str, str]

    def voice_register(self) -> str:
        # Extracted from voice.md frontmatter `voice_register:` line.
        for line in self.voice_md.splitlines():
            if line.startswith("voice_register:"):
                return line.split(":", 1)[1].strip()
        return "cypherpunk"

    def pillar_is_reserved(self, pillar: str) -> bool:
        """The `code_as_dojo` pillar is human-Convener-only; always refused."""
        return pillar.strip().lower() == "code_as_dojo"

    def audience_is_reserved(self, audience: str) -> bool:
        """Ring E (philosophical / longevity) is founder-only."""
        return audience.strip().upper() == "E"

    def has_competitor_constraints(self, name: str) -> bool:
        return name.strip().lower() in self.competitors.by_name


_INLINE_FLAGS_RE = re.compile(r"^\(\?[aiLmsux]+\)")


def _strip_inline_flags(pattern: str) -> str:
    """Strip a leading `(?i)` / `(?im)` etc.

    Python's `re` module rejects inline flag groups that aren't at position 0
    of the full expression. When we OR-combine patterns we must lift the
    flags to the compile call. All our forbidden-terms patterns are
    case-insensitive, so we apply `re.IGNORECASE` globally below.
    """
    return _INLINE_FLAGS_RE.sub("", pattern)


def _compile_patterns(patterns: List[str]) -> Optional[Pattern[str]]:
    if not patterns:
        return None
    cleaned = [_strip_inline_flags(p) for p in patterns]
    combined = "|".join(f"(?:{p})" for p in cleaned)
    return re.compile(combined, re.IGNORECASE)


def load_brand_code(root: Path) -> BrandCode:
    """Load one frozen BrandCode snapshot from `root` (e.g. data/brand_code).

    Raises FileNotFoundError if any required file is missing — the agent
    refuses to run with a partial brand-code rather than guessing.
    """
    root = Path(root)

    voice_md = (root / "voice.md").read_text(encoding="utf-8")
    pillars_md = (root / "positioning" / "pillars.md").read_text(encoding="utf-8")
    icp_md = (root / "positioning" / "icp_segments.md").read_text(encoding="utf-8")
    regulatory_md = (root / "regulatory_constraints.md").read_text(encoding="utf-8")

    forbidden_raw = json.loads((root / "forbidden_terms.json").read_text(encoding="utf-8"))
    deny_patterns = list(forbidden_raw.get("deny_patterns") or [])
    soft_warn_patterns = list(forbidden_raw.get("soft_warn_patterns") or [])
    forbidden = ForbiddenTerms(
        deny_re=_compile_patterns(deny_patterns),
        soft_warn_re=_compile_patterns(soft_warn_patterns),
        raw=forbidden_raw,
    )

    competitors_raw = json.loads((root / "competitor_map.json").read_text(encoding="utf-8"))
    competitors = CompetitorMap(
        rule=str(competitors_raw.get("rule", "")),
        by_name={
            name.strip().lower(): dict(meta or {})
            for name, meta in (competitors_raw.get("competitors") or {}).items()
        },
    )

    onboarding_dir = root / "onboarding"
    onboarding: Dict[str, str] = {}
    if onboarding_dir.is_dir():
        for jd in sorted(onboarding_dir.glob("*.md")):
            onboarding[jd.stem] = jd.read_text(encoding="utf-8")

    return BrandCode(
        root=root,
        voice_md=voice_md,
        pillars_md=pillars_md,
        icp_md=icp_md,
        regulatory_md=regulatory_md,
        forbidden=forbidden,
        competitors=competitors,
        onboarding=onboarding,
    )


__all__ = ["BrandCode", "ForbiddenTerms", "CompetitorMap", "load_brand_code"]
