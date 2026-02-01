# This file makes the 'llm' directory a Python package.
# Resilience: Ollama is the failsafe/fallback (see RESILIENCE.md). Use ModelRegistry.generate_with_fallback for graded inference.

from .model_selector import TaskType
from .model_registry import ModelRegistry, get_model_registry_async
from .llm_factory import create_llm_handler
from .llm_interface import LLMHandlerInterface

try:
    from .ollama_handler import OllamaHandler
except ImportError:
    OllamaHandler = None  # type: ignore

__all__ = [
    "TaskType",
    "ModelRegistry",
    "get_model_registry_async",
    "create_llm_handler",
    "OllamaHandler",
    "LLMHandlerInterface",
]
