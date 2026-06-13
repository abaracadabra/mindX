// SPDX-License-Identifier: Apache-2.0
import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";

import { tokens } from "./tokens/tokens";
import { motion } from "./tokens/motion";

/// Display-only pricing card. Token-aligned with @bankoneth/ui design tokens.
@customElement("bankoneth-pricing")
export class BankonethPricing extends LitElement {
  static styles = [
    tokens,
    motion.fadeIn,
    css`
      :host { display: block; font-family: var(--b-font-sans); }
      .card {
        display: grid;
        gap: var(--b-space-1);
        padding: var(--b-space-3) var(--b-space-4);
        background: var(--b-color-bg-2);
        border: 1px solid var(--b-color-border);
        border-radius: var(--b-radius-lg);
      }
      .label { color: var(--b-color-text-muted); font-size: var(--b-text-xs); }
      .v {
        font-size: var(--b-text-lg);
        font-weight: var(--b-weight-semibold);
        color: var(--b-color-text-primary);
        font-family: var(--b-font-mono);
        letter-spacing: -0.01em;
      }
    `,
  ];

  @property() label = "";
  @property({ type: Number }) durationYears = 1;
  @property({ type: Number }) usd6 = 0;
  @property({ type: Number }) eth = 0;

  render() {
    return html`
      <div class="card b-fade-in">
        <div class="label">${this.label}.bankon.eth · ${this.durationYears} year${this.durationYears > 1 ? "s" : ""}</div>
        <div class="v">${(this.usd6 / 1_000_000).toFixed(2)} USD</div>
        ${this.eth > 0 ? html`<div class="label">${this.eth.toFixed(6)} ETH equiv.</div>` : null}
      </div>
    `;
  }
}
