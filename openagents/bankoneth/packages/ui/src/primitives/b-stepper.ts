// SPDX-License-Identifier: Apache-2.0
//
// <b-stepper> — the carousel that drives the hero flows (search → review → sign → success).
//
// Children are rendered as separate `<section data-step>` panels inside the
// default slot. Navigation is keyboard-driven (arrow keys, Enter) and
// programmatic via next() / back() / goto(i).
//
// Visual: a sticky progress-dots bar at the top, animated active dot,
// labelled chips inside (search / review / sign / success). Smooth cross-fade
// between panels — beats parsec-wallet's hard tab switches.

import { LitElement, html, css } from "lit";
import { customElement, property, state, queryAssignedElements } from "lit/decorators.js";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";

@customElement("b-stepper")
export class BStepper extends LitElement {
  static styles = [
    tokens,
    motion.fadeIn,
    motion.slideUp,
    css`
      :host { display: block; font-family: var(--b-font-sans); }

      .progress {
        position: sticky;
        top: 0;
        z-index: var(--b-z-sticky);
        display: flex;
        align-items: center;
        justify-content: center;
        gap: var(--b-space-3);
        padding: var(--b-space-3) var(--b-space-4);
        background: color-mix(in srgb, var(--b-color-bg-1) 92%, transparent);
        border-bottom: 1px solid var(--b-color-border);
        backdrop-filter: blur(8px);
      }
      .step-dot {
        display: inline-flex;
        align-items: center;
        gap: var(--b-space-2);
        padding: var(--b-space-1) var(--b-space-3);
        font-size: var(--b-text-xs);
        font-weight: var(--b-weight-medium);
        color: var(--b-color-text-muted);
        border-radius: var(--b-radius-full);
        background: transparent;
        cursor: pointer;
        border: 0;
        transition: color var(--b-motion-fast) var(--b-ease-standard),
                    background var(--b-motion-fast) var(--b-ease-standard);
      }
      .step-dot[data-active] {
        color: var(--b-color-accent);
        background: var(--b-color-accent-faded);
      }
      .step-dot[data-done] { color: var(--b-color-success); }
      .step-dot:disabled   { cursor: not-allowed; opacity: 0.5; }

      .dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        background: currentColor;
        opacity: 0.7;
        transition: transform var(--b-motion-fast) var(--b-ease-spring);
      }
      .step-dot[data-active] .dot { transform: scale(1.25); opacity: 1; }

      .stage {
        position: relative;
        padding: var(--b-space-6) 0 var(--b-space-4);
        min-height: 240px;
      }
      ::slotted([data-step]) {
        display: none;
      }
      ::slotted([data-step][data-active]) {
        display: block;
        animation: b-slide-up var(--b-motion-base) var(--b-ease-decel) both;
      }
    `,
  ];

  /** Names shown beside each step dot. Length should match the # of slotted panels. */
  @property({ type: Array }) steps: string[] = [];

  @state() private _index = 0;

  @queryAssignedElements({ selector: "[data-step]" }) private _panels!: HTMLElement[];

  private _syncActive() {
    this._panels.forEach((p, i) => {
      if (i === this._index) p.setAttribute("data-active", "");
      else p.removeAttribute("data-active");
    });
  }

  private _emitChange() {
    this.dispatchEvent(new CustomEvent("b-step", {
      detail: { index: this._index, name: this.steps[this._index] ?? "" },
      bubbles: true, composed: true,
    }));
  }

  /** Move forward one step. */
  next() {
    if (this._index >= this._panels.length - 1) return;
    this._index += 1;
    this._syncActive();
    this._emitChange();
    this.requestUpdate();
  }

  /** Move backward one step. */
  back() {
    if (this._index === 0) return;
    this._index -= 1;
    this._syncActive();
    this._emitChange();
    this.requestUpdate();
  }

  /** Jump to an arbitrary step. */
  goto(i: number) {
    if (i < 0 || i >= this._panels.length) return;
    this._index = i;
    this._syncActive();
    this._emitChange();
    this.requestUpdate();
  }

  /** Current step index — read-only for consumers. */
  get index() { return this._index; }

  firstUpdated() { queueMicrotask(() => this._syncActive()); }

  private _onKeydown(e: KeyboardEvent) {
    if (e.key === "ArrowRight") { this.next(); e.preventDefault(); }
    else if (e.key === "ArrowLeft") { this.back(); e.preventDefault(); }
  }

  render() {
    const total = Math.max(this.steps.length, 1);
    return html`
      <div class="progress" role="tablist" aria-label="Step progress">
        ${this.steps.map((label, i) => html`
          <button
            class="step-dot"
            role="tab"
            aria-selected=${i === this._index ? "true" : "false"}
            ?data-active=${i === this._index}
            ?data-done=${i < this._index}
            ?disabled=${i > this._index}
            @click=${() => this.goto(i)}
          >
            <span class="dot"></span>
            <span>${i + 1}/${total} · ${label}</span>
          </button>
        `)}
      </div>
      <div class="stage" @keydown=${this._onKeydown}>
        <slot @slotchange=${() => this._syncActive()}></slot>
      </div>
    `;
  }
}
