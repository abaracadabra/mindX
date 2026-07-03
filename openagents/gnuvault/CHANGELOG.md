# Changelog — GNUVAULT

All notable changes to GNUVAULT. GPL-3.0-or-later. In the highest regard for the
[GNU Project](https://www.gnu.org/) and the [Free Software Foundation](https://www.fsf.org/).

## v1.0.0 — stable

- **Documented self-audit** ([AUDIT.md](AUDIT.md)) — every threat-model claim
  mapped to the test that proves it (22 tests, CI on 3.9/3.11/3.12). Honest that
  it is a self-audit, **not** a paid third-party audit; independent review is
  invited ([SECURITY.md](SECURITY.md)).
- **Semantic-versioning stability guarantee** — no breaking change to the public
  API ([API.md](API.md)) or the `SealedBundle` wire format without a major bump.
- **Checksummed release artifacts** — `SHA256SUMS` published with the sdist +
  wheel on the GitHub release; reproducible via `python -m build`.
- The standard's reference vault is complete. *take it, own it, use it, share it.*

## v0.1.0 — feature-complete beta

- **API frozen for 0.x.** See [API.md](API.md): the public surfaces are stable;
  a v0.1.0 build opens any tomb sealed by v0.0.1+ (legacy AAD fallback). The
  `SealedBundle` JSON wire format is fixed for 0.x.
- **Deprecation policy:** anything to be removed gets at least one minor release
  of warning first. Internals (leading `_`) are not API.
- **Full lifecycle integration test:** inter → exhume → rekey → export →
  keystore → verified backup → forget → restore → open, end to end.
- This is the **beta** gate on the road to v1.0.0 (self-audit + review).
- Test suite at 22.

## v0.0.9

- **GNUGUI client hardening** — full CLI parity in the GUI: `inter`, `exhume`,
  **rekey**, `export`, **backup** (verified, with a directory picker), **import**
  (file picker), **forget** (with confirmation), refresh — each with fail-closed
  error dialogs. This is the BANKON-public-client core.
- Test covers the GUI module headless (import + clean exit + all actions present).
  Visual rendering is exercised manually / behind a display, not in CI — stated
  plainly. Test suite grows to 21.

## v0.0.8

- **[`SECURITY.md`](SECURITY.md)** — full threat model: the cryptography, what
  GNUVAULT protects against, the **honest limits** (compromised host, weak
  passphrase, memory forensics/swap, no constant-time guarantee in Python), and
  responsible-disclosure instructions (private advisory + review invitation).
- **Fuzz + tamper tests** — randomized seal/open round-trips and a test that
  flipping any byte of ciphertext/nonce/salt fails closed.
- **`gnuvault.wipe(bytearray)`** — best-effort key zeroization, honestly
  documented (Python cannot scrub immutable `bytes`/`str`).
- Test suite grows to 20.

## v0.0.7

- **Packaging & distribution.** Installs cleanly with `pipx install
  git+https://github.com/gnugui/GNUVAULT` (or `pip install .`), putting the
  `gnuvault` and `gnugui` console scripts on your PATH. `python -m build`
  produces a verified sdist + wheel. Added PyPI classifiers, project URLs
  (Repository/Changelog/Issues), `MANIFEST.in`, and broader keywords.
- No functional change to the crypto — pure distribution polish.

## v0.0.6

- **Cold storage to USB** — `Mausoleum.detect_removable_mounts()` finds USB mounts
  (Linux `/media`/`/run/media`/`/mnt`, macOS `/Volumes`); `backup()` now
  **SHA-256-verifies** every copy by default (a backup you have not verified is a
  hope, not a backup) and raises on mismatch; `verify_backup()` and
  `restore_from()` round-trip cold storage. The tombs are already encrypted, so
  the USB is cold storage as-is (an outer LUKS/Tomb layer is optional).
- CLI: `gnuvault usb`, `backup [--no-verify]`, `verify <dest>`, `restore <src>`.
- Test suite grows to 17 (verified backup, tamper detection, restore).

## v0.0.5

- **Airgap custody** (`airgap.py`): sign a fixed public challenge on an offline
  machine / hardware wallet, bring the *signature* back, and
  `overseer_from_signature()` derives the vault key — the signing key never
  touches the network and the signature is never stored. Includes a
  self-contained ed25519 keygen/sign/verify (deterministic → reproducible
  custody) for those building their own software signer.
- **Export formats:** `export_key(fmt="pem")` and `export_keystore()` — a
  portable, re-encrypted keystore you can open anywhere with only an export
  passphrase. `key_to_pem` / `key_from_pem` helpers in `gnuvault.py`.
- CLI: `gnuvault export --pem`, `gnuvault airgap challenge|keygen|sign`.
- Test suite grows to 15.

## v0.0.4

- **AAD bound to tomb identity.** The Mausoleum now seals each tomb with AES-GCM
  associated data derived from the tomb's *name* (`KDF_ID|tomb:<name>`), computed
  at seal AND open and never stored. A sealed file relocated to a different tomb
  name fails closed — closing a cross-tomb/relay gap. Tombs sealed before v0.0.4
  still open (legacy KDF-id AAD fallback) and upgrade to name-binding on `rekey`.
- **Sealed inventory** (`Mausoleum(..., opaque=True)` / `--opaque`). Tombs are
  stored under the SHA-256 of their name, so a directory listing leaks no labels;
  you must know a name to address it.
- `GnuVault.seal_with`/`open_with`/`rekey_with` gain an `aad=` parameter.
- Test suite grows to 12 (AAD binding, opaque inventory, legacy fallback).

## v0.0.3

- **Pluggable Overseer protocol** (`overseer.py`) — *who is allowed to derive the
  key*. Three custodians: `PassphraseOverseer` (default), `KeyfileOverseer`
  (custody by a key file, e.g. on a USB stick), and `WalletSignatureOverseer`
  (key material = `SHA-256(signature)` over a fixed challenge — bring a signature
  from MetaMask/Ledger/any signer; deterministic, never stored).
- `GnuVault.seal_with` / `open_with` / `extract_key_with` / `rekey_with(overseer…)`.
  The passphrase API is now a thin wrapper over these. **`rekey_with` migrates a
  tomb across custody types** (passphrase → wallet signature, etc.) without ever
  exposing the secret.
- **CI** (`.github/workflows/ci.yml`) — selftests + test suite on Python 3.9/3.11/3.12.
- Test suite grows to 9 (keyfile, wallet-signature, cross-custody rekey).

## v0.0.2

- **`rekey` — passphrase rotation.** `GnuVault.rekey()` and `Mausoleum.rekey()`
  rotate a tomb's passphrase in place (fresh salt + nonce), atomically, fail-closed
  on a wrong current passphrase. The plaintext is never written to disk in the clear.
- **`gnuvault` CLI** (`cli.py`) — a standalone command line over a Mausoleum:
  `list · inter · exhume · export · rekey · backup · import · forget · gui · selftest`.
  Passphrases are read with `getpass` (never echoed, never on argv).
- **Test suite** (`test_gnuvault.py`) — runs under pytest or standalone. Verifiability
  is part of transparency: check the claims yourself in seconds.
- Console scripts wired in `pyproject.toml` (`gnuvault`, `gnugui`).

## v0.0.1

- Initial public release at [github.com/gnugui/GNUVAULT](https://github.com/gnugui/GNUVAULT).
- `gnuvault.py` (one tomb — scrypt + AES-256-GCM, `seal`/`open`/`extract_key`),
  `mausoleum.py` (many tombs + `export_key` → sovereign exit, backup to USB),
  `gnugui.py` (the GNUGUI client). Docs, lineage, GPLv3 license.

---

## Releases

GNUVAULT follows the only sensible release schedule for free software:
**the next release ships when ready.** Not on a calendar, not on a quarter — when
it is correct, auditable, and worth your time. *take it, own it, use it, share it.*
