"""
censura_client — read agent reputation, decide if faded.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class CensuraVerdict:
    score: int
    floor: int
    faded: bool


class CensuraClient:
    def __init__(
        self,
        contract_address: str,
        chain_id: int,
        floor: int = 50,
        web3_view: Any = None,
    ) -> None:
        self.contract_address = contract_address
        self.chain_id = int(chain_id)
        self.floor = int(floor)
        self.web3_view = web3_view

    async def evaluate(self, address: str) -> CensuraVerdict:
        if self.web3_view is None:
            return CensuraVerdict(score=255, floor=self.floor, faded=False)
        try:
            score = int(await self.web3_view.read_uint("score", address))
        except Exception:
            score = 0
        return CensuraVerdict(score=score, floor=self.floor, faded=score < self.floor)


__all__ = ["CensuraClient", "CensuraVerdict"]
