"""Ed25519 signing and canonical encoding for CONCLAVE envelopes.

We use deterministic CBOR for canonical bytes so that any well-formed
implementation produces the same bytes for the same logical envelope.
This matters for cross-language verification (Python convener,
Go-based AXL node, possible Rust/JS members).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import cbor2  # type: ignore[import-untyped]
from nacl.signing import SigningKey, VerifyKey  # type: ignore[import-untyped]
from nacl.exceptions import BadSignatureError  # type: ignore[import-untyped]


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    """Deterministic CBOR encoding (RFC 8949 §4.2.1, canonical form).

    cbor2's `canonical=True` flag sorts map keys lexicographically by
    their encoded form and uses the shortest length encoding for ints.
    This is identical bytes-on-the-wire for a given Python dict regardless
    of insertion order.
    """
    return cbor2.dumps(payload, canonical=True)


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def hex32(data: bytes) -> str:
    """0x-prefixed hex of a 32-byte digest."""
    if len(data) != 32:
        raise ValueError(f"expected 32 bytes, got {len(data)}")
    return "0x" + data.hex()


def hex_pubkey(pk: bytes) -> str:
    if len(pk) != 32:
        raise ValueError(f"expected 32-byte pubkey, got {len(pk)}")
    return "0x" + pk.hex()


def parse_hex(s: str) -> bytes:
    """Accept either '0x'-prefixed or bare hex."""
    if s.startswith("0x") or s.startswith("0X"):
        s = s[2:]
    return bytes.fromhex(s)


@dataclass(frozen=True)
class KeyPair:
    """Ed25519 keypair. The verify key bytes ARE the AXL peer ID."""

    signing_key: SigningKey
    verify_key: VerifyKey

    @classmethod
    def generate(cls) -> "KeyPair":
        sk = SigningKey.generate()
        return cls(signing_key=sk, verify_key=sk.verify_key)

    @classmethod
    def from_seed(cls, seed: bytes) -> "KeyPair":
        if len(seed) != 32:
            raise ValueError("seed must be 32 bytes")
        sk = SigningKey(seed)
        return cls(signing_key=sk, verify_key=sk.verify_key)

    @classmethod
    def from_pem(cls, pem_path: str) -> "KeyPair":
        """Load an Ed25519 private key in the same PEM format AXL uses
        (`openssl genpkey -algorithm ed25519`)."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )

        with open(pem_path, "rb") as f:
            key = serialization.load_pem_private_key(f.read(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("PEM is not an Ed25519 private key")
        seed = key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return cls.from_seed(seed)

    @property
    def peer_id(self) -> str:
        """The 0x-prefixed hex pubkey, identical to the AXL peer id."""
        return hex_pubkey(bytes(self.verify_key))

    @property
    def pubkey_bytes(self) -> bytes:
        return bytes(self.verify_key)


def sign(kp: KeyPair, payload: dict[str, Any]) -> str:
    """Sign canonical(payload) and return a 0x-prefixed hex signature."""
    msg = canonical_bytes(payload)
    sig = kp.signing_key.sign(msg).signature
    return "0x" + sig.hex()


def verify(pubkey_hex: str, payload: dict[str, Any], sig_hex: str) -> bool:
    """Return True iff sig is a valid Ed25519 signature over canonical(payload)."""
    try:
        vk = VerifyKey(parse_hex(pubkey_hex))
        vk.verify(canonical_bytes(payload), parse_hex(sig_hex))
        return True
    except (BadSignatureError, ValueError):
        return False


def session_id_for(manifest_body: dict[str, Any]) -> str:
    """The session id is sha256 of the canonical-encoded manifest body."""
    return hex32(sha256(canonical_bytes(manifest_body)))


def motion_id_for(motion_body_without_id: dict[str, Any]) -> str:
    """A motion's id is sha256 of its canonical body sans `motion_id` and `sig`."""
    body = {k: v for k, v in motion_body_without_id.items() if k != "motion_id"}
    return hex32(sha256(canonical_bytes(body)))
