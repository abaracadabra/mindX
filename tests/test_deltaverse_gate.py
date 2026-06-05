# SPDX-License-Identifier: Apache-2.0
"""Tests for the DeltaVerse NeuralNode gate (agents/deltaverse)."""
import pytest

from agents.catalogue.events import EVENT_KINDS
from agents.blockchain.abi_codec import encode_call, selector
from agents.deltaverse.neuralnode_gate import (
    DeltaVerseGate, GateSpec, MINTROOM_SIG, MINTROOM_TYPES, SPAWN_SIG, SPAWN_TYPES,
)


def test_event_kinds_registered():
    for k in ("deltaverse.gate.event", "deltaverse.room.created", "deltaverse.bubbleroom.spawned"):
        assert k in EVENT_KINDS


def test_arg_counts_match_signatures():
    spec = GateSpec(theme="t", origin_event="publication:x")
    assert len(spec.mintroom_args()) == len(MINTROOM_TYPES) == 15
    assert len(spec.spawn_args(1)) == len(SPAWN_TYPES) == 11


def test_calldata_encodes_with_correct_selector():
    spec = GateSpec(theme="DeltaVerse", origin_event="publication:apt-part-1",
                    metadata_uri="https://rage.pythai.net/x")
    room = encode_call(MINTROOM_SIG, MINTROOM_TYPES, spec.mintroom_args())
    assert room.startswith("0x" + selector(MINTROOM_SIG).hex())
    bub = encode_call(SPAWN_SIG, SPAWN_TYPES, spec.spawn_args(7))
    assert bub.startswith("0x" + selector(SPAWN_SIG).hex())
    # spawn's first arg (originRoomId=7) is encoded in the first 32-byte word
    assert int(bub[10:74], 16) == 7


@pytest.mark.asyncio
async def test_gate_fails_closed_when_not_deployed(monkeypatch):
    # zero addresses in config → gate must refuse to broadcast
    monkeypatch.setenv("MINDX_DELTAVERSE_RPC_URL", "http://127.0.0.1:9")
    monkeypatch.setenv("MINDX_DELTAVERSE_SPAWNER_PK", "0x" + "11" * 32)
    g = DeltaVerseGate(chain_id=137)
    res = await g.open_gate(GateSpec(theme="t", origin_event="publication:x"))
    assert res.ok is False
    assert res.blocked is True
    assert "not deployed" in (res.reason or "")
    assert res.room_tx is None and res.bubbleroom_tx is None
