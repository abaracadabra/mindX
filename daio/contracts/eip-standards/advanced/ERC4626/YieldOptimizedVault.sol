// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./DAIO_ERC4626Vault.sol";
import "../../oracles/core/OracleRegistry.sol";
import "../../oracles/core/VolatilityOracle.sol";
import "../../oracles/core/PriceFeedAggregator.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title YieldOptimizedVault
 * @notice Oracle-driven yield strategies with automated optimization and risk management
 * @dev Extends DAIO_ERC4626Vault with sophisticated yield optimization using oracle data
 */
contract YieldOptimizedVault is DAIO_ERC4626Vault {

    // Yield strategy configuration
    struct YieldStrategy {
        address strategyContract;       // Strategy implementation contract
        string strategyType;           // "LENDING", "STAKING", "LP", "ARBITRAGE"
        uint256 allocation;            // Current allocation in BPS
        uint256 targetAllocation;      // Target allocation in BPS
        uint256 minAllocation;         // Minimum allocation in BPS
        uint256 maxAllocation;         // Maximum allocation in BPS
        uint256 expectedYield;         // Expected annual yield in BPS
        uint256 riskScore;            // Risk score (0-10000, higher = riskier)
        uint256 lastRebalance;        // Last rebalancing timestamp
        bool active;                  // Whether strategy is active
        bool emergency;               // Whether strategy is in emergency mode
    }

    struct YieldOptimizationConfig {
        uint256 rebalanceThreshold;    // Threshold for rebalancing (BPS)
        uint256 rebalanceFrequency;    // Minimum time between rebalances
        uint256 maxRiskScore;          // Maximum allowed risk score
        uint256 minYieldThreshold;     // Minimum yield threshold for strategy inclusion
        uint256 emergencyExitThreshold; // Risk threshold for emergency exit
        bool autoOptimizationEnabled; // Whether automatic optimization is enabled
        bool riskAdjustedReturns;     // Whether to use risk-adjusted return optimization
    }

    struct YieldMetrics {
        uint256 totalYieldGenerated;   // Cumulative yield generated
        uint256 currentAPY;           // Current annualized percentage yield
        uint256 sevenDayAPY;          // 7-day rolling APY
        uint256 thirtyDayAPY;         // 30-day rolling APY
        uint256 bestStrategyAPY;      // Best performing strategy APY
        uint256 worstStrategyAPY;     // Worst performing strategy APY
        uint256 portfolioRiskScore;   // Portfolio-wide risk score
        uint256 lastOptimization;     // Last optimization timestamp
    }

    // Oracle integration
    OracleRegistry public immutable oracleRegistry;
    VolatilityOracle public immutable volatilityOracle;
    PriceFeedAggregator public immutable priceFeedAggregator;

    // State variables
    mapping(uint256 => YieldStrategy) public yieldStrategies;
    mapping(string => uint256[]) public strategiesByType; // strategy type -> strategy IDs
    mapping(address => uint256) public strategyIdByContract; // contract -> strategy ID

    YieldOptimizationConfig public optimizationConfig;
    YieldMetrics public yieldMetrics;

    uint256[] public activeStrategyIds;
    uint256 public nextStrategyId = 1;

    // Historical tracking for APY calculations
    mapping(uint256 => uint256) public dailyYield; // day -> yield
    mapping(uint256 => uint256) public dailyAssets; // day -> total assets
    uint256 public constant SECONDS_PER_DAY = 86400;

    // Oracle-driven asset tracking
    mapping(string => uint256) public assetPrices; // asset symbol -> latest price
    mapping(string => uint256) public assetVolatilities; // asset symbol -> volatility
    mapping(string => bool) public supportedAssets; // assets we can optimize for
    string[] public trackedAssets;

    // Automated yield farming parameters
    uint256 public lastYieldHarvest;
    uint256 public harvestFrequency = 86400; // Daily harvest
    uint256 public totalHarvested;

    // Events
    event StrategyAdded(
        uint256 indexed strategyId,
        address strategyContract,
        string strategyType,
        uint256 targetAllocation
    );
    event StrategyRebalanced(
        uint256 indexed strategyId,
        uint256 oldAllocation,
        uint256 newAllocation,
        string reason
    );
    event YieldHarvested(
        uint256 totalYield,
        uint256 timestamp,
        uint256 newAPY
    );
    event EmergencyStrategyExit(
        uint256 indexed strategyId,
        uint256 withdrawnAmount,
        string reason
    );
    event OptimizationExecuted(
        uint256 totalStrategies,
        uint256 portfolioRiskScore,
        uint256 expectedAPY
    );
    event RiskThresholdExceeded(
        uint256 indexed strategyId,
        uint256 currentRisk,
        uint256 threshold
    );
    event OracleDataUpdated(
        string indexed asset,
        uint256 price,
        uint256 volatility
    );

    /**
     * @notice Initialize YieldOptimizedVault with oracle integration
     * @param _asset Underlying asset token
     * @param _name Vault token name
     * @param _symbol Vault token symbol
     * @param _oracleRegistry Oracle registry contract
     * @param _volatilityOracle Volatility oracle contract
     * @param _priceFeedAggregator Price feed aggregator contract
     * @param _treasuryContract DAIO treasury contract
     * @param _constitutionContract DAIO constitution contract
     * @param admin Admin address
     */
    constructor(
        IERC20 _asset,
        string memory _name,
        string memory _symbol,
        address _oracleRegistry,
        address _volatilityOracle,
        address _priceFeedAggregator,
        address _treasuryContract,
        address _constitutionContract,
        address admin
    ) DAIO_ERC4626Vault(
        _asset,
        _name,
        _symbol,
        _treasuryContract,
        _constitutionContract,
        admin
    ) {
        require(_oracleRegistry != address(0), "Oracle registry cannot be zero address");
        require(_volatilityOracle != address(0), "Volatility oracle cannot be zero address");
        require(_priceFeedAggregator != address(0), "Price aggregator cannot be zero address");

        oracleRegistry = OracleRegistry(_oracleRegistry);
        volatilityOracle = VolatilityOracle(_volatilityOracle);
        priceFeedAggregator = PriceFeedAggregator(_priceFeedAggregator);

        // Initialize optimization configuration
        optimizationConfig = YieldOptimizationConfig({
            rebalanceThreshold: 500,        // 5% threshold for rebalancing
            rebalanceFrequency: 86400,      // Daily rebalancing
            maxRiskScore: 7500,            // 75% maximum risk score
            minYieldThreshold: 500,         // 5% minimum yield for inclusion
            emergencyExitThreshold: 9000,   // 90% risk threshold for emergency exit
            autoOptimizationEnabled: true,
            riskAdjustedReturns: true
        });

        // Initialize yield metrics
        yieldMetrics = YieldMetrics({
            totalYieldGenerated: 0,
            currentAPY: 0,
            sevenDayAPY: 0,
            thirtyDayAPY: 0,
            bestStrategyAPY: 0,
            worstStrategyAPY: 0,
            portfolioRiskScore: 0,
            lastOptimization: block.timestamp
        });

        lastYieldHarvest = block.timestamp;

        // Initialize supported assets
        _initializeSupportedAssets();
    }

    /**
     * @notice Add yield strategy with oracle risk assessment
     * @param strategyContract Strategy implementation contract
     * @param strategyType Strategy type ("LENDING", "STAKING", "LP", "ARBITRAGE")
     * @param targetAllocation Target allocation in BPS
     * @param expectedYield Expected annual yield in BPS
     * @return strategyId ID of added strategy
     */
    function addYieldStrategy(
        address strategyContract,
        string memory strategyType,
        uint256 targetAllocation,
        uint256 expectedYield
    ) external onlyRole(STRATEGY_ROLE) returns (uint256 strategyId) {
        require(strategyContract != address(0), "Invalid strategy contract");
        require(targetAllocation <= 10000, "Target allocation too high");
        require(expectedYield >= optimizationConfig.minYieldThreshold, "Yield below threshold");

        // Assess strategy risk using oracle data
        uint256 riskScore = _assessStrategyRisk(strategyContract, strategyType);
        require(riskScore <= optimizationConfig.maxRiskScore, "Strategy risk too high");

        strategyId = nextStrategyId++;

        yieldStrategies[strategyId] = YieldStrategy({
            strategyContract: strategyContract,
            strategyType: strategyType,
            allocation: 0, // Start with 0, will be allocated during rebalance
            targetAllocation: targetAllocation,
            minAllocation: targetAllocation / 4, // 25% of target as minimum
            maxAllocation: targetAllocation * 2,  // 200% of target as maximum
            expectedYield: expectedYield,
            riskScore: riskScore,
            lastRebalance: block.timestamp,
            active: true,
            emergency: false
        });

        activeStrategyIds.push(strategyId);
        strategiesByType[strategyType].push(strategyId);
        strategyIdByContract[strategyContract] = strategyId;

        emit StrategyAdded(strategyId, strategyContract, strategyType, targetAllocation);

        // Trigger rebalancing to allocate funds to new strategy
        if (optimizationConfig.autoOptimizationEnabled) {
            _executeOptimization();
        }

        return strategyId;
    }

    /**
     * @notice Execute yield optimization based on oracle data
     */
    function executeOptimization() external onlyRole(STRATEGY_ROLE) nonReentrant {
        _executeOptimization();
    }

    /**
     * @notice Harvest yield from all active strategies
     */
    function harvestYield() external nonReentrant {
        require(
            block.timestamp >= lastYieldHarvest + harvestFrequency,
            "Harvest frequency not met"
        );

        uint256 totalHarvestedAmount = 0;

        for (uint256 i = 0; i < activeStrategyIds.length; i++) {
            uint256 strategyId = activeStrategyIds[i];
            YieldStrategy storage strategy = yieldStrategies[strategyId];

            if (strategy.active && !strategy.emergency) {
                uint256 harvestedFromStrategy = _harvestFromStrategy(strategyId);
                totalHarvestedAmount += harvestedFromStrategy;
            }
        }

        // Update metrics
        totalHarvested += totalHarvestedAmount;
        lastYieldHarvest = block.timestamp;

        // Record daily yield for APY calculation
        uint256 currentDay = block.timestamp / SECONDS_PER_DAY;
        dailyYield[currentDay] += totalHarvestedAmount;
        dailyAssets[currentDay] = totalAssets();

        // Update APY metrics
        _updateAPYMetrics();

        emit YieldHarvested(totalHarvestedAmount, block.timestamp, yieldMetrics.currentAPY);

        // Trigger optimization if significant yield was harvested
        if (totalHarvestedAmount > 0 && optimizationConfig.autoOptimizationEnabled) {
            _executeOptimization();
        }
    }

    /**
     * @notice Emergency exit from strategy due to high risk
     * @param strategyId Strategy ID to exit
     * @param reason Reason for emergency exit
     */
    function emergencyExitStrategy(
        uint256 strategyId,
        string memory reason
    ) external onlyRole(EMERGENCY_ROLE) {
        require(yieldStrategies[strategyId].active, "Strategy not active");

        YieldStrategy storage strategy = yieldStrategies[strategyId];
        strategy.emergency = true;
        strategy.active = false;

        uint256 withdrawnAmount = _withdrawAllFromStrategy(strategyId);

        // Remove from active strategies
        _removeFromActiveStrategies(strategyId);

        emit EmergencyStrategyExit(strategyId, withdrawnAmount, reason);

        // Redistribute allocation
        if (optimizationConfig.autoOptimizationEnabled) {
            _executeOptimization();
        }
    }

    /**
     * @notice Update oracle data for optimization
     * @param assets Array of asset symbols to update
     */
    function updateOracleData(string[] memory assets) external nonReentrant {
        for (uint256 i = 0; i < assets.length; i++) {
            string memory assetSymbol = assets[i];

            if (!supportedAssets[assetSymbol]) continue;

            try priceFeedAggregator.getPrice(assetSymbol) returns (
                uint256 price,
                uint256 timestamp,
                uint256 confidence,
                bool isValid
            ) {
                if (isValid && confidence >= 7500) { // Require 75% confidence
                    assetPrices[assetSymbol] = price;
                }
            } catch {
                // Handle oracle failure gracefully
            }

            try volatilityOracle.getVolatilityData(assetSymbol) returns (
                VolatilityOracle.VolatilityData memory volData
            ) {
                assetVolatilities[assetSymbol] = volData.currentVolatility;
            } catch {
                // Handle oracle failure gracefully
            }

            emit OracleDataUpdated(assetSymbol, assetPrices[assetSymbol], assetVolatilities[assetSymbol]);
        }

        // Trigger optimization after oracle update
        if (optimizationConfig.autoOptimizationEnabled) {
            _executeOptimization();
        }
    }

    /**
     * @notice Get yield optimization metrics
     * @return metrics Current yield metrics
     */
    function getYieldMetrics() external view returns (YieldMetrics memory metrics) {
        return yieldMetrics;
    }

    /**
     * @notice Get strategy details
     * @param strategyId Strategy ID
     * @return strategy Strategy information
     */
    function getYieldStrategy(uint256 strategyId) external view returns (YieldStrategy memory strategy) {
        return yieldStrategies[strategyId];
    }

    /**
     * @notice Get active strategies
     * @return strategyIds Array of active strategy IDs
     */
    function getActiveStrategies() external view returns (uint256[] memory strategyIds) {
        return activeStrategyIds;
    }

    /**
     * @notice Get strategies by type
     * @param strategyType Strategy type to filter by
     * @return strategyIds Array of strategy IDs of given type
     */
    function getStrategiesByType(string memory strategyType) external view returns (uint256[] memory strategyIds) {
        return strategiesByType[strategyType];
    }

    /**
     * @notice Update optimization configuration
     * @param rebalanceThreshold New rebalance threshold (BPS)
     * @param maxRiskScore New maximum risk score
     * @param minYieldThreshold New minimum yield threshold
     * @param autoOptimizationEnabled Whether auto optimization is enabled
     */
    function updateOptimizationConfig(
        uint256 rebalanceThreshold,
        uint256 maxRiskScore,
        uint256 minYieldThreshold,
        bool autoOptimizationEnabled
    ) external onlyRole(VAULT_MANAGER_ROLE) {
        require(rebalanceThreshold <= 2000, "Rebalance threshold too high"); // Max 20%
        require(maxRiskScore <= 10000, "Max risk score too high");
        require(minYieldThreshold <= 5000, "Min yield threshold too high"); // Max 50%

        optimizationConfig.rebalanceThreshold = rebalanceThreshold;
        optimizationConfig.maxRiskScore = maxRiskScore;
        optimizationConfig.minYieldThreshold = minYieldThreshold;
        optimizationConfig.autoOptimizationEnabled = autoOptimizationEnabled;
    }

    // Internal Functions

    function _executeOptimization() internal {
        require(
            block.timestamp >= yieldMetrics.lastOptimization + optimizationConfig.rebalanceFrequency,
            "Optimization frequency not met"
        );

        uint256 totalAssets_ = totalAssets();
        if (totalAssets_ == 0) return;

        // Update oracle data for all tracked assets
        _updateAllOracleData();

        // Calculate optimal allocations
        uint256[] memory optimalAllocations = _calculateOptimalAllocations(totalAssets_);

        // Execute rebalancing
        uint256 totalRiskScore = 0;
        uint256 activeStrategies = 0;

        for (uint256 i = 0; i < activeStrategyIds.length; i++) {
            uint256 strategyId = activeStrategyIds[i];
            YieldStrategy storage strategy = yieldStrategies[strategyId];

            if (!strategy.active || strategy.emergency) continue;

            uint256 newAllocation = optimalAllocations[i];
            uint256 currentAllocation = strategy.allocation;

            // Check if rebalancing is needed
            uint256 allocationDiff = newAllocation > currentAllocation ?
                newAllocation - currentAllocation :
                currentAllocation - newAllocation;

            if ((allocationDiff * 10000) / totalAssets_ >= optimizationConfig.rebalanceThreshold) {
                _rebalanceStrategy(strategyId, newAllocation, currentAllocation);
                strategy.lastRebalance = block.timestamp;

                emit StrategyRebalanced(
                    strategyId,
                    currentAllocation,
                    newAllocation,
                    "Oracle-driven optimization"
                );
            }

            totalRiskScore += strategy.riskScore;
            activeStrategies++;
        }

        // Update portfolio metrics
        yieldMetrics.portfolioRiskScore = activeStrategies > 0 ? totalRiskScore / activeStrategies : 0;
        yieldMetrics.lastOptimization = block.timestamp;

        // Check for emergency conditions
        _checkEmergencyConditions();

        emit OptimizationExecuted(
            activeStrategies,
            yieldMetrics.portfolioRiskScore,
            yieldMetrics.currentAPY
        );
    }

    function _calculateOptimalAllocations(uint256 totalAssets_) internal view returns (uint256[] memory) {
        uint256[] memory allocations = new uint256[](activeStrategyIds.length);

        if (optimizationConfig.riskAdjustedReturns) {
            // Use Sharpe ratio for risk-adjusted optimization
            uint256[] memory sharpeRatios = new uint256[](activeStrategyIds.length);
            uint256 totalSharpe = 0;

            for (uint256 i = 0; i < activeStrategyIds.length; i++) {
                uint256 strategyId = activeStrategyIds[i];
                YieldStrategy memory strategy = yieldStrategies[strategyId];

                if (strategy.active && !strategy.emergency) {
                    // Calculate Sharpe ratio: (expected return - risk-free rate) / risk
                    uint256 riskFreeRate = 300; // 3% risk-free rate assumption
                    uint256 excessReturn = strategy.expectedYield > riskFreeRate ?
                        strategy.expectedYield - riskFreeRate : 0;

                    sharpeRatios[i] = strategy.riskScore > 0 ?
                        (excessReturn * 10000) / strategy.riskScore : 0;
                    totalSharpe += sharpeRatios[i];
                }
            }

            // Allocate based on Sharpe ratios
            if (totalSharpe > 0) {
                for (uint256 i = 0; i < activeStrategyIds.length; i++) {
                    allocations[i] = (totalAssets_ * sharpeRatios[i]) / totalSharpe;
                }
            }
        } else {
            // Simple yield-based allocation
            uint256 totalExpectedYield = 0;

            for (uint256 i = 0; i < activeStrategyIds.length; i++) {
                uint256 strategyId = activeStrategyIds[i];
                YieldStrategy memory strategy = yieldStrategies[strategyId];

                if (strategy.active && !strategy.emergency) {
                    totalExpectedYield += strategy.expectedYield;
                }
            }

            if (totalExpectedYield > 0) {
                for (uint256 i = 0; i < activeStrategyIds.length; i++) {
                    uint256 strategyId = activeStrategyIds[i];
                    YieldStrategy memory strategy = yieldStrategies[strategyId];

                    if (strategy.active && !strategy.emergency) {
                        allocations[i] = (totalAssets_ * strategy.expectedYield) / totalExpectedYield;
                    }
                }
            }
        }

        return allocations;
    }

    function _assessStrategyRisk(address strategyContract, string memory strategyType) internal view returns (uint256) {
        uint256 baseRiskScore = 5000; // 50% base risk

        // Adjust risk based on strategy type
        if (keccak256(bytes(strategyType)) == keccak256(bytes("LENDING"))) {
            baseRiskScore = 3000; // 30% for lending (generally safer)
        } else if (keccak256(bytes(strategyType)) == keccak256(bytes("STAKING"))) {
            baseRiskScore = 4000; // 40% for staking
        } else if (keccak256(bytes(strategyType)) == keccak256(bytes("LP"))) {
            baseRiskScore = 6000; // 60% for liquidity provision
        } else if (keccak256(bytes(strategyType)) == keccak256(bytes("ARBITRAGE"))) {
            baseRiskScore = 8000; // 80% for arbitrage (high risk)
        }

        // Additional risk assessment based on asset volatility
        for (uint256 i = 0; i < trackedAssets.length; i++) {
            string memory asset = trackedAssets[i];
            uint256 volatility = assetVolatilities[asset];

            if (volatility > 5000) { // High volatility (>50%)
                baseRiskScore += 1000;
            } else if (volatility > 2000) { // Medium volatility (>20%)
                baseRiskScore += 500;
            }
        }

        return baseRiskScore > 10000 ? 10000 : baseRiskScore;
    }

    function _harvestFromStrategy(uint256 strategyId) internal returns (uint256) {
        // This would call the actual strategy contract to harvest yield
        // For now, return a placeholder amount
        YieldStrategy memory strategy = yieldStrategies[strategyId];
        uint256 allocatedAmount = strategy.allocation;

        if (allocatedAmount > 0) {
            // Estimate yield based on expected yield and time elapsed
            uint256 timeElapsed = block.timestamp - strategy.lastRebalance;
            uint256 annualizedYield = (allocatedAmount * strategy.expectedYield) / 10000;
            uint256 harvestablleYield = (annualizedYield * timeElapsed) / 365 days;

            return harvestablleYield;
        }

        return 0;
    }

    function _rebalanceStrategy(uint256 strategyId, uint256 newAllocation, uint256 currentAllocation) internal {
        YieldStrategy storage strategy = yieldStrategies[strategyId];

        if (newAllocation > currentAllocation) {
            // Increase allocation - deposit more funds
            uint256 additionalFunds = newAllocation - currentAllocation;
            // Transfer funds to strategy (actual implementation would call strategy contract)
            strategy.allocation = newAllocation;
        } else if (newAllocation < currentAllocation) {
            // Decrease allocation - withdraw funds
            uint256 excessFunds = currentAllocation - newAllocation;
            // Withdraw funds from strategy (actual implementation would call strategy contract)
            strategy.allocation = newAllocation;
        }
    }

    function _withdrawAllFromStrategy(uint256 strategyId) internal returns (uint256) {
        YieldStrategy storage strategy = yieldStrategies[strategyId];
        uint256 withdrawnAmount = strategy.allocation;
        strategy.allocation = 0;
        return withdrawnAmount;
    }

    function _updateAllOracleData() internal {
        for (uint256 i = 0; i < trackedAssets.length; i++) {
            string memory assetSymbol = trackedAssets[i];

            try priceFeedAggregator.getPrice(assetSymbol) returns (
                uint256 price,
                uint256 timestamp,
                uint256 confidence,
                bool isValid
            ) {
                if (isValid && confidence >= 7500) {
                    assetPrices[assetSymbol] = price;
                }
            } catch {
                // Handle oracle failure
            }

            try volatilityOracle.getVolatilityData(assetSymbol) returns (
                VolatilityOracle.VolatilityData memory volData
            ) {
                assetVolatilities[assetSymbol] = volData.currentVolatility;
            } catch {
                // Handle oracle failure
            }
        }
    }

    function _updateAPYMetrics() internal {
        uint256 currentDay = block.timestamp / SECONDS_PER_DAY;

        // Calculate current APY
        if (dailyAssets[currentDay] > 0) {
            yieldMetrics.currentAPY = (dailyYield[currentDay] * 365 * 10000) / dailyAssets[currentDay];
        }

        // Calculate 7-day APY
        uint256 sevenDayYield = 0;
        uint256 sevenDayAssets = 0;
        for (uint256 i = 0; i < 7; i++) {
            if (currentDay >= i) {
                uint256 day = currentDay - i;
                sevenDayYield += dailyYield[day];
                sevenDayAssets += dailyAssets[day];
            }
        }
        if (sevenDayAssets > 0) {
            yieldMetrics.sevenDayAPY = (sevenDayYield * 365 * 10000) / (sevenDayAssets / 7);
        }

        // Calculate 30-day APY
        uint256 thirtyDayYield = 0;
        uint256 thirtyDayAssets = 0;
        for (uint256 i = 0; i < 30; i++) {
            if (currentDay >= i) {
                uint256 day = currentDay - i;
                thirtyDayYield += dailyYield[day];
                thirtyDayAssets += dailyAssets[day];
            }
        }
        if (thirtyDayAssets > 0) {
            yieldMetrics.thirtyDayAPY = (thirtyDayYield * 365 * 10000) / (thirtyDayAssets / 30);
        }
    }

    function _checkEmergencyConditions() internal {
        for (uint256 i = 0; i < activeStrategyIds.length; i++) {
            uint256 strategyId = activeStrategyIds[i];
            YieldStrategy storage strategy = yieldStrategies[strategyId];

            if (strategy.active && strategy.riskScore >= optimizationConfig.emergencyExitThreshold) {
                strategy.emergency = true;
                strategy.active = false;

                emit RiskThresholdExceeded(
                    strategyId,
                    strategy.riskScore,
                    optimizationConfig.emergencyExitThreshold
                );

                // Emergency exit would be triggered here
            }
        }
    }

    function _removeFromActiveStrategies(uint256 strategyId) internal {
        for (uint256 i = 0; i < activeStrategyIds.length; i++) {
            if (activeStrategyIds[i] == strategyId) {
                activeStrategyIds[i] = activeStrategyIds[activeStrategyIds.length - 1];
                activeStrategyIds.pop();
                break;
            }
        }
    }

    function _initializeSupportedAssets() internal {
        // Initialize commonly tracked assets
        supportedAssets["ETH"] = true;
        supportedAssets["BTC"] = true;
        supportedAssets["USDC"] = true;
        supportedAssets["USDT"] = true;
        supportedAssets["DAI"] = true;

        trackedAssets.push("ETH");
        trackedAssets.push("BTC");
        trackedAssets.push("USDC");
        trackedAssets.push("USDT");
        trackedAssets.push("DAI");
    }

    /**
     * @notice Add support for new asset
     * @param assetSymbol Asset symbol to add
     */
    function addSupportedAsset(string memory assetSymbol) external onlyRole(VAULT_MANAGER_ROLE) {
        require(!supportedAssets[assetSymbol], "Asset already supported");

        supportedAssets[assetSymbol] = true;
        trackedAssets.push(assetSymbol);
    }

    /**
     * @notice Get tracked assets
     * @return assets Array of tracked asset symbols
     */
    function getTrackedAssets() external view returns (string[] memory assets) {
        return trackedAssets;
    }
}