// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved

import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import type { ConnectedAccount } from "@openagents/wallet";
import { getMode } from "./lib/wallet.js";

@customElement("openagents-app-shell")
export class AppShell extends LitElement {
  static styles = css`
    :host {
      display: block;
      color: var(--fg, #e6edf3);
    }
    h1 {
      font-weight: 600;
      letter-spacing: 0.5px;
    }
    .mode-banner {
      padding: 8px 12px;
      border-radius: 4px;
      margin-bottom: 20px;
      font-size: 12px;
      letter-spacing: 0.5px;
    }
    .mode-web {
      background: rgba(252, 211, 77, 0.15);
      color: #fcd34d;
      border-left: 3px solid #fcd34d;
    }
    .mode-tauri {
      background: rgba(139, 233, 253, 0.12);
      color: var(--accent, #8be9fd);
      border-left: 3px solid var(--accent, #8be9fd);
    }
    section {
      margin: 32px 0;
    }
  `;

  @state()
  account?: ConnectedAccount;

  render() {
    const mode = getMode();
    return html`
      <h1>openagents dApp</h1>
      <div class="mode-banner ${mode === "tauri" ? "mode-tauri" : "mode-web"}">
        ${mode === "tauri"
          ? "TAURI SHELL — keys held in OS keychain"
          : "DEV WEBVIEW — keys clear on tab close. Do not paste mainnet keys."}
      </div>
      <section>
        <openagents-connect-wallet
          @account-changed=${(e: CustomEvent<ConnectedAccount | undefined>) =>
            (this.account = e.detail)}
        ></openagents-connect-wallet>
      </section>
      ${this.account
        ? html`<section>
            <openagents-contract-call .account=${this.account}></openagents-contract-call>
          </section>`
        : html``}
    `;
  }
}
