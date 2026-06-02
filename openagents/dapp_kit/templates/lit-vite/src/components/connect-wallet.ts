// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved

import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import type { ConnectedAccount } from "@openagents/wallet";
import { connect, rememberAddress, recallAddress } from "../lib/wallet.js";

@customElement("openagents-connect-wallet")
export class ConnectWallet extends LitElement {
  static styles = css`
    :host {
      display: block;
    }
    button {
      background: var(--accent, #8be9fd);
      color: #0a0a0f;
      border: 0;
      padding: 10px 18px;
      border-radius: 4px;
      font-weight: 600;
      cursor: pointer;
      font-size: 14px;
    }
    button:hover { filter: brightness(1.1); }
    .connected {
      background: rgba(139, 233, 253, 0.1);
      padding: 12px 16px;
      border-radius: 4px;
      border-left: 3px solid var(--accent, #8be9fd);
      font-family: ui-monospace, SFMono-Regular, monospace;
      font-size: 13px;
    }
    .error { color: #ff6b6b; margin-top: 12px; font-size: 13px; }
    .hint { color: var(--muted, #4a5060); margin-top: 8px; font-size: 12px; }
  `;

  @state() account?: ConnectedAccount;
  @state() error?: string;
  @state() lastAddress?: string;

  override connectedCallback() {
    super.connectedCallback();
    void recallAddress().then((addr) => {
      this.lastAddress = addr;
    });
  }

  private async onClick() {
    this.error = undefined;
    try {
      const account = await connect();
      this.account = account;
      await rememberAddress(account.address);
      this.dispatchEvent(
        new CustomEvent<ConnectedAccount>("account-changed", {
          detail: account,
          bubbles: true,
          composed: true,
        }),
      );
    } catch (err) {
      this.error = err instanceof Error ? err.message : String(err);
    }
  }

  override render() {
    if (this.account) {
      return html`
        <div class="connected">
          ${short(this.account.address)} · chain ${this.account.chainId}
          · ${this.account.rdns}
        </div>
      `;
    }
    return html`
      <button @click=${this.onClick}>Connect wallet</button>
      ${this.lastAddress
        ? html`<div class="hint">Last connected: ${short(this.lastAddress)}</div>`
        : html``}
      ${this.error ? html`<div class="error">${this.error}</div>` : html``}
    `;
  }
}

function short(addr: string): string {
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`;
}
