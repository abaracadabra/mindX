# x402evm — EVM-side x402 settlement + CoinMarketCap x402 ingestion

A self-contained, modular expansion of bankoneth (sibling of `pay2play/`) that brings **HTTP-402
(x402) payments to the EVM rails** — Base, Arc (Circle), Optimism, Polygon, Arbitrum, … — for two
directions:

1. **Receive** x402 payments for BANKON / mindX / AgenticPlace services (the on-chain settlement
   attestor `X402EVMFacilitator`).
2. **Pay** x402 to ingest **CoinMarketCap** data on the EVM/Arc/Base side (the `clients/` ingestion
   tools — the x402 *payer*), plus the keyed `cmc` CLI path for non-x402 ingestion.

It generalizes the existing rails — `BankonX402Attestor` (Algorand → EVM) and
`pay2play/Pay2PlayArcSettlement` (Arc) — to **every EVM chain**, reusing the proven EIP-712 +
two-replay-guard design.

## Contracts (`src/`, 6/6 tests)
- **`X402ChainRegistry`** — which chains + assets are valid settlement rails (canonical USDC per
  chain + an extensible allow-map). Owner-managed.
- **`X402EVMFacilitator`** — records a facilitator-signed `X402EVMReceipt`. Checks: facilitator
  allowlisted, not expired, asset/chain registered, **monotonic per-facilitator nonce**, **spent-digest
  set**, EIP-712 + ERC-1271 signature. Permissionless to *submit*; the signature + guards are the trust.
  Downstream services gate on `isSettled(digest)` or the `X402EVMSettled` event.

```
X402EVMReceipt = { resourceHash, payer, asset, amount, srcChainId, nonce, expiresAt }
typehash:        X402EVMReceipt(bytes32 resourceHash,address payer,address asset,uint256 amount,uint64 srcChainId,uint64 nonce,uint64 expiresAt)
domain:          X402EVMFacilitator / v1 / chainId / contract
```

EVM ∥ Arc ∥ Base handling: the **same** facilitator + registry cover all of them — `srcChainId` +
`asset` (the chain's USDC) say where a payment settled. Arc is chain `5042002` with USDC-as-gas;
Base is `8453`; add any EVM chain via `registry.setChain(chainId, usdc)`.

## CoinMarketCap x402 ingestion (`clients/`)
CMC's AI-Agent-Hub exposes **x402-gated** market-data endpoints (pay-per-call in USDC, no API key
needed for the x402 path). Two ingestion paths ship here:
- **`cmc_x402_ingest.mjs`** — the **x402 payer**: GET a CMC x402 resource → parse the `402` challenge
  → sign an **EIP-3009 USDC `transferWithAuthorization`** → resend with the `X-PAYMENT` header →
  ingest the JSON. Works on Base/Arc (USDC). Per the open x402 standard (Coinbase). *Confirm the exact
  CMC endpoint + network against https://pro.coinmarketcap.com/api/documentation/ai-agent-hub/x402.*
- **`cmc_cli.mjs`** — a thin wrapper over the **`cmc` Go CLI** (github.com/openCMC/CoinMarketCap-CLI)
  for the **keyed** ingestion path (`cmc price/resolve/markets …`), reusing the server-side key from
  `bankonchains` (`.bankonchains.env`). Use this for bulk/keyed pulls; use x402 for keyless pay-per-call.

The two ingestion paths feed the same place: `bankonchains/price.js` (holder-gated CMC prices) and any
mindX/AgenticPlace data needs. See `bankonMCP/` for the MCP-server adaptation that pays x402 on behalf
of agents.

## Deploy
```bash
cd x402evm && forge test                 # 6/6
forge script script/DeployX402EVM.s.sol --rpc-url <base|arc|…> --broadcast
# registers Base + Arc USDC and grants the bankon facilitator
```

## Where it plugs in
- `packages/web/payments.js` — a new `x402-evm` rail can target `X402EVMFacilitator` on the connected
  chain (vs the existing Algorand-attestor `x402` rail).
- `bankonMCP/` — the MCP × x402 proxy that auto-pays for agent tool calls (AgenticPlace processor).
- `bankonchains/price.js` — CMC ingestion (x402 or cmc-cli) behind the holder gate.

Docs: `docs/blockchain/X402_EVM.md`, `docs/operations/COINMARKETCAP_X402.md`.
