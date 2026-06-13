# Ownership Transfer — Phase 3.3

`<b-transfer>` ([source](../packages/ui/src/manage/b-transfer.ts)) transfers
a wrapped name's ownership via `NameWrapper.safeTransferFrom`.

## User flow

1. User types a destination — accepts a raw 0x address or an ENS name.
2. If the input ends with `.eth`, the panel resolves it via the
   Universal Resolver and shows the resolved address.
3. User clicks **Transfer name**. The panel calls
   `NameWrapper.safeTransferFrom(from, to, uint256(node), 1, "")`.
4. On success, fires `CustomEvent("transferred", { detail: { to, txHash } })`.

## Soulbound warning

If `CANNOT_TRANSFER` (fuse bit 4) is burned, the panel shows a red banner
and disables the input. The transfer would revert at NameWrapper — the
UI catches it upfront.

Burning `CANNOT_TRANSFER` is irreversible. See [`FUSES.md`](FUSES.md).

## Contract path

```solidity
NameWrapper.safeTransferFrom(
  address from,
  address to,
  uint256 tokenId,    // uint256(namehash(name))
  uint256 amount,     // always 1 — wrapped names are unique
  bytes calldata data // empty
);
```

Gas: ~70k.

## Resolution via UR

Pre-submit, the panel calls
`resolveProfile({ client, name }).address` to convert a name like
`vitalik.eth` to an address. UR follows CCIP-Read offchain resolvers
transparently, so destinations on `*.base.eth` etc. resolve correctly.

## Failure modes

- **CANNOT_TRANSFER burned.** UI blocks. NameWrapper would revert.
- **Caller != current owner.** NameWrapper reverts with `Unauthorised`.
  Wallet shows pre-flight failure.
- **Destination unresolvable.** UI keeps **Transfer name** disabled.

## Further reading

- [`<b-transfer>`](../packages/ui/src/manage/b-transfer.ts)
- [NameWrapper documentation](https://docs.ens.domains/wrapper)
- [Fuses](FUSES.md)
- [Universal Resolver](https://docs.ens.domains/resolvers/universal)
