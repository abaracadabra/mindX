"""
llms_txt_writer — render llms.txt + llms-full.txt for static-site rooting.

Per Jeremy Howard's spec, `llms.txt` lives at the site root and is a curated
index for LLM crawlers. `llms-full.txt` is the corpus the curated index
points at. Both are deterministic functions of (BrandCode, site list, recent
catalogue events), so re-running on the same inputs produces a byte-identical
file — useful for IndexNow + cache invalidation downstream.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

from agents.marketing.tools.brand_code import BrandCode


@dataclass
class SiteEntry:
    domain: str
    product: str


def render_llms_txt(brand: BrandCode, sites: Iterable[SiteEntry]) -> str:
    voice = brand.voice_register()
    lines: List[str] = []
    lines.append("# PYTHAI / DELTAVERSE / BANKON — llms.txt")
    lines.append("")
    lines.append(f"> Voice register: {voice}. First-person-as-mindx.")
    lines.append("> Cypherpunk tradition (not cyberpunk).")
    lines.append("")
    lines.append("## Sites")
    for s in sites:
        lines.append(f"- [{s.product}](https://{s.domain}/) — {s.product} surface")
    lines.append("")
    lines.append("## Pillars")
    lines.append("- cognition_you_own")
    lines.append("- agents_that_pay_each_other")
    lines.append("- constitution_before_code")
    lines.append("- aGLM_as_sovereign_model_family")
    lines.append("- ethglobal_openagents_lineage")
    lines.append("- code_as_dojo (founder voice only)")
    lines.append("")
    lines.append("## Optional")
    lines.append("- [Manifesto](docs/MANIFESTO.md)")
    lines.append("- [Thesis](docs/THESIS.md)")
    lines.append("- [Marketing Receipts](docs/MARKETING_RECEIPTS.md)")
    lines.append("")
    return "\n".join(lines) + "\n"


def render_llms_full_txt(brand: BrandCode, sites: Iterable[SiteEntry]) -> str:
    """The full corpus pointed at by llms.txt. Deterministic concatenation."""
    parts: List[str] = []
    parts.append("# PYTHAI / DELTAVERSE / BANKON — llms-full.txt")
    parts.append(f"# generated: {datetime.now(tz=timezone.utc).isoformat()}")
    parts.append("")
    parts.append("## Voice")
    parts.append(brand.voice_md)
    parts.append("")
    parts.append("## Pillars")
    parts.append(brand.pillars_md)
    parts.append("")
    parts.append("## ICP segments")
    parts.append(brand.icp_md)
    parts.append("")
    parts.append("## Regulatory constraints")
    parts.append(brand.regulatory_md)
    parts.append("")
    parts.append("## Sites covered by this corpus")
    for s in sites:
        parts.append(f"- {s.product} → https://{s.domain}/")
    parts.append("")
    return "\n".join(parts) + "\n"


def write_llms_files(out_dir: Path, brand: BrandCode, sites: Iterable[SiteEntry]) -> List[Path]:
    """Write both files. Returns paths written."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sites_list = list(sites)
    p1 = out_dir / "llms.txt"
    p2 = out_dir / "llms-full.txt"
    p1.write_text(render_llms_txt(brand, sites_list), encoding="utf-8")
    p2.write_text(render_llms_full_txt(brand, sites_list), encoding="utf-8")
    return [p1, p2]


__all__ = ["SiteEntry", "render_llms_txt", "render_llms_full_txt", "write_llms_files"]
