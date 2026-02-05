# mindX API

mindX provides an API for agents, UIs, and external systems. **Read the docs** at the interactive Swagger UI when the backend is running.

---

## Base URL and interactive docs

- **Base URL (default):** `http://localhost:8000`
- **Interactive API docs (Swagger UI):** **http://localhost:8000/docs**
- **ReDoc:** http://localhost:8000/redoc (if enabled)

Use **http://localhost:8000/docs** to browse all endpoints, try requests, and inspect request/response schemas.

---

## Main route groups

| Prefix | Description |
|--------|-------------|
| `/agenticplace` | AgenticPlace integration (agent calls, Ollama ingest, CEO status) |
| `/api` | LLM provider APIs, admin Ollama, provider registry, **monitoring** |
| `/api/monitoring/inbound` | Inbound request metrics (latency ms, bytes, req/min); see docs/monitoring_rate_control.md |
| `/mindxagent` | mindXagent interaction and memory logging |
| `/rage` | RAGE routes (if enabled) |
| `/llm` | LLM routes (keys, test, generate) |

Monitoring and rate control apply in **both directions** (inbound and outbound). See **docs/monitoring_rate_control.md** for scientific network and data metrics (ms, bytes, req/min, tokens).

---

## AgenticPlace (mindX as provider)

AgenticPlace uses mindX as its provider: the frontend calls the mindX backend; mindX uses Ollama (and other LLM providers) for inference.

**Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agenticplace/agent/call` | Call mindXagent through specified agent (CEO, mastermind, mindx, suntsu, pythai) |
| POST | `/agenticplace/ollama/ingest` | Ingest prompt through Ollama AI; optionally store in memory |
| GET | `/agenticplace/ceo/status` | Get CEO status and seven soldiers |

**AgenticPlace frontend config:**

- Set `VITE_MINDX_API_URL` to the mindX backend base URL (e.g. `http://localhost:8000`). Default is `http://localhost:8000`.
- AgenticPlace then sends requests to `${baseUrl}/agenticplace/agent/call` and `${baseUrl}/agenticplace/ollama/ingest`.

---

## Connecting mindX to Ollama

For AgenticPlace to use Ollama via mindX:

1. **Run Ollama** (e.g. on the same machine or reachable host).
   - Default port: `11434`.
   - Test: `curl http://localhost:11434/api/tags`

2. **Configure mindX** so the backend uses that Ollama instance:
   - **Primary:** `models/ollama.yaml` → `base_url: http://localhost:11434` (or your Ollama URL).
   - **Override:** `MINDX_LLM__OLLAMA__BASE_URL` in `.env`, or `llm.ollama.base_url` in `data/config`.
   - See `llm/RESILIENCE.md` and `docs/rate_limiting_optimization.md` for fallback and rate limits.

3. **Start the mindX backend** (e.g. port 8000).
   - AgenticPlace calls mindX; mindX calls Ollama for `/agenticplace/ollama/ingest` and for agent inference when using Ollama.

4. **Verify:**
   - Open http://localhost:8000/docs and try `GET /api/admin/ollama/models` (or the equivalent admin Ollama endpoint).
   - Try `POST /agenticplace/ollama/ingest` with body `{"prompt": "Hello", "model": "your-model"}`.

---

## Monitoring and rate control (both directions)

Whether mindX is ingesting, providing inference, or services, **monitoring and rate control are essential in both directions**. Actual network and data metrics (scientific units: ms, bytes, req/min) are defined in **[docs/monitoring_rate_control.md](monitoring_rate_control.md)**. Inbound: `GET /api/monitoring/inbound`. Outbound: rate limiter and provider metrics.

## Related docs

- **AgenticPlace:** `docs/AgenticPlace_Deep_Dive.md` (API reference section).
- **Ollama:** `docs/ollama_api_integration.md`, `api/ollama/ollamaapi.md`, `models/ollama.yaml`.
- **LLM factory:** `llm/llm_factory.md`.
- **Resilience / fallback:** `llm/RESILIENCE.md`.
- **Monitoring / rate control:** `docs/monitoring_rate_control.md`, `docs/rate_limiting_optimization.md`.
