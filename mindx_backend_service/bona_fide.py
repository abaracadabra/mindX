# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""bona_fide — .algo (and .eth) MEMBER resolution via the BONA FIDE reputation token.

The OVERSEER governs agent reputation on .algo: holding **BONA FIDE** IS privilege.
The OVERSEER mints it to grant and CLAWS IT BACK to revoke — so **NO TOKEN FOUND
= ACCESS DENIED**. This is the .algo counterpart to the .eth token/subname gate.

BONA FIDE ships as:
  - Algorand ASA — minted by `BonaFideDeployer`, governed by `BonafideController`
    (clawback/reserve). Membership = holding the ASA with amount > 0.
  - EVM ERC-20 — `daio/contracts/agenticplace/evm/BonaFide.sol` (clawback + ghosting),
    for the .eth side.

Day 0: BONA FIDE is not yet deployed, so the identifiers are **anticipated** — set
by env when the OVERSEER mints them. Until then the check returns False (NO TOKEN
FOUND → not a member → ACCESS DENIED), which is the correct fail-closed default:
membership is never granted on an unverifiable/absent token.

  MINDX_BONAFIDE_ASA_ID        Algorand ASA id (int) — anticipated, set on deploy
  MINDX_BONAFIDE_EVM_ADDRESS   EVM BonaFide ERC-20 address — anticipated, set on deploy
  MINDX_ALGO_INDEXER_URL       Algorand indexer (default: public algonode)
"""
from __future__ import annotations

import os
import logging
from typing import Optional

logger = logging.getLogger("mindx.bona_fide")

# Anticipated identifiers — activate the moment the OVERSEER deploys BONA FIDE.
def bonafide_asa_id() -> Optional[int]:
    raw = (os.environ.get("MINDX_BONAFIDE_ASA_ID") or "").strip()
    try:
        return int(raw) if raw else None
    except ValueError:
        return None


def bonafide_evm_address() -> Optional[str]:
    a = (os.environ.get("MINDX_BONAFIDE_EVM_ADDRESS") or "").strip()
    return a.lower() or None


def _indexer_url() -> str:
    return (os.environ.get("MINDX_ALGO_INDEXER_URL")
            or "https://mainnet-idx.algonode.cloud").rstrip("/")


async def holds_bona_fide_algo(address: str) -> bool:
    """True iff ``address`` holds the BONA FIDE ASA with amount > 0 on Algorand.

    Fail-CLOSED: an unset ASA id (not yet deployed) or any indexer error returns
    False — membership is never granted on an absent/unverifiable token
    (NO TOKEN FOUND = ACCESS DENIED). Read-only; no algosdk dependency.
    """
    asa = bonafide_asa_id()
    if not asa or not address:
        return False   # anticipated / awaiting deployment → not a member yet
    try:
        import httpx
    except ImportError:  # pragma: no cover
        return False
    url = f"{_indexer_url()}/v2/accounts/{address.strip().upper()}/assets"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url, params={"asset-id": asa})
        if r.status_code >= 400:
            return False
        for a in (r.json() or {}).get("assets", []):
            if int(a.get("asset-id", 0)) == asa and int(a.get("amount", 0)) > 0 and not a.get("deleted"):
                return True
    except Exception as e:  # network/parse — fail closed
        logger.debug(f"holds_bona_fide_algo({address[:8]}…): {e}")
    return False


async def resolve_algo_tier(address: str, *, is_overseer: bool) -> str:
    """Resolve an Algorand identity's realm tier:
    OVERSEER (mindx.algo) → overseer; holds BONA FIDE → member; else participant.
    """
    if is_overseer:
        return "overseer"
    if await holds_bona_fide_algo(address):
        return "member"
    return "participant"
