// SPDX-License-Identifier: Apache-2.0
//
// <b-availability-pill> — UX win #2.
//
// Sits beside the label input on the search step. Cycles through four states:
//   - idle    : empty / before user has typed
//   - checking: animated spinner + "Checking…"
//   - free    : ✓ in green pill, label.bankon.eth + "available"
//   - taken   : × in red pill, "taken by 0x…"
//
// Beats parsec-wallet's text-only "checking…" on the confirm screen — here
// it's right next to the input, with a satisfying spinner→checkmark
// transition driven by the spring easing.

import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";
import { icon } from "../tokens/icons";

export type AvailabilityState = "idle" | "checking" | "free" | "taken" | "error";

@customElement("b-availability-pill")
export class BAvailabilityPill extends LitElement {
  static styles = [
    tokens,
    motion.spin,
    motion.pop,
    motion.fadeIn,
    css`
      :host {
        display: inline-block;
        font-family: var(--b-font-sans);
        min-height: 28px;
      }
      .pill {
        display: inline-flex;
        align-items: center;
        gap: var(--b-space-2);
        padding: var(--b-space-1) var(--b-space-3);
        font-size: var(--b-text-xs);
        font-weight: var(--b-weight-medium);
        border-radius: var(--b-radius-full);
        line-height: 1;
        transition: background var(--b-motion-base) var(--b-ease-standard),
                    color      var(--b-motion-base) var(--b-ease-standard);
      }
      :host([state="idle"])     .pill { background: var(--b-color-bg-3); color: var(--b-color-text-muted); }
      :host([state="checking"]) .pill { background: var(--b-color-bg-3); color: var(--b-color-text-secondary); }
      :host([state="free"])     .pill { background: var(--b-color-success-faded); color: var(--b-color-success); }
      :host([state="taken"])    .pill { background: var(--b-color-danger-faded);  color: var(--b-color-danger); }
      :host([state="error"])    .pill { background: var(--b-color-bg-3); color: var(--b-color-warning); }

      .ico  { display: inline-flex; line-height: 0; font-size: 1.1em; }
      .free, .taken { animation: b-pop var(--b-motion-base) var(--b-ease-spring); }
      .spin { display: inline-flex; line-height: 0; font-size: 1.1em; }
    `,
  ];

  @property({ reflect: true }) state: AvailabilityState = "idle";
  /** When state = "taken", who owns it. Truncated for display. */
  @property() ownerLabel = "";
  /** Optional explanatory label (e.g. the resolved label for ".bankon.eth"). */
  @property() suffix = "";

  render() {
    switch (this.state) {
      case "idle":
        return html`<span class="pill"><span class="ico">${unsafeHTML(icon.search)}</span>type to check</span>`;
      case "checking":
        return html`<span class="pill"><span class="spin b-spin">${unsafeHTML(icon.spinner)}</span>checking…</span>`;
      case "free":
        return html`<span class="pill free"><span class="ico">${unsafeHTML(icon.check)}</span>available${this.suffix ? html` · ${this.suffix}` : null}</span>`;
      case "taken":
        return html`<span class="pill taken"><span class="ico">${unsafeHTML(icon.cross)}</span>taken${this.ownerLabel ? html` · ${this.ownerLabel}` : null}</span>`;
      case "error":
        return html`<span class="pill"><span class="ico">${unsafeHTML(icon.warn)}</span>check failed — retrying</span>`;
    }
  }
}
