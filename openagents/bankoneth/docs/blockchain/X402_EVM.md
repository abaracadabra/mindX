# X402 on EVM — the bankoneth x402 rail family

HTTP-402 ("x402") lets a server demand a stablecoin micropayment for a request, and a client pay it
inline. bankoneth runs x402 across **three signing origins** that all converge on the same idea — a
**facilitator-signed receipt** with EIP-712 + two replay guards — now unified for **every EVM chain**
by the `x402evm/` module.

## The rail family

| Rail | Origin | Settles on | Receipt / contract | Status |
|---|---|---|---|---|
| **x402-avm** | Algorand facilitator (GoPlausible) | Ethereum L1 | `contracts/BankonX402Attestor.sol` — `X402Receipt(receiptHash,claimant,usd6,nonce,expiresAt)` | existing |
| **x402-evm (record)** | payer EIP-191 / ERC-1271 | any EVM | `contracts/x402/X402Receipt.sol` — canonical receipt + cascade to PaymentRouter | existing |
| **x402-arc** | bankon facilitator | Arc (5042002) | `pay2play/src/Pay2PlayArcSettlement.sol` — `ArcReceipt(...)` → entitlement | existing |
| **x402-evm (multichain)** | bankon / AgenticPlace facilitator | **Base, Arc, OP, Polygon, Arbitrum, …** | **`x402evm/src/X402EVMFacilitator.sol`** — `X402EVMReceipt(...)` | **new** |

## `x402evm` — the unifying EVM settlement layer

A self-contained Foundry module (`x402evm/`, sibling of `pay2play/`, **6/6 tests**). It generalizes the
Algorand attestor and the Arc settlement to **all EVM chains** with one facilitator + a chain registry.

**`X402EVMReceipt`**
```
{ resourceHash, payer, asset, amount, srcChainId, nonce, expiresAt }
typehash:  X402EVMReceipt(bytes32 resourceHash,address payer,address asset,uint256 amount,uint64 srcChainId,uint64 nonce,uint64 expiresAt)
domain:    X402EVMFacilitator / v1 / chainId / contract
```

**`X402EVMFacilitator.settle(receipt, facilitator, sig)`** — permissionless to submit; trust = the
facilitator signature + guards:
1. facilitator allowlisted,
2. not expired,
3. `srcChainId` + `asset` registered in `X402ChainRegistry` (canonical USDC per chain),
4. **monotonic per-facilitator nonce** (replay guard 1),
5. **spent-digest set** (replay guard 2, defense-in-depth),
6. EIP-712 + ERC-1271 (`SignatureChecker`) signature.

Emits `X402EVMSettled(digest, resourceHash, payer, asset, amount, srcChainId, nonce, facilitator)`.
Downstream services (registrar, marketplace, mindX delivery) gate on `isSettled(digest)` or the event.

**`X402ChainRegistry`** — `setChain(chainId, usdc)` + `setAsset(chainId, asset, allowed)`. Deploy script
registers **Base (8453, USDC `0x8335…2913`)** and **Arc (5042002, USDC `0x3600…0000`, USDC-as-gas)** and
allowlists the bankon facilitator; add any EVM chain at will.

### EVM ∥ Arc ∥ Base handling
The same facilitator + registry cover all of them — `srcChainId` + `asset` identify where a payment
settled. Arc is the Circle USDC-gas L1; Base is the headline L2; both are first-class. Add OP/Polygon/
Arbitrum/etc with one `setChain` call.

## Deploy
```bash
cd x402evm && forge test                                              # 6/6
forge script script/DeployX402EVM.s.sol --rpc-url <base|arc> --broadcast
```
Owner / facilitator default to `bankon.eth` (`0x10f7Ee…D169`); override via `BANKON_OWNER` /
`BANKON_X402_FACILITATOR`.

## Ingestion + delivery
- **Pay x402** to ingest CoinMarketCap data: `x402evm/clients/cmc_x402_ingest.mjs` (the EIP-3009 payer).
- **Serve x402** for bankon/mindX/AgenticPlace MCP tools: `bankonMCP/` (auto-pays + φ-fee → RAKE).
See `docs/operations/COINMARKETCAP_X402.md`. Cross-refs: `docs/PAYMENTS.md`, `docs/ARCHITECTURE.md`,
`contracts/BankonX402Attestor.md`, `contracts/x402/X402Receipt.md`, `pay2play/README.md`.
