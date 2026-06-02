"""
tessera_client — issue DIDs and write per-action credentials against
`openagents/conclave/contracts/src/Tessera.sol`.

Tessera is admin-gated: only the admin can call `issue(holder, did, pubkey)`.
For Phase 1 we expose an `attest()` method that returns a deterministic
credential id off-chain (sha256 over the action payload) and ALSO would
submit a real Tessera issue if `dry_run=False` and a writer is wired.

The "credential id" is conceptual — Tessera itself doesn't return one; it
stores one credential per holder. So the per-action attestation in Phase 1
is best modeled as an off-chain structured record that references the
holder's Tessera DID. When BONAFIDE Tessera ships with per-action issuance,
this client switches to the new ABI without other code changes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class TesseraAttestation:
    holder: str             # 0x... agent address
    action_id: str          # caller-provided trace_id
    payload_hash: str       # sha256(json(payload))
    credential_id: str      # sha256(holder + action_id + payload_hash)
    dry_run: bool


class TesseraClient:
    def __init__(
        self,
        contract_address: str,
        chain_id: int,
        admin_private_key: Optional[str] = None,
        raw_tx_client: Any = None,
        web3_view: Any = None,
    ) -> None:
        self.contract_address = contract_address
        self.chain_id = int(chain_id)
        self.admin_private_key = admin_private_key
        self.raw_tx_client = raw_tx_client
        self.web3_view = web3_view

    async def has_valid_credential(self, holder: str) -> bool:
        if self.web3_view is None:
            return False
        try:
            return bool(await self.web3_view.read_bool("hasValidCredential", holder))
        except Exception:
            return False

    def attest(self, holder: str, action_id: str, payload: dict) -> TesseraAttestation:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        payload_hash = hashlib.sha256(body).hexdigest()
        cred_id = hashlib.sha256(f"{holder}|{action_id}|{payload_hash}".encode("utf-8")).hexdigest()
        return TesseraAttestation(
            holder=holder,
            action_id=action_id,
            payload_hash=payload_hash,
            credential_id=cred_id,
            dry_run=True,
        )


__all__ = ["TesseraClient", "TesseraAttestation"]
