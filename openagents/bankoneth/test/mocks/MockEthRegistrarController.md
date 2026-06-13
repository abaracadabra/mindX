# MockEthRegistrarController

`test/mocks/MockEthRegistrarController.sol` — storage-backed mock of the
canonical ENS `ETHRegistrarController`
(mainnet: `0x59E16fcCd424Cc24e280Be16E11Bcd56fb0CE547`). Lives in `test/mocks/`
because it is *only* compiled for unit tests; the production
`BankonEthRegistrar` talks to the real controller.

## What it mocks faithfully

- `commit(bytes32 commitment)` — records `block.timestamp` per commitment.
- `register(string, address, uint256, bytes32, address, bytes[], bool, uint16)`
  payable — requires `msg.value >= base + premium`, refunds overpayment
  to `msg.sender` via a low-level call (matches the live controller's
  behaviour, which is the whole reason `BankonEthRegistrar.receive()`
  exists at line 244).
- `rentPrice(name, duration)` → `(base, premium)`, where `base = duration
  * basePricePerSec` and `premium = premiumWei`. Both configurable so
  tests can drive markup-math and overpayment branches.
- `valid(name)` — `length >= 3` unless `setInvalid(true)`.
- `available(name)` — `true` unless `setUnavailable(true)`.
- `minCommitmentAge() = 60`, `maxCommitmentAge() = 86_400` — matches live
  constants close enough that the unit suite covers the window-bounds
  branches in `BankonEthRegistrar.reveal`.
- `makeCommitment(...)` — deterministic `keccak256` of all arguments;
  the real controller does the same.

## What it omits (out of scope for unit coverage)

- Subname write (no NameWrapper integration; that's covered by the
  separate `MockNameWrapper`).
- Actual rent-price oracle integration. Tests set
  `basePricePerSec`/`premiumWei` directly.
- Referral codes, the `registerWithConfig` overload, the L1 → DNS
  registrar fallback.
- ENS-specific revert selectors. The mock reverts with plain
  `require(..., "MockEthRegistrarController: underpay")` strings; tests
  expect either string reverts or the bankoneth wrapper's own selectors.

Anything that needs the real controller's behaviour (gas accounting,
exact revert selectors, the `IPriceOracle` plumbing) belongs in
`test/fork/BankonEnsFork.t.sol` (Phase 0.3) instead.

## Test-only setters

| setter | effect |
|--------|--------|
| `setBasePricePerSec(uint256)` | drives `rentPrice` base component |
| `setPremium(uint256)`         | drives `rentPrice` premium component |
| `setUnavailable(bool)`        | toggles `available` to false |
| `setInvalid(bool)`            | toggles `valid` to false regardless of length |

## Storage exposed for assertions

| getter | purpose |
|--------|---------|
| `commitments(bytes32)` | last seen commit timestamp per commitment |
| `lastLabel()`          | most recent register's label |
| `lastOwner()`          | most recent register's owner |
| `lastDuration()`       | most recent register's duration |
| `lastPaid()`           | actual cost paid (base + premium) |

Struct-returning getters split into individual functions to avoid
the Yul stack-too-deep that the auto-getter triggers when destructured
in tests with many local variables.

## Used by

- `test/BankonEthRegistrar.t.sol` — Phase 0.2 (23 tests).
- `test/fork/BankonEnsFork.t.sol` — Phase 0.3 uses a `vm.mockCall` against
  the real controller address instead; the mock isn't loaded there.
