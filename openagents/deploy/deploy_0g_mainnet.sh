#!/usr/bin/env bash
# Deploy openagents submission contracts to 0G mainnet (chain id 16661).
#
# DIFFERENCES FROM TESTNET:
#   - Real funds. No faucet. ZEROG_PRIVATE_KEY must be funded with ≥ 0.1 OG.
#   - Real finality. Wait for 12 confirmations after each deploy.
#   - chain id 16661 (testnet was 16602).
#   - RPC: https://evmrpc.0g.ai (testnet was https://evmrpc-testnet.0g.ai).
#   - Explorer: https://chainscan.0g.ai (testnet was chainscan-galileo.0g.ai).
#
# WHAT THIS DEPLOYS (Group A — 8 contracts):
#   1. AgentRegistry         (~2.1M gas)   ERC-8004 composable identity
#   2. THOT v1                (~1.5M gas)   memory anchor (commit/reveal)
#   3. iNFT_7857              (~3.8M gas)   intelligent NFT (sealed-key transfer)
#   4. DatasetRegistry        (~0.7M gas)   IPFS/0G storage offload anchor
#   5. Tessera                (~0.5M gas)   BONAFIDE credential placeholder
#   6. Censura                (~0.4M gas)   reputation registry placeholder
#   7. Conclave               (~2.0M gas)   AXL deliberation mesh
#   8. ConclaveBond           (~0.9M gas)   slash bond + Algorand bridge
#   Total: ~11.9M gas. At 4 gwei ≈ 0.048 OG (keep ≥ 0.1 OG for margin).
#
# WHAT THIS DOES NOT DEPLOY (reasons):
#   - BANKON v1 ENS (4 contracts): requires ENS NameWrapper + PublicResolver.
#     0G mainnet has no ENS deployment. Deploy BANKON to Sepolia or mainnet
#     Ethereum separately.
#
# REQUIRED ENV:
#   ZEROG_PRIVATE_KEY     deployer private key (0x...)
#   ROYALTY_RECEIVER      iNFT-7857 royalty recipient (default: deployer)
#   TREASURY_ADDR         iNFT-7857 clone-fee treasury (default: deployer)
#   ORACLE_ADDR           iNFT-7857 EIP-712 oracle pubkey (default: deployer)
#   ALGO_BRIDGE_ADDR      Conclave Algorand bridge (default: 0x0)
#
# OPTIONAL:
#   ZEROG_RPC_URL         override RPC (default https://evmrpc.0g.ai)
#   ZEROG_CHAIN_ID        override chain ID (default 16661)
#   ZEROG_GAS_GWEI        override gas price in gwei (default: pulled live)
#   CLONE_FEE_WEI         iNFT-7857 clone fee (default: 10000000000000000 = 0.01 OG)
#   ROYALTY_BPS           iNFT-7857 royalty bps (default: 250 = 2.5%)

set -euo pipefail

# ─── config ─────────────────────────────────────────────────────────
RPC="${ZEROG_RPC_URL:-https://evmrpc.0g.ai}"
CHAIN_ID="${ZEROG_CHAIN_ID:-16661}"
EXPLORER="https://chainscan.0g.ai"
MIN_BAL_OG="0.05"   # 5e16 wei

if [[ -z "${ZEROG_PRIVATE_KEY:-}" ]]; then
  echo "ERROR: ZEROG_PRIVATE_KEY is required (0x-prefixed deployer key)" >&2
  exit 1
fi

DEPLOYER=$(cast wallet address --private-key "$ZEROG_PRIVATE_KEY")
ROYALTY_RECEIVER="${ROYALTY_RECEIVER:-$DEPLOYER}"
TREASURY_ADDR="${TREASURY_ADDR:-$DEPLOYER}"
ORACLE_ADDR="${ORACLE_ADDR:-$DEPLOYER}"
ALGO_BRIDGE_ADDR="${ALGO_BRIDGE_ADDR:-0x0000000000000000000000000000000000000000}"
CLONE_FEE_WEI="${CLONE_FEE_WEI:-10000000000000000}"
ROYALTY_BPS="${ROYALTY_BPS:-250}"

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DAIO_DIR="$REPO_ROOT/daio/contracts"
CONCLAVE_DIR="$REPO_ROOT/openagents/conclave/contracts"
OUT_DIR="$REPO_ROOT/openagents/deployments"
mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/0g_mainnet.json"

# ─── pre-flight ─────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════"
echo " 0G MAINNET DEPLOYMENT — openagents submission stack"
echo "═══════════════════════════════════════════════════════════════"
echo " Deployer        : $DEPLOYER"
echo " RPC             : $RPC"
echo " Chain ID        : $CHAIN_ID"
echo " Explorer        : $EXPLORER"
echo " Royalty recv    : $ROYALTY_RECEIVER"
echo " Treasury addr   : $TREASURY_ADDR"
echo " Oracle (EIP-712): $ORACLE_ADDR"
echo " Algorand bridge : $ALGO_BRIDGE_ADDR"
echo " Clone fee (wei) : $CLONE_FEE_WEI"
echo " Royalty bps     : $ROYALTY_BPS"
echo " Output file     : $OUT_FILE"
echo "═══════════════════════════════════════════════════════════════"

# Verify chain
echo -n "→ verifying chain... "
ACTUAL_CHAIN=$(cast chain-id --rpc-url "$RPC" 2>/dev/null || echo 0)
if [[ "$ACTUAL_CHAIN" != "$CHAIN_ID" ]]; then
  echo "FAIL — RPC reports chain $ACTUAL_CHAIN, expected $CHAIN_ID"
  exit 1
fi
echo "OK ($CHAIN_ID)"

# Verify balance
echo -n "→ checking deployer balance... "
BAL_WEI=$(cast balance "$DEPLOYER" --rpc-url "$RPC")
BAL_OG=$(cast --to-unit "$BAL_WEI" ether)
echo "$BAL_OG OG"
MIN_BAL_WEI=$(cast --to-wei "$MIN_BAL_OG" ether)
if (( $(echo "$BAL_WEI < $MIN_BAL_WEI" | bc 2>/dev/null || echo 0) )); then
  echo "ERROR: balance < $MIN_BAL_OG OG. Fund the deployer first." >&2
  exit 1
fi

# Probe gas price
GAS_PRICE_WEI=$(cast gas-price --rpc-url "$RPC")
GAS_GWEI=$(echo "scale=2; $GAS_PRICE_WEI / 1000000000" | bc 2>/dev/null || echo "?")
echo "→ gas price       : $GAS_GWEI gwei ($GAS_PRICE_WEI wei)"

# Confirmation
read -p "→ Type 'DEPLOY' to proceed (anything else aborts): " CONFIRM
if [[ "$CONFIRM" != "DEPLOY" ]]; then
  echo "Aborted." >&2
  exit 1
fi

# ─── helpers ────────────────────────────────────────────────────────
deploy_contract() {
  local name="$1"; shift
  local contract_path="$1"; shift
  local cwd="$1"; shift
  echo
  echo "── $name ─────────────────────────────────────────"
  pushd "$cwd" > /dev/null
  local out
  out=$(forge create --rpc-url "$RPC" --private-key "$ZEROG_PRIVATE_KEY" \
                     --broadcast \
                     "$contract_path" "$@" 2>&1)
  popd > /dev/null
  echo "$out" | head -10
  local addr
  addr=$(echo "$out" | grep -oE "Deployed to: 0x[a-fA-F0-9]{40}" | awk '{print $3}')
  if [[ -z "$addr" ]]; then
    echo "ERROR: could not extract address from forge output" >&2
    return 1
  fi
  echo "✓ $name @ $addr"
  echo "$addr"
}

# ─── deploy ─────────────────────────────────────────────────────────
echo
echo ">>> 1/8 AgentRegistry"
AGENT_REG=$(deploy_contract "AgentRegistry" \
  "agentregistry/AgentRegistry.sol:AgentRegistry" \
  "$DAIO_DIR" \
  --constructor-args "$DEPLOYER" | tail -1 | awk '{print $NF}')

echo
echo ">>> 2/8 THOT v1"
THOT=$(deploy_contract "THOT" \
  "THOT/v1/THOT.sol:THOT" \
  "$DAIO_DIR" \
  --constructor-args "$DEPLOYER" "$DEPLOYER" | tail -1 | awk '{print $NF}')

echo
echo ">>> 3/8 iNFT_7857"
INFT=$(deploy_contract "iNFT_7857" \
  "inft/iNFT_7857.sol:iNFT_7857" \
  "$DAIO_DIR" \
  --constructor-args "mindX iNFT-7857" "MINFT" \
                     "$DEPLOYER" "$ROYALTY_RECEIVER" "$ROYALTY_BPS" \
                     "$ORACLE_ADDR" "$TREASURY_ADDR" "$CLONE_FEE_WEI" | tail -1 | awk '{print $NF}')

echo
echo ">>> 4/8 DatasetRegistry"
DATASET_REG=$(deploy_contract "DatasetRegistry" \
  "arc/DatasetRegistry.sol:DatasetRegistry" \
  "$DAIO_DIR" | tail -1 | awk '{print $NF}')

echo
echo ">>> 5-8/8 Conclave stack (Tessera + Censura + Conclave + ConclaveBond)"
pushd "$CONCLAVE_DIR" > /dev/null
SCRIPT_OUT=$(forge script script/Deploy.s.sol:Deploy \
  --rpc-url "$RPC" --private-key "$ZEROG_PRIVATE_KEY" \
  --sig 'runFresh(address)' "$ALGO_BRIDGE_ADDR" \
  --broadcast 2>&1)
popd > /dev/null
echo "$SCRIPT_OUT" | grep -E "Deployed to|=>" | head -10

# Extract addresses from broadcast file
BROADCAST_FILE="$CONCLAVE_DIR/broadcast/Deploy.s.sol/$CHAIN_ID/runFresh-latest.json"
if [[ -f "$BROADCAST_FILE" ]]; then
  TESSERA=$(jq -r '[.transactions[] | select(.contractName == "Tessera")][0].contractAddress' "$BROADCAST_FILE")
  CENSURA=$(jq -r '[.transactions[] | select(.contractName == "Censura")][0].contractAddress' "$BROADCAST_FILE")
  CONCLAVE=$(jq -r '[.transactions[] | select(.contractName == "Conclave")][0].contractAddress' "$BROADCAST_FILE")
  BOND=$(jq -r '[.transactions[] | select(.contractName == "ConclaveBond")][0].contractAddress' "$BROADCAST_FILE")
else
  echo "WARNING: broadcast file not found at $BROADCAST_FILE; addresses must be extracted manually" >&2
  TESSERA="?"
  CENSURA="?"
  CONCLAVE="?"
  BOND="?"
fi

# ─── output ─────────────────────────────────────────────────────────
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
cat > "$OUT_FILE" <<EOF
{
  "network": "0g-mainnet",
  "chain_id": $CHAIN_ID,
  "rpc": "$RPC",
  "explorer": "$EXPLORER",
  "deployed_at": "$TIMESTAMP",
  "deployer": "$DEPLOYER",
  "contracts": {
    "AgentRegistry": "$AGENT_REG",
    "THOT": "$THOT",
    "iNFT_7857": "$INFT",
    "DatasetRegistry": "$DATASET_REG",
    "Tessera": "$TESSERA",
    "Censura": "$CENSURA",
    "Conclave": "$CONCLAVE",
    "ConclaveBond": "$BOND"
  },
  "config": {
    "royalty_receiver": "$ROYALTY_RECEIVER",
    "treasury": "$TREASURY_ADDR",
    "oracle": "$ORACLE_ADDR",
    "algo_bridge": "$ALGO_BRIDGE_ADDR",
    "clone_fee_wei": "$CLONE_FEE_WEI",
    "royalty_bps": $ROYALTY_BPS
  },
  "note": "BANKON v1 (BankonSubnameRegistrar + 3 siblings) is NOT in this deploy. 0G mainnet has no ENS NameWrapper. Deploy BANKON separately to Ethereum mainnet/Sepolia."
}
EOF

echo
echo "═══════════════════════════════════════════════════════════════"
echo " ✓ DEPLOYMENT COMPLETE"
echo "═══════════════════════════════════════════════════════════════"
echo
echo " Addresses written to: $OUT_FILE"
echo
echo " Verify on explorer:"
echo "   $EXPLORER/address/$AGENT_REG"
echo "   $EXPLORER/address/$THOT"
echo "   $EXPLORER/address/$INFT"
echo "   $EXPLORER/address/$DATASET_REG"
echo "   $EXPLORER/address/$TESSERA"
echo "   $EXPLORER/address/$CENSURA"
echo "   $EXPLORER/address/$CONCLAVE"
echo "   $EXPLORER/address/$BOND"
echo
echo " Next steps:"
echo "   1. Cabinet onboarding: tessera.issue() + censura.setScore() per member"
echo "   2. Each member posts bond: bond.postBond{value: 1 ether}(...)"
echo "   3. CEO calls conclave.registerConclave() with the 8-member array"
echo "   4. Update openagents UI to read from $OUT_FILE"
echo
