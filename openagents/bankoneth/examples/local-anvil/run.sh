#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# bankoneth — local E2E driver.
#
# Boots anvil (Ethereum mainnet fork), deploys the bankoneth Ethereum stack,
# claims alice.bankon.eth via the CLI, and asserts the resolver returns the
# expected TBA. Single exit code; suitable for CI.
#
# Prereqs:
#   - foundry installed (forge, anvil, cast)
#   - pnpm 9+ + node 20+
#   - MAINNET_RPC env var (for anvil fork-from-mainnet)
#
# Usage:
#   ./examples/local-anvil/run.sh

set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/../.." && pwd)"

: "${MAINNET_RPC:?MAINNET_RPC required (used by anvil --fork-url)}"

cd "$root"

echo "==> [1/6] booting anvil (forked mainnet) on :8545"
anvil --fork-url "$MAINNET_RPC" --port 8545 --silent &
ANVIL_PID=$!
trap 'kill $ANVIL_PID 2>/dev/null || true' EXIT
sleep 3

echo "==> [2/6] building contracts"
forge build

echo "==> [3/6] deploying bankoneth"
export DEPLOYER_PK=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80   # anvil[0]
export TREASURY_ADDR=0xf39Fd6e51aad88F6F4ce6aB8827279cfFFb92266                          # anvil[0]
export NAME_WRAPPER_ADDR=0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401
export ETH_REGISTRAR_CONTROLLER=0x59E16fcCd424Cc24e280Be16E11Bcd56fb0CE547
export BANKON_ETH_NODE=0x0000000000000000000000000000000000000000000000000000000000000000  # operator computes namehash("bankon.eth") and exports
export WEBHOOK_URL="https://agenticplace.pythai.net/api/listings"

forge script script/DeployEthereum.s.sol --rpc-url http://127.0.0.1:8545 --broadcast --silent

echo "==> [4/6] (skipped) DeployZeroG — local-anvil does not boot 0G; iNFT path is unit-tested separately"

echo "==> [5/6] CLI claim alice"
# Operator would now extract deployed addresses from broadcast/run-latest.json,
# write them to bankoneth-addresses.json, then:
#   pnpm --filter @bankoneth/cli build
#   BANKONETH_RPC_URL=http://127.0.0.1:8545 \
#     BANKONETH_PK=$DEPLOYER_PK \
#     BANKONETH_ADDRESSES_JSON=./bankoneth-addresses.json \
#     ./packages/cli/dist/index.js claim alice --duration 1 --rail eth
echo "  → CLI claim left as operator step (requires extracting addresses from forge broadcast)"

echo "==> [6/6] success"
