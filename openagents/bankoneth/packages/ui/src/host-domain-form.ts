// SPDX-License-Identifier: Apache-2.0
//
// <bankoneth-host> — Flow C, the dual-mode carousel.
//
// A top-level mode toggle picks between:
//   - "enroll"  — register your .eth as a hosted parent (1-step form + sign)
//   - "issue"   — buy a subname under a hosted parent (3-step search → review → sign carousel)
//
// Wraps BankonethClient and emits `bankoneth-host:enroll` (for the parent to
// drive the contract write itself, since BankonethClient doesn't yet expose
// an enroll() method) and uses client.issueUnderHosted() for the issue path.

import { LitElement, html, css } from "lit";
import { customElement, property, query, state } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";
import { type Address, type Hex, namehash } from "viem";

import { BankonethClient } from "@bankoneth/core";

import { tokens } from "./tokens/tokens";
import { motion } from "./tokens/motion";
import { icon } from "./tokens/icons";

import "./primitives/b-stepper";
import "./primitives/b-button";
import "./primitives/b-input";
import "./primitives/b-card";
import "./primitives/b-rail-switcher";

import { BStepper } from "./primitives/b-stepper";
import type { Rail } from "./primitives/b-rail-switcher";

type Mode = "enroll" | "issue";

@customElement("bankoneth-host")
export class BankonethHost extends LitElement {
  static styles = [
    tokens,
    motion.fadeIn,
    motion.pop,
    css`
      :host { display: block; font-family: var(--b-font-sans); color: var(--b-color-text-primary); }
      .stack   { display: grid; gap: var(--b-space-5); }
      .actions { display: flex; gap: var(--b-space-3); justify-content: space-between; margin-top: var(--b-space-6); }
      .muted   { color: var(--b-color-text-muted); font-size: var(--b-text-sm); }
      .center  { text-align: center; }
      .success-ico {
        display: inline-flex; line-height: 0;
        color: var(--b-color-success); font-size: 3rem;
        animation: b-pop var(--b-motion-slow) var(--b-ease-spring);
      }
      .modes {
        display: grid; grid-template-columns: 1fr 1fr; gap: var(--b-space-2);
        padding: var(--b-space-1);
        background: var(--b-color-bg-3);
        border-radius: var(--b-radius-lg);
        margin-bottom: var(--b-space-5);
      }
      .modes button {
        all: unset; cursor: pointer; text-align: center;
        padding: var(--b-space-3);
        color: var(--b-color-text-secondary);
        font-weight: var(--b-weight-medium);
        font-size: var(--b-text-sm);
        border-radius: var(--b-radius-md);
        transition: background var(--b-motion-fast), color var(--b-motion-fast);
      }
      .modes button[aria-selected="true"] {
        background: var(--b-color-bg-1);
        color: var(--b-color-text-primary);
        box-shadow: var(--b-shadow-sm);
      }
      .modes button:focus-visible { outline: none; box-shadow: var(--b-shadow-focus); }
      .tx { font-family: var(--b-font-mono); font-size: var(--b-text-xs); color: var(--b-color-text-secondary); }
    `,
  ];

  @property({ attribute: false }) client!: BankonethClient;
  @property() explorerTxBase = "https://etherscan.io/tx/";

  @state() private _mode: Mode = "issue";
  // enroll mode state
  @state() private _enrollParent = "";
  @state() private _enrollPriceUsd = 5;
  @state() private _enrollOwnerSharePct = 50;
  // issue mode state
  @state() private _issueParent = "";
  @state() private _issueLabel = "";
  @state() private _issueRail: Rail = "eth";
  @state() private _issueSubmitting = false;
  @state() private _issueTxHash: Hex | null = null;
  @state() private _error = "";

  @query("b-stepper") private _stepper?: BStepper;

  private _setMode(m: Mode) { this._mode = m; this._error = ""; }

  // ── Enroll path ──────────────────────────────────────────────────
  private _enrollSubmit(e: Event) {
    e.preventDefault();
    this.dispatchEvent(new CustomEvent("bankoneth-host:enroll", {
      detail: {
        parentDomain:  this._enrollParent,
        parentNode:    namehash(this._enrollParent),
        pricePerLabel6: BigInt(Math.round(this._enrollPriceUsd * 1_000_000)),
        ownerShareBps: this._enrollOwnerSharePct * 100,
      },
      bubbles: true, composed: true,
    }));
  }

  private _renderEnroll() {
    return html`
      <b-card variant="elevated">
        <span slot="header">Enroll a hosted .eth</span>
        <form @submit=${this._enrollSubmit} class="stack">
          <b-input
            label="Your .eth"
            placeholder="yourdomain.eth"
            .value=${this._enrollParent}
            @input=${(e: Event) => { this._enrollParent = (e.target as HTMLInputElement).value.trim().toLowerCase(); }}
          ></b-input>
          <b-input
            label="Subname price (USD)"
            type="number" min="0"
            .value=${String(this._enrollPriceUsd)}
            @input=${(e: Event) => { this._enrollPriceUsd = Number((e.target as HTMLInputElement).value); }}
          >
            <span slot="suffix">USD / year</span>
          </b-input>
          <b-input
            label="Your share of revenue"
            type="number" min="0" max="75"
            .value=${String(this._enrollOwnerSharePct)}
            @input=${(e: Event) => { this._enrollOwnerSharePct = Number((e.target as HTMLInputElement).value); }}
          >
            <span slot="suffix">%</span>
          </b-input>
          <div class="muted">
            bankoneth keeps the rest as the host share. Once enrolled, anyone
            can claim a subname under your .eth via the bankoneth UI; you
            receive your share automatically through the payment router.
          </div>
          <div class="actions">
            <span></span>
            <b-button variant="primary" leadingIcon="shield">Enroll</b-button>
          </div>
        </form>
      </b-card>
    `;
  }

  // ── Issue path ───────────────────────────────────────────────────
  private async _issue() {
    this._issueSubmitting = true; this._error = "";
    try {
      const owner = this.client.walletClient!.account!.address as Address;
      const tx = await this.client.issueUnderHosted({
        parentNode: namehash(this._issueParent) as Hex,
        label: this._issueLabel,
        owner,
        payment: this._issueRail === "x402-avm" ? "x402-avm" : "eth",
      });
      this._issueTxHash = tx;
      this._stepper?.next();
    } catch (e) { this._error = (e as Error).message; }
    finally { this._issueSubmitting = false; }
  }

  private _renderIssueSearch() {
    return html`
      <div class="stack">
        <b-input
          label="Parent .eth"
          placeholder="yourdomain.eth"
          .value=${this._issueParent}
          @input=${(e: Event) => { this._issueParent = (e.target as HTMLInputElement).value.trim().toLowerCase(); }}
        ></b-input>
        <b-input
          label="Subname"
          placeholder="alice"
          .value=${this._issueLabel}
          @input=${(e: Event) => { this._issueLabel = (e.target as HTMLInputElement).value.trim().toLowerCase(); }}
        >
          <span slot="suffix">.${this._issueParent || "parent.eth"}</span>
        </b-input>
        <div class="actions">
          <span></span>
          <b-button variant="primary" trailingIcon="arrowRight"
            ?disabled=${!this._issueParent || !this._issueLabel}
            @click=${() => this._stepper?.next()}>Continue</b-button>
        </div>
      </div>
    `;
  }

  private _renderIssueReview() {
    return html`
      <div class="stack">
        <b-card variant="elevated">
          <span slot="header">Pricing</span>
          <div class="muted">
            Pricing is set per-parent by the host. Your wallet will be
            charged through the payment rail you select below.
          </div>
        </b-card>
        <b-card variant="elevated">
          <span slot="header">Payment rail</span>
          <b-rail-switcher
            .selected=${this._issueRail}
            @b-rail=${(e: Event) => { this._issueRail = (e as CustomEvent<{ selected: Rail }>).detail.selected; }}
          ></b-rail-switcher>
        </b-card>
        <div class="actions">
          <b-button variant="ghost" leadingIcon="arrowLeft" @click=${() => this._stepper?.back()}>Back</b-button>
          <b-button variant="primary" leadingIcon="wallet" .loading=${this._issueSubmitting} @click=${this._issue}>
            ${this._issueSubmitting ? "Submitting…" : `Claim ${this._issueLabel}.${this._issueParent}`}
          </b-button>
        </div>
        ${this._error
          ? html`<div style="color:var(--b-color-danger);font-size:var(--b-text-xs);font-family:var(--b-font-mono);">${this._error}</div>`
          : null}
      </div>
    `;
  }

  private _renderIssueSuccess() {
    return html`
      <div class="stack center">
        <div class="success-ico">${unsafeHTML(icon.check)}</div>
        <h2 style="margin:0;font-size:var(--b-text-xl);">
          ${this._issueLabel}.${this._issueParent} is yours
        </h2>
        <div class="muted">tx <code class="tx">${this._issueTxHash ?? "—"}</code></div>
        ${this._issueTxHash ? html`
          <div>
            <b-button variant="secondary" trailingIcon="external" size="sm"
              @click=${() => window.open(this.explorerTxBase + this._issueTxHash, "_blank")}>Etherscan</b-button>
          </div>
        ` : null}
      </div>
    `;
  }

  render() {
    return html`
      <div class="modes" role="tablist" aria-label="Host mode">
        <button role="tab" aria-selected=${this._mode === "issue"  ? "true" : "false"} @click=${() => this._setMode("issue")}>Issue under hosted .eth</button>
        <button role="tab" aria-selected=${this._mode === "enroll" ? "true" : "false"} @click=${() => this._setMode("enroll")}>Enroll your .eth as host</button>
      </div>
      ${this._mode === "enroll"
        ? this._renderEnroll()
        : html`
          <b-stepper .steps=${["Search", "Review", "Success"]}>
            <section data-step>${this._renderIssueSearch()}</section>
            <section data-step>${this._renderIssueReview()}</section>
            <section data-step>${this._renderIssueSuccess()}</section>
          </b-stepper>
        `}
    `;
  }
}
