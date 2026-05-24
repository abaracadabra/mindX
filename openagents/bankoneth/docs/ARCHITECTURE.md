# bankoneth — Architecture

Companion to the top-level [`BANKONETH.md`](../BANKONETH.md). This file is the
*operational* architecture for engineers writing code against bankoneth.
`BANKONETH.md` is the contract-and-flow map; this is the deployment-shape map.

For the **canonical specifications** that this implementation is verified
against, see [`specs/`](specs/) — the two ENS subname registrar spec
documents (production architecture + ERC-7857/ERC-6551 integration) live
there alongside their PDFs.

## One module, two chains, three flows

- **Ethereum mainnet** — `BankonSubnameRegistrar`, `BankonEthRegistrar`,
  `BankonDomainHosting`, `BankonSubnameResolver`, `BankonInftAdapter`,
  `BankonX402Attestor`, `BankonAgenticPlaceHook`, `BankonPriceOracle`,
  `BankonReputationGate`, `BankonPaymentRouter`, identity primitives,
  `X402Receipt`.
- **0G Galileo / 0G mainnet** — `iNFT_7857` (the actual ERC-7857 contract).
  The Ethereum-side `BankonInftAdapter` holds the cross-chain binding.
- **Algorand mainnet** — the GoPlausible x402-avm facilitator that
  attests USDC payments (ASA 31566704); the Ethereum-side
  `BankonX402Attestor` verifies the EIP-712 receipts the facilitator signs.

## Cross-chain flow (iNFT Mode A)

```
  user signs                        Ethereum                                    0G chain
  ──────────                        ────────                                    ────────
  claim()  ──── BankonSubnameRegistrar.register() ──┐
                NameWrapper.setSubnodeRecord()      │
                ERC-1155 minted to InftAdapter      │
                                                    │  emits RequestINFTMint
                                                    ▼
                                       (off-chain 0G-side worker watches event)
                                                    │
                                                    │  iNFT_7857.mint(...) on 0G
                                                    ▼
                                                    │  reports tokenId back
                                                    ▼
                BankonInftAdapter
                .registerZeroGTokenId(label, id) ──── computes ERC-6551 TBA via
                                                      CREATE2 against the singleton
                                                      registry; binds (label → TBA)
                BankonSubnameResolver
                .setINFTBinding(node, tba, id) ──── resolver.addr(node) now
                                                     returns the TBA
```

The 0G-side worker is operator-controlled (Treasury Safe + dedicated minter
key). Interim solution until a permissionless bridge is in place. The
binding is one-way trust-minimized: the worker can mint on 0G but cannot
unmint or rebind on Ethereum without the `WIRER_ROLE`.

## Permissions matrix

| Contract | Role | Holder | Powers |
|---|---|---|---|
| All | `DEFAULT_ADMIN_ROLE` | Treasury Safe | Grant/revoke other roles, pause/unpause |
| Registrars (A, B, C) | (multiple) | Treasury Safe (admin) | Pricing markup, fuse policy, pause |
| `BankonSubnameResolver` | `REGISTRAR_ROLE` | All three registrars | `setAddr`, `setText`, `setINFTBinding` |
| `BankonInftAdapter` | `REGISTRAR_ROLE` | `BankonSubnameRegistrar` | `requestMint` |
| `BankonInftAdapter` | `WIRER_ROLE` | 0G-side worker | `registerZeroGTokenId` |
| `BankonX402Attestor` | `CONSUMER_ROLE` | Registrars | `verify(receipt)` |
| `BankonAgenticPlaceHook` | `LISTER_ROLE` | Registrars | `list(...)` |
| `BankonPaymentRouter` | `REGISTRAR_ROLE` | Registrars | `distribute(asset, amount)` |
| `BankonPaymentRouter` | `TREASURER_ROLE` | Treasury Safe | Configure bucket recipients |

## What lives where

```
contracts/
├── BankonSubnameRegistrar.sol   Flow A — claim alice.bankon.eth (re-homed)
├── BankonEthRegistrar.sol       Flow B — buy newdomain.eth
├── BankonDomainHosting.sol      Flow C — host an external .eth
├── BankonPriceOracle.sol        USD pricing (re-homed)
├── BankonReputationGate.sol     free-tier eligibility (re-homed)
├── BankonPaymentRouter.sol      5-bucket fee split (re-homed)
├── BankonSubnameResolver.sol    addr(node) + text(node, k) + TBA override
├── BankonInftAdapter.sol        cross-chain ERC-7857 + ERC-6551 binding
├── BankonX402Attestor.sol       EIP-712 facilitator receipts
├── BankonAgenticPlaceHook.sol   per-mint listing emitter
├── identity/                    AgentRegistry, SoulBadger, IAgenticPlace
├── inft/                        iNFT_7857 + ITHOTCommitmentRegistry
├── x402/                        X402Receipt
└── interfaces/                  IBankon.sol + IBankonExtensions.sol
```

## Constructor wiring

The deploy order matters because most contracts take immutable references.
The canonical order is in
[`../script/DeployEthereum.s.sol`](../script/DeployEthereum.s.sol):

1. `BankonPriceOracle`, `BankonReputationGate`, `BankonPaymentRouter` — pure
   utilities; no constructor refs.
2. `AgentRegistry`, `X402Receipt`, `BankonX402Attestor`,
   `BankonAgenticPlaceHook` — independent of the registrars.
3. `BankonSubnameResolver`, `BankonInftAdapter` — built mutually-recursive;
   the resolver is constructed with `IBankonInftAdapter(0)`, the adapter is
   then deployed pointing at the resolver, and a follow-up tx calls
   `setInftAdapter` on the resolver.
4. `BankonSubnameRegistrar` (Flow A) — needs all of the above.
5. `BankonEthRegistrar` (Flow B), `BankonDomainHosting` (Flow C).
6. Post-deploy admin txs (in DeployEthereum.s.sol's `run()`):
   - `resolver.grantRegistrar(registrar)` for each Flow registrar
   - `inftAdapter.grantRegistrar(subnameRegistrar)`
   - `agenticPlaceHook.grantLister(...)` for each Flow registrar
   - `x402Attestor.grantConsumer(...)` for each Flow registrar

## Then WireCrossChain

After `DeployZeroG.s.sol` mints the 0G-side `iNFT_7857`,
`script/WireCrossChain.s.sol` runs the Treasury-Safe-signed admin txs:

- `inftAdapter.setZeroGiNFTContract(zeroGiNFT, zeroGChainId)`
- `inftAdapter.setErc6551Implementation(erc6551Impl)`
- `x402Attestor.setFacilitator(facilitatorAddr, true)`
- `agenticPlaceHook.setWebhookURL(webhookURL)`

After this, the iNFT Mode A path is fully closed loop.

## Reading on-chain state

`@bankoneth/core`'s `BankonethClient` exposes:

- `quoteSubname(label, years)` → `{usd6}`
- `quoteEthPurchase(label, years)` → `{wei, usd6}`
- `resolveAddr(label, parent?)` → address (returns TBA when iNFT Mode A active)
- `tbaOfLabel(label)` → ERC-6551 wallet address
- `isX402ReceiptSpent(receiptHash)` → bool

v2 (Phase 1+) adds:

- `resolveProfile({ client, name })` — full profile via Universal Resolver
- `resolveReverse({ client, address })` — reverse-name lookup
- `lookupName({ ... })` — name-card-ready bundle (records + fuses + TBA)
- `getNamesForAddress({ client, address })` — inventory via ensjs subgraph
- `getSubnames({ client, name })` / `getNameHistory({ client, name })`
- `normalize(name)` / `normalizeLabel(label)` — ENSIP-15 wrapper
- `evmCoinType(chainId)` / `COIN_TYPE` const map — ENSIP-11
- `signInWithBankoneth(...)` / `siweMessage(...)` — EIP-4361 helpers
- `MAINNET` / `SEPOLIA` / `ensAddressesFor(chainId)` — canonical addresses

For exhaustive contract surfaces use `forge inspect <contract> abi`.

## Reference implementations consulted

The v2 plan drew directly from these canonical sources:

- [`ensdomains/ens-contracts`](https://github.com/ensdomains/ens-contracts) — v1 contract surface, PublicResolver mixin chain
- [`ensdomains/namechain`](https://github.com/ensdomains/namechain) (formerly `contracts-v2`) — ENSv2 architecture
- [`ensdomains/ensjs`](https://github.com/ensdomains/ensjs) — canonical client lib (v4.2.2)
- [`ensdomains/ens-app-v3`](https://github.com/ensdomains/ens-app-v3) — UI parity target (TransactionFlowProvider pattern)
- [`ensdomains/subdomain-registrar`](https://github.com/ensdomains/subdomain-registrar) — sale-based registrar reference
- [`gskril/ens-offchain-registrar`](https://github.com/gskril/ens-offchain-registrar) — CCIP-Read reference
- [`mDeisen/ensauth`](https://github.com/mDeisen/ensauth) — ENS-gated auth inspiration

## v2 doc map

- [`ENSIP_COVERAGE.md`](ENSIP_COVERAGE.md) — exact ENSIP implementation matrix
- [`V2_READINESS.md`](V2_READINESS.md) — ENSv2 / Namechain forward-compat
- [`RECORD_EDITING.md`](RECORD_EDITING.md) — `<b-records-editor>` flow
- [`RENEWAL.md`](RENEWAL.md) — `<b-renewal>` flow
- [`TRANSFER.md`](TRANSFER.md) — `<b-transfer>` flow
- [`REVERSE_REGISTRATION.md`](REVERSE_REGISTRATION.md) — primary names (contract + user)
- [`FUSES.md`](FUSES.md) — `<b-permissions-panel>` flow
- [`ENSAUTH_GATING.md`](ENSAUTH_GATING.md) — `BankonAuthGate` + SIWE
- [`specs/CCIP_READ_REGISTRAR.md`](specs/CCIP_READ_REGISTRAR.md) — off-chain mode
