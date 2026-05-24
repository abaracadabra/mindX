// SPDX-License-Identifier: Apache-2.0
//
// <b-siwe-signin> — Phase 3.7. EIP-4361 sign-in via the connected wallet.
// Pluggable gate predicate: caller passes a `verify(bundle)` callback (or a
// REST endpoint) that ultimately invokes BankonAuthGate on-chain. This
// component is purely UI — the auth handshake lives in core/auth.ts.

import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { Address } from "viem";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";
import { signInWithBankoneth, type SiweBundle } from "@bankoneth/core";
import type { WalletClient } from "viem";

interface SiweClient {
  walletClient: WalletClient;
  address: Address;
  /** Optional explicit chainId override. Defaults to walletClient.chain.id. */
  chainId?: number;
  /** Submit the bundle to verify. Implementations may POST to a backend that
   *  calls BankonAuthGate.verify; this component is agnostic. */
  verify(bundle: SiweBundle): Promise<{ ok: boolean; message?: string }>;
}

@customElement("b-siwe-signin")
export class BankonethSiweSignin extends LitElement {
  static styles = [
    tokens,
    motion.fadeIn,
    css`
      :host { display: block; font-family: var(--b-font-sans); }
      .panel {
        background: var(--b-color-bg-1);
        border: 1px solid var(--b-color-border);
        border-radius: var(--b-radius-lg);
        padding: var(--b-space-5);
      }
      h3 { margin: 0 0 var(--b-space-3) 0; font-size: var(--b-text-md); }
      .statement {
        background: var(--b-color-bg-2);
        border-radius: var(--b-radius-md);
        padding: var(--b-space-3);
        font-size: var(--b-text-sm);
        color: var(--b-color-text-primary);
        margin-bottom: var(--b-space-4);
      }
      .actions { display: flex; justify-content: flex-end; }
      .status { margin-top: var(--b-space-3); font-size: var(--b-text-xs); color: var(--b-color-text-muted); }
      .status[data-state="error"]   { color: var(--b-color-danger); }
      .status[data-state="success"] { color: var(--b-color-success); }
    `,
  ];

  /** Why the user is signing in — shown verbatim above the metadata block. */
  @property() statement = "Sign in to verify your bankoneth identity.";
  /** Optional domain override; defaults to window.location.host. */
  @property() domain = "";
  /** Optional URI override; defaults to window.location.href. */
  @property() uri = "";
  /** Optional resources to request access to. */
  @property({ type: Array }) resources: string[] = [];
  /** Required — the SIWE submit + verify client. */
  @property({ attribute: false }) client?: SiweClient;

  @state() private _state: "idle" | "loading" | "success" | "error" = "idle";
  @state() private _error = "";
  @state() private _verifiedFor: Address | "" = "";

  private async _submit() {
    if (!this.client) { this._state = "error"; this._error = "no client wired"; return; }
    this._state = "loading"; this._error = "";
    try {
      const bundle = await signInWithBankoneth({
        walletClient:  this.client.walletClient,
        address:       this.client.address,
        chainId:       this.client.chainId,
        domain:        this.domain || undefined,
        uri:           this.uri    || undefined,
        statement:     this.statement,
        resources:     this.resources,
      });
      const res = await this.client.verify(bundle);
      if (res.ok) {
        this._state = "success";
        this._verifiedFor = this.client.address;
        this.dispatchEvent(new CustomEvent("signed-in", { detail: { bundle } }));
      } else {
        this._state = "error";
        this._error = res.message ?? "verification failed";
      }
    } catch (e: any) {
      this._state = "error"; this._error = e?.message ?? "sign-in failed";
    }
  }

  render() {
    return html`
      <div class="panel b-fade-in">
        <h3>Sign in with bankoneth</h3>
        <div class="statement">${this.statement}</div>
        <div class="actions">
          <b-button
            ?loading=${this._state === "loading"}
            ?disabled=${this._state === "loading"}
            @click=${this._submit}
          >${this._verifiedFor ? "Re-sign" : "Sign in"}</b-button>
        </div>
        ${this._state === "idle" ? null : html`
          <div class="status" data-state=${this._state}>
            ${this._state === "loading" ? "Awaiting signature…" :
              this._state === "success" ? `Signed in as ${this._verifiedFor.slice(0, 6)}…${this._verifiedFor.slice(-4)}` :
              `Failed: ${this._error}`}
          </div>`}
      </div>
    `;
  }
}
