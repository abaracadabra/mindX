# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""dojo_bridge — mindXtrain takes updates from the-dojo, as necessary for LoRA.

the-dojo (`~/the-dojo`, the Train→Serve→Spar→Score→Export→Retrain app) produces
LoRA adapters and curated datasets. Its first imprint succeeded
(`outputs/qwen3-0.6b-lora/adapter_model.safetensors`). This bridge lets the mindXtrain
ascent CONSUME those updates: continue from a dojo LoRA (warm start) and fold dojo
datasets into the training corpus. Read-only, clean-room, dependency-free.

Discovery only — nothing here trains; the ascent (dormant behind MINDX_ENABLE_MINDXTRAIN)
decides whether to use what this surfaces.
"""
from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def dojo_dir() -> Optional[Path]:
    """Locate the dojo. Prefers the vendored Python core (mindx/godel/mindxtrain/dojo);
    then MINDX_DOJO_DIR; then the standalone Tauri dApp checkout (~/the-dojo)."""
    vendored = Path(__file__).parent / "dojo"
    for cand in (str(vendored) if (vendored / "engine").is_dir() else None,
                 os.getenv("MINDX_DOJO_DIR"), os.path.expanduser("~/the-dojo"),
                 "/home/hacker/the-dojo", "/home/mindx/the-dojo"):
        if cand and Path(cand).is_dir():
            return Path(cand)
    return None


def _is_lora(d: Path) -> bool:
    return (d / "adapter_config.json").exists() and any(
        (d / f).exists() for f in ("adapter_model.safetensors", "adapter_model.bin"))


def dojo_updates() -> Dict[str, Any]:
    """Manifest of updates available from the-dojo: LoRA adapters, datasets, logs."""
    root = dojo_dir()
    if root is None:
        return {"available": False, "reason": "the-dojo not found (set MINDX_DOJO_DIR)"}
    adapters: List[Dict[str, Any]] = []
    out = root / "outputs"
    if out.is_dir():
        for d in sorted(out.iterdir()):
            if d.is_dir() and _is_lora(d):
                cfg = {}
                try:
                    cfg = json.loads((d / "adapter_config.json").read_text(encoding="utf-8"))
                except Exception:
                    pass
                weight = next((d / f for f in ("adapter_model.safetensors", "adapter_model.bin")
                               if (d / f).exists()), None)
                adapters.append({
                    "name": d.name, "path": str(d),
                    "base_model": cfg.get("base_model_name_or_path"),
                    "r": cfg.get("r"), "lora_alpha": cfg.get("lora_alpha"),
                    "size_mb": round(weight.stat().st_size / 1e6, 2) if weight else None,
                    "mtime": weight.stat().st_mtime if weight else None,
                })
    datasets: List[Dict[str, Any]] = []
    ds = root / "datasets"
    if ds.is_dir():
        for f in sorted(ds.glob("*.jsonl")):
            try:
                n = sum(1 for _ in f.open("r", encoding="utf-8"))
            except Exception:
                n = None
            datasets.append({"name": f.name, "path": str(f), "rows": n})
    logs = sorted((root / "logs").glob("*.log")) if (root / "logs").is_dir() else []
    return {"available": True, "dojo_dir": str(root),
            "adapters": adapters, "datasets": datasets,
            "latest_log": str(logs[-1]) if logs else None,
            "adapter_count": len(adapters), "dataset_count": len(datasets)}


def latest_lora() -> Optional[Dict[str, Any]]:
    """The most recently written dojo LoRA adapter — the warm-start candidate."""
    m = dojo_updates()
    ads = [a for a in m.get("adapters", []) if a.get("mtime")]
    if not ads:
        return None
    return sorted(ads, key=lambda a: a["mtime"], reverse=True)[0]


def dojo_dataset_paths() -> List[str]:
    """Paths of dojo datasets to fold into the training corpus (as necessary for LoRA)."""
    return [d["path"] for d in dojo_updates().get("datasets", [])]


def stage_datasets(dest_dir: Path) -> Dict[str, Any]:
    """Copy dojo datasets into a training-corpus dir so mindXtrain's dream adapter
    picks them up alongside the dreams. Idempotent (skips identical sizes)."""
    import shutil
    dest = Path(dest_dir); dest.mkdir(parents=True, exist_ok=True)
    staged = []
    for p in dojo_dataset_paths():
        src = Path(p); tgt = dest / f"dojo_{src.name}"
        try:
            if not tgt.exists() or tgt.stat().st_size != src.stat().st_size:
                shutil.copyfile(src, tgt)
            staged.append(str(tgt))
        except Exception:
            pass
    return {"staged": staged, "count": len(staged), "dest": str(dest)}
