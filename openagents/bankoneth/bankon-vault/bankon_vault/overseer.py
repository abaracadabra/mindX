"""
VaultOverseer — pluggable authenticator for the BANKON Vault.

The vault's existing HKDF derivation is unchanged.  The overseer is a
pluggable SOURCE for the 64-byte raw seed that feeds the existing
`HKDF(ikm=raw, salt=self._salt, info=b"bankon-vault-master-key")` path.

Three implementations, one protocol:

    MachineOverseer  — today's default. Reads `.master.key`.
    HumanOverseer    — Stage-1 target. EIP-191 signature → raw key.
    DAIOOverseer     — Stage-2 stub. On-chain governance attestation.

See the plan section "BANKON Vault Custody Handoff — Two-Stage Overseer
Model" in /home/hacker/.claude/plans/glimmering-growing-scroll.md for the
full design rationale and threat model.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from cryptography.hazmat.primitives.hashes import SHA512
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


@runtime_checkable
class VaultOverseer(Protocol):
    """Protocol every overseer satisfies.  See module docstring.

    Convention:
        `challenge`  — the challenge-message bytes that were signed/attested
                       (e.g. the EIP-191 message text encoded as UTF-8).
                       Same semantics in both methods.
        `evidence`   — the authorization payload (signature, on-chain proof,
                       etc).  Shape depends on the overseer `kind`.
    Both methods accept the same challenge; `produce_raw_key` consumes
    `evidence` for the IKM so a single set of parameters drives both
    verification and key derivation.
    """

    kind: str            # "machine" | "human" | "daio"
    identity: str        # file path | 0x-address | governor contract

    def fingerprint(self) -> str: ...
    def produce_raw_key(self, challenge: bytes, evidence: Dict[str, Any]) -> bytes: ...
    def verify_evidence(self, evidence: Dict[str, Any], challenge: bytes) -> bool: ...


# ─────────────────────────────────────────────────────────────────────────
# MachineOverseer — today's default. Reads `.master.key`.
# ─────────────────────────────────────────────────────────────────────────


@dataclass
class MachineOverseer:
    """Reads a raw 64-byte key file from disk. Evidence is a no-op."""
    kind: str = "machine"
    key_file_path: Path = field(default_factory=Path)

    @property
    def identity(self) -> str:
        return str(self.key_file_path)

    def fingerprint(self) -> str:
        if not self.key_file_path.exists():
            return "machine:missing"
        raw = self.key_file_path.read_bytes()
        return "machine:" + hashlib.sha256(raw).hexdigest()[:16]

    def produce_raw_key(self, challenge: bytes, evidence: Dict[str, Any]) -> bytes:
        if not self.key_file_path.exists():
            raise RuntimeError(
                f"MachineOverseer: key file missing at {self.key_file_path}"
            )
        return self.key_file_path.read_bytes()

    def verify_evidence(self, evidence: Dict[str, Any], challenge: bytes) -> bool:
        # Machine mode has no external authorization — the filesystem IS the auth.
        return evidence.get("kind") == "machine"


# ─────────────────────────────────────────────────────────────────────────
# HumanOverseer — Stage-1. EIP-191 personal_sign.
# ─────────────────────────────────────────────────────────────────────────

HUMAN_INFO_PREFIX = b"bankon-overseer-human-v1:"


@dataclass
class HumanOverseer:
    """
    Authenticator backed by an Ethereum EOA.  The operator signs a challenge
    via EIP-191 `personal_sign` using MetaMask / Ledger / Trezor / `cast
    wallet sign`.  The 65-byte signature is the evidence and also the IKM
    for the raw-key derivation.

    Determinism: Ledger/MetaMask use RFC 6979 deterministic ECDSA so the
    same (privkey, message) pair always yields the same 65 bytes.  The
    ceremony ALSO persists (challenge, signature) to
    `vault_bankon/.overseer_proof.json` so that subsequent unlocks do not
    require re-signing — the operator signs once per rotation.
    """

    eth_address: str             # checksummed or lowercase 0x... (we normalize)
    vault_salt: bytes            # 32-byte vault salt, for HKDF
    kind: str = "human"

    def __post_init__(self):
        # Normalize the address to lowercase 0x... — EIP-191 recovery is
        # case-insensitive, but we want a canonical form for fingerprint.
        if not self.eth_address.startswith("0x") or len(self.eth_address) != 42:
            raise ValueError(
                f"HumanOverseer: invalid EIP-55/hex address {self.eth_address!r}"
            )
        self.eth_address = self.eth_address.lower()
        if len(self.vault_salt) != 32:
            raise ValueError("HumanOverseer: vault_salt must be 32 bytes")

    @property
    def identity(self) -> str:
        return self.eth_address

    def fingerprint(self) -> str:
        return "human:" + self.eth_address[-8:]

    def produce_raw_key(self, challenge: bytes, evidence: Dict[str, Any]) -> bytes:
        """Extract the 65-byte signature from `evidence["signature"]` and
        use it as IKM.  `challenge` is the message bytes the signature
        covers; it is NOT used here directly (verify_evidence already
        bound the signature to this challenge), but accepting it keeps
        the protocol uniform."""
        sig_hex = evidence.get("signature")
        if not sig_hex:
            raise ValueError("HumanOverseer.produce_raw_key: evidence missing 'signature'")
        if sig_hex.startswith("0x"):
            sig_hex = sig_hex[2:]
        sig_bytes = bytes.fromhex(sig_hex)
        if len(sig_bytes) != 65:
            raise ValueError(
                f"HumanOverseer.produce_raw_key: signature must be 65 bytes, got {len(sig_bytes)}"
            )
        addr_bytes = bytes.fromhex(self.eth_address[2:])
        info = HUMAN_INFO_PREFIX + addr_bytes
        hkdf = HKDF(
            algorithm=SHA512(),
            length=64,
            salt=self.vault_salt,
            info=info,
        )
        return hkdf.derive(sig_bytes)

    def verify_evidence(self, evidence: Dict[str, Any], challenge: bytes) -> bool:
        """
        Evidence shape:
            {
                "kind": "human",
                "signature": "0x<130-hex-chars>",
                "message": "<human-readable challenge text>",
            }

        `challenge` here is the *original challenge text bytes* (not the
        signature); we pass it separately so the verifier can bind the
        signature to a specific message.
        """
        if evidence.get("kind") != "human":
            return False
        sig_hex = evidence.get("signature")
        message = evidence.get("message")
        if not sig_hex or not message:
            return False

        # `eth_account` recovers the address that signed an EIP-191 message.
        try:
            from eth_account import Account
            from eth_account.messages import encode_defunct
        except ImportError as e:
            raise RuntimeError(
                "HumanOverseer.verify_evidence requires eth_account: "
                "install via the mindX venv (already a web3 dep)."
            ) from e

        # Ensure the challenge bytes correspond to the message text — bind
        # the two together so a replayed signature on a different message
        # cannot be laundered.
        if message.encode("utf-8") != challenge:
            return False

        msg = encode_defunct(text=message)
        try:
            recovered = Account.recover_message(msg, signature=sig_hex)
        except Exception:
            return False
        return recovered.lower() == self.eth_address


# ─────────────────────────────────────────────────────────────────────────
# DAIOOverseer — Stage-2 stub.  Interface-only.
# ─────────────────────────────────────────────────────────────────────────

DAIO_INFO_PREFIX = b"bankon-overseer-daio-v1:"


@dataclass
class DAIOOverseer:
    """
    Stage-2 authenticator: unlock requires proof that an on-chain governance
    proposal with the right digest cleared a weighted-majority vote.

    Not implemented — exists so `rotate_overseer(DAIOOverseer(...))` compiles
    today.  The full verifier lives in the Phase-2 DAIO work.
    """

    registry: str                # 0x... of the Governor / DAIO registry contract
    threshold: int               # minimum weighted score (scaled 0-1000)
    chain_id: int
    kind: str = "daio"

    @property
    def identity(self) -> str:
        return f"daio:{self.chain_id}:{self.registry}"

    def fingerprint(self) -> str:
        h = hashlib.sha256(
            f"{self.chain_id}:{self.registry}:{self.threshold}".encode()
        ).hexdigest()[:16]
        return "daio:" + h

    def produce_raw_key(self, challenge: bytes, evidence: Dict[str, Any]) -> bytes:
        raise NotImplementedError(
            "DAIOOverseer.produce_raw_key is Stage-2 — not implemented. "
            "Design note: HKDF(ikm=attestation_digest, info=DAIO_INFO_PREFIX+registry+chain_id)."
        )

    def verify_evidence(self, evidence: Dict[str, Any], challenge: bytes) -> bool:
        raise NotImplementedError(
            "DAIOOverseer.verify_evidence is Stage-2 — not implemented. "
            "Design note: Governor.proposalState(id) == Executed AND "
            "hashProposal matches AND weighted vote ≥ threshold."
        )


# ─────────────────────────────────────────────────────────────────────────
# Convenience: build HumanOverseer from the ceremony proof file.
# ─────────────────────────────────────────────────────────────────────────

def load_human_from_proof(proof_path: Path, vault_salt: bytes) -> tuple["HumanOverseer", bytes, Dict[str, Any]]:
    """
    Read `.overseer_proof.json` and return (overseer, challenge_bytes, evidence).

    `challenge_bytes` is the message text (UTF-8 encoded) that was signed —
    same thing passed as `new_challenge` in the original rotation call.
    Callers pass this through to `unlock_with_overseer(overseer, challenge_bytes, evidence)`.

    The proof file is produced by `BankonVault.rotate_overseer` on successful
    commit to a HumanOverseer.  Re-unlocks (service restart) call this helper
    so the operator does NOT have to re-sign.
    """
    data = json.loads(proof_path.read_text())
    address = data["address"]
    message = data["message"]
    sig_hex = data["signature"]
    if not sig_hex.startswith("0x"):
        sig_hex = "0x" + sig_hex
    evidence: Dict[str, Any] = {
        "kind": "human",
        "signature": sig_hex,
        "message": message,
    }
    overseer = HumanOverseer(eth_address=address, vault_salt=vault_salt)
    challenge_bytes = message.encode("utf-8")
    return overseer, challenge_bytes, evidence
