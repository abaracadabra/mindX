// SPDX-License-Identifier: Apache-2.0
//
// bankoneth reference dApp entry point — Phase D of the connection-refit
// plan. Renders the three flows in a disconnected-preview-by-default mode;
// the connect bar at the top is the only path that prompts the wallet.

import "@bankoneth/ui";
import { namehash } from "viem";
import { mainnet } from "viem/chains";
import {
  BankonethClient,
  BankonethSession,
  type BankonethAddresses,
  type SessionState,
} from "@bankoneth/core";

import addressesJson from "./addresses.local.json";

async function boot() {
  const root = document.getElementById("app")!;

  // 1. Always create the session. publicClient is always available;
  //    walletClient is null until session.connect() succeeds.
  const session = BankonethSession.create({ defaultChain: mainnet });

  // 2. Render shell with the persistent connect bar at the top.
  root.innerHTML = `
    <b-connect-bar></b-connect-bar>
    <bankoneth-flow-tabs></bankoneth-flow-tabs>
    <div id="flow-A"><bankoneth-claim></bankoneth-claim></div>
    <div id="flow-B" hidden><bankoneth-purchase></bankoneth-purchase></div>
    <div id="flow-C" hidden><bankoneth-host></bankoneth-host></div>
  `;
  const bar = root.querySelector("b-connect-bar") as any;
  bar.session = session;

  const addresses = addressesJson as BankonethAddresses;
  const bankonNode = namehash("bankon.eth");

  // Pin a builder so the flows always have an up-to-date BankonethClient,
  // rebuilt each time the session walletClient changes.
  function buildClient(): BankonethClient {
    return new BankonethClient(
      session.publicClient,
      session.walletClient ?? undefined,
      addresses,
      bankonNode,
    );
  }

  function distributeClient() {
    const client = buildClient();
    for (const id of ["flow-A", "flow-B", "flow-C"]) {
      const child = root.querySelector(`#${id} > :first-child`) as any;
      if (child) child.client = client;
    }
  }

  distributeClient();
  session.subscribe(distributeClient);

  // 3. Tab switching.
  root.querySelector("bankoneth-flow-tabs")!.addEventListener("change", (e: any) => {
    const sel = e.detail.selected;
    root.querySelector<HTMLDivElement>("#flow-A")!.hidden = sel !== "subname";
    root.querySelector<HTMLDivElement>("#flow-B")!.hidden = sel !== "purchase";
    root.querySelector<HTMLDivElement>("#flow-C")!.hidden = sel !== "host";
  });

  // 4. Any child that dispatches `request-connect` triggers the wallet
  //    prompt. The bar's own button does the same thing internally.
  root.addEventListener("request-connect", () => {
    if (!session.state().walletAvailable) {
      // The bar's no-extension banner already explains how to install one.
      return;
    }
    void session.connect().catch(() => { /* bar surfaces the error */ });
  });
}

boot().catch(err => {
  document.getElementById("app")!.innerText = "init failed: " + (err?.message ?? err);
});
