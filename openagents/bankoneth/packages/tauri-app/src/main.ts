// SPDX-License-Identifier: Apache-2.0
//
// bankoneth reference dApp entry point. Renders the three flows.

import "@bankoneth/ui";
import { createPublicClient, createWalletClient, http, namehash, custom } from "viem";
import { mainnet } from "viem/chains";
import { BankonethClient, type BankonethAddresses } from "@bankoneth/core";

import addressesJson from "./addresses.local.json";

const eth = (window as any).ethereum;

async function boot() {
  if (!eth) {
    document.getElementById("app")!.innerHTML =
      "<p>No injected wallet found. Install MetaMask or Rabby to use this dApp.</p>";
    return;
  }
  await eth.request({ method: "eth_requestAccounts" });
  const publicClient = createPublicClient({ chain: mainnet, transport: http() });
  const walletClient = createWalletClient({ chain: mainnet, transport: custom(eth) });
  const account = (await walletClient.getAddresses())[0];

  const addresses = addressesJson as BankonethAddresses;
  const client = new BankonethClient(
    publicClient,
    Object.assign(walletClient, { account: { address: account, type: "json-rpc" } } as any),
    addresses,
    namehash("bankon.eth"),
  );

  const app = document.getElementById("app")!;
  app.innerHTML = `
    <bankoneth-flow-tabs></bankoneth-flow-tabs>
    <div id="flow-A"><bankoneth-claim></bankoneth-claim></div>
    <div id="flow-B" hidden><bankoneth-purchase></bankoneth-purchase></div>
    <div id="flow-C" hidden><bankoneth-host></bankoneth-host></div>
  `;

  for (const id of ["flow-A", "flow-B", "flow-C"]) {
    const root = document.getElementById(id)!;
    const child = root.firstElementChild as any;
    if (child) child.client = client;
  }

  document.querySelector("bankoneth-flow-tabs")!.addEventListener("change", (e: any) => {
    const sel = e.detail.selected;
    document.getElementById("flow-A")!.hidden = sel !== "subname";
    document.getElementById("flow-B")!.hidden = sel !== "purchase";
    document.getElementById("flow-C")!.hidden = sel !== "host";
  });
}

boot().catch(err => {
  document.getElementById("app")!.innerText = "init failed: " + err.message;
});
