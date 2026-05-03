#!/usr/bin/env bash
# Regenerate all 12 flattened contracts. Run from anywhere.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
DAIO="$REPO_ROOT/daio/contracts"
CONCLAVE="$REPO_ROOT/openagents/conclave/contracts"
OUT="$DAIO/flattened"

mkdir -p "$OUT/group-a" "$OUT/group-a-conclave" "$OUT/bankon"

# Group A — daio/contracts (per-profile)
cd "$DAIO"
echo "→ Group A (daio/contracts)"
FOUNDRY_PROFILE=agentregistry forge flatten agentregistry/AgentRegistry.sol > "$OUT/group-a/AgentRegistry.flat.sol"
FOUNDRY_PROFILE=thot          forge flatten THOT/v1/THOT.sol            > "$OUT/group-a/THOT.flat.sol"
FOUNDRY_PROFILE=inft          forge flatten inft/iNFT_7857.sol          > "$OUT/group-a/iNFT_7857.flat.sol"
FOUNDRY_PROFILE=default       forge flatten arc/DatasetRegistry.sol     > "$OUT/group-a/DatasetRegistry.flat.sol"

# Group A — openagents/conclave (default profile)
cd "$CONCLAVE"
echo "→ Group A (conclave)"
for c in Tessera Censura Conclave ConclaveBond; do
  forge flatten "src/$c.sol" > "$OUT/group-a-conclave/$c.flat.sol"
done

# Group B — BANKON v1
cd "$DAIO"
echo "→ Group B (BANKON)"
for c in BankonPriceOracle BankonReputationGate BankonPaymentRouter BankonSubnameRegistrar; do
  FOUNDRY_PROFILE=bankon forge flatten "ens/v1/$c.sol" > "$OUT/bankon/$c.flat.sol"
done

echo
echo "✓ regenerated 12 flattened contracts at $OUT"
ls "$OUT"/*/
