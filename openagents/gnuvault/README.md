<div align="center">

# GNUVAULT

### *A transparent, client-side vault. The key is yours — always.*

**`gnuvault` · `mausoleum` · GNUGUI** — the build-your-own reference implementation
of the [**cypherpunk2048**](https://github.com/cypherpunk2048) Operational Transparency standard.

[![version](https://img.shields.io/badge/version-1.0.0-36966e.svg)](CHANGELOG.md)
[![ci](https://github.com/gnugui/GNUVAULT/actions/workflows/ci.yml/badge.svg)](https://github.com/gnugui/GNUVAULT/actions/workflows/ci.yml)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-d4af37.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![GNU](https://img.shields.io/badge/GNU-respect%20in%20the%20highest%20regard-36966e.svg)](https://www.gnu.org/)
[![cypherpunk2048](https://img.shields.io/badge/standard-cypherpunk2048-0a0a12.svg)](https://github.com/cypherpunk2048)
[![Python](https://img.shields.io/badge/python-%E2%89%A53.9-blue.svg)](https://www.python.org/)

*take it · own it · use it · share it*

</div>

---

## In homage to GNU

GNUVAULT exists because of, and in the **absolute highest regard for**, the
[**GNU Project**](https://www.gnu.org/) and the
[**Free Software Foundation**](https://www.fsf.org/). Everything good about this
software is downstream of a simple, radical idea that
[Richard Stallman](https://www.gnu.org/gnu/the-gnu-project.html) and the GNU
community gave the world: software should grant its users
[**four freedoms**](https://www.gnu.org/philosophy/free-sw.html) — to run it, to
study it, to change it, and to share it. We hold those freedoms as sacred. The
[**GNU General Public License v3**](https://www.gnu.org/licenses/gpl-3.0.html)
is not a footnote here; it is the foundation. We build with **GNU tools**, in the
lineage of [`Tomb`](https://github.com/dyne/Tomb), the GNU/Linux crypto-undertaker
by [dyne.org](https://www.dyne.org/). To the GNU Project: thank you. We stand on
your shoulders, and we keep the source open so others can stand on ours.

> **GNU is not Unix.** GNUVAULT is not a product. Both are gifts.

---

## The idea, in one breath

Security software runs on **your** machine. You already hold it — so we give it
to you from **ownership**, not from leakage: open source you can read, audit,
change, and rebuild. Your **key** seals into the vault (the blackbox); the
**code** of the vault stays in the open. And at any moment you may
**extract your key from the running system** — at which point the key becomes
**sovereign**: portable, off-host, yours. A guaranteed exit, never a backdoor.

This is **open-source security through transparency on the client side**. It is,
in our reading, how [**Linux**](https://www.kernel.org/) won the war on a
battlefield no one was watching, and how **BSD** ([Darwin/XNU](https://en.wikipedia.org/wiki/Darwin_(operating_system)))
won the iPhone: open source put computing into the hands of the global
population. GNUVAULT carries that posture to the vault.

## The slogans (the threat model, stated plainly)

- *if you can touch it you own it*
- *The words computer and security should not be used in the same sentence*
- *The only real security is to build your own.*
- *take it, own it, use it, share it.*

---

## The suite

| Module | Role |
|---|---|
| [`gnuvault.py`](gnuvault.py) | one **tomb** — `scrypt` + `AES-256-GCM`; `seal` · `open` · **`extract_key`** |
| [`mausoleum.py`](mausoleum.py) | the **Mausoleum** — many tombs; `inter` · `exhume` · **`export_key`** (the sovereign exit) · `backup` to USB |
| [`overseer.py`](overseer.py) | **who may derive the key** — `Passphrase` / `Keyfile` / `WalletSignature` overseers (custody by passphrase, key file, or a wallet signature) |
| [`airgap.py`](airgap.py) | **offline custody** — sign a challenge on an airgapped machine / hardware wallet; the signing key never touches the network |
| [`gnugui.py`](gnugui.py) | **GNUGUI** — the public-facing client; a pseudo-3D, cypherpunk2048 vault view in pure-stdlib Tkinter |

The Tomb suite, resurrected and made plural: a *tomb* is one sealed bundle; a
*Mausoleum* holds many; **GNUGUI** is the `gtomb` GUI reborn. The crypto is the
spine of mindX's production **BANKON Vault** (itself GNU), distilled to one
auditable file you can read in a single sitting.

## Install

```bash
pipx install git+https://github.com/gnugui/GNUVAULT        # isolated, gives `gnuvault`
# or
pip install git+https://github.com/gnugui/GNUVAULT
gnuvault --version        # GNUVAULT 0.0.7
gnuvault inter my-secret  # the CLI is now on your PATH
```

## Quickstart (no install — just clone)

```bash
pip install cryptography
python3 gnuvault.py        # selftest — scrypt + AES-256-GCM; key extractable
python3 test_gnuvault.py   # the test suite (verify the claims yourself)

# the CLI (passphrases prompted, never echoed, never on argv)
python3 cli.py inter   my-secret     # seal a new tomb
python3 cli.py list
python3 cli.py rekey   my-secret     # rotate the passphrase in place
python3 cli.py export  my-secret     # extract the key → sovereign
python3 cli.py gui                   # launch GNUGUI
```

```python
from gnuvault import GnuVault, SealedBundle

v = GnuVault()
bundle = v.seal("my secret", "correct horse battery staple")
secret = v.open(SealedBundle.from_json(bundle.to_json()), "correct horse battery staple")
key    = v.extract_key(bundle, "correct horse battery staple")   # → sovereign
```

## Honest scope

Operational transparency applies to this README too. GNUVAULT is a **reference
implementation** — small, readable, and correct in its primitives (`scrypt`,
`AES-256-GCM`, fail-closed authentication). It is the *worked example* of the
standard, not a hardened HSM. Read it, run it, fork it, and — per the standard —
**build your own**. See [SECURITY.md](SECURITY.md) for the threat model and honest limits, and [LINEAGE.md](LINEAGE.md) for what it learned from
parsec-wallet, bankoneth, DeltaVerse, and the production BANKON Vault.

---

## The house that built this

GNUVAULT is shipped by the **mindX / PYTHAI / BANKON** ecosystem. **BANKON will
use GNUGUI in its public-facing client software.**

- **The standard** — [github.com/cypherpunk2048](https://github.com/cypherpunk2048)
- **mindX** — [mindx.pythai.net](https://mindx.pythai.net) · [docs](https://mindx.pythai.net/docs.html)
- **RAGE** — [rage.pythai.net](https://rage.pythai.net) (the aggregation & publishing company)
- **BANKON** — [bankon.pythai.net](https://bankon.pythai.net) (a doorway)
- **GNUGUI org** — [github.com/gnugui](https://github.com/gnugui)
- **Carried everywhere by `openBDK`** — [OpenBSD](https://www.openbsd.org/) + [Alpine](https://alpinelinux.org/) (BSD + GPLv3, all handheld devices)

## Releases

GNUVAULT follows the only sensible schedule for free software: **the next release
ships when ready** — not on a calendar, but when it is correct, auditable, and
worth your time. **v1.0.0 is here** — stable, semver-governed (see [API.md](API.md)), with a documented [self-audit](AUDIT.md) and an open invitation to review. See the [CHANGELOG](CHANGELOG.md).

## License

[**GPL-3.0-or-later**](LICENSE). You may read it, change it, and run your own —
that is the entire point. In the highest regard for the
[GNU Project](https://www.gnu.org/) and the [Free Software Foundation](https://www.fsf.org/).

<div align="center">

*take it · own it · use it · share it*

</div>
