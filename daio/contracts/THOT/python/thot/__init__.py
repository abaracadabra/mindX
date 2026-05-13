"""thot — canonical THOT family reference implementation.

SPDX-License-Identifier: Apache-2.0
(c) 2026 BANKON — all rights reserved
Standard: cypherpunk2048
"""

from .builder import THOTBundle, build_thot_bundle
from .matryoshka import PrefixProof, build_prefix_proof, truncate_vector, verify_prefix_proof
from .merkle import (
    CANONICAL_DIMS,
    LEAF_DIM,
    THOT4096Commitment,
    build_thot4096,
    hash_leaf_4096,
    merkle_root,
)
from .thot8_cpu import THOT8, cosine, dot, ternarize_first_eight, ternary_head_leaf

__all__ = [
    # builder
    "THOTBundle",
    "build_thot_bundle",
    # matryoshka
    "PrefixProof",
    "build_prefix_proof",
    "truncate_vector",
    "verify_prefix_proof",
    # merkle
    "CANONICAL_DIMS",
    "LEAF_DIM",
    "THOT4096Commitment",
    "build_thot4096",
    "hash_leaf_4096",
    "merkle_root",
    # thot8
    "THOT8",
    "cosine",
    "dot",
    "ternarize_first_eight",
    "ternary_head_leaf",
]

__version__ = "0.1.0"
