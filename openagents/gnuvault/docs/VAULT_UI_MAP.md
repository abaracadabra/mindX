# The map: dyne.org Tomb, the graveyard of vault UIs, and the deltacalculator answer

Research for the GNUGUI interactive experience — *the changing calculator that is
also the door to the vault.* Mapped 2026-06-08.

## 1. The dyne.org Tomb lineage (the gold standard CLI)

[**Tomb — the Crypto Undertaker**](https://dyne.org/tomb/), by Jaromil / the
[Dyne.org Foundation](https://dyne.org), trusted by hackers since **2007**.

- A minimalistic **Zsh** script over **LUKS / dm-crypt** (`cryptsetup`) with the
  Linux kernel crypto API; **AES-256-XTS**. Source small enough to review.
- Vocabulary GNUVAULT already borrows: `dig` · `forge` · `lock` · `open` ·
  `close` · `slam` · `bury` / `exhume`. A *tomb* = an encrypted volume; its *key*
  is a separate file you keep apart (the USB / steganographic key).
- Verdict: **the CLI is excellent.** It is the *UI* that never arrived.

### Tomb's own GUI attempts (`extras/`)

| Frontend | Tech | What it is | Why it isn't "vault-worthy" |
|---|---|---|---|
| [**gtomb**](https://github.com/dyne/Tomb/tree/master/extras/gtomb) | Zenity / GTK + Zsh | A wrapper-of-a-wrapper: Zenity dialog boxes around Tomb | A chain of modal popups. Functional, joyless, fragile; no identity, no flow. |
| **Mausoleum** | Python GTK | Create/manage many tombs | Basic file-manager-for-tombs; never widely adopted. (GNUVAULT keeps the *name* and the multi-tomb idea, not the UI.) |
| [**zuluCrypt**](https://github.com/dyne/Tomb/issues/105) | C++ | Generic encrypted-volume manager; opens Tombs via a plugin you must enable | Tomb is a second-class citizen behind a plugin toggle; a generic disk tool, not a vault experience. |

**The gap, stated plainly:** Tomb solved the cryptography in 2007 and has spent
~18 years *without a UI anyone loves.* Every frontend is a thin dialog wrapper —
none made opening a vault feel like anything.

## 2. The wider graveyard — and *why* vault UIs fail

This is not a Tomb problem; it is the field's oldest open problem.

- **["Why Johnny Can't Encrypt"](https://www.semanticscholar.org/paper/Why-Johnny-Can't-Encrypt:-A-Usability-Evaluation-of-Whitten-Tygar/389f55c5c376db4ce1c88161dca98c329614faa8)** (Whitten & Tygar, 1999): PGP 5.0 had an *attractive GUI* and was still unusable. UI design for effective security was declared an open problem — and it stayed open.
- **[TrueCrypt](https://en.wikipedia.org/wiki/TrueCrypt)**: abandoned 2014 ("not secure"); its UX was never solved, just inherited.
- **[VeraCrypt](https://dl.acm.org/doi/10.1145/3706598.3713983)** (CHI 2025 long-term usable-security study): in testing, **0 of 5 users could secure a file** with the stock interface. After UI fixes, 4 of 5 could do a sub-task. The killer finding: users are **overwhelmed by technical choices** (VeraCrypt was the only tool forcing a concrete cipher choice); they either freeze on defaults or drown in algorithm descriptions.

**The lesson (the design law for our build):**
1. **Hide the cryptography.** No cipher pickers, no "advanced options" in the path.
2. **Make the secure path the only path** — and make it feel ordinary.
3. **Defaults are the product.** The one good default beats ten exposed knobs.

GNUVAULT already obeys (1)–(3) at the library level: one KDF, one cipher,
fail-closed, the key always extractable. What is missing is a *front door* that a
human would actually enjoy using. That is the deltacalculator.

## 3. The answer: the deltacalculator (the door disguised as an everyday object)

Source today: `DeltaVerse/engine/lock.js` (325 lines, vanilla JS, no deps) +
`DeltaVerse/GNUGUI/gnuvault/`. It is a **working calculator** that is also the
**vault door**:

- You use it as a calculator. If what you type *looks like a key* (`looksLikeKey`:
  has letters or ≥26 chars), pressing **`+`** stops being addition and becomes
  **`_sign()`** — it asks your wallet to `personal_sign` the challenge
  `DeltaVerse · open the vault · <addr> · <host>` (PARSEC/Tauri first, EIP-1193
  fallback). A verified signature is the proof of custody (`dv_overlord_proof`);
  the vault opens with a 1.1s transition.
- cypherpunk2048 palette already wired (`--dv-violet #8b5cf6`, `--dv-gold #ffd166`,
  `--dv-cyan #56ccf2`, abyss `#050810`); glassmorphic window; draggable; airgap
  variant with an inline SVG vault crest.

**Why this beats every entry in the graveyard:** the crypto is *invisible*. There
is no cipher menu, no "create volume" wizard, no jargon. The secure act —
proving you hold the key — is hidden inside the most familiar object on a
computer. A calculator. You do not *learn* the vault; you *use a calculator*, and
the door opens. That is the inversion "Why Johnny Can't Encrypt" has been waiting
26 years for.

## 4. What we built — the changing calculator (web GNUGUI)

Delivered at [`../gnugui/`](../gnugui/) (`index.html` + `gnugui.js` + `vault.js` +
`gnugui.css`), vanilla JS, no build/CDN/tracking, GPLv3. Logic verified headlessly
in Node (calculator math, address recognition, and the full WebCrypto seal/open /
wrong-signature-fails-closed round-trip). **Not published yet — testing first.**

- **A genuinely working calculator that swipes basic → advanced → scientific.**
  A safe shunting-yard evaluator (no `eval`): precedence, parens, `^ % √`, unary
  `−`, `sin cos tan`, `log ln`, `π e`, `n!`. Touch/drag, ‹ ›, or arrow keys.
- **Recognition is SILENT.** A pasted **wallet address** (`0x` + exactly 40 hex,
  `/^0x[0-9a-fA-F]{40}$/`) — the *public address*, never called a "key" — is
  recognized internally only. **No hint, no glow, no "press + to open," no armed
  state.** The window and the `+` button look identical whether or not an address
  is present. *Security by obscurity, aesthetically pleasing.*
- **The `+` button is just the `+` button** — until an address is in the field and
  you **press and hold it** (~0.65 s, a subtle fill confirms the gesture only
  while held). Then it signs `GNUVAULT · open the vault · <addr> · <host>` (EIP-1193
  `personal_sign`; demo-open without a wallet). A short tap is plus; holding over a
  number does nothing.
- **The door leads somewhere real:** an in-browser **mausoleum** (`vault.js`) —
  seal/open/forget named tombs, all client-side via WebCrypto **AES-256-GCM**, with
  custody = the signature (`key = SHA-256(challenge ‖ signature)`, exactly
  GNUVAULT's `WalletSignatureOverseer`). Sign again → same custody; nothing stored
  but ciphertext.
- **Defaults are the product:** no cipher choice, ever. One cipher, one gesture.

The result is the first vault UI in this lineage that is **worth using because you
forget it is a vault** — which is, per the research above, exactly why the others
failed. Next: in-browser visual testing, then deciding whether to fold it into the
GNUVAULT repo.

---

### Sources
- [Tomb — dyne.org](https://dyne.org/tomb/) · [dyne/Tomb (GitHub)](https://github.com/dyne/Tomb) · [gtomb](https://github.com/dyne/Tomb/tree/master/extras/gtomb) · [zuluCrypt/Tomb issue](https://github.com/dyne/Tomb/issues/105)
- [Why Johnny Can't Encrypt (Whitten & Tygar, 1999)](https://www.semanticscholar.org/paper/Why-Johnny-Can't-Encrypt:-A-Usability-Evaluation-of-Whitten-Tygar/389f55c5c376db4ce1c88161dca98c329614faa8)
- [TrueCrypt (Wikipedia)](https://en.wikipedia.org/wiki/TrueCrypt)
- [VeraCrypt usable-security study, CHI 2025](https://dl.acm.org/doi/10.1145/3706598.3713983)
