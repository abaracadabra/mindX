#!/usr/bin/env bash
#
# bootstrap_algorand_localnet.sh — bring up AlgoKit LocalNet and export a funded
# deployer mnemonic for the deployer's Algorand driver.
#
# Prints `export` lines (and writes /tmp/algorand_localnet.env) for:
#   ALGOD_LOCALNET_URL
#   ALGORAND_DEPLOYER_MNEMONIC_LOCALNET   (a pre-funded LocalNet account)
#
# Usage:  source <(bash scripts/deployer/bootstrap_algorand_localnet.sh)
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="$REPO_ROOT/.mindx_env/bin/python"
ALGOD_URL="${ALGOD_LOCALNET_URL:-http://localhost:4001}"
KMD_URL="${ALGOD_KMD_URL:-http://localhost:4002}"

command -v algokit >/dev/null || { echo "ERROR: algokit not on PATH" >&2; exit 1; }

# 1. start LocalNet if algod isn't answering
if ! curl -fsS "$ALGOD_URL/genesis" -H "X-Algo-API-Token: $(printf 'a%.0s' {1..64})" >/dev/null 2>&1; then
  echo "[bootstrap-algo] starting algokit localnet ..." >&2
  algokit localnet start >&2
  for _ in $(seq 1 60); do
    curl -fsS "$ALGOD_URL/genesis" -H "X-Algo-API-Token: $(printf 'a%.0s' {1..64})" >/dev/null 2>&1 && break
    sleep 1
  done
fi

# 2. pull a pre-funded LocalNet account mnemonic from KMD's default wallet
MNEMONIC="$("$PY" - "$KMD_URL" <<'PY'
import sys
from algosdk.kmd import KMDClient
from algosdk import mnemonic
kmd = KMDClient("a" * 64, sys.argv[1])
wid = next(w["id"] for w in kmd.list_wallets() if w["name"] == "unencrypted-default-wallet")
h = kmd.init_wallet_handle(wid, "")
addr = kmd.list_keys(h)[0]
sk = kmd.export_key(h, "", addr)
print(mnemonic.from_private_key(sk))
PY
)"

ENV_FILE="/tmp/algorand_localnet.env"
{
  echo "export ALGOD_LOCALNET_URL=$ALGOD_URL"
  echo "export ALGORAND_DEPLOYER_MNEMONIC_LOCALNET=\"$MNEMONIC\""
} | tee "$ENV_FILE"
echo "[bootstrap-algo] wrote $ENV_FILE" >&2
