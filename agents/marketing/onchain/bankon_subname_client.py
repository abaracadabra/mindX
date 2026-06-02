"""
bankon_subname_client — register `marketinga.bankon.eth` + child subnames.

Wraps the existing `BankonSubnameRegistrar.sol` (956 LOC, tested) in
`daio/contracts/ens/v1/`. Phase 1 dry-run by default.

Existing helpers in `openagents/ens/agent_mint_service.py` and
`openagents/ens/subdomain_issuer.py` should be reused for the actual
EIP-712 voucher pattern; this module exposes the marketing-specific
parent + child subname plan. We delegate the live submission to whichever
of those modules the operator configures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class SubnamePlan:
    parent: str                       # "marketinga.bankon.eth"
    children: List[str] = field(default_factory=list)  # full FQDNs
    dry_run: bool = True


class BankonSubnameClient:
    DEFAULT_PARENT = "marketinga.bankon.eth"
    DEFAULT_CHILDREN = (
        "content.marketinga.bankon.eth",
        "experimentation.marketinga.bankon.eth",
        "distribution.marketinga.bankon.eth",
        "reporting.marketinga.bankon.eth",
        "governance.marketinga.bankon.eth",
    )

    def __init__(
        self,
        registrar_address: str,
        chain_id: int,
        raw_tx_client: Any = None,
        ens_helper: Any = None,
    ) -> None:
        self.registrar_address = registrar_address
        self.chain_id = int(chain_id)
        self.raw_tx_client = raw_tx_client
        self.ens_helper = ens_helper

    def plan(
        self,
        parent: Optional[str] = None,
        children: Optional[List[str]] = None,
    ) -> SubnamePlan:
        return SubnamePlan(
            parent=parent or self.DEFAULT_PARENT,
            children=list(children) if children else list(self.DEFAULT_CHILDREN),
            dry_run=True,
        )


__all__ = ["BankonSubnameClient", "SubnamePlan"]
