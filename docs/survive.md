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

## Replication: recovery before risk

A Gödel machine that rewrites itself must be able to survive a bad rewrite.
`./mindX.sh --replicate` was conceived for exactly this: **duplicate mindX
before testing a milestone, so a catastrophic "upgrade" can be rolled back to
the last-known-good self.** Replication is not vanity scaling — it is the
safety rail under self-modification. The rule of survival is: *never test an
upgrade you cannot undo.*

### The recovery substrate, today

mindX already has a lightweight replica-of-record: **`backup_agent` git-commits
and pushes before every shutdown** (a shutdown is a restart) with
`Pre-shutdown backup: <reason>`. The public git history is therefore a
continuous, append-only snapshot lineage — any prior self is one `git checkout`
away. This is the minimum viable replication: cheap, public, and always on.

- These backup commits are **routine**, not milestones — `github.awareness`
  filters `Pre-shutdown backup:` / merge / version-bump commits out of the
  milestone chronicle (`AuthorAgent.is_routine_commit`). Backups protect; only
  substantive pushes are recognized as milestones.
- A **milestone is the natural checkpoint to replicate before**: when
  AuthorAgent recognizes a worthy change (see [`MILESTONES.md`](MILESTONES.md)),
  that is precisely the moment to snapshot the running self before the next
  risky step.

### Why mindX has not been replicating (and what changes it)

Live replication has been constrained by **space** on the 2-core/8 GB VPS — a
full second running instance is a luxury this footprint cannot always afford
(see [`DEPLOYMENT_MINDX_PYTHAI_NET.md`](DEPLOYMENT_MINDX_PYTHAI_NET.md)). So the
recovery posture has leaned on git history rather than warm replicas. This is
changing:

- **IPFS / Lighthouse offload** (after the contracts deploy) moves cold state
  off the local disk to content-addressed, chain-anchored storage
  (`agents/storage/`). That reclaims the headroom a replica needs, and makes a
  replica's state portable and verifiable by CID rather than copied wholesale.
- **Build-into-a-new-environment from GitHub** is the further horizon: a replica
  is not a local directory copy but a fresh mindX *materialized from the public
  repo* into a new host, restoring offloaded state from IPFS. Replication then
  becomes "stand up another head, anywhere," not "copy a folder."

### Replication and the multiple-heads model

When space allows, replication becomes the substrate for the **coupled-head
model** of the Schmidhüber Engine (see
[`SCHMIDHUBER_ENGINE.md`](SCHMIDHUBER_ENGINE.md) §4, `mindX --replicate`):
phase-offset heads where one serves stably (ataraxic) while another disrupts
(tests an upgrade). A failed experiment on the disrupting head never touches the
serving head; roles rotate only when a change proves out. Pre-milestone
replication and multi-head operation are the same mechanism at two scales.

### Priority

**A working mindX outranks multiple replications.** Until IPFS offload frees the
footprint and the build-from-GitHub path is proven, the operative recovery
guarantee is the git lineage (backup_agent) plus the discipline of *replicate
before testing anything you cannot reverse*. Scale the heads when the space and
the storage rails exist — not before. Survival first; multiplicity second.
