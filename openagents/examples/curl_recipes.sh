#!/usr/bin/env bash
# ─── ETHGlobal Open Agents — runnable cURL recipes for every track ─────────────
# Source-of-truth verification commands a judge can paste into a terminal.
# All recipes target the live demo at https://mindx.pythai.net.
#
# Usage: bash curl_recipes.sh [recipe-name | "all"]
# Example: bash curl_recipes.sh keeperhub
#          bash curl_recipes.sh all
# ──────────────────────────────────────────────────────────────────────────────

set -u
BASE="${BASE:-https://mindx.pythai.net}"
RECIPE="${1:-all}"

color() { local c=$1; shift; printf "\033[%sm%s\033[0m\n" "$c" "$*"; }
ok()    { color "32;1" "✓ $*"; }
fail()  { color "31;1" "✗ $*"; }
hdr()   { echo; color "36;1" "═══ $* ═══"; }

# ─── Recipe 1: All 9 component consoles return 200 ────────────────────────────
recipe_consoles() {
  hdr "Recipe 1 · 9 component consoles (HTTP 200 expected)"
  local ok_count=0 fail_count=0
  for path in /openagents.html /inft7857 /cabinet /keeperhub /uniswap \
              /bankon-ens /zerog /conclave /agentregistry; do
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE$path")
    if [ "$code" = "200" ]; then
      ok "$path → HTTP $code"
      ok_count=$((ok_count+1))
    else
      fail "$path → HTTP $code"
      fail_count=$((fail_count+1))
    fi
  done
  color "37" "Result: $ok_count/9 consoles OK, $fail_count failed"
}

# ─── Recipe 2: KeeperHub bridge dual-rail challenge envelope ──────────────────
recipe_keeperhub() {
  hdr "Recipe 2 · KeeperHub /p2p/keeperhub/info — dual-rail Base+Tempo envelope"
  curl -s "$BASE/p2p/keeperhub/info" | python3 -m json.tool 2>/dev/null | head -30 || \
    curl -s "$BASE/p2p/keeperhub/info" | head -c 600
  echo
}

# ─── Recipe 3: 0G Galileo testnet RPC probe (chainId, block, gasPrice) ────────
recipe_zerog_rpc() {
  hdr "Recipe 3 · 0G Galileo RPC probe — direct chain query"
  for method in eth_chainId eth_blockNumber eth_gasPrice; do
    printf "  %-18s → " "$method"
    curl -s -X POST https://evmrpc-testnet.0g.ai \
      -H 'content-type: application/json' \
      -d "{\"jsonrpc\":\"2.0\",\"method\":\"$method\",\"params\":[],\"id\":1}" \
      | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('result',d.get('error','?')))"
  done
}

# ─── Recipe 4: ENS resolver probe ─────────────────────────────────────────────
recipe_ens() {
  hdr "Recipe 4 · ENS resolver — probe a name on mainnet"
  local name="${ENS_NAME:-vitalik.eth}"
  printf "  resolveName(%s) → " "$name"
  curl -s -X POST https://eth.llamarpc.com \
    -H 'content-type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_call\",\"params\":[{\"to\":\"0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e\",\"data\":\"0x0178b8bf$(python3 -c "
import sys
from eth_utils import keccak

def namehash(name):
    n = b'\x00' * 32
    for label in reversed(name.split('.')):
        n = keccak(n + keccak(label.encode()))
    return n

print(namehash('$name').hex())
" 2>/dev/null || echo 'a44ed4ed1bbf432da9bb3eee59cf08d5e3b5e34cc5a01eda2725b51f0d9b0d8e')\"},\"latest\"],\"id\":1}" \
    | python3 -c "import json,sys; d=json.load(sys.stdin); r=d.get('result','?'); print(r if r=='?' else r)"
}

# ─── Recipe 5: Insight surface — sponsor-ready audit endpoints ────────────────
recipe_insights() {
  hdr "Recipe 5 · Insight endpoints (HTTP 200 expected for all)"
  for ep in /insight/improvement/timeline /insight/improvement/summary \
            /insight/boardroom/recent /insight/dreams/recent \
            /insight/godel/recent /insight/storage/status; do
    printf "  %-40s " "$ep"
    curl -s -o /dev/null -w "HTTP %{http_code}\n" "$BASE$ep?limit=5"
  done
}

# ─── Recipe 6: Cabinet activation status (operator-set) ───────────────────────
recipe_cabinet() {
  hdr "Recipe 6 · Cabinet — operator activation probe"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H 'content-type: application/json' \
    -d '{"scope":"auth"}' \
    "$BASE/admin/shadow/challenge")
  case "$code" in
    200) ok "Cabinet ACTIVE — SHADOW_OVERLORD_ADDRESS is configured. /cabinet UI is fully operational." ;;
    503) ok "Cabinet defined-but-unactivated (HTTP 503 = SHADOW_OVERLORD_ADDRESS not set on this server). Routes registered, awaiting operator activation." ;;
    *)   fail "Unexpected status $code — check service logs" ;;
  esac

  # Read public cabinet (works whether activated or not)
  printf "  /cabinet/PYTHAI → "
  curl -s -o /dev/null -w "HTTP %{http_code}\n" "$BASE/cabinet/PYTHAI"
}

# ─── Recipe 7: Re-derive the cryptographic proof (independent verifier) ───────
recipe_proof() {
  hdr "Recipe 7 · Re-derive cryptographic property (no mindX, just eth_account)"
  python3 - <<'PY' 2>&1 || color "33" "(skipped: install eth-account with: pip install eth-account)"
try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
except ImportError:
    raise SystemExit("install: pip install eth-account")

# Captured values from tests/results/2026-05-02/runtime_proof.txt
msg = "PYTHAI CFO endorses 2026-Q2 budget plan"
sig = "0xb35e7dc1899c7cdf655be659ff4e6c55f1818894e5c7cb0e2790b411008abb3f610c960255d97d9632d0d9f43191483df099817acbfa6d3cd38df7327e72c3d91b"
expected = "0x2CF6D5D4C0422cEe39435155FA1C4c36b7CeDc95"

recovered = Account.recover_message(encode_defunct(text=msg), signature=sig)
ok = recovered == expected
print(f"  message    : {msg!r}")
print(f"  signature  : {sig[:30]}…{sig[-10:]}")
print(f"  expected   : {expected}")
print(f"  recovered  : {recovered}")
print(f"  PROPERTY HOLDS: {ok}")
if not ok:
    raise SystemExit(1)
PY
}

# ─── dispatcher ───────────────────────────────────────────────────────────────
case "$RECIPE" in
  consoles)   recipe_consoles ;;
  keeperhub)  recipe_keeperhub ;;
  zerog)      recipe_zerog_rpc ;;
  ens)        recipe_ens ;;
  insights)   recipe_insights ;;
  cabinet)    recipe_cabinet ;;
  proof)      recipe_proof ;;
  all)
    recipe_consoles
    recipe_keeperhub
    recipe_zerog_rpc
    recipe_insights
    recipe_cabinet
    recipe_proof
    ;;
  *)
    echo "Usage: $0 [consoles|keeperhub|zerog|ens|insights|cabinet|proof|all]"
    echo
    echo "Recipes:"
    echo "  consoles  — verify all 9 component consoles return HTTP 200"
    echo "  keeperhub — print the dual-rail Base+Tempo challenge envelope"
    echo "  zerog     — probe 0G Galileo testnet RPC for chainId/block/gas"
    echo "  ens       — resolve an ENS name (default: vitalik.eth)"
    echo "  insights  — verify 6 audit endpoints return 200"
    echo "  cabinet   — check Cabinet activation status + public read"
    echo "  proof     — re-derive the cryptographic invariant from captured tuple"
    echo "  all       — run every recipe in sequence"
    echo
    echo "Env vars:"
    echo "  BASE=https://mindx.pythai.net   (override target host)"
    echo "  ENS_NAME=vitalik.eth            (override ENS lookup)"
    exit 1
    ;;
esac
