// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { AccessControl } from "@openzeppelin/contracts/access/AccessControl.sol";

import { IDebtOracle }            from "../interfaces/IDebtOracle.sol";
import { IGlobalDebtStressIndex } from "../interfaces/IGlobalDebtStressIndex.sol";
import { DebtMath }               from "../libraries/DebtMath.sol";

/// @title GlobalDebtStressIndex
/// @notice Aggregates seven oracle metrics into a single 0..1e18 stress score
///         and derives a discrete regime from threshold crossings.
/// @dev    Designed to be cheap to `poke()` (public keeper entry) and cheaper
///         to `score()`/`regime()` (pure reads). Weights are governance-set.
contract GlobalDebtStressIndex is IGlobalDebtStressIndex, AccessControl {
    using DebtMath for uint256;

    bytes32 public constant INDEX_ADMIN_ROLE = keccak256("INDEX_ADMIN_ROLE");

    IDebtOracle public immutable oracle;

    // Last computed snapshot.
    Snapshot private _snap;

    /// @notice Weights per metric, must sum to 1e18.
    /// @dev    Default weights: [debtGDP 25%, cds 20%, yield 15%, real 10%,
    ///         dxy 10%, vix 10%, gold 10%].
    uint256[7] public weights = [
        0.25e18, 0.20e18, 0.15e18, 0.10e18, 0.10e18, 0.10e18, 0.10e18
    ];

    // Regime thresholds (exclusive upper bounds).
    uint256 public calmMax     = 0.20e18;
    uint256 public elevatedMax = 0.40e18;
    uint256 public distressMax = 0.60e18;
    uint256 public crisisMax   = 0.80e18;
    // >= crisisMax → Default

    constructor(address oracle_, address admin) {
        require(oracle_ != address(0), "oracle=0");
        oracle = IDebtOracle(oracle_);
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(INDEX_ADMIN_ROLE, admin);
    }

    // -------------------------------------------------------------- //
    //                              ADMIN                             //
    // -------------------------------------------------------------- //

    function setWeights(uint256[7] calldata w) external onlyRole(INDEX_ADMIN_ROLE) {
        uint256 sum;
        for (uint256 i = 0; i < 7; ++i) sum += w[i];
        if (sum != 1e18) revert InvalidWeights();
        weights = w;
        emit WeightsUpdated(w);
    }

    function setThresholds(uint256 calm_, uint256 elev_, uint256 distress_, uint256 crisis_)
        external
        onlyRole(INDEX_ADMIN_ROLE)
    {
        require(calm_ < elev_ && elev_ < distress_ && distress_ < crisis_ && crisis_ <= 1e18, "monotone");
        calmMax = calm_; elevatedMax = elev_; distressMax = distress_; crisisMax = crisis_;
    }

    // -------------------------------------------------------------- //
    //                          CORE UPDATE                           //
    // -------------------------------------------------------------- //

    function poke() external returns (Snapshot memory s) {
        s = _compute();
        Regime prev = _snap.regime;
        _snap = s;
        emit IndexUpdated(s.index, s.regime, s.timestamp);
        if (s.regime != prev) emit RegimeTransition(prev, s.regime, s.timestamp);
    }

    // -------------------------------------------------------------- //
    //                              VIEWS                             //
    // -------------------------------------------------------------- //

    function latestSnapshot() external view returns (Snapshot memory) {
        return _snap;
    }

    function score() external view returns (uint256) {
        return _compute().index;
    }

    function regime() external view returns (Regime) {
        return _compute().regime;
    }

    // -------------------------------------------------------------- //
    //                           INTERNAL                             //
    // -------------------------------------------------------------- //

    function _compute() internal view returns (Snapshot memory s) {
        // Normalise raw oracle values into [0, 1e18] stress contributions via
        // a logistic transform. Each metric has its own calibration baseline.
        uint256 debtGDP  = _normDebtGDP(oracle.blended(IDebtOracle.Metric.SovereignDebtGDP));
        uint256 cds      = _normCds(oracle.blended(IDebtOracle.Metric.CDS5Y));
        uint256 yieldInv = _normYield(oracle.blended(IDebtOracle.Metric.YieldCurveInversion));
        uint256 realRate = _normReal(oracle.blended(IDebtOracle.Metric.RealRate));
        uint256 dxy      = _normDxy(oracle.blended(IDebtOracle.Metric.DXY));
        uint256 vix      = _normVix(oracle.blended(IDebtOracle.Metric.VIX));
        uint256 gold     = _normGold(oracle.blended(IDebtOracle.Metric.GoldRatio));

        uint256[7] memory c = [debtGDP, cds, yieldInv, realRate, dxy, vix, gold];
        uint256 idx = DebtMath.weightedSum(c, weights);

        s = Snapshot({
            index: idx,
            regime: _regimeFromIndex(idx),
            timestamp: uint64(block.timestamp),
            debtGDP: debtGDP,
            cds: cds,
            yieldInv: yieldInv,
            realRate: realRate,
            dxy: dxy,
            vix: vix,
            gold: gold
        });
    }

    function _regimeFromIndex(uint256 idx) internal view returns (Regime) {
        if (idx < calmMax)     return Regime.Calm;
        if (idx < elevatedMax) return Regime.Elevated;
        if (idx < distressMax) return Regime.Distress;
        if (idx < crisisMax)   return Regime.Crisis;
        return Regime.Default;
    }

    // ---- Component normalisers ----
    // Each converts a signed raw metric into a 0..1e18 contribution via the
    // DebtMath.logistic sigmoid after shifting by the calibration baseline.
    function _normDebtGDP(int256 v) internal pure returns (uint256) {
        // Baseline: 100% global debt/GDP is "neutral"; above rises, below falls.
        return DebtMath.logistic((v - int256(1e18)) * 2);
    }

    function _normCds(int256 v) internal pure returns (uint256) {
        // CDS basis points scaled into WAD externally.
        return DebtMath.logistic((v - int256(0.01e18)) * 100);
    }

    function _normYield(int256 v) internal pure returns (uint256) {
        // Inversion depth: negative = inverted = higher stress.
        return DebtMath.logistic(-v * 20);
    }

    function _normReal(int256 v) internal pure returns (uint256) {
        // High real rates = disinflationary stress on debtors.
        return DebtMath.logistic(v * 20);
    }

    function _normDxy(int256 v) internal pure returns (uint256) {
        // Baseline DXY 100 in WAD → 100e18/100 = 1e18.
        return DebtMath.logistic((v - int256(1e18)) * 5);
    }

    function _normVix(int256 v) internal pure returns (uint256) {
        // VIX 20 as neutral; higher = stressed.
        return DebtMath.logistic((v - int256(20e18)) / 10);
    }

    function _normGold(int256 v) internal pure returns (uint256) {
        // Gold / reserves ratio; above baseline signals risk-off.
        return DebtMath.logistic((v - int256(1e18)) * 3);
    }
}
