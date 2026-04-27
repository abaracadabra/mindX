"""
On-chain anchoring of memory CIDs.

Two tiers:
- **everyday tier (ARC DatasetRegistry)** — permissionless registerDataset(bytes32,string).
  Every offload batch lands here.
- **curated tier (THOT)** — owner-gated mintTHOT(...). Only memories that
  pass through LTM consolidation and represent durable distilled knowledge.
  Phase C ships THOT as a no-op stub when no owner key is configured.

Anchor receipts are emitted as `memory.anchor` catalogue events.
"""

from __future__ import annotations

import hashlib
import os
from typing import Optional

from eth_utils import to_checksum_address  # type: ignore[import-not-found]

from utils.logging_config import get_logger

from .raw_tx import RawTxClient, RawTxError

logger = get_logger(__name__)

# Function selector for registerDataset(bytes32,string)
# keccak256("registerDataset(bytes32,string)")[:4] = 0x  --- computed once below
# We compute it lazily to avoid an import-time keccak in cold paths; cache result.
_REGISTER_DATASET_SELECTOR: Optional[bytes] = None


def _selector(signature: str) -> bytes:
    """Compute a 4-byte function selector via keccak256."""
    from Crypto.Hash import keccak  # type: ignore[import-not-found]
    k = keccak.new(digest_bits=256)
    k.update(signature.encode("utf-8"))
    return k.digest()[:4]


def _register_dataset_selector() -> bytes:
    global _REGISTER_DATASET_SELECTOR
    if _REGISTER_DATASET_SELECTOR is None:
        try:
            _REGISTER_DATASET_SELECTOR = _selector("registerDataset(bytes32,string)")
        except Exception:
            # Fallback: hardcoded value computed offline.
            # keccak256("registerDataset(bytes32,string)")[:4] = 0xf1783fb8
            _REGISTER_DATASET_SELECTOR = bytes.fromhex("f1783fb8")
    return _REGISTER_DATASET_SELECTOR


def _encode_register_dataset(dataset_id: bytes, root_cid: str) -> str:
    """ABI-encode calldata for registerDataset(bytes32,string)."""
    if len(dataset_id) != 32:
        raise ValueError("dataset_id must be 32 bytes")
    selector = _register_dataset_selector()
    # Layout: selector || dataset_id (32B) || offset_to_string (32B = 0x40) ||
    #         string_length (32B) || string_bytes_padded
    cid_bytes = root_cid.encode("utf-8")
    pad_len = (32 - (len(cid_bytes) % 32)) % 32
    encoded = (
        selector
        + dataset_id
        + (0x40).to_bytes(32, "big")
        + len(cid_bytes).to_bytes(32, "big")
        + cid_bytes
        + (b"\x00" * pad_len)
    )
    return "0x" + encoded.hex()


def derive_dataset_id(agent_id: str, date_str: str, cid: str) -> bytes:
    """Stable bytes32 dataset id for a given (agent, date, CID) triple."""
    h = hashlib.sha256(f"{agent_id}|{date_str}|{cid}".encode("utf-8")).digest()
    return h  # already 32 bytes


class AnchorClient:
    """
    Wraps a RawTxClient with mindX-specific anchor methods.

    Configure either with explicit args or via env:
      ARC_RPC_URL, ARC_CHAIN_ID, ARC_REGISTRY_ADDRESS, MEMORY_ANCHOR_TREASURY_PK
    """

    def __init__(
        self,
        *,
        rpc_url: Optional[str] = None,
        chain_id: Optional[int] = None,
        registry_address: Optional[str] = None,
        private_key: Optional[str] = None,
    ):
        self.rpc_url = rpc_url or os.environ.get("ARC_RPC_URL", "")
        self.chain_id = chain_id or int(os.environ.get("ARC_CHAIN_ID", "0") or 0)
        self.registry_address = registry_address or os.environ.get("ARC_REGISTRY_ADDRESS", "")
        self.private_key = private_key or os.environ.get("MEMORY_ANCHOR_TREASURY_PK", "")
        self._client: Optional[RawTxClient] = None

    @property
    def configured(self) -> bool:
        return bool(self.rpc_url and self.chain_id and self.registry_address and self.private_key)

    async def _ensure_client(self) -> RawTxClient:
        if self._client is None:
            if not self.configured:
                raise RawTxError(
                    "AnchorClient not configured: need ARC_RPC_URL, ARC_CHAIN_ID, "
                    "ARC_REGISTRY_ADDRESS, MEMORY_ANCHOR_TREASURY_PK"
                )
            self._client = RawTxClient(
                rpc_url=self.rpc_url,
                chain_id=self.chain_id,
                private_key=self.private_key,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()

    async def anchor_dataset_registry(
        self, *, agent_id: str, date_str: str, cid: str,
    ) -> dict:
        """
        Register the (agent_id, date_str, cid) tuple on the ARC DatasetRegistry.
        Returns receipt dict {tx_hash, dataset_id_hex, status} or {error} on failure.
        """
        client = await self._ensure_client()
        dataset_id = derive_dataset_id(agent_id, date_str, cid)
        try:
            data = _encode_register_dataset(dataset_id, cid)
            tx_hash = await client.send_tx(
                to=to_checksum_address(self.registry_address),
                data=data,
            )
            return {
                "tx_hash": tx_hash,
                "dataset_id_hex": "0x" + dataset_id.hex(),
                "chain": "arc",
                "registry": self.registry_address,
            }
        except RawTxError as e:
            return {"error": str(e), "chain": "arc"}

    async def anchor_thot(
        self, *, agent_id: str, batch_cid: str, dimensions: int = 768,
    ) -> dict:
        """
        Mint a THOT for a curated memory CID. Owner-gated; without mint key
        configured this returns an explicit not-configured stub.

        The full implementation is out of Phase C scope until access policy is
        decided (deploy permissive variant vs. centralized minter). Tracked in
        the plan as "THOT mint at scale" deferred work.
        """
        if not os.environ.get("THOT_MINTER_KEY"):
            return {
                "stub": True,
                "agent_id": agent_id,
                "batch_cid": batch_cid,
                "dimensions": dimensions,
                "note": "THOT mint disabled — set THOT_MINTER_KEY to enable",
            }
        # Reserved for the Phase 2 permissive-mint deploy.
        return {
            "stub": True,
            "note": "THOT mint owner-gated; permissive contract deploy pending",
        }
