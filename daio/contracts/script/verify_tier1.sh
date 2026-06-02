#!/usr/bin/env bash
# Tier-1 deploy + verify smoke for `daio/contracts`.
#
# Usage:  bash script/verify_tier1.sh <network>
# where <network> is one of: base_sepolia | sepolia | base | mainnet | arbitrum | optimism | bnb
#
# Steps:
#   1. Re-run all 5 Tier-1 forge profiles to confirm tests pass.
#   2. Source `.env.deploy`.
#   3. Create `deployments/<chainId>/` so DeployTier1's vm.writeJson lands.
#   4. forge script --broadcast --verify ...
#   5. Print the deployed addresses + verify links.

set -euo pipefail

NETWORK="${1:-}"
if [[ -z "$NETWORK" ]]; then
  echo "usage: $0 <network>" >&2
  echo "  networks: base_sepolia | sepolia | base | mainnet | arbitrum | optimism | bnb" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== 1/5 — confirming Tier-1 profiles still green ==="
for prof in inft bankon thot agentregistry x402; do
  echo "[ test $prof ]"
  FOUNDRY_PROFILE=$prof forge test 2>&1 | tail -2
done

echo
echo "=== 2/5 — sourcing .env.deploy ==="
if [[ ! -f .env.deploy ]]; then
  echo "FATAL: .env.deploy not found. Copy .env.deploy.sample and fill in." >&2
  exit 1
fi
# shellcheck disable=SC1091
set -o allexport; source .env.deploy; set +o allexport

# Map network → chainid for the deployments/ subdir.
case "$NETWORK" in
  base_sepolia) CHAIN_ID=84532 ;;
  sepolia)      CHAIN_ID=11155111 ;;
  base)         CHAIN_ID=8453 ;;
  mainnet)      CHAIN_ID=1 ;;
  arbitrum)     CHAIN_ID=42161 ;;
  optimism)     CHAIN_ID=10 ;;
  bnb)          CHAIN_ID=56 ;;
  *) echo "unknown network $NETWORK" >&2; exit 2 ;;
esac

echo
echo "=== 3/5 — preparing deployments/$CHAIN_ID/ ==="
mkdir -p "deployments/$CHAIN_ID"

echo
echo "=== 4/5 — forge script (broadcast + verify) on $NETWORK ==="
forge script script/DeployTier1.s.sol:DeployTier1 \
  --rpc-url "$NETWORK" \
  --broadcast \
  --verify \
  --slow

echo
echo "=== 5/5 — receipt summary ==="
RECEIPT="deployments/$CHAIN_ID/tier1.json"
if [[ -f "$RECEIPT" ]]; then
  echo "tier1.json @ $RECEIPT"
  cat "$RECEIPT" | python3 -m json.tool 2>/dev/null || cat "$RECEIPT"
else
  echo "WARN: $RECEIPT not written by DeployTier1. Check forge output above."
fi

echo
echo "Done. Next steps:"
echo "  - Confirm each contract is source-verified on the explorer for chainid=$CHAIN_ID"
echo "  - Confirm OWNER_MULTISIG owns each deployed address:"
echo "      cast call <addr> 'owner()(address)' --rpc-url $NETWORK"
echo "  - Commit deployments/$CHAIN_ID/tier1.json"
