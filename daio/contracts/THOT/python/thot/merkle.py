"""THOT Merkle commitment builder.

Produces the canonical 64-leaf binary Merkle tree over a 4096-dim
THOT artifact, matching THOTLib.sol byte-for-byte.

Leaf layout:
    - 64 leaves of 64 dimensions each (covers the full THOT4096).
    - Each leaf is keccak256( LEAF_DOMAIN_4096 || u32(idx) || u16(dim_start)
                               || u16(dim_end) || chunk_bytes ).
    - Non-power-of-two prefix counts are padded with the canonical
      TOMBSTONE leaf.

SPDX-License-Identifier: Apache-2.0
(c) 2026 BANKON — all rights reserved
Standard: cypherpunk2048
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from typing import Sequence

import numpy as np
from Crypto.Hash import keccak  # type: ignore[import-untyped]

# -----------------------------------------------------------------
#                       Domain separators
# -----------------------------------------------------------------


def _keccak(data: bytes) -> bytes:
    return keccak.new(digest_bits=256, data=data).digest()


LEAF_DOMAIN_4096: bytes = _keccak(b"THOT4096/leaf/v1")
TOMBSTONE: bytes = _keccak(b"THOT/tombstone/v1")

# RFC-6962 internal-node prefix. Every Merkle internal-node hash is
# keccak256(NODE_PREFIX || left || right). MUST stay byte-identical to
# daio/contracts/THOT/libraries/THOTLib.sol:NODE_PREFIX (0x01). Without
# this prefix, an attacker could pass internal-node bytes off as a leaf
# (CVE-2012-2459 / OpenZeppelin#3091).
NODE_PREFIX: bytes = b"\x01"

# Canonical dimensions for the THOT family.
CANONICAL_DIMS: tuple[int, ...] = (8, 768, 1024, 2048, 4096)

# Leaf width (in vector dimensions).
LEAF_DIM: int = 64

# Bytes per fp16 value.
FP16_BYTES: int = 2


# -----------------------------------------------------------------
#                       Helpers
# -----------------------------------------------------------------


def _next_power_of_two(n: int) -> int:
    if n <= 1:
        return 1
    return 1 << (n - 1).bit_length()


def leaf_count_for_dim(dim: int) -> tuple[int, int]:
    """Return (actual_leaf_count, padded_power_of_two) for a given dim."""
    if dim == 8:
        # THOT8 is a sub-leaf artifact, but for tree-shape purposes
        # it occupies a single dedicated leaf.
        return 1, 1
    if dim in (768, 1024, 2048, 4096):
        n = math.ceil(dim / LEAF_DIM)
        return n, _next_power_of_two(n)
    raise ValueError(f"non-canonical dimension: {dim}")


def encode_fp16_chunk(chunk: np.ndarray) -> bytes:
    """Encode a 64-dim fp16 chunk to its canonical 128-byte form."""
    if chunk.dtype != np.float16:
        chunk = chunk.astype(np.float16)
    if chunk.shape != (LEAF_DIM,):
        raise ValueError(f"chunk must have shape ({LEAF_DIM},), got {chunk.shape}")
    return chunk.tobytes()


def hash_leaf_4096(index: int, dim_start: int, dim_end: int, chunk_bytes: bytes) -> bytes:
    """Compute the canonical leaf hash for a THOT4096 chunk.

    Matches THOTLib.hashLeaf4096 byte-for-byte using abi.encodePacked
    semantics: uint32 (4 bytes BE), uint16 (2 bytes BE), uint16 (2 bytes BE).
    """
    if len(chunk_bytes) != LEAF_DIM * FP16_BYTES:
        raise ValueError(f"chunk_bytes must be {LEAF_DIM * FP16_BYTES} bytes")
    return _keccak(
        LEAF_DOMAIN_4096
        + struct.pack(">I", index)
        + struct.pack(">H", dim_start)
        + struct.pack(">H", dim_end)
        + chunk_bytes
    )


def merkle_root(leaves: Sequence[bytes]) -> bytes:
    """Merkle root with TOMBSTONE padding to the next power of two."""
    n = len(leaves)
    if n == 0:
        return TOMBSTONE
    padded = _next_power_of_two(n)
    layer = list(leaves) + [TOMBSTONE] * (padded - n)
    while len(layer) > 1:
        nxt: list[bytes] = []
        for i in range(0, len(layer), 2):
            nxt.append(_keccak(NODE_PREFIX + layer[i] + layer[i + 1]))
        layer = nxt
    return layer[0]


# -----------------------------------------------------------------
#                       Builder
# -----------------------------------------------------------------


@dataclass
class THOT4096Commitment:
    """The full Merkle commitment over a THOT4096 vector."""

    leaves: list[bytes]
    root: bytes
    ternary_head_leaf: bytes
    ternary_head_index: int

    def prefix_root(self, dim: int) -> bytes:
        """Compute the canonical Matryoshka prefix root at `dim`.

        For canonical dims (768, 1024, 2048), this is the Merkle root
        of the first ceil(dim/64) leaves with tombstone padding.
        For 8, returns the ternary head leaf itself (no padding).
        """
        if dim == 8:
            return self.ternary_head_leaf
        if dim not in (768, 1024, 2048):
            raise ValueError(f"non-prefix canonical dim: {dim}")
        n_leaves = math.ceil(dim / LEAF_DIM)
        return merkle_root(self.leaves[:n_leaves])


def build_thot4096(vector: np.ndarray) -> THOT4096Commitment:
    """Build the canonical Merkle commitment for a 4096-dim fp16 vector.

    Args:
        vector: Numpy array, length 4096, will be cast to fp16.

    Returns:
        THOT4096Commitment with all 64 leaves, root, and ternary head.
    """
    if vector.shape != (4096,):
        raise ValueError(f"vector must have shape (4096,), got {vector.shape}")
    if vector.dtype != np.float16:
        vector = vector.astype(np.float16)

    leaves: list[bytes] = []
    for i in range(64):
        dim_start = i * LEAF_DIM
        dim_end = dim_start + LEAF_DIM
        chunk = vector[dim_start:dim_end]
        chunk_bytes = encode_fp16_chunk(chunk)
        leaves.append(hash_leaf_4096(i, dim_start, dim_end, chunk_bytes))

    # Compute ternary head from the first eight dims.
    from .thot8_cpu import ternarize_first_eight, ternary_head_leaf

    head = ternary_head_leaf(ternarize_first_eight(vector.tolist()))

    return THOT4096Commitment(
        leaves=leaves,
        root=merkle_root(leaves),
        ternary_head_leaf=head,
        ternary_head_index=0xFF,  # reserved index
    )


__all__ = [
    "LEAF_DOMAIN_4096",
    "TOMBSTONE",
    "CANONICAL_DIMS",
    "LEAF_DIM",
    "FP16_BYTES",
    "leaf_count_for_dim",
    "encode_fp16_chunk",
    "hash_leaf_4096",
    "merkle_root",
    "THOT4096Commitment",
    "build_thot4096",
]
