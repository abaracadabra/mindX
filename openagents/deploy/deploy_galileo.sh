#!/usr/bin/env bash
# Deploy mindX 0G submission contracts to Galileo testnet (chain id 16602).
#
# Prereqs:
#   - foundryup
#   - export ZEROG_PRIVATE_KEY=0x...        (deployer; faucet 0G beforehand)
#   - export ROYALTY_RECEIVER=0x...         (defaults to deployer)
#   - export ROYALTY_FEE_BPS=250            (2.5%, optional)
#
# Outputs are appended to openagents/deployments/galileo.json.

set -euo pipefail

RPC="${ZEROG_RPC_URL:-https://evmrpc-testnet.0g.ai}"
CHAIN_ID="${ZEROG_CHAIN_ID:-16602}"
FAUCET="https://faucet.0g.ai"
EXPLORER="https://chainscan-galileo.0g.ai"

if [[ -z "${ZEROG_PRIVATE_KEY:-}" ]]; then
  echo "ZEROG_PRIVATE_KEY is required (faucet at $FAUCET first)" >&2
  exit 1
fi

DEPLOYER=$(cast wallet address --private-key "$ZEROG_PRIVATE_KEY")
ROYALTY_RECEIVER="${ROYALTY_RECEIVER:-$DEPLOYER}"
ROYALTY_FEE_BPS="${ROYALTY_FEE_BPS:-250}"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CONTRACTS_DIR="$REPO_ROOT/daio/contracts"
OUT_DIR="$REPO_ROOT/openagents/deployments"
mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/galileo.json"

echo "==> Deployer       : $DEPLOYER"
echo "==> RPC            : $RPC"
echo "==> Royalty recv   : $ROYALTY_RECEIVER"
echo "==> Royalty bps    : $ROYALTY_FEE_BPS"
echo "==> Out file       : $OUT_FILE"
echo

cd "$CONTRACTS_DIR"

# --- 1. DatasetRegistry (anchor target for memory) ---
echo "==> Deploying DatasetRegistry…"
DSREG_OUT=$(forge create --rpc-url "$RPC" --private-key "$ZEROG_PRIVATE_KEY" \
  arc/DatasetRegistry.sol:DatasetRegistry 2>&1)
DSREG_ADDR=$(echo "$DSREG_OUT" | awk '/Deployed to:/ {print $3}')
DSREG_TX=$(echo "$DSREG_OUT" | awk '/Transaction hash:/ {print $3}')
echo "    DatasetRegistry: $DSREG_ADDR  (tx $DSREG_TX)"

# --- 2. iNFT_7857 (the ERC-7857 intelligent NFT) ---
echo "==> Deploying iNFT_7857…"
INFT_OUT=$(forge create --rpc-url "$RPC" --private-key "$ZEROG_PRIVATE_KEY" \
  --constructor-args "mindX iNFT-7857" "MINFT" "$DEPLOYER" "$ROYALTY_RECEIVER" "$ROYALTY_FEE_BPS" \
  inft/iNFT_7857.sol:iNFT_7857 2>&1)
INFT_ADDR=$(echo "$INFT_OUT" | awk '/Deployed to:/ {print $3}')
INFT_TX=$(echo "$INFT_OUT" | awk '/Transaction hash:/ {print $3}')
echo "    iNFT_7857     : $INFT_ADDR  (tx $INFT_TX)"

# --- 3. IntelligentNFTFactory (existing) ---
echo "==> Deploying IntelligentNFTFactory…"
FAC_OUT=$(forge create --rpc-url "$RPC" --private-key "$ZEROG_PRIVATE_KEY" \
  inft/IntelligentNFTFactory.sol:IntelligentNFTFactory 2>&1)
FAC_ADDR=$(echo "$FAC_OUT" | awk '/Deployed to:/ {print $3}')
FAC_TX=$(echo "$FAC_OUT" | awk '/Transaction hash:/ {print $3}')
echo "    Factory       : $FAC_ADDR  (tx $FAC_TX)"

# --- write deployments json ---
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
cat > "$OUT_FILE" <<EOF
{
  "network": "galileo",
  "chainId": $CHAIN_ID,
  "rpc": "$RPC",
  "explorer": "$EXPLORER",
  "deployer": "$DEPLOYER",
  "royalty_receiver": "$ROYALTY_RECEIVER",
  "royalty_fee_bps": $ROYALTY_FEE_BPS,
  "deployed_at": "$TS",
  "contracts": {
    "DatasetRegistry":         { "address": "$DSREG_ADDR", "tx": "$DSREG_TX", "explorer": "$EXPLORER/address/$DSREG_ADDR" },
    "iNFT_7857":               { "address": "$INFT_ADDR",  "tx": "$INFT_TX",  "explorer": "$EXPLORER/address/$INFT_ADDR" },
    "IntelligentNFTFactory":   { "address": "$FAC_ADDR",   "tx": "$FAC_TX",   "explorer": "$EXPLORER/address/$FAC_ADDR" }
  }
}
EOF

echo
echo "==> Wrote $OUT_FILE"
echo "==> Done. Verify with:"
echo "    cast call $INFT_ADDR 'name()(string)' --rpc-url $RPC"
