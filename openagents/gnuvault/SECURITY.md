# GNUVAULT — security, threat model, and disclosure

Operational transparency applies to security first. This document states plainly
what GNUVAULT protects, what it does **not**, and how to report a problem. The
slogans are the threat model: *if you can touch it you own it; the only real
security is to build your own.*

## Cryptography

- **KDF:** `scrypt` (N=2¹⁵, r=8, p=1) over the Overseer's keying material + a
  per-tomb random 16-byte salt → a 32-byte key.
- **Cipher:** `AES-256-GCM` (AEAD) with a random 12-byte nonce. Authenticated:
  a wrong key, a tampered ciphertext, or a wrong **AAD** (the tomb's identity)
  fails closed — it never returns garbage plaintext.
- **AAD:** bound to the tomb name (`KDF_ID|tomb:<name>`), computed at seal/open,
  never stored — a bundle relocated to a different tomb name does not open.
- **Custody (Overseer):** passphrase, key file, or a wallet **signature**
  (`SHA-256(signature)`; deterministic signers reproduce it — the signature is
  never stored). The key is always **extractable** → sovereign.

Primitives come from [`cryptography`](https://cryptography.io) (OpenSSL). We do
not roll our own crypto.

## What GNUVAULT protects against

- **Disk theft / cloud leak of a tomb file.** Without the custody secret a tomb
  is opaque ciphertext; scrypt makes passphrase brute-force expensive.
- **Tampering.** GCM detects any modification of ciphertext, nonce, or AAD.
- **Cross-tomb relay.** AAD binds a bundle to its tomb name.
- **Lock-in.** `extract_key` / `export_key` / `export_keystore` are guaranteed
  exits; you can always leave with your key or build your own.
- **Inventory metadata leak** (opaque mode): tombs stored under the SHA-256 of
  their name; a directory listing reveals no labels.

## What GNUVAULT does NOT protect against (honest limits)

- **A compromised host while unlocked.** If malware runs as you while a secret is
  in memory, it can read it. *If you can touch it you own it* — and so can they.
- **A weak passphrase.** scrypt raises the cost; it does not save `"password"`.
- **Memory forensics / swap / core dumps.** Python cannot guarantee secrets are
  scrubbed from memory: `bytes`/`str` are immutable and may be copied or interned
  by the interpreter, and the OS may page them to swap. `gnuvault.wipe()` zeroes a
  `bytearray` best-effort, but treat in-memory secrets as recoverable by a
  privileged local attacker. Use full-disk encryption and disable swap for the
  paranoid case.
- **Side channels / constant-time.** Pure-Python comparison and control flow are
  not constant-time. The AEAD tag check (in OpenSSL) is; the surrounding glue is
  not. Not suitable as a network oracle.
- **Key management for the wallet/keyfile custodian.** If you lose the key file
  or the signing key, the tomb is unrecoverable by design. That is the point.
- **It is a reference implementation, not a hardened HSM.** Audit it, then decide.

## Reproducibility & verification

Everything is deterministic to verify: `python3 test_gnuvault.py` runs the full
suite (including randomized fuzz + tamper tests); CI runs it on 3.9/3.11/3.12.
`python -m build` produces a byte-stable wheel from a clean tree.

## Reporting a vulnerability

This project has **not** had a paid third-party audit. We invite review.

- Open a private security advisory at
  <https://github.com/gnugui/GNUVAULT/security/advisories/new>, or
- email the maintainer (see the GitHub profile). Please include a PoC and the
  affected version/commit.

We will acknowledge, fix, credit you (if you wish), and document the issue in the
CHANGELOG. *take it, own it, use it, share it.*
