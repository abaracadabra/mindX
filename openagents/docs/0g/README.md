# 0G — Two Submissions, $15,000 Pool

The 0G prize pool covers two distinct tracks, both addressable by modules already shipped here:

- **Track A — Best Agent Framework, Tooling & Core Extensions ($7,500)**
- **Track B — Best Autonomous Agents, Swarms & iNFT Innovations ($7,500)**

## Submission entry points

| Track | Submission | Primary doc |
|---|---|---|
| A | mindX 0G Adapter (Compute + Storage + Galileo Chain) | [`OG_INTEGRATION_GUIDE.md`](OG_INTEGRATION_GUIDE.md) |
| B | mindX iNFT-7857 (encrypted-intelligence ERC-7857 + agent swarm wiring) | [`INFT_7857.md`](INFT_7857.md) |

## What the judge sees per track

### Track A · 0G Adapter

- **0G Compute** — `llm/zerog_handler.py` (OpenAI-compat client). Captures `ZG-Res-Key` attestation per call.
- **0G Storage** — `agents/storage/zerog_provider.py` + `openagents/sidecar/` (Node TS HTTP bridge wrapping `@0glabs/0g-ts-sdk`). Sidecar binds localhost only; `POST /upload`, `GET /retrieve/:root`, `GET /health`.
- **0G Chain (Galileo)** — `openagents/deploy/deploy_galileo.sh` deploys iNFT-7857 + DatasetRegistry. Deployment outputs land in `openagents/deployments/galileo.json`.
- **Memory anchor** — [`THOT_0G_MEMORY_ANCHOR.md`](THOT_0G_MEMORY_ANCHOR.md) walks the THOT.commit() → 0G Storage Merkle root → on-chain anchor flow end-to-end.

### Track B · iNFT-7857 swarms

- **Standards-aligned ERC-7857** with sealed-key transfer gating, EIP-712 oracle proofs, and AgenticPlace + BANKON binding hooks. 56/56 tests pass under `FOUNDRY_PROFILE=inft forge test`.
- **Live console** at [https://mindx.pythai.net/inft7857](https://mindx.pythai.net/inft7857) — single-file ethers v6 + MetaMask UI, 9 tabs (Overview · Mint · Inspect · Transfer · Clone · Authorize · Burn · Bind · Admin), live event log subscribed to all 14 contract events.
- **Swarm composition** — `demo_agent.py` mints an iNFT, anchors a Merkle root via THOT, registers an agent identity via BANKON ENS, and runs a Conclave deliberation. Each module is independently usable.

## Files in this folder

- [`README.md`](README.md) — this file.
- [`INFT_7857.md`](INFT_7857.md) — module brief: contract surface, tests, deployment, UI tour.
- [`OG_INTEGRATION_GUIDE.md`](OG_INTEGRATION_GUIDE.md) — 0G Compute API integration (originally `OGintegrationguide.md`).
- [`THOT_0G_MEMORY_ANCHOR.md`](THOT_0G_MEMORY_ANCHOR.md) — memory-anchor primitive over 0G Storage.

## See also

- Cross-cutting architecture: [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
- Reproduction quickstart: [`../QUICKSTART.md`](../QUICKSTART.md)
- Canonical iNFT-7857 reference (full audit): [`../../../docs/INFT_7857.md`](../../../docs/INFT_7857.md) (in the mindX docs tree)
