#!/usr/bin/env python3
# GNUVAULT test suite. GPL-3.0-or-later.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Tests for GNUVAULT. Runs under pytest, or standalone (`python3 test_gnuvault.py`).
Operational transparency includes verifiability: you should be able to check the
claims yourself in seconds, without trusting us.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gnuvault import GnuVault, SealedBundle              # noqa: E402
from mausoleum import Mausoleum                          # noqa: E402
from overseer import (PassphraseOverseer, KeyfileOverseer,   # noqa: E402
                      WalletSignatureOverseer)


def test_seal_open_roundtrip():
    v = GnuVault()
    b = v.seal("hello sovereign", "pw")
    assert v.open(SealedBundle.from_json(b.to_json()), "pw").decode() == "hello sovereign"


def test_wrong_passphrase_fails_closed():
    v = GnuVault()
    b = v.seal("secret", "right")
    try:
        v.open(b, "wrong")
    except Exception:
        return  # expected — authenticated decryption fails, never returns garbage
    raise AssertionError("wrong passphrase did not fail closed")


def test_extract_key_is_32_bytes_and_deterministic():
    v = GnuVault()
    b = v.seal("x", "pw")
    k1 = v.extract_key(b, "pw")
    k2 = v.extract_key(b, "pw")
    assert len(k1) == 32 and k1 == k2          # same bundle + pw → same key (sovereign, reproducible)


def test_rekey_changes_envelope_keeps_secret():
    v = GnuVault()
    b1 = v.seal("constant secret", "old-pw")
    b2 = v.rekey(b1, "old-pw", "new-pw")
    assert v.open(b2, "new-pw").decode() == "constant secret"
    assert b2.salt != b1.salt and b2.ct != b1.ct      # fresh salt + ciphertext
    try:
        v.open(b2, "old-pw"); raise AssertionError("old passphrase still worked after rekey")
    except Exception as e:
        if isinstance(e, AssertionError):
            raise


def test_mausoleum_multi_tomb_and_export():
    with tempfile.TemporaryDirectory() as d:
        m = Mausoleum(d)
        m.inter("a", "secret-a", "pw-a")
        m.inter("b", "secret-b", "pw-b")
        assert {t.name for t in m.list_tombs()} == {"a", "b"}
        assert m.exhume("a", "pw-a").decode() == "secret-a"
        assert len(m.export_key("b", "pw-b")) == 64          # 32 bytes hex
        m.rekey("a", "pw-a", "pw-a2")
        assert m.exhume("a", "pw-a2").decode() == "secret-a"
        assert m.forget("a") and not m.forget("a")


def test_no_overwrite_without_forget():
    with tempfile.TemporaryDirectory() as d:
        m = Mausoleum(d)
        m.inter("dup", "first", "pw")
        try:
            m.inter("dup", "second", "pw"); raise AssertionError("overwrote a tomb")
        except FileExistsError:
            pass


def test_keyfile_overseer_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        kf = Path(d) / "master.key"
        kf.write_bytes(b"\x01" * 64)
        v = GnuVault()
        b = v.seal_with(KeyfileOverseer(kf), "keyfile secret")
        assert v.open_with(KeyfileOverseer(kf), b).decode() == "keyfile secret"
        # A different key file must fail closed.
        kf2 = Path(d) / "other.key"; kf2.write_bytes(b"\x02" * 64)
        try:
            v.open_with(KeyfileOverseer(kf2), b); raise AssertionError("wrong keyfile opened")
        except Exception as e:
            if isinstance(e, AssertionError):
                raise


def test_wallet_signature_overseer_is_deterministic():
    v = GnuVault()
    sig = "0x" + "ab" * 65                       # a stand-in 65-byte signature
    b = v.seal_with(WalletSignatureOverseer(sig), "wallet secret")
    # same signature reproduces custody (no signature stored)
    assert v.open_with(WalletSignatureOverseer(sig), b).decode() == "wallet secret"
    try:
        v.open_with(WalletSignatureOverseer("0x" + "cd" * 65), b); raise AssertionError("wrong sig opened")
    except Exception as e:
        if isinstance(e, AssertionError):
            raise


def test_rekey_passphrase_to_wallet():
    v = GnuVault()
    b1 = v.seal_with(PassphraseOverseer("human-pw"), "migrating secret")
    sig = "0x" + "11" * 65
    b2 = v.rekey_with(PassphraseOverseer("human-pw"), WalletSignatureOverseer(sig), b1)
    assert v.open_with(WalletSignatureOverseer(sig), b2).decode() == "migrating secret"
    try:
        v.open_with(PassphraseOverseer("human-pw"), b2); raise AssertionError("old custodian still worked")
    except Exception as e:
        if isinstance(e, AssertionError):
            raise


def test_aad_binds_to_tomb_name():
    import shutil
    with tempfile.TemporaryDirectory() as d:
        m = Mausoleum(d)
        m.inter("alpha", "bound secret", "pw")
        shutil.copy(m._tomb_path("alpha"), m._tomb_path("beta"))   # relocate the file
        try:
            m.exhume("beta", "pw"); raise AssertionError("relocated tomb opened (AAD not bound)")
        except Exception as e:
            if isinstance(e, AssertionError):
                raise
        assert m.exhume("alpha", "pw").decode() == "bound secret"  # original still opens


def test_opaque_inventory_hides_labels():
    with tempfile.TemporaryDirectory() as d:
        m = Mausoleum(d, opaque=True)
        m.inter("my-private-label", "s", "pw")
        files = [p.name for p in Path(d).glob("*.tomb.json")]
        assert files and all("my-private-label" not in f for f in files)
        assert m.exhume("my-private-label", "pw").decode() == "s"


def test_legacy_pre_v004_tomb_opens():
    import json as _j, time as _t
    with tempfile.TemporaryDirectory() as d:
        m = Mausoleum(d)
        b = GnuVault().seal("legacy secret", "pw")    # default (KDF-id) AAD, as pre-v0.0.4
        env = _j.loads(b.to_json()); env["_sealed_at"] = _t.time()
        m._tomb_path("legacy").write_text(_j.dumps(env))
        assert m.exhume("legacy", "pw").decode() == "legacy secret"     # opens via fallback
        m.rekey("legacy", "pw", "pw2")                                  # upgrades to name-bound AAD
        assert m.exhume("legacy", "pw2").decode() == "legacy secret"


def test_airgap_signature_custody_roundtrip():
    import airgap as ag
    priv, pub = ag.ed25519_keygen()
    ch = ag.airgap_challenge("vault-1")
    sig = ag.ed25519_sign(priv, ch)
    assert ag.ed25519_verify(pub, sig, ch)
    v = GnuVault()
    ov = ag.overseer_from_signature(sig, ch)
    b = v.seal_with(ov, "airgapped secret")
    # reproduce custody from the key alone (sign again → same signature)
    ov2 = ag.overseer_from_signature(ag.ed25519_sign(priv, ch), ch)
    assert v.open_with(ov2, b).decode() == "airgapped secret"


def test_pem_key_roundtrip():
    from gnuvault import key_to_pem, key_from_pem
    import os as _os
    k = _os.urandom(32)
    pem = key_to_pem(k)
    assert "BEGIN GNUVAULT KEY" in pem and key_from_pem(pem) == k


def test_export_keystore_is_portable():
    with tempfile.TemporaryDirectory() as d:
        m = Mausoleum(d)
        m.inter("acct", "portable secret", "host-pw")
        ks = m.export_keystore("acct", "host-pw", "export-pw")
        # open the keystore anywhere, with only the export passphrase
        assert GnuVault().open(SealedBundle.from_json(ks), "export-pw").decode() == "portable secret"
        # pem export is well-formed
        from gnuvault import key_from_pem
        pem = m.export_key("acct", "host-pw", fmt="pem")
        assert len(key_from_pem(pem)) == 32


def test_backup_verify_and_restore():
    with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as usb:
        m = Mausoleum(d)
        m.inter("cold-a", "secret a", "pw")
        m.inter("cold-b", "secret b", "pw")
        written = m.backup(usb, verify=True)          # raises if a copy mismatches
        assert len(written) == 2
        assert all(m.verify_backup(usb).values())
        # corrupt a backup → verify must catch it
        bad = sorted(Path(usb).glob("*.tomb.json"))[0]
        bad.write_text(bad.read_text() + " ")
        assert not all(m.verify_backup(usb).values())
        # restore into a fresh mausoleum from cold storage
        with tempfile.TemporaryDirectory() as d2:
            m2 = Mausoleum(d2)
            assert sorted(m2.restore_from(usb)) == ["cold-a", "cold-b"]
            assert m2.exhume("cold-b", "pw").decode() == "secret b"


def test_detect_removable_mounts_is_a_list():
    assert isinstance(Mausoleum.detect_removable_mounts(), list)   # never raises


def test_fuzz_roundtrip_random():
    import os as _os, random as _r
    v = GnuVault()
    for _ in range(60):
        secret = _os.urandom(_r.randint(0, 200))
        pw = _os.urandom(_r.randint(1, 40)).hex()
        b = v.seal(secret, pw)
        assert v.open(SealedBundle.from_json(b.to_json()), pw) == secret


def test_tamper_any_field_fails_closed():
    import base64 as _b64
    v = GnuVault()
    b = v.seal("integrity matters", "pw")
    for field in ("ct", "nonce", "salt"):
        raw = bytearray(_b64.b64decode(getattr(b, field)))
        if not raw:
            continue
        raw[0] ^= 0x01                                   # flip one bit
        fields = {"kdf": b.kdf, "salt": b.salt, "nonce": b.nonce, "ct": b.ct}
        fields[field] = _b64.b64encode(bytes(raw)).decode()
        tampered = SealedBundle(**fields)
        try:
            v.open(tampered, "pw"); raise AssertionError(f"tamper of {field} not caught")
        except Exception as e:
            if isinstance(e, AssertionError):
                raise


def test_wipe_zeroes_bytearray():
    from gnuvault import wipe
    buf = bytearray(b"\xff" * 32)
    wipe(buf)
    assert buf == bytearray(32)
    wipe(b"immutable")          # must not raise on immutables


def test_gnugui_headless_and_actions_present():
    import gnugui
    assert gnugui.main(["--headless"]) == 0     # no display → clean exit
    for meth in ("_inter", "_exhume", "_rekey", "_export", "_backup",
                 "_import", "_forget", "_refresh", "_draw"):
        assert hasattr(gnugui.GnuGui, meth), f"GnuGui missing {meth}"


def test_full_lifecycle_integration():
    with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as usb:
        m = Mausoleum(d)
        m.inter("acct", "lifecycle secret", "pw1")
        assert m.exhume("acct", "pw1").decode() == "lifecycle secret"
        m.rekey("acct", "pw1", "pw2")
        assert m.exhume("acct", "pw2").decode() == "lifecycle secret"
        assert len(m.export_key("acct", "pw2")) == 64
        ks = m.export_keystore("acct", "pw2", "exp-pw")
        assert GnuVault().open(SealedBundle.from_json(ks), "exp-pw").decode() == "lifecycle secret"
        m.backup(usb, verify=True)
        assert all(m.verify_backup(usb).values())
        m.forget("acct")
        assert not m.list_tombs()
        assert sorted(m.restore_from(usb)) == ["acct"]
        assert m.exhume("acct", "pw2").decode() == "lifecycle secret"   # full circle


def _run_standalone() -> int:
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"  PASS {fn.__name__}")
        except Exception as e:  # noqa: BLE001
            failed += 1; print(f"  FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_standalone())
