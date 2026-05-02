#!/usr/bin/env bash
# SPINTRADE local anvil + deploy + write deployments JSON
#
# Starts anvil in the background, deploys BankonToken + PythaiToken +
# SpinTradeFactory, creates the BANKON/PYTHAI pair, seeds 100k/400k initial
# liquidity. Writes addresses to deployments/anvil.json.
#
# The openagents/uniswap BDI trader reads this file to know where to send
# its swaps.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOYMENTS="$REPO_ROOT/deployments/anvil.json"
LOG_DIR="$REPO_ROOT/anvil/.log"
mkdir -p "$LOG_DIR"

ANVIL_PORT="${ANVIL_PORT:-8545}"
ANVIL_PID_FILE="$LOG_DIR/anvil.pid"
ANVIL_LOG="$LOG_DIR/anvil.log"

# Default Anvil account #0 — public well-known dev key
DEPLOYER_PK="${DEPLOYER_PK:-0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80}"

# ─── Stop any existing anvil ─────────────────────────────────────────
if [[ -f "$ANVIL_PID_FILE" ]]; then
  OLD_PID=$(cat "$ANVIL_PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "→ stopping existing anvil (pid $OLD_PID)…"
    kill "$OLD_PID" || true
    sleep 1
  fi
  rm -f "$ANVIL_PID_FILE"
fi

# ─── Start fresh anvil ───────────────────────────────────────────────
echo "→ starting anvil on port $ANVIL_PORT…"
nohup anvil --port "$ANVIL_PORT" --chain-id 31337 --accounts 10 --silent > "$ANVIL_LOG" 2>&1 &
echo $! > "$ANVIL_PID_FILE"
sleep 2

# Verify it came up
if ! curl -s -X POST "http://127.0.0.1:$ANVIL_PORT" \
    -H 'content-type: application/json' \
    -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' >/dev/null; then
  echo "✗ anvil failed to start; check $ANVIL_LOG" >&2
  exit 1
fi
echo "✓ anvil up (pid $(cat $ANVIL_PID_FILE))"

# ─── Deploy via forge script ─────────────────────────────────────────
echo "→ deploying SPINTRADE…"
cd "$REPO_ROOT"

OUT=$(DEPLOYER_PK="$DEPLOYER_PK" forge script script/DeploySpinTrade.s.sol:DeploySpinTrade \
  --rpc-url "http://127.0.0.1:$ANVIL_PORT" \
  --broadcast 2>&1)
echo "$OUT" | grep -E 'BankonToken|PythaiToken|Factory|Pair|LP minted|price' || true

# ─── Extract addresses from the broadcast file ──────────────────────
BC="$REPO_ROOT/broadcast/DeploySpinTrade.s.sol/31337/run-latest.json"
if [[ ! -f "$BC" ]]; then
  echo "✗ broadcast file not found at $BC" >&2
  exit 1
fi

BANKON=$(jq -r '[.transactions[] | select(.contractName == "BankonToken")][0].contractAddress' "$BC")
PYTHAI=$(jq -r '[.transactions[] | select(.contractName == "PythaiToken")][0].contractAddress' "$BC")
FACTORY=$(jq -r '[.transactions[] | select(.contractName == "SpinTradeFactory")][0].contractAddress' "$BC")

# Pair address — extracted from the factory createPair tx return value via a forge call
PAIR=$(cast call "$FACTORY" "getPair(address,address)(address)" "$BANKON" "$PYTHAI" --rpc-url "http://127.0.0.1:$ANVIL_PORT")

DEPLOYER=$(cast wallet address --private-key "$DEPLOYER_PK")

mkdir -p "$(dirname "$DEPLOYMENTS")"
cat > "$DEPLOYMENTS" <<EOF
{
  "network": "anvil",
  "chain_id": 31337,
  "rpc": "http://127.0.0.1:$ANVIL_PORT",
  "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "deployer": "$DEPLOYER",
  "deployer_pk": "$DEPLOYER_PK",
  "contracts": {
    "BankonToken":      "$BANKON",
    "PythaiToken":      "$PYTHAI",
    "SpinTradeFactory": "$FACTORY",
    "BankonPythaiPair": "$PAIR"
  },
  "initial_liquidity": {
    "bankon": "100000000000000000000000",
    "pythai": "400000000000000000000000",
    "starting_price": "1 BANKON = 4 PYTHAI"
  }
}
EOF

echo
echo "═══════════════════════════════════════════════════════════════"
echo " ✓ SPINTRADE LIVE on anvil (chain 31337)"
echo "═══════════════════════════════════════════════════════════════"
echo " RPC:     http://127.0.0.1:$ANVIL_PORT"
echo " BANKON:  $BANKON"
echo " PYTHAI:  $PYTHAI"
echo " Factory: $FACTORY"
echo " Pair:    $PAIR"
echo " Initial: 100k BANKON + 400k PYTHAI (1:4 starting price)"
echo
echo " Anvil pid: $(cat $ANVIL_PID_FILE)  (logs: $ANVIL_LOG)"
echo " Stop anvil:  kill \$(cat $ANVIL_PID_FILE)"
echo " Addresses:   $DEPLOYMENTS"
echo "═══════════════════════════════════════════════════════════════"
