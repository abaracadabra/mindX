# BankonReputationGate

> Pluggable eligibility check that decides which addresses can register (paid path) and which qualify for free registration via reputation, stake, or TEE attestation.

**SPDX:** MIT | **Pragma:** ^0.8.24 | **Source:** [`BankonReputationGate.sol`](./BankonReputationGate.sol)

## Role in bankoneth

`BankonReputationGate` answers two yes/no questions for the registrars:

1. **Can this address register at all?** (paid path) — true unless the address is banned.
2. **Does this address qualify for a free 7+-char registration?** (free path) — true if ANY of: BONAFIDE score ≥ threshold, PYTHAI stake ≥ threshold, or ERC-8004 TEE attestation flag.

The gate is the bankoneth abstraction layer over external reputation systems. The contract is "default implementation backed by an admin-set score map + an optional secondary oracle (BONAFIDE)". When the external oracles are unset (zero address), only the admin score map and ban list are considered — useful for testnet rehearsals and emergencies.

Only `BankonSubnameRegistrar` queries the gate directly today (Flow A). `BankonEthRegistrar` (Flow B) and `BankonDomainHosting` (Flow C) currently do not gate on reputation because they are pure paid flows — but they could plug into the same gate in a future revision because the interface is purely a view function set.

## Inheritance

- `IBankonReputationGate` — public interface defined in [`interfaces/IBankon.sol`](./interfaces/IBankon.sol).
- `AccessControl` — `DEFAULT_ADMIN_ROLE` + `GOV_ROLE` for governance-level updates.

## Constructor

| arg    | type      | purpose                                                                              |
|--------|-----------|--------------------------------------------------------------------------------------|
| `admin`| `address` | Granted both `DEFAULT_ADMIN_ROLE` and `GOV_ROLE`.                                    |

Roles granted at construction: `DEFAULT_ADMIN_ROLE` → `admin`, `GOV_ROLE` → `admin`.

## Storage layout

| name                     | type                              | purpose                                                                    | mutable? |
|--------------------------|-----------------------------------|----------------------------------------------------------------------------|----------|
| `GOV_ROLE`               | `bytes32 constant`                | `keccak256("GOV_ROLE")`.                                                   | no       |
| `freeThreshold`          | `uint256` public                  | Minimum BONAFIDE score for free registration (default `100`).              | yes (gov)|
| `freeStakeThreshold`     | `uint256` public                  | Minimum PYTHAI stake (default `10_000 * 1e6` — 6-dec ASA).                 | yes (gov)|
| `bonafide`               | `IExternalReputationOracle` public| External score oracle. Zero = disabled.                                    | yes (gov)|
| `attestation`            | `IAttestationRegistry` public     | External ERC-8004 TEE attestation registry. Zero = disabled.               | yes (gov)|
| `stake`                  | `IStakeView` public               | External PYTHAI stake view. Zero = disabled.                               | yes (gov)|
| `_adminScore`            | `mapping(address => uint256)` private | Admin-set score overrides (takes precedence over `bonafide` when > 0). | yes (gov)|
| `banned`                 | `mapping(address => bool)` public | Hard ban list — overrides all eligibility checks.                          | yes (gov)|

## Roles

| Role                 | keccak256                  | Who holds                | What they can do                                                |
|----------------------|----------------------------|--------------------------|------------------------------------------------------------------|
| `DEFAULT_ADMIN_ROLE` | OpenZeppelin default       | `admin` (constructor)    | Manage all roles.                                                |
| `GOV_ROLE`           | `keccak256("GOV_ROLE")`    | `admin` (constructor)    | `setThresholds`, `setOracles`, `setAdminScore`, `setBanned`.    |

## Events

### `ThresholdsUpdated(uint256 freeScore, uint256 freeStake)`

Emitted on `setThresholds`. Off-chain indexers should treat this as the canonical mirror for current eligibility cutoffs.

### `OraclesUpdated(address bonafide, address attestation, address stake)`

Emitted on `setOracles`. Indexers should react by re-pointing their off-chain mirror of these oracles. None of the addresses is indexed (three slots would push past the 3-indexed-arg limit only if one were added — leaving room for future indexer ergonomics).

### `AdminScoreSet(address indexed agent, uint256 score)`

Emitted on `setAdminScore`. `agent` is indexed.

### `BanSet(address indexed agent, bool banned)`

Emitted on `setBanned`. Critical for off-chain abuse-mitigation systems to mirror in real time.

## Errors

This contract defines no custom errors. Reverts come from OpenZeppelin's `AccessControl`.

## External / public API

### `isEligibleForRegistration(address agent) external view returns (bool)`

Returns `false` for `address(0)` or banned addresses, otherwise `true`. The paid-path gate; every registrar should call this on the prospective `owner` before minting.

### `isEligibleForFree(address agent) external view returns (bool)`

Returns `true` when **all** of:
- `agent != address(0)` and `!banned[agent]`, AND
- **any** of:
  - `bonafideScore(agent) >= freeThreshold`, OR
  - `address(stake) != address(0)` and `stake.stakedOf(agent) >= freeStakeThreshold`, OR
  - `address(attestation) != address(0)` and `attestation.isTeeAttested(agent)`.

The free-path gate. Called by `BankonSubnameRegistrar.registerFree` (label length ≥ 7).

### `bonafideScore(address agent) public view returns (uint256)`

Returns, in priority order: (1) `_adminScore[agent]` if > 0 (admin override), (2) `bonafide.score(agent)` if a `bonafide` oracle is set, (3) zero. Useful as a standalone read for UIs that want to show the user's score.

### `setThresholds(uint256 _freeScore, uint256 _freeStake) external`

Updates both free-tier thresholds atomically. Access: `GOV_ROLE`. Emits `ThresholdsUpdated`.

### `setOracles(address _bonafide, address _attestation, address _stake) external`

Atomically replaces all three external oracle bindings. Any of the addresses can be `address(0)` to disable that source. Access: `GOV_ROLE`. Emits `OraclesUpdated`.

### `setAdminScore(address agent, uint256 score) external`

Sets an admin override score for an address. Setting `score=0` falls back to the oracle. Access: `GOV_ROLE`. Emits `AdminScoreSet`. Useful for emergency "give this address a score of 100 right now" without waiting for the oracle to update.

### `setBanned(address agent, bool isBanned) external`

Hard-bans or unbans an address. Banned addresses fail both `isEligibleForRegistration` and `isEligibleForFree`. Access: `GOV_ROLE`. Emits `BanSet`.

## Internal helpers

—

## Invariants

- Ban list strictly dominates: `banned[a] == true` ⇒ `isEligibleForRegistration(a) == false` and `isEligibleForFree(a) == false`, regardless of any oracle.
- `bonafideScore(address(0)) == 0` (no admin score, oracle either disabled or rejects).
- `isEligibleForFree(a) == true` ⇒ `isEligibleForRegistration(a) == true` (free is a strict subset of allowed).
- Admin-set scores monotonically override oracle reads only when > 0.
- The contract holds no funds.

## Security considerations

- **Trust in oracles**: a malicious `bonafide` oracle can inflate any address's score above `freeThreshold` and unlock free registrations indefinitely. Use only audited oracles and consider rate-limiting `registerFree` calls per-address downstream.
- **Trust in stake view**: an attacker controlling `stake.stakedOf` can return any value. Bridge-view contracts must be locked down by the bridge governance.
- **TEE attestation**: assumes the attestation registry returns `true` only for genuinely-attested keys. ERC-8004 implementations vary; review the bound implementation before promoting to mainnet.
- **Admin override**: `setAdminScore` is privileged but cannot bypass the ban list — banning takes precedence.
- **No reentrancy surface**: all functions are pure view or pure setters.
- **Front-running governance**: an `setOracles` swap is visible in the mempool; coordinate with the registrar's UX to gracefully handle a brief mismatch (e.g. show "checking eligibility" between blocks).

## Integration patterns

- `BankonSubnameRegistrar.register` (paid path) calls `reputationGate.isEligibleForRegistration(owner)` at [`BankonSubnameRegistrar.sol:180`](./BankonSubnameRegistrar.sol) and reverts `NotEligible()` if false.
- `BankonSubnameRegistrar.registerFree` (free path) calls `reputationGate.isEligibleForFree(owner)` at [`BankonSubnameRegistrar.sol:287`](./BankonSubnameRegistrar.sol).
- `setReputationGate(address)` exists on `BankonSubnameRegistrar` (gated by `BONAFIDE_GOV_ROLE`) so a new gate implementation can be hot-swapped without touching the registrar code.
- Deployed via [`script/DeployEthereum.s.sol`](../script/DeployEthereum.s.sol) line 72: `new BankonReputationGate(treasury)`.

## Known gotchas

- The bonafide oracle is queried via `bonafide.score(agent)` — if the oracle returns a `uint256.max` value, that still satisfies the threshold (no clamping). Pick an oracle that returns a bounded score.
- Admin override `_adminScore` cannot represent "score 0" via override — it falls through to the oracle. To force a zero, ban the address.
- `freeStakeThreshold` default assumes a 6-decimal ASA (matching PYTHAI's Algorand decimals). If the stake oracle uses 18-decimal accounting, update the threshold accordingly.
- Setting `bonafide` oracle to a non-contract address causes `bonafide.score(agent)` to revert with a low-level call failure, which propagates up; double-check the address before `setOracles`.
- The contract has no pause; emergency stop is "ban everyone" which is impractical. Pause logic, if needed, lives at the registrar level.

## See also

- [`interfaces/IBankon.md`](./interfaces/IBankon.md) — `IBankonReputationGate` interface.
- [`BankonSubnameRegistrar.md`](./BankonSubnameRegistrar.md) — the primary consumer of this gate.
- [`identity/SoulBadger.md`](./identity/SoulBadger.md) — a candidate BONAFIDE-style attestation source.
- [`identity/AgentRegistry.md`](./identity/AgentRegistry.md) — ERC-8004 attestation surface.
