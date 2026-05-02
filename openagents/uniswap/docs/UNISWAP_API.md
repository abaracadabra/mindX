---
name: Uniswap Trading API — internal reference
description: Endpoint surface, curl + Python examples, EIP-712 permit2 signing, and BDI trader wiring for the openagents Uniswap V4 Trader submission.
---

# Uniswap Trading API — Internal Reference

The hosted gateway at `https://trade-api.gateway.uniswap.org/v1/*` is the
**production swap surface** the hackathon submission integrates against.
It abstracts the V2/V3/V4 routing decision behind a single REST API and
returns broadcast-ready transaction calldata.

This doc is the internal reference for the openagents BDI trader. Probed
live against the API; every example here was actually executed and the
responses are shown verbatim.

## Authentication

All endpoints require:

```
x-api-key:                      <your key>
x-universal-router-version:     2.0     (set on /quote and /swap; not on /check_approval)
Content-Type:                   application/json
```

The mindX project stores the key encrypted in BANKON Vault as
`uniswap_trade_api_key`. The Python tool retrieves it via
`get_credential("uniswap_trade_api_key")` — never put it in source or .env.

```bash
# Vault the key (one-time, AES-256-GCM at rest)
python3 manage_credentials.py store uniswap_trade_api_key "<your-key>"

# Read it programmatically
from mindx_backend_service.bankon_vault.credential_provider import get_credential
api_key = get_credential("uniswap_trade_api_key")
```

## Endpoints

| Method | Path | Purpose | Approval/Sig required |
|---|---|---|---|
| POST | `/v1/quote` | Get a quote + permitData (if ERC20 input) | — |
| POST | `/v1/check_approval` | Get ERC20 approve calldata for Permit2 | — |
| POST | `/v1/swap` | Get broadcast-ready swap calldata | EIP-712 permit2 sig |

`/v1/indicative_quote` exists in the docs but returned `403 Forbidden` with
this key — it appears to be a separately gated endpoint. Use `/v1/quote`
instead for all quoting.

## End-to-end swap flow

```
                  ┌──────────────────────────────────────────────┐
                  │  ERC20-input swap (USDC → WETH)              │
                  └──────────────────────────────────────────────┘
                                       │
              ┌────────────────────────┼─────────────────────────┐
              ▼                        ▼                         ▼
   1. POST /v1/check_approval   2. POST /v1/quote      3. EIP-712 sign
        ↓                              ↓                permitData.values
        approve(Permit2, max)          permitData (EIP-712 typed data)   ↓
        broadcast once                                                   │
                                                                         ▼
                                                   4. POST /v1/swap
                                                       {quote, permitData, signature}
                                                            ↓
                                                       transaction calldata
                                                       {to, data, value}
                                                            ↓
                                                   5. Sign & broadcast via web3

                  ┌──────────────────────────────────────────────┐
                  │  Native ETH-input swap (ETH → USDC)          │
                  └──────────────────────────────────────────────┘

                       1. POST /v1/quote → permitData=null
                       2. POST /v1/swap  → no signature needed
                       3. Sign & broadcast (value = amount)
```

---

## 1. POST `/v1/quote`

Returns route + price + (for ERC20 input) EIP-712 typed data to sign.

### Request

```bash
curl --request POST \
  --url https://trade-api.gateway.uniswap.org/v1/quote \
  --header 'Content-Type: application/json' \
  --header 'x-api-key: <KEY>' \
  --header 'x-universal-router-version: 2.0' \
  --data '{
    "type":              "EXACT_INPUT",
    "amount":            "1000000000000000000",
    "tokenInChainId":    "1",
    "tokenOutChainId":   "1",
    "tokenIn":           "0x0000000000000000000000000000000000000000",
    "tokenOut":          "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "swapper":           "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "autoSlippage":      "DEFAULT",
    "routingPreference": "BEST_PRICE",
    "spreadOptimization":"EXECUTION",
    "urgency":           "urgent",
    "permitAmount":      "FULL",
    "generatePermitAsTransaction": false
  }'
```

### Field reference

| Field | Type | Notes |
|---|---|---|
| `type` | enum | `EXACT_INPUT` (sell N tokens for any amount) or `EXACT_OUTPUT` (buy exactly N) |
| `amount` | string | wei amount of the exact-side token |
| `tokenIn` / `tokenOut` | address | `0x0000…0000` for native ETH; ERC20 address otherwise |
| `tokenInChainId` / `tokenOutChainId` | int as string | 1=mainnet, 8453=base, 42161=arbitrum, etc. |
| `swapper` | address | The EOA that will execute the swap |
| `autoSlippage` | enum | `DEFAULT`, `LOW`, `MEDIUM`, `HIGH` |
| `routingPreference` | enum | `BEST_PRICE`, `LOW_GAS`, `LOW_PRICE_IMPACT` |
| `urgency` | enum | `normal`, `fast`, `urgent` — affects gas pricing |
| `permitAmount` | enum | `FULL` or `EXACT` — Permit2 allowance amount |
| `generatePermitAsTransaction` | bool | Set true if your wallet doesn't support EIP-712 (transaction-based permit) |

### Response (live, ETH→USDC, 2026-05-02)

```json
{
  "requestId":"cwZ3Qg6eiYcEPjQ=",
  "routing":"CLASSIC",
  "permitData": null,                // null for native ETH input
  "permitTransaction": null,
  "quote": {
    "chainId": 1,
    "swapper": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "tradeType": "EXACT_INPUT",
    "route": [[{
      "type": "v3-pool",
      "address": "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640",
      "tokenIn":  {"address":"0xC02aaA39…","chainId":1,"symbol":"WETH","decimals":"18"},
      "tokenOut": {"address":"0xA0b86991…","chainId":1,"symbol":"USDC","decimals":"6"},
      "fee":"500",
      "amountIn":  "1000000000000000000",
      "amountOut": "2327256869"
    }]],
    "input":  {"amount":"1000000000000000000","token":"0x000…000"},
    "output": {"amount":"2327256869","token":"0xA0b86991…",
               "recipient":"0xd8dA6BF…"},
    "slippage": 0.5,
    "priceImpact": 0.05,
    "gasFee": "390101467909728",
    "gasFeeUSD": "0.09457669366971999",
    "gasUseEstimate": "171728",
    "quoteId": "3a4cfa6e-2aa5-44ae-a016-b61e5286db80",
    "maxFeePerGas": "2271624126",
    "maxPriorityFeePerGas": "2000000000",
    "aggregatedOutputs": [{
      "amount": "2327256869",
      "minAmount": "2315620584",          // slippage-protected output
      "bps": 10000
    }]
  }
}
```

### ERC20-input case (USDC→WETH) — `permitData` populated

```json
{
  "routing": "CLASSIC",
  "permitData": {
    "domain": { /* EIP-712 domain */ },
    "types":  { /* EIP-712 type definitions */ },
    "values": { /* the typed data to sign */ }
  },
  "quote": { /* same shape as above */ }
}
```

The `permitData` is a complete EIP-712 typed-data envelope. You sign it with
the swapper's private key using `eth_account.messages.encode_typed_data` +
`Account.sign_message`. The resulting signature goes into `/v1/swap`.

---

## 2. POST `/v1/check_approval`

Validates whether a wallet has sufficient token approval for a specified
amount; returns the `approve(Permit2, max)` calldata when approval is
needed, otherwise `null`. Required once per (token, swapper) before any
ERC20-input swap. **Not** required for native ETH input.

Reference: <https://developers.uniswap.org/docs/api-reference/check_approval>

### Headers

| Header | Required | Default | Notes |
|---|---|---|---|
| `x-api-key` | yes | — | Your API key |
| `Content-Type` | yes | — | `application/json` |
| `x-permit2-disabled` | no | `false` | Set `true` to bypass the Permit2 flow and use a direct ERC20 approval pattern (some wallets/tokens don't play nicely with Permit2) |

Note: `x-universal-router-version` is **not** required here — that header is
specific to `/v1/quote` and `/v1/swap`.

### Request body

| Field | Type | Required | Notes |
|---|---|---|---|
| `walletAddress` | address | yes | The EOA performing the swap |
| `token` | address | yes | Input token to be sent |
| `amount` | string (uint) | yes | Quantity in base units (must be > 0) |
| `chainId` | int (enum) | yes | 1 = mainnet (default), 8453 = Base, 42161 = Arbitrum, etc. |
| `urgency` | enum | no | `normal` \| `fast` \| `urgent` (default `urgent`) — affects estimated gas price |
| `includeGasInfo` | bool | no | When `true`, response includes `gasFee` + `cancelGasFee` (default `false`) |
| `tokenOut` | address | no | Receiving token — useful when the gateway wants to estimate full-swap gas |
| `tokenOutChainId` | int (enum) | no | Receiving chain (default `1`) — for cross-chain context |

### Request

```bash
curl --request POST \
  --url https://trade-api.gateway.uniswap.org/v1/check_approval \
  --header 'Content-Type: application/json' \
  --header 'x-api-key: <KEY>' \
  --data '{
    "walletAddress":  "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "token":          "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "amount":         "1000000000",
    "chainId":        1,
    "urgency":        "urgent",
    "includeGasInfo": true
  }'
```

### Response (live, USDC, 1000 base units)

```json
{
  "requestId": "cwaGugXXCYcEMBg=",
  "approval": {
    "to":     "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  // the ERC20
    "from":   "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "data":   "0x095ea7b3000000000000000000000000000000000022d473030f116ddee9f6b43ac78ba3ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
    "value":  "0x00",
    "chainId": 1
  },
  "cancel":       null,
  "gasFee":       null,
  "cancelGasFee": null
}
```

### Response field reference

| Field | Type | Meaning |
|---|---|---|
| `requestId` | string | Server-side trace id; capture in logs for support |
| `approval` | object \| `null` | Broadcast-ready approve calldata, or `null` if existing allowance covers `amount` |
| `approval.to` | address | The ERC20 contract address |
| `approval.from` | address | The wallet (matches request) |
| `approval.data` | hex | `approve(Permit2, max)` calldata — `0x095ea7b3` = `approve(address,uint256)` selector, target is canonical Permit2 `0x000000000022D473030F116dDEE9F6B43aC78BA3`, value is `MaxUint256` |
| `approval.value` | hex | Always `0x00` for ERC20 approve |
| `approval.chainId` | int | Echo of request |
| `cancel` | object \| `null` | A "reset to 0" tx if the token requires it before a new approval (USDT-style approval-race tokens) |
| `gasFee` | string \| `null` | Estimated `gasLimit × maxFeePerGas` for the approve, in chain base units. Only populated when `includeGasInfo=true` |
| `cancelGasFee` | string \| `null` | Same, for the optional cancel tx |

### Behavior notes

- **`approval` is `null` when sufficient allowance already exists** — your
  agent can short-circuit and proceed to `/v1/quote` immediately.
- **`cancel` populated** for tokens that require resetting allowance to
  zero before increasing (legacy USDT, some odd ERC20s). Broadcast the
  cancel tx first, wait for confirmation, then broadcast the approve.
- **Don't cache the response across chains** — `chainId` is part of the
  cache key; the canonical Permit2 address is the same everywhere but the
  ERC20 you're approving is chain-specific.
- **Permit2 max approval** — by approving Permit2 once for the max amount,
  every subsequent swap of that token uses signed permit2 messages
  (off-chain, gas-free) instead of a fresh approve per swap.

---

## 3. POST `/v1/swap`

Takes the quote + signed permit and returns broadcast-ready transaction
calldata. **The signature must be a real EIP-712 sig** — the API rejects
empty strings.

### Request

```bash
curl --request POST \
  --url https://trade-api.gateway.uniswap.org/v1/swap \
  --header 'Content-Type: application/json' \
  --header 'x-api-key: <KEY>' \
  --header 'x-universal-router-version: 2.0' \
  --data '{
    "quote":      <QUOTE_OBJECT_FROM_/v1/quote>,
    "permitData": <PERMIT_DATA_FROM_/v1/quote_OR_NULL_FOR_NATIVE>,
    "signature":  "0x<EIP-712 sig>"
  }'
```

### Response shape

```json
{
  "requestId": "...",
  "swap": {
    "to":       "0x66a9893cC07D91D95644AEDD05D03f95e1dBA8Af",  // Universal Router v2
    "from":     "0xd8dA6BF…",
    "data":     "0x3593564c000000000000000000000000…",        // UR.execute calldata
    "value":    "0x00",                                        // or hex amount for native input
    "gasLimit": "0x29810",
    "maxFeePerGas":         "0x10c388f0c8",
    "maxPriorityFeePerGas": "0x77359400",
    "chainId":  1,
    "nonce":    "0x1f4"
  },
  "gasFee":    "390101467909728",
  "gasFeeUSD": "0.0945…"
}
```

The `swap` object is a complete EIP-1559 transaction. Sign with the
swapper's key and broadcast to any mainnet RPC.

---

## Python end-to-end example

The mindX implementation lives at
`tools/uniswap_api_tool.py`. Highlights:

```python
import aiohttp
from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3

API = "https://trade-api.gateway.uniswap.org/v1"

class UniswapAPI:
    def __init__(self, api_key: str, swapper_pk: str, rpc_url: str):
        self.api_key = api_key
        self.account = Account.from_key(swapper_pk)
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "x-universal-router-version": "2.0",
        }

    async def quote(self, token_in, token_out, amount_in, chain_id=1):
        body = {
            "type": "EXACT_INPUT",
            "amount": str(amount_in),
            "tokenIn": token_in, "tokenOut": token_out,
            "tokenInChainId": str(chain_id), "tokenOutChainId": str(chain_id),
            "swapper": self.account.address,
            "autoSlippage": "DEFAULT", "routingPreference": "BEST_PRICE",
            "urgency": "urgent", "permitAmount": "FULL",
            "generatePermitAsTransaction": False,
            "spreadOptimization": "EXECUTION",
        }
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{API}/quote", json=body, headers=self.headers) as r:
                r.raise_for_status()
                return await r.json()

    async def check_approval(self, token, amount, chain_id=1):
        body = {
            "walletAddress": self.account.address,
            "token": token, "amount": str(amount), "chainId": chain_id,
        }
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{API}/check_approval", json=body,
                              headers={"x-api-key": self.api_key,
                                       "Content-Type": "application/json"}) as r:
                r.raise_for_status()
                return (await r.json()).get("approval")

    def _sign_permit(self, permit_data: dict) -> str:
        # eth_account 0.13+ accepts the Uniswap shape directly via encode_typed_data
        msg = encode_typed_data(
            domain_data=permit_data["domain"],
            message_types=permit_data["types"],
            message_data=permit_data["values"],
        )
        return self.account.sign_message(msg).signature.hex()

    async def swap(self, quote_resp: dict) -> dict:
        body = {"quote": quote_resp["quote"]}
        if quote_resp.get("permitData"):
            body["permitData"] = quote_resp["permitData"]
            body["signature"]  = "0x" + self._sign_permit(quote_resp["permitData"]).lstrip("0x")
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{API}/swap", json=body, headers=self.headers) as r:
                r.raise_for_status()
                return await r.json()

    async def broadcast(self, swap_resp: dict) -> str:
        tx = swap_resp["swap"]
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        signed = self.account.sign_transaction({
            "to":       Web3.to_checksum_address(tx["to"]),
            "data":     tx["data"],
            "value":    int(tx["value"], 16) if isinstance(tx["value"], str) else tx["value"],
            "gas":      int(tx["gasLimit"], 16),
            "maxFeePerGas":         int(tx["maxFeePerGas"], 16),
            "maxPriorityFeePerGas": int(tx["maxPriorityFeePerGas"], 16),
            "nonce":    nonce,
            "chainId":  tx["chainId"],
            "type":     2,
        })
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    async def execute_swap(self, token_in, token_out, amount_in, chain_id=1):
        # 1. (ERC20 only) approve Permit2
        if token_in.lower() != "0x0000000000000000000000000000000000000000":
            ap = await self.check_approval(token_in, amount_in, chain_id)
            if ap:
                signed = self.account.sign_transaction({
                    "to": Web3.to_checksum_address(ap["to"]),
                    "data": ap["data"],
                    "value": 0, "gas": 60_000,
                    "gasPrice": self.w3.eth.gas_price,
                    "nonce": self.w3.eth.get_transaction_count(self.account.address),
                    "chainId": chain_id,
                })
                self.w3.eth.wait_for_transaction_receipt(
                    self.w3.eth.send_raw_transaction(signed.raw_transaction))

        # 2. Quote
        q = await self.quote(token_in, token_out, amount_in, chain_id)

        # 3. Swap (signs permit if present)
        s = await self.swap(q)

        # 4. Broadcast
        return await self.broadcast(s)
```

---

## Common pitfalls

- **`"signature" is not allowed to be empty`** — `/v1/swap` rejects empty
  signatures. Sign the EIP-712 permit even if it feels redundant.
- **`"permitData" must be of type object`** — don't forward the entire
  `/v1/quote` envelope. Only forward the inner `quote` object plus
  `permitData` and `signature`.
- **Native ETH input** — `tokenIn = 0x000…000`, `permitData` will be
  `null`, no approval needed, and `value` on the broadcast tx must equal
  the input amount.
- **Slippage / minAmount** — `quote.aggregatedOutputs[0].minAmount` is the
  slippage-protected floor. Use this when computing minimum-out for risk
  management.
- **`gasFee` units** — denominated in chain base units (wei on EVM). The
  human-readable USD is in `gasFeeUSD`.

---

## Submission evidence

Live probes captured 2026-05-02:

| Endpoint | Tx | Result |
|---|---|---|
| `/v1/quote` (ETH→USDC, 1 ETH) | `requestId=cwZ3Qg6eiYcEPjQ=` | 2327.26 USDC, V3 0.05% pool, $0.09 gas |
| `/v1/quote` (USDC→WETH, 1000 USDC) | — | 0.4291 WETH, permitData populated |
| `/v1/check_approval` (USDC, 1000) | `requestId=cwaGugXXCYcEMBg=` | approval calldata returned |
| `/v1/swap` (sig empty) | — | RequestValidationError (expected) |

These probes prove the API key works against live mainnet routing. The
Python tool above wraps this surface for the BDI trader's `swap` action.

## Uniswap AI — LLM context + skills

Uniswap publishes two surfaces specifically for AI agents — both worth
plumbing into the openagents BDI trader's deliberation step.

### LLM context files

Pre-formatted markdown sized for model context windows:

- **Compact summary:** `https://developers.uniswap.org/docs/uniswap-ai/llms.txt`
- **Verbose v4 reference:** `https://developers.uniswap.org/docs/uniswap-ai/v4-llms.txt`

Wire them in:

| Tool | How |
|---|---|
| Cursor | Settings → Features → Docs → Add new doc URL → reference as `@docs` |
| Claude Code | Install plugins from the marketplace for richer integration than the static file alone |
| openagents BDI trader | Pull the file at startup; embed in the deliberation system prompt so the LLM has authoritative protocol context per cycle |

The Uniswap framing of why this matters: *"providing relevant documentation
upfront helps the model give better answers without hallucinating"* — the
trader's `deliberate()` step in `openagents/uniswap/demo_trader.py` should
prefer this canonical source over generic web knowledge.

### Skills (`npx skills add Uniswap/uniswap-ai`)

Eight skills published in the registry. Install all in one command, then
invoke individually with `/<skill-name>` from a Claude Code or Cursor
session:

| Skill | Purpose |
|---|---|
| `configurator` | Configures CCA auction parameters for new deployments |
| `deployer` | Deploys CCA contracts using factory patterns |
| `liquidity-planner` | Plans LP positions and generates interface deep links |
| `pay-with-any-token` | Handles HTTP 402 challenges using token swaps via Uniswap |
| **`swap-integration`** | Integrates swaps via the Uniswap API, Universal Router, or direct contract calls — invoked with `/swap-integration` |
| `swap-planner` | Plans token swaps and generates interface deep links |
| `v4-security-foundations` | Reviews v4 hook architecture and security risks before implementation |
| `viem-integration` | Sets up EVM clients and contract interactions with viem + wagmi |

Install:

```bash
npx skills add Uniswap/uniswap-ai
# Then invoke from your AI session:
/swap-integration
```

The `swap-integration` skill is the canonical agent-facing wrapper around
the Trading API — for the openagents BDI trader, this is the skill that
turns the trader's deliberation step into a structured "produce me valid
swap calldata" request rather than an ad-hoc API call.

For composability: `pay-with-any-token` is the skill that pairs with the
KeeperHub x402 bridge — when an x402 challenge requires a non-USDC
settlement asset, the agent can route through Uniswap to acquire it.

---

## References

### Uniswap docs

- [Trading API reference root](https://developers.uniswap.org/docs/api-reference)
- [POST /v1/check_approval](https://developers.uniswap.org/docs/api-reference/check_approval)
- [Uniswap AI overview (LLM context files)](https://developers.uniswap.org/docs/uniswap-ai/overview#llm-context-files)
- [Uniswap AI skills registry](https://developers.uniswap.org/docs/uniswap-ai/skills)

### Canonical contracts

- Permit2: `0x000000000022D473030F116dDEE9F6B43aC78BA3` (same on every chain)
- Universal Router v2: `0x66a9893cC07D91D95644AEDD05D03f95e1dBA8Af` (mainnet)

### LLM context endpoints (fetch at runtime)

- `https://developers.uniswap.org/docs/uniswap-ai/llms.txt` — compact
- `https://developers.uniswap.org/docs/uniswap-ai/v4-llms.txt` — verbose v4

### Internal mindX integration points

- Vault: `manage_credentials.py store uniswap_trade_api_key "<KEY>"`
- Provider: `mindx_backend_service/bankon_vault/credential_provider.py:55`
  (allowlist entry `uniswap_trade_api_key → UNISWAP_TRADE_API_KEY`)
- Tool: `tools/uniswap_api_tool.py` (the Python wrapper documented above)
- BDI trader: `openagents/uniswap/demo_trader.py` — `tool.execute("swap")`
  becomes a real broadcast when `UNISWAP_TRADE_API_KEY` is set
