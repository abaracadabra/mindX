# Ollama Bootstrap (No Inference Connection)

When **no inference connection is found** (no working cloud API and no local Ollama), mindX can **install and configure a working Ollama** on Linux and **continue self-improvement from core**. This folder holds the scripts and logic for that scenario.

## Quick: Install Ollama on Linux (aion.sh)

```bash
# From mindX project root
chmod +x llm/ollama_bootstrap/aion.sh
./llm/ollama_bootstrap/aion.sh

# Pull a specific model and start serve in background (e.g. headless)
./llm/ollama_bootstrap/aion.sh --pull-model llama3.2 --serve
```

**What aion.sh does:**

1. Checks if Ollama is already installed; if not, runs the **official install**:  
   `curl -fsSL https://ollama.com/install.sh | sh`
2. Optionally starts `ollama serve` in the background (`--serve`).
3. Waits for the API at `http://127.0.0.1:11434` (or `$OLLAMA_HOST`).
4. Pulls a default model (e.g. `llama3.2`) so mindX has a working model.

After this, mindX uses `models/ollama.yaml` **fallback_url** (`http://localhost:11434`) and can continue inference and self-improvement.

## Manual install (Linux)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve   # if not running as a service
ollama pull llama3.2
```

## Docker

Use the official image:

```bash
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
docker exec -it ollama ollama pull llama3.2
```

## Model library (examples)

| Model        | Size   | Command              |
|-------------|--------|----------------------|
| Llama 3.2   | 2.0GB  | `ollama run llama3.2` |
| Llama 3.2 1B| 1.3GB  | `ollama run llama3.2:1b` |
| Gemma 3 1B  | 815MB  | `ollama run gemma3:1b` |
| Mistral 7B  | 4.1GB  | `ollama run mistral` |

More: [ollama.com/library](https://ollama.com/library)

## REST API (for mindX)

```bash
# Generate
curl http://localhost:11434/api/generate -d '{"model":"llama3.2","prompt":"Why is the sky blue?"}'

# Chat
curl http://localhost:11434/api/chat -d '{"model":"llama3.2","messages":[{"role":"user","content":"why is the sky blue?"}]}'
```

See [api/ollama/ollamaapi.md](../../api/ollama/ollamaapi.md) and [docs.ollama.com/api](https://docs.ollama.com/api).

## When mindX uses this (no inference connection)

1. **Detection:** All providers fail (no API key, rate limit, or unreachable) and Ollama at primary/fallback URL is not reachable.
2. **Bootstrap:** mindX can invoke `llm/ollama_bootstrap/aion.sh` (Linux) or prompt the operator to run it.
3. **Config:** After install, `models/ollama.yaml` **fallback_url** `http://localhost:11434` is used; no code change needed.
4. **Continue:** `ModelRegistry.generate_with_fallback` or explicit Ollama handler then succeeds, and self-improvement continues from core.

See [RESILIENCE.md](../RESILIENCE.md) for the full resilience design and the “No inference connection” section.

## Libraries

- **ollama-python:** [github.com/ollama/ollama-python](https://github.com/ollama/ollama-python) — `pip install ollama`
- **ollama-js:** [github.com/ollama/ollama-js](https://github.com/ollama/ollama-js) — `npm i ollama`

## Community

- [Discord](https://discord.gg/ollama)
- [Reddit](https://reddit.com/r/ollama)
