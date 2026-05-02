# Portions adapted from confident-ai/deepeval (Apache-2.0). See NOTICE.
"""
MindXJudgeLLM — adapter from deepeval's DeepEvalBaseLLM contract to
mindX's llm/llm_factory.create_llm_handler().

Default judge: CPU pillar (Ollama at localhost:11434, model qwen3:1.7b),
free, ~8 tok/s. High-stakes consumers (boardroom, future Phase 2) can
override provider + model.

Log-probability reweighting (the GEval differentiator) requires the
OpenAI-style top_logprobs response shape. Ollama does not expose this
today; the `generate_with_logprobs` method is a stub that returns
(text, None). When mindX swaps the judge for a cloud provider that
returns top_logprobs, GEval will pick up the calibrated score.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class MindXJudgeLLM:
    """Async judge LLM wrapper for mindX evaluation metrics."""

    def __init__(
        self,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> None:
        self.provider_name = (
            provider_name
            or os.environ.get("MINDX_EVAL_JUDGE_PROVIDER")
            or "ollama"
        )
        self.model_name = (
            model_name
            or os.environ.get("MINDX_EVAL_JUDGE_MODEL")
            or "qwen3:1.7b"
        )
        self.base_url = base_url or os.environ.get("MINDX_EVAL_JUDGE_BASE_URL")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._handler = None

    def get_model_name(self) -> str:
        return f"{self.provider_name}/{self.model_name}"

    async def _ensure_handler(self):
        if self._handler is not None:
            return self._handler
        from llm.llm_factory import create_llm_handler
        kwargs = {
            "provider_name": self.provider_name,
            "model_name": self.model_name,
        }
        if self.base_url:
            kwargs["base_url"] = self.base_url
        self._handler = await create_llm_handler(**kwargs)
        return self._handler

    async def a_generate(self, prompt: str, json_mode: bool = True) -> str:
        """Generate a response for a single prompt. Returns plain text."""
        handler = await self._ensure_handler()
        response = await handler.generate_text(
            prompt=prompt,
            model=self.model_name,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            json_mode=json_mode,
        )
        if response is None:
            raise RuntimeError(
                f"MindXJudgeLLM ({self.get_model_name()}) returned None"
            )
        if isinstance(response, str) and response.startswith("Error:"):
            raise RuntimeError(
                f"MindXJudgeLLM ({self.get_model_name()}) error: {response}"
            )
        return response

    async def a_generate_with_logprobs(
        self, prompt: str, top_logprobs: int = 20
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Future hook for log-probability reweighting (GEval calibrated score).

        Today the CPU-pillar Ollama judge does not surface OpenAI-shape
        top_logprobs through mindX's LLMHandlerInterface, so this returns
        (text, None) and GEval falls back to the unweighted integer score.
        Wire a real provider-specific path here when calibrated scoring
        becomes economically warranted (cloud judge in Phase 2+).
        """
        text = await self.a_generate(prompt, json_mode=True)
        return text, None
