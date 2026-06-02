// SPDX-License-Identifier: Apache-2.0
//
// <b-renew-countdown> — UX win #4 (renewal nudge), surfaced on the success step.
//
// Shows a card with:
//   - days/months until expiry as a big number
//   - a thin ring that visually represents the % of lifetime remaining
//   - a "Renew now" button that dispatches `b-renew` for the parent flow to handle
//
// Parsec-wallet buries lease info inside the manage tab. bankoneth surfaces
// it the moment a subname is minted — and the user can act on it in one click.

import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";
import { icon } from "../tokens/icons";

@customElement("b-renew-countdown")
export class BRenewCountdown extends LitElement {
  static styles = [
    tokens,
    motion.fadeIn,
    css`
      :host { display: block; font-family: var(--b-font-sans); }
      .card {
        display: grid;
        grid-template-columns: 96px 1fr auto;
        gap: var(--b-space-4);
        align-items: center;
        padding: var(--b-space-4) var(--b-space-5);
        background: var(--b-color-bg-2);
        border: 1px solid var(--b-color-border);
        border-radius: var(--b-radius-lg);
      }
      .ring { position: relative; width: 96px; height: 96px; }
      .ring svg { transform: rotate(-90deg); display: block; }
      .ring circle { fill: none; stroke-width: 6; transition: stroke-dashoffset var(--b-motion-slow) var(--b-ease-standard); }
      .ring .bg  { stroke: var(--b-color-bg-4); }
      .ring .fg  { stroke: var(--b-color-accent); stroke-linecap: round; }
      .ring .pct {
        position: absolute; inset: 0;
        display: flex; align-items: center; justify-content: center;
        font-size: var(--b-text-sm); font-weight: var(--b-weight-semibold);
        color: var(--b-color-text-primary);
      }

      .meta { display: grid; gap: var(--b-space-1); }
      .big {
        font-size: var(--b-text-2xl);
        font-weight: var(--b-weight-bold);
        color: var(--b-color-text-primary);
        letter-spacing: -0.02em;
      }
      .small {
        font-size: var(--b-text-xs);
        color: var(--b-color-text-muted);
      }
      .renew {
        all: unset;
        cursor: pointer;
        display: inline-flex; align-items: center; gap: var(--b-space-2);
        padding: var(--b-space-3) var(--b-space-4);
        background: var(--b-color-accent-faded);
        color: var(--b-color-accent);
        font-weight: var(--b-weight-semibold);
        font-size: var(--b-text-sm);
        border-radius: var(--b-radius-md);
        transition: background var(--b-motion-fast) var(--b-ease-standard),
                    transform var(--b-motion-fast) var(--b-ease-spring);
      }
      .renew:hover         { background: color-mix(in srgb, var(--b-color-accent-faded) 70%, white); }
      .renew:active        { transform: scale(0.97); }
      .renew:focus-visible { outline: none; box-shadow: var(--b-shadow-focus); }
      .renew .ico { display: inline-flex; line-height: 0; }

      @media (max-width: 480px) {
        .card { grid-template-columns: 72px 1fr; }
        .ring { width: 72px; height: 72px; }
        .renew { grid-column: 1 / -1; justify-self: stretch; justify-content: center; }
      }
    `,
  ];

  /** Unix-seconds expiry. Triggers all derived display values. */
  @property({ type: Number }) expiresAt = 0;
  /** Total duration in years from initial registration. Used for the ring %. */
  @property({ type: Number }) durationYears = 1;

  render() {
    const now = Math.floor(Date.now() / 1000);
    const totalSec = this.durationYears * 365 * 24 * 3600;
    const remaining = Math.max(0, this.expiresAt - now);
    const pct = totalSec > 0 ? remaining / totalSec : 0;
    const days = Math.round(remaining / 86400);
    const big = days >= 365 ? `${(days / 365).toFixed(1)} yr` :
                days >= 30  ? `${Math.round(days / 30)} mo` :
                              `${days} d`;
    const circumference = 2 * Math.PI * 44;
    const offset = circumference * (1 - pct);

    return html`
      <div class="card b-fade-in">
        <div class="ring" aria-hidden="true">
          <svg width="96" height="96" viewBox="0 0 100 100">
            <circle class="bg" cx="50" cy="50" r="44"/>
            <circle class="fg" cx="50" cy="50" r="44"
              stroke-dasharray=${circumference}
              stroke-dashoffset=${offset}
            />
          </svg>
          <div class="pct">${Math.round(pct * 100)}%</div>
        </div>
        <div class="meta">
          <span class="big">${big} left</span>
          <span class="small">expires ${new Date(this.expiresAt * 1000).toISOString().slice(0, 10)}</span>
          <span class="small">${this.durationYears}-year registration</span>
        </div>
        <button class="renew" @click=${() => this.dispatchEvent(new CustomEvent("b-renew", { bubbles: true, composed: true }))}>
          <span class="ico">${unsafeHTML(icon.clock)}</span>
          Renew now
        </button>
      </div>
    `;
  }
}
