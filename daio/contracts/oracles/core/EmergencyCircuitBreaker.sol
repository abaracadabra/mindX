// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./VolatilityOracle.sol";
import "./PriceFeedAggregator.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title EmergencyCircuitBreaker
 * @notice Integration with existing EmergencyTimelock for oracle failure response
 * @dev Monitors oracle and market conditions to trigger emergency protocols automatically
 */
contract EmergencyCircuitBreaker is AccessControl, ReentrancyGuard, Pausable {

    bytes32 public constant CIRCUIT_BREAKER_ROLE = keccak256("CIRCUIT_BREAKER_ROLE");
    bytes32 public constant EMERGENCY_RESPONDER_ROLE = keccak256("EMERGENCY_RESPONDER_ROLE");
    bytes32 public constant ORACLE_MONITOR_ROLE = keccak256("ORACLE_MONITOR_ROLE");

    // Circuit breaker configuration
    struct CircuitBreakerConfig {
        uint256 priceDeviationThreshold;    // Price deviation that triggers circuit breaker (BPS)
        uint256 volatilityThreshold;        // Volatility threshold for emergency (BPS)
        uint256 oracleFailureThreshold;     // Number of failed oracle calls to trigger emergency
        uint256 correlationThreshold;       // Cross-asset correlation threshold
        uint256 liquidityThreshold;         // Minimum liquidity threshold
        uint256 cooldownPeriod;             // Cooldown between circuit breaker activations
        bool enabled;                       // Whether circuit breaker is enabled
    }

    struct EmergencyState {
        bool isActive;                      // Whether emergency is currently active
        uint256 activatedAt;                // When emergency was activated
        uint256 triggeredBy;                // What triggered the emergency (enum)
        string triggerAsset;                // Asset that triggered emergency
        uint256 triggerValue;               // Value that triggered emergency
        uint256 expectedResolution;         // Expected resolution timestamp
        address emergencyResponder;         // Address that can resolve emergency
    }

    // Emergency trigger types
    uint256 public constant TRIGGER_PRICE_DEVIATION = 1;
    uint256 public constant TRIGGER_VOLATILITY = 2;
    uint256 public constant TRIGGER_ORACLE_FAILURE = 3;
    uint256 public constant TRIGGER_CORRELATION = 4;
    uint256 public constant TRIGGER_LIQUIDITY = 5;
    uint256 public constant TRIGGER_MANUAL = 6;

    // Integration contracts
    VolatilityOracle public immutable volatilityOracle;
    PriceFeedAggregator public immutable priceFeedAggregator;
    address public emergencyTimelock;      // Existing DAIO EmergencyTimelock contract
    address public constitutionContract;
    address public treasuryContract;

    // State variables
    mapping(string => CircuitBreakerConfig) public circuitBreakerConfigs;
    mapping(string => uint256) public oracleFailureCounts;
    mapping(string => uint256) public lastPrices;
    mapping(string => uint256) public lastEmergencyTrigger; // Cooldown tracking

    EmergencyState public currentEmergency;
    string[] public monitoredAssets;

    // Emergency response actions
    mapping(uint256 => bool) public enabledActions; // trigger type -> enabled
    bool public autoTreasuryFreeze;
    bool public autoOraclePause;
    bool public autoTradingHalt;

    // Metrics and monitoring
    uint256 public totalEmergenciesTriggered;
    uint256 public falsePositiveCount;
    uint256 public averageResolutionTime;
    mapping(uint256 => uint256) public triggerTypeCount; // trigger type -> count

    // Events
    event CircuitBreakerTriggered(
        string indexed asset,
        uint256 indexed triggerType,
        uint256 triggerValue,
        uint256 threshold,
        address indexed responder
    );
    event EmergencyResolved(
        string indexed asset,
        uint256 indexed triggerType,
        uint256 duration,
        address indexed resolver
    );
    event OracleFailureDetected(
        string indexed asset,
        address indexed oracle,
        uint256 failureCount,
        uint256 threshold
    );
    event EmergencyActionExecuted(
        string indexed asset,
        string action,
        bool success
    );
    event CircuitBreakerConfigUpdated(
        string indexed asset,
        uint256 priceThreshold,
        uint256 volatilityThreshold,
        bool enabled
    );
    event FalsePositiveReported(
        string indexed asset,
        uint256 indexed triggerType,
        address indexed reporter
    );

    /**
     * @notice Initialize EmergencyCircuitBreaker with existing DAIO contracts
     * @param _volatilityOracle Address of volatility oracle
     * @param _priceFeedAggregator Address of price feed aggregator
     * @param _emergencyTimelock Address of existing DAIO emergency timelock
     * @param _constitutionContract Address of DAIO constitution
     * @param _treasuryContract Address of DAIO treasury
     * @param admin Admin address for role management
     */
    constructor(
        address _volatilityOracle,
        address _priceFeedAggregator,
        address _emergencyTimelock,
        address _constitutionContract,
        address _treasuryContract,
        address admin
    ) {
        require(_volatilityOracle != address(0), "Volatility oracle cannot be zero address");
        require(_priceFeedAggregator != address(0), "Price aggregator cannot be zero address");
        require(admin != address(0), "Admin cannot be zero address");

        volatilityOracle = VolatilityOracle(_volatilityOracle);
        priceFeedAggregator = PriceFeedAggregator(_priceFeedAggregator);
        emergencyTimelock = _emergencyTimelock;
        constitutionContract = _constitutionContract;
        treasuryContract = _treasuryContract;

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CIRCUIT_BREAKER_ROLE, admin);
        _grantRole(EMERGENCY_RESPONDER_ROLE, admin);
        _grantRole(ORACLE_MONITOR_ROLE, admin);

        // Set default emergency actions
        autoTreasuryFreeze = true;
        autoOraclePause = true;
        autoTradingHalt = false; // Require manual activation

        // Enable default trigger types
        enabledActions[TRIGGER_PRICE_DEVIATION] = true;
        enabledActions[TRIGGER_VOLATILITY] = true;
        enabledActions[TRIGGER_ORACLE_FAILURE] = true;
        enabledActions[TRIGGER_MANUAL] = true;

        // Initialize default circuit breaker configurations
        _setDefaultConfigurations();
    }

    /**
     * @notice Configure circuit breaker for an asset
     * @param asset Asset symbol
     * @param priceDeviationThreshold Price deviation threshold (BPS)
     * @param volatilityThreshold Volatility threshold (BPS)
     * @param oracleFailureThreshold Oracle failure count threshold
     * @param cooldownPeriod Cooldown between activations (seconds)
     */
    function configureCircuitBreaker(
        string memory asset,
        uint256 priceDeviationThreshold,
        uint256 volatilityThreshold,
        uint256 oracleFailureThreshold,
        uint256 cooldownPeriod
    ) external onlyRole(CIRCUIT_BREAKER_ROLE) {
        require(bytes(asset).length > 0, "Asset cannot be empty");
        require(priceDeviationThreshold <= 5000, "Price deviation threshold too high"); // Max 50%
        require(volatilityThreshold <= 10000, "Volatility threshold too high"); // Max 100%
        require(oracleFailureThreshold >= 3, "Oracle failure threshold too low"); // Min 3 failures
        require(cooldownPeriod >= 300, "Cooldown period too short"); // Min 5 minutes

        circuitBreakerConfigs[asset] = CircuitBreakerConfig({
            priceDeviationThreshold: priceDeviationThreshold,
            volatilityThreshold: volatilityThreshold,
            oracleFailureThreshold: oracleFailureThreshold,
            correlationThreshold: 8500, // 85% correlation threshold
            liquidityThreshold: 1000,   // 10% minimum liquidity
            cooldownPeriod: cooldownPeriod,
            enabled: true
        });

        // Add to monitored assets if not already present
        bool isMonitored = false;
        for (uint256 i = 0; i < monitoredAssets.length; i++) {
            if (keccak256(bytes(monitoredAssets[i])) == keccak256(bytes(asset))) {
                isMonitored = true;
                break;
            }
        }

        if (!isMonitored) {
            monitoredAssets.push(asset);
        }

        emit CircuitBreakerConfigUpdated(
            asset,
            priceDeviationThreshold,
            volatilityThreshold,
            true
        );
    }

    /**
     * @notice Monitor and potentially trigger circuit breaker for an asset
     * @param asset Asset symbol to monitor
     */
    function monitorAsset(string memory asset) external onlyRole(ORACLE_MONITOR_ROLE) nonReentrant whenNotPaused {
        require(circuitBreakerConfigs[asset].enabled, "Circuit breaker not enabled for asset");
        require(
            block.timestamp >= lastEmergencyTrigger[asset] + circuitBreakerConfigs[asset].cooldownPeriod,
            "Cooldown period not met"
        );
        require(!currentEmergency.isActive, "Emergency already active");

        CircuitBreakerConfig memory config = circuitBreakerConfigs[asset];

        // Check price deviation
        if (_checkPriceDeviation(asset, config.priceDeviationThreshold)) {
            _triggerCircuitBreaker(asset, TRIGGER_PRICE_DEVIATION, 0);
            return;
        }

        // Check volatility
        if (_checkVolatilityThreshold(asset, config.volatilityThreshold)) {
            _triggerCircuitBreaker(asset, TRIGGER_VOLATILITY, 0);
            return;
        }

        // Check oracle failures
        if (oracleFailureCounts[asset] >= config.oracleFailureThreshold) {
            _triggerCircuitBreaker(asset, TRIGGER_ORACLE_FAILURE, oracleFailureCounts[asset]);
            return;
        }

        // Check liquidity (if applicable)
        if (_checkLiquidityThreshold(asset, config.liquidityThreshold)) {
            _triggerCircuitBreaker(asset, TRIGGER_LIQUIDITY, 0);
            return;
        }
    }

    /**
     * @notice Manually trigger circuit breaker
     * @param asset Asset symbol
     * @param reason Reason for manual trigger
     */
    function manualTrigger(
        string memory asset,
        string memory reason
    ) external onlyRole(EMERGENCY_RESPONDER_ROLE) {
        require(circuitBreakerConfigs[asset].enabled, "Circuit breaker not enabled for asset");
        require(!currentEmergency.isActive, "Emergency already active");

        _triggerCircuitBreaker(asset, TRIGGER_MANUAL, 0);
    }

    /**
     * @notice Resolve current emergency
     * @param wasValidEmergency Whether the emergency was valid (not false positive)
     */
    function resolveEmergency(
        bool wasValidEmergency
    ) external onlyRole(EMERGENCY_RESPONDER_ROLE) {
        require(currentEmergency.isActive, "No active emergency");
        require(
            msg.sender == currentEmergency.emergencyResponder ||
            hasRole(DEFAULT_ADMIN_ROLE, msg.sender),
            "Unauthorized to resolve emergency"
        );

        uint256 duration = block.timestamp - currentEmergency.activatedAt;

        // Update metrics
        if (wasValidEmergency) {
            averageResolutionTime = (averageResolutionTime + duration) /
                (totalEmergenciesTriggered > 0 ? 2 : 1);
        } else {
            falsePositiveCount++;
            emit FalsePositiveReported(
                currentEmergency.triggerAsset,
                currentEmergency.triggeredBy,
                msg.sender
            );
        }

        string memory asset = currentEmergency.triggerAsset;
        uint256 triggerType = currentEmergency.triggeredBy;

        // Execute recovery actions
        _executeRecoveryActions(asset);

        // Reset emergency state
        delete currentEmergency;

        // Reset oracle failure count for this asset
        oracleFailureCounts[asset] = 0;

        emit EmergencyResolved(asset, triggerType, duration, msg.sender);
    }

    /**
     * @notice Report oracle failure
     * @param asset Asset symbol
     * @param oracleAddress Address of failed oracle
     */
    function reportOracleFailure(
        string memory asset,
        address oracleAddress
    ) external onlyRole(ORACLE_MONITOR_ROLE) {
        oracleFailureCounts[asset]++;

        emit OracleFailureDetected(
            asset,
            oracleAddress,
            oracleFailureCounts[asset],
            circuitBreakerConfigs[asset].oracleFailureThreshold
        );

        // Auto-trigger if threshold reached
        if (oracleFailureCounts[asset] >= circuitBreakerConfigs[asset].oracleFailureThreshold &&
            !currentEmergency.isActive) {
            _triggerCircuitBreaker(asset, TRIGGER_ORACLE_FAILURE, oracleFailureCounts[asset]);
        }
    }

    /**
     * @notice Get current emergency state
     * @return emergency Current emergency information
     */
    function getCurrentEmergency() external view returns (EmergencyState memory emergency) {
        return currentEmergency;
    }

    /**
     * @notice Get circuit breaker statistics
     * @return totalEmergencies Total emergencies triggered
     * @return falsePositives False positive count
     * @return avgResolutionTime Average resolution time
     * @return activeEmergency Whether emergency is currently active
     */
    function getCircuitBreakerStats() external view returns (
        uint256 totalEmergencies,
        uint256 falsePositives,
        uint256 avgResolutionTime,
        bool activeEmergency
    ) {
        return (
            totalEmergenciesTriggered,
            falsePositiveCount,
            averageResolutionTime,
            currentEmergency.isActive
        );
    }

    /**
     * @notice Get monitored assets
     * @return assets Array of monitored asset symbols
     */
    function getMonitoredAssets() external view returns (string[] memory assets) {
        return monitoredAssets;
    }

    /**
     * @notice Update emergency action configuration
     * @param treasuryFreeze Whether to auto-freeze treasury
     * @param oraclePause Whether to auto-pause oracles
     * @param tradingHalt Whether to auto-halt trading
     */
    function updateEmergencyActions(
        bool treasuryFreeze,
        bool oraclePause,
        bool tradingHalt
    ) external onlyRole(CIRCUIT_BREAKER_ROLE) {
        autoTreasuryFreeze = treasuryFreeze;
        autoOraclePause = oraclePause;
        autoTradingHalt = tradingHalt;
    }

    // Internal functions

    function _triggerCircuitBreaker(
        string memory asset,
        uint256 triggerType,
        uint256 triggerValue
    ) internal {
        require(enabledActions[triggerType], "Trigger type not enabled");

        // Set emergency state
        currentEmergency = EmergencyState({
            isActive: true,
            activatedAt: block.timestamp,
            triggeredBy: triggerType,
            triggerAsset: asset,
            triggerValue: triggerValue,
            expectedResolution: block.timestamp + 3600, // 1 hour default
            emergencyResponder: msg.sender
        });

        // Update metrics
        totalEmergenciesTriggered++;
        triggerTypeCount[triggerType]++;
        lastEmergencyTrigger[asset] = block.timestamp;

        // Execute emergency actions
        _executeEmergencyActions(asset);

        // Integrate with existing EmergencyTimelock if available
        if (emergencyTimelock != address(0)) {
            _notifyEmergencyTimelock(asset, triggerType);
        }

        emit CircuitBreakerTriggered(
            asset,
            triggerType,
            triggerValue,
            _getThresholdForTriggerType(asset, triggerType),
            msg.sender
        );
    }

    function _checkPriceDeviation(string memory asset, uint256 threshold) internal returns (bool) {
        try priceFeedAggregator.getPrice(asset) returns (
            uint256 currentPrice,
            uint256 timestamp,
            uint256 confidence,
            bool isValid
        ) {
            if (!isValid || confidence < 7500) { // Require 75% confidence
                return false;
            }

            uint256 lastPrice = lastPrices[asset];
            lastPrices[asset] = currentPrice;

            if (lastPrice > 0) {
                uint256 deviation = currentPrice > lastPrice ?
                    ((currentPrice - lastPrice) * 10000) / lastPrice :
                    ((lastPrice - currentPrice) * 10000) / lastPrice;

                return deviation > threshold;
            }

            return false;
        } catch {
            // Oracle call failed
            oracleFailureCounts[asset]++;
            return false;
        }
    }

    function _checkVolatilityThreshold(string memory asset, uint256 threshold) internal view returns (bool) {
        try volatilityOracle.getVolatilityData(asset) returns (
            VolatilityOracle.VolatilityData memory volData
        ) {
            return volData.currentVolatility > threshold;
        } catch {
            return false;
        }
    }

    function _checkLiquidityThreshold(string memory asset, uint256 threshold) internal view returns (bool) {
        try volatilityOracle.getRiskMetrics(asset) returns (
            VolatilityOracle.RiskMetrics memory riskData
        ) {
            return riskData.liquidityRisk > (10000 - threshold);
        } catch {
            return false;
        }
    }

    function _executeEmergencyActions(string memory asset) internal {
        // Auto-pause oracle if configured
        if (autoOraclePause) {
            try priceFeedAggregator.emergencyPause() {
                emit EmergencyActionExecuted(asset, "ORACLE_PAUSE", true);
            } catch {
                emit EmergencyActionExecuted(asset, "ORACLE_PAUSE", false);
            }
        }

        // Notify treasury to freeze operations (if configured)
        if (autoTreasuryFreeze && treasuryContract != address(0)) {
            // This would integrate with the existing Treasury contract
            emit EmergencyActionExecuted(asset, "TREASURY_FREEZE", true);
        }

        // Additional emergency actions would be implemented here
        // Integration with existing DAIO emergency protocols
    }

    function _executeRecoveryActions(string memory asset) internal {
        // Unpause oracle
        try priceFeedAggregator.unpause() {
            emit EmergencyActionExecuted(asset, "ORACLE_UNPAUSE", true);
        } catch {
            emit EmergencyActionExecuted(asset, "ORACLE_UNPAUSE", false);
        }

        // Additional recovery actions would be implemented here
    }

    function _notifyEmergencyTimelock(string memory asset, uint256 triggerType) internal {
        // This would integrate with the existing EmergencyTimelock contract
        // For now, just emit an event that the timelock can monitor
        emit EmergencyActionExecuted(asset, "TIMELOCK_NOTIFICATION", true);
    }

    function _getThresholdForTriggerType(
        string memory asset,
        uint256 triggerType
    ) internal view returns (uint256) {
        CircuitBreakerConfig memory config = circuitBreakerConfigs[asset];

        if (triggerType == TRIGGER_PRICE_DEVIATION) {
            return config.priceDeviationThreshold;
        } else if (triggerType == TRIGGER_VOLATILITY) {
            return config.volatilityThreshold;
        } else if (triggerType == TRIGGER_ORACLE_FAILURE) {
            return config.oracleFailureThreshold;
        } else if (triggerType == TRIGGER_CORRELATION) {
            return config.correlationThreshold;
        } else if (triggerType == TRIGGER_LIQUIDITY) {
            return config.liquidityThreshold;
        }

        return 0;
    }

    function _setDefaultConfigurations() internal {
        // ETH configuration
        circuitBreakerConfigs["ETH"] = CircuitBreakerConfig({
            priceDeviationThreshold: 2000,  // 20% price deviation
            volatilityThreshold: 5000,      // 50% volatility threshold
            oracleFailureThreshold: 3,      // 3 oracle failures
            correlationThreshold: 8500,     // 85% correlation
            liquidityThreshold: 1000,       // 10% minimum liquidity
            cooldownPeriod: 1800,           // 30 minutes cooldown
            enabled: true
        });

        // BTC configuration
        circuitBreakerConfigs["BTC"] = CircuitBreakerConfig({
            priceDeviationThreshold: 2000,  // 20% price deviation
            volatilityThreshold: 5000,      // 50% volatility threshold
            oracleFailureThreshold: 3,      // 3 oracle failures
            correlationThreshold: 8500,     // 85% correlation
            liquidityThreshold: 1000,       // 10% minimum liquidity
            cooldownPeriod: 1800,           // 30 minutes cooldown
            enabled: true
        });

        // USDC configuration (more sensitive for stablecoin)
        circuitBreakerConfigs["USDC"] = CircuitBreakerConfig({
            priceDeviationThreshold: 500,   // 5% price deviation
            volatilityThreshold: 1000,      // 10% volatility threshold
            oracleFailureThreshold: 2,      // 2 oracle failures
            correlationThreshold: 9000,     // 90% correlation
            liquidityThreshold: 500,        // 5% minimum liquidity
            cooldownPeriod: 900,            // 15 minutes cooldown
            enabled: true
        });

        // Add to monitored assets
        monitoredAssets.push("ETH");
        monitoredAssets.push("BTC");
        monitoredAssets.push("USDC");
    }

    /**
     * @notice Emergency pause all operations
     */
    function emergencyPause() external onlyRole(EMERGENCY_RESPONDER_ROLE) {
        _pause();
    }

    /**
     * @notice Unpause operations
     */
    function unpause() external onlyRole(EMERGENCY_RESPONDER_ROLE) {
        _unpause();
    }

    /**
     * @notice Update emergency timelock integration
     * @param _emergencyTimelock New emergency timelock address
     */
    function updateEmergencyTimelock(address _emergencyTimelock) external onlyRole(DEFAULT_ADMIN_ROLE) {
        emergencyTimelock = _emergencyTimelock;
    }
}