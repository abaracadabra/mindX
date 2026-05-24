# BankonEthRegistrar.t.sol

Phase 0.2 unit suite covering `BankonEthRegistrar` (Flow B — `.eth` 2LD
purchase as a service). 23 tests across 5 contracts. Mocks
`ETHRegistrarController` via `MockEthRegistrarController`. Fork-mainnet
variants live in `test/fork/BankonEnsFork.t.sol` (Phase 0.3).

## Why split into five contracts

The file used to be a single `BankonEthRegistrarTest` contract. Solc
0.8.24 with `via_ir = true` hit
`Yul exception: Variable _* is 1 too deep in the stack` during IR
optimization. Splitting into five smaller test contracts, each
inheriting an abstract `BankonEthRegistrarHarness`, relieves the per-
contract IR pressure and compiles cleanly. This is the same pattern
used in `test/BankonSubnameRegistrar.t.sol`.

## Harness — `BankonEthRegistrarHarness`

Deploys the full Flow-B stack:

- `MockEthRegistrarController` (test-only)
- `BankonPriceOracle`, `BankonPaymentRouter`, `BankonX402Attestor`
- `BankonEthRegistrar`

Wires the cross-contract roles in `setUp()`:

- `router.TREASURER_ROLE` → registrar (so sweep can call distribute)
- `router.setRecipients(treasury, 0, 0, 0, 0)` (single recipient — all
  the markup rolls to treasury per disabled-bucket fallback)
- `attestor.CONSUMER_ROLE` → registrar (so reveal can verify x402
  receipts)
- `attestor.setFacilitator(facilitator, true)` (deterministic
  facilitator key seeded from `keccak256("eth-registrar-facilitator")`)
- `registrar.TREASURER_ROLE` → admin (so sweep happy-path test can
  prank from admin)

Role IDs are cached as locals *before* `vm.prank` because view getters
consume the prank token — same trick documented in
`BankonDomainHosting.t.sol` setUp (HIGH-2 audit notes).

## Coverage matrix

### `BankonEthRegistrarAdminTest` (5 tests)
- Constructor grants `DEFAULT_ADMIN_ROLE` to admin
- `setMarkupBps` (admin / cap-at-5_000)
- `quote()` math (ENS price × `1 + markupBps/10_000`)
- `quote()` revert on invalid label

### `BankonEthRegistrarCommitTest` (3 tests)
- Commit revert on invalid label
- Commit revert on unavailable label
- Commit stores timestamp + mirrors upstream controller commitment

### `BankonEthRegistrarRevealEthTest` (6 tests)
- Reveal revert on commitment-not-found
- Reveal revert on commitment-too-young
- Reveal revert on commitment-too-old
- Reveal ETH happy path (asserts mock controller stored the registration)
- Reveal ETH underpayment revert (`InsufficientPayment(paid, required)`)
- Reveal ETH overpayment refund — asserts buyer balance + registrar
  retains exactly the BANKON markup post-refund

### `BankonEthRegistrarRevealX402Test` (3 tests)
- x402 happy path: relayer covers ETH, receipt EIP-712-verified, marked spent
- x402 reverts on `usd6 < usd6Owed`
- x402 reverts on `msg.value < weiOwed` (relayer under-funded)

Uses `_mkReceipt(hash, usd6, nonce)` to construct + sign receipts via
the shared `test/helpers/X402Sig.sol` library (extracted from the
inline pattern to keep this test contract's stack pressure low).

### `BankonEthRegistrarSweepPauseTest` (6 tests)
- `sweep()` routes the markup to the router → treasury — **caught
  HIGH-3** (`sweep` didn't fund router before `distribute()`; fixed)
- `sweep()` reverts for non-`TREASURER_ROLE`
- `sweep()` no-op on zero balance
- `pause()` blocks commit (`EnforcedPause` selector)
- `pause()` blocks reveal
- `unpause()` restores flow

## Helper library

`test/helpers/X402Sig.sol` — shared EIP-712 receipt signer used by
both the x402-rail tests here and `BankonSubnameRegistrarTest`. Pulls
the signing dance out of test contracts so the IR optimizer doesn't
inline it everywhere.

## Findings caught by this suite

- **HIGH-3** (`BankonEthRegistrar.sweep` doesn't fund router) — see
  `docs/AUDIT.md`. Fixed in the same Phase 0.2 commit.

## What this suite does **not** cover

- The real `ETHRegistrarController` behaviour (gas, exact reverts) →
  `test/fork/BankonEnsFork.t.sol` (Phase 0.3)
- Resolver / reverse-record interplay — Flow B doesn't write to a
  resolver; that's Flow A territory
- Cross-contract reentrancy — controller is trusted infrastructure
