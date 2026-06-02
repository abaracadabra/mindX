"""
marketing_treasury_client — read state + (operator-gated) trigger buybacks.

Phase 1: read-only is the default. Buyback execution is gated behind an
explicit `dry_run=False` from the operator + a Censura check.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class TreasurySnapshot:
    contract_address: str
    chain_id: int
    total_revenue: int
    total_bought_back: int
    total_burned: int
    total_to_foundation: int


class MarketingTreasuryClient:
    def __init__(
        self,
        contract_address: str,
        chain_id: int,
        web3_view: Any = None,
        raw_tx_client: Any = None,
    ) -> None:
        self.contract_address = contract_address
        self.chain_id = int(chain_id)
        self.web3_view = web3_view
        self.raw_tx_client = raw_tx_client

    async def snapshot(self) -> Optional[TreasurySnapshot]:
        if self.web3_view is None:
            return None
        try:
            r = await self.web3_view.read_uint("totalRevenue")
            b = await self.web3_view.read_uint("totalBoughtBack")
            d = await self.web3_view.read_uint("totalBurned")
            f = await self.web3_view.read_uint("totalToFoundation")
        except Exception:
            return None
        return TreasurySnapshot(
            contract_address=self.contract_address,
            chain_id=self.chain_id,
            total_revenue=int(r or 0),
            total_bought_back=int(b or 0),
            total_burned=int(d or 0),
            total_to_foundation=int(f or 0),
        )

    async def revenue_for_campaign(self, campaign_id: bytes) -> int:
        if self.web3_view is None:
            return 0
        try:
            return int(await self.web3_view.read_uint("revenueByCampaign", campaign_id))
        except Exception:
            return 0


__all__ = ["MarketingTreasuryClient", "TreasurySnapshot"]
