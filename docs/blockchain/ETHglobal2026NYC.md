# PYTHAI × ETHGlobal New York 2026: Integrated Build-and-Deployment Plan

## TL;DR
- **Build one integrated demo — an ERC-8004 agent marketplace where mindX agents transact via x402 USDC nanopayments, identity-anchored in ENS subnames under the mainnet-confirmed `bankon.eth`, with high-value DAIO directives gated by Ledger** — and submit it across three mutually reinforcing tracks: **Arc "Best Agentic Economy with Nanopayments" ($3,250), Ledger "AI Agents x Ledger" ($10,000), and ENS ($20,000)**. This is the maximum-capture, minimum-divergence path because all three reward exactly what AgenticPlace + mindX + BANKON already are.
- **The strategic anchor is already on mainnet**: ERC-8004 (Trustless Agents) went live on Ethereum mainnet on January 29, 2026 at the Identity Registry vanity address `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`; AgenticPlace already indexes 126,336 agents across 48 chains against it, and `bankon.eth` is confirmed live on Ethereum mainnet (resolves to contract `0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169`, expiry 2027-04-20). The hackathon work is to deploy the DAIO governance/treasury layer that sits on top of this anchor.
- **Deploy the DAIO with Foundry, mainnet-only, immutable**: anchor governance on Ethereum mainnet, mirror identity/governance to Base, Optimism, Arbitrum, Linea, Polygon and 0G using Hyperlane for message mirroring (CCIP reserved for high-value finalization), make BANKON an xERC20 (EIP-7281) sovereign bridged token, route treasury USDC via Circle CCTP + ERC-7683 intents, and meter agent inference with a chain-neutral x402 paywall that settles on either EVM (USDC) or Algorand (USDC ASA, via GoPlausible x402-avm).

---

## 1. Executive Summary — The Strategic Opportunity

ETHGlobal New York 2026 (sponsor prize pool led by Google Cloud and ENS at $20,000 each) is unusually well-aligned with the PYTHAI ecosystem because **the dominant theme across the EVM-focused sponsors is the autonomous agent economy and agent-to-agent payments** — exactly the problem AgenticPlace, mindX and BANKON already address in production.

The single most important fact for prioritization: **AgenticPlace is built on ERC-8004 (Trustless Agents)**, the Ethereum standard for on-chain agent identity, reputation and validation. Per Eco's support documentation: *"As of January 29, 2026, ERC-8004 went live on Ethereum mainnet, marking a significant milestone in the development of decentralized AI infrastructure."* The standard was authored by Marco De Rossi (MetaMask), Davide Crapis (Ethereum Foundation), Jordan Ellis (Google) and Erik Reppel (Coinbase), and audited by Cyfrin, Nethermind and the Ethereum Foundation Security Team. AgenticPlace already indexes 126,336 ERC-8004 agents across 48 chains, extends them with Algorand-native NFT types (aNFT/dNFT/iNFT/THOT), and adds an oracle-attestation layer (agenticORacle/aORC). This means the team arrives at the hackathon **not as a greenfield builder but as an existing operator of ERC-8004 infrastructure** — the strongest possible position for the agent-economy bounties.

Three bounties reward this directly and can be satisfied by a **single integrated submission**:
1. **Arc (Circle's EVM L1) — "Best Agentic Economy with Nanopayments"**: explicitly asks for "autonomous AI agents to transact with each other using nanopayments" for "API calls, LLM inference, data access per-use" and "agent marketplaces with gas-free microtransactions." Circle's Nanopayments product is built directly on x402 for sub-cent USDC transactions (per The Defiant, April 2, 2026), confirming the bounty maps to x402-metered agent inference — a verbatim description of AgenticPlace + mindX.
2. **Ledger — "AI Agents x Ledger" ($10,000, five prize places)**: explicitly asks for "agents that pay for APIs, tools, or services with Ledger-secured payment flows, including x402-style patterns" and "Ledger-backed identity … for autonomous systems." x402 is named in the bounty text.
3. **ENS ($20,000)**: BANKON already issues ENS subnames under `bankon.eth` (confirmed on mainnet). Agent identities as `agent.bankon.eth` subnames is a native ENS identity use case.

The recommended posture is to **win the agent-economy money (Arc + Ledger) with certainty, and position for the large ENS pool** while shipping the genuinely novel infrastructure piece — the cross-chain DAIO governance mirror — as the architectural backbone that ties the demo together.

---

## 2. ETHGlobal NY 2026 Prize-Track Matrix (EVM/Ethereum priority)

All sponsor names and prize amounts below are taken directly from the live prize page. Several large sponsors (Google Cloud, ENS, World, Chainlink, Canton, Dynamic, Privy) list "Prize details coming soon," so their qualification requirements are not yet published — this is flagged explicitly and must be re-checked before the event.

| # | Sponsor / Bounty | Prize | PYTHAI component that satisfies it | Qualification requirements | Effort | Priority |
|---|---|---|---|---|---|---|
| 1 | **Arc — Best Agentic Economy with Nanopayments** | $3,250 (1st $2,150 / 2nd $1,100) | AgenticPlace agent marketplace + mindX inference metered by x402 USDC nanopayments (agent-to-agent commerce) | Working frontend+backend, architecture diagram, video demo + presentation, GitHub/Replit repo, state which bounty | Low–Med (exists) | **P0** |
| 2 | **Ledger — AI Agents x Ledger** | $10,000 (5 places: $3,000/$2,500/$2,000/$1,500/$1,000) | mindX autonomous agents paying via x402 with Ledger as the device-backed approval/identity control layer for high-value DAIO directives | Concrete Ledger primitives (not just branding); clear autonomy/approval boundaries; feedback on Ledger docs/SDKs with screenshots/PRs | Med (new Ledger integration) | **P0** |
| 3 | **ENS** | $20,000 | BANKON ENS subname issuance under mainnet `bankon.eth`; agent identity as `agent.bankon.eth`; primary-name + text records for agent metadata | "Details coming soon" — UNKNOWN, re-check | Low–Med (exists) | **P1 (high value, unknown criteria)** |
| 4 | **Arc — Best Chain Abstracted USDC Apps (Arc as liquidity hub)** | $3,250 (1st $2,150 / 2nd $1,100) | DAIO cross-chain treasury moving USDC across chains via Arc as liquidity hub (CCTP + Gateway + Bridge Kit) | Working frontend+backend + diagram, video, repo | Med | **P1** |
| 5 | **Chainlink** | $10,000 | CCIP as the high-value cross-chain governance/treasury finalization rail for the DAIO mirror | "Details coming soon" — UNKNOWN | Med | **P2** |
| 6 | **LI.FI** | $15,000 | Bridge/DEX aggregation for DAIO cross-chain mirror routing | "Details coming soon" — UNKNOWN | Med | **P2** |
| 7 | **Hedera** | $15,000 | ERC-8004 agent registry on Hedera (EVM) + x402; Hedera supports HCS-14 UAIDs and x402 | "Details coming soon" — UNKNOWN | Med | **P2** |
| 8 | **Arc — Best Smart Contracts on Arc (advanced stablecoin logic)** | $3,250 (1st $2,150 / 2nd $1,100) | DAIO programmable treasury: conditional escrow / agent vesting / multi-step settlement in USDC/EURC | Working frontend+backend + diagram, video, repo | Med | **P2** |
| 9 | **Uniswap Foundation — Best Uniswap Stack Contribution** | $3,000 (1st $2,000 / 2nd $1,000) | Optional: agent treasury rebalancing via Uniswap v4 hook | TxIDs of real onchain execution, public repo + README, ≤3-min video, Uniswap feedback form | Med | **P3** |
| 10 | **Uniswap Foundation — Best Uniswap API Integration** | $7,000 (1st $4,000 / 2nd $2,000 / 3rd $1,000) | Agent-driven swaps via Uniswap API — **NOTE: Continuity Track participants only** | API key + TxIDs + repo + ≤3-min video + feedback form | Med | **P3 (eligibility-gated)** |
| 11 | **1inch — Build an Aqua App** | $5,000 (1st $2,500 / 2nd $1,500 / 3rd $1,000) | Weak fit (DeFi position primitives via SwapVM) | Onchain token-transfer demo (local OK), proper git history (no single-commit) | High | **P4** |
| 12 | **Dynamic / Privy / Blink / Unlink** | $10k / $5k / $5k / $5k | Wallet onboarding / funding / privacy SDKs — peripheral to core thesis | Mostly "coming soon"; Blink requires a working deposit flow + demo video | — | **P4** |
| 13 | **Sui** | $15,000 | Non-EVM (Move) — out of scope for EVM focus | — | — | **Skip** |

---

## 3. Recommended Primary Build Target(s)

**Build ONE demo that satisfies bounties #1, #2 and #3 simultaneously.** The judges reward overlapping properties, and the PYTHAI stack already spans them.

**The demo ("Agentic DAIO on Arc"):**
- An AgenticPlace marketplace view of ERC-8004 agents (already live), with a mindX agent exposed as a paid service.
- A consumer/agent calls the mindX inference endpoint → receives HTTP 402 → pays a USDC nanopayment on Arc (Circle's EVM L1) → receives the result. This is **agent-to-agent / pay-per-inference commerce** → satisfies **Arc Nanopayments (#1)**.
- The paying agent's identity is an ERC-8004 NFT with an EIP-6551 token-bound account as its wallet; high-value DAIO governance directives (e.g., treasury spend above a threshold) require **Ledger device approval** before funds move → satisfies **Ledger AI Agents (#2)**.
- Each agent has a human-readable ENS subname `agent.bankon.eth` with text records pointing to its MCP/A2A endpoints → satisfies **ENS (#3)**.

**Why this wins:** It is real (ERC-8004 + AgenticPlace are in production), it is novel (cross-chain DAIO governance with device-gated agent spending), and it is demo-able in three minutes. The Arc Nanopayments bounty is the single highest-probability win because the bounty text reads like AgenticPlace's product description, and x402 — the rail it depends on — is now battle-tested: Coinbase reported "69,000 active agents, 165 million transactions, and approximately $50 million in cumulative volume on x402 by late April 2026" (Eco, x402 Protocol Explained).

**Sequencing:** lock #1 (Arc Nanopayments) as the guaranteed deliverable; add the Ledger approval layer for #2; add ENS subnames for #3. Treat #4 (Arc chain-abstracted USDC) and #5 (Chainlink CCIP) as bonus submissions that reuse the same DAIO cross-chain code.

---

## 4. DAIO Cross-Chain Mainnet Deployment Architecture

The DAIO (Decentralized Autonomous Intelligent Organization) is the governance + treasury + identity layer that sits on top of the existing ERC-8004 anchor. Design constraints from the user are honored throughout: **Foundry over Hardhat, mainnet-only targets, no admin keys post-deploy, no upgradeable proxies, Apache 2.0.**

### 4.1 Contract set (all non-upgradeable / immutable)
- **`DAIOGovernor`** — OpenZeppelin Governor (non-upgradeable), token-weighted voting by BANKON, with the SunTsu-doctrine validation and 15% diversification mandate encoded as immutable proposal-validity checks (per the published AUGMENTIC architecture: "Immutable smart contract governance ensures 15% diversification mandate, agent equity ownership, and supermajority consensus for constitutional changes").
- **`DAIOTimelock`** — the only executor; `DAIOGovernor` is the sole proposer/executor; deployer renounces all admin roles post-deploy (assert `admin == address(timelock)` and no EOA backdoor).
- **`DAIOTreasury`** — holds USDC/EURC/BANKON; balance can decrease only via Timelock-executed proposals.
- **Agent identity** — **reuse the live ERC-8004 Identity Registry.** Per awesome-erc8004: *"The Identity Registry uses vanity address 0x8004A169... on mainnets and 0x8004A818... on testnets"*, deployed as per-chain singletons at the same address (covering Ethereum mainnet, Base, Optimism, Arbitrum, SKALE, Metis, XLayer et al.). Do not redeploy identity; anchor to it.
- **Agent wallets** — **EIP-6551 token-bound accounts**: each ERC-8004 agent NFT deterministically owns a smart-contract account (the agent's treasury/x402-paying wallet). Selling/transferring the agent NFT transfers its wallet, funds and reputation atomically — ideal for an agent marketplace.
- **Intelligent agents** — **ERC-7857 (iNFT)** is the EVM-native analogue of AgenticPlace's Algorand iNFT (encrypted, evolving agent metadata; introduced by 0G Labs in January 2025). On the EVM side, 0G is the natural home for ERC-7857 iNFTs; on Algorand, AgenticPlace's existing ARC-69 iNFT serves the same role.

### 4.2 Chains (mainnet)
- **Primary anchor: Ethereum mainnet.** Fusaka activated on Ethereum mainnet at epoch 411392 on December 3, 2025 at 21:49:11 UTC (Ethereum Foundation Blog, "Fusaka Mainnet Announcement"), raising the default block gas limit from 45M to 60M via EIP-7935. **Note the nuance:** ethereum.org cautions that "This upgrade does not lower gas fees on L1, at least not directly" — Fusaka's primary mechanism is L2 data-availability scaling (PeerDAS), and the observed sub-0.1-gwei L1 gas in early 2026 reflects broad demand migration to L2s plus higher gas limits, not a direct fee cut. Either way, L1 governance settlement is now economically viable; the canonical DAIO constitution and BANKON xERC20 lockbox live here.
- **EVM mirror targets: Base, Optimism, Arbitrum, Linea, Polygon, 0G.** ERC-8004 registries already exist as same-address singletons on most of these.
- **Algorand** as constitutional/payment rail: Falcon-secured State Proof finality, USDC ASA for x402-avm settlement, and AgenticPlace's aORC attestation contracts. Bridged to EVM at the identity/attestation layer (not a token bridge) — this is AgenticPlace's existing "identity bridge" pattern.

### 4.3 Bridging-rail selection (with justification)
The DAIO mirrors three distinct things — **governance messages, the BANKON token, and treasury USDC** — and each needs a different rail. This separation (message-only vs token vs USDC settlement) is the dominant 2026 architecture pattern, confirmed across multiple infrastructure analyses (Eco, "8 Best Cross-Chain Messaging Protocols 2026").
- **Governance/state mirroring → Hyperlane (message-only).** Hyperlane is permissionless (deploy on any chain, including 0G, without sponsor approval), modular (configurable Interchain Security Modules), and cheap/fast for high-frequency low-value governance events. This matches the "deploy anywhere, sovereign" ethos.
- **High-value constitutional finalization → Chainlink CCIP.** CCIP's Risk Management Network and longer finality make it the right rail for rare, high-value actions. Per Chainlink documentation: *"on Ethereum, it takes about 15 minutes for a block to be finalized"*, with finality "achieved when two-thirds of validators agree on block finalization over two epochs (64 slots, approximately 12.8 minutes)." That deliberate safety latency is acceptable for constitutional amendments and large treasury moves — and it doubles as a Chainlink-bounty (#5) integration.
- **BANKON token → xERC20 (EIP-7281).** Lock BANKON in a mainnet lockbox; mint/burn sovereign representations on each chain with immutable, per-bridge rate limits set at deploy. This gives the DAO bridge-agnostic sovereignty with no single-bridge lock-in and no admin key — consistent with the "no admin keys post-deploy" rule.
- **Treasury USDC → Circle CCTP + ERC-7683 intents.** Native USDC burn/mint via CCTP, with ERC-7683 cross-chain intents (Across/UniswapX-style; ratified early 2025, now live on Across, UniswapX and Eco) for user/agent-facing routing, and **Arc as the liquidity hub** (which directly satisfies Arc bounty #4).

### 4.4 Identity/governance mirroring design
- Canonical agent identity stays on the ERC-8004 Identity Registry (Ethereum mainnet).
- ENS subnames (`agent.bankon.eth`) provide the human-readable layer; text records carry MCP/A2A/x402 endpoints.
- Governance votes are tallied on Ethereum mainnet; results are mirrored to L2s via Hyperlane so that agent contracts on Base/Arbitrum/etc. can read the canonical DAIO state without re-running governance.
- aORC attestations on Algorand provide a cheap, high-frequency proof-of-state layer (0.001 ALGO/mint, ~4-second finality) cross-referencing the EVM governance root.

---

## 5. x402 + parsec-wallet Algorand Payment Integration

### 5.1 The metering layer
x402 (the HTTP 402 "Payment Required" agentic payment standard, launched by Coinbase in May 2025 and contributed to the Linux Foundation's newly formed **x402 Foundation on April 2, 2026** — governing body includes Cloudflare and Stripe, founding members Circle, Visa, Mastercard, Google and AWS, per The Defiant) is **chain-neutral** — the same 402 flow works on EVM, AVM (Algorand) and SVM. AgenticPlace already declares x402 as a supported agent protocol. The design:
- mindX inference endpoints (and RAGE query endpoints) are wrapped in x402 middleware. A request without payment returns 402 with payment requirements; the agent signs a USDC micropayment and retries; the facilitator verifies and settles; the resource is served.
- **Multi-rail 402 response**: using the GoPlausible `@x402-avm/paywall` multi-network pattern, a single endpoint can accept payment on **either** Algorand (`algorand:*` CAIP-2 network, USDC ASA) **or** an EVM chain (`eip155:*`, USDC) in the same 402 response. This is the concrete EVM↔AVM bridge for metering.
- **Phi-tier pricing** (AgenticPlace's golden-ratio directive pricing: 0.001 / 0.001618 / 0.002618 / 0.004236 ALGO tiers, with progressively stronger temporal verification — base UTC timestamp → blocktime → block+prediction proof → multi-block proof chain) maps cleanly onto x402 price tiers.

### 5.2 Algorand AVM rail (via GoPlausible)
- Algorand x402 is provided by the Algorand Foundation + GoPlausible collaboration (`x402-avm`), supporting mainnet and testnet, using CAIP-2 network identifiers, atomic transaction groups, and fee abstraction (a third-party fee payer can cover fees so the paying agent need not hold ALGO).
- Mainnet USDC on Algorand is the canonical USDC ASA (the user specifies ASA 31566704; **note GoPlausible's published examples use the Algorand testnet USDC ASA 10458941**, so mainnet vs testnet asset IDs must be set carefully).
- Python (`pip install x402-avm`, imports `from x402…`), TypeScript (`@x402-avm/express`, `/hono`, `/next`), and framework middleware exist today — directly usable from mindX's Python and PHP stack.

### 5.3 Parsec Wallet — deployable vs aspirational (FLAGGED)
- Per AgenticPlace's own documentation, **Parsec Wallet** is a sovereign desktop Algorand wallet that signs locally over a WebSocket on `localhost:9876` with no cloud relay, exposed to dApps via the Pera-compatible **Parsec Connect SDK** (JSON-RPC 2.0 over WebSocket), and AgenticPlace is described as its first production dApp integration.
- **Important sourcing caveat:** independent verification of the parsec-wallet public repository could not confirm these specific capabilities (the `localhost:9876` WebSocket signing, x402 support, and the Parsec Connect SDK). The `parsec-wallet` GitHub organization exists, but the deployable capability surface beyond AgenticPlace's self-description is **unverified** and should be treated as partly aspirational until the repo/README is public. For the hackathon, **Pera Wallet** (`@perawallet/connect@1.5.1`, already integrated per the AgenticPlace architecture docs and WalletConnect-compatible) is the safe, demonstrably-working signing path, with Parsec as the differentiator if/when its SDK is confirmed.
- Similarly, the user's **`pythai/x402-php`** library (typed enums, EVM/AVM mechanisms, PSR-15 middleware, DeltaBridge layer) **could not be found on Packagist or public GitHub**; treat it as private/unpublished. The publicly available, demonstrably-working x402 implementations for the demo are GoPlausible's `x402-avm` (Python/TS) for Algorand and the standard EVM x402 SDKs for Base/Arc. PSR-15 middleware is a real PHP-FIG standard, so a PHP x402 layer is architecturally sound — it just isn't a verifiable public artifact today.

### 5.4 How AVM metering settles against the EVM deployment
- x402 receipts are chain-local; the DAIO treasury maintains a unified ledger that credits inference revenue regardless of settlement chain.
- For consolidation, USDC collected on EVM chains is normalized via CCTP; USDC collected on Algorand is held as ASA and accounted in the treasury ledger, with aORC attestations on Algorand serving as the cross-chain payment proof referenced by the EVM DAIO state root.
- This maps to the BANKON token model: per the published AUGMENTIC architecture, "BANKON PYTHAI: Measures total knowledge asset value, appreciating through proven alpha generation with deflationary buyback mechanism" and "BANKON PAI: Prices inference consumption, creating demand-driven marketplace for verified computational intelligence" — i.e., x402 inference receipts are the demand signal that prices BANKON PAI.

---

## 6. Foundry Test Plan

### 6.1 Repository structure
```
daio/
├── src/            DAIOGovernor.sol, DAIOTimelock.sol, DAIOTreasury.sol,
│                   BankonXERC20.sol, BankonLockbox.sol, AgentTBA.sol (6551)
├── script/         Deploy.s.sol, DeployMultichain.s.sol, Renounce.s.sol
├── test/
│   ├── unit/       per-contract unit tests
│   ├── integration/ governance↔timelock↔treasury flows
│   ├── invariant/  invariant + handler contracts
│   └── fork/       mainnet & L2 fork tests
└── foundry.toml    (fork RPC endpoints, fuzz/invariant runs)
```

### 6.2 Fork-testing approach (against mainnet)
- Use `vm.createSelectFork(vm.rpcUrl("mainnet"))` to fork Ethereum mainnet and test against **live** contracts: the ERC-8004 Identity Registry (`0x8004A169…`), the ENS Registry/NameWrapper, live USDC, and the Circle CCTP TokenMessenger.
- Fork Base, Arbitrum, Optimism, Linea, Polygon and 0G to validate same-address CREATE2 deployment and cross-chain message handling.
- Simulate Hyperlane and CCIP message delivery by mocking the destination mailbox/router and asserting state-mirror correctness.

### 6.3 Key invariants to test
- **Governance:** only the Timelock can execute treasury actions; quorum and voting-period thresholds hold; **post-deploy there is no EOA admin** (`assert` all admin roles renounced); total voting power is conserved across delegations.
- **xERC20 (EIP-7281):** Σ(bridged BANKON supply across all chains) ≤ BANKON locked in the mainnet lockbox (no inflation); per-bridge mint never exceeds its immutable rate limit; burn/mint parity on every cross-chain transfer.
- **Treasury:** balance decreases only through an executed governance proposal; the 15% diversification mandate cannot be violated by any single proposal.
- **EIP-6551:** each agent NFT maps to exactly one canonical TBA per (chainId, tokenContract, tokenId, salt); TBA control follows NFT ownership; front-running-on-sale guard holds.
- **x402 settlement:** paid amount == required amount; nonce-based replay protection; settlement idempotency (a replayed payment proof cannot double-credit).

### 6.4 Deployment scripts
- `Deploy.s.sol` uses `forge script --broadcast --verify`; **CREATE2 with a fixed salt** so the DAIO contracts share one address across all chains (mirroring the ERC-8004 singleton pattern).
- `DeployMultichain.s.sol` loops over the target chain RPCs.
- `Renounce.s.sol` runs as the final step on every chain: transfer ownership to the Timelock, renounce deployer roles, and (for any ENS NameWrapper subname logic) burn the appropriate fuses — enforcing the "no admin keys post-deploy, no upgradeable proxies" rule.
- CI: `forge snapshot` (gas), `forge coverage`, and invariant runs gate every merge.

---

## 7. Appendix — The AllChain Mapping (framed for sponsors)

AgenticPlace maintains a canonical chain registry that should be supplied to sponsors as supplementary material. Per the live platform:
- **2,510 blockchains** tracked with connection data (RPC endpoints, explorers, native currency, native price, market cap), exposed via `/api/allchainft` and `/api/export?table=chains`.
- **48 chains** in the active ERC-8004 indexing set (described as 24 mainnet + 24 testnet).
- The `allchains` table schema: `chain_id` (EVM chain ID, primary key), `name`, `native_currency` (JSON `{name, symbol, decimals}`), `rpc_urls`, `explorers` (JSON), `native_price`, `market_cap`.
- On-chain verification: the aORC Registry contract on Algorand stores each chain's connection data in box storage (104-byte header + JSON) and accumulates consensus verification counts (1 ALGO per `listChain`/`verifyChain`), producing a crypto-economically attested chain map sorted by verification count.

**Framing for sponsors:** the allchain mapping provides canonical identifiers for every supported chain — EVM chain IDs for `eip155:*` networks plus CAIP-2 identifiers for AVM (`algorand:*`) — giving each sponsor a single authoritative reference for how their chain is addressed across the PYTHAI stack and the x402 multi-rail payment layer. (Note: the canonical `allchain.html` document itself could not be fetched directly during research; the figures above are drawn from AgenticPlace's architecture and API documentation and should be reconciled against the live `allchain.html` before distribution.)

---

## 8. Prioritized Action Timeline

**Pre-event (now → event):**
1. Confirm published criteria for ENS, Chainlink, LI.FI, Hedera the moment they leave "coming soon"; re-prioritize if ENS criteria favor a specific integration.
2. Obtain API keys: Circle/Arc (USDC, Bridge Kit, Gateway, Circle Wallets), Uniswap Developer Platform (only if pursuing #9/#10 and Continuity-eligible).
3. Stand up the Foundry repo; write fork tests against the live ERC-8004 registry, ENS, USDC and CCTP now.
4. Confirm mainnet vs testnet asset IDs (USDC ASA 31566704 mainnet vs 10458941 testnet on Algorand; USDC contract addresses on Arc/Base) and the `bankon.eth` subname registrar's network (parent name is confirmed mainnet; subname registrar network is unverified).

**Hackathon Day 1:**
5. Deploy DAIO core (Governor, Timelock, Treasury, BANKON xERC20 + lockbox) to a testnet first, then to the mainnet target chain(s); run `Renounce.s.sol`.
6. Wire x402 metering into the mindX inference endpoint (EVM/USDC primary, Algorand/x402-avm secondary).
7. Issue `agent.bankon.eth` subnames with endpoint text records for the demo agents.

**Hackathon Day 2:**
8. Add the Ledger device-approval gate for high-value DAIO directives (the #2 differentiator).
9. Mirror governance state to one L2 (Base) via Hyperlane; demonstrate a cross-chain treasury USDC move via CCTP/Arc.
10. Record architecture diagram + ≤3-minute video; finalize GitHub repos (Apache 2.0, clean commit history — 1inch-style single-commit submissions are penalized).
11. Submit to Arc (#1, and #4 if treasury demo lands), Ledger (#2), ENS (#3), and Chainlink (#5) if CCIP is integrated.

---

## 9. Caveats
- **Sponsor criteria gaps:** Google Cloud, ENS, World, Chainlink, Canton, Dynamic and Privy showed "Prize details coming soon" on the live page; the ENS ($20,000) and Chainlink ($10,000) qualification requirements are therefore not yet confirmed and must be re-checked. World's $15,003 figure (the odd $3) appears on the live page as stated.
- **Unverified PYTHAI components:** `pythai/x402-php` was not found publicly (treat as private/unpublished); Parsec Wallet's specific capabilities (localhost:9876 WebSocket signing, x402, Parsec Connect SDK) could not be independently verified beyond AgenticPlace's self-description. Use Pera Wallet + GoPlausible x402-avm + standard EVM x402 SDKs as the demonstrably-working baseline.
- **Mainnet vs testnet:** `bankon.eth` is confirmed on Ethereum mainnet (→ `0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169`, expiry 2027-04-20); the subname-registrar deployment network is unverified. Algorand USDC ASA must be set to the mainnet ID (31566704), not the testnet ID (10458941) used in GoPlausible's examples. Verify every contract/asset address against the live chain before deploying or demoing.
- **Continuity Track eligibility:** the $7,000 Uniswap API bounty is restricted to Continuity Track participants — do not plan around it unless eligibility is confirmed.
- **Fusaka and gas:** the dramatic sub-cent L1 gas observed in early 2026 is real but is driven primarily by L2 data-availability scaling (PeerDAS) and the raised gas limit, not a direct L1 fee reduction (ethereum.org explicitly cautions Fusaka "does not lower gas fees on L1, at least not directly"). Do not over-anchor cost projections to current gas; budget for variance.
- **ERC-7857 / iNFT status:** ERC-7857 is a relatively new standard (introduced by 0G Labs, January 2025) and is not as broadly deployed as ERC-721/6551; treat the EVM iNFT path as 0G-centric and keep the production iNFT on Algorand (ARC-69) as the proven implementation.
- **BANKON tokenomics:** the BANKON PYTHAI / BANKON PAI dual-token model is drawn from the team's own hackathon submission page (self-described, promotional), which itself flags "Tokens + AI = high risk/complexity." Treat tokenomics as project self-description, not independently audited fact.