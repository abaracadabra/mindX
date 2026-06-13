# Name Renewal — Phase 3.2

`<b-renewal>` ([source](../packages/ui/src/manage/b-renewal.ts)) extends a
name's expiry. Two modes per the user's plan:

## Mode 1 — `subname` (Flow A names)

For `*.bankon.eth` names issued by [`BankonSubnameRegistrar`](../contracts/BankonSubnameRegistrar.sol),
the panel calls `registrar.renew(node, additionalSeconds)`. The registrar
in turn calls `NameWrapper.extendExpiry`, capped by the parent's expiry
per NameWrapper semantics.

```solidity
function renew(bytes32 node, uint256 additionalSeconds) external;
```

Gas: ~80k (one NameWrapper write).

## Mode 2 — `eth2ld` (`.eth` 2LDs)

For `.eth` 2LDs purchased via [`BankonEthRegistrar`](../contracts/BankonEthRegistrar.sol),
renewals go **directly** to the canonical ENS controller (no bankoneth
intermediation). The user's wallet calls
`ETHRegistrarController.renew(name, duration)` at mainnet
`0x59E16fcCd424Cc24e280Be16E11Bcd56fb0CE547`. Pure pass-through.

## Pricing

The panel calls `client.quoteUsd(label, years)` for display. Implementations
can mirror `BankonPriceOracle.priceUSD(label, years)` (oracle USD-6) for
Flow A, or `ETHRegistrarController.rentPrice(name, duration)` (ETH wei)
for Flow B.

## UI

Duration radios: **1 / 3 / 5 / 10 years**. The panel shows:
- Current expiry (humanized via `formatExpiry()`)
- New expiry post-renewal
- USD-6 cost

After submit the panel fires a `CustomEvent("renewed", { detail: { years, txHash } })`.

## Failure modes

- **Parent expired.** NameWrapper rejects the call. The registrar surfaces
  the revert; the panel shows `error`.
- **No funds.** ETH rail: insufficient `msg.value`. Wallet rejects pre-broadcast.
- **No client wired.** Panel errors at submit.

## Further reading

- [ENS renewal mechanics](https://docs.ens.domains/learn/protocol#renewal)
- [`<b-renewal>`](../packages/ui/src/manage/b-renewal.ts)
- [`BankonSubnameRegistrar.md`](../contracts/BankonSubnameRegistrar.md)
- [`BankonEthRegistrar.md`](../contracts/BankonEthRegistrar.md)
