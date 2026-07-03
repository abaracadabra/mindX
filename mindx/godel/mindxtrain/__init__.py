"""mindx.godel.mindxtrain — the right tip of the Schmidhüber pendulum.

KNOWLEDGE -> WISDOM -> WEIGHTS.

This package is the bridge between mindX's `machine.dream` cycle and the
external fine-tuning framework:

    github.com/professor-codephreak/mindXtrain

mindXtrain is a production-grade LoRA fine-tuning framework for AMD MI300X
(ROCm 7.2.1) whose distinguishing feature is a 60-second ahead-of-time
autotune probe. Crucially, it already ships a `mindx_dreams` data-source
adapter designed to consume mindX dream-cycle JSONL. It is currently taken to
the "CPU training level": ~38 of its 99 modules run CPU-only (config, data
curation, autotune dry-run, provenance, deploy planning); the heavy training /
eval / quantize paths gate behind optional dependency groups (`--extra ml`,
`--extra eval`, `--extra data`) and require the MI300X.

The four stages of the tip (information is already knowledge by the time it
reaches us — machine.dream did that on the LEFT apex):

    distill  : gather machine.dream `*_training.jsonl` -> normalize into the
               `mindx_dreams` corpus mindXtrain expects.
    curate   : keep only utility-positive, alignment-clean, high-score rows
               (DreamInsight.score gate + the ataraxia BOTTOM alignment floor).
    forge    : build the deterministic dataset bundle + the XTrainConfig YAML
               (mindXtrain's 10-section schema) pointed at that corpus.
    ascend   : invoke the mindXtrain CLI (CPU dry-run, or MI300X train) to
               produce LoRA weights, then register the new model card so the
               NEXT generation of mindX serves the wiser mind.

Everything here degrades gracefully to a CPU dry-run when mindXtrain or the
MI300X is absent — matching the project's current CPU training level.
"""

from __future__ import annotations

import os

MINDXTRAIN_REPO = "https://github.com/professor-codephreak/mindXtrain"
MINDX_DREAMS_SOURCE = "mindx_dreams"   # the data-source adapter name in mindXtrain
DEFAULT_TEMPLATE = "qwen3_8b_sft_lora"  # mindXtrain quickstart LoRA template (GPU)

# v1.0.0 (2026-06-12) made CPU training active. On the 8GB/2-core VPS the
# right-apex ascent uses a small CPU-trainable base, bounded budget. The HF id
# is what mindXtrain trains; the Ollama tag is what mindX serves the result as.
# Smallest model we have — what CPU training trains by policy. mindXtrain's
# mindX CPU recipes already use it; the forge path matches.
CPU_SMALLEST_MODEL = "HuggingFaceTB/SmolLM2-135M"   # 135M — the smallest base
CPU_BASE_MODEL = CPU_SMALLEST_MODEL
CPU_BASE_OLLAMA_TAG = "qwen3:0.6b"     # FROM line for the promoted Modelfile

# ── CPU training regimen (operator policy 2026-06-13) ──────────────────────
# Slow-cook on the shared smartphone-class VPS: throttle to 33% of the
# processor (leaving ~67% for the live service) over a 24-hour wall window,
# which yields ≈8 hours of effective training compute (0.33 × 24 ≈ 8). The
# smallest model only, so the footprint stays tiny.
CPU_TRAIN_PERCENT = 33                  # processor throttle for any CPU ascent
CPU_TRAIN_WALL_HOURS = 24               # max wall-clock window
CPU_TRAIN_EFFECTIVE_HOURS = 8           # ≈ CPU_TRAIN_PERCENT/100 × wall hours
CPU_MAX_MINUTES = CPU_TRAIN_WALL_HOURS * 60   # bounded budget (24h)
# mindXtrain ships purpose-built mindX CPU recipes (`mindxtrain init --list`).
# The smoke recipe (SmolLM2-135M, ~1.2GB RSS, 10-30min) closes the full
# dream-corpus->SFT->checkpoint->imprint loop on a CPU box; _cpu_real is the
# qwen3-1.5B production run. Its mindx_dreams adapter reads data/memory directly.
CPU_RECIPE_SMOKE = "mindx_fallback_qwen3_1_5b_cpu_smoke"
CPU_RECIPE_REAL = "mindx_fallback_qwen3_1_5b_cpu_real"

# --------------------------------------------------------------------------- #
# Isolation contract (operator decision, 2026-06-04)                          #
#                                                                             #
# mindXtrain is an EXTERNAL, incomplete project (CPU training level; MI300X    #
# GPU paths gated). It is tested in ISOLATION in its own repo                  #
# (github.com/professor-codephreak/mindXtrain) until proven working. mindX     #
# carries only this thin bridge — NO mindXtrain framework code is vendored,    #
# and mindX core performs NO eager `import mindxtrain`. The bridge talks to it  #
# solely via subprocess + path discovery (see bridge.py).                      #
#                                                                             #
# The bridge is RECOGNIZED but DORMANT by default: discovery always runs, but  #
# any action that would actually drive training is gated behind an explicit    #
# opt-in env flag, so nothing activates inside mindX until mindXtrain is        #
# independently validated.                                                     #
# --------------------------------------------------------------------------- #

ENABLE_ENV = "MINDX_ENABLE_MINDXTRAIN"   # set to 1/true/yes to arm the bridge
# A SECOND, independent flag. Arming the bridge (above) enables operator/manual
# ascents. Autonomous, SEA-triggered training requires THIS flag as well — so
# that arming for a supervised operator ascent can never unleash spontaneous
# training. Both must be set for the autonomous loop to ever train.
AUTONOMOUS_TRAIN_ENV = "MINDX_ENABLE_AUTONOMOUS_TRAIN"
ASCEND_COOLDOWN_S = 24 * 3600            # min interval between autonomous ascents


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def is_enabled() -> bool:
    """True only when the operator has explicitly armed the mindXtrain bridge."""
    return _flag(ENABLE_ENV)


def autonomous_train_enabled() -> bool:
    """True only when BOTH the bridge is armed AND autonomous training is
    explicitly opted into — the two-flag guard for spontaneous ascents."""
    return is_enabled() and _flag(AUTONOMOUS_TRAIN_ENV)


__all__ = [
    "MINDXTRAIN_REPO",
    "MINDX_DREAMS_SOURCE",
    "DEFAULT_TEMPLATE",
    "CPU_BASE_MODEL",
    "CPU_BASE_OLLAMA_TAG",
    "CPU_MAX_MINUTES",
    "ENABLE_ENV",
    "AUTONOMOUS_TRAIN_ENV",
    "ASCEND_COOLDOWN_S",
    "is_enabled",
    "autonomous_train_enabled",
    "distill",
    "curate",
    "forge",
    "ascend",
    "ascend_recipe",
    "bridge",
    "imprint",
    "promote",
    "CPU_RECIPE_SMOKE",
    "CPU_RECIPE_REAL",
]
