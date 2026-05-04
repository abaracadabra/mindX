"""Bridge selector slug → concrete LLMHandler / Ollama model name.

The selector returns slugs like:
- `openai/gpt-oss-120b:free`         (OpenRouter)
- `qwen3:1.7b`                       (Ollama local)
- `gpt-oss:120b-cloud`               (Ollama cloud)
- `nvidia/nemotron-3-super-120b-a12b:free`  (OpenRouter)

This module classifies a slug and returns either:
- a tuple `(provider, model)` consumable by `llm.llm_factory.create_llm_handler`, or
- a simple Ollama model-name string for callers like `mindXagent._resolve_inference_model`.

Phase 1: handles Ollama (local + cloud) and stubs OpenRouter (returns
provider="openrouter" but the handler factory may not yet implement it; caller
falls through). Phase 2 of OPENROUTER backlog adds the real handler.
"""

from __future__ import annotations

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
    if the slug class is not yet routable in the current build.
    """
    cls = classify_slug(slug)
    if cls == "ollama_local" or cls == "ollama_cloud":
        return ("ollama", slug)
    if cls == "openrouter":
        return ("openrouter", slug)  # handler may not exist yet; caller falls through
    return (None, None)


def slug_is_ollama_resolvable(slug: str) -> bool:
    """True iff the slug can be routed to an Ollama daemon today.

    Used by `mindXagent._resolve_inference_model` to decide whether to honor
    the selector's pick or fall through to the deterministic chain.
    """
    return classify_slug(slug) in ("ollama_local", "ollama_cloud")
