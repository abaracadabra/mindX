// SPDX-License-Identifier: Apache-2.0
//
// <b-rail-switcher> — UX win #3, the tri-rail payment toggle.
//
// Horizontal control with three segments (ETH / USDC permit / Algorand USDC
// via x402-avm). An animated slider pill glides under the active segment
// using the spring easing. Each segment shows the chain icon + label + a
// live quote in that asset, with the relative price between assets
// computed in real time by the parent.
//
// Parsec-wallet is Algorand-only. bankoneth's cross-asset rail UX is
// genuinely novel.

import { LitElement, html, css } from "lit";
import { customElement, property, query } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";
import { icon } from "../tokens/icons";

export type Rail = "eth" | "usdc-permit" | "x402-avm";

interface RailMeta {
  id:    Rail;
  label: string;
  short: string;
  ico:   keyof typeof icon;
}

const RAILS: RailMeta[] = [
  { id: "eth",         label: "Ethereum",       short: "ETH",  ico: "ethereum" },
  { id: "usdc-permit", label: "USDC (permit)",  short: "USDC", ico: "usdc"     },
  { id: "x402-avm",    label: "Algorand USDC",  short: "x402", ico: "algorand" },
];

@customElement("b-rail-switcher")
export class BRailSwitcher extends LitElement {
  static styles = [
    tokens,
    motion.railSlide,
    motion.fadeIn,
    css`
      :host { display: block; font-family: var(--b-font-sans); }
      .wrap {
        position: relative;
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 0;
        padding: var(--b-space-1);
        background: var(--b-color-bg-3);
        border-radius: var(--b-radius-lg);
        overflow: hidden;
      }
      .indicator {
        position: absolute;
        top: var(--b-space-1);
        bottom: var(--b-space-1);
        width: calc((100% - var(--b-space-2)) / 3);
        background: var(--b-color-bg-1);
        border-radius: var(--b-radius-md);
        box-shadow: var(--b-shadow-sm);
        transform: translateX(var(--b-rail-x, 0%));
        transition: transform var(--b-motion-base) var(--b-ease-spring);
        pointer-events: none;
        z-index: 0;
      }
      button.seg {
        all: unset;
        position: relative;
        z-index: 1;
        cursor: pointer;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: var(--b-space-1);
        padding: var(--b-space-3) var(--b-space-2);
        color: var(--b-color-text-secondary);
        font-size: var(--b-text-xs);
        font-weight: var(--b-weight-medium);
        transition: color var(--b-motion-fast) var(--b-ease-standard);
      }
      button.seg[aria-selected="true"] { color: var(--b-color-text-primary); }
      button.seg:focus-visible          { outline: none; box-shadow: var(--b-shadow-focus); border-radius: var(--b-radius-md); }
      button.seg:hover:not([aria-selected="true"]) { color: var(--b-color-text-primary); }
      .seg .ico  { display: inline-flex; line-height: 0; font-size: 1.4em; color: var(--b-color-accent); }
      .seg .short{ font-weight: var(--b-weight-semibold); }
      .seg .full { color: var(--b-color-text-muted); font-size: var(--b-text-xs); }

      .quotes {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: var(--b-space-2);
        margin-top: var(--b-space-3);
        padding: 0 var(--b-space-2);
        font-size: var(--b-text-xs);
        color: var(--b-color-text-muted);
        font-family: var(--b-font-mono);
        text-align: center;
      }
      .quotes span[aria-selected="true"] { color: var(--b-color-text-primary); }
    `,
  ];

  @property({ reflect: true }) selected: Rail = "eth";
  /** Optional live quote per rail, formatted however the parent likes ("$5.00", "0.0019 ETH"). */
  @property({ type: Object }) quotes: Partial<Record<Rail, string>> = {};

  private _pick(r: Rail) {
    if (this.selected === r) return;
    this.selected = r;
    this.dispatchEvent(new CustomEvent("b-rail", {
      detail: { selected: r }, bubbles: true, composed: true,
    }));
  }

  render() {
    const idx = RAILS.findIndex(r => r.id === this.selected);
    const translate = idx <= 0 ? "0%" : idx === 1 ? "100%" : "200%";
    return html`
      <div class="wrap" role="tablist" aria-label="Payment rail" style="--b-rail-x: ${translate};">
        <div class="indicator"></div>
        ${RAILS.map(r => html`
          <button
            class="seg"
            role="tab"
            aria-selected=${r.id === this.selected ? "true" : "false"}
            @click=${() => this._pick(r.id)}
          >
            <span class="ico">${unsafeHTML(icon[r.ico])}</span>
            <span class="short">${r.short}</span>
            <span class="full">${r.label}</span>
          </button>
        `)}
      </div>
      <div class="quotes b-fade-in">
        ${RAILS.map(r => html`
          <span aria-selected=${r.id === this.selected ? "true" : "false"}>
            ${this.quotes[r.id] ?? "—"}
          </span>
        `)}
      </div>
    `;
  }
}
