# KeeperHub — $5,000 + $500 Bounty

Two prizes here, both addressable by the **bidirectional x402/MPP bridge** shipped at `openagents/keeperhub/`:

- **Best Use of KeeperHub ($4,500)** — innovative use of KeeperHub MCP / CLI for agents, workflows, or dApps; integration with x402 or MPP rails.
- **Builder Feedback Bounty ($500, two teams × $250)** — actionable DX feedback from real integration.

## Submission entry points

| Prize | Submission | Primary doc |
|---|---|---|
| Best Use | mindX × KeeperHub Bridge — dual-network challenge + settlement (Base USDC + Tempo MPP) | [`KEEPERHUB_BRIDGE.md`](KEEPERHUB_BRIDGE.md) |
| Builder Bounty | KeeperHub DX Feedback — friction notes from real integration | [`FEEDBACK.md`](FEEDBACK.md) |

## What ships

- `openagents/keeperhub/bridge_routes.py` — 390 lines, FastAPI routes hosting **inbound** x402 challenges (KH wallet pays AgenticPlace) and **outbound** consumption (mindX pays KH workflows via `KeeperHubX402Client`).
- `tools/keeperhub_x402_client.py` — Python client mirroring the existing `pay2play_metered_tool` x402 shape.
- Live verification: `GET https://mindx.pythai.net/p2p/keeperhub/info` returns the dual-network challenge envelope (Base USDC payment requirement + Tempo MPP payment requirement, both in one response).

## How to verify

```bash
# Inbound 402 challenge (no auth, any caller)
curl -i https://mindx.pythai.net/p2p/keeperhub/challenge

# Expect: HTTP/1.1 402 Payment Required with X-Payment-* headers
# describing both Base USDC and Tempo MPP rails simultaneously.

# Outbound consumption (requires KEEPERHUB_API_KEY in vault)
python -c "
import asyncio
from tools.keeperhub_x402_client import KeeperHubX402Client
async def main():
    c = KeeperHubX402Client()
    print(await c.list_workflows())
asyncio.run(main())
"
```

## Files in this folder

- [`README.md`](README.md) — this file.
- [`KEEPERHUB_BRIDGE.md`](KEEPERHUB_BRIDGE.md) — agnostic write-up of the dual-network bridge: handshake sequence, envelope schema, settlement reconciliation, replay protection.
- [`FEEDBACK.md`](FEEDBACK.md) — Builder-Bounty submission: DX friction, bugs, doc gaps encountered during integration.

## See also

- Cross-cutting architecture: [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
- Bridge code: [`../../keeperhub/bridge_routes.py`](../../keeperhub/bridge_routes.py)
- Python client: [`../../../tools/keeperhub_x402_client.py`](../../../tools/keeperhub_x402_client.py)
- Related architecture (BANKON ENS deep dive that mentions KeeperHub): [`../ens/BANKON_ARCHITECTURE.md`](../ens/BANKON_ARCHITECTURE.md)
