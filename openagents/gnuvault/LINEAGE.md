# GNUVAULT — lineage & what it improves

GNUVAULT is a standalone, GPLv3 vault suite (`gnuvault` + `mausoleum` + `gnugui`)
that learns from four existing mindX/PYTHAI vault & wallet implementations and
improves on the production mindX version. Destined for
**<https://github.com/gnugui>** — *gnugui is both brand new and antiquated.*

> **BANKON will use GNUGUI in its public-facing client software.** This module is
> that client's open, auditable core.

## Security slogans (the spine)

- *"if you can touch it you own it"*
- *"The words computer and security should not be used in the same sentence"*
  (with no punctuation, the statement stays true)
- *"The only real security is to build your own."*
- *take it, own it, use it, share it.*

These are not jokes. They are the threat model. Security software runs on the
client's machine — they can touch it, so they own it — so the only honest posture
is **open-source security through transparency on the client side**, with a
guaranteed exit (extraction → sovereign key) and a real *build-your-own* path.

## What it learned, and what it improves

| Source | Borrowed | GNUVAULT improves |
|---|---|---|
| **BANKON Vault** (`mindx_backend_service/bankon_vault/vault.py`) — PBKDF2-HMAC-SHA512 600k + HKDF-SHA512 per-entry + AES-256-GCM + atomic rotation | the crypto spine + atomic temp→`os.replace` write discipline | **key export / extraction → sovereign** (BANKON rotates *within*; GNUVAULT lets you *leave* with your key); **multi-vault Mausoleum** (BANKON is one vault per instance); **portable standalone** (no FastAPI/web3) |
| **bankoneth** (`openagents/bankoneth/bankon-vault/`) — pluggable overseer protocol (Machine/Human/DAIO), HKDF domain separation `bankon-entry:{id}:{context}` | the overseer-as-trait idea; per-entry domain separation | overseer trait left as a clean extension point (hardware-wallet / M-of-N threshold) without FastAPI coupling |
| **DeltaVerse** (`services/bankon_vault/seal_folder.py`, `overlord_overseer.py`) — signature-derived sealing, AES-GCM **AAD bound to the file path**, OVERLORD custody | AAD-bound AEAD (GNUVAULT binds AAD to the KDF id) | generalizes beyond `personal_sign`; no single-OVERLORD SPOF in the standalone path |
| **parsec-wallet** (`src-tauri/src/bankon_vault/{crypto,tomb}.rs`) — Argon2id + AES-256-GCM, **Tomb USB LUKS cold storage**, Tauri desktop client | the Tomb cold-storage pattern → `Mausoleum.backup()` to a USB mount; the client-app form factor → GNUGUI | explicit, OWASP-grade KDF params (vs Argon2 implicit defaults); sealed inventory (no plaintext label leak) |

## The Tomb suite, resurrected and made plural

The Tomb lineage (dyne.org's `tomb`/`gtomb`) is brought forward:

- **a tomb** = one sealed GNUVAULT bundle (`*.tomb.json`).
- **the Mausoleum** = a directory that holds many tombs (`mausoleum.py`).
- **GNUGUI** = the pseudo-3D client over the mausoleum (`gnugui.py`), the `gtomb`
  GUI reborn as a cypherpunk2048 isometric vault view, in pure-stdlib Tkinter.

## Handheld reach — why the licensing matters

`openBDK` uses a combination of **OpenBSD** and **Alpine** — and that pairing,
**BSD + GPLv3**, is compatible with all handheld devices. This is the same thesis
the standard rests on: Linux won the unwatched battlefield, BSD (Darwin/XNU) won
the iPhone, and open source put handheld computing in the global population's
hands. GNUVAULT ships Apache-2.0/GPLv3 so it can ride that substrate everywhere.

## Files

| File | License | Role |
|---|---|---|
| `gnuvault.py` | GPLv3 | core tomb: scrypt + AES-256-GCM, seal/open/`extract_key` |
| `mausoleum.py` | GPLv3 | many tombs: list/inter/exhume/`export_key`/backup/import |
| `gnugui.py` | GPLv3 | the public-facing client (BANKON ships this); pseudo-3D Tk |
| `README.md` / `LINEAGE.md` / `LICENSE` | GPLv3 | docs + license |

Run the self-tests: `python3 gnuvault.py && python3 mausoleum.py && python3 gnugui.py --headless`.
