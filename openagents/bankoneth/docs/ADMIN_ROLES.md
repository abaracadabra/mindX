# Admin roles — "owns bankon.eth ⇒ can administer"

The bankon admin contracts are OpenZeppelin `AccessControl`. At deploy
(`script/DeployEthereum.s.sol`) every admin role is granted to the `treasury`
address. The tiered-login model requires that the **owner of `bankon.eth`** be the
page-admin AND able to actually set fees/prices on-chain. `script/GrantOwnerRoles.s.sol`
re-grants the page-admin roles to that owner.

## Who is the owner

`bankon.eth` is **wrapped** (ENS registry owner = NameWrapper). The real owner is
`NameWrapper.ownerOf(namehash("bankon.eth"))`:

```
node  = 0x79c178642317fc2d61d186f3b412440f06590d8314f126362d6a88929a6cbe1a
owner = 0x54165AdA93FA752cfec95F3f3bAE2676D3752A99   # observed 2026-06-02
```

Confirm anytime: `node script/etherscan_lookup.mjs owner bankon.eth`. The gate
resolves the admin tier **live** from `NameWrapper.ownerOf`, so a future transfer
moves admin automatically — this address is only the role-grant target.

## Roles granted to the owner

| Contract | Role | Enables |
|---|---|---|
| `BankonPriceOracle` | `GOV_ROLE`, `DEFAULT_ADMIN_ROLE` | `setPrices(p3..p7)`, `setPythaiDiscount`, feeds/tokens |
| `BankonReputationGate` | `GOV_ROLE` | free-tier thresholds / oracles |
| `BankonPaymentRouter` | `DEFAULT_ADMIN_ROLE`, `TREASURER_ROLE` | `setSplits`, `setRecipients`, `distribute` |
| `BankonDomainHosting` | `DEFAULT_ADMIN_ROLE` | `setHostShareBps`, pause (per-parent enroll/setPrices is gated by NameWrapper ownership, which the owner already has) |
| `BankonSubnameRegistrar` | `DEFAULT_ADMIN_ROLE`, `BANKON_OPS_ROLE`, `BONAFIDE_GOV_ROLE` | pause, ops, governance setters |

Not granted: `GATEWAY_SIGNER_ROLE` (x402 facilitator key) and
`MINDX_AGENT_MINTER_ROLE` (autonomous agent minting) — operationally distinct.

## Run

```bash
export DEPLOYER_PK=<current treasury/admin key>     # must hold DEFAULT_ADMIN_ROLE
export BANKON_OWNER_ADDR=0x54165AdA93FA752cfec95F3f3bAE2676D3752A99
export PRICE_ORACLE_ADDR=… REPUTATION_GATE_ADDR=… PAYMENT_ROUTER_ADDR=… \
       DOMAIN_HOSTING_ADDR=… SUBNAME_REGISTRAR_ADDR=…   # from deployments/<chain>.json
forge script script/GrantOwnerRoles.s.sol --rpc-url $RPC --broadcast
```

`_grant` skips any address-zero slot, so it is safe to run with a partial set
during phased deploys. Roles are additive — the treasury keeps its roles unless
separately renounced.
