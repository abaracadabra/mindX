// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
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
 * @title CrossCollateralVault — Unified Multi-Asset Collateral Pool (Audited v2)
 * @author Professor Codephreak — DELTAVERSE Ecosystem
 * @notice Multi-asset RWA collateral pool with oracle pricing, interest accrual,
 *         and liquidation with close factor protection
 * @dev Accepts multiple ERC-20 RWA tokens as collateral, oracle-priced via
 *      Chainlink feeds, enabling unified stablecoin borrowing against a
 *      diversified tokenized real-world asset portfolio.
 *
 * Part of: "The Cryptographic Inheritance of Global Debt"
 * Contract III of III — Composability Premium Primitive
 *
 * Audit Fixes (v2):
 *   [CRITICAL] Replaced unbounded supportedAssets loop with per-user asset tracking
 *   [CRITICAL] Added close factor cap (default 50%) to prevent over-liquidation
 *   [CRITICAL] Separate liquidation threshold from max borrow LTV
 *   [CRITICAL] Added interest accrual on borrowed positions
 *   [CRITICAL] Oracle decimal normalization handles all feed decimal values
 *   [CRITICAL] Stablecoin reserve validation before borrow disbursement
 *   [MEDIUM]   Added Pausable emergency stop
 *   [MEDIUM]   Replaced Ownable with AccessControl (ADMIN, ORACLE_MANAGER)
 *   [MEDIUM]   Added per-asset deposit caps
 *   [MEDIUM]   Added asset enable/disable without removal
 *   [MEDIUM]   Per-asset configurable oracle staleness
 *   [LOW]      Custom errors for gas efficiency
 *   [LOW]      Richer events with USD values
 *   [LOW]      Health factor view function (>1 = healthy)
 */
contract CrossCollateralVault is AccessControl, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ════════════════════════════════════════════════════════════════
    //  ROLES
    // ════════════════════════════════════════════════════════════════

    bytes32 public constant ORACLE_MANAGER_ROLE = keccak256("ORACLE_MANAGER_ROLE");

    // ════════════════════════════════════════════════════════════════
    //  CUSTOM ERRORS
    // ════════════════════════════════════════════════════════════════

    error ZeroAddress();
    error ZeroAmount();
    error AssetAlreadyExists();
    error AssetNotSupported();
    error AssetDisabled();
    error DepositCapExceeded(address token, uint256 requested, uint256 cap);
    error ExceedsDeposit();
    error ExceedsLTV();
    error ExceedsDebt();
    error ExceedsCloseFactorCap(uint256 requested, uint256 maxAllowed);
    error PositionHealthy(uint256 healthFactor);
    error InsufficientReserves(uint256 requested, uint256 available);
    error OracleStale(address feed, uint256 updatedAt, uint256 maxAge);
    error OracleBadPrice(address feed);
    error InterestRateTooHigh(uint256 requested, uint256 max);

    // ════════════════════════════════════════════════════════════════
    //  CONSTANTS
    // ════════════════════════════════════════════════════════════════

    uint256 public constant PRECISION        = 1e18;
    uint256 public constant BPS_DENOMINATOR  = 10_000;
    uint256 public constant SECONDS_PER_YEAR = 365.25 days;
    uint256 public constant MAX_INTEREST_RATE_BPS = 5000; // 50% max annual rate
    uint256 public constant MAX_ASSETS       = 50;        // max supported asset types

    // ════════════════════════════════════════════════════════════════
    //  CORE STATE
    // ════════════════════════════════════════════════════════════════

    IERC20 public immutable stablecoin;         // borrow denomination (USDC, etc.)
    uint8  public immutable stablecoinDecimals;

    // ════════════════════════════════════════════════════════════════
    //  GLOBAL PARAMETERS (governance)
    // ════════════════════════════════════════════════════════════════

    uint256 public maxBorrowLtvBps         = 7500;   // 75% — max LTV for new borrows
    uint256 public liquidationThresholdBps = 8500;   // 85% — LTV where liquidation triggers
    uint256 public liquidationBonusBps     = 500;    // 5%  — bonus to liquidator
    uint256 public closeFactorBps          = 5000;   // 50% — max debt repayable per liquidation
    uint256 public interestRateBps         = 300;    // 3%  — annual interest on borrows
    uint256 public protocolFeeBps          = 1000;   // 10% — protocol share of interest revenue

    uint256 public totalProtocolFees;                // accumulated protocol fees

    // ════════════════════════════════════════════════════════════════
    //  ASSET CONFIGURATION
    // ════════════════════════════════════════════════════════════════

    struct AssetConfig {
        bool           enabled;
        IChainlinkFeed feed;
        uint8          tokenDecimals;
        uint8          feedDecimals;
        uint256        collateralFactorBps;  // haircut (e.g. 9000 = 90%)
        uint256        maxStaleness;         // per-asset oracle staleness
        uint256        depositCap;           // 0 = unlimited
        uint256        totalDeposited;       // global deposits of this asset
    }

    mapping(address => AssetConfig) public assetConfigs;
    address[] public supportedAssets;

    // ════════════════════════════════════════════════════════════════
    //  USER VAULTS
    // ════════════════════════════════════════════════════════════════

    struct UserVault {
        mapping(address => uint256) deposits;   // token => amount
        uint256 borrowed;                        // principal borrowed
        uint256 lastAccrualTimestamp;            // last interest accrual
        uint256 accruedInterest;                 // accumulated unpaid interest
    }

    mapping(address => UserVault) internal vaults;

    /// @dev Per-user tracking of deposited assets (avoids global loop)
    mapping(address => address[]) internal userAssets;
    mapping(address => mapping(address => bool)) internal userHasAsset;

    // ════════════════════════════════════════════════════════════════
    //  EVENTS
    // ════════════════════════════════════════════════════════════════

    event AssetAdded(
        address indexed token, address feed,
        uint256 collateralFactorBps, uint256 depositCap
    );
    event AssetConfigUpdated(address indexed token, bool enabled, uint256 factorBps);
    event Deposited(
        address indexed user, address indexed token,
        uint256 amount, uint256 newTotalUsd
    );
    event Withdrawn(
        address indexed user, address indexed token,
        uint256 amount
    );
    event Borrowed(address indexed user, uint256 amount, uint256 totalDebt);
    event Repaid(address indexed user, uint256 principal, uint256 interest);
    event Liquidated(
        address indexed user, address indexed liquidator,
        address indexed seizeToken, uint256 debtRepaid,
        uint256 tokensSeized, uint256 bonusUsd
    );
    event InterestAccrued(address indexed user, uint256 interest, uint256 totalDebt);
    event ProtocolFeesWithdrawn(address indexed to, uint256 amount);

    // ════════════════════════════════════════════════════════════════
    //  CONSTRUCTOR
    // ════════════════════════════════════════════════════════════════

    /**
     * @param stablecoin_         Stablecoin used for borrowing (e.g. USDC)
     * @param stablecoinDecimals_ Decimal precision of the stablecoin
     */
    constructor(address stablecoin_, uint8 stablecoinDecimals_) {
        if (stablecoin_ == address(0)) revert ZeroAddress();

        stablecoin = IERC20(stablecoin_);
        stablecoinDecimals = stablecoinDecimals_;

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(ORACLE_MANAGER_ROLE, msg.sender);
    }

    // ════════════════════════════════════════════════════════════════
    //  ASSET MANAGEMENT
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Register a new collateral asset type
     * @param token         ERC-20 token address (RWAToken, etc.)
     * @param feed          Chainlink price feed for the asset
     * @param tokenDecimals Token's decimal precision
     * @param factorBps     Collateral factor in BPS (9000 = 90% of value counts)
     * @param maxStaleness  Maximum oracle staleness in seconds
     * @param depositCap    Maximum total deposits of this asset (0 = unlimited)
     */
    function addAsset(
        address token,
        address feed,
        uint8   tokenDecimals,
        uint256 factorBps,
        uint256 maxStaleness,
        uint256 depositCap
    )
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        if (token == address(0) || feed == address(0)) revert ZeroAddress();
        if (assetConfigs[token].feed != IChainlinkFeed(address(0)))
            revert AssetAlreadyExists();
        require(supportedAssets.length < MAX_ASSETS, "max assets");

        uint8 feedDec = IChainlinkFeed(feed).decimals();

        assetConfigs[token] = AssetConfig({
            enabled:             true,
            feed:                IChainlinkFeed(feed),
            tokenDecimals:       tokenDecimals,
            feedDecimals:        feedDec,
            collateralFactorBps: factorBps,
            maxStaleness:        maxStaleness,
            depositCap:          depositCap,
            totalDeposited:      0
        });
        supportedAssets.push(token);

        emit AssetAdded(token, feed, factorBps, depositCap);
    }

    /// @notice Enable or disable an asset and update its collateral factor
    function updateAssetConfig(address token, bool enabled, uint256 factorBps)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        if (assetConfigs[token].feed == IChainlinkFeed(address(0)))
            revert AssetNotSupported();
        assetConfigs[token].enabled = enabled;
        assetConfigs[token].collateralFactorBps = factorBps;
        emit AssetConfigUpdated(token, enabled, factorBps);
    }

    /// @notice Update the oracle feed for an asset
    function updateAssetFeed(address token, address newFeed)
        external
        onlyRole(ORACLE_MANAGER_ROLE)
    {
        if (assetConfigs[token].feed == IChainlinkFeed(address(0)))
            revert AssetNotSupported();
        if (newFeed == address(0)) revert ZeroAddress();
        assetConfigs[token].feed = IChainlinkFeed(newFeed);
        assetConfigs[token].feedDecimals = IChainlinkFeed(newFeed).decimals();
    }

    /// @notice Update per-asset deposit cap
    function updateDepositCap(address token, uint256 newCap)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        if (assetConfigs[token].feed == IChainlinkFeed(address(0)))
            revert AssetNotSupported();
        assetConfigs[token].depositCap = newCap;
    }

    // ════════════════════════════════════════════════════════════════
    //  DEPOSIT / WITHDRAW
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Deposit collateral tokens into the vault
     * @param token  The ERC-20 token to deposit
     * @param amount The amount to deposit
     */
    function deposit(address token, uint256 amount)
        external
        nonReentrant
        whenNotPaused
    {
        if (amount == 0) revert ZeroAmount();
        AssetConfig storage cfg = assetConfigs[token];
        if (cfg.feed == IChainlinkFeed(address(0))) revert AssetNotSupported();
        if (!cfg.enabled) revert AssetDisabled();

        // Check deposit cap
        if (cfg.depositCap != 0 && cfg.totalDeposited + amount > cfg.depositCap)
            revert DepositCapExceeded(token, amount, cfg.depositCap);

        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);

        vaults[msg.sender].deposits[token] += amount;
        cfg.totalDeposited += amount;

        // Track which assets this user has deposited (for efficient valuation)
        if (!userHasAsset[msg.sender][token]) {
            userHasAsset[msg.sender][token] = true;
            userAssets[msg.sender].push(token);
        }

        // Accrue interest on any existing debt
        _accrueInterest(msg.sender);

        uint256 totalUsd = getCollateralValueUsd(msg.sender);
        emit Deposited(msg.sender, token, amount, totalUsd);
    }

    /**
     * @notice Withdraw collateral from the vault
     * @dev    Reverts if withdrawal would make position undercollateralized
     * @param token  The ERC-20 token to withdraw
     * @param amount The amount to withdraw
     */
    function withdraw(address token, uint256 amount)
        external
        nonReentrant
        whenNotPaused
    {
        if (amount == 0) revert ZeroAmount();
        UserVault storage v = vaults[msg.sender];
        if (amount > v.deposits[token]) revert ExceedsDeposit();

        _accrueInterest(msg.sender);

        // Simulate withdrawal and check health
        v.deposits[token] -= amount;
        if (!_isHealthyForBorrow(msg.sender)) {
            v.deposits[token] += amount; // revert state
            revert ExceedsLTV();
        }

        assetConfigs[token].totalDeposited -= amount;
        IERC20(token).safeTransfer(msg.sender, amount);

        emit Withdrawn(msg.sender, token, amount);
    }

    // ════════════════════════════════════════════════════════════════
    //  BORROW / REPAY
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Borrow stablecoin against deposited collateral
     * @param amount The stablecoin amount to borrow
     */
    function borrow(uint256 amount)
        external
        nonReentrant
        whenNotPaused
    {
        if (amount == 0) revert ZeroAmount();

        _accrueInterest(msg.sender);

        // ── AUDIT FIX: Check stablecoin reserves ──
        uint256 available = stablecoin.balanceOf(address(this)) - totalProtocolFees;
        if (amount > available)
            revert InsufficientReserves(amount, available);

        vaults[msg.sender].borrowed += amount;

        // Check borrow LTV (not liquidation threshold)
        if (!_isHealthyForBorrow(msg.sender)) {
            vaults[msg.sender].borrowed -= amount;
            revert ExceedsLTV();
        }

        stablecoin.safeTransfer(msg.sender, amount);

        uint256 totalDebt = _getTotalDebt(msg.sender);
        emit Borrowed(msg.sender, amount, totalDebt);
    }

    /**
     * @notice Repay borrowed stablecoin
     * @dev    Payment applies to accrued interest first, then principal.
     *         Protocol fee is extracted from the interest portion.
     * @param amount The stablecoin amount to repay
     */
    function repay(uint256 amount)
        external
        nonReentrant
        whenNotPaused
    {
        if (amount == 0) revert ZeroAmount();

        _accrueInterest(msg.sender);

        UserVault storage v = vaults[msg.sender];
        uint256 totalDebt = v.borrowed + v.accruedInterest;
        if (amount > totalDebt) amount = totalDebt; // cap at total debt

        stablecoin.safeTransferFrom(msg.sender, address(this), amount);

        // Apply to interest first, then principal
        uint256 interestPaid;
        uint256 principalPaid;

        if (amount <= v.accruedInterest) {
            interestPaid = amount;
            v.accruedInterest -= amount;
        } else {
            interestPaid = v.accruedInterest;
            principalPaid = amount - interestPaid;
            v.accruedInterest = 0;
            v.borrowed -= principalPaid;
        }

        // Protocol fee on interest paid
        if (interestPaid > 0) {
            uint256 protocolCut = (interestPaid * protocolFeeBps) / BPS_DENOMINATOR;
            totalProtocolFees += protocolCut;
        }

        emit Repaid(msg.sender, principalPaid, interestPaid);
    }

    // ════════════════════════════════════════════════════════════════
    //  LIQUIDATION
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Liquidate an undercollateralized position
     * @dev    Liquidator repays a portion of the user's debt and receives
     *         the equivalent collateral value plus a liquidation bonus.
     *
     *         Close factor cap prevents full liquidation in a single tx
     *         (default 50% of total debt per liquidation call).
     *
     * @param user        The address of the user to liquidate
     * @param seizeToken  The collateral token to seize
     * @param repayAmount The stablecoin amount to repay on user's behalf
     */
    function liquidate(
        address user,
        address seizeToken,
        uint256 repayAmount
    )
        external
        nonReentrant
        whenNotPaused
    {
        if (repayAmount == 0) revert ZeroAmount();

        _accrueInterest(user);

        // Check position is liquidatable (using liquidation threshold, NOT borrow LTV)
        uint256 hf = healthFactor(user);
        if (hf >= PRECISION)
            revert PositionHealthy(hf);

        uint256 totalDebt = _getTotalDebt(user);

        // ── AUDIT FIX: Close factor cap ──
        uint256 maxRepay = (totalDebt * closeFactorBps) / BPS_DENOMINATOR;
        if (repayAmount > maxRepay)
            revert ExceedsCloseFactorCap(repayAmount, maxRepay);
        if (repayAmount > totalDebt) repayAmount = totalDebt;

        // Pull stablecoin from liquidator
        stablecoin.safeTransferFrom(msg.sender, address(this), repayAmount);

        // Reduce user's debt (interest first, then principal)
        UserVault storage v = vaults[user];
        if (repayAmount <= v.accruedInterest) {
            uint256 protocolCut = (repayAmount * protocolFeeBps) / BPS_DENOMINATOR;
            totalProtocolFees += protocolCut;
            v.accruedInterest -= repayAmount;
        } else {
            uint256 interestPortion = v.accruedInterest;
            if (interestPortion > 0) {
                uint256 protocolCut = (interestPortion * protocolFeeBps) / BPS_DENOMINATOR;
                totalProtocolFees += protocolCut;
            }
            v.accruedInterest = 0;
            v.borrowed -= (repayAmount - interestPortion);
        }

        // ── AUDIT FIX: Correct bonus arithmetic with proper parentheses ──
        uint256 seizeUsd = (repayAmount * (BPS_DENOMINATOR + liquidationBonusBps))
                           / BPS_DENOMINATOR;
        uint256 bonusUsd = seizeUsd - repayAmount;

        // Convert USD value to token amount
        AssetConfig storage cfg = assetConfigs[seizeToken];
        if (cfg.feed == IChainlinkFeed(address(0))) revert AssetNotSupported();

        uint256 tokenPrice = _getPrice(seizeToken);
        uint256 seizeAmt = (seizeUsd * (10 ** cfg.tokenDecimals)) / tokenPrice;

        // Cap at user's actual deposit of this token
        uint256 userDeposit = v.deposits[seizeToken];
        if (seizeAmt > userDeposit) seizeAmt = userDeposit;

        v.deposits[seizeToken] -= seizeAmt;
        cfg.totalDeposited -= seizeAmt;

        IERC20(seizeToken).safeTransfer(msg.sender, seizeAmt);

        emit Liquidated(
            user, msg.sender, seizeToken,
            repayAmount, seizeAmt, bonusUsd
        );
    }

    // ════════════════════════════════════════════════════════════════
    //  INTEREST ACCRUAL
    // ════════════════════════════════════════════════════════════════

    /**
     * @dev Accrue simple interest on a user's borrowed position
     *      Interest = principal * rate * elapsed / SECONDS_PER_YEAR
     */
    function _accrueInterest(address user) internal {
        UserVault storage v = vaults[user];
        if (v.borrowed == 0 && v.accruedInterest == 0) {
            v.lastAccrualTimestamp = block.timestamp;
            return;
        }
        if (v.lastAccrualTimestamp == 0) {
            v.lastAccrualTimestamp = block.timestamp;
            return;
        }

        uint256 elapsed = block.timestamp - v.lastAccrualTimestamp;
        if (elapsed == 0) return;

        // Simple interest on outstanding principal
        uint256 interest = (v.borrowed * interestRateBps * elapsed)
                           / (BPS_DENOMINATOR * SECONDS_PER_YEAR);

        if (interest > 0) {
            v.accruedInterest += interest;
            emit InterestAccrued(user, interest, v.borrowed + v.accruedInterest);
        }

        v.lastAccrualTimestamp = block.timestamp;
    }

    // ════════════════════════════════════════════════════════════════
    //  VIEW FUNCTIONS
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Get total collateral value in USD (18 decimal precision)
     * @dev    Only iterates over assets the user has actually deposited,
     *         not the entire supportedAssets array (audit fix for gas).
     */
    function getCollateralValueUsd(address user)
        public
        view
        returns (uint256 total)
    {
        address[] storage assets = userAssets[user];
        for (uint256 i; i < assets.length; ) {
            address token = assets[i];
            uint256 bal = vaults[user].deposits[token];
            if (bal > 0) {
                AssetConfig storage cfg = assetConfigs[token];
                uint256 price = _getPrice(token);
                uint256 usdVal = (bal * price) / (10 ** cfg.tokenDecimals);
                uint256 adjusted = (usdVal * cfg.collateralFactorBps) / BPS_DENOMINATOR;
                total += adjusted;
            }
            unchecked { ++i; }
        }
    }

    /**
     * @notice Health factor: collateral * liquidationThreshold / totalDebt
     * @return hf Scaled to PRECISION (1e18). >= 1e18 means healthy.
     */
    function healthFactor(address user) public view returns (uint256 hf) {
        uint256 totalDebt = _getTotalDebt(user);
        if (totalDebt == 0) return type(uint256).max;

        uint256 colVal = getCollateralValueUsd(user);
        uint256 liquidationLimit = (colVal * liquidationThresholdBps) / BPS_DENOMINATOR;

        hf = (liquidationLimit * PRECISION) / totalDebt;
    }

    /// @notice Remaining borrow capacity in stablecoin units
    function getBorrowCapacity(address user) external view returns (uint256) {
        uint256 colVal = getCollateralValueUsd(user);
        uint256 maxBorrow = (colVal * maxBorrowLtvBps) / BPS_DENOMINATOR;
        uint256 totalDebt = _getTotalDebt(user);
        if (maxBorrow <= totalDebt) return 0;
        return maxBorrow - totalDebt;
    }

    /// @notice Get a user's deposit of a specific token
    function getUserDeposit(address user, address token)
        external view returns (uint256)
    {
        return vaults[user].deposits[token];
    }

    /// @notice Get a user's total debt (principal + accrued interest)
    function getUserTotalDebt(address user) external view returns (uint256) {
        return _getTotalDebt(user);
    }

    /// @notice Get principal and accrued interest separately
    function getUserDebtBreakdown(address user)
        external
        view
        returns (uint256 principal, uint256 interest)
    {
        UserVault storage v = vaults[user];
        principal = v.borrowed;
        interest = v.accruedInterest;
        if (v.borrowed > 0 && v.lastAccrualTimestamp > 0) {
            uint256 elapsed = block.timestamp - v.lastAccrualTimestamp;
            interest += (v.borrowed * interestRateBps * elapsed)
                        / (BPS_DENOMINATOR * SECONDS_PER_YEAR);
        }
    }

    /// @notice Get all tokens a user has deposited
    function getUserAssets(address user) external view returns (address[] memory) {
        return userAssets[user];
    }

    /// @notice Check if a user's position is liquidatable
    function isLiquidatable(address user) external view returns (bool) {
        return healthFactor(user) < PRECISION;
    }

    /// @notice Total number of supported asset types
    function supportedAssetCount() external view returns (uint256) {
        return supportedAssets.length;
    }

    // ════════════════════════════════════════════════════════════════
    //  ADMIN / CONFIGURATION
    // ════════════════════════════════════════════════════════════════

    function setMaxBorrowLtv(uint256 bps) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(bps < liquidationThresholdBps, "LTV >= liq threshold");
        maxBorrowLtvBps = bps;
    }

    function setLiquidationThreshold(uint256 bps) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(bps > maxBorrowLtvBps, "threshold <= LTV");
        require(bps <= BPS_DENOMINATOR, "threshold > 100%");
        liquidationThresholdBps = bps;
    }

    function setLiquidationBonus(uint256 bps) external onlyRole(DEFAULT_ADMIN_ROLE) {
        liquidationBonusBps = bps;
    }

    function setCloseFactor(uint256 bps) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(bps <= BPS_DENOMINATOR, "> 100%");
        closeFactorBps = bps;
    }

    function setInterestRate(uint256 bps) external onlyRole(DEFAULT_ADMIN_ROLE) {
        if (bps > MAX_INTEREST_RATE_BPS) revert InterestRateTooHigh(bps, MAX_INTEREST_RATE_BPS);
        interestRateBps = bps;
    }

    function setProtocolFee(uint256 bps) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(bps <= BPS_DENOMINATOR, "> 100%");
        protocolFeeBps = bps;
    }

    /// @notice Withdraw accumulated protocol fees
    function withdrawProtocolFees(address to, uint256 amount)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        if (to == address(0)) revert ZeroAddress();
        require(amount <= totalProtocolFees, "exceeds fees");
        totalProtocolFees -= amount;
        stablecoin.safeTransfer(to, amount);
        emit ProtocolFeesWithdrawn(to, amount);
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) { _pause(); }
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) { _unpause(); }

    // ════════════════════════════════════════════════════════════════
    //  INTERNAL
    // ════════════════════════════════════════════════════════════════

    /// @dev Total debt including accrued + pending interest
    function _getTotalDebt(address user) internal view returns (uint256) {
        UserVault storage v = vaults[user];
        uint256 debt = v.borrowed + v.accruedInterest;
        if (v.borrowed > 0 && v.lastAccrualTimestamp > 0) {
            uint256 elapsed = block.timestamp - v.lastAccrualTimestamp;
            debt += (v.borrowed * interestRateBps * elapsed)
                    / (BPS_DENOMINATOR * SECONDS_PER_YEAR);
        }
        return debt;
    }

    /// @dev Check if user's position is within borrow LTV
    function _isHealthyForBorrow(address user) internal view returns (bool) {
        uint256 totalDebt = _getTotalDebt(user);
        if (totalDebt == 0) return true;
        uint256 colVal = getCollateralValueUsd(user);
        uint256 maxBorrow = (colVal * maxBorrowLtvBps) / BPS_DENOMINATOR;
        return totalDebt <= maxBorrow;
    }

    /**
     * @dev Fetch, validate, and normalize oracle price to 18 decimals
     *      Handles all Chainlink feed decimal configurations safely.
     */
    function _getPrice(address token) internal view returns (uint256) {
        AssetConfig storage cfg = assetConfigs[token];
        IChainlinkFeed feed = cfg.feed;

        (, int256 answer, , uint256 updatedAt, ) = feed.latestRoundData();

        if (answer <= 0) revert OracleBadPrice(address(feed));
        if (block.timestamp - updatedAt > cfg.maxStaleness)
            revert OracleStale(address(feed), updatedAt, cfg.maxStaleness);

        // ── AUDIT FIX: Safe normalization for any decimal count ──
        uint256 price = uint256(answer);
        uint8 feedDec = cfg.feedDecimals;

        if (feedDec < 18) {
            price = price * (10 ** (18 - feedDec));
        } else if (feedDec > 18) {
            price = price / (10 ** (feedDec - 18));
        }

        return price;
    }
}
