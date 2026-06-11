#!/usr/bin/env python3
# GNUVAULT command-line interface.
# Copyright (C) 2026 cypherpunk2048 / BANKON.  GPL-3.0-or-later.
# SPDX-License-Identifier: GPL-3.0-or-later
"""
gnuvault — a standalone command line over a GNUVAULT Mausoleum.

    gnuvault list
    gnuvault inter   <name>            # seal a new tomb (secret + passphrase prompted)
    gnuvault exhume  <name>            # open a tomb, print the secret
    gnuvault export  <name> [--b64]    # extract the key → sovereign (hex or base64)
    gnuvault rekey   <name>            # rotate the passphrase in place
    gnuvault backup  <dest>            # copy every tomb to a directory / USB mount
    gnuvault import  <path>            # bring an external tomb in
    gnuvault forget  <name>            # remove a tomb from the mausoleum
    gnuvault gui                       # launch GNUGUI
    gnuvault selftest

Passphrases are read with getpass (never echoed, never taken on argv). The
mausoleum lives at ~/.gnuvault/mausoleum unless --root is given. Read this file;
it is short on purpose. take it, own it, use it, share it.
"""
from __future__ import annotations

import argparse
import sys
from getpass import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mausoleum import Mausoleum  # noqa: E402

VERSION = "1.0.0"


def _m(args) -> Mausoleum:
    return Mausoleum(args.root, opaque=getattr(args, "opaque", False))


def cmd_list(args) -> int:
    for t in _m(args).list_tombs():
        print(f"  ⚰ {t.name:24} {t.kdf}  ({t.bytes} bytes)")
    return 0


def cmd_inter(args) -> int:
    secret = getpass("secret to seal: ")
    pw = getpass("passphrase: ")
    if getpass("passphrase (again): ") != pw:
        print("passphrases did not match", file=sys.stderr)
        return 2
    info = _m(args).inter(args.name, secret, pw)
    print(f"sealed ⚰ {info.name} → {info.path}")
    return 0


def cmd_exhume(args) -> int:
    try:
        secret = _m(args).exhume(args.name, getpass("passphrase: "))
    except Exception:
        print("wrong passphrase (failed closed)", file=sys.stderr)
        return 1
    sys.stdout.write(secret.decode("utf-8", "replace") + "\n")
    return 0


def cmd_export(args) -> int:
    fmt = "pem" if args.pem else ("base64" if args.b64 else "hex")
    try:
        key = _m(args).export_key(args.name, getpass("passphrase: "), fmt=fmt)
    except Exception:
        print("wrong passphrase (failed closed)", file=sys.stderr)
        return 1
    print(key)
    print("# the key has left the running system — it is sovereign now.", file=sys.stderr)
    return 0


def cmd_airgap(args) -> int:
    import airgap as ag
    if args.what == "challenge":
        print(ag.airgap_challenge(args.nonce or ""))
    elif args.what == "keygen":
        priv, pub = ag.ed25519_keygen()
        print("private (keep offline): " + priv)
        print("public:                 " + pub)
    elif args.what == "sign":
        priv = getpass("ed25519 private (hex): ")
        print(ag.ed25519_sign(priv, ag.airgap_challenge(args.nonce or "")))
    return 0


def cmd_rekey(args) -> int:
    old = getpass("current passphrase: ")
    new = getpass("new passphrase: ")
    if getpass("new passphrase (again): ") != new:
        print("new passphrases did not match", file=sys.stderr)
        return 2
    try:
        _m(args).rekey(args.name, old, new)
    except Exception:
        print("wrong current passphrase (failed closed)", file=sys.stderr)
        return 1
    print(f"rekeyed ⚰ {args.name}")
    return 0


def cmd_backup(args) -> int:
    written = _m(args).backup(args.dest, verify=not args.no_verify)
    print(f"backed up {len(written)} tomb(s) → {args.dest}"
          + ("" if args.no_verify else " (sha256-verified)"))
    return 0


def cmd_usb(args) -> int:
    mounts = Mausoleum.detect_removable_mounts()
    print("\n".join(mounts) if mounts else "(no removable mounts detected)")
    return 0


def cmd_verify(args) -> int:
    res = _m(args).verify_backup(args.dest)
    ok = sum(1 for v in res.values() if v)
    for name, good in sorted(res.items()):
        print(f"  {'OK  ' if good else 'FAIL'} {name}")
    print(f"{ok}/{len(res)} verified")
    return 0 if ok == len(res) else 1


def cmd_restore(args) -> int:
    names = _m(args).restore_from(args.src)
    print(f"restored {len(names)} tomb(s): {', '.join(names) if names else '(none new)'}")
    return 0


def cmd_import(args) -> int:
    info = _m(args).import_tomb(args.path)
    print(f"imported ⚰ {info.name}")
    return 0


def cmd_forget(args) -> int:
    print("forgotten" if _m(args).forget(args.name) else "no such tomb")
    return 0


def cmd_gui(args) -> int:
    from gnugui import main as gui_main
    return gui_main([])


def cmd_selftest(args) -> int:
    import gnuvault as gv
    import mausoleum as ms
    gv._selftest()
    ms._selftest()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gnuvault", description="GNUVAULT — a transparent client-side vault.")
    p.add_argument("--version", action="version", version=f"GNUVAULT {VERSION}")
    p.add_argument("--root", default="~/.gnuvault/mausoleum", help="mausoleum directory")
    p.add_argument("--opaque", action="store_true", help="sealed inventory: store tombs under hashed filenames")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    for name, fn in [("inter", cmd_inter), ("exhume", cmd_exhume), ("rekey", cmd_rekey), ("forget", cmd_forget)]:
        sp = sub.add_parser(name); sp.add_argument("name"); sp.set_defaults(fn=fn)
    sp = sub.add_parser("export"); sp.add_argument("name"); sp.add_argument("--b64", action="store_true"); sp.add_argument("--pem", action="store_true"); sp.set_defaults(fn=cmd_export)
    sp = sub.add_parser("airgap"); sp.add_argument("what", choices=["challenge", "keygen", "sign"]); sp.add_argument("--nonce", default=""); sp.set_defaults(fn=cmd_airgap)
    sp = sub.add_parser("backup"); sp.add_argument("dest"); sp.add_argument("--no-verify", action="store_true"); sp.set_defaults(fn=cmd_backup)
    sp = sub.add_parser("verify"); sp.add_argument("dest"); sp.set_defaults(fn=cmd_verify)
    sp = sub.add_parser("restore"); sp.add_argument("src"); sp.set_defaults(fn=cmd_restore)
    sub.add_parser("usb").set_defaults(fn=cmd_usb)
    sp = sub.add_parser("import"); sp.add_argument("path"); sp.set_defaults(fn=cmd_import)
    sub.add_parser("gui").set_defaults(fn=cmd_gui)
    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
