// SPDX-License-Identifier: Apache-2.0
//
// <b-permissions-panel> — Phase 3.6. Surface NameWrapper fuses as
// toggleable burn options. Each toggle ONE-WAY only — already-burned fuses
// are disabled. Confirms each burn as IRREVERSIBLE per ens-app-v3 UX.

import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { Hex } from "viem";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";
import { FUSE, hasFuse, type FuseName } from "@bankoneth/core";
import { requestConnect } from "./_disconnected";

interface FuseClient {
  /** NameWrapper.setFuses(node, fuseMask). */
  setFuses(node: Hex, fuseMask: number): Promise<Hex>;
}

interface FuseSpec {
  name: FuseName;
  label: string;
  description: string;
  /** Whether this fuse can be burned by the owner (true) or only by the parent (false). */
  ownerControllable: boolean;
}

const SPECS: FuseSpec[] = [
  { name: "CANNOT_UNWRAP",           label: "Cannot unwrap",            description: "Locks the wrapped NFT — no unwrap allowed.", ownerControllable: true  },
  { name: "CANNOT_BURN_FUSES",       label: "Cannot burn fuses",        description: "Prevents burning further fuses.",            ownerControllable: true  },
  { name: "CANNOT_TRANSFER",         label: "Cannot transfer",          description: "Soulbound — no transfers.",                  ownerControllable: true  },
  { name: "CANNOT_SET_RESOLVER",     label: "Cannot set resolver",      description: "Locks the resolver address.",                ownerControllable: true  },
  { name: "CANNOT_SET_TTL",          label: "Cannot set TTL",           description: "Locks the TTL.",                             ownerControllable: true  },
  { name: "CANNOT_CREATE_SUBDOMAIN", label: "Cannot create subdomain",  description: "Locks subname issuance under this name.",    ownerControllable: true  },
  { name: "CANNOT_APPROVE",          label: "Cannot approve",           description: "Prevents approvals.",                        ownerControllable: true  },
  { name: "PARENT_CANNOT_CONTROL",   label: "Parent cannot control",    description: "Parent loses authority (set by parent only)", ownerControllable: false },
];

@customElement("b-permissions-panel")
export class BankonethPermissionsPanel extends LitElement {
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
        display: flex; align-items: center; justify-content: space-between;
        padding: var(--b-space-3);
        background: var(--b-color-bg-2);
        border-radius: var(--b-radius-md);
        margin-bottom: var(--b-space-2);
      }
      .info { flex: 1; }
      .name { font-size: var(--b-text-sm); color: var(--b-color-text-primary); font-weight: var(--b-weight-semibold); }
      .desc { font-size: var(--b-text-xs); color: var(--b-color-text-muted); margin-top: 2px; }
      .row[data-state="burned"] {
        background: var(--b-color-success-faded);
        opacity: 0.7;
      }
      .row[data-state="burned"] .name { color: var(--b-color-success); }
      .badge {
        font-family: var(--b-font-mono);
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        padding: 2px 6px;
        border-radius: var(--b-radius-sm);
      }
      .badge[data-state="burned"] {
        color: var(--b-color-success);
        background: var(--b-color-success-faded);
      }
      .warn {
        background: var(--b-color-danger-faded);
        color: var(--b-color-danger);
        padding: var(--b-space-3);
        border-radius: var(--b-radius-md);
        font-size: var(--b-text-xs);
        margin-top: var(--b-space-3);
      }
      .status { margin-top: var(--b-space-3); font-size: var(--b-text-xs); color: var(--b-color-text-muted); }
      .status[data-state="error"]   { color: var(--b-color-danger); }
      .status[data-state="success"] { color: var(--b-color-success); }
    `,
  ];

  @property() node: Hex = "0x";
  @property({ type: Number }) fuses = 0;
  @property({ attribute: false }) client?: FuseClient;

  @state() private _selecting: FuseName | "" = "";
  @state() private _state: "idle" | "loading" | "success" | "error" = "idle";
  @state() private _error = "";

  private async _burn(name: FuseName) {
    if (!this.client) { this._state = "error"; this._error = "no client wired"; return; }
    if (!confirm(`IRREVERSIBLE — burn ${name}?\nThis fuse cannot be un-burned. Confirm?`)) return;

    this._selecting = name;
    this._state = "loading"; this._error = "";
    try {
      const mask = FUSE[name];
      await this.client.setFuses(this.node, mask);
      this._state = "success";
      this.fuses |= mask;
      this.dispatchEvent(new CustomEvent("fuse-burned", { detail: { fuse: name } }));
    } catch (e: any) {
      this._state = "error"; this._error = e?.message ?? "burn failed";
    } finally {
      this._selecting = "";
    }
  }

  render() {
    return html`
      <div class="panel b-fade-in">
        <h3>Permissions</h3>
        ${SPECS.map(s => {
          const burned = hasFuse({ fuses: this.fuses }, s.name);
          return html`
            <div class="row" data-state=${burned ? "burned" : "active"}>
              <div class="info">
                <div class="name">${s.label}</div>
                <div class="desc">${s.description}</div>
              </div>
              ${burned
                ? html`<span class="badge" data-state="burned">burned</span>`
                : this.client ? html`
                    <b-button
                      size="sm"
                      variant="danger"
                      ?disabled=${!s.ownerControllable || this._state === "loading"}
                      ?loading=${this._selecting === s.name}
                      @click=${() => this._burn(s.name)}
                    >Burn</b-button>` : html`
                    <b-button size="sm" variant="secondary"
                              ?disabled=${!s.ownerControllable}
                              @click=${() => requestConnect(this)}>
                      Connect
                    </b-button>`}
            </div>`;
        })}
        <div class="warn">
          Every burn is permanent. Once burned, a fuse cannot be restored. Review
          the ENS docs at <code>docs.ens.domains/wrapper/expiry</code> before acting.
        </div>
        ${this._state === "idle" ? null : html`
          <div class="status" data-state=${this._state}>
            ${this._state === "loading" ? "Submitting burn…" :
              this._state === "success" ? "Burned." :
              `Failed: ${this._error}`}
          </div>`}
      </div>
    `;
  }
}
