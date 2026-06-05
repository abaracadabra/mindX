# DELTAVERSE Debt Inheritance Protocol — Technical Reference

This document is the single technical reference for the protocol. It complements ARCHITECTURE.md (which teaches the mental model) and README.md (which gives the quickstart) by providing the precise parameters, interfaces, invariants, and operational thresholds an implementer needs to deploy, operate, and audit the system.

## Contract Parameters

The RWAToken is deployed with a name, symbol, human-readable description, ISIN identifier, maturity timestamp, coupon rate in basis points, supply cap, and yield-payment token address. Production values are chosen per instrument; the reference deployment uses a ten-year US Treasury analogue with four hundred basis points coupon and one hundred million token supply cap, with yield paid in USDC.

The CrossCollateralVault is deployed with the stablecoin address and its decimals (six for USDC). Assets are registered post-deployment via addAsset, specifying the ERC20 address, Chainlink feed, token decimals, collateral factor in basis points, oracle staleness threshold in seconds, and optional deposit cap. Recommended collateral factor for tokenized Treasuries is eighty-five hundred basis points (eighty-five percent), staleness threshold two hours, and close factor fifty percent enforced at liquidation time.

The PerpetualEngine is deployed with the stablecoin address, the oracle address, and the admin. Post-deployment the admin seeds the insurance fund via depositInsurance. Default maximum leverage is twenty, funding rate cap is eight hundred basis points annualized, liquidation bonus is one hundred basis points, and insurance cut is fifty basis points.

The DeltaVerseDebtOracle is deployed with the admin, the Pyth contract address, and the LP staking token (USDC in reference deployment). Sub-indices are registered post-deployment and weighted so that the five-sub-index composite sums to ten thousand basis points. The deviation circuit breaker defaults to one thousand basis points (ten percent), heartbeat six hours, and minimum reporter count one (raised to three in mature deployment).

The DebtInheritanceProtocol is deployed with the oracle, vault, perp engine, stablecoin, and admin. Mint and burn fees default to thirty basis points each; the base index is one thousand multiplied by ten to the eighteenth.

## Key Invariants

The first invariant is that sGDSI supply times current oracle price divided by base index must not exceed the protocol stablecoin balance minus pendingFees. The second is that a thesis position is either fully active across vault, perp, and capstone state or entirely absent with no partial state. The third is that the composite value equals the weighted average of non-stale sub-indices at every updateComposite call. The fourth is that a user's vault health factor cannot decrease from adding collateral and cannot increase from additional borrow. The fifth is that the insurance fund balance is non-negative at all times. The sixth is that admin operations on operational contracts route through the Timelock exclusively. The seventh is that pause is idempotent and that paused contracts reject state-changing calls while still serving views.

## Operational Thresholds

The Pyth updater runs every sixty seconds with a maximum gas price of one hundred gwei. The sub-index finalizer runs every four hours. The fee router runs hourly with a minimum pending-fee threshold of one hundred USDC. The liquidator scans every thirty seconds and uses transaction simulation before sending each liquidation to avoid paying gas for races lost to competing bots. The EmergencyPauser unpause cooldown is one hour after the last pause event.

## Governance Parameters

The Timelock minimum delay is forty-eight hours. The Governor voting delay is one day (7200 blocks at twelve seconds per block on mainnet), voting period is one week (50400 blocks), proposal threshold is one hundred thousand governance tokens, and quorum fraction is four percent of total supply at the proposal snapshot block.

## Deployment Order

Deploy in this order: stablecoin dependency (use existing USDC), Pyth dependency (use existing Pyth on the target chain), RWAToken, DeltaVerseDebtOracle, CrossCollateralVault, PerpetualEngine, DebtInheritanceProtocol, DeltaVerseTimelock, DeltaVerseGovernor, EmergencyPauser. Then configure collateral assets, oracle sources, initial sub-index submissions, insurance fund seed, stablecoin reserves, and RWAToken whitelist. Finally transfer DEFAULT_ADMIN_ROLE on all operational contracts to the Timelock, grant PROPOSER_ROLE on Timelock to the Governor, revoke deployer proposer rights, and renounce deployer admin rights.

## Integration Points

The frontend at agenticplace.pythai.net reads contract addresses from allchain.json, queries the subgraph for historical state, calls mindx.pythai.net for risk scoring before high-leverage operations, and calls bankon.pythai.net for identity credential verification before expressThesis. The x402 Algorand payment system from Parsec can be integrated as an alternative payment rail by wrapping mint and burn calls in a Parsec payment facade that accepts Algorand-denominated payments and settles to USDC on the target EVM chain.

## Testing and Verification

Run forge test with verbosity level three for integration tests. Run forge test with fuzz-runs ten thousand for property-based testing of the invariants above. Run slither with the provided config for static analysis. Run mythril with the provided config for symbolic execution of the capstone contract. For production deployment, additionally commission a third-party audit using SCOPE.md and KNOWN_ISSUES.md as the input brief.
