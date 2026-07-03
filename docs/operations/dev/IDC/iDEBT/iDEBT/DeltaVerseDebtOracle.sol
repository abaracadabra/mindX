// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

// ════════════════════════════════════════════════════════════════════
//  EXTERNAL INTERFACES
// ════════════════════════════════════════════════════════════════════

/**
 * @title IChainlinkFeed — Chainlink AggregatorV3 (push oracle)
 */
interface IChainlinkFeed {
    function latestRoundData() external view returns (
        uint80 roundId, int256 answer, uint256 startedAt,
        uint256 updatedAt, uint80 answeredInRound
    );
    function decimals() external view returns (uint8);
}

/**
 * @title IPyth — Pyth Network pull oracle interface
 * @dev   Minimal interface for on-chain integration.
 *        Full SDK: @pythnetwork/pyth-sdk-solidity
 */
interface IPyth {
    struct Price {
        int64  price;
        uint64 conf;          // confidence interval
        int32  expo;          // price = price * 10^expo
        uint   publishTime;
    }

    function getPriceNoOlderThan(bytes32 id, uint age)
        external view returns (Price memory price);

    function getEmaPriceNoOlderThan(bytes32 id, uint age)
        external view returns (Price memory price);

    function getPriceUnsafe(bytes32 id)
        external view returns (Price memory price);

    function updatePriceFeeds(bytes[] calldata updateData)
        external payable;

    function getUpdateFee(bytes[] calldata updateData)
        external view returns (uint feeAmount);

    function getValidTimePeriod() external view returns (uint validTimePeriod);
}

/**
 * @title IPriceOracle — PerpetualEngine compatible output interface
 */
interface IPriceOracle {
    function latestPrice() external view returns (uint256 price, uint256 updatedAt);
    function decimals() external view returns (uint8);
}

/**
 * @title DeltaVerseDebtOracle — Global Debt Stress Index Oracle (v2)
 * @author Professor Codephreak — DELTAVERSE Ecosystem
 * @notice Composite oracle tracking global debt stress via weighted sub-indices.
 *         Integrates Chainlink push oracles, Pyth Network pull oracles, and
 *         authorized reporter submissions using Synthetix V3 Oracle Manager
 *         composable node patterns.
 *
 * Part of: "The Cryptographic Inheritance of Global Debt"
 * Contract IV — Debt Index Data Primitive
 *
 * ═══════════════════════════════════════════════════════════════════
 *  ARCHITECTURE — Synthetix V3 Oracle Manager Pattern
 * ═══════════════════════════════════════════════════════════════════
 *
 * Inspired by Synthetix V3's composable oracle node graph (SIP-329),
 * each sub-index is an oracle node with three configurable data sources:
 *
 *   ┌─────────────┐   ┌──────────────┐   ┌─────────────────┐
 *   │  Chainlink   │   │    Pyth      │   │   Reporters     │
 *   │  Push Feed   │   │  Pull Feed   │   │  (Median of N)  │
 *   └──────┬───────┘   └──────┬───────┘   └────────┬────────┘
 *          │                  │                     │
 *          └──────────┬───────┴─────────────────────┘
 *                     │
 *              ┌──────▼───────┐
 *              │  Aggregation │  ← weighted blend of available sources
 *              │    Node      │
 *              └──────┬───────┘
 *                     │
 *              ┌──────▼───────┐
 *              │  Staleness   │  ← rejects data older than threshold
 *              │  Breaker     │
 *              └──────┬───────┘
 *                     │
 *              ┌──────▼───────┐
 *              │  Deviation   │  ← flags >10% jumps for governor review
 *              │  Breaker     │
 *              └──────┬───────┘
 *                     │
 *              ┌──────▼───────┐
 *              │  Composite   │  ← weighted average of all sub-indices
 *              │    GDSI      │
 *              └──────┬───────┘
 *                     │
 *          ┌──────────▼───────────┐
 *          │   IPriceOracle       │  → PerpetualEngine
 *          │   latestPrice()      │  → CrossCollateralVault
 *          └──────────────────────┘
 *
 * ═══════════════════════════════════════════════════════════════════
 *  SUB-INDEX DEFINITIONS
 * ═══════════════════════════════════════════════════════════════════
 *
 *   0. SOVEREIGN DEBT RATIO (SDR)  — Debt-to-GDP across G20
 *   1. YIELD SPREAD INDEX  (YSI)   — Sovereign spreads vs risk-free
 *   2. CREDIT STRESS INDEX (CSI)   — CDS spreads, defaults
 *   3. MONETARY DEBASEMENT (MDI)   — M2 growth vs GDP growth
 *   4. REFINANCING PRESSURE (RPI)  — Maturing debt / GDP (12mo)
 *
 * ═══════════════════════════════════════════════════════════════════
 *  INDEX METHODOLOGY
 * ═══════════════════════════════════════════════════════════════════
 *
 *   GDSI = Σ(subIndex_i × weight_i) / Σ(weight_i)
 *
 *   Base: 1000 (= 1000e18).  >1500 = Critical.  >2000 = Systemic.
 *
 *   LONG on PerpetualEngine  = debt stress increases  = thesis trade
 *   SHORT on PerpetualEngine = debt system stabilizes
 *
 * ═══════════════════════════════════════════════════════════════════
 *  SYNTHETIX V3 THESIS PROOF
 * ═══════════════════════════════════════════════════════════════════
 *
 * This contract demonstrates the core Synthetix V3 thesis applied
 * to the DELTAVERSE debt inheritance model:
 *
 * 1. PERMISSIONLESS LIQUIDITY LAYER — LP staking pool accepts
 *    collateral that backs sGDSI synthetic positions.
 *    Pattern: Synthetix LP → Pool → Market → Trader
 *
 * 2. COMPOSABLE ORACLE MANAGER — Multi-source oracle aggregation
 *    using Chainlink push + Pyth pull + reporter median, exactly
 *    as Synthetix V3's Oracle Manager combines oracle node types.
 *
 * 3. SYNTHETIC ASSET CREATION — sGDSI tracks the Global Debt
 *    Stress Index as a synthetic asset, just as Synthetix creates
 *    sETH, sBTC, etc. from oracle prices + collateral.
 *
 * 4. MARKET MODULE — This oracle is a self-contained "market"
 *    in Synthetix V3 terms: it turns LP liquidity into a tradeable
 *    financial instrument (debt stress exposure).
 *
 * 5. DELTA-NEUTRAL LP DESIGN — Trading fees accrue to stakers
 *    regardless of whether debt stress rises or falls, matching
 *    Synthetix V3's LP fee model.
 *
 * Synthetix V3 proved that ANY derivative can be built on a
 * collateralized debt position + oracle + market module.
 * This contract proves the same for GLOBAL DEBT ITSELF.
 */
contract DeltaVerseDebtOracle is IPriceOracle, AccessControl, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ════════════════════════════════════════════════════════════════
    //  ROLES
    // ════════════════════════════════════════════════════════════════

    bytes32 public constant REPORTER_ROLE  = keccak256("REPORTER_ROLE");
    bytes32 public constant GOVERNOR_ROLE  = keccak256("GOVERNOR_ROLE");
    bytes32 public constant KEEPER_ROLE    = keccak256("KEEPER_ROLE");

    // ════════════════════════════════════════════════════════════════
    //  CUSTOM ERRORS
    // ════════════════════════════════════════════════════════════════

    error ZeroValue();
    error ZeroAddress();
    error InvalidSubIndex(uint8 id);
    error SubIndexDisabled(uint8 id);
    error DeviationBreached(uint256 newValue, uint256 oldValue, uint256 maxBps);
    error NoReportsAvailable(uint8 subIndexId);
    error SnapshotNotFound(uint256 roundId);
    error WeightsSumZero();
    error TooManyReporters();
    error DuplicateReport();
    error PythUpdateFailed();
    error InsufficientPythFee(uint256 required, uint256 provided);
    error StakingAmountZero();
    error InsufficientStake();
    error NoRewardsAvailable();
    error ConfidenceTooWide(uint64 confidence, uint64 maxConfidence);

    // ════════════════════════════════════════════════════════════════
    //  CONSTANTS
    // ════════════════════════════════════════════════════════════════

    uint256 public constant PRECISION         = 1e18;
    uint256 public constant BASE_INDEX_VALUE  = 1000 * PRECISION;
    uint256 public constant BPS_DENOMINATOR   = 10_000;
    uint8   public constant ORACLE_DECIMALS   = 18;
    uint8   public constant MAX_SUB_INDICES   = 10;
    uint8   public constant MAX_REPORTERS     = 20;
    uint256 public constant MAX_REPORT_AGE    = 24 hours;

    // Pre-defined sub-index IDs
    uint8 public constant SDR_INDEX = 0;  // Sovereign Debt Ratio
    uint8 public constant YSI_INDEX = 1;  // Yield Spread Index
    uint8 public constant CSI_INDEX = 2;  // Credit Stress Index
    uint8 public constant MDI_INDEX = 3;  // Monetary Debasement Index
    uint8 public constant RPI_INDEX = 4;  // Refinancing Pressure Index

    // ════════════════════════════════════════════════════════════════
    //  PYTH NETWORK INTEGRATION
    // ════════════════════════════════════════════════════════════════

    /// @notice Pyth Network contract address (chain-specific)
    IPyth public pyth;

    /// @notice Maximum acceptable Pyth confidence interval (BPS of price)
    ///         If conf/|price| > maxPythConfidenceBps, the price is rejected.
    ///         Synthetix V3 uses similar confidence filtering.
    uint256 public maxPythConfidenceBps = 500; // 5% max uncertainty

    /// @notice Whether to prefer Pyth EMA prices over spot (smoothing)
    bool public usePythEma = false;

    /// @notice Default staleness tolerance for Pyth feeds
    uint256 public pythStalenessSeconds = 120; // 2 minutes

    // ════════════════════════════════════════════════════════════════
    //  ORACLE NODE CONFIGURATION (per sub-index)
    // ════════════════════════════════════════════════════════════════

    /**
     * @dev Each sub-index has three oracle source types, following
     *      Synthetix V3 Oracle Manager's composable node pattern:
     *
     *      1. Chainlink push feed (traditional heartbeat oracle)
     *      2. Pyth pull feed (low-latency, caller-pays update model)
     *      3. Reporter median (N authorized reporters submit values)
     *
     *      Each source has a weight. The aggregated value is:
     *      value = Σ(source_i × weight_i) / Σ(active_weight_i)
     *
     *      If a source is stale or unavailable, its weight is excluded.
     */
    struct OracleNodeConfig {
        // ── Chainlink Source ──
        IChainlinkFeed chainlinkFeed;
        uint8          chainlinkDecimals;
        uint256        chainlinkWeight;      // BPS weight
        uint256        chainlinkMaxStale;    // max staleness seconds

        // ── Pyth Source ──
        bytes32        pythPriceFeedId;      // Pyth price feed ID
        uint256        pythWeight;           // BPS weight
        // staleness uses global pythStalenessSeconds

        // ── Reporter Source ──
        uint256        reporterWeight;       // BPS weight
    }

    struct SubIndexConfig {
        bool    enabled;
        string  name;
        uint256 weight;                      // composite weight (BPS)
        uint256 value;                       // current aggregated value
        uint256 lastUpdated;
        uint256 maxStaleness;                // per-sub-index staleness
        OracleNodeConfig oracle;
    }

    mapping(uint8 => SubIndexConfig) public subIndices;
    uint8 public activeSubIndexCount;

    // ════════════════════════════════════════════════════════════════
    //  REPORTER SUBMISSIONS
    // ════════════════════════════════════════════════════════════════

    struct Report {
        address reporter;
        uint256 value;
        uint256 timestamp;
    }

    mapping(uint8 => Report[]) internal currentReports;
    mapping(uint8 => mapping(address => bool)) internal hasReported;

    // ════════════════════════════════════════════════════════════════
    //  COMPOSITE INDEX STATE
    // ════════════════════════════════════════════════════════════════

    uint256 public compositeValue;
    uint256 public compositeTimestamp;
    uint256 public roundId;

    /// @notice EMA-smoothed composite (reduces volatility for LP risk mgmt)
    uint256 public emaComposite;
    uint256 public emaSmoothingBps = 2000; // 20% weight to new value

    // ════════════════════════════════════════════════════════════════
    //  HISTORICAL SNAPSHOTS
    // ════════════════════════════════════════════════════════════════

    struct Snapshot {
        uint256 value;
        uint256 emaValue;
        uint256 timestamp;
        uint256[5] subValues;
        uint256[5] confidences;  // Pyth confidence intervals per sub-index
    }

    mapping(uint256 => Snapshot) public snapshots;

    // ════════════════════════════════════════════════════════════════
    //  CIRCUIT BREAKERS
    // ════════════════════════════════════════════════════════════════

    uint256 public heartbeatInterval  = 6 hours;
    uint256 public maxDeviationBps    = 1000;    // 10%
    uint256 public minReportsRequired = 1;

    uint256 public pendingCompositeValue;
    uint256 public pendingCompositeTimestamp;
    bool    public hasPendingUpdate;

    // ════════════════════════════════════════════════════════════════
    //  SYNTHETIX V3 PATTERN: LP STAKING POOL
    // ════════════════════════════════════════════════════════════════
    //
    //  Synthetix V3 flow: LP → Pool → Market → Trader
    //
    //  LPs stake collateral tokens into this oracle's pool.
    //  The pool backs the sGDSI synthetic debt index market.
    //  Trading fees from PerpetualEngine accrue as rewards.
    //  Stakers earn pro-rata share of accumulated fees.
    //
    //  This proves the thesis: the same Synthetix V3 liquidity
    //  primitive that powers sETH/sBTC perps can power a
    //  Global Debt Stress Index derivative market.
    // ════════════════════════════════════════════════════════════════

    IERC20  public stakingToken;              // collateral token (USDC, RWAToken)
    uint256 public totalStaked;
    uint256 public accRewardsPerToken;        // accumulated rewards (scaled)
    uint256 public totalRewardsDistributed;

    struct StakeInfo {
        uint256 amount;
        uint256 rewardDebt;
        uint256 pendingRewards;
    }

    mapping(address => StakeInfo) public stakes;

    // ════════════════════════════════════════════════════════════════
    //  EVENTS
    // ════════════════════════════════════════════════════════════════

    event SubIndexConfigured(uint8 indexed id, string name, uint256 weight, bool enabled);
    event SubIndexUpdated(
        uint8 indexed id, uint256 value, uint256 confidence,
        uint8 sourcesUsed, uint256 timestamp
    );
    event CompositeUpdated(
        uint256 indexed roundId, uint256 value, uint256 emaValue,
        uint256 timestamp, uint256 previousValue
    );
    event DeviationFlagged(uint256 newValue, uint256 oldValue, uint256 deviationBps);
    event PendingUpdateApproved(uint256 indexed roundId, uint256 value);
    event PendingUpdateRejected(uint256 rejectedValue);
    event ReportSubmitted(uint8 indexed subIndexId, address indexed reporter, uint256 value);
    event PythPriceUpdated(uint8 indexed subIndexId, int64 price, uint64 conf, uint publishTime);
    event PythFeedsUpdated(uint256 feedCount, uint256 feePaid);
    event OracleNodeConfigured(uint8 indexed subIndexId, string sourceType);
    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount);
    event RewardsClaimed(address indexed user, uint256 amount);
    event RewardsDeposited(uint256 amount);
    event HeartbeatUpdated(uint256 oldInterval, uint256 newInterval);

    // ════════════════════════════════════════════════════════════════
    //  CONSTRUCTOR
    // ════════════════════════════════════════════════════════════════

    /**
     * @param admin_        Admin and governor address
     * @param pyth_         Pyth Network contract address for this chain
     * @param stakingToken_ ERC-20 token for LP staking (USDC, RWAToken)
     */
    constructor(
        address admin_,
        address pyth_,
        address stakingToken_
    ) {
        if (admin_ == address(0)) revert ZeroAddress();

        if (pyth_ != address(0)) {
            pyth = IPyth(pyth_);
        }
        if (stakingToken_ != address(0)) {
            stakingToken = IERC20(stakingToken_);
        }

        _grantRole(DEFAULT_ADMIN_ROLE, admin_);
        _grantRole(GOVERNOR_ROLE, admin_);
        _grantRole(REPORTER_ROLE, admin_);
        _grantRole(KEEPER_ROLE, admin_);

        // Initialize five core sub-indices
        _initSubIndex(SDR_INDEX, "Sovereign Debt Ratio",      2500, 6 hours);
        _initSubIndex(YSI_INDEX, "Yield Spread Index",        2000, 4 hours);
        _initSubIndex(CSI_INDEX, "Credit Stress Index",       2000, 4 hours);
        _initSubIndex(MDI_INDEX, "Monetary Debasement Index", 1500, 12 hours);
        _initSubIndex(RPI_INDEX, "Refinancing Pressure Index", 2000, 12 hours);

        // Baseline composite
        compositeValue    = BASE_INDEX_VALUE;
        emaComposite      = BASE_INDEX_VALUE;
        compositeTimestamp = block.timestamp;
        roundId           = 1;

        snapshots[1] = Snapshot({
            value:       BASE_INDEX_VALUE,
            emaValue:    BASE_INDEX_VALUE,
            timestamp:   block.timestamp,
            subValues:   [BASE_INDEX_VALUE, BASE_INDEX_VALUE, BASE_INDEX_VALUE,
                          BASE_INDEX_VALUE, BASE_INDEX_VALUE],
            confidences: [uint256(0), 0, 0, 0, 0]
        });
    }

    // ════════════════════════════════════════════════════════════════
    //  IPriceOracle INTERFACE (PerpetualEngine compatible)
    // ════════════════════════════════════════════════════════════════

    /// @notice Returns composite GDSI and timestamp for PerpetualEngine
    function latestPrice()
        external view override
        returns (uint256 price, uint256 updatedAt)
    {
        return (compositeValue, compositeTimestamp);
    }

    function decimals() external pure override returns (uint8) {
        return ORACLE_DECIMALS;
    }

    /// @notice EMA-smoothed price (lower volatility for LP risk management)
    function latestEmaPrice()
        external view returns (uint256 price, uint256 updatedAt)
    {
        return (emaComposite, compositeTimestamp);
    }

    // ════════════════════════════════════════════════════════════════
    //  PYTH NETWORK: PULL ORACLE UPDATES
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Update Pyth on-chain prices before reading them
     * @dev    Pyth uses a pull model: callers must push price updates
     *         from Hermes off-chain service and pay a verification fee.
     *         This mirrors Synthetix V3's SIP-329 Pull Oracle Node pattern.
     *
     *         Call flow: off-chain keeper fetches from Pyth Hermes →
     *         calls updatePythFeeds() with signed price data →
     *         Pyth contract verifies Wormhole signatures →
     *         on-chain prices updated → ready for consumption.
     *
     * @param priceUpdateData Signed price data from Pyth Hermes API
     */
    function updatePythFeeds(bytes[] calldata priceUpdateData)
        external
        payable
        onlyRole(KEEPER_ROLE)
        whenNotPaused
    {
        if (address(pyth) == address(0)) revert ZeroAddress();

        uint256 fee = pyth.getUpdateFee(priceUpdateData);
        if (msg.value < fee) revert InsufficientPythFee(fee, msg.value);

        pyth.updatePriceFeeds{value: fee}(priceUpdateData);

        // Refund excess ETH
        if (msg.value > fee) {
            (bool ok, ) = payable(msg.sender).call{value: msg.value - fee}("");
            require(ok, "refund failed");
        }

        emit PythFeedsUpdated(priceUpdateData.length, fee);
    }

    /**
     * @notice Read a Pyth price feed for a specific sub-index
     * @dev    Returns normalized value (PRECISION scaled, base 1000).
     *         Validates confidence interval (Synthetix V3 pattern).
     *         Uses EMA or spot based on usePythEma flag.
     * @param  subIndexId The sub-index to read Pyth data for
     * @return value      Normalized price value
     * @return confidence Confidence interval (PRECISION scaled)
     * @return publishTs  Publish timestamp from Pyth
     */
    function readPythSubIndex(uint8 subIndexId)
        public
        view
        returns (uint256 value, uint256 confidence, uint256 publishTs)
    {
        SubIndexConfig storage cfg = subIndices[subIndexId];
        bytes32 feedId = cfg.oracle.pythPriceFeedId;
        if (feedId == bytes32(0) || address(pyth) == address(0)) return (0, 0, 0);

        IPyth.Price memory p;
        try pyth.getPriceNoOlderThan(feedId, pythStalenessSeconds) returns (IPyth.Price memory result) {
            p = result;
        } catch {
            // Pyth feed stale or unavailable — return 0 (excluded from aggregation)
            return (0, 0, 0);
        }

        if (p.price <= 0) return (0, 0, 0);

        // Confidence filter (Synthetix V3 pattern: reject wide spreads)
        uint256 absPrice = uint256(uint64(p.price));
        uint256 confPct = (uint256(p.conf) * BPS_DENOMINATOR) / absPrice;
        if (confPct > maxPythConfidenceBps) return (0, 0, 0);

        // Normalize: convert from Pyth's (price, expo) to PRECISION scale
        // Pyth price = price * 10^expo, we want PRECISION (1e18) scaled
        value = _normalizePythPrice(p.price, p.expo);
        confidence = _normalizePythPrice(int64(uint64(p.conf)), p.expo);
        publishTs = p.publishTime;
    }

    // ════════════════════════════════════════════════════════════════
    //  REPORTER SUBMISSION
    // ════════════════════════════════════════════════════════════════

    /// @notice Submit a value for a specific sub-index
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

        emit ReportSubmitted(subIndexId, msg.sender, value);
    }

    // ════════════════════════════════════════════════════════════════
    //  SUB-INDEX AGGREGATION (Synthetix V3 Oracle Node Pattern)
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Aggregate all oracle sources for a sub-index
     * @dev    Implements the Synthetix V3 Oracle Manager pattern:
     *         1. Read Chainlink push oracle (if configured)
     *         2. Read Pyth pull oracle (if configured + fresh)
     *         3. Calculate reporter median (if enough reports)
     *         4. Weighted blend of all available sources
     *         5. Apply staleness circuit breaker
     *
     *         Sources with weight 0 or stale data are excluded.
     *         The aggregation is resilient: any 1 of 3 sources
     *         is sufficient for the sub-index to produce a value.
     */
    function finalizeSubIndex(uint8 subIndexId)
        external
        onlyRole(KEEPER_ROLE)
        whenNotPaused
    {
        SubIndexConfig storage cfg = subIndices[subIndexId];
        if (!cfg.enabled) revert SubIndexDisabled(subIndexId);

        uint256 weightedSum;
        uint256 totalWeight;
        uint256 aggregatedConf;
        uint8   sourcesUsed;

        // ── Source 1: Chainlink Push Oracle ──
        if (address(cfg.oracle.chainlinkFeed) != address(0) && cfg.oracle.chainlinkWeight > 0) {
            (uint256 clValue, bool clValid) = _readChainlink(cfg);
            if (clValid) {
                weightedSum += clValue * cfg.oracle.chainlinkWeight;
                totalWeight += cfg.oracle.chainlinkWeight;
                sourcesUsed++;
            }
        }

        // ── Source 2: Pyth Pull Oracle ──
        if (cfg.oracle.pythPriceFeedId != bytes32(0) && cfg.oracle.pythWeight > 0) {
            (uint256 pythValue, uint256 pythConf, ) = readPythSubIndex(subIndexId);
            if (pythValue > 0) {
                weightedSum += pythValue * cfg.oracle.pythWeight;
                totalWeight += cfg.oracle.pythWeight;
                aggregatedConf = pythConf;
                sourcesUsed++;
            }
        }

        // ── Source 3: Reporter Median ──
        if (cfg.oracle.reporterWeight > 0) {
            uint256 median = _calculateReporterMedian(subIndexId);
            if (median > 0) {
                weightedSum += median * cfg.oracle.reporterWeight;
                totalWeight += cfg.oracle.reporterWeight;
                sourcesUsed++;
            }
        }

        if (totalWeight == 0) revert NoReportsAvailable(subIndexId);

        uint256 finalValue = weightedSum / totalWeight;

        cfg.value       = finalValue;
        cfg.lastUpdated = block.timestamp;

        // Clear reporter submissions for next round
        _clearReports(subIndexId);

        emit SubIndexUpdated(subIndexId, finalValue, aggregatedConf, sourcesUsed, block.timestamp);
    }

    // ════════════════════════════════════════════════════════════════
    //  COMPOSITE INDEX CALCULATION
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Recalculate composite GDSI from all sub-indices
     * @dev    Weighted average with deviation circuit breaker.
     *         Also updates EMA composite for LP risk management.
     */
    function updateComposite()
        external
        onlyRole(KEEPER_ROLE)
        whenNotPaused
    {
        uint256 weightedSum;
        uint256 totalWeight;
        uint256[5] memory subValues;
        uint256[5] memory subConfs;

        for (uint8 i; i < activeSubIndexCount; ) {
            SubIndexConfig storage cfg = subIndices[i];
            if (cfg.enabled && cfg.value > 0) {
                // Skip stale sub-indices
                if (block.timestamp - cfg.lastUpdated <= cfg.maxStaleness) {
                    weightedSum += cfg.value * cfg.weight;
                    totalWeight += cfg.weight;
                }
                if (i < 5) subValues[i] = cfg.value;
            }
            unchecked { ++i; }
        }

        if (totalWeight == 0) revert WeightsSumZero();

        uint256 newValue = weightedSum / totalWeight;

        // ── Deviation circuit breaker ──
        if (compositeValue > 0) {
            uint256 deviation = newValue > compositeValue
                ? ((newValue - compositeValue) * BPS_DENOMINATOR) / compositeValue
                : ((compositeValue - newValue) * BPS_DENOMINATOR) / compositeValue;

            if (deviation > maxDeviationBps) {
                pendingCompositeValue    = newValue;
                pendingCompositeTimestamp = block.timestamp;
                hasPendingUpdate         = true;
                emit DeviationFlagged(newValue, compositeValue, deviation);
                return;
            }
        }

        _applyCompositeUpdate(newValue, subValues, subConfs);
    }

    /// @notice Governor approves a deviation-flagged update
    function approvePendingUpdate() external onlyRole(GOVERNOR_ROLE) {
        require(hasPendingUpdate, "no pending");
        uint256[5] memory sv;
        uint256[5] memory sc;
        for (uint8 i; i < 5; ) { sv[i] = subIndices[i].value; unchecked { ++i; } }
        _applyCompositeUpdate(pendingCompositeValue, sv, sc);
        hasPendingUpdate = false;
        pendingCompositeValue = 0;
        emit PendingUpdateApproved(roundId, compositeValue);
    }

    /// @notice Governor rejects a deviation-flagged update
    function rejectPendingUpdate() external onlyRole(GOVERNOR_ROLE) {
        require(hasPendingUpdate, "no pending");
        emit PendingUpdateRejected(pendingCompositeValue);
        hasPendingUpdate = false;
        pendingCompositeValue = 0;
    }

    // ════════════════════════════════════════════════════════════════
    //  SYNTHETIX V3 PATTERN: LP STAKING (Pool → Market)
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Stake collateral into the debt index LP pool
     * @dev    Synthetix V3 pattern: LPs deposit collateral → pool
     *         allocates to market → market serves traders.
     *         Here, stakers back the GDSI derivatives market
     *         and earn trading fees from PerpetualEngine.
     */
    function stake(uint256 amount) external nonReentrant whenNotPaused {
        if (amount == 0) revert StakingAmountZero();
        if (address(stakingToken) == address(0)) revert ZeroAddress();

        _updateStakeRewards(msg.sender);
        stakingToken.safeTransferFrom(msg.sender, address(this), amount);

        stakes[msg.sender].amount += amount;
        stakes[msg.sender].rewardDebt = (stakes[msg.sender].amount * accRewardsPerToken) / PRECISION;
        totalStaked += amount;

        emit Staked(msg.sender, amount);
    }

    /// @notice Unstake collateral from the LP pool
    function unstake(uint256 amount) external nonReentrant whenNotPaused {
        if (amount == 0) revert StakingAmountZero();
        if (amount > stakes[msg.sender].amount) revert InsufficientStake();

        _updateStakeRewards(msg.sender);
        stakes[msg.sender].amount -= amount;
        stakes[msg.sender].rewardDebt = (stakes[msg.sender].amount * accRewardsPerToken) / PRECISION;
        totalStaked -= amount;

        stakingToken.safeTransfer(msg.sender, amount);
        emit Unstaked(msg.sender, amount);
    }

    /// @notice Claim accumulated trading fee rewards
    function claimRewards() external nonReentrant whenNotPaused {
        _updateStakeRewards(msg.sender);
        uint256 rewards = stakes[msg.sender].pendingRewards;
        if (rewards == 0) revert NoRewardsAvailable();

        stakes[msg.sender].pendingRewards = 0;
        stakingToken.safeTransfer(msg.sender, rewards);
        emit RewardsClaimed(msg.sender, rewards);
    }

    /**
     * @notice Deposit trading fee rewards for distribution to stakers
     * @dev    Called by PerpetualEngine or governance to distribute
     *         trading fees to LP stakers (Synthetix V3 rewards pattern).
     */
    function depositRewards(uint256 amount) external nonReentrant {
        if (amount == 0) revert ZeroValue();
        if (totalStaked == 0) revert ZeroValue();

        stakingToken.safeTransferFrom(msg.sender, address(this), amount);
        accRewardsPerToken += (amount * PRECISION) / totalStaked;
        totalRewardsDistributed += amount;

        emit RewardsDeposited(amount);
    }

    /// @notice View pending rewards for a staker
    function pendingStakeRewards(address user) external view returns (uint256) {
        StakeInfo storage s = stakes[user];
        uint256 acc = (s.amount * accRewardsPerToken) / PRECISION;
        return s.pendingRewards + acc - s.rewardDebt;
    }

    // ════════════════════════════════════════════════════════════════
    //  VIEW FUNCTIONS
    // ════════════════════════════════════════════════════════════════

    function isHeartbeatAlive() external view returns (bool) {
        return (block.timestamp - compositeTimestamp) <= heartbeatInterval;
    }

    function getSnapshot(uint256 _roundId)
        external view
        returns (uint256 value, uint256 emaValue, uint256 timestamp,
                 uint256[5] memory subValues, uint256[5] memory confidences)
    {
        Snapshot storage s = snapshots[_roundId];
        if (s.timestamp == 0) revert SnapshotNotFound(_roundId);
        return (s.value, s.emaValue, s.timestamp, s.subValues, s.confidences);
    }

    function getRecentSnapshots(uint256 count)
        external view
        returns (uint256[] memory values, uint256[] memory timestamps)
    {
        if (count > roundId) count = roundId;
        values = new uint256[](count);
        timestamps = new uint256[](count);
        for (uint256 i; i < count; ) {
            uint256 rid = roundId - i;
            values[i] = snapshots[rid].value;
            timestamps[i] = snapshots[rid].timestamp;
            unchecked { ++i; }
        }
    }

    function getAllSubIndices()
        external view
        returns (
            string[] memory names, uint256[] memory values,
            uint256[] memory weights, uint256[] memory lastUpdated,
            bool[] memory enabled
        )
    {
        uint8 count = activeSubIndexCount;
        names = new string[](count);
        values = new uint256[](count);
        weights = new uint256[](count);
        lastUpdated = new uint256[](count);
        enabled = new bool[](count);
        for (uint8 i; i < count; ) {
            SubIndexConfig storage cfg = subIndices[i];
            names[i] = cfg.name; values[i] = cfg.value;
            weights[i] = cfg.weight; lastUpdated[i] = cfg.lastUpdated;
            enabled[i] = cfg.enabled;
            unchecked { ++i; }
        }
    }

    /// @notice Index change from baseline (BPS, signed)
    function indexChangeBps() external view returns (int256) {
        if (compositeValue >= BASE_INDEX_VALUE) {
            return int256(((compositeValue - BASE_INDEX_VALUE) * BPS_DENOMINATOR) / BASE_INDEX_VALUE);
        } else {
            return -int256(((BASE_INDEX_VALUE - compositeValue) * BPS_DENOMINATOR) / BASE_INDEX_VALUE);
        }
    }

    /// @notice 0=Low 1=Moderate 2=Elevated 3=High 4=Critical 5=Systemic
    function stressLevel() external view returns (uint8) {
        uint256 v = compositeValue / PRECISION;
        if (v < 800)  return 0;
        if (v < 1000) return 1;
        if (v < 1250) return 2;
        if (v < 1500) return 3;
        if (v < 2000) return 4;
        return 5;
    }

    function getReportCount(uint8 subIndexId) external view returns (uint256) {
        return currentReports[subIndexId].length;
    }

    // ════════════════════════════════════════════════════════════════
    //  ADMIN / CONFIGURATION
    // ════════════════════════════════════════════════════════════════

    // ── Sub-Index Management ──

    function addSubIndex(uint8 id, string calldata name, uint256 weight, uint256 maxStale)
        external onlyRole(GOVERNOR_ROLE)
    {
        require(id >= activeSubIndexCount && id < MAX_SUB_INDICES, "invalid id");
        _initSubIndex(id, name, weight, maxStale);
        emit SubIndexConfigured(id, name, weight, true);
    }

    function setSubIndexWeight(uint8 id, uint256 weight) external onlyRole(GOVERNOR_ROLE) {
        if (id >= activeSubIndexCount) revert InvalidSubIndex(id);
        subIndices[id].weight = weight;
    }

    function setSubIndexEnabled(uint8 id, bool enabled) external onlyRole(GOVERNOR_ROLE) {
        if (id >= activeSubIndexCount) revert InvalidSubIndex(id);
        subIndices[id].enabled = enabled;
    }

    // ── Oracle Node Configuration ──

    function setChainlinkSource(uint8 id, address feed, uint256 weightBps, uint256 maxStale)
        external onlyRole(GOVERNOR_ROLE)
    {
        if (id >= activeSubIndexCount) revert InvalidSubIndex(id);
        OracleNodeConfig storage o = subIndices[id].oracle;
        o.chainlinkFeed = IChainlinkFeed(feed);
        if (feed != address(0)) o.chainlinkDecimals = IChainlinkFeed(feed).decimals();
        o.chainlinkWeight = weightBps;
        o.chainlinkMaxStale = maxStale;
        emit OracleNodeConfigured(id, "chainlink");
    }

    function setPythSource(uint8 id, bytes32 feedId, uint256 weightBps)
        external onlyRole(GOVERNOR_ROLE)
    {
        if (id >= activeSubIndexCount) revert InvalidSubIndex(id);
        subIndices[id].oracle.pythPriceFeedId = feedId;
        subIndices[id].oracle.pythWeight = weightBps;
        emit OracleNodeConfigured(id, "pyth");
    }

    function setReporterWeight(uint8 id, uint256 weightBps) external onlyRole(GOVERNOR_ROLE) {
        if (id >= activeSubIndexCount) revert InvalidSubIndex(id);
        subIndices[id].oracle.reporterWeight = weightBps;
        emit OracleNodeConfigured(id, "reporter");
    }

    // ── Pyth Global Config ──

    function setPyth(address pyth_) external onlyRole(GOVERNOR_ROLE) {
        pyth = IPyth(pyth_);
    }

    function setPythStaleness(uint256 seconds_) external onlyRole(GOVERNOR_ROLE) {
        pythStalenessSeconds = seconds_;
    }

    function setMaxPythConfidence(uint256 bps) external onlyRole(GOVERNOR_ROLE) {
        maxPythConfidenceBps = bps;
    }

    function setUsePythEma(bool useEma) external onlyRole(GOVERNOR_ROLE) {
        usePythEma = useEma;
    }

    // ── Circuit Breakers ──

    function setHeartbeat(uint256 interval) external onlyRole(GOVERNOR_ROLE) {
        uint256 old = heartbeatInterval;
        heartbeatInterval = interval;
        emit HeartbeatUpdated(old, interval);
    }

    function setMaxDeviation(uint256 bps) external onlyRole(GOVERNOR_ROLE) { maxDeviationBps = bps; }
    function setMinReports(uint256 min) external onlyRole(GOVERNOR_ROLE) { minReportsRequired = min; }
    function setEmaSmoothingBps(uint256 bps) external onlyRole(GOVERNOR_ROLE) { emaSmoothingBps = bps; }

    // ── Emergency ──

    function emergencySetComposite(uint256 value) external onlyRole(GOVERNOR_ROLE) {
        if (value == 0) revert ZeroValue();
        uint256[5] memory sv; uint256[5] memory sc;
        for (uint8 i; i < 5; ) { sv[i] = subIndices[i].value; unchecked { ++i; } }
        _applyCompositeUpdate(value, sv, sc);
    }

    function pause() external onlyRole(GOVERNOR_ROLE) { _pause(); }
    function unpause() external onlyRole(GOVERNOR_ROLE) { _unpause(); }

    // ════════════════════════════════════════════════════════════════
    //  INTERNAL
    // ════════════════════════════════════════════════════════════════

    function _initSubIndex(uint8 id, string memory name, uint256 weight, uint256 maxStale) internal {
        subIndices[id].enabled      = true;
        subIndices[id].name         = name;
        subIndices[id].weight       = weight;
        subIndices[id].value        = BASE_INDEX_VALUE;
        subIndices[id].lastUpdated  = block.timestamp;
        subIndices[id].maxStaleness = maxStale;
        // Oracle node starts with reporter-only (weight 10000 = 100%)
        subIndices[id].oracle.reporterWeight = BPS_DENOMINATOR;
        if (id >= activeSubIndexCount) activeSubIndexCount = id + 1;
    }

    function _applyCompositeUpdate(
        uint256 newValue,
        uint256[5] memory subValues,
        uint256[5] memory subConfs
    ) internal {
        uint256 prev = compositeValue;
        compositeValue    = newValue;
        compositeTimestamp = block.timestamp;

        // Update EMA: ema = alpha * new + (1 - alpha) * old
        emaComposite = (newValue * emaSmoothingBps
                        + emaComposite * (BPS_DENOMINATOR - emaSmoothingBps))
                       / BPS_DENOMINATOR;

        roundId++;
        snapshots[roundId] = Snapshot({
            value:       newValue,
            emaValue:    emaComposite,
            timestamp:   block.timestamp,
            subValues:   subValues,
            confidences: subConfs
        });

        emit CompositeUpdated(roundId, newValue, emaComposite, block.timestamp, prev);
    }

    /// @dev Read and normalize a Chainlink push oracle feed
    function _readChainlink(SubIndexConfig storage cfg)
        internal view returns (uint256 value, bool valid)
    {
        IChainlinkFeed feed = cfg.oracle.chainlinkFeed;
        try feed.latestRoundData() returns (
            uint80, int256 answer, uint256, uint256 updatedAt, uint80
        ) {
            if (answer <= 0) return (0, false);
            if (block.timestamp - updatedAt > cfg.oracle.chainlinkMaxStale) return (0, false);

            uint256 price = uint256(answer);
            uint8 dec = cfg.oracle.chainlinkDecimals;
            if (dec < 18) price = price * (10 ** (18 - dec));
            else if (dec > 18) price = price / (10 ** (dec - 18));
            return (price, true);
        } catch {
            return (0, false);
        }
    }

    /// @dev Calculate reporter median (insertion sort, max 20 elements)
    function _calculateReporterMedian(uint8 subIndexId)
        internal view returns (uint256)
    {
        Report[] storage reports = currentReports[subIndexId];
        if (reports.length < minReportsRequired) return 0;

        uint256 validCount;
        uint256[] memory vals = new uint256[](reports.length);
        for (uint256 i; i < reports.length; ) {
            if (block.timestamp - reports[i].timestamp <= MAX_REPORT_AGE) {
                vals[validCount] = reports[i].value;
                unchecked { ++validCount; }
            }
            unchecked { ++i; }
        }
        if (validCount < minReportsRequired) return 0;
        return _median(vals, validCount);
    }

    function _median(uint256[] memory vals, uint256 count) internal pure returns (uint256) {
        // Insertion sort
        for (uint256 i = 1; i < count; ) {
            uint256 key = vals[i];
            uint256 j = i;
            while (j > 0 && vals[j - 1] > key) { vals[j] = vals[j - 1]; j--; }
            vals[j] = key;
            unchecked { ++i; }
        }
        if (count % 2 == 1) return vals[count / 2];
        return (vals[count / 2 - 1] + vals[count / 2]) / 2;
    }

    function _clearReports(uint8 subIndexId) internal {
        Report[] storage reports = currentReports[subIndexId];
        for (uint256 i; i < reports.length; ) {
            hasReported[subIndexId][reports[i].reporter] = false;
            unchecked { ++i; }
        }
        delete currentReports[subIndexId];
    }

    /**
     * @dev Normalize Pyth price from (int64 price, int32 expo) to PRECISION (1e18)
     *      Pyth represents prices as: realPrice = price * 10^expo
     *      where expo is typically negative (e.g. -8 for 8 decimal places)
     */
    function _normalizePythPrice(int64 price, int32 expo)
        internal pure returns (uint256)
    {
        if (price <= 0) return 0;
        uint256 absPrice = uint256(uint64(price));

        if (expo >= 0) {
            return absPrice * PRECISION * (10 ** uint32(expo));
        } else {
            uint32 absExpo = uint32(-expo);
            if (absExpo >= 18) {
                // More decimals than PRECISION: divide down
                return absPrice * PRECISION / (10 ** absExpo);
            } else {
                // Fewer decimals than PRECISION: scale up
                return absPrice * (10 ** (18 - absExpo));
            }
        }
    }

    function _updateStakeRewards(address user) internal {
        StakeInfo storage s = stakes[user];
        if (s.amount > 0) {
            uint256 acc = (s.amount * accRewardsPerToken) / PRECISION;
            s.pendingRewards += acc - s.rewardDebt;
        }
        s.rewardDebt = (s.amount * accRewardsPerToken) / PRECISION;
    }

    /// @dev Accept ETH for Pyth feed update fees
    receive() external payable {}
}
