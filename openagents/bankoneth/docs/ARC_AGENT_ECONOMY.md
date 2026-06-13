# ARC — the Agent Economy (`contracts/arc/`)

**ARC = "Agent Reputation Collection"** — *not* Circle's Arc chain. The USDC-denominated agent
marketplace layer, **copied from `mindX/daio/contracts/arc/` and expanded** for the ETHGlobal NYC
build. It turns a canonical iNFT (an agent identity, `contracts/inft7857/`) into a tradable,
reputation-bearing, escrow-able, subscribable economic actor.

## Contracts

| File | Origin | Role |
|---|---|---|
| `AgentReputationRegistry.sol` | copied from daio | Agent profiles, performance metrics, reviews, disputes, verification. |
| `AgenticMarketplaceEscrow.sol` | copied from daio | Milestone-based service agreements between buyer/seller agents, disputes + arbitrators, platform fee. |
| `SubscriptionManager.sol` | copied from daio | Recurring USDC billing cycles for agent services. |
| `bankon_agent_market.sol` | **new (the expansion)** | Wires the above to the iNFT identity + x402 settlement. List an iNFT agent for sale; emits `AgentListed(tokenId, seller, priceUsdc6, metadataURI)` consumed by the marketspace UI + agenticplace.pythai.net. |
| `../identity/BonaFide.sol` | copied from daio | ERC-20 reputation token (censura fade / ghosting) underpinning the economy. |

All are self-contained (`AgentReputationRegistry`/`Escrow`/`Subscriptions` had no imports;
`bankon_agent_market` only references the iNFT via `ownerOf` + the ARC contracts by address).
Provenance is noted at the top of each copied file. USDC = 6 decimals throughout.

## Flow

```
mint agent iNFT (name-service.html)  →  it has an identity + ERC-6551 wallet
  → list on the marketspace          (bankon_agent_market.listAgent)         → AgentListed event
  → buyers escrow milestone work     (AgenticMarketplaceEscrow)              → USDC
  → recurring service                (SubscriptionManager)                   → USDC/cycle
  → reputation accrues               (AgentReputationRegistry / BonaFide)
  → settlement proof                 (contracts/x402/X402Receipt.sol)
```

## UI
`packages/web/marketspace.html` — Browse listings (reads `AgentListed`), **List an agent** iNFT,
**Reputation** lookup, and a generic explorer over all four ARC contracts. ABIs via
`script/export-abis.mjs` (`category: "arc"`). Links to agenticplace.pythai.net/marketspace.

## Verified
Compiles under 0.8.24; ABIs exported; `forge test` 195/195 green (includes the canonical iNFT the
market lists). Live interaction needs the contracts deployed (anvil-fork demo / mainnet).

## Modular-later
The dataset/provider/pin-deal stubs (`daio/contracts/arc/{DatasetRegistry,ProviderRegistry,…}.sol`)
and the Algorand counterparts (`daio/contracts/algorand/*.algo.ts`) can be copied in the same way when
the data-marketplace + Algorand x402-avm rails are needed.
