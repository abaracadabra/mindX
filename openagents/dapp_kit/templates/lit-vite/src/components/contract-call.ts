// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved

import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { ConnectedAccount } from "@openagents/wallet";
import { chainById } from "@openagents/wallet/chains";
import { buildRegistry } from "../lib/contracts.js";

/**
 * Demo component that reads a contract method from the current chain's
 * deployment record. Real dApps replace this with their own UI.
 */
@customElement("openagents-contract-call")
export class ContractCall extends LitElement {
  static styles = css`
    :host {
      display: block;
    }
    label {
      display: block;
      margin: 12px 0 6px;
      color: var(--muted, #4a5060);
      font-size: 12px;
      letter-spacing: 0.5px;
      text-transform: uppercase;
    }
    input, select {
      width: 100%;
      padding: 8px 10px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: var(--fg, #e6edf3);
      border-radius: 4px;
      font-family: ui-monospace, monospace;
      font-size: 13px;
    }
    button {
      margin-top: 16px;
      background: var(--accent, #8be9fd);
      color: #0a0a0f;
      border: 0;
      padding: 10px 18px;
      border-radius: 4px;
      font-weight: 600;
      cursor: pointer;
    }
    pre {
      background: rgba(255, 255, 255, 0.03);
      padding: 12px;
      border-radius: 4px;
      overflow-x: auto;
      font-size: 12px;
      margin-top: 16px;
    }
    .error { color: #ff6b6b; margin-top: 12px; font-size: 13px; }
  `;

  @property({ attribute: false }) account!: ConnectedAccount;
  @state() contractName = "";
  @state() methodName = "";
  @state() argsJson = "[]";
  @state() result?: string;
  @state() error?: string;
  @state() running = false;

  private async onCall() {
    this.error = undefined;
    this.result = undefined;
    this.running = true;
    try {
      const networkKey = (chainById(this.account.chainId)?.name ?? "")
        .toLowerCase()
        .replace(/\s+/g, "-");
      const registry = await buildRegistry(networkKey, this.account);
      const handle = (registry as unknown as Record<string, unknown>)[this.contractName] as
        | { read: Record<string, (...args: unknown[]) => Promise<unknown>> }
        | undefined;
      if (!handle) throw new Error(`Contract '${this.contractName}' not in deployments/${networkKey}.json`);
      const args = JSON.parse(this.argsJson) as unknown[];
      const out = await handle.read[this.methodName](...args);
      this.result = JSON.stringify(out, replacer, 2);
    } catch (err) {
      this.error = err instanceof Error ? err.message : String(err);
    } finally {
      this.running = false;
    }
  }

  override render() {
    return html`
      <label>Contract name</label>
      <input
        .value=${this.contractName}
        @input=${(e: Event) => (this.contractName = (e.target as HTMLInputElement).value)}
        placeholder="e.g. AgentRegistry"
      />
      <label>Method</label>
      <input
        .value=${this.methodName}
        @input=${(e: Event) => (this.methodName = (e.target as HTMLInputElement).value)}
        placeholder="e.g. totalSupply"
      />
      <label>Arguments (JSON array)</label>
      <input
        .value=${this.argsJson}
        @input=${(e: Event) => (this.argsJson = (e.target as HTMLInputElement).value)}
      />
      <button ?disabled=${this.running} @click=${this.onCall}>
        ${this.running ? "Reading…" : "Read contract"}
      </button>
      ${this.error ? html`<div class="error">${this.error}</div>` : html``}
      ${this.result ? html`<pre>${this.result}</pre>` : html``}
    `;
  }
}

function replacer(_key: string, value: unknown): unknown {
  if (typeof value === "bigint") return value.toString() + "n";
  return value;
}
