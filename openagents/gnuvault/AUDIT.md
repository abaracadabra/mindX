# GNUVAULT — v1.0.0 self-audit

**This is a documented self-audit, not a paid third-party audit.** Operational
transparency means saying that plainly. Every claim below maps to a test you can
run yourself (`python3 test_gnuvault.py`, 22 tests, also in CI on 3.9/3.11/3.12).
We invite independent review — see [SECURITY.md](SECURITY.md).

Scope: `gnuvault.py`, `overseer.py`, `airgap.py`, `mausoleum.py` at v1.0.0.

## Claims ↔ evidence

| # | Claim | Verified by |
|---|---|---|
| 1 | AEAD round-trips correctly for arbitrary data | `test_seal_open_roundtrip`, `test_fuzz_roundtrip_random` (60 random cases) |
| 2 | Wrong passphrase fails closed (no garbage plaintext) | `test_wrong_passphrase_fails_closed` |
| 3 | Any 1-bit tamper of ct/nonce/salt is detected | `test_tamper_any_field_fails_closed` |
| 4 | AAD binds a bundle to its tomb; relocation fails | `test_aad_binds_to_tomb_name` |
| 5 | Legacy (pre-0.0.4) tombs still open; rekey upgrades | `test_legacy_pre_v004_tomb_opens` |
| 6 | Key is extractable & deterministic (sovereign exit) | `test_extract_key_is_32_bytes_and_deterministic` |
| 7 | Keyfile / wallet-signature custody; cross-custody rekey | `test_keyfile_overseer_roundtrip`, `test_wallet_signature_overseer_is_deterministic`, `test_rekey_passphrase_to_wallet` |
| 8 | Airgap: offline signature → reproducible custody | `test_airgap_signature_custody_roundtrip` |
| 9 | Portable PEM / keystore export | `test_pem_key_roundtrip`, `test_export_keystore_is_portable` |
| 10 | Opaque inventory hides labels | `test_opaque_inventory_hides_labels` |
| 11 | Backups are SHA-256-verified; tamper caught; restore works | `test_backup_verify_and_restore` |
| 12 | No-overwrite safety; full lifecycle | `test_no_overwrite_without_forget`, `test_full_lifecycle_integration` |

## Cryptographic review notes

- Primitives are from `cryptography`/OpenSSL: `scrypt` (N=2¹⁵,r=8,p=1, 16-byte
  random salt) and `AES-256-GCM` (12-byte random nonce). No home-rolled crypto.
- Nonce + salt are `os.urandom` per seal; GCM nonce-reuse is avoided by always
  generating fresh randomness and never re-encrypting under the same (key,nonce).
- AAD is authenticated and bound to context (tomb name), computed not stored.
- Authentication failure surfaces as an exception (fail-closed) everywhere.

## Residual risks (unchanged from SECURITY.md, restated)

- Compromised host while unlocked; weak passphrases; memory forensics/swap
  (Python cannot guarantee secret scrubbing); pure-Python is not constant-time.
- This is a **reference implementation**, intentionally small and readable, not a
  hardened HSM. Audit it, then decide.

## Stability guarantee

From v1.0.0, GNUVAULT follows [semantic versioning](https://semver.org): no
breaking changes to the public API ([API.md](API.md)) or the `SealedBundle` wire
format without a major-version bump. Releases ship checksummed (`SHA256SUMS` on
each GitHub release); the source is GPLv3 and reproducible (`python -m build`).

*Reviewed against SECURITY.md at v1.0.0. take it, own it, use it, share it.*
