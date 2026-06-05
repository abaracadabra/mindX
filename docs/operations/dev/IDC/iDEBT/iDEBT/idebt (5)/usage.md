# iDEBT — Usage Guide

This document is for **holders**, **heirs**, **agents**, and **integrators**
who want to interact with a deployed iDEBT stack. For architecture see
[technical.md](./technical.md). For deployment see [deploy.md](./deploy.md).

## 1. Prerequisites

- An EVM wallet with settlement-token balance (typically USDC or USDCa,
  depending on chain).
- Optional but recommended:
  - A BANKON AlgoIDNFT sovereign identity ([bankon.pythai.net](https://bankon.pythai.net)).
  - A Parsec wallet ([parsec.finance](https://parsec.finance)) for x402 flows.
  - A mindX API key for risk advisories ([mindx.pythai.net](https://mindx.pythai.net)).

## 2. Opening a position

### 2.1 Choose principal, maturity, dormancy

- **principal** — amount of settlement token to lock; capped by
  `iDEBT.maxPrincipal()`.
- **maturity** — unix seconds; must be strictly in the future.
- **dormancy** — seconds the holder can be silent before heirs may claim.
  Typical values: `30 days` (active trader), `1 year` (passive holder).

### 2.2 Build the heir set

iDEBT requires exactly one Merkle root committing to `{(successor, sharesBps)}`
tuples summing to 10_000 bps. Leaves are `keccak256(abi.encode(successor, sharesBps))`.

Reference JavaScript (using viem + merkletreejs):

```ts
import { keccak256, encodeAbiParameters } from "viem";
import { MerkleTree } from "merkletreejs";

const heirs = [
  { successor: "0xAAAA...", sharesBps: 5000 },
  { successor: "0xBBBB...", sharesBps: 3000 },
  { successor: "0xCCCC...", sharesBps: 2000 },
];

const leaves = heirs.map(h =>
  keccak256(
    encodeAbiParameters(
      [{ type: "address" }, { type: "uint16" }],
      [h.successor, h.sharesBps]
    )
  )
);
const tree = new MerkleTree(leaves, keccak256, { sortPairs: true });
const root = tree.getHexRoot();
```

All heir structs passed to `openPosition` share the same `proofRoot == root`.

### 2.3 Pay for the open (if x402 gated)

If `iDEBT.x402()` is set, the holder must have a current receipt for
`keccak256("iDEBT.open")`. See §4 below for the full payment flow.

### 2.4 Approve and call

```ts
await settlementToken.approve(iDEBT.address, principal);

const tx = await iDEBT.openPosition(
  principal,
  Math.floor(Date.now() / 1000) + 180 * 86_400, // 180-day maturity
  30 * 86_400,                                  // 30-day dormancy
  heirs.map(h => ({ successor: h.successor, sharesBps: h.sharesBps, proofRoot: root }))
);
const { logs } = await tx.wait();
// PositionOpened emits the tokenId.
```

## 3. Position lifecycle

### 3.1 Heartbeat

Call `heartbeat(tokenId)` any time as the holder. It refreshes
`lastHeartbeat` to `block.timestamp`. ERC-721 transfer also refreshes the
heartbeat — an intentional design so that transferring to a new custodian
resets the dormancy clock automatically.

### 3.2 Servicing

Anyone (not just the holder) can call
`service(tokenId, amount)` to pay down principal. This is useful for
programmatic counterparty payments.

⚠️ **Servicing does not reset the heartbeat.** Only the holder's own
`heartbeat`, `service`, or `transfer` counts as proof-of-life.

### 3.3 Closing

After `block.timestamp >= maturity`, the holder can call `close(tokenId)` to
burn the NFT and receive `min(MTM, principal)` in settlement token. The
protocol reserve captures any excess (MTM > principal), forming the DAIO's
upside pool.

### 3.4 Inheritance

After `block.timestamp >= lastHeartbeat + dormancy`, any registered heir may
call:

```ts
const proof = tree.getHexProof(leaves[heirIndex]);
const heirProof = encodeAbiParameters(
  [{ type: "address" }, { type: "uint16" }, { type: "bytes32[]" }],
  [heirs[heirIndex].successor, heirs[heirIndex].sharesBps, proof]
);
await iDEBT.claimInheritance(tokenId, heirProof);
```

Each heir's payout is `MTM × sharesBps / 10_000`. Heirs claim independently;
when the last share is claimed, principal reaches zero and the position is
burned.

Like `openPosition`, `claimInheritance` is gated by
`keccak256("iDEBT.claim")` if x402 is enabled.

## 4. x402 payment flow (Parsec / Algorand)

1. **Get pricing.** Call `X402PaymentGateway.priceOf(scope)` or read the
   price from your own off-chain catalog.
2. **Pay on Algorand.** Use parsec-wallet to send the required
   `amount` of `asset` (typically USDCa) to the Parsec facilitator's Algorand
   address. Grab the Algorand transaction id.
3. **Request a receipt.** POST to `https://x402.parsec.finance/receipt`
   with `{ payer, scope, amount, asset, algoTxId }`. Receive a JSON body
   with the `Receipt` struct and `sig`.
4. **Submit on-chain.** Call `X402PaymentGateway.consume(r, sig)`. The
   gateway marks your address as paid through `r.expiry`.
5. **Perform the gated op.** Call `iDEBT.openPosition` or
   `iDEBT.claimInheritance` while the receipt is still valid.

Reference pseudocode:

```ts
const receipt = await fetch("https://x402.parsec.finance/receipt", {
  method: "POST",
  body: JSON.stringify({
    payer, scope: keccak256("iDEBT.open"),
    amount: 1_000_000, asset: toBytes32("USDCa"),
    algoTxId
  })
}).then(r => r.json());

await x402.consume(receipt.r, receipt.sig);
await iDEBT.openPosition(/* ... */);
```

## 5. Reading the stress index

```ts
const score = await stressIndex.score();     // 0..1e18
const regime = await stressIndex.regime();   // enum 0..4
const snap = await stressIndex.latestSnapshot();
// snap.debtGDP, snap.cds, snap.yieldInv, snap.realRate, snap.dxy, snap.vix, snap.gold
```

To update the stored snapshot (keepers):

```ts
await stressIndex.poke();
```

Before pokeing, make sure each metric's adapter cache is fresh:

```ts
for (let m = 0; m < 7; m++) {
  await oracle.refresh(m);
}
await stressIndex.poke();
```

## 6. Agent integration (AgenticPlace)

1. Register an agent identity on-chain:

   ```ts
   const agentId = keccak256(toHex("my-agent-v1"));
   await agents.register(agentId, "https://my-agent.example.com");
   ```

2. Request attestations from services holding `ATTESTER_ROLE`.

3. Expose the endpoint described at registration. Consumers will fetch
   `${endpoint}/.well-known/agent.json` to discover capabilities. The
   canonical schema lives at [agenticplace.pythai.net/schema](https://agenticplace.pythai.net/schema).

## 7. mindX advisory settlement

1. Holder requests an advisory via the mindX API:

   ```
   POST https://mindx.pythai.net/api/v1/advisory
   { "subject": "0xHolder", "positionId": 42 }
   ```

2. mindX responds with an EIP-712 `Attestation` and signature. The holder (or
   anyone) posts it on-chain:

   ```ts
   await mindx.settle(attestation, sig);
   const [score, at] = await mindx.latestRiskScore(holder);
   ```

## 8. BANKON binding

1. Mint or retrieve your AlgoIDNFT on Algorand.
2. Request a cross-chain binding signature from BANKON:

   ```
   POST https://bankon.pythai.net/api/bind
   { "algoIdRoot": "0x...", "evm": "0x...", "chainId": 137 }
   ```

3. Submit:

   ```ts
   await bankon.bind(algoIdRoot, sig);
   ```

## 9. ABI & deployed addresses

Deployed addresses per chain are published in `deployments/<chain>.json` as
artefacts of each Deploy broadcast. ABIs are emitted to `out/` after
`forge build`. TypeChain types may be regenerated with:

```bash
npx typechain --target ethers-v6 --out-dir frontend/src/types 'out/**/*.abi.json'
```

## 10. Safety checklist for users

- **Always verify the deployed contract address** against the canonical list
  in the repo's `deployments/` directory or the DAIO's published registry.
- **Do not share your heir Merkle tree off-chain.** The on-chain root is the
  only thing needed for inheritance; revealing the tree prematurely leaks
  your succession plan.
- **Keep your dormancy window generous.** Too-short dormancy combined with
  lost keys = immediate inheritance claim. The system assumes the holder has
  at least one reliable mechanism (auto-heartbeat bot, multisig relayer) to
  stay active.
- **Heartbeat bots are first-class citizens.** Any address can be granted
  permission to `heartbeat` on the holder's behalf via a simple custom
  relayer contract (not included here); this is encouraged for long-dated
  positions.
