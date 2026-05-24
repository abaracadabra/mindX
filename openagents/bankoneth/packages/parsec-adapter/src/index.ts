// SPDX-License-Identifier: Apache-2.0
//
// @bankoneth/parsec-adapter — PARSEC wallet-component bridge.
//
// This package proposes the wallet-component contract for PARSEC. PARSEC's
// wallet UI is built as a shell that loads "components" — feature modules
// that share a lifecycle, surface a tab/route, and emit events the wallet
// shell observes. bankoneth's PARSEC presence is one such component.
//
// The component contract this file declares is *our proposal*; PARSEC adopts
// it (or pushes back, after which this file changes). Until that handshake,
// the contract is whatever this file says.

import type { BankonethClient } from "@bankoneth/core";

/// The PARSEC wallet-component contract bankoneth implements.
///
/// `mount` is called when PARSEC opens the bankoneth tab. The component
/// inserts its UI into the provided element and runs until `unmount` is
/// called.
///
/// `events` is a typed event bus PARSEC listens on to update its own UI
/// (transaction history, network indicator, balance).
export interface ParsecWalletComponent {
  readonly id:    string;          // "bankoneth"
  readonly label: string;          // "bankon.eth"
  readonly icon?: string;          // CSS class or inline SVG

  mount(host: HTMLElement, ctx: ParsecHostContext): void | Promise<void>;
  unmount(): void | Promise<void>;
}

export interface ParsecHostContext {
  readonly chainId:        number;
  readonly accountAddress: `0x${string}`;
  readonly client:         BankonethClient;
  emit(event: ParsecComponentEvent): void;
}

export type ParsecComponentEvent =
  | { kind: "tx:submitted";  hash: `0x${string}`; label?: string }
  | { kind: "tx:confirmed";  hash: `0x${string}` }
  | { kind: "tx:reverted";   hash: `0x${string}`; reason?: string }
  | { kind: "subname:claimed"; label: string; tba?: `0x${string}` }
  | { kind: "domain:purchased"; label: string }
  | { kind: "listing:published"; agenticPlaceId?: string };

/// The exported PARSEC component. PARSEC imports this and registers it once.
export class BankonethComponent implements ParsecWalletComponent {
  readonly id    = "bankoneth";
  readonly label = "bankon.eth";

  private _root: HTMLElement | null = null;
  private _ctx:  ParsecHostContext | null = null;

  async mount(host: HTMLElement, ctx: ParsecHostContext): Promise<void> {
    this._root = host;
    this._ctx  = ctx;
    // Lazy-load the UI bundle. PARSEC's bundler resolves @bankoneth/ui.
    await import("@bankoneth/ui");
    host.innerHTML = `
      <div style="display:grid;gap:16px;max-width:520px;padding:16px">
        <bankoneth-flow-tabs></bankoneth-flow-tabs>
        <bankoneth-claim></bankoneth-claim>
      </div>
    `;
    const claim = host.querySelector("bankoneth-claim") as any;
    if (claim) claim.client = ctx.client;
    host.addEventListener("bankoneth-claim:success", (e: Event) => {
      const ev = e as CustomEvent<{ txHash: `0x${string}` }>;
      ctx.emit({ kind: "tx:submitted", hash: ev.detail.txHash });
    });
  }

  async unmount(): Promise<void> {
    if (this._root) this._root.innerHTML = "";
    this._root = null;
    this._ctx = null;
  }
}

export default BankonethComponent;
