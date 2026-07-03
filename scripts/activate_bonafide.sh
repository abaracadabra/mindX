#!/usr/bin/env bash
# activate_bonafide.sh — activate the BONA FIDE .algo member gate on prod once the
# OVERSEER has deployed the ASA. Sets MINDX_BONAFIDE_ASA_ID in the VPS .env,
# restarts mindx.service, and verifies bona_fide picks it up.
#
#   ./scripts/activate_bonafide.sh <ASA_ID> [mainnet|testnet]
#
# The agent cannot sign the on-chain deploy — the OVERSEER (mindx.algo) deploys
# BonaFideDeployer and calls mintBonafideAsa(controller); this script only wires
# the resulting, REAL ASA id into the running service (fail-closed until then).
set -euo pipefail
ASA_ID="${1:?usage: activate_bonafide.sh <ASA_ID> [mainnet|testnet]}"
NET="${2:-mainnet}"
[[ "$ASA_ID" =~ ^[0-9]+$ ]] || { echo "ASA_ID must be an integer"; exit 1; }
case "$NET" in
  mainnet) IDX="https://mainnet-idx.algonode.cloud";;
  testnet) IDX="https://testnet-idx.algonode.cloud";;
  *) echo "network must be mainnet|testnet"; exit 1;;
esac
VPS="root@168.231.126.58"; KEY="$HOME/.ssh/id_rsa"; ENVF="/home/mindx/mindX/.env"
ssh -i "$KEY" -o ConnectTimeout=15 "$VPS" "
  set -e
  touch $ENVF
  sed -i '/^MINDX_BONAFIDE_ASA_ID=/d;/^MINDX_ALGO_INDEXER_URL=/d' $ENVF
  echo 'MINDX_BONAFIDE_ASA_ID=$ASA_ID' >> $ENVF
  echo 'MINDX_ALGO_INDEXER_URL=$IDX'   >> $ENVF
  chown mindx:mindx $ENVF
  systemctl restart mindx.service
"
echo 'set MINDX_BONAFIDE_ASA_ID='"$ASA_ID"' ('"$NET"'); mindx.service restarting'
# verify (wait for boot, then confirm the running service reads the id)
ssh -i "$KEY" -o ConnectTimeout=15 "$VPS" '
  for i in $(seq 1 12); do curl -s -m6 http://127.0.0.1:8000/health >/dev/null 2>&1 && break; sleep 6; done
  cd /home/mindx/mindX && sudo -u mindx env PYTHONPATH=/home/mindx/mindX .mindx_env/bin/python -c \
    "from mindx_backend_service import bona_fide as b; print(\"BONA FIDE active — ASA:\", b.bonafide_asa_id(), \"indexer:\", b._indexer_url())" 2>/dev/null | tail -1
'
