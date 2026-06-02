// SPDX-License-Identifier: Apache-2.0
import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";

import { tokens } from "./tokens/tokens";

/// Standalone iNFT mode-A toggle. Emits `change` with the new value.
@customElement("bankoneth-inft-toggle")
export class BankonethInftToggle extends LitElement {
  static styles = [
    tokens,
    css`
      :host { display: block; font-family: var(--b-font-sans); }
      label {
        display: flex; gap: var(--b-space-2); align-items: center;
        color: var(--b-color-text-primary);
        font-size: var(--b-text-sm);
        cursor: pointer;
      }
      input[type="checkbox"] {
        accent-color: var(--b-color-accent);
        width: 16px; height: 16px;
      }
      input[type="checkbox"]:focus-visible {
        outline: none; box-shadow: var(--b-shadow-focus); border-radius: 2px;
      }
      .hint {
        margin: var(--b-space-1) 0 0 calc(var(--b-space-2) + 18px);
        color: var(--b-color-text-muted);
        font-size: var(--b-text-xs);
      }
    `,
  ];

  @property({ type: Boolean, reflect: true }) enabled = true;

  private _onChange(e: Event) {
    this.enabled = (e.target as HTMLInputElement).checked;
    this.dispatchEvent(new CustomEvent("change", {
      detail: { enabled: this.enabled }, bubbles: true, composed: true,
    }));
  }

  render() {
    return html`
      <label>
        <input type="checkbox" .checked=${this.enabled} @change=${this._onChange} />
        Wrap as iNFT (ERC-7857 + ERC-6551 TBA on 0G)
      </label>
      <div class="hint">One token in your wallet; deterministic agent wallet derived.</div>
    `;
  }
}
