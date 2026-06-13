#!/usr/bin/env bash
# Deploy BankonAgentRegistrar to Sepolia (mainnet path also supported).
#
# Prereqs:
#   - bankon.eth wrapped via app.ens.domains, fuses CANNOT_UNWRAP +
#     PARENT_CANNOT_CONTROL burned (irreversible — verify on Sepolia first)
#   - export ENS_CONTROLLER_PK=0x...     (controller wallet of bankon.eth)
#   - export ENS_NETWORK=sepolia         (or "mainnet")
#
# After deploy, you MUST also call:
#   cast send $NAME_WRAPPER "setApprovalForAll(address,bool)" $REGISTRAR true \
#     --rpc-url $RPC --private-key $ENS_CONTROLLER_PK
# so the registrar can mint subnames.

set -euo pipefail

NET="${ENS_NETWORK:-sepolia}"
case "$NET" in
  sepolia)
    RPC="${ENS_RPC_URL:-https://ethereum-sepolia-rpc.publicnode.com}"
    NAME_WRAPPER="${ENS_NAME_WRAPPER:-0x0635CFb3Ec4d8a4B3d83d8B3534EB0122e37A353}"
    PUBLIC_RESOLVER="${ENS_PUBLIC_RESOLVER:-0x8FADE66B79cC9f707aB26799354482EB93a5B7dD}"
    EXPLORER="https://sepolia.etherscan.io"
    ;;
  mainnet)
    RPC="${ENS_RPC_URL:-https://eth.llamarpc.com}"
    NAME_WRAPPER="${ENS_NAME_WRAPPER:-0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401}"
    PUBLIC_RESOLVER="${ENS_PUBLIC_RESOLVER:-0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63}"
    EXPLORER="https://etherscan.io"
    ;;
  *)
    echo "Unknown ENS_NETWORK: $NET (expected sepolia|mainnet)" >&2
    exit 1
    ;;
esac

if [[ -z "${ENS_CONTROLLER_PK:-}" ]]; then
  echo "ENS_CONTROLLER_PK is required" >&2
  exit 1
fi

CONTROLLER=$(cast wallet address --private-key "$ENS_CONTROLLER_PK")
PARENT_LABEL="${ENS_PARENT_LABEL:-bankon}"
PARENT_NAME="${ENS_PARENT_NAME:-bankon.eth}"

# namehash("bankon.eth")
PARENT_NODE=$(cast namehash "$PARENT_NAME")

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CONTRACTS_DIR="$REPO_ROOT/daio/contracts"
OUT_DIR="$REPO_ROOT/openagents/deployments"
mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/${NET}.json"

echo "==> Network        : $NET"
echo "==> RPC            : $RPC"
echo "==> Parent name    : $PARENT_NAME"
echo "==> Parent node    : $PARENT_NODE"
echo "==> NameWrapper    : $NAME_WRAPPER"
echo "==> PublicResolver : $PUBLIC_RESOLVER"
echo "==> Controller     : $CONTROLLER"
echo "==> Out file       : $OUT_FILE"
echo

cd "$CONTRACTS_DIR"

echo "==> Deploying BankonAgentRegistrar…"
REG_OUT=$(forge create --rpc-url "$RPC" --private-key "$ENS_CONTROLLER_PK" \
  --constructor-args "$NAME_WRAPPER" "$PARENT_NODE" "$PUBLIC_RESOLVER" \
  ens/BankonAgentRegistrar.sol:BankonAgentRegistrar 2>&1)
REG_ADDR=$(echo "$REG_OUT" | awk '/Deployed to:/ {print $3}')
REG_TX=$(echo "$REG_OUT" | awk '/Transaction hash:/ {print $3}')
echo "    BankonAgentRegistrar: $REG_ADDR  (tx $REG_TX)"

TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
cat > "$OUT_FILE" <<EOF
{
  "network": "$NET",
  "rpc": "$RPC",
  "explorer": "$EXPLORER",
  "controller": "$CONTROLLER",
  "parent_name": "$PARENT_NAME",
  "parent_node": "$PARENT_NODE",
  "name_wrapper": "$NAME_WRAPPER",
  "public_resolver": "$PUBLIC_RESOLVER",
  "deployed_at": "$TS",
  "contracts": {
    "BankonAgentRegistrar": { "address": "$REG_ADDR", "tx": "$REG_TX", "explorer": "$EXPLORER/address/$REG_ADDR" }
  }
}
EOF

echo
echo "==> Wrote $OUT_FILE"
echo
echo "==> NEXT: authorize the registrar to mint subnames:"
echo "    cast send $NAME_WRAPPER 'setApprovalForAll(address,bool)' $REG_ADDR true \\"
echo "      --rpc-url $RPC --private-key \$ENS_CONTROLLER_PK"
