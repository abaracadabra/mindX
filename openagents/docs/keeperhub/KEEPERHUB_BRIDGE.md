# KeeperHub × AgenticPlace — Bidirectional x402/MPP Bridge

> Agnostic write-up of the bridge module. The full BANKON architecture document at [`../ens/BANKON_ARCHITECTURE.md`](../ens/BANKON_ARCHITECTURE.md) covers the same material in the context of agent-identity issuance; this file extracts the rails-only view so that any framework — not just BANKON or mindX — can integrate.

## What it does

A single FastAPI route group exposes two flows:

1. **Inbound** — A KeeperHub-hosted wallet hits `https://mindx.pythai.net/p2p/keeperhub/*` and is challenged with an HTTP 402 envelope. The envelope advertises *two* payment rails simultaneously: Base USDC (x402) and Tempo MPP. The caller picks one, settles, and replays the request with the receipt header.
2. **Outbound** — A mindX agent (or any consumer) calls a KeeperHub-hosted workflow via `tools.keeperhub_x402_client.KeeperHubX402Client`. The client handles the 402 dance, picks Base USDC by default, and exposes the receipt for downstream catalogue entry.

## Why "dual-network" matters

Most x402 bridges advertise one rail. KeeperHub workflows can be priced in USDC on Base *or* metered through Tempo MPP, and which one is cheapest changes by region and by time of day. The bridge serves the choice into a single envelope so the caller does the comparison once, in one place, with one signature.

## Envelope schema (inbound)

```http
HTTP/1.1 402 Payment Required
Content-Type: application/json
X-Payment-Required: true
X-Payment-Rails: base-usdc, tempo-mpp

{
  "rails": [
    {
      "name": "base-usdc",
      "chain_id": 8453,
      "asset": "USDC",
      "asset_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      "recipient": "0x...",
      "amount_atomic": "100000",
      "expires_at": 1714512000,
      "nonce": "0x..."
    },
    {
      "name": "tempo-mpp",
      "rail_id": "tempo:metered",
      "rate_per_unit": "0.01",
      "unit": "request",
      "endpoint": "https://tempo.example/mpp",
      "expires_at": 1714512000,
      "nonce": "0x..."
    }
  ],
  "challenge_id": "kh-challenge-...",
  "callback": "https://mindx.pythai.net/p2p/keeperhub/settle"
}
```

The caller picks one rail, settles externally, and replays with `X-Payment-Receipt: <receipt>`.

## Replay protection

Each rail entry carries a `nonce` and `expires_at`. The bridge stores the `(challenge_id, rail.nonce)` pair on first use and rejects re-presentations with HTTP 409. Receipts older than `expires_at` return HTTP 410.

## Catalogue mirroring

Settlements are mirrored as `tool.invoke` and `tool.result` events into the unified catalogue stream when available — the catalogue import is wrapped in `try/except ImportError` so this is a soft dependency, not a build-time requirement.

## Files

- `openagents/keeperhub/bridge_routes.py` — the routes themselves (390 lines).
- `tools/keeperhub_x402_client.py` — the consumer client.
- `openagents/keeperhub/__init__.py` — package marker.

## Public verification

```bash
# Hit the live challenge endpoint (no auth required)
curl -s -o /dev/null -w 'HTTP %{http_code}\n' https://mindx.pythai.net/p2p/keeperhub/challenge
# expect: HTTP 402

# Inspect the envelope
curl -s https://mindx.pythai.net/p2p/keeperhub/info | jq .
# expect: rails[] with both base-usdc and tempo-mpp entries
```
