// SPDX-License-Identifier: Apache-2.0
//
// <b-contract-name-status> — Phase E. Operator inspector that audits the
// four bankoneth registrar contracts' primary-name configuration via
// `verifyContractName()` from @bankoneth/core and renders a status table
// with green/amber/red dots per the audit doc's traffic-light scheme.
//
// Read-only: uses the publicClient; no wallet needed. Mounted on
// packages/tauri-app/admin.html.

import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { Address, PublicClient } from "viem";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";
import { verifyContractName, type ContractNameStatus } from "@bankoneth/core";

export interface ContractRow {
  address: Address;
  expectedName: string;
  /** Optional friendly label. Defaults to `expectedName`. */
  label?: string;
}

type RowState = {
  row: ContractRow;
  status: ContractNameStatus | null;
  loading: boolean;
  expanded: boolean;
  error: string;
};

@customElement("b-contract-name-status")
export class BankonethContractNameStatus extends LitElement {
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

      .row {
        display: grid;
        grid-template-columns: 1fr auto auto auto;
        align-items: center;
        gap: var(--b-space-3);
        padding: var(--b-space-3);
        background: var(--b-color-bg-2);
        border-radius: var(--b-radius-md);
        margin-bottom: var(--b-space-2);
        cursor: pointer;
        transition: border var(--b-motion-fast) var(--b-ease-standard);
        border: 1px solid transparent;
      }
      .row:hover { border-color: var(--b-color-border); }

      .label {
        font-family: var(--b-font-mono);
        font-size: var(--b-text-sm);
        color: var(--b-color-text-primary);
      }

      .pill {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 4px 10px;
        border-radius: var(--b-radius-full);
        font-size: 11px;
        font-family: var(--b-font-mono);
        font-weight: var(--b-weight-semibold);
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }
      .pill[data-state="ok"] {
        background: var(--b-color-success-faded);
        color: var(--b-color-success);
        border: 1px solid color-mix(in srgb, var(--b-color-success) 30%, transparent);
      }
      .pill[data-state="warn"] {
        background: color-mix(in srgb, var(--b-color-danger-faded) 30%, var(--b-color-bg-3));
        color: var(--b-color-danger);
        border: 1px solid color-mix(in srgb, var(--b-color-danger) 30%, transparent);
      }
      .pill[data-state="fail"] {
        background: var(--b-color-danger-faded);
        color: var(--b-color-danger);
        border: 1px solid color-mix(in srgb, var(--b-color-danger) 50%, transparent);
      }
      .pill[data-state="loading"] {
        background: var(--b-color-bg-3);
        color: var(--b-color-text-muted);
        border: 1px solid var(--b-color-border);
      }

      .detail {
        padding: var(--b-space-3) var(--b-space-4);
        background: var(--b-color-bg-3);
        border-radius: var(--b-radius-sm);
        font-family: var(--b-font-mono);
        font-size: var(--b-text-xs);
        color: var(--b-color-text-muted);
        margin: 0 0 var(--b-space-3) 0;
        line-height: 1.6;
      }
      .detail strong { color: var(--b-color-text-primary); }
      .detail .gap   { color: var(--b-color-danger); }

      .empty {
        padding: var(--b-space-5);
        text-align: center;
        color: var(--b-color-text-muted);
        font-size: var(--b-text-sm);
      }
    `,
  ];

  @property({ attribute: false }) client?: PublicClient;

  /** Rows to audit. Empty → "no contracts configured" message. */
  @property({ attribute: false }) contracts: ContractRow[] = [];

  /** Override the forward resolver address. Defaults to the client's chain canonical. */
  @property() forwardResolver?: Address;

  /** Override the ENS Registry address. Defaults to the client's chain canonical. */
  @property() registry?: Address;

  @state() private _rows: RowState[] = [];

  willUpdate(c: Map<string, unknown>) {
    if (c.has("contracts") || c.has("client")) {
      this._rows = this.contracts.map(r => ({
        row: r, status: null, loading: false, expanded: false, error: "",
      }));
      if (this.client) void this._auditAll();
    }
  }

  private async _auditAll() {
    if (!this.client) return;
    const c = this.client;
    await Promise.all(this._rows.map(async (state, idx) => {
      this._rows[idx] = { ...state, loading: true, error: "" };
      this.requestUpdate();
      try {
        const status = await verifyContractName({
          client:           c,
          address:          state.row.address,
          expectedName:     state.row.expectedName,
          forwardResolver:  this.forwardResolver,
          registry:         this.registry,
        });
        this._rows[idx] = { ...this._rows[idx]!, status, loading: false };
      } catch (e: unknown) {
        const msg = (e as { message?: string } | undefined)?.message ?? "audit failed";
        this._rows[idx] = { ...this._rows[idx]!, loading: false, error: msg };
      }
      this.requestUpdate();
    }));
  }

  private _toggleRow(idx: number) {
    this._rows[idx]!.expanded = !this._rows[idx]!.expanded;
    this.requestUpdate();
  }

  private _refresh() {
    if (this.client) void this._auditAll();
  }

  render() {
    if (this._rows.length === 0) {
      return html`
        <div class="panel b-fade-in">
          <h3>Contract naming status</h3>
          <div class="empty">No contracts configured. Pass <code>contracts</code> prop.</div>
        </div>`;
    }
    return html`
      <div class="panel b-fade-in">
        <h3>Contract naming status
          <b-button size="sm" variant="ghost" @click=${this._refresh}>Refresh</b-button>
        </h3>
        ${this._rows.map((s, idx) => this._renderRow(s, idx))}
      </div>`;
  }

  private _renderRow(s: RowState, idx: number) {
    const label  = s.row.label ?? s.row.expectedName;
    const status = s.status;

    let reversePill = "loading", forwardPill = "loading", roundTripPill = "loading";
    let reverseText = "checking…", forwardText = "checking…", roundTripText = "checking…";

    if (s.error) {
      reversePill = forwardPill = roundTripPill = "fail";
      reverseText = forwardText = roundTripText = "error";
    } else if (status) {
      const reverseOk = status.reverseName === status.expectedName;
      const forwardOk = status.forwardAddr !== null
        && status.forwardAddr.toLowerCase() === s.row.address.toLowerCase();
      reversePill   = status.reverseName === null ? "fail" : reverseOk ? "ok" : "warn";
      forwardPill   = status.forwardAddr === null ? "fail" : forwardOk ? "ok" : "warn";
      roundTripPill = status.roundTrip ? "ok" : "fail";
      reverseText   = "reverse";
      forwardText   = "forward";
      roundTripText = status.roundTrip ? "roundtrip" : "broken";
    }

    return html`
      <div class="row" @click=${() => this._toggleRow(idx)}>
        <div class="label">${label}</div>
        <span class="pill" data-state=${reversePill}>${reverseText}</span>
        <span class="pill" data-state=${forwardPill}>${forwardText}</span>
        <span class="pill" data-state=${roundTripPill}>${roundTripText}</span>
      </div>
      ${s.expanded ? html`
        <div class="detail">
          ${s.error ? html`<span class="gap">${s.error}</span>` : status ? html`
            <div><strong>address:</strong>      ${s.row.address}</div>
            <div><strong>expected name:</strong> ${status.expectedName}</div>
            <div><strong>reverse name:</strong>  ${status.reverseName ?? "(none)"}</div>
            <div><strong>forward addr:</strong>  ${status.forwardAddr ?? "(none)"}</div>
            ${status.gaps.length > 0 ? html`
              <div><strong>gaps:</strong></div>
              ${status.gaps.map(g => html`<div class="gap">• ${g}</div>`)}
            ` : null}
          ` : html`<span>loading…</span>`}
        </div>` : null}
    `;
  }
}
