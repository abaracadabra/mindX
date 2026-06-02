"""Bridge selector slug → concrete LLMHandler / Ollama model name.

The selector returns slugs like:
- `openai/gpt-oss-120b:free`         (OpenRouter)
- `qwen3:1.7b`                       (Ollama local)
- `gpt-oss:120b-cloud`               (Ollama cloud)
- `nvidia/nemotron-3-super-120b-a12b:free`  (OpenRouter)

This module classifies a slug and returns either:
- a tuple `(provider, model)` consumable by `llm.llm_factory.create_llm_handler`, or
- a simple Ollama model-name string for callers like `mindXagent._resolve_inference_model`.

OpenRouter is now routable via `llm.openrouter_handler.OpenRouterHandler` —
`slug_is_routable` returns True for both ollama and openrouter classes.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple


def classify_slug(slug: str) -> str:
    """Return one of: 'openrouter', 'ollama_cloud', 'ollama_local', 'unknown'."""
    if not slug:
        return "unknown"
    if "/" in slug:
        # author/model:tag — OpenRouter shape
        return "openrouter"
    if slug.endswith(":cloud") or slug.endswith("-cloud"):
        return "ollama_cloud"
    return "ollama_local"


def slug_to_provider_model(slug: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (provider, model) suitable for `create_llm_handler`. (None, None)
    if the slug class is unknown.
    """
    cls = classify_slug(slug)
    if cls == "ollama_local" or cls == "ollama_cloud":
        return ("ollama", slug)
    if cls == "openrouter":
        return ("openrouter", slug)
    return (None, None)


def slug_is_ollama_resolvable(slug: str) -> bool:
    """True iff the slug routes to an Ollama daemon (local or cloud-proxied).

    Kept for backward compatibility with `mindXagent._resolve_inference_model`,
    which returns a plain model-name string assumed to be Ollama-shaped.
    """
    return classify_slug(slug) in ("ollama_local", "ollama_cloud")


def slug_is_openrouter_resolvable(slug: str) -> bool:
    """True iff the slug routes to OpenRouter AND a key is present in env.

    The vault-injected OPENROUTER_API_KEY is what makes OpenRouter routable in
    practice; without it, the handler returns None and we should fall through.
    """
    if classify_slug(slug) != "openrouter":
        return False
    return bool(os.getenv("OPENROUTER_API_KEY"))


def slug_is_routable(slug: str) -> bool:
    """True iff the slug can be routed to ANY working handler today."""
    return slug_is_ollama_resolvable(slug) or slug_is_openrouter_resolvable(slug)


def slug_budget_headroom(slug: str) -> float:
    """0..1 rate-limit budget remaining for this slug's provider tier.

    classify_slug already maps a slug to its tier (openrouter / ollama_cloud /
    ollama_local); local is unlimited (->1.0). Fail-open: 1.0 on any error so the
    budget can deprioritise but never block a slug. Used by the self-aware
    selector to route inference toward tiers that still have headroom.
    """
    try:
        from llm.inference_budget import headroom as _h
        cls = classify_slug(slug)
        if cls == "openrouter":
            return _h("openrouter")
        if cls == "ollama_cloud":
            return _h("ollama_cloud")
        return 1.0  # ollama_local / unknown -- unlimited
    except Exception:
        return 1.0
