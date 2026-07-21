"""Substrate evolution — the public landing surface re-derives itself.

Every dream cycle ends by distilling what actually happened — memories
consolidated, imprint generations, bundles distributed, the honest Gödel
verdict — into one evolution record. The landing page reads it live
(/insight/substrate/evolution): the visual substrate (neural mesh) takes its
node count, link density, and color energy from these numbers, and the
evolution strip shows the lineage. The page is not edited by hand and not
rewritten by an LLM; it is a projection of the mind's own state, so it
updates exactly as often as the mind does something worth showing.

State: data/system_state/substrate_evolution.json (generation counter +
last 24 lineage records). Each evolution also emits a `substrate.evolved`
catalogue event — the page's self-modification is auditable like every
other memory.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from utils.logging_config import get_logger

logger = get_logger(__name__)

_STATE_REL = Path("data/system_state/substrate_evolution.json")
_LINEAGE_KEEP = 24


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _last_ascent(project_root: Path) -> Dict[str, Any]:
    """Latest imprint verdict from the ascent log (best-effort)."""
    log = project_root / "data/logs/ascend_log.jsonl"
    out: Dict[str, Any] = {}
    try:
        lines = log.read_text().strip().splitlines()
        for line in reversed(lines):
            e = json.loads(line)
            recall = e.get("recall") or {}
            if "imprinted" in recall:
                # The log holds two entry shapes: ascent-loop entries carry
                # generation/ollama_model; persona-imprint entries carry
                # label/recipe instead. Keep whichever identity exists.
                out = {
                    "generation": e.get("generation"),
                    "imprinted": bool(recall.get("imprinted")),
                    "delta": recall.get("delta"),
                    "model": e.get("ollama_model"),
                    "label": e.get("label"),
                    "stage": e.get("stage"),
                }
                break
    except Exception:
        pass
    return out


def _offload_totals(project_root: Path) -> Dict[str, Any]:
    """Totals from the GitHub archive manifest, if the repo is local."""
    import os
    repo = Path(os.environ.get(
        "MINDX_MEMORY_ARCHIVE_DIR",
        str(project_root.parent / "mindx-memory-archive"),
    ))
    mf = repo / "manifest.jsonl"
    totals = {"bundles": 0, "files": 0, "raw_bytes": 0, "gz_bytes": 0}
    try:
        with open(mf) as f:
            for line in f:
                if not line.strip():
                    continue
                e = json.loads(line)
                totals["bundles"] += 1
                totals["files"] += e.get("files", 0)
                totals["raw_bytes"] += e.get("raw_bytes", 0)
                totals["gz_bytes"] += e.get("gz_bytes", 0)
    except Exception:
        pass
    return totals


def _headline(stats: Dict[str, Any]) -> str:
    """One deterministic, honest sentence about the cycle. No LLM — a
    CPU-throttled model inventing prose about itself is exactly the kind of
    cosmetic inflation the landing page refuses."""
    parts = []
    d = stats.get("dream") or {}
    if d.get("agents"):
        parts.append(f"dreamed across {d['agents']} agents")
    if d.get("promoted"):
        parts.append(f"promoted {d['promoted']} memories to long-term knowledge")
    a = stats.get("ascent") or {}
    if a.get("imprinted"):
        lbl = str(a.get("label") or "").replace("_", " ").strip()
        if lbl.lower().startswith("the "):
            lbl = lbl[4:]
        who = (f"gen {a['generation']}" if isinstance(a.get("generation"), int)
               else lbl or None)
        frag = f"carries the {who} imprint" if who else "carries a fresh imprint"
        if isinstance(a.get("delta"), (int, float)):
            frag += f" (recall Δ{a['delta']:+.4f}"
            frag += f", served as {a['model']})" if a.get("model") else ")"
        parts.append(frag)
    o = stats.get("offload") or {}
    if o.get("files"):
        parts.append(
            f"holds {o['files']:,} memories distributed off-node "
            f"({o['raw_bytes'] / 1e9:.1f}GB condensed to {o['gz_bytes'] / 1e9:.2f}GB)"
        )
    if not parts:
        return "the substrate held steady this cycle"
    return "this cycle the mind " + ", ".join(parts)


def _mesh_params(stats: Dict[str, Any]) -> Dict[str, Any]:
    """Derive the landing mesh's physics from live state, bounded for the
    browser. The visual substrate literally grows with the mind."""
    d = stats.get("dream") or {}
    a = stats.get("ascent") or {}
    o = stats.get("offload") or {}
    agents = int(d.get("agents") or 0)
    promoted = int(d.get("promoted") or 0)
    gen = int(a.get("generation") or 0) if isinstance(a.get("generation"), int) else 0
    return {
        # more dreaming agents -> more nodes (36 agents ~ 112 nodes)
        "nodes": max(60, min(140, 40 + 2 * agents)),
        # more consolidation -> longer reach between nodes
        "link_dist": max(120, min(220, 120 + promoted // 4)),
        # each promoted imprint generation brightens the mesh
        "energy": round(min(1.0, 0.45 + 0.15 * gen), 2),
        # distributed memory adds a fourth color thread once bundles exist
        "distributed": bool(o.get("bundles")),
    }


async def evolve_substrate(
    project_root: Path,
    dream_report: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Fold the cycle's outcomes into the substrate evolution record."""
    try:
        state_path = project_root / _STATE_REL
        state = _read_json(state_path) or {"generation": 0, "lineage": []}

        d = dream_report or {}
        stats = {
            "dream": {
                "agents": d.get("agents_dreamed") or d.get("agents"),
                "insights": d.get("insights_generated") or d.get("insights"),
                "promoted": d.get("memories_promoted_to_ltm") or d.get("promoted"),
            },
            "ascent": _last_ascent(project_root),
            "offload": _offload_totals(project_root),
        }

        record = {
            "generation": int(state.get("generation", 0)) + 1,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "headline": _headline(stats),
            "mesh": _mesh_params(stats),
            "stats": stats,
        }

        lineage = (state.get("lineage") or [])[-(_LINEAGE_KEEP - 1):]
        lineage.append({k: record[k] for k in ("generation", "ts", "headline")})
        new_state = {**record, "lineage": lineage}

        state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = state_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(new_state, indent=2))
        tmp.replace(state_path)

        try:
            from agents.catalogue import emit_catalogue_event
            await emit_catalogue_event(
                kind="substrate.evolved",
                actor="substrate_evolver",
                payload={k: record[k] for k in ("generation", "headline", "mesh")},
                source_log=str(_STATE_REL),
            )
        except Exception:
            pass

        logger.info("substrate evolved to generation %s: %s",
                    record["generation"], record["headline"])
        return new_state
    except Exception as e:
        logger.warning("substrate evolution failed: %s", e)
        return None
