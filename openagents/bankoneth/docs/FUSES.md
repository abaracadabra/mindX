# Fuse Management — Phase 3.6

`<b-permissions-panel>` ([source](../packages/ui/src/manage/b-permissions-panel.ts))
surfaces the 8 owner-controllable NameWrapper fuses as burn toggles.

## Fuse bitmap

| Fuse | Bit | Owner-burnable | Effect |
|---|---|---|---|
| `CANNOT_UNWRAP`           | `1 << 0`  | ✓ | Locks the wrapped NFT — no unwrap. |
| `CANNOT_BURN_FUSES`       | `1 << 1`  | ✓ | Prevents burning further fuses. Permanent freeze. |
| `CANNOT_TRANSFER`         | `1 << 2`  | ✓ | Soulbound — no transfers. |
| `CANNOT_SET_RESOLVER`     | `1 << 3`  | ✓ | Locks the resolver address. |
| `CANNOT_SET_TTL`          | `1 << 4`  | ✓ | Locks the TTL. |
| `CANNOT_CREATE_SUBDOMAIN` | `1 << 5`  | ✓ | Locks subname issuance under this name. |
| `CANNOT_APPROVE`          | `1 << 6`  | ✓ | Prevents approvals. |
| `PARENT_CANNOT_CONTROL`   | `1 << 16` | ✗ (parent only) | Parent loses authority over this name. |
| `IS_DOT_ETH`              | `1 << 17` | ✗ (auto) | Set by NameWrapper for `.eth` 2LDs. Read-only signal. |
| `CAN_EXTEND_EXPIRY`       | `1 << 18` | ✗ (parent only) | Holder can call `extendExpiry` on themselves. |

Bankoneth default mint (Flow A): `0x50005` =
`PARENT_CANNOT_CONTROL | CANNOT_UNWRAP | CANNOT_TRANSFER | CAN_EXTEND_EXPIRY`.
This is the **soulbound** preset — non-transferable, parent-locked,
renewable by the holder.

## User flow

1. Panel reads current fuses via `NameWrapper.getData(node)`.
2. Each owner-controllable fuse renders as a row with a **Burn**
   button. Already-burned fuses show a green `burned` badge instead.
3. Click **Burn**. The panel shows a `confirm()` dialog with the
   IRREVERSIBLE warning + the fuse name.
4. On confirm, calls `NameWrapper.setFuses(node, fuseMask)`. Updates
   internal state so the row flips to `burned`.

## Contract path

```solidity
NameWrapper.setFuses(bytes32 node, uint16 ownerControlledFuses) returns (uint32);
```

The mask must be one of the 7 owner-controllable bits (1, 2, 4, 8, 16,
32, 64). Passing parent-controlled bits (`1 << 16`, `1 << 18`) reverts.

Gas: ~50k.

## Soulbound preset

The panel doesn't ship a "burn all 4 soulbound fuses at once" composite
action — burns must happen one at a time. To check the soulbound preset
in code:

```ts
import { hasFuse } from "@bankoneth/core";
const soulbound = hasFuse(lookup, "CANNOT_UNWRAP")
  && hasFuse(lookup, "CANNOT_TRANSFER")
  && hasFuse(lookup, "PARENT_CANNOT_CONTROL")
  && hasFuse(lookup, "CAN_EXTEND_EXPIRY");
```

The `<bankoneth-name-card>` shows a `SOULBOUND` badge when this is true.

## Failure modes

- **Fuse already burned.** Panel disables the button + shows the badge.
- **Parent not locked.** Burning a child fuse before the parent burns
  `CANNOT_UNWRAP` is allowed but the child fuses don't take effect
  until the parent locks. Surface this when wiring against an
  unlocked parent.
- **CANNOT_BURN_FUSES already burned.** Every subsequent burn reverts.
  Panel disables remaining buttons.

## Further reading

- [NameWrapper fuses](https://docs.ens.domains/wrapper/fuses)
- [Creating a Subname Registrar](https://docs.ens.domains/wrapper/creating-subname-registrar)
- [`<b-permissions-panel>`](../packages/ui/src/manage/b-permissions-panel.ts)
- [`<b-fuse-badges>` primitive](../packages/ui/src/primitives/b-fuse-badges.ts)
