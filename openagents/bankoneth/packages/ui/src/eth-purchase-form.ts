// SPDX-License-Identifier: Apache-2.0
//
// <bankoneth-purchase> — Flow B, the four-step carousel for .eth 2LD purchase.
//
//   Step 1 · Search   live availability + namehash preview
//   Step 2 · Review   ETH quote + tri-rail switcher
//   Step 3 · Commit   commit-window countdown ring (60s minimum)
//   Step 4 · Reveal   sign the reveal tx + success card
//
// The commit-reveal flow is what makes Flow B special; we visualise the
// 60-second window as a thick SVG ring that drains while the user waits.

import { LitElement, html, css } from "lit";
import { customElement, property, query, state } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";
import { type Address, type Hex, keccak256, toHex } from "viem";

import { BankonethClient, shortHex } from "@bankoneth/core";

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

@customElement("bankoneth-purchase")
export class BankonethPurchase extends LitElement {
  static styles = [
    tokens,
    motion.fadeIn,
    motion.pop,
    motion.slideUp,
    motion.ringCountdown,
    css`
      :host { display: block; font-family: var(--b-font-sans); color: var(--b-color-text-primary); }
      .stack   { display: grid; gap: var(--b-space-5); }
      .actions { display: flex; gap: var(--b-space-3); justify-content: space-between; margin-top: var(--b-space-6); }
      .muted   { color: var(--b-color-text-muted); font-size: var(--b-text-sm); }
      .center  { text-align: center; }

      .timer-ring {
        position: relative;
        width: 180px; height: 180px;
        margin: var(--b-space-4) auto;
      }
      .timer-ring svg { transform: rotate(-90deg); }
      .timer-ring circle { fill: none; stroke-width: 8; }
      .timer-ring .bg { stroke: var(--b-color-bg-4); }
      .timer-ring .fg { stroke: var(--b-color-accent); stroke-linecap: round; }
      .timer-ring .center-text {
        position: absolute; inset: 0;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        font-family: var(--b-font-mono);
      }
      .timer-ring .secs {
        font-size: var(--b-text-3xl);
        font-weight: var(--b-weight-bold);
      }
      .timer-ring .hint {
        font-size: var(--b-text-xs);
        color: var(--b-color-text-muted);
      }

      .success-ico {
        display: inline-flex; line-height: 0;
        color: var(--b-color-success); font-size: 3rem;
        animation: b-pop var(--b-motion-slow) var(--b-ease-spring);
      }
      .tx { font-family: var(--b-font-mono); font-size: var(--b-text-xs); color: var(--b-color-text-secondary); }
    `,
  ];

  @property({ attribute: false }) client!: BankonethClient;
  @property({ type: Number }) defaultDurationYears = 1;
  @property() explorerTxBase = "https://etherscan.io/tx/";

  @state() private _label = "";
  @state() private _durationYears = 1;
  @state() private _rail: Rail = "eth";
  @state() private _quoteWei: bigint | null = null;
  @state() private _quoteUsd6: bigint | null = null;
  @state() private _quotes: Partial<Record<Rail, string>> = {};
  @state() private _secret: Hex = "0x" as Hex;
  @state() private _committed = false;
  @state() private _commitHash: Hex | null = null;
  @state() private _remainingS = 0;
  @state() private _submitting = false;
  @state() private _txHash: Hex | null = null;
  @state() private _error = "";

  @query("b-stepper") private _stepper!: BStepper;

  private _countdownTimer: ReturnType<typeof setInterval> | null = null;

  connectedCallback() {
    super.connectedCallback();
    this._durationYears = this.defaultDurationYears;
  }

  disconnectedCallback() {
    if (this._countdownTimer) clearInterval(this._countdownTimer);
    super.disconnectedCallback();
  }

  private async _refreshQuote() {
    if (!this._label) return;
    try {
      const q = await this.client.quoteEthPurchase(this._label, this._durationYears);
      this._quoteWei = q.wei;
      this._quoteUsd6 = q.usd6;
      this._quotes = {
        "eth":      `${(Number(q.wei) / 1e18).toFixed(5)} ETH`,
        "x402-avm": `${(Number(q.usd6) / 1_000_000).toFixed(2)} USDCa`,
      };
    } catch (e) { this._error = (e as Error).message; }
  }

  private async _toReview() {
    await this._refreshQuote();
    this._stepper.next();
  }

  private async _commit() {
    this._submitting = true; this._error = "";
    try {
      const owner = this.client.walletClient!.account!.address as Address;
      this._secret = keccak256(toHex(`${this._label}|${owner}|${Date.now()}`));
      const { commitment } = await this.client.purchaseCommit({
        label: this._label,
        owner,
        durationYears: this._durationYears,
        resolver: this.client.addresses.resolver,
        reverseRecord: false,
        ownerControlledFuses: 0,
        payment: this._rail === "x402-avm" ? "x402-avm" : "eth",
      });
      this._committed = true;
      this._commitHash = commitment;
      this._stepper.next();
      this._startCountdown(65);
    } catch (e) { this._error = (e as Error).message; }
    finally { this._submitting = false; }
  }

  private _startCountdown(seconds: number) {
    this._remainingS = seconds;
    if (this._countdownTimer) clearInterval(this._countdownTimer);
    this._countdownTimer = setInterval(() => {
      this._remainingS = Math.max(0, this._remainingS - 1);
      if (this._remainingS === 0 && this._countdownTimer) {
        clearInterval(this._countdownTimer); this._countdownTimer = null;
      }
    }, 1000);
  }

  private async _reveal() {
    this._submitting = true; this._error = "";
    try {
      const owner = this.client.walletClient!.account!.address as Address;
      const tx = await this.client.purchaseReveal({
        label: this._label,
        owner,
        durationYears: this._durationYears,
        resolver: this.client.addresses.resolver,
        reverseRecord: false,
        ownerControlledFuses: 0,
        payment: this._rail === "x402-avm" ? "x402-avm" : "eth",
      }, this._secret);
      this._txHash = tx;
      this._stepper.next();
    } catch (e) { this._error = (e as Error).message; }
    finally { this._submitting = false; }
  }

  render() {
    return html`
      <b-stepper .steps=${["Search", "Review", "Commit", "Reveal"]}>
        <section data-step>${this._renderSearch()}</section>
        <section data-step>${this._renderReview()}</section>
        <section data-step>${this._renderCommit()}</section>
        <section data-step>${this._renderReveal()}</section>
      </b-stepper>
    `;
  }

  private _renderSearch() {
    return html`
      <div class="stack">
        <b-input
          label=".eth 2LD"
          placeholder="newdomain"
          .value=${this._label}
          @input=${(e: Event) => { this._label = (e.target as HTMLInputElement).value.trim().toLowerCase(); }}
        >
          <span slot="suffix">.eth</span>
        </b-input>
        <div class="muted">
          The canonical ENS commit-reveal flow, wrapped through bankoneth. Pay
          with ETH or Algorand USDC (x402). The 60-second commit window is
          enforced on-chain by the ENS controller.
        </div>
        <div class="actions">
          <span></span>
          <b-button variant="primary" trailingIcon="arrowRight"
            ?disabled=${!this._label} @click=${this._toReview}>Continue</b-button>
        </div>
      </div>
    `;
  }

  private _renderReview() {
    return html`
      <div class="stack">
        <b-card variant="elevated">
          <span slot="header">Pricing</span>
          <div class="muted">
            <strong style="color:var(--b-color-text-primary);font-size:var(--b-text-lg);font-family:var(--b-font-mono);">
              ${this._quoteWei != null ? (Number(this._quoteWei) / 1e18).toFixed(5) : "—"} ETH
            </strong>
            for ${this._durationYears} year${this._durationYears > 1 ? "s" : ""}
            ${this._quoteUsd6 ? ` · ≈ $${(Number(this._quoteUsd6) / 1_000_000).toFixed(2)}` : ""}
          </div>
          <div style="display:flex;align-items:center;gap:var(--b-space-3);margin-top:var(--b-space-4);">
            <span class="muted">Duration</span>
            <b-input
              type="number"
              .value=${String(this._durationYears)}
              min="1" max="10"
              @input=${(e: Event) => { this._durationYears = Number((e.target as HTMLInputElement).value); this._refreshQuote(); }}
              style="width:120px"
            ></b-input>
          </div>
        </b-card>
        <b-card variant="elevated">
          <span slot="header">Payment rail</span>
          <b-rail-switcher
            .selected=${this._rail}
            .quotes=${this._quotes}
            @b-rail=${(e: Event) => { this._rail = (e as CustomEvent<{ selected: Rail }>).detail.selected; }}
          ></b-rail-switcher>
        </b-card>
        <div class="actions">
          <b-button variant="ghost" leadingIcon="arrowLeft" @click=${() => this._stepper.back()}>Back</b-button>
          ${this.client ? html`
            <b-button variant="primary" leadingIcon="shield" .loading=${this._submitting} @click=${this._commit}>
              ${this._submitting ? "Committing…" : "Commit"}
            </b-button>` : html`
            <b-button variant="secondary" leadingIcon="wallet"
                      @click=${() => this.dispatchEvent(new CustomEvent("request-connect", { bubbles: true, composed: true }))}>
              Connect to commit
            </b-button>`}
        </div>
      </div>
    `;
  }

  private _renderCommit() {
    const circ = 2 * Math.PI * 80;
    const pct = this._remainingS / 65;
    const offset = circ * (1 - pct);
    return html`
      <div class="stack center">
        <h2 style="margin:0;font-size:var(--b-text-lg);">Wait for the commit window</h2>
        <p class="muted" style="margin:0;">ENS enforces a 60-second minimum between commit and reveal.</p>

        <div class="timer-ring" role="timer" aria-live="off">
          <svg width="180" height="180" viewBox="0 0 180 180" aria-hidden="true">
            <circle class="bg" cx="90" cy="90" r="80"/>
            <circle class="fg" cx="90" cy="90" r="80"
              stroke-dasharray=${circ}
              stroke-dashoffset=${offset}
              style="transition: stroke-dashoffset 1s linear;"
            />
          </svg>
          <div class="center-text">
            <span class="secs">${this._remainingS}s</span>
            <span class="hint">${this._remainingS > 0 ? "open in a moment" : "ready"}</span>
          </div>
        </div>

        <div class="muted">commitment <code class="tx">${shortHex(this._commitHash ?? "0x" as Hex, 10, 8)}</code></div>

        <div class="actions">
          <b-button variant="ghost" leadingIcon="arrowLeft" ?disabled=${this._submitting} @click=${() => this._stepper.back()}>Cancel</b-button>
          ${this.client ? html`
            <b-button variant="primary" leadingIcon="wallet" .loading=${this._submitting}
              ?disabled=${this._remainingS > 0} @click=${this._reveal}>
              ${this._remainingS > 0 ? `Reveal in ${this._remainingS}s` : "Reveal & register"}
            </b-button>` : html`
            <b-button variant="secondary" leadingIcon="wallet"
                      @click=${() => this.dispatchEvent(new CustomEvent("request-connect", { bubbles: true, composed: true }))}>
              Connect to reveal
            </b-button>`}
        </div>
      </div>
    `;
  }

  private _renderReveal() {
    return html`
      <div class="stack center">
        <div class="success-ico">${unsafeHTML(icon.check)}</div>
        <h2 style="margin:0;font-size:var(--b-text-xl);">${this._label}.eth is yours</h2>
        <div class="muted">tx <code class="tx">${this._txHash ?? "—"}</code></div>
        ${this._txHash ? html`
          <div>
            <b-button variant="secondary" trailingIcon="external" size="sm"
              @click=${() => window.open(this.explorerTxBase + this._txHash, "_blank")}>Etherscan</b-button>
          </div>
        ` : null}
        ${this._error
          ? html`<div style="color:var(--b-color-danger);font-size:var(--b-text-xs);font-family:var(--b-font-mono);">${this._error}</div>`
          : null}
      </div>
    `;
  }
}
