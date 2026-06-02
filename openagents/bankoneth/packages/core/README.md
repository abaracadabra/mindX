# @bankoneth/core

> viem v2 typed client for the bankoneth contracts. Zero UI dependencies.
> Drop-in for PARSEC, mindX, AgenticPlace, or any project that mints
> `bankon.eth` subnames, buys `.eth` 2LDs, or issues subnames under a hosted
> external `.eth`.

## Install

```bash
pnpm add @bankoneth/core viem
```

## Quick use

```ts
import { createPublicClient, createWalletClient, http } from "viem";
import { mainnet } from "viem/chains";
import { BankonethClient } from "@bankoneth/core";

const publicClient = createPublicClient({ chain: mainnet, transport: http() });
const walletClient = createWalletClient({ chain: mainnet, transport: http(), account: "..." });

const client = new BankonethClient(publicClient, walletClient, {
  subnameRegistrar: "0x...",
  ethRegistrar:     "0x...",
  domainHosting:    "0x...",
  resolver:         "0x...",
  inftAdapter:      "0x...",
  x402Attestor:     "0x...",
  agenticPlaceHook: "0x...",
  priceOracle:      "0x...",
  paymentRouter:    "0x...",
}, "0x..."  /* namehash("bankon.eth") */);

// Flow A: claim alice.bankon.eth
const tx = await client.claim({
  label: "alice",
  owner: "0x...",
  durationYears: 1,
  payment: "eth",
  inftModeA: true,
  listOnAgenticPlace: true,
});

// Flow B: buy newdomain.eth
const { commitment } = await client.purchaseCommit({ label: "newdomain", ... });
// wait 60 seconds for the commit window
const reveal = await client.purchaseReveal({ label: "newdomain", ... }, secret);

// Flow C: issue alice.parent.eth where parent.eth is hosted on bankoneth
const tx2 = await client.issueUnderHosted({
  parentNode: "0x..." /* namehash("parent.eth") */,
  label: "alice",
  owner: "0x...",
  payment: "eth",
});
```

## License

Apache-2.0
