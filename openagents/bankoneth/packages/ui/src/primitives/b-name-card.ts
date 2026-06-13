// SPDX-License-Identifier: Apache-2.0
//
// <bankoneth-name-card> — the hero name display.
//
// Designed to beat the ENS app.ens.domains profile card on:
//   - Density          (single card vs. ENS's long vertical scroll across tabs)
//   - Agentic context  (BONAFIDE score, mindx.endpoint badge, inft.uri thumbnail,
//                       agenticplace.listing chip — ENS shows none of this)
//   - Visual treatment (gradient name header + animated avatar ring, fuse badge
//                       row, sparkline expiry timeline)
//   - Embed-ability    (single Web Component, drops into any HTML, exposes a
//                       resolution prop or a full NameLookup; emits standard
//                       events)
//
// Inputs (either is sufficient):
//   - `name`     — full subname like "alice.bankon.eth"; component fetches via
//                  `lookupName()` using the passed `client` (or fires
//                  `bankoneth-card:request` for parent to handle).
//   - `lookup`   — pre-fetched NameLookup; component just renders.

import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";
import { type Address, type Hex } from "viem";

import {
  type BankonethClient,
  type NameLookup,
  lookupName,
  formatExpiry,
  hasFuse,
} from "@bankoneth/core";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";
import { icon } from "../tokens/icons";

import "./b-card";
import "./b-fuse-badges";
import "./b-tba-chip";

@customElement("bankoneth-name-card")
export class BankonethNameCard extends LitElement {
  static styles = [
    tokens,
    motion.fadeIn,
    motion.slideUp,
    motion.pop,
    motion.pulse,
    css`
      :host {
        display: block;
        font-family: var(--b-font-sans);
        --_grad: linear-gradient(135deg,
          var(--b-color-accent)   0%,
          var(--b-color-accent-2) 60%,
          color-mix(in srgb, var(--b-color-success) 50%, var(--b-color-accent-2)) 100%);
      }

      .frame {
        background:
          radial-gradient(circle at 0% 0%, color-mix(in srgb, var(--b-color-accent) 18%, transparent) 0%, transparent 45%),
          var(--b-color-bg-2);
        border: 1px solid var(--b-color-border);
        border-radius: var(--b-radius-xl);
        padding: var(--b-space-6);
        overflow: hidden;
        position: relative;
      }
      .frame::before {
        content: ""; position: absolute;
        inset: 0;
        background: var(--_grad);
        opacity: 0.08;
        pointer-events: none;
      }
      .frame > * { position: relative; }

      /* ── Hero header (avatar + name + status) ─────────────────── */
      header {
        display: grid;
        grid-template-columns: 88px 1fr auto;
        gap: var(--b-space-4);
        align-items: center;
        margin-bottom: var(--b-space-5);
      }
      .avatar-ring {
        position: relative;
        width: 88px; height: 88px;
        border-radius: var(--b-radius-full);
        background: var(--_grad);
        padding: 3px;
        animation: b-pulse 4s var(--b-ease-standard) infinite;
      }
      .avatar {
        width: 100%; height: 100%;
        border-radius: var(--b-radius-full);
        background: var(--b-color-bg-1);
        overflow: hidden;
        display: flex; align-items: center; justify-content: center;
      }
      .avatar img { width: 100%; height: 100%; object-fit: cover; }
      .avatar-fallback {
        font-family: var(--b-font-mono);
        font-size: 28px;
        font-weight: var(--b-weight-bold);
        background: var(--_grad);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
      }

      .name-group { min-width: 0; }
      .name {
        font-family: var(--b-font-mono);
        font-size: var(--b-text-2xl);
        font-weight: var(--b-weight-bold);
        letter-spacing: -0.02em;
        background: var(--_grad);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        word-break: break-all;
        line-height: 1.05;
      }
      .name-sub {
        display: flex; flex-wrap: wrap; gap: var(--b-space-2) var(--b-space-3);
        margin-top: var(--b-space-2);
        font-size: var(--b-text-xs);
        color: var(--b-color-text-muted);
        align-items: center;
      }
      .name-sub code { font-family: var(--b-font-mono); }
      .dot { width: 4px; height: 4px; background: var(--b-color-text-muted); border-radius: 50%; }

      .actions { display: flex; gap: var(--b-space-2); align-items: flex-start; }
      .ico-btn {
        all: unset; cursor: pointer; display: inline-flex; line-height: 0;
        color: var(--b-color-text-muted);
        padding: var(--b-space-2);
        border-radius: var(--b-radius-md);
        font-size: 14px;
        background: var(--b-color-bg-3);
        transition: color var(--b-motion-fast) var(--b-ease-standard),
                    background var(--b-motion-fast) var(--b-ease-standard);
      }
      .ico-btn:hover { color: var(--b-color-text-primary); background: var(--b-color-bg-4); }
      .ico-btn:focus-visible { outline: none; box-shadow: var(--b-shadow-focus); }

      /* ── Status row (owner / expiry / fuses) ──────────────────── */
      .status {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: var(--b-space-3);
        padding: var(--b-space-4);
        background: var(--b-color-bg-3);
        border-radius: var(--b-radius-md);
        margin-bottom: var(--b-space-5);
      }
      .stat {
        display: grid; gap: 2px;
        font-size: var(--b-text-xs);
      }
      .stat-label {
        color: var(--b-color-text-muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 10px;
        font-weight: var(--b-weight-semibold);
      }
      .stat-value {
        color: var(--b-color-text-primary);
        font-family: var(--b-font-mono);
        font-size: var(--b-text-sm);
      }
      .stat .badge-row { display: flex; gap: var(--b-space-2); align-items: center; flex-wrap: wrap; margin-top: 2px; }
      .badge {
        display: inline-flex; align-items: center; gap: 4px;
        padding: 2px 8px;
        border-radius: var(--b-radius-full);
        font-size: 10px;
        font-weight: var(--b-weight-semibold);
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }
      .badge-ok      { background: var(--b-color-success-faded); color: var(--b-color-success); }
      .badge-warn    { background: rgba(245,158,11,.18); color: var(--b-color-warning); }
      .badge-info    { background: var(--b-color-accent-faded); color: var(--b-color-accent); }

      /* ── Records grid ─────────────────────────────────────────── */
      .records-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: var(--b-space-3);
      }
      .section {
        background: var(--b-color-bg-3);
        border-radius: var(--b-radius-md);
        padding: var(--b-space-3) var(--b-space-4);
      }
      .section-title {
        display: flex; align-items: center; gap: var(--b-space-2);
        margin: 0 0 var(--b-space-2);
        color: var(--b-color-text-secondary);
        font-size: 10px;
        font-weight: var(--b-weight-bold);
        letter-spacing: 0.1em;
        text-transform: uppercase;
      }
      .section-title .ico { line-height: 0; color: var(--b-color-accent); font-size: 12px; }
      .rec-row {
        display: grid;
        grid-template-columns: 92px 1fr auto;
        gap: var(--b-space-2);
        align-items: center;
        padding: var(--b-space-1) 0;
        border-bottom: 1px dashed var(--b-color-border);
        font-size: var(--b-text-xs);
      }
      .rec-row:last-child { border-bottom: 0; }
      .rec-key {
        color: var(--b-color-text-muted);
        font-family: var(--b-font-mono);
      }
      .rec-val {
        color: var(--b-color-text-primary);
        overflow-wrap: anywhere;
        word-break: break-all;
        font-family: var(--b-font-mono);
      }
      .rec-empty { color: var(--b-color-text-muted); font-style: italic; }
      .rec-link {
        color: var(--b-color-accent);
        text-decoration: none;
        word-break: break-all;
      }
      .rec-link:hover { text-decoration: underline; }

      /* ── Loading / empty states ───────────────────────────────── */
      .loading {
        height: 280px;
        display: flex; align-items: center; justify-content: center;
        color: var(--b-color-text-muted);
        font-size: var(--b-text-sm);
      }
      .empty {
        text-align: center;
        padding: var(--b-space-12) var(--b-space-4);
        color: var(--b-color-text-muted);
      }
      .empty .name-ghost {
        font-family: var(--b-font-mono);
        font-size: var(--b-text-lg);
        color: var(--b-color-text-secondary);
        margin-bottom: var(--b-space-2);
      }

      .err {
        color: var(--b-color-danger);
        font-size: var(--b-text-xs);
        font-family: var(--b-font-mono);
        margin-top: var(--b-space-2);
      }

      @media (max-width: 600px) {
        header { grid-template-columns: 64px 1fr; }
        .actions { grid-column: 1 / -1; }
        .avatar-ring { width: 64px; height: 64px; }
        .status { grid-template-columns: 1fr; }
        .frame { padding: var(--b-space-4); }
      }
    `,
  ];

  // ── Inputs ────────────────────────────────────────────────────────
  @property({ attribute: false }) client?: BankonethClient;
  @property() name = "";
  /** When set, ignore `name` and just render this. */
  @property({ attribute: false }) lookup?: NameLookup;
  /** Etherscan/0G explorer URL prefix, e.g. "https://etherscan.io/address/". */
  @property() addressExplorerBase = "https://etherscan.io/address/";
  /** Block-explorer URL for the iNFT chain where the TBA lives. */
  @property() tbaExplorerBase = "https://explorer.0g.ai/address/";

  // ── State ─────────────────────────────────────────────────────────
  @state() private _lookup: NameLookup | null = null;
  @state() private _loading = false;
  @state() private _error = "";

  // ── Lifecycle ─────────────────────────────────────────────────────
  connectedCallback() {
    super.connectedCallback();
    this._maybeFetch();
  }

  updated(changed: Map<string, unknown>) {
    if (changed.has("name") || changed.has("client") || changed.has("lookup")) {
      this._maybeFetch();
    }
  }

  private async _maybeFetch() {
    if (this.lookup) { this._lookup = this.lookup; return; }
    if (!this.name || !this.client) return;
    const nameWrapperAddr =
      (this.client.addresses as unknown as { nameWrapper?: Address }).nameWrapper;
    if (!nameWrapperAddr) {
      // BankonethAddresses doesn't carry the NameWrapper directly today; the
      // host page must pass `lookup` pre-fetched. Surface a helpful message.
      this._error = "client.addresses.nameWrapper not set — pass `lookup` pre-fetched.";
      return;
    }
    this._loading = true; this._error = "";
    try {
      this._lookup = await lookupName({
        publicClient:    this.client.publicClient,
        nameWrapperAddr,
        resolverAddr:    this.client.addresses.resolver,
        inftAdapterAddr: this.client.addresses.inftAdapter,
        name:            this.name,
      });
    } catch (e) {
      this._error = (e as Error).message;
    } finally {
      this._loading = false;
    }
  }

  // ── Render ────────────────────────────────────────────────────────
  render() {
    if (this._loading && !this._lookup) {
      return html`<div class="frame loading b-fade-in">Resolving ${this.name}…</div>`;
    }
    const L = this._lookup;
    if (!L) {
      return html`
        <div class="frame empty b-fade-in">
          <div class="name-ghost">${this.name || "—"}</div>
          <div>Pass a <code>name</code> + <code>client</code> or a pre-fetched <code>lookup</code>.</div>
          ${this._error ? html`<div class="err">${this._error}</div>` : null}
        </div>
      `;
    }

    return html`
      <article class="frame b-slide-up" aria-label="${L.name}">
        ${this._renderHeader(L)}
        ${this._renderStatus(L)}
        ${this._renderRecords(L)}
      </article>
    `;
  }

  private _renderHeader(L: NameLookup) {
    const avatarUrl = L.records["avatar"] || "";
    const initial = L.name.split(".")[0]?.[0]?.toUpperCase() ?? "?";
    return html`
      <header>
        <div class="avatar-ring">
          <div class="avatar">
            ${avatarUrl
              ? html`<img src=${avatarUrl} alt="${L.name} avatar"
                       @error=${(e: Event) => { (e.target as HTMLImageElement).style.display = "none"; }}/>`
              : html`<span class="avatar-fallback">${initial}</span>`}
          </div>
        </div>
        <div class="name-group">
          <div class="name">${L.name}</div>
          <div class="name-sub">
            <code title="${L.node}">${L.node.slice(0, 10)}…${L.node.slice(-6)}</code>
            <span class="dot"></span>
            <span>${formatExpiry(L.expiry)}</span>
            ${L.isSoulbound
              ? html`<span class="dot"></span><span class="badge badge-ok">SOULBOUND</span>`
              : null}
            ${L.tba && L.tba !== "0x0000000000000000000000000000000000000000"
              ? html`<span class="dot"></span><b-tba-chip
                  .tba=${L.tba}
                  .chainExplorerBase=${this.tbaExplorerBase}
                ></b-tba-chip>`
              : null}
          </div>
        </div>
        <div class="actions">
          <button class="ico-btn" @click=${() => this._copy(L.name)} aria-label="Copy name">${unsafeHTML(icon.copy)}</button>
          <a class="ico-btn"
             target="_blank" rel="noopener"
             href="https://app.ens.domains/${L.name}"
             aria-label="Open on ENS app">${unsafeHTML(icon.external)}</a>
        </div>
      </header>
    `;
  }

  private _renderStatus(L: NameLookup) {
    const short = (a: string) => !a || a === "0x0000000000000000000000000000000000000000"
      ? "—" : `${a.slice(0, 6)}…${a.slice(-4)}`;
    const bonafide = L.records["bonafide.attestation"];
    return html`
      <div class="status">
        <div class="stat">
          <span class="stat-label">Owner</span>
          <span class="stat-value">
            <a class="rec-link" target="_blank" rel="noopener"
               href="${this.addressExplorerBase}${L.owner}">${short(L.owner)}</a>
          </span>
          <div class="badge-row">
            ${bonafide ? html`<span class="badge badge-info">BONAFIDE</span>` : null}
            ${L.records["mindx.endpoint"] ? html`<span class="badge badge-info">mindX</span>` : null}
            ${L.records["agenticplace.listing"] ? html`<span class="badge badge-info">AgenticPlace</span>` : null}
          </div>
        </div>
        <div class="stat">
          <span class="stat-label">Fuses</span>
          <b-fuse-badges .fuses=${L.fuses}></b-fuse-badges>
        </div>
      </div>
    `;
  }

  private _renderRecords(L: NameLookup) {
    const identity = [
      ["url",          L.records["url"]],
      ["description",  L.records["description"]],
      ["com.twitter",  L.records["com.twitter"]],
      ["com.github",   L.records["com.github"]],
      ["email",        L.records["email"]],
    ] as const;
    const agentic = [
      ["mindx.endpoint",       L.records["mindx.endpoint"]],
      ["agent.capabilities",   L.records["agent.capabilities"]],
      ["bonafide.attestation", L.records["bonafide.attestation"]],
      ["inft.uri",             L.records["inft.uri"]],
      ["x402.endpoint",        L.records["x402.endpoint"]],
      ["algoid.did",           L.records["algoid.did"]],
      ["agenticplace.listing", L.records["agenticplace.listing"]],
    ] as const;

    return html`
      <div class="records-grid">
        ${this._renderSection("Identity", "info",  identity as unknown as ReadonlyArray<readonly [string, string]>)}
        ${this._renderSection("Agentic",  "agent", agentic  as unknown as ReadonlyArray<readonly [string, string]>)}
      </div>
    `;
  }

  private _renderSection(
    title: string,
    iconName: "info" | "agent" | "shield" | "ethereum",
    rows: ReadonlyArray<readonly [string, string]>,
  ) {
    const filled = rows.filter(([, v]) => v && v.length > 0);
    return html`
      <div class="section">
        <p class="section-title">
          <span class="ico">${unsafeHTML(icon[iconName])}</span>
          ${title} · <span style="color:var(--b-color-text-muted);">${filled.length}/${rows.length}</span>
        </p>
        ${rows.map(([k, v]) => html`
          <div class="rec-row">
            <span class="rec-key">${k}</span>
            <span class="rec-val ${v ? "" : "rec-empty"}">${
              !v ? "—" :
              v.startsWith("http") || v.startsWith("ipfs:") || v.startsWith("ar:")
                ? html`<a class="rec-link" target="_blank" rel="noopener" href=${v}>${this._trim(v)}</a>`
                : this._trim(v)
            }</span>
            <button class="ico-btn" @click=${() => this._copy(v)}
              ?hidden=${!v}
              aria-label="Copy ${k}">${unsafeHTML(icon.copy)}</button>
          </div>
        `)}
      </div>
    `;
  }

  private _trim(s: string): string {
    return s.length > 38 ? `${s.slice(0, 26)}…${s.slice(-8)}` : s;
  }

  private _copy(s: string) { if (s) navigator.clipboard?.writeText(s).catch(() => {}); }
}
