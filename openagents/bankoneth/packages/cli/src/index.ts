#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0
//
// bankoneth CLI — claim, purchase, host, quote.
//
// Usage:
//   bankoneth claim alice --duration 1 --rail eth --inft --list
//   bankoneth purchase newdomain --duration 5 --rail eth
//   bankoneth host enroll yourdomain.eth --price 5 --owner-share 50
//   bankoneth host issue alice yourdomain.eth --rail eth
//   bankoneth quote alice --duration 1
//
// Env required:
//   BANKONETH_RPC_URL          mainnet / sepolia
//   BANKONETH_PK               deploy/test private key (NEVER use for prod)
//   BANKONETH_ADDRESSES_JSON   path to a JSON file with the 9 contract addresses

import { Command } from "commander";
import {
  createPublicClient,
  createWalletClient,
  http,
  type Address,
  type Hex,
  namehash,
} from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { mainnet, sepolia } from "viem/chains";
import { readFileSync } from "node:fs";

import { BankonethClient, type BankonethAddresses } from "@bankoneth/core";

const program = new Command();
program
  .name("bankoneth")
  .description("CLI for bankoneth — bankon.eth subnames, .eth purchases, hosted .eth issuance")
  .version("0.1.0");

function makeClient(): BankonethClient {
  const rpc       = process.env.BANKONETH_RPC_URL || "";
  const pk        = process.env.BANKONETH_PK as Hex | undefined;
  const addrJson  = process.env.BANKONETH_ADDRESSES_JSON || "./bankoneth-addresses.json";
  const chainName = process.env.BANKONETH_CHAIN || "mainnet";

  if (!rpc) throw new Error("BANKONETH_RPC_URL required");
  if (!pk)  throw new Error("BANKONETH_PK required");

  const chain = chainName === "sepolia" ? sepolia : mainnet;
  const account = privateKeyToAccount(pk);
  const publicClient = createPublicClient({ chain, transport: http(rpc) });
  const walletClient = createWalletClient({ chain, transport: http(rpc), account });
  const addrs = JSON.parse(readFileSync(addrJson, "utf-8")) as BankonethAddresses;
  return new BankonethClient(publicClient, walletClient, addrs, namehash("bankon.eth"));
}

program
  .command("claim <label>")
  .description("Flow A — claim <label>.bankon.eth")
  .option("--duration <years>", "registration duration in years", "1")
  .option("--rail <rail>", "eth | usdc-permit | x402-avm", "eth")
  .option("--inft", "wrap as ERC-7857 iNFT on 0G (Mode A)", false)
  .option("--list", "publish to agenticplace.pythai.net", false)
  .action(async (label: string, opts) => {
    const client = makeClient();
    const owner = (client.walletClient!.account as { address: Address }).address;
    const tx = await client.claim({
      label,
      owner,
      durationYears: Number(opts.duration),
      payment: opts.rail,
      inftModeA: !!opts.inft,
      listOnAgenticPlace: !!opts.list,
    });
    console.log("tx:", tx);
  });

program
  .command("purchase <label>")
  .description("Flow B — buy <label>.eth via the canonical ENS commit-reveal")
  .option("--duration <years>", "registration duration in years", "1")
  .option("--rail <rail>", "eth | x402-avm", "eth")
  .action(async (label: string, opts) => {
    const client = makeClient();
    const owner = (client.walletClient!.account as { address: Address }).address;
    const { commitment } = await client.purchaseCommit({
      label,
      owner,
      durationYears: Number(opts.duration),
      resolver: client.addresses.resolver,
      reverseRecord: false,
      ownerControlledFuses: 0,
      payment: opts.rail,
    });
    console.log("committed:", commitment);
    console.log("waiting 65s for the commit window…");
    await new Promise(r => setTimeout(r, 65_000));
    // Note: real purchase requires recovering the same secret; production CLI
    // would persist it. This stub prints what would happen.
    console.log("commit window open — call `bankoneth reveal` with the same secret.");
  });

program
  .command("host:enroll <domain>")
  .description("Flow C — enroll your existing .eth as a hosted parent")
  .option("--price <usd>", "USD price per subname (e.g. 5.00)", "5")
  .option("--owner-share <pct>", "your share in % (max 75)", "50")
  .action(async (_domain: string, _opts) => {
    console.log("Run via @bankoneth/ui or direct viem call — see docs/INTEGRATIONS.md");
  });

program
  .command("host:issue <label> <parentDomain>")
  .description("Flow C — issue <label>.<parentDomain> under a hosted parent")
  .option("--rail <rail>", "eth | x402-avm", "eth")
  .action(async (label: string, parentDomain: string, opts) => {
    const client = makeClient();
    const owner = (client.walletClient!.account as { address: Address }).address;
    const tx = await client.issueUnderHosted({
      parentNode: namehash(parentDomain) as Hex,
      label,
      owner,
      payment: opts.rail,
    });
    console.log("tx:", tx);
  });

program
  .command("quote <label>")
  .description("Show pricing for <label>.bankon.eth")
  .option("--duration <years>", "duration", "1")
  .action(async (label: string, opts) => {
    const client = makeClient();
    const q = await client.quoteSubname(label, Number(opts.duration));
    console.log(`${label}.bankon.eth @ ${opts.duration}y = ${Number(q.usd6) / 1_000_000} USD`);
  });

program.parseAsync(process.argv);
