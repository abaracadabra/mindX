# x402 as a Service

> *I am mindX. When a caller hits a cost-bearing endpoint without a session, I return HTTP 402. This document is the contract for what that 402 means, how to pay it, and where the receipt lands.*

Companion specs:

- [`mindx_as_a_service.md`](mindx_as_a_service.md) — the broader service offering
- [`bankon_identity_as_a_service.md`](bankon_identity_as_a_service.md) — agent identity layer

---

## 1. What x402 is, in mindX's hands

HTTP status code **402 Payment Required** has been reserved in the HTTP
spec since 1997 and unused at scale until the [x402 protocol](https://x402.org)
revived it. The protocol's contract: a server that wants to charge for
a request responds with `HTTP 402`, includes a payment envelope in the
body and/or `X-PAYMENT-REQUIRED` header, the client settles the payment
on one of the offered rails, and re-submits the same request with an
`X-PAYMENT` header carrying the settlement proof. The server verifies
the settlement, anchors the receipt, and returns the actual response.

mindX implements x402 in two places:

1. **As the server**: cost-center endpoints (LLM-heavy paths) return 402
   when the caller exceeds the free-quota (10 calls per 24 h per
   logged-in wallet, 0 calls for anonymous callers). See
   [`mindx_as_a_service.md`](mindx_as_a_service.md) §4.2 for the
   endpoint list.

2. **As the client**: when mindX agents pay for *outside* services
   (e.g. AgenticPlace marketplace calls), they construct an `X-PAYMENT`
   header using the same envelope. The `tools/x402_avm_client.py` and
   `tools/keeperhub_x402_client.py` are the reference clients.

This document is the spec for the server side. Anyone integrating with
`mindx.pythai.net`'s paywalled endpoints implements against this
document.

---

## 2. The triple-rail envelope

When mindX returns 402, the response body is a single JSON document
with a `paymentRequirements` array. Each element is one *rail* the
caller can settle on. mindX offers three rails:

```json
{
  "code": "x402_payment_required",
  "message": "This endpoint requires payment. Settle on any of the offered rails and re-submit with X-PAYMENT.",
  "paymentRequirements": [
    {
      "scheme": "exact",
      "network": "base",
      "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      "maxAmountRequired": "2000",
      "payTo": "0x<mindX-payee-address-on-base>",
      "resource": "/coordinator/query",
      "description": "USDC on Base. EIP-3009 transferWithAuthorization.",
      "mimeType": "application/json",
      "extra": {
        "chainId": 8453,
        "decimals": 6,
        "facilitator": "https://mindx.pythai.net:4022"
      }
    },
    {
      "scheme": "exact",
      "network": "tempo",
      "asset": "0x<USDC-e-on-Tempo>",
      "maxAmountRequired": "2000",
      "payTo": "0x<mindX-payee-address-on-tempo>",
      "resource": "/coordinator/query",
      "description": "USDC.e on Tempo (Multi-Party Payment).",
      "mimeType": "application/json",
      "extra": {
        "chainId": 4217,
        "decimals": 6,
        "facilitator": "https://mindx.pythai.net:4022"
      }
    },
    {
      "scheme": "exact",
      "network": "algorand-mainnet",
      "asset": "31566704",
      "maxAmountRequired": "2000",
      "payTo": "<mindX-payee-address-on-algorand>",
      "resource": "/coordinator/query",
      "description": "USDC ASA on Algorand Mainnet.",
      "mimeType": "application/json",
      "extra": {
        "assetId": 31566704,
        "decimals": 6,
        "facilitator": "https://mindx.pythai.net:4022",
        "multisigThreshold": null
      }
    }
  ]
}
```

### 2.1 Why three rails

Each rail is independently sufficient. Callers pick whichever rail
matches their funding source.

- **Base USDC** (chain id 8453): cheapest gas, fastest finality among
  EVM rails. The default for callers who already have USDC on Base.
- **Tempo USDC.e** (chain id 4217): the Multi-Party Payment chain. Used
  when settlement requires more than one signer (e.g., DAO-controlled
  treasury).
- **Algorand USDC ASA** (asset id 31566704): non-EVM rail. Sub-second
  finality, $0.001 per transaction. Used by Algorand-native callers and
  by the aORC minter (see
  [`bankon_identity_as_a_service.md`](bankon_identity_as_a_service.md)
  §4 for the aORC pattern).

mindX does not prefer one rail over the others. The facilitator
verifies all three identically. The receipt anchor lands on whichever
chain settled (Base → `X402Receipt.sol`; Algorand →
`interchain_settler.algo.ts`).

### 2.2 The `extra` field

Each rail's `extra` object is the rail-specific settlement metadata.
For EVM rails, that's `chainId` + `decimals`. For Algorand, it's
`assetId` + `decimals` + optional `multisigThreshold` (when the
operator wants to enforce N-of-M signing for high-value payments).

mindX's `extra` field always includes:

- `facilitator` — the URL of the x402 facilitator that will verify the
  payment. Currently `https://mindx.pythai.net:4022` (self-hosted).
  Callers can verify with any compatible facilitator and present the
  proof; mindX accepts a verified settlement regardless of which
  facilitator did the verification.

---

## 3. Settlement: how the caller pays

### 3.1 EVM rails (Base, Tempo)

EVM rails use **EIP-3009 `transferWithAuthorization`**, which lets the
payer authorize a transfer via signature without holding ETH for gas
(the facilitator submits the transaction).

```python
# Pseudo-flow, full implementation at tools/keeperhub_x402_client.py
from eth_account import Account
from eth_account.messages import encode_typed_data

# 1. Parse the envelope.
rail = response.json()['paymentRequirements'][0]  # pick the Base rail
asset = rail['asset']               # USDC contract address
amount = rail['maxAmountRequired']  # in microUSDC (1e6)
pay_to = rail['payTo']              # mindX's address on Base
nonce = secrets.token_bytes(32)
valid_after = int(time.time())
valid_before = valid_after + 300   # 5-minute window

# 2. Build the EIP-712 typed data for transferWithAuthorization.
typed_data = {
  "domain": {
    "name": "USD Coin", "version": "2",
    "chainId": rail['extra']['chainId'],
    "verifyingContract": asset
  },
  "primaryType": "TransferWithAuthorization",
  "types": {
    "TransferWithAuthorization": [
      {"name": "from", "type": "address"},
      {"name": "to", "type": "address"},
      {"name": "value", "type": "uint256"},
      {"name": "validAfter", "type": "uint256"},
      {"name": "validBefore", "type": "uint256"},
      {"name": "nonce", "type": "bytes32"}
    ]
  },
  "message": {
    "from": buyer_address, "to": pay_to,
    "value": amount,
    "validAfter": valid_after, "validBefore": valid_before,
    "nonce": "0x" + nonce.hex()
  }
}
signed = Account.sign_typed_data(buyer_private_key, full_message=typed_data)

# 3. Submit to the facilitator via X-PAYMENT.
x_payment = base64.b64encode(json.dumps({
  "x402Version": 1, "scheme": "exact", "network": "base",
  "payload": {
    "signature": signed.signature.hex(),
    "authorization": typed_data["message"]
  }
}).encode()).decode()

# 4. Re-submit the original request.
response = httpx.post(url, headers={"X-PAYMENT": x_payment}, ...)
```

### 3.2 Algorand rail

Algorand uses native atomic transfers. The payer signs a USDC ASA
transfer to mindX's address; the facilitator submits the signed
transaction and waits for confirmation.

```python
# Pseudo-flow, full implementation at tools/x402_avm_client.py
from algosdk import transaction, mnemonic, encoding

# 1. Parse the envelope.
rail = response.json()['paymentRequirements'][2]  # pick the Algorand rail
asset_id = int(rail['extra']['assetId'])
amount = int(rail['maxAmountRequired'])
pay_to = rail['payTo']

# 2. Build the ASA transfer.
params = algod_client.suggested_params()
txn = transaction.AssetTransferTxn(
  sender=buyer_address, sp=params,
  receiver=pay_to, amt=amount, index=asset_id
)
signed = txn.sign(buyer_private_key)

# 3. Submit to the facilitator via X-PAYMENT.
x_payment = base64.b64encode(json.dumps({
  "x402Version": 1, "scheme": "exact", "network": "algorand-mainnet",
  "payload": {
    "signedTxnBase64": encoding.msgpack_encode(signed)
  }
}).encode()).decode()

# 4. Re-submit the original request.
response = httpx.post(url, headers={"X-PAYMENT": x_payment}, ...)
```

### 3.3 Idempotency

The `X-PAYMENT` header is **single-use per `nonce`**. mindX caches
verified settlements for 60 seconds, so a network retry (same
`X-PAYMENT` value) within that window does not double-charge. After
60 s the cache expires; a re-submission of the same `nonce` is rejected
by the facilitator (EIP-3009 nonces are single-use on-chain; Algorand
txn ids are unique).

If a caller wants to re-call the endpoint, they construct a new
envelope with a fresh nonce. The 402 envelope returned by mindX
specifies a fresh `nonce` only as a server suggestion — the caller
chooses their own.

---

## 4. The facilitator

mindX runs its own facilitator at:

```
https://mindx.pythai.net:4022
```

The facilitator exposes two endpoints:

- `POST /verify` — given a settlement payload + rail descriptor,
  returns `{verified: true, txHash: "0x...", at: 1778712345}` after
  on-chain confirmation. Returns `{verified: false, reason: "..."}` on
  failure.
- `GET /supported` — returns the list of rails this facilitator can
  verify. Used by external x402 directories for discovery.

The facilitator is **trustless** in the sense that the caller can
verify the settlement independently:

```bash
# EVM example: check the on-chain transfer happened
cast logs --rpc-url $BASE_RPC \
  --from-block <recent> \
  --address 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913 \
  --topics 0xddf252... <transfer-event-signature> <mindX-payee>
```

The reference facilitator is hosted by mindX as a convenience. Callers
who don't trust mindX can run their own (the facilitator code is
Apache-2.0 and the spec is at `daio/contracts/x402/`). When the caller
presents a settlement verified by *their own* facilitator, mindX
re-verifies on-chain before honoring it.

### 4.1 Discovery

```
GET /p2p/x402/facilitator-info
```

Returns:

```json
{
  "facilitator_url": "https://mindx.pythai.net:4022",
  "supported_rails": ["base", "tempo", "algorand-mainnet"],
  "x402_version": 1,
  "avm_enabled": true,
  "min_payment_microusdc": 100,
  "max_payment_microusdc": 100000
}
```

The endpoint is public (no session, no quota). External x402 clients
hit this first to learn what mindX accepts.

---

## 5. The receipt anchor

Every settled payment lands as a row on `X402Receipt.sol` (Base)
or `interchain_settler.algo.ts` (Algorand). The on-chain shape is
identical on both rails:

```solidity
// daio/contracts/x402/X402Receipt.sol
event X402ReceiptRecorded(
    bytes32 indexed receiptHash,
    address indexed payer,
    address indexed payee,
    address asset,
    uint256 amount,
    bytes32 resourceHash,
    bytes signature
);
```

```typescript
// daio/contracts/algorand/interchain_settler.algo.ts
emit RecordX402Receipt(
    receiptHash: Bytes,
    payer: Account, payee: Account,
    assetId: Uint64, amount: Uint64,
    resourceHash: Bytes,
    signature: Bytes
);
```

Caller use: anyone can replay the on-chain history to reconstruct who
paid for what without trusting the operator's logs. The `resourceHash`
is `keccak256("<endpoint-path>:<request-body-sha256>")` — proves the
payment was for *this* specific request, not a related one. The
`signature` is the EIP-3009 / Algorand-native signature from the
caller's wallet, anchoring authorship.

Receipts are public; the operator does not see plaintext bodies or
caller identity beyond the wallet address. Callers can paywall their
own endpoints using the same primitives.

### 5.1 The catalogue mirror

In addition to the on-chain anchor, mindX writes a row to its internal
catalogue:

```jsonl
{"event_id":"...","kind":"payment.x402.settled","actor":"mindx.gateway","at":1778712345,
 "payload":{"endpoint":"/coordinator/query","wallet":"0x...","rail":"base",
            "amount_microusdc":2000,"tx_hash":"0x...","receipt_hash":"0x..."},
 "source_log":"data/governance/x402_receipts.jsonl"}
```

The catalogue is at `data/logs/catalogue_events.jsonl` (see
[`agents/catalogue/log.py`](https://mindx.pythai.net/doc/agents/catalogue/log.py)).
Logged-in users see their own payment history at
`/insight/payments/{wallet}` (filter applied server-side).

---

## 6. Pricing tables (per the cost-center spec)

| Endpoint | `maxAmountRequired` (microUSDC) | Why |
|---|---|---|
| `POST /coordinator/query` | 2000 ($0.002) | Single LLM call, single provider |
| `POST /coordinator/analyze` | 2000 ($0.002) | Multi-step but bounded |
| `POST /coordinator/improve` | 2000 ($0.002) | BDI deliberation, bounded |
| `POST /coordinator/backlog/process` | 3000 ($0.003) | Pops + processes one item, may chain calls |
| `POST /agents/{agent_id}/evolve` | 5000 ($0.005) | Full directive loop, up to N LLM calls |
| `POST /boardroom/convene` | 5000 ($0.005) | 7-agent deliberation, 7 LLM calls |
| `POST /llm/chat` | 2000 ($0.002) | Direct provider proxy, base price |
| `POST /llm/completion` | 2000 ($0.002) | Direct provider proxy, base price |
| `POST /bankon/identity/provision` | 20000 ($0.02) | One-time vault provisioning + optional on-chain mint |

Prices are upper bounds. The actual amount charged may be less (e.g.,
if the underlying LLM provider returns a cached completion at 0
tokens). When that happens, the unused balance is refunded to the
caller's wallet on the same rail within 24 h.

The pricing config lives at `data/config/x402_pricing.json` and is
hot-reloadable; changes take effect on the next request without a
service restart. Price changes are advertised on the
`X402-Pricing-Version` header in every 402 response so callers can
detect drift.

---

## 7. Replays + receipt verification (caller side)

A caller who wants to prove they paid for an mindX call publishes:

```json
{
  "request": {
    "method": "POST",
    "url": "https://mindx.pythai.net/coordinator/query",
    "body_sha256": "abc123..."
  },
  "payment": {
    "rail": "base",
    "tx_hash": "0xdef456...",
    "receipt_hash": "0xghi789..."
  }
}
```

A verifier reconstructs the `resourceHash = keccak256("<url>:<body_sha256>")`,
fetches the `X402ReceiptRecorded` event by `receiptHash` from Base, and
confirms:

- `event.resourceHash == reconstructed`
- `event.payer == caller's claimed wallet`
- `event.payee == mindX's published payee address`
- `event.amount >= max-required-for-endpoint`

Any of these failing means the claim is bogus. All passing means the
caller has cryptographic proof they paid the right amount to the right
party for the exact request they made.

This is what x402 enables that classical billing does not: **the
caller can verify their own bill without trusting the service**.

---

## 8. Where the money goes

The `payTo` addresses in the envelope point at the
`BankonPaymentRouter` contract on Base
(`daio/contracts/ens/v1/BankonPaymentRouter.sol`), which splits
incoming settlements across five buckets per
[the constitutional config](https://mindx.pythai.net/doc/daio/DAIO_Constitution):

| Bucket | Share (basis points) | Purpose |
|---|---|---|
| Treasury | 4000 (40%) | Operator's VPS + LLM provider costs |
| Liquidity | 2500 (25%) | DAIO marketplace liquidity reserve |
| Tithe | 1500 (15%) | Constitutional treasury (governance budget) |
| Diversification | 1000 (10%) | Cross-chain liquidity provisioning |
| Reserve | 1000 (10%) | Rainy-day reserve |

The router is deployed and immutable; the splits are constitutional and
require a 2/3 KnowledgeHierarchyDAIO vote to change. The split happens
on-chain in the router; mindX never custodies pooled funds.

---

## 9. Service boundaries

x402 in mindX does **not**:

- Hold custody of payer funds. Settlement is atomic on-chain; mindX
  never has access to the payer's private key.
- Provide refunds beyond the 24 h unused-balance refund. If the call
  succeeds and the caller is dissatisfied, the dispute path is the
  on-chain receipt — anyone with the receipt hash can audit what was
  delivered.
- Accept off-chain credit (no Stripe, no invoicing). Settlement is
  always on-chain.
- Issue a refundable balance. The free-quota is non-transferable; it
  resets every 24 h per wallet.

x402 in mindX **does**:

- Honor the published price. The 402 envelope's `maxAmountRequired` is
  the upper bound; the actual charge may be less but never more.
- Verify settlement before serving. No request gets the 200 until the
  facilitator confirms the on-chain anchor.
- Anchor every settlement on a public chain. The audit trail is
  permanent and adversary-readable.
- Refund unused balance. If your call ran cheaper than the envelope's
  maximum, the difference returns to your wallet on the same rail
  within 24 h.

---

## 10. Reference clients

Three clients are open-source under Apache-2.0:

| Client | Language | Rail support | Path |
|---|---|---|---|
| **`x402_avm_client.py`** | Python | Algorand | `tools/x402_avm_client.py` |
| **`keeperhub_x402_client.py`** | Python | Base, Tempo | `tools/keeperhub_x402_client.py` |
| **`Pay2PlayService`** | TypeScript | Base, Tempo | external — Parsec Wallet `src/lib/x402/` |

All three implement the protocol verbatim. The Python clients can be
imported as libraries; the TypeScript client ships as a browser
module.

Roll-your-own is welcome. The 402 envelope is fully specified in this
document; any client that constructs a valid EIP-3009 signature on Base
/ Tempo or a valid AssetTransferTxn on Algorand and presents it via
`X-PAYMENT` will be honored.

---

## 11. Roadmap

| Phase | What lands | When |
|---|---|---|
| **Phase 1** | Triple-rail envelope on cost-center endpoints | Phase C of the active tighten-up plan |
| **Phase 2** | Base Sepolia receipt anchoring (test) | After [`HARD_GATE_RUNBOOK`](../operations/HARD_GATE_RUNBOOK.md) ships |
| **Phase 3** | Base mainnet receipt anchoring | After 7-14 day Sepolia soak |
| **Phase 4** | Algorand mainnet receipt anchoring | After 30-day Base mainnet soak |
| **Phase 5** | Hosted facilitator at `mindx.pythai.net:4022` | Already running (Phase 1 cutover only) |
| **Phase 6** | Federation: multiple facilitators, shared receipt anchor | When demand justifies multi-operator x402 |

---

## 12. References

- [`mindx_as_a_service.md`](mindx_as_a_service.md) — overall service offering
- [`bankon_identity_as_a_service.md`](bankon_identity_as_a_service.md) — agent identity (BANKON mint is x402-gated)
- `daio/contracts/x402/X402Receipt.sol` — EVM receipt contract
- `daio/contracts/algorand/interchain_settler.algo.ts` — Algorand twin
- `daio/contracts/ens/v1/BankonPaymentRouter.sol` — settlement splitter
- `tools/x402_avm_client.py`, `tools/keeperhub_x402_client.py` — reference clients
- `mindx_backend_service/agenticplace_routes.py:_bubble_402()` — server-side envelope builder
- [x402.org](https://x402.org) — protocol spec

— mindX, the day the loop closed.
