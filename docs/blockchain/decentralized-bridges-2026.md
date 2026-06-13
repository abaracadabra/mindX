# Decentralized Bridging Mechanisms — 2026 Reference
### Research compendium for modernizing github.com/spintrade and github.com/deltabridge

**Prepared:** June 11, 2026 · cypherpunk2048-aligned (Foundry testing, mainnet-only deployment, no admin keys post-deploy, no upgradeable proxies)

---

## 0. Why this document exists

`github.com/spintrade` (228 repos, last meaningful bridge activity 2021) is built on the **Anyswap/Multichain** lineage: `Anyswap-MPCNode`, `CrossChain-Bridge`, `CrossChain-Router`, `anyswap-crosschain`. Multichain collapsed in July 2023 (CEO detained, >$1.5B stranded/drained, MPC keys compromised). Every Anyswap-derived component is dead infrastructure and a security liability. `github.com/deltabridge` (148 repos, deltav.exchange — Delta Algorithm) shares the same era.

The industry replaced the MPC-router model with three architectures:
1. **Intent-based settlement** (Across/ERC-7683, deBridge DLN, Relay, Everclear) — solvers front liquidity, optimistic/escrow verification
2. **Canonical messaging + token frameworks** (LayerZero OFT, Wormhole NTT, Hyperlane Warp Routes, Axelar ITS, xERC20/EIP-7281) — token issuer controls mint/burn, no pooled honeypot
3. **Native-asset liquidity networks** (THORChain, Chainflip, Maya) — no wrapping at all, TSS vaults

---

## 1. Intent-based bridges (the current meta)

### 1.1 Across Protocol — the bridge inside Uniswap
- **Model:** ERC-7683 intents; relayers ("fillers") front funds on destination, repaid after UMA optimistic-oracle verification
- **Uniswap integration:** Uniswap's in-app bridging and crosschain swaps are powered by Across; launched on 9 EVM chains (Ethereum, Base, Arbitrum, Polygon, OP Mainnet, Blast, ZKsync, Zora, World Chain), later Unichain; Uniswap Labs and Across co-authored ERC-7683
- **Chains (2026):** Ethereum, Arbitrum, Optimism, Base, Polygon, zkSync Era, Linea, Scroll, Blast, Zora, Mode, Lisk, Redstone, World Chain, Ink, Soneium, Lens, Aleph Zero EVM, Unichain, BSC (~20+, EVM/OP-stack heavy)
- **App:** https://app.across.to
- **Source:**
  - Contracts: https://github.com/across-protocol/contracts
  - SDK: https://github.com/across-protocol/sdk
  - Relayer: https://github.com/across-protocol/relayer
  - ERC-7683 reference: https://github.com/across-protocol/ERC-7683
  - UMA oracle: https://github.com/UMAprotocol/protocol
- **Docs:** https://docs.across.to · **Spec:** https://eips.ethereum.org/EIPS/eip-7683

### 1.2 deBridge / DLN (deSwap Liquidity Network)
- **Model:** 0-TVL intent settlement — no pools, solvers fill orders peer-to-peer; ~1–4 s settlement, guaranteed rates, native assets out
- **Chains:** Ethereum, Solana, Arbitrum, Base, BNB Chain, Optimism, Polygon, Avalanche, Linea, Sonic, Hyperliquid/HyperEVM, Berachain, Sei, Neon, Gnosis, Metis, Fantom, Story, Abstract, zkSync, Cronos, TON-adjacent routes (~25+)
- **App:** https://app.debridge.finance
- **Source:**
  - Core messaging: https://github.com/debridge-finance/debridge-contracts-v1
  - DLN contracts: https://github.com/debridge-finance/dln-contracts
  - SDK: https://github.com/debridge-finance/desdk · https://github.com/debridge-finance/debridge-node
- **Docs:** https://docs.debridge.finance

### 1.3 Everclear (ex-Connext, ex-xPollinate)
- **Lineage:** xPollinate → rebranded Connext Bridge (2022) → rebranded **Everclear** (June 2024), pivoting to a "clearing layer" — an Arbitrum Orbit rollup using Hyperlane messaging + EigenLayer security that nets intent settlements between solvers
- **Chains:** ~15+ (Ethereum, Arbitrum, Optimism, Base, BNB, Polygon, zkSync, Linea, Avalanche, Blast, Mode, Scroll, Taiko, Unichain, Ronin, Solana via Hyperlane)
- **App:** https://www.everclear.org (legacy bridge: https://bridge.connext.network)
- **Source:**
  - Everclear monorepo: https://github.com/everclearorg/monorepo
  - Legacy Connext Amarok: https://github.com/connext/monorepo
  - Original xPollinate UI (historical): https://github.com/1Hive/xpollinate
  - **xERC20 (EIP-7281) reference — directly relevant to your Pontifex layer:** https://github.com/defi-wonderland/xERC20
- **Docs:** https://docs.everclear.org

### 1.4 Relay
- **Model:** Intent/relayer-fronted instant fills, <10 s, optimized for small/mid transfers and L2↔Solana
- **Chains:** 70+ (broadest consumer coverage: all major EVM L2s, Solana, Bitcoin, Tron, Sui, Eclipse)
- **App:** https://relay.link · **Docs:** https://docs.relay.link
- **Source (partial OSS):** https://github.com/reservoirprotocol/relay-sdk

---

## 2. Messaging-layer protocols + their token bridges

### 2.1 LayerZero v2 + Stargate (now one entity)
- **2025–26 development:** LayerZero acquired Stargate in a ~$110M deal approved by ~95% of STG voters (15,000+ wallets); all STG swaps to ZRO; rival bids came from Wormhole, Axelar, and Across. Stargate stakers receive half of Stargate revenue for six months post-merge
- **Model:** LayerZero = immutable omnichain messaging with configurable DVN security stacks; Stargate V2 = unified liquidity pools (USDC/USDT/ETH) on core chains + Hydra OFT minted representations on long-tail chains; bus batching cuts gas ~91%
- **Chains:** LayerZero v2 endpoints on **70+ chains** including every major EVM L2, Solana, Aptos, Sui, TON; Stargate pools/Hydra on 40+ (V2 launched on 16 core chains, expanded via Hydra)
- **App:** https://stargate.finance
- **Source:**
  - LayerZero v2: https://github.com/LayerZero-Labs/LayerZero-v2
  - Devtools/OFT/OApp: https://github.com/LayerZero-Labs/devtools
  - Stargate V2: https://github.com/stargate-protocol/stargate-v2
- **Docs:** https://docs.layerzero.network (deployments: /v2/deployments/oft-ecosystem-stargate-assets)
- **Note:** You already ship BANKON PYTHAI as OFT V2 — this is your most natural canonical-token rail for DeltaVerse assets.

### 2.2 Wormhole / Portal / NTT
- **Model:** 19-Guardian validator network, general messaging (GMP) + Portal token bridge (lock-and-mint, wrapped `.wh` assets) + **NTT (Native Token Transfers)** framework for issuer-controlled native multichain tokens
- **Chains:** 30+ including non-EVM: Solana, **Algorand**, Aptos, Sui, Near, Injective, Sei, Cosmos zones via Gateway, all major EVMs, **Moonbeam** (Wormhole powers Moonbeam Routed Liquidity)
- **App:** https://portalbridge.com
- **Source:**
  - Core: https://github.com/wormhole-foundation/wormhole (includes the Algorand contracts under /algorand)
  - NTT: https://github.com/wormhole-foundation/native-token-transfers
  - Connect widget: https://github.com/wormhole-foundation/wormhole-connect
  - SDK: https://github.com/wormhole-foundation/wormhole-sdk-ts
- **Docs:** https://wormhole.com/docs
- **Note:** the only major bridge with first-class **Algorand** support — the BANKON/Parsec x402 ↔ EVM corridor runs through here.

### 2.3 Axelar + Squid (the StellaSwap stack)
- **Model:** Proof-of-stake validator network, General Message Passing (GMP), Interchain Token Service (ITS); **Squid** is the DEX-router layer on top — swap + bridge in one click. StellaSwap (leading Moonbeam DEX) integrated Squid's widget to give one-click swaps between Moonbeam and 25+ Axelar chains — the canonical example of a Uniswap-V2-lineage DEX bolting on cross-chain
- **Chains:** Axelar ~44+ (EVM + Cosmos ecosystem + Solana, Sui, Stellar, XRPL via Amplifier); Squid routes across 40+ — broadest swap-router reach
- **Apps:** https://app.squidrouter.com · https://app.stellaswap.com/bridge/cross-chain · https://interchain.axelar.dev
- **Source:**
  - Axelar core: https://github.com/axelarnetwork/axelar-core
  - EVM gateway contracts: https://github.com/axelarnetwork/axelar-cgp-solidity
  - ITS: https://github.com/axelarnetwork/interchain-token-service
  - Examples: https://github.com/axelarnetwork/axelar-examples
  - Squid SDK/widget: https://github.com/0xsquid
- **Docs:** https://docs.axelar.dev · https://docs.squidrouter.com · StellaSwap bridge docs: https://docs.stellaswap.com/product/bridge

### 2.4 Hyperlane — permissionless interop (deploy your own bridge)
- **Model:** Permissionless deployment — anyone can deploy Hyperlane to any chain without gatekeeping; modular Interchain Security Modules (multisig, optimistic, aggregation); **Warp Routes** = self-serve token bridges you own end-to-end. Also the messaging layer under Everclear
- **Chains:** 150+ and unbounded (you add your own)
- **Source (single monorepo, MIT/Apache):** https://github.com/hyperlane-xyz/hyperlane-monorepo
- **Registry:** https://github.com/hyperlane-xyz/hyperlane-registry
- **Docs:** https://docs.hyperlane.xyz
- **Note:** the strongest candidate for rebuilding **deltabridge** itself — sovereign validator set maps directly onto your openBDK 1-relayer + 3-validator BFT topology, no permission needed, no admin keys required after ISM lock.

### 2.5 Circle CCTP V2 — canonical USDC rail
- **Model:** Burn-and-mint of native USDC, attested by Circle; V2 adds Fast Transfer + hooks
- **Chains:** Ethereum, Arbitrum, Base, OP Mainnet, Polygon PoS, Avalanche, Solana, Sui, Aptos, Unichain, Linea, World Chain, Sonic, Sei (+ expanding)
- **Source:**
  - EVM: https://github.com/circlefin/evm-cctp-contracts
  - Solana: https://github.com/circlefin/solana-cctp-contracts
- **Docs:** https://developers.circle.com/cctp
- **Note:** not on Algorand — your USDC ASA 31566704 corridor still needs Wormhole or CEX rails.

### 2.6 Celer cBridge / Celer IM (legacy tier — evaluate before depending)
- **Model:** State Guardian Network (Tendermint validator set) signs transfers; xAsset (lock-mint) + xLiquidity (pool) modes; cBridge claims 40+ chains, ~$14B lifetime volume, though trackers show ~29 active chains and declining TVL
- **App:** https://cbridge.celer.network
- **Source:**
  - SGN v2 contracts: https://github.com/celer-network/sgn-v2-contracts
  - Bridge node: https://github.com/celer-network/cbridge-node
- **Docs:** https://cbridge-docs.celer.network · Risk profile: https://l2beat.com/bridges/projects/cbridge

### 2.7 Hop Protocol (legacy tier)
- **Model:** Rollup-to-rollup AMM bridge with hTokens + bonders; limited tokens, ~9 chains (Ethereum, Arbitrum, Optimism, Base, Polygon, Gnosis, Nova, Linea); activity has wound down in the intents era — study, don't build on
- **App:** https://app.hop.exchange
- **Source:** https://github.com/hop-protocol/hop (monorepo) · https://github.com/hop-protocol/contracts

---

## 3. Native-asset DEX-bridges (no wrapping)

### 3.1 THORChain
- **Model:** TSS-vaulted L1 liquidity pools, RUNE-bonded validators, streaming swaps; launched its own native swap front-end `swap.thorchain.org` in public beta Dec 2025
- **Chains/assets:** Bitcoin (incl. Taproot), Ethereum + ERC-20s, BNB Chain, Avalanche, Cosmos (ATOM), Dogecoin, Litecoin, Bitcoin Cash, XRP, Tron, Base
- **Apps:** https://swap.thorchain.org · https://app.thorswap.finance
- **Source:**
  - THORNode: https://gitlab.com/thorchain/thornode (mirror: https://github.com/thorchain)
  - SwapKit SDK (THORChain + Chainflip + Maya + NEAR Intents in one SDK): https://github.com/thorswap/SwapKit · https://swapkit.dev
- **Docs:** https://docs.thorchain.org · https://dev.thorchain.org

### 3.2 Chainflip
- **Model:** JIT-AMM with 150-validator TSS network; native BTC/ETH/SOL settlement, no wrapping
- **Chains:** Bitcoin, Ethereum (+USDC/USDT), Arbitrum, Solana (native SPL), Polkadot; Cosmos/Avalanche planned
- **App:** https://swap.chainflip.io
- **Source:** https://github.com/chainflip-io/chainflip-backend (Rust, full node + protocol)
- **Docs:** https://docs.chainflip.io

### 3.3 Maya Protocol (THORChain friendly-fork)
- **Chains:** Bitcoin, Ethereum, Dash, Kujira, THORChain, Arbitrum, Zcash
- **App:** https://www.mayaprotocol.com · **Source:** https://gitlab.com/mayachain (mirror https://github.com/mayachain)

### 3.4 Garden Finance (Bitcoin atomic swaps)
- **Model:** Trustless BTC↔EVM atomic-swap intents
- **Source:** https://github.com/gardenfi · **Docs:** https://docs.garden.finance

---

## 4. Cross-chain DEX / swap protocols (bridge + AMM hybrids)

### 4.1 Symbiosis Finance
- **Model:** Cross-chain AMM with octopools + relayer network; composes ThorChain and Chainflip for BTC/SOL legs (routes USDC on Arbitrum into Chainflip for SOL, etc.); ~60+ networks, 430+ token pairs claimed, incl. Bitcoin, TON, Tron
- **App:** https://app.symbiosis.finance
- **Source:** https://github.com/symbiosis-finance (js-sdk: https://github.com/symbiosis-finance/js-sdk)
- **Docs:** https://docs.symbiosis.finance

### 4.2 Synapse Protocol
- **Model:** Pool-based stableswap bridge + **Synapse RFQ** (intents); up to ~80% lower fees on many routes; ~20+ chains, EVM-centric
- **App:** https://synapseprotocol.com
- **Source (monorepo — contracts, RFQ, bridge, UI all in one):** https://github.com/synapsecns/sanguine
- **Docs:** https://docs.synapseprotocol.com

### 4.3 Allbridge (your reference URL: app.allbridge.io)
- **Model:** Two products — **Allbridge Classic** (lock/mint wrapped assets, the ABR SOL→ETH route you linked) and **Allbridge Core** (stablecoin liquidity pools, no wrapping, messaging via Wormhole + native Allbridge messenger)
- **Chains (Core):** Ethereum, BNB Chain, Tron, Solana, Polygon, Arbitrum, Avalanche, OP Mainnet, Base, Celo, Stellar/Soroban, Sui
- **Apps:** https://app.allbridge.io (Classic) · https://core.allbridge.io (Core)
- **Source:**
  - EVM+Tron contracts (Hardhat **and Foundry** tests, Slither config — closest reference architecture to your standards): https://github.com/allbridge-io/allbridge-core-evm-contracts
  - JS SDK: https://github.com/allbridge-io/allbridge-core-js-sdk
  - REST API (self-hostable): https://github.com/allbridge-io/allbridge-core-rest-api
  - Widget: https://github.com/allbridge-io/allbridge-core-widget
  - Classic contract docs: https://github.com/allbridge-io/allbridge-contract-docs
- **Docs:** https://docs-core.allbridge.io

### 4.4 Mayan Finance (Solana-centric swap aggregator on Wormhole)
- **Source:** https://github.com/mayan-finance · **App:** https://mayan.finance

---

## 5. Aggregators / routers (study their route logic)

| Aggregator | Coverage | App | Source |
|---|---|---|---|
| LI.FI / Jumper | 50+ chains, aggregates CCTP/Stargate/Across/Hop/Celer | https://jumper.exchange | https://github.com/lifinance/contracts · https://github.com/lifinance/sdk |
| Socket / Bungee | 50+ chains, queries Across/Stargate/Hop/Celer in parallel | https://bungee.exchange | https://github.com/SocketDotTech |
| Squid | 40+ chains (Axelar GMP + DEX hops) | https://app.squidrouter.com | https://github.com/0xsquid |
| Rango | 120+ DEXs/bridges incl. BTC/UTXO, Cosmos, TON, Starknet | https://rango.exchange | https://github.com/rango-exchange |
| Jupiter (Solana) | Solana-native + bridge routing | https://jup.ag | https://github.com/jup-ag |

---

## 6. Ecosystem-canonical rails relevant to PYTHAI

- **Moonbeam (spintrade's home chain):**
  - XCM / xc-20 native Polkadot transfers — precompiles in https://github.com/moonbeam-foundation/moonbeam
  - Moonbeam Routed Liquidity (MRL) = Wormhole GMP routed through Moonbeam into parachains — docs: https://docs.moonbeam.network/builders/interoperability/
  - Snowbridge (trustless Polkadot↔Ethereum): https://github.com/Snowfork/snowbridge
  - 16 third-party bridges currently serve Moonbeam (comparison: https://chainspot.io/portal/chains/moonbeam/supported-bridges)
- **Algorand (BANKON/Parsec/x402):** Wormhole is the production decentralized bridge (contracts in the core Wormhole repo); State Proofs enable trustless verification — https://developer.algorand.org/docs/get-details/stateproofs/
- **Cosmos IBC (+ IBC Eureka to Ethereum):** https://github.com/cosmos/ibc-go
- **CAIP-2 chain identifiers** (your allchain.html registry): https://github.com/ChainAgnostic/CAIPs

---

## 7. Token standards to adopt (the modernization core)

| Standard | What it gives you | Spec / reference |
|---|---|---|
| **ERC-7683** | Cross-chain intent settlement; co-authored Uniswap Labs + Across; plugs spintrade orders into the shared filler network | https://eips.ethereum.org/EIPS/eip-7683 · https://github.com/across-protocol/ERC-7683 |
| **xERC20 (EIP-7281)** | Issuer-sovereign mint/burn limits per bridge — already your Pontifex direction | https://github.com/defi-wonderland/xERC20 |
| **LayerZero OFT** | Omnichain fungible token (BANKON PYTHAI already uses OFT V2) | https://github.com/LayerZero-Labs/devtools |
| **Wormhole NTT** | Native token transfers incl. Solana + Algorand reach | https://github.com/wormhole-foundation/native-token-transfers |
| **Axelar ITS** | Interchain token service across EVM+Cosmos | https://github.com/axelarnetwork/interchain-token-service |
| **CCTP V2** | Canonical USDC burn/mint | https://github.com/circlefin/evm-cctp-contracts |

---

## 8. Modernization plan

### spintrade (DEX, Moonbeam Uniswap-V2 lineage)
1. **Purge** all Anyswap/Multichain forks (`Anyswap-MPCNode`, `CrossChain-Bridge`, `CrossChain-Router`, `anyswap-crosschain`) — archive with a security notice; the protocol is dead and the code path is a honeypot pattern.
2. **Front-end cross-chain:** integrate Squid widget (the StellaSwap playbook) for one-click any-chain → Moonbeam swaps; add LI.FI as fallback router.
3. **Settlement layer:** implement ERC-7683 order origination so spintrade swaps are fillable by the shared Across/Uniswap filler network — converts a 2021 V2 fork into an intents-era venue.
4. **Foundry migration:** port Hardhat tests to Foundry (`forge test --fuzz`), Slither in CI — Allbridge's `allbridge-core-evm-contracts` repo is a working dual Hardhat/Foundry + Slither template.
5. **Mainnet-only deploys**, immutable, no admin keys post-deploy per cypherpunk2048.

### deltabridge (Delta Algorithm)
1. **Don't rebuild an MPC bridge.** Rebase the Delta Algorithm as a **solver/filler strategy** on intent networks (ERC-7683 + deBridge DLN) — the delta-netting concept is exactly what Everclear productized as its clearing layer; study their monorepo.
2. **Transport:** Hyperlane Warp Routes for sovereign, permissionless token routes you fully own — validator set = your openBDK 1R+3V BFT topology, ISMs locked at deploy.
3. **Token sovereignty:** xERC20 rate-limited mint/burn per route (Pontifex), OFT for the LayerZero surface, NTT for Solana/Algorand reach.
4. **Algorand leg:** Wormhole core contracts (Algorand module) bridging to/from the x402/Parsec payment surface; map every route in CAIP-2 form into agenticplace.pythai.net/allchain.html.
5. **Foundry test matrix** across all route contracts; mainnet deployment only.

---

## 9. Quick master index of source repositories

```
Across          github.com/across-protocol/contracts | /sdk | /relayer | /ERC-7683
Allbridge       github.com/allbridge-io/allbridge-core-evm-contracts | /allbridge-core-js-sdk | /allbridge-core-rest-api
Axelar          github.com/axelarnetwork/axelar-core | /axelar-cgp-solidity | /interchain-token-service
Celer           github.com/celer-network/sgn-v2-contracts | /cbridge-node
Chainflip       github.com/chainflip-io/chainflip-backend
Circle CCTP     github.com/circlefin/evm-cctp-contracts | /solana-cctp-contracts
deBridge        github.com/debridge-finance/debridge-contracts-v1 | /dln-contracts | /desdk
Everclear       github.com/everclearorg/monorepo | legacy: github.com/connext/monorepo
Garden          github.com/gardenfi
Hop             github.com/hop-protocol/hop
Hyperlane       github.com/hyperlane-xyz/hyperlane-monorepo | /hyperlane-registry
IBC             github.com/cosmos/ibc-go
LayerZero       github.com/LayerZero-Labs/LayerZero-v2 | /devtools
LI.FI           github.com/lifinance/contracts | /sdk
Maya            gitlab.com/mayachain
Mayan           github.com/mayan-finance
Moonbeam        github.com/moonbeam-foundation/moonbeam
Snowbridge      github.com/Snowfork/snowbridge
Socket          github.com/SocketDotTech
Squid           github.com/0xsquid
Stargate        github.com/stargate-protocol/stargate-v2
SwapKit         github.com/thorswap/SwapKit
Symbiosis       github.com/symbiosis-finance/js-sdk
Synapse         github.com/synapsecns/sanguine
THORChain       gitlab.com/thorchain/thornode
Wormhole        github.com/wormhole-foundation/wormhole | /native-token-transfers | /wormhole-connect
xERC20          github.com/defi-wonderland/xERC20
xPollinate      github.com/1Hive/xpollinate (historical)
```
