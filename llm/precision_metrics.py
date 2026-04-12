"""
Precision Metrics for Ollama Inference

Scientific-grade token and timing tracking at 18 decimal places of precision.
Uses Python Decimal (28-digit significand) for accumulation — no floating-point
drift on long-running systems. Aligned with blockchain precision (1 token =
10^18 sub-token units, same as 1 ETH = 10^18 wei).

Design principles:
    1. ACTUAL over estimated — use eval_count/prompt_eval_count from Ollama API
    2. NANOSECOND timing — Ollama returns durations in nanoseconds natively
    3. DECIMAL accumulation — no float compounding errors over millions of requests
    4. ZERO estimation fallback — if Ollama doesn't return counts, record 0 (unknown)
       rather than fabricate numbers from word-count heuristics

Usage:
    tracker = PrecisionMetricsTracker()
    tracker.record(OllamaResponseMetrics.from_api_response(data))
    print(tracker.summary())
"""

import time
import json
from decimal import Decimal, getcontext, ROUND_HALF_UP
from dataclasses import dataclass, field, asdict
from typing import Optional, Any
from pathlib import Path

from utils.logging_config import get_logger

logger = get_logger(__name__)

# Set global decimal precision to 36 digits (18dp + 18 integer digits)
getcontext().prec = 36

# Constants — 18 decimal places, matching blockchain wei precision
PRECISION_PLACES = 18
DECIMAL_ZERO = Decimal("0")
DECIMAL_ONE = Decimal("1")
NANO_TO_SEC = Decimal("1e-9")      # 1 nanosecond in seconds
NANO_TO_MS = Decimal("1e-6")       # 1 nanosecond in milliseconds

# Sub-token unit: 1 token = 10^18 sub-tokens (like wei to ETH)
SUBTOKEN_FACTOR = Decimal(10) ** PRECISION_PLACES


def _now_ns() -> int:
    """Current time in nanoseconds (monotonic for durations, wall for timestamps)."""
    return time.time_ns()


def _decimal(value: Any) -> Decimal:
    """Safely convert any numeric value to Decimal."""
    if isinstance(value, Decimal):
        return value
    if value is None:
        return DECIMAL_ZERO
    try:
        return Decimal(str(value))
    except Exception:
        return DECIMAL_ZERO


@dataclass
class OllamaResponseMetrics:
    """
    Metrics extracted from a single Ollama API response.
    All values are ACTUAL from the API — no estimation.

    Ollama API returns:
        eval_count:          int — output tokens generated
        prompt_eval_count:   int — input tokens in prompt
        total_duration:      int — total time in nanoseconds
        load_duration:       int — model load time in nanoseconds
        prompt_eval_duration: int — prompt evaluation time in nanoseconds
        eval_duration:       int — token generation time in nanoseconds
    """

    # Token counts — exact integers from Ollama
    eval_count: int = 0               # output tokens (ACTUAL)
    prompt_eval_count: int = 0        # input tokens (ACTUAL)

    # Durations in nanoseconds — exact integers from Ollama
    total_duration_ns: int = 0        # total time
    load_duration_ns: int = 0         # model load time
    prompt_eval_duration_ns: int = 0  # prompt evaluation time
    eval_duration_ns: int = 0         # token generation time

    # Metadata
    model: str = ""
    timestamp_ns: int = 0             # wall clock at response time
    success: bool = True
    done_reason: str = ""

    @classmethod
    def from_api_response(cls, data: dict, model: str = "") -> "OllamaResponseMetrics":
        """
        Extract metrics from an Ollama API response dict.
        Only uses ACTUAL values — never estimates.
        """
        return cls(
            eval_count=int(data.get("eval_count", 0)),
            prompt_eval_count=int(data.get("prompt_eval_count", 0)),
            total_duration_ns=int(data.get("total_duration", 0)),
            load_duration_ns=int(data.get("load_duration", 0)),
            prompt_eval_duration_ns=int(data.get("prompt_eval_duration", 0)),
            eval_duration_ns=int(data.get("eval_duration", 0)),
            model=model or data.get("model", ""),
            timestamp_ns=_now_ns(),
            success=data.get("done", True),
            done_reason=data.get("done_reason", ""),
        )

    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output). Exact integer."""
        return self.prompt_eval_count + self.eval_count

    @property
    def tokens_per_second(self) -> Decimal:
        """Output tokens per second. Decimal precision from nanosecond timing."""
        if self.eval_duration_ns <= 0:
            return DECIMAL_ZERO
        return _decimal(self.eval_count) / (_decimal(self.eval_duration_ns) * NANO_TO_SEC)

    @property
    def prompt_tokens_per_second(self) -> Decimal:
        """Prompt processing speed. Decimal precision."""
        if self.prompt_eval_duration_ns <= 0:
            return DECIMAL_ZERO
        return _decimal(self.prompt_eval_count) / (_decimal(self.prompt_eval_duration_ns) * NANO_TO_SEC)

    @property
    def total_duration_ms(self) -> Decimal:
        """Total duration in milliseconds. Decimal precision."""
        return _decimal(self.total_duration_ns) * NANO_TO_MS

    @property
    def eval_duration_ms(self) -> Decimal:
        """Token generation duration in milliseconds."""
        return _decimal(self.eval_duration_ns) * NANO_TO_MS

    @property
    def has_actual_counts(self) -> bool:
        """True if Ollama returned actual token counts (not zero)."""
        return self.eval_count > 0 or self.prompt_eval_count > 0

    def to_subtokens(self) -> dict:
        """
        Express token counts in sub-token units (18 decimal places).
        1 token = 10^18 sub-tokens, like 1 ETH = 10^18 wei.
        """
        return {
            "eval_count_subtokens": str(Decimal(self.eval_count) * SUBTOKEN_FACTOR),
            "prompt_eval_count_subtokens": str(Decimal(self.prompt_eval_count) * SUBTOKEN_FACTOR),
            "total_tokens_subtokens": str(Decimal(self.total_tokens) * SUBTOKEN_FACTOR),
        }

    def cost_usd(self, input_price_per_million: Decimal, output_price_per_million: Decimal) -> Decimal:
        """Calculate cost in USD at 18-decimal precision.

        Prices are per 1M tokens. cypherpunk2048 standard: every fraction counts.
        Spending .01 to earn .011 is profit at any scale.
        """
        input_cost = _decimal(self.prompt_eval_count) * input_price_per_million / Decimal("1000000")
        output_cost = _decimal(self.eval_count) * output_price_per_million / Decimal("1000000")
        return input_cost + output_cost


@dataclass
class PrecisionAccumulator:
    """
    Decimal-precision accumulator for a single metric.
    Tracks count, sum, min, max — no floating-point drift.
    """
    count: int = 0
    sum: Decimal = field(default_factory=lambda: DECIMAL_ZERO)
    min: Optional[Decimal] = None
    max: Optional[Decimal] = None

    def record(self, value: Decimal):
        """Record a value with full precision."""
        self.count += 1
        self.sum += value
        if self.min is None or value < self.min:
            self.min = value
        if self.max is None or value > self.max:
            self.max = value

    @property
    def mean(self) -> Decimal:
        """Arithmetic mean with full Decimal precision."""
        if self.count == 0:
            return DECIMAL_ZERO
        return self.sum / Decimal(self.count)

    def to_dict(self) -> dict:
        """Serialize with full 18dp precision."""
        return {
            "count": self.count,
            "sum": str(self.sum),
            "mean": str(self.mean.quantize(Decimal(f"1e-{PRECISION_PLACES}"), rounding=ROUND_HALF_UP)),
            "min": str(self.min) if self.min is not None else None,
            "max": str(self.max) if self.max is not None else None,
        }


@dataclass
class ModelPrecisionMetrics:
    """Precision metrics for a single model."""
    model_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # Token counts — exact integers
    total_eval_count: int = 0              # total output tokens (ACTUAL)
    total_prompt_eval_count: int = 0       # total input tokens (ACTUAL)
    requests_with_actual_counts: int = 0   # how many had real counts vs zero

    # Precision accumulators
    tokens_per_second: PrecisionAccumulator = field(default_factory=PrecisionAccumulator)
    prompt_tokens_per_second: PrecisionAccumulator = field(default_factory=PrecisionAccumulator)
    latency_ms: PrecisionAccumulator = field(default_factory=PrecisionAccumulator)
    eval_duration_ms: PrecisionAccumulator = field(default_factory=PrecisionAccumulator)

    # Nanosecond-precision totals
    total_eval_duration_ns: int = 0
    total_prompt_eval_duration_ns: int = 0
    total_load_duration_ns: int = 0

    # Timestamps
    first_request_ns: int = 0
    last_request_ns: int = 0

    def record(self, metrics: OllamaResponseMetrics):
        """Record a response with full precision. Only uses actuals."""
        self.total_requests += 1
        if metrics.success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        # Token counts — exact addition
        self.total_eval_count += metrics.eval_count
        self.total_prompt_eval_count += metrics.prompt_eval_count

        if metrics.has_actual_counts:
            self.requests_with_actual_counts += 1

        # Nanosecond durations — exact addition
        self.total_eval_duration_ns += metrics.eval_duration_ns
        self.total_prompt_eval_duration_ns += metrics.prompt_eval_duration_ns
        self.total_load_duration_ns += metrics.load_duration_ns

        # Decimal accumulators — per-request rates
        if metrics.eval_duration_ns > 0:
            self.tokens_per_second.record(metrics.tokens_per_second)
            self.eval_duration_ms.record(metrics.eval_duration_ms)

        if metrics.prompt_eval_duration_ns > 0:
            self.prompt_tokens_per_second.record(metrics.prompt_tokens_per_second)

        self.latency_ms.record(metrics.total_duration_ms)

        # Timestamps
        now = metrics.timestamp_ns or _now_ns()
        if self.first_request_ns == 0:
            self.first_request_ns = now
        self.last_request_ns = now

    @property
    def total_tokens(self) -> int:
        """Total tokens processed. Exact integer."""
        return self.total_eval_count + self.total_prompt_eval_count

    @property
    def aggregate_tokens_per_second(self) -> Decimal:
        """
        Aggregate output throughput: total eval tokens / total eval duration.
        More statistically sound than averaging per-request rates.
        """
        if self.total_eval_duration_ns <= 0:
            return DECIMAL_ZERO
        return _decimal(self.total_eval_count) / (_decimal(self.total_eval_duration_ns) * NANO_TO_SEC)

    @property
    def success_rate(self) -> Decimal:
        """Success rate as Decimal (0-1)."""
        if self.total_requests == 0:
            return DECIMAL_ZERO
        return _decimal(self.successful_requests) / _decimal(self.total_requests)

    @property
    def actual_count_rate(self) -> Decimal:
        """Fraction of requests that had actual token counts from Ollama."""
        if self.total_requests == 0:
            return DECIMAL_ZERO
        return _decimal(self.requests_with_actual_counts) / _decimal(self.total_requests)

    def to_dict(self) -> dict:
        """Full precision serialization."""
        q = lambda d: str(d.quantize(Decimal(f"1e-{PRECISION_PLACES}"), rounding=ROUND_HALF_UP))
        return {
            "model": self.model_name,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": q(self.success_rate),
            "tokens": {
                "total_eval_count": self.total_eval_count,
                "total_prompt_eval_count": self.total_prompt_eval_count,
                "total_tokens": self.total_tokens,
                "total_tokens_subtokens": str(Decimal(self.total_tokens) * SUBTOKEN_FACTOR),
                "requests_with_actual_counts": self.requests_with_actual_counts,
                "actual_count_rate": q(self.actual_count_rate),
            },
            "throughput": {
                "aggregate_tokens_per_second": q(self.aggregate_tokens_per_second),
                "per_request_tokens_per_second": self.tokens_per_second.to_dict(),
                "per_request_prompt_tokens_per_second": self.prompt_tokens_per_second.to_dict(),
            },
            "timing_ns": {
                "total_eval_duration_ns": self.total_eval_duration_ns,
                "total_prompt_eval_duration_ns": self.total_prompt_eval_duration_ns,
                "total_load_duration_ns": self.total_load_duration_ns,
            },
            "latency_ms": self.latency_ms.to_dict(),
            "eval_duration_ms": self.eval_duration_ms.to_dict(),
            "period": {
                "first_request_ns": self.first_request_ns,
                "last_request_ns": self.last_request_ns,
                "span_seconds": str(
                    _decimal(self.last_request_ns - self.first_request_ns) * NANO_TO_SEC
                ) if self.last_request_ns > self.first_request_ns else "0",
            },
        }


class PrecisionMetricsTracker:
    """
    Central tracker for all Ollama inference metrics with 18-decimal precision.

    Replaces:
        - OllamaAPIMetrics.total_tokens (int accumulation, estimation fallback)
        - OllamaChatManager's 1.3x word multiplier
        - InferenceOptimizer's float throughput
        - HierarchicalModelScorer's float EMA

    Data sources:
        - eval_count, prompt_eval_count: ACTUAL from Ollama API (integer)
        - total_duration, eval_duration: ACTUAL from Ollama API (nanoseconds)
        - Timing: time.time_ns() for wall-clock (nanosecond resolution)
    """

    def __init__(self, persistence_path: str = "data/metrics/precision_metrics.json"):
        self.models: dict[str, ModelPrecisionMetrics] = {}
        self.persistence_path = Path(persistence_path)

        # Global counters — exact integers
        self.global_total_requests: int = 0
        self.global_total_eval_tokens: int = 0
        self.global_total_prompt_tokens: int = 0
        self.global_total_eval_duration_ns: int = 0
        self.global_requests_with_actuals: int = 0

        # Cost tracking — 18-decimal Decimal precision (cypherpunk2048 standard)
        # Prices per 1M tokens, loaded from provider pricing data
        self.global_total_cost_usd: Decimal = DECIMAL_ZERO
        self.provider_pricing: dict[str, dict[str, Decimal]] = self._load_provider_pricing()

        self._load()

    def record(self, response: OllamaResponseMetrics):
        """Record an Ollama response with full precision."""
        model = response.model or "unknown"

        if model not in self.models:
            self.models[model] = ModelPrecisionMetrics(model_name=model)

        self.models[model].record(response)

        # Global counters — exact integer accumulation
        self.global_total_requests += 1
        self.global_total_eval_tokens += response.eval_count
        self.global_total_prompt_tokens += response.prompt_eval_count
        self.global_total_eval_duration_ns += response.eval_duration_ns
        if response.has_actual_counts:
            self.global_requests_with_actuals += 1

        # Auto-save periodically (every 50 requests)
        if self.global_total_requests % 50 == 0:
            self._save()

    @property
    def global_total_tokens(self) -> int:
        """Total tokens across all models. Exact integer."""
        return self.global_total_eval_tokens + self.global_total_prompt_tokens

    @property
    def global_tokens_per_second(self) -> Decimal:
        """Aggregate throughput across all models."""
        if self.global_total_eval_duration_ns <= 0:
            return DECIMAL_ZERO
        return _decimal(self.global_total_eval_tokens) / (
            _decimal(self.global_total_eval_duration_ns) * NANO_TO_SEC
        )

    @property
    def global_actual_rate(self) -> Decimal:
        """Fraction of all requests with actual token counts."""
        if self.global_total_requests == 0:
            return DECIMAL_ZERO
        return _decimal(self.global_requests_with_actuals) / _decimal(self.global_total_requests)

    def _load_provider_pricing(self) -> dict:
        """Load token pricing from TokenCalculatorTool's pricing data.

        Returns {model_key: {"input": Decimal, "output": Decimal}} per 1M tokens.
        All prices stored as Decimal — no float drift across millions of requests.
        """
        pricing = {}
        try:
            pricing_path = Path("data/config/token_pricing.json")
            if not pricing_path.exists():
                pricing_path = Path("data/monitoring/token_pricing.json")
            if pricing_path.exists():
                raw = json.loads(pricing_path.read_text())
                for provider, models in raw.get("pricing_per_1M_tokens", {}).items():
                    for model_key, prices in models.items():
                        if isinstance(prices, dict):
                            key = f"{provider}/{model_key}"
                            pricing[key] = {
                                "input": _decimal(prices.get("input", 0)),
                                "output": _decimal(prices.get("output", 0)),
                            }
        except Exception:
            pass

        # Hardcoded fallback for known providers (per 1M tokens, USD)
        defaults = {
            "ollama/local": {"input": DECIMAL_ZERO, "output": DECIMAL_ZERO},
            "ollama/cloud": {"input": DECIMAL_ZERO, "output": DECIMAL_ZERO},
            "gemini/gemini-2.0-flash": {"input": Decimal("0.10"), "output": Decimal("0.40")},
            "gemini/gemini-1.5-pro": {"input": Decimal("1.25"), "output": Decimal("5.00")},
            "groq/llama3-8b-8192": {"input": Decimal("0.05"), "output": Decimal("0.08")},
            "groq/llama3-70b-8192": {"input": Decimal("0.59"), "output": Decimal("0.79")},
            "openai/gpt-4o": {"input": Decimal("2.50"), "output": Decimal("10.00")},
            "openai/gpt-4o-mini": {"input": Decimal("0.15"), "output": Decimal("0.60")},
            "anthropic/claude-sonnet-4-6": {"input": Decimal("3.00"), "output": Decimal("15.00")},
            "anthropic/claude-haiku-4-5": {"input": Decimal("0.80"), "output": Decimal("4.00")},
            "mistral/mistral-large": {"input": Decimal("2.00"), "output": Decimal("6.00")},
            "mistral/mistral-small": {"input": Decimal("0.10"), "output": Decimal("0.30")},
            "together/meta-llama/Llama-3-70b": {"input": Decimal("0.90"), "output": Decimal("0.90")},
        }
        for k, v in defaults.items():
            if k not in pricing:
                pricing[k] = v
        return pricing

    def _get_pricing(self, model: str, provider: str = "") -> tuple:
        """Resolve pricing for a model. Returns (input_per_M, output_per_M) as Decimals."""
        # Try exact match
        for key_prefix in [f"{provider}/{model}", model]:
            if key_prefix in self.provider_pricing:
                p = self.provider_pricing[key_prefix]
                return p["input"], p["output"]
        # Try substring match
        for key, p in self.provider_pricing.items():
            if model and model in key:
                return p["input"], p["output"]
        return DECIMAL_ZERO, DECIMAL_ZERO

    def record_with_cost(self, response: OllamaResponseMetrics, provider: str = "") -> Decimal:
        """Record response AND calculate cost. Returns cost in USD (18dp)."""
        self.record(response)
        input_price, output_price = self._get_pricing(response.model, provider)
        cost = response.cost_usd(input_price, output_price)
        self.global_total_cost_usd += cost
        return cost

    def summary(self) -> dict:
        """Full precision summary across all models."""
        q = lambda d: str(d.quantize(Decimal(f"1e-{PRECISION_PLACES}"), rounding=ROUND_HALF_UP))
        return {
            "precision": f"{PRECISION_PLACES} decimal places",
            "global": {
                "total_requests": self.global_total_requests,
                "total_eval_tokens": self.global_total_eval_tokens,
                "total_prompt_tokens": self.global_total_prompt_tokens,
                "total_tokens": self.global_total_tokens,
                "total_tokens_subtokens": str(Decimal(self.global_total_tokens) * SUBTOKEN_FACTOR),
                "aggregate_tokens_per_second": q(self.global_tokens_per_second),
                "actual_count_rate": q(self.global_actual_rate),
                "total_eval_duration_ns": self.global_total_eval_duration_ns,
                "requests_with_actual_counts": self.global_requests_with_actuals,
                "total_cost_usd": q(self.global_total_cost_usd),
            },
            "models": {name: m.to_dict() for name, m in self.models.items()},
        }

    def get_model_metrics(self, model: str) -> Optional[ModelPrecisionMetrics]:
        """Get precision metrics for a specific model."""
        return self.models.get(model)

    def get_tokens_per_second_for_scorer(self, model: str) -> Decimal:
        """
        Return aggregate tokens/sec for HierarchicalModelScorer integration.
        Uses aggregate (total_tokens / total_duration) not per-request average
        because aggregate is more statistically robust.
        """
        m = self.models.get(model)
        if not m:
            return DECIMAL_ZERO
        return m.aggregate_tokens_per_second

    def _save(self):
        """Persist metrics to disk."""
        try:
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "global_total_requests": self.global_total_requests,
                "global_total_eval_tokens": self.global_total_eval_tokens,
                "global_total_prompt_tokens": self.global_total_prompt_tokens,
                "global_total_eval_duration_ns": self.global_total_eval_duration_ns,
                "global_requests_with_actuals": self.global_requests_with_actuals,
                "global_total_cost_usd": str(self.global_total_cost_usd),
                "models": {},
            }
            for name, m in self.models.items():
                data["models"][name] = {
                    "total_requests": m.total_requests,
                    "successful_requests": m.successful_requests,
                    "failed_requests": m.failed_requests,
                    "total_eval_count": m.total_eval_count,
                    "total_prompt_eval_count": m.total_prompt_eval_count,
                    "requests_with_actual_counts": m.requests_with_actual_counts,
                    "total_eval_duration_ns": m.total_eval_duration_ns,
                    "total_prompt_eval_duration_ns": m.total_prompt_eval_duration_ns,
                    "total_load_duration_ns": m.total_load_duration_ns,
                    "first_request_ns": m.first_request_ns,
                    "last_request_ns": m.last_request_ns,
                }
            self.persistence_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug(f"Failed to save precision metrics: {e}")

    def _load(self):
        """Load persisted metrics."""
        if not self.persistence_path.exists():
            return
        try:
            data = json.loads(self.persistence_path.read_text())
            self.global_total_requests = data.get("global_total_requests", 0)
            self.global_total_eval_tokens = data.get("global_total_eval_tokens", 0)
            self.global_total_prompt_tokens = data.get("global_total_prompt_tokens", 0)
            self.global_total_eval_duration_ns = data.get("global_total_eval_duration_ns", 0)
            self.global_requests_with_actuals = data.get("global_requests_with_actuals", 0)
            self.global_total_cost_usd = _decimal(data.get("global_total_cost_usd", 0))

            for name, mdata in data.get("models", {}).items():
                m = ModelPrecisionMetrics(model_name=name)
                m.total_requests = mdata.get("total_requests", 0)
                m.successful_requests = mdata.get("successful_requests", 0)
                m.failed_requests = mdata.get("failed_requests", 0)
                m.total_eval_count = mdata.get("total_eval_count", 0)
                m.total_prompt_eval_count = mdata.get("total_prompt_eval_count", 0)
                m.requests_with_actual_counts = mdata.get("requests_with_actual_counts", 0)
                m.total_eval_duration_ns = mdata.get("total_eval_duration_ns", 0)
                m.total_prompt_eval_duration_ns = mdata.get("total_prompt_eval_duration_ns", 0)
                m.total_load_duration_ns = mdata.get("total_load_duration_ns", 0)
                m.first_request_ns = mdata.get("first_request_ns", 0)
                m.last_request_ns = mdata.get("last_request_ns", 0)
                self.models[name] = m
        except Exception as e:
            logger.debug(f"Failed to load precision metrics: {e}")
