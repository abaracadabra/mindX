"""
IPFSProvider — abstract base for content-addressed offload backends.

Concrete implementations: LighthouseProvider, NFTStorageProvider, MultiProvider.

Design rules:
- Content-addressed: callers pass bytes, get back a CID; providers must agree
  on the same CID for the same content (IPFS guarantees this when the same
  hash function and chunking is used).
- Async-only: every provider method is awaitable. No blocking IO.
- Failures are typed, not silent. ProviderError carries provider name +
  HTTP status + message. Callers decide retry policy.
- No keys in logs. Authorization headers redacted on log.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


_CID_V1_RE = re.compile(r"^bafy[a-z2-7]{55,}$")
_CID_V0_RE = re.compile(r"^Qm[1-9A-HJ-NP-Za-km-z]{44}$")


@dataclass(frozen=True, slots=True)
class CID:
    """Validated IPFS content identifier (v0 'Qm…' or v1 'bafy…')."""

    value: str

    def __post_init__(self) -> None:
        v = self.value.strip()
        if not v:
            raise ValueError("CID cannot be empty")
        if not (_CID_V0_RE.match(v) or _CID_V1_RE.match(v)):
            raise ValueError(f"Not a valid IPFS CID: {v!r}")
        # frozen dataclass: bypass to normalize
        object.__setattr__(self, "value", v)

    def __str__(self) -> str:
        return self.value

    @property
    def is_v1(self) -> bool:
        return self.value.startswith("bafy")


class ProviderError(RuntimeError):
    """Raised when an IPFS provider request fails."""

    def __init__(self, provider: str, status: int, message: str):
        super().__init__(f"[{provider}] HTTP {status}: {message}")
        self.provider = provider
        self.status = status
        self.message = message


class IPFSProvider(ABC):
    """Abstract async IPFS gateway/pin service adapter."""

    name: str = "abstract"

    @abstractmethod
    async def upload(self, data: bytes, name: str) -> CID:
        """Upload bytes; return the resulting CID. May pin transparently."""

    @abstractmethod
    async def retrieve(self, cid: CID, timeout: float = 5.0) -> bytes:
        """Fetch content for the CID. Raises ProviderError on miss/timeout."""

    @abstractmethod
    async def pin(self, cid: CID) -> bool:
        """Ensure the CID is pinned. Idempotent. Returns True on success."""

    @abstractmethod
    async def health(self) -> dict:
        """Cheap probe: returns {provider, reachable, latency_ms} or similar."""

    async def close(self) -> None:
        """Optional teardown for HTTP sessions etc. Default: no-op."""
        return None
