// SPDX-License-Identifier: Apache-2.0
//
// <b-tba-chip> — inline ERC-6551 token-bound-account chip.
//
// Shows the TBA address with a green "AGENT" tag, a copy button, and (when
// `chainExplorerBase` is set) an external-link button to Etherscan / 0G
// explorer. Tooltip on hover surfaces the iNFT chain id + tokenId.

import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";
import { icon } from "../tokens/icons";

@customElement("b-tba-chip")
export class BTbaChip extends LitElement {
  static styles = [
    tokens,
    motion.fadeIn,
    css`
      :host { display: inline-block; font-family: var(--b-font-sans); }
      .chip {
        display: inline-flex; align-items: center; gap: var(--b-space-2);
        padding: var(--b-space-1) var(--b-space-2);
        background: linear-gradient(135deg,
          var(--b-color-accent-faded) 0%,
          color-mix(in srgb, var(--b-color-success-faded) 80%, transparent) 100%);
        border: 1px solid color-mix(in srgb, var(--b-color-accent) 30%, transparent);
        border-radius: var(--b-radius-full);
        font-size: var(--b-text-xs);
        line-height: 1;
      }
      .tag {
        font-family: var(--b-font-mono);
        font-size: 10px;
        font-weight: var(--b-weight-bold);
        letter-spacing: 0.08em;
        color: var(--b-color-success);
        background: var(--b-color-success-faded);
        padding: 3px 6px;
        border-radius: var(--b-radius-sm);
      }
      .addr {
        font-family: var(--b-font-mono);
        font-size: var(--b-text-xs);
        color: var(--b-color-text-primary);
      }
      .ico-btn {
        all: unset; cursor: pointer; display: inline-flex; line-height: 0;
        color: var(--b-color-text-muted);
        padding: 2px;
        border-radius: var(--b-radius-sm);
        transition: color var(--b-motion-fast) var(--b-ease-standard),
                    background var(--b-motion-fast) var(--b-ease-standard);
      }
      .ico-btn:hover { color: var(--b-color-text-primary); background: var(--b-color-bg-3); }
      .ico-btn:focus-visible { outline: none; box-shadow: var(--b-shadow-focus); }
    `,
  ];

  @property() tba = "" as `0x${string}` | "";
  @property({ type: Number }) chainId = 0;
  @property() chainExplorerBase = "";

  private _copy() { navigator.clipboard?.writeText(this.tba).catch(() => {}); }

  render() {
    if (!this.tba || this.tba === "0x0000000000000000000000000000000000000000") return null;
    const short = `${this.tba.slice(0, 6)}…${this.tba.slice(-4)}`;
    return html`
      <span class="chip b-fade-in" title="ERC-6551 token-bound agent wallet${this.chainId ? ` on chain ${this.chainId}` : ""}">
        <span class="tag">AGENT</span>
        <span class="addr">${short}</span>
        <button class="ico-btn" @click=${this._copy} aria-label="Copy agent wallet address">${unsafeHTML(icon.copy)}</button>
        ${this.chainExplorerBase ? html`
          <a class="ico-btn" target="_blank" rel="noopener"
             href="${this.chainExplorerBase}${this.tba}"
             aria-label="Open agent wallet on block explorer">${unsafeHTML(icon.external)}</a>
        ` : null}
      </span>
    `;
  }
}
