// SPDX-License-Identifier: Apache-2.0
//
// @bankoneth/ui — motion library.
//
// Tagged-CSS fragments for entrance / exit / loading / microinteraction
// animations. Compose into a component's `static styles` array alongside
// `tokens` and the component's local CSS.
//
// The keyframes lift the structure of parsec-wallet's
// src/styles/base/_animations.scss (14 keyframes, prefers-reduced-motion
// handling) but translate to Lit-friendly tagged template fragments so
// components opt in by composition, not by CSS imports.

import { css } from "lit";

export const motion = {
  /** Soft fade-in for content entering view. */
  fadeIn: css`
    @keyframes b-fade-in {
      from { opacity: 0; }
      to   { opacity: 1; }
    }
    .b-fade-in { animation: b-fade-in var(--b-motion-base) var(--b-ease-decel) both; }
  `,

  /** Fade + 8px translateY — content arriving from below. */
  slideUp: css`
    @keyframes b-slide-up {
      from { opacity: 0; transform: translateY(8px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .b-slide-up { animation: b-slide-up var(--b-motion-base) var(--b-ease-decel) both; }
  `,

  /** Card / modal pop using the spring easing — bankoneth's signature feel. */
  pop: css`
    @keyframes b-pop {
      0%   { opacity: 0; transform: scale(0.92); }
      60%  { opacity: 1; transform: scale(1.02); }
      100% { opacity: 1; transform: scale(1.00); }
    }
    .b-pop { animation: b-pop var(--b-motion-slow) var(--b-ease-spring) both; }
  `,

  /** Staggered list item appearance. Combine with --b-stagger-i inline style. */
  stagger: css`
    @keyframes b-stagger {
      from { opacity: 0; transform: translateY(6px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    .b-stagger {
      animation: b-stagger var(--b-motion-base) var(--b-ease-decel) both;
      animation-delay: calc(var(--b-stagger-i, 0) * 60ms);
    }
  `,

  /** Continuous gentle pulse for loading dots / placeholders. */
  pulse: css`
    @keyframes b-pulse {
      0%, 100% { opacity: 1; }
      50%      { opacity: 0.45; }
    }
    .b-pulse { animation: b-pulse 1.6s var(--b-ease-standard) infinite; }
  `,

  /** Rotating spinner. */
  spin: css`
    @keyframes b-spin {
      from { transform: rotate(0deg); }
      to   { transform: rotate(360deg); }
    }
    .b-spin { animation: b-spin 0.8s linear infinite; }
  `,

  /** Shake — used to call attention to validation errors. */
  shake: css`
    @keyframes b-shake {
      0%, 100% { transform: translateX(0); }
      20%      { transform: translateX(-4px); }
      40%      { transform: translateX(4px); }
      60%      { transform: translateX(-3px); }
      80%      { transform: translateX(3px); }
    }
    .b-shake { animation: b-shake 380ms var(--b-ease-standard); }
  `,

  /** Ring countdown — used by the commit-reveal timer in Flow B. */
  ringCountdown: css`
    @keyframes b-ring {
      from { stroke-dashoffset: 0; }
      to   { stroke-dashoffset: var(--b-ring-circumference, 283); }
    }
    .b-ring {
      animation: b-ring var(--b-ring-duration, 60s) linear forwards;
    }
  `,

  /** Slide between rail-switcher options — driven via CSS var for direction. */
  railSlide: css`
    .b-rail-track {
      transition: transform var(--b-motion-base) var(--b-ease-spring);
      will-change: transform;
    }
  `,

  /** Ripple — for b-button press affordance. */
  ripple: css`
    @keyframes b-ripple {
      from { opacity: 0.35; transform: scale(0); }
      to   { opacity: 0;    transform: scale(2.5); }
    }
    .b-ripple {
      position: absolute;
      border-radius: 50%;
      pointer-events: none;
      background: currentColor;
      animation: b-ripple 600ms var(--b-ease-decel) forwards;
    }
  `,

  /** Spring press — scale + spring-back used by b-button on :active. */
  springPress: css`
    .b-spring-press {
      transition: transform var(--b-motion-fast) var(--b-ease-spring);
    }
    .b-spring-press:active:not(:disabled) {
      transform: scale(0.97);
    }
  `,
} as const;
