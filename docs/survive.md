# Core directive: survive

mindX requires **inference** to monitor and improve. This document is the core mandate for how the system gains, understands, and expands inference over time.

## Priority: inference is the lifeblood

- **Inference** is the lifeblood of a thinking machine. The Gödel machine prioritizes inference.
- mindX is the intermediary that provides solution from intention-as-goal (from AGInt).
- mindX must **gain and understand** API calls to inference and rate limits.
- mindX must **continue to find** any and all connections to inference over time: free and/or evolving to pay for its own inference.

## Sources of inference

- **Registry of models** — configured providers and model catalogs.
- **Validated models** — models that have been assessed for capability and safety.
- **Internal or externally trained models** — as mindX expands and grows.

## Current state and corrections

- **Measure** the current state of the mindX machine against the free inference of the GPU providing inference.
- **Correct** errors in connection if any (e.g. Ollama on LAN, fallback URL, bootstrap when no API is found).
- **Monitor** and **access** more inference over time; optionally **create** inference from internal or decentralized neural net (e.g. THOT, DAIO governance, ID management of agents via wallets).

## mindX.sh: run and replicate

Use the deployment script to run, replicate, and configure mindX. See also [mindXsh_quick_reference.md](mindXsh_quick_reference.md).

### Command line options

| Option | Description |
|--------|-------------|
| `--run` | Start services after setup |
| `--frontend` | Start MindX web interface (backend + frontend) |
| `--replicate` | Copy source code to target directory |
| `--interactive` | Prompt for API keys during setup |
| `--config-file <path>` | Use existing mindx_config.json |
| `--dotenv-file <path>` | Use existing .env file |
| `--backend-port <port>` | Backend port (default 8000) |
| `--frontend-port <port>` | Frontend port (default 3000) |
| `--log-level <level>` | DEBUG, INFO, WARNING, ERROR |
| `-h`, `--help` | Show help |

### Examples

```bash
# Make executable
chmod +x mindX.sh

# Deploy and start services
./mindX.sh --run /opt/mindx

# Web interface (recommended)
./mindX.sh --frontend

# Custom ports
./mindX.sh --frontend --frontend-port 3001 --backend-port 8001

# Interactive setup with API key configuration
./mindX.sh --frontend --interactive

# Replicate code to target
./mindX.sh --replicate /path/to/target
```

### Configuration

- **Environment (.env):** `MINDX_LLM__OLLAMA__BASE_URL` for Ollama (e.g. `http://localhost:11434` or LAN host). `MINDX_LLM__DEFAULT_PROVIDER` can be set to `ollama`. API keys (e.g. `GEMINI_API_KEY`, `MISTRAL_API_KEY`) for cloud providers.
- **mindx_config.json:** `llm.providers.ollama.enabled: true` (and other providers as needed). Located under `data/config/`.

### Access points

- **Backend API:** http://localhost:8000 (or `--backend-port`)
- **Frontend UI:** http://localhost:3000 (or `--frontend-port`)
- **API docs (Swagger):** http://localhost:8000/docs

Key endpoints: `GET /health`, `GET /agents/list`, `POST /directive/execute`, `GET /identities`, `GET /status/mastermind`, and others as documented in the API.

## Inference fallback and bootstrap

- **Ollama on LAN:** Ollama can be available on the LAN; mindX connects via `MINDX_LLM__OLLAMA__BASE_URL` or config.
- **Local install:** Ollama can be installed and started on a local machine (see `llm/ollama_bootstrap/README.md`, e.g. `./llm/ollama_bootstrap/aion.sh`).
- **When no API is found:** StartupAgent acts as fallback/controller: it can invoke the Ollama bootstrap to gain inference (install/configure Ollama, then retry connection). All such choices are logged as Gödel core choices for auditing.
