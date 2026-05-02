# mindX × Open Agents — Quickstart

End-to-end reproduction in ~10 minutes (with all keys in hand).

## 0. Prerequisites

- Linux with Python 3.11+, Node 20.6+, Foundry (`foundryup`).
- Ethereum-style wallet funded:
  - **0G Galileo** (faucet: https://faucet.0g.ai) — for iNFT contract deploy + mints + storage uploads
  - **Sepolia** (faucet: https://sepoliafaucet.com) — for ENS BankonAgentRegistrar deploy
  - **Base** (Coinbase or any onramp) — small USDC for KH x402 testing (optional)
- ENS name `bankon.eth` registered on Sepolia (free) and/or mainnet.
- 0G Compute API key from https://api.0g.ai (`app-sk-…`).

## 1. Clone + install

```bash
git clone https://github.com/Professor-Codephreak/mindX
cd mindX

# Python deps
python -m venv .mindx_env
.mindx_env/bin/pip install -r requirements.txt

# Sidecar deps
cd openagents/sidecar && npm install && cd ../..
```

## 2. Configure secrets

Either `.env` (gitignored) or BANKON Vault — env vars take precedence:

```bash
# 0G
export ZEROG_API_KEY="app-sk-…"
export ZEROG_PRIVATE_KEY="0x…"           # Galileo deployer
export ZEROG_RPC_URL="https://evmrpc-testnet.0g.ai"

# ENS
export ENS_CONTROLLER_PK="0x…"           # owns bankon.eth
export ENS_NETWORK="sepolia"
export ENS_RPC_URL="https://ethereum-sepolia-rpc.publicnode.com"

# KeeperHub (optional for inbound bridge testing)
export KH_RECIPIENT_ADDRESS="0x…"        # mindX Turnkey wallet on Base
export KEEPERHUB_ORG_KEY="kh_…"

# Uniswap V4 trader (optional)
export UNISWAP_TRADER_PK="0x…"           # Sepolia
```

## 3. Wrap bankon.eth (one-time, irreversible — test on Sepolia first)

1. Visit https://app.ens.domains/bankon.eth
2. Click **Wrap** under the parent name
3. Burn fuses **CANNOT_UNWRAP** + **PARENT_CANNOT_CONTROL**
4. Note the wrapped expiry (subnames cannot exceed it)

## 4. Deploy contracts

```bash
# 0G Galileo: DatasetRegistry + iNFT_7857 + Factory
./openagents/deploy/deploy_galileo.sh
# → writes openagents/deployments/galileo.json

# ENS Sepolia: BankonAgentRegistrar
./openagents/ens/deploy_registrar.sh
# → writes openagents/deployments/sepolia.json

# Then authorize the registrar to mint subnames:
cast send <NameWrapper> "setApprovalForAll(address,bool)" <BankonAgentRegistrar> true \
  --rpc-url $ENS_RPC_URL --private-key $ENS_CONTROLLER_PK
```

## 5. Start the storage sidecar

```bash
ZEROG_PRIVATE_KEY=$ZEROG_PRIVATE_KEY \
  node --experimental-strip-types openagents/sidecar/index.ts &

# verify:
curl http://127.0.0.1:7878/health
```

## 6. Boot mindX

```bash
./mindX.sh --frontend          # frontend on :3000, backend on :8000
# OR backend only:
.mindx_env/bin/python -m uvicorn mindx_backend_service.main_service:app --port 8000
```

Visit:
- http://localhost:8000/openagents.html — live 4-panel dashboard
- http://localhost:8000/inft7857.html — **interactive iNFT-7857 console** (mint, inspect, transfer-with-sealed-key, clone, authorize, burn, bind, admin)
- http://localhost:8000/p2p/keeperhub/info — bridge metadata
- http://localhost:8000/insight/openagents/summary — submission status JSON

## 7. Run the end-to-end demo

```bash
.mindx_env/bin/python openagents/demo_agent.py
```

Output (representative):

```
[1/5] Building payload …                        12,032 bytes  sha256=…
[2/5] Uploading to 0G Storage …                 root=0xabc…  tx=0xdef…
[3/5] Minting ERC-7857 iNFT on Galileo …        tokenId=1  contract=0x…
[4/5] Running BDI cycle on 0G Compute …         8 soldiers polled, 8 attestations collected
[5/5] Anchoring session log on Galileo DSReg …  tx=0x…
```

All hashes link to `chainscan-galileo.0g.ai/tx/<hash>` and `etherscan.io/...`.

## 8. (Optional) Hit the KeeperHub bridge

Inbound (KH wallet pays an AgenticPlace job):
```bash
# This returns 402 with a dual x402+MPP envelope
curl -s -X POST http://localhost:8000/p2p/keeperhub/inference \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"hi"}' | jq .
```

Outbound (mindX consumes a paid KH workflow):
```python
from tools.keeperhub_x402_client import KeeperHubX402Client

client = KeeperHubX402Client(buyer_private_key=os.environ["KH_BUYER_PRIVATE_KEY"])
result = await client.fetch("POST", "https://app.keeperhub.com/some-paid-workflow",
                            json_body={"input": "..."})
print(result["response"])
```

## 9. (Optional) Spawn a fresh agent → auto-issues bankon.eth subname

```bash
# In a Python REPL with the backend running:
from agents.core.id_manager_agent import IDManagerAgent
mgr = await IDManagerAgent.get_instance()
wallet = await mgr.create_agent_wallet("trader-001")
# Async-fires SubdomainIssuer.register_agent in the background.
# Within ~30s, trader-001.bankon.eth resolves to `wallet`.
```

## Run the iNFT-7857 contract test suite

```bash
cd daio/contracts
FOUNDRY_PROFILE=inft forge test                  # 56/56 pass
FOUNDRY_PROFILE=inft forge test --gas-report     # with gas table
FOUNDRY_PROFILE=inft forge test -vvv             # verbose traces
```

The `inft` profile scopes the build to `inft/` + `test/inft/`. See [docs/INFT_7857.md](../../docs/INFT_7857.md) for the full audit, design rationale, and per-tab UI guide.

## Verification matrix

| Piece | Command | Expected |
|-------|---------|----------|
| zerog handler | `curl -X POST localhost:8000/llm/chat -d '{"provider":"zerog",...}'` | 200 + non-empty `attestation` |
| **iNFT-7857 tests** | `cd daio/contracts && FOUNDRY_PROFILE=inft forge test` | **56/56 pass** in <20 s |
| **iNFT-7857 UI** | open `localhost:8000/inft7857.html` | wallet connect button + 9 tabs render |
| sidecar | `curl localhost:7878/health` | `{"ok":true,"network":"galileo"}` |
| KH bridge | `curl localhost:8000/p2p/keeperhub/info` | 200 with both networks (base+tempo) |
| KH 402 | `curl -X POST localhost:8000/p2p/keeperhub/inference -d '{}'` | 402 with `accepts: [exact/base, mpp/tempo]` |
| iNFT deployed | `cast call <inft> 'name()(string)' --rpc-url evmrpc-testnet.0g.ai` | returns `mindX iNFT-7857` |
| ENS subname | `dig +short trader-001.bankon.eth ANY @1.1.1.1` | returns mindX agent record |
| Demo cycle | `python openagents/demo_agent.py` | prints tokenId + 8 attestations + anchor tx |
| Dashboard | open `localhost:8000/openagents.html` | 4 panels populated, status badges live |

## Submission deliverables location

| Track | Where to look |
|-------|---------------|
| 0G Best Framework | this repo + `openagents/README.md` + `mindx-0g/ARCHITECTURE.md` |
| 0G Best iNFT | minted token on `chainscan-galileo.0g.ai/address/<inft_7857>` + `openagents/deployments/galileo.json` |
| KeeperHub | `openagents/keeperhub/bridge_routes.py` + `openagents/keeperhub/FEEDBACK.md` + live `/p2p/keeperhub/info` |
| ENS | `daio/contracts/ens/BankonAgentRegistrar.sol` + `openagents/deployments/sepolia.json` + live ENS resolution |
| Uniswap | `tools/uniswap_v4_tool.py` + `personas/trader.prompt` + `openagents/uniswap/FEEDBACK.md` + decision log under `data/logs/uniswap_decisions.jsonl` |
