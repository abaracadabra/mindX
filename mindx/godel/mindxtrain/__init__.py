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
DEFAULT_TEMPLATE = "qwen3_8b_sft_lora"  # mindXtrain quickstart LoRA template

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


def is_enabled() -> bool:
    """True only when the operator has explicitly armed the mindXtrain bridge."""
    return os.environ.get(ENABLE_ENV, "").strip().lower() in ("1", "true", "yes", "on")


__all__ = [
    "MINDXTRAIN_REPO",
    "MINDX_DREAMS_SOURCE",
    "DEFAULT_TEMPLATE",
    "ENABLE_ENV",
    "is_enabled",
    "distill",
    "curate",
    "forge",
    "ascend",
    "bridge",
]
