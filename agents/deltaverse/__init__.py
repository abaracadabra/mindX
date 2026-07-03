# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved.
"""
agents.deltaverse — DeltaVerse on-chain primitives for mindX.

Currently exposes the NeuralNode gate: a governed bridge that turns a
``DeltaVerse.gate.event`` into a *room* (BubbleRoomV4.mintRoom) and a
*bubbleroom* (BubbleRoomSpawn.spawnFromRoom) on Polygon. The contracts are the
DeltaVerse NeuralNode suite (github.com/deltav-deltaverse/neuralnode); mindX is
one consumer of them.

Fails CLOSED: with no deployed contract addresses, no RPC, or no spawner key,
the gate refuses to broadcast and emits a ``deltaverse.gate.event`` recording
the block reason instead. Nothing is ever spent by accident.
"""

from .neuralnode_gate import DeltaVerseGate, GateResult, GateError

__all__ = ["DeltaVerseGate", "GateResult", "GateError"]
