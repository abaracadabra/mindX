#!/usr/bin/env bash
# Sepolia-first BANKON deploy — single command that does everything you need
# to stand up the BANKON v1 registrar suite on Sepolia for staging.
#
# What this script handles automatically that deploy_eth_bankon.sh does NOT:
#
#   1. Computes PARENT_NODE from a parent ENS name (default "bankon.eth")
#      so you don't need to run `cast namehash` yourself.
#   2. Auto-deploys the ERC-8004 IdentityRegistryUpgradeable behind an
#      ERC1967 proxy if you don't already have one — typically required
#      because Sepolia is fresh and you haven't deployed it yet.
#   3. Verifies the deployer wallet owns the parent ENS name (or warns
#      that subname registration will revert without it).
#   4. Lists Sepolia faucets up front + funding requirements so you know
#      where to top up before pressing DEPLOY.
#   5. Chains into deploy_eth_bankon.sh sepolia with all required env
#      already populated.
#
# All state-changing calls go through the same key (BANKON_DEPLOYER_PK).
#
# REQUIRED ENV:
#   BANKON_DEPLOYER_PK    deployer private key (0x... — the shadow-overlord
#                         key, or any funded test key for staging)
#
# OPTIONAL ENV (with sensible defaults):
#   BANKON_PARENT_NAME    parent ENS name for subdomains (default: "bankon.eth")
#   IDENTITY_REGISTRY     skip auto-deploy if you already have one (proxy addr)
#   ETH_RPC_URL           override RPC (default https://sepolia.drpc.org)
#   ENS_NAME_WRAPPER      override (default Sepolia NameWrapper 0x0635...)
#   ENS_PUBLIC_RESOLVER   override (default Sepolia PublicResolver 0x8FAD...)
#
# USAGE:
#   export BANKON_DEPLOYER_PK=0x...
#   bash openagents/deploy/deploy_sepolia_bankon.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DAIO_DIR="$REPO_ROOT/daio/contracts"
DEPLOY_DIR="$REPO_ROOT/openagents/deploy"
OUT_DIR="$REPO_ROOT/openagents/deployments"
mkdir -p "$OUT_DIR"

# ─── Sepolia network constants ───────────────────────────────────────
CHAIN_ID=11155111
RPC="${ETH_RPC_URL:-https://sepolia.drpc.org}"
EXPLORER="https://sepolia.etherscan.io"
NAME_WRAPPER="${ENS_NAME_WRAPPER:-0x0635513f179D50A207757E05759CbD106d7dFcE8}"
RESOLVER="${ENS_PUBLIC_RESOLVER:-0x8FADE66B79cC9f707aB26799354482EB93a5B7dD}"
PARENT_NAME="${BANKON_PARENT_NAME:-bankon.eth}"
MIN_BAL_ETH="0.05"

# ─── Pre-flight ──────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════════════"
echo " BANKON v1 — SEPOLIA FAST-PATH DEPLOY"
echo "═══════════════════════════════════════════════════════════════"

if [[ -z "${BANKON_DEPLOYER_PK:-}" ]]; then
  cat <<'EOF' >&2
ERROR: BANKON_DEPLOYER_PK is required.

  export BANKON_DEPLOYER_PK=0x<your-funded-sepolia-key>

Sepolia faucets (need ~0.05 ETH):
  - https://sepoliafaucet.com           (Alchemy)
  - https://www.sepoliafaucet.io        (PoW)
  - https://faucet.quicknode.com/ethereum/sepolia
  - https://cloud.google.com/application/web3/faucet/ethereum/sepolia
EOF
  exit 1
fi

DEPLOYER=$(cast wallet address --private-key "$BANKON_DEPLOYER_PK")
echo " Deployer:        $DEPLOYER"
echo " Network:         sepolia (chainId $CHAIN_ID)"
echo " RPC:             $RPC"
echo " Parent ENS:      $PARENT_NAME"
echo " NameWrapper:     $NAME_WRAPPER"
echo " PublicResolver:  $RESOLVER"
echo "───────────────────────────────────────────────────────────────"

# Verify chain reachability
echo -n "→ verifying RPC + chainId... "
ACTUAL=$(cast chain-id --rpc-url "$RPC" 2>/dev/null || echo 0)
if [[ "$ACTUAL" != "$CHAIN_ID" ]]; then
  echo "FAIL — RPC reports $ACTUAL, expected $CHAIN_ID"
  exit 1
fi
echo "OK"

# Verify balance
echo -n "→ deployer balance: "
BAL_WEI=$(cast balance "$DEPLOYER" --rpc-url "$RPC")
BAL_ETH=$(cast --to-unit "$BAL_WEI" ether)
echo "$BAL_ETH ETH"
MIN_BAL_WEI=$(cast --to-wei "$MIN_BAL_ETH" ether)
if (( $(echo "$BAL_WEI < $MIN_BAL_WEI" | bc 2>/dev/null || echo 0) )); then
  cat <<EOF >&2

ERROR: balance < $MIN_BAL_ETH ETH. Top up before continuing.

Sepolia faucets:
  - https://sepoliafaucet.com
  - https://www.sepoliafaucet.io
  - https://faucet.quicknode.com/ethereum/sepolia

Address to fund:
  $DEPLOYER
EOF
  exit 1
fi

# Compute PARENT_NODE
echo -n "→ computing namehash($PARENT_NAME)... "
PARENT_NODE=$(cast namehash "$PARENT_NAME")
echo "$PARENT_NODE"

# Verify parent ENS ownership (warn but do not block)
echo -n "→ checking $PARENT_NAME ownership on NameWrapper... "
TOKEN_ID=$(cast --to-uint256 "$PARENT_NODE" 2>/dev/null | tr -d '\n')
PARENT_OWNER=$(cast call "$NAME_WRAPPER" "ownerOf(uint256)(address)" "$PARENT_NODE" --rpc-url "$RPC" 2>/dev/null || echo "0x0000000000000000000000000000000000000000")
if [[ "$PARENT_OWNER" == "0x0000000000000000000000000000000000000000" ]]; then
  echo "UNOWNED"
  cat <<EOF >&2

⚠ Warning: $PARENT_NAME is not wrapped on the Sepolia NameWrapper.

You can either:
  (a) Register $PARENT_NAME at https://app.ens.domains (Sepolia tab),
      then run this script again, OR
  (b) Override BANKON_PARENT_NAME with a parent name you DO own:
        export BANKON_PARENT_NAME=mytestname.eth
        bash $0
  (c) Continue anyway — the registrar will deploy but you can't mint
      subnames until the parent is wrapped + setApprovalForAll() is run.
EOF
  read -p "→ Type 'CONTINUE' to deploy anyway, anything else aborts: " CONT
  [[ "$CONT" == "CONTINUE" ]] || { echo "Aborted."; exit 1; }
elif [[ "${PARENT_OWNER,,}" == "${DEPLOYER,,}" ]]; then
  echo "OWNED-BY-DEPLOYER ✓"
else
  echo "owned by $PARENT_OWNER"
  cat <<EOF >&2

⚠ Warning: $PARENT_NAME is owned by $PARENT_OWNER, not by you ($DEPLOYER).

Subname registration will revert until that owner runs:
  cast send $NAME_WRAPPER "setApprovalForAll(address,bool)" <REGISTRAR> true \\
    --private-key <PARENT_OWNER_PK> --rpc-url $RPC

Continue if you control the parent owner key separately.
EOF
  read -p "→ Type 'CONTINUE' to proceed, anything else aborts: " CONT
  [[ "$CONT" == "CONTINUE" ]] || { echo "Aborted."; exit 1; }
fi

# ─── Phase A: deploy IdentityRegistry if not provided ──────────────
if [[ -z "${IDENTITY_REGISTRY:-}" ]]; then
  echo
  echo "═══ Phase A: deploying ERC-8004 IdentityRegistryUpgradeable ═══"
  echo " (set IDENTITY_REGISTRY env to skip this step)"

  cd "$DAIO_DIR"

  # 1) Implementation
  echo -n "→ deploying implementation... "
  IMPL_OUT=$(forge create --rpc-url "$RPC" --private-key "$BANKON_DEPLOYER_PK" \
    --broadcast \
    agenticplace/evm/IdentityRegistryUpgradeable.sol:IdentityRegistryUpgradeable 2>&1)
  IMPL_ADDR=$(echo "$IMPL_OUT" | grep -oE "Deployed to: 0x[a-fA-F0-9]{40}" | awk '{print $3}')
  if [[ -z "$IMPL_ADDR" ]]; then
    echo "FAIL"; echo "$IMPL_OUT" | tail -10 >&2; exit 1
  fi
  echo "$IMPL_ADDR"

  # 2) Encode initialize() calldata
  INIT_CALLDATA=$(cast calldata "initialize()")

  # 3) ERC1967Proxy
  echo -n "→ deploying ERC1967 proxy... "
  PROXY_OUT=$(forge create --rpc-url "$RPC" --private-key "$BANKON_DEPLOYER_PK" \
    --broadcast \
    agenticplace/evm/ERC1967Proxy.sol:ERC1967Proxy \
    --constructor-args "$IMPL_ADDR" "$INIT_CALLDATA" 2>&1)
  PROXY_ADDR=$(echo "$PROXY_OUT" | grep -oE "Deployed to: 0x[a-fA-F0-9]{40}" | awk '{print $3}')
  if [[ -z "$PROXY_ADDR" ]]; then
    echo "FAIL"; echo "$PROXY_OUT" | tail -10 >&2; exit 1
  fi
  echo "$PROXY_ADDR"

  IDENTITY_REGISTRY="$PROXY_ADDR"
  echo "✓ IdentityRegistry proxy deployed at $IDENTITY_REGISTRY"
  echo "  (impl: $IMPL_ADDR, will be upgraded via UUPS in future)"
else
  echo
  echo "→ Reusing IdentityRegistry: $IDENTITY_REGISTRY"
  IMPL_ADDR=""
fi

# ─── Phase B: chain into the existing BANKON deploy script ─────────
echo
echo "═══ Phase B: deploying BANKON v1 (4 contracts) ═══"
echo

export ETH_RPC_URL="$RPC"
export PARENT_NODE
export IDENTITY_REGISTRY
# BANKON_DEPLOYER_PK already in env

bash "$DEPLOY_DIR/deploy_eth_bankon.sh" sepolia

# ─── Phase C: enrich the deployments JSON ──────────────────────────
SEPOLIA_JSON="$OUT_DIR/sepolia.json"
if [[ -f "$SEPOLIA_JSON" ]]; then
  TMP="$SEPOLIA_JSON.tmp"
  jq --arg parent "$PARENT_NAME" \
     --arg parent_node "$PARENT_NODE" \
     --arg id_impl "$IMPL_ADDR" \
     '.bankon_parent_name = $parent
      | .bankon_parent_node = $parent_node
      | (if $id_impl != "" then .external.identity_registry_impl = $id_impl else . end)' \
     "$SEPOLIA_JSON" > "$TMP" && mv "$TMP" "$SEPOLIA_JSON"
fi

echo
echo "═══════════════════════════════════════════════════════════════"
echo " ✓ SEPOLIA BANKON v1 DEPLOYED"
echo "═══════════════════════════════════════════════════════════════"
if [[ -f "$SEPOLIA_JSON" ]]; then
  echo " Addresses:"
  jq -r '.contracts | to_entries[] | "   \(.key): \(.value)"' "$SEPOLIA_JSON"
  echo
  echo " External:"
  jq -r '.external | to_entries[] | "   \(.key): \(.value)"' "$SEPOLIA_JSON"
fi
echo
echo " Next steps:"
if [[ "$PARENT_OWNER" == "$DEPLOYER" ]]; then
  REGISTRAR=$(jq -r .contracts.BankonSubnameRegistrar "$SEPOLIA_JSON")
  echo "   1. Approve registrar on NameWrapper:"
  echo "      cast send $NAME_WRAPPER 'setApprovalForAll(address,bool)' $REGISTRAR true \\"
  echo "        --private-key \$BANKON_DEPLOYER_PK --rpc-url $RPC"
fi
echo "   2. Grant MINDX_AGENT_MINTER_ROLE to the agent mint service:"
echo "      ROLE=\$(cast call \$REGISTRAR 'MINDX_AGENT_MINTER_ROLE()(bytes32)' --rpc-url $RPC)"
echo "      cast send \$REGISTRAR 'grantRole(bytes32,address)' \$ROLE \$MINTER \\"
echo "        --private-key \$BANKON_DEPLOYER_PK --rpc-url $RPC"
echo "   3. Hit /bankonminter at https://mindx.pythai.net/bankonminter,"
echo "      click 'Auto-load from deployments JSON', mint your first subname."
echo
