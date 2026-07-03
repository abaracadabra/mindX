// SPDX-License-Identifier: Apache-2.0
//
// chains.js — backward-compatible re-export. The canonical registry now lives in
// bankonchains/ (chain registry + chainid.network extensibility + CoinMarketCap price
// handling). Existing imports (`./chains.js`, `../chains.js`) keep working.
export * from "./bankonchains/chains.js";
