#!/usr/bin/env bash
# Bring up an 8-node Cabinet on the local host for development.
#
# Layout:
#   - One AXL node per role, on bridge ports 9002 / 9012 / .../ 9072
#     and listen ports 9001 / 9011 / .../ 9071 (CEO public, others peer to it).
#   - One soldier_node.py per role except CEO.
#   - Run examples/ceo_node.py separately to drive the demo.
#
# Requires:
#   - AXL binary at $AXL_BIN (default ./axl/node)
#   - openssl
#   - Python virtualenv with conclave installed

set -euo pipefail

AXL_BIN="${AXL_BIN:-./axl/node}"
KEYS_DIR="$(dirname "$0")/keys"
LOG_DIR="$(dirname "$0")/logs"
mkdir -p "$KEYS_DIR" "$LOG_DIR"

ROLES=(CEO COO CFO CTO CISO GC COS OPS)

# 1. Generate Ed25519 keys (one per role) if missing.
for ROLE in "${ROLES[@]}"; do
    PEM="$KEYS_DIR/$ROLE.pem"
    if [[ ! -f "$PEM" ]]; then
        echo "[$ROLE] generating Ed25519 key"
        openssl genpkey -algorithm ed25519 -out "$PEM"
    fi
done

# 2. Write per-role node configs.
write_config() {
    local ROLE="$1"; local IDX="$2"
    local PORT_LISTEN=$((9001 + IDX * 10))
    local PORT_BRIDGE=$((9002 + IDX * 10))
    local CFG="$KEYS_DIR/${ROLE}-config.json"
    if [[ "$ROLE" == "CEO" ]]; then
        # CEO is the public listener; everyone else peers to it.
        cat > "$CFG" <<EOF
{
  "PrivateKeyPath": "$KEYS_DIR/$ROLE.pem",
  "Peers": [],
  "Listen": ["tls://127.0.0.1:$PORT_LISTEN"],
  "AdminListen": null,
  "BridgeAddr": "127.0.0.1:$PORT_BRIDGE"
}
EOF
    else
        cat > "$CFG" <<EOF
{
  "PrivateKeyPath": "$KEYS_DIR/$ROLE.pem",
  "Peers": ["tls://127.0.0.1:9001"],
  "Listen": [],
  "AdminListen": null,
  "BridgeAddr": "127.0.0.1:$PORT_BRIDGE"
}
EOF
    fi
}

# 3. Start AXL nodes.
PIDS=()
for IDX in "${!ROLES[@]}"; do
    ROLE="${ROLES[$IDX]}"
    write_config "$ROLE" "$IDX"
    CFG="$KEYS_DIR/${ROLE}-config.json"
    LOG="$LOG_DIR/axl-$ROLE.log"
    echo "[$ROLE] starting AXL with $CFG -> $LOG"
    "$AXL_BIN" -config "$CFG" >>"$LOG" 2>&1 &
    PIDS+=($!)
done

trap 'echo; echo "stopping..."; kill ${PIDS[@]} 2>/dev/null || true' EXIT INT TERM

# 4. Wait briefly for the mesh to converge.
sleep 3

# 5. Start counsellor agents (everyone except CEO).
AGENT_PIDS=()
for ROLE in "${ROLES[@]:1}"; do
    LOG="$LOG_DIR/agent-$ROLE.log"
    echo "[$ROLE] starting soldier_node -> $LOG"
    python examples/soldier_node.py --role "$ROLE" --disposition yea \
        >>"$LOG" 2>&1 &
    AGENT_PIDS+=($!)
done

PIDS+=("${AGENT_PIDS[@]}")

echo
echo "========================================================="
echo "Cabinet up. To convene a session, run in another terminal:"
echo "  python examples/ceo_node.py --title 'Q3 M&A Review'"
echo "Logs: $LOG_DIR/"
echo "Press Ctrl-C to stop."
echo "========================================================="
wait
