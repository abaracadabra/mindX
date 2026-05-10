"""
inft_mint_client — mint iNFT_7857 per agent.

One mint per (orchestrator + 5 sub-agents) = 6 mints. Operator-gated;
dry-run by default. The mint payload references the agent's Tessera DID
and the agent's ENS subname, so a future viewer can resolve the mint
back to a real on-chain identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class MintPayload:
    agent_address: str
    did: str
    ens_subname: str
    metadata_uri: str             # ipfs:// or https://


@dataclass
class MintResult:
    payload: MintPayload
    token_id: Optional[int]
    tx_hash: Optional[str]
    dry_run: bool
    error: Optional[str] = None


class INFT7857Client:
    def __init__(
        self,
        contract_address: str,
        chain_id: int,
        raw_tx_client: Any = None,
    ) -> None:
        self.contract_address = contract_address
        self.chain_id = int(chain_id)
        self.raw_tx_client = raw_tx_client

    async def mint(self, payload: MintPayload, *, dry_run: bool = True) -> MintResult:
        return MintResult(
            payload=payload,
            token_id=None,
            tx_hash=None,
            dry_run=True if dry_run else False,
            error=None if dry_run else "live mint not implemented in Phase 1",
        )


__all__ = ["INFT7857Client", "MintPayload", "MintResult"]
