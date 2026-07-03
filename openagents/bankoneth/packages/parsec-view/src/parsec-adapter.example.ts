// SPDX-License-Identifier: Apache-2.0
//
// parsec-adapter.example.ts — copy this into parsec-wallet/src/views/ as
// `bankon-deploy.ts`. It is the ~15-line glue that wires parsec's real
// dom/store/wallet into the @bankoneth/parsec-view factory. The imports below
// resolve inside parsec-wallet (not in this package), so this file is an
// EXAMPLE here — it intentionally does not typecheck against this repo.
//
// Register it in parsec-wallet/src/main.ts:
//   registerView('bankon-deploy',
//     lazyView(async () => (await import('./views/bankon-deploy')).bankonDeployView));
// and reach it from the dashboard with:  store.navigate('bankon-deploy')
//
// @ts-nocheck
import { el, btn, input, toast } from "../lib/dom";
import { store, getAccountAddress } from "../lib/store";
import { ethers } from "ethers";
import { createBankonDeployView } from "@bankoneth/parsec-view";

export function bankonDeployView(): HTMLElement {
  const state = store.get();
  const account = state.accounts[state.activeAccountIndex];

  const view = createBankonDeployView({
    el, btn, input, toast,
    navigate: (v) => store.navigate(v as never),
    // EVM address for the active account, if parsec already derived one.
    account: account ? getAccountAddress(account, 1) ?? null : null,
    // Parsec's MetaMask bridge lives in src/views/xchain-connect.ts; in the
    // browser/Tauri webview window.ethereum is the injected EVM provider.
    getEvmProvider: async () => (window as unknown as { ethereum?: unknown }).ethereum ?? null,
    ethers,
    // Served alongside the parsec app (copy packages/web/public/* into
    // parsec-wallet/public/bankon/ and point here):
    publicBase: "/bankon",
  });

  return view.render();
}
