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

from . import (DEFAULT_TEMPLATE, CPU_BASE_MODEL, CPU_MAX_MINUTES, is_enabled)
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
    ollama_model: Optional[str] = None
    recall: dict = field(default_factory=dict)   # dcoach proof-of-recall result
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "stage": self.stage,
            "generation": self.generation,
            "promoted": self.promoted,
            "weights_path": self.weights_path,
            "ollama_model": self.ollama_model,
            "recall": self.recall,
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
    cpu_train: bool = False,
    max_minutes: Optional[int] = None,
    use_dcoach: bool = False,
    promote: bool = False,
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
    budget_minutes = max_minutes if max_minutes is not None else (
        CPU_MAX_MINUTES if cpu_train else 120)
    fr = forge(rows, out_dir=work_dir, generation=generation,
               base_model=base_model, template=template,
               max_minutes=budget_minutes,
               max_seq_len=1024 if cpu_train else 4096)
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

    # 5. train. GPU path unchanged; CPU path is live as of mindXtrain v1.0.0
    #    (was previously gated on the MI300X). Either way the budget lives in
    #    the forged YAML; we only append a budget flag if the verb exposes one.
    did_train = False
    if cap.level == "gpu" and train_if_gpu:
        train = _bridge.run_cli(
            ["train", "--config", fr.config_path.name],
            cap=cap, cwd=fr.config_path.parent, timeout=3600,
        )
        result.train = train
        did_train = bool(train.get("ok"))
    elif cap.cpu_train_active and cpu_train:
        train_args = ["train", "--config", fr.config_path.name]
        flags = _bridge.discover_verb_flags("train", cap)
        if "--max-minutes" in flags:
            train_args += ["--max-minutes", str(budget_minutes)]
        train = _bridge.run_cli(
            train_args, cap=cap, cwd=fr.config_path.parent,
            timeout=budget_minutes * 60 + 300,
        )
        result.train = train
        did_train = bool(train.get("ok"))
        notes.append(f"CPU train (v1.0.0): {'ok' if did_train else 'failed'}")
    else:
        notes.append("forged plan only; arm cpu_train (v1.0.0) or run on MI300X")

    if did_train:
        result.stage = "trained"
        result.weights_path = str(fr.config_path.parent / f"runs/mindx-gen{generation}")

    # 5b. dcoach proof-of-recall verdict (v1.0.0): if asked and we trained, the
    #     objective gate is whether the model now recalls its training. This
    #     becomes the verdict when no explicit verdict callback was supplied.
    if did_train and use_dcoach and verdict is None:
        try:
            from .dcoach import dcoach_verdict_factory
            verdict = dcoach_verdict_factory(cap, fr.config_path.parent)
        except Exception as e:  # pragma: no cover - defensive
            notes.append(f"dcoach verdict unavailable: {e}")

    # 6. proof-gated promotion. No verdict callback => shadow mode, promote
    #    nothing (matches the kernel-absent posture of the engine).
    if verdict is not None:
        v = await verdict(fr)
        result.recall = {k: v.get(k) for k in ("recall_before", "recall_after", "delta")
                         if v.get(k) is not None}
        if v.get("accepted"):
            result.stage = "accepted"
            notes.append(f"generation {generation} accepted: {v.get('reason','')}")
            # 7. LoRA -> Modelfile -> Ollama: the next generation becomes a
            #    servable mindX model. Only after the proof gate accepts.
            if promote and result.weights_path:
                try:
                    from .promote import promote_to_ollama
                    pr = await promote_to_ollama(cap, fr, result.weights_path, generation)
                    if pr.get("ok"):
                        result.promoted = True
                        result.stage = "promoted"
                        result.ollama_model = pr.get("model_name")
                        notes.append(f"promoted to Ollama model {result.ollama_model}")
                    else:
                        notes.append(f"promotion failed: {pr.get('reason') or pr.get('stderr','')[:200]}")
                except Exception as e:  # pragma: no cover - defensive
                    notes.append(f"promotion error: {e}")
            else:
                notes.append("accepted (shadow): no promotion requested or no weights")
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
