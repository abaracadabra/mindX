// SPDX-License-Identifier: Apache-2.0
//
// <b-connect-bar> — persistent header bar for the bankoneth dApp.
//
// States rendered:
//   - no-wallet      : window.ethereum missing → "Install MetaMask / Rabby" banner
//   - disconnected   : "Connect wallet" button
//   - connected/main : Ethereum chip + short address + primary .eth name
//   - connected/alt  : amber chain chip with "Switch" button + short address
//
// Subscribes to BankonethSession; re-renders on state changes. Dispatches
// CustomEvents the host page can act on:
//   - connect-clicked
//   - disconnect-clicked
//   - switch-chain-clicked  (detail: { targetChainId: 1 })
//
// All events bubble + are composed so a parent listener on the document
// root catches everything. Reuses <b-button> for the CTAs.

import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";
import { icon } from "../tokens/icons";

import type { BankonethSession, SessionState } from "@bankoneth/core";

type ChainNamer = (chainId: number) => string;

const DEFAULT_CHAIN_NAME: ChainNamer = (id) => {
  switch (id) {
    case 1:           return "Ethereum";
    case 10:          return "Optimism";
    case 137:         return "Polygon";
    case 8453:        return "Base";
    case 42161:       return "Arbitrum";
    case 11155111:    return "Sepolia";
    default:          return `chain ${id}`;
  }
};

@customElement("b-connect-bar")
export class BankonethConnectBar extends LitElement {
  static styles = [
    tokens,
    motion.fadeIn,
    css`
      :host { display: block; font-family: var(--b-font-sans); }
      .bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--b-space-3);
        padding: var(--b-space-3) var(--b-space-5);
        background: var(--b-color-bg-3);
        border-bottom: 1px solid var(--b-color-border);
      }
      .brand {
        font-family: var(--b-font-mono);
        font-size: var(--b-text-sm);
        font-weight: var(--b-weight-semibold);
        color: var(--b-color-text-primary);
        letter-spacing: -0.01em;
      }
      .right {
        display: flex;
        align-items: center;
        gap: var(--b-space-2);
      }
      /* Chain chip */
      .chain {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: var(--b-radius-full);
        font-size: 11px;
        font-family: var(--b-font-mono);
        font-weight: var(--b-weight-semibold);
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }
      .chain[data-state="ok"] {
        background: var(--b-color-success-faded);
        color: var(--b-color-success);
        border: 1px solid color-mix(in srgb, var(--b-color-success) 30%, transparent);
      }
      .chain[data-state="warn"] {
        background: color-mix(in srgb, var(--b-color-danger-faded) 50%, var(--b-color-bg-2));
        color: var(--b-color-danger);
        border: 1px solid color-mix(in srgb, var(--b-color-danger) 30%, transparent);
        gap: 6px;
      }
      /* Address chip */
      .acct {
        display: inline-flex;
        align-items: center;
        gap: var(--b-space-2);
        padding: 4px 10px;
        background: var(--b-color-bg-2);
        border: 1px solid var(--b-color-border);
        border-radius: var(--b-radius-full);
        font-size: var(--b-text-xs);
      }
      .dot {
        width: 6px; height: 6px;
        border-radius: 50%;
        background: var(--b-color-success);
        box-shadow: 0 0 0 2px color-mix(in srgb, var(--b-color-success) 25%, transparent);
      }
      .addr {
        font-family: var(--b-font-mono);
        color: var(--b-color-text-primary);
      }
      .primary {
        font-family: var(--b-font-mono);
        color: var(--b-color-accent);
      }
      .sep {
        color: var(--b-color-text-muted);
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

      /* No-extension banner sits below the bar. */
      .banner {
        padding: var(--b-space-3) var(--b-space-5);
        background: color-mix(in srgb, var(--b-color-accent-faded) 80%, transparent);
        color: var(--b-color-text-primary);
        font-size: var(--b-text-xs);
        border-bottom: 1px solid var(--b-color-border);
      }
      .banner a { color: var(--b-color-accent); text-decoration: underline; }

      /* Error toast inside the bar. */
      .err {
        font-size: var(--b-text-xs);
        color: var(--b-color-danger);
        font-family: var(--b-font-mono);
      }
    `,
  ];

  /** The session to subscribe to. Required for connected/disconnected toggle. */
  @property({ attribute: false }) session?: BankonethSession;

  /** Brand label shown on the left. */
  @property() brand = "bankon.eth";

  /** Override the default chainId → human-name mapping. */
  @property({ attribute: false }) chainName: ChainNamer = DEFAULT_CHAIN_NAME;

  /** Target chainId for the "Switch" CTA. Defaults to 1 (mainnet). */
  @property({ type: Number }) targetChainId = 1;

  @state() private _s: SessionState = {
    connected: false, address: null, primaryName: null, chainId: 1, walletAvailable: false,
  };
  @state() private _err = "";
  @state() private _busy: "connect" | "switch" | "disconnect" | "" = "";

  private _unsub?: () => void;

  connectedCallback() {
    super.connectedCallback();
    if (this.session) {
      this._s = this.session.state();
      this._unsub = this.session.subscribe(s => { this._s = s; this.requestUpdate(); });
    }
  }
  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._unsub) this._unsub();
  }

  willUpdate(changed: Map<string, unknown>) {
    if (changed.has("session") && this.session) {
      if (this._unsub) this._unsub();
      this._s = this.session.state();
      this._unsub = this.session.subscribe(s => { this._s = s; this.requestUpdate(); });
    }
  }

  private async _connect() {
    if (!this.session) return;
    this._err = ""; this._busy = "connect";
    try { await this.session.connect(); }
    catch (e: unknown) {
      const msg = (e as { message?: string } | undefined)?.message ?? "connect failed";
      this._err = msg;
    }
    finally { this._busy = ""; }
    this.dispatchEvent(new CustomEvent("connect-clicked", { bubbles: true, composed: true }));
  }

  private async _disconnect() {
    if (!this.session) return;
    this._busy = "disconnect";
    try { await this.session.disconnect(); }
    finally { this._busy = ""; }
    this.dispatchEvent(new CustomEvent("disconnect-clicked", { bubbles: true, composed: true }));
  }

  private async _switch() {
    if (!this.session) return;
    this._err = ""; this._busy = "switch";
    try { await this.session.switchChain(this.targetChainId); }
    catch (e: unknown) {
      const msg = (e as { message?: string } | undefined)?.message ?? "switch failed";
      this._err = msg;
    }
    finally { this._busy = ""; }
    this.dispatchEvent(new CustomEvent("switch-chain-clicked", {
      bubbles: true, composed: true,
      detail: { targetChainId: this.targetChainId },
    }));
  }

  private _shortAddr(addr: string): string {
    return `${addr.slice(0, 6)}…${addr.slice(-4)}`;
  }

  render() {
    const s = this._s;
    const onTargetChain = s.chainId === this.targetChainId;
    const chainLabel = this.chainName(s.chainId);

    return html`
      <div class="bar b-fade-in">
        <div class="brand">${this.brand}</div>
        <div class="right">
          ${s.connected && s.address ? html`
            <span class="chain" data-state=${onTargetChain ? "ok" : "warn"} title="chain ${s.chainId}">
              ${chainLabel}
              ${onTargetChain ? null : html`
                <b-button size="sm" variant="ghost" ?loading=${this._busy === "switch"} @click=${this._switch}>
                  Switch
                </b-button>`}
            </span>
            <span class="acct" title=${s.address}>
              <span class="dot"></span>
              <span class="addr">${this._shortAddr(s.address)}</span>
              ${s.primaryName ? html`
                <span class="sep">·</span>
                <span class="primary">${s.primaryName}</span>` : null}
              <button class="ico-btn"
                      aria-label="Disconnect"
                      ?disabled=${this._busy === "disconnect"}
                      @click=${this._disconnect}>${unsafeHTML(icon.cross)}</button>
            </span>
          ` : html`
            <b-button
              variant="primary"
              size="sm"
              ?loading=${this._busy === "connect"}
              ?disabled=${!s.walletAvailable || this._busy === "connect"}
              @click=${this._connect}
            >Connect wallet</b-button>
          `}
        </div>
      </div>

      ${!s.walletAvailable ? html`
        <div class="banner">
          No injected wallet detected. Install
          <a href="https://metamask.io" target="_blank" rel="noopener">MetaMask</a>
          or <a href="https://rabby.io" target="_blank" rel="noopener">Rabby</a>
          to mint, renew, transfer, or sign in. The rest of this page works in
          read-only preview.
        </div>` : null}

      ${this._err ? html`<div class="banner err">${this._err}</div>` : null}
    `;
  }
}
