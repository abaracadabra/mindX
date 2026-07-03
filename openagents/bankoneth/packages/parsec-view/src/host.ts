// SPDX-License-Identifier: Apache-2.0
//
// host.ts — the seam between this package and parsec-wallet. The view factory
// (bankon-deploy.ts) renders entirely through these helpers, so when parsec
// passes in its own `el`/`btn`/`input`/`toast`/`store` the result IS a native
// parsec view (Blueprint classes, parsec router, parsec toasts) — no Lit, no
// iframe. Any other host (a test harness, another wallet) can implement the
// same shape. This mirrors parsec-wallet/src/lib/dom.ts + store.ts.

import type { ethers as Ethers } from "ethers";

export interface ElOpts {
  cls?: string;
  attrs?: Record<string, string>;
  text?: string;
  html?: string;
  children?: (HTMLElement | string)[];
  onClick?: (e: Event) => void;
}

export interface BtnOpts {
  intent?: "primary" | "success" | "warning" | "danger" | "none";
  large?: boolean;
  minimal?: boolean;
  outlined?: boolean;
  icon?: string;
  cls?: string;
  disabled?: boolean;
  onClick?: (e: Event) => void;
}

export interface InputOpts {
  type?: string;
  placeholder?: string;
  cls?: string;
  value?: string;
  onInput?: (value: string) => void;
  onEnter?: (value: string) => void;
}

export type ToastIntent = "success" | "danger" | "warning" | "primary";

/** EIP-1193 provider — parsec's xchain-connect exposes window.ethereum. */
export interface Eip1193 {
  request(args: { method: string; params?: unknown[] }): Promise<unknown>;
  on?(event: string, handler: (...a: unknown[]) => void): void;
}

export interface ParsecHost {
  el(tag: string, opts?: ElOpts): HTMLElement;
  btn(label: string, opts?: BtnOpts): HTMLButtonElement;
  input(opts: InputOpts): HTMLInputElement;
  toast(message: string, intent?: ToastIntent): void;
  /** Navigate parsec's router (e.g. back to 'dashboard'). Optional. */
  navigate?(view: string): void;
  /** The connected account address, if parsec already has one. */
  account?: string | null;
  /** Acquire the EVM provider. Parsec wires this to its MetaMask bridge
   *  (src/views/xchain-connect.ts). Falls back to window.ethereum. */
  getEvmProvider(): Promise<Eip1193 | null>;
  ethers: typeof Ethers;
  /** URL of the served packages/web/public dir (manifest + abis + deployments). */
  publicBase: string;
}
