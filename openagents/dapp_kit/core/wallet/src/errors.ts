// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// Typed errors raised by @openagents/wallet.
// Contract: docs/services/wallet_connection_as_a_service.md §7.

export class WalletError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "WalletError";
  }
}

/** EIP-6963 discovery returned 0 providers, no window.ethereum. */
export class WalletNotFound extends WalletError {
  constructor() {
    super("No wallet found. Install MetaMask, Coinbase Wallet, or another EIP-6963 provider.");
    this.name = "WalletNotFound";
  }
}

/** User clicked Reject in the wallet popup. */
export class WalletRejected extends WalletError {
  constructor(operation: string) {
    super(`User rejected the ${operation} request.`);
    this.name = "WalletRejected";
  }
}

/** Requested switchChain to a chain the wallet doesn't know. */
export class ChainAddRequired extends WalletError {
  constructor(public chainKey: string) {
    super(`Wallet does not have the ${chainKey} chain. Add it first.`);
    this.name = "ChainAddRequired";
  }
}

/** Signer is on chain A, but the operation requires chain B. */
export class ChainMismatch extends WalletError {
  constructor(public expected: number, public actual: number) {
    super(`Chain mismatch: expected ${expected}, got ${actual}.`);
    this.name = "ChainMismatch";
  }
}

/** Wallet disappeared mid-operation. */
export class ProviderDisconnected extends WalletError {
  constructor() {
    super("Wallet disconnected mid-operation. Reconnect to continue.");
    this.name = "ProviderDisconnected";
  }
}

/** Wallet UI sat idle longer than the configured timeout. */
export class SigningTimeout extends WalletError {
  constructor(public timeoutMs: number) {
    super(`Wallet did not respond within ${timeoutMs}ms.`);
    this.name = "SigningTimeout";
  }
}

/** The dApp asked for a chain not in the catalog. */
export class UnknownChain extends WalletError {
  constructor(public chainKey: string) {
    super(`Unknown chain '${chainKey}'. Add it to CHAINS or pass via extraChains.`);
    this.name = "UnknownChain";
  }
}
