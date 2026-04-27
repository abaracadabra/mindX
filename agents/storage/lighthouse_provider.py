"""
LighthouseProvider — Lighthouse Storage (https://lighthouse.storage) adapter.

Lighthouse pins to Filecoin under the hood; pricing is one-time
($0.15/GB/year-equivalent), making it the cheapest durable IPFS pin.
Free tier covers initial backfill of small batches.

API key from env LIGHTHOUSE_API_KEY (loaded via BANKON Vault on boot).

Endpoints:
- Upload:    POST https://node.lighthouse.storage/api/v0/add
- Retrieve:  GET  https://gateway.lighthouse.storage/ipfs/{cid}
- Pin info:  GET  https://api.lighthouse.storage/api/lighthouse/file_info?cid={cid}

Note: upload is multipart form-data with Authorization: Bearer <key>.
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

import aiohttp  # type: ignore[import-not-found]

from .provider import CID, IPFSProvider, ProviderError

UPLOAD_URL = "https://node.lighthouse.storage/api/v0/add"
GATEWAY_URL = "https://gateway.lighthouse.storage/ipfs/"
INFO_URL = "https://api.lighthouse.storage/api/lighthouse/file_info"


class LighthouseProvider(IPFSProvider):
    name = "lighthouse"

    def __init__(self, api_key: Optional[str] = None, session: Optional[aiohttp.ClientSession] = None):
        self.api_key = api_key or os.environ.get("LIGHTHOUSE_API_KEY", "")
        if not self.api_key:
            raise ProviderError(self.name, 0, "LIGHTHOUSE_API_KEY not set")
        self._session = session
        self._owns_session = session is None

    async def _sess(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60.0)
            )
            self._owns_session = True
        return self._session

    @property
    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def upload(self, data: bytes, name: str) -> CID:
        sess = await self._sess()
        form = aiohttp.FormData()
        form.add_field("file", data, filename=name, content_type="application/octet-stream")
        try:
            async with sess.post(UPLOAD_URL, headers=self._auth_headers, data=form) as resp:
                body = await resp.text()
                if resp.status != 200:
                    raise ProviderError(self.name, resp.status, body[:300])
                # Response is one JSON line: {"Name":..,"Hash":"bafy…","Size":..}
                # Some Lighthouse responses wrap; handle both.
                try:
                    j = json.loads(body)
                except json.JSONDecodeError:
                    # Sometimes ndjson: take last non-empty line
                    lines = [l for l in body.strip().splitlines() if l.strip()]
                    if not lines:
                        raise ProviderError(self.name, resp.status, "empty response")
                    j = json.loads(lines[-1])
                cid_str = j.get("Hash") or j.get("cid") or j.get("data", {}).get("Hash")
                if not cid_str:
                    raise ProviderError(self.name, resp.status, f"no CID in response: {body[:200]}")
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
        # Lighthouse pins on upload automatically; this is a no-op idempotent
        # confirmation that the CID is known to the service.
        sess = await self._sess()
        try:
            async with sess.get(INFO_URL, params={"cid": cid.value}, headers=self._auth_headers) as resp:
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
                    "reachable": resp.status in (200, 404),  # 404 = gateway up but CID not present
                    "latency_ms": int((time.time() - t0) * 1000),
                    "status": resp.status,
                }
        except Exception as e:
            return {"provider": self.name, "reachable": False, "error": str(e)[:160]}

    async def close(self) -> None:
        if self._owns_session and self._session is not None and not self._session.closed:
            await self._session.close()
