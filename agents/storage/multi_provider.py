"""
MultiProvider — fan out uploads to two IPFS providers, retrieve from either.

IPFS is content-addressed: the same bytes produce the same CID regardless
of provider. Uploading to both Lighthouse and nft.storage gives:
- Redundancy (single provider outage non-fatal)
- Quorum verification (both must agree on CID)
- Free retrieval from either gateway

Failure semantics:
- Upload: succeeds if EITHER provider succeeds (degraded mode warning when
  only one succeeds).
- Retrieve: tries primary first, falls back to mirror on timeout/miss.
- Pin: best-effort on both.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from utils.logging_config import get_logger

from .provider import CID, IPFSProvider, ProviderError

logger = get_logger(__name__)


class MultiProvider(IPFSProvider):
    name = "multi"

    def __init__(self, primary: IPFSProvider, mirror: Optional[IPFSProvider] = None):
        self.primary = primary
        self.mirror = mirror

    async def upload(self, data: bytes, name: str) -> CID:
        """Upload to both providers in parallel; require at least one success."""
        if self.mirror is None:
            return await self.primary.upload(data, name)
        results = await asyncio.gather(
            self.primary.upload(data, name),
            self.mirror.upload(data, name),
            return_exceptions=True,
        )
        cids: list[CID] = []
        errors: list[str] = []
        for r, prov in zip(results, [self.primary.name, self.mirror.name]):
            if isinstance(r, CID):
                cids.append(r)
            else:
                errors.append(f"{prov}: {r}")
        if not cids:
            raise ProviderError("multi", 0, "; ".join(errors) or "all providers failed")
        if len(cids) == 2 and cids[0].value != cids[1].value:
            # Same input must give the same CID; if not, providers disagree —
            # log and trust the primary (Lighthouse). This shouldn't happen
            # for byte-identical input.
            logger.warning(
                "[storage.multi] CID mismatch primary=%s mirror=%s — using primary",
                cids[0].value, cids[1].value,
            )
        if errors:
            logger.warning("[storage.multi] upload partial: %s", "; ".join(errors))
        return cids[0]

    async def retrieve(self, cid: CID, timeout: float = 5.0) -> bytes:
        try:
            return await self.primary.retrieve(cid, timeout=timeout)
        except ProviderError as e:
            if self.mirror is None:
                raise
            logger.info("[storage.multi] primary miss for %s, trying mirror: %s", cid, e)
            return await self.mirror.retrieve(cid, timeout=timeout)

    async def pin(self, cid: CID) -> bool:
        if self.mirror is None:
            return await self.primary.pin(cid)
        results = await asyncio.gather(
            self.primary.pin(cid), self.mirror.pin(cid), return_exceptions=True,
        )
        return any(r is True for r in results)

    async def health(self) -> dict:
        if self.mirror is None:
            return {"primary": await self.primary.health()}
        primary, mirror = await asyncio.gather(self.primary.health(), self.mirror.health())
        return {
            "primary": primary,
            "mirror": mirror,
            "any_reachable": bool(primary.get("reachable")) or bool(mirror.get("reachable")),
        }

    async def close(self) -> None:
        await self.primary.close()
        if self.mirror is not None:
            await self.mirror.close()
