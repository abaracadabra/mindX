# mindx/llm/inference_discovery.py
"""
Inference Discovery — finds inference when there is none.

When all primary providers are down, this module:
  1. Probes all known inference sources (vLLM, Ollama, cloud APIs)
  2. Discovers new Ollama models or vLLM endpoints on the network
  3. Auto-selects the best available provider
  4. Enables decision-making even without LLM access via rule-based fallback
  5. Drives self-improvement by evaluating and scoring provider reliability

Architecture:
  InferenceDiscovery (singleton)
    ├── probe_all()         — test every known source, rank by latency/capability
    ├── discover_network()  — scan for Ollama/vLLM on local network
    ├── get_best_provider() — return the best available provider right now
    ├── fallback_decide()   — rule-based decisions without LLM inference
    └── self_improve()      — record reliability stats, adjust preference order
"""

import asyncio
import os
import time
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

try:
    import aiohttp
except ImportError:
    aiohttp = None

from utils.logging_config import get_logger

logger = get_logger(__name__)


class ProviderStatus(Enum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"


@dataclass
class InferenceSource:
    """A discovered inference endpoint."""
    name: str
    provider_type: str  # "vllm", "ollama", "cloud"
    base_url: str
    status: ProviderStatus = ProviderStatus.UNKNOWN
    latency_ms: float = 0.0
    models: List[str] = field(default_factory=list)
    last_checked: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0

    @property
    def reliability(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5  # unknown
        return self.success_count / total

    @property
    def score(self) -> float:
        """Composite score: reliability * speed_factor * recency."""
        reliability = self.reliability
        # Prefer lower latency (normalize: 100ms=1.0, 1000ms=0.5, 5000ms=0.1)
        speed_factor = max(0.1, 1.0 - (self.latency_ms / 2000.0))
        # Penalize stale checks
        age = time.time() - self.last_checked
        recency = max(0.1, 1.0 - (age / 3600.0))  # decays over 1 hour
        return reliability * speed_factor * recency


class InferenceDiscovery:
    """
    Discovers and manages inference sources.
    Singleton — use get_instance().
    """

    _instance: Optional["InferenceDiscovery"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self.sources: Dict[str, InferenceSource] = {}
        self._probe_interval = 60  # seconds between full probes
        self._last_probe = 0.0
        self._decision_rules: List[Dict[str, Any]] = []
        self._improvement_log: List[Dict[str, Any]] = []
        self._initialize_known_sources()

    @classmethod
    async def get_instance(cls) -> "InferenceDiscovery":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _initialize_known_sources(self):
        """Register known inference endpoints from environment/config."""
        # vLLM sources — default port 8001 to avoid conflict with mindX API on 8000
        vllm_url = os.getenv("VLLM_BASE_URL")
        if vllm_url:
            self.sources["vllm_primary"] = InferenceSource(
                name="vllm_primary",
                provider_type="vllm",
                base_url=vllm_url,
            )

        # Ollama sources
        ollama_primary = os.getenv(
            "MINDX_LLM__OLLAMA__BASE_URL", "http://10.0.0.155:18080"
        )
        self.sources["ollama_gpu"] = InferenceSource(
            name="ollama_gpu",
            provider_type="ollama",
            base_url=ollama_primary,
        )
        self.sources["ollama_local"] = InferenceSource(
            name="ollama_local",
            provider_type="ollama",
            base_url="http://localhost:11434",
        )

        # Ollama Cloud — free tier, GPU-hosted models via ollama.com
        # No API key required for free tier (session limits: reset every 5h, weekly reset 7d)
        # API key (OLLAMA_API_KEY) upgrades to Pro tier with 50x usage
        ollama_cloud_key = os.getenv("OLLAMA_API_KEY", "")
        self.sources["ollama_cloud"] = InferenceSource(
            name="ollama_cloud",
            provider_type="ollama_cloud",
            base_url="https://ollama.com",
            status=ProviderStatus.AVAILABLE,  # always available (free tier)
        )

        # Cloud providers (checked via API key presence)
        cloud_providers = {
            "gemini": ("GEMINI_API_KEY", "https://generativelanguage.googleapis.com"),
            "groq": ("GROQ_API_KEY", "https://api.groq.com"),
            "mistral": ("MISTRAL_API_KEY", "https://api.mistral.ai"),
            "openai": ("OPENAI_API_KEY", "https://api.openai.com"),
            "anthropic": ("ANTHROPIC_API_KEY", "https://api.anthropic.com"),
            "together": ("TOGETHER_API_KEY", "https://api.together.xyz"),
            "deepseek": ("DEEPSEEK_API_KEY", "https://api.deepseek.com"),
        }
        for name, (env_var, url) in cloud_providers.items():
            key = os.getenv(env_var)
            self.sources[f"cloud_{name}"] = InferenceSource(
                name=f"cloud_{name}",
                provider_type="cloud",
                base_url=url,
                status=ProviderStatus.AVAILABLE if key else ProviderStatus.UNREACHABLE,
            )

        # Task-to-model correlation: which models suit which agent skills
        # Efficiency optimization — route heavy tasks to cloud, light to local
        self.task_model_map = {
            # Local models (fast, always available, light tasks)
            "heartbeat": {"provider": "ollama_local", "model": "qwen3:0.6b", "reason": "fast, low resource"},
            "embedding": {"provider": "ollama_local", "model": "mxbai-embed-large", "reason": "embedding-native"},
            "simple_chat": {"provider": "ollama_local", "model": "qwen3:1.7b", "reason": "balanced speed/quality"},
            # Cloud models (heavy reasoning, free tier with limits)
            "reasoning": {"provider": "ollama_cloud", "model": "deepseek-v3.2", "reason": "671B reasoning, free tier"},
            "coding": {"provider": "ollama_cloud", "model": "qwen3-coder-next", "reason": "code-specialized, free tier"},
            "blueprint": {"provider": "ollama_cloud", "model": "qwen3.5:397b", "reason": "strategic planning, free tier"},
            "analysis": {"provider": "ollama_cloud", "model": "gemma4:31b", "reason": "analytical, free tier"},
        }

        # Rate limits: realistic free tier constraints
        self.rate_limits = {
            "ollama_local": {"rpm": 60, "daily": None, "note": "no limit, local"},
            "ollama_cloud": {"rpm": 5, "daily": 100, "note": "free tier, 5h session reset, 7d weekly reset"},
            "cloud_gemini": {"rpm": 15, "daily": 1500, "note": "free tier Google AI Studio"},
            "cloud_groq": {"rpm": 30, "daily": 14400, "note": "free tier"},
            "cloud_openai": {"rpm": 3, "daily": 200, "note": "free tier"},
            "cloud_anthropic": {"rpm": 5, "daily": 1000, "note": "with API key"},
        }
        self._cloud_call_count = 0
        self._cloud_last_reset = time.time()

    async def probe_all(self) -> Dict[str, ProviderStatus]:
        """Probe all inference sources concurrently. Returns status map."""
        if not aiohttp:
            logger.warning("InferenceDiscovery: aiohttp not available")
            return {}

        now = time.time()
        if now - self._last_probe < self._probe_interval:
            return {k: v.status for k, v in self.sources.items()}

        self._last_probe = now
        tasks = []
        for name, source in self.sources.items():
            if source.provider_type == "cloud":
                # Cloud providers: just check if API key exists
                key_present = source.status != ProviderStatus.UNREACHABLE
                if key_present:
                    source.status = ProviderStatus.AVAILABLE
                    source.last_checked = now
                continue
            tasks.append(self._probe_source(source))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        available = [s for s in self.sources.values()
                     if s.status == ProviderStatus.AVAILABLE]
        logger.info(
            f"InferenceDiscovery: probed {len(self.sources)} sources, "
            f"{len(available)} available"
        )
        return {k: v.status for k, v in self.sources.items()}

    async def _probe_source(self, source: InferenceSource):
        """Probe a single local inference source."""
        if not aiohttp:
            return

        start = time.time()
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if source.provider_type == "vllm":
                    # Try /health then /v1/models
                    try:
                        async with session.get(
                            f"{source.base_url}/health"
                        ) as resp:
                            if resp.status == 200:
                                source.status = ProviderStatus.AVAILABLE
                            else:
                                source.status = ProviderStatus.DEGRADED
                    except Exception:
                        try:
                            async with session.get(
                                f"{source.base_url}/v1/models"
                            ) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    source.models = [
                                        m.get("id", "")
                                        for m in data.get("data", [])
                                    ]
                                    source.status = ProviderStatus.AVAILABLE
                                else:
                                    source.status = ProviderStatus.UNREACHABLE
                        except Exception:
                            source.status = ProviderStatus.UNREACHABLE

                elif source.provider_type == "ollama":
                    async with session.get(
                        f"{source.base_url}/api/tags"
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            source.models = [
                                m.get("name", "")
                                for m in data.get("models", [])
                            ]
                            source.status = ProviderStatus.AVAILABLE
                        else:
                            source.status = ProviderStatus.UNREACHABLE

                elapsed = (time.time() - start) * 1000
                source.latency_ms = elapsed
                source.last_checked = time.time()

                if source.status == ProviderStatus.AVAILABLE:
                    source.success_count += 1
                    source.consecutive_failures = 0
                else:
                    source.failure_count += 1
                    source.consecutive_failures += 1

        except Exception as e:
            source.status = ProviderStatus.UNREACHABLE
            source.failure_count += 1
            source.consecutive_failures += 1
            source.last_checked = time.time()
            logger.debug(f"InferenceDiscovery: {source.name} unreachable: {e}")

    async def discover_network(
        self, subnet: str = "10.0.0", ports: List[int] = None
    ) -> List[InferenceSource]:
        """
        Scan local network for Ollama/vLLM instances.
        Checks common ports on the given subnet.
        """
        if not aiohttp:
            return []

        ports = ports or [11434, 18080, 8000, 8080]
        discovered = []
        timeout = aiohttp.ClientTimeout(total=2)

        async def check_host(ip: str, port: int):
            url = f"http://{ip}:{port}"
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    # Try Ollama
                    try:
                        async with session.get(f"{url}/api/tags") as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                models = [
                                    m.get("name", "")
                                    for m in data.get("models", [])
                                ]
                                src = InferenceSource(
                                    name=f"discovered_ollama_{ip}_{port}",
                                    provider_type="ollama",
                                    base_url=url,
                                    status=ProviderStatus.AVAILABLE,
                                    models=models,
                                    last_checked=time.time(),
                                )
                                discovered.append(src)
                                return
                    except Exception:
                        pass

                    # Try vLLM
                    try:
                        async with session.get(f"{url}/v1/models") as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                models = [
                                    m.get("id", "")
                                    for m in data.get("data", [])
                                ]
                                src = InferenceSource(
                                    name=f"discovered_vllm_{ip}_{port}",
                                    provider_type="vllm",
                                    base_url=url,
                                    status=ProviderStatus.AVAILABLE,
                                    models=models,
                                    last_checked=time.time(),
                                )
                                discovered.append(src)
                    except Exception:
                        pass
            except Exception:
                pass

        # Scan last octet 1-254 on common ports (parallel)
        tasks = []
        for last_octet in range(1, 255):
            ip = f"{subnet}.{last_octet}"
            for port in ports:
                tasks.append(check_host(ip, port))

        # Limit concurrency to avoid flooding
        sem = asyncio.Semaphore(50)

        async def limited(coro):
            async with sem:
                return await coro

        await asyncio.gather(
            *[limited(t) for t in tasks], return_exceptions=True
        )

        # Register discovered sources
        for src in discovered:
            if src.name not in self.sources:
                self.sources[src.name] = src
                logger.info(
                    f"InferenceDiscovery: found {src.provider_type} at "
                    f"{src.base_url} with models: {src.models}"
                )

        return discovered

    async def get_best_provider(self) -> Optional[Tuple[str, InferenceSource]]:
        """
        Return the best available inference source right now.
        Probes if stale, ranks by composite score.
        """
        await self.probe_all()

        available = [
            (name, src)
            for name, src in self.sources.items()
            if src.status == ProviderStatus.AVAILABLE
        ]

        if not available:
            logger.warning("InferenceDiscovery: NO inference sources available")
            return None

        # Sort by score (highest first)
        available.sort(key=lambda x: x[1].score, reverse=True)
        best_name, best_src = available[0]
        logger.info(
            f"InferenceDiscovery: best provider = {best_name} "
            f"(score={best_src.score:.3f}, latency={best_src.latency_ms:.0f}ms, "
            f"reliability={best_src.reliability:.2f})"
        )
        return best_name, best_src

    async def get_provider_for_task(self, task_type: str) -> Optional[Tuple[str, InferenceSource, str]]:
        """
        Get the best provider for a specific task type.
        Returns (provider_name, source, recommended_model) or None.

        Task routing: micro models prove intelligence is intelligence —
        mindX works from substandard inference because structure > raw power.
        Cloud models are used for heavy tasks when free tier is available.

        Efficiency: local for speed, cloud for depth, always within rate limits.
        """
        # Check task-to-model map
        mapping = self.task_model_map.get(task_type)
        if mapping:
            provider_name = mapping["provider"]
            source = self.sources.get(provider_name)
            if source and source.status == ProviderStatus.AVAILABLE:
                # Check cloud rate limits
                if "cloud" in provider_name:
                    limits = self.rate_limits.get(provider_name, {})
                    daily_limit = limits.get("daily")
                    if daily_limit and self._cloud_call_count >= daily_limit:
                        logger.debug(f"InferenceDiscovery: {provider_name} daily limit ({daily_limit}) reached, falling back to local")
                    else:
                        self._cloud_call_count += 1
                        return provider_name, source, mapping["model"]

        # Fallback: local ollama for any task (intelligence is intelligence)
        local = self.sources.get("ollama_local")
        if local and local.status == ProviderStatus.AVAILABLE:
            # Route to appropriate local model by task
            local_model_map = {
                "heartbeat": "qwen3:0.6b",
                "embedding": "mxbai-embed-large",
                "simple_chat": "qwen3:1.7b",
                "reasoning": "qwen3:1.7b",  # small model, still reasons
                "coding": "qwen3:1.7b",
                "blueprint": "qwen3:1.7b",
                "analysis": "qwen3:1.7b",
            }
            model = local_model_map.get(task_type, "qwen3:1.7b")
            return "ollama_local", local, model

        # Last resort: any available provider
        best = await self.get_best_provider()
        if best:
            return best[0], best[1], ""
        return None

    def fallback_decide(
        self, context: str, options: List[str], criteria: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rule-based decision making when NO inference is available.
        Uses heuristics, keyword matching, and priority rules to make decisions
        without LLM assistance.

        This is the last resort — enables the system to continue operating
        even when all inference is down.

        Args:
            context: Description of the situation requiring a decision
            options: Available choices
            criteria: Optional evaluation criteria

        Returns:
            Decision dict with 'choice', 'reasoning', 'confidence'
        """
        if not options:
            return {
                "choice": None,
                "reasoning": "No options provided",
                "confidence": 0.0,
                "method": "fallback_rule",
            }

        context_lower = context.lower()
        criteria_lower = (criteria or "").lower()

        # Rule 1: Safety-first — if context mentions error/failure/critical,
        # choose the most conservative option (shortest, or one containing
        # "safe", "stop", "wait", "retry")
        safety_keywords = {"error", "fail", "critical", "crash", "down", "broken"}
        if any(kw in context_lower for kw in safety_keywords):
            safe_words = {"safe", "stop", "wait", "retry", "rollback", "revert"}
            for opt in options:
                if any(sw in opt.lower() for sw in safe_words):
                    return {
                        "choice": opt,
                        "reasoning": f"Safety rule: context indicates error/failure, choosing conservative: '{opt}'",
                        "confidence": 0.7,
                        "method": "fallback_rule_safety",
                    }
            # Default: pick first option (status quo / no action)
            return {
                "choice": options[0],
                "reasoning": "Safety rule: defaulting to first option (least change) during error condition",
                "confidence": 0.5,
                "method": "fallback_rule_safety_default",
            }

        # Rule 2: Improvement — if context mentions improve/optimize/evolve,
        # prefer options with action words
        improve_keywords = {"improve", "optimize", "evolve", "upgrade", "enhance"}
        if any(kw in context_lower for kw in improve_keywords):
            action_words = {"update", "upgrade", "optimize", "refactor", "improve", "add"}
            for opt in options:
                if any(aw in opt.lower() for aw in action_words):
                    return {
                        "choice": opt,
                        "reasoning": f"Improvement rule: context requests improvement, choosing action: '{opt}'",
                        "confidence": 0.6,
                        "method": "fallback_rule_improve",
                    }

        # Rule 3: Priority matching — if criteria specifies "fast"/"quick",
        # prefer shorter/simpler options
        if "fast" in criteria_lower or "quick" in criteria_lower:
            shortest = min(options, key=len)
            return {
                "choice": shortest,
                "reasoning": f"Speed rule: criteria requests fast, choosing shortest: '{shortest}'",
                "confidence": 0.5,
                "method": "fallback_rule_speed",
            }

        # Rule 4: Keyword overlap — score options by keyword overlap with context
        scored = []
        context_words = set(context_lower.split())
        for opt in options:
            opt_words = set(opt.lower().split())
            overlap = len(context_words & opt_words)
            scored.append((opt, overlap))
        scored.sort(key=lambda x: x[1], reverse=True)
        if scored[0][1] > 0:
            return {
                "choice": scored[0][0],
                "reasoning": f"Keyword overlap: '{scored[0][0]}' has {scored[0][1]} matching words with context",
                "confidence": 0.4 + min(0.3, scored[0][1] * 0.1),
                "method": "fallback_rule_keyword",
            }

        # Rule 5: Default — first option
        return {
            "choice": options[0],
            "reasoning": "Default rule: no specific heuristic matched, choosing first option",
            "confidence": 0.3,
            "method": "fallback_rule_default",
        }

    async def self_improve(self) -> Dict[str, Any]:
        """
        Evaluate provider reliability and adjust preference order.
        Records improvement actions for the autonomous improvement loop.

        Returns:
            Improvement report with actions taken.
        """
        await self.probe_all()

        report = {
            "timestamp": time.time(),
            "sources_total": len(self.sources),
            "available": [],
            "degraded": [],
            "unreachable": [],
            "actions": [],
        }

        for name, src in self.sources.items():
            entry = {
                "name": name,
                "type": src.provider_type,
                "score": round(src.score, 3),
                "reliability": round(src.reliability, 3),
                "latency_ms": round(src.latency_ms, 1),
                "models": src.models[:5],
            }
            if src.status == ProviderStatus.AVAILABLE:
                report["available"].append(entry)
            elif src.status == ProviderStatus.DEGRADED:
                report["degraded"].append(entry)
            else:
                report["unreachable"].append(entry)

        # Action: if primary local inference is down, attempt to pull a model
        local_sources = [
            s for s in self.sources.values()
            if s.provider_type in ("ollama", "vllm")
            and s.status == ProviderStatus.AVAILABLE
        ]

        if not local_sources:
            report["actions"].append({
                "action": "no_local_inference",
                "recommendation": (
                    "All local inference sources are down. "
                    "1) Start Ollama: systemctl start ollama && ollama pull qwen3:0.6b "
                    "2) Start vLLM: vllm serve Qwen/Qwen3-0.6B --port 8000 "
                    "3) Scan network: discovery.discover_network()"
                ),
            })

        # Action: if an Ollama source is up but has no models, suggest pulling
        for name, src in self.sources.items():
            if (
                src.provider_type == "ollama"
                and src.status == ProviderStatus.AVAILABLE
                and not src.models
            ):
                report["actions"].append({
                    "action": "pull_model",
                    "source": name,
                    "recommendation": (
                        f"Ollama at {src.base_url} has no models. "
                        "Pull: ollama pull qwen3:0.6b"
                    ),
                })

        # Action: track reliability degradation
        for name, src in self.sources.items():
            if src.consecutive_failures >= 3:
                report["actions"].append({
                    "action": "reliability_alert",
                    "source": name,
                    "consecutive_failures": src.consecutive_failures,
                    "recommendation": f"{name} has failed {src.consecutive_failures}x consecutively. Check service health.",
                })

        # Generate recommended preference order based on current scores
        available_sorted = sorted(
            [(n, s) for n, s in self.sources.items()
             if s.status == ProviderStatus.AVAILABLE],
            key=lambda x: x[1].score,
            reverse=True,
        )
        if available_sorted:
            report["recommended_order"] = [n for n, _ in available_sorted]

        self._improvement_log.append(report)
        # Keep last 100 improvement records
        if len(self._improvement_log) > 100:
            self._improvement_log = self._improvement_log[-100:]

        logger.info(
            f"InferenceDiscovery self-improve: "
            f"{len(report['available'])} available, "
            f"{len(report['unreachable'])} unreachable, "
            f"{len(report['actions'])} actions"
        )
        return report

    def get_improvement_history(self) -> List[Dict[str, Any]]:
        """Return recent improvement/evaluation history."""
        return list(self._improvement_log)

    def status_summary(self) -> Dict[str, Any]:
        """Quick status summary for API endpoints."""
        available = [
            s for s in self.sources.values()
            if s.status == ProviderStatus.AVAILABLE
        ]
        return {
            "total_sources": len(self.sources),
            "available": len(available),
            "local_inference": any(
                s.provider_type in ("vllm", "ollama")
                for s in available
            ),
            "cloud_inference": any(
                s.provider_type == "cloud"
                for s in available
            ),
            "best_local": next(
                (
                    {"name": s.name, "type": s.provider_type,
                     "url": s.base_url, "models": s.models[:3]}
                    for s in sorted(available, key=lambda x: x.score, reverse=True)
                    if s.provider_type in ("vllm", "ollama")
                ),
                None,
            ),
            "sources": {
                name: {
                    "type": src.provider_type,
                    "status": src.status.value,
                    "score": round(src.score, 3),
                    "models": src.models[:3],
                }
                for name, src in self.sources.items()
            },
        }
