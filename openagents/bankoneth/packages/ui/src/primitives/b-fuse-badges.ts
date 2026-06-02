// SPDX-License-Identifier: Apache-2.0
//
// <b-fuse-badges> — compact row of NameWrapper fuse pills.
//
// Visualises which fuses are burned on a wrapped ENS name. Each pill is
// either active (burned, colored) or inactive (greyed out). Hovering shows
// the full fuse name + description.
//
// ENS's official UI lists fuses as plain-text rows; this is denser and
// scannable at a glance.

import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";

import { tokens } from "../tokens/tokens";
import { motion } from "../tokens/motion";
import { icon } from "../tokens/icons";
import { FUSE, hasFuse, type FuseName } from "@bankoneth/core";

interface FuseSpec {
  name:  FuseName;
  short: string;       // 3-4 char chip label
  long:  string;       // hover tooltip
  ico:   keyof typeof icon;
}

const FUSE_SPECS: FuseSpec[] = [
  { name: "PARENT_CANNOT_CONTROL", short: "PCC",  long: "Parent cannot control",        ico: "shield" },
  { name: "CANNOT_UNWRAP",         short: "CUN",  long: "Cannot unwrap",                ico: "shield" },
  { name: "CANNOT_TRANSFER",       short: "CTX",  long: "Cannot transfer (soulbound)",  ico: "flame"  },
  { name: "CAN_EXTEND_EXPIRY",     short: "CEX",  long: "Owner can extend expiry",      ico: "clock"  },
  { name: "CANNOT_SET_RESOLVER",   short: "CSR",  long: "Resolver locked",              ico: "shield" },
  { name: "CANNOT_BURN_FUSES",     short: "CBF",  long: "Fuse-bitmap locked",           ico: "shield" },
  { name: "CANNOT_CREATE_SUBDOMAIN", short: "CCS", long: "No further subdomains",       ico: "shield" },
  { name: "CANNOT_APPROVE",        short: "CAP",  long: "ERC-1155 approval locked",     ico: "shield" },
];

@customElement("b-fuse-badges")
export class BFuseBadges extends LitElement {
  static styles = [
    tokens,
    motion.fadeIn,
    motion.stagger,
    css`
      :host { display: block; font-family: var(--b-font-sans); }
      .row { display: flex; flex-wrap: wrap; gap: var(--b-space-1); }
      .pill {
        display: inline-flex; align-items: center; gap: 4px;
        padding: 3px 8px;
        border-radius: var(--b-radius-full);
        font-size: 10px;
        font-weight: var(--b-weight-semibold);
        font-family: var(--b-font-mono);
        letter-spacing: 0.04em;
        text-transform: uppercase;
        border: 1px solid transparent;
        position: relative;
      }
      .pill .ico { font-size: 11px; display: inline-flex; line-height: 0; }
      .on {
        background: var(--b-color-success-faded);
        color: var(--b-color-success);
        border-color: color-mix(in srgb, var(--b-color-success) 35%, transparent);
      }
      .off {
        background: transparent;
        color: var(--b-color-text-muted);
        border-color: var(--b-color-border);
        opacity: 0.55;
      }
      .pill[title]:hover::after {
        content: attr(title);
        position: absolute;
        bottom: calc(100% + 6px); left: 50%;
        transform: translateX(-50%);
        white-space: nowrap;
        background: var(--b-color-bg-3);
        color: var(--b-color-text-primary);
        padding: var(--b-space-1) var(--b-space-2);
        border-radius: var(--b-radius-sm);
        font-size: var(--b-text-xs);
        font-family: var(--b-font-sans);
        font-weight: var(--b-weight-regular);
        text-transform: none;
        letter-spacing: 0;
        pointer-events: none;
        z-index: var(--b-z-overlay);
      }
    `,
  ];

  @property({ type: Number }) fuses = 0;
  /** Show all 8 fuses (true) or only the 4 soulbound ones (false). */
  @property({ type: Boolean }) all = false;

  render() {
    const specs = this.all ? FUSE_SPECS : FUSE_SPECS.slice(0, 4);
    return html`
      <div class="row b-fade-in" role="list" aria-label="ENS NameWrapper fuses">
        ${specs.map((s, i) => {
          const on = hasFuse({ fuses: this.fuses }, s.name);
          return html`
            <span class="pill ${on ? "on" : "off"} b-stagger"
                  style="--b-stagger-i: ${i};"
                  role="listitem"
                  title="${s.long} (${on ? "burned" : "not burned"})">
              <span class="ico">${unsafeHTML(icon[s.ico])}</span>
              ${s.short}
            </span>
          `;
        })}
      </div>
    `;
  }
}
