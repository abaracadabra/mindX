# llm/ollama_bootstrap: Install and configure Ollama when no inference connection is found.
# See README.md and RESILIENCE.md for the "no connection → install Ollama → continue" scenario.

from .bootstrap import (
    ensure_ollama_available,
    run_ollama_bootstrap_linux,
    NO_INFERENCE_CONNECTION,
)

__all__ = [
    "ensure_ollama_available",
    "run_ollama_bootstrap_linux",
    "NO_INFERENCE_CONNECTION",
]
