# tools/warchest/shotgun.py
"""
ShotgunTool — fire a prompt at all available inference providers simultaneously.

When you need an answer and don't care which provider gives it first,
shotgun blasts the prompt across every available source in parallel.
First valid response wins. The rest are cancelled.

Use cases:
  - Critical planning decisions where latency matters more than cost
  - Consensus verification — compare responses across providers
  - Provider benchmarking — measure actual response time under load
  - Failover testing — verify which providers are truly alive

Not for routine inference. The BDI provider cascade (minimal → maximal)
is the daily driver. Shotgun is for when you need to win.

Author: Professor Codephreak (© Professor Codephreak)
"""

import asyncio
import time
from decimal import Decimal
from typing import Dict, Any, Optional, List
from pathlib import Path

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ShotgunTool:
    """Fire a prompt at all available providers simultaneously. First response wins."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    async def fire(
        self,
        prompt: str,
        model_hint: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        json_mode: bool = False,
        consensus: bool = False,
    ) -> Dict[str, Any]:
        """Blast prompt across all available providers.

        Args:
            prompt: The prompt to send.
            model_hint: Preferred model name (providers may override).
            max_tokens: Max tokens per response.
            temperature: Sampling temperature.
            json_mode: Request JSON output.
            consensus: If True, wait for ALL providers and return all responses
                       for comparison. If False (default), return first valid response.

        Returns:
            {
                "winner": provider_name,
                "response": text,
                "latency_ms": Decimal (18dp),
                "all_results": [...] (if consensus=True),
                "providers_fired": int,
                "providers_responded": int,
            }
        """
        providers = await self._gather_providers()
        if not providers:
            return {"winner": None, "response": None, "error": "no providers available"}

        logger.info(f"Shotgun: firing at {len(providers)} providers (consensus={consensus})")

        start_ns = time.time_ns()

        if consensus:
            return await self._fire_consensus(providers, prompt, model_hint,
                                               max_tokens, temperature, json_mode, start_ns)
        else:
            return await self._fire_first_wins(providers, prompt, model_hint,
                                                max_tokens, temperature, json_mode, start_ns)

    async def _fire_first_wins(
        self, providers, prompt, model_hint, max_tokens, temperature, json_mode, start_ns
    ) -> Dict[str, Any]:
        """First valid response wins. Cancel the rest."""
        tasks = {}
        for name, handler, model in providers:
            task = asyncio.create_task(
                self._call_provider(handler, prompt, model or model_hint, max_tokens, temperature, json_mode),
                name=name,
            )
            tasks[task] = name

        winner = None
        winner_response = None
        winner_latency = Decimal("0")
        providers_responded = 0

        try:
            done, pending = await asyncio.wait(
                tasks.keys(),
                timeout=self.timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Find first successful result
            for task in done:
                providers_responded += 1
                try:
                    result = task.result()
                    if result and not str(result).startswith("Error:"):
                        winner = tasks[task]
                        winner_response = result
                        elapsed_ns = time.time_ns() - start_ns
                        winner_latency = Decimal(str(elapsed_ns)) / Decimal("1000000")  # ns → ms, 18dp
                        break
                except Exception:
                    continue

            # If first batch had no winner, check remaining as they complete
            if not winner and pending:
                for coro in asyncio.as_completed(list(pending), timeout=self.timeout):
                    try:
                        result = await coro
                        providers_responded += 1
                        if result and not str(result).startswith("Error:"):
                            # Find which task this was
                            for t, n in tasks.items():
                                if t.done() and not t.cancelled():
                                    try:
                                        if t.result() == result:
                                            winner = n
                                            break
                                    except Exception:
                                        continue
                            winner = winner or "unknown"
                            winner_response = result
                            elapsed_ns = time.time_ns() - start_ns
                            winner_latency = Decimal(str(elapsed_ns)) / Decimal("1000000")
                            break
                    except Exception:
                        providers_responded += 1
        finally:
            # Cancel all remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()

        logger.info(
            f"Shotgun: winner='{winner}', latency={winner_latency:.2f}ms, "
            f"{providers_responded}/{len(providers)} responded"
        )

        return {
            "winner": winner,
            "response": winner_response,
            "latency_ms": str(winner_latency),
            "providers_fired": len(providers),
            "providers_responded": providers_responded,
        }

    async def _fire_consensus(
        self, providers, prompt, model_hint, max_tokens, temperature, json_mode, start_ns
    ) -> Dict[str, Any]:
        """Wait for all providers. Return all responses for comparison."""
        tasks = {}
        for name, handler, model in providers:
            task = asyncio.create_task(
                self._call_provider(handler, prompt, model or model_hint, max_tokens, temperature, json_mode),
                name=name,
            )
            tasks[task] = name

        all_results = []
        try:
            done, _ = await asyncio.wait(tasks.keys(), timeout=self.timeout)
            for task in done:
                name = tasks[task]
                try:
                    result = task.result()
                    elapsed_ns = time.time_ns() - start_ns
                    latency = Decimal(str(elapsed_ns)) / Decimal("1000000")
                    all_results.append({
                        "provider": name,
                        "response": result,
                        "latency_ms": str(latency),
                        "success": bool(result and not str(result).startswith("Error:")),
                    })
                except Exception as e:
                    all_results.append({
                        "provider": name,
                        "response": None,
                        "error": str(e),
                        "success": False,
                    })
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()

        # Pick winner = fastest successful
        successful = [r for r in all_results if r["success"]]
        winner = successful[0] if successful else None

        return {
            "winner": winner["provider"] if winner else None,
            "response": winner["response"] if winner else None,
            "latency_ms": winner["latency_ms"] if winner else "0",
            "all_results": all_results,
            "providers_fired": len(providers),
            "providers_responded": len(all_results),
        }

    async def _call_provider(
        self, handler, prompt, model, max_tokens, temperature, json_mode
    ) -> Optional[str]:
        """Call a single provider. Returns response string or None."""
        try:
            return await asyncio.wait_for(
                handler.generate_text(
                    prompt=prompt,
                    model=model or getattr(handler, 'model_name_for_api', None) or "default",
                    max_tokens=max_tokens,
                    temperature=temperature,
                    json_mode=json_mode,
                ),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.debug(f"Shotgun: provider error: {e}")
            return None

    async def _gather_providers(self) -> List[tuple]:
        """Discover all available inference providers and create handlers.

        Returns list of (name, handler, recommended_model) tuples.
        """
        providers = []

        try:
            from llm.inference_discovery import InferenceDiscovery
            disc = await InferenceDiscovery.get_instance()
            await disc.probe_all()

            from llm.llm_factory import create_llm_handler

            for name, source in disc.sources.items():
                status = str(getattr(source, 'status', '')).upper()
                if status not in ('AVAILABLE', 'DEGRADED'):
                    continue

                provider_type = getattr(source, 'provider_type', name)
                models = getattr(source, 'models', [])
                model = models[0] if models else None

                try:
                    handler = await create_llm_handler(
                        provider_name=provider_type,
                        model_name=model,
                    )
                    if handler:
                        providers.append((name, handler, model))
                except Exception:
                    continue

            # Also try OllamaCloudTool as a provider (has its own rate limiter)
            try:
                from tools.cloud.ollama_cloud_tool import OllamaCloudTool
                import os
                if os.getenv("OLLAMA_API_KEY"):
                    cloud = OllamaCloudTool()
                    # Wrap as a handler-like object
                    providers.append(("ollama_cloud_shotgun", _CloudAdapter(cloud), "qwen3:32b"))
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"Shotgun: provider discovery failed: {e}")

        return providers


class _CloudAdapter:
    """Adapt OllamaCloudTool to handler-like interface for shotgun."""

    def __init__(self, cloud_tool):
        self._cloud = cloud_tool
        self.provider_name = "ollama_cloud"
        self.model_name_for_api = "qwen3:32b"

    async def generate_text(self, prompt, model=None, max_tokens=2048,
                            temperature=0.7, json_mode=False, **kwargs):
        result = await self._cloud.execute(
            operation="generate",
            model=model or self.model_name_for_api,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if result.get("success"):
            return result.get("response")
        return None
