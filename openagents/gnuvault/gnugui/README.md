# GNUGUI (web) — the calculator that is the door

*A working calculator. Swipe **basic → advanced → scientific**.* That is all it
appears to be, and it gives no hint otherwise. But if a **wallet address**
(`0x` + 40 hex) has been pasted into the number field, **pressing and holding the
`+` button** is the door: it signs a challenge with your wallet and opens the
vault. With anything else in the field, **`+` is just `+`**.

The recognition is **silent** — no label, no glow, no "press + to open." It is
**security by obscurity, made aesthetically pleasing**: the door reveals nothing;
only someone who already knows pastes their address and holds `+`.

This is the [deltacalculator](../docs/VAULT_UI_MAP.md) answer to ~18 years of
vault UIs nobody loved (gtomb / Mausoleum / zuluCrypt) and the older
"Why Johnny Can't Encrypt" problem: hide the crypto inside an everyday object.

Vanilla JS, no build, no CDN, no tracking, GPL-3.0-or-later.

## Run it

```bash
python3 -m http.server      # in this folder → open http://localhost:8000
```

## Try it

1. It's a real calculator — `2+3*4 = 14`, `2^10 = 1024`, `sqrt(144) = 12`,
   `5! = 120`. Swipe (or use ‹ › / arrow keys) between basic, advanced, scientific.
   Nothing on screen mentions a vault.
2. Paste a wallet address into the number field — e.g.
   `0x52908400098527886E0F7030069857D2E4169EE7` (or your own, or 📋). The display
   shows it like any other input; **nothing changes, by design**.
3. **Press and hold `+`** (~0.65 s — a subtle fill confirms the gesture). With a
   browser wallet (MetaMask/etc.) it does a real `personal_sign`; without one it
   demo-opens so you can see the flow. A short tap on `+` is still just plus, and
   holding `+` over a normal number does nothing.
4. The vault opens into a **mausoleum**: seal named secrets, open them, forget
   them — all client-side. Custody is your **signature** (`key = SHA-256(challenge
   ‖ signature)`, exactly GNUVAULT's `WalletSignatureOverseer`); AES-256-GCM via
   WebCrypto; tombs in `localStorage`. Sign again and the same custody returns —
   nothing is stored but ciphertext.

## Files

| File | Role |
|---|---|
| [`index.html`](index.html) | the shell |
| [`gnugui.js`](gnugui.js) | calculator (safe shunting-yard evaluator), swipe panels, EVM recognition, press-hold-to-open |
| [`vault.js`](vault.js) | the in-browser vault — WebCrypto AES-256-GCM mausoleum, signature custody |
| [`gnugui.css`](gnugui.css) | cypherpunk2048 theme |

## Status

Logic verified headlessly (calculator math, address recognition, and the full
WebCrypto seal/open/wrong-sig-fails-closed round-trip). Visual/in-browser testing
is the next step — this is **not** published anywhere yet. *take it, own it, use
it, share it.*
