"""
agent_registry_client — register marketinga + sub-agents in AgentRegistry
(ERC-8004) with capability bitmaps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional


# Capability bits — kept stable as an enum-like int since AgentRegistry
# accepts a uint256 bitmap. Document each bit precisely; never reuse a bit.
CAP_ORCHESTRATE         = 1 << 0
CAP_DRAFT_CONTENT       = 1 << 1
CAP_EXPERIMENT          = 1 << 2
CAP_DISTRIBUTE          = 1 << 3
CAP_REPORT              = 1 << 4
CAP_GOVERN              = 1 << 5
CAP_ATTEST_CAMPAIGN     = 1 << 6
CAP_ROUTE_GOVERNANCE    = 1 << 7


@dataclass
class AgentRegistration:
    agent_address: str
    ens_subname: str
    capability_bitmap: int
    dry_run: bool
    tx_hash: Optional[str] = None


class AgentRegistryClient:
    def __init__(
        self,
        contract_address: str,
        chain_id: int,
        raw_tx_client: Any = None,
    ) -> None:
        self.contract_address = contract_address
        self.chain_id = int(chain_id)
        self.raw_tx_client = raw_tx_client

    async def register(
        self,
        agent_address: str,
        ens_subname: str,
        capabilities: List[int],
        *,
        dry_run: bool = True,
    ) -> AgentRegistration:
        bitmap = 0
        for c in capabilities:
            bitmap |= int(c)
        return AgentRegistration(
            agent_address=agent_address,
            ens_subname=ens_subname,
            capability_bitmap=bitmap,
            dry_run=dry_run,
        )


__all__ = [
    "AgentRegistryClient",
    "AgentRegistration",
    "CAP_ORCHESTRATE",
    "CAP_DRAFT_CONTENT",
    "CAP_EXPERIMENT",
    "CAP_DISTRIBUTE",
    "CAP_REPORT",
    "CAP_GOVERN",
    "CAP_ATTEST_CAMPAIGN",
    "CAP_ROUTE_GOVERNANCE",
]
