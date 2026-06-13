# BankonX402Attestor.t

> Unit suite for `BankonX402Attestor` — EIP-712 receipt verification happy path, replay protection, expiry rejection, unregistered facilitator rejection, monotonic nonce enforcement.

**SPDX:** Apache-2.0 | **Pragma:** ^0.8.24 | **Source:** [`BankonX402Attestor.t.sol`](./BankonX402Attestor.t.sol) | **Suite:** `BankonX402AttestorTest`

## Role in bankoneth

Exercises [`contracts/BankonX402Attestor.sol`](../contracts/BankonX402Attestor.sol) — the on-chain verifier for x402 (HTTP 402 stablecoin payment receipts) signed by a registered facilitator. Consumers (e.g. `BankonSubnameRegistrar`, `BankonEthRegistrar`, `BankonDomainHosting`) call `verify(X402Receipt)` to confirm payment before granting service.

This file covers the five critical invariants of the x402 attestor: signature validity, single-use replay protection, expiry, facilitator allowlist, and nonce monotonicity.

Flow coverage: payment-gating across Flow A / B / C.

## Fixture (`setUp()`)

1. `vm.prank(admin)` → `attestor = new BankonX402Attestor(admin)` — admin is constructor admin.
2. Derives `facilitatorPk = uint256(keccak256("facilitator-pk"))` and `facilitator = vm.addr(facilitatorPk)`.
3. `vm.startPrank(admin)` → `attestor.setFacilitator(facilitator, true)` + `attestor.grantConsumer(consumer)`.

Roles after setup:
- `admin` — `DEFAULT_ADMIN_ROLE`.
- `consumer` — `CONSUMER_ROLE` (only role permitted to call `verify`).
- `facilitator` — registered signer.

## Test inventory

| Test | What it asserts | Notable cheatcodes |
|---|---|---|
| `test_VerifyHappyPath` | Builds a receipt (receiptHash=`keccak256("receipt-1")`, claimant, usd6=5_000_000, nonce=1, expiresAt=now+1h), signs with `facilitatorPk` via the `_signReceipt` helper, then `consumer` calls `verify(r)`. Asserts return `true` AND `attestor.isReceiptSpent(r.receiptHash) == true`. | `vm.sign(facilitatorPk, digest)` + `vm.prank(consumer)` |
| `test_RejectReplay` | First verify succeeds; second verify of the *same* receipt reverts with `BankonX402Attestor.ReceiptAlreadyConsumed.selector` (with `r.receiptHash` arg via `abi.encodeWithSelector`). | `vm.prank(consumer)` × 2 + `vm.expectRevert(abi.encodeWithSelector(...))` |
| `test_RejectExpired` | Receipt with `expiresAt = block.timestamp - 1`. `verify` reverts with bare `BankonX402Attestor.ReceiptExpired.selector`. | `vm.expectRevert(selector)` |
| `test_RejectUnregisteredFacilitator` | Receipt signed by a rogue PK (`keccak256("rogue")`) whose address was never `setFacilitator`'d. `verify` reverts with `FacilitatorNotRegistered(rogueAddr)`. | `vm.sign(roguePk, digest)` + `vm.expectRevert(abi.encodeWithSelector(...))` |
| `test_MonotonicNonce` | Receipt r1 with `nonce=5` verifies. Receipt r2 with `nonce=4` (older) reverts with `NonceTooOld(4, 5)`. | `vm.sign` + `vm.prank(consumer)` × 2 + `vm.expectRevert(abi.encodeWithSelector(...))` |

## Coverage

**Covered:**
- `verify(X402Receipt)` — happy path + 4 negative cases.
- `setFacilitator(address, bool)` — implicitly via setUp (true) and `test_RejectUnregisteredFacilitator` (absent).
- `grantConsumer(address)` — implicitly via setUp.
- `isReceiptSpent(bytes32)` view.
- EIP-712 domain separator: name="BankonX402Attestor", version="1", chainId, verifyingContract.
- Type hash: `X402Receipt(bytes32 receiptHash,address claimant,uint256 usd6,uint64 nonce,uint64 expiresAt)` — note **signature** field excluded from the struct hash.
- Custom errors: `ReceiptAlreadyConsumed(bytes32)`, `ReceiptExpired`, `FacilitatorNotRegistered(address)`, `NonceTooOld(uint64,uint64)`.

**Not covered:**
- `verify` called by a non-consumer (no `CONSUMER_ROLE`).
- Facilitator revocation (`setFacilitator(addr, false)` after a successful verify).
- Receipt with `usd6 == 0` or other corner values.
- Multi-claimant nonce isolation — the contract tracks last-nonce-seen per signer; the test doesn't probe per-claimant nonce semantics.
- Fuzz over receipt parameters.

## Notable patterns

- **`_signReceipt` helper** — encapsulates the EIP-712 digest construction: domain hash + struct hash → `keccak256("\x19\x01" || domain || struct)` → `vm.sign(pk, digest)` → `abi.encodePacked(r, s, v)` (note the RSV order, not VRS — Foundry returns `(v, r, s)` from `vm.sign`).
- **Type-hash literal duplicated in test** — both the helper and `test_RejectUnregisteredFacilitator` re-compute the type hash with the same string. Risk: if the contract's type-hash string ever changes, the test must be updated in two places.
- **`abi.encodeWithSelector(...)` for parameterised reverts** — used for `ReceiptAlreadyConsumed(receiptHash)`, `FacilitatorNotRegistered(rogueAddr)`, `NonceTooOld(4, 5)`. Bare selectors used for parameter-less errors (`ReceiptExpired`).

## Known caveats

- All tests use a single `facilitator`; multi-facilitator nonce isolation (each facilitator tracking its own last-nonce) is not exercised.
- The `signature` field is mutably reassigned on the `X402Receipt` struct (`r.signature = _signReceipt(r)`) after building — relies on the struct hash *excluding* the signature field. This is enforced by the type hash string above.
- No test for a malformed signature (e.g. wrong length). `verify` is expected to revert in OpenZeppelin's `ECDSA.recover`, but the symptom isn't pinned.
- `setFacilitator(facilitator, false)` followed by `verify` of a still-fresh receipt isn't tested — operationally important during incident response.

## How to run

```bash
forge test --match-path test/BankonX402Attestor.t.sol -vvv
```

## See also

- [`../contracts/BankonX402Attestor.sol`](../contracts/BankonX402Attestor.sol) — system under test.
- [`../contracts/interfaces/IBankonExtensions.sol`](../contracts/interfaces/IBankonExtensions.sol) — `IBankonX402Attestor` interface + `X402Receipt` struct.
- [`../contracts/x402/X402Receipt.sol`](../contracts/x402/X402Receipt.sol) — receipt-token sibling.
- `docs/X402.md` — x402 facilitator protocol architecture.
