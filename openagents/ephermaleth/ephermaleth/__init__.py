# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""ephermaleth — verifiable chains of command + a voting booth for councils.

A small, agnostic protocol-enhancement library:

  • ``AttestationChain`` — a hash-linked, multi-signer chain of custody. Each
    link is signed by a different identity's wallet (EIP-191); the chain is
    tamper-evident and verifiable by anyone with public keys.
  • ``verify_chain`` — recover every signer, check the linkage, no trust required.
  • pluggable ``Signer`` oracles — the chain never holds a private key.
  • ``VotingBooth`` — an append-only, hash-linked ledger of council decisions
    (a board, a war council, a DAIO, a throne), each optionally carrying its own
    attestation chain.

Bring your own signer and registry; ephermaleth imports no application code.
"""
from __future__ import annotations

from .chain import AttestationChain, ChainLink, CHALLENGE_NS, build_challenge, sha256_hex
from .signer import (
    EnvKeystoreSigner,
    KeymapSigner,
    NullSigner,
    OracleSigner,
    Signer,
    parse_keys_env,
    recover_signer,
)
from .verify import extract_chain_from_html, verify_chain
from .votingbooth import VotingBooth

__version__ = "0.1.0"

__all__ = [
    "AttestationChain", "ChainLink", "CHALLENGE_NS", "build_challenge", "sha256_hex",
    "Signer", "NullSigner", "KeymapSigner", "EnvKeystoreSigner", "OracleSigner",
    "parse_keys_env", "recover_signer",
    "verify_chain", "extract_chain_from_html", "VotingBooth",
    "__version__",
]
