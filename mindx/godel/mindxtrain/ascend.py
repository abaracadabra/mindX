"""ascend — knowledge becomes wisdom becomes weights becomes the next mind.

This is the orchestration of the RIGHT apex of the Schmidhüber pendulum. It
chains the stages and drives the external mindXtrain CLI:

    distill  -> curate -> forge -> [bench --dry-run] -> [train] -> register

On a CPU-only host (mindXtrain's current level) ascend() runs through
distill/curate/forge and then `mindxtrain bench --dry-run`, producing a
training PLAN and a forged config without consuming a GPU. On an MI300X host
it additionally runs `mindxtrain train` to emit LoRA weights and, if asked,
registers the resulting model card so the next generation of mindX serves the
wiser mind.

The ascent is PROOF-GATED by design: the new weights are not promoted to the
live model registry unless a verdict callback (the Gödel kernel, or in shadow
mode the alignment-eval gate) accepts the generation. Absent a kernel, ascend
stops at "forged"/"trained" and promotes nothing — shadow mode.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Optional

from . import DEFAULT_TEMPLATE, is_enabled
from . import bridge as _bridge
from .curate import CurationStats, curate
from .distill import distill, write_corpus  # noqa: F401  (write_corpus re-exported)
from .forge import ForgeResult, forge


@dataclass
class AscentResult:
    stage: str                      # forged | benched | trained | promoted | shadow
    generation: int
    forge_result: Optional[ForgeResult] = None
    curation: dict = field(default_factory=dict)
    capability: dict = field(default_factory=dict)
    bench: dict = field(default_factory=dict)
    train: dict = field(default_factory=dict)
    promoted: bool = False
    weights_path: Optional[str] = None
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "stage": self.stage,
            "generation": self.generation,
            "promoted": self.promoted,
            "weights_path": self.weights_path,
            "forge": self.forge_result.as_dict() if self.forge_result else None,
            "curation": self.curation,
            "capability": self.capability,
            "bench": self.bench,
            "train": self.train,
            "notes": self.notes,
        }


# A verdict callback receives the forge provenance and returns an accept/reject.
Verdict = Callable[[ForgeResult], Awaitable[dict]]


async def ascend(
    *,
    dreams_dir: Path,
    work_dir: Path,
    generation: int,
    since_ts: Optional[float] = None,
    base_model: str = "Qwen/Qwen3-8B",
    template: str = DEFAULT_TEMPLATE,
    min_score: float = 0.05,
    verdict: Optional[Verdict] = None,
    train_if_gpu: bool = True,
) -> AscentResult:
    """Run the full knowledge->wisdom->weights ascent for one generation.

    DORMANT BY DEFAULT: until the operator sets MINDX_ENABLE_MINDXTRAIN=1
    (after mindXtrain is validated in isolation), this returns a recognized-
    but-disabled result without touching dreams or driving any training. This
    is the isolation contract — mindX recognizes mindXtrain but does not act
    through it until armed.
    """
    notes: list[str] = []
    cap = _bridge.discover()
    notes.append(f"mindXtrain level: {cap.level}; enabled: {cap.enabled}")
    if not is_enabled():
        return AscentResult(
            stage="dormant", generation=generation,
            capability=cap.as_dict(),
            notes=notes + ["mindXtrain bridge dormant; set MINDX_ENABLE_MINDXTRAIN=1 "
                           "to arm after isolated validation"],
        )

    # 1. distill + 2. curate (streamed)
    stats = CurationStats()
    rows = curate(distill(dreams_dir, since_ts=since_ts),
                  min_score=min_score, stats=stats)

    # 3. forge corpus + config (materializes the curated stream)
    fr = forge(rows, out_dir=work_dir, generation=generation,
               base_model=base_model, template=template)
    result = AscentResult(
        stage="forged", generation=generation, forge_result=fr,
        curation=stats.as_dict(), capability=cap.as_dict(), notes=notes,
    )
    if fr.row_count == 0:
        notes.append("no curated rows — nothing to train this generation")
        return result

    # 4. bench --dry-run (CPU-safe AOT plan; validates config + autotune)
    bench = _bridge.run_cli(
        ["bench", "--dry-run", "--config", fr.config_path.name],
        cap=cap, cwd=fr.config_path.parent,
    )
    result.bench = bench
    result.stage = "benched"

    # 5. train (GPU only). On CPU we stop at the plan — the project's level.
    if cap.level == "gpu" and train_if_gpu:
        train = _bridge.run_cli(
            ["train", "--config", fr.config_path.name],
            cap=cap, cwd=fr.config_path.parent, timeout=3600,
        )
        result.train = train
        if train.get("ok"):
            result.stage = "trained"
            result.weights_path = str(
                fr.config_path.parent / f"runs/mindx-gen{generation}"
            )
    else:
        notes.append("CPU level: forged plan only; train gated on MI300X")

    # 6. proof-gated promotion. No verdict callback => shadow mode, promote
    #    nothing (matches the kernel-absent posture of the engine).
    if verdict is not None:
        v = await verdict(fr)
        if v.get("accepted"):
            result.promoted = True
            result.stage = "promoted"
            notes.append(f"generation {generation} accepted: {v.get('reason','')}")
        else:
            notes.append(f"generation {generation} rejected: {v.get('reason','')}")
    else:
        result.stage = result.stage if result.stage == "trained" else "shadow"
        notes.append("no verdict callback — shadow mode, no promotion")

    return result


def watermark_path(work_dir: Path) -> Path:
    return Path(work_dir) / ".ascend_watermark"


def read_watermark(work_dir: Path) -> Optional[float]:
    p = watermark_path(work_dir)
    try:
        return float(p.read_text().strip())
    except Exception:
        return None


def write_watermark(work_dir: Path, ts: Optional[float] = None) -> None:
    p = watermark_path(work_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(str(ts if ts is not None else time.time()))
