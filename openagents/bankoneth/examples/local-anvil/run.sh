#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# bankoneth — local pseudo-live driver.
#
# Boots anvil (Ethereum mainnet fork, chain-id 31337), deploys the bankoneth
# Ethereum stack, auto-writes the deployed addresses into deployments/local.json
# (+ the dApp's public mirror), demonstrates live ABI reads via cast, then stays
# running so the dApp at packages/web/bankoneth.html can interact with it through
# MetaMask. Ctrl-C to stop.
#
# NOTE: must be run in YOUR shell — anvil does not run inside the Claude Code
# tool sandbox. From the repo: `bash examples/local-anvil/run.sh`
#
# Prereqs: foundry (forge, anvil, cast) + node 20+. A mainnet RPC for the fork
# (defaults to a public node; override with MAINNET_RPC).

set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/../.." && pwd)"
cd "$root"

MAINNET_RPC="${MAINNET_RPC:-https://ethereum-rpc.publicnode.com}"
RPC=http://127.0.0.1:8545

echo "==> [1/6] booting anvil (fork: $MAINNET_RPC) on :8545 chain-id 31337"
anvil --fork-url "$MAINNET_RPC" --chain-id 31337 --port 8545 --silent &
ANVIL_PID=$!
trap 'echo; echo "stopping anvil ($ANVIL_PID)"; kill $ANVIL_PID 2>/dev/null || true' EXIT
for i in $(seq 1 30); do cast block-number --rpc-url $RPC >/dev/null 2>&1 && break; sleep 1; done
echo "    anvil up — block $(cast block-number --rpc-url $RPC), chain $(cast chain-id --rpc-url $RPC)"

echo "==> [2/6] building contracts"
forge build >/dev/null

echo "==> [3/6] deploying bankoneth stack"
export DEPLOYER_PK=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80   # anvil[0]
export TREASURY_ADDR=0xf39Fd6e51aad88F6F4ce6aB8827279cfFFb92266                          # anvil[0]
export NAME_WRAPPER_ADDR=0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401
export ETH_REGISTRAR_CONTROLLER=0x59E16fcCd424Cc24e280Be16E11Bcd56fb0CE547
export BANKON_ETH_NODE="$(cast namehash bankon.eth)"
export WEBHOOK_URL="https://agenticplace.pythai.net/api/listings"
forge script script/DeployEthereum.s.sol --rpc-url $RPC --broadcast --silent

echo "==> [4/6] wiring deployments/local.json (+ dApp public mirror)"
node script/extract-deployment.mjs 31337 local

echo "==> [5/6] live ABI reads (proof the contracts respond on anvil)"
PO=$(node -e "console.log(require('./deployments/local.json').bankon.priceOracle)")
AR=$(node -e "console.log(require('./deployments/local.json').bankon.agentRegistry)")
echo "    priceOracle.priceUSD('alice', 1) = $(cast call "$PO" 'priceUSD(string,uint256)(uint256)' alice 1 --rpc-url $RPC) (USD, 6dp)"
echo "    agentRegistry.name()             = $(cast call "$AR" 'name()(string)' --rpc-url $RPC)"

echo "==> [6/6] ready — dApp can now interact pseudo-live"
cat <<EOF

  Serve the dApp (separate shell):  cd packages/web && python3 -m http.server 8788
  Open:                             http://localhost:8788/bankoneth.html

  MetaMask -> Add network:
    RPC URL  : http://127.0.0.1:8545
    Chain ID : 31337
    Currency : ETH
  Import anvil account #0 (1e4 ETH) with key:
    0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

  Pseudo-live from ABI:
    * Contract explorer -> pick any contract -> reads return live values, writes
      sign via MetaMask (e.g. AgentRegistry.register works out of the box).
    * Reads like priceOracle.priceUSD / ethRegistrar.quote / reputationGate.* are live.
    * NOTE: claiming *.bankon.eth needs the deployer to OWN bankon.eth in the
      NameWrapper — on a fork it's the real mainnet owner, so registerFree reverts.
      The fork tests (test/fork/) impersonate that owner; the live dApp can't.
      Everything else is fully interactive.

  Anvil is running (pid $ANVIL_PID). Ctrl-C here to stop it.
EOF

wait $ANVIL_PID
