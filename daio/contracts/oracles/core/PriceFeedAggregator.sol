// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./OracleRegistry.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title PriceFeedAggregator
 * @notice Constitutional constraint-compliant price feeds for DAIO integration
 * @dev Aggregates price data with governance oversight and emergency controls
 */
contract PriceFeedAggregator is AccessControl, ReentrancyGuard, Pausable {

    bytes32 public constant FEED_MANAGER_ROLE = keccak256("FEED_MANAGER_ROLE");
    bytes32 public constant CONSTITUTIONAL_VALIDATOR_ROLE = keccak256("CONSTITUTIONAL_VALIDATOR_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");

    // Price feed configuration
    struct PriceFeed {
        string asset;
        address primaryOracle;
        address[] fallbackOracles;
        uint256 maxDeviationBPS;     // Maximum allowed deviation between oracles
        uint256 emergencyThreshold;  // Deviation that triggers emergency mode
        uint256 confidenceThreshold; // Minimum confidence required
        uint256 stalenessThreshold;  // Maximum age of acceptable data
        bool constitutionalCompliant; // Whether feed meets constitutional requirements
        bool emergencyMode;          // Whether feed is in emergency mode
        uint256 totalQueries;        // Total number of price queries
        uint256 lastUpdated;         // Last successful update timestamp
    }

    struct PriceData {
        uint256 price;
        uint256 timestamp;
        uint256 confidence;
        uint256 roundId;
        bool isEmergency;
        address sourceOracle;
    }

    // Constitutional compliance tracking
    struct ConstitutionalConstraints {
        uint256 maxPriceImpactBPS;   // Maximum price impact allowed (15% tithe constraint)
        uint256 diversificationLimit; // Maximum single asset exposure
        uint256 treasuryAllocationCap; // Maximum treasury allocation percentage
        bool requiresMultiSigApproval; // Whether large moves require multi-sig
        uint256 governanceCooldown;   // Cooldown between governance updates
    }

    // State variables
    OracleRegistry public immutable oracleRegistry;
    address public constitutionContract;
    address public treasuryContract;
    address public emergencyTimelock;

    mapping(string => PriceFeed) public priceFeeds;
    mapping(string => PriceData) public latestPrices;
    mapping(string => ConstitutionalConstraints) public constitutionalConstraints;
    mapping(address => bool) public authorizedConsumers;

    string[] public supportedAssets;
    uint256 public totalFeeds;
    uint256 public emergencyModeCount;

    // Performance tracking
    mapping(string => uint256) public assetVolatility;
    mapping(string => uint256) public averageConfidence;
    mapping(address => uint256) public oraclePerformanceScore;

    // Events
    event PriceFeedCreated(
        string indexed asset,
        address indexed primaryOracle,
        uint256 maxDeviation
    );
    event PriceUpdated(
        string indexed asset,
        uint256 price,
        uint256 confidence,
        address sourceOracle
    );
    event EmergencyModeActivated(
        string indexed asset,
        uint256 deviation,
        uint256 threshold
    );
    event EmergencyModeDeactivated(
        string indexed asset
    );
    event ConstitutionalViolation(
        string indexed asset,
        string violationType,
        uint256 value,
        uint256 limit
    );
    event FallbackOracleUsed(
        string indexed asset,
        address fallbackOracle,
        string reason
    );
    event ConsumerAuthorized(
        address indexed consumer,
        bool authorized
    );

    /**
     * @notice Initialize PriceFeedAggregator with DAIO integration
     * @param _oracleRegistry Address of the oracle registry
     * @param _constitutionContract DAIO constitution contract
     * @param _treasuryContract DAIO treasury contract
     * @param _emergencyTimelock Emergency timelock contract
     * @param admin Admin address for role management
     */
    constructor(
        address _oracleRegistry,
        address _constitutionContract,
        address _treasuryContract,
        address _emergencyTimelock,
        address admin
    ) {
        require(_oracleRegistry != address(0), "Oracle registry cannot be zero address");
        require(admin != address(0), "Admin cannot be zero address");

        oracleRegistry = OracleRegistry(_oracleRegistry);
        constitutionContract = _constitutionContract;
        treasuryContract = _treasuryContract;
        emergencyTimelock = _emergencyTimelock;

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(FEED_MANAGER_ROLE, admin);
        _grantRole(CONSTITUTIONAL_VALIDATOR_ROLE, admin);
        _grantRole(EMERGENCY_ROLE, admin);

        // Set default constitutional constraints
        _setDefaultConstitutionalConstraints();
    }

    /**
     * @notice Create a new price feed for an asset
     * @param asset Asset symbol
     * @param primaryOracle Primary oracle address
     * @param fallbackOracles Array of fallback oracle addresses
     * @param maxDeviationBPS Maximum allowed deviation between oracles
     * @param confidenceThreshold Minimum confidence required
     */
    function createPriceFeed(
        string memory asset,
        address primaryOracle,
        address[] memory fallbackOracles,
        uint256 maxDeviationBPS,
        uint256 confidenceThreshold
    ) external onlyRole(FEED_MANAGER_ROLE) {
        require(bytes(asset).length > 0, "Asset cannot be empty");
        require(primaryOracle != address(0), "Primary oracle cannot be zero address");
        require(maxDeviationBPS <= 5000, "Max deviation too high"); // Max 50%
        require(confidenceThreshold <= 10000, "Confidence threshold too high");
        require(priceFeeds[asset].primaryOracle == address(0), "Feed already exists");

        // Validate constitutional compliance
        require(_validateConstitutionalCompliance(asset), "Constitutional compliance check failed");

        priceFeeds[asset] = PriceFeed({
            asset: asset,
            primaryOracle: primaryOracle,
            fallbackOracles: fallbackOracles,
            maxDeviationBPS: maxDeviationBPS,
            emergencyThreshold: maxDeviationBPS * 2, // Emergency at 2x normal deviation
            confidenceThreshold: confidenceThreshold,
            stalenessThreshold: 3600, // 1 hour default
            constitutionalCompliant: true,
            emergencyMode: false,
            totalQueries: 0,
            lastUpdated: 0
        });

        supportedAssets.push(asset);
        totalFeeds++;

        emit PriceFeedCreated(asset, primaryOracle, maxDeviationBPS);
    }

    /**
     * @notice Get latest price for an asset with constitutional validation
     * @param asset Asset symbol
     * @return price Latest price
     * @return timestamp When price was obtained
     * @return confidence Confidence level
     * @return isValid Whether price meets constitutional requirements
     */
    function getPrice(string memory asset) external nonReentrant whenNotPaused returns (
        uint256 price,
        uint256 timestamp,
        uint256 confidence,
        bool isValid
    ) {
        require(bytes(asset).length > 0, "Asset cannot be empty");
        require(priceFeeds[asset].primaryOracle != address(0), "Feed does not exist");
        require(authorizedConsumers[msg.sender] || hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "Unauthorized consumer");

        PriceFeed storage feed = priceFeeds[asset];
        feed.totalQueries++;

        // Try primary oracle first
        (price, timestamp, confidence, isValid) = _getPriceFromOracle(asset, feed.primaryOracle);

        // Check if primary oracle data is acceptable
        if (!isValid || confidence < feed.confidenceThreshold ||
            block.timestamp > timestamp + feed.stalenessThreshold) {

            // Try fallback oracles
            for (uint256 i = 0; i < feed.fallbackOracles.length; i++) {
                (uint256 fallbackPrice, uint256 fallbackTimestamp, uint256 fallbackConfidence, bool fallbackValid) =
                    _getPriceFromOracle(asset, feed.fallbackOracles[i]);

                if (fallbackValid && fallbackConfidence >= feed.confidenceThreshold &&
                    block.timestamp <= fallbackTimestamp + feed.stalenessThreshold) {

                    price = fallbackPrice;
                    timestamp = fallbackTimestamp;
                    confidence = fallbackConfidence;
                    isValid = true;

                    emit FallbackOracleUsed(asset, feed.fallbackOracles[i], "Primary oracle failure");
                    break;
                }
            }
        }

        // Final validation and constitutional check
        if (isValid) {
            isValid = _validateConstitutionalPrice(asset, price);

            if (isValid) {
                // Update latest price data
                latestPrices[asset] = PriceData({
                    price: price,
                    timestamp: timestamp,
                    confidence: confidence,
                    roundId: feed.totalQueries,
                    isEmergency: feed.emergencyMode,
                    sourceOracle: feed.primaryOracle
                });

                feed.lastUpdated = block.timestamp;

                // Check for emergency conditions
                _checkEmergencyConditions(asset, price);

                emit PriceUpdated(asset, price, confidence, feed.primaryOracle);
            }
        }

        return (price, timestamp, confidence, isValid);
    }

    /**
     * @notice Get price with detailed information
     * @param asset Asset symbol
     * @return priceData Complete price data structure
     */
    function getPriceWithDetails(string memory asset) external view returns (PriceData memory priceData) {
        require(priceFeeds[asset].primaryOracle != address(0), "Feed does not exist");
        return latestPrices[asset];
    }

    /**
     * @notice Authorize a consumer to access price feeds
     * @param consumer Consumer contract address
     * @param authorized Whether consumer is authorized
     */
    function setConsumerAuthorization(
        address consumer,
        bool authorized
    ) external onlyRole(FEED_MANAGER_ROLE) {
        require(consumer != address(0), "Consumer cannot be zero address");
        authorizedConsumers[consumer] = authorized;
        emit ConsumerAuthorized(consumer, authorized);
    }

    /**
     * @notice Set constitutional constraints for an asset
     * @param asset Asset symbol
     * @param maxPriceImpactBPS Maximum price impact (BPS)
     * @param diversificationLimit Maximum single asset exposure
     * @param treasuryAllocationCap Maximum treasury allocation
     */
    function setConstitutionalConstraints(
        string memory asset,
        uint256 maxPriceImpactBPS,
        uint256 diversificationLimit,
        uint256 treasuryAllocationCap
    ) external onlyRole(CONSTITUTIONAL_VALIDATOR_ROLE) {
        require(maxPriceImpactBPS <= 1500, "Price impact too high"); // Max 15% (DAIO constitution)
        require(diversificationLimit <= 1500, "Diversification limit too high"); // Max 15%
        require(treasuryAllocationCap <= 10000, "Allocation cap too high");

        constitutionalConstraints[asset] = ConstitutionalConstraints({
            maxPriceImpactBPS: maxPriceImpactBPS,
            diversificationLimit: diversificationLimit,
            treasuryAllocationCap: treasuryAllocationCap,
            requiresMultiSigApproval: treasuryAllocationCap > 500, // 5% threshold
            governanceCooldown: 86400 // 24 hours
        });
    }

    /**
     * @notice Activate emergency mode for an asset
     * @param asset Asset symbol
     * @param reason Reason for emergency activation
     */
    function activateEmergencyMode(
        string memory asset,
        string memory reason
    ) external onlyRole(EMERGENCY_ROLE) {
        require(priceFeeds[asset].primaryOracle != address(0), "Feed does not exist");
        require(!priceFeeds[asset].emergencyMode, "Already in emergency mode");

        priceFeeds[asset].emergencyMode = true;
        emergencyModeCount++;

        emit EmergencyModeActivated(asset, 0, priceFeeds[asset].emergencyThreshold);
    }

    /**
     * @notice Deactivate emergency mode for an asset
     * @param asset Asset symbol
     */
    function deactivateEmergencyMode(
        string memory asset
    ) external onlyRole(EMERGENCY_ROLE) {
        require(priceFeeds[asset].primaryOracle != address(0), "Feed does not exist");
        require(priceFeeds[asset].emergencyMode, "Not in emergency mode");

        priceFeeds[asset].emergencyMode = false;
        if (emergencyModeCount > 0) {
            emergencyModeCount--;
        }

        emit EmergencyModeDeactivated(asset);
    }

    /**
     * @notice Get all supported assets
     * @return assets Array of supported asset symbols
     */
    function getSupportedAssets() external view returns (string[] memory assets) {
        return supportedAssets;
    }

    /**
     * @notice Check if asset is in emergency mode
     * @param asset Asset symbol
     * @return isEmergency Whether asset is in emergency mode
     */
    function isEmergencyMode(string memory asset) external view returns (bool isEmergency) {
        return priceFeeds[asset].emergencyMode;
    }

    /**
     * @notice Get performance metrics for the aggregator
     * @return totalQueries Total number of price queries
     * @return activeFeeds Number of active price feeds
     * @return emergencyFeeds Number of feeds in emergency mode
     * @return averageUptime Average uptime percentage
     */
    function getPerformanceMetrics() external view returns (
        uint256 totalQueries,
        uint256 activeFeeds,
        uint256 emergencyFeeds,
        uint256 averageUptime
    ) {
        uint256 totalQueriesSum = 0;
        uint256 activeCount = 0;

        for (uint256 i = 0; i < supportedAssets.length; i++) {
            string memory asset = supportedAssets[i];
            PriceFeed memory feed = priceFeeds[asset];

            totalQueriesSum += feed.totalQueries;

            if (feed.lastUpdated > 0 && block.timestamp <= feed.lastUpdated + feed.stalenessThreshold) {
                activeCount++;
            }
        }

        // Calculate average uptime (simplified)
        averageUptime = totalFeeds > 0 ? (activeCount * 10000) / totalFeeds : 0;

        return (totalQueriesSum, activeCount, emergencyModeCount, averageUptime);
    }

    // Internal functions

    function _getPriceFromOracle(
        string memory asset,
        address oracle
    ) internal view returns (
        uint256 price,
        uint256 timestamp,
        uint256 confidence,
        bool isValid
    ) {
        try oracleRegistry.getLatestPrice(asset) returns (
            uint256 _price,
            uint256 _timestamp,
            uint256 _roundId,
            uint256 _confidence
        ) {
            return (_price, _timestamp, _confidence, _price > 0);
        } catch {
            return (0, 0, 0, false);
        }
    }

    function _validateConstitutionalCompliance(string memory asset) internal view returns (bool) {
        // Check if asset meets constitutional requirements
        ConstitutionalConstraints memory constraints = constitutionalConstraints[asset];

        // For new assets, use default constraints
        if (constraints.maxPriceImpactBPS == 0) {
            return true; // Allow creation with defaults
        }

        // Validate against DAIO constitution constraints
        if (constraints.diversificationLimit > 1500) { // 15% max per constitution
            return false;
        }

        return true;
    }

    function _validateConstitutionalPrice(
        string memory asset,
        uint256 price
    ) internal returns (bool) {
        ConstitutionalConstraints memory constraints = constitutionalConstraints[asset];
        PriceData memory lastPrice = latestPrices[asset];

        // Check price impact constraint
        if (lastPrice.price > 0) {
            uint256 priceImpact = price > lastPrice.price ?
                ((price - lastPrice.price) * 10000) / lastPrice.price :
                ((lastPrice.price - price) * 10000) / lastPrice.price;

            if (priceImpact > constraints.maxPriceImpactBPS) {
                emit ConstitutionalViolation(asset, "PRICE_IMPACT", priceImpact, constraints.maxPriceImpactBPS);
                return false;
            }
        }

        return true;
    }

    function _checkEmergencyConditions(string memory asset, uint256 price) internal {
        PriceFeed storage feed = priceFeeds[asset];
        PriceData memory lastPrice = latestPrices[asset];

        if (lastPrice.price > 0) {
            uint256 deviation = price > lastPrice.price ?
                ((price - lastPrice.price) * 10000) / lastPrice.price :
                ((lastPrice.price - price) * 10000) / lastPrice.price;

            if (deviation > feed.emergencyThreshold && !feed.emergencyMode) {
                feed.emergencyMode = true;
                emergencyModeCount++;

                emit EmergencyModeActivated(asset, deviation, feed.emergencyThreshold);
            }
        }
    }

    function _setDefaultConstitutionalConstraints() internal {
        // ETH constraints
        constitutionalConstraints["ETH"] = ConstitutionalConstraints({
            maxPriceImpactBPS: 1500,     // 15% max price impact
            diversificationLimit: 1500,   // 15% max exposure
            treasuryAllocationCap: 2500,  // 25% max treasury allocation
            requiresMultiSigApproval: true,
            governanceCooldown: 86400     // 24 hours
        });

        // BTC constraints
        constitutionalConstraints["BTC"] = ConstitutionalConstraints({
            maxPriceImpactBPS: 1500,     // 15% max price impact
            diversificationLimit: 1500,   // 15% max exposure
            treasuryAllocationCap: 2500,  // 25% max treasury allocation
            requiresMultiSigApproval: true,
            governanceCooldown: 86400     // 24 hours
        });

        // USDC constraints (stablecoin - stricter)
        constitutionalConstraints["USDC"] = ConstitutionalConstraints({
            maxPriceImpactBPS: 200,      // 2% max price impact
            diversificationLimit: 3000,   // 30% max exposure (stable asset)
            treasuryAllocationCap: 5000,  // 50% max treasury allocation
            requiresMultiSigApproval: false, // Lower risk
            governanceCooldown: 43200     // 12 hours
        });
    }

    /**
     * @notice Emergency pause all price feeds
     */
    function emergencyPause() external onlyRole(EMERGENCY_ROLE) {
        _pause();
    }

    /**
     * @notice Unpause all price feeds
     */
    function unpause() external onlyRole(EMERGENCY_ROLE) {
        _unpause();
    }

    /**
     * @notice Update feed configuration
     * @param asset Asset symbol
     * @param maxDeviationBPS New maximum deviation
     * @param confidenceThreshold New confidence threshold
     */
    function updateFeedConfig(
        string memory asset,
        uint256 maxDeviationBPS,
        uint256 confidenceThreshold
    ) external onlyRole(FEED_MANAGER_ROLE) {
        require(priceFeeds[asset].primaryOracle != address(0), "Feed does not exist");
        require(maxDeviationBPS <= 5000, "Max deviation too high");
        require(confidenceThreshold <= 10000, "Confidence threshold too high");

        priceFeeds[asset].maxDeviationBPS = maxDeviationBPS;
        priceFeeds[asset].confidenceThreshold = confidenceThreshold;
        priceFeeds[asset].emergencyThreshold = maxDeviationBPS * 2;
    }
}