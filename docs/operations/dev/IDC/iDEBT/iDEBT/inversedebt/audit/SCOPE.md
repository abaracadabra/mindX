# DELTAVERSE Debt Inheritance Protocol — Audit Scope Document

**Version:** 1.0
**Prepared for:** Third-party security audit
**Prepared by:** Professor Codephreak, DELTAVERSE Ecosystem
**Date:** February 2026

---

## 1. Protocol Overview

The DELTAVERSE Debt Inheritance Protocol is a seven-contract Solidity system that composes real-world asset tokenization, cross-asset collateralized borrowing, 24/7 perpetual derivatives, a composite debt stress oracle, and a capstone orchestrator into a unified market for expressing inverse positions against the global debt complex. The academic thesis underlying the protocol is documented in three companion papers included in the `docs/` directory; auditors are encouraged to read at least the abstract of each to understand the design intent.

The system's flagship function is `expressThesis()` on the capstone contract, which atomically executes a four-step flow: pull tokenized debt collateral from the user, deposit it into the vault, borrow stablecoin against it, and open a leveraged position on the debt stress index via the perpetual engine. This single transaction implements what we call recursive debt inheritance: the debt system is used as fuel to short itself. Auditors should pay particular attention to this function because its atomicity guarantees are central to the protocol's value proposition, and any way to leave a user's state in a partial or inconsistent configuration between the four underlying calls would be a critical finding.

## 2. Contract Inventory

The following seven contracts are in scope for this audit. The line counts are approximate and exclude blank lines and comments. Lines that exist primarily as NatSpec documentation should be treated as specification, not as code to audit for bugs.

The `RWAToken.sol` contract implements an ERC-20 token that represents fractional ownership of an off-chain debt instrument with KYC-gated transfers, scheduled yield distribution in a secondary token, a supply cap, a maturity date after which transfers are disabled, and a freeze-and-seize mechanism for regulatory compliance. This contract is approximately 447 lines and has already been audited in an earlier version; the current version incorporates critical fixes for double yield accounting and frozen account seizure, plus medium-severity improvements including Pausable, batch whitelist, and custom errors.

The `CrossCollateralVault.sol` contract accepts deposits of multiple whitelisted ERC-20 collateral tokens, prices them via Chainlink oracle feeds with per-asset staleness thresholds, and allows users to borrow a single stablecoin against their combined collateral value up to a configurable loan-to-value ratio. It implements simple interest accrual on borrowed positions, separate borrow LTV and liquidation threshold, a close factor cap on liquidations, and tracks per-user asset arrays to avoid unbounded loops. Approximately 736 lines.

The `PerpetualEngine.sol` contract implements leveraged long and short perpetual futures positions against a single underlying oracle (in our deployment, the DeltaVerseDebtOracle). It supports configurable leverage up to 20x, automated funding rate calculation based on open interest imbalance, liquidation of undercollateralized positions with a bounded liquidator reward, an insurance fund that absorbs socialized losses when individual liquidations are insolvent, partial position close, and adding or removing collateral on open positions. Approximately 697 lines.

The `DeltaVerseDebtOracle.sol` contract aggregates five sub-indices into a composite Global Debt Stress Index using the Synthetix V3 Oracle Manager pattern of multi-source node composition. Each sub-index can blend data from Chainlink push feeds, Pyth Network pull feeds, and authorized reporter median submissions with configurable weights. It includes a staleness circuit breaker, a deviation circuit breaker that stages large jumps for governor approval, historical snapshots for derivatives settlement, and a built-in LP staking pool that distributes fees collected elsewhere in the protocol. Approximately 862 lines.

The `DebtInheritanceProtocol.sol` contract is the capstone orchestrator and is also an ERC-20 token contract (sGDSI). It exposes `mintSGdsi()` and `burnSGdsi()` for unlevered thesis expression, `expressThesis()` and `closeThesis()` for the full recursive inheritance flow, and `routeFees()` for the fee routing loop that compensates oracle LP stakers. Approximately 680 lines.

The `DeltaVerseTimelock.sol` and `DeltaVerseGovernor.sol` contracts form the governance layer using OpenZeppelin's Governor framework with token-weighted voting, quorum fraction, and timelock-controlled execution. The `EmergencyPauser.sol` contract provides an immediate-action circuit breaker controlled by a multisig of guardians, with a cooldown-enforced unpause that requires governance approval. These three contracts together hold the admin role on the other five and represent the complete trust boundary for protocol upgrades. Approximately 500 lines combined.

## 3. Trust Model

The protocol assumes the following trust relationships. The auditor should verify that no contract grants more trust than this document describes, because any undocumented privilege escalation is a finding.

The `DEFAULT_ADMIN_ROLE` on all five operational contracts is held by the `DeltaVerseTimelock`. Any parameter change, role grant, or other privileged operation must be proposed through the `DeltaVerseGovernor`, pass a token-weighted vote, be queued in the Timelock for a minimum of 48 hours, and then be executed. The auditor should verify that this path is the only way to reach admin functions, and that no function bypasses the Timelock by accepting a caller other than the Timelock address.

The `GUARDIAN_ROLE` on the `EmergencyPauser` is held by a small multisig (recommended 3-of-5) of parties independent of the core team. Guardians can call `pauseAll()` or `pauseOne()` immediately without waiting for governance. Guardians cannot unpause; unpausing requires `UNPAUSER_ROLE` which is held by the Timelock. The auditor should verify that the Guardian's power is strictly limited to pausing, and that no Guardian privilege can be used to move funds, change parameters, or upgrade contracts.

The `REPORTER_ROLE` on the `DeltaVerseDebtOracle` is held by a set of authorized data reporters who submit sub-index values. Individual reporters cannot influence the composite value beyond their contribution to the median; the median of all valid reports is what gets used. A malicious reporter can push the median by at most their weight fraction, which is bounded by the configured number of reporters (default minimum is one, but recommended production minimum is three or more). The auditor should verify that no single reporter submission can cause the composite to move by more than the documented deviation circuit breaker allows.

The `KEEPER_ROLE` on the oracle is held by off-chain keeper bots that call `updatePythFeeds()`, `finalizeSubIndex()`, and `updateComposite()`. Keepers cannot influence values; they only trigger state transitions that the contract would permit anyway. A malicious keeper's worst action is denying service by refusing to run, which is bounded because the role is not exclusive and multiple keepers can run in parallel.

The `complianceOfficer` on `RWAToken` (inherited from the existing audited version) holds the ability to freeze accounts and seize frozen balances. This is a deliberate regulatory compliance mechanism. The auditor should verify that freeze and seize are only callable by the compliance officer, that seized funds go to a configured treasury address, and that the mechanism cannot be used to steal from non-frozen accounts.

## 4. Invariants

The following invariants should hold across all executions of the protocol. The auditor should attempt to find execution paths that violate any of them, because each represents a core safety property.

**Invariant 1: sGDSI supply equals collateral backing minus fees.** At any time, the total supply of sGDSI multiplied by the current oracle price divided by the base index should be less than or equal to the stablecoin balance held by the protocol minus the pendingFees counter. If this inequality ever flips, the protocol is undercollateralized and burns would be unable to pay out. The auditor should look for paths where this can happen: a mint that does not charge the full fee, a burn that takes more than its share, a reentrancy between mint and price update, or a price oracle manipulation.

**Invariant 2: Thesis positions are atomic or absent.** At any time, the `ThesisPosition` struct for a given user is either entirely active (all four underlying contract interactions have succeeded) or entirely absent (no partial state). The `expressThesis()` function should never leave a user with vault debt but no perp position, or with a perp position but no vault collateral. The auditor should verify that all revert paths in `expressThesis()` roll back the full flow.

**Invariant 3: Oracle composite reflects weighted sub-indices.** At any time after `updateComposite()` has been called, the composite value should equal the weighted average of non-stale sub-indices. The auditor should verify that stale sub-indices are correctly excluded, that weights sum correctly, and that the deviation circuit breaker prevents any single update from moving the composite more than `maxDeviationBps` without governor approval.

**Invariant 4: Vault health factor monotonicity under benign actions.** A user's health factor should not decrease as a result of the user depositing more collateral, and should not increase as a result of the user borrowing more. The auditor should verify that these monotonicity properties hold even under interest accrual and asset price changes.

**Invariant 5: Insurance fund never produces negative balance.** The PerpetualEngine's insurance fund can go to zero under socialized losses but should never be reported as negative. The auditor should verify that the `_closePartial` and `liquidate` functions correctly handle the case where the deficit exceeds available insurance.

**Invariant 6: Governance delay cannot be bypassed.** No state change affecting the protocol's admin-controlled parameters should execute without passing through the Timelock's minimum delay. The auditor should search for functions that accept calls directly from the deployer, the Governor, or any non-Timelock address and modify protocol state.

**Invariant 7: Emergency pause is idempotent and bounded.** Calling `pauseAll()` multiple times should have the same effect as calling it once. A paused contract should reject all state-changing operations but should still allow view functions. The auditor should verify that the `whenNotPaused` modifier is applied to every function that could damage the protocol if called during an emergency.

## 5. Out of Scope

The following components are not in scope for this audit and the auditor should not spend time on them unless they directly affect the in-scope contracts.

OpenZeppelin Contracts dependencies are out of scope because they have been independently audited and are widely used in production. The auditor should assume OpenZeppelin implementations are correct and focus on how we use them, including whether we override functions correctly in our inheritance hierarchy.

The Pyth Network contract on the host chain is out of scope because it is maintained by the Pyth Data Association and has been audited separately. The auditor should assume that when our oracle calls Pyth's `getPriceNoOlderThan()`, Pyth correctly returns either a fresh valid price or reverts. Our responsibility is to handle both outcomes correctly on our side.

Chainlink price feeds are out of scope for the same reason. The auditor should assume that `latestRoundData()` returns the documented tuple and that timestamps and answers are what they claim to be. Our responsibility is to validate the timestamp against staleness thresholds and to reject non-positive answers.

Off-chain keeper bots, subgraph mapping code, and frontend integration code are out of scope for the smart contract audit, but may be covered by separate operational security review. The auditor is encouraged to flag any on-chain attack surface that depends on off-chain components being honest, because such dependencies are often where vulnerabilities hide.

## 6. Attack Surface Summary

The most critical attack surface is the oracle manipulation path. If an attacker can move the GDSI composite value to a target of their choice, they can profit by opening a position, triggering the move, and closing for a large profit. The protocol's primary defenses against this are the multi-source aggregation (no single source can carry the median), the deviation circuit breaker (large jumps require governor approval), and the confidence interval filter on Pyth data (wide uncertainty bands are rejected). The auditor should attempt to find paths that bypass any of these defenses.

The second critical surface is the recursive `expressThesis()` flow. Any reentrancy between the four sub-calls, any path that lets one contract's state get out of sync with another's, or any revert handling that leaves partial state is a potential critical finding. The auditor should verify that `nonReentrant` is applied correctly and that no user-controlled call between the sub-calls can execute.

The third critical surface is the liquidation flow in both the vault and the perp engine. Liquidations are where the most money changes hands in DeFi exploits, usually because of bonus miscalculations, price manipulation, or insolvency handling bugs. The auditor should pay particular attention to the close factor cap enforcement in the vault and the insurance fund balance logic in the perp engine.

## 7. Build and Test Instructions

The protocol uses Foundry as its development toolchain. To build and test:

```
forge install
forge build
forge test -vvv
```

The test suite in `test/DebtInheritanceProtocol.t.sol` covers basic integration flows but is not exhaustive. The auditor is encouraged to add adversarial test cases and to run Foundry's fuzzing and invariant testing on the contracts:

```
forge test --fuzz-runs 10000
forge test --match-contract Invariant
```

Static analysis can be run with Slither:

```
slither src/ --config-file audit/slither.config.json
```

---

*This document is a living specification. Any update to the protocol's trust model, invariants, or scope must be accompanied by an update to this document before the next audit review.*
