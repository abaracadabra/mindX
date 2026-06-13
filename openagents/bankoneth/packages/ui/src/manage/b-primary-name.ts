// SPDX-License-Identifier: Apache-2.0
//
// <b-primary-name> — Phase 3.4. Set the connected wallet's ENS primary
// (reverse) name via ReverseRegistrar.setName. Reads the current primary
// via UR.reverse(addr, 60).

import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { Hex } from "viem";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";
import { requestConnect } from "./_disconnected";

interface PrimaryNameClient {
  /** UR.reverse(addr, 60) → primary name or null. */
  reverseAddr(): Promise<string | null>;
  /** ReverseRegistrar.setName(name). */
  setPrimaryName(name: string): Promise<Hex>;
}

@customElement("b-primary-name")
export class BankonethPrimaryName extends LitElement {
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
      .current {
        display: flex; align-items: center; justify-content: space-between;
        padding: var(--b-space-3);
        background: var(--b-color-bg-2);
        border-radius: var(--b-radius-md);
        font-size: var(--b-text-sm); color: var(--b-color-text-primary);
        margin-bottom: var(--b-space-4);
      }
      .current code { font-family: var(--b-font-mono); }
      .muted { color: var(--b-color-text-muted); }
      .actions { display: flex; justify-content: flex-end; }
      .status { margin-top: var(--b-space-3); font-size: var(--b-text-xs); color: var(--b-color-text-muted); }
      .status[data-state="error"]   { color: var(--b-color-danger); }
      .status[data-state="success"] { color: var(--b-color-success); }
    `,
  ];

  /** The name this panel proposes to set as primary. */
  @property() name = "";
  @property({ attribute: false }) client?: PrimaryNameClient;

  @state() private _current: string | null = null;
  @state() private _state: "idle" | "loading" | "success" | "error" = "idle";
  @state() private _error = "";
  @state() private _txHash: Hex | "" = "";

  protected async firstUpdated() { void this._refresh(); }

  private async _refresh() {
    if (!this.client) return;
    try { this._current = await this.client.reverseAddr(); } catch { /* swallow */ }
  }

  private async _submit() {
    if (!this.client || !this.name) {
      this._state = "error"; this._error = "no name to set"; return;
    }
    this._state = "loading"; this._error = "";
    try {
      const hash = await this.client.setPrimaryName(this.name);
      this._txHash = hash; this._state = "success"; this._current = this.name;
      this.dispatchEvent(new CustomEvent("primary-set", { detail: { name: this.name, txHash: hash } }));
    } catch (e: any) {
      this._state = "error"; this._error = e?.message ?? "set primary failed";
    }
  }

  render() {
    const isCurrent = this._current === this.name;
    return html`
      <div class="panel b-fade-in">
        <div class="current">
          <span class="muted">Current primary:</span>
          <code>${this._current ?? "none"}</code>
        </div>
        <div class="actions">
          ${this.client ? html`
            <b-button
              ?loading=${this._state === "loading"}
              ?disabled=${isCurrent || this._state === "loading"}
              @click=${this._submit}
            >${isCurrent ? "Already primary" : `Use ${this.name} as primary`}</b-button>` : html`
            <b-button variant="secondary" @click=${() => requestConnect(this)}>
              Connect to set primary
            </b-button>`}
        </div>
        ${this._state === "idle" ? null : html`
          <div class="status" data-state=${this._state}>
            ${this._state === "loading" ? "Submitting…" :
              this._state === "success" ? `Set. tx: ${this._txHash.slice(0, 10)}…` :
              `Failed: ${this._error}`}
          </div>`}
      </div>
    `;
  }
}
