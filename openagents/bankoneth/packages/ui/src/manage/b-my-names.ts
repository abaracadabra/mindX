// SPDX-License-Identifier: Apache-2.0
//
// <b-my-names> — Phase 3.5. Inventory dashboard. Reads via
// @bankoneth/core inventory.getNamesForAddress. Filterable, sortable.

import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { Address } from "viem";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";
import { type OwnedName, formatExpiry, hasFuse } from "@bankoneth/core";

interface InventoryClient {
  getOwnedNames(address: Address): Promise<OwnedName[]>;
}

type Filter = "all" | "expiring" | "wrapped" | "soulbound";

@customElement("b-my-names")
export class BankonethMyNames extends LitElement {
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
      .filters {
        display: flex; gap: var(--b-space-2); margin-bottom: var(--b-space-4);
        flex-wrap: wrap;
      }
      .pill {
        padding: var(--b-space-1) var(--b-space-3);
        background: var(--b-color-bg-2);
        border: 1px solid var(--b-color-border);
        border-radius: var(--b-radius-full);
        font-size: var(--b-text-xs);
        cursor: pointer;
        color: var(--b-color-text-primary);
      }
      .pill[aria-selected="true"] {
        background: var(--b-color-accent-faded);
        border-color: var(--b-color-accent);
        color: var(--b-color-accent);
        font-weight: var(--b-weight-semibold);
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: var(--b-space-3);
      }
      .card {
        background: var(--b-color-bg-2);
        border: 1px solid var(--b-color-border);
        border-radius: var(--b-radius-md);
        padding: var(--b-space-4);
        cursor: pointer;
        transition: border var(--b-motion-fast) var(--b-ease-standard);
      }
      .card:hover { border-color: var(--b-color-accent); }
      .name {
        font-family: var(--b-font-mono);
        font-size: var(--b-text-sm);
        color: var(--b-color-text-primary);
        margin-bottom: var(--b-space-2);
        word-break: break-all;
      }
      .meta {
        display: flex; justify-content: space-between;
        font-size: var(--b-text-xs);
        color: var(--b-color-text-muted);
      }
      .empty {
        padding: var(--b-space-5);
        text-align: center;
        color: var(--b-color-text-muted);
        font-size: var(--b-text-sm);
      }
    `,
  ];

  @property() address: Address = "0x0000000000000000000000000000000000000000";
  @property({ attribute: false }) client?: InventoryClient;

  @state() private _names: OwnedName[] = [];
  @state() private _filter: Filter = "all";
  @state() private _loading = false;

  protected async firstUpdated() { void this._load(); }
  protected async updated(c: Map<string, unknown>) {
    if (c.has("address") || c.has("client")) void this._load();
  }

  private async _load() {
    if (!this.client) return;
    this._loading = true;
    try { this._names = await this.client.getOwnedNames(this.address); }
    catch { this._names = []; }
    finally { this._loading = false; }
  }

  private _filtered(): OwnedName[] {
    const now = Math.floor(Date.now() / 1000);
    switch (this._filter) {
      case "expiring":
        return this._names.filter(n => n.expiry > 0 && n.expiry - now < 30 * 86400);
      case "wrapped":
        return this._names.filter(n => n.wrapped);
      case "soulbound": {
        const mask = 0x50005; // PARENT_CANNOT_CONTROL | CANNOT_UNWRAP | CANNOT_TRANSFER | CAN_EXTEND_EXPIRY
        return this._names.filter(n => (n.fuses & mask) === mask);
      }
      default:
        return this._names;
    }
  }

  private _onCardClick(n: OwnedName) {
    this.dispatchEvent(new CustomEvent("name-selected", { detail: n }));
  }

  render() {
    const list = this._filtered();
    const filters: Array<[Filter, string]> = [
      ["all",       `All (${this._names.length})`],
      ["expiring",  "Expiring"],
      ["wrapped",   "Wrapped"],
      ["soulbound", "Soulbound"],
    ];
    return html`
      <div class="panel b-fade-in">
        <h3>My Names</h3>
        <div class="filters">
          ${filters.map(([f, label]) => html`
            <button
              class="pill"
              aria-selected=${this._filter === f ? "true" : "false"}
              @click=${() => { this._filter = f; }}
            >${label}</button>
          `)}
        </div>
        ${this._loading
          ? html`<div class="empty">Loading…</div>`
          : list.length === 0
            ? html`<div class="empty">No names match this filter.</div>`
            : html`
              <div class="grid">
                ${list.map(n => html`
                  <div class="card" @click=${() => this._onCardClick(n)}>
                    <div class="name">${n.name}</div>
                    <div class="meta">
                      <span>${formatExpiry(n.expiry)}</span>
                      <span>${n.wrapped ? "wrapped" : "legacy"}</span>
                    </div>
                  </div>`)}
              </div>`}
      </div>
    `;
  }
}
