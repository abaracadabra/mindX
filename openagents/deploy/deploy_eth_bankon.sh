#!/usr/bin/env bash
# Deploy BANKON v1 (4 contracts) to Ethereum — Sepolia (staging) or mainnet (prod).
#
# WHY THIS SCRIPT EXISTS:
#   BANKON v1 has a hard ENS NameWrapper + PublicResolver dependency. 0G has
#   no ENS deployment, so BANKON cannot live on 0G. Sepolia / Eth mainnet are
#   the only options. The Group A (8 contracts) deploy on 0G is independent.
#
# WHAT THIS DEPLOYS (Group B — 4 contracts):
#   1. BankonPriceOracle      (~1.0M gas)
#   2. BankonReputationGate   (~0.6M gas)
#   3. BankonPaymentRouter    (~1.5M gas)
#   4. BankonSubnameRegistrar (~3.5M gas)   8-arg constructor — wires the others
#   Total: ~6.6M gas.
#
# REQUIRED ENV:
#   BANKON_DEPLOYER_PK    deployer private key (0x...)
#   PARENT_NODE           bytes32 namehash of parent (e.g. namehash("bankon.eth"))
#   IDENTITY_REGISTRY     ERC-8004 IdentityRegistry on the same chain (deploy first)
#
# OPTIONAL:
#   ETH_RPC_URL           override RPC (default: from network arg)
#   BANKON_GAS_GWEI       override gas price in gwei
#   ENS_NAME_WRAPPER      override (default: real ENS for the chosen network)
#   ENS_PUBLIC_RESOLVER   override (default: real ENS for the chosen network)
#
# USAGE:
#   bash deploy_eth_bankon.sh sepolia
#   bash deploy_eth_bankon.sh mainnet
#   bash deploy_eth_bankon.sh anvil       # local fork — needs ENS deployed locally

set -euo pipefail

NETWORK="${1:-}"
if [[ -z "$NETWORK" ]]; then
  echo "Usage: $0 {sepolia|mainnet|anvil}" >&2
  exit 1
fi

# ─── network presets ────────────────────────────────────────────────
case "$NETWORK" in
  sepolia)
    CHAIN_ID=11155111
    DEFAULT_RPC="https://sepolia.drpc.org"
    EXPLORER="https://sepolia.etherscan.io"
    DEFAULT_NAME_WRAPPER="0x0635513f179D50A207757E05759CbD106d7dFcE8"
    DEFAULT_RESOLVER="0x8FADE66B79cC9f707aB26799354482EB93a5B7dD"
    OUT_NAME="sepolia"
    MIN_BAL_ETH="0.05"
    ;;
  mainnet)
    CHAIN_ID=1
    DEFAULT_RPC="https://eth.drpc.org"
    EXPLORER="https://etherscan.io"
    DEFAULT_NAME_WRAPPER="0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401"
    DEFAULT_RESOLVER="0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63"
    OUT_NAME="ethereum_mainnet"
    MIN_BAL_ETH="0.2"
    ;;
  anvil)
    CHAIN_ID=31337
    DEFAULT_RPC="http://127.0.0.1:8545"
    EXPLORER="(none — local)"
    DEFAULT_NAME_WRAPPER=""    # must be set by caller (deploy mock first)
    DEFAULT_RESOLVER=""
    OUT_NAME="anvil_bankon"
    MIN_BAL_ETH="0.0"
    ;;
  *)
    echo "Unknown network '$NETWORK'. Choose sepolia / mainnet / anvil." >&2
    exit 1
    ;;
esac

# ─── config ─────────────────────────────────────────────────────────
RPC="${ETH_RPC_URL:-$DEFAULT_RPC}"
NAME_WRAPPER="${ENS_NAME_WRAPPER:-$DEFAULT_NAME_WRAPPER}"
RESOLVER="${ENS_PUBLIC_RESOLVER:-$DEFAULT_RESOLVER}"

if [[ -z "${BANKON_DEPLOYER_PK:-}" ]]; then
  echo "ERROR: BANKON_DEPLOYER_PK is required (0x-prefixed)" >&2
  exit 1
fi
if [[ -z "${PARENT_NODE:-}" ]]; then
  echo "ERROR: PARENT_NODE is required (bytes32 namehash of parent ENS name)" >&2
  echo "  Compute with: cast namehash bankon.eth" >&2
  exit 1
fi
if [[ -z "${IDENTITY_REGISTRY:-}" ]]; then
  echo "ERROR: IDENTITY_REGISTRY is required (deployed ERC-8004 registry)" >&2
  exit 1
fi
if [[ -z "$NAME_WRAPPER" || -z "$RESOLVER" ]]; then
  echo "ERROR: NAME_WRAPPER + RESOLVER must be set (no defaults for $NETWORK)" >&2
  exit 1
fi

DEPLOYER=$(cast wallet address --private-key "$BANKON_DEPLOYER_PK")
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DAIO_DIR="$REPO_ROOT/daio/contracts"
OUT_DIR="$REPO_ROOT/openagents/deployments"
mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/${OUT_NAME}.json"

# ─── pre-flight ─────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════"
echo " BANKON v1 DEPLOYMENT — Group B (4 contracts)"
echo "═══════════════════════════════════════════════════════════════"
echo " Network          : $NETWORK"
echo " Chain ID         : $CHAIN_ID"
echo " RPC              : $RPC"
echo " Explorer         : $EXPLORER"
echo " Deployer         : $DEPLOYER"
echo " Parent node      : $PARENT_NODE"
echo " ENS NameWrapper  : $NAME_WRAPPER"
echo " ENS Resolver     : $RESOLVER"
echo " Identity registry: $IDENTITY_REGISTRY"
echo " Output file      : $OUT_FILE"
echo "═══════════════════════════════════════════════════════════════"

# Verify chain
echo -n "→ verifying chain... "
ACTUAL_CHAIN=$(cast chain-id --rpc-url "$RPC" 2>/dev/null || echo 0)
if [[ "$ACTUAL_CHAIN" != "$CHAIN_ID" ]]; then
  echo "FAIL — RPC reports chain $ACTUAL_CHAIN, expected $CHAIN_ID"
  exit 1
fi
echo "OK ($CHAIN_ID)"

# Verify NameWrapper exists (skip on anvil)
if [[ "$NETWORK" != "anvil" ]]; then
  echo -n "→ verifying ENS NameWrapper... "
  WRAPPER_CODE=$(cast code "$NAME_WRAPPER" --rpc-url "$RPC")
  if [[ "$WRAPPER_CODE" == "0x" ]]; then
    echo "FAIL — no contract at $NAME_WRAPPER"
    exit 1
  fi
  echo "OK"

  echo -n "→ verifying ENS Resolver... "
  RESOLVER_CODE=$(cast code "$RESOLVER" --rpc-url "$RPC")
  if [[ "$RESOLVER_CODE" == "0x" ]]; then
    echo "FAIL — no contract at $RESOLVER"
    exit 1
  fi
  echo "OK"
fi

# Verify identity registry exists
echo -n "→ verifying identity registry... "
ID_CODE=$(cast code "$IDENTITY_REGISTRY" --rpc-url "$RPC")
if [[ "$ID_CODE" == "0x" ]]; then
  echo "FAIL — no contract at $IDENTITY_REGISTRY"
  exit 1
fi
echo "OK"

# Verify balance
echo -n "→ checking deployer balance... "
BAL_WEI=$(cast balance "$DEPLOYER" --rpc-url "$RPC")
BAL_ETH=$(cast --to-unit "$BAL_WEI" ether)
echo "$BAL_ETH ETH"
MIN_BAL_WEI=$(cast --to-wei "$MIN_BAL_ETH" ether)
if (( $(echo "$BAL_WEI < $MIN_BAL_WEI" | bc 2>/dev/null || echo 0) )); then
  echo "ERROR: balance < $MIN_BAL_ETH ETH. Fund the deployer first." >&2
  exit 1
fi

# Probe gas
GAS_PRICE_WEI=$(cast gas-price --rpc-url "$RPC")
GAS_GWEI=$(echo "scale=2; $GAS_PRICE_WEI / 1000000000" | bc 2>/dev/null || echo "?")
echo "→ gas price       : $GAS_GWEI gwei"

# Confirmation
read -p "→ Type 'DEPLOY-$NETWORK' to proceed (anything else aborts): " CONFIRM
if [[ "$CONFIRM" != "DEPLOY-$NETWORK" ]]; then
  echo "Aborted." >&2
  exit 1
fi

# ─── helpers ────────────────────────────────────────────────────────
deploy_contract() {
  local name="$1"; shift
  local contract_path="$1"; shift
  echo
  echo "── $name ─────────────────────────────────────────"
  pushd "$DAIO_DIR" > /dev/null
  local out
  out=$(forge create --rpc-url "$RPC" --private-key "$BANKON_DEPLOYER_PK" \
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

# ─── deploy in dependency order ─────────────────────────────────────
echo
echo ">>> 1/4 BankonPriceOracle"
ORACLE=$(deploy_contract "BankonPriceOracle" \
  "ens/v1/BankonPriceOracle.sol:BankonPriceOracle" \
  --constructor-args "$DEPLOYER" | tail -1 | awk '{print $NF}')

echo
echo ">>> 2/4 BankonReputationGate"
GATE=$(deploy_contract "BankonReputationGate" \
  "ens/v1/BankonReputationGate.sol:BankonReputationGate" \
  --constructor-args "$DEPLOYER" | tail -1 | awk '{print $NF}')

echo
echo ">>> 3/4 BankonPaymentRouter"
ROUTER=$(deploy_contract "BankonPaymentRouter" \
  "ens/v1/BankonPaymentRouter.sol:BankonPaymentRouter" \
  --constructor-args "$DEPLOYER" | tail -1 | awk '{print $NF}')

echo
echo ">>> 4/4 BankonSubnameRegistrar (8-arg constructor)"
REGISTRAR=$(deploy_contract "BankonSubnameRegistrar" \
  "ens/v1/BankonSubnameRegistrar.sol:BankonSubnameRegistrar" \
  --constructor-args \
    "$NAME_WRAPPER" \
    "$RESOLVER" \
    "$PARENT_NODE" \
    "$ROUTER" \
    "$ORACLE" \
    "$GATE" \
    "$IDENTITY_REGISTRY" \
    "$DEPLOYER" | tail -1 | awk '{print $NF}')

# ─── output ─────────────────────────────────────────────────────────
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
cat > "$OUT_FILE" <<EOF
{
  "network": "$NETWORK",
  "chain_id": $CHAIN_ID,
  "rpc": "$RPC",
  "explorer": "$EXPLORER",
  "deployed_at": "$TIMESTAMP",
  "deployer": "$DEPLOYER",
  "contracts": {
    "BankonPriceOracle": "$ORACLE",
    "BankonReputationGate": "$GATE",
    "BankonPaymentRouter": "$ROUTER",
    "BankonSubnameRegistrar": "$REGISTRAR"
  },
  "external": {
    "ens_name_wrapper": "$NAME_WRAPPER",
    "ens_public_resolver": "$RESOLVER",
    "parent_node": "$PARENT_NODE",
    "identity_registry": "$IDENTITY_REGISTRY"
  },
  "note": "Deploy AFTER 0G mainnet Group A (see openagents/docs/0G_MAINNET_DEPLOY.md). Grant MINDX_AGENT_MINTER_ROLE to the agent mint service to enable free <addr>.bankon.eth subnames."
}
EOF

echo
echo "═══════════════════════════════════════════════════════════════"
echo " ✓ BANKON v1 DEPLOYED on $NETWORK"
echo "═══════════════════════════════════════════════════════════════"
echo
echo " Addresses written to: $OUT_FILE"
echo
if [[ "$NETWORK" != "anvil" ]]; then
  echo " Verify on explorer:"
  echo "   $EXPLORER/address/$ORACLE"
  echo "   $EXPLORER/address/$GATE"
  echo "   $EXPLORER/address/$ROUTER"
  echo "   $EXPLORER/address/$REGISTRAR"
  echo
fi
echo " Next steps:"
echo "   1. Approve registrar on NameWrapper (from bankon.eth owner):"
echo "      cast send $NAME_WRAPPER 'setApprovalForAll(address,bool)' $REGISTRAR true \\"
echo "        --private-key \$BANKON_OWNER_PK --rpc-url $RPC"
echo
echo "   2. Grant MINDX_AGENT_MINTER_ROLE to the agent mint service:"
echo "      ROLE=\$(cast call $REGISTRAR 'MINDX_AGENT_MINTER_ROLE()(bytes32)' --rpc-url $RPC)"
echo "      cast send $REGISTRAR 'grantRole(bytes32,address)' \$ROLE \$MINTER_ADDR \\"
echo "        --private-key \$ADMIN_PK --rpc-url $RPC"
echo
echo "   3. Configure agent mint service env:"
echo "      export BANKON_REGISTRAR_ADDR=$REGISTRAR"
echo "      export ENS_RPC_URL=$RPC"
echo "      python -m openagents.ens.agent_mint_service --agent 0x... --agent-uri ipfs://..."
echo
