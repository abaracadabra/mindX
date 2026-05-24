// SPDX-License-Identifier: Apache-2.0
import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";

import { tokens } from "./tokens/tokens";

export type Flow = "subname" | "purchase" | "host";

@customElement("bankoneth-flow-tabs")
export class BankonethFlowTabs extends LitElement {
  static styles = [
    tokens,
    css`
      :host { display: block; font-family: var(--b-font-sans); }
      .tabs {
        display: flex; gap: var(--b-space-1);
        padding: var(--b-space-1);
        background: var(--b-color-bg-3);
        border-radius: var(--b-radius-lg);
        margin-bottom: var(--b-space-4);
      }
      button {
        flex: 1; cursor: pointer; border: 0;
        padding: var(--b-space-3) var(--b-space-4);
        background: transparent; color: var(--b-color-text-secondary);
        font-family: inherit;
        font-size: var(--b-text-sm);
        font-weight: var(--b-weight-medium);
        border-radius: var(--b-radius-md);
        transition: background var(--b-motion-fast) var(--b-ease-standard),
                    color var(--b-motion-fast) var(--b-ease-standard);
      }
      button:hover:not([aria-selected="true"]) { color: var(--b-color-text-primary); }
      button[aria-selected="true"] {
        background: var(--b-color-bg-1);
        color: var(--b-color-text-primary);
        font-weight: var(--b-weight-semibold);
        box-shadow: var(--b-shadow-sm);
      }
      button:focus-visible { outline: none; box-shadow: var(--b-shadow-focus); }
      .hint {
        color: var(--b-color-text-muted);
        font-size: var(--b-text-xs);
        margin-bottom: var(--b-space-4);
      }
    `,
  ];

  @property({ reflect: true }) selected: Flow = "subname";

  private _select(f: Flow) {
    this.selected = f;
    this.dispatchEvent(new CustomEvent("change", {
      detail: { selected: f }, bubbles: true, composed: true,
    }));
  }

  render() {
    return html`
      <div class="tabs" role="tablist" aria-label="Issuance flow">
        <button role="tab" aria-selected=${this.selected === "subname"  ? "true" : "false"} @click=${() => this._select("subname")}>A · *.bankon.eth</button>
        <button role="tab" aria-selected=${this.selected === "purchase" ? "true" : "false"} @click=${() => this._select("purchase")}>B · Buy .eth</button>
        <button role="tab" aria-selected=${this.selected === "host"     ? "true" : "false"} @click=${() => this._select("host")}>C · Host your .eth</button>
      </div>
      <div class="hint">
        ${this.selected === "subname"
          ? "Claim a subname under bankon.eth — alice.bankon.eth, ada.bankon.eth, …"
          : this.selected === "purchase"
          ? "Buy a brand-new .eth 2LD (ENS commit-reveal, wrapped through bankoneth)."
          : "Plug your existing .eth into bankoneth's issuance pipeline. Subdomain-minting-as-a-service."}
      </div>
    `;
  }
}
