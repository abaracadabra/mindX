# agents/orchestration/inference_agent.py
"""
InferenceAgent: Central handler for inference requests from agents.

Coordinator and any agent that needs inference can access inference through this agent.
There is never enough inference; the InferenceAgent tracks each provider and works with
settings to maintain solvency and maximum inference consumption over time in accordance
with budget as a guideline.
"""

from __future__ import annotations

import asyncio
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from utils.config import Config
from utils.logging_config import get_logger
from agents.memory_agent import MemoryAgent

logger = get_logger(__name__)


@dataclass
class ProviderUsage:
    """Per-provider usage and limits."""
    provider: str
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    last_used: float = 0.0
    errors: int = 0


@dataclass
class InferenceRequest:
    """Request for inference from an agent."""
    agent_id: str
    task_type: str
    prompt: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    provider_preference: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InferenceResult:
    """Result of an inference request."""
    success: bool
    response: Optional[str] = None
    provider_used: Optional[str] = None
    model_used: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    error: Optional[str] = None


class InferenceAgent:
    """
    Handles all requests for inference from agents. Tracks each provider and works
    with settings to maintain solvency and maximum inference consumption over time
    in accordance with budget as a guideline.
    """

    _instance: Optional["InferenceAgent"] = None
    _lock = asyncio.Lock()

    def __init__(
        self,
        config: Optional[Config] = None,
        memory_agent: Optional[MemoryAgent] = None,
    ):
        self.config = config or Config()
        self.memory_agent = memory_agent or MemoryAgent(config=self.config)
        self.agent_id = "inference_agent"
        self.log_prefix = f"InferenceAgent ({self.agent_id}):"

        # Per-provider usage (solvency and consumption tracking)
        self._usage: Dict[str, ProviderUsage] = {}
        self._total_requests = 0
        self._lock_local = asyncio.Lock()

        # Budget guideline (tokens or cost - configurable)
        self._budget_tokens = self.config.get("inference.budget_tokens")  # optional cap
        self._budget_requests_per_hour = self.config.get("inference.budget_requests_per_hour")
        self._consumed_tokens = 0
        self._window_start = time.time()

        logger.info(f"{self.log_prefix} Initialized; budget_tokens={self._budget_tokens}, budget_rph={self._budget_requests_per_hour}")

    @classmethod
    async def get_instance(
        cls,
        config: Optional[Config] = None,
        memory_agent: Optional[MemoryAgent] = None,
    ) -> "InferenceAgent":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config=config, memory_agent=memory_agent)
            return cls._instance

    def _get_usage(self, provider: str) -> ProviderUsage:
        if provider not in self._usage:
            self._usage[provider] = ProviderUsage(provider=provider)
        return self._usage[provider]

    def _record_use(self, provider: str, input_tokens: int = 0, output_tokens: int = 0, error: bool = False):
        u = self._get_usage(provider)
        u.requests += 1
        u.input_tokens += input_tokens
        u.output_tokens += output_tokens
        u.last_used = time.time()
        if error:
            u.errors += 1
        self._total_requests += 1
        self._consumed_tokens += input_tokens + output_tokens

    async def request_inference(self, request: InferenceRequest) -> InferenceResult:
        """
        Handle an inference request from an agent. Delegates to the model registry
        (or LLM factory) and records usage for solvency and budget tracking.
        """
        async with self._lock_local:
            # Optional: enforce budget guideline (e.g. refuse or throttle)
            if self._budget_tokens is not None and self._consumed_tokens >= self._budget_tokens:
                logger.warning(f"{self.log_prefix} Budget token limit reached ({self._consumed_tokens} >= {self._budget_tokens})")
                return InferenceResult(success=False, error="Budget token limit reached")
            if self._budget_requests_per_hour is not None:
                elapsed_h = (time.time() - self._window_start) / 3600.0
                if elapsed_h >= 1.0:
                    self._window_start = time.time()
                    self._total_requests = 0
                if self._total_requests >= self._budget_requests_per_hour:
                    return InferenceResult(success=False, error="Budget requests per hour reached")

        try:
            from llm.model_registry import get_model_registry_async
            registry = await get_model_registry_async()
            task_type_str = request.task_type if isinstance(request.task_type, str) else "simple_chat"
            from llm.model_selector import TaskType
            task_map = {
                "reasoning": TaskType.REASONING,
                "code": TaskType.CODE_GENERATION,
                "code_generation": TaskType.CODE_GENERATION,
                "simple_chat": TaskType.SIMPLE_CHAT,
                "chat": TaskType.SIMPLE_CHAT,
            }
            task_enum = task_map.get(task_type_str.lower(), TaskType.SIMPLE_CHAT)

            response = await registry.generate_with_fallback(
                prompt=request.prompt,
                task_type=task_enum,
                max_tokens=request.max_tokens or 2048,
                temperature=request.temperature,
                try_bootstrap_on_no_connection=False,
            )
            if response is None or (isinstance(response, str) and response.startswith("Error:")):
                self._record_use(provider="unknown", error=True)
                return InferenceResult(
                    success=False,
                    error=response if isinstance(response, str) else "No response",
                )
            text = str(response)
            # Registry returns str; we do not get provider/tokens from it here
            provider_used = request.provider_preference or "registry"
            self._record_use(provider_used, 0, 0, error=False)
            return InferenceResult(
                success=True,
                response=text,
                provider_used=provider_used,
                model_used=None,
                input_tokens=0,
                output_tokens=0,
            )
        except Exception as e:
            logger.warning(f"{self.log_prefix} Inference request failed: {e}")
            self._record_use(provider="unknown", error=True)
            return InferenceResult(success=False, error=str(e))

    def get_providers(self) -> List[str]:
        """Return list of providers currently tracked (from usage)."""
        return list(self._usage.keys())

    def get_usage(self) -> Dict[str, Dict[str, Any]]:
        """Return per-provider usage for settings and solvency."""
        return {
            p: {
                "provider": u.provider,
                "requests": u.requests,
                "input_tokens": u.input_tokens,
                "output_tokens": u.output_tokens,
                "last_used": u.last_used,
                "errors": u.errors,
            }
            for p, u in self._usage.items()
        }

    def get_status(self) -> Dict[str, Any]:
        """Status for UI: providers, usage, budget guideline, solvency."""
        usage = self.get_usage()
        total_tokens = sum(u["input_tokens"] + u["output_tokens"] for u in usage.values())
        remaining_tokens = None
        if self._budget_tokens is not None:
            remaining_tokens = max(0, self._budget_tokens - self._consumed_tokens)
        return {
            "agent_id": self.agent_id,
            "providers": list(usage.keys()),
            "usage_by_provider": usage,
            "total_requests": self._total_requests,
            "total_tokens_consumed": self._consumed_tokens,
            "budget_tokens": self._budget_tokens,
            "budget_remaining_tokens": remaining_tokens,
            "budget_requests_per_hour": self._budget_requests_per_hour,
            "solvency": remaining_tokens is None or remaining_tokens > 0,
        }
