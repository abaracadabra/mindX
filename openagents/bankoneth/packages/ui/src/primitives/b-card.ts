// SPDX-License-Identifier: Apache-2.0
//
// <b-card> — surface container with elevation tiers.
//
// Variants:
//   - flat                — no shadow, just border (default)
//   - elevated            — md shadow, no border
//   - floating            — lg shadow + hover lift (2px translateY)
//
// Slots:
//   - header   (top row — title, optional action)
//   - default  (body)
//   - footer   (bottom row — actions)

import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";

export type CardVariant = "flat" | "elevated" | "floating";

@customElement("b-card")
export class BCard extends LitElement {
  static styles = [
    tokens,
    motion.fadeIn,
    css`
      :host { display: block; font-family: var(--b-font-sans); }
      .card {
        background: var(--b-color-bg-2);
        border-radius: var(--b-radius-lg);
        padding: var(--b-space-5);
        color: var(--b-color-text-primary);
        transition: transform var(--b-motion-base) var(--b-ease-spring),
                    box-shadow var(--b-motion-base) var(--b-ease-standard),
                    background var(--b-motion-base) var(--b-ease-standard);
      }
      :host([variant="flat"]) .card     { border: 1px solid var(--b-color-border); }
      :host                   .card     { border: 1px solid var(--b-color-border); }
      :host([variant="elevated"]) .card { border: 0; box-shadow: var(--b-shadow-md); }
      :host([variant="floating"]) .card { border: 0; box-shadow: var(--b-shadow-lg); }
      :host([variant="floating"]) .card:hover { transform: translateY(-2px); box-shadow: var(--b-shadow-xl); }

      :host([padding="sm"]) .card { padding: var(--b-space-3); }
      :host([padding="lg"]) .card { padding: var(--b-space-8); }

      .head, .foot {
        display: flex; align-items: center; justify-content: space-between;
        gap: var(--b-space-3);
      }
      .head { margin: 0 0 var(--b-space-4) 0; }
      .foot { margin: var(--b-space-5) 0 0 0; }
      ::slotted([slot="header"]) {
        font-size: var(--b-text-lg);
        font-weight: var(--b-weight-semibold);
        color: var(--b-color-text-primary);
      }
    `,
  ];

  @property({ reflect: true }) variant: CardVariant = "elevated";
  @property({ reflect: true }) padding: "sm" | "md" | "lg" = "md";

  render() {
    return html`
      <div class="card b-fade-in">
        <header class="head"><slot name="header"></slot></header>
        <slot></slot>
        <footer class="foot"><slot name="footer"></slot></footer>
      </div>
    `;
  }
}
