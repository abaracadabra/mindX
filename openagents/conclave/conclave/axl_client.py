"""Thin HTTP wrapper around the AXL local bridge at 127.0.0.1:9002.

AXL exposes the four endpoints we care about:

  GET  /topology
  POST /send                                  (header X-Destination-Peer-Id)
  GET  /recv                                  (returns 204 if empty)
  POST /mcp/{peer_id}/{service}               (JSON-RPC over MCP)
  POST /a2a/{peer_id}                         (JSON-RPC over A2A)

This module is deliberately minimal. Everything is synchronous httpx so
that examples remain readable; an asyncio variant is trivial if needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from .messages import Envelope


DEFAULT_BRIDGE = "http://127.0.0.1:9002"


@dataclass
class Topology:
    our_ipv6: str
    our_public_key: str
    peers: list[dict[str, Any]]
    tree: list[dict[str, Any]]


@dataclass
class InboundMessage:
    """Result of a /recv poll."""

    from_peer: str           # 0x-prefixed hex, value of X-From-Peer-Id
    data: bytes


class AXLClient:
    """Minimal client for the AXL local HTTP bridge."""

    def __init__(self, bridge: str = DEFAULT_BRIDGE, timeout: float = 30.0):
        self.bridge = bridge.rstrip("/")
        self._client = httpx.Client(base_url=self.bridge, timeout=timeout)

    # ----- transport primitives ----- #

    def topology(self) -> Topology:
        r = self._client.get("/topology")
        r.raise_for_status()
        d = r.json()
        return Topology(
            our_ipv6=d["our_ipv6"],
            our_public_key=d["our_public_key"],
            peers=list(d.get("peers", [])),
            tree=list(d.get("tree", [])),
        )

    def send(self, dest_peer_id: str, payload: bytes) -> int:
        """Fire-and-forget. Returns bytes accepted by the local node."""
        r = self._client.post(
            "/send",
            content=payload,
            headers={
                "X-Destination-Peer-Id": _strip_0x(dest_peer_id),
                "Content-Type": "application/octet-stream",
            },
        )
        r.raise_for_status()
        return int(r.headers.get("X-Sent-Bytes", "0"))

    def recv(self) -> InboundMessage | None:
        """Poll once. Returns None if the queue is empty (HTTP 204)."""
        r = self._client.get("/recv")
        if r.status_code == 204:
            return None
        r.raise_for_status()
        from_peer = r.headers.get("X-From-Peer-Id", "")
        return InboundMessage(from_peer=_with_0x(from_peer), data=r.content)

    # ----- structured calls ----- #

    def mcp(
        self,
        peer_id: str,
        service: str,
        method: str,
        params: dict[str, Any] | None = None,
        rpc_id: int = 1,
    ) -> dict[str, Any]:
        """JSON-RPC call into a remote peer's MCP service."""
        body = {
            "jsonrpc": "2.0",
            "method": method,
            "id": rpc_id,
            "params": params or {},
        }
        r = self._client.post(
            f"/mcp/{_strip_0x(peer_id)}/{service}",
            json=body,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        return r.json()

    def a2a(
        self,
        peer_id: str,
        text: str,
        message_id: str,
        rpc_id: int = 1,
    ) -> dict[str, Any]:
        """JSON-RPC `message/send` into a remote peer's A2A server.

        The `text` is whatever the peer's A2A server expects; for our
        protocol it's a JSON-stringified envelope. See CONCLAVE.md §6.
        """
        body = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "id": rpc_id,
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": text}],
                    "messageId": message_id,
                }
            },
        }
        r = self._client.post(
            f"/a2a/{_strip_0x(peer_id)}",
            json=body,
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        return r.json()

    # ----- conclave helper ----- #

    def send_envelope(self, env: Envelope, dest_peer_id: str) -> int:
        """Convenience: serialize an Envelope to canonical bytes and /send it."""
        return self.send(dest_peer_id, env.to_bytes())

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "AXLClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


# ----- helpers ----- #

def _strip_0x(s: str) -> str:
    return s[2:] if s.lower().startswith("0x") else s


def _with_0x(s: str) -> str:
    if not s:
        return s
    return s if s.lower().startswith("0x") else "0x" + s
