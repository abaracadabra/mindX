"""High-level convenience builder for THOTs.

Wraps Merkle commitment + Matryoshka prefix building into a single
entry point for issuance pipelines (mindX API, AgenticPlace, BANKON).

SPDX-License-Identifier: Apache-2.0
(c) 2026 BANKON — all rights reserved
Standard: cypherpunk2048
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .matryoshka import PrefixProof, build_prefix_proof
from .merkle import CANONICAL_DIMS, THOT4096Commitment, build_thot4096


@dataclass
class THOTBundle:
    """A complete issuance bundle: parent commitment + all prefix proofs."""

    commitment: THOT4096Commitment
    prefix_proofs: dict[int, PrefixProof]


def build_thot_bundle(vector: np.ndarray, prefix_dims: Iterable[int] = (8, 768, 1024, 2048)) -> THOTBundle:
    """Build the full issuance bundle for a 4096-dim vector.

    Args:
        vector: Numpy array of length 4096 (will be cast to fp16).
        prefix_dims: Which canonical prefix dimensions to materialize.
            Default: all four (8, 768, 1024, 2048).

    Returns:
        THOTBundle containing the parent commitment and each requested
        prefix proof.
    """
    for d in prefix_dims:
        if d not in CANONICAL_DIMS or d == 4096:
            raise ValueError(f"prefix_dim must be one of 8/768/1024/2048: {d}")

    commitment = build_thot4096(vector)
    proofs = {d: build_prefix_proof(commitment, d) for d in prefix_dims}
    return THOTBundle(commitment=commitment, prefix_proofs=proofs)


__all__ = ["THOTBundle", "build_thot_bundle"]
