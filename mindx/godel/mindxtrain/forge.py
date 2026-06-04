"""forge — build the deterministic dataset bundle + the mindXtrain run config.

Given a curated corpus, forge() produces two artifacts:

  1. a content-addressed dataset bundle (deterministic, byte-stable) so the
     same curriculum always yields the same bundle id — provenance for the
     mindXtrain `contracts/` ERC-8004 attestation registry and mindX's own
     storage/anchor layer. We compute a sha256 over the canonicalized rows;
     when the storage CAR-bundle helper is available we defer to it for a
     real IPFS CID, otherwise the sha256 stands in.

  2. an XTrainConfig YAML (mindXtrain's 10-section schema) whose `data`
     section points its `mindx_dreams` source at the bundle, selects the LoRA
     template, and records the budget/eval knobs. This is what
     `mindxtrain init` / `mindxtrain train` consume.

YAML is emitted by hand (no PyYAML dependency) to keep the bridge stdlib-only
and CPU-safe.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from . import DEFAULT_TEMPLATE, MINDX_DREAMS_SOURCE
from .distill import DreamRow


@dataclass
class ForgeResult:
    corpus_path: Path
    config_path: Path
    bundle_id: str            # sha256 (or IPFS CID if storage layer present)
    row_count: int
    template: str
    meta: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "corpus_path": str(self.corpus_path),
            "config_path": str(self.config_path),
            "bundle_id": self.bundle_id,
            "row_count": self.row_count,
            "template": self.template,
            **self.meta,
        }


def _canonical_bundle_id(corpus_path: Path) -> str:
    """Deterministic id over the corpus bytes. Prefers a real CID if the
    storage CAR-bundle helper is importable; else sha256 (byte-stable)."""
    raw = corpus_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    try:  # reuse mindX's deterministic gzipped-JSONL CAR bundler if present
        from agents.storage.car_bundle import compute_cid  # type: ignore
        return compute_cid(raw)  # byte-stable CID
    except Exception:
        return f"sha256:{sha}"


def _emit_yaml(cfg: dict, path: Path) -> None:
    """Minimal, deterministic YAML writer for the flat/nested config we need."""
    def dump(obj, indent=0):
        pad = "  " * indent
        lines = []
        for k, v in obj.items():
            if isinstance(v, dict):
                lines.append(f"{pad}{k}:")
                lines.extend(dump(v, indent + 1))
            elif isinstance(v, list):
                lines.append(f"{pad}{k}:")
                for item in v:
                    if isinstance(item, dict):
                        first = True
                        for ik, iv in item.items():
                            prefix = f"{pad}  - " if first else f"{pad}    "
                            lines.append(f"{prefix}{ik}: {json.dumps(iv)}")
                            first = False
                    else:
                        lines.append(f"{pad}  - {json.dumps(item)}")
            else:
                lines.append(f"{pad}{k}: {json.dumps(v)}")
        return lines

    path.parent.mkdir(parents=True, exist_ok=True)
    header = ("# mindXtrain XTrainConfig — forged by mindx.godel.mindxtrain.forge\n"
              f"# generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")
    path.write_text(header + "\n".join(dump(cfg)) + "\n", encoding="utf-8")


def forge(
    rows: Iterable[DreamRow],
    *,
    out_dir: Path,
    generation: int,
    base_model: str = "Qwen/Qwen3-8B",
    template: str = DEFAULT_TEMPLATE,
) -> ForgeResult:
    """Write corpus + config; return provenance for the ascent step."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    corpus_path = out_dir / f"mindx_dreams_gen{generation}.jsonl"

    # Materialize corpus (canonical: sorted-key JSON per line for stable bytes).
    n = 0
    with corpus_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(
                {"messages": row.messages, "meta": row.meta},
                ensure_ascii=False, sort_keys=True) + "\n")
            n += 1

    bundle_id = _canonical_bundle_id(corpus_path)

    # XTrainConfig — the 10-section schema mindXtrain documents in
    # docs/yaml_schema.md. Only the sections we drive are populated; the rest
    # fall back to mindXtrain template defaults.
    cfg = {
        "run": {
            "name": f"mindx-gen{generation}",
            "seed": 42,
            "output_dir": f"runs/mindx-gen{generation}",
        },
        "model": {
            "base": base_model,
            "template": template,
            "lora": {"r": 16, "alpha": 32, "dropout": 0.05},
        },
        "data": {
            "sources": [
                {"adapter": MINDX_DREAMS_SOURCE,
                 "path": corpus_path.name,
                 "bundle_id": bundle_id,
                 "format": "chat_jsonl"}
            ],
            "max_seq_len": 4096,
        },
        "autotune": {"aot_probe_seconds": 60, "attention": "auto",
                     "hipblaslt": "auto", "rccl": "auto"},
        "train": {"epochs": 1, "lr": 2.0e-4, "micro_batch": 1,
                  "grad_accum": 16, "scheduler": "cosine"},
        "eval": {"enabled": True, "holdout_fraction": 0.05},
        "budget": {"max_minutes": 120, "max_usd": 0},
        "deploy": {"serve": False, "openai_compatible": True},
        "provenance": {"erc8004_attest": True,
                       "parent_generation": generation - 1,
                       "bundle_id": bundle_id},
        "storage": {"anchor": "thot", "mirror": "ipfs"},
    }
    config_path = out_dir / f"mindx-gen{generation}.yaml"
    _emit_yaml(cfg, config_path)

    return ForgeResult(
        corpus_path=corpus_path,
        config_path=config_path,
        bundle_id=bundle_id,
        row_count=n,
        template=template,
        meta={"base_model": base_model, "generation": generation},
    )
