// SPDX-License-Identifier: Apache-2.0
//
// <b-renewal> — Phase 3.2. Extend a name's expiry. Two modes:
//   - mode="subname" : calls BankonSubnameRegistrar.renew(node, secs)
//   - mode="eth2ld"  : calls ETHRegistrarController.renew(name, secs)
//
// Shows USD quote + duration slider (1 / 3 / 5 / 10 years).

import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { Address, Hex } from "viem";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";
import { formatExpiry } from "@bankoneth/core";
import { requestConnect } from "./_disconnected";

export type RenewalMode = "subname" | "eth2ld";

interface RenewalClient {
  /** subname mode — calls our registrar.renew(node, additionalSeconds). */
  renewSubname?(node: Hex, additionalSeconds: bigint): Promise<Hex>;
  /** .eth 2LD mode — calls ETHRegistrarController.renew(name, secs). */
  renewEth2ld?(label: string, durationSeconds: bigint): Promise<Hex>;
  /** USD-6 quote for the current label + duration. */
  quoteUsd?(label: string, durationYears: number): Promise<bigint>;
}

const YEAR = 365 * 86_400;
const STEPS = [1, 3, 5, 10] as const;

@customElement("b-renewal")
export class BankonethRenewal extends LitElement {
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
      .row { display: flex; gap: var(--b-space-2); margin-bottom: var(--b-space-4); }
      .step {
        flex: 1; padding: var(--b-space-3); text-align: center;
        background: var(--b-color-bg-2); border: 1px solid var(--b-color-border);
        border-radius: var(--b-radius-md); cursor: pointer; user-select: none;
        font-size: var(--b-text-sm); color: var(--b-color-text-primary);
        transition: all var(--b-motion-fast) var(--b-ease-standard);
      }
      .step[aria-selected="true"] {
        background: var(--b-color-accent-faded);
        border-color: var(--b-color-accent);
        color: var(--b-color-accent);
        font-weight: var(--b-weight-semibold);
      }
      .meta {
        display: flex; justify-content: space-between;
        font-size: var(--b-text-sm); color: var(--b-color-text-muted);
        margin-bottom: var(--b-space-3);
      }
      .meta strong { color: var(--b-color-text-primary); }
      .actions { display: flex; justify-content: flex-end; }
      .status { margin-top: var(--b-space-3); font-size: var(--b-text-xs); color: var(--b-color-text-muted); }
      .status[data-state="error"]   { color: var(--b-color-danger); }
      .status[data-state="success"] { color: var(--b-color-success); }
    `,
  ];

  @property() mode: RenewalMode = "subname";
  /** For mode=subname, the name's bytes32 node. */
  @property() node: Hex = "0x";
  /** Display name + label for the quote and for eth2ld mode. */
  @property() name = "";
  @property() label = "";
  /** Current expiry, unix-seconds. */
  @property({ type: Number }) currentExpiry = 0;
  @property({ attribute: false }) client?: RenewalClient;

  @state() private _years = 1;
  @state() private _quote = 0n;
  @state() private _state: "idle" | "loading" | "success" | "error" = "idle";
  @state() private _error = "";
  @state() private _txHash: Hex | "" = "";

  protected async firstUpdated() { void this._refreshQuote(); }
  protected async updated(c: Map<string, unknown>) {
    if (c.has("_years") || c.has("label") || c.has("client")) void this._refreshQuote();
  }

  private async _refreshQuote() {
    if (!this.client?.quoteUsd || !this.label) return;
    try { this._quote = await this.client.quoteUsd(this.label, this._years); }
    catch { /* leave stale; renewal proceeds anyway */ }
  }

  private async _submit() {
    if (!this.client) { this._state = "error"; this._error = "no client wired"; return; }
    this._state = "loading"; this._error = "";
    try {
      const secs = BigInt(this._years * YEAR);
      const hash = this.mode === "subname"
        ? await this.client.renewSubname!(this.node, secs)
        : await this.client.renewEth2ld!(this.label, secs);
      this._txHash = hash; this._state = "success";
      this.dispatchEvent(new CustomEvent("renewed", { detail: { years: this._years, txHash: hash } }));
    } catch (e: any) {
      this._state = "error"; this._error = e?.message ?? "renewal failed";
    }
  }

  render() {
    const newExpiry = this.currentExpiry === 0
      ? Math.floor(Date.now() / 1000) + this._years * YEAR
      : this.currentExpiry + this._years * YEAR;
    return html`
      <div class="panel b-fade-in">
        <div class="meta">
          <span>Current expiry: <strong>${formatExpiry(this.currentExpiry)}</strong></span>
          <span>New expiry: <strong>${formatExpiry(newExpiry)}</strong></span>
        </div>
        <div class="row" role="radiogroup" aria-label="Renewal duration">
          ${STEPS.map(y => html`
            <button
              class="step"
              role="radio"
              aria-selected=${this._years === y ? "true" : "false"}
              @click=${() => { this._years = y; }}
            >${y} ${y === 1 ? "year" : "years"}</button>
          `)}
        </div>
        <div class="meta">
          <span>Cost</span>
          <span><strong>$${(Number(this._quote) / 1_000_000).toFixed(2)}</strong></span>
        </div>
        <div class="actions">
          ${this.client ? html`
            <b-button
              ?loading=${this._state === "loading"}
              ?disabled=${this._state === "loading"}
              @click=${this._submit}
            >Renew ${this._years} ${this._years === 1 ? "year" : "years"}</b-button>` : html`
            <b-button variant="secondary" @click=${() => requestConnect(this)}>
              Connect to renew
            </b-button>`}
        </div>
        ${this._state === "idle" ? null : html`
          <div class="status" data-state=${this._state}>
            ${this._state === "loading" ? "Submitting…" :
              this._state === "success" ? `Renewed. tx: ${this._txHash.slice(0, 10)}…` :
              `Failed: ${this._error}`}
          </div>`}
      </div>
    `;
  }
}
