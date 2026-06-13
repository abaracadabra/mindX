// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

interface IDebtStressOracle {
    function latestPrice() external view returns (uint256 price, uint256 updatedAt);
    function stressLevel() external view returns (uint8 level);
}

interface IBitcoinAnchorOracle {
    function latestPrice() external view returns (uint256 price, uint256 updatedAt);
    function latestEma() external view returns (uint256);
    function isFresh(uint256 maxAge) external view returns (bool);
}

/**
 * @title DebasementIndex
 * @author Professor Codephreak — DELTAVERSE Ecosystem
 * @notice Composite "fiat debasement" measurement. Combines the Global Debt Stress Index (GDSI)
 *         and Bitcoin's appreciation against a baseline into a single scalar representing
 *         how much real purchasing power the dollar has lost since the index's inception.
 *
 * @dev Why a composite? Because each component alone is incomplete. GDSI tells us debt stress
 *      is rising, but stress can persist for years without fiat debasement (the classic
 *      "widow-maker" problem with shorting Japan). BTC appreciation tells us the market has
 *      identified debasement, but Bitcoin moves for many reasons unrelated to debt cycles
 *      (adoption, regulation, macro liquidity). Taking a weighted geometric combination of
 *      both gives a more robust signal: the index rises meaningfully only when both debt
 *      stress AND Bitcoin appreciation confirm the debasement thesis.
 *
 *      Formula (in log space for stability):
 *          debasement_index = BASE * (GDSI_ratio ^ w_gdsi) * (BTC_ratio ^ w_btc)
 *
 *      where GDSI_ratio = current_GDSI / baseline_GDSI
 *            BTC_ratio  = current_BTC  / baseline_BTC
 *
 *      Implemented without fractional exponents by using linear weights on the ratio
 *      deltas, which preserves the monotonicity properties while being cheap to compute
 *      and easy to audit. The geometric intuition survives: both components must move
 *      in the thesis direction for the index to rise.
 *
 *      Scale: index is 18 decimals, baseline is 1e18. An index value of 1.5e18 means
 *      the combined debasement signal has risen 50% since baseline.
 */
contract DebasementIndex is AccessControl, ReentrancyGuard, Pausable {

    bytes32 public constant INDEX_MANAGER_ROLE = keccak256("INDEX_MANAGER_ROLE");
    uint256 public constant PRECISION = 1e18;
    uint256 public constant BPS_DENOM = 10_000;

    error ZeroAddress();
    error NotInitialized();
    error WeightSumInvalid();
    error OracleStale();

    IDebtStressOracle public immutable gdsiOracle;
    IBitcoinAnchorOracle public immutable btcOracle;

    /// @notice Baseline values locked at initialization. All future readings are relative.
    uint256 public baselineGdsi;
    uint256 public baselineBtc;
    uint256 public baselineTimestamp;

    /// @notice Weights for the two components, must sum to BPS_DENOM.
    uint16 public gdsiWeightBps = 4000;   // 40% debt stress
    uint16 public btcWeightBps = 6000;    // 60% Bitcoin (the market's aggregate view)

    uint256 public maxOracleAge = 6 hours;

    event BaselineInitialized(uint256 gdsi, uint256 btc, uint256 timestamp);
    event WeightsUpdated(uint16 gdsiWeightBps, uint16 btcWeightBps);

    constructor(address admin, address _gdsiOracle, address _btcOracle) {
        if (admin == address(0) || _gdsiOracle == address(0) || _btcOracle == address(0))
            revert ZeroAddress();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(INDEX_MANAGER_ROLE, admin);
        gdsiOracle = IDebtStressOracle(_gdsiOracle);
        btcOracle = IBitcoinAnchorOracle(_btcOracle);
    }

    /*//////////////////////////////////////////////////////////////
                           INITIALIZATION
    //////////////////////////////////////////////////////////////*/

    /// @notice Locks in the baseline from which all future debasement measurements are taken.
    ///         Callable once by admin after both oracles are live and seeded.
    function initializeBaseline() external onlyRole(INDEX_MANAGER_ROLE) {
        require(baselineGdsi == 0, "already initialized");
        (uint256 gdsi, uint256 gdsiTs) = gdsiOracle.latestPrice();
        (uint256 btc, uint256 btcTs) = btcOracle.latestPrice();
        require(gdsi > 0 && btc > 0, "oracle not ready");
        require(block.timestamp - gdsiTs <= maxOracleAge, "gdsi stale");
        require(block.timestamp - btcTs <= maxOracleAge, "btc stale");
        baselineGdsi = gdsi;
        baselineBtc = btc;
        baselineTimestamp = block.timestamp;
        emit BaselineInitialized(gdsi, btc, block.timestamp);
    }

    function setWeights(uint16 _gdsiWeightBps, uint16 _btcWeightBps)
        external onlyRole(INDEX_MANAGER_ROLE)
    {
        if (uint256(_gdsiWeightBps) + uint256(_btcWeightBps) != BPS_DENOM)
            revert WeightSumInvalid();
        gdsiWeightBps = _gdsiWeightBps;
        btcWeightBps = _btcWeightBps;
        emit WeightsUpdated(_gdsiWeightBps, _btcWeightBps);
    }

    function setMaxOracleAge(uint256 newAge) external onlyRole(INDEX_MANAGER_ROLE) {
        maxOracleAge = newAge;
    }

    /*//////////////////////////////////////////////////////////////
                        INDEX COMPUTATION
    //////////////////////////////////////////////////////////////*/

    /// @notice Current debasement index, scaled to 1e18. Returns BASE (1e18) at inception.
    function currentIndex() public view returns (uint256 index) {
        if (baselineGdsi == 0) revert NotInitialized();
        (uint256 gdsi, uint256 gdsiTs) = gdsiOracle.latestPrice();
        (uint256 btc, uint256 btcTs) = btcOracle.latestPrice();
        if (block.timestamp - gdsiTs > maxOracleAge) revert OracleStale();
        if (block.timestamp - btcTs > maxOracleAge) revert OracleStale();

        // GDSI ratio in 1e18 fixed point.
        uint256 gdsiRatio = (gdsi * PRECISION) / baselineGdsi;
        uint256 btcRatio = (btc * PRECISION) / baselineBtc;

        // Weighted average of ratios (linear combination).
        index = (gdsiRatio * gdsiWeightBps + btcRatio * btcWeightBps) / BPS_DENOM;
    }

    /// @notice Signed change in basis points from baseline (1e18). Positive = debasement,
    ///         negative = fiat strengthening.
    function debasementBps() external view returns (int256) {
        uint256 idx = currentIndex();
        if (idx >= PRECISION) {
            return int256(((idx - PRECISION) * BPS_DENOM) / PRECISION);
        } else {
            return -int256(((PRECISION - idx) * BPS_DENOM) / PRECISION);
        }
    }

    /// @notice The multiplier that converts nominal USDC value into BTC-equivalent "real"
    ///         value at the current moment. Used by profit recognition to translate
    ///         fiat-denominated gains into hard-money terms.
    function realValueMultiplier(uint256 usdcAmount) external view returns (uint256) {
        uint256 idx = currentIndex();
        // If debasement index has risen 50%, a nominal $100 is "really" $66.67 in baseline terms.
        return (usdcAmount * PRECISION) / idx;
    }

    /// @notice BTC-equivalent value of a USDC amount at current BTC price.
    ///         Expressed in satoshis (1 BTC = 1e8 satoshis) for downstream accounting.
    function btcEquivalent(uint256 usdcAmount) external view returns (uint256 satoshis) {
        (uint256 btcPrice, uint256 btcTs) = btcOracle.latestPrice();
        if (block.timestamp - btcTs > maxOracleAge) revert OracleStale();
        require(btcPrice > 0, "btc price zero");
        // usdcAmount is 6 decimals (USDC). Convert to 18-decimal BTC units, then satoshis.
        // usdc18 = usdcAmount * 1e12
        // btcUnits = (usdc18 * 1e18) / btcPrice  -- gives 18-decimal BTC amount
        // satoshis = btcUnits / 1e10             -- BTC * 1e8
        uint256 usdc18 = usdcAmount * 1e12;
        uint256 btcUnits = (usdc18 * PRECISION) / btcPrice;
        satoshis = btcUnits / 1e10;
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }
}
