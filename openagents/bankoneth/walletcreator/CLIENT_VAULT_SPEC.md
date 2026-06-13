# Client-side vault & wallet-creation — dApp spec

How the bankon-vault and wallet-creation behave **in the client dApp** (Tauri
desktop + web), and the flow that turns a payment into a deployed contract. The
Python modules in this folder ([`bankon_vault.py`](bankon_vault.py),
[`wallet_creator.py`](wallet_creator.py)) are the **open-source reference
implementation** of the crypto and the minting; in production the same logic runs
on the client.

© BANKON — all rights preserved. Always open source (this code touches private keys).

## Non-custodial by construction

The vault lives **entirely on the client** — the Tauri app, or the web build in the
browser's own **processor, RAM, and filesystem**. It is created from **parsec**, and
its master key is **bound to the participant's own private key**:

```
participant wallet ──signs BINDING_MESSAGE ("BANKON-VAULT-KEY-BINDING/v1")──▶ signature
signature ──HKDF-SHA512──▶ vault master key (client RAM only)
```

So only the holder of that private key can decrypt the vault. **BANKON — or any
host or hostile entity — can never read it**, because the key never leaves the
client and is derived from the participant's wallet. That is what makes the
bankon-vault unique.

## Choice: create a folder / encrypt a folder

The client offers the participant a choice:
- **create a vault** (single-secret keystore), or
- **encrypt a folder** (`encrypt_folder` / `decrypt_folder`) — a whole directory
  (documents, keystores, a parsec workspace) sealed into the vault.

## Airgap-first (the first time)

Before the **first** vault/key creation, the client runs the airgap diagnostic
(`airgap_advisory()` → `network_connected()`):

> **If the network is connected**, show the diagnostic and ask, as a question:
> **"Network is connected. Do you want to proceed?"** — and require an explicit
> confirmation before generating keys. The advice: do this first run on an
> **airgapped device**.

## Wallet creation across the allchain

`wallet_creator.create_allchain_wallet()` mints an identity for **every chain on
[allchain.html](https://agenticplace.pythai.net/allchain.html)** — one EVM keypair
valid on every EVM chain (Ethereum, 0G, Base, Polygon, Arbitrum, Optimism, Circle
ARC, …) plus an Algorand ed25519 keypair — and vaults the keys client-side. The
participant can create a wallet on each / any / every chain. (`allchain.html`
source: `/home/hacker/chainmarketcap`; UI: `/home/hacker/live`.)

Wallet creation and vault creation are **pay-to-play services** (`wallet.create`,
`vault.create`) — the fee is set in the bankon contracts (see [`../pay2play`](../pay2play)).
Pay → the client mints + vaults; BANKON never touches the key.

## The deploy flow: DEPLOY → LAUNCH → RETURN

Three buttons, three phases:

| Button | Action |
|--------|--------|
| **DEPLOY** | triggers the contract deployment (the participant's wallet signs and broadcasts the deploy tx) |
| **LAUNCH** | the **payment confirmation** — confirms the x402 / on-chain fee for the service before/at deploy |
| **RETURN** | displays the **transaction returned from the blockchain** — tx hash, receipt, deployed address — as confirmation |

The wallet signature is the proof of identity (pay2play `playWithSig`); the returned
transaction is the public, verifiable record. Nothing in this flow asks the
participant to surrender a key — the dApp signs locally and shows the chain's answer.

## Where the trust lives

- **Open source** — every line that touches a key is auditable (this folder + the
  Tauri/web client).
- **Client-side** — keys are generated and used on the participant's device.
- **Key-bound** — the vault unlocks only with the participant's private-key signature.
- **Airgap-first** — the first key generation is advised offline, with a hard
  "network is connected, do you want to proceed?" gate.
