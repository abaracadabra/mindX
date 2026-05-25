"""
BoardroomClient — Python client for the standalone boardroom-service.

After the Phase A–D scaffold, the boardroom lives as a Node.js service on
loopback port 8771. mindX no longer holds the consensus state in-process;
it talks to the service over HTTP and WebSocket.

This client:
  - Loads `mindx.boardroom.client:pk` from the BANKON vault (lazy).
  - Performs the EIP-191 challenge → sign → verify handshake to obtain
    a cabinet-tier session token.
  - Caches the token until it expires; re-handshakes transparently.
  - Exposes `convene_in_default_room(directive, ...)` and
    `convene_in_room(room_id, directive, ...)` — both return a Session
    dict identical in shape to what `daio/governance/boardroom.py:convene`
    used to return.

The `daio.governance.boardroom.Boardroom` Python class is patched in this
phase to become a thin shim that delegates to BoardroomClient, so the 25+
existing callers (CEOAgent, AuthorAgent, demo_agent, marketinga test,
main_service insight routes) need no source change.

Vault keys expected (operator must enroll before this client works):
  - mindx.boardroom.client:pk   — wallet private key (hex, with or without 0x)
  - mindx.boardroom.client:addr — derived address (optional; client derives on its own)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional

import aiohttp
from eth_account import Account
from eth_account.messages import encode_defunct

from utils.config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)

_DEFAULT_BASE_URL = "http://127.0.0.1:8771"
_DEFAULT_ROOM = "mindx-private-boardroom"
_SESSION_REFRESH_MARGIN_S = 300   # re-handshake when token has <5min left


class BoardroomClient:
    """Lazy singleton with vault-backed key + session caching."""

    _instance: Optional["BoardroomClient"] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls, config: Optional[Config] = None) -> "BoardroomClient":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(config=config)
            return cls._instance

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.base_url = os.environ.get("MINDX_BOARDROOM_URL", _DEFAULT_BASE_URL).rstrip("/")
        self.default_room = os.environ.get("MINDX_BOARDROOM_DEFAULT_ROOM", _DEFAULT_ROOM)
        self._private_key: Optional[str] = None
        self._address: Optional[str] = None
        self._session_token: Optional[str] = None
        self._session_exp: int = 0
        self._http: Optional[aiohttp.ClientSession] = None

    # ── Vault + identity ───────────────────────────────────────────

    def _load_private_key(self) -> str:
        if self._private_key:
            return self._private_key
        # Vault path — same pattern wordpress_agent uses (vault_creds.py).
        # For Phase E we fall back to env if vault isn't wired yet.
        env_key = os.environ.get("MINDX_BOARDROOM_CLIENT_PK")
        if env_key:
            self._private_key = env_key.removeprefix("0x")
            self._address = Account.from_key(self._private_key).address
            return self._private_key
        try:
            from mindx_backend_service.bankon_vault.vault import BankonVault
            vault = BankonVault()
            key = vault.get_credential("mindx.boardroom.client:pk")
            if key:
                self._private_key = key.removeprefix("0x")
                self._address = Account.from_key(self._private_key).address
                return self._private_key
        except Exception as e:
            logger.debug(f"BoardroomClient: vault read failed: {e}")
        raise RuntimeError(
            "BoardroomClient: no client key — set MINDX_BOARDROOM_CLIENT_PK env "
            "or enroll mindx.boardroom.client:pk in the BANKON vault."
        )

    @property
    def address(self) -> str:
        if not self._address:
            self._load_private_key()
        return self._address or ""

    # ── HTTP session ───────────────────────────────────────────────

    async def _ensure_http(self) -> aiohttp.ClientSession:
        if self._http is None or self._http.closed:
            self._http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600))
        return self._http

    async def close(self) -> None:
        if self._http and not self._http.closed:
            await self._http.close()
            self._http = None

    # ── Auth handshake ─────────────────────────────────────────────

    async def _handshake(self) -> str:
        """Run EIP-191 challenge/verify, return a fresh session token."""
        pk = self._load_private_key()
        addr = self.address
        http = await self._ensure_http()

        async with http.post(
            f"{self.base_url}/auth/challenge",
            json={"wallet": addr, "scope": "boardroom-service"},
        ) as r:
            r.raise_for_status()
            ch = await r.json()
        msg = ch["message"]
        signed = Account.sign_message(encode_defunct(text=msg), private_key=pk)
        sig_hex = "0x" + signed.signature.hex() if not signed.signature.hex().startswith("0x") else signed.signature.hex()

        async with http.post(
            f"{self.base_url}/auth/verify",
            json={"challenge_id": ch["challenge_id"], "signature": sig_hex},
        ) as r:
            if r.status != 200:
                body = await r.text()
                raise RuntimeError(f"BoardroomClient handshake failed: {r.status} {body[:200]}")
            v = await r.json()
        self._session_token = v["session_token"]
        self._session_exp = int(v["exp"])
        logger.info(
            f"BoardroomClient: session issued addr={addr} tier={v.get('tier')} "
            f"tier_name={v.get('tier_name')} exp_in={self._session_exp - int(time.time())}s"
        )
        return v["session_token"]

    async def _bearer(self) -> str:
        now = int(time.time())
        if not self._session_token or now + _SESSION_REFRESH_MARGIN_S >= self._session_exp:
            await self._handshake()
        return self._session_token or ""

    # ── Convene ────────────────────────────────────────────────────

    async def convene_in_default_room(
        self,
        directive: str,
        *,
        importance: str = "standard",
        context: Optional[str] = None,
        timeout: float = 300.0,
    ) -> Dict[str, Any]:
        return await self.convene_in_room(self.default_room, directive,
                                          importance=importance, context=context, timeout=timeout)

    async def convene_in_room(
        self,
        room_id: str,
        directive: str,
        *,
        importance: str = "standard",
        context: Optional[str] = None,
        timeout: float = 300.0,
    ) -> Dict[str, Any]:
        token = await self._bearer()
        http = await self._ensure_http()
        body: Dict[str, Any] = {"directive": directive, "importance": importance}
        if context is not None:
            body["context"] = context
        try:
            async with http.post(
                f"{self.base_url}/rooms/{room_id}/convene",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as r:
                if r.status == 401:
                    # Token may have expired between bearer check and call.
                    self._session_token = None
                    return await self.convene_in_room(room_id, directive,
                                                     importance=importance, context=context, timeout=timeout)
                if r.status != 200:
                    return {
                        "overall_campaign_status": "BOARDROOM_HTTP_ERROR",
                        "final_bdi_message": f"BoardroomClient: {r.status}",
                        "error": (await r.text())[:500],
                    }
                return await r.json()
        except asyncio.TimeoutError:
            return {
                "overall_campaign_status": "BOARDROOM_TIMEOUT",
                "final_bdi_message": "BoardroomClient: convene timed out",
            }
        except Exception as e:
            logger.warning(f"BoardroomClient.convene_in_room failed: {e}")
            return {
                "overall_campaign_status": "BOARDROOM_CLIENT_ERROR",
                "final_bdi_message": f"BoardroomClient exception: {type(e).__name__}",
                "error": str(e),
            }

    async def get_recent_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        http = await self._ensure_http()
        try:
            async with http.get(f"{self.base_url}/sessions/recent?limit={limit}") as r:
                if r.status != 200:
                    return []
                data = await r.json()
                return data.get("sessions", [])
        except Exception:
            return []

    async def health(self) -> Dict[str, Any]:
        http = await self._ensure_http()
        try:
            async with http.get(f"{self.base_url}/healthz", timeout=aiohttp.ClientTimeout(total=5)) as r:
                if r.status != 200:
                    return {"status": "unreachable", "code": r.status}
                return await r.json()
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}
