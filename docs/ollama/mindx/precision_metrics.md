# Precision Metrics — Scientific Token Tracking

> 18 decimal places. Actual values only. No estimation. Blockchain-grade precision.
>
> Live benchmark: [Latest Benchmark](../INDEX.md#latest-benchmark-2026-04-11) | Results: [`data/cloud_test_results.json`](../../../data/cloud_test_results.json) | Script: [`test_cloud_all_models.py`](../../../scripts/test_cloud_all_models.py)

## Design Principles

1. **ACTUAL over estimated** — use `eval_count` and `prompt_eval_count` from Ollama API
2. **NANOSECOND timing** — Ollama returns durations in nanoseconds natively
3. **DECIMAL accumulation** — Python `Decimal` (28-digit significand), no float drift
4. **ZERO estimation** — if Ollama doesn't return counts, record 0 rather than fabricate

## Why 18 Decimal Places

Same precision as blockchain token tracking:
- 1 ETH = 10^18 wei
- 1 token = 10^18 sub-tokens

This isn't cosmetic. Float accumulation loses precision:

```python
# Float fails
acc = 0.0
for _ in range(1_000_000):
    acc += 1e-18
print(acc)  # 9.999999999999843e-13 (WRONG)

# Decimal succeeds
from decimal import Decimal
acc = Decimal("0")
for _ in range(1_000_000):
    acc += Decimal("1e-18")
print(acc)  # 1.000000E-12 (EXACT)
```

Over millions of requests on a long-running system, float drift becomes measurable.

## Data Sources (from Ollama API)

Every response from `/api/chat` and `/api/generate` includes:

| Field | Type | Precision | Description |
|-------|------|-----------|-------------|
| `eval_count` | int | exact | Output tokens generated |
| `prompt_eval_count` | int | exact | Input tokens in prompt |
| `total_duration` | int | nanoseconds | Total request time |
| `load_duration` | int | nanoseconds | Model loading time |
| `prompt_eval_duration` | int | nanoseconds | Prompt evaluation time |
| `eval_duration` | int | nanoseconds | Token generation time |

All integers. All exact. All directly from the model runtime.

## What Was Removed

### Before (estimation)
```python
# api/ollama/ollama_url.py — OLD
estimated_tokens = len(prompt.split()) * 1.3 + len(content.split()) * 1.3
self.metrics.total_tokens += int(estimated_tokens)

# agents/core/ollama_chat_manager.py — OLD
response_length = len(response.split()) * 1.3
tokens_per_second = response_length / latency  # Rough estimate
```

### After (actual)
```python
# api/ollama/ollama_url.py — NEW
total_tokens = eval_count + prompt_eval_count  # exact integers from API
self.metrics.total_tokens += total_tokens

# Precision tracker records with Decimal at 18dp
precision_response = OllamaResponseMetrics.from_api_response(data, model=model)
self.precision_tracker.record(precision_response)

# agents/core/ollama_chat_manager.py — NEW
rd = self.ollama_api._last_response_data
tokens_per_second = rd.get("tokens_per_second", 0)  # from eval_count / eval_duration_ns
```

## Module: `llm/precision_metrics.py`

### Key Classes

**`OllamaResponseMetrics`** — Metrics from a single API response
```python
metrics = OllamaResponseMetrics.from_api_response(data, model="qwen3:1.7b")
metrics.total_tokens        # int: exact
metrics.tokens_per_second   # Decimal: from nanosecond timing
metrics.to_subtokens()      # {"total_tokens_subtokens": "53000000000000000000"}
```

**`PrecisionAccumulator`** — Decimal-precision running statistics
```python
acc = PrecisionAccumulator()
acc.record(Decimal("800.309315739536589275"))
acc.mean   # Decimal, not float
acc.min    # Decimal
acc.max    # Decimal
```

**`ModelPrecisionMetrics`** — Per-model precision tracking
```python
model_metrics.total_eval_count           # int: exact total output tokens
model_metrics.total_prompt_eval_count    # int: exact total input tokens  
model_metrics.aggregate_tokens_per_second  # Decimal: total_tokens / total_duration
model_metrics.actual_count_rate          # Decimal: fraction with real counts
```

**`PrecisionMetricsTracker`** — Central tracker (singleton in OllamaAPI)
```python
tracker = PrecisionMetricsTracker()
tracker.record(response_metrics)
tracker.global_total_tokens        # int: exact
tracker.global_tokens_per_second   # Decimal
tracker.summary()                  # Full 18dp JSON report
```

## Throughput Calculation

Two methods, both from actuals:

### Per-Request Rate
```
tokens_per_second = eval_count / (eval_duration_ns * 1e-9)
```
Calculated per response, accumulated via `PrecisionAccumulator.mean`.

### Aggregate Rate (preferred for scoring)
```
aggregate_tps = total_eval_count / (total_eval_duration_ns * 1e-9)
```
Total tokens divided by total generation time. More statistically robust — not affected by outlier requests.

## Integration Points

| Component | Before | After |
|-----------|--------|-------|
| `OllamaAPI.metrics.total_tokens` | int + 1.3x fallback | int, actual only |
| `OllamaAPI.precision_tracker` | (new) | PrecisionMetricsTracker |
| `OllamaAPI._last_response_data` | (new) | dict with eval_count, durations |
| `OllamaChatManager.tokens_per_second` | word_count * 1.3 / latency | eval_count / eval_duration |
| `OllamaChatManager.chat() return` | no token data | eval_count, prompt_eval_count |
| `HierarchicalModelScorer` | float EMA | can use Decimal via precision_tracker |
| `InferenceOptimizer` | float throughput | can use actual eval_count/duration |

## Persistence

Metrics persist to `data/metrics/precision_metrics.json` every 50 requests:
- Integer counters (exact)
- Nanosecond timestamps (exact)
- No Decimal serialization needed — integers are the source of truth

On load, accumulators (mean, min, max) are not restored — only totals. This is correct because per-request Decimal accumulators are session-level statistics, while totals are the durable scientific record.

## Verification

```python
from llm.precision_metrics import PrecisionMetricsTracker, OllamaResponseMetrics

tracker = PrecisionMetricsTracker()

# Simulate response
data = {"eval_count": 42, "prompt_eval_count": 11, "eval_duration": 52479709}
metrics = OllamaResponseMetrics.from_api_response(data, model="qwen3:1.7b")

assert metrics.total_tokens == 53
assert metrics.has_actual_counts == True
assert metrics.tokens_per_second > 0

tracker.record(metrics)
assert tracker.global_total_tokens == 53
print(tracker.summary())
```
