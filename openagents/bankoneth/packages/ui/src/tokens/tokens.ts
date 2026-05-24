// SPDX-License-Identifier: Apache-2.0
//
// @bankoneth/ui — design tokens.
//
// CSS custom properties on `:host` for every component in the package.
// Three themes ship: dark (default), light, high-contrast.
//
// Override globally by setting the variables on your app root, or per-component
// by setting them on the component element. Components never hard-code colors,
// spacings, or motion values — they always reach through these tokens, so a
// consumer (mindX console, PARSEC wallet, third-party dApp) can re-skin
// bankoneth without touching the source.
//
// The structure is lifted (not copied) from parsec-wallet's
// src/styles/abstracts/_variables.scss — same token categories, same
// `prefers-reduced-motion` fallback shape, different palette.

import { css } from "lit";

export const tokens = css`
  :host {
    /* ── Surfaces (dark, default) ────────────────────────────────── */
    --b-color-bg-0: #07090d;             /* page background */
    --b-color-bg-1: #0b0d12;             /* deepest surface */
    --b-color-bg-2: #181a20;             /* card surface */
    --b-color-bg-3: #22262e;             /* elevated card */
    --b-color-bg-4: #2a2e36;             /* input + hover */
    --b-color-border:        #2a2e36;
    --b-color-border-strong: #3a3e46;

    /* ── Text ────────────────────────────────────────────────────── */
    --b-color-text-primary:   #e8eaed;
    --b-color-text-secondary: #9aa0a6;
    --b-color-text-muted:     #6b7280;
    --b-color-text-inverse:   #0b0d12;

    /* ── Accents ─────────────────────────────────────────────────── */
    --b-color-accent:    #4a90e2;        /* primary CTA */
    --b-color-accent-2:  #6366f1;        /* secondary CTA */
    --b-color-accent-faded: rgba(74, 144, 226, 0.18);
    --b-color-success:   #10b981;
    --b-color-success-faded: rgba(16, 185, 129, 0.16);
    --b-color-warning:   #f59e0b;
    --b-color-danger:    #ef4444;
    --b-color-danger-faded:  rgba(239, 68, 68, 0.16);
    --b-color-info:      #38bdf8;
    --b-color-focus-ring: #4a90e2;

    /* ── Radii ───────────────────────────────────────────────────── */
    --b-radius-sm:   4px;
    --b-radius-md:   8px;
    --b-radius-lg:   12px;
    --b-radius-xl:   16px;
    --b-radius-full: 9999px;

    /* ── Spacing (4px base) ──────────────────────────────────────── */
    --b-space-0:  0;
    --b-space-1:  4px;
    --b-space-2:  8px;
    --b-space-3:  12px;
    --b-space-4:  16px;
    --b-space-5:  20px;
    --b-space-6:  24px;
    --b-space-8:  32px;
    --b-space-10: 40px;
    --b-space-12: 48px;
    --b-space-16: 64px;

    /* ── Typography ──────────────────────────────────────────────── */
    --b-font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                   "Helvetica Neue", Arial, sans-serif;
    --b-font-mono: "SF Mono", Monaco, "Roboto Mono", "Source Code Pro", monospace;

    /* Fluid scale via clamp() — beats parsec-wallet's fixed-breakpoint sizing. */
    --b-text-xs:  clamp(0.75rem, 0.7rem + 0.25vw, 0.875rem);     /* 12 → 14 */
    --b-text-sm:  clamp(0.875rem, 0.8rem + 0.25vw, 1rem);        /* 14 → 16 */
    --b-text-md:  clamp(1rem, 0.95rem + 0.25vw, 1.125rem);       /* 16 → 18 */
    --b-text-lg:  clamp(1.125rem, 1rem + 0.5vw, 1.375rem);       /* 18 → 22 */
    --b-text-xl:  clamp(1.375rem, 1.2rem + 0.75vw, 1.75rem);     /* 22 → 28 */
    --b-text-2xl: clamp(1.75rem, 1.4rem + 1.5vw, 2.25rem);       /* 28 → 36 */
    --b-text-3xl: clamp(2.25rem, 1.75rem + 2.25vw, 3rem);        /* 36 → 48 */

    --b-leading-tight:   1.2;
    --b-leading-snug:    1.35;
    --b-leading-normal:  1.5;
    --b-leading-relaxed: 1.65;

    --b-weight-regular:  400;
    --b-weight-medium:   500;
    --b-weight-semibold: 600;
    --b-weight-bold:     700;

    /* ── Shadows (dark-mode native) ──────────────────────────────── */
    --b-shadow-sm:  0 1px 2px rgba(0, 0, 0, 0.40);
    --b-shadow-md:  0 4px 12px rgba(0, 0, 0, 0.45), 0 1px 2px rgba(0, 0, 0, 0.30);
    --b-shadow-lg:  0 10px 30px rgba(0, 0, 0, 0.55), 0 4px 6px rgba(0, 0, 0, 0.30);
    --b-shadow-xl:  0 20px 50px rgba(0, 0, 0, 0.60), 0 8px 16px rgba(0, 0, 0, 0.35);
    --b-shadow-focus: 0 0 0 3px var(--b-color-accent-faded);

    /* ── Motion ──────────────────────────────────────────────────── */
    --b-motion-instant: 0ms;
    --b-motion-fast:    150ms;
    --b-motion-base:    250ms;
    --b-motion-slow:    400ms;
    --b-motion-pause:   600ms;

    --b-ease-standard:  cubic-bezier(0.4, 0.0, 0.2, 1);
    --b-ease-decel:     cubic-bezier(0.0, 0.0, 0.2, 1);
    --b-ease-accel:     cubic-bezier(0.4, 0.0, 1.0, 1);
    --b-ease-spring:    cubic-bezier(0.34, 1.56, 0.64, 1);   /* the parsec-missing pop */
    --b-ease-back:      cubic-bezier(0.68, -0.55, 0.27, 1.55);

    /* ── Z-index scale ───────────────────────────────────────────── */
    --b-z-base:     0;
    --b-z-dropdown: 1000;
    --b-z-sticky:   1100;
    --b-z-overlay:  1200;
    --b-z-modal:    1300;
    --b-z-toast:    1400;
  }

  /* ── Light theme override ─────────────────────────────────────── */
  :host([theme="light"]) {
    --b-color-bg-0: #f7f8fa;
    --b-color-bg-1: #ffffff;
    --b-color-bg-2: #f1f3f5;
    --b-color-bg-3: #e9ecef;
    --b-color-bg-4: #dee2e6;
    --b-color-border:        #dee2e6;
    --b-color-border-strong: #ced4da;
    --b-color-text-primary:   #1a1d23;
    --b-color-text-secondary: #495057;
    --b-color-text-muted:     #868e96;
    --b-color-text-inverse:   #ffffff;
    --b-shadow-sm:  0 1px 2px rgba(0, 0, 0, 0.06);
    --b-shadow-md:  0 4px 12px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.04);
    --b-shadow-lg:  0 10px 30px rgba(0, 0, 0, 0.10), 0 4px 6px rgba(0, 0, 0, 0.06);
    --b-shadow-xl:  0 20px 50px rgba(0, 0, 0, 0.12), 0 8px 16px rgba(0, 0, 0, 0.08);
  }

  /* ── High-contrast theme (WCAG AAA) ───────────────────────────── */
  :host([theme="high-contrast"]) {
    --b-color-bg-0: #000000;
    --b-color-bg-1: #000000;
    --b-color-bg-2: #0a0a0a;
    --b-color-bg-3: #161616;
    --b-color-bg-4: #1f1f1f;
    --b-color-border:        #ffffff;
    --b-color-border-strong: #ffffff;
    --b-color-text-primary:   #ffffff;
    --b-color-text-secondary: #d4d4d4;
    --b-color-text-muted:     #a0a0a0;
    --b-color-accent:    #66b0ff;
    --b-color-success:   #00ff88;
    --b-color-danger:    #ff5252;
    --b-color-focus-ring: #ffff00;
    --b-shadow-focus: 0 0 0 3px #ffff00;
  }

  /* ── Reduced motion ───────────────────────────────────────────── */
  @media (prefers-reduced-motion: reduce) {
    :host {
      --b-motion-fast:  0ms;
      --b-motion-base:  0ms;
      --b-motion-slow:  0ms;
      --b-motion-pause: 0ms;
    }
  }
`;
