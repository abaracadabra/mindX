# deployer — client-side contract deployer

> **⚠ PROTOTYPE — message to the next agent (Claude).**
> This deployer — and the wider client-side bankoneth stack it sits in
> (`deployer/` + [`../walletcreator/`](../walletcreator) + [`../pay2play/`](../pay2play))
> — is a **working prototype**, not production. It compiles, its contracts pass
> `forge test` (pay2play 15/15), and the deploy flow runs against Anvil — but it has
> NOT been audited, the constructor ABI encoder is static-types only, `token` value
> is native-only, and `bankon.eth` resolution is a hook. Treat it as a proven shape
> to build on, not a finished system. Known follow-ups are listed under **Scope /
> notes** below; the architecture of record is
> [`../docs/DELIVERY_AND_MODULARITY.md`](../docs/DELIVERY_AND_MODULARITY.md). Keep the
> modular folder separation; do not collapse concerns. — built by Claude, for Claude.

A simpler-than-Remix, **client-side** contract deployer for bankoneth. No build
step, no framework, no external script in the trust path — just `index.html`,
`index.xml`, and `deployer.js`, driven by the wallet's EIP-1193 provider.

© BANKON — always open source · client-side. (c) BANKON all rights preserved.

## The flow — DEPLOY → LAUNCH → RETURN

Two events, then the chain's answer:

| Button | Event |
|--------|-------|
| **DEPLOY** | **arms** a deployment — resolves constructor args, fetches the compiled Foundry artifact, ABI-encodes the args, builds the tx. No cost, no broadcast. |
| **LAUNCH** | **fires it from VALUE** — a **signature** (prove identity to deploy) or a **token** (pay native value), then broadcasts. |
| **RETURN** | the **transaction the blockchain returns** — hash, status, and the deployed contract address. |

Your wallet **public key is the identity** (optionally a `bankon.eth` name) — the
identity that receives the privilege. `index.html` is the protective layer: nothing
deploys until a wallet is connected. `index.xml` is the **solution** — the manifest
of deployable contracts; access is extended from that index.

## index.xml (the solution)

Each `<contract>` points at a Foundry artifact (so the deployer reads the exact
compiled bytecode/ABI — auditable), declares its constructor args (`from="wallet"`,
a literal `value=`, or `from="deployed:<id>"` to chain on an address deployed earlier
in the session), the `value` kind (`signature` or `token`), and the pay2play
`privilege` it confers.

## Chains — isolation + the ALL cycle (`chains.xml`)

The chain bar is the **isolation** control. Each `<chain>` in `chains.xml` is a
separate target (0G, Ethereum, Base, ARC, Moonbeam/GLMR, Polygon/POL, Anvil); before
LAUNCH the deployer requires the wallet to be **on** the selected chain and offers
`wallet_switchEthereumChain`, and it records addresses **per chain** so deployments
never cross chains. `marketRef` is the chainmarketcap key — the "innerstanding" hook
for live fee/market context.

Pick **ALL** to run the **launch cycle**: the armed contract/bundle is deployed to
*every* chain in turn (POL included; ARC is skipped until its chainId finalises), each
with a fresh per-chain address namespace so stage chaining stays correct on each chain.

## Bundles + stages (topic launch pattern)

Contracts group into **topic bundles** — derived from the artifact path (`../pay2play/`
→ `pay2play`, `../openbdk/` → `openbdk`) or set explicitly. `bundles/*.xml` are
self-contained manifests merged via `<include>` (seeded: `daio-inft`, `deltaverse`).
**DEPLOY BUNDLE** arms a whole topic in **stage** order (`stage="N"`, else document
order); **LAUNCH BUNDLE** fires it sequentially, so `from="deployed:<id>"` resolves to
the address the prior stage just produced. Build happens at fire time, so dependents
always see their dependencies. This is how hundreds of contracts launch as one
cohesive pattern — add `<contract>` rows to a bundle to grow a topic.

## Deployment fee (pay-to-play → mindX / AgenticPlace)

Deploying is itself a service. `<fee>` in `index.xml` settles to mindX/AgenticPlace
on LAUNCH — native value to `recipient`, or via the `x402` endpoint for USDC. Set the
recipient/amount before mainnet; `amount="0"` means free (the prototype default).

## Algorand — a separate modular tool (`algorand/`)

Algorand is **not** in `chains.xml` and **not** in the EVM launch cycle: the AVM is
not the EVM. It lives in [`algorand/`](algorand/) as its own tool — same
DEPLOY→LAUNCH→RETURN shape, ARC-56 appspecs + `algosdk` instead of Foundry artifacts +
`window.ethereum`. See [`algorand/README.md`](algorand/README.md).

## Run it

```bash
# 1. compile the contracts so the artifacts exist
cd ../pay2play && forge build

# 2. start a local chain
anvil

# 3. serve the deployer folder (any static server) and open it
cd ../deployer && python3 -m http.server 8088
#   → http://localhost:8088  (connect an Anvil account in your wallet)

# 4. DEPLOY a contract (arm) → LAUNCH (sign / pay → broadcast) → RETURN (tx + address)
```

In the Tauri client this same folder is the deploy surface; keys stay on the device
(see [`../walletcreator/CLIENT_VAULT_SPEC.md`](../walletcreator/CLIENT_VAULT_SPEC.md)).

## Scope / notes

- Constructor encoding supports **static** ABI types (address, uint*, bool, bytes32) —
  enough for the bankon constructors. Dynamic types (string/bytes/arrays) are a
  follow-up.
- `bankon.eth` reverse resolution is a hook (the address is the identity by default),
  kept out of the trust path so the deployer has no keccak/ENS dependency.
- Token value currently means **native** value carried on the deploy tx; ERC-20
  approve+pay is a follow-up (pairs with the pay2play `playWithSig` / ARC settlement).
