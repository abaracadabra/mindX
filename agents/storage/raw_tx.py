"""
Minimal raw EIP-1559 transaction sender.

Built on `eth_account` (already a dep via IDManagerAgent) plus aiohttp
JSON-RPC calls — same shape as `mindx_backend_service/access_gate.py` but
write-side. No `web3.py` dependency.

Designed for the memory-anchor use case: tiny calldata, single-shot tx,
not for high-frequency DEX trading or anything latency-sensitive.

Plan: ~/.claude/plans/whispering-floating-merkle.md
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Optional

import aiohttp  # type: ignore[import-not-found]
from eth_account import Account  # type: ignore[import-not-found]

from utils.logging_config import get_logger

logger = get_logger(__name__)


class RawTxError(RuntimeError):
    """JSON-RPC failure or transaction submission error."""


class RawTxClient:
    """
    Minimal EIP-1559 sender.

    Methods are async wrappers over JSON-RPC eth_* calls. On any HTTP/RPC
    error a RawTxError is raised; callers decide retry policy.
    """

    def __init__(
        self,
        rpc_url: str,
        chain_id: int,
        private_key: str,
        session: Optional[aiohttp.ClientSession] = None,
    ):
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.account = Account.from_key(private_key)
        self.address = self.account.address
        self._session = session
        self._owns_session = session is None

    async def _sess(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30.0)
            )
            self._owns_session = True
        return self._session

    async def close(self) -> None:
        if self._owns_session and self._session is not None and not self._session.closed:
            await self._session.close()

    async def _rpc(self, method: str, params: list[Any]) -> Any:
        sess = await self._sess()
        payload = {"jsonrpc": "2.0", "id": int(time.time() * 1000), "method": method, "params": params}
        try:
            async with sess.post(self.rpc_url, json=payload) as resp:
                if resp.status != 200:
                    raise RawTxError(f"RPC HTTP {resp.status}: {await resp.text()}")
                data = await resp.json()
        except aiohttp.ClientError as e:
            raise RawTxError(f"RPC network error: {e}") from e
        if "error" in data:
            raise RawTxError(f"RPC {method} error: {data['error']}")
        return data.get("result")

    async def get_nonce(self, address: Optional[str] = None) -> int:
        addr = address or self.address
        result = await self._rpc("eth_getTransactionCount", [addr, "pending"])
        return int(result, 16)

    async def get_chain_id(self) -> int:
        result = await self._rpc("eth_chainId", [])
        return int(result, 16)

    async def get_max_fees(self) -> tuple[int, int]:
        """Return (max_fee_per_gas, max_priority_fee_per_gas) in wei."""
        gas_price_hex = await self._rpc("eth_gasPrice", [])
        base = int(gas_price_hex, 16)
        priority = max(1_000_000_000, base // 10)  # 1 gwei or base/10
        max_fee = base * 2 + priority
        return max_fee, priority

    async def estimate_gas(self, to: str, data: str, value: int = 0) -> int:
        params = [{"from": self.address, "to": to, "data": data, "value": hex(value)}]
        try:
            result = await self._rpc("eth_estimateGas", params)
            return int(result, 16)
        except RawTxError as e:
            logger.debug(f"estimate_gas failed (using fallback 200_000): {e}")
            return 200_000

    async def send_tx(
        self,
        *,
        to: str,
        data: str = "0x",
        value: int = 0,
        gas_limit: Optional[int] = None,
        nonce: Optional[int] = None,
    ) -> str:
        """
        Sign and broadcast a transaction. Returns the tx_hash hex string.

        Raises RawTxError on any JSON-RPC failure.
        """
        if nonce is None:
            nonce = await self.get_nonce()
        if gas_limit is None:
            gas_limit = await self.estimate_gas(to, data, value=value)
        max_fee, priority = await self.get_max_fees()
        tx = {
            "type": 2,
            "chainId": self.chain_id,
            "nonce": nonce,
            "to": to,
            "value": value,
            "gas": int(gas_limit * 12 // 10),  # 20% headroom
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": priority,
            "data": data,
        }
        signed = self.account.sign_transaction(tx)
        raw_hex = "0x" + signed.raw_transaction.hex() if hasattr(signed, "raw_transaction") else signed.rawTransaction.hex()
        if not raw_hex.startswith("0x"):
            raw_hex = "0x" + raw_hex
        tx_hash = await self._rpc("eth_sendRawTransaction", [raw_hex])
        return tx_hash

    async def wait_for_receipt(self, tx_hash: str, timeout: float = 120.0, poll: float = 4.0) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                receipt = await self._rpc("eth_getTransactionReceipt", [tx_hash])
                if receipt is not None:
                    return receipt
            except RawTxError:
                pass
            await asyncio.sleep(poll)
        raise RawTxError(f"timeout waiting for receipt: {tx_hash}")
