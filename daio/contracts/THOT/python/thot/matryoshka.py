"""Matryoshka prefix utilities for the THOT family.

Given a canonical THOT4096 commitment, produce the prefix-binding
proof for any smaller canonical dimension. The proof is consumable
by THOTRegistry.registerPrefix on Ethereum.

Three prefix-binding modes are supported:

  Mode A — Pure Merkle prefix (power-of-two-aligned dims).
      For dims whose leaf count is a power of two (1024 = 16 leaves,
      2048 = 32 leaves), the canonical prefix root is *literally a
      node* of the parent Merkle tree. The proof is the standard
      right-sibling path from that node up to the parent root.

  Mode B — Merkle prefix with co-witness leaves (non-pow2-aligned dims).
      For dims whose leaf count is not a power of two (e.g. 768 = 12
      leaves), the canonical prefix root is computed with tombstone
      padding (12 real leaves + 4 tombstones → 16 internal positions),
      while the *parent* tree at that level uses real data in those
      positions. The proof reveals the missing co-witness leaves so the
      verifier can:
          (1) compute the canonical prefix root with tombstone padding,
          (2) independently reconstruct the parent subtree node using
              real co-witness data,
          (3) climb to the parent root.
      Both computations bind the same set of revealed prefix leaves.

  Mode C — Sibling commitment (THOT8 only).
      The ternary head is a 16-bit ternary projection, not a Merkle
      prefix; the registry stores it as a separate sibling field
      alongside the parent root. Verification is by direct registry
      equality.

SPDX-License-Identifier: Apache-2.0
(c) 2026 BANKON — all rights reserved
Standard: cypherpunk2048
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .merkle import (
    CANONICAL_DIMS,
    LEAF_DIM,
    THOT4096Commitment,
    TOMBSTONE,
    NODE_PREFIX,
    _keccak,
    merkle_root,
)


@dataclass
class PrefixProof:
    """Proof that a smaller THOT root is the canonical prefix of a parent.

    Fields:
        parent_root:       The THOT4096 parent Merkle root.
        prefix_dim:        The canonical prefix dimension (8, 768, 1024, 2048).
        prefix_root:       The canonical commitment for the prefix artifact.
                           For 768/1024/2048: merkle_root(prefix_leaves)
                           with internal tombstone padding.
                           For 8: the ternary head leaf hash.
        prefix_leaves:     The real parent leaves covering the prefix
                           region. For 768: 12 leaves. For 1024: 16.
                           For 2048: 32. For 8: [ternary_head_leaf].
        co_witness_leaves: Extra parent leaves needed to climb to the
                           parent tree's internal node aligned with the
                           prefix subtree (Mode B). Non-empty only when
                           the prefix leaf count is not a power of two.
                           For 768: 4 leaves (parent leaves 12..15).
                           For 1024/2048/8: empty.
        right_siblings:    Right-sibling path from the parent subtree
                           node up to the parent root.
                           For 8: empty (sibling commitment).
    """

    parent_root: bytes
    prefix_dim: int
    prefix_root: bytes
    prefix_leaves: list[bytes]
    co_witness_leaves: list[bytes] = field(default_factory=list)
    right_siblings: list[bytes] = field(default_factory=list)


def truncate_vector(vector_4096: list[float], prefix_dim: int) -> list[float]:
    """Take the canonical Matryoshka prefix of a 4096-dim vector."""
    if prefix_dim not in CANONICAL_DIMS or prefix_dim > 4096:
        raise ValueError(f"non-canonical prefix dim: {prefix_dim}")
    return list(vector_4096[:prefix_dim])


def _next_power_of_two(n: int) -> int:
    if n <= 1:
        return 1
    return 1 << (n - 1).bit_length()


def _build_full_tree(leaves: list[bytes]) -> list[list[bytes]]:
    """Build all tree levels bottom-up.

    Level 0 is the leaves layer; the last level has a single element
    (the root). Pads to power of two with TOMBSTONE.
    """
    n = len(leaves)
    if n == 0:
        return [[TOMBSTONE]]
    padded = _next_power_of_two(n)
    layer = list(leaves) + [TOMBSTONE] * (padded - n)
    levels: list[list[bytes]] = [layer]
    while len(layer) > 1:
        nxt: list[bytes] = []
        for i in range(0, len(layer), 2):
            nxt.append(_keccak(NODE_PREFIX + layer[i] + layer[i + 1]))
        levels.append(nxt)
        layer = nxt
    return levels


def build_prefix_proof(commitment: THOT4096Commitment, prefix_dim: int) -> PrefixProof:
    """Build a prefix-binding proof for `prefix_dim` against the parent.

    Dispatches to one of three modes based on the prefix dimension's
    relationship to the parent tree (see module docstring).
    """
    # -------- Mode C: THOT8 ternary head (sibling commitment) --------
    if prefix_dim == 8:
        return PrefixProof(
            parent_root=commitment.root,
            prefix_dim=8,
            prefix_root=commitment.ternary_head_leaf,
            prefix_leaves=[commitment.ternary_head_leaf],
            co_witness_leaves=[],
            right_siblings=[],
        )

    if prefix_dim not in (768, 1024, 2048):
        raise ValueError(f"prefix_dim must be one of 8/768/1024/2048: {prefix_dim}")

    n_prefix_leaves = math.ceil(prefix_dim / LEAF_DIM)
    padded_prefix = _next_power_of_two(n_prefix_leaves)

    prefix_leaves = commitment.leaves[:n_prefix_leaves]
    prefix_root = merkle_root(prefix_leaves)  # tombstone-padded if needed

    full_levels = _build_full_tree(commitment.leaves)

    # The parent-aligned subtree node sits at level log2(padded_prefix).
    # Example: padded_prefix=16 -> level 4 in a 7-level tree.
    level_index = padded_prefix.bit_length() - 1

    if n_prefix_leaves == padded_prefix:
        # -------- Mode A: pure Merkle prefix (pow2-aligned) --------
        co_witness_leaves: list[bytes] = []
    else:
        # -------- Mode B: Merkle prefix with co-witness leaves --------
        # The parent subtree node uses REAL leaves where the canonical
        # prefix root uses TOMBSTONE. Reveal those leaves so the
        # verifier can reconstruct the parent subtree node.
        co_witness_leaves = list(commitment.leaves[n_prefix_leaves:padded_prefix])

    # Climb from level_index to the root level, collecting right
    # siblings. Cursor starts at 0 (leftmost) and stays on the left edge.
    right_siblings: list[bytes] = []
    cursor = 0
    for lvl in range(level_index, len(full_levels) - 1):
        sibling = full_levels[lvl][cursor ^ 1]
        right_siblings.append(sibling)
        cursor >>= 1

    return PrefixProof(
        parent_root=commitment.root,
        prefix_dim=prefix_dim,
        prefix_root=prefix_root,
        prefix_leaves=prefix_leaves,
        co_witness_leaves=co_witness_leaves,
        right_siblings=right_siblings,
    )


def verify_prefix_proof(proof: PrefixProof) -> bool:
    """Locally verify a prefix proof — mirrors THOTLib.verifyPrefix.

    Returns True iff:
      - THOT8: proof has the expected sibling-commitment shape.
        Binding to a specific parent is by registry equality, not
        Merkle inclusion.
      - THOT768: prefix_root is the tombstone-padded Merkle root of the
        12 revealed prefix leaves, AND those 12 leaves combined with
        the 4 co-witness leaves hash up (with right siblings) to the
        parent root.
      - THOT1024 / THOT2048: prefix_root is the Merkle root of the
        revealed prefix leaves (no padding needed), AND those leaves
        hash up (with right siblings) to the parent root.
    """
    # -------- Mode C: THOT8 sibling commitment --------
    if proof.prefix_dim == 8:
        return (
            len(proof.right_siblings) == 0
            and len(proof.co_witness_leaves) == 0
            and len(proof.prefix_leaves) == 1
            and proof.prefix_leaves[0] == proof.prefix_root
        )

    # (1) Recompute the canonical prefix root (tombstone padding inside
    #     merkle_root if needed).
    reconstructed_prefix_root = merkle_root(proof.prefix_leaves)
    if reconstructed_prefix_root != proof.prefix_root:
        return False

    # (2) Reconstruct the parent subtree node using real co-witness data.
    combined = list(proof.prefix_leaves) + list(proof.co_witness_leaves)
    parent_subtree_node = merkle_root(combined)

    # (3) Climb to the parent root via right siblings. NODE_PREFIX on
    #     every step to match THOTLib.verifyPrefix.
    cursor = parent_subtree_node
    for sibling in proof.right_siblings:
        cursor = _keccak(NODE_PREFIX + cursor + sibling)
    return cursor == proof.parent_root


__all__ = [
    "PrefixProof",
    "truncate_vector",
    "build_prefix_proof",
    "verify_prefix_proof",
]
