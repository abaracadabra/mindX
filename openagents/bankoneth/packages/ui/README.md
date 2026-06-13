# @bankoneth/ui

> Lit 3 Web Components for bankoneth — claim subnames, buy `.eth` 2LDs, and
> host third-party `.eth` issuance. Token-driven design system. Drop into any
> HTML page (Tauri, Vite, Next.js, mindX console, PARSEC wallet).

## Install

```bash
pnpm add @bankoneth/ui @bankoneth/core lit viem
```

## Quick use

```ts
import "@bankoneth/ui";
import { BankonethClient, namehash } from "@bankoneth/core";

const client = new BankonethClient(publicClient, walletClient, addresses, namehash("bankon.eth"));

document.body.innerHTML = `
  <bankoneth-flow-tabs></bankoneth-flow-tabs>
  <bankoneth-claim></bankoneth-claim>
`;
const claim = document.querySelector("bankoneth-claim");
claim.client            = client;
claim.inftTokenContract = "0x...";        // 0G iNFT_7857 address
claim.inftImplementation = "0x...";       // ERC-6551 account implementation
claim.inftChainId       = 16601;
```

## What ships

### Hero flows (4-step carousels)

- `<bankoneth-claim>`     — Flow A: claim `*.bankon.eth`
- `<bankoneth-purchase>`  — Flow B: buy `newdomain.eth` via wrapped ENS commit-reveal
- `<bankoneth-host>`      — Flow C: enroll your `.eth` as a host **or** issue under one

### Primitives

- `<b-button>`             — solid/outlined/ghost/danger, ripple, spring press, loading
- `<b-input>`              — focus ring, validation states, suffix slot, shake on error
- `<b-card>`               — flat/elevated/floating with hover lift
- `<b-stepper>`            — sticky progress dots, smooth cross-fade carousel
- `<b-availability-pill>`  — animated spinner → ✓/× pill (live)
- `<b-namehash-preview>`   — bytes32 namehash + ERC-6551 TBA card (pre-sign)
- `<b-suggestions>`        — label-taken alternatives, batched availability
- `<b-renew-countdown>`    — days-left ring + one-click renew button
- `<b-rail-switcher>`      — animated tri-rail payment toggle

### Secondary

- `<bankoneth-pricing>`           — display-only pricing card
- `<bankoneth-inft-toggle>`       — wrap-as-iNFT checkbox
- `<bankoneth-flow-tabs>`         — A/B/C selector
- `<bankoneth-agenticplace-toggle>` — opt-in marketplace listing

## Design tokens

All components share a single token system exposed as CSS custom properties
on `:host`. Override them on your app root, or per-component element, or
even per-instance, to re-skin without touching the source.

```css
:root {
  --b-color-accent: #4a90e2;        /* primary CTA */
  --b-color-bg-1:   #0b0d12;        /* deepest surface */
  --b-color-text-primary: #e8eaed;
  /* … */
}
```

Three themes ship: `dark` (default), `light` (set `theme="light"` on the
component), and `high-contrast` (set `theme="high-contrast"` — WCAG AAA).
A `prefers-reduced-motion: reduce` fallback disables all transitions
automatically.

Full token reference: [`src/tokens/tokens.ts`](src/tokens/tokens.ts).
Motion library: [`src/tokens/motion.ts`](src/tokens/motion.ts).
Icon set: [`src/tokens/icons.ts`](src/tokens/icons.ts).

## Why this design

The bar to clear was parsec-wallet's `.algo` NFD minter
(`/home/hacker/parsec/parsec-wallet/src/views/nfdominter*.ts`). Where
parsec-wallet was solid but had gaps, bankoneth fills them:

| Parsec gap | bankoneth fix |
|---|---|
| Availability checked on the confirm screen | Live `<b-availability-pill>` on the search step |
| App ID only shown post-mint | `<b-namehash-preview>` shows the bytes32 + TBA address before sign |
| Generic "checking…" text | Spinner + spring-pop ✓/× transition |
| Single-chain (Algorand only) | `<b-rail-switcher>` — animated ETH/USDC/x402 toggle |
| Hub-with-tabs flow model | Carousel via `<b-stepper>` — linear, mobile-friendly |
| No name-taken suggestions | `<b-suggestions>` generates + batches alternatives |
| Lease info buried in manage tab | `<b-renew-countdown>` surfaced on the success step |

## License

Apache-2.0
