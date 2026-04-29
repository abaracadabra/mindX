#!/usr/bin/env python3
"""
BANKON Vault — airgap signer.

Runs on an AIRGAPPED machine with no mindX imports. Reads a challenge text
produced by `manage_custody.py challenge`, signs it via EIP-191 personal_sign,
and emits the 65-byte signature.

The signature is the BANKON Vault's IKM under HumanOverseer: whoever can
produce it can rotate the vault. Therefore this script must run only on a
machine that holds the wallet's private key and no others.

Dependencies (install once on the airgap):
    pip install eth-account>=0.13

Optional:
    pip install mnemonic               # only for --mnemonic-file
    pip install qrcode[pil] pillow     # only for --out-qr

Usage examples (each runs offline; no network calls):

    # Privkey from prompt (no shell history), challenge from file
    python airgap_sign.py --challenge-file handoff_challenge.txt --privkey-prompt

    # BIP39 mnemonic + derivation path, write signature JSON
    python airgap_sign.py \\
        --challenge-file handoff_challenge.txt \\
        --mnemonic-file ~/.airgap/seed.txt \\
        --derivation-path "m/44'/60'/0'/0/0" \\
        --out handoff_sig.json

    # Encrypted keystore JSON (V3), with password prompt
    python airgap_sign.py \\
        --challenge-file handoff_challenge.txt \\
        --keystore ~/.airgap/keystore-utc.json \\
        --out handoff_sig.json \\
        --out-qr handoff_sig.qr.png

    # Hardware-wallet path: Ledger / Trezor produce the sig externally;
    # this script just verifies + repackages it as the JSON evidence.
    python airgap_sign.py \\
        --challenge-file handoff_challenge.txt \\
        --paste-sig 0xabc... --address 0xMINE \\
        --out handoff_sig.json

The output JSON has the exact shape `manage_custody.py dry-run` consumes:

    {"address": "0x...", "signature": "0x<130-hex>", "message": "<challenge>"}
"""
from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path
from typing import Optional


def _die(msg: str, code: int = 2) -> None:
    print(f"airgap-sign: ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def _read_challenge(args: argparse.Namespace) -> str:
    if args.challenge_text is not None:
        return args.challenge_text
    if args.challenge_file:
        p = Path(args.challenge_file)
        if not p.exists():
            _die(f"challenge file not found: {p}")
        return p.read_text()
    if args.stdin:
        return sys.stdin.read()
    _die("provide one of: --challenge-file, --challenge-text, --stdin")


def _resolve_privkey(args: argparse.Namespace) -> Optional[str]:
    """Return a 0x-prefixed 32-byte hex privkey, or None for paste-sig mode."""
    sources = [
        bool(args.privkey),
        bool(args.privkey_prompt),
        bool(args.privkey_file),
        bool(args.mnemonic_file),
        bool(args.keystore),
        bool(args.paste_sig),
    ]
    if sum(sources) == 0:
        _die("provide a key source: --privkey / --privkey-prompt / "
             "--privkey-file / --mnemonic-file / --keystore / --paste-sig")
    if sum(sources) > 1:
        _die("multiple key sources given — pick one")

    if args.paste_sig:
        return None  # paste-sig mode skips local signing

    if args.privkey:
        pk = args.privkey
    elif args.privkey_prompt:
        pk = getpass.getpass("Private key (hex, hidden): ").strip()
    elif args.privkey_file:
        pk = Path(args.privkey_file).read_text().strip()
    elif args.mnemonic_file:
        try:
            from eth_account import Account
        except ImportError:
            _die("eth-account not installed (pip install eth-account)")
        Account.enable_unaudited_hdwallet_features()
        words = Path(args.mnemonic_file).read_text().strip()
        path = args.derivation_path or "m/44'/60'/0'/0/0"
        try:
            acct = Account.from_mnemonic(words, account_path=path)
        except Exception as e:
            _die(f"mnemonic decode failed (path={path}): {e}")
        return acct.key.hex()
    elif args.keystore:
        try:
            from eth_account import Account
        except ImportError:
            _die("eth-account not installed (pip install eth-account)")
        ks_path = Path(args.keystore)
        if not ks_path.exists():
            _die(f"keystore not found: {ks_path}")
        try:
            ks = json.loads(ks_path.read_text())
        except Exception as e:
            _die(f"keystore not valid JSON: {e}")
        password = getpass.getpass("Keystore password (hidden): ")
        try:
            pk_bytes = Account.decrypt(ks, password)
        except Exception as e:
            _die(f"keystore decrypt failed: {e}")
        return "0x" + pk_bytes.hex()
    else:
        _die("unreachable: no key source matched")

    if not pk.startswith("0x"):
        pk = "0x" + pk
    if len(pk) != 66:
        _die(f"private key must be 32 bytes (got {(len(pk)-2)//2})")
    try:
        int(pk, 16)
    except ValueError:
        _die("private key is not hex")
    return pk


def _sign(challenge: str, privkey_hex: str) -> tuple[str, str]:
    """Return (address, signature_hex). EIP-191 personal_sign over the challenge."""
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
    except ImportError:
        _die("eth-account not installed (pip install eth-account)")
    msg = encode_defunct(text=challenge)
    signed = Account.sign_message(msg, private_key=privkey_hex)
    sig = signed.signature.hex()
    if not sig.startswith("0x"):
        sig = "0x" + sig
    address = Account.from_key(privkey_hex).address
    return address, sig


def _verify(challenge: str, signature: str, expected_address: str) -> bool:
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
    except ImportError:
        _die("eth-account not installed")
    msg = encode_defunct(text=challenge)
    try:
        recovered = Account.recover_message(msg, signature=signature)
    except Exception:
        return False
    return recovered.lower() == expected_address.lower()


def _emit_qr(payload: str, out_path: Path) -> None:
    try:
        import qrcode  # type: ignore
    except ImportError:
        _die("qrcode not installed (pip install 'qrcode[pil]') — required for --out-qr")
    img = qrcode.make(payload)
    img.save(out_path)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Airgap signer for BANKON Vault HumanOverseer handoff.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    src = p.add_argument_group("challenge source (pick one)")
    src.add_argument("--challenge-file", help="path to handoff_challenge.txt")
    src.add_argument("--challenge-text", help="challenge text inline (testing)")
    src.add_argument("--stdin", action="store_true", help="read challenge from stdin")

    key = p.add_argument_group("key source (pick one)")
    key.add_argument("--privkey", help="hex private key (avoid: lands in shell history)")
    key.add_argument("--privkey-prompt", action="store_true",
                     help="prompt for private key (hidden input)")
    key.add_argument("--privkey-file", help="path to file containing hex private key")
    key.add_argument("--mnemonic-file", help="path to file containing BIP39 words")
    key.add_argument("--derivation-path", default="m/44'/60'/0'/0/0",
                     help="HD derivation path (default: %(default)s)")
    key.add_argument("--keystore", help="path to encrypted keystore V3 JSON")
    key.add_argument("--paste-sig", help="hex signature produced by an external "
                     "signer (Ledger/Trezor) — verify-and-package mode")
    key.add_argument("--address", help="expected signer address (required with --paste-sig)")

    out = p.add_argument_group("output")
    out.add_argument("--out", help="write signature JSON to this path")
    out.add_argument("--out-qr", help="write a QR PNG of the signature JSON for camera transfer")
    out.add_argument("--quiet", action="store_true", help="suppress stdout sig hex")

    args = p.parse_args()

    challenge = _read_challenge(args)

    if args.paste_sig:
        if not args.address:
            _die("--paste-sig requires --address (the EOA expected to have signed)")
        if not args.paste_sig.startswith("0x"):
            args.paste_sig = "0x" + args.paste_sig
        if not _verify(challenge, args.paste_sig, args.address):
            _die("pasted signature does NOT recover to --address — refusing to package")
        address, signature = args.address.lower(), args.paste_sig
    else:
        privkey = _resolve_privkey(args)
        assert privkey is not None
        address, signature = _sign(challenge, privkey)
        # Best-effort wipe — Python's GC means this is advisory.
        privkey = "0" * len(privkey)
        del privkey

        if not _verify(challenge, signature, address):
            _die("post-sign verify failed — implementation bug, do NOT use this signature")

    sig_bytes_len = (len(signature) - 2) // 2
    if sig_bytes_len != 65:
        _die(f"signature is {sig_bytes_len} bytes, expected 65")

    payload = {
        "address": address.lower() if address.startswith("0x") else "0x" + address.lower(),
        "signature": signature,
        "message": challenge,
    }
    payload_json = json.dumps(payload, indent=2)

    if not args.quiet:
        print(payload_json)

    if args.out:
        out_path = Path(args.out)
        out_path.write_text(payload_json + "\n")
        try:
            out_path.chmod(0o600)
        except OSError:
            pass
        print(f"airgap-sign: wrote {out_path}", file=sys.stderr)

    if args.out_qr:
        _emit_qr(payload_json, Path(args.out_qr))
        print(f"airgap-sign: wrote QR {args.out_qr}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
