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

    # 5b. imprint proof-of-recall verdict (v1.0.0): if asked and we trained, the
    #     objective gate is whether the model now recalls its training. This
    #     becomes the verdict when no explicit verdict callback was supplied.
    if did_train and use_dcoach and verdict is None:
        try:
            from .imprint import imprint_verdict_factory
            verdict = imprint_verdict_factory(cap, fr.config_path.parent, fr.config_path.name)
        except Exception as e:  # pragma: no cover - defensive
            notes.append(f"imprint verdict unavailable: {e}")

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


async def ascend_recipe(
    *,
    work_dir: Path,
    generation: int,
    data_memory_dir: Path,
    recipe: str,
    cpu_percent: int = 20,
    cpu_nice: int = 19,
    use_imprint: bool = True,
    promote: bool = False,
    register_fallback: bool = False,
) -> AscentResult:
    """The PROVEN v1.0.0 ascent flow, driving mindXtrain's own recipe CLI
    (validated on the VPS 2026-06-13):

        init -t <recipe> -o run.yaml         # known-good config
        (point data.path at this deploy's data/memory)
        train run.yaml --out out/runs --cpu-percent N --cpu-nice M
        imprint run.yaml --out out/runs --n 5   # proof-of-recall verdict
        [if imprinted] serve run.yaml -c <adapter> --to ollama --tag mindx-gen{N}

    Unlike forge-based ascend(), this consumes mindXtrain's `mindx_dreams`
    adapter, which reads the dream training files under data/memory directly —
    so no hand-forged config/corpus is needed. DORMANT unless the bridge is
    armed.
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []
    cap = _bridge.discover()
    result = AscentResult(stage="dormant", generation=generation,
                          capability=cap.as_dict(), notes=notes)
    if not is_enabled():
        notes.append("mindXtrain bridge dormant; set MINDX_ENABLE_MINDXTRAIN=1")
        return result
    if not cap.cpu_train_active:
        notes.append(f"mindXtrain not CPU-train-active (version {cap.version})")
        return result

    cfg = "run.yaml"
    # 1. init a known-good recipe config
    init = _bridge.run_cli(["init", "-t", recipe, "-o", cfg], cap=cap, cwd=work_dir, timeout=300)
    if not init.get("ok"):
        notes.append(f"init failed: {(init.get('stderr') or init.get('reason') or '')[:200]}")
        return result
    # 2. point the mindx_dreams adapter at THIS deploy's dream memory
    try:
        p = work_dir / cfg
        text = p.read_text(encoding="utf-8")
        text = _re_sub_data_path(text, str(data_memory_dir))
        p.write_text(text, encoding="utf-8")
    except Exception as e:
        notes.append(f"could not set data.path: {e}")
        return result

    # 3. train (positional config + built-in CPU throttle)
    train = _bridge.run_cli(
        ["train", cfg, "--out", "out/runs", "--cpu-percent", str(cpu_percent),
         "--cpu-nice", str(cpu_nice)],
        cap=cap, cwd=work_dir, timeout=CPU_MAX_MINUTES * 60 + 600,
    )
    result.train = {"ok": train.get("ok"), "tail": (train.get("stdout") or "")[-600:]}
    if not train.get("ok"):
        result.stage = "train_failed"
        notes.append(f"train failed: {(train.get('stderr') or '')[-300:]}")
        return result
    result.stage = "trained"
    # locate the adapter dir under out/runs/<run>/checkpoint
    adapter = _find_adapter(work_dir / "out" / "runs")
    result.weights_path = str(adapter) if adapter else str(work_dir / "out" / "runs")

    # 4. imprint proof-of-recall verdict
    if use_imprint:
        from .imprint import imprint_verdict_factory
        verdict = imprint_verdict_factory(cap, work_dir, cfg)
        v = await verdict(None)
        result.recall = {k: v.get(k) for k in ("recall_before", "recall_after", "delta", "imprinted")
                         if v.get(k) is not None}
        if not v.get("accepted"):
            result.stage = "proof_rejected"
            notes.append(f"imprint verdict: {v.get('reason')}")
            return result
        notes.append(f"imprint accepted: {v.get('reason')}")
        result.stage = "accepted"

    # 5. promote: serve --to ollama
    if promote and result.weights_path:
        from .promote import promote_to_ollama
        pr = await promote_to_ollama(cap, None, result.weights_path, generation,
                                     config_name=cfg, work_dir=str(work_dir),
                                     register_fallback=register_fallback)
        if pr.get("ok"):
            result.promoted = True
            result.stage = "promoted"
            result.ollama_model = pr.get("model_name")
            notes.append(f"promoted to Ollama model {result.ollama_model}")
        else:
            notes.append(f"promotion failed: {pr.get('reason') or pr.get('stderr','')[:200]}")
    return result


def _re_sub_data_path(text: str, new_path: str) -> str:
    import re
    # replace `path: <anything>` under the data: block (recipe default is the
    # dev box path); also handle when it's already correct (no-op).
    return re.sub(r"(?m)^(\s*path:\s*).*/data/memory\s*$", rf"\1{new_path}", text)


def _find_adapter(runs_dir: Path):
    runs_dir = Path(runs_dir)
    for p in runs_dir.rglob("adapter_config.json"):
        return p.parent
    return None


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
