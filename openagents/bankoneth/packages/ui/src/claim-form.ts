// SPDX-License-Identifier: Apache-2.0
//
// <bankoneth-claim> — Flow A, the four-step carousel.
//
//   Step 1 · Search   live availability pill + namehash + TBA preview + suggestions
//   Step 2 · Review   pricing card + tri-rail switcher + iNFT + AgenticPlace
//   Step 3 · Sign     confirmation card with the full payload
//   Step 4 · Success  tx hash + post-mint links + b-renew-countdown widget

import { LitElement, html, css } from "lit";
import { customElement, property, query, state } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";
import { type Address, type Hex } from "viem";

import {
  BankonethClient,
  bankonSubnameNode,
  labelToTokenId,
  previewTba,
  createDebouncedAvailabilityChecker,
  type AvailabilityHandle,
  type AvailabilityResult,
  suggestAlternatives,
  shortHex,
} from "@bankoneth/core";

import { tokens } from "./tokens/tokens";
import { motion } from "./tokens/motion";
import { icon } from "./tokens/icons";

import "./primitives/b-stepper";
import "./primitives/b-button";
import "./primitives/b-input";
import "./primitives/b-card";
import "./primitives/b-availability-pill";
import "./primitives/b-namehash-preview";
import "./primitives/b-suggestions";
import "./primitives/b-rail-switcher";
import "./primitives/b-renew-countdown";

import "./inft-toggle";
import "./agenticplace-toggle";

import { BStepper } from "./primitives/b-stepper";
import type { AvailabilityState } from "./primitives/b-availability-pill";
import type { Rail } from "./primitives/b-rail-switcher";
import type { SuggestionItem } from "./primitives/b-suggestions";

@customElement("bankoneth-claim")
export class BankonethClaim extends LitElement {
  static styles = [
    tokens,
    motion.fadeIn,
    motion.slideUp,
    motion.pop,
    css`
      :host { display: block; font-family: var(--b-font-sans); color: var(--b-color-text-primary); }
      .stack  { display: grid; gap: var(--b-space-5); }
      .row    { display: grid; grid-template-columns: 1fr auto; gap: var(--b-space-3); align-items: center; }
      .actions{ display: flex; gap: var(--b-space-3); justify-content: space-between; margin-top: var(--b-space-6); }
      .center { text-align: center; }

      .success-ico {
        display: inline-flex;
        line-height: 0;
        color: var(--b-color-success);
        font-size: 3rem;
        animation: b-pop var(--b-motion-slow) var(--b-ease-spring);
      }
      .title {
        font-size: var(--b-text-xl);
        font-weight: var(--b-weight-semibold);
        margin: 0 0 var(--b-space-2);
      }
      .muted { color: var(--b-color-text-muted); font-size: var(--b-text-sm); }
      .tx    { font-family: var(--b-font-mono); font-size: var(--b-text-xs); color: var(--b-color-text-secondary); }
      .links { display: flex; gap: var(--b-space-2); flex-wrap: wrap; justify-content: center; }
    `,
  ];

  // ── Inputs from the consumer ─────────────────────────────────────
  @property({ attribute: false }) client!: BankonethClient;
  /** Address of the iNFT_7857 contract on its host chain (e.g. 0G Galileo). */
  @property() inftTokenContract = "" as Address | "";
  /** ERC-6551 account implementation on the iNFT host chain. */
  @property() inftImplementation = "" as Address | "";
  /** Chain ID of the iNFT host chain (default 0G Galileo). */
  @property({ type: Number }) inftChainId = 16601;
  /** Default duration shown in step 2. */
  @property({ type: Number }) defaultDurationYears = 1;
  /** etherscan URL builder; consumer can override for Sepolia / etc. */
  @property() explorerTxBase = "https://etherscan.io/tx/";

  // ── Internal state ───────────────────────────────────────────────
  @state() private _label = "";
  @state() private _availability: AvailabilityState = "idle";
  @state() private _availabilityRes: AvailabilityResult | null = null;
  @state() private _suggestions: SuggestionItem[] = [];
  @state() private _durationYears = 1;
  @state() private _rail: Rail = "eth";
  @state() private _inftModeA = true;
  @state() private _listOnAgenticPlace = false;
  @state() private _quoteUsd6: bigint | null = null;
  @state() private _quotes: Partial<Record<Rail, string>> = {};
  @state() private _submitting = false;
  @state() private _error = "";
  @state() private _txHash: Hex | null = null;
  @state() private _expiresAt = 0;

  @query("b-stepper") private _stepper!: BStepper;

  private _availChecker: AvailabilityHandle | null = null;

  connectedCallback() {
    super.connectedCallback();
    this._durationYears = this.defaultDurationYears;
    if (this.client) this._initChecker();
  }

  disconnectedCallback() {
    this._availChecker?.dispose();
    super.disconnectedCallback();
  }

  updated(changed: Map<string, unknown>) {
    if (changed.has("client") && this.client && !this._availChecker) {
      this._initChecker();
    }
  }

  private _initChecker() {
    const nameWrapperAddr = (this.client as unknown as { addresses: { nameWrapper?: Address } }).addresses.nameWrapper;
    // BankonethAddresses may not include nameWrapper; fall back to subnameRegistrar's known dependency.
    // For the in-tab preview we accept either via prop in a future revision.
    if (!nameWrapperAddr) return;
    this._availChecker = createDebouncedAvailabilityChecker(
      {
        publicClient: this.client.publicClient,
        nameWrapperAddr,
        parentNode: this.client.bankonEthNode,
      },
      (res, err) => {
        if (err) { this._availability = "error"; return; }
        if (!res) { this._availability = "idle"; this._availabilityRes = null; return; }
        this._availability = res.available ? "free" : "taken";
        this._availabilityRes = res;
        if (!res.available) this._loadSuggestions();
        else this._suggestions = [];
      },
    );
  }

  private async _loadSuggestions() {
    const nameWrapperAddr = (this.client as unknown as { addresses: { nameWrapper?: Address } }).addresses.nameWrapper;
    if (!nameWrapperAddr) return;
    const walletAddr = (this.client.walletClient?.account?.address as Address | undefined);
    const list = await suggestAlternatives({
      publicClient: this.client.publicClient,
      nameWrapperAddr,
      parentNode:   this.client.bankonEthNode,
      label:        this._label,
      walletAddress: walletAddr,
      limit: 6,
    });
    this._suggestions = list.map(s => ({
      label: s.label, available: s.available, reason: s.reason,
    }));
  }

  private _onLabel(e: Event) {
    const v = (e.target as HTMLInputElement).value.trim().toLowerCase();
    this._label = v;
    if (!v) { this._availability = "idle"; this._suggestions = []; return; }
    this._availability = "checking";
    this._availChecker?.check(v);
  }

  private _pickSuggestion(e: Event) {
    const label = (e as CustomEvent<{ label: string }>).detail.label;
    this._label = label;
    this._availability = "checking";
    this._availChecker?.check(label);
  }

  private async _toReview() {
    if (this._availability !== "free") return;
    try {
      const q = await this.client.quoteSubname(this._label, this._durationYears);
      this._quoteUsd6 = q.usd6;
      this._quotes = {
        "eth":         `≈ ${(Number(q.usd6) / 1_000_000 / 2200).toFixed(5)} ETH`,
        "usdc-permit": `${(Number(q.usd6) / 1_000_000).toFixed(2)} USDC`,
        "x402-avm":    `${(Number(q.usd6) / 1_000_000).toFixed(2)} USDCa`,
      };
    } catch (e) { this._quoteUsd6 = null; }
    this._stepper.next();
  }

  private async _submit() {
    this._submitting = true; this._error = "";
    try {
      const owner = this.client.walletClient?.account?.address as Address;
      const tx = await this.client.claim({
        label: this._label,
        owner,
        durationYears: this._durationYears,
        payment: this._rail,
        inftModeA: this._inftModeA,
        listOnAgenticPlace: this._listOnAgenticPlace,
      });
      this._txHash = tx;
      this._expiresAt = Math.floor(Date.now() / 1000) + this._durationYears * 365 * 24 * 3600;
      this._stepper.next();
    } catch (e) {
      this._error = (e as Error).message;
    } finally {
      this._submitting = false;
    }
  }

  private _tbaPreview(): Hex | "" {
    if (!this._label || !this.inftTokenContract || !this.inftImplementation) return "";
    const { tokenId } = labelToTokenId(this._label);
    return previewTba({
      implementation: this.inftImplementation,
      chainId:        this.inftChainId,
      tokenContract:  this.inftTokenContract,
      tokenId,
    }) as Hex;
  }

  private _namehash(): Hex | "" {
    if (!this._label) return "";
    return bankonSubnameNode(this._label, this.client.bankonEthNode) as Hex;
  }

  render() {
    return html`
      <b-stepper .steps=${["Search", "Review", "Sign", "Success"]}>
        <section data-step>${this._renderSearch()}</section>
        <section data-step>${this._renderReview()}</section>
        <section data-step>${this._renderSign()}</section>
        <section data-step>${this._renderSuccess()}</section>
      </b-stepper>
    `;
  }

  // ── Step 1 ────────────────────────────────────────────────────────
  private _renderSearch() {
    return html`
      <div class="stack">
        <div class="row">
          <b-input
            label="Subname"
            placeholder="alice"
            .value=${this._label}
            @input=${this._onLabel}
            inputId="claim-label"
          >
            <span slot="suffix">.bankon.eth</span>
          </b-input>
          <b-availability-pill
            state=${this._availability}
            ownerLabel=${this._availabilityRes && !this._availabilityRes.available ? shortHex(this._availabilityRes.owner) : ""}
            suffix="${this._label || ""}.bankon.eth"
          ></b-availability-pill>
        </div>

        <b-namehash-preview
          subname=${this._label ? `${this._label}.bankon.eth` : ""}
          namehashHex=${this._namehash() as string}
          tbaAddress=${this._tbaPreview() as string}
        ></b-namehash-preview>

        ${this._suggestions.length > 0
          ? html`<b-suggestions .items=${this._suggestions} @b-suggestion-pick=${this._pickSuggestion}></b-suggestions>`
          : null}

        <div class="actions">
          <span></span>
          <b-button
            variant="primary"
            trailingIcon="arrowRight"
            ?disabled=${this._availability !== "free"}
            @click=${this._toReview}
          >Continue</b-button>
        </div>
      </div>
    `;
  }

  // ── Step 2 ────────────────────────────────────────────────────────
  private _renderReview() {
    return html`
      <div class="stack">
        <b-card variant="elevated">
          <span slot="header">Pricing</span>
          <div class="muted">
            <strong style="color:var(--b-color-text-primary);font-size:var(--b-text-lg);font-family:var(--b-font-mono);">
              ${this._quoteUsd6 != null ? (Number(this._quoteUsd6) / 1_000_000).toFixed(2) : "—"} USD
            </strong>
            / year · ${this._durationYears} year${this._durationYears > 1 ? "s" : ""} total
          </div>
          <div style="display:flex;align-items:center;gap:var(--b-space-3);margin-top:var(--b-space-4);">
            <span class="muted">Duration</span>
            <b-input
              type="number"
              .value=${String(this._durationYears)}
              min="1" max="20"
              @input=${(e: Event) => { this._durationYears = Number((e.target as HTMLInputElement).value); }}
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

        <b-card variant="elevated">
          <span slot="header">Options</span>
          <div style="display:grid;gap:var(--b-space-3);">
            <bankoneth-inft-toggle
              ?enabled=${this._inftModeA}
              @change=${(e: Event) => { this._inftModeA = (e as CustomEvent<{ enabled: boolean }>).detail.enabled; }}
            ></bankoneth-inft-toggle>
            <bankoneth-agenticplace-toggle
              ?enabled=${this._listOnAgenticPlace}
              @change=${(e: Event) => { this._listOnAgenticPlace = (e as CustomEvent<{ enabled: boolean }>).detail.enabled; }}
            ></bankoneth-agenticplace-toggle>
          </div>
        </b-card>

        <div class="actions">
          <b-button variant="ghost" leadingIcon="arrowLeft" @click=${() => this._stepper.back()}>Back</b-button>
          <b-button variant="primary" trailingIcon="arrowRight" @click=${() => this._stepper.next()}>Continue</b-button>
        </div>
      </div>
    `;
  }

  // ── Step 3 ────────────────────────────────────────────────────────
  private _renderSign() {
    return html`
      <div class="stack">
        <b-card variant="elevated">
          <span slot="header">${unsafeHTML(icon.shield)} Confirm & sign</span>
          <div style="display:grid;gap:var(--b-space-3);font-size:var(--b-text-sm);">
            <div><span class="muted">Subname:</span>
              <strong style="font-family:var(--b-font-mono)">${this._label}.bankon.eth</strong></div>
            <div><span class="muted">TBA address:</span>
              <code class="tx">${this._tbaPreview() || "—"}</code></div>
            <div><span class="muted">Payment rail:</span> ${this._rail.toUpperCase()}</div>
            <div><span class="muted">Cost:</span>
              <strong style="font-family:var(--b-font-mono)">
                ${this._quoteUsd6 ? (Number(this._quoteUsd6) / 1_000_000).toFixed(2) : "—"} USD
                × ${this._durationYears} yr
              </strong></div>
            ${this._error
              ? html`<div style="color:var(--b-color-danger);font-size:var(--b-text-xs);font-family:var(--b-font-mono);user-select:text;">${this._error}</div>`
              : null}
          </div>
        </b-card>

        <div class="actions">
          <b-button variant="ghost" leadingIcon="arrowLeft" ?disabled=${this._submitting} @click=${() => this._stepper.back()}>Back</b-button>
          ${this.client ? html`
            <b-button variant="primary" leadingIcon="wallet" .loading=${this._submitting} @click=${this._submit}>
              ${this._submitting ? "Submitting…" : "Sign & claim"}
            </b-button>` : html`
            <b-button variant="secondary" leadingIcon="wallet"
                      @click=${() => this.dispatchEvent(new CustomEvent("request-connect", { bubbles: true, composed: true }))}>
              Connect to claim
            </b-button>`}
        </div>
      </div>
    `;
  }

  // ── Step 4 ────────────────────────────────────────────────────────
  private _renderSuccess() {
    return html`
      <div class="stack center">
        <div class="success-ico">${unsafeHTML(icon.check)}</div>
        <h2 class="title">${this._label}.bankon.eth is yours</h2>
        <div class="muted">tx <code class="tx">${this._txHash ?? "—"}</code></div>

        <div class="links">
          ${this._txHash ? html`
            <b-button variant="secondary" trailingIcon="external" size="sm"
              @click=${() => window.open(this.explorerTxBase + this._txHash, "_blank")}>Etherscan</b-button>
          ` : null}
          ${this._inftModeA && this._tbaPreview() ? html`
            <b-button variant="ghost" trailingIcon="agent" size="sm"
              @click=${() => navigator.clipboard?.writeText(this._tbaPreview())}>Copy agent wallet</b-button>
          ` : null}
        </div>

        ${this._expiresAt > 0 ? html`
          <b-renew-countdown
            .expiresAt=${this._expiresAt}
            .durationYears=${this._durationYears}
            @b-renew=${() => this.dispatchEvent(new CustomEvent("bankoneth-claim:renew", { detail: { label: this._label }, bubbles: true, composed: true }))}
          ></b-renew-countdown>
        ` : null}
      </div>
    `;
  }
}
