#!/usr/bin/env bash
#
# deploy.sh — thin CLI wrapper around the deployer for a single chain stage.
#
# Usage:  bash scripts/deployer/deploy.sh <manifest.deploy> <chain> [--signer 0x..]
#
# Local/dev only: sets MINDX_DEPLOYER_CLI_UNSIGNED=1 so the CLI runs without a
# wallet signature. Production deploys go through the wallet-signed backend
# route POST /deployer/intent + /deployer/confirm/<id>.
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="$REPO_ROOT/.mindx_env/bin/python"

[ $# -ge 2 ] || { echo "usage: $0 <manifest.deploy> <chain> [--signer 0x..]" >&2; exit 2; }

cd "$REPO_ROOT"
MINDX_DEPLOYER_CLI_UNSIGNED=1 "$PY" -m agents.deployer.cli deploy "$@"
