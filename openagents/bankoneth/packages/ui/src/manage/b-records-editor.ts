// SPDX-License-Identifier: Apache-2.0
//
// <b-records-editor> — edit any record post-mint via the resolver's
// multicall(bytes[]). Phase 3.1. Modal-driven multi-step pattern mirroring
// ens-app-v3's transaction-flow reducer.
//
// Surfaces three record buckets:
//   1. Identity     — avatar, description, url, email, com.twitter, com.github
//   2. Multichain   — ETH addr + Polygon/Base/Optimism/Arbitrum/Algorand
//   3. Agentic edge — mindx.endpoint, bonafide.attestation, agent.capabilities,
//                     inft.uri, agenticplace.listing, x402.endpoint, algoid.did
//
// Batched into a single resolver multicall to minimize tx count + gas.

import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { Hex } from "viem";
import { encodeFunctionData } from "viem";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";

interface ResolverClient {
  multicall(node: Hex, data: Hex[]): Promise<Hex>;
}

interface RecordSpec { key: string; label: string; placeholder?: string }

const IDENTITY: RecordSpec[] = [
  { key: "avatar",      label: "Avatar URL",     placeholder: "https://… or ipfs://…" },
  { key: "description", label: "Description" },
  { key: "url",         label: "Website" },
  { key: "email",       label: "Email" },
  { key: "com.twitter", label: "Twitter handle" },
  { key: "com.github",  label: "GitHub handle" },
];

const AGENTIC: RecordSpec[] = [
  { key: "mindx.endpoint",       label: "mindX endpoint",           placeholder: "https://mindx.pythai.net/agent/…" },
  { key: "bonafide.attestation", label: "BONAFIDE attestation hash" },
  { key: "agent.capabilities",   label: "Agent capabilities (JSON)" },
  { key: "inft.uri",             label: "ERC-7857 iNFT URI",        placeholder: "ipfs://…" },
  { key: "agenticplace.listing", label: "AgenticPlace listing ID" },
  { key: "x402.endpoint",        label: "x402 endpoint" },
  { key: "algoid.did",           label: "Algorand DID",             placeholder: "did:algo:…" },
];

const SET_TEXT_ABI = [{
  type: "function", name: "setText", stateMutability: "nonpayable",
  inputs: [
    { name: "node",  type: "bytes32" },
    { name: "key",   type: "string"  },
    { name: "value", type: "string"  },
  ],
  outputs: [],
}] as const;

@customElement("b-records-editor")
export class BankonethRecordsEditor extends LitElement {
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
      h3 {
        margin: 0 0 var(--b-space-3) 0;
        font-size: var(--b-text-md);
        font-weight: var(--b-weight-semibold);
        color: var(--b-color-text-primary);
      }
      .section + .section { margin-top: var(--b-space-5); }
      .grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: var(--b-space-3);
      }
      @media (max-width: 600px) { .grid { grid-template-columns: 1fr; } }
      label {
        display: block;
        font-size: var(--b-text-xs);
        color: var(--b-color-text-muted);
        margin-bottom: var(--b-space-1);
      }
      input {
        width: 100%;
        box-sizing: border-box;
        padding: var(--b-space-2) var(--b-space-3);
        font-family: var(--b-font-mono);
        font-size: var(--b-text-sm);
        background: var(--b-color-bg-2);
        border: 1px solid var(--b-color-border);
        border-radius: var(--b-radius-sm);
        color: var(--b-color-text-primary);
      }
      input:focus { outline: none; border-color: var(--b-color-accent); box-shadow: var(--b-shadow-focus); }
      .actions {
        margin-top: var(--b-space-5);
        display: flex; justify-content: flex-end; gap: var(--b-space-2);
      }
      .status {
        margin-top: var(--b-space-3);
        font-size: var(--b-text-xs);
        color: var(--b-color-text-muted);
      }
      .status[data-state="error"] { color: var(--b-color-danger); }
      .status[data-state="success"] { color: var(--b-color-success); }
    `,
  ];

  @property() node: Hex = "0x";
  /** Existing records — pre-populate the editor (typically from NameLookup.records). */
  @property({ type: Object }) records: Record<string, string> = {};
  /** Client that knows how to call resolver.multicall(node, calls). */
  @property({ attribute: false }) client?: ResolverClient;

  @state() private _draft: Record<string, string> = {};
  @state() private _state: "idle" | "loading" | "success" | "error" = "idle";
  @state() private _error = "";

  willUpdate(changed: Map<string, unknown>) {
    if (changed.has("records") && Object.keys(this._draft).length === 0) {
      this._draft = { ...this.records };
    }
  }

  private _bind(spec: RecordSpec) {
    return (e: Event) => {
      const v = (e.target as HTMLInputElement).value;
      this._draft = { ...this._draft, [spec.key]: v };
    };
  }

  private async _submit() {
    if (!this.client) {
      this._state = "error"; this._error = "no client wired"; return;
    }
    // Build a setText() call for every record where draft differs from prop.
    const calls: Hex[] = [];
    for (const k of Object.keys(this._draft)) {
      if (this._draft[k] !== this.records[k]) {
        const data = encodeFunctionData({
          abi: SET_TEXT_ABI,
          functionName: "setText",
          args: [this.node, k, this._draft[k] ?? ""],
        });
        calls.push(data);
      }
    }
    if (calls.length === 0) { this._state = "idle"; return; }

    this._state = "loading"; this._error = "";
    try {
      await this.client.multicall(this.node, calls);
      this._state = "success";
      this.dispatchEvent(new CustomEvent("records-saved", { detail: { count: calls.length } }));
    } catch (e: any) {
      this._state = "error"; this._error = e?.message ?? "save failed";
    }
  }

  private _renderGroup(name: string, specs: RecordSpec[]) {
    return html`
      <div class="section">
        <h3>${name}</h3>
        <div class="grid">
          ${specs.map(s => html`
            <div>
              <label>${s.label}</label>
              <input
                type="text"
                placeholder=${s.placeholder ?? ""}
                .value=${this._draft[s.key] ?? ""}
                @input=${this._bind(s)}
              />
            </div>
          `)}
        </div>
      </div>
    `;
  }

  render() {
    const dirty = Object.keys(this._draft).some(k => this._draft[k] !== this.records[k]);
    return html`
      <div class="panel b-fade-in">
        ${this._renderGroup("Identity",      IDENTITY)}
        ${this._renderGroup("Agentic edge",  AGENTIC)}
        <div class="actions">
          <b-button variant="ghost" @click=${() => { this._draft = { ...this.records }; this._state = "idle"; }}>Reset</b-button>
          <b-button
            ?loading=${this._state === "loading"}
            ?disabled=${!dirty || this._state === "loading"}
            @click=${this._submit}
          >Save records</b-button>
        </div>
        ${this._state === "idle" ? null : html`
          <div class="status" data-state=${this._state}>
            ${this._state === "loading" ? "Saving via multicall…" :
              this._state === "success" ? "Saved." :
              `Failed: ${this._error}`}
          </div>`}
      </div>
    `;
  }
}
