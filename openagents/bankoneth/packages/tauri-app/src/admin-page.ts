// SPDX-License-Identifier: Apache-2.0
//
// Admin page entry — Phase E. Renders the contract-naming inspector
// against the four bankoneth registrar contracts. Read-only; no wallet
// required (uses the session's publicClient).

import "@bankoneth/ui";
import { mainnet } from "viem/chains";
import {
  BankonethSession,
  type BankonethAddresses,
} from "@bankoneth/core";
import type { ContractRow } from "@bankoneth/ui";

import addressesJson from "./addresses.local.json";

async function boot() {
  const root = document.getElementById("admin")!;
  const session = BankonethSession.create({ defaultChain: mainnet });

  root.innerHTML = `
    <b-connect-bar></b-connect-bar>
    <section>
      <b-contract-name-status></b-contract-name-status>
    </section>
  `;
  const bar = root.querySelector("b-connect-bar") as any;
  bar.session = session;

  const addresses = addressesJson as BankonethAddresses;

  // The four canonical reverse-name targets from script/SetPrimaryNames.s.sol.
  const rows: ContractRow[] = [
    { address: addresses.subnameRegistrar, expectedName: "registrar.bankon.eth",     label: "BankonSubnameRegistrar" },
    { address: addresses.ethRegistrar,     expectedName: "eth-registrar.bankon.eth", label: "BankonEthRegistrar"     },
    { address: addresses.domainHosting,    expectedName: "host.bankon.eth",          label: "BankonDomainHosting"    },
  ];
  // BankonOffchainRegistrar isn't in the legacy addresses interface yet;
  // when ops adds it to addresses.local.json, append:
  //   { address: addresses.offchainRegistrar, expectedName: "offchain.bankon.eth", … }

  const inspector = root.querySelector("b-contract-name-status") as any;
  inspector.client = session.publicClient;
  inspector.contracts = rows;

  // Re-audit when the connect bar surfaces a chain switch — the canonical
  // ENS addresses differ on Sepolia vs mainnet.
  session.subscribe(() => {
    inspector.client = session.publicClient;
  });

  // request-connect bubbling — same handler as main.ts / manage-page.ts.
  root.addEventListener("request-connect", () => {
    if (!session.state().walletAvailable) return;
    void session.connect().catch(() => {});
  });
}

boot().catch(err => {
  document.getElementById("admin")!.innerText = "admin init failed: " + (err?.message ?? err);
});
