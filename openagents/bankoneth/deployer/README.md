# deployer — client-side contract deployer

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
