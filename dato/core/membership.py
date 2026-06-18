# Copyright 2026 BANKON. All rights reserved.
# Licensed under the Apache License, Version 2.0.
"""dato request-to-join — fee + settings, settled over the existing x402 rails.

A participant requests to join a dato (and thereby the DAIO umbrella the dato
belongs to). If the dato sets a ``join_fee_microusd``, admission requires a
settled x402 payment on the ``/dato/join`` endpoint (priced in
``data/config/x402_pricing.json``); the settlement receipt id is recorded on the
member. Free/open datos admit directly. Per-member settings are stored on the
:class:`~dato.core.model.Member`.

This is the join *logic* + fee accounting; the actual on-the-wire settlement is
performed by mindX's x402 middleware when ``/dato/join`` is hit (the EVM analogue
is ``dato/contracts/DatoMembership.sol`` via TreasuryFeeCollector).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from dato.core.dato_process import DatoError, DatoRegistry
from dato.core.model import Member

JOIN_ENDPOINT = "/dato/join"


class JoinFeeRequired(DatoError):
    """Raised when a paid dato is joined without a settled fee receipt."""

    def __init__(self, dato_id: str, fee_microusd: int):
        self.dato_id = dato_id
        self.fee_microusd = fee_microusd
        super().__init__(
            f"dato {dato_id} requires a {fee_microusd} microUSD join fee settled on "
            f"{JOIN_ENDPOINT} (present the x402 receipt as fee_tx)"
        )


def quote_join(reg: DatoRegistry, dato_id: str) -> Dict[str, Any]:
    """Return the join quote: fee + the x402 endpoint to settle it on."""
    inst = reg._require(dato_id)  # noqa: SLF001 - internal accessor by design
    fee = int(inst.settings.join_fee_microusd or 0)
    return {
        "dato_id": dato_id,
        "name": inst.name,
        "owner_daio": inst.owner_daio,
        "fee_microusd": fee,
        "x402_endpoint": JOIN_ENDPOINT,
        "open_join": inst.settings.open_join,
        "free": fee == 0,
    }


def join(
    reg: DatoRegistry,
    dato_id: str,
    wallet: str,
    *,
    settings: Optional[Dict[str, Any]] = None,
    fee_tx: Optional[str] = None,
    fee_paid_microusd: int = 0,
) -> Member:
    """Admit ``wallet`` to the dato, enforcing the join fee when set.

    - Free/open dato (fee == 0) → admit directly.
    - Paid dato → require a settled x402 receipt (``fee_tx``) covering the fee.
    Per-member ``settings`` are stored on the member record.
    """
    quote = quote_join(reg, dato_id)
    fee = quote["fee_microusd"]
    if fee > 0:
        if not fee_tx or fee_paid_microusd < fee:
            raise JoinFeeRequired(dato_id, fee)
    return reg.request_join(
        dato_id, wallet,
        fee_paid_microusd=max(fee, fee_paid_microusd),
        fee_tx=fee_tx, settings=settings,
    )


__all__ = ["JOIN_ENDPOINT", "JoinFeeRequired", "quote_join", "join"]
