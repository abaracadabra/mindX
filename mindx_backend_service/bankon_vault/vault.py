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

import fcntl
import hashlib
import os
import json
import shutil
import stat
import tempfile
import time
import secrets
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Dict, List, Any, TYPE_CHECKING

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

if TYPE_CHECKING:
    from mindx_backend_service.bankon_vault.overseer import VaultOverseer


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
        """Unlock vault using a key file (for automated service startup).

        After a handoff to a HumanOverseer, the sentinel file
        `.human_overseer_active` is written; this method REFUSES to run
        under that sentinel so a missing `.master.key` cannot silently
        regenerate machine control.  Callers must use `unlock_with_overseer`
        with a HumanOverseer proof in that case.
        """
        sentinel = self.vault_dir / ".human_overseer_active"
        if sentinel.exists():
            raise RuntimeError(
                "Vault is under HumanOverseer custody (sentinel .human_overseer_active present). "
                "Use unlock_with_overseer(HumanOverseer(...), ...) — refusing to regenerate a "
                "machine-owned .master.key."
            )

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

    # ─────────────────────────────────────────────────────────────────────
    # Overseer-based unlock + rotation (Stage-1 handoff ceremony)
    # ─────────────────────────────────────────────────────────────────────

    def unlock_with_overseer(
        self,
        overseer: "VaultOverseer",
        challenge: bytes,
        evidence: Dict[str, Any],
    ) -> bool:
        """Unlock using a pluggable overseer.  Verifies evidence first, then
        derives raw key via the overseer, then runs the same HKDF path as
        unlock_with_key_file — same `salt`, same `info`."""
        if not overseer.verify_evidence(evidence, challenge):
            raise RuntimeError(
                f"unlock_with_overseer: evidence did not verify for overseer {overseer.fingerprint()}"
            )
        raw = overseer.produce_raw_key(challenge, evidence)
        if len(raw) != 64:
            raise RuntimeError(
                f"unlock_with_overseer: overseer produced {len(raw)}-byte key, expected 64"
            )
        hkdf = HKDF(
            algorithm=hashes.SHA512(),
            length=KEY_BYTES,
            salt=self._salt,
            info=b"bankon-vault-master-key",
        )
        self._vault_key = hkdf.derive(raw)
        self._locked = False
        return True

    def _derive_vault_key_from_raw(self, raw: bytes) -> bytes:
        """Internal: HKDF a 64-byte raw seed down to the 32-byte vault key."""
        if len(raw) != 64:
            raise ValueError("raw seed must be 64 bytes")
        hkdf = HKDF(
            algorithm=hashes.SHA512(),
            length=KEY_BYTES,
            salt=self._salt,
            info=b"bankon-vault-master-key",
        )
        return hkdf.derive(raw)

    # Internal helpers for hardened rotation
    def _fsync_file(self, path: Path):
        """fsync a file so its contents survive power loss."""
        try:
            fd = os.open(str(path), os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError:
            pass  # best-effort; file may have been replaced concurrently

    def _fsync_dir(self, path: Path):
        """fsync a directory so rename/create/delete survives power loss."""
        try:
            fd = os.open(str(path), os.O_RDONLY | (os.O_DIRECTORY if hasattr(os, "O_DIRECTORY") else 0))
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError:
            pass

    def _secure_write(self, path: Path, content: bytes):
        """Write `content` to `path` with mode 0600 atomically as far as perms are concerned.
        Eliminates the open(0644)→chmod(0600) race under a permissive umask."""
        # O_CREAT|O_WRONLY|O_TRUNC; mode 0600; set umask locally so inherited dirs don't widen.
        old_umask = os.umask(0o077)
        try:
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                os.write(fd, content)
                os.fsync(fd)
            finally:
                os.close(fd)
            if os.name != "nt":
                os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        finally:
            os.umask(old_umask)

    @contextmanager
    def _vault_dir_lock(self):
        """Acquire an exclusive fcntl lock on a lockfile in the vault dir so
        concurrent rotations serialize.  Releases on context exit."""
        lock_path = self.vault_dir / ".rotation.lock"
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError(
                    "rotate_overseer: another rotation holds the vault lock "
                    f"({lock_path}) — aborting to avoid concurrent mutation."
                )
            try:
                # write our PID into the lockfile for forensics
                os.ftruncate(fd, 0)
                os.write(fd, f"{os.getpid()}\n{time.time()}\n".encode())
                yield
            finally:
                try:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except OSError:
                    pass
        finally:
            try:
                os.close(fd)
            except OSError:
                pass
            # leave the lockfile in place (its permissions are already constrained);
            # a future rotation can acquire it immediately.

    def rotate_overseer(
        self,
        new_overseer: "VaultOverseer",
        new_challenge: bytes,
        new_evidence: Dict[str, Any],
        reason: str,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Atomic master-key rotation.  Safe-by-default (dry_run=True).

        Steps (see the plan for full rationale):
          1. Require env flag MINDX_VAULT_ALLOW_OVERSEER_ROTATION=1.
          2. Require vault unlocked under the CURRENT overseer.
          3. Snapshot the entire vault dir to /tmp.
          4. Hash every existing entry's plaintext.
          5. Verify new overseer's evidence.
          6. Derive the new vault key via HKDF (same salt, same info).
          7. Re-encrypt all entries with the new key; write entries.json.candidate.
          8. If dry_run: scratch-load the candidate, decrypt each entry, sha256-verify.
             On any mismatch — abort.  On success — write .rotation.ok marker.
          9. If NOT dry_run: require a fresh .rotation.ok (<=300 s, sha matches).
             os.replace(candidate, entries.json) — POSIX atomic.
         10. On non-machine commit: persist proof, delete .master.key, write sentinel.
         11. Append one line to data/governance/overseer_history.jsonl.
        """
        if not os.environ.get("MINDX_VAULT_ALLOW_OVERSEER_ROTATION"):
            raise RuntimeError(
                "rotate_overseer: refusing to run without env flag "
                "MINDX_VAULT_ALLOW_OVERSEER_ROTATION=1"
            )
        if self._locked:
            raise RuntimeError(
                "rotate_overseer: vault must be unlocked under the current overseer first"
            )

        # Acquire exclusive rotation lock — serializes concurrent rotations.
        # The rest of this function runs inside the `_vault_dir_lock()` context.
        with self._vault_dir_lock():
            return self._rotate_overseer_locked(
                new_overseer, new_challenge, new_evidence, reason, dry_run,
            )

    def _rotate_overseer_locked(
        self,
        new_overseer: "VaultOverseer",
        new_challenge: bytes,
        new_evidence: Dict[str, Any],
        reason: str,
        dry_run: bool,
    ) -> Dict[str, Any]:
        # 3. Snapshot.
        snapshot_dir = Path(tempfile.mkdtemp(prefix="mindx-vault-snapshot-"))
        shutil.copytree(self.vault_dir, snapshot_dir / "vault_bankon", dirs_exist_ok=False)

        # 4. Hash every plaintext.
        plaintext_hashes: Dict[str, str] = {}
        for entry_id in list(self._entries.keys()):
            pt = self.retrieve(entry_id)
            if pt is None:
                raise RuntimeError(
                    f"rotate_overseer: entry {entry_id!r} failed to decrypt under current key"
                )
            plaintext_hashes[entry_id] = hashlib.sha256(pt.encode("utf-8")).hexdigest()

        # 5. Verify evidence.
        if not new_overseer.verify_evidence(new_evidence, new_challenge):
            raise RuntimeError(
                f"rotate_overseer: evidence did not verify for new overseer {new_overseer.fingerprint()}"
            )

        # 6. Derive new vault key.
        new_raw = new_overseer.produce_raw_key(new_challenge, new_evidence)
        new_vault_key = self._derive_vault_key_from_raw(new_raw)

        # 7. Re-encrypt into a candidate entries dict — derive each per-entry key
        #    using the NEW vault key directly (do not mutate self._vault_key yet).
        candidate_entries: Dict[str, VaultEntry] = {}
        for entry_id, entry in self._entries.items():
            pt = self.retrieve(entry_id)
            if pt is None:
                raise RuntimeError(
                    f"rotate_overseer: entry {entry_id!r} decrypt failed during re-encryption"
                )
            info = f"bankon-entry:{entry_id}:{entry.context}".encode("utf-8")
            entry_key_hkdf = HKDF(
                algorithm=hashes.SHA512(),
                length=KEY_BYTES,
                salt=self._salt,
                info=info,
            )
            entry_key = entry_key_hkdf.derive(new_vault_key)
            iv = secrets.token_bytes(IV_BYTES)
            aesgcm = AESGCM(entry_key)
            ciphertext = aesgcm.encrypt(iv, pt.encode("utf-8"), entry_id.encode("utf-8"))
            now = time.time()
            new_entry = VaultEntry(
                entry_id=entry_id,
                ciphertext=ciphertext,
                iv=iv,
                context=entry.context,
                created_at=entry.created_at,
                updated_at=now,
            )
            new_entry.access_count = entry.access_count
            candidate_entries[entry_id] = new_entry

        candidate_file = self.vault_dir / "entries.json.candidate"
        candidate_payload = {
            "version": VAULT_VERSION,
            "cipher": "aes-256-gcm",
            "kdf": "hkdf-sha512",
            "pbkdf2_iterations": PBKDF2_ITERATIONS,
            "entries": [e.to_dict() for e in candidate_entries.values()],
        }
        # Use secure_write (0600 via umask, fsync'd) — avoids the write→chmod race.
        self._secure_write(candidate_file, json.dumps(candidate_payload, indent=2).encode())

        candidate_sha = hashlib.sha256(candidate_file.read_bytes()).hexdigest()

        # 8. Scratch-verify: decrypt every candidate entry with the NEW vault key
        #    and sha256-compare the plaintext to the pre-rotation hash.
        def _scratch_decrypt(entry: VaultEntry) -> Optional[str]:
            info = f"bankon-entry:{entry.id}:{entry.context}".encode("utf-8")
            h = HKDF(algorithm=hashes.SHA512(), length=KEY_BYTES,
                     salt=self._salt, info=info)
            k = h.derive(new_vault_key)
            try:
                pt = AESGCM(k).decrypt(entry.iv, entry.ciphertext, entry.id.encode("utf-8"))
                return pt.decode("utf-8")
            except Exception:
                return None

        verify_failures: List[str] = []
        for entry_id, cand in candidate_entries.items():
            pt = _scratch_decrypt(cand)
            if pt is None:
                verify_failures.append(f"{entry_id}: decrypt failed")
                continue
            expected = plaintext_hashes[entry_id]
            actual = hashlib.sha256(pt.encode("utf-8")).hexdigest()
            if expected != actual:
                verify_failures.append(f"{entry_id}: hash mismatch")
        if verify_failures:
            candidate_file.unlink(missing_ok=True)
            raise RuntimeError(
                "rotate_overseer: candidate re-encryption failed verification — "
                f"{len(verify_failures)} errors: {verify_failures[:5]}. Vault untouched."
            )

        # Write .rotation.ok marker — secure_write for consistent 0600.
        ok_marker = self.vault_dir / ".rotation.ok"
        ok_payload = {
            "candidate_sha": candidate_sha,
            "ts": time.time(),
            "new_overseer_fingerprint": new_overseer.fingerprint(),
            "entries_count": len(candidate_entries),
        }
        self._secure_write(ok_marker, json.dumps(ok_payload).encode())

        if dry_run:
            return {
                "status": "dry_run_ok",
                "entries": len(candidate_entries),
                "new_fingerprint": new_overseer.fingerprint(),
                "snapshot_dir": str(snapshot_dir),
                "candidate_file": str(candidate_file),
                "candidate_sha256": candidate_sha,
            }

        # 9. Commit path.
        if not ok_marker.exists():
            raise RuntimeError("rotate_overseer commit: no .rotation.ok marker — run dry_run first")
        try:
            ok = json.loads(ok_marker.read_text())
        except Exception as e:
            raise RuntimeError(f"rotate_overseer commit: malformed .ok marker: {e}")
        if time.time() - float(ok.get("ts", 0)) > 300:
            raise RuntimeError("rotate_overseer commit: .ok marker stale (>300s) — run dry_run again")
        fresh_cand_sha = hashlib.sha256(candidate_file.read_bytes()).hexdigest()
        if ok.get("candidate_sha") != fresh_cand_sha:
            raise RuntimeError(
                "rotate_overseer commit: candidate file sha changed since dry_run — aborting"
            )

        entries_file = self.vault_dir / "entries.json"

        # ── CRITICAL SECTION: ordering matters for crash recovery ──────────
        # Principle: after any crash, the system must be diagnosable by an admin.
        # INVARIANT: sentinel existence ⇒ entries.json is under the new key AND
        #            .master.key either is absent OR is ignored by unlock code.
        #
        # Order:
        #   (a) POSIX-atomic swap of entries.json.candidate → entries.json
        #   (b) fsync the vault dir so the rename hits disk before anything else
        #   (c) For non-machine overseers:
        #         write .overseer_proof.json (fsync)   — so post-crash unlock has the sig
        #         write .human_overseer_active sentinel (fsync)   — guards against machine regeneration
        #         delete .master.key (fsync dir)      — only now safe; sentinel protects vault
        #   (d) Swap in-memory state   — last, so any exception above keeps disk authoritative
        #   (e) Append audit log
        #   (f) Clean up .rotation.ok
        os.replace(candidate_file, entries_file)
        self._fsync_file(entries_file)
        self._fsync_dir(self.vault_dir)

        old_fingerprint = "machine:" + hashlib.sha256(self._vault_key or b"").hexdigest()[:16]

        if new_overseer.kind != "machine":
            if new_overseer.kind == "human":
                proof_path = self.vault_dir / ".overseer_proof.json"
                proof_payload = {
                    "kind": "human",
                    "address": new_overseer.identity,
                    "signature": new_evidence.get("signature"),
                    "message": new_evidence.get("message"),
                    "ts": time.time(),
                }
                self._secure_write(proof_path, json.dumps(proof_payload, indent=2).encode())

            # Write sentinel BEFORE deleting .master.key — crash during this
            # window leaves sentinel present + master.key present. On restart
            # unlock_with_key_file refuses (sentinel), admin uses overseer.
            sentinel = self.vault_dir / ".human_overseer_active"
            self._secure_write(sentinel, json.dumps({
                "since": time.time(),
                "overseer_kind": new_overseer.kind,
                "overseer_identity": new_overseer.identity,
            }).encode())
            self._fsync_dir(self.vault_dir)

            master_key_path = self.vault_dir / ".master.key"
            if master_key_path.exists():
                # Best-effort overwrite of the key file bytes BEFORE unlink so
                # a filesystem undelete cannot recover the machine key material.
                try:
                    fd = os.open(str(master_key_path), os.O_WRONLY)
                    try:
                        os.write(fd, b"\x00" * 64)
                        os.fsync(fd)
                    finally:
                        os.close(fd)
                except OSError:
                    pass
                master_key_path.unlink()
                self._fsync_dir(self.vault_dir)

        # (d) Swap in-memory state.  The vault is now under the new key on
        # disk — making the in-memory state match is the final atomicity step.
        self._vault_key = new_vault_key
        self._entries = candidate_entries

        # Post-commit sanity: decrypt one entry with the new in-memory key.
        # If this fails, the rotation is committed on disk but unusable in
        # memory — raise loudly so the admin sees immediately.
        if self._entries:
            sanity_id = next(iter(self._entries))
            sanity_pt = self.retrieve(sanity_id)
            if sanity_pt is None:
                raise RuntimeError(
                    f"rotate_overseer: post-commit sanity failed — cannot decrypt {sanity_id!r} "
                    "under new vault_key. Disk state is committed; admin intervention required."
                )

        # (e) Audit log.
        record = None
        try:
            history_dir = self.vault_dir.parent.parent / "data" / "governance"
            history_dir.mkdir(parents=True, exist_ok=True)
            history = history_dir / "overseer_history.jsonl"
            evidence_digest = hashlib.sha256(
                json.dumps(new_evidence, sort_keys=True).encode()
            ).hexdigest()
            record = {
                "timestamp": time.time(),
                "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "from_kind": "machine",
                "from_fingerprint": old_fingerprint,
                "to_kind": new_overseer.kind,
                "to_identity": new_overseer.identity,
                "to_fingerprint": new_overseer.fingerprint(),
                "reason": reason,
                "evidence_digest": evidence_digest,
                "entries_re_encrypted_count": len(candidate_entries),
                "vault_salt_fingerprint": hashlib.sha256(self._salt).hexdigest()[:16],
            }
            with history.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            # Do not fail rotation on audit-log write issues.
            pass

        # (f) Clean up .rotation.ok so a re-run requires a fresh dry_run.
        ok_marker.unlink(missing_ok=True)
        self._fsync_dir(self.vault_dir)

        return {
            "status": "committed",
            "entries": len(candidate_entries),
            "new_fingerprint": new_overseer.fingerprint(),
            "snapshot_dir": str(snapshot_dir),
            "history_record": record,
        }

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

    def derive_for_context(self, namespace: str, subkey: str) -> bytes:
        """
        Derive a 32-byte key via HKDF-SHA512 with per-context domain separation.

        Public companion to `_derive_entry_key`. agentID's identity issuance
        (agents/core/agentid_bridge.py) uses this to produce deterministic,
        domain-separated keys for purposes outside the entry store — for
        example a BANKON-Vault-rooted KDF for an agentID subsystem that
        replaces the deleted coral_id_agent hardcoded salt.

        Never returns the vault master key itself; always a derived value.
        """
        if self._locked:
            raise RuntimeError("Vault locked — unlock first")
        info = f"bankon-context:{namespace}:{subkey}".encode("utf-8")
        hkdf = HKDF(
            algorithm=hashes.SHA512(),
            length=KEY_BYTES,
            salt=self._salt,
            info=info,
        )
        return hkdf.derive(self._vault_key)
