// SPDX-License-Identifier: Apache-2.0
//
// <b-button> — the only button bankoneth uses.
//
// Variants:
//   - primary  (default) — solid accent fill
//   - secondary          — outlined
//   - ghost              — transparent, accent text
//   - danger             — solid danger fill
// Sizes:
//   - sm | md (default) | lg
//
// Behaviour:
//   - ripple on press (parsec doesn't have this)
//   - spring-back transform on :active (token --b-ease-spring)
//   - loading state (replaces label with spinner; click no-ops)
//   - icon-only mode via the `icon-only` attribute (sets square padding + aspect)

import { LitElement, html, css } from "lit";
import { customElement, property, query, state } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";
import { icon } from "../tokens/icons";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize    = "sm" | "md" | "lg";

@customElement("b-button")
export class BButton extends LitElement {
  static styles = [
    tokens,
    motion.ripple,
    motion.springPress,
    motion.spin,
    css`
      :host {
        display: inline-block;
        font-family: var(--b-font-sans);
      }
      :host([block]) { display: block; }
      :host([block]) button { width: 100%; }

      button {
        position: relative;
        overflow: hidden;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: var(--b-space-2);
        padding: var(--_pad);
        border: 1px solid var(--_border);
        border-radius: var(--b-radius-md);
        background: var(--_bg);
        color: var(--_fg);
        font-size: var(--_text);
        font-weight: var(--b-weight-semibold);
        font-family: inherit;
        line-height: 1;
        cursor: pointer;
        user-select: none;
        white-space: nowrap;
        transition: background var(--b-motion-fast) var(--b-ease-standard),
                    color      var(--b-motion-fast) var(--b-ease-standard),
                    border     var(--b-motion-fast) var(--b-ease-standard),
                    transform  var(--b-motion-fast) var(--b-ease-spring),
                    box-shadow var(--b-motion-fast) var(--b-ease-standard);
      }
      button:hover:not(:disabled)  { background: var(--_bg-hover); }
      button:focus-visible         { outline: none; box-shadow: var(--b-shadow-focus); }
      button:active:not(:disabled) { transform: scale(0.97); }
      button:disabled              { opacity: 0.55; cursor: not-allowed; }

      /* Size tokens */
      :host([size="sm"]) button { --_pad: var(--b-space-2) var(--b-space-3); --_text: var(--b-text-xs); }
      :host                     button { --_pad: var(--b-space-3) var(--b-space-5); --_text: var(--b-text-sm); }
      :host([size="lg"]) button { --_pad: var(--b-space-4) var(--b-space-6); --_text: var(--b-text-md); }
      :host([icon-only]) button { padding: var(--b-space-2); aspect-ratio: 1; }

      /* Variants — primary by default */
      :host                       button { --_bg: var(--b-color-accent);
                                           --_bg-hover: color-mix(in srgb, var(--b-color-accent) 88%, white);
                                           --_fg: white;
                                           --_border: var(--b-color-accent); }
      :host([variant="secondary"]) button {
                                           --_bg: transparent;
                                           --_bg-hover: var(--b-color-accent-faded);
                                           --_fg: var(--b-color-text-primary);
                                           --_border: var(--b-color-border-strong); }
      :host([variant="ghost"]) button {
                                           --_bg: transparent;
                                           --_bg-hover: var(--b-color-accent-faded);
                                           --_fg: var(--b-color-accent);
                                           --_border: transparent; }
      :host([variant="danger"]) button {
                                           --_bg: var(--b-color-danger);
                                           --_bg-hover: color-mix(in srgb, var(--b-color-danger) 88%, white);
                                           --_fg: white;
                                           --_border: var(--b-color-danger); }

      .ico  { display: inline-flex; font-size: 1.1em; line-height: 0; }
      .spin { display: inline-flex; font-size: 1.15em; line-height: 0; }
      .label { display: inline-flex; align-items: center; gap: var(--b-space-2); }
    `,
  ];

  @property({ reflect: true }) variant: ButtonVariant = "primary";
  @property({ reflect: true }) size:    ButtonSize    = "md";
  @property({ type: Boolean, reflect: true }) block = false;
  @property({ type: Boolean, reflect: true }) disabled = false;
  @property({ type: Boolean, reflect: true }) loading  = false;
  /** Optional left icon — name from the icon set. */
  @property() leadingIcon  = "";
  @property() trailingIcon = "";

  @query("button") private _btn!: HTMLButtonElement;

  private _onPointerDown(e: PointerEvent) {
    if (this.disabled || this.loading) return;
    const r = this._btn.getBoundingClientRect();
    const size = Math.max(r.width, r.height);
    const x = e.clientX - r.left - size / 2;
    const y = e.clientY - r.top  - size / 2;
    const ripple = document.createElement("span");
    ripple.className = "b-ripple";
    ripple.style.width = ripple.style.height = `${size}px`;
    ripple.style.left = `${x}px`;
    ripple.style.top  = `${y}px`;
    this._btn.appendChild(ripple);
    setTimeout(() => ripple.remove(), 650);
  }

  private _onClick(e: Event) {
    if (this.disabled || this.loading) {
      e.preventDefault(); e.stopPropagation();
    }
  }

  render() {
    const leading  = this.leadingIcon  && (icon as Record<string, string>)[this.leadingIcon];
    const trailing = this.trailingIcon && (icon as Record<string, string>)[this.trailingIcon];

    return html`
      <button
        ?disabled=${this.disabled || this.loading}
        @pointerdown=${this._onPointerDown}
        @click=${this._onClick}
      >
        ${this.loading
          ? html`<span class="spin b-spin">${unsafeHTML(icon.spinner)}</span>`
          : leading ? html`<span class="ico">${unsafeHTML(leading)}</span>` : null}
        <span class="label"><slot></slot></span>
        ${!this.loading && trailing
          ? html`<span class="ico">${unsafeHTML(trailing)}</span>`
          : null}
      </button>
    `;
  }
}
