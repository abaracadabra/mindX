# BankonDomainHosting

> Flow C — subdomain-minting-as-a-service: external `.eth` holders enroll their domain and bankoneth becomes the issuance contract for subnames under their parent.

**SPDX:** Apache-2.0 | **Pragma:** ^0.8.24 | **Source:** [`BankonDomainHosting.sol`](./BankonDomainHosting.sol)

## Role in bankoneth

`BankonDomainHosting` implements **Flow C**: an external `.eth` 2LD owner (already wrapped in ENS NameWrapper with `CANNOT_UNWRAP` burned — the parent-lock requirement called out in the ENS docs) enrolls their domain by calling `enroll(...)`. From that point, bankoneth is authorized to mint subnames under that parent for paying customers. The parent owner sets per-parent pricing, child fuses, default expiry, and an owner-payout share in basis points. Revenue is split three ways:

1. Parent owner receives `ownerShareBps` of `msg.value`.
2. The rest goes to `BankonPaymentRouter` for the standard 5-bucket distribution (treasury / buyback / public-goods / ops / squat).
3. bankoneth's "host share" (`hostShareBps`, default 25%) is implicit in the math: parent owner is capped at `(10000 - hostShareBps)` of revenue.

Flow C complements Flow A (`*.bankon.eth` agent subnames via `BankonSubnameRegistrar`) and Flow B (new `.eth` 2LD purchases via `BankonEthRegistrar`). Like the other registrars, it speaks two payment rails — ETH (`msg.value`) and x402-avm (`payment` byte payload starting with `0x02`) verified by `BankonX402Attestor`.

**Critical prerequisite**: the parent owner MUST call `NameWrapper.setApprovalForAll(thisAddress, true)` before `enroll()` — without that approval, `issue()` cannot mint subnames. This is called out in the contract's NatSpec at lines 22-24.

## Inheritance

- `IBankonDomainHosting` — interface in [`interfaces/IBankonExtensions.sol`](./interfaces/IBankonExtensions.sol) (struct `EnrolledParent`, events, functions).
- `AccessControl` — `DEFAULT_ADMIN_ROLE`, `TREASURER_ROLE` (declared but not used in this contract for any external function; reserved).
- `ReentrancyGuard` — `issue` is `nonReentrant`.
- `Pausable` — `enroll` and `issue` honor `whenNotPaused`.

## Constructor

| arg               | type                    | purpose                                                          |
|-------------------|-------------------------|------------------------------------------------------------------|
| `admin`           | `address`               | Granted `DEFAULT_ADMIN_ROLE`.                                    |
| `_nameWrapper`    | `INameWrapper`          | Canonical ENS NameWrapper (mainnet `0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401`).|
| `_resolver`       | `IPublicResolver`       | Resolver used on every minted subname (typically `BankonSubnameResolver`). |
| `_paymentRouter`  | `IBankonPaymentRouter`  | Receives the non-parent revenue cut.                             |
| `_x402Attestor`   | `IBankonX402Attestor`   | Verifies x402-avm receipts.                                      |

Roles granted at construction: `DEFAULT_ADMIN_ROLE` → `admin`.

## Storage layout

| name                     | type                                    | purpose                                                                         | mutable? |
|--------------------------|-----------------------------------------|---------------------------------------------------------------------------------|----------|
| `TREASURER_ROLE`         | `bytes32 constant`                      | `keccak256("TREASURER_ROLE")` (reserved; not used by any function here).        | no       |
| `CANNOT_UNWRAP`          | `uint32 constant`                       | `1` — ENS fuse bit for parent-lock.                                             | no       |
| `PARENT_CANNOT_CONTROL`  | `uint32 constant`                       | `1 << 16` — child-fuse default.                                                 | no       |
| `CAN_EXTEND_EXPIRY`      | `uint32 constant`                       | `1 << 18` — child-fuse default.                                                 | no       |
| `DEFAULT_CHILD_FUSES`    | `uint32 constant`                       | `PARENT_CANNOT_CONTROL | CANNOT_UNWRAP | CAN_EXTEND_EXPIRY`.                    | no       |
| `nameWrapper`            | `INameWrapper` immutable                | ENS NameWrapper.                                                                 | no       |
| `resolver`               | `IPublicResolver` immutable             | Resolver for minted subnames.                                                    | no       |
| `paymentRouter`          | `IBankonPaymentRouter` immutable        | Revenue router.                                                                   | no       |
| `x402Attestor`           | `IBankonX402Attestor` immutable         | x402 verifier.                                                                    | no       |
| `hostShareBps`           | `uint16` public                          | bankoneth share in bps (default `2500` = 25%). Caps `ownerShareBps`.            | yes (admin)|
| `_parents`               | `mapping(bytes32 => EnrolledParent)` private | Parent-node → enrollment record.                                          | yes (enroll/disenroll)|

## Roles

| Role                 | keccak256                              | Who holds                | What they can do                                          |
|----------------------|----------------------------------------|---------------------------|-----------------------------------------------------------|
| `DEFAULT_ADMIN_ROLE` | OpenZeppelin default                   | `admin` (constructor)     | `setHostShareBps`, `pause`, `unpause`.                    |
| `TREASURER_ROLE`     | `keccak256("TREASURER_ROLE")`          | (none granted; reserved)  | (no external function in this contract uses it).          |

## Events

### `ParentEnrolled(bytes32 indexed parentNode, address indexed parentOwner, uint16 ownerShareBps)` (from interface)

Emitted on `enroll`. Indexers can build the parent-marketplace view from this event stream.

### `SubnameIssued(bytes32 indexed parentNode, string label, address indexed owner)` (from interface)

Emitted on `issue` after the subname mints. `label` is unhashed (it's a calldata string parameter on `issue`).

## Errors

### `ParentNotWrapped()`

Reverted on `enroll` when `!nameWrapper.isWrapped(parentNode)`. The parent must be wrapped in NameWrapper first.

### `CannotUnwrapNotBurned()`

Reverted on `enroll` when the parent has not burned the `CANNOT_UNWRAP` fuse. This is the parent-lock requirement.

### `NotParentOwner()`

Reverted on `enroll` (wrong caller) and `disenroll` (non-owner). The caller must be the wrapped-name owner per `nameWrapper.getData`.

### `ParentNotEnrolled()`

Reverted on `disenroll` or `issue` when the target parent has no active enrollment.

### `AlreadyEnrolled()`

Reverted on `enroll` when the parent is already active. Disenroll first, then re-enroll.

### `LabelTaken()`

Reverted on `issue` when the computed subname node already has an owner.

### `InsufficientPayment(uint256 paid, uint256 required)`

Reverted on `issue` when the ETH rail receives `msg.value == 0`. (x402 rail has a separate require with string message.)

## External / public API

### `setHostShareBps(uint16 newBps) external`

Updates the bankoneth host share. Reverts `"host share > 50%"` if `newBps > 5000`. Access: `DEFAULT_ADMIN_ROLE`. Note: changing this does NOT retroactively re-cap existing `ownerShareBps` values; new enrollments enforce the new cap.

### `pause() external` / `unpause() external`

Halt/resume `enroll` and `issue`. Access: `DEFAULT_ADMIN_ROLE`.

### `enroll(bytes32 parentNode, uint256 pricePerLabel6, uint16 childFuses, uint64 defaultExpiry, uint16 ownerShareBps) external`

Registers a parent for hosting. Behaviour:
1. Revert `AlreadyEnrolled` if `_parents[parentNode].active`.
2. Revert `ParentNotWrapped` if `!nameWrapper.isWrapped(parentNode)`.
3. Read parent owner + fuses via `nameWrapper.getData(uint256(parentNode))`.
4. Revert `NotParentOwner` if `msg.sender != owner`.
5. Revert `CannotUnwrapNotBurned` if `CANNOT_UNWRAP` fuse not burned.
6. Require `ownerShareBps <= 10_000 - hostShareBps`.
7. Store the `EnrolledParent` (substituting `DEFAULT_CHILD_FUSES` if `childFuses == 0`).
8. Emit `ParentEnrolled`.

Access: anyone (per-parent ownership is enforced by step 4). Modifier: `whenNotPaused`.

### `disenroll(bytes32 parentNode) external`

Sets `_parents[parentNode].active = false`. Reverts `ParentNotEnrolled` if not active or `NotParentOwner` if caller is not the recorded owner. Access: anyone (gated by ownership). No event (intentional; presence/absence of the parent in subsequent issuances suffices).

### `issue(bytes32 parentNode, string calldata label, address owner, bytes calldata payment) external payable returns (bytes32 subnameNode)`

Mints a subname under an enrolled parent. Behaviour:

1. Load `EnrolledParent`; revert `ParentNotEnrolled` if not active.
2. **Payment dispatch**:
   - If `payment.length > 0 && payment[0] == 0x02`: x402-avm — `abi.decode(payment[1:])` into receipt; `x402Attestor.verify(r)`; require `r.usd6 >= p.pricePerLabel6`.
   - Else (ETH rail): require `msg.value > 0`.
3. Compute `labelhash = keccak256(bytes(label))`, `subnameNode = keccak256(parentNode || labelhash)`.
4. Revert `LabelTaken` if `nameWrapper.getData(subnameNode).owner != address(0)`.
5. Call `nameWrapper.setSubnodeRecord(parentNode, label, owner, address(resolver), 0, childFuses, defaultExpiry)`.
6. **Revenue split** (ETH rail only):
   - `ownerCut = msg.value * ownerShareBps / 10_000` → forwarded to `parentOwner` via raw `call`.
   - `routerCut = msg.value - ownerCut` → forwarded to `paymentRouter` via raw `call`, then `paymentRouter.distribute(address(0), routerCut)` triggers the 5-bucket fan-out.
7. Emit `SubnameIssued`.

Access: anyone. Modifiers: `nonReentrant`, `whenNotPaused`. Reverts `"parent payout failed"` or `"router fund failed"` on raw-call failure.

### `parentOf(bytes32 parentNode) external view returns (EnrolledParent memory)`

Returns the full enrollment record. Useful for UI dashboards showing per-parent stats.

## Internal helpers

—

## Invariants

- `_parents[node].active == true` iff `enroll(node, ...)` was successful and `disenroll(node)` has not been called.
- `ownerShareBps + hostShareBps <= 10_000` for every enrolled parent (enforced at enroll time).
- `subnameNode = keccak256(parentNode || keccak256(bytes(label)))` (standard ENS namehash derivation).
- After successful `issue`, the parent has received `ownerCut`; the router has received and distributed `routerCut`; the contract retains no ETH for that issuance.
- Holds funds only transiently within `issue`; no `receive()` declared, so unsolicited transfers REVERT.

## Security considerations

- **Reentrancy**: `issue` is `nonReentrant`. The two raw `call`s in the revenue split happen sequentially; a malicious `parentOwner` cannot drain by re-entering because the guard is set. The router call also can re-enter only into pure setters there.
- **Parent payout DoS**: if `parentOwner` is a contract that reverts in `receive()`, the entire `issue` reverts (`"parent payout failed"`). The parent griefs themselves — they get no revenue and can't even unenroll-and-rescue because disenroll only flips a bool. Parents should use plain EOAs.
- **Router payout DoS**: similarly, if `paymentRouter` reverts on receive (it doesn't — `receive() external payable {}` is empty), `issue` reverts. Audit the router before swapping.
- **Parent-owner change in NameWrapper**: enrollment captures `msg.sender` at enroll-time but does NOT track NameWrapper owner changes. If the parent is transferred via NameWrapper, the old owner can still `disenroll` and receive payouts. Periodic re-enrollment may be needed.
- **`CANNOT_UNWRAP` burn requirement**: enforced at enroll-time. Once enrolled, the contract relies on the parent never being unwrapped — but NameWrapper's `CANNOT_UNWRAP` burn is permanent, so this holds.
- **Approval requirement**: enrollment does NOT verify `nameWrapper.isApprovedForAll(parentOwner, address(this))`. Issuance simply reverts later if approval is missing. A future improvement: check in `enroll` and revert early.
- **x402 underpay check**: x402 rail enforces `r.usd6 >= p.pricePerLabel6`. The `pricePerLabel6` is parent-declared USD; the front-end is responsible for converting to ETH for the ETH rail.
- **ETH-rail no price check**: on the ETH rail, the contract accepts ANY non-zero `msg.value` — no min-value check against `pricePerLabel6`. Parents should set their UI to enforce client-side pricing; otherwise an attacker can mint for 1 wei.
- **Pause behaviour**: pausing halts new enrollments and new issuances; existing enrollments remain unaffected.
- **`TREASURER_ROLE` is dead code**: declared but not used. Consider removing or wiring it to a future `sweep`-like method.

## Integration patterns

- Parent-owner setup:
  1. Wrap their `.eth` 2LD: `NameWrapper.wrapETH2LD(...)` (one-time).
  2. Burn `CANNOT_UNWRAP`: `NameWrapper.setFuses(parentNode, CANNOT_UNWRAP)`.
  3. Approve hosting contract: `NameWrapper.setApprovalForAll(BankonDomainHosting, true)`.
  4. Call `enroll(parentNode, price, fuses, expiry, ownerShareBps)`.
- Customer purchase flow: front-end builds `payment` bytes (rail byte + optional x402 receipt) and calls `issue(parentNode, label, owner, payment)` with `msg.value`.
- The contract requires `BankonSubnameResolver.grantRegistrar(BankonDomainHosting)` (done at deploy script line 117) so the resolver accepts writes from this contract.
- Deployed via [`script/DeployEthereum.s.sol`](../script/DeployEthereum.s.sol) line 107.

## Known gotchas

- **Funding-before-distribute pattern** (the "BANKON vault payment-router funding bug" fix): the contract correctly funds the router with `routerCut` ETH **before** calling `paymentRouter.distribute(address(0), routerCut)` — see lines 178-182. Don't reorder; the router does not pre-stage ETH and would silently/violently fail the underlying transfers if distribute were called against an empty balance. The two-step (`call{value:routerCut}` then `distribute`) is intentional.
- The contract has **no `receive()`** declared, so any unsolicited ETH transfer reverts. This is a feature — accidental funds can't get stuck.
- `disenroll` does not refund or sweep anything because the contract holds no per-parent balance — revenue is forwarded synchronously in `issue`.
- `childFuses` is `uint16` in the struct but the NameWrapper expects `uint32` — the contract casts via `uint32(p.childFuses)` at line 161, which **truncates the top 16 bits** of `DEFAULT_CHILD_FUSES` if it's ever used as the fallback (because `0x50005 > 0xFFFF`). Audit: the cast happens AFTER the `childFuses == 0 ? uint16(DEFAULT_CHILD_FUSES) : childFuses` assignment, and `uint16(0x50005) == 0x0005`, losing `PARENT_CANNOT_CONTROL` (`1 << 16`) and `CAN_EXTEND_EXPIRY` (`1 << 18`). Customers passing non-zero `childFuses` are unaffected; defaulters get a degraded fuse set. **This is the bug to call out for audit.**
- ETH rail accepts ANY non-zero `msg.value`. Front-end enforcement is mandatory.
- The `payment` payload format is the same as `BankonEthRegistrar`: byte 0 = rail, rest = rail-specific ABI encoding.

## See also

- [`interfaces/IBankonExtensions.md`](./interfaces/IBankonExtensions.md) — `IBankonDomainHosting` interface + `EnrolledParent` struct.
- [`interfaces/IBankon.md`](./interfaces/IBankon.md) — `INameWrapper`, `IPublicResolver`, `IBankonPaymentRouter` interfaces.
- [`BankonX402Attestor.md`](./BankonX402Attestor.md) — verifies x402 rail receipts.
- [`BankonPaymentRouter.md`](./BankonPaymentRouter.md) — receives the non-parent revenue cut.
- [`BankonSubnameResolver.md`](./BankonSubnameResolver.md) — the resolver used on minted subnames.
- [`BankonSubnameRegistrar.md`](./BankonSubnameRegistrar.md) — Flow A counterpart (`bankon.eth` only).
- [`BankonEthRegistrar.md`](./BankonEthRegistrar.md) — Flow B counterpart (new `.eth` purchase).
