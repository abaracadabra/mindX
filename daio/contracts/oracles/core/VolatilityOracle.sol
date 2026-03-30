// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./PriceFeedAggregator.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title VolatilityOracle
 * @notice Risk management for DAIO treasury with volatility tracking and risk scoring
 * @dev Calculates volatility metrics and risk scores for treasury asset allocation decisions
 */
contract VolatilityOracle is AccessControl, ReentrancyGuard, Pausable {

    bytes32 public constant RISK_MANAGER_ROLE = keccak256("RISK_MANAGER_ROLE");
    bytes32 public constant TREASURY_ROLE = keccak256("TREASURY_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");

    // Volatility calculation parameters
    struct VolatilityConfig {
        uint256 windowSize;          // Number of price points for calculation
        uint256 updateFrequency;     // Minimum time between updates (seconds)
        uint256 highVolThreshold;    // High volatility threshold (BPS)
        uint256 extremeVolThreshold; // Extreme volatility threshold (BPS)
        uint256 decayFactor;         // Exponential decay factor for historical data
        bool enabled;                // Whether volatility tracking is enabled
    }

    struct VolatilityData {
        uint256 currentVolatility;   // Current volatility (BPS)
        uint256 averageVolatility;   // 30-day average volatility
        uint256 maxVolatility;       // Maximum volatility in period
        uint256 minVolatility;       // Minimum volatility in period
        uint256 lastUpdated;         // Last update timestamp
        uint256 sampleCount;         // Number of samples collected
        bool isHighVolatility;       // Whether asset is in high volatility regime
        bool isExtremeVolatility;    // Whether asset is in extreme volatility regime
    }

    struct RiskMetrics {
        uint256 riskScore;           // Overall risk score (0-10000, higher = riskier)
        uint256 valueAtRisk;         // Value at Risk (95% confidence, BPS)
        uint256 expectedShortfall;   // Expected Shortfall (BPS)
        uint256 sharpeRatio;         // Risk-adjusted return ratio (scaled by 1000)
        uint256 correlationRisk;     // Correlation with other portfolio assets
        uint256 liquidityRisk;       // Liquidity risk score
        uint256 lastCalculated;      // Last risk calculation timestamp
    }

    // DAIO constitutional integration
    struct TreasuryRiskLimits {
        uint256 maxSingleAssetVol;   // Maximum volatility for single asset (BPS)
        uint256 maxPortfolioVol;     // Maximum portfolio volatility (BPS)
        uint256 maxCorrelation;      // Maximum correlation between assets (BPS)
        uint256 minLiquidityScore;   // Minimum liquidity score required
        uint256 riskBudget;          // Total risk budget (BPS)
        bool enforceConstitution;    // Whether to enforce constitutional limits
    }

    // State variables
    PriceFeedAggregator public immutable priceFeedAggregator;
    address public treasuryContract;
    address public constitutionContract;

    mapping(string => VolatilityConfig) public volatilityConfigs;
    mapping(string => VolatilityData) public volatilityData;
    mapping(string => RiskMetrics) public riskMetrics;
    mapping(string => uint256[]) private priceHistory; // asset -> price history
    mapping(string => uint256[]) private returnHistory; // asset -> return history

    TreasuryRiskLimits public treasuryLimits;
    string[] public trackedAssets;

    // Portfolio-level tracking
    mapping(string => mapping(string => int256)) public assetCorrelations; // asset1 -> asset2 -> correlation (scaled)
    uint256 public portfolioVolatility;
    uint256 public portfolioRiskScore;
    uint256 public lastPortfolioUpdate;

    // Performance tracking
    uint256 public totalRiskAssessments;
    uint256 public riskAlertsTriggered;
    uint256 public constitutionalViolations;

    // Events
    event VolatilityUpdated(
        string indexed asset,
        uint256 volatility,
        uint256 riskScore,
        bool isHighVol
    );
    event RiskThresholdExceeded(
        string indexed asset,
        uint256 riskScore,
        uint256 threshold,
        string riskType
    );
    event ConstitutionalRiskViolation(
        string indexed asset,
        string violationType,
        uint256 value,
        uint256 limit
    );
    event PortfolioRiskUpdated(
        uint256 portfolioVolatility,
        uint256 portfolioRiskScore,
        uint256 assetsCount
    );
    event EmergencyRiskAlert(
        string indexed asset,
        uint256 volatility,
        uint256 extremeThreshold
    );
    event TreasuryRiskLimitsUpdated(
        uint256 maxSingleAssetVol,
        uint256 maxPortfolioVol,
        uint256 riskBudget
    );

    /**
     * @notice Initialize VolatilityOracle with DAIO treasury integration
     * @param _priceFeedAggregator Address of price feed aggregator
     * @param _treasuryContract DAIO treasury contract
     * @param _constitutionContract DAIO constitution contract
     * @param admin Admin address for role management
     */
    constructor(
        address _priceFeedAggregator,
        address _treasuryContract,
        address _constitutionContract,
        address admin
    ) {
        require(_priceFeedAggregator != address(0), "Price aggregator cannot be zero address");
        require(admin != address(0), "Admin cannot be zero address");

        priceFeedAggregator = PriceFeedAggregator(_priceFeedAggregator);
        treasuryContract = _treasuryContract;
        constitutionContract = _constitutionContract;

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(RISK_MANAGER_ROLE, admin);
        _grantRole(TREASURY_ROLE, admin);
        _grantRole(EMERGENCY_ROLE, admin);

        // Set default treasury risk limits aligned with DAIO constitution
        _setDefaultTreasuryLimits();
    }

    /**
     * @notice Configure volatility tracking for an asset
     * @param asset Asset symbol
     * @param windowSize Number of price points for calculation
     * @param updateFrequency Minimum time between updates
     * @param highVolThreshold High volatility threshold (BPS)
     * @param extremeVolThreshold Extreme volatility threshold (BPS)
     */
    function configureVolatilityTracking(
        string memory asset,
        uint256 windowSize,
        uint256 updateFrequency,
        uint256 highVolThreshold,
        uint256 extremeVolThreshold
    ) external onlyRole(RISK_MANAGER_ROLE) {
        require(bytes(asset).length > 0, "Asset cannot be empty");
        require(windowSize >= 10, "Window size too small");
        require(updateFrequency >= 300, "Update frequency too high"); // Min 5 minutes
        require(highVolThreshold <= extremeVolThreshold, "Invalid threshold configuration");

        volatilityConfigs[asset] = VolatilityConfig({
            windowSize: windowSize,
            updateFrequency: updateFrequency,
            highVolThreshold: highVolThreshold,
            extremeVolThreshold: extremeVolThreshold,
            decayFactor: 9500, // 0.95 decay factor
            enabled: true
        });

        // Initialize tracking if new asset
        if (volatilityData[asset].lastUpdated == 0) {
            trackedAssets.push(asset);

            volatilityData[asset] = VolatilityData({
                currentVolatility: 0,
                averageVolatility: 0,
                maxVolatility: 0,
                minVolatility: type(uint256).max,
                lastUpdated: block.timestamp,
                sampleCount: 0,
                isHighVolatility: false,
                isExtremeVolatility: false
            });
        }
    }

    /**
     * @notice Update volatility and risk metrics for an asset
     * @param asset Asset symbol
     */
    function updateVolatilityMetrics(string memory asset) external nonReentrant whenNotPaused {
        require(volatilityConfigs[asset].enabled, "Volatility tracking not enabled");
        require(
            block.timestamp >= volatilityData[asset].lastUpdated + volatilityConfigs[asset].updateFrequency,
            "Update frequency not met"
        );

        // Get latest price from aggregator
        (uint256 price, uint256 timestamp, uint256 confidence, bool isValid) =
            priceFeedAggregator.getPrice(asset);

        require(isValid && confidence >= 7500, "Invalid price data"); // Require 75% confidence

        // Update price history
        _updatePriceHistory(asset, price);

        // Calculate volatility if we have enough data
        uint256 windowSize = volatilityConfigs[asset].windowSize;
        if (priceHistory[asset].length >= windowSize) {
            uint256 volatility = _calculateVolatility(asset);
            _updateVolatilityData(asset, volatility);

            // Calculate risk metrics
            _calculateRiskMetrics(asset, volatility);

            // Check constitutional compliance
            _validateTreasuryRiskLimits(asset);

            totalRiskAssessments++;
        }

        // Update portfolio-level metrics
        _updatePortfolioRisk();
    }

    /**
     * @notice Get volatility data for an asset
     * @param asset Asset symbol
     * @return volatilityInfo Current volatility data
     */
    function getVolatilityData(string memory asset) external view returns (VolatilityData memory volatilityInfo) {
        return volatilityData[asset];
    }

    /**
     * @notice Get risk metrics for an asset
     * @param asset Asset symbol
     * @return riskInfo Current risk metrics
     */
    function getRiskMetrics(string memory asset) external view returns (RiskMetrics memory riskInfo) {
        return riskMetrics[asset];
    }

    /**
     * @notice Get treasury risk assessment for allocation decision
     * @param asset Asset symbol
     * @param allocationAmount Amount to allocate
     * @param currentPortfolioValue Current total portfolio value
     * @return isAllowed Whether allocation meets risk limits
     * @return riskAssessment Risk assessment details
     */
    function assessTreasuryAllocation(
        string memory asset,
        uint256 allocationAmount,
        uint256 currentPortfolioValue
    ) external view onlyRole(TREASURY_ROLE) returns (
        bool isAllowed,
        string memory riskAssessment
    ) {
        VolatilityData memory volData = volatilityData[asset];
        RiskMetrics memory riskData = riskMetrics[asset];

        // Check single asset volatility limit
        if (volData.currentVolatility > treasuryLimits.maxSingleAssetVol) {
            return (false, "Asset volatility exceeds treasury limits");
        }

        // Check asset concentration (15% diversification limit from constitution)
        uint256 assetPercentage = (allocationAmount * 10000) / currentPortfolioValue;
        if (assetPercentage > 1500) { // 15% constitutional limit
            return (false, "Allocation exceeds constitutional diversification limit");
        }

        // Check risk score
        if (riskData.riskScore > 8000) { // 80% risk score threshold
            return (false, "Asset risk score too high for treasury allocation");
        }

        // Check liquidity requirements
        if (riskData.liquidityRisk > (10000 - treasuryLimits.minLiquidityScore)) {
            return (false, "Asset liquidity insufficient for treasury");
        }

        // Simulate portfolio impact
        uint256 newPortfolioRisk = _simulatePortfolioRisk(asset, allocationAmount, currentPortfolioValue);
        if (newPortfolioRisk > treasuryLimits.maxPortfolioVol) {
            return (false, "Allocation would exceed portfolio volatility limits");
        }

        return (true, "Allocation approved within risk limits");
    }

    /**
     * @notice Get portfolio-wide risk metrics
     * @return portfolioVol Current portfolio volatility
     * @return portfolioRisk Current portfolio risk score
     * @return assetCount Number of assets in portfolio
     * @return lastUpdate Last portfolio update timestamp
     */
    function getPortfolioRisk() external view returns (
        uint256 portfolioVol,
        uint256 portfolioRisk,
        uint256 assetCount,
        uint256 lastUpdate
    ) {
        return (portfolioVolatility, portfolioRiskScore, trackedAssets.length, lastPortfolioUpdate);
    }

    /**
     * @notice Update treasury risk limits
     * @param maxSingleAssetVol Maximum single asset volatility (BPS)
     * @param maxPortfolioVol Maximum portfolio volatility (BPS)
     * @param maxCorrelation Maximum asset correlation (BPS)
     * @param minLiquidityScore Minimum liquidity score
     * @param riskBudget Total risk budget (BPS)
     */
    function updateTreasuryRiskLimits(
        uint256 maxSingleAssetVol,
        uint256 maxPortfolioVol,
        uint256 maxCorrelation,
        uint256 minLiquidityScore,
        uint256 riskBudget
    ) external onlyRole(RISK_MANAGER_ROLE) {
        require(maxSingleAssetVol <= 5000, "Single asset volatility limit too high"); // Max 50%
        require(maxPortfolioVol <= 3000, "Portfolio volatility limit too high"); // Max 30%
        require(maxCorrelation <= 8000, "Correlation limit too high"); // Max 80%
        require(minLiquidityScore <= 10000, "Liquidity score invalid");
        require(riskBudget <= 2500, "Risk budget too high"); // Max 25%

        treasuryLimits.maxSingleAssetVol = maxSingleAssetVol;
        treasuryLimits.maxPortfolioVol = maxPortfolioVol;
        treasuryLimits.maxCorrelation = maxCorrelation;
        treasuryLimits.minLiquidityScore = minLiquidityScore;
        treasuryLimits.riskBudget = riskBudget;

        emit TreasuryRiskLimitsUpdated(maxSingleAssetVol, maxPortfolioVol, riskBudget);
    }

    /**
     * @notice Emergency stop volatility tracking for an asset
     * @param asset Asset symbol
     */
    function emergencyStopTracking(string memory asset) external onlyRole(EMERGENCY_ROLE) {
        volatilityConfigs[asset].enabled = false;
        volatilityData[asset].isHighVolatility = true;
        volatilityData[asset].isExtremeVolatility = true;

        emit EmergencyRiskAlert(asset, volatilityData[asset].currentVolatility, 0);
    }

    // Internal functions

    function _updatePriceHistory(string memory asset, uint256 price) internal {
        priceHistory[asset].push(price);

        // Maintain window size
        uint256 windowSize = volatilityConfigs[asset].windowSize;
        if (priceHistory[asset].length > windowSize * 2) {
            // Remove oldest half of data to maintain efficiency
            uint256[] storage prices = priceHistory[asset];
            uint256 keepFrom = prices.length - windowSize;

            for (uint256 i = 0; i < windowSize; i++) {
                prices[i] = prices[keepFrom + i];
            }

            // Adjust array length
            assembly {
                sstore(add(priceHistory.slot, keccak256(abi.encode(asset))), windowSize)
            }
        }

        // Calculate returns if we have previous price
        if (priceHistory[asset].length > 1) {
            uint256 prevPrice = priceHistory[asset][priceHistory[asset].length - 2];
            int256 return_ = int256((price * 10000) / prevPrice) - 10000; // BPS return
            returnHistory[asset].push(uint256(return_ < 0 ? -return_ : return_)); // Store absolute return for volatility calc
        }
    }

    function _calculateVolatility(string memory asset) internal view returns (uint256) {
        uint256[] storage returns = returnHistory[asset];
        uint256 windowSize = volatilityConfigs[asset].windowSize;
        uint256 dataLength = returns.length;

        if (dataLength < 2) return 0;

        uint256 startIdx = dataLength > windowSize ? dataLength - windowSize : 0;
        uint256 sampleSize = dataLength - startIdx;

        // Calculate mean return
        uint256 meanReturn = 0;
        for (uint256 i = startIdx; i < dataLength; i++) {
            meanReturn += returns[i];
        }
        meanReturn = meanReturn / sampleSize;

        // Calculate variance
        uint256 variance = 0;
        for (uint256 i = startIdx; i < dataLength; i++) {
            uint256 diff = returns[i] > meanReturn ? returns[i] - meanReturn : meanReturn - returns[i];
            variance += diff * diff;
        }
        variance = variance / sampleSize;

        // Return square root of variance (volatility) scaled to BPS
        return _sqrt(variance);
    }

    function _updateVolatilityData(string memory asset, uint256 volatility) internal {
        VolatilityData storage data = volatilityData[asset];
        VolatilityConfig memory config = volatilityConfigs[asset];

        // Update current volatility
        data.currentVolatility = volatility;
        data.lastUpdated = block.timestamp;
        data.sampleCount++;

        // Update exponential moving average
        if (data.averageVolatility == 0) {
            data.averageVolatility = volatility;
        } else {
            data.averageVolatility = (data.averageVolatility * config.decayFactor +
                                   volatility * (10000 - config.decayFactor)) / 10000;
        }

        // Update min/max
        if (volatility > data.maxVolatility) {
            data.maxVolatility = volatility;
        }
        if (volatility < data.minVolatility) {
            data.minVolatility = volatility;
        }

        // Update volatility regime flags
        bool wasHighVol = data.isHighVolatility;
        data.isHighVolatility = volatility > config.highVolThreshold;
        data.isExtremeVolatility = volatility > config.extremeVolThreshold;

        // Trigger alerts
        if (data.isExtremeVolatility) {
            emit EmergencyRiskAlert(asset, volatility, config.extremeVolThreshold);
            riskAlertsTriggered++;
        } else if (data.isHighVolatility && !wasHighVol) {
            emit RiskThresholdExceeded(asset, volatility, config.highVolThreshold, "HIGH_VOLATILITY");
            riskAlertsTriggered++;
        }

        emit VolatilityUpdated(asset, volatility, riskMetrics[asset].riskScore, data.isHighVolatility);
    }

    function _calculateRiskMetrics(string memory asset, uint256 volatility) internal {
        RiskMetrics storage metrics = riskMetrics[asset];

        // Calculate base risk score (volatility weighted)
        uint256 baseRiskScore = volatility * 100 / 100; // Scale volatility to risk score

        // Adjust for liquidity (simplified - in production would use DEX liquidity data)
        uint256 liquidityRisk = _estimateLiquidityRisk(asset);

        // Calculate Value at Risk (95% confidence)
        uint256 valueAtRisk = volatility * 196 / 100; // ~1.96 * volatility for 95% confidence

        // Calculate Expected Shortfall (simplified)
        uint256 expectedShortfall = valueAtRisk * 130 / 100; // ~1.3 * VaR

        // Calculate overall risk score
        uint256 riskScore = (baseRiskScore * 6000 + liquidityRisk * 4000) / 10000;
        if (riskScore > 10000) riskScore = 10000;

        // Update metrics
        metrics.riskScore = riskScore;
        metrics.valueAtRisk = valueAtRisk;
        metrics.expectedShortfall = expectedShortfall;
        metrics.liquidityRisk = liquidityRisk;
        metrics.lastCalculated = block.timestamp;

        // Calculate Sharpe ratio (simplified - would need yield data in production)
        metrics.sharpeRatio = volatility > 0 ? (500 * 1000) / volatility : 0; // Assume 5% risk-free rate
    }

    function _estimateLiquidityRisk(string memory asset) internal pure returns (uint256) {
        // Simplified liquidity risk estimation
        // In production, this would query DEX liquidity, order book depth, etc.

        if (keccak256(bytes(asset)) == keccak256(bytes("ETH")) ||
            keccak256(bytes(asset)) == keccak256(bytes("BTC"))) {
            return 1000; // 10% liquidity risk for major assets
        } else if (keccak256(bytes(asset)) == keccak256(bytes("USDC")) ||
                  keccak256(bytes(asset)) == keccak256(bytes("USDT"))) {
            return 500; // 5% liquidity risk for stablecoins
        } else {
            return 3000; // 30% liquidity risk for other assets
        }
    }

    function _validateTreasuryRiskLimits(string memory asset) internal {
        if (!treasuryLimits.enforceConstitution) return;

        VolatilityData memory volData = volatilityData[asset];
        RiskMetrics memory riskData = riskMetrics[asset];

        // Check single asset volatility limit
        if (volData.currentVolatility > treasuryLimits.maxSingleAssetVol) {
            emit ConstitutionalRiskViolation(
                asset,
                "ASSET_VOLATILITY",
                volData.currentVolatility,
                treasuryLimits.maxSingleAssetVol
            );
            constitutionalViolations++;
        }

        // Check risk score limit
        if (riskData.riskScore > (10000 - treasuryLimits.riskBudget)) {
            emit ConstitutionalRiskViolation(
                asset,
                "RISK_SCORE",
                riskData.riskScore,
                (10000 - treasuryLimits.riskBudget)
            );
            constitutionalViolations++;
        }
    }

    function _updatePortfolioRisk() internal {
        uint256 totalAssets = trackedAssets.length;
        if (totalAssets == 0) return;

        uint256 weightedVolatility = 0;
        uint256 totalRiskScore = 0;

        for (uint256 i = 0; i < totalAssets; i++) {
            string memory asset = trackedAssets[i];
            VolatilityData memory volData = volatilityData[asset];
            RiskMetrics memory riskData = riskMetrics[asset];

            // Simple equal weighting for portfolio metrics
            // In production, would use actual portfolio weights
            weightedVolatility += volData.currentVolatility / totalAssets;
            totalRiskScore += riskData.riskScore / totalAssets;
        }

        portfolioVolatility = weightedVolatility;
        portfolioRiskScore = totalRiskScore;
        lastPortfolioUpdate = block.timestamp;

        emit PortfolioRiskUpdated(portfolioVolatility, portfolioRiskScore, totalAssets);
    }

    function _simulatePortfolioRisk(
        string memory newAsset,
        uint256 allocationAmount,
        uint256 currentPortfolioValue
    ) internal view returns (uint256) {
        uint256 newWeight = (allocationAmount * 10000) / (currentPortfolioValue + allocationAmount);
        uint256 assetVol = volatilityData[newAsset].currentVolatility;

        // Simplified portfolio volatility simulation
        // In production, would use full covariance matrix
        uint256 simulatedVol = (portfolioVolatility * (10000 - newWeight) + assetVol * newWeight) / 10000;

        return simulatedVol;
    }

    function _setDefaultTreasuryLimits() internal {
        treasuryLimits = TreasuryRiskLimits({
            maxSingleAssetVol: 2500,    // 25% maximum single asset volatility
            maxPortfolioVol: 2000,      // 20% maximum portfolio volatility
            maxCorrelation: 7000,       // 70% maximum correlation between assets
            minLiquidityScore: 7000,    // 70% minimum liquidity score
            riskBudget: 1500,           // 15% risk budget (aligns with constitution)
            enforceConstitution: true
        });
    }

    function _sqrt(uint256 x) internal pure returns (uint256) {
        if (x == 0) return 0;

        uint256 z = (x + 1) / 2;
        uint256 y = x;

        while (z < y) {
            y = z;
            z = (x / z + z) / 2;
        }

        return y;
    }

    /**
     * @notice Get tracked assets list
     * @return assets Array of all tracked asset symbols
     */
    function getTrackedAssets() external view returns (string[] memory assets) {
        return trackedAssets;
    }

    /**
     * @notice Emergency pause all operations
     */
    function emergencyPause() external onlyRole(EMERGENCY_ROLE) {
        _pause();
    }

    /**
     * @notice Unpause operations
     */
    function unpause() external onlyRole(EMERGENCY_ROLE) {
        _unpause();
    }
}