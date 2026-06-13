#!/usr/bin/env bash
#
# bootstrap_anvil.sh — bring up a local Anvil node, deploy the Tier-1 contract
# set (DeployTier1.s.sol), and cache the resulting addresses into
# data/config/blockchain_addresses.json so the blockchain.agents mint pipeline
# can broadcast against chain 1337.
#
# Idempotent: re-running re-deploys a fresh set and overwrites the config.
#
# Requires: foundry (anvil/forge/cast) on PATH; the mindX venv at .mindx_env.
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTRACTS_DIR="$REPO_ROOT/daio/contracts"
RPC_URL="${BLOCKCHAIN_RPC_URL:-http://127.0.0.1:8545}"
CHAIN_ID="${BLOCKCHAIN_CHAIN_ID:-1337}"
PY="$REPO_ROOT/.mindx_env/bin/python"

# Well-known Anvil account[0]: deployer == owner == MINTER_ROLE holder.
ANVIL_PK="${BLOCKCHAIN_MINTER_PK:-0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80}"
ANVIL_ADDR="${BLOCKCHAIN_OWNER_ADDR:-0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266}"

command -v anvil >/dev/null || { echo "ERROR: anvil not on PATH (install foundry)"; exit 1; }
command -v forge >/dev/null || { echo "ERROR: forge not on PATH (install foundry)"; exit 1; }

# 1. Start anvil if nothing is answering on the RPC.
if ! cast block-number --rpc-url "$RPC_URL" >/dev/null 2>&1; then
  echo "[bootstrap] starting anvil (chain-id $CHAIN_ID) ..."
  nohup anvil --chain-id "$CHAIN_ID" --silent >/tmp/anvil_1337.log 2>&1 &
  for _ in $(seq 1 30); do
    cast block-number --rpc-url "$RPC_URL" >/dev/null 2>&1 && break
    sleep 0.5
  done
  cast block-number --rpc-url "$RPC_URL" >/dev/null 2>&1 || { echo "ERROR: anvil did not come up"; exit 1; }
else
  echo "[bootstrap] anvil already up at $RPC_URL"
fi

# 2. Deploy Tier-1. anvil[0] is deployer/owner/royalty/treasury on a local node.
#
# FOUNDRY_PROFILE=thot_commitment scopes the build to inft/ + script/ and follows
# DeployTier1's relative imports (agentregistry, THOT/v1, x402, ens/v1) — avoiding
# the default profile's broken bonding/lib/prb-math tree. The dummy *SCAN keys
# satisfy foundry.toml's eager [etherscan] env resolution (no verification on a
# local node).
echo "[bootstrap] deploying Tier1 ..."
cd "$CONTRACTS_DIR"
mkdir -p "deployments/$CHAIN_ID"   # DeployTier1 writes its receipt here (fs_permissions)
FOUNDRY_PROFILE="${FOUNDRY_PROFILE:-thot_commitment}" \
DEPLOY_BANKON="${DEPLOY_BANKON:-0}" \
ETHERSCAN_API_KEY="${ETHERSCAN_API_KEY:-dummy}" \
BASESCAN_API_KEY="${BASESCAN_API_KEY:-dummy}" \
ARBISCAN_API_KEY="${ARBISCAN_API_KEY:-dummy}" \
OPTIMISTIC_ETHERSCAN_API_KEY="${OPTIMISTIC_ETHERSCAN_API_KEY:-dummy}" \
BSCSCAN_API_KEY="${BSCSCAN_API_KEY:-dummy}" \
DEPLOYER_PRIVATE_KEY="$ANVIL_PK" \
OWNER_MULTISIG="$ANVIL_ADDR" \
ROYALTY_RECEIVER="$ANVIL_ADDR" \
TREASURY_ADDR="$ANVIL_ADDR" \
forge script script/DeployTier1.s.sol \
  --rpc-url "$RPC_URL" \
  --broadcast \
  --skip-simulation 2>&1 | tail -25

RECEIPT="$CONTRACTS_DIR/deployments/$CHAIN_ID/tier1.json"
[ -f "$RECEIPT" ] || { echo "ERROR: deploy receipt missing: $RECEIPT"; exit 1; }

# 3. Merge addresses into data/config/blockchain_addresses.json.
echo "[bootstrap] caching addresses into data/config/blockchain_addresses.json"
"$PY" - "$REPO_ROOT" "$CHAIN_ID" "$RECEIPT" <<'PY'
import json, os, sys
repo, chain_id, receipt_path = sys.argv[1], sys.argv[2], sys.argv[3]
cfg_path = os.path.join(repo, "data", "config", "blockchain_addresses.json")
with open(receipt_path) as fh:
    receipt = json.load(fh)
try:
    with open(cfg_path) as fh:
        cfg = json.load(fh)
except Exception:
    cfg = {}
entry = cfg.get(chain_id, {}) if isinstance(cfg.get(chain_id), dict) else {}
for k in ("inft7857", "agentRegistry", "thot", "x402Receipt", "bankonSubnameRegistrar"):
    if receipt.get(k):
        entry[k] = receipt[k]
entry.setdefault("agenticPlace", None)
entry.setdefault("bankonVault", None)
cfg[chain_id] = entry
with open(cfg_path, "w") as fh:
    json.dump(cfg, fh, indent=2)
print(f"  inft7857      = {entry.get('inft7857')}")
print(f"  agentRegistry = {entry.get('agentRegistry')}")
PY

# 4. Grant the minter MINTER_ROLE on AgentRegistry so it can register agents on
#    behalf of their own identity wallets (owner != msg.sender). The deployer is
#    DEFAULT_ADMIN on the registry, so it grants the role to itself. iNFT_7857
#    already grants the minter MINTER_ROLE in its constructor.
AGENT_REGISTRY="$("$PY" -c "import json;print(json.load(open('$REPO_ROOT/data/config/blockchain_addresses.json'))['$CHAIN_ID']['agentRegistry'])")"
if [ -n "$AGENT_REGISTRY" ] && [ "$AGENT_REGISTRY" != "None" ]; then
  echo "[bootstrap] granting MINTER_ROLE on AgentRegistry to $ANVIL_ADDR"
  MINTER_ROLE="$(cast keccak 'MINTER_ROLE')"
  cast send "$AGENT_REGISTRY" "grantRole(bytes32,address)" "$MINTER_ROLE" "$ANVIL_ADDR" \
    --private-key "$ANVIL_PK" --rpc-url "$RPC_URL" >/dev/null && echo "  granted."
fi

echo "[bootstrap] done. Live mint:"
echo "  curl -s -X POST localhost:8000/blockchain/agentfactory/mint -H 'content-type: application/json' \\"
echo "    -H \"Authorization: Bearer \$ADMIN_JWT\" -d '{\"name\":\"oracle-scout\",\"dry_run\":false}'"
