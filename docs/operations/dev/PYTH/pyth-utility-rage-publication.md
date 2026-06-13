# How a Project Can Use the PYTH Token

**A technical and economic field guide for builders, May 2026**
*Published at [rage.pythai.net](https://rage.pythai.net) · BANKON Research*

---

## TL;DR

PYTH, the native token of [Pyth Network](https://www.pyth.network/), is now a multi-purpose oracle-economy token rather than a pure governance asset. A project can put PYTH to work in seven distinct ways: (1) stake it for governance voting on the Solana-based [Pyth DAO](https://app.realms.today/dao/PYTH); (2) self-stake or delegate-stake it into [Oracle Integrity Staking (OIS)](https://docs.pyth.network/oracle-integrity-staking) against specific publishers — though emissions are currently zero following [OP-PIP-103](https://forum.pyth.network/t/passed-op-pip-103-pausing-ois-rewards/2471); (3) pay [Pull-oracle update fees](https://docs.pyth.network/price-feeds/core/how-pyth-works/fees) that flow to the DAO treasury; (4) subscribe to [Pyth Pro](https://www.pyth.network/blog/introducing-pyth-pro-reinventing-the-market-data-supply-chain) institutional feeds; (5) earn publisher rewards by streaming first-party data; (6) apply to the [Pyth Ecosystem Grants Program](https://in.superteam.fun/instagrants/pyth-network-grants); and (7) move PYTH across chains through [Wormhole-wrapped bridges](https://docs.pyth.network/home/pyth-token/pyth-token-addresses).

The decisive recent change is the December 2025 launch of the [PYTH Reserve](https://www.theblock.co/post/382357/pyth-token-buyback-program-33-dao-treasury-monthly-pyth-purchases), a structural buyback that deploys 33% of the Pyth DAO treasury balance each month into open-market PYTH purchases, funded by revenue from [Pyth Pro (>$1M ARR in its first month)](https://www.businesswire.com/news/home/20250923720158/en/Pyth-Network-Launches-Pyth-Pro-a-Next-Generation-Subscription-Service-for-Institutional-Market-Data), Pyth Core update fees, Entropy, and Express Relay. Combined with the [OP-PIP-92](https://forum.pyth.network/t/passed-op-pip-92-q1-2026-pyth-express-relay-fee-implementation/2342), [OP-PIP-93](https://forum.pyth.network/t/q1-2026-pyth-express-relay-onchain-fee/2324), and [OP-PIP-94](https://forum.pyth.network/t/passed-op-pip-94-q1-2026-entropy-protocol-fee-implementation/2347) Q1 2026 fee mandates, this transforms PYTH from an emissions-funded incentive token into a revenue-funded value-accrual instrument.

Builders should treat OIS as paused for reward purposes (Y = 0 since April 2026) but still slashable; treat Pyth Pro as the dominant net-new revenue source and therefore the largest indirect demand driver for PYTH via the Reserve; and design integrations on the assumption that all per-update fees remain denominated in destination-chain native gas tokens rather than in PYTH itself. They should also account for the [parallel retirement of Pythnet](https://www.pyth.network/blog/pyth-s-next-chapter-infrastructure-upgrade-and-a-revenue-based-economic-model) under [OP-PIP-100](https://forum.pyth.network/t/passed-op-pip-100-2456) by late 2026, after which the network's center of gravity moves entirely to Pyth Lazer / Pyth Pro infrastructure.

---

## 1. Governance — staking PYTH for votes on Pyth DAO Realms

A project participates in governance by staking PYTH at [staking.pyth.network](https://staking.pyth.network), which routes funds into the Pyth staking program on Solana (deployed from [`pyth-network/governance`](https://github.com/pyth-network/governance)). The same SPL position simultaneously underpins governance voting and is separately allocated to OIS pools — locked tokens (vesting positions) can be used for governance staking but **not** for OIS, because OIS slashing requires unlocked PYTH. Epochs are seven days long, starting Thursdays at 00:00 UTC; staked tokens enter a one-epoch warmup before becoming vote-eligible, and unstaking requires a one-epoch cooldown before tokens are withdrawable.

The [Pyth DAO Constitution](https://github.com/pyth-network/governance/blob/main/docs/constitution/pyth-dao-constitution.md) defines a tri-council structure operated through Pyth DAO LLC, each managing a dedicated multisig wallet:

- **Pythian Council** — eight members plus the Operations Wallet `opsLibxVY7Vz5eYMmSfX8cLFCFVYTtH6fr6MiifMpA7`, configured as a 7-of-9 multisig. Delegated control over oracle program upgrades, the size and denomination of update fees, the Pythnet validator set, and on-chain fee schedules. The third Pythian Council ([OP-PIP-59](https://forum.pyth.network/t/passed-op-pip-59-third-pythian-council-elections/2089)) added members from Douro Labs, the Pyth Data Association, XBTO, and Euler Labs.
- **Price Feed Council** — seven members, Ops Wallet `ACzP6RC98vcBk9oTeAwcH1o5HJvtBzU59b5nqdwc7Cxy`. Manages feed catalog, publisher selection per feed, and minimum publisher counts. The third Price Feed Council ([OP-PIP-66](https://forum.pyth.network/t/passed-op-pip-66-third-price-feed-council-elections/2168)) elected members from PDA, Douro Labs, and Objective Labs with a six-month, 315,000 PYTH stipend (45,000 PYTH per seat).
- **Community Council** — seven members, Ops Wallet `Ef7AjJzDXK6Tn2gYuMvL9YdXATV29b8PwpsT1yoPokTC`. Handles community programs, partnerships, and analyst functions, [introduced in 2024](https://www.pyth.network/blog/introducing-the-new-community-council).

Constitutional PIPs (upgrading governance, staking, or multisig programs) require >67% of Votable Tokens in favor; Operational PIPs voted by the DAO require >50%; PIPs delegated to a council require only that council's multisig threshold. To submit a DAO-level PIP a proposer must hold ≥0.25% of Votable Tokens (approximately 25M PYTH at current circulating supply). All on-chain voting takes place at [app.realms.today/dao/PYTH](https://app.realms.today/dao/PYTH), with proposals published at [forum.pyth.network](https://forum.pyth.network/).

The DAO's actual control surface widened materially in 2025–26. Beyond electing councils and managing treasury withdrawals, the DAO now sets quarterly on-chain fee schedules for [Pyth Core](https://forum.pyth.network/t/q2-2026-pyth-core-onchain-fees/2464), [Express Relay](https://forum.pyth.network/t/passed-op-pip-92-q1-2026-pyth-express-relay-fee-implementation/2342), and [Entropy](https://forum.pyth.network/t/passed-op-pip-94-q1-2026-entropy-protocol-fee-implementation/2347); appoints exclusive operators (OP-PIP-67 made Douro Labs the exclusive Express Relay relayer at 6% of platform fees versus 94% to the DAO); and authorizes treasury sweeps of fees from product contracts. Crucially, **OP-PIP-87** delegated to the Pythian Council a standing quarterly mandate to set on-chain fee parameters across all Pyth products except Pyth Pro, making fee policy a Council-controlled lever rather than a contributor-controlled one.

---

## 2. Oracle Integrity Staking (OIS) — paused-but-slashable as of April 2026

[OIS](https://docs.pyth.network/oracle-integrity-staking) uses the same Solana staking program and the same 7-day epoch as governance. Each onboarded publisher is programmatically assigned a staking pool. The publisher self-stakes into their pool, and other PYTH holders can delegate-stake to that same pool as an LP-like position. At each epoch boundary, pool snapshots are taken, soft caps are recomputed (the cap dynamically expands and shrinks with the number of symbols a publisher covers, weighted to favor feeds with fewer publishers), and rewards/penalties are applied. Stake above the soft cap earns no rewards but is still slashable.

The economic parameters governed by the Pyth DAO:

- **Slashing cap**: 5% of stake in the affected pool per slashing event. Both publisher self-stake and delegators are slashed pro-rata.
- **Delegate fee**: 20% of net rewards (after penalties) deducted by the publisher from delegator rewards. DAO-adjustable.
- **Maximum reward rate (Y)**: DAO-set APY ceiling. Historically the cap was approximately 10% APY; third-party operators such as [BLOCKSIZE](https://blocksize.info/blog/pyth-staking-guide/) advertised ~8–10% APY through 2025.

**As of April 2026, Y = 0.** Per the [Pyth DAO forum confirmation](https://forum.pyth.network/t/ois-rewards-update-april-2026/2479): "Following the passage of OP-PIP-103: Pausing OIS Rewards, the OIS reward rate parameter (Y) has been set to 0 as of April 2026." This followed depletion of the original 100M PYTH bootstrap reward pool seeded by the Pyth Data Association on 22–23 April 2026, as described in the [Phase 2 economic-model blog](https://www.pyth.network/blog/pyth-s-next-chapter-infrastructure-upgrade-and-a-revenue-based-economic-model): "That reward pool has distributed rewards on schedule and is now approaching depletion, expected by the end of April, 2026. OP-PIP-103 proposes to set the OIS reward rate parameter (Y) to 0 before the pool reaches zero."

Per [KuCoin News, citing Pyth's April 23 announcement](https://www.kucoin.com/news/flash/pyth-network-to-retire-pythnet-app-chain-and-end-ois-rewards-in-2026), OIS at its peak had "approximately 1 billion PYT[H] tokens" staked across "approximately 120 data provider pools" — distinct from the 100M reward pool which it dwarfed by 10x. Pyth notes that "the OIS staking and penalty system remains active, with unstaking available at any time." No public on-chain slashing events have been triggered as of May 2026.

OIS supports four concrete patterns for projects. First, a market maker or exchange that becomes a Pyth publisher can self-stake PYTH into its own pool to anchor delegator confidence and (when Y returns above zero) compound publisher rewards. Second, a DeFi protocol that consumes Pyth feeds can delegate-stake to the publishers it relies on as a defensive hedge — slashing partially offsets oracle losses, and delegation pressure to underperforming publishers signals to the Price Feed Council. Third, a treasury manager can build an aggregator vault that auto-allocates delegator stake across the top-ranked publishers (currently uneconomic with Y = 0 but architecturally relevant). Fourth, a "PYTH-as-an-LP" wrapper can tokenize delegated positions for liquid-staking-style secondary trading, subject to warmup/cooldown friction.

---

## 3. Pull-oracle update fees — native-gas-denominated, DAO-treasury-routed

Pyth's Pull model requires a consumer to fetch a signed VAA from [Hermes](https://hermes.pyth.network/) and submit `updatePriceFeeds(bytes[] updateData)` to the destination-chain Pyth receiver, paying the fee in `msg.value` (or its chain equivalent). The fee is denominated in the **destination chain's native unit, never in PYTH**, and the consumer pays both the Pyth fee and the chain's gas.

Per [Pyth's official fees documentation](https://docs.pyth.network/price-feeds/core/how-pyth-works/fees), the default fee where no governance vote has set a custom value is 1 unit of the smallest denomination of the native gas token (1 wei on Ethereum-class chains, 1 octa on Aptos, 1 MIST on Sui, 1 uSTX on [Stacks](https://docs.pyth.network/price-feeds/core/use-real-time-data/pull-integration/stacks)). The Pythian Council resets these levels quarterly. The [Q1 2026 EVM rebase under OP-PIP-93](https://forum.pyth.network/t/q1-2026-pyth-core-onchain-fees/2280) calibrated EVM update fees to target approximately $0.01 per update across 70 EVM chains, with [OP-PIP-111](https://forum.pyth.network/t/q2-2026-pyth-core-onchain-fees/2464) refreshing levels for Q2 2026.

**Fee revenue flow**: Fees collected on each chain accumulate in the Pyth receiver contract for that chain. Periodic governance proposals move the accumulated fees from product contracts into the Pyth DAO Treasury wallet on Solana. From the treasury, 33% of the running balance is deployed monthly via the PYTH Reserve buyback. Note that under current parameters fees do **not** flow directly to publishers — publisher rewards historically came from the Publisher Rewards allocation (22% of the 10B max supply) and from the OIS reward pool (now Y = 0). The [Phase 2 model](https://www.pyth.network/blog/pyth-s-next-chapter-infrastructure-upgrade-and-a-revenue-based-economic-model) contemplates redirecting on-chain revenue to a revived OIS reward pool.

For projects with fee-abstraction needs (gasless apps, smart-account flows), the recommended pattern is to wrap `getUpdateFee()` and bundle the Pyth fee with the user's intent transaction, sponsored by the project's paymaster — exactly as integrations on Stacks and Sei demonstrate.

---

## 4. Pyth Pro and Pyth Pro X — the institutional subscription engine

Pyth Pro is a subscription-based off-chain/on-chain hybrid distribution product [launched on 24 September 2025](https://www.businesswire.com/news/home/20250923720158/en/Pyth-Network-Launches-Pyth-Pro-a-Next-Generation-Subscription-Service-for-Institutional-Market-Data). It sits in a [tiered product stack alongside Pyth Lazer](https://docs.pyth.network/lazer) (low-latency feeds), Pyth Core (Pull oracle), Entropy (on-chain randomness), and Express Relay (MEV/order-flow) — Pyth Pro is the institutional commercial layer, not a rename of Lazer despite occasional third-party conflation.

Public list pricing per [Coincub's analysis citing Pyth's pricing page](https://coincub.com/price-prediction/pyth-price-prediction/):

- **Pyth Crypto** — free; crypto feeds at 1-second updates.
- **Pyth Crypto+** — $5,000/month; crypto data at 1ms updates with new ticker additions weekly.
- **Pyth Pro** — $10,000/month; 2,000+ feeds across cryptocurrencies, equities, futures, fixed income/Treasury rates, commodities, and FX; 1ms updates; enterprise support and redistribution rights.
- **Pyth Pro X** — exchange-specific commercial tier ([launched separately for venues](https://www.pyth.network/blog/introducing-pyth-pro-x-institutional-market-data-built-for-exchanges)) used by Coinbase International Exchange, BitMEX, Bitget, LMAX, and Crypto.com for collateral valuation, liquidations, and new market launches.

**Adoption metrics**: per [Messari's State of Pyth Q4 2025 report cited in Coincub](https://coincub.com/price-prediction/pyth-price-prediction/), "Messari reports 54 active subscribers in Q4 2025, up from 28 in Q3 and 8 in Q2, and $352,600 in Q4 revenue from Pyth Pro, with ARR surpassing $1M." The "$1M ARR in first month" and "80+ active subscribers" figures from [The Block's December 12, 2025 interview with Michael James](https://www.theblock.co/post/382357/pyth-token-buyback-program-33-dao-treasury-monthly-pyth-purchases) reflect annualized run-rate and a December snapshot respectively, not a single quarter's recognized revenue. James, head of institutional business development at Douro Labs, added in the same interview: "Based on pipeline projections for the next 12–18 months, we're targeting $50 million ARR."

[Pyth Pro for AI Agents](https://www.pyth.network/blog/pyth-pro-for-ai-agents-institutional-market-data-for-autonomous-finance), launched 31 March 2026, extends the same data fabric to autonomous agent workflows with 3,000+ feeds and redistribution-friendly licensing. Pyth's own framing in that announcement: "AI agents will consume more market data than humans ever have. A single agent workflow can query prices across dozens of assets in seconds, repeatedly, 24/7." [Pyth Pro on Cardano](https://crypto-economy.com/pyth-pro-goes-live-on-cardano-delivering-institutional-pricing-for-defi-builders/) launched in early May 2026, with Indigo Protocol as the first integration.

**Payment flow**: Pyth Pro institutional billing is denominated in USD and on-chain stablecoins as of May 2026. The [Phase 2 blog](https://www.pyth.network/blog/pyth-s-next-chapter-infrastructure-upgrade-and-a-revenue-based-economic-model) explicitly proposes that "payments can be made in multiple ways, including USD, onchain stablecoins, or PYTH tokens" — PYTH-denominated billing is on the roadmap but not the default. Subscription revenue accrues to the Pyth DAO Treasury, and one-third of the resulting treasury balance is recycled monthly through the PYTH Reserve into open-market PYTH purchases.

---

## 5. Publisher rewards — becoming a first-party data publisher

Publishing access is restricted to first-party data owners — exchanges, regulated market makers, banks, and trading firms — vetted by the Pyth Data Association. Per the [Pyth Publisher onboarding documentation](https://docs.pyth.network/price-feeds/core/publish-data), the flow is:

1. Register interest at [pyth.network/publishers](https://www.pyth.network/publishers) and execute a publisher agreement.
2. Generate a Solana ed25519 keypair (typically one for test/devnet, one for mainnet) and share the public key with PDA.
3. PDA assists in provisioning a Pythnet validator (transitioning to Lazer infrastructure per [OP-PIP-100](https://www.pyth.network/blog/pyth-s-next-chapter-infrastructure-upgrade-and-a-revenue-based-economic-model)) and a Solana RPC endpoint.
4. Deploy [`pyth-agent`](https://github.com/pyth-network/pyth-agent) — open-source, in the Pyth Network GitHub organization — point it at the publisher's internal price source via JSON-RPC, and start signing per-symbol updates.
5. Performance is tracked publicly via the [Publisher Metrics dashboard](https://www.pyth.network/blog/introducing-pyth-publishers-metrics), which scores price accuracy versus aggregate, uptime, calibration to a Laplace confidence distribution, and price-quality regression.

When OIS rewards (Y) are positive, publishers earn from the OIS pool proportional to their stake-weighted pool, net of slashing. The Publisher Rewards tokenomics bucket (22% = 2.2B PYTH) was the historical funding source pre-OIS and continues to seed grants for new asset coverage.

[Per Messari's "Pyth: Pricing the World" report (January 2026)](https://messari.io/report/pyth-pricing-the-world-and-capturing-the-value): "Pyth secures more than $6 billion in value across 301 protocols, representing 5.9% of total oracle market share by value secured… 125+ publishers, 650+ integrations, and over $2.3 trillion in cumulative traded volume." Institutional publishers active as of Q1 2026 include Jane Street, Two Sigma, Jump Trading, Cumberland (DRW), Optiver, Wintermute, Susquehanna, Virtu, Hudson River Trading, Galaxy, Flow Traders, IMC, Tower Research, Cboe Global Markets, LMAX, Coinbase, Binance, OKX, Bybit, Revolut, Raydium, Orca, Kaiko, Kalshi — and uniquely, [the U.S. Department of Commerce's Bureau of Economic Analysis](https://www.pyth.network/blog/pyth-network-selected-by-u-s-department-of-commerce-to-verify-and-distribute-economic-data-onchain).

---

## 6. Treasury, grants, and ecosystem programs

The Pyth DAO Treasury composition is split among PYTH tokens (drawn from the 52% Ecosystem Growth allocation), USDC/USDT/SOL/wSOL fee revenue swept from Pyth Core, Entropy, and Express Relay contracts via OP-PIPs, and Pyth Pro subscription revenue. Treasury holdings sat near $500K at the December 2025 PYTH Reserve launch per [Blockonomi](https://blockonomi.com/pyth-network-launches-monthly-buybacks-with-33-dao-treasury/): "The first buyback is expected to range between $100,000 and $200,000, reflecting the DAO treasury's current balance of around $500,000."

**Grant programs available to builders:**

- **[Pyth Ecosystem Grants Program](https://www.pyth.network/blog/pyth-ecosystem-grants-program)** — launched May 2024 by the Pyth Data Association with 50M PYTH (≈$21M at announcement). Three tracks: Community Grants (educational content and events), Research Grants (oracle improvements, aggregation, novel applications), and Developer Grants (SDKs, tooling, integrations, cross-chain). Tokens are distributed as a mix of unlocked and locked PYTH from the Ecosystem Growth bucket.
- **[Superteam Pyth Grants](https://in.superteam.fun/instagrants/pyth-network-grants)** — fast-track ($1K–$5K) micro-grants with 48-hour decisions, focused on integrations, dev education, and dev tooling. 50% paid on approval, 50% on delivery.
- **Quarterly council allocations** — Council Operations Wallets make targeted stipends and operational grants via OP-PIPs.
- **Hackathon prize pools** — Pyth co-sponsors prize tracks at Solana, EthGlobal, ETHCC, Encode Club, Sui, Aptos, and other ecosystem hackathons.

---

## 7. Cross-chain mobility of PYTH

PYTH is a canonical SPL token on Solana at mint [`HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3`](https://solscan.io/token/HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3) with mint and freeze authorities disabled. Per [Pyth's own token-addresses documentation](https://docs.pyth.network/home/pyth-token/pyth-token-addresses), "through the use of permissionless bridges like Wormhole, (wrapped) PYTH tokens may exist on various other chains." In practice this means:

- **Solana (canonical, SPL)**: All staking, DAO voting, and the largest spot liquidity (Raydium, Orca, Jupiter aggregator) live here.
- **Ethereum mainnet (Wormhole-wrapped ERC-20)**: [`0xefc0CED4B3D536103e76a1c4c74F0385C8F4Bdd3`](https://etherscan.io/token/0xefc0ced4b3d536103e76a1c4c74f0385c8f4bdd3). This is the Wormhole portal-bridged wrapper, not a Wormhole NTT deployment.
- **Arbitrum One (Wormhole-wrapped)**: `0xE4D5c6aE46ADFAF04313081e8C0052A30b6Dd724`.
- **Base, Optimism, BNB Chain, Polygon, Sui, Aptos**: Wormhole-wrapped representations where listed.

Because the deployment model is Wormhole portal-wrapped rather than full Wormhole NTT, moving PYTH from Solana to an EVM chain currently locks SPL PYTH in the Wormhole Solana vault and mints wrapped PYTH on the destination; the reverse burns wrapped and unlocks SPL. There is no NTT-style burn-and-mint with a unified accounting layer for PYTH at this time. [Stakers who hold tokens on an EVM chain can map an EVM wallet to a Solana address](https://www.bitget.com/news/detail/12560603884450) on the staking site so the underlying staked SPL PYTH still controls the votes.

---

## 8. Tokenomics and supply state (May 2026)

Per [Pyth's official PYTH Distribution documentation](https://docs.pyth.network/home/pyth-token/pyth-distribution) and [Understanding the PYTH Tokenomics blog](https://www.pyth.network/blog/understanding-the-pyth-tokenomics):

- **Max supply**: 10,000,000,000 PYTH (fixed).
- **Allocation**: Publisher Rewards 22% (2.2B), Ecosystem Growth 52% (5.2B), Protocol Development 10% (1B), Community & Launch 6% (600M; fully unlocked at TGE November 2023), Private Sales 10% (1B).
- **Vesting**: 85% of supply was initially locked, releasing on cliffs at 6, 18, 30, and 42 months post-launch (May 2024 / May 2025 / May 2026 / May 2027). The [May 19, 2026 cliff just added another ~2.13B PYTH](https://phemex.com/academy/what-is-pyth-network-token-unlock), of which the majority is earmarked for ecosystem growth and publisher rewards (programmatic, not insider sell pressure).
- **Net emissions**: With OIS Y = 0 since April 2026 and the PYTH Reserve buying tokens monthly, net protocol-level token flow is buyback-positive for the first time in the network's history. [Per KuCoin News](https://www.kucoin.com/news/flash/pyth-network-to-retire-pythnet-app-chain-and-end-ois-rewards-in-2026), "The PYTH reserve has already purchased around 12 million tokens from the open market" as of late April 2026.

---

## 9. The PYTH Reserve — structural buyback mechanics

Launched 12 December 2025 and detailed in [The Block's interview with Douro Labs' Michael James](https://www.theblock.co/post/382357/pyth-token-buyback-program-33-dao-treasury-monthly-pyth-purchases): "The buyback program — formally called the 'PYTH Reserve' — uses network revenue to acquire tokens each month. Revenue flows into the Pyth DAO treasury, and '33% of the total treasury balance' will be used each month to purchase PYTH on the open market." The first month's buyback was estimated at $100K–$200K against the ~$500K treasury balance per [MEXC News reporting on Pyth's announcement](https://www.mexc.co/news/264935): "The first buyback this December is expected to be between $100,000 and $200,000, and this amount will increase as the network earns more revenue."

The Reserve is funded from four revenue streams per [Blockonomi's coverage](https://blockonomi.com/pyth-network-launches-monthly-buybacks-with-33-dao-treasury/): "Revenue for the treasury comes from Pyth Network's four main products: Pyth Pro, Pyth Core, Entropy, and Express Relay." Acquired tokens are permanently locked in a multisig-controlled Reserve wallet, with on-chain transparency; James declined to provide long-term supply-impact estimates. Pyth's positioning per its own tweet quoted in [Bitget News](https://www.bitget.com/news/detail/12560605115508): "Every month, the DAO deploys one-third of its treasury to acquire PYTH from the open market. The PYTH Reserve is governed, systematic, and transparent."

By April 2026, [KuCoin News reports the Reserve "has already purchased around 12 million tokens from the open market"](https://www.kucoin.com/news/flash/pyth-network-to-retire-pythnet-app-chain-and-end-ois-rewards-in-2026), confirming that the program has executed monthly as designed.

---

## 10. Recent developments through May 2026

- **Pyth Pro launch (24 September 2025)**: [Hedgeweek](https://www.hedgeweek.com/pyth-network-launches-pyth-pro-cross-asset-pricing-service/) and [Business Wire](https://www.businesswire.com/news/home/20250923720158/en/Pyth-Network-Launches-Pyth-Pro-a-Next-Generation-Subscription-Service-for-Institutional-Market-Data) confirm the launch, developed with Douro Labs, with Jump Trading Group and several major banks in the early-access program.
- **U.S. Department of Commerce GDP partnership (28 August 2025)**: Pyth (alongside Chainlink) selected by the BEA to publish quarterly GDP data on-chain. Per [Crypto Briefing](https://cryptobriefing.com/pyth-token-surge-commerce/): "PYTH token soars 68% after Commerce Department taps Pyth Network for GDP feeds." CPI and BLS extensions [are publicly contemplated by Pyth CEO Mike Cahill and Secretary Lutnick](https://www.thestreet.com/crypto/policy/after-gdp-u-s-may-put-cpi-data-on-blockchain-according-to-mike-cahill).
- **PYTH Reserve launch (12 December 2025)**: 33% of monthly treasury balance deployed to open-market PYTH buybacks; tokens locked in the Reserve wallet under a supermajority unlock requirement.
- **DAO fee mandate (OP-PIP-87, 9 December 2025)**: Pythian Council given the quarterly mandate to set on-chain fees for Pyth Core, Entropy, and Express Relay (excluding Pyth Pro). Q1 2026 implementations: [OP-PIP-92](https://forum.pyth.network/t/passed-op-pip-92-q1-2026-pyth-express-relay-fee-implementation/2342) (Express Relay tiered fees), [OP-PIP-93](https://forum.pyth.network/t/q1-2026-pyth-core-onchain-fees/2280) (Core fees on 70 EVM chains targeting ~$0.01/update), and [OP-PIP-94](https://forum.pyth.network/t/passed-op-pip-94-q1-2026-entropy-protocol-fee-implementation/2347) (Entropy fees on 19 EVM chains). Q2 2026: [OP-PIP-111](https://forum.pyth.network/t/q2-2026-pyth-core-onchain-fees/2464) (Core refresh) and OP-PIP-112 (Entropy refresh).
- **Pythnet retirement (OP-PIP-100, April 2026)**: [Pyth's Phase 2 blog](https://www.pyth.network/blog/pyth-s-next-chapter-infrastructure-upgrade-and-a-revenue-based-economic-model) confirms: "Pythnet is being retired per OP-PIP-100, with sunset scheduled for later in 2026. OIS rewards are winding down with OP-PIP-103, setting Y to 0 before the reward pool depletes. Staking and slashing themselves remain live." [KuCoin News](https://www.kucoin.com/news/flash/pyth-network-to-retire-pythnet-app-chain-and-end-ois-rewards-in-2026) adds operational detail: "The network upgrade will refocus efforts on Lazer, Pyth Pro, and the data market."
- **OIS rewards paused (OP-PIP-103, April 2026)**: [Y = 0 confirmed](https://forum.pyth.network/t/ois-rewards-update-april-2026/2479) after the 100M PYTH bootstrap pool depleted on 22–23 April 2026. The [original proposal](https://forum.pyth.network/t/passed-op-pip-103-pausing-ois-rewards/2471) states it will "Preserve OIS staking and slashing mechanisms — publishers and delegators retain stake at risk."
- **30-month cliff unlock (19 May 2026)**: ~2.13B PYTH released; majority earmarked for ecosystem growth and publisher rewards.
- **Pyth Pro for AI Agents (31 March 2026)**: [3,000+ feeds with agent-native API](https://www.pyth.network/blog/pyth-pro-for-ai-agents-institutional-market-data-for-autonomous-finance), including `get_price_no_older_than` and `get_historical_price` (history from April 2025 onward).
- **Pyth Pro on Cardano (May 2026)**: [Pyth Pro went live on Cardano](https://crypto-economy.com/pyth-pro-goes-live-on-cardano-delivering-institutional-pricing-for-defi-builders/) with sub-100ms latency; Indigo Protocol is the first active integration.

---

## 11. Integration patterns for builders

**Auto-staking OIS vault**: Tokenize delegator positions into an SPL/Token-2022 share token. The vault holds PYTH in OIS pools allocated by a heuristic (top-N publishers by quality score) and rebalances at epoch boundaries. With Y = 0 today the yield is zero, so this is best built and tested ahead of a Phase 2 reward reactivation.

**Governance aggregator**: Aggregate delegated PYTH and vote programmatically using the Realms voting program and the Pyth staking program. Add an off-chain signal layer (Snapshot-like) for delegators to instruct the aggregator on each OP-PIP.

**Pyth Pro reseller**: With a $10K/mo enterprise tier and redistribution rights, build a developer-tier reseller — capturing margin between wholesale and downstream subscriptions. AI-agent platforms and quant tooling vendors are obvious customers.

**Fee-abstraction wrapper**: Smart-account paymasters that absorb Pyth update fees in the destination chain's native token, charging users a flat USD subscription on the application side. With per-update fees calibrated to approximately $0.01 on EVM, absorbed cost is tiny versus UX uplift.

**Cross-chain PYTH liquidity router**: Combine Wormhole Portal bridging, Jupiter aggregation on Solana, and Uniswap v3 on Ethereum/Base/Arbitrum to enable cross-chain PYTH swaps for treasury managers needing to consolidate into the staking-eligible Solana SPL form.

**SDKs and contracts**:

- Price feed consumption: [`@pythnetwork/pyth-sdk-solidity`](https://github.com/pyth-network/pyth-sdk-solidity) (Solidity), [`pyth-solana-receiver-sdk`](https://crates.io/crates/pyth-solana-receiver-sdk) (Rust), [`@pythnetwork/pyth-sui-js`](https://github.com/pyth-network/pyth-crosschain), [`@pythnetwork/pyth-aptos-js`](https://github.com/pyth-network/pyth-crosschain), `pyth-sdk-cw` (CosmWasm).
- Pyth Pro / Lazer: `@pythnetwork/pyth-lazer-sdk`.
- OIS / staking: Anchor IDL in [`pyth-network/governance/staking/programs/staking`](https://github.com/pyth-network/governance/tree/main/staking).
- Express Relay: `@pythnetwork/express-relay-evm-js`, `express-relay-svm`.
- Pyth Solana Receiver program: `rec5EKMGg6MxZYaMdyBfgwp4d5rB9T1VQH5pJv5LtFJ`.
- Hermes API: [hermes.pyth.network](https://hermes.pyth.network) (PDA-hosted); alternate instances at Triton, P2P, Liquify, EXTR.

---

## 12. Recommendations — a staged playbook

**Stage 0 — Integrate Pyth feeds before holding any PYTH.** Every project should treat Pyth Core integration as the entry point. Use [`@pythnetwork/pyth-sdk-solidity`](https://github.com/pyth-network/pyth-sdk-solidity) (or the SVM/Sui/Aptos/Cosm/TON equivalents), wrap `getUpdateFee()` and `updatePriceFeeds()` in your transaction flow, denominate the per-update fee in native gas, and rely on Hermes for VAA fetching. This requires zero PYTH holdings and unlocks the rest of the network's surface area.

**Stage 1 — Hold PYTH only if you need a governance voice or want OIS exposure.** PYTH is no longer a "you must hold to use the oracle" token. Hold it if (a) your protocol relies materially on specific publishers and you want delegation-stake influence on publisher selection, (b) you want voting power on fee schedules and listing decisions that affect your feeds, or (c) you want directional exposure to Pyth Pro revenue via the PYTH Reserve flywheel. The benchmark to re-evaluate this: if Pyth Pro ARR clears $10M and the PYTH Reserve buys >$1M/month, the buyback materially competes with quarterly unlock supply.

**Stage 2 — If you publish data, onboard as a first-party publisher.** Exchanges and market makers should treat Pyth publishership as low-cost institutional brand-building plus optional rewards (Y > 0 expected to return). Apply at [pyth.network/publishers](https://www.pyth.network/publishers), run [`pyth-agent`](https://github.com/pyth-network/pyth-agent), and consider self-staking PYTH into your own pool as a credibility signal.

**Stage 3 — If you build infrastructure on top of Pyth, apply for grants and build for the Phase 2 ARR pipeline.** Pyth Pro resellers, AI-agent data routers, OIS-aggregating vaults, and fee-abstraction paymasters are the four clearest builder categories. Apply for Developer or Research grants from the 50M PYTH Ecosystem Grants Program; grants are paid in a mix of unlocked and locked PYTH.

**Stage 4 — Monitor revenue accrual quarterly.** Track three numbers: Pyth Pro ARR (currently >$1M, target $50M), monthly PYTH Reserve buyback size (function of treasury balance × 33%), and per-chain Pyth Core fee revenue (set quarterly via OP-PIPs). These three numbers, divided by 12-month forward token unlocks (~2B/year), determine whether PYTH is structurally bid-supported or supply-overhanging. The single most important benchmark is whether monthly buyback dollars approach $5–10M, at which point the Reserve materially absorbs unlocks.

**Do not**: denominate user invoices in PYTH today (institutional billing remains USD/stablecoin); assume OIS rewards exist (Y = 0 since April 2026); assume PYTH on Ethereum is Wormhole NTT (it is currently a Wormhole-wrapped representation); build governance integrations that hard-code program IDs without fetching from the live [`pyth-network/governance`](https://github.com/pyth-network/governance) repo; or build on Pythnet (it is being [retired by end of 2026](https://www.pyth.network/blog/pyth-s-next-chapter-infrastructure-upgrade-and-a-revenue-based-economic-model)).

---

## 13. Caveats and source-quality notes

- **OIS rewards are paused (Y = 0)** as of 22–23 April 2026 following OP-PIP-103. Third-party guides quoting 8–10% APY reflect pre-pause conditions. Treat all OIS APY references as historical until the DAO authorizes a successor reward source funded by on-chain revenue.
- **Cross-chain PYTH is Wormhole-wrapped, not Wormhole NTT.** Despite frequent third-party assertions of "NTT-bridged" PYTH, [Pyth's own documentation](https://docs.pyth.network/home/pyth-token/pyth-token-addresses) describes wrapped representations via Wormhole. NTT-style burn-and-mint with unified accounting is not in play for PYTH.
- **The Pyth Pro / Lazer relationship is layered, not a rename.** Some third-party sources (including [Coincub](https://coincub.com/price-prediction/pyth-price-prediction/)) state "It was previously called Pyth Lazer." More precisely, [Pyth's own documentation](https://docs.pyth.network/lazer) and Messari's [Pyth: Pricing the World](https://messari.io/report/pyth-pricing-the-world-and-capturing-the-value) describe a tiered stack: Lazer is the low-latency infrastructure layer, Pyth Pro is the institutional commercial product built on top. Some Pyth Pro documentation URLs route through `/lazer` paths, reflecting the shared infrastructure.
- **Pyth Pro adoption figures vary by metric and time window.** Q4 2025 had 54 active subscribers and $352,600 in recognized quarterly revenue per Messari; the "80+ active subscribers" and "$1M ARR" cited by Michael James in [The Block (12 December 2025)](https://www.theblock.co/post/382357/pyth-token-buyback-program-33-dao-treasury-monthly-pyth-purchases) reflect a December snapshot and annualized run-rate respectively. Both are accurate at their respective dates and metrics.
- **Slashing has not been triggered to date.** OIS slashing is an architectural commitment; no public slashing event has been recorded as of May 2026. The 5% cap and disposition rules remain DAO-governed and unexercised.
- **Solana program IDs can drift across upgrades.** Always fetch the current `declare_id!()` from [`pyth-network/governance`](https://github.com/pyth-network/governance) rather than hard-coding constants; the staking program has been upgraded multiple times via Constitutional PIPs.
- **PYTH-denominated subscription billing is proposed but not yet active.** The [Phase 2 blog](https://www.pyth.network/blog/pyth-s-next-chapter-infrastructure-upgrade-and-a-revenue-based-economic-model) contemplates USD, stablecoin, **or** PYTH billing for institutional subscriptions, but as of May 2026 the dominant flow is USD/stablecoin invoicing → DAO treasury → 33% monthly Reserve buyback.
- **Treasury figures are early-stage.** Treasury at ~$500K (December 2025) and the first executed buybacks (~12M PYTH cumulative by April 2026) are small relative to a ~7.88B-circulating-supply token; the bull case for the Reserve absorbing unlock pressure requires Pyth Pro ARR to scale 10–50x. Targets: [$50M ARR within 12–18 months per James](https://www.theblock.co/post/382357/pyth-token-buyback-program-33-dao-treasury-monthly-pyth-purchases).

---

## Primary sources

- [Pyth Network blog: Phase 2 economic model & Pythnet retirement](https://www.pyth.network/blog/pyth-s-next-chapter-infrastructure-upgrade-and-a-revenue-based-economic-model)
- [Pyth Network blog: Introducing Pyth Pro](https://www.pyth.network/blog/introducing-pyth-pro-reinventing-the-market-data-supply-chain)
- [Pyth Network blog: Pyth Pro X for exchanges](https://www.pyth.network/blog/introducing-pyth-pro-x-institutional-market-data-built-for-exchanges)
- [Pyth Network blog: Pyth Pro for AI Agents](https://www.pyth.network/blog/pyth-pro-for-ai-agents-institutional-market-data-for-autonomous-finance)
- [Pyth Network blog: U.S. Department of Commerce partnership](https://www.pyth.network/blog/pyth-network-selected-by-u-s-department-of-commerce-to-verify-and-distribute-economic-data-onchain)
- [Pyth Network blog: Understanding the PYTH Tokenomics](https://www.pyth.network/blog/understanding-the-pyth-tokenomics)
- [Pyth Network blog: OIS announcement](https://www.pyth.network/blog/oracle-integrity-staking-incentivizing-safer-price-feeds-for-a-more-secure-defi)
- [Pyth Network blog: Phase Two institutional monetization](https://www.pyth.network/blog/phase-two-institutional-monetization-through-offchain-data)
- [Pyth Network blog: Ecosystem Grants Program](https://www.pyth.network/blog/pyth-ecosystem-grants-program)
- [Pyth Network blog: Community Council](https://www.pyth.network/blog/introducing-the-new-community-council)
- [Pyth Developer Hub: Oracle Integrity Staking](https://docs.pyth.network/oracle-integrity-staking)
- [Pyth Developer Hub: Fees](https://docs.pyth.network/price-feeds/core/how-pyth-works/fees)
- [Pyth Developer Hub: Publish Data](https://docs.pyth.network/price-feeds/core/publish-data)
- [Pyth Developer Hub: PYTH Distribution](https://docs.pyth.network/home/pyth-token/pyth-distribution)
- [Pyth Developer Hub: PYTH token addresses](https://docs.pyth.network/home/pyth-token/pyth-token-addresses)
- [Pyth Developer Hub: Pyth Pro / Lazer](https://docs.pyth.network/lazer)
- [Pyth DAO Constitution (GitHub)](https://github.com/pyth-network/governance/blob/main/docs/constitution/pyth-dao-constitution.md)
- [Pyth Governance repository (GitHub)](https://github.com/pyth-network/governance)
- [Pyth Crosschain repository (GitHub)](https://github.com/pyth-network/pyth-crosschain)
- [Pyth DAO forum: OP-PIP-103 OIS rewards pause (passed)](https://forum.pyth.network/t/passed-op-pip-103-pausing-ois-rewards/2471)
- [Pyth DAO forum: OIS Rewards Update April 2026](https://forum.pyth.network/t/ois-rewards-update-april-2026/2479)
- [Pyth DAO forum: OP-PIP-92 Express Relay Q1 2026 fees](https://forum.pyth.network/t/passed-op-pip-92-q1-2026-pyth-express-relay-fee-implementation/2342)
- [Pyth DAO forum: OP-PIP-94 Entropy Q1 2026 fees](https://forum.pyth.network/t/passed-op-pip-94-q1-2026-entropy-protocol-fee-implementation/2347)
- [Pyth DAO forum: Q2 2026 Pyth Core Onchain Fees (OP-PIP-111)](https://forum.pyth.network/t/q2-2026-pyth-core-onchain-fees/2464)
- [Pyth DAO Realms voting](https://app.realms.today/dao/PYTH)
- [Pyth staking dashboard](https://staking.pyth.network)
- [Hermes API](https://hermes.pyth.network)
- [Business Wire: Pyth Pro launch (24 September 2025)](https://www.businesswire.com/news/home/20250923720158/en/Pyth-Network-Launches-Pyth-Pro-a-Next-Generation-Subscription-Service-for-Institutional-Market-Data)
- [The Block: PYTH Reserve buyback program (12 December 2025)](https://www.theblock.co/post/382357/pyth-token-buyback-program-33-dao-treasury-monthly-pyth-purchases)
- [FinanceFeeds: Pyth Pro $50B market data target](https://financefeeds.com/pyth-targets-50-billion-market-data-industry-with-institutional-subscription-launch/)
- [Hedgeweek: Pyth Pro launch coverage](https://www.hedgeweek.com/pyth-network-launches-pyth-pro-cross-asset-pricing-service/)
- [Messari: Pyth — Pricing the World and Capturing the Value (January 2026)](https://messari.io/report/pyth-pricing-the-world-and-capturing-the-value)
- [Messari: State of Pyth Q2 2025](https://messari.io/report/state-of-pyth-q2-2025)
- [Messari: State of Pyth Q3 2025](https://messari.io/report/state-of-pyth-q3-2025)
- [Messari: Understanding Pyth Network](https://messari.io/report/understanding-pyth-network-a-comprehensive-overview)
- [Crypto Briefing: PYTH +68% on Commerce Department news](https://cryptobriefing.com/pyth-token-surge-commerce/)
- [TheStreet: Commerce CPI on blockchain via Pyth](https://www.thestreet.com/crypto/policy/after-gdp-u-s-may-put-cpi-data-on-blockchain-according-to-mike-cahill)
- [KuCoin News: Pythnet retirement & OIS sunset](https://www.kucoin.com/news/flash/pyth-network-to-retire-pythnet-app-chain-and-end-ois-rewards-in-2026)
- [Crypto Economy: Pyth Pro on Cardano](https://crypto-economy.com/pyth-pro-goes-live-on-cardano-delivering-institutional-pricing-for-defi-builders/)
- [Coincub: PYTH price analysis & Pyth Pro Q4 2025 metrics](https://coincub.com/price-prediction/pyth-price-prediction/)
- [Blockonomi: PYTH Reserve coverage](https://blockonomi.com/pyth-network-launches-monthly-buybacks-with-33-dao-treasury/)
- [Bitget News: PYTH Reserve coverage](https://www.bitget.com/news/detail/12560605115508)
- [Bitget News: ERC20-Solana wallet mapping for stakers](https://www.bitget.com/news/detail/12560603884450)
- [MEXC News: 33% treasury buyback details](https://www.mexc.co/news/264935)
- [Phemex Academy: May 2026 unlock context](https://phemex.com/academy/what-is-pyth-network-token-unlock)
- [Superteam: Pyth Network Grants](https://in.superteam.fun/instagrants/pyth-network-grants)
- [Etherscan: PYTH ERC-20 contract on Ethereum](https://etherscan.io/token/0xefc0ced4b3d536103e76a1c4c74f0385c8f4bdd3)

---

*BANKON Research, May 2026. Published at [rage.pythai.net](https://rage.pythai.net) under Apache 2.0. (c) 2026 BANKON — all rights reserved. No financial advice; all figures verified against primary sources at time of publication. Corrections welcome to research@pythai.net.*
