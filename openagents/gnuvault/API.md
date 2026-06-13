# GNUVAULT — public API (frozen for the 0.x line)

As of **v0.1.0** the surfaces below are the stable public API. Within 0.x they
will not change incompatibly; anything not listed is internal (leading `_`) and
may change. Deprecations get one minor release of warning before removal.

## `gnuvault`

- `GnuVault()` — `seal(secret, passphrase)`, `open(bundle, passphrase)`,
  `extract_key(bundle, passphrase)`, `rekey(bundle, old, new)` and the
  Overseer forms `seal_with` / `open_with` / `extract_key_with` /
  `rekey_with(overseer…, *, aad=…)`.
- `SealedBundle` — `to_json()`, `from_json(text)`; fields `kdf, salt, nonce, ct`.
- `derive_key(passphrase, salt)`, `derive_key_material(material, salt)`.
- `key_to_pem(key)`, `key_from_pem(pem)`, `wipe(bytearray)`.

## `overseer`

- `Overseer` (ABC, `.material() -> bytes`), `PassphraseOverseer(passphrase)`,
  `KeyfileOverseer(path)`, `WalletSignatureOverseer(signature, challenge=…)`,
  `DEFAULT_CHALLENGE`.

## `airgap`

- `airgap_challenge(nonce="")`, `overseer_from_signature(signature, challenge=…)`,
  `ed25519_keygen()`, `ed25519_sign(private_hex, challenge=…)`,
  `ed25519_verify(public_hex, signature_hex, challenge=…)`.

## `mausoleum`

- `Mausoleum(root="~/.gnuvault/mausoleum", *, opaque=False)` —
  `inter(name, secret, passphrase)`, `exhume(name, passphrase)`,
  `extract_key(name, passphrase)`, `export_key(name, passphrase, *, fmt="hex|base64|pem")`,
  `export_keystore(name, passphrase, export_passphrase)`,
  `rekey(name, old, new)`, `forget(name)`, `list_tombs()`,
  `backup(dest, *, verify=True)`, `verify_backup(dest)`, `restore_from(src)`,
  `import_tomb(path)`, `detect_removable_mounts()` (static).
- `TombInfo` (dataclass), `SLOGANS`.

## `cli` / `gnugui`

- `cli.main(argv=None)` — the `gnuvault` console command.
- `gnugui.main(argv=None)` — the `gnugui` / GNUGUI client (`--headless` safe).

The wire format (`SealedBundle` JSON) is stable for 0.x: a v0.1.0 build opens any
tomb sealed by v0.0.1+ (legacy AAD fallback included).
