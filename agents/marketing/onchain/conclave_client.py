"""
conclave_client — post session anchors when above-threshold proposals are
decided.

Phase 1: this client sketches the call shape but defers actual submission
to the operator after Conclave deployment. The real Conclave session API
takes (conclaveId, sessionId, motionId, resolutionHash, ...) — we emit a
catalogue event that mirrors that shape so the migration is mechanical.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class SessionAnchor:
    conclave_id: bytes      # bytes32
    session_id: bytes       # bytes32
    motion_id: bytes        # bytes32
    resolution_hash: bytes  # bytes32
    dry_run: bool


def derive_session_anchor(campaign_id: str, decision: str) -> SessionAnchor:
    """Pure derivation. Same inputs → same anchor; useful for tests + replay."""
    cid = hashlib.sha256(f"campaign:{campaign_id}".encode("utf-8")).digest()
    sid = hashlib.sha256(f"session:{campaign_id}".encode("utf-8")).digest()
    mid = hashlib.sha256(f"motion:{campaign_id}:{decision}".encode("utf-8")).digest()
    rsh = hashlib.sha256(f"resolution:{campaign_id}:{decision}".encode("utf-8")).digest()
    return SessionAnchor(
        conclave_id=cid,
        session_id=sid,
        motion_id=mid,
        resolution_hash=rsh,
        dry_run=True,
    )


class ConclaveClient:
    def __init__(
        self,
        contract_address: str,
        chain_id: int,
        raw_tx_client: Any = None,
    ) -> None:
        self.contract_address = contract_address
        self.chain_id = int(chain_id)
        self.raw_tx_client = raw_tx_client

    async def anchor_session(self, campaign_id: str, decision: str) -> SessionAnchor:
        return derive_session_anchor(campaign_id, decision)


__all__ = ["ConclaveClient", "SessionAnchor", "derive_session_anchor"]
