# Monitoring and Rate Control (Both Directions)

Whether mindX is **ingesting** (receiving data from clients), **providing inference** (calling Ollama/LLMs), or **services** (orchestration, memory, tools), **monitoring and rate control are essential in both directions**. This document defines **actual network and data metrics** in scientific form (SI or standard units) and where they apply.

---

## 1. Both directions

| Direction | Role | Monitoring | Rate control |
|-----------|------|------------|--------------|
| **Inbound** | Clients → mindX (ingestion, agent/call, ollama/ingest) | Request latency, payload size, throughput | Per-client or global req/s, req/min |
| **Outbound** | mindX → Ollama / LLM providers (inference) | Latency, tokens, throughput, errors | RPM, RPH, token bucket (see `llm/rate_limiter.py`) |

Both directions must be measured and, where configured, limited so that ingestion, inference, and services stay within capacity and quotas.

---

## 2. Scientific network and data metrics

All metrics use explicit units. Prefer SI or widely used standards.

### 2.1 Time

| Symbol | Unit | Description |
|--------|------|-------------|
| \(t\) | s (second) | Wall-clock time |
| \(T_{\mathrm{lat}}\) | s or ms | Latency (request start → response end) |
| \(T_{\mathrm{wait}}\) | ms | Wait time in rate limiter before sending |

- **Latency:** Report in **seconds (s)** or **milliseconds (ms)**. APIs: `average_latency_ms`, `latency_ms`, `total_duration` (ns → convert to s or ms).
- **Throughput (time-based):** Requests per second **req/s** or per minute **req/min (RPM)**.

### 2.2 Data volume

| Symbol | Unit | Description |
|--------|------|-------------|
| \(B_{\mathrm{in}}\) | byte | Request body size (payload in) |
| \(B_{\mathrm{out}}\) | byte | Response body size (payload out) |
| \(N_{\mathrm{tok}}\) | 1 (dimensionless) | Token count (input + output) |

- **Payload sizes:** Report in **bytes (B)**. Request/response body length in bytes.
- **Tokens:** Count as integers; report **tokens** or **tokens/s** for throughput.

### 2.3 Rate (throughput)

| Quantity | Unit | Description |
|----------|------|-------------|
| Request rate (inbound) | req/s, req/min | Incoming API requests per unit time |
| Request rate (outbound) | req/min (RPM), req/h (RPH) | Outgoing calls to Ollama/LLM per unit time |
| Token rate | tokens/s, tokens/min (TPM) | Tokens consumed or generated per unit time |
| Data rate | byte/s (B/s), kB/s | Payload bytes per unit time |

### 2.4 Counts and ratios

| Quantity | Unit | Description |
|----------|------|-------------|
| Total requests | 1 | Cumulative count |
| Success / failure | 1 | Counts or ratio (dimensionless) |
| Rate limit hits | 1 | Count of requests delayed or blocked by limiter |
| Utilization | 0–1 or % | e.g. token bucket utilization, queue depth / max |

---

## 3. Where metrics are collected

### 3.1 Inbound (clients → mindX)

- **Middleware:** `mindx_backend_service/inbound_metrics.py` — `InboundMetricsMiddleware` records per-request latency \(T_{\mathrm{lat}}\) (ms), request body size \(B_{\mathrm{in}}\) (bytes), response body size \(B_{\mathrm{out}}\) (bytes). Optional inbound rate limit (req/min) returns 429 when exceeded.
- **Aggregates:** `get_metrics(window_s)` returns `total_requests`, `total_latency_ms`, `average_latency_ms`, `total_request_bytes`, `total_response_bytes`, `requests_per_minute` (in window), `rate_limit_rejects`, `latency_p50_ms`, `latency_p90_ms`, `latency_p99_ms`.
- **API:** `GET /api/monitoring/inbound` — returns `inbound_metrics` (scientific units) and `inbound_rate_limit` (requests_per_minute, window_s). Enable limit via `set_inbound_rate_limit(requests_per_minute, window_s)`.

### 3.2 Outbound (mindX → Ollama / LLMs)

- **Per provider (e.g. `api/ollama/ollama_url.py`):** `total_requests`, `successful_requests`, `failed_requests`, `rate_limit_hits`, `total_tokens`, `average_latency_ms`, `rate_limits.rpm`, `rate_limits.tpm`.
- **Rate limiter (`llm/rate_limiter.py`):** `wait_time_ms`, `wait_time_p50/p90/p99`, `token_utilization`, `requests_per_minute`, `requests_per_hour`; `get_metrics()` returns these.
- **Units:** Latency in **ms**, tokens as **count**, rate as **req/min** and **req/h**.

### 3.3 Services (internal)

- **PerformanceMonitor (`agents/monitoring/performance_monitor.py`):** `total_calls`, `successful_calls`, `failed_calls`, `total_latency_ms`, `latencies_ms`, `total_prompt_tokens`, `total_completion_tokens`, `total_cost`.
- Use the same units: **ms** for latency, **tokens** for counts, **USD** or equivalent for cost where applicable.

---

## 4. API and config

- **Rate limiter API:** `llm/rate_limiter.py` — `RateLimiter.get_metrics()`, `DualLayerRateLimiter.get_metrics()`, `HourlyRateLimiter.get_metrics()`; `api/llm_routes.py` — rate limit status and update endpoints.
- **Provider YAML:** `models/*.yaml` — `rate_limits` (rpm, rph) and optional `quota` (total_calls, period_days) for even distribution.
- **Factory config:** `data/config/llm_factory_config.json` — `rate_limit_profiles` (rpm, rph, strict, very_strict, etc.).

---

## 5. Summary

- **Ingestion, inference, and services:** Monitor and apply rate control in **both directions** (inbound and outbound).
- **Scientific metrics:** Use **s or ms** for time, **bytes** for payload size, **req/s or req/min** for request rate, **tokens** and **tokens/s or TPM** for token throughput, and **dimensionless** counts/ratios where appropriate.
- **Actual metrics:** Exposed via `get_metrics()` on limiters and API clients, PerformanceMonitor, and optional inbound middleware; persist or export as needed for dashboards and alerts.
