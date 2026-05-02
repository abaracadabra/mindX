# Live Evidence — Per-Track Verification

> One page a judge can scan to verify each submission against the live system. Every claim links to either a passing test, a curl-able endpoint, or a runnable demo. Status reflects **2026-04-30**.
>
> Companion to [`/feedback.html`](https://mindx.pythai.net/feedback.html) (the live "Mind-of-mindX" page) and [`/feedback.txt`](https://mindx.pythai.net/feedback.txt) (one-screen plain-text snapshot).

## Quick smoke (run this first)

```bash
# All 9 of these should return HTTP 200
for ep in /openagents.html /inft7857 /feedback.html /feedback.txt \
          /insight/boardroom/recent /insight/improvement/summary \
          /insight/dreams/recent /insight/godel/recent /insight/storage/status; do
  printf "%-40s -> " "$ep"
  curl -s -o /dev/null -w "HTTP %{http_code}\n" "https://mindx.pythai.net${ep}"
done
```

Storage endpoints (`/storage/health`, `/storage/anchor/health`) are auth-gated and return **401** by design — they hold operator credentials.

---

## 0G — Best Framework + Best iNFT/Swarm ($15,000)

### Local tests

```bash
cd daio/contracts
FOUNDRY_PROFILE=inft forge test
# expect: 56 passed; 0 failed
```

Verified 2026-04-30: **56/56 pass**.

### Live UI

- **iNFT-7857 console**: [`https://mindx.pythai.net/inft7857`](https://mindx.pythai.net/inft7857) → HTTP 200. Single-file ethers v6 + MetaMask UI; 9 tabs (Overview · Mint · Inspect · Transfer · Clone · Authorize · Burn · Bind · Admin). Live event log subscribes to all 14 contract events.
- **OpenAgents composition demo**: [`https://mindx.pythai.net/openagents.html`](https://mindx.pythai.net/openagents.html) → HTTP 200.

### Live insight (read-only, public)

```bash
curl -s 'https://mindx.pythai.net/insight/storage/status?h=true' | head -10
# -> IPFS offload counts, recent CIDs, tx_hashes
curl -s 'https://mindx.pythai.net/insight/storage/recent?h=true'
```

### Source

- Contract: [`daio/contracts/inft/iNFT_7857.sol`](../../daio/contracts/inft/iNFT_7857.sol)
- 0G Compute handler: [`llm/zerog_handler.py`](../../llm/zerog_handler.py)
- 0G Storage provider (Python): [`agents/storage/zerog_provider.py`](../../agents/storage/zerog_provider.py)
- 0G Storage sidecar (Node TS): [`sidecar/`](../sidecar/)
- Galileo deploy script: [`deploy/deploy_galileo.sh`](../deploy/deploy_galileo.sh)

### Submission docs

[`0g/README.md`](0g/README.md) · [`0g/INFT_7857.md`](0g/INFT_7857.md) · [`0g/OG_INTEGRATION_GUIDE.md`](0g/OG_INTEGRATION_GUIDE.md) · [`0g/THOT_0G_MEMORY_ANCHOR.md`](0g/THOT_0G_MEMORY_ANCHOR.md)

---

## Uniswap — Best API Integration ($5,000)

### Local tests

No dedicated forge suite (the trader is Python over Sepolia). Verification is the **decision log + on-chain receipts**:

```bash
cd openagents/uniswap
python demo_trader.py --dry-run            # quote-only smoke
python demo_trader.py                       # full quote → swap on Sepolia
tail -n1 ../../data/logs/uniswap_decisions.jsonl | jq .  # latest decision trace
```

Each decision-trace entry includes a `tx_hash`; paste it into Sepolia Etherscan to verify the swap settled exactly as the BDI cycle decided.

### Source

- Tool: [`tools/uniswap_v4_tool.py`](../../tools/uniswap_v4_tool.py)
- Persona: [`personas/trader.prompt`](../../personas/trader.prompt)
- Demo: [`uniswap/demo_trader.py`](../uniswap/demo_trader.py)

### Submission docs

[`uniswap/README.md`](uniswap/README.md) · [`uniswap/UNISWAP_TRADER.md`](uniswap/UNISWAP_TRADER.md) · **[`uniswap/FEEDBACK.md`](uniswap/FEEDBACK.md)** *(track-required, real content with code references and dated DX issues)*

---

## Gensyn AXL — Best Application of AXL ($5,000)

### Local tests

```bash
cd openagents/conclave
pytest tests/ -c /dev/null                  # 9 protocol tests — verified 9/9 pass on 2026-04-30
cd contracts
forge install foundry-rs/forge-std          # one-time submodule init
forge test                                   # 10 contract tests
```

### Local mesh demo (the AXL evidence)

```bash
cd openagents/conclave
./examples/run_local_8node.sh
# Boots 8 separate AXL processes (CEO + 7 Counsellors) on one host.
# Each is a real AXL node with its own Ed25519 keypair — no in-process shortcuts.
# Watch ./examples/camera_view.html for the live mesh visualization.
```

By design, AXL has **no public endpoint** — communication is mesh-to-mesh between the 8 nodes. The on-chain artifacts are the proofs:

- Bond posting + slash path: `ConclaveBond.sol` (deployed AXL contract)
- Resolution anchoring: `Conclave.sol` (BONAFIDE-gated)

### Source

- Python protocol: [`conclave/conclave/`](../conclave/conclave/) (19 modules)
- Contracts: [`conclave/contracts/src/`](../conclave/contracts/src/) (`Conclave.sol`, `ConclaveBond.sol`)
- mindX adapter (does NOT import mindX): [`conclave/integrations/mindx_boardroom_adapter.py`](../conclave/integrations/mindx_boardroom_adapter.py)

### Submission docs

[`axl/README.md`](axl/README.md) · [`axl/AXL_CEO_SEVENSOLDIERS.md`](axl/AXL_CEO_SEVENSOLDIERS.md) · [`../conclave/SUBMISSION.md`](../conclave/SUBMISSION.md) · [`../conclave/CONCLAVE.md`](../conclave/CONCLAVE.md) · [`../conclave/docs/`](../conclave/docs/)

---

## ENS — Best Integration + Most Creative ($5,000)

### Local tests

```bash
cd daio/contracts
FOUNDRY_PROFILE=bankon forge test
# expect: 29 passed; 0 failed
```

Verified 2026-04-30: **29/29 pass**.

### Live UI

- **BANKON registrar entry**: [`https://mindx.pythai.net/bankon`](https://mindx.pythai.net/bankon) (`/bankon`, `/bankon/page` exposed in prod openapi.json).

### Source

- Solidity registrar: [`daio/contracts/ens/v1/`](../../daio/contracts/ens/v1/)
- Python issuer (agnostic — no mindX imports): [`ens/subdomain_issuer.py`](../ens/subdomain_issuer.py)

### Submission docs

[`ens/README.md`](ens/README.md) · [`ens/BANKON_ENS.md`](ens/BANKON_ENS.md) · [`ens/BANKON_ARCHITECTURE.md`](ens/BANKON_ARCHITECTURE.md) · [`ens/SUBNAME_REGISTRY.md`](ens/SUBNAME_REGISTRY.md)

---

## KeeperHub — Best Use + Builder Bounty ($5,000 + $500)

### Production verification (live as of 2026-05-02)

```bash
curl -s https://mindx.pythai.net/p2p/keeperhub/info | head -c 400
```
```json
{"ok":true,"service":"mindX × AgenticPlace × KeeperHub bridge",
 "x402_supported_networks":[
   {"name":"base","chainId":8453,"usdc":"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"},
   {"name":"tempo","chainId":4217,"usdc":"0x20c0…8b50"}],
 "recipient_configured":false,
 "exposed_endpoints":[
   {"path":"/p2p/keeperhub/agent/register","price_usdc":0.005,"wraps":"/p2p/agent/register"},
   {"path":"/p2p/keeperhub/job/create",...}, ...]}
```

Five routes registered on prod:
- `GET  /p2p/keeperhub/info`
- `POST /p2p/keeperhub/agent/register`
- `POST /p2p/keeperhub/inference`
- `POST /p2p/keeperhub/job/create`
- `POST /p2p/keeperhub/workflow/callback`

### Local verification (works today)

```bash
# Imports cleanly without mindX (catalogue.events is try/except wrapped)
python3 -c "
import sys
sys.path.insert(0, '/home/hacker/mindX/openagents')
from keeperhub import bridge_routes
print('bridge_routes routes:', [r.path for r in bridge_routes.router.routes])
"
```

### Source

- Bridge routes: [`keeperhub/bridge_routes.py`](../keeperhub/bridge_routes.py) (390 lines)
- Python client: [`tools/keeperhub_x402_client.py`](../../tools/keeperhub_x402_client.py)

### Submission docs

[`keeperhub/README.md`](keeperhub/README.md) · [`keeperhub/KEEPERHUB_BRIDGE.md`](keeperhub/KEEPERHUB_BRIDGE.md) · **[`keeperhub/FEEDBACK.md`](keeperhub/FEEDBACK.md)** *(Builder Bounty submission, real content with documentation/SDK/API gaps and dated observations)*

---

## Boardroom — the cross-cutting deliberation engine

> Not a separate prize track, but **the connector that makes the eight modules into one system**. Every other track lands here: 0G inference attestations are recorded in Boardroom sessions, ENS/iNFT decisions are deliberated, the Uniswap trader pulls its opportunity beliefs from Boardroom voting, and Conclave is the AXL-native distributed Boardroom.

### Live endpoints (all 200, public read-only)

| Endpoint | What it returns |
|---|---|
| [`/boardroom/sessions`](https://mindx.pythai.net/boardroom/sessions) | Recent boardroom sessions (auth-gated convene endpoints below) |
| [`/insight/boardroom/recent`](https://mindx.pythai.net/insight/boardroom/recent) | Sessions with per-soldier votes, providers, confidence scores |
| `/insight/boardroom/recent?h=true` | Same data as plain text for terminal monitoring |
| `/boardroom/convene` | (auth-gated) start a new deliberation |
| `/boardroom/convene/stream` | (auth-gated) live SSE stream of an in-progress session |

### Quick verify

```bash
curl -s 'https://mindx.pythai.net/insight/boardroom/recent?h=true' | head -30
```

### How Boardroom maps to each track

- **0G Compute** — Every soldier's vote includes the inference-call attestation (`ZG-Res-Key`) captured from `llm/zerog_handler.py`. The ledger is provider-attested, not just provider-claimed.
- **iNFT-7857** — Mint decisions for new agent persona NFTs flow through Boardroom voting; the resulting tx_hash is recorded with the session.
- **ENS / BANKON** — Subname-issuance decisions for new agents are Boardroom outputs.
- **Uniswap V4 Trader** — Opportunity beliefs are produced by Boardroom and consumed by [`uniswap/demo_trader.py`](../uniswap/demo_trader.py); the persona's slippage/reserve constraints reject anything Boardroom hasn't justified.
- **AXL / Conclave** — Conclave is the *distributed* Boardroom: same deliberation contract, but P2P over AXL with on-chain bond + slash. The `mindx_boardroom_adapter.py` shows the symmetry.

### Source + spec

- Spec: [`boardroom/BOARDROOM.md`](boardroom/BOARDROOM.md) — full DAIO Boardroom v1.0.0 specification (1911 lines).
- Implementation: [`daio/governance/boardroom.py`](../../daio/governance/boardroom.py)
- Catalogue mirroring (every session lands in the unified event stream): [`agents/catalogue/events.py`](../../agents/catalogue/events.py)

---

## Cross-cutting feedback page

The live `/feedback.html` ("Mind-of-mindX") consolidates many of the same signals into one HTML page:

- live agent dialogue
- improvement ledger
- boardroom recent sessions
- dream cycles (machine-dreaming Phases 1–8)
- stuck-loop detector
- memories on chain (storage offload + anchor)

Visit: [`https://mindx.pythai.net/feedback.html`](https://mindx.pythai.net/feedback.html). Plain-text one-screen snapshot for terminals: [`/feedback.txt`](https://mindx.pythai.net/feedback.txt) — pairs with `watch -n5 'curl -s https://mindx.pythai.net/feedback.txt'`.

This file (`LIVE_EVIDENCE.md`) is the per-track *judging* counterpart: organized by prize, with curl-able verification commands so a judge can confirm every claim from the terminal.
