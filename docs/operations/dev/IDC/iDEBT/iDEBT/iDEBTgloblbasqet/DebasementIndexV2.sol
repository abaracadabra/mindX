// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

interface IDebtStressOracle {
    function latestPrice() external view returns (uint256, uint256);
    function stressLevel() external view returns (uint8);
}

interface IGlobalCurrencyBasket {
    function fiatDebasementIndex() external view returns (uint256);
}

interface IBitcoinAnchorOracle {
    function latestPrice() external view returns (uint256, uint256);
}

/**
 * @title DebasementIndexV2
 * @author Professor Codephreak — DELTAVERSE Ecosystem
 * @notice Second-generation debasement index. Combines the Global Debt Stress Index
 *         (GDSI) with the GlobalCurrencyBasket's basket-aware fiat debasement measure
 *         to produce a single scalar that reflects systemic, multi-currency debasement
 *         of the debt complex rather than bilateral movement of any one fiat pair.
 *
 * @dev Compared to V1 (DebasementIndex.sol):
 *      - V1 used raw BTC/USD price ratio against a baseline. Single bilateral pair.
 *      - V2 uses the GlobalCurrencyBasket's weighted multi-currency vs BTC measure.
 *
 *      The result composition: index = w_gdsi * gdsi_ratio + w_basket * basket_debasement
 *      where basket_debasement is already normalized to 1e18 at the basket's baseline.
 *
 *      This contract is upgrade-compatible with InverseDebtToken — both expose
 *      currentIndex() and btcEquivalent(uint256) views with identical semantics, so
 *      iDEBT can be reconfigured to read from V2 by changing the constructor argument
 *      at deployment time. Deployments that are already live on V1 can run both in
 *      parallel and migrate liquidity through the BitcoinProfitRecognizer.
 */
contract DebasementIndexV2 is AccessControl, Pausable {

    bytes32 public constant INDEX_MANAGER_ROLE = keccak256("INDEX_MANAGER_ROLE");
    uint256 public constant PRECISION = 1e18;
    uint256 public constant BPS_DENOM = 10_000;

    error ZeroAddress();
    error NotInitialized();
    error WeightSumInvalid();
    error OracleStale();

    IDebtStressOracle public immutable gdsiOracle;
    IGlobalCurrencyBasket public immutable basket;
    IBitcoinAnchorOracle public immutable btcOracle;  // for btcEquivalent reporting

    uint256 public baselineGdsi;
    uint256 public baselineTimestamp;

    /// @notice Default 30/70 split — basket is the heavier weight because it carries
    ///         the multi-currency view that the GDSI alone cannot capture.
    uint16 public gdsiWeightBps = 3000;
    uint16 public basketWeightBps = 7000;

    uint256 public maxOracleAge = 6 hours;

    event BaselineInitialized(uint256 gdsi, uint256 timestamp);
    event WeightsUpdated(uint16 gdsiWeightBps, uint16 basketWeightBps);

    constructor(
        address admin,
        address _gdsiOracle,
        address _basket,
        address _btcOracle
    ) {
        if (admin == address(0) || _gdsiOracle == address(0)
            || _basket == address(0) || _btcOracle == address(0))
            revert ZeroAddress();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(INDEX_MANAGER_ROLE, admin);
        gdsiOracle = IDebtStressOracle(_gdsiOracle);
        basket = IGlobalCurrencyBasket(_basket);
        btcOracle = IBitcoinAnchorOracle(_btcOracle);
    }

    function initializeBaseline() external onlyRole(INDEX_MANAGER_ROLE) {
        require(baselineGdsi == 0, "already initialized");
        (uint256 gdsi, uint256 gdsiTs) = gdsiOracle.latestPrice();
        require(gdsi > 0, "gdsi not ready");
        require(block.timestamp - gdsiTs <= maxOracleAge, "gdsi stale");
        baselineGdsi = gdsi;
        baselineTimestamp = block.timestamp;
        emit BaselineInitialized(gdsi, block.timestamp);
    }

    function setWeights(uint16 _gdsiWeightBps, uint16 _basketWeightBps)
        external onlyRole(INDEX_MANAGER_ROLE)
    {
        if (uint256(_gdsiWeightBps) + uint256(_basketWeightBps) != BPS_DENOM)
            revert WeightSumInvalid();
        gdsiWeightBps = _gdsiWeightBps;
        basketWeightBps = _basketWeightBps;
        emit WeightsUpdated(_gdsiWeightBps, _basketWeightBps);
    }

    function setMaxOracleAge(uint256 newAge) external onlyRole(INDEX_MANAGER_ROLE) {
        maxOracleAge = newAge;
    }

    /*//////////////////////////////////////////////////////////////
                        INDEX COMPUTATION
    //////////////////////////////////////////////////////////////*/

    function currentIndex() public view returns (uint256 index) {
        if (baselineGdsi == 0) revert NotInitialized();
        (uint256 gdsi, uint256 gdsiTs) = gdsiOracle.latestPrice();
        if (block.timestamp - gdsiTs > maxOracleAge) revert OracleStale();

        uint256 gdsiRatio = (gdsi * PRECISION) / baselineGdsi;
        uint256 basketDebasement = basket.fiatDebasementIndex();

        index = (gdsiRatio * gdsiWeightBps + basketDebasement * basketWeightBps) / BPS_DENOM;
    }

    function debasementBps() external view returns (int256) {
        uint256 idx = currentIndex();
        if (idx >= PRECISION) {
            return int256(((idx - PRECISION) * BPS_DENOM) / PRECISION);
        } else {
            return -int256(((PRECISION - idx) * BPS_DENOM) / PRECISION);
        }
    }

    function realValueMultiplier(uint256 usdcAmount) external view returns (uint256) {
        uint256 idx = currentIndex();
        return (usdcAmount * PRECISION) / idx;
    }

    function btcEquivalent(uint256 usdcAmount) external view returns (uint256 satoshis) {
        (uint256 btcPrice, uint256 btcTs) = btcOracle.latestPrice();
        if (block.timestamp - btcTs > maxOracleAge) revert OracleStale();
        require(btcPrice > 0, "btc price zero");
        uint256 usdc18 = usdcAmount * 1e12;
        uint256 btcUnits = (usdc18 * PRECISION) / btcPrice;
        satoshis = btcUnits / 1e10;
    }

    /// @notice Decompose the index into its two contributors for analytics.
    function indexComponents() external view returns (
        uint256 gdsiContribution,
        uint256 basketContribution,
        uint256 totalIndex
    ) {
        if (baselineGdsi == 0) revert NotInitialized();
        (uint256 gdsi, ) = gdsiOracle.latestPrice();
        uint256 gdsiRatio = (gdsi * PRECISION) / baselineGdsi;
        uint256 basketDebasement = basket.fiatDebasementIndex();
        gdsiContribution = (gdsiRatio * gdsiWeightBps) / BPS_DENOM;
        basketContribution = (basketDebasement * basketWeightBps) / BPS_DENOM;
        totalIndex = gdsiContribution + basketContribution;
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }
}
