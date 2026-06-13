# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved.
#
# inference_discovery_llmfit_hook.py — wiring snippet, not a standalone module.
#
# Where InferenceDiscovery currently scores only providers that are already
# *running* (reliability × speed × recency), this adds a fourth, prospective
# factor: would a model even fit this node? A provider advertising a model the
# node cannot serve should never win routing. llmfit supplies that gate.
#
# Drop the body of augment_with_fit() into the composite-scoring path of
# llm/inference_discovery.py (after the existing reliability/speed/recency
# multiply, before final ranking).

from tools.inference.llmfit_tool import fit_profile


async def get_node_runnable_set(use_case: str = "general") -> set[str]:
    """Lowercased model names this node can serve at >= marginal fit."""
    prof = await fit_profile(use_case=use_case, limit=24)
    if not prof.get("ok"):
        return set()  # fail-open: no profile => no gating, preserve current behaviour
    return {m["name"].lower() for m in prof["runnable"] if m.get("name")}


def augment_with_fit(provider_score: float, model_name: str,
                     runnable: set[str]) -> float:
    """
    Multiply an existing composite provider score by a fit factor.

    runnable empty            -> 1.0  (oracle unavailable; do not penalise)
    model in runnable         -> 1.0  (no change; node can serve it)
    model not in runnable     -> 0.15 (heavy deprioritise; still selectable as
                                       a last resort if nothing else exists)
    """
    if not runnable:
        return provider_score
    return provider_score if model_name.lower() in runnable else provider_score * 0.15
