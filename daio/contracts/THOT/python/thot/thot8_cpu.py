"""THOT8 CPU reference implementation.

The THOT8 is the on-chain head of the THOT family: an 8-dimensional
ternary vector with values in {-1, 0, +1}, packed at 2 bits per
dimension into a single 16-bit word.

This module provides the canonical encode / decode / dot-product
primitives and the Keccak-256 leaf hash that matches THOTLib.sol on
EVM. It runs on any CPU and is the reference against which on-chain
implementations are checked.

SPDX-License-Identifier: Apache-2.0
(c) 2026 BANKON — all rights reserved
Standard: cypherpunk2048
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from Crypto.Hash import keccak  # type: ignore[import-untyped]

# -----------------------------------------------------------------
#                       Domain separators
# -----------------------------------------------------------------

LEAF_DOMAIN_THOT8: bytes = keccak.new(digest_bits=256, data=b"THOT8/head/v1").digest()


# -----------------------------------------------------------------
#                          Codec
# -----------------------------------------------------------------


@dataclass(frozen=True)
class THOT8:
    """An eight-dimensional ternary tensor."""

    values: tuple[int, int, int, int, int, int, int, int]

    def __post_init__(self) -> None:
        if len(self.values) != 8:
            raise ValueError("THOT8 must have exactly 8 values")
        for v in self.values:
            if v not in (-1, 0, 1):
                raise ValueError(f"ternary value out of range: {v!r}")

    @classmethod
    def from_sequence(cls, seq: Sequence[int]) -> "THOT8":
        if len(seq) != 8:
            raise ValueError("input must have length 8")
        return cls(tuple(int(v) for v in seq))  # type: ignore[arg-type]

    def pack(self) -> bytes:
        """Pack into a canonical 2-byte representation.

        Codon assignment (per dimension, LSB-first within the word):
            0 -> 0b00
           +1 -> 0b01
           -1 -> 0b10

        The reserved codon 0b11 is never produced and is rejected
        on decode.
        """
        word = 0
        for i, v in enumerate(self.values):
            codon = {0: 0b00, 1: 0b01, -1: 0b10}[v]
            word |= codon << (i * 2)
        return word.to_bytes(2, byteorder="little")

    @classmethod
    def unpack(cls, packed: bytes) -> "THOT8":
        if len(packed) != 2:
            raise ValueError("THOT8 packed must be exactly 2 bytes")
        word = int.from_bytes(packed, byteorder="little")
        out: list[int] = []
        for i in range(8):
            codon = (word >> (i * 2)) & 0x3
            if codon == 0b11:
                raise ValueError("reserved ternary codon 0b11")
            out.append({0b00: 0, 0b01: 1, 0b10: -1}[codon])
        return cls(tuple(out))  # type: ignore[arg-type]


# -----------------------------------------------------------------
#                          Operations
# -----------------------------------------------------------------


def dot(a: THOT8, b: THOT8) -> int:
    """Integer dot product of two THOT8 vectors. Range: [-8, +8]."""
    return sum(x * y for x, y in zip(a.values, b.values))


def cosine(a: THOT8, b: THOT8) -> float:
    """Cosine similarity in [-1, +1], with 0 for zero-norm vectors."""
    na = sum(x * x for x in a.values) ** 0.5
    nb = sum(y * y for y in b.values) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot(a, b) / (na * nb)


# -----------------------------------------------------------------
#                       Merkle leaf hash
# -----------------------------------------------------------------


def ternary_head_leaf(t: THOT8) -> bytes:
    """Compute the canonical Merkle leaf hash for the ternary head.

    Matches THOTLib.hashTernaryHead in Solidity:

        keccak256(LEAF_DOMAIN_THOT8 || packedTernary || bytes30(0))
    """
    packed = t.pack()
    payload = LEAF_DOMAIN_THOT8 + packed + b"\x00" * 30
    return keccak.new(digest_bits=256, data=payload).digest()


# -----------------------------------------------------------------
#                       Quantization head
# -----------------------------------------------------------------


def ternarize_first_eight(vector: Sequence[float], threshold: float = 0.0) -> THOT8:
    """Quantize the first eight values of a real vector into a THOT8.

    This is the canonical "ternary head" of any THOT4096: take the
    first eight dimensions, threshold against ±threshold, and emit
    the eight-dim ternary projection.

    Args:
        vector: Real-valued vector of length >= 8.
        threshold: Magnitude below which values map to 0 (default 0.0,
            meaning sign of value).

    Returns:
        The canonical THOT8 representation of the first eight dims.
    """
    if len(vector) < 8:
        raise ValueError("vector must have length >= 8")
    out: list[int] = []
    for v in vector[:8]:
        if abs(v) < threshold:
            out.append(0)
        elif v > 0:
            out.append(1)
        else:
            out.append(-1)
    return THOT8.from_sequence(out)


__all__ = [
    "THOT8",
    "LEAF_DOMAIN_THOT8",
    "dot",
    "cosine",
    "ternary_head_leaf",
    "ternarize_first_eight",
]
