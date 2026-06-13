#!/usr/bin/env python3
# GNUVAULT — the Overseer protocol (pluggable unlock).
# Copyright (C) 2026 cypherpunk2048 / BANKON.  GPL-3.0-or-later.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
The Overseer protocol — *who is allowed to derive the key*.

An ``Overseer`` produces the input keying material a tomb is sealed/opened with.
This is the bankoneth/BANKON pattern (Machine / Human / DAIO overseers),
generalized and de-coupled from any service. Three are shipped:

  • ``PassphraseOverseer``       — a human passphrase (the default path).
  • ``KeyfileOverseer``          — bytes from a key file (e.g. a ``.master.key``
                                   on a USB stick; the machine/keyfile custody).
  • ``WalletSignatureOverseer``  — key material = SHA-256(signature) over a fixed
                                   challenge (the DeltaVerse signature-derived
                                   pattern). Deterministic: the same wallet, over
                                   the same challenge, reproduces the same key —
                                   so a hardware wallet or any signer can be the
                                   custodian, and the signature never has to be
                                   stored. GNUVAULT does NOT sign for you; you
                                   bring the signature.

The contract is one method: ``material() -> bytes``. The cipher key is then
``scrypt(material, salt)`` exactly as for a passphrase — so overseers compose
with everything in gnuvault.py without changing the crypto.
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path

# A fixed, public challenge so a WalletSignatureOverseer is reproducible across
# machines and clients. Sign THIS string to derive your vault custody.
DEFAULT_CHALLENGE = "GNUVAULT custody · cypherpunk2048 · the key becomes sovereign"


class Overseer(ABC):
    """Produces the keying material a tomb is sealed/opened with."""

    kind: str = "overseer"

    @abstractmethod
    def material(self) -> bytes:
        """Return the input keying material (fed to scrypt with the salt)."""
        raise NotImplementedError


class PassphraseOverseer(Overseer):
    kind = "passphrase"

    def __init__(self, passphrase: str) -> None:
        self._p = passphrase

    def material(self) -> bytes:
        return self._p.encode("utf-8")


class KeyfileOverseer(Overseer):
    """Custody by a key file — keep it on a USB stick and the laptop alone can
    never open the tomb. Domain-separated so a key file and a passphrase of the
    same bytes do not collide."""
    kind = "keyfile"

    def __init__(self, path: str | Path) -> None:
        self._path = Path(str(path)).expanduser()

    def material(self) -> bytes:
        raw = self._path.read_bytes()
        return b"gnuvault-keyfile:" + raw


class WalletSignatureOverseer(Overseer):
    """Custody by a wallet signature. key material = SHA-256(signature_bytes).

    Bring a signature over ``challenge`` (default: DEFAULT_CHALLENGE) produced by
    any signer you control — MetaMask ``personal_sign``, a Ledger, an offline
    ``openssl``/``ssh`` signature, anything. Deterministic signing schemes
    (RFC-6979 ECDSA, ed25519) reproduce the same signature, so the key is
    recoverable from the wallet alone and the signature is never stored."""
    kind = "wallet-signature"

    def __init__(self, signature: str | bytes, challenge: str = DEFAULT_CHALLENGE) -> None:
        if isinstance(signature, str):
            s = signature.strip()
            if s.startswith("0x") or s.startswith("0X"):
                s = s[2:]
            try:
                sig = bytes.fromhex(s)
            except ValueError:
                sig = signature.encode("utf-8")
        else:
            sig = signature
        self._sig = sig
        self._challenge = challenge

    def material(self) -> bytes:
        # Bind the challenge in so a signature for a different purpose can't be
        # cross-used to open the vault.
        return hashlib.sha256(self._challenge.encode("utf-8") + b"\x00" + self._sig).digest()


__all__ = ["Overseer", "PassphraseOverseer", "KeyfileOverseer",
           "WalletSignatureOverseer", "DEFAULT_CHALLENGE"]
