// SPDX-License-Identifier: Apache-2.0
//
// <b-suggestions> — UX win #4, the "your label is taken" rescue list.
//
// Renders horizontally-scrolling chip cards. Each chip:
//   - shows the suggested label
//   - shows a green check (available) or red × (also taken, dimmed)
//   - shows a small reason ("numeric suffix", "current year", "wallet-prefix")
//   - on click, dispatches `b-suggestion-pick` with the label
//
// Parsec-wallet doesn't surface alternatives when an NFD name is taken.

import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";
import { icon } from "../tokens/icons";

export interface SuggestionItem {
  label: string;
  available: boolean;
  reason: string;
}

@customElement("b-suggestions")
export class BSuggestions extends LitElement {
  static styles = [
    tokens,
    motion.stagger,
    motion.fadeIn,
    css`
      :host { display: block; font-family: var(--b-font-sans); }
      .heading {
        display: flex; align-items: center; gap: var(--b-space-2);
        margin: 0 0 var(--b-space-2);
        font-size: var(--b-text-sm);
        color: var(--b-color-text-secondary);
        font-weight: var(--b-weight-medium);
      }
      .scroll {
        display: flex;
        gap: var(--b-space-2);
        overflow-x: auto;
        padding-bottom: var(--b-space-2);
        scrollbar-width: thin;
        scrollbar-color: var(--b-color-border-strong) transparent;
      }
      .scroll::-webkit-scrollbar { height: 6px; }
      .scroll::-webkit-scrollbar-thumb { background: var(--b-color-border-strong); border-radius: var(--b-radius-full); }

      button.chip {
        all: unset;
        cursor: pointer;
        display: inline-flex;
        flex-direction: column;
        gap: var(--b-space-1);
        padding: var(--b-space-3) var(--b-space-4);
        background: var(--b-color-bg-2);
        border: 1px solid var(--b-color-border);
        border-radius: var(--b-radius-md);
        transition: background var(--b-motion-fast) var(--b-ease-standard),
                    border var(--b-motion-fast) var(--b-ease-standard),
                    transform var(--b-motion-fast) var(--b-ease-spring);
        min-width: 130px;
      }
      button.chip:hover:not(:disabled) {
        background: var(--b-color-bg-3);
        border-color: var(--b-color-accent);
        transform: translateY(-1px);
      }
      button.chip:focus-visible { outline: none; box-shadow: var(--b-shadow-focus); }
      button.chip:disabled { opacity: 0.55; cursor: not-allowed; }

      .top {
        display: flex; align-items: center; gap: var(--b-space-2);
        font-family: var(--b-font-mono);
        font-size: var(--b-text-sm);
        color: var(--b-color-text-primary);
      }
      .top .ico { display: inline-flex; line-height: 0; font-size: 1em; }
      .free  .ico  { color: var(--b-color-success); }
      .taken .ico  { color: var(--b-color-danger); }
      .reason {
        font-size: var(--b-text-xs);
        color: var(--b-color-text-muted);
        font-weight: var(--b-weight-regular);
      }
    `,
  ];

  @property({ type: Array }) items: SuggestionItem[] = [];

  private _pick(label: string) {
    this.dispatchEvent(new CustomEvent("b-suggestion-pick", {
      detail: { label }, bubbles: true, composed: true,
    }));
  }

  render() {
    if (this.items.length === 0) return null;
    return html`
      <div class="b-fade-in">
        <p class="heading">
          <span style="display:inline-flex;line-height:0;">${unsafeHTML(icon.flame)}</span>
          Try one of these instead
        </p>
        <div class="scroll" role="list">
          ${this.items.map((s, i) => html`
            <button
              role="listitem"
              class="chip b-stagger ${s.available ? "free" : "taken"}"
              style="--b-stagger-i: ${i};"
              ?disabled=${!s.available}
              title=${s.available ? `Claim ${s.label}` : `${s.label} is taken`}
              @click=${() => s.available && this._pick(s.label)}
            >
              <span class="top">
                <span class="ico">${unsafeHTML(s.available ? icon.check : icon.cross)}</span>
                ${s.label}
              </span>
              <span class="reason">${s.reason}</span>
            </button>
          `)}
        </div>
      </div>
    `;
  }
}
