"""
ZeroGProvider — 0G Storage adapter for mindX.

0G Storage uses merkle-root content addressing (0x-prefixed 32-byte hex),
NOT IPFS CIDs. Roots are deterministic: identical bytes produce the
identical root, regardless of who uploads.

mindX is Python; 0G's only first-party SDKs are Go and TypeScript. This
adapter proxies a Node sidecar at http://127.0.0.1:7878 (see
openagents/sidecar/index.ts). Run the sidecar before this provider:

    cd openagents/sidecar
    npm install
    ZEROG_PRIVATE_KEY=0x... node --experimental-strip-types index.ts &

This provider stands alongside (not inside) the IPFSProvider hierarchy
because its address type differs. It exposes the same conceptual surface
(upload/retrieve/health) so callers can fan out to all storage paths.

Used by:
- openagents/demo_agent.py            — uploads encrypted iNFT payloads
- openagents/keeperhub/bridge_routes  — anchors paid-workflow proofs (optional)
"""

from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass
from typing import Optional

import aiohttp  # type: ignore[import-not-found]

from utils.logging_config import get_logger

logger = get_logger(__name__)


_ROOT_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")


@dataclass(frozen=True, slots=True)
class ZGRoot:
    """Validated 0G Storage merkle root (0x-prefixed 32-byte hex)."""

    value: str

    def __post_init__(self) -> None:
        v = self.value.strip()
        if not _ROOT_RE.match(v):
            raise ValueError(f"Not a valid 0G root hash: {v!r}")
        object.__setattr__(self, "value", v.lower())

    def __str__(self) -> str:
        return self.value

    @property
    def uri(self) -> str:
        return f"0g://galileo/{self.value}"


class ZeroGProviderError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(f"[zerog] HTTP {status}: {message}")
        self.status = status
        self.message = message


class ZeroGProvider:
    """Async client for the 0G Storage Node sidecar."""

    name = "zerog"

    def __init__(
        self,
        sidecar_url: Optional[str] = None,
        timeout_s: float = 60.0,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        self.sidecar_url = (
            sidecar_url
            or os.environ.get("ZEROG_SIDECAR_URL")
            or "http://127.0.0.1:7878"
        ).rstrip("/")
        self.timeout_s = timeout_s
        self._session = session
        self._owns_session = session is None

    async def _sess(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout_s)
            )
            self._owns_session = True
        return self._session

    async def upload(self, data: bytes, name: str = "blob") -> tuple[ZGRoot, Optional[str]]:
        """Upload bytes to 0G Storage. Returns (root, tx_hash). tx_hash is
        None when the upload deduped to existing storage."""
        sess = await self._sess()
        form = aiohttp.FormData()
        form.add_field("file", data, filename=name, content_type="application/octet-stream")
        try:
            async with sess.post(f"{self.sidecar_url}/upload", data=form) as resp:
                body = await resp.json()
                if resp.status != 200 or not body.get("ok"):
                    raise ZeroGProviderError(resp.status, body.get("error", "upload failed"))
                return ZGRoot(body["rootHash"]), body.get("txHash")
        except aiohttp.ClientError as e:
            raise ZeroGProviderError(0, f"network error: {e}") from e

    async def retrieve(self, root: ZGRoot, timeout: float = 10.0) -> bytes:
        """Fetch bytes for a merkle root from 0G Storage."""
        sess = await self._sess()
        try:
            async with sess.get(
                f"{self.sidecar_url}/retrieve/{root.value}",
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status == 404:
                    raise ZeroGProviderError(404, f"root {root.value} not found")
                if resp.status != 200:
                    txt = await resp.text()
                    raise ZeroGProviderError(resp.status, txt[:300])
                return await resp.read()
        except aiohttp.ClientError as e:
            raise ZeroGProviderError(0, f"network error: {e}") from e

    async def health(self) -> dict:
        sess = await self._sess()
        try:
            async with sess.get(
                f"{self.sidecar_url}/health",
                timeout=aiohttp.ClientTimeout(total=5.0),
            ) as resp:
                if resp.status != 200:
                    return {"provider": self.name, "reachable": False, "status": resp.status}
                body = await resp.json()
                return {
                    "provider": self.name,
                    "reachable": bool(body.get("ok")),
                    "rpc": body.get("rpc"),
                    "block_number": body.get("blockNumber"),
                    "signer": body.get("signer"),
                    "balance": body.get("balance"),
                    "sidecar_uptime_s": body.get("uptime_s"),
                }
        except aiohttp.ClientError as e:
            return {"provider": self.name, "reachable": False, "error": str(e)}

    async def close(self) -> None:
        if self._owns_session and self._session and not self._session.closed:
            await self._session.close()
