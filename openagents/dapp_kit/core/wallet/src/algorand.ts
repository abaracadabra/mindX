// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// Algorand adapter slot. Optional — requires @txnlab/use-wallet at the
// consumer dApp level. EVM dApps incur zero Algorand cost at install time.
//
// Contract: docs/services/wallet_connection_as_a_service.md §5.1.

import type { ChainEntry } from "./chains.js";

export interface AlgorandAccount {
  /** 58-char base32 Algorand address. */
  address: string;
  chainId: number; // synthetic EIP-155 id from chains.ts (416001 / 416002)
  /**
   * Sign an arbitrary message (UTF-8 string). Returns the Ed25519
   * signature as a hex string. The adapter delegates to the underlying
   * wallet (Pera, Defly, Exodus).
   */
  signMessage(message: string): Promise<string>;
  /**
   * Sign and submit a pre-built unsigned transaction blob (base64 msgpack).
   * Returns the txid on confirmation.
   */
  signAndSubmit(unsignedTxnBase64: string): Promise<string>;
}

/**
 * Lazy-import the Algorand adapter implementation, when @txnlab/use-wallet
 * is available in the consumer's node_modules. Returns null when the dep
 * is not present (EVM-only dApps).
 *
 * @example
 *   const algo = await loadAlgorandAdapter('algorand-testnet');
 *   if (!algo) {
 *     // tell the user: "Install @txnlab/use-wallet to support Algorand"
 *   }
 */
export async function loadAlgorandAdapter(
  chain: ChainEntry,
): Promise<AlgorandAccount | null> {
  if (!chain.isAlgorand) return null;
  try {
    // The actual @txnlab/use-wallet client is constructed by the consumer dApp
    // (it needs framework-specific bindings — react, lit, vanilla). This
    // adapter slot just makes sure consumers can import it without breaking
    // when the dep is absent.
    const mod = await dynamicImport("@txnlab/use-wallet");
    if (!mod) return null;
    // The real binding is the consumer's responsibility; we return null here
    // to signal "you have to wire @txnlab/use-wallet yourself." This keeps
    // the kit honest about not silently doing wallet work that needs UI.
    return null;
  } catch {
    return null;
  }
}

/**
 * Indirected dynamic import so bundlers that statically analyze imports
 * don't choke on the optional peer dep.
 */
async function dynamicImport(spec: string): Promise<unknown> {
  try {
    // eslint-disable-next-line @typescript-eslint/no-implied-eval
    return await new Function("s", "return import(s)")(spec);
  } catch {
    return null;
  }
}
