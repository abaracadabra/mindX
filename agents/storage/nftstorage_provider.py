"""
NFTStorageProvider — nft.storage / Storacha (web3.storage) IPFS adapter.

nft.storage transitioned to Storacha (the w3up protocol). For the offload
use-case we use the classic nft.storage HTTP API which is still available
and free for IPFS pinning (rate-limited).

API key from env NFTSTORAGE_API_KEY (loaded via BANKON Vault).

Endpoints:
- Upload:    POST https://api.nft.storage/upload
- Retrieve:  GET  https://nftstorage.link/ipfs/{cid}
- Status:    GET  https://api.nft.storage/{cid}

Bearer auth via Authorization header.
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

import aiohttp  # type: ignore[import-not-found]

from .provider import CID, IPFSProvider, ProviderError

UPLOAD_URL = "https://api.nft.storage/upload"
GATEWAY_URL = "https://nftstorage.link/ipfs/"
STATUS_URL = "https://api.nft.storage/"


class NFTStorageProvider(IPFSProvider):
    name = "nftstorage"

    def __init__(self, api_key: Optional[str] = None, session: Optional[aiohttp.ClientSession] = None):
        self.api_key = api_key or os.environ.get("NFTSTORAGE_API_KEY", "")
        if not self.api_key:
            raise ProviderError(self.name, 0, "NFTSTORAGE_API_KEY not set")
        self._session = session
        self._owns_session = session is None

    async def _sess(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60.0))
            self._owns_session = True
        return self._session

    @property
    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def upload(self, data: bytes, name: str) -> CID:
        sess = await self._sess()
        try:
            async with sess.post(
                UPLOAD_URL,
                headers={**self._auth_headers, "Content-Type": "application/octet-stream"},
                data=data,
            ) as resp:
                body = await resp.text()
                if resp.status != 200:
                    raise ProviderError(self.name, resp.status, body[:300])
                j = json.loads(body)
                if not j.get("ok"):
                    raise ProviderError(self.name, resp.status, body[:200])
                cid_str = j.get("value", {}).get("cid")
                if not cid_str:
                    raise ProviderError(self.name, resp.status, f"no cid in response: {body[:200]}")
                return CID(cid_str)
        except aiohttp.ClientError as e:
            raise ProviderError(self.name, 0, f"network error: {e}") from e

    async def retrieve(self, cid: CID, timeout: float = 5.0) -> bytes:
        sess = await self._sess()
        try:
            async with sess.get(GATEWAY_URL + cid.value, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status != 200:
                    raise ProviderError(self.name, resp.status, await resp.text())
                return await resp.read()
        except aiohttp.ClientError as e:
            raise ProviderError(self.name, 0, f"retrieve failed: {e}") from e

    async def pin(self, cid: CID) -> bool:
        # nft.storage pins automatically on upload. Status endpoint confirms.
        sess = await self._sess()
        try:
            async with sess.get(STATUS_URL + cid.value, headers=self._auth_headers) as resp:
                return resp.status == 200
        except aiohttp.ClientError:
            return False

    async def health(self) -> dict:
        sess = await self._sess()
        t0 = time.time()
        try:
            async with sess.get(GATEWAY_URL + "bafkqaaa", timeout=aiohttp.ClientTimeout(total=4.0)) as resp:
                return {
                    "provider": self.name,
                    "reachable": resp.status in (200, 404),
                    "latency_ms": int((time.time() - t0) * 1000),
                    "status": resp.status,
                }
        except Exception as e:
            return {"provider": self.name, "reachable": False, "error": str(e)[:160]}

    async def close(self) -> None:
        if self._owns_session and self._session is not None and not self._session.closed:
            await self._session.close()
