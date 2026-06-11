#!/usr/bin/env python3
# GNUVAULT — airgap signing helpers (build-your-own custody, offline).
# Copyright (C) 2026 cypherpunk2048 / BANKON.  GPL-3.0-or-later.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Airgap custody for GNUVAULT.

The flow, with no key ever touching the network:

  1. ``airgap_challenge()`` prints a fixed, public string.
  2. You sign it on an offline machine / hardware wallet — anything you control.
  3. You bring the *signature* back and hand it to
     ``overseer_from_signature(sig)`` → a ``WalletSignatureOverseer`` that
     derives your vault key as SHA-256(signature). The signature is never
     stored; deterministic signing (ed25519 RFC 8032, RFC-6979 ECDSA) reproduces
     it from the key alone.

GNUVAULT does NOT hold your signing key. For people who want a *software* signer
to build their own, a self-contained ed25519 keygen/sign/verify is included
(``cryptography``'s audited primitive). Hardware wallets sign externally and you
paste the result — GNUVAULT only verifies + packages.
"""
from __future__ import annotations

from typing import Tuple

from cryptography.hazmat.primitives.asymmetric import ed25519

from overseer import DEFAULT_CHALLENGE, WalletSignatureOverseer


def airgap_challenge(nonce: str = "") -> str:
    """The string to sign offline. Add a ``nonce`` to scope a one-off custody."""
    return DEFAULT_CHALLENGE + (("|nonce:" + nonce) if nonce else "")


def overseer_from_signature(signature: str | bytes, challenge: str = DEFAULT_CHALLENGE
                            ) -> WalletSignatureOverseer:
    """Build a custodian from a signature produced by any signer you control."""
    return WalletSignatureOverseer(signature, challenge)


# ── optional software signer (build-your-own; hardware signs externally) ──
def ed25519_keygen() -> Tuple[str, str]:
    """Generate an ed25519 keypair. Returns (private_hex, public_hex). Keep the
    private hex offline — it IS your custody."""
    sk = ed25519.Ed25519PrivateKey.generate()
    return sk.private_bytes_raw().hex(), sk.public_key().public_bytes_raw().hex()


def ed25519_sign(private_hex: str, challenge: str = DEFAULT_CHALLENGE) -> str:
    """Sign ``challenge`` with an ed25519 private key (hex). Deterministic →
    reproducible custody, so the signature need never be stored."""
    sk = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_hex))
    return sk.sign(challenge.encode("utf-8")).hex()


def ed25519_verify(public_hex: str, signature_hex: str, challenge: str = DEFAULT_CHALLENGE) -> bool:
    """Verify an ed25519 signature over ``challenge``. Never raises."""
    try:
        pk = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex))
        pk.verify(bytes.fromhex(signature_hex), challenge.encode("utf-8"))
        return True
    except Exception:
        return False


def _selftest() -> bool:
    priv, pub = ed25519_keygen()
    ch = airgap_challenge("demo")
    sig = ed25519_sign(priv, ch)
    assert ed25519_verify(pub, sig, ch)
    assert not ed25519_verify(pub, sig, airgap_challenge("other"))
    # deterministic: signing again reproduces the same signature → same custody
    assert ed25519_sign(priv, ch) == sig
    ov1 = overseer_from_signature(sig, ch)
    ov2 = overseer_from_signature(sig, ch)
    assert ov1.material() == ov2.material()
    print("airgap selftest OK — challenge → offline signature → reproducible custody")
    return True


if __name__ == "__main__":
    _selftest()


__all__ = ["airgap_challenge", "overseer_from_signature",
           "ed25519_keygen", "ed25519_sign", "ed25519_verify"]
