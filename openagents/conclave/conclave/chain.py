"""On-chain bindings.

Thin wrappers around `Conclave.sol`, `Tessera`, `Censura`, and
`ConclaveBond` using web3.py. Designed so the Python protocol can:

  - Pre-flight a manifest (verify all members are gated)
  - Anchor a Resolution after the conclave reaches quorum
  - Submit a slash proof if a member leaks

Algorand bindings (for the x402/Algorand stake path) live in a sibling
module that we will add when wiring `parsec-wallet` in.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable

log = logging.getLogger("conclave.chain")


# Minimal ABIs — enough to call the methods we use. The full ABIs live
# in `contracts/out/` after `forge build`; we don't bundle them here so
# that the Python package doesn't need a Solidity toolchain installed.

CONCLAVE_ABI: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "registerConclave",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "conclave_id", "type": "bytes32"},
            {"name": "members", "type": "address[]"},
            {"name": "pubkeys", "type": "bytes32[]"},
            {"name": "roles", "type": "uint8[]"},
            {"name": "censura_min", "type": "uint8"},
            {"name": "bond_per_member", "type": "uint256"},
        ],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "isMemberSeated",
        "stateMutability": "view",
        "inputs": [
            {"name": "conclave_id", "type": "bytes32"},
            {"name": "member", "type": "address"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
    },
    {
        "type": "function",
        "name": "recordResolution",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "conclave_id", "type": "bytes32"},
            {"name": "session_id", "type": "bytes32"},
            {"name": "motion_id", "type": "bytes32"},
            {"name": "resolution_hash", "type": "bytes32"},
            {"name": "voters", "type": "address[]"},
            {"name": "outcome_passed", "type": "bool"},
        ],
        "outputs": [],
    },
    {
        "type": "function",
        "name": "slashForLeak",
        "stateMutability": "nonpayable",
        "inputs": [
            {"name": "conclave_id", "type": "bytes32"},
            {"name": "session_id", "type": "bytes32"},
            {"name": "leaker", "type": "address"},
            {"name": "leak_proof", "type": "bytes"},
        ],
        "outputs": [],
    },
]


@dataclass
class ConclaveChain:
    """Convenience facade. Pass a connected `web3.Web3` and the deployed addr."""

    w3: Any                    # web3.Web3
    conclave_addr: str
    sender: str                # tx.from
    private_key: str | None = None  # for signing if not using a local node

    def _contract(self) -> Any:
        return self.w3.eth.contract(address=self.conclave_addr, abi=CONCLAVE_ABI)

    def _send(self, fn: Any) -> str:
        if self.private_key is None:
            tx_hash = fn.transact({"from": self.sender})
            return tx_hash.hex()
        # Offline signing path.
        nonce = self.w3.eth.get_transaction_count(self.sender)
        tx = fn.build_transaction({
            "from": self.sender,
            "nonce": nonce,
            "gas": 500_000,
            "maxFeePerGas": self.w3.eth.gas_price,
            "maxPriorityFeePerGas": self.w3.eth.gas_price,
        })
        signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
        return self.w3.eth.send_raw_transaction(signed.rawTransaction).hex()

    # ---- preflight ---- #

    def verify_member_seated(self, conclave_id: bytes, member_addr: str) -> bool:
        c = self._contract()
        return bool(c.functions.isMemberSeated(conclave_id, member_addr).call())

    def verify_all_seated(self, conclave_id: bytes,
                          members: Iterable[str]) -> list[str]:
        """Returns the list of members NOT seated. Empty == all good."""
        bad: list[str] = []
        for addr in members:
            if not self.verify_member_seated(conclave_id, addr):
                bad.append(addr)
        return bad

    # ---- anchor ---- #

    def record_resolution(
        self,
        conclave_id: bytes,
        session_id: bytes,
        motion_id: bytes,
        resolution_hash: bytes,
        voters: list[str],
        outcome_passed: bool,
    ) -> str:
        fn = self._contract().functions.recordResolution(
            conclave_id, session_id, motion_id, resolution_hash,
            voters, outcome_passed,
        )
        return self._send(fn)

    # ---- slash ---- #

    def slash_for_leak(
        self,
        conclave_id: bytes,
        session_id: bytes,
        leaker: str,
        leak_proof: bytes,
    ) -> str:
        fn = self._contract().functions.slashForLeak(
            conclave_id, session_id, leaker, leak_proof,
        )
        return self._send(fn)
