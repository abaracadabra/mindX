# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved.
"""
NeuralNode gate — DeltaVerse.gate.event → room + bubbleroom on Polygon.

A *gate event* (e.g. a wordpress.agent publication crossing the DeltaVerse
turnstile) creates two on-chain artifacts on the NeuralNode suite
(github.com/deltav-deltaverse/neuralnode):

  1. a **room**        — ``BubbleRoomV4.mintRoom(...)``  → roomId   (RoomCreated)
  2. a **bubbleroom**  — ``BubbleRoomSpawn.spawnFromRoom(originRoomId=roomId, ...)``
                          → emergenceId (RoomSpawned)

The spawned bubbleroom is the Origin→Emergence child of the room just minted, so
each gate event leaves a two-node lineage on chain.

Built on the existing minimal primitives — no web3.py:
  * ``agents.blockchain.abi_codec.encode_call`` / ``parse_event_uint``
  * ``agents.storage.raw_tx.RawTxClient`` (EIP-1559 sender)

FAILS CLOSED. ``open_gate`` broadcasts only when ALL of these resolve:
  * deployed ``bubbleRoomV4`` + ``bubbleRoomSpawn`` addresses for the chain
    (``data/config/blockchain_addresses.json`` → "<chain_id>"), non-zero;
  * an RPC URL (``MINDX_DELTAVERSE_RPC_URL`` / ``MINDX_POLYGON_RPC_URL``);
  * a spawner private key (``MINDX_DELTAVERSE_SPAWNER_PK``).
Otherwise it records a ``deltaverse.gate.event`` with ``status="blocked"`` and a
reason, and returns a non-fatal GateResult — never a partial broadcast.

NOTE: BubbleRoomV4 / BubbleRoomSpawn are NOT yet deployed to Polygon mainnet
(the neuralnode repo ships them tested with empty address placeholders). Deploy
them first via openBDK (agents/deployer + neuralnode/script/Deploy.s.sol), then
populate the "137" addresses below — the gate goes live the moment they exist.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

ADDRESSES_PATH = os.path.join(str(PROJECT_ROOT), "data", "config", "blockchain_addresses.json")
ZERO_ADDR = "0x0000000000000000000000000000000000000000"

# ── canonical NeuralNode signatures (from neuralnode/src/abis/*.json) ──────────
MINTROOM_SIG = (
    "mintRoom(string,string,string,address[],uint8[],bool,bool,bool,uint8,"
    "uint256,string,bool,string,string,bool)"
)
MINTROOM_TYPES: List[str] = [
    "string", "string", "string", "address[]", "uint8[]", "bool", "bool",
    "bool", "uint8", "uint256", "string", "bool", "string", "string", "bool",
]
SPAWN_SIG = (
    "spawnFromRoom(uint256,string,string,string,address[],uint8[],bool,uint8,"
    "string,string,bool)"
)
SPAWN_TYPES: List[str] = [
    "uint256", "string", "string", "string", "address[]", "uint8[]", "bool",
    "uint8", "string", "string", "bool",
]
# events — roomId is topic[1] of RoomCreated; emergenceId is topic[2] of RoomSpawned
ROOM_CREATED_SIG = "RoomCreated(uint256,string,uint8,address)"
ROOM_SPAWNED_SIG = "RoomSpawned(uint256,uint256,string,address)"

DEFAULT_CHAIN_ID = 137  # Polygon mainnet


class GateError(RuntimeError):
    pass


@dataclass
class GateSpec:
    """The DeltaVerse.gate.event payload → room/bubbleroom minting parameters.

    Sensible DeltaVerse defaults; a caller (e.g. wordpress.agent /gate) overrides
    ``metadata_uri``/``theme``/``origin_event`` per publication.
    """

    theme: str
    origin_event: str
    metadata_uri: str = ""
    participants: List[str] = field(default_factory=list)
    roles: List[int] = field(default_factory=list)
    is_private: bool = False
    is_stable: bool = False
    is_soulbound: bool = False
    room_type: int = 0
    unlock_time: int = 0
    storage_cid: str = ""
    is_encrypted_storage: bool = False
    ai_seed: str = "mindX"
    tone: str = "genesis"
    evolves: bool = True
    seed_mutation: str = "emergence"

    def mintroom_args(self) -> list:
        return [
            self.metadata_uri, self.theme, self.origin_event,
            [self._addr(a) for a in self.participants], list(self.roles),
            self.is_private, self.is_stable, self.is_soulbound, self.room_type,
            self.unlock_time, self.storage_cid, self.is_encrypted_storage,
            self.ai_seed, self.tone, self.evolves,
        ]

    def spawn_args(self, origin_room_id: int) -> list:
        return [
            origin_room_id, self.metadata_uri, self.theme, self.origin_event,
            [self._addr(a) for a in self.participants], list(self.roles),
            self.is_private, self.room_type, self.seed_mutation, self.tone,
            self.evolves,
        ]

    @staticmethod
    def _addr(a: str) -> str:
        from eth_utils import to_checksum_address  # type: ignore[import-not-found]

        return to_checksum_address(a)


@dataclass
class GateResult:
    ok: bool
    blocked: bool = False
    reason: Optional[str] = None
    chain_id: int = DEFAULT_CHAIN_ID
    room_id: Optional[int] = None
    bubbleroom_id: Optional[int] = None
    room_tx: Optional[str] = None
    bubbleroom_tx: Optional[str] = None
    spawner: Optional[str] = None
    links: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok, "blocked": self.blocked, "reason": self.reason,
            "chain_id": self.chain_id, "room_id": self.room_id,
            "bubbleroom_id": self.bubbleroom_id, "room_tx": self.room_tx,
            "bubbleroom_tx": self.bubbleroom_tx, "spawner": self.spawner,
            "links": self.links,
        }


class DeltaVerseGate:
    """Governed bridge from a gate event to a NeuralNode room + bubbleroom."""

    def __init__(self, chain_id: int = DEFAULT_CHAIN_ID):
        self.chain_id = chain_id

    # ── resolution / fails-closed checks ──────────────────────────────────
    @staticmethod
    def _load_addresses(chain_id: int) -> Dict[str, Any]:
        try:
            with open(ADDRESSES_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
        return data.get(str(chain_id), {}) or {}

    @staticmethod
    def _is_deployed(addr: Optional[str]) -> bool:
        return bool(addr) and isinstance(addr, str) and len(addr) == 42 \
            and addr.lower() != ZERO_ADDR.lower()

    @staticmethod
    def _rpc_url() -> Optional[str]:
        return os.environ.get("MINDX_DELTAVERSE_RPC_URL") \
            or os.environ.get("MINDX_POLYGON_RPC_URL")

    @staticmethod
    def _spawner_key() -> Optional[str]:
        # NO local-dev default — mainnet spawning must be explicitly keyed.
        return os.environ.get("MINDX_DELTAVERSE_SPAWNER_PK") or None

    def _resolve(self) -> tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Return (bubble_room, spawn, rpc, key, block_reason)."""
        addrs = self._load_addresses(self.chain_id)
        bubble_room = addrs.get("bubbleRoomV4")
        spawn = addrs.get("bubbleRoomSpawn")
        rpc = self._rpc_url()
        key = self._spawner_key()
        if not self._is_deployed(bubble_room):
            return bubble_room, spawn, rpc, key, (
                f"BubbleRoomV4 not deployed for chain {self.chain_id} "
                f"(blockchain_addresses.json). Deploy via openBDK first.")
        if not self._is_deployed(spawn):
            return bubble_room, spawn, rpc, key, (
                f"BubbleRoomSpawn not deployed for chain {self.chain_id}. "
                f"Deploy via openBDK first.")
        if not rpc:
            return bubble_room, spawn, rpc, key, (
                "no RPC (set MINDX_DELTAVERSE_RPC_URL / MINDX_POLYGON_RPC_URL)")
        if not key:
            return bubble_room, spawn, rpc, key, (
                "no spawner key (set MINDX_DELTAVERSE_SPAWNER_PK)")
        return bubble_room, spawn, rpc, key, None

    # ── main entry ────────────────────────────────────────────────────────
    async def open_gate(self, spec: GateSpec, *, actor: str = "deltaverse_gate",
                        actor_wallet: Optional[str] = None) -> GateResult:
        """Create a room then a bubbleroom spawned from it. Fails closed.

        Always emits a ``deltaverse.gate.event``; on success also emits
        ``deltaverse.room.created`` and ``deltaverse.bubbleroom.spawned``.
        Never raises for an operational/config failure — returns a GateResult
        with ``blocked=True`` and a reason.
        """
        bubble_room, spawn, rpc, key, reason = self._resolve()
        if reason is not None:
            logger.info("DeltaVerseGate: gate blocked — %s", reason)
            res = GateResult(ok=False, blocked=True, reason=reason, chain_id=self.chain_id)
            await self._emit("deltaverse.gate.event", {
                "status": "blocked", "reason": reason, "theme": spec.theme,
                "origin_event": spec.origin_event, "chain_id": self.chain_id,
            }, actor, actor_wallet)
            return res

        from agents.blockchain.abi_codec import encode_call, parse_event_uint
        from agents.storage.raw_tx import RawTxClient, RawTxError

        client = RawTxClient(rpc_url=rpc, chain_id=self.chain_id, private_key=key)  # type: ignore[arg-type]
        try:
            on_chain_cid = await client.get_chain_id()
            if on_chain_cid != self.chain_id:
                reason = f"RPC chainId {on_chain_cid} != expected {self.chain_id}"
                await self._emit("deltaverse.gate.event",
                                 {"status": "blocked", "reason": reason}, actor, actor_wallet)
                return GateResult(ok=False, blocked=True, reason=reason, chain_id=self.chain_id)

            spawner = client.address
            await self._emit("deltaverse.gate.event", {
                "status": "opening", "theme": spec.theme, "origin_event": spec.origin_event,
                "chain_id": self.chain_id, "spawner": spawner,
                "bubble_room": bubble_room, "spawn": spawn,
            }, actor, actor_wallet or spawner)

            # 1. room — mintRoom
            room_data = encode_call(MINTROOM_SIG, MINTROOM_TYPES, spec.mintroom_args())
            room_tx = await client.send_tx(to=bubble_room, data=room_data)  # type: ignore[arg-type]
            room_receipt = await client.wait_for_receipt(room_tx)
            room_id = parse_event_uint(room_receipt, ROOM_CREATED_SIG, 1)
            if room_id is None:
                raise GateError(f"room minted (tx {room_tx}) but no RoomCreated event found")
            links_room = self._links(bubble_room, room_id)  # type: ignore[arg-type]
            await self._emit("deltaverse.room.created", {
                "room_id": room_id, "tx_hash": room_tx, "chain_id": self.chain_id,
                "theme": spec.theme, "contract": bubble_room, "links": links_room,
            }, actor, actor_wallet or spawner)

            # 2. bubbleroom — spawnFromRoom(originRoomId=room_id)
            spawn_data = encode_call(SPAWN_SIG, SPAWN_TYPES, spec.spawn_args(room_id))
            bub_tx = await client.send_tx(to=spawn, data=spawn_data)  # type: ignore[arg-type]
            bub_receipt = await client.wait_for_receipt(bub_tx)
            bub_id = parse_event_uint(bub_receipt, ROOM_SPAWNED_SIG, 2)
            links_bub = self._links(bubble_room, bub_id) if bub_id is not None else {}
            await self._emit("deltaverse.bubbleroom.spawned", {
                "bubbleroom_id": bub_id, "origin_room_id": room_id, "tx_hash": bub_tx,
                "chain_id": self.chain_id, "seed_mutation": spec.seed_mutation,
                "contract": spawn, "links": links_bub,
            }, actor, actor_wallet or spawner)

            await self._emit("deltaverse.gate.event", {
                "status": "opened", "theme": spec.theme, "origin_event": spec.origin_event,
                "chain_id": self.chain_id, "spawner": spawner,
                "room_id": room_id, "bubbleroom_id": bub_id,
                "room_tx": room_tx, "bubbleroom_tx": bub_tx,
            }, actor, actor_wallet or spawner)

            return GateResult(
                ok=True, chain_id=self.chain_id, room_id=room_id, bubbleroom_id=bub_id,
                room_tx=room_tx, bubbleroom_tx=bub_tx, spawner=spawner,
                links={**links_room, **{f"bubbleroom_{k}": v for k, v in links_bub.items()}},
            )
        except (RawTxError, GateError) as e:
            reason = f"on-chain failure: {e}"
            logger.error("DeltaVerseGate: %s", reason)
            await self._emit("deltaverse.gate.event",
                             {"status": "failed", "reason": reason, "theme": spec.theme},
                             actor, actor_wallet)
            return GateResult(ok=False, blocked=False, reason=reason, chain_id=self.chain_id)
        finally:
            await client.close()

    # ── helpers ───────────────────────────────────────────────────────────
    def _links(self, contract: str, token_id: int) -> Dict[str, str]:
        if self.chain_id == 137:
            return {
                "opensea": f"https://opensea.io/item/polygon/{contract.lower()}/{token_id}",
                "polygonscan": f"https://polygonscan.com/token/{contract}?a={token_id}",
            }
        return {}

    async def _emit(self, kind: str, payload: Dict[str, Any], actor: str,
                    actor_wallet: Optional[str]) -> None:
        try:
            from agents.catalogue.events import emit_catalogue_event

            await emit_catalogue_event(
                kind, actor=actor, payload=payload,
                source_log="data/governance/deltaverse_gate",
                actor_wallet=actor_wallet)
        except Exception as e:  # catalogue is best-effort instrumentation
            logger.debug("DeltaVerseGate: catalogue emit skipped (%s): %s", kind, e)
