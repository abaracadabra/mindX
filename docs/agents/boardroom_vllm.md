# Boardroom × vLLM — true continuous batching for 8 concurrent members

The boardroom can route through **vLLM** for genuine continuous-batching inference: all 8 members in flight on one model, each getting full attention at the token-level (the model "takes turns" generating one token per request per step, finishing roughly together rather than sequentially). This is what gpt-oss:120b-cloud does upstream; vLLM lets you self-host the same pattern on any GPU.

## Selector

```
BOARDROOM_INFERENCE_BACKEND   = ollama | vllm | auto      (default: auto)
BOARDROOM_VLLM_BASE_URL       = http://localhost:8001/v1  (default)
BOARDROOM_VLLM_MODEL          = mistralai/Mistral-7B-Instruct-v0.3
```

| Mode | Behaviour |
|---|---|
| `auto` | Try vLLM first; fall through to Ollama if no server reachable. **Best for live operations** — you can deploy vLLM later without code changes. |
| `vllm` | vLLM only. No Ollama fallback. Use when you want to verify a vLLM deployment exclusively. |
| `ollama` | Skip the vLLM check entirely. Default behaviour pre-vLLM. |

Verify the active backend:

```bash
curl https://mindx.pythai.net/insight/boardroom/health?h=true | grep vLLM
# vLLM (auto):      ✓ Mistral-7B-Instruct-v0.3 @ http://localhost:8001/v1
# or
# vLLM (auto):      ○ no server @ http://localhost:8001/v1 — Ollama in use
```

## Three deploy paths

### A. Cloud GPU (Modal, RunPod, Lambda) — easiest, $0.30–0.80/hr

Recommended starting point. A single A10G (24 GB) runs Mistral-7B-Instruct at 50–100 tok/s with vLLM continuous batching, comfortably handling 8 concurrent boardroom prompts.

**Modal** (Python-only setup, no Docker):

```python
# modal_vllm.py
import modal
app = modal.App("mindx-boardroom-vllm")
image = modal.Image.debian_slim().pip_install(
    "vllm==0.6.4", "fastapi", "uvicorn"
)

@app.function(image=image, gpu="A10G", timeout=3600, allow_concurrent_inputs=8)
@modal.web_endpoint(method="POST", custom_domains=["vllm.example.com"])
def serve():
    from vllm.entrypoints.openai.api_server import run_server
    run_server(model="mistralai/Mistral-7B-Instruct-v0.3", port=8001, host="0.0.0.0")
```

`modal deploy modal_vllm.py` → public URL → set as `BOARDROOM_VLLM_BASE_URL`.

**RunPod**: spin up an A10G pod with the prebuilt vLLM template (`vllm/vllm-openai:latest`), expose port 8000. Set `BOARDROOM_VLLM_BASE_URL=https://<pod>:8000/v1`.

### B. LAN GPU server (10.0.0.155 mentioned in CLAUDE.md)

If the GPU server has a CUDA-capable card and reaches the VPS, run vLLM there:

```bash
# On the LAN GPU host
pip install vllm
python -m vllm.entrypoints.openai.api_server \
    --model mistralai/Mistral-7B-Instruct-v0.3 \
    --port 8001 \
    --host 0.0.0.0 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.9

# On the VPS, point boardroom at it (must be reachable from VPS):
sudo systemctl edit mindx
#   Environment="BOARDROOM_VLLM_BASE_URL=http://10.0.0.155:8001/v1"
#   Environment="BOARDROOM_VLLM_MODEL=mistralai/Mistral-7B-Instruct-v0.3"
sudo systemctl restart mindx
```

The VPS doesn't reach 10.0.0.155 directly today (we tested). If your GPU host is private, expose it through the same proxy mindx.pythai.net uses, or set up a tailscale/wireguard mesh.

### C. vLLM CPU on the VPS — works but slow

For full self-hosting without a GPU. ~1–3 tok/s on this 8 GB VPS with `Mistral-7B-Instruct-q4`. Slower than Ollama Cloud but free.

```bash
# On the VPS
ssh root@168.231.126.58
sudo -u mindx bash -c 'cd /home/mindx/mindX && \
    .mindx_env/bin/pip install vllm[cpu] && \
    VLLM_TARGET_DEVICE=cpu .mindx_env/bin/python -m vllm.entrypoints.openai.api_server \
        --model microsoft/Phi-3.5-mini-instruct \
        --port 8001 --host 127.0.0.1 \
        --max-model-len 8192 --max-num-seqs 8'
```

For mindX backend to pick it up: leave `BOARDROOM_VLLM_BASE_URL` at default (`http://localhost:8001/v1`) and switch model name to a CPU-realistic one (`microsoft/Phi-3.5-mini-instruct`, ~3.8B params, runs on CPU).

`agents/vllm_agent.py:182` has a CPU-build path already wired (`VLLM_TARGET_DEVICE=cpu`).

## What you get

With any of the three paths plus `BOARDROOM_INFERENCE_BACKEND=auto` and `MAX_CONCURRENT=8`:

- All 8 members fire simultaneously into one vLLM endpoint
- vLLM's continuous batching interleaves token generation across the 8 prompts
- Each member's generation runs to its own `num_predict` budget without blocking the others
- A typical 7-vote session completes in ~3–5 seconds wall (vs ~20s with Ollama Cloud sequential per-soldier)

## Comparison vs current

| | Ollama Cloud (today) | vLLM (after deploy) |
|---|---|---|
| Concurrency | 8 prompts → 1 cloud model | 8 prompts → 1 self-hosted model |
| Continuous batching | upstream (cloud handles it) | local, transparent |
| Cost | free tier (~50 req/5h) | ~$0.50/h GPU or $0/free CPU |
| Self-hosted | no | yes |
| Per-soldier model diversity | no (one shared model) | yes (run multiple vLLM instances on different ports/models) |
| Auth dependency | `ollama signin` periodically | none |

For everyday operation, Ollama Cloud is fine. For sovereignty (no external dependency, full self-host), commit-history audit (every prompt processed under your own GPU), or per-seat model diversity (CISO on a safety-aligned model, CFO on a code model), vLLM is the right move.

## Per-seat model diversity (advanced)

Once you have GPU headroom, run multiple vLLM instances on different ports:

```
:8001 → Mistral-7B-Instruct-v0.3   (general, all soldiers default)
:8002 → google/gemma-2-9b-it        (CFO — structured analysis)
:8003 → microsoft/Phi-3.5-MoE       (CTO — architecture depth)
:8004 → meta-llama/Llama-Guard-2-8B (CISO — safety-aligned)
```

Then in `daio/agents/agent_map.json` (already has per-soldier provider routing) override each soldier's vLLM endpoint. The `_query_soldier` path can be extended to read `agent_map.json` per-seat and pick the right vLLM URL.

This is the substrate for the war-council 13-seat roster too — each seat can run on the model that suits its character.

## Verification

After deploy:

```bash
# 1. confirm vLLM is reachable from the boardroom side
curl http://localhost:8001/v1/models           # should list your model

# 2. confirm boardroom sees it
curl https://mindx.pythai.net/insight/boardroom/health?h=true | grep vLLM
#   vLLM (auto):      ✓ mistralai/Mistral-7B-Instruct-v0.3 @ http://localhost:8001/v1

# 3. force vLLM-only and convene a session
sudo systemctl edit mindx
#   Environment="BOARDROOM_INFERENCE_BACKEND=vllm"
sudo systemctl restart mindx

curl -X POST "https://mindx.pythai.net/boardroom/convene?directive=Test"

# 4. inspect the persisted session — provider field should read vllm/<model>
curl https://mindx.pythai.net/insight/boardroom/recent | jq '.sessions[0].votes[].provider'
```

## Related

- [`llm/vllm_handler.py`](../../llm/vllm_handler.py) — OpenAI-compatible client, already wired
- [`agents/vllm_agent.py`](../../agents/vllm_agent.py) — lifecycle: detect, build (CPU from source), serve, stop
- [`scripts/start_vllm_embed.sh`](../../scripts/start_vllm_embed.sh) — embed-only starter script
- [`docs/ollama/cloud/cloud.md`](../ollama/cloud/cloud.md) — current Ollama Cloud routing
- [`docs/agents/boardroom_members.md`](boardroom_members.md) — the three-file role architecture this routes through
