// SPDX-License-Identifier: Apache-2.0
//
// <b-input> — text/number input with focus ring, validation states, suffix slot.
//
// Slots:
//   - default (leading content, optional)
//   - suffix  (trailing content — typically a fixed `.bankon.eth` label)
//
// States:
//   - default
//   - state="success" (green border)
//   - state="error"   (red border + shake on each new error message)
//
// Events:
//   - input  (CustomEvent<{value: string}>) — fires on every keystroke

import { LitElement, html, css } from "lit";
import { customElement, property, query, state } from "lit/decorators.js";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";

export type InputState = "default" | "success" | "error" | "warning";

@customElement("b-input")
export class BInput extends LitElement {
  static styles = [
    tokens,
    motion.shake,
    css`
      :host { display: block; font-family: var(--b-font-sans); }
      .field {
        display: grid;
        grid-template-columns: auto 1fr auto;
        align-items: center;
        gap: var(--b-space-2);
        padding: var(--b-space-3) var(--b-space-4);
        background: var(--b-color-bg-2);
        border: 1px solid var(--b-color-border);
        border-radius: var(--b-radius-md);
        transition: border var(--b-motion-fast) var(--b-ease-standard),
                    box-shadow var(--b-motion-fast) var(--b-ease-standard),
                    background var(--b-motion-fast) var(--b-ease-standard);
      }
      .field:focus-within {
        border-color: var(--b-color-accent);
        box-shadow: var(--b-shadow-focus);
        background: var(--b-color-bg-3);
      }
      :host([state="success"]) .field { border-color: var(--b-color-success); }
      :host([state="error"])   .field { border-color: var(--b-color-danger); }
      :host([state="warning"]) .field { border-color: var(--b-color-warning); }

      input {
        all: unset;
        font-family: inherit;
        font-size: var(--b-text-md);
        color: var(--b-color-text-primary);
        width: 100%;
        line-height: 1.4;
      }
      input::placeholder { color: var(--b-color-text-muted); }
      input::-webkit-outer-spin-button,
      input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
      input[type=number] { -moz-appearance: textfield; }

      .leading, .suffix {
        display: inline-flex;
        align-items: center;
        color: var(--b-color-text-secondary);
        font-size: var(--b-text-sm);
        white-space: nowrap;
      }
      .suffix { color: var(--b-color-text-muted); font-family: var(--b-font-mono); }

      .label {
        display: block;
        margin-bottom: var(--b-space-2);
        font-size: var(--b-text-sm);
        color: var(--b-color-text-secondary);
        font-weight: var(--b-weight-medium);
      }
      .hint {
        margin-top: var(--b-space-2);
        font-size: var(--b-text-xs);
        color: var(--b-color-text-muted);
        min-height: 1em;
      }
      :host([state="error"])   .hint { color: var(--b-color-danger); }
      :host([state="success"]) .hint { color: var(--b-color-success); }
      :host([state="warning"]) .hint { color: var(--b-color-warning); }

      .shake { animation: b-shake 380ms var(--b-ease-standard); }
    `,
  ];

  @property() label = "";
  @property() placeholder = "";
  @property() value = "";
  @property() type:  "text" | "number" | "email" | "password" = "text";
  @property() hint = "";
  @property({ reflect: true }) state: InputState = "default";
  @property({ type: Number }) min?: number;
  @property({ type: Number }) max?: number;
  @property() inputId = "";
  @property() autocomplete = "off";
  @property({ type: Boolean }) disabled = false;

  @state() private _shake = false;
  @query("input") private _input!: HTMLInputElement;

  /** Programmatic focus — useful for the carousel auto-focus on step change. */
  override focus() { this._input?.focus(); }

  willUpdate(changed: Map<string, unknown>) {
    if (changed.has("state") && this.state === "error") {
      this._shake = true;
      setTimeout(() => { this._shake = false; this.requestUpdate(); }, 400);
    }
  }

  private _onInput(e: Event) {
    const v = (e.target as HTMLInputElement).value;
    this.value = v;
    this.dispatchEvent(new CustomEvent("input", { detail: { value: v }, bubbles: true, composed: true }));
  }

  render() {
    return html`
      ${this.label ? html`<label class="label" for=${this.inputId || "b-input"}>${this.label}</label>` : null}
      <div class="field ${this._shake ? "shake" : ""}">
        <span class="leading"><slot name="leading"></slot></span>
        <input
          id=${this.inputId || "b-input"}
          .value=${this.value}
          .type=${this.type}
          placeholder=${this.placeholder}
          autocomplete=${this.autocomplete}
          ?disabled=${this.disabled}
          min=${this.min as unknown as string}
          max=${this.max as unknown as string}
          aria-invalid=${this.state === "error" ? "true" : "false"}
          aria-describedby=${this.hint ? "b-input-hint" : ""}
          @input=${this._onInput}
        />
        <span class="suffix"><slot name="suffix"></slot></span>
      </div>
      <div id="b-input-hint" class="hint" aria-live="polite">${this.hint}</div>
    `;
  }
}
