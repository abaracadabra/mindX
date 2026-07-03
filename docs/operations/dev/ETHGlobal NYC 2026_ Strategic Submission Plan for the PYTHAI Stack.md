# ETHGlobal NYC 2026: Strategic Submission Analysis for the PYTHAI/mindX/BANKON Stack

## TL;DR
- **Submit, but go all-in on the new Continuity Track.** ETHGlobal has officially changed its rules ("3 ways to hack: classic / extend an open source repo / ship a new feature to an existing product") and ETHGlobal New York (June 12–14, 2026, Metropolitan Pavilion, $200,000+ prize pool per @ETHGlobal's May 15, 2026 post) is explicitly the first IRL hackathon to host the Continuity Track — so the existing PYTHAI/mindX/BANKON/AgenticPlace stack can be entered legally for the first time. Lead with mindX + AgenticPlace as the spine.
- **Moonbeam is NOT a confirmed NYC 2026 sponsor and Moonbeam Elastic Scaling is not yet live** (it is the centerpiece of Moonbeam's March 31, 2026 roadmap, rolling out in three forward-looking phases targeting ~2-second block times). The "RAGE-to-elastic on Moonbeam" angle should be filed as a Q3/Q4 2026 play (Tokyo Sept 25–27 or Mumbai Q4), not the NYC headline. NYC should lead with **0G ($15K — ERC-7857 iNFT and OpenClaw/dAIOS) + ENS ($20K — agent identity per Coinpedia's NYC listing) + Gensyn ($5K AXL + Gensyn Foundation grant fast-track)**, plus Coinbase Developer Platform x402 if confirmed.
- **Sovereignty preserved, exposure maximized.** All recommended tracks are SDK/protocol integrations that wrap mindX rather than replacing it; none require hosted-service lock-in. Top three for Series A signal: 0G (whose dedicated **$20M Apollo AI Accelerator** launched March 17, 2026 explicitly funds decentralized AI infrastructure teams), ENS (universally-cited identity layer; every VC reads ENS finalists), and Gensyn (which states verbatim that "All winners are fast-tracked into the Gensyn Foundation grant programme").

---

## Key Findings

### 1. Event Confirmed: June 12–14, 2026, Metropolitan Pavilion, NYC

- **Dates:** Friday June 12 – Sunday June 14, 2026 (36-hour in-person hackathon). Announced by @ETHGlobal on Nov 24, 2025 as part of the 2026 IRL calendar: "Cannes — April 3-5; New York — June 12-14; Lisbon — July 24-26; Tokyo — September 25-27; Mumbai — Q4."
- **Venue:** Metropolitan Pavilion, 125 W 18th St, New York, NY 10011 (same venue as ETHGlobal NYC 2025). **Do not confuse with ETHConf 2026 (June 8–10) at the Javits Center** — that is a separate conference event; some third-party listings (Coinpedia, helloyellow.ai) conflate the two.
- **Prize pool advertised:** "$200,000+" per @ETHGlobal's May 15, 2026 X post ("ETHGlobal New York loading... [███░░░░░] 40% > start_date: 06.12.26 > prize_pool: $200,000+ > location: nyc"). Application deadline was May 29, 2026.
- **Judging rubric:** Technicality, Originality, Practicality, Usability, WOW Factor. Finalists present live; Partner Prizes are judged separately at sponsor booths or asynchronously.
- **Submission mechanics:** ETHGlobal Hacker Dashboard; 2–4 minute demo video, public GitHub repo, project description. **Up to 3 Partner Prizes per submission** (a sponsor with multiple sub-tracks counts as 1 toward the cap).
- **Finalist perks** (NYC 2025 precedent, NYC Finalists Pack): 1000 USDC per team member, $500 flight reimbursement for another 2026 hackathon, finalist hoodie, 10x faucet multiplier, $10,000 in AWS credits, discounted Pragma tickets.
- **ETHConf adjacency (June 8–10, Javits Center)** is decisive for investor exposure: confirmed speakers per cryptoevents.global include **Stani Kulechov (CEO, Aave), Sergey Nazarov (CEO, Chainlink Labs), Robbie Mitchnick (Global Head of Digital Assets, BlackRock), Shan Aggarwal (Chief Business Officer, Coinbase), Hayden Adams (Founder, Uniswap Labs), and Joe Lubin (CEO, Consensys).** Arrive a few days early and work the ETHConf hallway track for the Series A.

### 2. The Rule Change — Continuity Track (CRITICAL FOR PYTHAI)

ETHGlobal announced a rules overhaul via @ETHGlobal on X and an article by CEO Kartik Talwar titled **"We're Changing How Hackathons Work."** Verbatim from @ETHGlobal:

> "We're changing how hackathons work. Starting today, your project doesn't have to start at zero... We've got 3 ways to hack at ETHGlobal events: ↪︎ [classic] start from scratch ↪︎ [new] extend an open source repo ↪︎ [new] ship a new feature to an existing product"

And:

> "The first ever group of Continuity Track hackers will be at ETHGlobal New York on June 12-14! Join us ↓"

**This is the first ETHGlobal IRL hackathon to host the Continuity Track.** Practical implications:

- **mindX, AgenticPlace, BANKON, BONAFIDE, DELTAVERSE, RAGE, DAIO, Parsec/x402-avm — all can be entered.** Either as "extend an open source repo" (if their GitHub is public and Apache-2.0 / open) or as "ship a new feature to an existing product" (the live deployments at pythai.net qualify).
- **What still has to be done at the event:** The new feature shipped during the 36-hour window. The *deployment* of DAIO to mainnet, the *elastic-retrieval extension* of RAGE, a *new x402 endpoint* on AgenticPlace, or a *new BONAFIDE attestation type* are all valid Continuity submissions.
- **Caveat:** As of May 19, 2026 the ethglobal.com/rules page has NOT been updated and still carries the old "start from scratch" language ("We require everyone starts building from scratch... By using any pre-existing work (even after written approval), you forfeit the right to be considered for Partner prizes or as a finalist"). The Kartik Talwar announcement post supersedes this, but the canonical Continuity Track rules will be published on the NYC event's `/info/details` page — read it carefully on arrival day. A reasonable working assumption: full transparent disclosure of pre-existing work in the README, demo video, and judging conversations is mandatory; partner prizes are explicitly eligible (otherwise the Continuity Track would be meaningless).

### 3. Confirmed Sponsor Tracks at NYC 2026

The ethglobal.com/events/newyork2026/prizes page was returning HTTP 500 during research, so the table below combines (a) sponsors publicly indexed via Coinpedia's NYC 2026 partner listing, (b) sponsor channels (Arc community page, Ledger developer portal), and (c) historical NYC 2025 and Cannes 2026 patterns. The ~$115K residual relative to the advertised $200K+ pool means roughly half the sponsor list is still unannounced.

| Sponsor | Prize (NYC 2026) | Focus | PYTHAI Fit | Continuity-eligible? |
|---|---|---|---|---|
| **ENS** | $20,000 (per Coinpedia) | Identity layer, "Best ENS Integration for AI Agents" | **VERY HIGH** — bankon.eth subname registrar; CONCLAVE cabinet as ENS subname tree | Yes |
| **0G** | $15,000 (per Coinpedia) | dAIOS / OpenClaw / iNFT (ERC-7857) / 0G Storage+Compute+DA | **VERY HIGH** — direct match to mindX Soul/Mind/Hands; iNFT-minted agents | Yes |
| **Sui / Walrus** | $15,000 | Sui-native DeFi / Walrus storage | Medium — Walrus could host mindX checkpoints | Yes |
| **World (Worldcoin)** | $15,000 | World ID / Mini Apps | Medium — proof-of-personhood for AgenticPlace operators | Yes |
| **Uniswap Foundation** | $10,000 | v4 Hooks / Uniswap API / agentic finance | Medium — AgenticPlace agents that trade via Uniswap API | Yes |
| **Dynamic** | $10,000 | Embedded wallets, AI-on-Dynamic | High — wallet layer for AgenticPlace agents | Yes |
| **Ledger** | $10,000 ($10K bounty pool, 5 prizes) | "AI agents and AI-powered products that use Ledger as the trust layer" | High — hardware-anchored signing for sovereign mindX agents | Yes |
| **Circle (Arc)** | TBD (bounty track on Arc) | Stablecoins/payments on Arc testnet (chainId 5042002) | **VERY HIGH** — Gregory already has Arc chainId noted; BANKON payment layer fit | Yes |

**Cannes 2026 (April 3–5, the immediately preceding IRL event) confirmed sponsor list per HackerNoon's post-event article "0G Labs Sponsors ETHGlobal Cannes Hackathon And Supports $275K Prize Pool"** was: **LayerZero, 1inch, World, Oasis Protocol, Chainlink, Hedera, Ledger, Circle, The Graph, and 0G ($5K)** — total pool $275K. Notably absent at Cannes: Moonbeam, Coinbase Developer Platform, and Privy. The same lineup is the highest-probability baseline for NYC 2026 — meaning **LayerZero, Chainlink, The Graph, Hedera, and 1inch are likely (not yet confirmed) NYC 2026 sponsors**, while CDP/Privy presence remains genuinely uncertain. ENS at Cannes 2026 ran a $4,000 pool ("Best ENS Integration for AI Agents" $2,500 first / $1,500 second + a "Most Creative Use of ENS" prize) per crypto.news — Coinpedia's listed $20,000 at NYC 2026 would be a meaningful expansion if accurate.

### 4. Moonbeam: The Elastic-Scaling Angle Is Not Ready Yet

Per the Moonbeam Foundation's official "Moonbeam Roadmap 2026: Scaling for the Next Generation," published March 31, 2026:

> "The centerpiece of the 2026 roadmap is Elastic Scaling, a fundamental upgrade to Moonbeam's performance model. Elastic Scaling will roll out in phases: Step 1: Slot-Based Collators... Step 2: Fork-Free Parachains... Step 3: Elastic Scaling Activation — Enable parallel execution across multiple cores, Target: ~2 second block times."

Three important facts:

1. **Moonbeam's "Elastic Scaling" is a Polkadot 2.0 parachain throughput upgrade (parallel execution across multiple cores), not an Elasticsearch-style retrieval primitive.** This is *different from* what RAGE-to-elastic conceptually means (horizontal-scale vector/retrieval indexing). The semantic overlap is coincidental. Re-positioning RAGE elasticity as "ride Moonbeam's elastic scaling wave" would be a marketing stretch, not a technical match.
2. **Moonbeam Elastic Scaling is not live on mainnet or testnet as of May 19, 2026** — all three phases are described as future work in the official roadmap.
3. **Moonbeam is NOT a confirmed sponsor at ETHGlobal NYC 2026** (and was not at Cannes 2026 or HackMoney 2026 either). Moonbeam's 2026 ecosystem focus per its own roadmap is gaming. Per CoinsHolder's coverage of the October 27, 2025 @MoonbeamNetwork announcement, the HELLO Labs × Moonbeam Accelerator **"offers a $30,000 grant from the Moonbeam Foundation, up to $50,000 in milestone-based growth budgets, and developer support from the Moonbeam tech team,"** spanning six milestones over six months — this is the Moonbeam funding lane to consider, but it's gaming-focused, not RAG/AI-agent-focused.

**Recommendation: Do NOT lead the NYC submission with a Moonbeam Elastic angle.** It is a fabricated track. If Gregory wants to develop the elastic retrieval angle, the correct ETHGlobal venue is the async circuit (ETHOnline) or a direct Moonbeam Foundation grant application after their Elastic Scaling Phase 1 ships. For NYC, the closest legitimate analog to elastic retrieval in the ETHGlobal sponsor stack is **The Graph (Token API / Subgraphs / Substreams + MCP)** if they sponsor (they did at NYC 2025 with $10K and at Cannes 2026).

### 5. Sponsor Deep Dives Most Relevant to PYTHAI

**0G Foundation — $15,000 (highest-fit single sponsor):**
At the Open Agents async event 0G ran a $15K track split into "Best Agent Framework, Tooling & Core Extensions" ($7,500, 5 tiers) and "Best Autonomous Agents, Swarms & iNFT Innovations" ($7,500). Verbatim from 0G's track text: "Build the best core extensions, improvements, forks, or entirely new open agent frameworks inspired by OpenClaw... Focus on advancing how agents are created in 2026 — architectures, developer tooling, and infrastructure primitives that other builders will use." Their qualification calls out: "Self-evolving agent framework that autonomously generates/tests/integrates new skills/tools using persistent 0G Storage memory" and "iNFT-minted agents with embedded intelligence (encrypted on 0G Storage), persistent memory, dynamic upgrades, and automatic royalty splits on usage."

This is the **highest-fit single sponsor for mindX**. Soul/Mind/Hands maps cleanly onto persistent memory (0G Storage KV/Log) + sealed inference (0G Compute) + iNFT-minted identity (ERC-7857). 0G's separately-announced **$20M Apollo AI Accelerator** (per GlobeNewswire, March 17, 2026: *"$20M Apollo AI Accelerator launched with Stanford blockchain veterans to fund teams building on decentralized AI infrastructure"*) is the most credible follow-on funding pipeline at the entire event for a sovereign-agent thesis. (Note: 0G's Apollo is distinct from the ASI Alliance's ASI:Cloud product, which launched September 23, 2025 and is run by SingularityNET/CUDOS/Fetch.ai — don't conflate the two ecosystems.)

**ENS — $20,000 (highest-fit identity track):**
ENS's official agent-track wording (used at recent ETHGlobal events): "AI agents need persistent, human-readable identities too. Build a functional project where ENS is the identity mechanism for one or more AI agents. ENS should be doing real work — resolving the agent's address, storing its metadata, gating access, enabling discovery, or coordinating agent-to-agent interaction." Gregory already operates `bankon.eth` and has a subname registrar; CONCLAVE's CEO + 7 Counsellors pattern is a textbook ENS subname-as-cabinet implementation. **Stack 100% with the 0G track** — name your 0G iNFT agents via ENS subnames. Note: Coinpedia lists $20K for ENS at NYC 2026; if the actual prize page (when restored) shows the smaller $4K Cannes pattern instead, the absolute prize is lower but the fit and exposure are unchanged.

**Gensyn — $5,000 (AXL already integrated in CONCLAVE):**
Gensyn at Open Agents: "AXL is our peer-to-peer network node... AXL ships with built-in MCP and A2A support for structured agent-to-agent communication, and everything is end-to-end encrypted by default... Must use AXL for inter-agent or inter-node communication (no centralised message broker replacing what AXL provides). Must demonstrate communication across separate AXL nodes." CONCLAVE already uses AXL — a deeper end-to-end demo (multiple sovereign mindX nodes coordinating via AXL across geos) is a natural submission. **Critical bonus, verbatim:** "All winners are fast-tracked into the Gensyn Foundation grant programme." Direct follow-on funding pipeline for the Series A narrative.

**Coinbase Developer Platform — up to $20,000 (x402 is core to Gregory's stack):**
CDP's pattern at NYC 2025 and Buenos Aires 2025: "Build a Great Onchain App Using CDP" with Onramp, CDP Wallets (Server/Embedded), CDP Data APIs, and x402 as qualifying tools, a $20K pool. Their workshop is literally called "Agent Bootcamp with x402: Build a wallet-aware AI app that pays for the APIs it uses." Gregory's Parsec/x402-avm work is uniquely positioned to bridge x402 across EVM and Algorand. **Submission angle:** AgenticPlace agents that pay for APIs they consume using x402 over both Coinbase's EVM endpoints and Parsec's Algorand x402 implementation — a cross-VM x402 demo, which has not been done before. **CRITICAL CONTINGENCY: CDP was NOT a Cannes 2026 sponsor. Confirm CDP at NYC before locking this in.** If absent, this angle moves to ETHOnline async.

**LayerZero — $20,000 (Cannes 2026 sponsor; high-probability NYC):**
At NYC 2025: "Best Omnichain Interaction" ($12,500) + "Best Omnichain DeFi Primitive" ($7,500). The "Omnichain Governance: Allowing a DAO on one chain to control contracts or treasuries on others" example is literally the DAIO design (Algorand constitutional layer controlling EVM economic layer). **Strong fit for DAIO deployment as a Continuity Track submission.** DELTAVERSE currently uses Wormhole — if LayerZero sponsors NYC, the DAIO submission is the cleaner LayerZero candidate, not DELTAVERSE.

**Chainlink — $10,000 (Cannes 2026 sponsor; high-probability NYC):**
At NYC 2025: "Best usage of Chainlink CCIP and/or CCT — $4,000" + "Connect the World with Chainlink — $6,000." Qualification: "Each project must use Chainlink CCIP and/or CCT Standard in some form to make a state change on a blockchain." A Chainlink Functions integration to the BitcoinAnchorOracle, or a CCT for a DELTAVERSE debt-inheritance token, is a tight fit.

**Dynamic — $10,000 (embedded wallets for AgenticPlace):**
NYC 2025 tracks: "Best Financial App," "Best Consumer App," "Best App Involving AI" — all $3,333 each. Verbatim AI qualification: "Must incorporate an AI component (e.g. LLMs, autonomous agents, recommendation systems, or generative models) that drives some part of the user experience or app logic." Trivial wrapper integration with strong VC distribution.

**The Graph (Cannes 2026 sponsor; likely NYC):**
"Best Use of The Graph Token API, Subgraphs, Substreams, or AI MCPs — $5,000" and "Best Application Built on Hypergraph — $4,000." This is the *legitimate* "elastic retrieval" wrapper for RAGE — Substreams + Token API MCP gives mindX agents a horizontally-scaled blockchain-data retrieval layer. **This, not Moonbeam, is the actual elastic-retrieval play at NYC 2026.**

### 6. Identity / Attestation / KYC Fit (for BONAFIDE)

- **ENS** as above — primary identity track.
- **World (Worldcoin) — $15,000** at NYC 2026: proof-of-personhood that gates which humans can operate which sovereign mindX agents. BONAFIDE's nine-contract Latin-named attestation suite can attest to World-ID-verified agent operators. **Caveat:** World ID requires Worldcoin's Orb infrastructure for the human verification step, which is a hosted dependency — preserve sovereignty by making the World ID layer optional rather than required for the agent.
- **Sign Protocol / EAS** — not confirmed for NYC 2026; if present, BONAFIDE is a direct mapping.

### 7. DeFi / Sovereign Debt / Stablecoin Fit (for DELTAVERSE & DAIO)

- **Circle (Arc)** — Gregory already has Arc Testnet chainId 5042002. A DELTAVERSE Arc deployment with CCTP V2 for multichain debt-inheritance transfers, plus Circle Paymaster so heirs pay gas in USDC (USDC ASA ID 31566704 on the Algorand side), is a tight fit.
- **PayPal USD** (NYC 2025: $10K; presence at NYC 2026 unconfirmed) — PYUSD-denominated debt instruments in DELTAVERSE.
- **Katana / agglayer** (NYC 2025: $10K) — DeFi-sector L2 with "the more primitives you integrate with, the better" judging criterion.
- **DAIO mainnet deployment is the cleanest single Continuity Track submission for novel governance.** Deploy the Algorand constitutional layer + EVM economic layer + openBDK bridge during the 36 hours, submit to LayerZero (omnichain governance) and Chainlink (oracle for cross-chain state).

### 8. Cross-Chain / Interop

- **LayerZero $20K (high-probability NYC sponsor)** — primary cross-chain target. Omnichain Governance = DAIO.
- **Hyperlane** (NYC 2025: $10K) — permissionless interop; could relay CONCLAVE coordination messages.
- **Wormhole** — already in DELTAVERSE; if they sponsor NYC 2026, submit the existing cross-chain debt flow as a Continuity Track entry.
- **Axelar** — has historically run Moonbeam joint hackathons; unlikely to sponsor NYC standalone.

---

## Details — Strategic Submission Plan

### Top 5 Tracks Ranked for Strategic Fit

| Rank | Track | Prize | Why | Sovereignty Risk |
|---|---|---|---|---|
| 1 | **0G Foundation — agent framework + iNFT** | $15,000 + 0G Apollo Accelerator pipeline ($20M fund) | Direct architectural match to mindX Soul/Mind/Hands; iNFT (ERC-7857) for monetizable sovereign agents; 0G is the most aggressive AI-L1 funder in 2026. | Low — 0G storage/compute can be optional adapter, not core. |
| 2 | **ENS — agent identity** | $20,000 (per Coinpedia listing) | bankon.eth already exists; CONCLAVE cabinet pattern is the textbook ENS subname tree; trivial stacking with every other track. Most-watched identity track in Web3. | Zero — ENS is purely additive. |
| 3 | **Gensyn — AXL multi-node** | $5,000 + Gensyn Foundation grant fast-track | CONCLAVE already uses AXL; deeper demo (multi-region sovereign nodes coordinating) is a 36-hour deliverable; **explicit, verbatim fast-track to Gensyn Foundation grant programme**. Best non-cash follow-on. | Zero — AXL is peer-to-peer by design; sovereignty-preserving. |
| 4 | **LayerZero — Omnichain Governance for DAIO** | up to $20,000 (Cannes 2026 sponsor; high-probability NYC) | DAIO's dual-chain (Algorand constitutional + EVM economic via openBDK) is the textbook LayerZero "DAO on one chain controlling treasuries on others" example. **DAIO mainnet deployment is THE Continuity Track headline.** | Low — LayerZero V2 is messaging only; doesn't constrain governance logic. |
| 5 | **Coinbase Developer Platform — x402 cross-VM** | up to $20,000 (CONTINGENT on NYC sponsorship) | Gregory's Parsec/GoPlausible x402-avm work demonstrates EVM↔Algorand x402 bridging — genuinely novel. Coinbase Ventures = best Series A signal. **Confirm CDP sponsorship before locking this in; CDP was absent from Cannes 2026.** | Low — CDP SDKs are wrappers, not replacements. |

### Tracks to Stack on the Same Submission

The 3-Partner-Prize cap means each submission can target 3 sponsors. Two coherent submission packages:

**Submission A — "Sovereign Agent Cabinet" (mindX + AgenticPlace + CONCLAVE):**
- 0G (iNFT-minted mindX agents with persistent 0G Storage memory + sealed 0G Compute inference)
- ENS (CONCLAVE cabinet as ENS subname tree under bankon.eth: ceo.bankon.eth + counsellor1.bankon.eth ... counsellor7.bankon.eth)
- Gensyn (AXL peer-to-peer mesh between the cabinet members across distinct sovereign nodes)
- **New work to ship in 36h:** ERC-7857 iNFT minting flow for each cabinet role; ENS subname auto-issuance on agent spawn; AXL multi-node deployment demo.

**Submission B — "DAIO Mainnet" (governance Continuity Track headline):**
- LayerZero (omnichain DAO control flow: Algorand constitutional layer → EVM economic layer)
- Chainlink (oracle feed for cross-chain state attestation between Algorand and EVM)
- Coinbase Developer Platform / x402 — IF confirmed at NYC (governance-token payments via x402 — agents pay for proposal submissions)
- **New work to ship in 36h:** Foundry test suite green; deploy DAIO governance contracts to testnets (Sepolia + Algorand testnet) and demonstrate one end-to-end proposal-to-execution cross-chain via openBDK + LayerZero relay. **Skip mainnet during the event** — leave that for the week after, but show the deploy script + verified testnet deployment.

Two parallel submissions is feasible — one team can submit multiple genuinely distinct projects.

### Where NOT to Submit (Risk Flags)

- **Moonbeam** — not a sponsor at NYC 2026; the "elastic" angle is semantic-only, not technical.
- **Worldcoin/World ID alone as primary track** — hosted Orb dependency; usable as augmentation but does not preserve sovereign architecture as the lead.
- **OpenSea MCP** (if they sponsor) — requires writing your project to depend on OpenSea's beta MCP server; sovereignty risk medium.
- **Privy / Dynamic as lead** — wallet SDKs are easy wrappers but a mindX-as-wallet-wrapper submission undersells the cognition architecture. Use Dynamic as a secondary track at most.
- **Nora (AI coding tool, $5K at NYC 2025)** — they may require you to use their tool throughout development, which conflicts with mindXtrain/automindXtrain checkpoint development. Skip.
- **Lit Protocol's Vincent** — requires building inside the Vincent delegation framework, which means agent authority lives in Lit's network rather than mindX's Soul/Mind/Hands. Architectural conflict; avoid.

### Series A / Google for Startups Exposure Map

Three sponsors at NYC 2026 give meaningful follow-on signal for the $3–5M Series A:

1. **0G Foundation → 0G Apollo AI Accelerator ($20M fund, Stanford blockchain veterans, March 17, 2026 launch, decentralized AI infrastructure thesis).** This is the single best-aligned check at the event for sovereign-agent architectures.
2. **Gensyn Foundation Grant Programme.** Explicit, in the Gensyn track text: "All winners are fast-tracked into the Gensyn Foundation grant programme." Cleanest non-dilutive bridge between hackathon and seed/Series A.
3. **Coinbase Developer Platform → Coinbase Ventures** (if CDP confirms at NYC). CV is also a logical Google for Startups co-investor since Coinbase is a Google Cloud customer.

Secondary exposure:
- **Circle** — direct Series A involvement is rare, but Arc sponsorship + Circle's war chest = strong logo for the deck.
- **Uniswap Foundation** — grant program for protocol contributors.
- **Dynamic** — connects to FinTech Collective network.

ETHConf 2026 (Javits Center, June 8–10) is the higher-density Series A venue. With **Stani Kulechov (Aave), Sergey Nazarov (Chainlink Labs), Robbie Mitchnick (BlackRock Digital Assets), Shan Aggarwal (Coinbase CBO), Hayden Adams (Uniswap Labs), and Joe Lubin (Consensys)** all on the speaker roster, Series A conversations happen in hallways, not just at sponsor booths. **Arrive June 7 and work ETHConf before the hackathon kicks off.**

---

## Recommendations

### Immediate (this week, before/during arrival in NYC June 11)

1. **Confirm Continuity Track terms** on the official NYC 2026 event page (ethglobal.com/events/newyork2026/info/details) as soon as it returns from its 500 error. Specifically verify: (a) disclosure requirements, (b) partner-prize eligibility for Continuity submissions, (c) version-control requirements for pre-existing repos.
2. **Confirm the full NYC 2026 sponsor list.** Specifically check whether Coinbase Developer Platform, LayerZero, Chainlink, The Graph, Pyth Network, Polygon, Algorand Foundation, and Wormhole are confirmed. The above plan assumes LayerZero + Chainlink confirm (high probability per Cannes 2026 pattern) and CDP is contingent — if CDP is absent, swap Submission B's third slot to Hyperlane or Circle.
3. **Polish two READMEs** (Submission A "Sovereign Agent Cabinet" and Submission B "DAIO Mainnet") in advance — Continuity Track requires explicit disclosure of what was done before vs. during the event. Have the diffs ready.
4. **Pre-stage the ENS subname registrar contracts** so that during the event you can demonstrate live agent-spawn → ENS subname auto-issuance flow.
5. **Apply for the 0G Apollo AI Accelerator and the Gensyn Foundation grant in parallel** before NYC — both applications are independent of the hackathon outcome and give second shots at the same money.

### During the 36 Hours (June 12–14)

- **Hour 0–6:** Submission B (DAIO testnet deploy via Foundry + LayerZero + Chainlink oracle) — most contained scope; lock in the LayerZero/Chainlink partner-prize targets early.
- **Hour 6–24:** Submission A (0G iNFT minting for cabinet roles + ENS subname tree + AXL multi-node deployment).
- **Hour 24–30:** Demo video recording for both submissions (separate teams of mindX agents can narrate them).
- **Hour 30–36:** Booth visits to 0G, ENS, Gensyn, LayerZero, Chainlink, and CDP (if present) — these are the partner-prize judging conversations and the Series A introduction window.

### Thresholds That Would Change This Plan

- **If Moonbeam Elastic Scaling Phase 1 ships on Moonbase Alpha before June 12:** Re-evaluate adding a Moonbeam submission at the async ETHGlobal Tokyo (Sept 25–27) or Q4 Mumbai event — not NYC.
- **If CDP is not a NYC 2026 sponsor:** Move Submission B's third slot to Hyperlane + Circle; move the x402 cross-VM angle to ETHOnline async.
- **If 0G is not a NYC 2026 sponsor:** Move Submission A's lead to ENS + Gensyn + Dynamic. The iNFT angle becomes an ETHGlobal Lisbon (July 24–26) target where 0G is more likely to return.
- **If the Google for Startups $350k credit closes before June 12:** Lead booth conversations with Google Cloud + AWS multi-cloud sovereignty story, since Google for Startups + AWS credits stack to ~$360k in unrestricted compute — the strongest Series A bridge narrative.

---

## Caveats

1. **The full sponsor/prize list for NYC 2026 was not retrievable** — ethglobal.com/events/newyork2026/prizes returned HTTP 500 during the research window. The 8 sponsors confirmed via secondary sources (Coinpedia, Arc community page, Ledger developer portal) account for roughly $85K–$95K of the advertised $200K+ pool; the remaining ~$105K+ is unconfirmed. The Top-5 ranking is contingent on the Cannes 2026 sponsor list (LayerZero, Chainlink, The Graph) carrying into NYC, which is high-probability but unverified.
2. **Continuity Track rules have not been codified at ethglobal.com/rules** as of May 19, 2026 — the old "start from scratch" language is still live. The Kartik Talwar announcement and ETHGlobal's X posts are the primary sources. Watch for the official rules update before submitting.
3. **Moonbeam claims:** Moonbeam Elastic Scaling is *announced* and *roadmapped* for 2026 in three phases, but no phase has shipped per the official March 31, 2026 Moonbeam Foundation post. Treat any "Moonbeam elastic is live" claim as unverified until the foundation announces Phase 1 activation. The HELLO Labs × Moonbeam Accelerator ($30K grant + up to $50K milestone-based growth budgets over six months) is gaming-focused, not AI-agent-focused.
4. **0G Apollo vs. ASI:Cloud disambiguation:** 0G's $20M Apollo AI Accelerator (March 17, 2026, GlobeNewswire) is separate from the ASI Alliance's ASI:Cloud product (SingularityNET/CUDOS/Fetch.ai, September 23, 2025) — don't conflate the two when pitching.
5. **Venue conflict in third-party listings:** Coinpedia and helloyellow.ai list "Javits Center"; icoholder.com and the 2025 precedent list "Metropolitan Pavilion." ETHConf 2026 (June 8–10) is at Javits; the hackathon (June 12–14) is at Metropolitan Pavilion. Confirm on arrival.
6. **Cannes 2026 prize pool was $275K, not $300K+** (per HackerNoon's confirmation), suggesting NYC's "$200K+" advertised figure is realistic — likely $200–250K rather than $275K, since NYC has historically had a larger pool than Cannes but mainstream-cycle 2026 hackathon budgets have compressed slightly. Don't assume $300K+.
7. **Some sponsor prize amounts** (e.g., ENS $20K, World $15K per Coinpedia) are sourced from a third-party event listing and have NOT been independently corroborated by the ETHGlobal prize page. If the official page when restored shows different amounts (e.g., ENS at the $4K Cannes pattern), the strategic fit ranking is unchanged but absolute prize stacking math shifts down by ~$20K.
8. **The DAIO mainnet deployment, if attempted at the event, carries genuine execution risk** (mainnet deploys during a hackathon are routinely botched by gas spikes, RPC instability, or last-minute audits). The recommendation is testnet deployment during the 36 hours with mainnet deploy scheduled for the following week — this still earns the "shipped a new feature to an existing product" Continuity Track status.
9. **Partner-prize eligibility for Continuity Track is the single biggest open question.** If ETHGlobal mirrors the new rules to allow Continuity submissions to win partner prizes (most likely interpretation given the entire point of the change is to make existing projects competitive), the plan above stands. If they restrict Continuity to a non-partner-prize-eligible carve-out (less likely but possible), the entire strategy reduces to "ship the smallest possible new module on top of mindX as a 'classic from scratch' track and disclose it as built on top of pre-existing private infrastructure." **Confirm before NYC.**