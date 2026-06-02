# BankonPaymentRouter

> Records cross-chain x402 receipts and distributes L1-deposited revenue across five buckets (treasury 40 / buyback 25 / public goods 15 / ops 10 / squat reserve 10).

**SPDX:** MIT | **Pragma:** ^0.8.24 | **Source:** [`BankonPaymentRouter.sol`](./BankonPaymentRouter.sol)

## Role in bankoneth

`BankonPaymentRouter` is the **financial backbone** of bankoneth. It has two complementary jobs:

1. **Record receipts** (`recordReceipt`) — every registrar (Flow A/B/C) calls this with `(receiptHash, usd6, asset)` after a paid registration. This is the L1 audit trail for off-chain x402 settlements (Base USDC, Algorand PYTHAI, L1 ETH). It also accumulates the projected 25% buyback share into `buybackPending` and emits `BuybackTriggerCrossed` once the threshold is hit so off-chain keepers can trigger PYTHAI buybacks.
2. **Distribute revenue** (`distribute`) — sweeps either ETH (`asset == address(0)`) or any ERC-20 to the five configured recipient addresses by the configured basis-point splits. Disabled (zero-address) buckets roll their shares into treasury.

The receipt-hash set here is a **companion** to the per-registrar `usedReceipts` mapping (e.g. `BankonSubnameRegistrar.usedReceipts`). Same hash, different layer — the registrar prevents replay against itself; the router prevents the same receipt from being accounted twice across registrars.

This is the only contract in the suite that holds revenue (transiently — between `receive()` deposits from `BankonEthRegistrar.reveal`/`BankonDomainHosting.issue` and a `TREASURER_ROLE` sweep). It is the only contract that owns the bucket-split policy.

## Inheritance

- `AccessControl` — `DEFAULT_ADMIN_ROLE` (policy), `TREASURER_ROLE` (distribute), `REGISTRAR_ROLE` (recordReceipt).
- `ReentrancyGuard` — `distribute` is `nonReentrant`.
- `IBankonPaymentRouter` — public interface in [`interfaces/IBankon.sol`](./interfaces/IBankon.sol).

Uses `SafeERC20` for safe ERC-20 transfers (handles tokens with non-standard return semantics).

## Constructor

| arg    | type      | purpose                                                              |
|--------|-----------|----------------------------------------------------------------------|
| `admin`| `address` | Granted `DEFAULT_ADMIN_ROLE`, `TREASURER_ROLE`, and `REGISTRAR_ROLE`.|

Roles granted at construction: all three to `admin`. The deploy script can later transfer/revoke as needed.

## Storage layout

| name                    | type                          | purpose                                                                  | mutable? |
|-------------------------|-------------------------------|--------------------------------------------------------------------------|----------|
| `TREASURER_ROLE`        | `bytes32 constant`            | `keccak256("TREASURER_ROLE")`.                                           | no       |
| `REGISTRAR_ROLE`        | `bytes32 constant`            | `keccak256("REGISTRAR_ROLE")`.                                           | no       |
| `treasury`              | `address` public              | 40% bucket recipient.                                                    | yes (admin)|
| `buybackVault`          | `address` public              | 25% bucket — funds PYTHAI buyback-and-make.                              | yes (admin)|
| `publicGoods`           | `address` public              | 15% bucket — public-goods grants.                                        | yes (admin)|
| `ops`                   | `address` public              | 10% bucket — operations float.                                           | yes (admin)|
| `squatReserve`          | `address` public              | 10% bucket — defensive squat protection.                                 | yes (admin)|
| `bpsTreasury`           | `uint16` public               | Treasury split bps (default `4000`).                                     | yes (admin)|
| `bpsBuyback`            | `uint16` public               | Buyback split bps (default `2500`).                                      | yes (admin)|
| `bpsPublicGoods`        | `uint16` public               | Public-goods split bps (default `1500`).                                 | yes (admin)|
| `bpsOps`                | `uint16` public               | Ops split bps (default `1000`).                                          | yes (admin)|
| `bpsSquat`              | `uint16` public               | Squat reserve bps (default `1000`).                                      | yes (admin)|
| `seenReceipt`           | `mapping(bytes32 => bool)` public | Recorded receipt hashes (anti-replay).                              | yes (registrar)|
| `buybackThresholdUSD6`  | `uint256` public              | Trigger threshold in USDC base units (default `100_000000` = $100).      | yes (admin)|
| `buybackPending`        | `uint256` public              | Accumulated buyback share since last trigger.                            | yes (registrar)|

## Roles

| Role                 | keccak256                          | Who holds                                                                 | What they can do                            |
|----------------------|------------------------------------|---------------------------------------------------------------------------|---------------------------------------------|
| `DEFAULT_ADMIN_ROLE` | OpenZeppelin default               | `admin` (constructor)                                                     | `setRecipients`, `setSplits`, `setBuybackThreshold`, manage roles. |
| `TREASURER_ROLE`     | `keccak256("TREASURER_ROLE")`      | `admin` initially; also held by `BankonEthRegistrar` for `sweep` (TBD by deploy ops). | `distribute(asset, amount)`.            |
| `REGISTRAR_ROLE`     | `keccak256("REGISTRAR_ROLE")`      | `admin` initially; expected to be granted to each Bankon registrar in production. | `recordReceipt(receiptHash, usd6, asset)`. |

> Note: `DeployEthereum.s.sol` does not currently grant `REGISTRAR_ROLE` to the three registrars — they call `recordReceipt` inside `try/catch` (`splitConfigured()` gate + best-effort), so missing role simply skips the L1 audit row. Add explicit grants if you want the receipt ledger populated.

## Events

### `RecipientsUpdated(address treasury, address buybackVault, address publicGoods, address ops, address squatReserve)`

Emitted on `setRecipients`. Off-chain accounting should mirror.

### `SplitsUpdated(uint16 t, uint16 b, uint16 p, uint16 o, uint16 s)`

Emitted on `setSplits`. The sum is enforced to equal `10000` so split %s are auditable from the event.

### `ReceiptRecorded(bytes32 indexed receiptHash, uint256 usd6, address asset)`

Emitted on `recordReceipt`. `receiptHash` is indexed for fast lookup against the registrar's same-hash event.

### `Distributed(address indexed asset, uint256 total, uint256 toTreasury, uint256 toBuyback, uint256 toPublicGoods, uint256 toOps, uint256 toSquat)`

Emitted on `distribute`. `asset` is indexed (`address(0)` = ETH). The five amount fields are the actual transfer sizes (post-disabled-bucket rollup).

### `BuybackTriggerCrossed(uint256 amountUSD6)`

Emitted when `buybackPending >= buybackThresholdUSD6`. Off-chain keeper (KeeperHub upkeep) watches this and fires the PYTHAI buyback transaction.

### `BuybackThresholdUpdated(uint256 oldT, uint256 newT)`

Emitted on `setBuybackThreshold`.

## Errors

### `ReceiptAlreadyRecorded(bytes32 h)`

Reverted by `recordReceipt` when `seenReceipt[h]` is already true. Caller should treat as benign duplicate.

### `BadSplits()`

Reverted by `setSplits` when `t + b + p + o + s != 10000`.

### `NoRecipients()`

Reverted by `distribute` when all five recipient addresses are zero. Admin must `setRecipients` before any distribution.

## External / public API

### `splitConfigured() external view returns (bool)`

Returns `true` if **any** recipient is non-zero. Registrars use this as a cheap gate before calling `recordReceipt` (skipping the call when the router is not configured prevents wasted gas).

### `recordReceipt(bytes32 receiptHash, uint256 usd6, address asset) external`

Records a receipt. Reverts `ReceiptAlreadyRecorded` on duplicate. Increments `buybackPending` by `(usd6 * bpsBuyback) / 10000` and emits `BuybackTriggerCrossed` (zeroing `buybackPending`) once the threshold is reached. Access: `REGISTRAR_ROLE`. Emits `ReceiptRecorded`.

### `distribute(address asset, uint256 amount) external`

Splits `amount` of `asset` across the five buckets per the basis-point splits. Zero-address buckets are skipped and their share is rolled into treasury. For `asset == address(0)` uses raw `call{value:}` (no return-data check beyond `ok`); for ERC-20s uses `SafeERC20.safeTransfer`. Access: `TREASURER_ROLE`. `nonReentrant`. Reverts `NoRecipients` if every bucket is zero. Emits `Distributed`.

### `setRecipients(address _treasury, address _buyback, address _publicGoods, address _ops, address _squat) external`

Atomically replaces all five recipient addresses. Any can be `address(0)` to disable. Access: `DEFAULT_ADMIN_ROLE`. Emits `RecipientsUpdated`.

### `setSplits(uint16 t, uint16 b, uint16 p, uint16 o, uint16 s) external`

Replaces all five splits. Reverts `BadSplits` if the sum is not exactly `10000`. Access: `DEFAULT_ADMIN_ROLE`. Emits `SplitsUpdated`.

### `setBuybackThreshold(uint256 newThreshold) external`

Updates `buybackThresholdUSD6`. Access: `DEFAULT_ADMIN_ROLE`. Emits `BuybackThresholdUpdated`.

### `receive() external payable`

Accepts plain ETH transfers. Used by `BankonDomainHosting.issue` (forwards `routerCut`) and `BankonEthRegistrar` (accumulates markup until `sweep()`).

## Internal helpers

### `_send(address to, uint256 wei_) internal`

Native-token sender. No-ops if `to == address(0)` or `wei_ == 0`; reverts `"ETH send failed"` if the low-level call fails. Used only by `distribute` for ETH legs.

## Invariants

- `bpsTreasury + bpsBuyback + bpsPublicGoods + bpsOps + bpsSquat == 10000` (enforced on every `setSplits`).
- For any recorded `receiptHash`, `seenReceipt[receiptHash]` is true forever.
- `distribute` never sends more than `amount`; rounding leftovers (≤ 4 wei per call due to integer division) stay in the contract.
- The five recipient addresses can each independently be zero or non-zero; a fully-zero config reverts `NoRecipients` on distribute.
- `buybackPending` is reset to 0 every time `BuybackTriggerCrossed` fires.
- Holds funds. Has `receive()` (no `fallback()`).

## Security considerations

- **Reentrancy**: `distribute` is `nonReentrant`. ETH sends use raw `call`, which can call back into recipients — the guard handles that. ERC-20 `safeTransfer` can also trigger reentrant flows for ERC-777-like tokens; the guard handles that too.
- **Recipient gas griefing**: a malicious recipient contract can revert its receive() and cause `distribute` to revert (because `_send` requires success). Mitigation: set recipients to plain EOAs or audited splitters.
- **Rounding leftover**: integer division leaves up to 4 wei per call stuck in the contract. Sweep periodically via a manual ETH transfer from the contract (not currently supported via a method — admin would need to send via raw call from a contract they control).
- **Receipt replay**: prevented by `seenReceipt` for the same hash. Registrars also enforce their own `usedReceipts` set. Both layers must hold the same hash format (currently arbitrary `bytes32`).
- **Role hygiene**: `admin` is granted all three roles in the constructor. In production, transfer `TREASURER_ROLE` and `REGISTRAR_ROLE` to a hot wallet / multisig and reserve `DEFAULT_ADMIN_ROLE` for the cold key.
- **`setSplits` non-atomicity hazard**: if you mis-sum the bps, the call reverts; old splits stay. Safe.
- **No pause**: in an emergency, revoke `TREASURER_ROLE` to freeze distributions; receipts can still be recorded.
- **`distribute` does NOT decrement an internal balance** — it transfers based on `amount` you pass. If you pass more than the contract holds, the first transfer that runs out will revert. Always call `address(this).balance` or `IERC20(asset).balanceOf(address(this))` off-chain before invoking.

## Integration patterns

- `BankonSubnameRegistrar.register` calls `paymentRouter.recordReceipt(...)` inside `try/catch` at [`BankonSubnameRegistrar.sol:214`](./BankonSubnameRegistrar.sol), gated by `paymentRouter.splitConfigured()`.
- `BankonSubnameRegistrar.renew` also records receipts.
- `BankonEthRegistrar.sweep` calls `paymentRouter.distribute(address(0), bal)` after a `TREASURER_ROLE` operator sweeps accumulated markup.
- `BankonDomainHosting.issue` funds the router via `payable(address(paymentRouter)).call{value: routerCut}("")` and then calls `paymentRouter.distribute(address(0), routerCut)`.
- Deployed via [`script/DeployEthereum.s.sol`](../script/DeployEthereum.s.sol) line 73: `new BankonPaymentRouter(treasury)`.

## Known gotchas

- **Funding-before-distribute pattern**: `BankonDomainHosting.issue` correctly funds the router with ETH **before** calling `distribute` (see [`BankonDomainHosting.sol:179-181`](./BankonDomainHosting.sol)). Don't follow the inverse order — `distribute` makes no internal balance check and will revert when sending into the empty recipients.
- **Best-effort recordReceipt**: registrars wrap `recordReceipt` in `try/catch`, so a missing `REGISTRAR_ROLE` silently skips audit-log writes. Either grant the role explicitly in your deploy or accept that the on-chain receipt ledger will be empty for those flows.
- **PYTHAI buyback signal vs payment**: `buybackPending` accumulates the **projected** 25% share even when the receipt was paid on Algorand. It does not represent actual L1 dollars; an off-chain keeper must convert the signal into a real buyback tx.
- **MIT-licensed**: only the router uses MIT (other contracts are Apache-2.0). Update SPDX consistency if you re-license.
- **No receipt-hash uniqueness with payment**: the router only checks `seenReceipt`; it does not verify that `usd6` matches what was actually paid. Trust comes from `BankonX402Attestor` upstream.

## See also

- [`interfaces/IBankon.md`](./interfaces/IBankon.md) — `IBankonPaymentRouter` interface.
- [`BankonSubnameRegistrar.md`](./BankonSubnameRegistrar.md) — Flow A receipt source.
- [`BankonEthRegistrar.md`](./BankonEthRegistrar.md) — Flow B markup source.
- [`BankonDomainHosting.md`](./BankonDomainHosting.md) — Flow C revenue source.
- [`BankonX402Attestor.md`](./BankonX402Attestor.md) — upstream verifier whose receipt-hash is the one recorded here.
- [`BankonPriceOracle.md`](./BankonPriceOracle.md) — supplies the `usd6` value passed into `recordReceipt`.
