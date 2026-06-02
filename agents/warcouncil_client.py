"""
WarcouncilClient — Python client for mastermind.pythai.net's war-council.

The war-council is a peer service, NOT a mindX subsystem. mindX is an
external client from the war-council's perspective; it must sign each
request with an EIP-191 envelope that the war-council's
`src/clients/mindx_envelope.ts` validates.

Envelope shape (matches warcouncil-service/src/clients/mindx_envelope.ts):

  X-MindX-Signer:    0x<40 hex>
  X-MindX-Nonce:     <16 bytes hex>
  X-MindX-Timestamp: <unix seconds>
  X-MindX-Signature: EIP-191 sig of canonical preimage

The war-council, if it ever calls back to mindX, signs with its own
mastermind.warcouncil.client key — mindX's reciprocal verifier lives in
`mindx_backend_service/main_service.py` warcouncil callback routes.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import secrets
import time
from typing import Any, Dict, Optional

import aiohttp
from eth_account import Account
from eth_account.messages import encode_defunct

from utils.config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)

_DEFAULT_BASE_URL = "https://warcouncil.mastermind.pythai.net"
# When running locally on the same VPS, the operator can override:
#   MINDX_WARCOUNCIL_URL=http://127.0.0.1:8773
_DEFAULT_DOMAIN = "warcouncil.mastermind.pythai.net"


class WarcouncilClient:
    """Stateless per-call envelope signer."""

    _instance: Optional["WarcouncilClient"] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls, config: Optional[Config] = None) -> "WarcouncilClient":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config=config)
            return cls._instance

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.base_url = os.environ.get("MINDX_WARCOUNCIL_URL", _DEFAULT_BASE_URL).rstrip("/")
        self.domain = os.environ.get("MINDX_WARCOUNCIL_DOMAIN", _DEFAULT_DOMAIN)
        self._private_key: Optional[str] = None
        self._address: Optional[str] = None
        self._http: Optional[aiohttp.ClientSession] = None

    def _load_private_key(self) -> str:
        if self._private_key:
            return self._private_key
        env_key = os.environ.get("MINDX_WARCOUNCIL_CLIENT_PK")
        if env_key:
            self._private_key = env_key.removeprefix("0x")
            self._address = Account.from_key(self._private_key).address
            return self._private_key
        try:
            from mindx_backend_service.bankon_vault.vault import BankonVault
            vault = BankonVault()
            key = vault.get_credential("mindx.warcouncil.client:pk")
            if key:
                self._private_key = key.removeprefix("0x")
                self._address = Account.from_key(self._private_key).address
                return self._private_key
        except Exception as e:
            logger.debug(f"WarcouncilClient: vault read failed: {e}")
        raise RuntimeError(
            "WarcouncilClient: no client key — set MINDX_WARCOUNCIL_CLIENT_PK env "
            "or enroll mindx.warcouncil.client:pk in the BANKON vault."
        )

    @property
    def address(self) -> str:
        if not self._address:
            self._load_private_key()
        return self._address or ""

    async def _ensure_http(self) -> aiohttp.ClientSession:
        if self._http is None or self._http.closed:
            self._http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60))
        return self._http

    async def close(self) -> None:
        if self._http and not self._http.closed:
            await self._http.close()
            self._http = None

    def _build_envelope(self, method: str, path: str, body_bytes: bytes) -> Dict[str, str]:
        pk = self._load_private_key()
        addr = self.address
        nonce = secrets.token_hex(16)
        ts = int(time.time())
        body_hash = hashlib.sha256(body_bytes).hexdigest()
        msg = (
            f"mindX→warcouncil envelope v1\n"
            f"domain: {self.domain}\n"
            f"method: {method}\n"
            f"path: {path}\n"
            f"nonce: {nonce}\n"
            f"timestamp: {ts}\n"
            f"body_sha256: {body_hash}\n"
        )
        signed = Account.sign_message(encode_defunct(text=msg), private_key=pk)
        sig_hex = signed.signature.hex()
        if not sig_hex.startswith("0x"):
            sig_hex = "0x" + sig_hex
        return {
            "X-MindX-Signer": addr,
            "X-MindX-Nonce": nonce,
            "X-MindX-Timestamp": str(ts),
            "X-MindX-Signature": sig_hex,
            "Content-Type": "application/json",
        }

    async def consult(self, directive: str, *, context: Optional[str] = None,
                      timeout: float = 30.0) -> Dict[str, Any]:
        """Ask the war-council for a non-binding strategic read on a directive.

        Returns whatever the war-council answers. On rejection (401 envelope
        invalid, rate limit, etc.) returns a minimal error dict — we don't
        get told why, by design.
        """
        body: Dict[str, Any] = {"directive": directive}
        if context is not None:
            body["context"] = context
        import json as _json
        body_bytes = _json.dumps(body).encode("utf-8")
        path = "/mindx/consult"
        headers = self._build_envelope("POST", path, body_bytes)
        http = await self._ensure_http()
        try:
            async with http.post(f"{self.base_url}{path}", data=body_bytes, headers=headers,
                                 timeout=aiohttp.ClientTimeout(total=timeout)) as r:
                text = await r.text()
                if r.status == 200:
                    try:
                        return _json.loads(text)
                    except Exception:
                        return {"status": "ok", "raw": text[:500]}
                return {"status": "rejected", "code": r.status, "detail": text[:200]}
        except asyncio.TimeoutError:
            return {"status": "timeout"}
        except Exception as e:
            logger.warning(f"WarcouncilClient.consult failed: {e}")
            return {"status": "client_error", "error": str(e)}

    async def health(self) -> Dict[str, Any]:
        """Probe /healthz — unauthenticated public endpoint."""
        http = await self._ensure_http()
        try:
            async with http.get(f"{self.base_url}/healthz",
                                timeout=aiohttp.ClientTimeout(total=5)) as r:
                if r.status != 200:
                    return {"status": "unreachable", "code": r.status}
                return await r.json()
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}
