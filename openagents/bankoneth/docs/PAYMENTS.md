# Payments — accept any denomination, convert it (incl. ARC)

Buying a `*.bankon.eth` accepts **any denomination** and converts it to what the
contracts settle in. The on-chain price/fee is **admin-set** (the bankon.eth owner,
via the admin console → `BankonPriceOracle` / `BankonDomainHosting`); this layer only
routes funds into the `payment` bytes `BankonDomainHosting.issue(parentNode,label,owner,payment)`
expects:

- **rail `0x00`** — ETH via `msg.value` (direct).
- **rail `0x02`** — an EIP-712 **X402Receipt** signed by a registered facilitator
  (`BankonX402Attestor.verify`), so USDC/any-token/cross-chain settlements mint without
  an inline ERC-20 transfer. *(This is the Algorand-origin attestor; for native EVM
  settlement on Base / Arc / Optimism / … see [**x402evm**](#x402-on-every-evm-rail--x402evm) below.)*

## Layer (packages/web/)

- `chains.js` — chain + USDC + CCTP config. Includes **Arc testnet** (chain `5042002`,
  RPC `rpc.testnet.arc.network`, USDC `0x3600…0000` / native-gas, CCTP domain `26`).
- `payments.js` — `quoteFor()` (reads admin price), `RAILS`, `preparePayment({rail,…})`.
  - `eth` — direct `msg.value` (functional).
  - `x402` — calls the facilitator (`POST /x402/settle`), encodes `0x02 || abi.encode(X402Receipt)` (functional).
  - `swap` — swap any ERC-20 → USDC via Circle **App/Swap Kit** (`swap-tokens` skill), then x402. *(adapter)*
  - `arc` — bridge USDC from **Arc**/L2 → settlement chain via **CCTP** (`bridge-stablecoin`) /
    **Gateway** (`use-gateway`), then x402. *(adapter)*
- core: `packages/core/src/addresses.ts` `USDC_BY_CHAIN` (USDC + CCTP domains incl. Arc).

## Facilitator (`backend/x402.py`, `POST /x402/settle`)

Signs an EIP-712 `X402Receipt` (`BankonX402Attestor`/v1) that recovers to the facilitator
EOA — verified to match the on-chain attestor's domain+typehash, so a registered
facilitator's receipt is accepted on-chain.

```
env: BANKON_X402_FACILITATOR_PK   facilitator EOA (vault/env); register via
                                  BankonX402Attestor.setFacilitator(addr, true)
     BANKON_X402_ATTESTOR         attestor addr (else from deployments/<chain>.json)
     BANKON_X402_TRUST_REQUEST=1  DEV ONLY — sign without a settlement verifier
```

> **Production**: the facilitator MUST verify the USDC actually settled (an on-chain
> transfer to treasury, a Circle CCTP/Gateway mint receipt, or an Algorand x402 proof)
> BEFORE signing. Without `BANKON_X402_TRUST_REQUEST=1` the endpoint 501s until a verifier
> is wired. GoPlausible or a self-hosted facilitator both fit.

## x402 on every EVM rail — `x402evm/`

The `0x02` rail above is the **Algorand-origin** attestor. The [`x402evm/`](../x402evm/) module
generalizes x402 settlement to **every EVM chain** (Base, Arc, Optimism, Polygon, Arbitrum, …) with one
`X402EVMFacilitator` + an `X402ChainRegistry` (canonical USDC per chain). A facilitator signs an EIP-712
`X402EVMReceipt(resourceHash,payer,asset,amount,srcChainId,nonce,expiresAt)`; `srcChainId` + `asset` say
where a payment settled, so **Arc (5042002, USDC-as-gas)** and **Base (8453)** are the same code path. Two
replay guards (monotonic per-facilitator nonce + spent-digest) + ERC-1271. **6/6 tests.**

This is the receive side for **BANKON / mindX / AgenticPlace** service delivery; the [`bankonMCP/`](../bankonMCP/)
proxy auto-pays it for agent tool calls (φ/10 fee → RAKE home to `bankon.eth`), and
[`x402evm/clients/cmc_x402_ingest.mjs`](../x402evm/clients/cmc_x402_ingest.mjs) is the EIP-3009 USDC payer
for CoinMarketCap ingestion.

See **[`docs/blockchain/X402_EVM.md`](blockchain/X402_EVM.md)** (the full x402 rail family + receipt shapes)
and **[`docs/operations/COINMARKETCAP_X402.md`](operations/COINMARKETCAP_X402.md)** (CMC ingestion + key
handling + MCP delivery).

## Conversion flow (any token, any chain → mint)

```
user pays ANY token on ANY chain
  → swap → USDC            (Circle App/Swap Kit; same-chain)
  → bridge → settlement USDC (CCTP/Gateway; Arc↔Base↔Ethereum…)
  → facilitator verifies settlement, signs X402Receipt
  → DomainHosting.issue(..., 0x02||receipt)  mints name.bankon.eth
fees route through BankonPaymentRouter (admin-set 5-bucket split).
```

Testnet-first: the `swap`/`arc` adapters are documented plug-points (need Circle keys +
SDKs); `eth` and `x402` are functional today. See the `use-arc`, `swap-tokens`,
`bridge-stablecoin`, `use-gateway`, `use-usdc` skills.
