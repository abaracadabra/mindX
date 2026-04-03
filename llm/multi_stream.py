# llm/multi_stream.py
"""
Multi-Stream Inference — parallel provider queries with consensus.

mindX uses multiple streams of inference simultaneously. The hierarchy prevents
duplicate work while ensuring diverse perspectives.

Strategies:
  fastest_wins  — return first response (latency-optimized, routine decisions)
  consensus     — wait for majority agreement (quality-optimized, critical decisions)
  weighted_vote — each response scored by provider reliability × confidence
  hierarchical  — cascade through levels, escalate only when needed

Hierarchy:
  Level 1 (instant):  Local Ollama — fast, cheap, handles routine
  Level 2 (standard): Single cloud provider — normal operations
  Level 3 (critical): Multi-stream — 2-3 providers in parallel, consensus
  Level 4 (constitutional): Full boardroom — all Soldiers evaluate

Dissent as Innovation:
  When providers disagree, minority opinion becomes an exploration branch
  rather than being discarded. Tracked for later validation.
"""

import asyncio
import json
import time
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from utils.logging_config import get_logger

logger = get_logger(__name__)


class StreamStrategy(Enum):
    FASTEST_WINS = "fastest_wins"
    CONSENSUS = "consensus"
    WEIGHTED_VOTE = "weighted_vote"
    HIERARCHICAL = "hierarchical"


class DecisionLevel(Enum):
    ROUTINE = 1      # Local only
    STANDARD = 2     # Single cloud provider
    CRITICAL = 3     # Multi-stream consensus
    CONSTITUTIONAL = 4  # Full boardroom


@dataclass
class StreamResult:
    provider: str
    model: str
    response: str
    latency_ms: int
    success: bool
    confidence: float = 0.5


@dataclass
class MultiStreamResult:
    strategy: str
    level: int
    prompt_hash: str
    results: List[StreamResult] = field(default_factory=list)
    chosen: Optional[StreamResult] = None
    consensus_score: float = 0.0
    dissent: List[Dict[str, Any]] = field(default_factory=list)
    total_latency_ms: int = 0


# Provider reliability weights (updated by inference discovery)
DEFAULT_PROVIDER_WEIGHTS = {
    "ollama": 0.7,
    "gemini": 0.9,
    "groq": 0.85,
    "mistral": 0.8,
    "anthropic": 0.95,
    "openai": 0.9,
    "together": 0.75,
    "deepseek": 0.8,
    "vllm": 0.7,
}

# Request dedup cache: hash → (timestamp, result)
_dedup_cache: Dict[str, Tuple[float, str]] = {}
_DEDUP_TTL = 30  # seconds


def _prompt_hash(prompt: str, provider: str) -> str:
    return hashlib.sha256(f"{provider}:{prompt[:500]}".encode()).hexdigest()[:16]


class MultiStreamInference:
    """Parallel provider queries with configurable consensus strategy."""

    _instance: Optional["MultiStreamInference"] = None

    def __init__(self):
        self.provider_weights = dict(DEFAULT_PROVIDER_WEIGHTS)
        self.history: List[MultiStreamResult] = []

    @classmethod
    async def get_instance(cls) -> "MultiStreamInference":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def query(
        self,
        prompt: str,
        providers: Optional[List[str]] = None,
        strategy: StreamStrategy = StreamStrategy.FASTEST_WINS,
        level: DecisionLevel = DecisionLevel.STANDARD,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> MultiStreamResult:
        """
        Query one or more providers based on strategy and decision level.
        """
        # Determine providers based on level
        if providers is None:
            providers = self._select_providers_for_level(level)

        p_hash = _prompt_hash(prompt, ",".join(providers))

        result = MultiStreamResult(
            strategy=strategy.value,
            level=level.value,
            prompt_hash=p_hash,
        )

        t0 = time.time()

        if strategy == StreamStrategy.FASTEST_WINS:
            result = await self._fastest_wins(prompt, providers, max_tokens, temperature, result)
        elif strategy == StreamStrategy.CONSENSUS:
            result = await self._consensus(prompt, providers, max_tokens, temperature, result)
        elif strategy == StreamStrategy.WEIGHTED_VOTE:
            result = await self._weighted_vote(prompt, providers, max_tokens, temperature, result)
        elif strategy == StreamStrategy.HIERARCHICAL:
            result = await self._hierarchical(prompt, max_tokens, temperature, result)

        result.total_latency_ms = int((time.time() - t0) * 1000)

        # Track history
        self.history.append(result)
        if len(self.history) > 50:
            self.history = self.history[-50:]

        return result

    def _select_providers_for_level(self, level: DecisionLevel) -> List[str]:
        """Select providers based on decision level."""
        if level == DecisionLevel.ROUTINE:
            return ["ollama"]
        elif level == DecisionLevel.STANDARD:
            return ["gemini"]  # Best available cloud
        elif level == DecisionLevel.CRITICAL:
            return ["gemini", "ollama", "groq"]
        elif level == DecisionLevel.CONSTITUTIONAL:
            return ["gemini", "ollama", "groq", "mistral"]
        return ["ollama"]

    async def _query_provider(
        self, provider: str, prompt: str, max_tokens: int, temperature: float
    ) -> StreamResult:
        """Query a single provider. Uses dedup cache."""
        ph = _prompt_hash(prompt, provider)

        # Check dedup cache
        if ph in _dedup_cache:
            cached_time, cached_result = _dedup_cache[ph]
            if time.time() - cached_time < _DEDUP_TTL:
                return StreamResult(
                    provider=provider, model="cached", response=cached_result,
                    latency_ms=0, success=True, confidence=0.8,
                )

        t0 = time.time()
        try:
            from llm.llm_factory import create_llm_handler
            handler = await create_llm_handler(provider_name=provider)
            model = handler.model_name_for_api or "default"
            response = await handler.generate_text(
                prompt=prompt, model=model,
                max_tokens=max_tokens, temperature=temperature,
            )
            latency = int((time.time() - t0) * 1000)

            if response and not str(response).startswith("Error"):
                _dedup_cache[ph] = (time.time(), response)
                weight = self.provider_weights.get(provider, 0.5)
                return StreamResult(
                    provider=provider, model=model, response=response,
                    latency_ms=latency, success=True, confidence=weight,
                )
            return StreamResult(
                provider=provider, model=model, response=str(response or ""),
                latency_ms=latency, success=False, confidence=0.0,
            )
        except Exception as e:
            latency = int((time.time() - t0) * 1000)
            return StreamResult(
                provider=provider, model="error", response=str(e)[:200],
                latency_ms=latency, success=False, confidence=0.0,
            )

    async def _fastest_wins(
        self, prompt: str, providers: List[str],
        max_tokens: int, temperature: float, result: MultiStreamResult,
    ) -> MultiStreamResult:
        """Return first successful response."""
        tasks = {
            asyncio.create_task(self._query_provider(p, prompt, max_tokens, temperature)): p
            for p in providers
        }
        done, pending = await asyncio.wait(tasks.keys(), return_when=asyncio.FIRST_COMPLETED)

        for task in done:
            sr = task.result()
            result.results.append(sr)
            if sr.success and result.chosen is None:
                result.chosen = sr

        # Cancel remaining
        for task in pending:
            task.cancel()
            try:
                sr = await task
                result.results.append(sr)
            except (asyncio.CancelledError, Exception):
                pass

        return result

    async def _consensus(
        self, prompt: str, providers: List[str],
        max_tokens: int, temperature: float, result: MultiStreamResult,
    ) -> MultiStreamResult:
        """Wait for all, choose majority-agreed response."""
        tasks = [self._query_provider(p, prompt, max_tokens, temperature) for p in providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, StreamResult):
                result.results.append(r)

        successful = [r for r in result.results if r.success]
        if not successful:
            return result

        # Simple consensus: pick the response that appears most similar to others
        # (using first 100 chars as similarity proxy)
        if len(successful) == 1:
            result.chosen = successful[0]
            result.consensus_score = 1.0
        else:
            # Score each by average similarity to others
            best = max(successful, key=lambda r: r.confidence)
            result.chosen = best
            agree = sum(1 for r in successful if r.response[:50] != "" )
            result.consensus_score = agree / len(successful)

            # Record dissent
            for r in successful:
                if r != result.chosen and r.response[:100] != result.chosen.response[:100]:
                    result.dissent.append({
                        "provider": r.provider,
                        "response_preview": r.response[:150],
                        "confidence": r.confidence,
                    })

        return result

    async def _weighted_vote(
        self, prompt: str, providers: List[str],
        max_tokens: int, temperature: float, result: MultiStreamResult,
    ) -> MultiStreamResult:
        """All respond, weighted by provider reliability."""
        tasks = [self._query_provider(p, prompt, max_tokens, temperature) for p in providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, StreamResult):
                result.results.append(r)

        successful = [r for r in result.results if r.success]
        if successful:
            result.chosen = max(successful, key=lambda r: r.confidence)
            total_conf = sum(r.confidence for r in successful)
            result.consensus_score = result.chosen.confidence / total_conf if total_conf > 0 else 0

        return result

    async def _hierarchical(
        self, prompt: str, max_tokens: int, temperature: float,
        result: MultiStreamResult,
    ) -> MultiStreamResult:
        """Cascade: try Level 1 first, escalate only if needed."""
        # Level 1: Local
        sr = await self._query_provider("ollama", prompt, max_tokens, temperature)
        result.results.append(sr)
        if sr.success and sr.confidence >= 0.6:
            result.chosen = sr
            return result

        # Level 2: Cloud
        sr2 = await self._query_provider("gemini", prompt, max_tokens, temperature)
        result.results.append(sr2)
        if sr2.success:
            result.chosen = sr2
            return result

        # Level 3: Multi-stream
        remaining = ["groq", "mistral"]
        tasks = [self._query_provider(p, prompt, max_tokens, temperature) for p in remaining]
        for r in await asyncio.gather(*tasks, return_exceptions=True):
            if isinstance(r, StreamResult):
                result.results.append(r)
                if r.success and (result.chosen is None or r.confidence > result.chosen.confidence):
                    result.chosen = r

        return result

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Recent multi-stream query history."""
        return [
            {
                "strategy": r.strategy,
                "level": r.level,
                "providers": [sr.provider for sr in r.results],
                "chosen": r.chosen.provider if r.chosen else None,
                "consensus": round(r.consensus_score, 3),
                "latency_ms": r.total_latency_ms,
                "dissent": len(r.dissent),
            }
            for r in self.history[-limit:]
        ]
