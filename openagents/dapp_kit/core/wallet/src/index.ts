// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
//
// @openagents/wallet — public API.
// Contract: docs/services/wallet_connection_as_a_service.md

export {
  discoverProviders,
  pickProvider,
  type AnnouncedProvider,
  type EIP1193Provider,
  type ProviderInfo,
} from "./eip6963.js";

export {
  connect,
  connectWithProvider,
  switchChain,
  addChain,
  signMessage,
  sendTransaction,
  type ConnectedAccount,
  type ConnectOptions,
} from "./evm.js";

export {
  loadAlgorandAdapter,
  type AlgorandAccount,
} from "./algorand.js";

export {
  CHAINS,
  chainByKey,
  chainById,
  zerogGalileo,
  zerogMainnet,
  algorandMainnet,
  algorandTestnet,
  type ChainEntry,
} from "./chains.js";

export {
  WalletError,
  WalletNotFound,
  WalletRejected,
  ChainAddRequired,
  ChainMismatch,
  ProviderDisconnected,
  SigningTimeout,
  UnknownChain,
} from "./errors.js";
