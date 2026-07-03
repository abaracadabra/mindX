// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title IChainlinkFeed — Chainlink AggregatorV3 compatible interface
 */
interface IChainlinkFeed {
    function latestRoundData() external view returns (
        uint80 roundId, int256 answer, uint256 startedAt,
        uint256 updatedAt, uint80 answeredInRound
    );
    function decimals() external view returns (uint8);
}

/**
 * @title IPriceOracle — PerpetualEngine compatible oracle interface
 * @dev   The DeltaVerseDebtOracle implements this so it can plug directly
 *        into PerpetualEngine as the underlying price feed.
 */
interface IPriceOracle {
    function latestPrice() external view returns (uint256 price, uint256 updatedAt);
    function decimals() external view returns (uint8);
}

/**
 * @title DeltaVerseDebtOracle — Global Debt Index Oracle (v1)
 * @author Professor Codephreak — DELTAVERSE Ecosystem
 * @notice Composite oracle tracking global debt stress via weighted sub-indices.
 *         Implements IPriceOracle for direct integration with PerpetualEngine.
 *
 * Part of: "The Cryptographic Inheritance of Global Debt"
 * Contract IV — Debt Index Data Primitive
 *
 * ═══════════════════════════════════════════════════════════════════
 *  ARCHITECTURE
 * ═══════════════════════════════════════════════════════════════════
 *
 * The oracle constructs a composite Global Debt Stress Index (GDSI) from
 * five weighted sub-indices:
 *
 *   1. SOVEREIGN DEBT RATIO INDEX (SDR)
 *      Tracks aggregate debt-to-GDP across G20 economies.
 *      Source: Off-chain reporters aggregating IMF/BIS data.
 *      Rising values = increasing debt burden.
 *
 *   2. YIELD SPREAD INDEX (YSI)
 *      Tracks sovereign yield spreads vs risk-free benchmark.
 *      Can integrate Chainlink bond yield feeds where available.
 *      Rising values = market pricing higher default/inflation risk.
 *
 *   3. CREDIT STRESS INDEX (CSI)
 *      Tracks CDS spreads, credit downgrades, and default rates.
 *      Rising values = deteriorating credit conditions.
 *
 *   4. MONETARY DEBASEMENT INDEX (MDI)
 *      Tracks M2 money supply growth relative to GDP growth.
 *      Rising values = currency purchasing power erosion.
 *
 *   5. REFINANCING PRESSURE INDEX (RPI)
 *      Tracks the volume of sovereign debt maturing within 12 months
 *      as a percentage of GDP — the "refinancing wall" from Thesis I.
 *      Rising values = increasing rollover risk.
 *
 * ═══════════════════════════════════════════════════════════════════
 *  INDEX METHODOLOGY
 * ═══════════════════════════════════════════════════════════════════
 *
 *   GDSI = Σ(subIndex_i × weight_i) / Σ(weight_i)
 *
 *   Base value: 1000 (= 1000e18 in contract precision)
 *   Interpretation:
 *     < 1000  = Debt stress below historical baseline
 *     = 1000  = Historical baseline (calibrated to Jan 2020)
 *     > 1000  = Elevated debt stress
 *     > 1500  = Critical stress zone
 *     > 2000  = Systemic crisis territory
 *
 *   The index is designed to RISE as global debt conditions deteriorate,
 *   making a SHORT position on this index via PerpetualEngine equivalent
 *   to betting that the debt system stabilizes, and a LONG position
 *   equivalent to the inverse debt thesis from Part I.
 *
 * ═══════════════════════════════════════════════════════════════════
 *  DATA FLOW
 * ═══════════════════════════════════════════════════════════════════
 *
 *   Off-chain keepers / Chainlink nodes
 *         │
 *         ▼
 *   submitSubIndex()  ─── per sub-index, from authorized REPORTER_ROLE
 *         │
 *         ▼
 *   updateComposite() ─── recalculates GDSI from latest sub-indices
 *         │
 *         ▼
 *   latestPrice()     ─── PerpetualEngine reads composite GDSI
 *
 *   Additionally, sub-indices can be backed by Chainlink feeds for
 *   on-chain verifiable data (e.g. ETH/USD as proxy for risk appetite,
 *   or future Chainlink bond yield feeds).
 *
 * ═══════════════════════════════════════════════════════════════════
 *  SECURITY MODEL
 * ═══════════════════════════════════════════════════════════════════
 *
 *   - Multi-reporter median: Each sub-index accepts reports from multiple
 *     authorized reporters. The median value is used (not mean) to resist
 *     manipulation by any single reporter.
 *   - Deviation circuit breaker: If a new composite value deviates more
 *     than maxDeviationBps from the previous value, the update is flagged
 *     and requires governor confirmation.
 *   - Heartbeat enforcement: If no update arrives within heartbeatInterval,
 *     the oracle reports itself as stale (PerpetualEngine will reject it).
 *   - Historical snapshots: Every composite update is stored with timestamp
 *     for derivatives settlement at specific points in time.
 */
contract DeltaVerseDebtOracle is IPriceOracle, AccessControl, Pausable {

    // ════════════════════════════════════════════════════════════════
    //  ROLES
    // ════════════════════════════════════════════════════════════════

    bytes32 public constant REPORTER_ROLE  = keccak256("REPORTER_ROLE");
    bytes32 public constant GOVERNOR_ROLE  = keccak256("GOVERNOR_ROLE");

    // ════════════════════════════════════════════════════════════════
    //  CUSTOM ERRORS
    // ════════════════════════════════════════════════════════════════

    error ZeroValue();
    error ZeroAddress();
    error InvalidSubIndex(uint8 id);
    error SubIndexDisabled(uint8 id);
    error DeviationBreached(uint256 newValue, uint256 oldValue, uint256 maxBps);
    error HeartbeatExpired(uint256 lastUpdate, uint256 heartbeat);
    error ChainlinkFeedStale(address feed, uint256 updatedAt);
    error ChainlinkBadPrice(address feed);
    error NoReportsAvailable(uint8 subIndexId);
    error ReportTooOld(uint256 reportTs, uint256 maxAge);
    error SnapshotNotFound(uint256 roundId);
    error WeightsSumZero();
    error TooManyReporters();
    error DuplicateReport();

    // ════════════════════════════════════════════════════════════════
    //  CONSTANTS
    // ════════════════════════════════════════════════════════════════

    uint256 public constant PRECISION         = 1e18;
    uint256 public constant BASE_INDEX_VALUE  = 1000 * PRECISION;  // 1000.0
    uint256 public constant BPS_DENOMINATOR   = 10_000;
    uint8   public constant ORACLE_DECIMALS   = 18;
    uint8   public constant MAX_SUB_INDICES   = 10;
    uint8   public constant MAX_REPORTERS     = 20;
    uint256 public constant MAX_REPORT_AGE    = 24 hours;

    // ════════════════════════════════════════════════════════════════
    //  SUB-INDEX DEFINITIONS
    // ════════════════════════════════════════════════════════════════

    /// @dev Pre-defined sub-index IDs (extendable up to MAX_SUB_INDICES)
    uint8 public constant SDR_INDEX = 0;  // Sovereign Debt Ratio
    uint8 public constant YSI_INDEX = 1;  // Yield Spread Index
    uint8 public constant CSI_INDEX = 2;  // Credit Stress Index
    uint8 public constant MDI_INDEX = 3;  // Monetary Debasement Index
    uint8 public constant RPI_INDEX = 4;  // Refinancing Pressure Index

    struct SubIndexConfig {
        bool    enabled;
        string  name;                    // human-readable name
        uint256 weight;                  // weight in composite (BPS, e.g. 2500 = 25%)
        uint256 value;                   // current median value (PRECISION scaled)
        uint256 lastUpdated;             // timestamp of last accepted update
        IChainlinkFeed chainlinkFeed;    // optional Chainlink backup feed
        uint256 chainlinkWeight;         // how much to weight Chainlink vs reporters (BPS)
        uint256 maxStaleness;            // per-sub-index staleness threshold
    }

    mapping(uint8 => SubIndexConfig) public subIndices;
    uint8 public activeSubIndexCount;

    // ════════════════════════════════════════════════════════════════
    //  REPORTER SUBMISSIONS
    // ════════════════════════════════════════════════════════════════

    struct Report {
        address reporter;
        uint256 value;       // PRECISION scaled
        uint256 timestamp;
    }

    /// @dev subIndexId => array of current-round reports
    mapping(uint8 => Report[]) internal currentReports;

    /// @dev Tracks whether a reporter has submitted for current round
    mapping(uint8 => mapping(address => bool)) internal hasReported;

    // ════════════════════════════════════════════════════════════════
    //  COMPOSITE INDEX STATE
    // ════════════════════════════════════════════════════════════════

    uint256 public compositeValue;       // current GDSI (PRECISION scaled)
    uint256 public compositeTimestamp;   // last composite update
    uint256 public roundId;              // increments each composite update

    // ════════════════════════════════════════════════════════════════
    //  HISTORICAL SNAPSHOTS (for derivatives settlement)
    // ════════════════════════════════════════════════════════════════

    struct Snapshot {
        uint256 value;
        uint256 timestamp;
        uint256[5] subValues;  // sub-index values at snapshot time
    }

    mapping(uint256 => Snapshot) public snapshots;  // roundId => Snapshot

    // ════════════════════════════════════════════════════════════════
    //  CONFIGURATION
    // ════════════════════════════════════════════════════════════════

    uint256 public heartbeatInterval    = 6 hours;     // max time between updates
    uint256 public maxDeviationBps      = 1000;        // 10% max single-update deviation
    uint256 public minReportsRequired   = 1;           // min reporters before median accepted

    /// @dev When deviation is breached, value is staged here for governor approval
    uint256 public pendingCompositeValue;
    uint256 public pendingCompositeTimestamp;
    bool    public hasPendingUpdate;

    // ════════════════════════════════════════════════════════════════
    //  EVENTS
    // ════════════════════════════════════════════════════════════════

    event SubIndexConfigured(
        uint8 indexed id, string name, uint256 weight, bool enabled
    );
    event SubIndexUpdated(
        uint8 indexed id, uint256 medianValue,
        uint256 reportCount, uint256 timestamp
    );
    event CompositeUpdated(
        uint256 indexed roundId, uint256 value,
        uint256 timestamp, uint256 previousValue
    );
    event DeviationFlagged(
        uint256 newValue, uint256 oldValue, uint256 deviationBps
    );
    event PendingUpdateApproved(uint256 indexed roundId, uint256 value);
    event PendingUpdateRejected(uint256 rejectedValue);
    event ReportSubmitted(
        uint8 indexed subIndexId, address indexed reporter,
        uint256 value, uint256 timestamp
    );
    event HeartbeatUpdated(uint256 oldInterval, uint256 newInterval);
    event ChainlinkFeedSet(uint8 indexed subIndexId, address feed, uint256 weight);

    // ════════════════════════════════════════════════════════════════
    //  CONSTRUCTOR
    // ════════════════════════════════════════════════════════════════

    constructor(address admin_) {
        if (admin_ == address(0)) revert ZeroAddress();

        _grantRole(DEFAULT_ADMIN_ROLE, admin_);
        _grantRole(GOVERNOR_ROLE, admin_);
        _grantRole(REPORTER_ROLE, admin_);

        // Initialize the five core sub-indices with default weights
        _initSubIndex(SDR_INDEX, "Sovereign Debt Ratio",      2500, 6 hours);
        _initSubIndex(YSI_INDEX, "Yield Spread Index",        2000, 4 hours);
        _initSubIndex(CSI_INDEX, "Credit Stress Index",       2000, 4 hours);
        _initSubIndex(MDI_INDEX, "Monetary Debasement Index", 1500, 12 hours);
        _initSubIndex(RPI_INDEX, "Refinancing Pressure Index", 2000, 12 hours);

        // Set initial composite to baseline
        compositeValue     = BASE_INDEX_VALUE;
        compositeTimestamp  = block.timestamp;
        roundId             = 1;

        snapshots[1] = Snapshot({
            value:     BASE_INDEX_VALUE,
            timestamp: block.timestamp,
            subValues: [BASE_INDEX_VALUE, BASE_INDEX_VALUE, BASE_INDEX_VALUE,
                        BASE_INDEX_VALUE, BASE_INDEX_VALUE]
        });
    }

    // ════════════════════════════════════════════════════════════════
    //  IPriceOracle INTERFACE (PerpetualEngine compatible)
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Returns the current composite GDSI value and timestamp
     * @dev    PerpetualEngine calls this to get the "price" of the debt index.
     *         A trader going LONG on this index via PerpetualEngine is
     *         effectively betting that global debt stress increases.
     *         A trader going SHORT is betting it stabilizes.
     * @return price     The composite GDSI value (18 decimal precision)
     * @return updatedAt The timestamp of the last composite update
     */
    function latestPrice()
        external
        view
        override
        returns (uint256 price, uint256 updatedAt)
    {
        return (compositeValue, compositeTimestamp);
    }

    /// @notice Oracle precision — always 18 decimals
    function decimals() external pure override returns (uint8) {
        return ORACLE_DECIMALS;
    }

    // ════════════════════════════════════════════════════════════════
    //  REPORTER SUBMISSION
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Submit a value for a specific sub-index
     * @dev    Multiple reporters can submit for the same sub-index.
     *         The median of all submissions is used when updateComposite()
     *         is called. This resists manipulation by any single reporter.
     *
     * @param subIndexId The sub-index to report on (0-4 for core indices)
     * @param value      The reported value (PRECISION scaled, base 1000e18)
     */
    function submitSubIndex(uint8 subIndexId, uint256 value)
        external
        onlyRole(REPORTER_ROLE)
        whenNotPaused
    {
        if (value == 0) revert ZeroValue();
        SubIndexConfig storage cfg = subIndices[subIndexId];
        if (!cfg.enabled) revert SubIndexDisabled(subIndexId);
        if (hasReported[subIndexId][msg.sender]) revert DuplicateReport();

        Report[] storage reports = currentReports[subIndexId];
        if (reports.length >= MAX_REPORTERS) revert TooManyReporters();

        reports.push(Report({
            reporter:  msg.sender,
            value:     value,
            timestamp: block.timestamp
        }));
        hasReported[subIndexId][msg.sender] = true;

        emit ReportSubmitted(subIndexId, msg.sender, value, block.timestamp);
    }

    /**
     * @notice Finalize a sub-index value from current reports (median)
     * @dev    Can be called by any reporter or keeper once enough reports exist.
     *         Calculates the median of all current-round reports, updates
     *         the sub-index value, and clears reports for the next round.
     */
    function finalizeSubIndex(uint8 subIndexId)
        external
        onlyRole(REPORTER_ROLE)
        whenNotPaused
    {
        SubIndexConfig storage cfg = subIndices[subIndexId];
        if (!cfg.enabled) revert SubIndexDisabled(subIndexId);

        Report[] storage reports = currentReports[subIndexId];
        if (reports.length < minReportsRequired)
            revert NoReportsAvailable(subIndexId);

        // Filter out stale reports
        uint256 validCount;
        uint256[] memory validValues = new uint256[](reports.length);
        for (uint256 i; i < reports.length; ) {
            if (block.timestamp - reports[i].timestamp <= MAX_REPORT_AGE) {
                validValues[validCount] = reports[i].value;
                unchecked { ++validCount; }
            }
            unchecked { ++i; }
        }

        if (validCount < minReportsRequired)
            revert NoReportsAvailable(subIndexId);

        // Calculate median
        uint256 median = _calculateMedian(validValues, validCount);

        // Blend with Chainlink feed if configured
        uint256 finalValue = median;
        if (address(cfg.chainlinkFeed) != address(0) && cfg.chainlinkWeight > 0) {
            uint256 chainlinkValue = _getChainlinkValue(cfg);
            if (chainlinkValue > 0) {
                finalValue = (median * (BPS_DENOMINATOR - cfg.chainlinkWeight)
                             + chainlinkValue * cfg.chainlinkWeight)
                             / BPS_DENOMINATOR;
            }
        }

        // Update sub-index
        cfg.value       = finalValue;
        cfg.lastUpdated = block.timestamp;

        // Clear reports for next round
        _clearReports(subIndexId);

        emit SubIndexUpdated(subIndexId, finalValue, validCount, block.timestamp);
    }

    // ════════════════════════════════════════════════════════════════
    //  COMPOSITE INDEX CALCULATION
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Recalculate the composite GDSI from all sub-indices
     * @dev    Weighted average: GDSI = Σ(value_i × weight_i) / Σ(weight_i)
     *         If the new value deviates more than maxDeviationBps from the
     *         current value, it is staged as pending and requires governor
     *         approval (circuit breaker against data manipulation).
     */
    function updateComposite()
        external
        onlyRole(REPORTER_ROLE)
        whenNotPaused
    {
        uint256 weightedSum;
        uint256 totalWeight;
        uint256[5] memory subValues;

        for (uint8 i; i < activeSubIndexCount; ) {
            SubIndexConfig storage cfg = subIndices[i];
            if (cfg.enabled && cfg.value > 0) {
                // Check sub-index staleness
                if (block.timestamp - cfg.lastUpdated > cfg.maxStaleness) {
                    // Skip stale sub-indices — they don't contribute
                    unchecked { ++i; }
                    continue;
                }
                weightedSum += cfg.value * cfg.weight;
                totalWeight += cfg.weight;
                if (i < 5) subValues[i] = cfg.value;
            }
            unchecked { ++i; }
        }

        if (totalWeight == 0) revert WeightsSumZero();

        uint256 newValue = weightedSum / totalWeight;

        // ── Circuit breaker: check deviation ──
        if (compositeValue > 0) {
            uint256 deviation = newValue > compositeValue
                ? ((newValue - compositeValue) * BPS_DENOMINATOR) / compositeValue
                : ((compositeValue - newValue) * BPS_DENOMINATOR) / compositeValue;

            if (deviation > maxDeviationBps) {
                // Stage for governor approval instead of applying directly
                pendingCompositeValue     = newValue;
                pendingCompositeTimestamp  = block.timestamp;
                hasPendingUpdate          = true;

                emit DeviationFlagged(newValue, compositeValue, deviation);
                return;
            }
        }

        // Apply update
        _applyCompositeUpdate(newValue, subValues);
    }

    /**
     * @notice Governor approves a pending update that breached deviation limits
     */
    function approvePendingUpdate()
        external
        onlyRole(GOVERNOR_ROLE)
    {
        require(hasPendingUpdate, "no pending update");

        uint256[5] memory subValues;
        for (uint8 i; i < 5; ) {
            subValues[i] = subIndices[i].value;
            unchecked { ++i; }
        }

        _applyCompositeUpdate(pendingCompositeValue, subValues);

        hasPendingUpdate          = false;
        pendingCompositeValue     = 0;
        pendingCompositeTimestamp  = 0;

        emit PendingUpdateApproved(roundId, compositeValue);
    }

    /**
     * @notice Governor rejects a pending update (keeps current value)
     */
    function rejectPendingUpdate()
        external
        onlyRole(GOVERNOR_ROLE)
    {
        require(hasPendingUpdate, "no pending update");
        uint256 rejected = pendingCompositeValue;

        hasPendingUpdate          = false;
        pendingCompositeValue     = 0;
        pendingCompositeTimestamp  = 0;

        emit PendingUpdateRejected(rejected);
    }

    // ════════════════════════════════════════════════════════════════
    //  HISTORICAL SNAPSHOTS
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Get a historical snapshot by round ID
     * @dev    Used for derivatives settlement at specific points in time
     */
    function getSnapshot(uint256 _roundId)
        external
        view
        returns (uint256 value, uint256 timestamp, uint256[5] memory subValues)
    {
        Snapshot storage s = snapshots[_roundId];
        if (s.timestamp == 0) revert SnapshotNotFound(_roundId);
        return (s.value, s.timestamp, s.subValues);
    }

    /**
     * @notice Get the latest N snapshots for charting/analysis
     * @param count Number of recent snapshots to return
     */
    function getRecentSnapshots(uint256 count)
        external
        view
        returns (uint256[] memory values, uint256[] memory timestamps)
    {
        if (count > roundId) count = roundId;

        values     = new uint256[](count);
        timestamps = new uint256[](count);

        for (uint256 i; i < count; ) {
            uint256 rid = roundId - i;
            Snapshot storage s = snapshots[rid];
            values[i]     = s.value;
            timestamps[i] = s.timestamp;
            unchecked { ++i; }
        }
    }

    // ════════════════════════════════════════════════════════════════
    //  VIEW FUNCTIONS
    // ════════════════════════════════════════════════════════════════

    /// @notice Check if the oracle is within its heartbeat (not stale)
    function isHeartbeatAlive() external view returns (bool) {
        return (block.timestamp - compositeTimestamp) <= heartbeatInterval;
    }

    /// @notice Get all sub-index values and weights
    function getAllSubIndices()
        external
        view
        returns (
            string[] memory names,
            uint256[] memory values,
            uint256[] memory weights,
            uint256[] memory lastUpdated,
            bool[]    memory enabled
        )
    {
        uint8 count = activeSubIndexCount;
        names       = new string[](count);
        values      = new uint256[](count);
        weights     = new uint256[](count);
        lastUpdated = new uint256[](count);
        enabled     = new bool[](count);

        for (uint8 i; i < count; ) {
            SubIndexConfig storage cfg = subIndices[i];
            names[i]       = cfg.name;
            values[i]      = cfg.value;
            weights[i]     = cfg.weight;
            lastUpdated[i] = cfg.lastUpdated;
            enabled[i]     = cfg.enabled;
            unchecked { ++i; }
        }
    }

    /// @notice Get current number of pending reports for a sub-index
    function getReportCount(uint8 subIndexId) external view returns (uint256) {
        return currentReports[subIndexId].length;
    }

    /**
     * @notice Calculate the current index change from baseline (in BPS)
     * @return changeBps Positive = above baseline, negative = below
     */
    function indexChangeBps() external view returns (int256 changeBps) {
        if (compositeValue >= BASE_INDEX_VALUE) {
            changeBps = int256(
                ((compositeValue - BASE_INDEX_VALUE) * BPS_DENOMINATOR)
                / BASE_INDEX_VALUE
            );
        } else {
            changeBps = -int256(
                ((BASE_INDEX_VALUE - compositeValue) * BPS_DENOMINATOR)
                / BASE_INDEX_VALUE
            );
        }
    }

    /**
     * @notice Interpret the current stress level as a human-readable category
     * @return level 0=Low, 1=Moderate, 2=Elevated, 3=High, 4=Critical, 5=Systemic
     */
    function stressLevel() external view returns (uint8 level) {
        uint256 v = compositeValue / PRECISION; // de-scale for comparison
        if (v < 800)  return 0;  // Low
        if (v < 1000) return 1;  // Moderate
        if (v < 1250) return 2;  // Elevated
        if (v < 1500) return 3;  // High
        if (v < 2000) return 4;  // Critical
        return 5;                // Systemic
    }

    // ════════════════════════════════════════════════════════════════
    //  ADMIN / CONFIGURATION
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Add a new sub-index beyond the initial five
     * @param id          Sub-index ID (must be >= 5, < MAX_SUB_INDICES)
     * @param name        Human-readable name
     * @param weight      Weight in BPS
     * @param maxStale    Max staleness in seconds
     */
    function addSubIndex(
        uint8   id,
        string calldata name,
        uint256 weight,
        uint256 maxStale
    )
        external
        onlyRole(GOVERNOR_ROLE)
    {
        require(id >= activeSubIndexCount && id < MAX_SUB_INDICES, "invalid id");
        require(!subIndices[id].enabled, "already exists");

        subIndices[id] = SubIndexConfig({
            enabled:          true,
            name:             name,
            weight:           weight,
            value:            BASE_INDEX_VALUE,
            lastUpdated:      block.timestamp,
            chainlinkFeed:    IChainlinkFeed(address(0)),
            chainlinkWeight:  0,
            maxStaleness:     maxStale
        });

        if (id >= activeSubIndexCount) {
            activeSubIndexCount = id + 1;
        }

        emit SubIndexConfigured(id, name, weight, true);
    }

    /// @notice Update the weight of a sub-index
    function setSubIndexWeight(uint8 id, uint256 weight)
        external
        onlyRole(GOVERNOR_ROLE)
    {
        if (id >= activeSubIndexCount) revert InvalidSubIndex(id);
        subIndices[id].weight = weight;
        emit SubIndexConfigured(id, subIndices[id].name, weight, subIndices[id].enabled);
    }

    /// @notice Enable or disable a sub-index
    function setSubIndexEnabled(uint8 id, bool enabled)
        external
        onlyRole(GOVERNOR_ROLE)
    {
        if (id >= activeSubIndexCount) revert InvalidSubIndex(id);
        subIndices[id].enabled = enabled;
        emit SubIndexConfigured(id, subIndices[id].name, subIndices[id].weight, enabled);
    }

    /// @notice Attach a Chainlink feed to a sub-index for blended valuation
    function setChainlinkFeed(
        uint8 id, address feed, uint256 weightBps
    )
        external
        onlyRole(GOVERNOR_ROLE)
    {
        if (id >= activeSubIndexCount) revert InvalidSubIndex(id);
        require(weightBps <= BPS_DENOMINATOR, "weight > 100%");

        subIndices[id].chainlinkFeed   = IChainlinkFeed(feed);
        subIndices[id].chainlinkWeight = weightBps;

        emit ChainlinkFeedSet(id, feed, weightBps);
    }

    function setHeartbeatInterval(uint256 interval)
        external
        onlyRole(GOVERNOR_ROLE)
    {
        uint256 old = heartbeatInterval;
        heartbeatInterval = interval;
        emit HeartbeatUpdated(old, interval);
    }

    function setMaxDeviation(uint256 bps)
        external
        onlyRole(GOVERNOR_ROLE)
    {
        maxDeviationBps = bps;
    }

    function setMinReports(uint256 min)
        external
        onlyRole(GOVERNOR_ROLE)
    {
        minReportsRequired = min;
    }

    /**
     * @notice Emergency: directly set composite value (governor only)
     * @dev    For use only in extreme circumstances (oracle failure, migration)
     */
    function emergencySetComposite(uint256 value)
        external
        onlyRole(GOVERNOR_ROLE)
    {
        if (value == 0) revert ZeroValue();
        uint256 prev = compositeValue;

        uint256[5] memory subValues;
        for (uint8 i; i < 5; ) {
            subValues[i] = subIndices[i].value;
            unchecked { ++i; }
        }

        _applyCompositeUpdate(value, subValues);
        emit CompositeUpdated(roundId, value, block.timestamp, prev);
    }

    function pause() external onlyRole(GOVERNOR_ROLE) { _pause(); }
    function unpause() external onlyRole(GOVERNOR_ROLE) { _unpause(); }

    // ════════════════════════════════════════════════════════════════
    //  INTERNAL
    // ════════════════════════════════════════════════════════════════

    /// @dev Initialize a sub-index in the constructor
    function _initSubIndex(
        uint8 id, string memory name, uint256 weight, uint256 maxStale
    ) internal {
        subIndices[id] = SubIndexConfig({
            enabled:          true,
            name:             name,
            weight:           weight,
            value:            BASE_INDEX_VALUE,
            lastUpdated:      block.timestamp,
            chainlinkFeed:    IChainlinkFeed(address(0)),
            chainlinkWeight:  0,
            maxStaleness:     maxStale
        });
        activeSubIndexCount = id + 1;
    }

    /// @dev Apply a validated composite update and record snapshot
    function _applyCompositeUpdate(
        uint256 newValue,
        uint256[5] memory subValues
    ) internal {
        uint256 prev = compositeValue;
        compositeValue    = newValue;
        compositeTimestamp = block.timestamp;
        roundId++;

        snapshots[roundId] = Snapshot({
            value:     newValue,
            timestamp: block.timestamp,
            subValues: subValues
        });

        emit CompositeUpdated(roundId, newValue, block.timestamp, prev);
    }

    /// @dev Clear all reports for a sub-index (new round)
    function _clearReports(uint8 subIndexId) internal {
        Report[] storage reports = currentReports[subIndexId];
        for (uint256 i; i < reports.length; ) {
            hasReported[subIndexId][reports[i].reporter] = false;
            unchecked { ++i; }
        }
        delete currentReports[subIndexId];
    }

    /**
     * @dev Calculate the median of an array of values
     *      Uses insertion sort (fine for small arrays, max MAX_REPORTERS = 20)
     */
    function _calculateMedian(uint256[] memory values, uint256 count)
        internal
        pure
        returns (uint256)
    {
        // Insertion sort (efficient for small N)
        for (uint256 i = 1; i < count; ) {
            uint256 key = values[i];
            uint256 j = i;
            while (j > 0 && values[j - 1] > key) {
                values[j] = values[j - 1];
                j--;
            }
            values[j] = key;
            unchecked { ++i; }
        }

        if (count % 2 == 1) {
            return values[count / 2];
        } else {
            return (values[count / 2 - 1] + values[count / 2]) / 2;
        }
    }

    /**
     * @dev Fetch a value from a Chainlink feed and normalize to PRECISION
     *      Returns 0 if feed is stale or returns bad data (non-reverting)
     */
    function _getChainlinkValue(SubIndexConfig storage cfg)
        internal
        view
        returns (uint256)
    {
        try cfg.chainlinkFeed.latestRoundData() returns (
            uint80, int256 answer, uint256, uint256 updatedAt, uint80
        ) {
            if (answer <= 0) return 0;
            if (block.timestamp - updatedAt > cfg.maxStaleness) return 0;

            uint8 feedDec = cfg.chainlinkFeed.decimals();
            uint256 price = uint256(answer);

            // Normalize to PRECISION (1e18)
            if (feedDec < 18) {
                price = price * (10 ** (18 - feedDec));
            } else if (feedDec > 18) {
                price = price / (10 ** (feedDec - 18));
            }

            return price;
        } catch {
            return 0; // Non-reverting: Chainlink failure falls back to reporter median
        }
    }
}
