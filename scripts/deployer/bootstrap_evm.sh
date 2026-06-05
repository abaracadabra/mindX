#!/usr/bin/env bash
#
# bootstrap_evm.sh — ensure a local Anvil node is up for the deployer's EVM
# driver. Unlike scripts/blockchain/bootstrap_anvil.sh (which also deploys
# Tier1), this only guarantees the node + exports ANVIL_RPC_URL, since the
# deployer's FoundryDriver runs `forge script` itself.
#
# Usage:  source <(bash scripts/deployer/bootstrap_evm.sh)
#
set -euo pipefail

CHAIN_ID="${ANVIL_CHAIN_ID:-1337}"
RPC_URL="${ANVIL_RPC_URL:-http://127.0.0.1:8545}"

command -v anvil >/dev/null || { echo "ERROR: anvil not on PATH (install foundry)" >&2; exit 1; }

if ! cast block-number --rpc-url "$RPC_URL" >/dev/null 2>&1; then
  echo "[bootstrap-evm] starting anvil (chain-id $CHAIN_ID) ..." >&2
  nohup anvil --chain-id "$CHAIN_ID" --silent >/tmp/anvil_deployer.log 2>&1 &
  for _ in $(seq 1 30); do
    cast block-number --rpc-url "$RPC_URL" >/dev/null 2>&1 && break
    sleep 0.5
  done
fi
cast block-number --rpc-url "$RPC_URL" >/dev/null 2>&1 || { echo "ERROR: anvil did not come up" >&2; exit 1; }
echo "export ANVIL_RPC_URL=$RPC_URL"
echo "[bootstrap-evm] anvil up at $RPC_URL" >&2
