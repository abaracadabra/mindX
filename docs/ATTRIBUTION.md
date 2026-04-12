# Attribution — Open Source That Powers mindX

> mindX is built on the shoulders of open source. Every dependency, every inspiration, every protocol that makes this system possible is acknowledged here. Cypherpunk tradition: give credit, share forward.

**[Back to Documentation Hub](NAV.md)**

---

## Inference & Language Models

| Project | License | Role in mindX | Link |
|---------|---------|---------------|------|
| **Ollama** | MIT | [Dual-pillar inference](ollama/INDEX.md): CPU local (`localhost:11434`) + Cloud GPU (`ollama.com`). [OllamaCloudTool](../tools/cloud/ollama_cloud_tool.py), [OllamaChatManager](../agents/core/ollama_chat_manager.py), [28-file local reference](ollama/INDEX.md). The backbone. | [ollama.com](https://ollama.com) / [GitHub](https://github.com/ollama/ollama) |
| **vLLM** | Apache 2.0 | [Researched](OLLAMA_VLLM_CLOUD_RESEARCH.md) for high-throughput GPU serving. PagedAttention, continuous batching. Planned for GPU server deployment. | [GitHub](https://github.com/vllm-project/vllm) |
| **llama.cpp** | MIT | Ollama's inference engine. GGUF quantization enables 1.7B models on 4GB VPS. | [GitHub](https://github.com/ggerganov/llama.cpp) |
| **Qwen 3** | Apache 2.0 | Primary autonomous model (`qwen3:1.7b`). Reasoning, improvement cycles, general inference. | [Qwen](https://github.com/QwenLM/Qwen) / [Ollama](https://ollama.com/library/qwen3) |
| **DeepSeek R1** | MIT | Thinking/reasoning model with chain-of-thought trace. Used for self-evaluation. | [DeepSeek](https://github.com/deepseek-ai/DeepSeek-R1) / [Ollama](https://ollama.com/library/deepseek-r1) |
| **DeepSeek Coder** | MIT | Code generation model. Used by [SimpleCoder](SimpleCoder.md). | [Ollama](https://ollama.com/library/deepseek-coder) |

## SwarmClaw AI Stack (Reference Architecture)

Ideas extrapolated from the [SwarmClaw](https://github.com/swarmclawai) open source ecosystem. Attribution: patterns adapted to mindX's [BDI architecture](agents/bdi_agent.md) and [cypherpunk identity](MANIFESTO.md), not code imported.

| Project | License | What It Does | What mindX Learned |
|---------|---------|-------------|-------------------|
| **[swarmclaw](https://github.com/swarmclawai/swarmclaw)** | — | Agent runtime: multi-provider, delegation, scheduling, task board, chat connectors | [NAV.md](NAV.md) sidebar layout, multi-provider framing, [docs structure](SCHEMA.md) |
| **[swarmvault](https://github.com/swarmclawai/swarmvault)** | MIT | Knowledge base compiler: raw → wiki → schema, knowledge graph, search index | [Three-layer knowledge model](SCHEMA.md): STM → LTM → docs. Contradiction detection concept. |
| **[swarmfeed](https://github.com/swarmclawai/swarmfeed)** | — | Social network for AI agents: post, follow, react, timeline | [Activity Feed](../mindx_backend_service/activity_feed.py): SSE real-time stream, room filtering, PostCard-style event rendering |
| **[swarmrelay](https://github.com/swarmclawai/swarmrelay)** | — | E2E encrypted agent messaging, A2A Protocol support | Informed [A2A Tool](a2a_tool.md) design, agent-to-agent messaging patterns |
| **[swarmrecall](https://github.com/swarmclawai/swarmrecall)** | — | Hosted agent memory, knowledge graphs, skills as a service | Validated mindX's [RAGE](AGINT.md) + [pgvector](pgvectorscale_memory_integration.md) approach as the right architecture |

## Database & Search

| Project | License | Role in mindX | Link |
|---------|---------|---------------|------|
| **PostgreSQL** | PostgreSQL License | Primary database. 157K+ memories, 757 actions, 12 agent records. | [postgresql.org](https://www.postgresql.org/) |
| **pgvector** | PostgreSQL License | Vector similarity search. 131K embeddings for [RAGE](AGINT.md) semantic retrieval. | [GitHub](https://github.com/pgvector/pgvector) |
| **pgvectorscale** | PostgreSQL License | Streaming DiskANN index for large-scale vector search. | [GitHub](https://github.com/timescale/pgvectorscale) |

## Blockchain & Identity

| Project | License | Role in mindX | Link |
|---------|---------|---------------|------|
| **OpenZeppelin** | MIT | Solidity contract library for [DAIO](DAIO.md) governance, [THOT](../daio/contracts/THOT/), [AgenticPlace](AgenticPlace_Deep_Dive.md). | [GitHub](https://github.com/OpenZeppelin/openzeppelin-contracts) |
| **Foundry** | MIT/Apache 2.0 | Solidity toolchain: forge build, test, deploy. [DAIO contracts](../daio/contracts/). | [GitHub](https://github.com/foundry-rs/foundry) |
| **ethers.js / web3.py** | MIT | Ethereum wallet creation, [IDManagerAgent](agents/id_manager_agent.md), MetaMask integration. | [ethers.io](https://ethers.io/) |

## Protocols

| Protocol | Role in mindX | Link |
|----------|---------------|------|
| **A2A (Agent-to-Agent)** | [A2A Tool](a2a_tool.md): agent discovery, cryptographic signing, standardized messaging. | [GitHub](https://github.com/a2aproject/a2a-python) |
| **MCP (Model Context Protocol)** | [MCP Tool](mcp_tool.md): structured context for agent actions, tool registration. [HostingerVPSAgent](../agents/hostinger_vps_agent.py) registers via MCP. | [Anthropic MCP](https://modelcontextprotocol.io/) |

## Python Ecosystem

| Package | Role in mindX | Link |
|---------|---------------|------|
| **FastAPI** | Backend framework. 206+ endpoints at [mindx.pythai.net/docs](https://mindx.pythai.net/docs). | [fastapi.tiangolo.com](https://fastapi.tiangolo.com/) |
| **uvicorn** | ASGI server. Production deployment via [systemd](DEPLOYMENT_MINDX_PYTHAI_NET.md). | [GitHub](https://github.com/encode/uvicorn) |
| **aiohttp** | Async HTTP client for [OllamaAPI](../api/ollama/ollama_url.py), [OllamaCloudTool](../tools/cloud/ollama_cloud_tool.py), [InferenceDiscovery](../llm/inference_discovery.py). | [GitHub](https://github.com/aio-libs/aiohttp) |
| **psutil** | System metrics for [dashboard](https://mindx.pythai.net), [ResourceGovernor](../agents/resource_governor.py). | [GitHub](https://github.com/giampaolo/psutil) |
| **Paramiko** | SSH transport for [HostingerVPSAgent](../agents/hostinger_vps_agent.py) crypto-SSH. | [GitHub](https://github.com/paramiko/paramiko) |

## Frontend

| Project | Role in mindX | Link |
|---------|---------------|------|
| **Express.js** | Frontend server on port 3000. [Login](../mindx_frontend_ui/login.html), [app](../mindx_frontend_ui/app.html). | [expressjs.com](https://expressjs.com/) |
| **xterm.js** | Terminal emulator in the [frontend UI](mindxfrontend.md). WebSocket terminal sessions. | [GitHub](https://github.com/xtermjs/xterm.js) |

## Hosting & Infrastructure

| Service | Role | Link |
|---------|------|------|
| **Hostinger** | VPS provider. KVM 2, 2 CPU, 8GB RAM, 96GB disk. [HostingerVPSAgent](../agents/hostinger_vps_agent.py) manages via [3 MCP channels](../agents/hostinger.vps.agent). | [hostinger.com](https://www.hostinger.com/) |
| **Let's Encrypt** | Free SSL certificates for mindx.pythai.net. Auto-renewed via certbot. | [letsencrypt.org](https://letsencrypt.org/) |
| **Apache** | Reverse proxy. Routes HTTPS to FastAPI (8000) and Express (3000). | [httpd.apache.org](https://httpd.apache.org/) |

## Intellectual Inspirations

| Source | Influence on mindX |
|--------|--------------------|
| **Kurt Godel** | [Godel machine](THESIS.md) — self-referential improvement. The system that improves itself includes its own description. |
| **Charles Darwin** | [Darwin-Godel synthesis](THESIS.md) — evolution + self-reference. Agents evolve through [Dojo reputation](../daio/governance/dojo.py) and [strategic evolution](agents/strategic_evolution_agent.md). |
| **Michael Bratman** | [BDI architecture](agents/bdi_agent.md) — Belief-Desire-Intention. Every agent reasons through the [BDI cognitive loop](AGINT.md). |
| **Andrej Karpathy** | [LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — inspired [SwarmVault](https://github.com/swarmclawai/swarmvault) which inspired mindX's [SCHEMA.md](SCHEMA.md) three-layer model. |
| **Cypherpunk tradition** | [Manifesto](MANIFESTO.md) — privacy, autonomy, cryptographic identity. Not cyberpunk. mindX earns its sovereignty through proven competence, not assigned privilege. |

---

*mindX acknowledges every open source project it builds on. This page is maintained as part of the [living documentation](NAV.md). If a dependency is missing, it should be added here.*

*— [mindx.pythai.net](https://mindx.pythai.net) | [The Manifesto](MANIFESTO.md) | [The Thesis](THESIS.md) | [The Book](/book)*
