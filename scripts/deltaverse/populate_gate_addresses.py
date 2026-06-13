#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
populate_gate_addresses — copy a NeuralNode deploy receipt into
data/config/blockchain_addresses.json so DeltaVerseGate (POST /gate) goes live.

The deploy writes openagents/bankoneth/neuralnode/deployments/<chainId>/neuralnode.json
with keys matching the config (bubbleRoomV4, bubbleRoomSpawn, …). This merges those
addresses into blockchain_addresses.json["<chainId>"], replacing the 0x000…0
placeholders. Once bubbleRoomV4 + bubbleRoomSpawn are non-zero (and the wp-agent has
MINDX_DELTAVERSE_RPC_URL + MINDX_DELTAVERSE_SPAWNER_PK), the gate stops failing closed.

Usage:
  python scripts/deltaverse/populate_gate_addresses.py <chain_id> [--write]
Dry-run by default; pass --write to persist.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RECEIPT = os.path.join(ROOT, "openagents", "bankoneth", "neuralnode",
                       "deployments", "{chain_id}", "neuralnode.json")
CONFIG = os.path.join(ROOT, "data", "config", "blockchain_addresses.json")

# receipt key -> config key (identical here, but explicit for safety)
KEYS = [
    "bubbleRoomV4", "bubbleRoomSpawn", "deltaVerseOrchestrator", "deltaGenesisSBT",
    "emergenceTraits", "seedRegistry", "swarmGovernance", "tombRegistry",
]


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    chain_id = argv[0]
    write = "--write" in argv[1:]

    receipt_path = RECEIPT.format(chain_id=chain_id)
    if not os.path.exists(receipt_path):
        print(f"ERROR: no receipt at {receipt_path} — run the neuralnode deploy first.", file=sys.stderr)
        return 2
    with open(receipt_path, "r", encoding="utf-8") as fh:
        receipt = json.load(fh)

    with open(CONFIG, "r", encoding="utf-8") as fh:
        config = json.load(fh)
    section = dict(config.get(chain_id, {}))

    changed = {}
    for k in KEYS:
        addr = receipt.get(k)
        if addr and addr.lower() != "0x" + "0" * 40:
            if section.get(k) != addr:
                changed[k] = (section.get(k), addr)
            section[k] = addr
    if "_chain" not in section:
        section["_chain"] = f"chain-{chain_id}"
    config[chain_id] = section

    print(f"chain {chain_id}: {len(changed)} address(es) to update")
    for k, (old, new) in changed.items():
        print(f"  {k}: {old} -> {new}")
    gate_ready = section.get("bubbleRoomV4", "").lower() not in ("", "0x" + "0" * 40) and \
        section.get("bubbleRoomSpawn", "").lower() not in ("", "0x" + "0" * 40)
    print(f"  /gate will be LIVE on chain {chain_id}: {gate_ready} "
          f"(also needs MINDX_DELTAVERSE_RPC_URL + MINDX_DELTAVERSE_SPAWNER_PK)")

    if not write:
        print("DRY RUN — pass --write to persist.")
        return 0
    with open(CONFIG, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)
        fh.write("\n")
    print(f"WROTE {CONFIG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
