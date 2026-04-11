# Cloud Rate Limiting Strategy

> Maximize free tier usage without triggering blocks. Sane pacing for sustainable operation.
>
> Access methods: [How Cloud Works Without an API Key](../INDEX.md#how-cloud-works-without-an-api-key) | Benchmark: [Latest Results](../INDEX.md#latest-benchmark-2026-04-11) | Precision: [`llm/precision_metrics.py`](../../../llm/precision_metrics.py)

## Free Tier Constraints

| Constraint | Limit | Reset |
|-----------|-------|-------|
| Session usage | Light | Every 5 hours |
| Weekly usage | Light | Every 7 days |
| Concurrent cloud models | 1 | — |

"Light usage" is not precisely documented. The strategy below is designed conservatively.

## Design Principles

1. **Spread requests over time** — avoid bursts that signal automation
2. **Jitter all intervals** — deterministic timing is a bot fingerprint
3. **Track quota usage** — stop before limits, don't wait for 429s
4. **Degrade gracefully** — fall back to local when cloud is throttled
5. **Respect the service** — this is a free tier, not an exploit target

## Precision Token Tracking

The cloud rate limiter uses **actual token counts** from the Ollama API response,
not estimation. Token tracking uses `Decimal` at 18 decimal places via
`llm/precision_metrics.py` — see that module for the full scientific tracking system.

```python
# After each cloud request, record ACTUAL tokens from response:
# data["eval_count"] + data["prompt_eval_count"] → exact integers
# data["eval_duration"] → nanoseconds (10^-9 second precision)
# Never use word-count * 1.3 estimation
```

## Rate Limiter Implementation

```python
import asyncio
import time
import random
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class CloudQuotaTracker:
    """Track cloud usage against estimated free tier limits."""
    
    # Conservative estimates for free tier
    max_requests_per_session: int = 50       # ~50 requests per 5-hour session
    max_requests_per_week: int = 500         # ~500 requests per week
    max_tokens_per_session: int = 100_000    # ~100K tokens per session
    
    # Current counters
    session_requests: int = 0
    session_tokens: int = 0
    weekly_requests: int = 0
    
    # Timing
    session_start: float = field(default_factory=time.time)
    week_start: float = field(default_factory=time.time)
    last_request: float = 0.0
    
    # Backoff state
    consecutive_429s: int = 0
    backoff_until: float = 0.0
    
    def _reset_session_if_needed(self):
        """Reset session counters every 5 hours."""
        if time.time() - self.session_start > 5 * 3600:
            self.session_requests = 0
            self.session_tokens = 0
            self.session_start = time.time()
            self.consecutive_429s = 0
    
    def _reset_week_if_needed(self):
        """Reset weekly counters every 7 days."""
        if time.time() - self.week_start > 7 * 86400:
            self.weekly_requests = 0
            self.week_start = time.time()
    
    def can_make_request(self) -> tuple[bool, str]:
        """Check if a cloud request is allowed."""
        self._reset_session_if_needed()
        self._reset_week_if_needed()
        
        now = time.time()
        
        # Check backoff
        if now < self.backoff_until:
            wait = self.backoff_until - now
            return False, f"Backing off for {wait:.0f}s after rate limit"
        
        # Check session limit (leave 10% buffer)
        if self.session_requests >= self.max_requests_per_session * 0.9:
            remaining = 5 * 3600 - (now - self.session_start)
            return False, f"Session quota near limit. Resets in {remaining/60:.0f}m"
        
        # Check weekly limit (leave 10% buffer)
        if self.weekly_requests >= self.max_requests_per_week * 0.9:
            remaining = 7 * 86400 - (now - self.week_start)
            return False, f"Weekly quota near limit. Resets in {remaining/3600:.0f}h"
        
        return True, "OK"
    
    def record_request(self, eval_count: int = 0, prompt_eval_count: int = 0):
        """Record a successful request with ACTUAL token counts from Ollama API."""
        self.session_requests += 1
        self.session_tokens += eval_count + prompt_eval_count  # exact integers, not estimates
        self.weekly_requests += 1
        self.last_request = time.time()
        self.consecutive_429s = 0
    
    def record_rate_limit(self):
        """Record a 429 response. Exponential backoff."""
        self.consecutive_429s += 1
        # Backoff: 30s, 60s, 120s, 300s, 600s
        backoff = min(30 * (2 ** (self.consecutive_429s - 1)), 600)
        # Add jitter: +/- 20%
        jitter = backoff * random.uniform(-0.2, 0.2)
        self.backoff_until = time.time() + backoff + jitter
    
    @property
    def session_utilization(self) -> float:
        """Fraction of session quota used (0.0 - 1.0)."""
        return self.session_requests / self.max_requests_per_session
    
    @property
    def weekly_utilization(self) -> float:
        """Fraction of weekly quota used (0.0 - 1.0)."""
        return self.weekly_requests / self.max_requests_per_week


class OllamaCloudRateLimiter:
    """
    Rate limiter for Ollama cloud free tier.
    
    Strategy: Space requests to maximize useful throughput while staying
    well within limits. Uses adaptive pacing — slows down as quotas fill.
    """
    
    def __init__(self):
        self.quota = CloudQuotaTracker()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> tuple[bool, str]:
        """
        Acquire permission to make a cloud request.
        Returns (allowed, reason).
        If allowed, also applies minimum spacing.
        """
        async with self._lock:
            allowed, reason = self.quota.can_make_request()
            if not allowed:
                return False, reason
            
            # Adaptive pacing based on quota utilization
            min_interval = self._calculate_interval()
            
            elapsed = time.time() - self.quota.last_request
            if elapsed < min_interval:
                wait = min_interval - elapsed
                # Add small jitter
                wait += random.uniform(0, wait * 0.3)
                await asyncio.sleep(wait)
            
            return True, "OK"
    
    def _calculate_interval(self) -> float:
        """
        Adaptive interval: faster when quota is fresh, slower as it fills.
        
        At 0% utilization:  ~3s between requests (20/min)
        At 50% utilization: ~6s between requests (10/min)
        At 80% utilization: ~15s between requests (4/min)
        At 90%+ utilization: ~30s between requests (2/min)
        """
        util = max(self.quota.session_utilization, self.quota.weekly_utilization)
        
        if util < 0.3:
            return 3.0    # Fresh quota — reasonable pace
        elif util < 0.5:
            return 6.0    # Half used — slow down
        elif util < 0.8:
            return 15.0   # Getting tight — conserve
        else:
            return 30.0   # Near limit — minimal requests
    
    def record_success(self, tokens: int = 0):
        """Record successful request."""
        self.quota.record_request(tokens)
    
    def record_rate_limit(self):
        """Record 429 error — trigger backoff."""
        self.quota.record_rate_limit()
    
    @property
    def status(self) -> dict:
        """Current rate limiter status."""
        return {
            "session_requests": self.quota.session_requests,
            "session_max": self.quota.max_requests_per_session,
            "session_utilization": f"{self.quota.session_utilization:.1%}",
            "weekly_requests": self.quota.weekly_requests,
            "weekly_max": self.quota.max_requests_per_week,
            "weekly_utilization": f"{self.quota.weekly_utilization:.1%}",
            "current_interval": f"{self._calculate_interval():.1f}s",
            "backing_off": time.time() < self.quota.backoff_until,
        }
```

## Usage with mindX

```python
# Initialize once at startup
cloud_limiter = OllamaCloudRateLimiter()

async def cloud_chat(model: str, messages: list, **kwargs) -> dict:
    """Rate-limited cloud chat."""
    allowed, reason = await cloud_limiter.acquire()
    if not allowed:
        # Fall back to local model
        return await local_chat("qwen3:1.7b", messages, **kwargs)
    
    try:
        response = await make_cloud_request(model, messages, **kwargs)
        tokens = response.get("eval_count", 0) + response.get("prompt_eval_count", 0)
        cloud_limiter.record_success(tokens)
        return response
    except RateLimitError:
        cloud_limiter.record_rate_limit()
        # Fall back to local
        return await local_chat("qwen3:1.7b", messages, **kwargs)
```

## Request Budget Planning

### Free Tier Budget (Conservative)

| Timeframe | Requests | Tokens (est.) |
|-----------|----------|---------------|
| Per 5h session | ~50 | ~100K |
| Per day | ~150 (3 sessions) | ~300K |
| Per week | ~500 | ~1M |

### Agent Budget Allocation

| Agent | Requests/Day | Priority | Cloud Model |
|-------|-------------|----------|-------------|
| BlueprintAgent | 10-20 | High | qwen3-coder-next |
| AuthorAgent | 5-10 | Medium | qwen3.5:27b |
| Heavy reasoning | 5-10 | Medium | deepseek-v3.2 |
| Emergency/ad-hoc | 10-20 | Low | Any |
| **Total** | **30-60** | | |

This leaves ~60% of daily budget unused as buffer for spikes.

### Timing Strategy

```
Session 1: 00:00-05:00 UTC — Autonomous improvement (~20 requests)
Session 2: 08:00-13:00 UTC — Interactive use (~30 requests)  
Session 3: 16:00-21:00 UTC — Background tasks (~15 requests)

Total: ~65/day, well within ~150/day estimate
```

## Integration with Existing Rate Limiter

The `DualLayerRateLimiter` in `llm/rate_limiter.py` can be extended for cloud:

```python
# In llm_factory_config.json, add:
{
    "provider_rate_limits": {
        "ollama_cloud": {
            "rpm": 10,
            "rph": 150,
            "max_retries": 2,
            "initial_backoff_s": 5.0
        }
    }
}
```

The key difference from local Ollama (1000 RPM) is that cloud should be **10 RPM** with much longer backoff.
