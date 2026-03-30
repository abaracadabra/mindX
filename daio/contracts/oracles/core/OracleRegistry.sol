// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title OracleRegistry
 * @notice Multi-source oracle aggregation with DAIO governance integration
 * @dev Central registry for all oracle data sources with constitutional compliance
 */
contract OracleRegistry is AccessControl, ReentrancyGuard, Pausable {

    bytes32 public constant ORACLE_MANAGER_ROLE = keccak256("ORACLE_MANAGER_ROLE");
    bytes32 public constant PRICE_UPDATER_ROLE = keccak256("PRICE_UPDATER_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");

    // Oracle data source configuration
    struct OracleSource {
        address sourceAddress;
        string name;
        uint256 weight;              // Weight in aggregation (BPS, 10000 = 100%)
        uint256 maxDeviationBPS;     // Maximum allowed price deviation from median
        uint256 heartbeatInterval;   // Expected update frequency in seconds
        uint256 lastUpdated;         // Last successful update timestamp
        bool active;                 // Whether source is active
        bool trusted;                // Whether source is trusted for emergency situations
        uint256 totalUpdates;        // Total number of updates provided
        uint256 failureCount;        // Consecutive failure count
        string dataType;             // "PRICE", "VOLATILITY", "VOLUME", "MARKET_CAP"
    }

    struct AssetPriceData {
        uint256 price;               // Price in USD with 8 decimals (like Chainlink)
        uint256 timestamp;           // When price was last updated
        uint256 roundId;             // Round ID for version tracking
        uint256 confidence;          // Confidence level (BPS, 10000 = 100%)
        uint256 sourceCount;         // Number of sources contributing
        bool stale;                  // Whether data is considered stale
    }

    struct AggregationConfig {
        uint256 minSources;          // Minimum sources required for valid price
        uint256 maxDeviationBPS;     // Maximum deviation allowed between sources
        uint256 staleThreshold;      // Seconds after which data is stale
        uint256 emergencyThreshold;  // Deviation threshold for emergency circuit breaker
        bool requireTrustedSource;   // Whether at least one trusted source is required
        string aggregationMethod;    // "MEDIAN", "WEIGHTED_AVERAGE", "MEAN"
    }

    // State variables
    mapping(string => mapping(address => OracleSource)) public oracleSources; // asset -> source -> data
    mapping(string => address[]) public assetSources; // asset -> array of source addresses
    mapping(string => AssetPriceData) public assetPrices; // asset -> latest aggregated price
    mapping(string => AggregationConfig) public aggregationConfigs; // asset -> config

    // DAIO integration
    address public constitutionContract;
    address public treasuryContract;
    address public emergencyTimelock;
    address public governanceAdapter;

    // Oracle analytics
    mapping(string => uint256) public totalRounds; // asset -> total rounds
    mapping(address => uint256) public sourceReputationScore; // source -> reputation (0-10000 BPS)
    mapping(string => uint256) public assetVolatility; // asset -> volatility measure

    // Events
    event OracleSourceRegistered(
        string indexed asset,
        address indexed source,
        string name,
        uint256 weight
    );
    event OracleSourceUpdated(
        string indexed asset,
        address indexed source,
        uint256 newWeight,
        bool active
    );
    event PriceUpdated(
        string indexed asset,
        uint256 price,
        uint256 timestamp,
        uint256 roundId,
        uint256 sourceCount
    );
    event EmergencyTriggered(
        string indexed asset,
        uint256 priceDeviation,
        uint256 threshold
    );
    event StaleDataDetected(
        string indexed asset,
        uint256 lastUpdate,
        uint256 threshold
    );
    event SourceFailure(
        string indexed asset,
        address indexed source,
        uint256 failureCount
    );
    event AggregationConfigUpdated(
        string indexed asset,
        uint256 minSources,
        string method
    );

    /**
     * @notice Initialize OracleRegistry with DAIO integration
     * @param admin Admin address for role management
     * @param _constitutionContract DAIO constitution contract
     * @param _treasuryContract DAIO treasury contract
     * @param _emergencyTimelock Emergency timelock contract
     */
    constructor(
        address admin,
        address _constitutionContract,
        address _treasuryContract,
        address _emergencyTimelock
    ) {
        require(admin != address(0), "Admin cannot be zero address");
        require(_constitutionContract != address(0), "Constitution cannot be zero address");

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(ORACLE_MANAGER_ROLE, admin);
        _grantRole(EMERGENCY_ROLE, admin);

        constitutionContract = _constitutionContract;
        treasuryContract = _treasuryContract;
        emergencyTimelock = _emergencyTimelock;

        // Set default aggregation configs for common assets
        _setDefaultConfigs();
    }

    /**
     * @notice Register a new oracle source for an asset
     * @param asset Asset symbol (e.g., "ETH", "BTC", "USDC")
     * @param sourceAddress Address of the oracle source
     * @param name Human-readable name of the source
     * @param weight Weight in aggregation (BPS)
     * @param maxDeviationBPS Maximum allowed deviation from median
     * @param heartbeatInterval Expected update frequency
     * @param trusted Whether this is a trusted source
     */
    function registerOracleSource(
        string memory asset,
        address sourceAddress,
        string memory name,
        uint256 weight,
        uint256 maxDeviationBPS,
        uint256 heartbeatInterval,
        bool trusted
    ) external onlyRole(ORACLE_MANAGER_ROLE) {
        require(sourceAddress != address(0), "Source cannot be zero address");
        require(weight <= 10000, "Weight cannot exceed 100%");
        require(maxDeviationBPS <= 5000, "Max deviation cannot exceed 50%");
        require(heartbeatInterval >= 60, "Heartbeat interval too short");
        require(bytes(asset).length > 0, "Asset cannot be empty");
        require(bytes(name).length > 0, "Name cannot be empty");

        // Check if source already exists
        require(oracleSources[asset][sourceAddress].sourceAddress == address(0), "Source already exists");

        oracleSources[asset][sourceAddress] = OracleSource({
            sourceAddress: sourceAddress,
            name: name,
            weight: weight,
            maxDeviationBPS: maxDeviationBPS,
            heartbeatInterval: heartbeatInterval,
            lastUpdated: 0,
            active: true,
            trusted: trusted,
            totalUpdates: 0,
            failureCount: 0,
            dataType: "PRICE"
        });

        assetSources[asset].push(sourceAddress);

        // Initialize reputation score
        if (trusted) {
            sourceReputationScore[sourceAddress] = 9000; // 90% initial reputation for trusted sources
        } else {
            sourceReputationScore[sourceAddress] = 7500; // 75% initial reputation for new sources
        }

        emit OracleSourceRegistered(asset, sourceAddress, name, weight);
    }

    /**
     * @notice Update price data from an oracle source
     * @param asset Asset symbol
     * @param price New price (8 decimals)
     * @param confidence Confidence level (BPS)
     */
    function updatePrice(
        string memory asset,
        uint256 price,
        uint256 confidence
    ) external onlyRole(PRICE_UPDATER_ROLE) nonReentrant whenNotPaused {
        require(price > 0, "Price must be greater than 0");
        require(confidence <= 10000, "Confidence cannot exceed 100%");

        OracleSource storage source = oracleSources[asset][msg.sender];
        require(source.active, "Source not active");
        require(source.sourceAddress == msg.sender, "Unauthorized source");

        // Update source data
        source.lastUpdated = block.timestamp;
        source.totalUpdates++;
        source.failureCount = 0; // Reset failure count on successful update

        // Aggregate prices from all active sources
        _aggregateAssetPrice(asset);

        // Update reputation score based on performance
        _updateSourceReputation(msg.sender, true);
    }

    /**
     * @notice Get latest price for an asset
     * @param asset Asset symbol
     * @return price Latest aggregated price
     * @return timestamp When price was last updated
     * @return roundId Current round ID
     * @return confidence Aggregated confidence level
     */
    function getLatestPrice(string memory asset) external view returns (
        uint256 price,
        uint256 timestamp,
        uint256 roundId,
        uint256 confidence
    ) {
        AssetPriceData memory priceData = assetPrices[asset];
        return (priceData.price, priceData.timestamp, priceData.roundId, priceData.confidence);
    }

    /**
     * @notice Get price data with staleness check
     * @param asset Asset symbol
     * @return price Latest price
     * @return isStale Whether data is considered stale
     * @return lastUpdate When price was last updated
     */
    function getPriceWithFreshness(string memory asset) external view returns (
        uint256 price,
        bool isStale,
        uint256 lastUpdate
    ) {
        AssetPriceData memory priceData = assetPrices[asset];
        AggregationConfig memory config = aggregationConfigs[asset];

        bool stale = block.timestamp > priceData.timestamp + config.staleThreshold;

        return (priceData.price, stale, priceData.timestamp);
    }

    /**
     * @notice Set aggregation configuration for an asset
     * @param asset Asset symbol
     * @param minSources Minimum sources required
     * @param maxDeviationBPS Maximum deviation between sources
     * @param staleThreshold Seconds after which data is stale
     * @param method Aggregation method
     */
    function setAggregationConfig(
        string memory asset,
        uint256 minSources,
        uint256 maxDeviationBPS,
        uint256 staleThreshold,
        string memory method
    ) external onlyRole(ORACLE_MANAGER_ROLE) {
        require(minSources > 0, "Min sources must be greater than 0");
        require(maxDeviationBPS <= 5000, "Max deviation too high");
        require(staleThreshold >= 300, "Stale threshold too short"); // Min 5 minutes

        aggregationConfigs[asset] = AggregationConfig({
            minSources: minSources,
            maxDeviationBPS: maxDeviationBPS,
            staleThreshold: staleThreshold,
            emergencyThreshold: maxDeviationBPS * 2, // Emergency at 2x normal deviation
            requireTrustedSource: false,
            aggregationMethod: method
        });

        emit AggregationConfigUpdated(asset, minSources, method);
    }

    /**
     * @notice Emergency pause oracle for an asset
     * @param asset Asset to pause
     */
    function emergencyPauseAsset(string memory asset) external onlyRole(EMERGENCY_ROLE) {
        assetPrices[asset].stale = true;
        emit StaleDataDetected(asset, assetPrices[asset].timestamp, block.timestamp);
    }

    /**
     * @notice Pause all oracle operations
     */
    function emergencyPause() external onlyRole(EMERGENCY_ROLE) {
        _pause();
    }

    /**
     * @notice Unpause oracle operations
     */
    function unpause() external onlyRole(EMERGENCY_ROLE) {
        _unpause();
    }

    /**
     * @notice Get all active sources for an asset
     * @param asset Asset symbol
     * @return sources Array of active source addresses
     */
    function getActiveSources(string memory asset) external view returns (address[] memory sources) {
        address[] memory allSources = assetSources[asset];
        uint256 activeCount = 0;

        // Count active sources
        for (uint256 i = 0; i < allSources.length; i++) {
            if (oracleSources[asset][allSources[i]].active) {
                activeCount++;
            }
        }

        // Create array of active sources
        sources = new address[](activeCount);
        uint256 index = 0;
        for (uint256 i = 0; i < allSources.length; i++) {
            if (oracleSources[asset][allSources[i]].active) {
                sources[index] = allSources[i];
                index++;
            }
        }

        return sources;
    }

    /**
     * @notice Get source reputation score
     * @param source Source address
     * @return reputation Reputation score (0-10000 BPS)
     */
    function getSourceReputation(address source) external view returns (uint256 reputation) {
        return sourceReputationScore[source];
    }

    // Internal functions

    function _aggregateAssetPrice(string memory asset) internal {
        address[] memory sources = assetSources[asset];
        AggregationConfig memory config = aggregationConfigs[asset];

        uint256[] memory prices = new uint256[](sources.length);
        uint256[] memory weights = new uint256[](sources.length);
        uint256 validSources = 0;
        uint256 totalWeight = 0;

        // Collect valid prices from active sources
        for (uint256 i = 0; i < sources.length; i++) {
            OracleSource memory source = oracleSources[asset][sources[i]];

            if (source.active &&
                block.timestamp <= source.lastUpdated + source.heartbeatInterval * 2 &&
                source.lastUpdated > 0) {

                // Get price from source (this would call the actual oracle in a real implementation)
                uint256 sourcePrice = _getSourcePrice(sources[i], asset);

                if (sourcePrice > 0) {
                    prices[validSources] = sourcePrice;
                    weights[validSources] = source.weight;
                    totalWeight += source.weight;
                    validSources++;
                }
            }
        }

        require(validSources >= config.minSources, "Insufficient valid sources");

        uint256 aggregatedPrice;

        if (keccak256(bytes(config.aggregationMethod)) == keccak256(bytes("MEDIAN"))) {
            aggregatedPrice = _calculateMedian(prices, validSources);
        } else if (keccak256(bytes(config.aggregationMethod)) == keccak256(bytes("WEIGHTED_AVERAGE"))) {
            aggregatedPrice = _calculateWeightedAverage(prices, weights, validSources, totalWeight);
        } else {
            aggregatedPrice = _calculateMean(prices, validSources);
        }

        // Check for extreme price deviations
        uint256 currentPrice = assetPrices[asset].price;
        if (currentPrice > 0) {
            uint256 deviation = aggregatedPrice > currentPrice ?
                ((aggregatedPrice - currentPrice) * 10000) / currentPrice :
                ((currentPrice - aggregatedPrice) * 10000) / currentPrice;

            if (deviation > config.emergencyThreshold) {
                emit EmergencyTriggered(asset, deviation, config.emergencyThreshold);
                // Could trigger emergency circuit breaker here
                return;
            }
        }

        // Update asset price data
        totalRounds[asset]++;
        assetPrices[asset] = AssetPriceData({
            price: aggregatedPrice,
            timestamp: block.timestamp,
            roundId: totalRounds[asset],
            confidence: _calculateConfidence(validSources, config.minSources),
            sourceCount: validSources,
            stale: false
        });

        emit PriceUpdated(asset, aggregatedPrice, block.timestamp, totalRounds[asset], validSources);
    }

    function _getSourcePrice(address source, string memory asset) internal view returns (uint256) {
        // In a real implementation, this would call the actual oracle source
        // For now, return a placeholder that would be implemented per source type
        return 0;
    }

    function _calculateMedian(uint256[] memory prices, uint256 length) internal pure returns (uint256) {
        // Simple bubble sort for median calculation
        for (uint256 i = 0; i < length - 1; i++) {
            for (uint256 j = 0; j < length - i - 1; j++) {
                if (prices[j] > prices[j + 1]) {
                    uint256 temp = prices[j];
                    prices[j] = prices[j + 1];
                    prices[j + 1] = temp;
                }
            }
        }

        if (length % 2 == 0) {
            return (prices[length / 2 - 1] + prices[length / 2]) / 2;
        } else {
            return prices[length / 2];
        }
    }

    function _calculateWeightedAverage(
        uint256[] memory prices,
        uint256[] memory weights,
        uint256 length,
        uint256 totalWeight
    ) internal pure returns (uint256) {
        uint256 weightedSum = 0;

        for (uint256 i = 0; i < length; i++) {
            weightedSum += prices[i] * weights[i];
        }

        return weightedSum / totalWeight;
    }

    function _calculateMean(uint256[] memory prices, uint256 length) internal pure returns (uint256) {
        uint256 sum = 0;

        for (uint256 i = 0; i < length; i++) {
            sum += prices[i];
        }

        return sum / length;
    }

    function _calculateConfidence(uint256 validSources, uint256 minSources) internal pure returns (uint256) {
        if (validSources >= minSources * 2) {
            return 10000; // 100% confidence with 2x minimum sources
        } else if (validSources >= minSources) {
            // Linear scaling from minimum required to double
            return 7500 + (2500 * (validSources - minSources)) / minSources;
        } else {
            return 0; // Should not happen due to require check
        }
    }

    function _updateSourceReputation(address source, bool success) internal {
        uint256 currentReputation = sourceReputationScore[source];

        if (success) {
            // Increase reputation on successful update (max 10000)
            if (currentReputation < 10000) {
                sourceReputationScore[source] = currentReputation +
                    ((10000 - currentReputation) * 10) / 1000; // 1% of remaining
            }
        } else {
            // Decrease reputation on failure
            sourceReputationScore[source] = currentReputation -
                (currentReputation * 50) / 1000; // 5% decrease
        }
    }

    function _setDefaultConfigs() internal {
        // ETH configuration
        aggregationConfigs["ETH"] = AggregationConfig({
            minSources: 3,
            maxDeviationBPS: 500, // 5%
            staleThreshold: 3600, // 1 hour
            emergencyThreshold: 1000, // 10%
            requireTrustedSource: true,
            aggregationMethod: "MEDIAN"
        });

        // BTC configuration
        aggregationConfigs["BTC"] = AggregationConfig({
            minSources: 3,
            maxDeviationBPS: 500, // 5%
            staleThreshold: 3600, // 1 hour
            emergencyThreshold: 1000, // 10%
            requireTrustedSource: true,
            aggregationMethod: "MEDIAN"
        });

        // USDC configuration (more strict for stablecoin)
        aggregationConfigs["USDC"] = AggregationConfig({
            minSources: 2,
            maxDeviationBPS: 100, // 1%
            staleThreshold: 1800, // 30 minutes
            emergencyThreshold: 200, // 2%
            requireTrustedSource: true,
            aggregationMethod: "WEIGHTED_AVERAGE"
        });
    }

    /**
     * @notice Set governance adapter for DAIO integration
     * @param adapter Address of the governance adapter contract
     */
    function setGovernanceAdapter(address adapter) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(adapter != address(0), "Adapter cannot be zero address");
        governanceAdapter = adapter;
    }

    /**
     * @notice Update source status based on governance decision
     * @param asset Asset symbol
     * @param source Source address
     * @param active Whether source should be active
     */
    function updateSourceStatus(
        string memory asset,
        address source,
        bool active
    ) external {
        require(msg.sender == governanceAdapter || hasRole(ORACLE_MANAGER_ROLE, msg.sender), "Unauthorized");
        require(oracleSources[asset][source].sourceAddress != address(0), "Source does not exist");

        oracleSources[asset][source].active = active;

        emit OracleSourceUpdated(asset, source, oracleSources[asset][source].weight, active);
    }
}