"""slash.py — submit a `Conclave.slashForLeak` transaction.

In a real deployment the convener (or any conclave-monitor agent)
would notice a transcript leak in the wild and submit the on-chain
slash. The proof bytes are the canonical CBOR encoding of the leaked
transcript; the signatures inside it bind the leak to a specific peer
key, which the contract resolves to the seated address via the
membership table.

Usage:

    export RPC_URL=http://localhost:8545
    export CONCLAVE_ADDR=0x...
    export CONVENER_PRIVKEY=0x...
    python demos/slash.py \\
        --conclave-id 0x...01 \\
        --session-id  0x... \\
        --leaker      0xCOO_ADDR \\
        --proof       /tmp/leaked-transcript.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from web3 import Web3
    from eth_account import Account
except ImportError:  # pragma: no cover
    print("install web3: pip install 'conclave[chain]'", file=sys.stderr)
    raise SystemExit(2)

from conclave.chain import CONCLAVE_ABI


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--conclave-id", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--leaker", required=True,
                        help="EVM address of the suspected leaker.")
    parser.add_argument("--proof", required=True,
                        help="Path to leaked-transcript.json (from leak.py).")
    args = parser.parse_args()

    rpc = os.environ.get("RPC_URL", "http://localhost:8545")
    addr = os.environ.get("CONCLAVE_ADDR")
    pk = os.environ.get("CONVENER_PRIVKEY")
    if not addr or not pk:
        print("CONCLAVE_ADDR and CONVENER_PRIVKEY must be set", file=sys.stderr)
        raise SystemExit(2)

    w3 = Web3(Web3.HTTPProvider(rpc))
    acct = Account.from_key(pk)
    contract = w3.eth.contract(address=addr, abi=CONCLAVE_ABI)

    proof_bytes = Path(args.proof).read_bytes()  # raw JSON for v0.1
    print(f"submitting slashForLeak: {len(proof_bytes)} byte proof")

    tx = contract.functions.slashForLeak(
        bytes.fromhex(args.conclave_id.removeprefix("0x")),
        bytes.fromhex(args.session_id.removeprefix("0x")),
        Web3.to_checksum_address(args.leaker),
        proof_bytes,
    ).build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address),
        "gas": 400_000,
        "gasPrice": w3.eth.gas_price,
    })

    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(signed.rawTransaction)
    receipt = w3.eth.wait_for_transaction_receipt(h)
    print(json.dumps({
        "tx_hash": h.hex(),
        "status": receipt.status,
        "gas_used": receipt.gasUsed,
        "events": [e["event"] for e in contract.events.MemberSlashed().process_receipt(receipt)],
    }, indent=2))


if __name__ == "__main__":
    main()
