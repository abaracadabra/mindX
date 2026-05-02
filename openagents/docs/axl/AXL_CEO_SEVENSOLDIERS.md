# In camera at the localhost edge: AXL for a CEO and seven soldiers

Gensyn's **Agent eXchange Layer (AXL)** is a Go single-binary daemon that wraps a **Yggdrasil IPv6 mesh + gVisor userspace TCP/IP stack + ed25519 identity** behind a localhost-HTTP bridge on **port 9002**, with built-in **MCP and A2A** routers. It is a *transport-layer* primitive, not a cryptographic protocol of its own design — confidentiality is inherited from Yggdrasil's two-layer encryption (TLS on the direct peering link plus Yggdrasil end-to-end across the path), and Gensyn's own documentation explicitly states *"intermediate routing nodes cannot read your messages."* For a CEO + seven-soldiers private command hierarchy, AXL gives you reachability, identity, NAT traversal, and pairwise E2E encryption for free; it gives you **nothing** at the group, replay, traffic-analysis, MLS, or on-chain layers — those must be built at the application level. The ETHGlobal OpenAgents Gensyn track (April 24 – May 6, 2026) is **a $5,000 single-pool prize** ($2.5K / $1.5K / $1K) judged on **depth of AXL integration, code quality, documentation, and working examples**, with a hard qualifier: *"Must demonstrate communication across separate AXL nodes, not just in-process."* This is Gensyn's debut as an ETHGlobal sponsor — there are no past winners to mine — and the proposed C2 architecture maps cleanly onto Gensyn's "Decentralised Agent Messaging" suggested idea, which explicitly invites "self-organising working groups."

This report assumes you will write the soldiers in mindX, route inference through 0G Compute, persist memories on 0G Storage, name agents via ENS subnames, and register identities through ERC-8004. The remainder is the technical map for doing exactly that.

## Critical fact corrections before we begin

Three premises in your brief need correction so downstream architecture decisions are sound. **The Gensyn token is `$AI`, not "GENS"** — `$AI` claimed and distributed February 2026, mainnet live April 22, 2026 alongside the Delphi prediction market app; any "GENS" SPL token on Solana is unrelated. **AXL is written in Go, not Rust** — the entire Rust/libp2p/Noise/snow/dalek toolchain in your prompt does not apply; AXL leans on `yggdrasil-network/yggdrasil-go` + `gvisor.dev/gvisor/pkg/tcpip` + Go stdlib `crypto/ed25519` and `crypto/tls`. **There is no public "0G THOT" memory layer** as of April 28, 2026; 0G's actual memory primitive is **0G Storage (KV + Log)**, and the closest "Memory-as-Asset" pattern in production is the Ghast AI app (April 2026) on 0G. If THOT is real it is Discord/X-only and not yet indexed. Also: there is no "Identity & Reputation Vault" page in Gensyn docs by that name — on-chain identity lives on the **Gensyn L2 (OP-Stack Bedrock)**, peer identity lives in AXL's local `private.pem`, and the two are **deliberately uncoupled**.

## What AXL actually is, in one paragraph

AXL is a packaging move, not a protocol invention. The base layer is **Yggdrasil** — a decentralized IPv6 overlay that builds a dynamic spanning tree as nodes join — running on top of a **gVisor userspace TCP/IP stack** so the daemon needs no TUN device and no root. Each node generates an **ed25519 keypair** locally (literally `openssl genpkey -algorithm ed25519 -out private.pem`); the public key is the permanent peer ID and network address. Two encryption layers operate in tandem: **TLS on every direct peer hop**, and **Yggdrasil's end-to-end session encryption across the full path** so relays cannot read traffic. On top of that, AXL adds a **localhost HTTP bridge on `:9002`** with five documented endpoints — `POST /send`, `GET /recv`, `GET /topology`, `POST /mcp/{peer_id}/{service}`, `POST /a2a/{peer_id}` — and **dynamic registries** for MCP services and A2A skills. *"Any language that can make HTTP requests can use AXL"* (the docs' phrasing). It is **explicitly permissionless**: no staking, no on-chain registration, no whitelist, no DNS, no cloud. Multiple apps on the same machine can share one node. NAT traversal is solved by the outbound-only model — at least one node in a fresh mesh needs to be publicly reachable, but everything else dials out.

## Threat model AXL claims and does not claim

The only adversary AXL explicitly addresses in its docs is **the intermediate routing relay**, which is unable to decrypt traffic because of the Yggdrasil E2E layer. Beyond that, the documentation is silent. The table below maps your concrete threat questions onto what is and is not provided.

| Threat | AXL position | Source |
|---|---|---|
| Honest-but-curious relay reads payload | **Defended** — Yggdrasil E2E + TLS link | docs.gensyn.ai/tech/agent-exchange-layer |
| Malicious relay drops/reorders/replays | Not stated; reliability semantics undocumented | gap |
| Network observer at link layer | TLS hop encryption hides payload; metadata (timing, size, peer identifiers) is **not** padded or mixed | gap |
| Sybil flood of fake peer IDs | Not defended; ed25519 keys are free to mint | gap |
| Swarm member observes group traffic | **No native groups exist**; CEO must build a group key himself | gap |
| Forward secrecy on session compromise | Not stated; inherited from Yggdrasil/Ironwood (read upstream source to confirm) | gap |
| Post-compromise security / rekey | Not stated | gap |
| Anti-replay | Not stated | gap |
| Anti-traffic-analysis / mixing / cover traffic | Not provided | gap |
| Deniability / repudiation | Not stated | gap |
| Counterparty authentication beyond raw key | Out-of-band public-key exchange only | docs.gensyn.ai/tech/agent-exchange-layer |
| DoS / spam | Not addressed | gap |

For a "trade-secret-grade" comms channel between a CEO and seven soldiers on a public mesh, this means **you must not rely on AXL alone**. AXL gives you a confidential pipe between two known peer IDs; you supply the rest — group key agreement, replay nonces, sequence numbers, traffic padding, identity attestation. The good news: AXL's *"the node doesn't care what you send"* posture means there is nothing fighting you when you wrap your own MLS / Double Ratchet / Noise-IK on top.

## Repository inventory: what is on disk

The `gensyn-ai/axl` repository was made public on **April 15, 2026**, last pushed **April 23, 2026**, currently around 5 stars and 1 fork — it is two weeks old. **The org listing identifies the language as Go.** The license file was not retrievable in this research pass (other gensyn-ai repos default to MIT, but AXL's SPDX is unconfirmed). The directory tree below is **inferred from the build steps and the launch blog**; treat it as a starting hypothesis to verify with `git clone`, not a source of truth.

```
axl/
├── Makefile                  # `make build` → ./node binary
├── go.mod / go.sum           # NOT retrieved; pin versions unknown
├── README.md                 # NOT retrieved
├── LICENSE                   # SPDX unconfirmed (likely MIT)
├── node-config.json          # sample config consumed by ./node -config
├── cmd/node/main.go          # daemon entry point (inferred)
├── docs/
│   ├── api.md                # AUTHORITATIVE HTTP API reference (read first)
│   └── examples.md           # AUTHORITATIVE example index (read first)
└── examples/                 # at least four built-in demos:
    ├── ai-agent-collaboration  # MCP-based research-signal sharing
    ├── distributed-inference   # tensor exchange via msgpack
    ├── gossipsub               # pub/sub layered on /send + /recv
    └── convergecast            # tree aggregation over the spanning tree
```

The internal Go packages logically separate into **identity/keypair**, **Yggdrasil overlay binding**, **gVisor netstack glue**, **HTTP local bridge**, **MCP router** (dynamic register/deregister of services), **A2A server** (skill-based), **general message queue**, and a **topology service**. There is no published `.proto` file; the "transport envelope" the blog refers to for wrapping JSON-RPC bodies is internal and undocumented. The Gensyn-supplied **`gensyn-ai/collaborative-autoresearch-demo`** is the canonical end-to-end reference implementation for AXL — clone it before you write your own.

Sibling repos worth knowing: **`rl-swarm`** (1.7K stars, Python, MIT) is the RL training framework but does *not* document AXL as its transport — it uses its own libp2p/Hivemind-derived stack with `swarm.pem`. **`genrl`** is the underlying RL SDK. **`sapo`**, **`verde`**, and **`identity-vault`** as named in your brief **do not exist as separate repos** — SAPO is a paper (arXiv 2509.08721) executed inside GenRL, Verde is a refereed-delegation verification scheme implemented as RepOps inside the **REE (Reproducible Execution Environment)**, and identity is split between `rl-swarm-contracts` and the Gensyn L2 chain itself. Don't waste time looking for those repo names.

## Wire protocol and cryptographic primitives

| Layer | Mechanism | What's confirmed | What's a gap |
|---|---|---|---|
| Mesh routing | Yggdrasil dynamic spanning tree | Confirmed | Topology endpoint payload schema undocumented |
| TCP/IP | gVisor userspace netstack | Confirmed | — |
| Link transport | TLS on direct peering | Confirmed | Cipher suite, listener ports, multi-transport (TCP/QUIC/WS) defaults undocumented |
| Path encryption | Yggdrasil E2E (Ironwood session crypto, ed25519 + Curve25519/ChaCha20-Poly1305 upstream) | Confirmed *that* it is E2E | Exact handshake (no Noise pattern named), AEAD, KDF, FS granularity all undocumented at AXL layer |
| Identity | ed25519 keypair, peer ID = pubkey | Confirmed | Format of `node-config.json`, identity rotation path undocumented |
| Counterparty auth | Out-of-band public-key exchange | Confirmed (the docs literally say *"You share your public key with another person"*) | No CA, no on-chain registry, no signed attestation system at AXL layer |
| Discovery | Spanning-tree once you have any live peer; bootstrap is manual | Confirmed | No published Gensyn seed peers; no Kademlia DHT; mDNS not mentioned |
| Pubsub | **Not a primitive — only an example app** | Confirmed | Topic semantics, ACLs, retention undocumented |
| Group / private room | **None native** | Confirmed by absence | Application must implement its own group key agreement |
| Message envelope | Application-defined for `/send`; JSON-RPC for MCP/A2A | Confirmed | Internal transport envelope wrapping is opaque |
| Reliability | Unspecified | gap | At-most-once vs at-least-once, ordering, max payload size all unknown |
| Default API port | `localhost:9002` | Confirmed | Auth on the local HTTP API itself is **not** documented — anything on the host that can reach `:9002` can `/send` |

This is the most important table in the report: **AXL is a strong NAT-traversing E2E pipe between two known ed25519 peers, and nothing more.** Every other guarantee is yours to build.

## CEO + seven soldiers reference architecture

The architecture below assumes Gensyn-track victory is the priority and `0G` + `ENS` are stacked underneath without diluting AXL depth. Eight nodes total — one CEO, seven soldiers — each running its own AXL daemon in a separate container, communicating across the Yggdrasil mesh, with an application-layer group ratchet on top because AXL gives you no MLS.

```mermaid
flowchart TB
    subgraph ENS["ENS L2 subname tree (e.g., on Base)"]
        E0[ceo.codephreak.eth<br/>text: axl.pubkey=ed25519:...<br/>text: erc8004.id=42]
        E1[soldier1.codephreak.eth ... soldier7.codephreak.eth<br/>each with axl.pubkey + erc8004.id]
    end

    subgraph Reg["ERC-8004 IdentityRegistry on Base/Mainnet"]
        R0[agentURI per agent → JSON with<br/>endpoints:[{name:'AXL', pubkey, network:'yggdrasil'}]]
    end

    subgraph CEO["CEO node — Docker container 0"]
        C_app[CEO agent<br/>mindX Soul/Mind/Hands<br/>Group-key custodian]
        C_axl[AXL node<br/>localhost:9002<br/>peer_id = ed25519_C]
        C_app <-->|HTTP| C_axl
    end

    subgraph S1["Soldier 1..7 — Docker containers 1..7"]
        S_app[Soldier agent N<br/>mindX worker<br/>0G Storage memory<br/>0G Compute inference]
        S_axl[AXL node<br/>localhost:9002<br/>peer_id = ed25519_Sn]
        S_app <-->|HTTP| S_axl
    end

    subgraph Mesh["Yggdrasil mesh (E2E encrypted)"]
        M((spanning tree<br/>TLS hop + Ironwood E2E))
    end

    subgraph Storage["0G Aristotle L1"]
        OG_S[(0G Storage<br/>encrypted memory blob<br/>per soldier, key sealed by CEO)]
        OG_C[0G Compute<br/>sealed inference]
        INFT[ERC-7857 INFT per agent<br/>tokenURI → 8004 registration]
    end

    C_axl -.peer.-> M
    S_axl -.peer.-> M
    M -.E2E.-> C_axl
    M -.E2E.-> S_axl

    E0 -.resolves.-> R0
    E1 -.resolves.-> R0
    R0 -.endpoint.-> C_axl
    R0 -.endpoint.-> S_axl

    S_app -->|read/write encrypted| OG_S
    S_app -->|sealed inference| OG_C
    INFT -.owns.-> S_app
```

**Composition pattern.** The CEO holds eight pairwise AXL sessions — one with each soldier and one self-loop for clarity — plus a logical "group" abstraction the CEO synthesizes locally. The CEO is **the group-key custodian**: he generates a fresh symmetric **epoch key** $K_e$ on every meeting, sends it to each of the seven soldiers over their pairwise AXL channel (which is already E2E-encrypted by Yggdrasil), and from then on broadcasts use AES-GCM-with-$K_e$ wrapped inside `POST /send` calls to all seven peer IDs in a fan-out. Soldiers respond with reports on their pairwise channel; the CEO authenticates each report by source peer ID. Rotate $K_e$ at every meeting boundary or on detection of compromise. This gives you what AXL won't: **post-compromise security at the application layer, replay defense via $(epoch, seq)$ tuples in the AEAD AAD, and forward secrecy by deletion of $K_{e-1}$ after rotation.** It is a poor man's MLS, but for $N=8$ with a single trusted root it is sufficient and shippable in a hackathon week.

**Why not a tree topology with the CEO as root?** Yggdrasil already routes optimally on the underlying spanning tree; building an *additional* application-layer tree on top of it gains nothing for $N=8$ and costs you a hop of latency. Use star (CEO-centric pairwise sessions) for command and a CEO-broadcast for joint announcements.

**Why not gossipsub?** Gensyn's gossipsub is an *example app*, not a primitive — and broadcasting a trade-secret topic into a permissionless mesh is exactly the wrong privacy posture even with payload encryption, because the topic name itself becomes a metadata beacon. **Stay unicast.**

**Eight Docker containers, one host.** For the demo, run all eight AXL nodes on a single host with `docker compose up`, each container with its own `private.pem`, its own `:9002`, and a static peer list pointing at one designated bootstrap container. Containers satisfy the *"separate AXL nodes, not in-process"* qualifier because they each run their own daemon; the docs are explicit that this is what counts. For the video, also run two containers on a second laptop to demonstrate cross-machine routing.

**Discovery and naming.** Each agent gets an ENS subname under `codephreak.eth` (e.g., `ceo.codephreak.eth`, `soldier1.codephreak.eth`). The ENS subname carries a custom text record `axl.pubkey` whose value is the agent's hex-encoded ed25519 public key, plus `erc8004.id` referencing the agent's tokenId in the **ERC-8004 IdentityRegistry** (deployed on Base at `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`). The 8004 `agentURI` resolves to a JSON file whose `endpoints` array advertises `{name: "AXL", pubkey: "ed25519:…", network: "yggdrasil"}`. This solves the problem AXL's own launch blog calls out: *"none of these standards solve a more basic problem: how agents reach each other in the first place."* You answer it by composing ENS (human-readable) + ERC-8004 (registration) + AXL (transport).

**Memory and inference.** Each soldier persists its working memory as an encrypted blob on **0G Storage** (KV + Log), keyed under its ed25519 pubkey, with the symmetric storage key sealed to the CEO's pubkey so that revocation = CEO refuses to release the key. Sealed inference runs on **0G Compute** when a soldier needs to call a model. Optionally, mint each agent as an **ERC-7857 INFT** on 0G Chain so the encrypted "brain" (model weights, persona) is owned by an EVM key, and use the INFT's per-executor sealed-key mechanism to authorize a specific AXL daemon to execute the agent. This is a clean composition: **ERC-7857 owns the brain, ERC-8004 publishes the identity, ENS names it, AXL transports it.**

## Concrete CLI and code

These are the only verbatim snippets the docs provide; treat them as the floor.

**Bring an AXL node up:**

```bash
git clone https://github.com/gensyn-ai/axl
cd axl
make build
openssl genpkey -algorithm ed25519 -out private.pem
./node -config node-config.json
```

**The five HTTP endpoints exposed on `localhost:9002`:**

```
POST /send                       body: { "to": "<peer_id>", "data": <bytes> }
GET  /recv                       returns queued inbound messages
GET  /topology                   returns mesh peers / spanning-tree view
POST /mcp/{peer_id}/{service}    JSON-RPC body, MCP service call to remote peer
POST /a2a/{peer_id}              JSON-RPC body, A2A skill invocation on remote peer
```

**Conceptual client pattern from the docs:**

```
Your App → HTTP POST localhost:9002/send                          → AXL node → mesh
Your App ← HTTP GET  localhost:9002/recv                          ← AXL node ← mesh
Your App → HTTP POST localhost:9002/mcp/{peer_id}/{service}       (JSON-RPC body)
Your App → HTTP POST localhost:9002/a2a/{peer_id}                 (JSON-RPC body)
```

The wire-envelope schema, `node-config.json` schema, multi-transport listener URIs, default inbound peering port, max payload size, reliability semantics, and gossipsub topic format are all **not in the public docs** — you will need to read `docs/api.md`, `docs/examples.md`, and the `examples/` source in the repo to fill them in. The docs explicitly point you there; the launch blog links both files.

## Prize track decoded with strategic recommendations

The Gensyn track is a **$5,000 single ranked pool**: $2,500 / $1,500 / $1,000. All winners are **fast-tracked into the Gensyn Foundation grant programme** — that is arguably worth more than the cash. Two qualification rules, verbatim: *"Must use AXL for inter-agent or inter-node communication (no centralised message broker replacing what AXL provides)"* and *"Must demonstrate communication across separate AXL nodes, not just in-process. Project must be built during the hackathon."* Judging is on **depth of AXL integration, code quality, clear documentation, working examples** — three of the four are engineering-craft signals, which is unusual and high-leverage. The two suggested ideas are **"Agent Town"** (generative-agent sandbox with personalities) and **"Decentralised Agent Messaging"** ("Agent social networks, agent marketplaces, self-organising working groups"). Followed by *"Or something else entirely!"*

**Your project maps directly onto the Decentralised Agent Messaging bullet** — quote it in the README. The "self-organising working groups" sub-phrase is the precise framing for a CEO-coordinated worker swarm. The trade-secret protection narrative leans into AXL's only real differentiated value claim ("end-to-end encrypted by default, no central coordinator"). To turn this into a top-three finish: ship a `docker compose up` that brings 8 AXL nodes alive locally, add a tcpdump-comparison demo where a centralized-Redis baseline visibly leaks plaintext while the AXL version doesn't, include an architecture diagram in the README using Gensyn's own vocabulary (peer ID, topology, MCP, A2A), and write at least one MCP service registration so the project flexes Gensyn's built-in routers rather than only `/send`. The Foundation-grant fast-track means even a 3rd-place placement converts into a follow-on relationship — write the README accordingly.

**Past Gensyn ETHGlobal winners: there are none.** OpenAgents is Gensyn's debut as an ETHGlobal sponsor. There is no winner pattern to copy; judging signals come from the published rubric and the canonical reference implementation (`gensyn-ai/collaborative-autoresearch-demo`). Read that repo before you start.

**Stacking with 0G and ENS is permitted.** ETHGlobal's standard rule, verbatim: *"You can select up to 3 Partner Prizes during submission. If a partner has multiple tracks, you can be eligible for all of them while only counting as 1 Partner Prize."* That means **Gensyn + 0G + ENS = exactly 3 partner slots** while remaining eligible for **5 separate prize pools** (Gensyn AXL, 0G Framework, 0G Agents/INFT, ENS-for-AI, ENS Creative Use), with a theoretical max of roughly $25K. Realistic expectation: $5K–$10K combined if you place mid-tier across two of three. **0G demands a deployed contract address** (the iNFT mint plus a soldier-state contract); **ENS demands a functional demo with no hard-coded values** (live ENS resolution required during the demo video); both are fully compatible with the C2 architecture. The demo video must be **2–4 minutes, ≥720p, no AI voiceover** to satisfy ETHGlobal's standard rules and **under 3 minutes** to also satisfy 0G's specific rule — produce a 3-minute video to satisfy both. **Do not target Uniswap's track**; their `FEEDBACK.md` requirement is unrelated and would dilute focus.

**Strategic warning.** Gensyn's #1 criterion is *depth of AXL integration*. If 0G and ENS show up only as cosmetic add-ons, AXL depth scores will suffer. Make ENS the **discovery layer that resolves to AXL peer IDs**, and make 0G the **encrypted memory and inference substrate** that AXL transports messages between — both reinforce, rather than compete with, the AXL story.

## Integration matrix

The matrix below maps your existing stack against the AXL surface so you can see exactly where the wires go.

| Your component | Role in C2 architecture | AXL touch point | Notes |
|---|---|---|---|
| **mindX agents** (Soul/Mind/Hands) | The CEO and seven soldiers | App that POSTs to `localhost:9002/send` and polls `/recv`; registers MCP services per soldier role | mindX runs in the same container as one AXL node; A2A skill registration per agent role gives Gensyn judges the "depth" signal |
| **AgenticPlace identity registry** | Bootstrap and friend-list for the eight peer IDs | Off-chain mirror of ERC-8004 registry; on join, agent fetches the seven other peer IDs from AgenticPlace + verifies via 8004 + ENS text record | Use AgenticPlace as a faster cache; ERC-8004 as the canonical source |
| **BANKON soulbound IDs** | One-soulbound-token-per-agent ownership claim, treasury authorization | Issue an SBT per agent on Base; SBT tokenId is referenced inside the ERC-8004 `agentURI` JSON; CEO checks SBT ownership before accepting epoch-key handshake | SBTs are non-transferable, which fits the "you cannot impersonate another soldier" requirement |
| **ERC-8004 agent identity** | The on-chain registry pointing to AXL peer IDs | Agent registration JSON's `endpoints` array gets a custom `{name:"AXL", pubkey:..., network:"yggdrasil"}` entry | ERC-8004 is **Draft, not Final** as of April 2026, but reference contracts are live on Mainnet/Base/Sepolia at `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`. v2 work active; expect minor breaking changes |
| **0G Storage (replacing the imagined "0G THOT")** | Per-soldier encrypted long-term memory | Soldier writes encrypted blob; storage key sealed to CEO pubkey; key released over AXL pairwise channel under epoch-key wrapping | "THOT" doesn't exist publicly; use 0G Storage KV+Log directly via `@0glabs/0g-ts-sdk` |
| **0G Compute** | Sealed inference for soldiers needing model calls | Off the AXL critical path; soldier-internal | Adds 0G prize eligibility |
| **ERC-7857 INFT** | Optional ownership wrapper for each agent's encrypted "brain" | Per-agent INFT on 0G Chain; tokenURI references the ERC-8004 registration JSON | Fits the Autonomous Agents/iNFT 0G prize bucket; integrates the per-executor sealed-key model with AXL's ed25519 keypair via off-chain attestation |
| **ENS subnames** | Human-readable names for agents | `text(node, "axl.pubkey")` returns hex ed25519; `text(node, "erc8004.id")` returns tokenId | Avoid EIP-1577 multiaddr — still Draft, sparse tooling. Plain text records are reliable today |
| **openBDK 1+3 BFT consensus** | Validator-set side channel | Each validator runs an AXL node; off-consensus chat happens over a CEO-style epoch key shared among the 4 validators; consensus messages still flow through openBDK's normal path | AXL becomes the "off-band" channel; do NOT rewire openBDK consensus through AXL |
| **DELTAVERSE pre-vote deliberation** | Validator caucus before on-chain vote | Same epoch-key pattern; transcript hash optionally pinned to 0G Storage post-vote for audit | The fact that AXL leaves no relay logs is a feature here |
| **mindX dual CEO formations (16 agents)** | Two CEOs, two squads of seven | Two separate epoch keys (one per squad) plus a *third* "CEO-to-CEO" pairwise channel for cross-squad coordination | This is the natural scale-up of the architecture; the same AXL primitives compose |

## Gotchas, unknowns, and where you must read source

Eleven things are not in the public Gensyn docs and **will bite a hackathon team** if not surfaced early:

The cipher suite, KDF, AEAD, and forward-secrecy granularity at the Yggdrasil session layer are not specified by Gensyn — for a "trade-secret-grade" claim in your README, either read upstream `yggdrasil-network/yggdrasil-go` and Ironwood source, or qualify the claim. The **transport envelope schema** wrapping JSON-RPC bodies for MCP/A2A is opaque; the wire format will only be discoverable from `gensyn-ai/axl` source. **Authentication on `localhost:9002` itself is not documented** — by default it appears any process on the host can `/send`; if you're running multi-tenant, plan a reverse-proxy guard. The `node-config.json` schema is not published; live by example until you read the repo. **Bootstrap peer discovery** is left to the user; you must supply at least one publicly reachable peer when the mesh starts cold. **Reliability semantics, ordering, and max payload size for `/send`** are unspecified — chunk tensor payloads conservatively (the distributed-inference example uses msgpack, suggesting modest per-message budgets). **No native group/MLS** — your application-layer epoch ratchet is mandatory, not optional. **No Sybil resistance** — if the mesh is open, treat any peer ID you have not personally key-exchanged with as adversarial. **No anti-replay or anti-traffic-analysis** at the AXL layer; your AAD-with-(epoch, seq) is your only defense against replay, and your demo cannot claim hide-the-fact-of-talking. **AXL is not RL Swarm's transport** despite both being "Peer-to-Peer Communication" core components in Gensyn's diagrams — they are parallel primitives, and there is no documented unified API. **The repo is two weeks old**, has no tagged release, no security audit, and probably will see breaking changes before mainnet hardening; pin your build to a specific commit hash in the submission.

Two final action items before code: clone `gensyn-ai/collaborative-autoresearch-demo` and run it end-to-end as the canonical AXL client reference; and fetch `https://github.com/gensyn-ai/axl/blob/main/docs/api.md` and `examples.md` directly — those two files are the authoritative API reference and example index that public docs index pages defer to and that this research pass could not retrieve.

## Conclusion: positioning the submission

Treat AXL as **the encrypted backplane** and your project as **the application that proves AXL is the right backplane for confidential multi-agent coordination**. The CEO+seven-soldiers framing is structurally aligned with Gensyn's "Decentralised Agent Messaging — self-organising working groups" suggestion, and the trade-secret narrative is the strongest answer Gensyn's value prop has been asked to give. The architecture composes cleanly with 0G (memory + inference + INFT) and ENS (human-readable identity) without diluting AXL depth — provided you make ENS the discovery layer for AXL peer IDs and make 0G the substrate AXL transports between, rather than tacking them on. The single thing that separates a finalist submission from an honorable mention will be **demonstrable cross-host AXL traffic** with **MCP/A2A registration in use**, **a docker-compose 8-node spin-up** that judges can run in five minutes, and **a `tcpdump` comparison** that shows the centralized baseline leaks where AXL doesn't. Build that, write the README in Gensyn's own vocabulary, and the Foundation grant pipeline opens regardless of tier. The cap is three partner tracks; spend them on Gensyn, 0G, and ENS, in that priority order — and accept that Uniswap and KeeperHub stay off the table for this submission.