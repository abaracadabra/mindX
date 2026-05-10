"""
x402_receipt_client — thin wrapper around existing x402 clients for
marketing-tagged payments.

Reuses `tools/keeperhub_x402_client.py` (EVM USDC on Base) and
`tools/x402_avm_client.py` (Algorand AVM USDC) at runtime; this module
exposes the marketing-side adapter so calls are tagged by `campaignId`
for downstream join with `MarketingAttributionReceipt`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class X402PaymentResult:
    campaign_id: str
    resource_url: str
    amount_micro_usd: int
    receipt_hash: Optional[str]
    chain_kind: str             # "evm" | "avm"
    chain_id: int
    error: Optional[str] = None


class X402ReceiptClient:
    """Adapter — accepts an injected x402 sender and tags by campaign_id."""

    def __init__(self, x402_sender: Any = None) -> None:
        self.x402_sender = x402_sender

    async def pay(
        self,
        campaign_id: str,
        resource_url: str,
        amount_micro_usd: int,
        *,
        chain_kind: str = "evm",
        chain_id: int = 8453,
    ) -> X402PaymentResult:
        if self.x402_sender is None:
            return X402PaymentResult(
                campaign_id=campaign_id,
                resource_url=resource_url,
                amount_micro_usd=amount_micro_usd,
                receipt_hash=None,
                chain_kind=chain_kind,
                chain_id=chain_id,
                error="no x402_sender injected",
            )
        try:
            send_fn = getattr(self.x402_sender, "pay", None) or getattr(self.x402_sender, "send", None)
            if send_fn is None:
                raise AttributeError("x402_sender missing .pay/.send")
            outcome = send_fn(
                resource_url=resource_url,
                amount_micro_usd=amount_micro_usd,
                metadata={"campaign_id": campaign_id},
            )
            if hasattr(outcome, "__await__"):
                outcome = await outcome
            receipt_hash = None
            if isinstance(outcome, dict):
                receipt_hash = outcome.get("receipt_hash") or outcome.get("receiptHash")
            return X402PaymentResult(
                campaign_id=campaign_id,
                resource_url=resource_url,
                amount_micro_usd=amount_micro_usd,
                receipt_hash=str(receipt_hash) if receipt_hash else None,
                chain_kind=chain_kind,
                chain_id=chain_id,
            )
        except Exception as exc:
            return X402PaymentResult(
                campaign_id=campaign_id,
                resource_url=resource_url,
                amount_micro_usd=amount_micro_usd,
                receipt_hash=None,
                chain_kind=chain_kind,
                chain_id=chain_id,
                error=repr(exc),
            )


__all__ = ["X402ReceiptClient", "X402PaymentResult"]
