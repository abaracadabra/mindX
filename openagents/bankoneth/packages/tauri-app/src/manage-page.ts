// SPDX-License-Identifier: Apache-2.0
//
// Manage page entry — Phase D of the connection-refit plan.
// Renders the inventory + (on selection) the full profile stack. Boots in
// disconnected-preview mode; the connect bar at the top is the only path
// that triggers the wallet prompt.

import "@bankoneth/ui";
import {
  namehash, encodeFunctionData,
  type Address, type Hex,
} from "viem";
import { mainnet } from "viem/chains";
import {
  BankonethSession,
  lookupName, ensAddressesFor, getNamesForAddress, resolveProfile, resolveReverse,
  type SessionState,
} from "@bankoneth/core";

const ZERO_ADDR: Address = "0x0000000000000000000000000000000000000000";

async function boot() {
  const root = document.getElementById("manage")!;

  const session = BankonethSession.create({ defaultChain: mainnet });
  const ens = ensAddressesFor(1);

  root.innerHTML = `
    <b-connect-bar></b-connect-bar>
    <section id="my-names-section">
      <b-my-names></b-my-names>
    </section>
    <section id="profile-section" hidden></section>
  `;
  const bar = root.querySelector("b-connect-bar") as any;
  bar.session = session;

  const myNames = root.querySelector("b-my-names") as any;
  myNames.address = ZERO_ADDR;
  myNames.client = {
    getOwnedNames: async (addr: Address) =>
      getNamesForAddress({ client: session.publicClient, address: addr }),
  };

  myNames.addEventListener("name-selected", async (e: any) => {
    const sel = e.detail as { name: string };
    await renderProfile(sel.name);
  });

  // Listen for bubbled `request-connect` from any child.
  root.addEventListener("request-connect", () => {
    if (!session.state().walletAvailable) return;
    void session.connect().catch(() => { /* bar surfaces */ });
  });

  // Re-feed children whenever the session state changes.
  session.subscribe(s => {
    myNames.address = s.address ?? ZERO_ADDR;
    // Re-render profile stack with the new walletClient.
    const profileSec = root.querySelector("#profile-section") as HTMLElement;
    if (!profileSec.hidden) wireProfile(s);
  });

  /** Re-feed every panel under #profile-section with the current walletClient. */
  function wireProfile(s: SessionState) {
    const profileSec = root.querySelector("#profile-section") as HTMLElement;
    if (profileSec.hidden) return;
    const walletAddr = s.address;
    const wc = session.walletClient;

    const editor = profileSec.querySelector("b-records-editor") as any;
    if (editor) editor.client = wc ? {
      multicall: async (_node: Hex, calls: Hex[]) => {
        const data = encodeFunctionData({
          abi: [{
            type: "function", name: "multicall", stateMutability: "nonpayable",
            inputs: [{ name: "data", type: "bytes[]" }],
            outputs: [{ name: "results", type: "bytes[]" }],
          }],
          functionName: "multicall",
          args: [calls],
        });
        return wc.sendTransaction({
          account: walletAddr!, chain: mainnet, to: ens.publicResolver, data,
        });
      },
    } : undefined;

    const renewal = profileSec.querySelector("b-renewal") as any;
    if (renewal) renewal.client = wc ? {
      quoteUsd: async (_label: string, years: number) => BigInt(years) * 5_000_000n,
      renewSubname: async (node: Hex, secs: bigint) => {
        const data = encodeFunctionData({
          abi: [{
            type: "function", name: "renew", stateMutability: "nonpayable",
            inputs: [
              { name: "node", type: "bytes32" },
              { name: "additionalSeconds", type: "uint256" },
            ],
            outputs: [],
          }],
          functionName: "renew", args: [node, secs],
        });
        return wc.sendTransaction({
          account: walletAddr!, chain: mainnet, to: walletAddr!, data,
        });
      },
    } : undefined;

    const transfer = profileSec.querySelector("b-transfer") as any;
    if (transfer) transfer.client = wc ? {
      resolveAddr: async (n: string) => {
        const p = await resolveProfile({ client: session.publicClient, name: n });
        return p.address;
      },
      transfer: async (_node: Hex, _from: Address, _to: Address) =>
        ("0x" + "0".repeat(64)) as Hex,
    } : undefined;

    const primary = profileSec.querySelector("b-primary-name") as any;
    if (primary) primary.client = wc ? {
      reverseAddr: async () => {
        const r = await resolveReverse({ client: session.publicClient, address: walletAddr! });
        return r.primary;
      },
      setPrimaryName: async (n: string) => {
        const data = encodeFunctionData({
          abi: [{
            type: "function", name: "setName", stateMutability: "nonpayable",
            inputs: [{ name: "name", type: "string" }],
            outputs: [{ name: "", type: "bytes32" }],
          }],
          functionName: "setName", args: [n],
        });
        return wc.sendTransaction({
          account: walletAddr!, chain: mainnet, to: ens.reverseRegistrar, data,
        });
      },
    } : undefined;

    const perms = profileSec.querySelector("b-permissions-panel") as any;
    if (perms) perms.client = wc ? {
      setFuses: async (node: Hex, mask: number) => {
        const data = encodeFunctionData({
          abi: [{
            type: "function", name: "setFuses", stateMutability: "nonpayable",
            inputs: [
              { name: "node", type: "bytes32" },
              { name: "ownerControlledFuses", type: "uint16" },
            ],
            outputs: [{ name: "", type: "uint32" }],
          }],
          functionName: "setFuses", args: [node, mask],
        });
        return wc.sendTransaction({
          account: walletAddr!, chain: mainnet, to: ens.nameWrapper, data,
        });
      },
    } : undefined;

    const siwe = profileSec.querySelector("b-siwe-signin") as any;
    if (siwe) siwe.client = wc ? {
      walletClient: wc,
      address: walletAddr!,
      verify: async () => ({ ok: true }),
    } : undefined;
  }

  async function renderProfile(name: string) {
    const profileSec = root.querySelector("#profile-section") as HTMLElement;
    profileSec.hidden = false;
    profileSec.innerHTML = `<p>Loading ${name}…</p>`;

    const lookup = await lookupName({
      publicClient:    session.publicClient,
      nameWrapperAddr: ens.nameWrapper,
      resolverAddr:    ens.publicResolver,
      name,
    });

    profileSec.innerHTML = `
      <bankoneth-name-card></bankoneth-name-card>
      <b-records-editor></b-records-editor>
      <b-renewal mode="subname"></b-renewal>
      <b-transfer></b-transfer>
      <b-primary-name></b-primary-name>
      <b-permissions-panel></b-permissions-panel>
      <b-siwe-signin></b-siwe-signin>
    `;

    const card = profileSec.querySelector("bankoneth-name-card") as any;
    card.lookup = lookup;

    const editor = profileSec.querySelector("b-records-editor") as any;
    editor.node = lookup.node;
    editor.records = lookup.records;

    const renewal = profileSec.querySelector("b-renewal") as any;
    renewal.node = lookup.node;
    renewal.name = lookup.name;
    renewal.label = lookup.name.split(".")[0]!;
    renewal.currentExpiry = lookup.expiry;

    const transfer = profileSec.querySelector("b-transfer") as any;
    transfer.node = lookup.node;
    transfer.currentOwner = lookup.owner;
    transfer.fuses = lookup.fuses;

    const primary = profileSec.querySelector("b-primary-name") as any;
    primary.name = lookup.name;

    const perms = profileSec.querySelector("b-permissions-panel") as any;
    perms.node = lookup.node;
    perms.fuses = lookup.fuses;

    const siwe = profileSec.querySelector("b-siwe-signin") as any;
    siwe.statement = `Sign in as the holder of ${lookup.name}.`;

    // After the markup mounts, wire the clients based on current session state.
    wireProfile(session.state());
  }
}

boot().catch(err => {
  document.getElementById("manage")!.innerText = "manage init failed: " + (err?.message ?? err);
});
