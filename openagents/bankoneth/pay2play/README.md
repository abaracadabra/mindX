# pay2play — BANKON pay-to-play rails

Modular **pay-to-play** rails for identity management and BANKON-as-a-Service,
fulfilling [bankon.pythai.net](https://bankon.pythai.net). A self-contained Foundry
sub-module of [bankoneth](../) — it compiles on its own, reuses the parent's
vendored libraries (`../lib`), and keeps its concerns in separate contracts per the
[delivery doctrine](../docs/DELIVERY_AND_MODULARITY.md).

Authored in the cypherpunk tradition — [github.com/cypherpunk2048](https://github.com/cypherpunk2048).

## The model

> Pay → (signature-proven) identity → time-boxed access.

Three concerns, three contracts, one rule each:

| Contract | Knows | Rule |
|----------|-------|------|
| [`BankonServiceRegistry`](src/BankonServiceRegistry.sol) | **what** is for sale | the BANKON-as-a-Service catalogue: price, asset, period, tier, beneficiary per `serviceId` |
| [`BankonEntitlement`](src/BankonEntitlement.sol) | **who** holds access | identity ledger: `user → service → expiry`, monotonic tier; only `GRANTER_ROLE` writes |
| [`BANKONPaymentRouter`](src/BANKONPaymentRouter.sol) | **how** to charge | the spine: charge (native/ERC-20), take a fair/nominal fee, forward net, grant the entitlement |

Adding a service is adding a registry row — never editing the router. That separation
is what keeps each piece auditable.

## Identity is a signature

`BANKONPaymentRouter.playWithSig(serviceId, user, sig)` lets a sponsor pay while the
entitlement binds to the wallet that signed the EIP-712 `Play(serviceId,user,nonce)`
message — **ownership of the private key is the proof of identity** (EOA ECDSA or
ERC-1271 smart accounts, via OpenZeppelin `SignatureChecker`). No passwords, no
custody.

## Fair & nominal fee

The fee lives in `BANKONPaymentRouter` (`feeBps`, default **2.5%**, hard-capped at
**10%** — `MAX_FEE_BPS`). The value is the service, not the toll. The router never
custodies funds: it transfers the net straight to the service beneficiary.

## ARC-chain USDC x402 settlement layer

[`Pay2PlayArcSettlement`](src/Pay2PlayArcSettlement.sol) is the most off-chain rail:
the customer pays **USDC on Circle's ARC chain** through an x402 facilitator; the
facilitator returns an **EIP-712-signed receipt** attesting the settlement; this layer
verifies it and **grants the entitlement without moving any tokens** (they already
moved on ARC). Same shape as the Algorand x402-avm rail
([`BankonX402Attestor`](../contracts/BankonX402Attestor.sol)).

Trust is bounded by the facilitator's signing key, so the layer enforces:
- an admin-managed **facilitator allowlist** (EOA or ERC-1271 safe),
- a strictly **monotonic per-facilitator nonce** (replay layer 1),
- a **spent-once receipt digest** set (replay layer 2),
- the receipt must reference the configured **ARC `chainId` + USDC asset**,
- the attested **amount must cover the service price**,
- a receipt **deadline**.

`ArcReceipt = { serviceId, payer, asset, amount, srcChainId, nonce, deadline }`; the
payer (who signed the EIP-3009 USDC authorization on ARC) receives the entitlement.

## Wire-up

The router and the ARC settlement layer each need `GRANTER_ROLE` on the entitlement
ledger, and the ARC layer needs at least one facilitator registered:

```solidity
ent.grantRole(ent.GRANTER_ROLE(), address(router));
ent.grantRole(ent.GRANTER_ROLE(), address(arc));
arc.setFacilitator(facilitatorKey, true);     // admin should be a multisig in prod
```

[`script/DeployPay2Play.s.sol`](script/DeployPay2Play.s.sol) does all of this and seeds
two services (native `identity.register`, USDC `allchain.access`).

```bash
# build + test the module standalone
forge build
forge test

# deploy (env: ADMIN, FEE_RECIPIENT, SERVICE_BENEFICIARY, ARC_CHAIN_ID, ARC_USDC, ARC_FACILITATOR)
forge script script/DeployPay2Play.s.sol --rpc-url $RPC --broadcast
```

## Toolchain

solc 0.8.24 · EVM Cancun · `via_ir` · OpenZeppelin v5 — identical to the parent
bankoneth profile, isolated here. See [`foundry.toml`](foundry.toml) and
[`remappings.txt`](remappings.txt).

---

*RAGE remembers, aGLM decides, MASTERMIND orchestrates — bankoneth settles, pay2play
admits. Modular, open at the client, paid at the contract, identified by signature.*
