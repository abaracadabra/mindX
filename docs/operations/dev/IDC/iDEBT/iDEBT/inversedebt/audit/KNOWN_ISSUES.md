# DELTAVERSE Debt Inheritance Protocol — Known Issues

**Version:** 1.0
**Purpose:** Disclosure of design compromises, accepted limitations, and deferred work known to the team at the time of audit submission.

This document exists so that auditors can focus their time on genuinely unknown risks rather than rediscovering things the team has already considered. Each entry below describes an issue, explains why the current design accepts it, and states what conditions would cause us to revisit the decision.

---

## Issue 1: Oracle Reporter Minimum Count Defaults to One

The `DeltaVerseDebtOracle` allows the admin to configure the minimum number of reporter submissions required to finalize a sub-index from reporter data alone. The default value at deployment is one, which means a single reporter's submission can carry a sub-index's finalization if no Chainlink or Pyth sources are configured for that sub-index.

A single-reporter configuration is a documented trust dependency. It exists because some of the macroeconomic data we want to represent in the composite index, particularly the Sovereign Debt Ratio and the Refinancing Pressure Index, do not have natural Chainlink or Pyth equivalents and must come from a curated off-chain source initially. A production deployment should raise the minimum to three or more reporters as soon as multiple independent data providers are operational, and governance should be used to update this parameter.

Auditors should verify that a single malicious reporter can at most submit their own value to the median and cannot amplify it, and that the deviation circuit breaker still catches large jumps even in the single-reporter case.

## Issue 2: Pyth Confidence Interval Filter Is a Hard Gate

When reading from Pyth, the oracle rejects price updates where the confidence interval exceeds a configurable fraction of the price itself. This protects against Pyth reporting low-confidence data during market stress. However, the rejection is a hard gate with no graceful degradation: if all Pyth updates in a given window have wide confidence intervals, the Pyth source is fully excluded from the composite for that window, and the composite falls back to Chainlink and reporter data alone.

During a real market crisis, Pyth's confidence intervals are expected to widen, which is exactly when the oracle is most needed. The accepted compromise is that a crisis-time composite using only Chainlink and reporter data is more trustworthy than a composite polluted by low-confidence Pyth data, but it means the oracle's freshness during the most critical moments depends on non-Pyth sources being responsive. Mitigations include running reporter bots with elevated priority during high-volatility periods and having governance adjust the confidence threshold if it proves too strict.

## Issue 3: Close Factor Cap Can Leave Dust Positions

The `CrossCollateralVault` caps liquidation repayment at fifty percent of the user's total debt per liquidation transaction. This is a standard Aave-style protection against over-liquidation, but it has a known edge case: a liquidator who is forced to leave fifty percent of the debt outstanding may find that the remaining debt is smaller than the gas cost of a second liquidation call, and they simply walk away. The protocol is then left with a dust position that accrues interest indefinitely.

The accepted compromise is that dust positions represent a minor ongoing drag on the protocol treasury but do not pose a solvency risk, because they are by definition small. A future version may introduce a dust-sweeper keeper that liquidates positions below a threshold at a bonus rate. For now, auditors should verify that dust positions cannot grow into structural problems and that the interest accrual on them is correctly accounted.

## Issue 4: PerpetualEngine Funding Rate Uses Simple Open Interest Imbalance

The funding rate calculation in `PerpetualEngine` is based on a simple imbalance between long and short open interest, multiplied by a configurable sensitivity factor. This is simpler than the funding rate formulas used by mature venues like dYdX or GMX, which incorporate premium-to-mark-price convergence and time-weighted averaging.

The simpler formula is sufficient for the protocol's current scale and can be tuned by governance if it produces undesirable behavior. The accepted compromise is that the funding rate may be noisier than ideal during low-liquidity periods, which is acceptable because the primary users of the perp engine in this protocol are thesis-expressers rather than high-frequency traders. If the engine becomes a standalone venue with significant independent volume, the funding formula should be upgraded to a premium-converging model.

## Issue 5: Emergency Pauser Uses Low-Level Call to Tolerate Interface Variation

The `EmergencyPauser` contract invokes `pause()` and `unpause()` on its managed contracts using low-level `call` rather than a typed `IPausable` interface. This is deliberate: it tolerates the case where the managed contracts have a compatible `pause()` selector without formally implementing `IPausable`, which is the actual situation in our stack where different contracts inherit from different pausable implementations.

The accepted risk is that a misconfiguration in `managedContracts` could point at a contract whose `pause()` has unexpected semantics, and the low-level call would still succeed without reverting. Governance is expected to verify each contract address before adding it to the managed set, and the `addManagedContract` function is gated on `DEFAULT_ADMIN_ROLE` to ensure this verification happens through the Timelock review process.

## Issue 6: Keeper Dependence for Oracle Freshness

The oracle's freshness depends entirely on off-chain keepers calling `updatePythFeeds`, `finalizeSubIndex`, and `updateComposite`. If all keepers go offline simultaneously, the oracle's `isHeartbeatAlive()` will return false within the configured heartbeat window, and the `DebtInheritanceProtocol` will revert all mint and burn operations with the `OracleStale` error.

This is a graceful degradation: the protocol fails closed rather than open, so no incorrect prices are used. But it is a liveness risk, because a coordinated keeper outage disables the protocol even though no funds are at risk. The accepted mitigation is running multiple independent keepers in geographically distributed infrastructure, with alerting configured to page the ops team if any keeper falls behind. The open-source keeper code allows third parties to run their own keepers if they wish, providing defense in depth.

## Issue 7: sGDSI ERC-20 Transfers Are Not Reflected in Subgraph User Balances

The subgraph mapping tracks sGDSI balances on the `User` entity by observing `SGdsiMinted` and `SGdsiBurned` events. It does not observe standard ERC-20 `Transfer` events. This means that if a user sends sGDSI to another user via a plain transfer, the sender's balance in the subgraph remains artificially high and the receiver's balance remains artificially low until one of them interacts with the mint or burn functions.

This is a known incompleteness in the indexer, not in the contract. The contract's actual balances are always correct. The subgraph limitation affects UI displays of "your balance" if the UI relies on the subgraph rather than reading `balanceOf` directly. The recommended mitigation for the frontend is to query `balanceOf` for authoritative balance display and use the subgraph only for history and aggregates. A future version of the subgraph should add a Transfer event handler.

## Issue 8: Governance Token Not Yet Deployed

The `DeltaVerseGovernor` accepts any `IVotes`-compatible ERC20 token. The intended governance token for the DELTAVERSE ecosystem is THRUST, but THRUST at the time of this audit does not implement `IVotes` and may need to be wrapped or migrated. The initial deployment of the Governor may use a placeholder token until the governance token decision is finalized.

The accepted compromise is that governance during the initial deployment phase will be held by the DELTAVERSE multisig acting as a de facto proxy for the eventual token holder community. The transition to token-weighted governance is a future milestone that requires its own planning and audit, and this document acknowledges that the current contract code supports the transition but the operational path is not yet fully defined.

## Issue 9: No Flash Loan Protection on sGDSI Mint and Burn

The `mintSGdsi` and `burnSGdsi` functions do not prevent the caller from borrowing flash-loaned stablecoin, minting sGDSI, and burning it in the same transaction. This is by design: sGDSI is a synthetic token with transparent pricing from the oracle, and flash-loaned mint-burn cycles cannot profit from it because the price is the same on both sides of the trade minus the fees.

However, a sufficiently sophisticated attacker might try to combine sGDSI mint-burn with oracle manipulation in the same transaction. The oracle's deviation circuit breaker, staleness checks, and multi-source aggregation are the defenses against this. The auditor should verify that no execution path allows a single transaction to both move the oracle and trade against it, because that is the canonical flash-loan exploit pattern and the most important thing to rule out.

## Issue 10: Fee Routing Is Gas-Bounded But Not Time-Bounded

The `routeFees` function on `DebtInheritanceProtocol` transfers all `pendingFees` to the oracle's LP staking pool in a single transaction. If the number of LP stakers grows very large, the gas cost of `depositRewards` inside the oracle could in principle grow unboundedly. In practice, `depositRewards` uses an accumulator pattern that is O(1) regardless of staker count, so this concern is theoretical.

The auditor should verify that the accumulator pattern in the oracle's LP pool correctly handles the case of rewards being added when total staked supply is zero (in which case the rewards should either be held until someone stakes or returned to the caller, but should not be lost). The current implementation's behavior in this corner case should be explicitly confirmed.

---

*This document should be updated whenever a new issue is identified or an existing issue is resolved. The auditor's final report should cross-reference this document to indicate which issues were verified, which were escalated, and which remain open.*
