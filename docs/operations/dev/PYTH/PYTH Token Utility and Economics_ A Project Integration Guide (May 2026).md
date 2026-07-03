# How a Project Can Use the PYTH Token: A Technical and Economic Report on Pyth Network (May 2026)

## TL;DR
- **PYTH is now a multi-purpose oracle-economy token, not a pure governance asset.** A project can (1) stake PYTH for governance voting on the Solana-based Pyth DAO, (2) self-stake or delegate-stake PYTH into Oracle Integrity Staking (OIS) against specific publishers for slashable, performance-linked rewards (rewards currently paused as of April 2026), (3) pay Pull-oracle update fees that flow to the DAO treasury, (4) subscribe to Pyth Pro / Pyth Pro X institutional feeds (currently invoiced in USD/stablecoin, with PYTH-denominated billing proposed under Phase 2), (5) earn publisher rewards by streaming first-party data, (6) tap grants from the 50M PYTH Ecosystem Grants Program, and (7) move PYTH across chains through Wormhole-wrapped bridges.
- **The decisive recent change is the December 2025 launch of the PYTH Reserve**, a structural buyback that deploys 33% of the Pyth DAO treasury balance each month into open-market PYTH purchases, funded by revenue from Pyth Pro (>$1M ARR in its first month per The Block, December 12, 2025), Pyth Core update fees, Entropy, and Express Relay. Combined with OP-PIP-92/93/94/111/112, which set per-chain Pyth Core update fees targeting approximately $0.01 per update across 70 EVM chains and tiered Express Relay fees (1 bps stablecoins / 2.5–5 bps majors / 10 bps other), this transforms PYTH from an emissions-funded incentive token into a revenue-funded equity-like instrument.
- **Builders should treat OIS as paused for reward purposes (Y = 0 since April 2026) but still slashable**, treat Pyth Pro as the dominant net-new revenue source (and therefore the largest indirect demand driver for PYTH via the Reserve), and design integrations on the assumption that all per-update fees remain denominated in destination-chain native gas tokens — not in PYTH itself.

## Key Findings

1. **Governance is dual-staked and tri-council.** A holder stakes PYTH on `staking.pyth.network` (program in `pyth-network/governance`); the same staking position is independently usable for governance voting and (separately) for OIS. Three constellations — the **Pythian Council** (8 members, 7-of-9 multisig, controls oracle parameters, fees, validator set), the **Price Feed Council** (7 members, manages listings and publishers), and the **Community Council** (7 members, community ops) — execute delegated Operational PIPs. The DAO operates through Pyth DAO LLC; Constitutional PIPs require >67% of Votable Tokens in favor; Operational PIPs voted by the DAO require >50%. Voting is on Solana Realms at `app.realms.today/dao/PYTH`. Proposing requires ≥0.25% of Votable Tokens (~25M PYTH at current circulating supply).
2. **OIS is currently a security mechanism without active rewards.** OP-PIP-103 (passed April 2026) set the OIS reward rate parameter Y = 0 after the original 100M PYTH bootstrap reward pool depleted on April 22, 2026. Publishers and delegators retain stake at risk (5% slashing cap, 20% delegate fee), but no new staking emissions flow until the DAO authorizes a new reward source.
3. **Update fees stay in native gas, not PYTH.** On EVM, Aptos, Sui, Stacks, TON, etc., consumers call `updatePriceFeeds{value: fee}` and pay `msg.value` in the destination chain's native token. The Q1/Q2 2026 fee resets (OP-PIP-93 and OP-PIP-111) calibrated EVM update fees to target approximately $0.01 per update across 70 EVM chains, with collected fees periodically withdrawn to the Pyth DAO Treasury on Solana (e.g., OP-PIP-108/110/111 for Express Relay USDC/SOL/wSOL fees).
4. **Pyth Pro is the cash engine.** Launched as Pyth Pro on September 24, 2025 (renamed from Pyth Lazer), it offers three transparent tiers — Pyth Crypto (free, 1s), Pyth Crypto+ ($5,000/mo, 1ms crypto), Pyth Pro ($10,000/mo, full cross-asset 1ms with redistribution rights). Pyth Pro hit >$1M ARR with 80+ active subscribers in its first month, per Michael James, head of institutional business development at Douro Labs, in The Block (December 12, 2025): *"Since launching in late September, Pyth Pro has reached $1 million annual recurring revenue (ARR) in its first month, onboarded 80+ active subscribers, and received around 10 inbound organic leads per week."* BitMEX, Coinbase International Exchange, LMAX, Crypto.com, and Bitget have integrated the exchange-targeted Pyth Pro X variant.
5. **The PYTH Reserve creates structural buy demand.** Each month the Pyth DAO deploys 33% of the treasury balance to open-market PYTH purchases via a multisig executor, locking the acquired tokens in the Reserve wallet. The first December 2025 buyback was estimated by Michael James at The Block at $100K–$200K against a ~$500K treasury balance; the first executed purchase totaled 2,157,086.99 PYTH on January 5, 2026 per the DAO forum execution reports (as cited in Coincub's analysis).
6. **PYTH supply: ~7.88B circulating of 10B max, after the 2.13B cliff on May 19, 2026.** Allocation is 22% publisher rewards, 52% ecosystem growth, 10% protocol development, 6% community/launch, 10% private. The 18-month cliff in May 2025 added 2.13B PYTH; the equivalent 30-month cliff on May 19, 2026 just added another 2.13B PYTH, of which ~1.13B is earmarked for ecosystem growth and ~537M for publisher rewards (programmatic, not exchange-bound).
7. **PYTH is canonically a Solana SPL token** at mint `HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3`. Cross-chain mobility is currently via permissionless Wormhole-wrapped representations rather than full Wormhole NTT — the Ethereum mainnet PYTH ERC-20 at `0xefc0CED4B3D536103e76a1c4c74F0385C8F4Bdd3` is a bridged wrapped token. PYTH stakers can map an EVM wallet to their Solana staking address to participate from EVM wallets.
8. **Publisher onboarding is permissioned to first-party data owners.** Exchanges, market makers, and trading firms apply through the Pyth Data Association, generate a Solana keypair, deploy a Pythnet validator and `pyth-agent`, and begin signing prices. Quality is tracked by the Publisher Metrics dashboard and feeds publisher reward eligibility. Pyth's December 2025 KPI snapshot reports 128+ data providers and 2,853+ price feeds across 113+ chains.

## Details

### 1. Governance utility — staking PYTH for votes on Pyth DAO Realms

A project participates in governance by staking PYTH at `staking.pyth.network`, which routes funds into the Pyth staking program on Solana (deployed from `pyth-network/governance`). The same SPL position simultaneously underpins governance and is separately allocated to OIS pools — locked tokens (vesting positions) can be used for governance staking but **not** for OIS, because OIS slashing requires unlocked PYTH. Epochs are seven days long, starting Thursdays at 00:00 UTC; staked tokens enter a one-epoch warmup before becoming vote-eligible, and unstaking requires a one-epoch cooldown before tokens are withdrawable (e.g., unstaking Monday means withdrawal the following Thursday week).

The Pyth DAO is operated through Pyth DAO LLC and three councils, each managing a dedicated multisig wallet:

- **Pythian Council** (8 members + Operations Wallet `opsLibxVY7Vz5eYMmSfX8cLFCFVYTtH6fr6MiifMpA7`, 7-of-9 multisig). Delegated control over oracle program upgrades, the size and denomination of update fees, the Pythnet validator set / PGAS distribution, and on-chain fee schedules. Inaugural members (March 2024) came from Synthetix, Pyth Data Association, Wormhole Foundation, Douro Labs (two seats), Flowdesk, HMX, and Solend; the third council (OP-PIP-59, Q2 2025) added Yaser Jazouane (Douro Labs), Marc Tillement (PDA), George M (XBTO), and Lee Mount (Euler Labs), with a 100,000 PYTH stipend.
- **Price Feed Council** (7 members; Ops Wallet `ACzP6RC98vcBk9oTeAwcH1o5HJvtBzU59b5nqdwc7Cxy`). Manages feed catalog, publisher selection per feed, and minimum publisher counts. The third Price Feed Council (OP-PIP-66, Q2 2025) elected Mario Bernardi (PDA), Nicholas Diakomihalis (Douro Labs), and Anton Totomanov (Objective Labs) with a six-month, 315,000 PYTH stipend (45,000 PYTH per seat).
- **Community Council** (7 members; Ops Wallet `Ef7AjJzDXK6Tn2gYuMvL9YdXATV29b8PwpsT1yoPokTC`). Handles community programs, partnerships, and analyst functions.

Constitutional PIPs (upgrading governance, staking, or multisig programs) require >67% of Votable Tokens in favor; Operational PIPs voted by the DAO require >50%; PIPs delegated to a council require only that council's multisig threshold. To submit a DAO-level PIP a proposer must hold ≥0.25% of Votable Tokens. All on-chain voting takes place at `app.realms.today/dao/PYTH`, with proposals published at `proposals.pyth.network` and `forum.pyth.network`.

The DAO's actual control surface widened materially in 2025–26. Beyond electing councils, allocating stipends, and managing treasury withdrawals, the DAO now sets quarterly on-chain fee schedules for Pyth Core (OP-PIP-93, OP-PIP-111), Express Relay (OP-PIP-92), and Entropy (OP-PIP-94, OP-PIP-112); appoints exclusive operators (OP-PIP-67 made Douro Labs the exclusive Express Relay relayer at 6% of platform fees vs. 94% to the DAO); upgrades Pyth Lazer and Pyth Solana Receiver contracts (OP-PIP-58, OP-PIP-5); and authorizes treasury sweeps of fees from product contracts (OP-PIP-107/108/109/110/111). Crucially, OP-PIP-87 ("Pyth Token Phase 2") delegated to the Pythian Council a standing quarterly mandate to set on-chain fee parameters across all Pyth products (except Pyth Pro), making fee policy a DAO-controlled lever rather than a contributor-controlled one.

### 2. Oracle Integrity Staking (OIS): self-stake, delegate, and slashing risk

OIS uses the same Solana staking program and the same 7-day epoch as governance. Each onboarded publisher is programmatically assigned a staking pool. The publisher self-stakes into their pool, and other PYTH holders can delegate-stake to that same pool as an LP-like position. At each epoch boundary (Thursday 00:00 UTC), pool snapshots are taken, soft caps are recomputed (the soft cap dynamically expands and shrinks with the number of symbols a publisher covers, weighted to favor feeds with fewer publishers), and rewards/penalties are applied to that snapshot. Stake above the soft cap earns no rewards but is still slashable. Like governance staking, OIS positions require a warmup epoch before becoming active and a one-epoch cooldown before withdrawal.

The economic parameters governed by the Pyth DAO:

- **Slashing cap:** 5% of stake in the affected pool per slashing event. Both publisher self-stake and delegators are slashed pro-rata. The DAO can vote on the disposition of slashed tokens.
- **Delegate fee:** 20% of net rewards (after penalties) deducted by the publisher from delegator rewards. DAO-adjustable.
- **Maximum reward rate (Y):** DAO-set APY ceiling. Historically the cap was approximately 10% APY; third-party operators (e.g., BLOCKSIZE) advertised ~8–10% APY through 2025. **As of April 2026, Y = 0 per OP-PIP-103**, after the 100M PYTH bootstrap reward pool seeded by the Pyth Data Association depleted on April 22, 2026. No new rewards accrue; staking and slashing mechanisms remain live, and the DAO is expected to authorize a successor reward source (likely a share of on-chain revenue per the Phase 2 model) before re-enabling Y > 0.
- **Slashing events to date:** No public on-chain slashing events have been triggered as of May 2026; the mechanism has remained an ex-ante deterrent rather than an ex-post enforcement tool.

For a project, OIS supports four concrete patterns. First, a market maker or exchange that becomes a Pyth publisher can self-stake PYTH into its own pool to anchor delegator confidence and (when Y > 0) compound publisher rewards. Second, a DeFi protocol that consumes Pyth feeds can delegate-stake to the publishers it relies on as a defensive hedge — slashing partially offsets oracle losses, and delegation pressure to underperforming publishers signals to the Price Feed Council. Third, a treasury manager can build an aggregator vault that auto-allocates delegator stake across the top-ranked publishers (currently uneconomic with Y = 0 but architecturally relevant). Fourth, a "PYTH-as-an-LP" wrapper can tokenize delegated positions for liquid-staking-style secondary trading, subject to warmup/cooldown friction.

Staked supply was 819.7M PYTH in OIS as of December 31, 2025 per Messari's State of Pyth Q4 2025 report, down quarter-over-quarter due to a large one-day withdrawal. After the May 2025 unlock, staked supply had risen to 938M by end of Q2 2025 (13.3% of unlocked supply at that point) before settling lower.

The Solana program ID for the Pyth staking program is published in `pyth-network/governance/staking/programs/staking/src/lib.rs` and used by `staking.pyth.network`. Production integrators should fetch the current `declare_id!` from the repo rather than hard-coding it; the staking and OIS instructions are exposed via the Anchor IDL and TypeScript SDK in the same repository.

### 3. Pyth Pro and Pyth Pro X subscription economics

Pyth Pro (formerly Pyth Lazer, renamed September 24, 2025) is a subscription-based off-chain/on-chain hybrid distribution product. Pricing as published at `pyth.network/pricing`:

- **Pyth Crypto** — free; crypto feeds at 1-second updates.
- **Pyth Crypto+** — $5,000/month; crypto data at 1ms updates with new ticker additions weekly.
- **Pyth Pro** — $10,000/month; 2,000+ feeds across cryptocurrencies, equities, futures, fixed income/Treasury rates, commodities, and FX; 1ms updates; enterprise support and redistribution rights.
- **Pyth Pro X** — exchange-specific commercial tier used by Coinbase International Exchange, BitMEX, Bitget, LMAX, Crypto.com, TradeXYZ, DreamCash, and CASH markets for collateral valuation, liquidations, and new market launches.

Adoption metrics, per Michael James of Douro Labs in The Block, December 12, 2025: "Since launching in late September, Pyth Pro has reached $1 million annual recurring revenue (ARR) in its first month, onboarded 80+ active subscribers, and received around 10 inbound organic leads per week." James added in the same interview: "Based on pipeline projections for the next 12–18 months, we're targeting $50 million ARR." Messari's State of Pyth Q2 2025 quantifies the pre-rebrand Lazer service: "roughly 15 applications across both Web2 and Web3 are using Lazer subscriptions, generating an annual recurring revenue (ARR) of about $1.8 million. These clients are paying subscription fees of approximately $10,000 per month."

**Payment flow.** Pyth Pro institutional billing is denominated in USD and on-chain stablecoins as of May 2026. The Phase 2 economic-design blog explicitly proposes that "payments can be made in multiple ways, including USD, onchain stablecoins, or PYTH tokens" — PYTH-denominated billing is on the roadmap but not the default. Subscription revenue accrues to the Pyth DAO Treasury (60% under the CO-PIP-9 split; 40% retained by Douro Labs over a 24-month distribution window per Messari), and one-third of the resulting treasury balance is recycled monthly through the PYTH Reserve into open-market PYTH purchases.

Pyth Pro for AI Agents, launched in 2026, extends the same data fabric to autonomous agent workflows with redistribution-friendly licensing — a structurally important product because programmatic AI consumption can multiply per-firm price-update query rates by orders of magnitude.

### 4. Pull-oracle update fees: native-gas-denominated, DAO-treasury-routed

Pyth's Pull model requires a consumer to fetch a signed VAA from Hermes (`hermes.pyth.network`) and submit `updatePriceFeeds(bytes[] updateData)` to the destination-chain Pyth receiver, paying the fee in `msg.value` (or its chain equivalent). The fee is denominated in the **destination chain's native unit**, never in PYTH, and the consumer pays both the Pyth fee and the chain's gas. The Pythian Council sets fees quarterly per OP-PIP-87.

Concrete per-update fee figures:

- **Default (chains without explicit governance vote):** 1 unit of the smallest denomination of the native gas token (1 wei on Ethereum-class chains, 1 octa on Aptos, 1 MIST on Sui, 1 uSTX on Stacks = 0.000001 STX).
- **Q1 2026 EVM rebase (OP-PIP-93):** Targeted approximately $0.01 per update across 70 EVM chains, calibrated per-chain to native-token volatility. OP-PIP-111 (Q2 2026) refreshes these levels for the next quarter.
- **Solana / SVM:** Update accounts pay rent plus a small per-update fee handled by the Pyth Solana Receiver at `rec5EKMGg6MxZYaMdyBfgwp4d5rB9T1VQH5pJv5LtFJ`.
- **Stacks:** 1 uSTX per `verify-and-update-price-feeds` call against `.pyth-oracle-v4`.

**Fee revenue flow.** Fees collected on each chain accumulate in the Pyth receiver contract for that chain. Periodic governance proposals (e.g., OP-PIP-107 test withdrawal, OP-PIP-108 USDC sweep, OP-PIP-109/111 wSOL sweep, OP-PIP-110 SOL sweep) move the accumulated fees from product contracts into the Pyth DAO Treasury wallet on Solana. From the treasury, 33% of the running balance is deployed monthly via the PYTH Reserve buyback. Note that under current parameters fees do **not** flow directly to publishers — publisher rewards historically came from the Publisher Rewards allocation (22% of the 10B max supply) and from the OIS reward pool (now Y = 0). The Phase 2 model contemplates redirecting on-chain revenue to a revived OIS reward pool.

For projects with fee-abstraction needs (gasless apps, smart-account flows), the recommended pattern is to wrap `getUpdateFee()` and bundle the Pyth fee with the user's intent transaction, sponsored by the project's paymaster — exactly as integrations with Stacks (`pyth-oracle-v4`) and Sei demonstrate.

### 5. Becoming a Pyth publisher and earning rewards

Publishing access is restricted to first-party data owners — exchanges, regulated market makers, banks, and trading firms — vetted by the Pyth Data Association. The onboarding flow:

1. Register interest at `pyth.network/become-a-publisher` and execute a publisher agreement.
2. Generate a Solana ed25519 keypair (typically one for test/devnet, one for mainnet) and share the public key with PDA.
3. PDA assists in provisioning a Pythnet validator and a Solana RPC endpoint.
4. Deploy `pyth-agent` (open-source, in `pyth-network/pyth-agent`), point it at the publisher's internal price source via JSON-RPC, and start signing per-symbol updates.
5. Performance is exposed publicly via the Publisher Metrics dashboard on `pyth.network`, which scores price accuracy vs. aggregate, uptime, calibration to a Laplace confidence distribution, and price-quality regression.

The publisher rewards formula combines uptime (slot inclusion in the aggregate), price-quality (predictive R² against future aggregate movements), and confidence calibration. When OIS rewards (Y) are positive, publishers earn from the OIS pool proportional to their stake-weighted pool, net of slashing for proven errors. The Publisher Rewards tokenomics bucket (22% = 2.2B PYTH) was the historical funding source pre-OIS and continues to seed grants for new asset coverage.

Institutional publishers active as of Q1 2026 include Jane Street, Two Sigma, Jump Trading, Cumberland (DRW), Optiver, Wintermute, Susquehanna, Virtu, Hudson River Trading, Galaxy, Flow Traders, IMC, Tower Research, Genesis, Amber Group, Akuna Capital, Auros, QCP Capital, Cboe Global Markets, LMAX, Coinbase (via Coinbase International Exchange), Binance, OKX, Bybit, Bitstamp, Gate, Revolut, Raydium, Orca, 0x, MEMX, GTS, Kaiko, IEX Cloud, Kalshi, Blue Ocean, and — uniquely — the U.S. Department of Commerce's Bureau of Economic Analysis. Pyth's December 2025 KPI snapshot reports 128+ data providers, 2,853+ price feeds, and 113+ supported chains; the network has cumulatively paid out >$50M to institutional publishers per Pyth's Phase 3 blog.

### 6. Treasury, grants, and ecosystem programs

The Pyth DAO Treasury composition is split among PYTH tokens (drawn from the 52% Ecosystem Growth allocation = 5.2B PYTH, of which ~700M was unlocked at TGE with the balance vesting on the 6/18/30/42-month cliffs), USDC/USDT/SOL/wSOL fee revenue swept from Pyth Core, Entropy, and Express Relay contracts via OP-PIPs, and Pyth Pro subscription revenue. Treasury holdings sat near $500K at the December 2025 PYTH Reserve launch per The Block, and are projected by Douro Labs to scale with Pyth Pro ARR (targeting $50M ARR within 12–18 months per Michael James in The Block, December 12, 2025).

**Grant programs available to builders:**

- **Pyth Ecosystem Grants Program** — launched May 2024 by the Pyth Data Association with 50M PYTH (≈$21M at announcement). Three tracks: Community Grants (educational content and events), Research Grants (oracle improvements, aggregation, novel applications), and Developer Grants (SDKs, tooling, integrations, cross-chain). Applications at the Pyth Ecosystem Grants homepage; tokens are distributed as a mix of unlocked and locked PYTH from the Ecosystem Growth bucket.
- **Superteam Pyth Grants** — fast-track ($1–$5K) micro-grants with 48-hour decisions, focused on integrations, dev education, and dev tooling. 50% paid on approval, 50% on delivery.
- **Phase 2 RFPs / quarterly council allocations** — Council Operations Wallets (`opsLibx…`, `ACzP6RC…`, `Ef7AjJzD…`) make targeted stipends and operational grants via OP-PIPs.
- **Hackathon prize pools** — Pyth co-sponsors prize tracks at Solana, EthGlobal, ETHCC, Encode Club, Sui, Aptos, and other ecosystem hackathons, typically 10K–100K PYTH per event.

### 7. Cross-chain mobility of PYTH

PYTH is a canonical SPL token on Solana at mint `HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3` with mint and freeze authorities disabled. Per Pyth's own docs, "through the use of permissionless bridges like Wormhole, (wrapped) PYTH tokens may exist on various other chains." In practice this means:

- **Solana (canonical, SPL):** All staking (governance and OIS), DAO voting (Realms), and the largest spot liquidity (Raydium, Orca, Jupiter aggregator) live here.
- **Ethereum mainnet (Wormhole-wrapped ERC-20):** `0xefc0CED4B3D536103e76a1c4c74F0385C8F4Bdd3`. This is the Wormhole portal-bridged wrapper, not a Wormhole NTT deployment. Liquidity on Uniswap v3 is thin compared to Solana.
- **Arbitrum One (Wormhole-wrapped):** `0xE4D5c6aE46ADFAF04313081e8C0052A30b6Dd724`.
- **Base, Optimism, BNB Chain, Polygon, Sui, Aptos:** Wormhole-wrapped representations where listed; trading volumes concentrate on CEX pairs (Binance, Bybit, OKX, Coinbase, plus Robinhood Crypto from January 2026) rather than DEX pools.

Because the deployment model is Wormhole portal-wrapped rather than full Wormhole NTT, moving PYTH from Solana to an EVM chain currently locks SPL PYTH in the Wormhole Solana vault and mints wrapped PYTH on the destination; the reverse burns wrapped and unlocks SPL. There is no NTT-style burn-and-mint with a unified accounting layer for PYTH at this time. Stakers and governance participants who hold tokens on an EVM chain can map an EVM wallet to a Solana address on the staking site so the underlying staked SPL PYTH still controls the votes.

### 8. Tokenomics and supply state in May 2026

- **Max supply:** 10,000,000,000 PYTH (fixed).
- **Allocation:** Publisher Rewards 22% (2.2B), Ecosystem Growth 52% (5.2B), Protocol Development 10% (1B), Community & Launch 6% (600M; fully unlocked at TGE November 2023), Private Sales 10%.
- **Vesting schedule:** 85% of supply was initially locked, releasing on cliffs at 6, 18, 30, and 42 months post-launch (May 2024 / May 2025 / May 2026 / May 2027).
- **Circulating supply as of May 19, 2026 (post-cliff):** approximately 7.88B PYTH (5.75B before the 30-month cliff + ~2.13B released on May 19), of which ~1.13B of the new tranche is earmarked Ecosystem Growth and ~537M Publisher Rewards — programmatic allocations rather than insider sell pressure.
- **Emission rate from publisher rewards:** Historically funded from the OIS reward pool (100M PYTH bootstrap) at a target ceiling of approximately 10% APY; **Y = 0 as of April 2026**, so net protocol-level PYTH emissions are zero at the time of writing. Net token flow is now buyback-positive (PYTH Reserve) rather than emission-negative for the first time in the network's history.

### 9. Integration patterns for builders

Concrete patterns a senior protocol architect can ship today:

- **Auto-staking OIS vault.** Tokenize delegator positions into an ERC-4626-like share token on Solana (e.g., a Token-2022 wrapper). The vault holds PYTH in OIS pools allocated by a heuristic (top-N publishers by quality score from Publisher Metrics) and rebalances at epoch boundaries. With Y = 0 today the yield is zero, so this is best built and tested ahead of a Phase 2 reward reactivation; market with slashing-insurance overlays.
- **Governance aggregator.** Aggregate delegated PYTH and vote programmatically using the Realms voting program (`GovER5Lthms3bLBqWub97yVrMmEogzX7xNjdXpPPCVZw`) and the Pyth staking program. Add an off-chain signal layer (Snapshot-like) for delegators to instruct the aggregator on each OP-PIP.
- **Pyth Pro reseller.** With a $10K/mo enterprise tier and redistribution rights, build a developer-tier reseller (e.g., $99/mo "Pyth Pro for indie devs"), capturing margin between wholesale and downstream subscriptions. AI-agent platforms and quant tooling vendors are obvious customers.
- **Fee-abstraction wrapper.** Smart-account paymasters that absorb Pyth update fees in the destination chain's native token, charging users a flat USD subscription on the application side. With per-update fees calibrated to approximately $0.01 on EVM, the absorbed cost is tiny vs. UX uplift.
- **Cross-chain PYTH liquidity router.** Combine Wormhole Portal bridging, Jupiter aggregation on Solana, and Uniswap v3 on Ethereum/Base/Arbitrum to enable cross-chain PYTH swaps for treasury managers needing to consolidate into the staking-eligible Solana SPL form.

**SDKs and contracts:**

- Price feed consumption: `@pythnetwork/pyth-sdk-solidity` (Solidity), `@pythnetwork/pyth-solana-receiver` and `pyth-solana-receiver-sdk` (Rust/TypeScript), `@pythnetwork/pyth-sui-js`, `@pythnetwork/pyth-aptos-js`, `pyth-sdk-cw` (CosmWasm).
- Pyth Pro / Lazer: `@pythnetwork/pyth-lazer-sdk` (now Pyth Pro SDK — the npm package name is unchanged).
- OIS / staking: Anchor IDL in `pyth-network/governance/staking/programs/staking`.
- Express Relay: `@pythnetwork/express-relay-evm-js`, `express-relay-svm`.
- Pyth Solana Receiver program: `rec5EKMGg6MxZYaMdyBfgwp4d5rB9T1VQH5pJv5LtFJ`.
- EVM Pyth contract address (typical Ethereum mainnet deployment): `0x4305FB66699C3B2702D4d05CF36551390A4c69C6` (canonical Pyth address used across most EVM chains; check `docs.pyth.network/price-feeds/core/contract-addresses/evm` for chain-specific addresses).
- Wormhole core bridge (Solana): `worm2ZoG2kUd4vFXhvjh93UUH596ayRfgQ2MgjNMTth`; Ethereum: `0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B`.
- Hermes API: `hermes.pyth.network` (PDA-hosted; alternate hosted instances at Triton, P2P, Liquify, EXTR).

### 10. Recent developments through May 2026

- **Pyth Pro launch and rebrand (September 24, 2025).** Pyth Lazer renamed Pyth Pro, tiered pricing made transparent, redistribution rights formalized. >$1M ARR in month one, 80+ active subscribers by December (Michael James, The Block, December 12, 2025); BitMEX integration for equity perps in January 2026; Pyth Pro X for exchanges launched with Coinbase International Exchange, BitMEX, Bitget, LMAX, Crypto.com, TradeXYZ, DreamCash, and CASH markets.
- **U.S. Department of Commerce GDP partnership (August 28, 2025).** Pyth (alongside Chainlink) selected by the BEA to publish quarterly GDP data on-chain across nine networks (Bitcoin, Ethereum, Solana, TRON, Stellar, Avalanche, Arbitrum One, Polygon PoS, Optimism), with five years of history. PYTH rallied 68% on the day per Crypto Briefing (August 28, 2025): "PYTH token soars 68% after Commerce Department taps Pyth Network for GDP feeds." CPI and BLS extensions are publicly contemplated by Mike Cahill and Secretary Lutnick.
- **PYTH Reserve launch (December 12, 2025).** 33% of monthly treasury balance deployed to open-market PYTH buybacks; tokens locked in the Reserve wallet under a 67% supermajority unlock requirement. The first month's buyback was estimated by Michael James at The Block at $100K–$200K against a ~$500K treasury, with the first executed purchase totaling 2,157,086.99 PYTH on January 5, 2026 (per Coincub's analysis of DAO forum execution reports).
- **Pyth Data Marketplace (announced with Fidelity, Euronext, and others).** Distribution engine allowing institutions to monetize unique datasets through Pyth's rails. Polymarket integrated Pyth as resolution source for equity-index and commodity markets.
- **DAO fee mandate (OP-PIP-87, December 9, 2025).** Pythian Council given the quarterly mandate to set on-chain fees for Pyth Core, Entropy, and Express Relay (excluding Pyth Pro). Q1 2026 implementations: OP-PIP-92 (Express Relay tiered fees 1/2.5/5/10 bps), OP-PIP-93 (Core fees on 70 EVM chains targeting ~$0.01/update), OP-PIP-94 (Entropy fees on 19 EVM chains). Q2 2026: OP-PIP-111 (Core refresh), OP-PIP-112 (Entropy refresh).
- **OIS rewards paused (OP-PIP-103, April 2026).** Y = 0 after the 100M PYTH bootstrap pool depleted April 22, 2026. Staking and slashing remain live; the DAO is in the design phase for a revenue-funded successor reward source.
- **30-month cliff unlock (May 19, 2026).** 2.13B PYTH released, +36.96% to circulating supply; majority earmarked for ecosystem growth and publisher rewards rather than insider sell pressure.
- **Robinhood Crypto listing (January 27, 2026).** Materially expanded U.S. retail access.
- **Lazer/Pyth Pro Sui mainnet (Q1 2026).** Pyth Pro contracts deployed on Sui mainnet; MegaETH Core and Pro contracts also deployed.
- **Express Relay relayer designation (OP-PIP-67).** Douro Labs designated exclusive relayer at 6% of platform fees (94% to DAO); configurable by Pythian Council.

## Recommendations

For a project deciding how to use PYTH, the staged playbook is as follows.

**Stage 0 — Integrate Pyth feeds before holding any PYTH.** Every project should treat Pyth Core integration as the entry point. Use `@pythnetwork/pyth-sdk-solidity` (or the SVM/Sui/Aptos/Cosm/TON equivalents), wrap `getUpdateFee()` and `updatePriceFeeds()` in your transaction flow, denominate the per-update fee in native gas, and rely on Hermes for VAA fetching. This requires zero PYTH holdings and unlocks the rest of the network's surface area.

**Stage 1 — Hold PYTH only if you need a governance voice or want OIS exposure.** PYTH is no longer a "you must hold to use the oracle" token. Hold it if (a) your protocol relies materially on specific publishers and you want delegation-stake influence on publisher selection, (b) you want voting power on fee schedules and listing decisions that affect your feeds, or (c) you want directional exposure to Pyth Pro revenue via the PYTH Reserve flywheel. The benchmark to re-evaluate this: if Pyth Pro ARR clears $10M and the PYTH Reserve buys >$1M/month, the buyback materially competes with quarterly unlock supply.

**Stage 2 — If you publish data, onboard as a first-party publisher.** Exchanges and market makers should treat Pyth publishership as low-cost institutional brand-building plus optional rewards (Y > 0 expected to return). Apply at `pyth.network/become-a-publisher`, run `pyth-agent`, and consider self-staking PYTH into your own pool as a credibility signal. The threshold to re-evaluate: if the DAO authorizes a revenue-funded OIS pool of >50M PYTH/year, publisher-side economics become directly attractive again.

**Stage 3 — If you build infrastructure on top of Pyth, apply for grants and build for the Phase 2 ARR pipeline.** Pyth Pro resellers, AI-agent data routers, OIS-aggregating vaults, and fee-abstraction paymasters are the four clearest builder categories. Apply for Developer or Research grants from the 50M PYTH Ecosystem Grants Program; the bar for funding is comparatively low (proof-of-work plus a credible use case), and grants are paid in a mix of unlocked and locked PYTH.

**Stage 4 — Monitor revenue accrual quarterly.** Track three numbers: Pyth Pro ARR (currently >$1M, target $50M per Michael James in The Block), monthly PYTH Reserve buyback size (function of treasury balance × 33%), and per-chain Pyth Core fee revenue (set quarterly via OP-PIPs). These three numbers, divided by 12-month forward token unlocks (~2B/year), determine whether PYTH is structurally bid-supported or supply-overhanging. The single most important benchmark is whether monthly buyback dollars approach $5–10M, at which point the Reserve materially absorbs unlocks.

**Do not:** denominate user invoices in PYTH today (institutional billing remains USD/stablecoin); assume OIS rewards exist (Y = 0 since April 2026); assume PYTH on Ethereum is Wormhole NTT (it is currently a Wormhole-wrapped representation); or build governance integrations that hard-code program IDs without fetching from the live `pyth-network/governance` repo.

## Caveats

- **OIS rewards are paused (Y = 0) as of April 22, 2026** following OP-PIP-103. Third-party guides quoting 8–10% APY (e.g., BLOCKSIZE, 99bitcoins) reflect pre-pause conditions. Treat all OIS APY references as historical until the DAO authorizes a successor reward source.
- **Cross-chain PYTH is Wormhole-wrapped, not Wormhole NTT.** Despite frequent third-party assertions of "NTT-bridged" PYTH, Pyth's own documentation says only "(wrapped) PYTH tokens may exist on various other chains" via Wormhole. NTT-style burn-and-mint rate limits and unified accounting are not in play for PYTH. Architects should plan around Wormhole portal latency and Guardian attestation models.
- **The Solana staking program ID published in third-party articles can drift.** Always fetch the current `declare_id!()` from `pyth-network/governance/staking/programs/staking/src/lib.rs` rather than hard-coding constants; the program has been upgraded multiple times via Constitutional PIPs.
- **PYTH-denominated subscription billing is proposed but not yet active.** The Phase 2 blog explicitly contemplates USD, stablecoin, **or** PYTH billing for institutional subscriptions, but as of May 2026 the dominant flow is USD/stablecoin invoicing → DAO treasury → 33% monthly Reserve buyback. Project plans should not assume direct PYTH billing as a current revenue channel.
- **Holder-voting power over fee schedules is delegated, not direct.** While the DAO can theoretically vote on fees (Constitutional/Operational PIPs), in practice OP-PIP-87 delegated the quarterly fee-setting to the Pythian Council. A token holder's voice on per-chain fee numbers runs through Council elections rather than direct PIP votes.
- **Treasury figures are early-stage.** Treasury at ~$500K (Dec 2025) and the first executed buyback of ~2.16M PYTH are small relative to a 5.75B-circulating-supply token; the bull case for the Reserve absorbing unlock pressure requires Pyth Pro ARR to scale by 10–50x.
- **Source-quality flags:** Some third-party guides conflate Lazer pricing or report APY ceilings inconsistently. Where third-party numbers conflict with Pyth blog, `forum.pyth.network` PIPs, or Messari quarterly state-of-Pyth reports, prefer the latter.
- **Slashing has not been triggered to date.** OIS slashing is an architectural commitment; no public slashing event has been recorded as of May 2026. The 5% cap and disposition rules remain DAO-governed and unexercised.
- **Staking program ID and exact reward-pool size require live verification.** Third-party sources have alternately cited 100M and 200M PYTH for the OIS reward bootstrap pool; the Pyth blog confirms the 100M figure but engineers should confirm both the reward-pool size and the current `declare_id!()` against the live `pyth-network/governance` repository before production deployment.