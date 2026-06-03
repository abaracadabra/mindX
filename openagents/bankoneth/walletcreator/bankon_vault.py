"""
BANKON Vault — clean, single-file private-key vault.

================================================================================
  ⚠  ALWAYS OPEN SOURCE.
  The bankon-vault handles PRIVATE KEYS. Software that holds keys must be
  auditable or it cannot be trusted. This file is, and will always remain, open
  source — that is what makes the bankon-vault unique among all other software.
  No blackbox. Read it, audit it, fork it, self-host it. The value is in the
  service and the contracts, never in hiding the code that touches your keys.

  © BANKON — all rights preserved.
================================================================================

Crypto (same family as mindX's bankon_vault):
  passphrase ──HKDF-SHA512(salt, info="bankon-vault-master-key")──▶ master key
  master key ──HKDF-SHA512(salt, info="bankon-vault-entry:<id>")──▶ per-entry key
  per-entry key ──AES-256-GCM(nonce=12B, aad=<id>)──▶ ciphertext

The master key lives in memory only; only salt + per-entry {nonce, ciphertext}
touch disk. A reserved "__check__" entry lets the vault detect a wrong passphrase
without leaking anything. Per-entry HKDF domain separation means compromising one
entry's derived key reveals nothing about another.

This module has NO dependency on the rest of bankoneth or mindX — it is the
trust root and stays minimal on purpose.

CLIENT-SIDE & NON-CUSTODIAL
---------------------------
In production the vault lives ENTIRELY ON THE CLIENT — the Tauri desktop app, or
the web build running in the browser's own processor, RAM and filesystem. The
vault is created from parsec and its master key is **bound to the participant's
own private key** (see `from_participant_signature`): the participant signs a
fixed binding message with their wallet, and that signature is the only input
that derives the vault key. Therefore:

  • BANKON never sees the master key, the passphrase, or any plaintext key.
  • No host, server, or other hostile entity can decrypt the vault — only the
    holder of the participant's private key can.
  • This is what makes the bankon-vault unique: an always-open-source,
    client-side, key-bound vault you can audit line by line.

AIRGAP-FIRST
------------
The FIRST creation of a vault (and the first key generation) should be done on an
**airgapped device**. Call `network_connected()` before creating; if it returns
True, the client must warn the participant — see `airgap_advisory()` — and ask
"network is connected, do you want to proceed?" before continuing.
"""
from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, List, Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

_VERSION = "bankon-vault/1"
_MASTER_INFO = b"bankon-vault-master-key"
_ENTRY_INFO = b"bankon-vault-entry:"
_CHECK_ID = "__check__"
_CHECK_PLAINTEXT = b"bankon-vault-ok"

# The fixed message a participant signs (with their wallet's private key) to bind
# a vault to themselves. The signature is deterministic per key, so the same wallet
# always re-derives the same vault key — no passphrase to remember, and the key is
# attached to the participant's private key. Sign this with personal_sign / EIP-191.
BINDING_MESSAGE = "BANKON-VAULT-KEY-BINDING/v1"


class VaultError(Exception):
    """Base class for vault errors."""


class BadPassphrase(VaultError):
    """The supplied passphrase does not unlock this vault."""


class EntryNotFound(KeyError):
    """No such entry in the vault."""


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _ub64(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


class BankonVault:
    """A passphrase-locked, AES-256-GCM file vault for secrets (private keys).

    Usage:
        v = BankonVault("wallets.vault", "correct horse battery staple")
        v.put("wallet:0xabc", priv_key_bytes, meta={"chain": "evm"})
        priv = v.get("wallet:0xabc")          # bytes, decrypted in memory
        for row in v.list(): ...              # ids + meta only, never secrets
    """

    def __init__(self, path: str, passphrase, *, salt: Optional[bytes] = None):
        self.path = path
        self._entries: Dict[str, Dict[str, Any]] = {}
        self._salt: bytes = b""
        self._master: bytes = b""
        self._unlock(passphrase, salt)

    @classmethod
    def from_participant_signature(cls, path: str, signature, *, salt: Optional[bytes] = None) -> "BankonVault":
        """Open/create a vault BOUND TO THE PARTICIPANT'S PRIVATE KEY.

        `signature` is the participant's wallet signature over `BINDING_MESSAGE`
        (deterministic per key). It is used as the only key-derivation input, so
        the vault can be unlocked only by the holder of that private key — never by
        BANKON or any host. This is the production path; it should run client-side
        (Tauri / browser), ideally airgapped on first use.
        """
        sig = signature if isinstance(signature, (bytes, bytearray)) else bytes.fromhex(
            signature[2:] if str(signature).startswith("0x") else str(signature)
        )
        return cls(path, bytes(sig), salt=salt)

    # ── key derivation ──────────────────────────────────────────────────
    def _derive_master(self, passphrase: str, salt: bytes) -> bytes:
        ikm = passphrase.encode("utf-8") if isinstance(passphrase, str) else passphrase
        return HKDF(algorithm=hashes.SHA512(), length=32, salt=salt, info=_MASTER_INFO).derive(ikm)

    def _entry_key(self, entry_id: str) -> bytes:
        info = _ENTRY_INFO + entry_id.encode("utf-8")
        return HKDF(algorithm=hashes.SHA512(), length=32, salt=self._salt, info=info).derive(self._master)

    # ── seal / open ─────────────────────────────────────────────────────
    def _seal(self, entry_id: str, secret: bytes) -> Dict[str, str]:
        nonce = os.urandom(12)
        ct = AESGCM(self._entry_key(entry_id)).encrypt(nonce, secret, entry_id.encode("utf-8"))
        return {"nonce": _b64(nonce), "ct": _b64(ct)}

    def _open(self, entry_id: str, blob: Dict[str, str]) -> bytes:
        return AESGCM(self._entry_key(entry_id)).decrypt(
            _ub64(blob["nonce"]), _ub64(blob["ct"]), entry_id.encode("utf-8")
        )

    # ── lifecycle ───────────────────────────────────────────────────────
    def _unlock(self, passphrase: str, salt: Optional[bytes]) -> None:
        check: Optional[Dict[str, str]] = None
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
            if doc.get("version") != _VERSION:
                raise VaultError(f"unsupported vault version: {doc.get('version')}")
            self._salt = _ub64(doc["salt"])
            self._entries = dict(doc.get("entries", {}))
            check = doc.get("check")
        else:
            self._salt = salt or os.urandom(32)
            self._entries = {}

        self._master = self._derive_master(passphrase, self._salt)

        if check is not None:
            try:
                if self._open(_CHECK_ID, check) != _CHECK_PLAINTEXT:
                    raise BadPassphrase("wrong passphrase")
            except BadPassphrase:
                raise
            except Exception as exc:  # AES-GCM auth failure → wrong key
                raise BadPassphrase("wrong passphrase") from exc
        else:
            self._save()  # create the vault file + check token now

    def _save(self) -> None:
        doc = {
            "version": _VERSION,
            "salt": _b64(self._salt),
            "check": self._seal(_CHECK_ID, _CHECK_PLAINTEXT),
            "entries": self._entries,
        }
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2)
        os.replace(tmp, self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    # ── public API ──────────────────────────────────────────────────────
    def put(self, entry_id: str, secret, meta: Optional[Dict[str, Any]] = None) -> None:
        """Store (or replace) a secret under `entry_id`, encrypted at rest."""
        if entry_id == _CHECK_ID:
            raise VaultError("reserved entry id")
        b = secret.encode("utf-8") if isinstance(secret, str) else bytes(secret)
        blob = self._seal(entry_id, b)
        blob["meta"] = meta or {}
        self._entries[entry_id] = blob
        self._save()

    def get(self, entry_id: str) -> bytes:
        """Decrypt and return the secret bytes for `entry_id`."""
        e = self._entries.get(entry_id)
        if e is None:
            raise EntryNotFound(entry_id)
        return self._open(entry_id, e)

    def get_str(self, entry_id: str) -> str:
        return self.get(entry_id).decode("utf-8")

    def meta(self, entry_id: str) -> Dict[str, Any]:
        e = self._entries.get(entry_id)
        if e is None:
            raise EntryNotFound(entry_id)
        return dict(e.get("meta", {}))

    def has(self, entry_id: str) -> bool:
        return entry_id in self._entries

    def list(self) -> List[Dict[str, Any]]:
        """Ids + metadata only — never secrets."""
        return [{"id": k, "meta": v.get("meta", {})} for k, v in self._entries.items()]

    def remove(self, entry_id: str) -> None:
        if self._entries.pop(entry_id, None) is not None:
            self._save()

    # ── folder encryption (create / encrypt a folder) ───────────────────
    def encrypt_folder(self, entry_id: str, folder_path: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """Tar+gzip a whole folder and store it encrypted under `entry_id`.

        Lets the client choose to encrypt an entire folder (documents, keystores,
        a parsec workspace) into the vault — not just single secrets."""
        import io
        import tarfile

        name = os.path.basename(folder_path.rstrip(os.sep)) or "folder"
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            tar.add(folder_path, arcname=name)
        self.put(entry_id, buf.getvalue(), meta={**(meta or {}), "type": "folder", "name": name})

    def decrypt_folder(self, entry_id: str, dest_dir: str) -> str:
        """Restore a folder stored via `encrypt_folder` into `dest_dir`."""
        import io
        import tarfile

        data = self.get(entry_id)
        os.makedirs(dest_dir, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            try:
                tar.extractall(dest_dir, filter="data")  # py3.12+: block traversal/links
            except TypeError:
                tar.extractall(dest_dir)  # older Python; source is our own encrypted tar
        return dest_dir


# ── airgap diagnostic ───────────────────────────────────────────────────
def network_connected(host: str = "1.1.1.1", port: int = 53, timeout: float = 1.5) -> bool:
    """Best-effort check whether the device currently has network egress.
    Used to advise airgapped-first vault / key creation."""
    import socket

    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except OSError:
        return False


def airgap_advisory() -> Dict[str, Any]:
    """Diagnostic the client shows BEFORE the first vault/key creation. When the
    network is connected, the client MUST surface `question` and require an explicit
    confirmation before proceeding (key generation while online is riskier)."""
    online = network_connected()
    return {
        "network_connected": online,
        "advice": (
            "Create your vault and first keys from an AIRGAPPED device. Keys "
            "generated while online face a larger attack surface."
        ),
        "proceed_required": online,
        "question": "Network is connected. Do you want to proceed?" if online else "",
    }


__all__ = [
    "BankonVault",
    "VaultError",
    "BadPassphrase",
    "EntryNotFound",
    "BINDING_MESSAGE",
    "network_connected",
    "airgap_advisory",
]
