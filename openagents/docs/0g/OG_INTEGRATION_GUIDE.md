# 0G integration playbook for the OpenAgents prize track

**The single highest-leverage move for mindX + AgenticPlace + BANKON + Parsec at ETHGlobal OpenAgents is to ship an ERC-7857 INFT marketplace where mindX agents are minted as intelligent NFTs, coordinated as a swarm via shared 0G Storage, billed through a new `@x402-0g` payment scheme settling on 0G Chain.** That single project hits Sub-track 2's "iNFT-minted agents with embedded intelligence" and "specialist agent swarms" suggestions verbatim, opens a less-crowded category (only Warriors AI-rena touched iNFTs at Cannes), and creates reusable infrastructure (the x402 scheme) that doubles as an obvious framework artifact. With $15,000 on the table — **0G is 30% of the entire OpenAgents prize pool and 3× the size of every other sponsor** — and submissions due May 3 with finalists May 6, 2026, the operative window is roughly 8 days from this report. The rest of this document is the engineering reference needed to execute that play, including a full repo inventory, mainnet/testnet config, SDK call patterns, and explicit gotchas.

---

## 1. Organization, mission, and current chain status

0G runs as a two-entity setup. **0G Labs (Zero Gravity Labs, Inc.)** is the for-profit core dev shop that authors the protocol, SDKs, and reference clients; **0G Foundation** is the independent governance/grants/ecosystem entity at 0gfoundation.ai that runs the $8.88M Guild on 0G, the $88.8M Ecosystem Growth Program (Feb 2025), the OnePiece Labs accelerator cohort, and the $0G token treasury. Founders are **Michael Heinrich (CEO, ex-Garten/Bridgewater)**, **Ming Wu (CTO, ex-CTO Conflux/Microsoft Research)**, **Fan Long (CSO, MIT/UToronto, Conflux co-founder)**, and **Thomas Yao (CBO, IMO Ventures)**.

Funding totals roughly **$325M committed**: a $35M pre-seed (Mar 2024, Hack VC lead), a $40M seed plus a $250M token-purchase commitment (Nov 2024, Hack VC + Animoca + Samsung Next + Polygon's Sandeep Nailwal + Stanford Blockchain Fund + Bankless Ventures), and a ~$30M AI Alignment Node sale across 18 launchpads. The mission framing is **"Make AI a Public Good"** via a **decentralized AI operating system (deAIOS)** — a modular AI-native L1 stack of four primitives: **0G Chain** (EVM execution + CometBFT consensus), **0G Storage** (log + KV layers), **0G DA** (data availability with VRF-quorum BFT), and **0G Compute** (decentralized GPU/inference marketplace).

**Aristotle Mainnet went live September 21, 2025**, with 100+ launch partners (Chainlink, Google Cloud, Alibaba Cloud, Coinbase Wallet, Binance Wallet, MetaMask, Ankr, Fireblocks, Figment, Ledger). The active testnet is **Galileo (Testnet V3)**, released April 2025, which posts ~2,500 TPS on optimized CometBFT. Chain + Storage are full mainnet today; **DA and Compute are on mainnet with progressive expansion** — Compute now serves 7 production models including GPT-OSS-120B, GLM-5-FP8, DeepSeek-Chat-v3, Qwen3.6-Plus (TeeTLS-routed via Alibaba Cloud), Qwen3-VL-30B, Whisper-Large-v3, and Z-Image. By H2 2025 the ecosystem reported **400+ integrations across 300+ projects**, with notable AI/L2 customers Polygon, Arbitrum, Manta, Astar, Conflux, Fuel, Eliza OS, ModulusLabs, and Animoca's Kult Games. NTU Singapore signed an S$5M research partnership in December 2025 — the project's first university research deal.

The **$0G token** (1B fixed supply, ~210–251M circulating per CoinGecko April 2026, market cap ~$120M, FDV ~$498–569M) is gas, staking, AI-compute payment, storage payment, and governance. Listings span KuCoin, Binance, Bybit, Kraken, Upbit, Gate, Bitget, MEXC, HashKey, OKX (24+ exchanges total). Note the legacy Newton-era ticker **A0GI** still appears on some third-party pages — on mainnet/Galileo the canonical ticker is **0G**.

## 2. Complete repository inventory

The two GitHub orgs largely **mirror each other** — many flagship repos exist under both `0glabs/<repo>` and `0gfoundation/<repo>` (both `awesome-0g`, `0g-storage-node`, `0g-ts-sdk`, `0g-da-client`, `0g-blockscout`, `0g-doc` etc.). Treat them as one canonical codebase; `0gfoundation` is the newer/canonical home (the current TS SDK is `@0gfoundation/0g-ts-sdk` v1.2.6+ while `@0glabs/0g-ts-sdk` is legacy still referenced widely in docs). The Foundation org reports **103 repos**; `0glabs` reports several hundred.

### Storage layer

| Repo | Lang | License | Purpose |
|---|---|---|---|
| **0g-storage-node** | Rust 92.5% | Apache-2.0 | PoRA mining, erasure coding, Merkle commitments. v1.2.0 Jan 13 2026. ~178★ |
| **0g-storage-client** | Go | Apache-2.0 | Go SDK + CLI. Upload/download/KV/encryption/hot-storage routing |
| **0g-storage-contracts** | Solidity/TS | — | Flow / FixedPrice Market / ChunkDecayReward / ChunkLinearReward / PoraMine |
| **0g-storage-kv** | Rust | — | Mutable KV runtime replaying KV stream files atop the storage node |
| **0g-ts-sdk** | TS | — | npm `@0gfoundation/0g-ts-sdk` v1.2.6+ (legacy `@0glabs/0g-ts-sdk`) |
| **0g-python-api** | Python | — | "Quick & dirty" Python wrapper around the Go CLI |
| **0g-storage-web-starter-kit** | Next.js+Wagmi | — | Browser drag-drop UI starter |
| **0g-storage-ts-starter-kit** | TS+Express | — | Scripts + lib + Vite browser UI; current pattern reference |
| **0g-storage-go-starter-kit** | Go+Gin+Swagger | — | Go REST API starter |
| **0g-storage-scan** | Go | — | Backend powering storagescan(-galileo).0g.ai |

### Data Availability layer

| Repo | Lang | Purpose |
|---|---|---|
| **0g-da-node** | Rust | DA node — KZG, VRF sampling, BLS quorum aggregation |
| **0g-da-client** | Go | Disperser/retriever gRPC; submits and retrieves blobs (port 51001) |
| **0g-da-encoder** | Rust (CUDA optional) | AMT/LVMT encoder; gRPC :34000; 4090-tested |
| **0g-da-op-plasma** | Go | OP Stack DA-server sidecar for generic commitments → 0G DA |
| **0g-da-example-rust** | Rust | gRPC reference using `disperser.proto` |
| **0g-data-avail** | Go | Older/alt DA monorepo |

### Chain (L1)

| Repo | Lang | Purpose |
|---|---|---|
| **0g-chain** | Go (Cosmos SDK + Ethermint) | Legacy L1 — chain ID `zgchain_8888-1`, denom `ua0gi`, EVM denom `neuron`. ~80★ |
| **0gchain-NG** | Go | Active successor — CometBFT-based, Aug 2025 shared-staking hardfork w/ Symbiotic restaking |
| **0g-geth** | Go | go-ethereum fork used as the EL |
| **0g-blockscout** | Elixir/JS | Powers chainscan(-galileo).0g.ai |
| **0g-monitor** | Go | Fullnode/storage monitoring; InfluxDB + DingTalk/Telegram alerts |

### Compute / Serving / Agent stack

| Repo | Lang | Purpose |
|---|---|---|
| **0g-serving-user-broker** | TS | The compute SDK — `@0glabs/0g-serving-broker`. Discover/fund/sign/settle |
| **0g-compute-ts-starter-kit** | TS+Express+Swagger | REST starter w/ auto-payments, TEE verification, ledger ops |
| **0g-eliza** | TS | ElizaOS conversational agent template wired for Twitter/Discord on 0G |
| **0g-agent-nft** | Solidity | **ERC-7857 reference implementation** — INFT spec for AI agents w/ encrypted metadata. CC0-1.0. ~14★ |
| **0g-agent-skills** | MD/TS | **Cursor/Claude Code/Copilot skill pack** — 14 skills, 4 runnable examples (`file-vault`, `ai-chatbot`, `nft-with-metadata`, `ai-image-gallery`) |
| **0g-tapp** | — | TEE deployment management ("Securing TEE Deployments Without SSH") |
| **A0GI-contracts** | Solidity | Internal contracts (likely native A0GI wrapping) |
| **0g-deployment-scripts** | Hardhat/Foundry | `MyToken.sol` reference deploy across Hardhat/Foundry/ethers/viem to Galileo |

### Documentation, tooling, third-party

| Repo | Purpose |
|---|---|
| **awesome-0g** | Curated index — SDKs, kits, RPCs, MCP servers, hackathon winners. 53★ |
| **0g-doc** | Docusaurus source for docs.0g.ai |
| Community **0g-storage-sdk** (PyPI) | Independent line-by-line Python port of 0g-ts-sdk (v0.1.0, third-party) |
| Community MCP servers | `colygon/0g-mcp-server`, `Tairon-ai/0g-chain-mcp` |

For DAIO purposes the four highest-value repos are **0g-agent-nft** (the ERC-7857 reference — agent ownership semantics), **0g-agent-skills** (drop-in expert knowledge for any LLM coding co-pilot working on 0G), **0g-serving-user-broker** (the only path to verifiable inference billing), and **0g-ts-sdk** (the universal storage primitive).

## 3. Core components in technical depth

### 0G Storage — log + KV with PoRA mining

The architecture is a **two-layer / two-lane** system. The **log layer** is an append-only flow indexed by universal offset (the "main flow"); the **KV layer** is a mutable transactional runtime that replays log entries to maintain consistent KV snapshots. Files split into chunks, get **Reed-Solomon erasure-coded**, and distribute across nodes — reconstruction tolerates ≥30% offline. Storage nodes use `shard_position = "shard_id/shard_number"` (powers of 2). Data publishing commits Merkle roots on-chain via the **Flow** contract; data storage runs the actual chunked replication. **PoRA (Proof of Random Access)** mining caps single-miner range at 8 TB to keep small operators competitive.

Two parallel networks coexist: **Turbo** (higher fee, low latency, default — indexer `https://indexer-storage-testnet-turbo.0g.ai`) and **Standard** (cheaper, slower, different flow contract). Files in turbo are **not** retrievable via standard. Marketing claims of "50 GB/s DA throughput" and "100× cheaper than competing decentralized storage" originate from the whitepaper — current observed Galileo TPS is ~2,500 chain throughput; real DA mainnet load benchmarks aren't publicly pinned.

Critical TS SDK pattern (v1.2.6+ supports AES-256 and ECIES encryption):

```ts
import { ZgFile, Indexer, MemData } from '@0gfoundation/0g-ts-sdk';
import { ethers } from 'ethers';
const provider = new ethers.JsonRpcProvider('https://evmrpc-testnet.0g.ai');
const signer   = new ethers.Wallet(PRIVATE_KEY, provider);
const indexer  = new Indexer('https://indexer-storage-testnet-turbo.0g.ai');

const file = await ZgFile.fromFilePath('./agent-memory.bin');
const [tree] = await file.merkleTree();           // MUST run before upload
const [tx]   = await indexer.upload(file, RPC_URL, signer,
                  { encryption: { type:'aes256', key } });
await indexer.download(tree.rootHash(), './out', /*withProof*/ true);
```

Quirks: SDK expects ethers v5 Signer types — cast `signer as any` for ethers v6; `merkleTree()` must run before `upload()`; browsers can't use `indexer.download()` (uses Node `fs`) — use `downloadToBlob` instead.

### 0G DA — VRF-selected BLS quorums over erasure-coded blobs

DA nodes are separate from validators. **VRF selects a quorum** of signers per blob (up to 1024 votes per signer, voting power ∝ delegated stake), each signer signs **one row of the encoded blob with BLS**, and aggregate signatures attest availability. Validators on 0G Chain (CometBFT) finalize the DA proofs but DA nodes don't participate in chain finality. **DAS (Data Availability Sampling)** lets light clients verify availability without downloading full blocks. Erasure encoding is GPU-accelerated (CUDA 12.04 on RTX 4090; NVIDIA H20 GPU TEE testing referenced in Oct 2025 update — H100/H200 confidential computing is roadmap, not production). Submission is via the `0g-da-client` combined binary (gRPC :51001) with `--batcher.da-entrance-contract` and `--batcher.da-signers-contract 0x0000000000000000000000000000000000001000` precompile flags. Polygon was the first major rollup customer; **0g-da-op-plasma** is described in 0G's docs as the first AI-focused external integration to the OP Stack.

### 0G Compute — TeeML and TeeTLS with on-chain settlement

Three roles: **Provider** (registers GPU, sets price, runs model in TEE), **Broker** (escrow ledger sub-account per user-provider pair), **Consumer** (deposits 0G, calls inference). Two verification modes matter: **TeeML** runs the AI model itself **inside Intel TDX / Phala dstack** with response signing by the TEE key (verifiable via `dstack-verifier` and sigstore — used for self-hosted GLM-5-FP8, DeepSeek, GPT-OSS-120B, Whisper, Z-Image); **TeeTLS** runs the broker in a TEE acting as a verifiable HTTPS relay to centralized providers like Alibaba Cloud Model Studio (used for Qwen3.6-Plus). Settlement is delayed/batched via signed-transaction batches; min ledger deposit is 3 0G, min provider sub-account 1 0G. Rate limit: **30 req/min/user/provider, burst 5, max 5 concurrent** (HTTP 429 over).

Live mainnet pricing (April 2026):

| Model | Type | Verification | Input/M | Output/M |
|---|---|---|---|---|
| GLM-5-FP8 | Chat | TeeML | 1.0 0G | 3.2 0G |
| deepseek-chat-v3-0324 | Chat | TeeML | 0.30 0G | 1.00 0G |
| gpt-oss-120b | Chat | TeeML | 0.10 0G | 0.49 0G |
| qwen3-vl-30b-a3b-instruct | VL | TeeML | 0.49 0G | 0.49 0G |
| qwen3.6-plus | Chat | TeeTLS | 0.80–3.20 0G | 4.80–9.60 0G |
| whisper-large-v3 | STT | TeeML | 0.05 0G | 0.11 0G |
| z-image | T2I | TeeML | — | 0.003 0G/img |

The compute SDK is OpenAI-compatible — meaning `openai-python` works directly with `app-sk-<SECRET>` Bearer tokens from `0g-compute-cli inference get-secret`, which papers over the missing first-party Python SDK. **Six rules from `0g-agent-skills/AGENTS.md` will save hours**: always call `processResponse()` after every inference; parameter order is `(providerAddress, chatID, usageData)`; extract chatID from `ZG-Res-Key` response header (body fallback); headers are single-use and replay-protected; use ethers v6; all testnet services advertise TeeML verifiability.

```ts
import { createZGComputeNetworkBroker } from '@0glabs/0g-serving-broker';
const broker = await createZGComputeNetworkBroker(wallet);
await broker.ledger.addLedger(3);                              // ≥3 0G
const provider = '0x69Eb5a0BD7d0f4bF39eD5CE9Bd3376c61863aE08'; // Gemma 3 27B testnet
await broker.inference.acknowledgeProviderSigner(provider);    // once per provider
await broker.ledger.transferFund(provider, 'inference', ethers.parseEther('1.0'));
const { endpoint, model } = await broker.inference.getServiceMetadata(provider);
const headers   = await broker.inference.getRequestHeaders(provider, content);
const openai    = new OpenAI({ baseURL: endpoint, apiKey: '' });
const completion = await openai.chat.completions.create({ messages, model }, { headers });
await broker.inference.processResponse(provider, chatID, usageData); // MANDATORY
```

### 0G Chain — modular CometBFT + Reth EL

Modular consensus (CometBFT/Tendermint, optimized) and execution (full-EVM, Cancun-compatible). The **Geth → Reth migration completed in 2025**, a major perf upgrade for AI workloads (exact production cutover not pinned in primary docs). VRF validator selection, native 0G PoS staking. 11,000 TPS per shard claim, sub-second finality; roadmap targets DAG-based parallel execution at 100K TPS / 50ms latency. Foundry/Hardhat both supported with **`evm_version = "cancun"` mandatory** when deploying.

| | Mainnet (Aristotle) | Testnet (Galileo) |
|---|---|---|
| Chain ID | **16661** | **16602** (some kits report 16601 — minor discrepancy) |
| RPC | `https://evmrpc.0g.ai` | `https://evmrpc-testnet.0g.ai` |
| Explorer | `chainscan.0g.ai` | `chainscan-galileo.0g.ai` |
| Storage scan | `storagescan.0g.ai` | `storagescan-galileo.0g.ai` |
| Faucet | n/a | `https://faucet.0g.ai` (0.1 0G/day) + Google Cloud faucet |
| Storage Indexer | `indexer-storage-turbo.0g.ai` | `indexer-storage-testnet-turbo.0g.ai` |
| Flow contract | `0x62D4144dB0F0a6fBBaeb6296c785C71B3D57C526` | `0x22E03a6A89B950F1c82ec5e74F8eCa321a105296` |
| Mine contract | `0xCd01c5Cd953971CE4C2c9bFb95610236a7F414fe` | `0x00A9E9604b0538e06b268Fb297Df333337f9593b` |
| Reward contract | `0x457aC76B58ffcDc118AABD6DbC63ff9072880870` | `0xA97B57b4BdFEA2D0a25e535bd849ad4e6C440A69` |
| DA Entrance | — | `0xE75A073dA5bb7b0eC622170Fd268f35E675a957B` (alt: `0x857C0A28A8634614BB2C96039Cf4a20AFF709Aa9` in older configs) |
| DA-signers precompile | — | `0x0000000000000000000000000000000000001000` |

Production should use **QuickNode / Ankr / dRPC / Thirdweb** RPCs — public dev RPCs are documented as dev-only. Contract verification goes via `chainscan(-galileo).0g.ai/open/api` with `hardhat verify` `customChains` config.

### ERC-7857 — the INFT standard 0G authored

ERC-7857 is **0G Labs' own NFT standard introduced January 2025** that extends ERC-721 to handle AI agents with encrypted, dynamic metadata. The core innovation: ERC-721 cannot privately transfer the encrypted metadata that *is* the actual value of an AI agent. ERC-7857 adds a `transfer(proof)` flow where an oracle (TEE or ZKP) attests that `oldDataHash` (encrypted under sender's key) → `newDataHash` (re-encrypted under a fresh key) is a faithful re-encryption, and produces a `sealedKey` encrypted with the receiver's public key. It also defines `clone()` (new tokenId, same metadata) and `authorizeUsage()` (executor-mediated read access without key transfer — the executor seal can be TEE or FHE). `PROOF_VALIDITY_PERIOD = 1 hour`. The reference implementation in `github.com/0gfoundation/0g-agent-nft` uses OpenZeppelin v5 `ERC721 + Ownable + ReentrancyGuard` and supports Intel SGX / Phala dstack TEE oracles or ZKP oracles. **This is the highest-leverage repo for any DAIO ownership semantics — agents become tradeable while keeping model weights and memory private.** The planned **AIverse** marketplace ("OpenSea for iNFTs") is in early-access rollout to One Gravity NFT holders.

## 4. The OpenAgents 0G prize track — verbatim and decoded

ETHGlobal OpenAgents runs **April 24 → May 6, 2026** (submissions close May 3, finalists May 6) entirely online with a **$50K+ pool across 5 sponsors**. **0G is the largest sponsor at $15,000 — 30% of the entire pool, 3× any other sponsor.** Other tracks (Uniswap Foundation $5K, Gensyn $5K, ENS $5K, KeeperHub $5K) are stackable up to ETHGlobal's 3-prize cap per submission.

The 0G prize splits into two **strictly separated** sub-tracks. Cross-pollution is the prize page's most aggressive language ("strictly for framework-level work" / "strictly for building the actual agents") — pick one and stay in it.

### Sub-track 1 — Best Agent Framework, Tooling & Core Extensions ($7,500)

Ranked five tiers: $2,500 / $2,000 / $1,500 / $1,000 / $500. Verbatim brief: *"Build the best core extensions, improvements, forks, or entirely new open agent frameworks inspired by **OpenClaw** (or alternatives like **ZeroClaw, NullClaw**, etc.) and deployed on 0G."* Suggested ideas: new OpenClaw modules using 0G Compute sealed inference (qwen3.6-plus or GLM-5-FP8); self-evolving frameworks generating/testing/integrating skills with 0G Storage memory; modular "agent brain" libraries with swappable memory layers (KV/Log) and LLM backends; no-code/low-code visual builders with one-click 0G Compute+Storage deploy. Submissions must include **at least one working example agent** built using the framework, plus an architecture diagram (labeled "optional but strongly recommended" — at ETHGlobal that means de facto required to win).

### Sub-track 2 — Best Autonomous Agents, Swarms & iNFT Innovations ($7,500)

Flat pool — "up to **5 teams will receive $1,500**." Verbatim brief: *"This track is strictly for building the actual agents. Create the most capable autonomous single agents, powerful multi-agent swarms/collectives, or any highly creative open agent project deployed on 0G. This track celebrates long-running goal-driven agents, emergent collaboration, and novel uses of **iNFTs (ERC-7857)** for ownership, composability, and monetization on 0G."* Suggested ideas: personal "Digital Twin" agents with persistent 0G Storage memory (KV state + Log history); research/knowledge agents with self-fact-checking via verifiable 0G Compute; specialist swarms (planner + researcher + critic + executor) coordinating via shared 0G Storage; **iNFT-minted agents with embedded intelligence (encrypted on 0G Storage), persistent memory, dynamic upgrades, and automatic royalty splits on usage**; agent breeding/merging via iNFTs. iNFT submissions must include a **link to the minted iNFT on 0G explorer + proof that intelligence/memory is embedded**; swarm submissions must explain how agents communicate and coordinate.

### Universal qualification requirements

Project name + short description, **contract deployment addresses**, public GitHub with README, demo video and live demo link, **explicit explanation of which 0G protocol features/SDKs were used**, team member contact info (Telegram + X). **Demo video is hard-capped under 3 minutes** — judges have stated they will not watch longer.

### Past winner pattern (ETHGlobal Cannes July 2025, $5K 0G track)

11/12 submissions used 0G Compute, 3/12 used 0G Storage. **AInfluencer** (1st) ran a fully autonomous YouTube content agent through verifiable 0G inference. **PrivyCycle** (2nd) used 0G Compute for private health AI. **Warriors AI-rena** (3rd) was the **only** project to touch iNFTs and won 3rd specifically for that — at OpenAgents iNFTs are now a co-headlined sub-track with explicit suggested ideas, making this a structurally less-crowded path. Common winning DNA: full-stack 0G integration (not bolted-on), verifiable/zk-backed outputs, public-facing real product (not just demo), and one of: AI agent + game / social / health vertical.

### Strategic decoding

OpenClaw is **0G's currently-championed agent framework** — the April 21, 2026 0G blog post "Ghast AI: OpenClaw In Your Browser, Powered by 0G" is the canonical reference implementation worth studying. The two named live models (qwen3.6-plus, GLM-5-FP8) are the inference targets that earn plausibility points. The "0G Storage (KV for real-time state + Log for conversation history)" phrasing wants builders to demonstrate they understand the **two storage modalities** — using both is depth signal. The Telegram support channel `https://t.me/+mQmldXXVBGpkODU1` is the de facto office hours; Day-1 visibility there with 0G DevRel matters. Builder Hub `https://build.0g.ai` is the portal.

## 5. Strategic fit and recommended architecture

The user's stack maps unusually cleanly onto 0G's primitives because the architectural overlap is structural rather than coincidental: **mindX is already a Gödel-machine reasoning engine that needs verifiable execution and immutable logs; AgenticPlace is already an ERC-8004 agent marketplace that needs iNFT semantics; Parsec is an x402 wallet that needs a settlement chain optimized for AI inference; BDK6/openBDK is an L3 launcher that needs a DA layer; BANKON needs cheap verifiable oracle proofs.** Every primitive 0G ships has a pre-existing socket on the user's side.

### Priority-ordered integration map

| Priority | User component | 0G primitive | Concrete artifact |
|---|---|---|---|
| 1 | AgenticPlace | ERC-7857 INFT + 0G Chain ERC-8004 mirror | iNFT marketplace where each listing wraps an OpenClaw/mindX agent; CREATE2-deploy 8004 registries on 16661 |
| 2 | Parsec wallet | 0G Chain + x402 | Ship `@x402-0g` package alongside `@x402-evm` and `@x402-avm`, settling AI inference micropayments on 0G |
| 3 | mindX | 0G Compute + Storage | Replace OpenAI/Ollama with TeeML inference; persist Gödel-machine decision log to 0G Storage Log layer; KV for hot AGInt state |
| 4 | BDK6/openBDK | 0G DA | Ship a "0G preset" in the Kurtosis + Podman + Polygon CDK template — every L3 spun up via BDK6 becomes a 0G DA customer |
| 5 | BANKON | 0G DA | Publish Qubic oracle price-proof commitments to DA so BANKON ASA price feeds become verifiable |

### The single submission that wins

Build **"AgenticPlace × 0G"** — an ERC-7857 INFT marketplace where mindX agents are minted as INFTs, coordinated as a multi-agent swarm via shared 0G Storage memory, served through 0G Compute (qwen3.6-plus or GLM-5-FP8 with TeeML verification), and billed via a new `@x402-0g` x402 scheme settling on 0G Chain (16661 mainnet for the demo, 16602 testnet for development). This single project hits Sub-track 2 verbatim suggestions on **three axes simultaneously** — iNFT-minted agents, specialist swarms, persistent 0G Storage memory — while the `@x402-0g` package provides the framework artifact that could alternatively fit Sub-track 1 if the agent demo gets cut. The required iNFT-explorer link with embedded-intelligence proof is a competitive moat: nearly no other team will produce this.

Concrete component layout:

```
agenticplace-0g/
├── contracts/
│   ├── INFTAgent.sol            # ERC-7857 from 0g-agent-nft, OZ v5
│   ├── IdentityRegistry.sol     # ERC-8004 mirror (CREATE2 across chains)
│   ├── ReputationRegistry.sol   # ERC-8004
│   └── X402Settlement.sol       # x402 receipt verification on 0G
├── packages/
│   ├── x402-0g/                 # NEW — @x402-0g/core scheme package
│   ├── mindx-on-0g/             # OpenClaw fork w/ 0G Storage memory layer
│   └── agentic-swarm/           # Planner+Researcher+Critic+Executor
├── apps/
│   ├── marketplace/             # Next.js + Wagmi + 0g-storage-web-starter-kit
│   └── parsec-bridge/           # Tauri/Rust wallet plugin signing X402
└── examples/
    ├── digital-twin/            # mindX-on-0G as a single-agent demo
    └── breeding/                # iNFT merge → child INFT inheriting memory
```

### Foundry deployment template for 0G

```toml
# foundry.toml
[profile.default]
src = "contracts"
solc = "0.8.24"
evm_version = "cancun"          # MANDATORY on 0G
optimizer = true
optimizer_runs = 200

[rpc_endpoints]
og_testnet = "https://evmrpc-testnet.0g.ai"
og_mainnet = "https://evmrpc.0g.ai"

[etherscan]
og_testnet = { key = "no-api-key", url = "https://chainscan-galileo.0g.ai/open/api" }
og_mainnet = { key = "no-api-key", url = "https://chainscan.0g.ai/open/api" }
```

```bash
forge create contracts/INFTAgent.sol:INFTAgent \
  --rpc-url og_testnet --private-key $PK \
  --constructor-args "MindX Agents" "MX-INFT" $TEE_ORACLE
forge verify-contract <addr> INFTAgent --chain 16602 --watch
```

### x402-0g scheme sketch

The Algorand `@x402-avm` package uses ASAs with no smart contract for the "exact" scheme. On 0G the equivalent is straightforward EIP-3009 / ERC-20 `transferWithAuthorization` against $0G or a 0G-native USDC; the facilitator simulates and submits, returns the resource. Because 0G Chain is Cancun-EVM, the entire x402-evm scheme works unmodified — `@x402-0g` is mostly a config/CAIP-2 wrapper (`eip155:16661` mainnet, `eip155:16602` testnet) plus a recommended facilitator endpoint. The novel angle for the prize submission: **integrate x402 settlement directly with the 0G Compute broker** so a single HTTP 402 round-trip funds the broker ledger and triggers inference, eliminating the upfront `addLedger`/`depositFund` UX friction that today forces users to pre-fund. That's the kind of framework-level contribution Sub-track 1 explicitly invites.

### Gotchas the user should pre-empt

The `@0glabs/0g-ts-sdk` ↔ `@0gfoundation/0g-ts-sdk` package split is genuinely confusing — pin to **`@0gfoundation/0g-ts-sdk` v1.2.6+** in mindX/AgenticPlace dependencies. The compute SDK is `@0glabs/0g-serving-broker` (still under labs, not foundation) and **expects ethers v6** while the storage SDK was originally typed for v5 — when mixing, cast `signer as any`. `merkleTree()` must run before `upload()` or the upload throws. Browser dApps cannot call `indexer.download()` (Node `fs`) — use `downloadToBlob` and Vite `vite-plugin-node-polyfills` for `crypto`/`buffer`/`stream`/`util`/`events`/`process`. Compute headers are **single-use replay-protected** — re-requesting `getRequestHeaders` per call is mandatory. **`processResponse(provider, chatID, usageData)` parameter order must be exact** and must be called after every inference or the ledger doesn't settle correctly. ChatID extraction prefers the `ZG-Res-Key` response header, body fallback. Faucet is 0.1 0G/day per wallet — request more via Discord ticket if a swarm demo needs many funded keys. Rate limit is 30 req/min/user/provider with burst 5 and max 5 concurrent — design swarm parallelism around that. **Public RPCs are dev-only**; use QuickNode/Ankr/dRPC for any production demo. The **chain ID discrepancy** (16601 vs 16602) — the 0g-storage-ts-starter-kit README says 16601 but current docs say 16602 for Galileo; verify against the deployed Flow contract address before posting submission contracts. NVIDIA H100/H200 confidential computing is roadmap not production — TeeML today is Intel TDX / Phala dstack; don't over-claim GPU TEE in the demo video. Mainnet vs testnet: **Galileo testnet (16602) is correct for hackathon submissions** for the free faucet; deploy INFTs you intend to launch publicly on 16661 mainnet where 7 production models including GPT-OSS-120B are live. The DA Entrance contract appears in two addresses across docs (`0xE75A...957B` and `0x857C...9Aa9`) — confirm via `0g-da-client` config before integrating.

### Universal pre-submission checklist

1. Deploy verified contracts to Galileo (16602) and paste addresses into ETHGlobal submission.
2. Cut demo video to **≤2:50** (3:00 hard cap, build slack).
3. Architecture diagram showing **OpenClaw + 0G Storage + 0G Compute + ERC-7857** integration points.
4. Use **qwen3.6-plus** (TeeTLS) or **GLM-5-FP8** (TeeML) as the named inference model in README.
5. README must explicitly enumerate every 0G SDK and feature touched (Storage KV vs Log, Compute sealed inference, DA, Chain, ERC-7857).
6. Join `https://t.me/+mQmldXXVBGpkODU1` Day 1 — pre-judging visibility with 0G DevRel matters in past results.
7. For iNFT submissions: minted iNFT link on `chainscan-galileo.0g.ai` + proof intelligence is embedded (verifiable encrypted-metadata commitment hash).
8. For swarm submissions: explicit sequence diagram of inter-agent communication via 0G Storage.
9. Drop `git clone https://github.com/0gfoundation/0g-agent-skills .0g-skills` into the repo — gives Claude/Cursor expert 0G knowledge with correct patterns out of the box.
10. Stack with **ENS** (agent identity, synergistic with iNFT) and **Uniswap** (if the swarm executes onchain trades) up to the 3-prize cap.

## 6. External references

The canonical entry points are **docs.0g.ai** for protocol docs (footer copyright 2026, Docusaurus source at `github.com/0gfoundation/0g-doc`), **0g.ai** for marketing and the blog, **0gfoundation.ai** for grants/governance, **build.0g.ai** as Builder Hub, **hub.0g.ai** for dApp/analytics, and **explorer.0g.ai** for ecosystem discovery. The whitepaper PDF — *"0G: Towards Fully Decentralized AI Operating System"* — is at `https://cdn.jsdelivr.net/gh/0glabs/0g-doc/static/whitepaper.pdf`; the EU MiCA regulatory white paper (v1.0, 2025-08-01) is hosted on the Foundation site. Discord is `https://discord.gg/0glabs` (~570K members), Telegram `https://t.me/zgcommunity`, X handles `@0G_labs` and `@0G_Foundation`. The compute marketplace UI is at `https://compute-marketplace.0g.ai/inference` and the testnet Google Cloud faucet is `https://cloud.google.com/application/web3/faucet/0g/galileo`. Five technical blog posts worth reading before submission: "Introducing 0G, the AI x Web3 starship," "0G's Data Availability Layer," "0G Storage: Built for the AI Era," "0G Introducing ERC-7857" (canonical INFT explainer), and "Building Infinite AI: H2 2025 0G Ecosystem Update." Monthly tech updates (Aug/Sep/Oct 2025) are the truest signal of production status. The OpenAgents prize page itself is `https://ethglobal.com/events/openagents/prizes/0g`; the Cannes recap blog (July 17, 2025) lists past winners with patterns worth copying.

## Closing observations

What's actually new about 0G is the combination, not any single piece — Celestia has DA, Filecoin has storage, Bittensor has decentralized inference, but **0G is the only project shipping all four primitives behind one EVM L1 with a self-authored INFT standard tying them together**. ERC-7857 is the strategic centerpiece because it solves the one problem ERC-721 cannot — privately transferring the encrypted metadata that *is* the value of an AI agent — and 0G is the only chain currently championing it with a TEE/ZKP oracle reference implementation. For Professor Codephreak's stack, the architectural collision is unusually fortunate: ERC-8004 already gives AgenticPlace agent identity, but 0G's INFT gives those identities the encrypted-state semantics the marketplace needs to actually monetize agency. Layering x402 settlement on top creates a complete loop — discover (8004) → license (7857) → invoke (Compute) → pay (x402-on-0G) — which is approximately the same architecture diagram any thoughtful judge would draw on a whiteboard if asked "what does the agent economy actually need?" That's the diagram to ship in the demo video. The 8-day window from this report to the May 6 finalist announcement is tight for the full stack, but the 0g-agent-nft reference implementation, the 0g-compute-ts-starter-kit, and the 0g-storage-ts-starter-kit collapse roughly 60% of the build time — leaving the differentiation work (the swarm coordination protocol via shared 0G Storage memory and the `@x402-0g` package) as the actual hackathon contribution.