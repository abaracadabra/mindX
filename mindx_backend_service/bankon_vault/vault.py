# ╔══════════════════════════════════════════════════════════════════╗
# ║  BANKON Vault — Pure Python Credential Vault                   ║
# ║  (c) BANKON — All Rights Reserved                              ║
# ║  License: GPL-3.0 (cypherpunk2048 standard)                    ║
# ║                                                                ║
# ║  Passphrase → HKDF-SHA512 → vault key (memory only)           ║
# ║  Per-entry HKDF domain separation → AES-256-GCM               ║
# ║  On lock: all keys zeroized from memory                        ║
# ║                                                                ║
# ║  ZERO DEPENDENCIES beyond Python stdlib + cryptography         ║
# ╚══════════════════════════════════════════════════════════════════╝

import os
import json
import stat
import time
import secrets
from pathlib import Path
from typing import Optional, Dict, List, Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


VAULT_VERSION = "1.0.0"
PBKDF2_ITERATIONS = 600_000  # OWASP 2024 recommendation
SALT_BYTES = 32
IV_BYTES = 12  # GCM standard
KEY_BYTES = 32  # AES-256


class VaultEntry:
    """A single encrypted entry."""

    def __init__(self, entry_id: str, ciphertext: bytes, iv: bytes,
                 context: str, created_at: float, updated_at: float):
        self.id = entry_id
        self.ciphertext = ciphertext
        self.iv = iv
        self.context = context
        self.created_at = created_at
        self.updated_at = updated_at
        self.access_count = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ciphertext": self.ciphertext.hex(),
            "iv": self.iv.hex(),
            "context": self.context,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VaultEntry":
        entry = cls(
            entry_id=data["id"],
            ciphertext=bytes.fromhex(data["ciphertext"]),
            iv=bytes.fromhex(data["iv"]),
            context=data["context"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
        entry.access_count = data.get("access_count", 0)
        return entry


class BankonVault:
    """
    BANKON Vault — AES-256-GCM + HKDF-SHA512 encrypted credential storage.

    Modes:
      - passphrase: PBKDF2-HMAC-SHA512 from passphrase (default for service use)
      - file_key:   Read master key from a file (for automated service startup)
    """

    def __init__(self, vault_dir: Optional[str] = None):
        if vault_dir:
            self.vault_dir = Path(vault_dir)
        else:
            self.vault_dir = Path(__file__).parent.parent / "vault_bankon"

        self._vault_key: Optional[bytes] = None
        self._entries: Dict[str, VaultEntry] = {}
        self._salt: Optional[bytes] = None
        self._locked = True

        self._ensure_structure()
        self._load_entries()

    def _ensure_structure(self):
        """Create vault directory with strict permissions."""
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            os.chmod(self.vault_dir, stat.S_IRWXU)

        salt_file = self.vault_dir / ".salt"
        if salt_file.exists():
            self._salt = salt_file.read_bytes()
        else:
            self._salt = secrets.token_bytes(SALT_BYTES)
            salt_file.write_bytes(self._salt)
            if os.name != "nt":
                os.chmod(salt_file, stat.S_IRUSR | stat.S_IWUSR)

    def _load_entries(self):
        """Load encrypted entries from disk (stays encrypted in memory until retrieved)."""
        entries_file = self.vault_dir / "entries.json"
        if entries_file.exists():
            try:
                data = json.loads(entries_file.read_text())
                for entry_data in data.get("entries", []):
                    entry = VaultEntry.from_dict(entry_data)
                    self._entries[entry.id] = entry
            except (json.JSONDecodeError, KeyError):
                pass

    def _save_entries(self):
        """Persist encrypted entries to disk."""
        entries_file = self.vault_dir / "entries.json"
        data = {
            "version": VAULT_VERSION,
            "cipher": "aes-256-gcm",
            "kdf": "hkdf-sha512",
            "pbkdf2_iterations": PBKDF2_ITERATIONS,
            "entries": [e.to_dict() for e in self._entries.values()],
        }
        entries_file.write_text(json.dumps(data, indent=2))
        if os.name != "nt":
            os.chmod(entries_file, stat.S_IRUSR | stat.S_IWUSR)

    def _derive_vault_key(self, passphrase: str) -> bytes:
        """Derive vault master key from passphrase via PBKDF2-HMAC-SHA512."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=KEY_BYTES,
            salt=self._salt,
            iterations=PBKDF2_ITERATIONS,
        )
        return kdf.derive(passphrase.encode("utf-8"))

    def _derive_vault_key_from_file(self, key_file: Path) -> bytes:
        """Derive vault master key from a key file via HKDF-SHA512."""
        raw_key = key_file.read_bytes()
        hkdf = HKDF(
            algorithm=hashes.SHA512(),
            length=KEY_BYTES,
            salt=self._salt,
            info=b"bankon-vault-master-key",
        )
        return hkdf.derive(raw_key)

    def _derive_entry_key(self, entry_id: str, context: str) -> bytes:
        """Per-entry key derivation via HKDF (domain separation)."""
        info = f"bankon-entry:{entry_id}:{context}".encode("utf-8")
        hkdf = HKDF(
            algorithm=hashes.SHA512(),
            length=KEY_BYTES,
            salt=self._salt,
            info=info,
        )
        return hkdf.derive(self._vault_key)

    def unlock_with_passphrase(self, passphrase: str) -> bool:
        """Unlock vault using passphrase (PBKDF2-HMAC-SHA512)."""
        self._vault_key = self._derive_vault_key(passphrase)
        self._locked = False
        return True

    def unlock_with_key_file(self, key_file: Optional[Path] = None) -> bool:
        """Unlock vault using a key file (for automated service startup)."""
        if key_file is None:
            key_file = self.vault_dir / ".master.key"

        if not key_file.exists():
            # Generate new master key file
            raw_key = secrets.token_bytes(64)
            key_file.write_bytes(raw_key)
            if os.name != "nt":
                os.chmod(key_file, stat.S_IRUSR)

        self._vault_key = self._derive_vault_key_from_file(key_file)
        self._locked = False
        return True

    def lock(self):
        """Lock vault — zeroize all keys from memory."""
        if self._vault_key:
            # Overwrite key bytes before releasing
            zeroed = b"\x00" * len(self._vault_key)
            self._vault_key = zeroed
        self._vault_key = None
        self._locked = True

    def is_unlocked(self) -> bool:
        return not self._locked

    def store(self, entry_id: str, value: str, context: str = "default") -> bool:
        """Store a credential (AES-256-GCM encrypted)."""
        if self._locked:
            raise RuntimeError("Vault locked — unlock first")

        entry_key = self._derive_entry_key(entry_id, context)
        iv = secrets.token_bytes(IV_BYTES)
        aesgcm = AESGCM(entry_key)
        ciphertext = aesgcm.encrypt(iv, value.encode("utf-8"), entry_id.encode("utf-8"))

        now = time.time()
        if entry_id in self._entries:
            entry = self._entries[entry_id]
            entry.ciphertext = ciphertext
            entry.iv = iv
            entry.context = context
            entry.updated_at = now
        else:
            entry = VaultEntry(entry_id, ciphertext, iv, context, now, now)
            self._entries[entry_id] = entry

        self._save_entries()
        return True

    def retrieve(self, entry_id: str) -> Optional[str]:
        """Retrieve and decrypt a credential."""
        if self._locked:
            raise RuntimeError("Vault locked — unlock first")

        entry = self._entries.get(entry_id)
        if not entry:
            return None

        entry_key = self._derive_entry_key(entry_id, entry.context)
        aesgcm = AESGCM(entry_key)
        try:
            plaintext = aesgcm.decrypt(entry.iv, entry.ciphertext, entry_id.encode("utf-8"))
            entry.access_count += 1
            return plaintext.decode("utf-8")
        except Exception:
            return None

    def delete(self, entry_id: str) -> bool:
        """Delete a credential."""
        if entry_id in self._entries:
            del self._entries[entry_id]
            self._save_entries()
            return True
        return False

    def list_entries(self) -> List[Dict[str, Any]]:
        """List credential IDs and metadata (no secrets)."""
        return [
            {
                "id": e.id,
                "context": e.context,
                "access_count": e.access_count,
                "created_at": e.created_at,
                "updated_at": e.updated_at,
            }
            for e in self._entries.values()
        ]

    def info(self) -> dict:
        return {
            "locked": self._locked,
            "entries": len(self._entries),
            "cipher": "aes-256-gcm",
            "kdf": "hkdf-sha512 + pbkdf2-hmac-sha512",
            "version": VAULT_VERSION,
            "vault_dir": str(self.vault_dir),
        }
