# BankonDomainHosting.t

> Smoke suite for `BankonDomainHosting` — third-party parent enrollment, fuse pre-condition, owner-only enroll, paid subname issuance, and disenrollment.

**SPDX:** Apache-2.0 | **Pragma:** ^0.8.24 | **Source:** [`BankonDomainHosting.t.sol`](./BankonDomainHosting.t.sol) | **Suite:** `BankonDomainHostingTest`

## Role in bankoneth

Exercises [`contracts/BankonDomainHosting.sol`](../contracts/BankonDomainHosting.sol) — the contract that lets external `.eth` 2LD owners (i.e. NOT just `bankon.eth`) enroll their wrapped name into the BANKON hosting market and earn a configurable share of subname fees.

Smoke-level coverage of the four primary state transitions: enroll, fuse-precondition check, owner gate, subname issue, disenroll. Does not cover x402-receipt-bearing variants, multi-parent settle paths, or the revenue-split math beyond a single happy-path issuance.

Flow coverage: **Flow B** (third-party hosted subname market).

## Fixture (`setUp()`)

1. Deploys `MockNameWrapper`, `MockResolver`, `BankonPaymentRouter(admin)`, `BankonX402Attestor(admin)`.
2. Deploys `BankonDomainHosting(admin, wrapper, resolver, router, attestor)`.
3. `wrapper.adminSetParent(PARENT_NODE, parentOwner, CANNOT_UNWRAP=1, type(uint64).max)` — seeds a wrapped parent with `CANNOT_UNWRAP` fuse burned and far-future expiry. The mock treats `owner != address(0)` as `isWrapped == true`.
4. Wires the payment router so `distribute()` won't `NoRecipients`-revert during the issue test:
   - Caches `router.TREASURER_ROLE()` and `treasurySink = makeAddr("treasury-sink")` **before** `vm.startPrank(admin)` — otherwise the view getters would consume the prank token.
   - `vm.startPrank(admin)` → `router.grantRole(treasurerRole, address(hosting))` + `router.setRecipients(treasurySink, 0, 0, 0, 0)`.

Roles:
- `admin` holds `DEFAULT_ADMIN_ROLE` on hosting + router + attestor.
- `parentOwner` holds the parent ENS node in the mock wrapper.
- `buyer` is the test's third-party purchaser EOA.

Constants:
- `PARENT_NODE = bytes32(uint256(0xdadd1e))` — synthetic parent namehash.
- `CANNOT_UNWRAP = 1` — ENS fuse bit.

## Test inventory

| Test | What it asserts | Notable cheatcodes |
|---|---|---|
| `test_EnrollHappyPath` | `parentOwner` enrolls `PARENT_NODE` with feeUsd6=5_000_000, no x402 reqs, 1y window, ownerShareBps=5000. Reads `parentOf(PARENT_NODE)` and asserts `.active`, `.parentOwner == parentOwner`, `.ownerShareBps == 5000`. | `vm.prank(parentOwner)` |
| `test_EnrollRequiresCannotUnwrapBurned` | Re-seeds parent with `fuses=0`, then enroll reverts with `BankonDomainHosting.CannotUnwrapNotBurned.selector`. | `vm.prank(parentOwner)` + `vm.expectRevert(selector)` |
| `test_OnlyParentOwnerCanEnroll` | `buyer` (not parent owner) calling `enroll(...)` reverts with `BankonDomainHosting.NotParentOwner.selector`. | `vm.prank(buyer)` + `vm.expectRevert(selector)` |
| `test_IssueSubname` | After happy-path enroll, `buyer` sends `0.1 ether` to `hosting.issue{value:…}(PARENT_NODE, "alice", buyer, "")`. Asserts the mock recorded the subnode mint to `buyer` at the deterministic node `keccak256(parentNode || keccak256("alice"))` via `wrapper.getData(uint256(expected))`. | `vm.deal(buyer, 1 ether)` + `vm.prank(buyer)` |
| `test_DisenrollByOwner` | After enroll, `parentOwner` calls `disenroll(PARENT_NODE)`. Asserts `parentOf(PARENT_NODE).active == false`. | `vm.prank(parentOwner)` × 2 |

## Coverage

**Covered (`BankonDomainHosting.sol`):**
- `enroll(bytes32, uint128, uint128, uint64, uint16)` — happy path, fuse check, owner gate.
- `issue(bytes32, string, address, bytes)` payable — minimal happy path.
- `disenroll(bytes32)` — owner case.
- `parentOf(bytes32)` view.
- Custom errors: `CannotUnwrapNotBurned`, `NotParentOwner`.

**Not covered:**
- `issue` with non-empty x402 receipt data — the empty `""` path skips attestor verification.
- Revenue-split math: `setRecipients` only configures one sink; multi-recipient share routing isn't exercised.
- Admin overrides (force disenroll, pause).
- Subname expiry / renewal of issued subnames.
- `wrapper.adminSetParent` with `isWrapped == false` (the mock conflates that with the owner-zero case).

## Notable patterns

- **Cache-before-prank**: `bytes32 treasurerRole = router.TREASURER_ROLE();` runs OUTSIDE `vm.startPrank(admin)` — because `vm.prank` is single-shot for the *next* call, a view inside a multi-call setup will consume the prank token. The comment in the source documents the gotcha.
- **`vm.deal(buyer, 1 ether)`** — seeds buyer ETH before the `issue{value: 0.1 ether}(...)` payable call.
- **Subnode address derivation** mirrors ENS namehash: `keccak256(abi.encodePacked(parentNode, keccak256("alice")))` — both the contract and the test compute it the same way.

## Known caveats

- `MockNameWrapper` accepts subnode mints unconditionally (no fuse checks beyond the parent fuse the test seeds), so `test_IssueSubname` does not validate full ENS fuse-burn semantics on the child.
- `MockResolver` is a recording stub — the test doesn't read back the resolver's `setAddr` or any records the issue flow may write.
- Mock `isWrapped` conflates "parent has owner" with "wrapped" — real `NameWrapper` has independent wrap state.
- The `""` (empty) receipt path bypasses `BankonX402Attestor.verify` entirely; the attestor in setUp is deployed but never invoked.

## How to run

```bash
forge test --match-path test/BankonDomainHosting.t.sol -vvv
```

## See also

- [`../contracts/BankonDomainHosting.sol`](../contracts/BankonDomainHosting.sol) — system under test.
- [`mocks/MockNameWrapper.sol`](./mocks/MockNameWrapper.sol) — used here.
- [`mocks/MockResolver.sol`](./mocks/MockResolver.sol) — used here.
- [`BankonSubnameRegistrar.t.sol`](./BankonSubnameRegistrar.t.sol) — far more exhaustive subname-mint coverage on the sibling registrar.
- `docs/FLOWS.md` (Flow B) — third-party domain hosting flow.
