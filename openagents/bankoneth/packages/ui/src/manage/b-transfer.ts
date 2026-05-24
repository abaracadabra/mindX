// SPDX-License-Identifier: Apache-2.0
//
// <b-transfer> — Phase 3.3. Ownership transfer via NameWrapper
// safeTransferFrom. Resolves the destination via Universal Resolver if it
// looks like an ENS name. Warns when CANNOT_TRANSFER is burned.

import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { Address, Hex } from "viem";
import { isAddress } from "viem";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";
import { hasFuse, type FuseName } from "@bankoneth/core";
import { requestConnect } from "./_disconnected";

interface TransferClient {
  /** Resolve an ENS name to an address via UR. Returns 0x… or null. */
  resolveAddr(name: string): Promise<Address | null>;
  /** NameWrapper.safeTransferFrom(from, to, tokenId, 1, ""). */
  transfer(node: Hex, from: Address, to: Address): Promise<Hex>;
}

@customElement("b-transfer")
export class BankonethTransfer extends LitElement {
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
      label { display: block; font-size: var(--b-text-xs); color: var(--b-color-text-muted); margin-bottom: var(--b-space-1); }
      input {
        width: 100%; box-sizing: border-box;
        padding: var(--b-space-3);
        font-family: var(--b-font-mono);
        font-size: var(--b-text-sm);
        background: var(--b-color-bg-2);
        border: 1px solid var(--b-color-border);
        border-radius: var(--b-radius-sm);
        color: var(--b-color-text-primary);
      }
      input:focus { outline: none; border-color: var(--b-color-accent); box-shadow: var(--b-shadow-focus); }
      .resolved {
        margin-top: var(--b-space-2);
        font-family: var(--b-font-mono);
        font-size: var(--b-text-xs);
        color: var(--b-color-success);
      }
      .warn {
        background: var(--b-color-danger-faded);
        color: var(--b-color-danger);
        padding: var(--b-space-3);
        border-radius: var(--b-radius-md);
        font-size: var(--b-text-sm);
        margin-bottom: var(--b-space-4);
      }
      .actions { display: flex; justify-content: flex-end; margin-top: var(--b-space-4); }
      .status { margin-top: var(--b-space-3); font-size: var(--b-text-xs); color: var(--b-color-text-muted); }
      .status[data-state="error"]   { color: var(--b-color-danger); }
      .status[data-state="success"] { color: var(--b-color-success); }
    `,
  ];

  @property() node: Hex = "0x";
  @property() currentOwner: Address = "0x0000000000000000000000000000000000000000";
  @property({ type: Number }) fuses = 0;
  @property({ attribute: false }) client?: TransferClient;

  @state() private _input = "";
  @state() private _resolved: Address | null = null;
  @state() private _state: "idle" | "resolving" | "loading" | "success" | "error" = "idle";
  @state() private _error = "";
  @state() private _txHash: Hex | "" = "";

  private _onInput(e: Event) {
    this._input = (e.target as HTMLInputElement).value.trim();
    this._resolved = null;
    if (!this._input) return;
    if (isAddress(this._input)) { this._resolved = this._input as Address; return; }
    if (this._input.endsWith(".eth") && this.client) {
      this._state = "resolving";
      this.client.resolveAddr(this._input)
        .then(a => { this._resolved = a; this._state = "idle"; })
        .catch(() => { this._resolved = null; this._state = "idle"; });
    }
  }

  private async _submit() {
    if (!this.client || !this._resolved) {
      this._state = "error"; this._error = "no destination resolved"; return;
    }
    this._state = "loading"; this._error = "";
    try {
      const hash = await this.client.transfer(this.node, this.currentOwner, this._resolved);
      this._txHash = hash; this._state = "success";
      this.dispatchEvent(new CustomEvent("transferred", {
        detail: { to: this._resolved, txHash: hash },
      }));
    } catch (e: any) {
      this._state = "error"; this._error = e?.message ?? "transfer failed";
    }
  }

  render() {
    const cannotTransfer = hasFuse({ fuses: this.fuses }, "CANNOT_TRANSFER");
    return html`
      <div class="panel b-fade-in">
        ${cannotTransfer ? html`
          <div class="warn">
            <strong>CANNOT_TRANSFER fuse burned.</strong>
            This name is non-transferable. The transaction will revert.
          </div>` : null}

        <label>Send to address or ENS name</label>
        <input
          type="text"
          placeholder="vitalik.eth or 0x..."
          .value=${this._input}
          @input=${this._onInput}
          ?disabled=${cannotTransfer}
        />
        ${this._resolved ? html`<div class="resolved">→ ${this._resolved}</div>` : null}

        <div class="actions">
          ${this.client ? html`
            <b-button
              variant="danger"
              ?loading=${this._state === "loading"}
              ?disabled=${cannotTransfer || !this._resolved || this._state === "loading"}
              @click=${this._submit}
            >Transfer name</b-button>` : html`
            <b-button variant="secondary"
                      ?disabled=${cannotTransfer}
                      @click=${() => requestConnect(this)}>
              Connect to transfer
            </b-button>`}
        </div>
        ${this._state === "idle" || this._state === "resolving" ? null : html`
          <div class="status" data-state=${this._state}>
            ${this._state === "loading" ? "Submitting…" :
              this._state === "success" ? `Transferred. tx: ${this._txHash.slice(0, 10)}…` :
              `Failed: ${this._error}`}
          </div>`}
      </div>
    `;
  }
}
