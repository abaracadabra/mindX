#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# gate-anvil.sh — full local E2E for the tiered-login gate on an anvil fork.
#
# anvil does NOT run inside the Claude Code tool sandbox, so run this in YOUR
# shell. It: boots an anvil mainnet-fork, REASSIGNS bankon.eth ownership to a
# local wallet you control (so you can exercise the ADMIN tier), deploys the
# bankon stack, grants the owner roles, enrolls bankon.eth for sale, and starts
# the gate pointed at the fork. Then open the gate and sign in as the local
# admin / a member / a visitor.
#
#   bash examples/gate-anvil.sh
#
# Prereqs: foundry (anvil/forge/cast) + node 20 + python (fastapi/uvicorn/web3).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"; root="$(cd "$here/.." && pwd)"; cd "$root"

MAINNET_RPC="${MAINNET_RPC:-https://ethereum-rpc.publicnode.com}"
RPC=http://127.0.0.1:8545
NODE=0x79c178642317fc2d61d186f3b412440f06590d8314f126362d6a88929a6cbe1a
WRAPPER=0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401
A0=0xf39Fd6e51aad88F6F4ce6aB8827279cfFFb92266       # anvil[0] (admin-to-be)
A0_PK=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
A1=0x70997970C51812dc3A010C7d01b50e0d17dc79C8       # anvil[1] (will buy → member)

echo "==> [1/7] anvil fork (chain-id 31337) on :8545"
anvil --fork-url "$MAINNET_RPC" --chain-id 31337 --port 8545 --silent & ANVIL=$!
trap 'kill $ANVIL 2>/dev/null || true; kill ${GATE:-0} 2>/dev/null || true' EXIT
for i in $(seq 1 30); do cast block-number --rpc-url $RPC >/dev/null 2>&1 && break; sleep 1; done
echo "    up — block $(cast block-number --rpc-url $RPC)"

echo "==> [2/7] reassign bankon.eth → anvil[0] (so you control the admin tier locally)"
CUR=$(cast call $WRAPPER 'ownerOf(uint256)(address)' $NODE --rpc-url $RPC)
echo "    current owner: $CUR"
cast rpc anvil_impersonateAccount "$CUR" --rpc-url $RPC >/dev/null
cast rpc anvil_setBalance "$CUR" 0xde0b6b3a7640000 --rpc-url $RPC >/dev/null   # 1 ETH for gas
cast send $WRAPPER 'safeTransferFrom(address,address,uint256,uint256,bytes)' \
  "$CUR" "$A0" "$NODE" 1 0x --from "$CUR" --unlocked --rpc-url $RPC >/dev/null
cast rpc anvil_stopImpersonatingAccount "$CUR" --rpc-url $RPC >/dev/null
echo "    new owner: $(cast call $WRAPPER 'ownerOf(uint256)(address)' $NODE --rpc-url $RPC) (= anvil[0])"

echo "==> [3/7] deploy bankon stack"
export DEPLOYER_PK=$A0_PK TREASURY_ADDR=$A0
export NAME_WRAPPER_ADDR=$WRAPPER ETH_REGISTRAR_CONTROLLER=0x59E16fcCd424Cc24e280Be16E11Bcd56fb0CE547
export BANKON_ETH_NODE="$(cast namehash bankon.eth)" WEBHOOK_URL="https://agenticplace.pythai.net/api/listings"
forge script script/DeployEthereum.s.sol --rpc-url $RPC --broadcast --silent
node script/extract-deployment.mjs 31337 local

echo "==> [4/7] grant the bankon.eth owner (anvil[0]) admin roles"
DEP=deployments/local.json
export BANKON_OWNER_ADDR=$A0
export PRICE_ORACLE_ADDR=$(node -e "console.log(require('./$DEP').bankon.priceOracle)")
export REPUTATION_GATE_ADDR=$(node -e "console.log(require('./$DEP').bankon.reputationGate)")
export PAYMENT_ROUTER_ADDR=$(node -e "console.log(require('./$DEP').bankon.paymentRouter)")
export DOMAIN_HOSTING_ADDR=$(node -e "console.log(require('./$DEP').bankon.domainHosting)")
export SUBNAME_REGISTRAR_ADDR=$(node -e "console.log(require('./$DEP').bankon.subnameRegistrar)")
forge script script/GrantOwnerRoles.s.sol --rpc-url $RPC --broadcast --silent

echo "==> [5/7] enroll bankon.eth for sale (price 0.002 ETH / label)"
# anvil[0] owns bankon.eth in the NameWrapper, so enroll is authorized.
EXP=$(( $(date +%s) + 31536000 ))
cast send "$DOMAIN_HOSTING_ADDR" 'enroll(bytes32,uint256,uint256,uint32,uint64,uint16)' \
  "$NODE" 5000000 2000000000000000 327685 "$EXP" 9000 --private-key $A0_PK --rpc-url $RPC >/dev/null \
  && echo "    enrolled." || echo "    (enroll reverted — check NameWrapper approval/fuses; storefront price will show 'not enrolled')"

echo "==> [6/7] start the gate against the fork"
export BANKON_GATE_RPC=$RPC
export BANKON_GATE_SECRET=$(python3 -c "import secrets;print(secrets.token_hex(24))")
python3 -m uvicorn backend.app:app --port 8800 --app-dir "$root" >/tmp/bankon-gate.log 2>&1 & GATE=$!
for i in $(seq 1 20); do curl -fsS http://127.0.0.1:8800/healthz >/dev/null 2>&1 && break; sleep 1; done
echo "    gate: http://127.0.0.1:8800/   (log: /tmp/bankon-gate.log)"

echo "==> [7/7] tier checks against the fork"
echo "    resolve admin (anvil[0]): $(python3 -c "import os;os.environ['BANKON_GATE_RPC']='$RPC';from backend.tiers import resolve_tier;print(resolve_tier('$A0')['tier'])")"
echo "    resolve visitor (anvil[1]): $(python3 -c "import os;os.environ['BANKON_GATE_RPC']='$RPC';from backend.tiers import resolve_tier;print(resolve_tier('$A1')['tier'])")"
cat <<EOF

  Open http://127.0.0.1:8800/ and:
    • MetaMask → add network http://127.0.0.1:8545 (chainId 31337)
    • Import anvil[0] ($A0_PK) → Sign in → ADMIN console (set price, run vault)
    • Import anvil[1] (0x59c6...; \`cast wallet\` for the key) → buy a name → becomes MEMBER
    • Any other wallet → VISITOR storefront only; /admin.html and /member.html are 302'd away

  Ctrl-C to stop anvil + the gate.
EOF
wait $ANVIL
