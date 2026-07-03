#!/usr/bin/env python3
# GNUVAULT / Mausoleum — a place that holds many tombs.
# Copyright (C) 2026 cypherpunk2048 / BANKON.
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.  Distributed WITHOUT ANY WARRANTY.  See <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Mausoleum — multi-tomb management for GNUVAULT.

The Tomb suite, resurrected and made plural: a *Mausoleum* is a directory that
holds many *tombs* (each tomb is one GNUVAULT sealed bundle). It is the standalone
GNU answer to mindX's production **BANKON Vault**, and it deliberately improves
on it where the production version is closed-by-omission:

  • multi-vault by construction — BANKON is one vault per instance; a Mausoleum
    holds as many tombs as you like, each independently keyed.
  • **key export = extraction → sovereignty** — BANKON can rotate *within* the
    vault but has no first-class "give me my key and let me leave"; the
    Mausoleum's `extract_key()`/`export_key()` is exactly that exit. The whole
    point of the cypherpunk2048 standard: you can always walk out with your key.
  • portable + standalone — no FastAPI, no web3, no service. Pure stdlib +
    `cryptography`. Deployable on its own; destined for https://github.com/gnugui.

Lineage it learned from (see LINEAGE.md): BANKON Vault (PBKDF2-600k + HKDF-SHA512
+ AES-256-GCM + atomic rotation), bankoneth (pluggable overseer protocol),
DeltaVerse (AAD-bound sealing), parsec-wallet (Tomb USB cold storage). GNUGUI is
the public-facing client BANKON will ship on top of this.

Security slogans this module keeps in mind:
  • "if you can touch it you own it"
  • "The words computer and security should not be used in the same sentence"
    (note: with no punctuation, the statement stays true)
  • "The only real security is to build your own."
  • take it, own it, use it, share it.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from gnuvault import GnuVault, SealedBundle, CYPHERPUNK2048_STANDARD

SLOGANS = (
    "if you can touch it you own it",
    "The words computer and security should not be used in the same sentence",
    "The only real security is to build your own.",
    "take it, own it, use it, share it.",
)

_TOMB_SUFFIX = ".tomb.json"


@dataclass(frozen=True)
class TombInfo:
    name: str
    path: str
    kdf: str
    bytes: int
    sealed_at: Optional[float]


class Mausoleum:
    """A directory of tombs. Each tomb is an independently-keyed GNUVAULT bundle."""

    def __init__(self, root: str | Path = "~/.gnuvault/mausoleum", *, opaque: bool = False) -> None:
        """``opaque=True`` seals the *inventory*: tombs are stored under the
        SHA-256 of their name, so a directory listing leaks no labels. You must
        know a tomb's name to address it (the sealed-inventory property);
        ``list_tombs()`` can then only report opaque hashes."""
        self.root = Path(os.path.expanduser(str(root)))
        self.root.mkdir(parents=True, exist_ok=True)
        self.opaque = bool(opaque)
        self._v = GnuVault()

    # ── inventory ──────────────────────────────────────────────────
    def _aad(self, name: str) -> bytes:
        """AES-GCM associated data binding a bundle to THIS tomb's identity, so a
        sealed file relocated to another tomb name fails to open (authenticated,
        not secret). Computed from the name at seal AND open — never stored."""
        return (self._v.KDF_ID + "|tomb:" + name).encode("utf-8")

    def _tomb_path(self, name: str) -> Path:
        if self.opaque:
            stem = hashlib.sha256(("gnuvault-tomb:" + name).encode("utf-8")).hexdigest()[:32]
        else:
            stem = "".join(c for c in name if c.isalnum() or c in "-_.").strip(".") or "tomb"
        return self.root / f"{stem}{_TOMB_SUFFIX}"

    def _open_secret(self, name: str, passphrase: str) -> bytes:
        """Open a tomb, binding AAD to the name; fall back to the legacy
        (KDF-id) AAD for tombs sealed before v0.0.4."""
        from overseer import PassphraseOverseer
        ov = PassphraseOverseer(passphrase)
        bundle = self._load(name)
        try:
            return self._v.open_with(ov, bundle, aad=self._aad(name))
        except Exception:
            return self._v.open_with(ov, bundle, aad=None)  # legacy pre-v0.0.4

    def list_tombs(self) -> List[TombInfo]:
        out: List[TombInfo] = []
        for p in sorted(self.root.glob(f"*{_TOMB_SUFFIX}")):
            try:
                meta = json.loads(p.read_text())
            except Exception:
                continue
            out.append(TombInfo(
                name=p.name[: -len(_TOMB_SUFFIX)], path=str(p),
                kdf=meta.get("kdf", "?"), bytes=p.stat().st_size,
                sealed_at=meta.get("_sealed_at"),
            ))
        return out

    # ── inter / exhume (seal / open) ───────────────────────────────
    def inter(self, name: str, secret: str | bytes, passphrase: str) -> TombInfo:
        """Seal ``secret`` into a new tomb named ``name``. Refuses to overwrite."""
        from overseer import PassphraseOverseer
        path = self._tomb_path(name)
        if path.exists():
            raise FileExistsError(f"tomb already exists: {path} (forget it first)")
        bundle = self._v.seal_with(PassphraseOverseer(passphrase), secret, aad=self._aad(name))
        envelope = json.loads(bundle.to_json())
        envelope["_sealed_at"] = time.time()
        # Atomic write (BANKON discipline): temp + os.replace.
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(envelope, indent=2))
        os.replace(tmp, path)
        return TombInfo(name=name, path=str(path), kdf=bundle.kdf,
                        bytes=path.stat().st_size, sealed_at=envelope["_sealed_at"])

    def exhume(self, name: str, passphrase: str) -> bytes:
        """Open a tomb and return its secret. Wrong passphrase (or a relocated
        tomb whose AAD no longer matches its name) fails closed."""
        return self._open_secret(name, passphrase)

    # ── the exit: extraction → sovereignty ─────────────────────────
    def extract_key(self, name: str, passphrase: str) -> bytes:
        """Pull the 32-byte key OUT of the tomb. Once held, the key is sovereign.
        This is the guaranteed exit the cypherpunk2048 standard requires."""
        return self._v.extract_key(self._load(name), passphrase)

    def export_key(self, name: str, passphrase: str, *, fmt: str = "hex") -> str:
        """Export the extracted key for cold storage / your own build.
        fmt ∈ {hex, base64, pem}. The key leaves the running system, sovereign."""
        import base64
        from gnuvault import key_to_pem
        key = self.extract_key(name, passphrase)
        if fmt == "pem":
            return key_to_pem(key)
        if fmt == "base64":
            return base64.b64encode(key).decode("ascii")
        return key.hex()

    def export_keystore(self, name: str, passphrase: str, export_passphrase: str) -> str:
        """Export a tomb's *secret* as a portable, re-encrypted keystore (a
        GNUVAULT bundle sealed under ``export_passphrase``). Move it anywhere;
        open it with ``GnuVault().open(SealedBundle.from_json(text), export_pw)``.
        The on-host passphrase never leaves; the secret is never exposed."""
        secret = self._open_secret(name, passphrase)
        return self._v.seal(secret, export_passphrase).to_json()

    def rekey(self, name: str, old_passphrase: str, new_passphrase: str) -> TombInfo:
        """Rotate a tomb's passphrase in place (atomic). Fails closed on a wrong
        old passphrase. The secret is never written to disk in the clear."""
        from overseer import PassphraseOverseer
        path = self._tomb_path(name)
        secret = self._open_secret(name, old_passphrase)  # name-bound, legacy fallback
        new_bundle = self._v.seal_with(PassphraseOverseer(new_passphrase), secret, aad=self._aad(name))
        envelope = json.loads(new_bundle.to_json())
        envelope["_sealed_at"] = time.time()
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(envelope, indent=2))
        os.replace(tmp, path)
        return TombInfo(name=name, path=str(path), kdf=new_bundle.kdf,
                        bytes=path.stat().st_size, sealed_at=envelope["_sealed_at"])

    # ── custody housekeeping ───────────────────────────────────────
    def forget(self, name: str) -> bool:
        """Remove a tomb from the mausoleum (does not shred external copies)."""
        path = self._tomb_path(name)
        if path.exists():
            path.unlink()
            return True
        return False

    @staticmethod
    def detect_removable_mounts() -> List[str]:
        """Find likely removable / USB mount points (the Tomb cold-storage
        pattern). Cross-platform best-effort; returns writable directories."""
        import getpass
        user = ""
        try:
            user = getpass.getuser()
        except Exception:
            user = os.environ.get("USER", "")
        candidates = [
            f"/media/{user}", "/media", "/mnt",
            f"/run/media/{user}", "/Volumes",   # Linux + macOS
        ]
        out: List[str] = []
        for c in candidates:
            base = Path(c)
            if not base.is_dir():
                continue
            for child in sorted(base.iterdir()) if base.name in ("media", user or "x", "Volumes") else []:
                if child.is_dir() and os.access(child, os.W_OK):
                    out.append(str(child))
            if os.access(base, os.W_OK) and base.name in ("mnt",):
                out.append(str(base))
        return out

    def backup(self, dest: str | Path, *, verify: bool = True) -> List[str]:
        """Copy every tomb to ``dest`` (e.g. a USB mount). With ``verify`` (default),
        each copy is read back and its SHA-256 compared to the source — a backup
        you have not verified is a hope, not a backup. Raises on mismatch."""
        import hashlib as _h
        dest = Path(os.path.expanduser(str(dest)))
        dest.mkdir(parents=True, exist_ok=True)
        written: List[str] = []
        for p in self.root.glob(f"*{_TOMB_SUFFIX}"):
            data = p.read_bytes()
            target = dest / p.name
            target.write_bytes(data)
            if verify and _h.sha256(target.read_bytes()).hexdigest() != _h.sha256(data).hexdigest():
                raise IOError(f"backup verification FAILED for {target}")
            written.append(str(target))
        return written

    def verify_backup(self, dest: str | Path) -> Dict[str, bool]:
        """Compare each tomb in the mausoleum against its copy in ``dest`` by
        SHA-256. Returns {tomb_filename: matches}. Missing copies → False."""
        import hashlib as _h
        dest = Path(os.path.expanduser(str(dest)))
        out: Dict[str, bool] = {}
        for p in self.root.glob(f"*{_TOMB_SUFFIX}"):
            t = dest / p.name
            out[p.name] = bool(t.exists()
                               and _h.sha256(t.read_bytes()).hexdigest()
                               == _h.sha256(p.read_bytes()).hexdigest())
        return out

    def restore_from(self, src: str | Path) -> List[str]:
        """Restore tombs from a cold-storage directory into this mausoleum
        (copies any ``*.tomb.json`` not already present). Returns names restored."""
        src = Path(os.path.expanduser(str(src)))
        restored: List[str] = []
        for p in sorted(src.glob(f"*{_TOMB_SUFFIX}")):
            target = self.root / p.name
            if not target.exists():
                target.write_bytes(p.read_bytes())
                restored.append(p.name[: -len(_TOMB_SUFFIX)])
        return restored

    def import_tomb(self, path: str | Path) -> TombInfo:
        """Bring an external tomb file into the mausoleum."""
        src = Path(os.path.expanduser(str(path)))
        SealedBundle.from_json(src.read_text())  # validate shape
        name = src.name[: -len(_TOMB_SUFFIX)] if src.name.endswith(_TOMB_SUFFIX) else src.stem
        target = self._tomb_path(name)
        target.write_bytes(src.read_bytes())
        meta = json.loads(target.read_text())
        return TombInfo(name=name, path=str(target), kdf=meta.get("kdf", "?"),
                        bytes=target.stat().st_size, sealed_at=meta.get("_sealed_at"))

    def _load(self, name: str) -> SealedBundle:
        path = self._tomb_path(name)
        if not path.exists():
            raise FileNotFoundError(f"no such tomb: {name}")
        return SealedBundle.from_json(path.read_text())


def _selftest() -> bool:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        m = Mausoleum(d)
        m.inter("alpha", "first secret", "pw-alpha")
        m.inter("beta", "second secret", "pw-beta")
        assert {t.name for t in m.list_tombs()} == {"alpha", "beta"}
        assert m.exhume("alpha", "pw-alpha").decode() == "first secret"
        try:
            m.exhume("alpha", "wrong"); raise AssertionError("wrong pw opened tomb")
        except Exception as e:
            if isinstance(e, AssertionError):
                raise
        k = m.export_key("beta", "pw-beta", fmt="hex")
        assert len(k) == 64  # 32 bytes hex
        assert m.forget("alpha") and not m.forget("alpha")
        print(f"Mausoleum selftest OK — multi-tomb + key export (sovereign exit); "
              f"standard: {CYPHERPUNK2048_STANDARD}")
    return True


if __name__ == "__main__":
    _selftest()
