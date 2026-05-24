// SPDX-License-Identifier: Apache-2.0
//
// Manage page entry — Phase 3.8. Renders the inventory dashboard and (on
// selection) the full profile stack: name card + the six v2 manage panels
// (records / renewal / transfer / primary / permissions / siwe).

import "@bankoneth/ui";
import {
  createPublicClient, createWalletClient, http, namehash, custom, encodeFunctionData,
  type Address, type Hex,
} from "viem";
import { mainnet } from "viem/chains";
import {
  lookupName, ensAddressesFor, getNamesForAddress, resolveProfile, resolveReverse,
  type NameLookup,
} from "@bankoneth/core";

const eth = (window as any).ethereum;

async function boot() {
  if (!eth) {
    document.getElementById("manage")!.innerHTML =
      "<p>No injected wallet found.</p>";
    return;
  }
  await eth.request({ method: "eth_requestAccounts" });
  const publicClient = createPublicClient({ chain: mainnet, transport: http() });
  const walletClient = createWalletClient({ chain: mainnet, transport: custom(eth) });
  const account = (await walletClient.getAddresses())[0] as Address;
  const ens = ensAddressesFor(1);

  const root = document.getElementById("manage")!;
  root.innerHTML = `
    <section id="my-names-section">
      <b-my-names></b-my-names>
    </section>
    <section id="profile-section" hidden></section>
  `;

  const myNames = root.querySelector("b-my-names") as any;
  myNames.address = account;
  myNames.client = {
    getOwnedNames: async (addr: Address) => getNamesForAddress({ client: publicClient, address: addr }),
  };

  myNames.addEventListener("name-selected", async (e: any) => {
    const sel = e.detail as { name: string };
    await renderProfile(sel.name);
  });

  async function renderProfile(name: string) {
    const profileSec = root.querySelector("#profile-section") as HTMLElement;
    profileSec.hidden = false;
    profileSec.innerHTML = `<p>Loading ${name}…</p>`;

    const lookup = await lookupName({
      publicClient,
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
    editor.client = {
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
        return walletClient.sendTransaction({
          account, chain: mainnet, to: ens.publicResolver, data,
        });
      },
    };

    const renewal = profileSec.querySelector("b-renewal") as any;
    renewal.node = lookup.node;
    renewal.name = lookup.name;
    renewal.label = lookup.name.split(".")[0]!;
    renewal.currentExpiry = lookup.expiry;
    renewal.client = {
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
        // Caller writes the per-contract address; placeholder no-op for the
        // reference dApp until the registrar addresses are wired in.
        return walletClient.sendTransaction({
          account, chain: mainnet, to: account, data,
        });
      },
    };

    const transfer = profileSec.querySelector("b-transfer") as any;
    transfer.node = lookup.node;
    transfer.currentOwner = lookup.owner;
    transfer.fuses = lookup.fuses;
    transfer.client = {
      resolveAddr: async (n: string) => {
        const p = await resolveProfile({ client: publicClient, name: n });
        return p.address;
      },
      transfer: async (_node: Hex, _from: Address, _to: Address) => {
        // NameWrapper.safeTransferFrom call — wired by the operator in
        // production. Reference dApp returns the call-data hash as a stub.
        return ("0x" + "0".repeat(64)) as Hex;
      },
    };

    const primary = profileSec.querySelector("b-primary-name") as any;
    primary.name = lookup.name;
    primary.client = {
      reverseAddr: async () => {
        const r = await resolveReverse({ client: publicClient, address: account });
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
        return walletClient.sendTransaction({
          account, chain: mainnet, to: ens.reverseRegistrar, data,
        });
      },
    };

    const perms = profileSec.querySelector("b-permissions-panel") as any;
    perms.node = lookup.node;
    perms.fuses = lookup.fuses;
    perms.client = {
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
        return walletClient.sendTransaction({
          account, chain: mainnet, to: ens.nameWrapper, data,
        });
      },
    };

    const siwe = profileSec.querySelector("b-siwe-signin") as any;
    siwe.statement = `Sign in as the holder of ${lookup.name}.`;
    siwe.client = {
      walletClient,
      address: account,
      verify: async () => ({ ok: true }),
    };
  }
}

boot().catch(err => {
  document.getElementById("manage")!.innerText = "manage init failed: " + (err?.message ?? err);
});
