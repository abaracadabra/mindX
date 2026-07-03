# bankoneth — Delivery Doctrine & Modular Separation

Standing direction for how bankoneth is built, delivered, and monetised. Companion
to [`ARCHITECTURE.md`](ARCHITECTURE.md) (deployment shape), [`PAYMENTS.md`](PAYMENTS.md)
and the [`x402`](../contracts/x402/) contracts (the rail), [`IDENTITY_AAS.md`](IDENTITY_AAS.md)
+ [`TIERED_LOGIN.md`](TIERED_LOGIN.md) (identity), and the [`specs/`](specs/) ENS
subname registrar documents.

Authored in the cypherpunk tradition — [github.com/cypherpunk2048](https://github.com/cypherpunk2048).

## 1. Modular separation is a standing rule

bankoneth is modular and expanding; the folder boundaries are **load-bearing** and
must be **maintained**, never collapsed for convenience. Each module is independently
auditable and replaceable; cross-module coupling goes through explicit interfaces, not
shared internals.

| Module | Concern — stays separate |
|--------|--------------------------|
| `contracts/{identity,inft,inft7857,arc,x402,interfaces}` | on-chain logic, one concern per subfolder; cross-chain bindings via adapters/interfaces only |
| `packages/{core,ui,web,react,parsec-view,parsec-adapter,cli,tauri-app}` | client surfaces — each a self-contained module; `core` is the shared SDK, the rest consume it |
| `clients/python` | language client; mirrors the SDK, no UI |
| `integrations/{mindx,parsec}` | host-specific glue — kept out of `core` and `contracts` |
| `backend` | optional off-chain workers (event watchers, 0G-side mint) — never a trust dependency for the client |
| `docs/{specs,design}` | canonical specs vs working design — the contract the code is verified against |

When the project grows, **add a module or a subfolder — do not merge two concerns
into one.** That separation is what keeps each piece auditable.

## 2. Two routing directions, both first-class

The product expands in **two** addressing directions and both are supported end to end:

- **`subdomain.bankon.eth`** — the ENS subname itself: `BankonSubnameRegistrar` +
  `NameWrapper` + `BankonSubnameResolver` (+ the ERC-7857 iNFT / ERC-6551 TBA binding).
- **`subdomain.bankon.eth/…`** — paths *under* a name: handled by the client/hosting
  layer (`BankonDomainHosting` + the `packages/web` surfaces).

A name is both an identity (the subname) and a site (the path space). Neither direction
is an afterthought.

## 3. Web2 ↔ Web3 bridge — allchain

[`agenticplace.pythai.net/allchain.html`](https://agenticplace.pythai.net/allchain.html)
is the bridge surface: seamless interaction across the **allchain** — EVM (Ethereum +
0G), Algorand (x402-avm USDC), and **CosmWasm** (cosm-wasm) — from a single web2 entry
point. The bridge is the product surface; the chains are the substrate.

## 4. Delivery is itself an x402 service

Delivering this product — registration, hosting, cross-chain allchain interaction — is
**itself an x402-metered service**. The fee is **set in the bankon contracts**
(`BankonPriceOracle` / `BankonPaymentRouter` / `BankonX402Attestor` + `X402Receipt`),
charged at **fair and nominal profit**. Payment is proven on-chain (EIP-712 x402
receipts), not gatekept by a server. See [`PAYMENTS.md`](PAYMENTS.md).

## 5. The frontend is open source — necessarily

Client-side software is **necessarily open source**. We give the frontend
(`packages/{web,ui,react,parsec-view}`) to the community:

- **Security:** client code must be auditable so the community can verify there is no
  **blackbox exploit** — no hidden key exfiltration, no silent fee inflation, no rug.
- **Trust:** the value and the fee live in the **contracts and the service**, not in
  hiding client code. An open client that anyone can read, fork, and self-host is the
  cypherpunk guarantee that the dApp does only what it says.

This is a deliberate consideration *to* the community, not a concession.

## 6. Identity is a signature, not a password

Connection to a contract is authorised by a **wallet signature**: signing the challenge
proves **ownership of the private key**, which **is** proof of identity. No passwords,
no custodial accounts — the signature *is* the credential
([`IDENTITY_AAS.md`](IDENTITY_AAS.md), [`TIERED_LOGIN.md`](TIERED_LOGIN.md),
`BankonAuthGate` / `BankonReputationGate`).

---

*RAGE remembers, aGLM decides, MASTERMIND orchestrates — and bankoneth settles. Modular,
open at the client, paid at the contract, identified by signature.*
