// SPDX-License-Identifier: Apache-2.0
//
// <b-namehash-preview> — UX win #1, the headline differentiator.
//
// Renders a card that shows, *before the user signs anything*:
//   - the full subname (alice.bankon.eth)
//   - the bytes32 ENS namehash (truncated, with copy button)
//   - the deterministic ERC-6551 TBA address (truncated, with copy button)
//   - a status line ("TBA derived offline · matches the post-mint resolver")
//
// Parsec-wallet only shows app IDs *after* mint. bankoneth shows the full
// resolution chain *before* sign — the user knows the wallet address the
// agent will inherit before they hit the button.

import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";
import { icon } from "../tokens/icons";

@customElement("b-namehash-preview")
export class BNamehashPreview extends LitElement {
  static styles = [
    tokens,
    motion.fadeIn,
    css`
      :host { display: block; font-family: var(--b-font-sans); }
      .card {
        display: grid;
        gap: var(--b-space-3);
        padding: var(--b-space-4);
        background: var(--b-color-bg-2);
        border: 1px solid var(--b-color-border);
        border-radius: var(--b-radius-lg);
      }
      .row {
        display: grid;
        grid-template-columns: auto 1fr auto;
        gap: var(--b-space-3);
        align-items: center;
        font-size: var(--b-text-xs);
      }
      .lbl { color: var(--b-color-text-muted); font-weight: var(--b-weight-medium); }
      .val {
        font-family: var(--b-font-mono);
        color: var(--b-color-text-primary);
        font-size: var(--b-text-xs);
        word-break: break-all;
      }
      .name {
        font-family: var(--b-font-mono);
        font-size: var(--b-text-lg);
        color: var(--b-color-accent);
        font-weight: var(--b-weight-semibold);
        letter-spacing: -0.02em;
      }
      .empty {
        text-align: center;
        padding: var(--b-space-6) var(--b-space-3);
        color: var(--b-color-text-muted);
        font-size: var(--b-text-sm);
      }
      button.copy {
        all: unset;
        cursor: pointer;
        display: inline-flex;
        color: var(--b-color-text-muted);
        padding: var(--b-space-1);
        border-radius: var(--b-radius-sm);
        line-height: 0;
        transition: color var(--b-motion-fast) var(--b-ease-standard),
                    background var(--b-motion-fast) var(--b-ease-standard);
      }
      button.copy:hover         { color: var(--b-color-text-primary); background: var(--b-color-bg-3); }
      button.copy:focus-visible { outline: none; box-shadow: var(--b-shadow-focus); }

      .footnote {
        display: flex; align-items: center; gap: var(--b-space-2);
        font-size: var(--b-text-xs);
        color: var(--b-color-text-muted);
      }
      .ok { color: var(--b-color-success); display: inline-flex; line-height: 0; }
    `,
  ];

  /** Subname being previewed, e.g. "alice.bankon.eth". Empty → empty state. */
  @property() subname = "";
  /** bytes32 ENS namehash of the subname. */
  @property() namehashHex = "" as `0x${string}` | "";
  /** Deterministically-derived ERC-6551 TBA address (computed off-chain). */
  @property() tbaAddress = "" as `0x${string}` | "";

  private _copy(text: string) {
    navigator.clipboard?.writeText(text).catch(() => {});
  }

  render() {
    if (!this.subname) {
      return html`
        <div class="card b-fade-in">
          <div class="empty">Type a label to preview the namehash and the agent wallet.</div>
        </div>
      `;
    }
    return html`
      <div class="card b-fade-in">
        <div class="name">${this.subname}</div>

        ${this.namehashHex ? html`
          <div class="row">
            <span class="lbl">namehash</span>
            <span class="val">${this._truncate(this.namehashHex)}</span>
            <button class="copy" @click=${() => this._copy(this.namehashHex)}
              aria-label="Copy namehash to clipboard"
              title="Copy namehash">${unsafeHTML(icon.copy)}</button>
          </div>
        ` : null}

        ${this.tbaAddress ? html`
          <div class="row">
            <span class="lbl">agent wallet (TBA)</span>
            <span class="val">${this._truncate(this.tbaAddress)}</span>
            <button class="copy" @click=${() => this._copy(this.tbaAddress)}
              aria-label="Copy TBA address to clipboard"
              title="Copy TBA">${unsafeHTML(icon.copy)}</button>
          </div>
        ` : null}

        ${this.tbaAddress ? html`
          <div class="footnote">
            <span class="ok">${unsafeHTML(icon.shield)}</span>
            Derived offline — matches the post-mint resolver output.
          </div>
        ` : null}
      </div>
    `;
  }

  private _truncate(s: string): string {
    if (s.length < 24) return s;
    return `${s.slice(0, 10)}…${s.slice(-8)}`;
  }
}
