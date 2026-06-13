// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

// ════════════════════════════════════════════════════════════════════
//  MINIMAL INTERFACES TO THE DELTAVERSE STACK
// ════════════════════════════════════════════════════════════════════

interface IDeltaVerseDebtOracle {
    function latestPrice() external view returns (uint256 price, uint256 updatedAt);
    function latestEmaPrice() external view returns (uint256 price, uint256 updatedAt);
    function stressLevel() external view returns (uint8);
    function indexChangeBps() external view returns (int256);
    function depositRewards(uint256 amount) external;
    function roundId() external view returns (uint256);
    function isHeartbeatAlive() external view returns (bool);
}

interface ICrossCollateralVault {
    function deposit(address token, uint256 amount) external;
    function withdraw(address token, uint256 amount) external;
    function borrow(uint256 amount) external;
    function repay(uint256 amount) external;
    function getCollateralValueUsd(address user) external view returns (uint256);
    function getUserTotalDebt(address user) external view returns (uint256);
    function healthFactor(address user) external view returns (uint256);
    function getBorrowCapacity(address user) external view returns (uint256);
}

interface IPerpetualEngine {
    function openPosition(bool isLong, uint256 collateralAmt, uint256 leverage) external;
    function closePosition() external;
    function reducePosition(uint256 closeSize) external;
    function addCollateral(uint256 amount) external;
    function liquidate(address trader) external;
    function getEquity(address trader) external view returns (int256);
    function isLiquidatable(address trader) external view returns (bool);
    function getUnrealizedPnL(address trader) external view returns (int256);
}

interface IRWAToken {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function isWhitelisted(address account) external view returns (bool);
}

/**
 * @title DebtInheritanceProtocol — Capstone Orchestrator (Part III Proof)
 * @author Professor Codephreak — DELTAVERSE Ecosystem
 *
 * ═══════════════════════════════════════════════════════════════════
 *  THE PROOF OF THESIS
 * ═══════════════════════════════════════════════════════════════════
 *
 * Part I (global_debt_thesis.docx) established the structural
 * unsustainability of the $346T global debt complex and identified
 * four channels of inverse positioning, naming paradigmatic
 * displacement as the most durable.
 *
 * Part II (cryptographic_inheritance.docx) specified that displacement
 * mechanism: RWA tokenization + on-chain derivatives + unified
 * collateralization, and delivered three production primitives:
 *   • RWAToken.sol          — compliance-gated tokenization of debt
 *   • PerpetualEngine.sol   — 24/7 derivatives with insurance fund
 *   • CrossCollateralVault  — multi-asset borrowing with interest
 *
 * Part II+ added the measurement layer:
 *   • DeltaVerseDebtOracle  — composite GDSI with Pyth + Synthetix
 *                              V3 Oracle Manager patterns, LP pool
 *
 * This contract — DebtInheritanceProtocol — is the Synthetix V3
 * "Market Module" that composes all four primitives into a single
 * executable system. It is the capstone proof:
 *
 *   "The debt system can be shorted using collateral derived
 *    from the debt system itself, with the shorting instrument
 *    backed by the measurement oracle that tracks the very
 *    phenomenon being shorted."
 *
 * This is recursive self-demonstration. A user can:
 *
 *   1. Deposit tokenized sovereign debt (RWAToken) into the vault
 *   2. Borrow stablecoin against it (CrossCollateralVault)
 *   3. Use that stablecoin to open a leveraged LONG position on
 *      the Global Debt Stress Index via PerpetualEngine
 *   4. Profit when debt stress rises — which is caused by the
 *      same structural dynamics that debase the collateral they
 *      started with
 *
 * The collateral and the position are counterweights. The system
 * inherits the debt function and enables inversion of it in the
 * same transaction. This is the "cryptographic inheritance of
 * global debt" made literal.
 *
 * ═══════════════════════════════════════════════════════════════════
 *  SYNTHETIX V3 ARCHITECTURE MAPPING
 * ═══════════════════════════════════════════════════════════════════
 *
 *   Synthetix V3 Concept      │ DELTAVERSE Implementation
 *   ──────────────────────────┼────────────────────────────────
 *   Collateral Types          │ RWAToken + any whitelisted ERC-20
 *   Vault                     │ CrossCollateralVault positions
 *   Pool                      │ DeltaVerseDebtOracle LP staking pool
 *   Oracle Manager            │ DeltaVerseDebtOracle (Chainlink +
 *                             │   Pyth + Reporter median)
 *   Market Module             │ DebtInheritanceProtocol (this)
 *   Perps Market              │ PerpetualEngine long/short on GDSI
 *   Synthetic Asset           │ sGDSI (this contract)
 *   Rewards Distributor       │ Fee routing to oracle LP pool
 *   Liquidator                │ PerpetualEngine + Vault liquidators
 *
 * ═══════════════════════════════════════════════════════════════════
 *  sGDSI — SYNTHETIC GLOBAL DEBT STRESS INDEX TOKEN
 * ═══════════════════════════════════════════════════════════════════
 *
 * This contract IS an ERC-20: sGDSI. Users mint sGDSI by depositing
 * stablecoin at the current GDSI oracle price. One sGDSI represents
 * one unit of debt stress exposure. Burning sGDSI redeems collateral
 * at the current price.
 *
 *   Mint:    collateral_in → sGDSI_out = collateral_in × (BASE / price)
 *   Burn:    sGDSI_in      → collateral_out = sGDSI_in × (price / BASE)
 *
 * If the GDSI rises from 1000 to 1500 (50% debt stress increase):
 *   • Holders of sGDSI see their collateral claim rise proportionally
 *   • Mint was at price=1000, burn at price=1500 → 50% gain
 *
 * This is the passive, non-leveraged expression of the thesis.
 * For leveraged expression, users go through PerpetualEngine.
 * sGDSI is to Perp what sBTC is to sBTC-PERP in Synthetix V3.
 *
 * ═══════════════════════════════════════════════════════════════════
 *  THE FEE ROUTING LOOP (Value Closure)
 * ═══════════════════════════════════════════════════════════════════
 *
 * Protocol fees collected on mint/burn/leverage are routed to the
 * oracle's LP staking pool via depositRewards(). This creates a
 * closed economic loop:
 *
 *   Traders pay fees → Oracle LP stakers earn rewards →
 *   Stakers provide collateral that backs the oracle →
 *   Oracle provides price data that enables trading →
 *   Traders pay fees.
 *
 * The people who provide the measurement infrastructure (collateral
 * backing the oracle's credibility) are paid by the people who trade
 * against the measurement. This is the Synthetix V3 delta-neutral
 * LP fee model applied to debt stress measurement.
 */
contract DebtInheritanceProtocol is
    ERC20,              // sGDSI synthetic token
    AccessControl,
    ReentrancyGuard,
    Pausable
{
    using SafeERC20 for IERC20;

    // ════════════════════════════════════════════════════════════════
    //  ROLES
    // ════════════════════════════════════════════════════════════════

    bytes32 public constant GOVERNOR_ROLE  = keccak256("GOVERNOR_ROLE");
    bytes32 public constant KEEPER_ROLE    = keccak256("KEEPER_ROLE");

    // ════════════════════════════════════════════════════════════════
    //  CUSTOM ERRORS
    // ════════════════════════════════════════════════════════════════

    error ZeroAmount();
    error ZeroAddress();
    error OracleStale();
    error InsufficientCollateral();
    error MintCapExceeded(uint256 requested, uint256 cap);
    error SlippageExceeded(uint256 expected, uint256 actual);
    error InvalidLeverage();
    error ThesisNotActivated();
    error FeeTooHigh(uint256 bps);

    // ════════════════════════════════════════════════════════════════
    //  CONSTANTS
    // ════════════════════════════════════════════════════════════════

    uint256 public constant PRECISION        = 1e18;
    uint256 public constant BASE_INDEX       = 1000 * PRECISION;
    uint256 public constant BPS_DENOMINATOR  = 10_000;
    uint256 public constant MAX_MINT_FEE_BPS = 500;  // 5% hard cap
    uint256 public constant MAX_LEVERAGE     = 20;

    // ════════════════════════════════════════════════════════════════
    //  IMMUTABLE STACK REFERENCES
    // ════════════════════════════════════════════════════════════════

    IDeltaVerseDebtOracle public immutable oracle;
    ICrossCollateralVault public immutable vault;
    IPerpetualEngine      public immutable perpEngine;
    IERC20                public immutable stablecoin;

    // ════════════════════════════════════════════════════════════════
    //  PROTOCOL CONFIGURATION
    // ════════════════════════════════════════════════════════════════

    uint256 public mintFeeBps      = 30;    // 0.30% fee on sGDSI mint
    uint256 public burnFeeBps      = 30;    // 0.30% fee on sGDSI burn
    uint256 public maxSGdsiSupply  = 100_000_000 * PRECISION;  // 100M sGDSI cap
    uint256 public maxOracleAge    = 1 hours;

    /// @notice Accumulated protocol fees (stablecoin) awaiting distribution
    uint256 public pendingFees;

    /// @notice Whether to use EMA-smoothed price for mint/burn (lower volatility)
    bool public useEmaPrice = false;

    // ════════════════════════════════════════════════════════════════
    //  THESIS POSITION TRACKING
    // ════════════════════════════════════════════════════════════════

    /**
     * @dev A "thesis position" is a user who has executed the full
     *      recursive inheritance flow: RWA → vault → borrow → perp.
     *      We track this to provide atomic unwinding and reporting.
     */
    struct ThesisPosition {
        address rwaCollateral;     // RWAToken deposited
        uint256 rwaAmount;
        uint256 borrowedStable;    // amount borrowed from vault
        uint256 perpCollateral;    // amount committed to perp
        uint256 openedAt;
        uint256 openRoundId;       // oracle round at open
        uint256 openIndexValue;    // GDSI value at open
        bool    isLong;
        uint256 leverage;
        bool    active;
    }

    mapping(address => ThesisPosition) public thesisPositions;

    // ════════════════════════════════════════════════════════════════
    //  EVENTS
    // ════════════════════════════════════════════════════════════════

    event SGdsiMinted(
        address indexed user, uint256 stableIn,
        uint256 sGdsiOut, uint256 price, uint256 fee
    );
    event SGdsiBurned(
        address indexed user, uint256 sGdsiIn,
        uint256 stableOut, uint256 price, uint256 fee
    );
    event ThesisExpressed(
        address indexed user, address rwaCollateral,
        uint256 rwaAmount, uint256 borrowed, uint256 leverage,
        bool isLong, uint256 openIndexValue
    );
    event ThesisClosed(
        address indexed user, uint256 openIndex, uint256 closeIndex,
        int256 perpPnl, uint256 stableReturned
    );
    event FeesRoutedToOracleLPs(uint256 amount);
    event ConfigUpdated(string param, uint256 value);

    // ════════════════════════════════════════════════════════════════
    //  CONSTRUCTOR
    // ════════════════════════════════════════════════════════════════

    /**
     * @param oracle_      DeltaVerseDebtOracle contract
     * @param vault_       CrossCollateralVault contract
     * @param perpEngine_  PerpetualEngine contract
     * @param stablecoin_  Stablecoin used by vault + perp (e.g. USDC)
     * @param admin_       Admin / governor address
     */
    constructor(
        address oracle_,
        address vault_,
        address perpEngine_,
        address stablecoin_,
        address admin_
    )
        ERC20("Synthetic Global Debt Stress Index", "sGDSI")
    {
        if (oracle_     == address(0)) revert ZeroAddress();
        if (vault_      == address(0)) revert ZeroAddress();
        if (perpEngine_ == address(0)) revert ZeroAddress();
        if (stablecoin_ == address(0)) revert ZeroAddress();
        if (admin_      == address(0)) revert ZeroAddress();

        oracle     = IDeltaVerseDebtOracle(oracle_);
        vault      = ICrossCollateralVault(vault_);
        perpEngine = IPerpetualEngine(perpEngine_);
        stablecoin = IERC20(stablecoin_);

        _grantRole(DEFAULT_ADMIN_ROLE, admin_);
        _grantRole(GOVERNOR_ROLE,      admin_);
        _grantRole(KEEPER_ROLE,        admin_);
    }

    // ════════════════════════════════════════════════════════════════
    //  sGDSI — SPOT SYNTHETIC ASSET (MINT/BURN)
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Mint sGDSI synthetic debt index tokens
     * @dev    Deposit stablecoin, receive sGDSI at current GDSI price.
     *
     *         sGDSI amount = (stableIn - fee) * BASE_INDEX / gdsiPrice
     *
     *         When GDSI rises, each sGDSI token is worth more stablecoin
     *         on burn. This is the passive, unlevered expression of
     *         the debt thesis — holding sGDSI = being long debt stress.
     *
     * @param stableAmount   Amount of stablecoin to deposit
     * @param minSGdsiOut    Minimum sGDSI to receive (slippage protection)
     */
    function mintSGdsi(uint256 stableAmount, uint256 minSGdsiOut)
        external
        nonReentrant
        whenNotPaused
        returns (uint256 sGdsiOut)
    {
        if (stableAmount == 0) revert ZeroAmount();

        uint256 price = _getValidPrice();
        uint256 fee = (stableAmount * mintFeeBps) / BPS_DENOMINATOR;
        uint256 netStable = stableAmount - fee;

        // sGDSI_out = netStable * BASE_INDEX / gdsiPrice
        // (when GDSI > BASE, you get fewer sGDSI per stablecoin)
        sGdsiOut = (netStable * BASE_INDEX) / price;

        if (sGdsiOut < minSGdsiOut)
            revert SlippageExceeded(minSGdsiOut, sGdsiOut);
        if (totalSupply() + sGdsiOut > maxSGdsiSupply)
            revert MintCapExceeded(totalSupply() + sGdsiOut, maxSGdsiSupply);

        // Pull collateral
        stablecoin.safeTransferFrom(msg.sender, address(this), stableAmount);
        pendingFees += fee;

        _mint(msg.sender, sGdsiOut);
        emit SGdsiMinted(msg.sender, stableAmount, sGdsiOut, price, fee);
    }

    /**
     * @notice Burn sGDSI to redeem stablecoin at current oracle price
     * @dev    stableOut = sGdsiIn * gdsiPrice / BASE_INDEX - fee
     *
     *         If GDSI rose since mint, burn returns more stablecoin
     *         than was deposited at mint. This is the profit mechanism.
     *
     * @param sGdsiAmount     Amount of sGDSI to burn
     * @param minStableOut    Minimum stablecoin to receive (slippage)
     */
    function burnSGdsi(uint256 sGdsiAmount, uint256 minStableOut)
        external
        nonReentrant
        whenNotPaused
        returns (uint256 stableOut)
    {
        if (sGdsiAmount == 0) revert ZeroAmount();

        uint256 price = _getValidPrice();

        // stable_gross = sGdsiIn * price / BASE_INDEX
        uint256 gross = (sGdsiAmount * price) / BASE_INDEX;
        uint256 fee = (gross * burnFeeBps) / BPS_DENOMINATOR;
        stableOut = gross - fee;

        if (stableOut < minStableOut)
            revert SlippageExceeded(minStableOut, stableOut);

        // Check contract has sufficient stable balance
        uint256 available = stablecoin.balanceOf(address(this)) - pendingFees;
        if (stableOut > available) revert InsufficientCollateral();

        _burn(msg.sender, sGdsiAmount);
        pendingFees += fee;
        stablecoin.safeTransfer(msg.sender, stableOut);

        emit SGdsiBurned(msg.sender, sGdsiAmount, stableOut, price, fee);
    }

    // ════════════════════════════════════════════════════════════════
    //  EXPRESS THE THESIS — LEVERAGED RECURSIVE INHERITANCE
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Express the full debt inheritance thesis atomically
     * @dev    This function IS the proof of thesis. In a single
     *         transaction, a user:
     *
     *         1. Deposits tokenized sovereign debt (RWAToken) into vault
     *         2. Borrows stablecoin against it at configured LTV
     *         3. Opens a leveraged LONG position on the GDSI via perp
     *
     *         The collateral (tokenized debt) and the position (long
     *         debt stress) are mirror images. As the debt system
     *         deteriorates:
     *            - GDSI rises → perp position profits (leverage × delta)
     *            - Debt collateral value may decline in real terms
     *         The perp profit offsets and exceeds the collateral erosion.
     *
     *         This is the cryptographic inheritance made literal: the
     *         debt system is used as fuel to short itself.
     *
     *         For shorting GDSI (betting stress decreases), pass isLong=false.
     *
     * @param rwaToken     RWAToken (or any whitelisted vault asset) to use
     * @param rwaAmount    Amount of RWA to deposit as collateral
     * @param borrowAmount Stablecoin to borrow (must respect vault LTV)
     * @param leverage     Perpetual leverage (1-20×)
     * @param isLong       True = long GDSI (bet stress rises = thesis),
     *                     False = short GDSI (bet stress stabilizes)
     */
    function expressThesis(
        address rwaToken,
        uint256 rwaAmount,
        uint256 borrowAmount,
        uint256 leverage,
        bool    isLong
    )
        external
        nonReentrant
        whenNotPaused
    {
        if (rwaAmount == 0 || borrowAmount == 0) revert ZeroAmount();
        if (leverage == 0 || leverage > MAX_LEVERAGE) revert InvalidLeverage();
        if (thesisPositions[msg.sender].active) revert ThesisNotActivated();

        // ── Step 1: Pull RWA collateral from user ──
        IERC20(rwaToken).safeTransferFrom(msg.sender, address(this), rwaAmount);

        // ── Step 2: Deposit into CrossCollateralVault ──
        IERC20(rwaToken).forceApprove(address(vault), rwaAmount);
        vault.deposit(rwaToken, rwaAmount);

        // ── Step 3: Borrow stablecoin against the collateral ──
        vault.borrow(borrowAmount);

        // ── Step 4: Route borrowed stable into PerpetualEngine ──
        //          Open leveraged position on GDSI oracle
        stablecoin.forceApprove(address(perpEngine), borrowAmount);
        perpEngine.openPosition(isLong, borrowAmount, leverage);

        // ── Step 5: Record the thesis position ──
        (uint256 indexValue, ) = oracle.latestPrice();
        uint256 roundId = oracle.roundId();

        thesisPositions[msg.sender] = ThesisPosition({
            rwaCollateral:  rwaToken,
            rwaAmount:      rwaAmount,
            borrowedStable: borrowAmount,
            perpCollateral: borrowAmount,
            openedAt:       block.timestamp,
            openRoundId:    roundId,
            openIndexValue: indexValue,
            isLong:         isLong,
            leverage:       leverage,
            active:         true
        });

        emit ThesisExpressed(
            msg.sender, rwaToken, rwaAmount,
            borrowAmount, leverage, isLong, indexValue
        );
    }

    /**
     * @notice Close a thesis position and unwind the full stack
     * @dev    Reverses expressThesis() atomically:
     *         1. Close perp position → stablecoin PnL to this contract
     *         2. Repay vault debt
     *         3. Withdraw RWA collateral back to user
     *         4. Return residual stablecoin profit to user
     */
    function closeThesis()
        external
        nonReentrant
        whenNotPaused
        returns (int256 perpPnl, uint256 stableReturned)
    {
        ThesisPosition memory pos = thesisPositions[msg.sender];
        if (!pos.active) revert ThesisNotActivated();

        // Snapshot balances to measure what came out of perp close
        uint256 balBefore = stablecoin.balanceOf(address(this));

        // ── Step 1: Close perp position ──
        //          (PerpetualEngine sends stable to this contract)
        perpEngine.closePosition();

        uint256 balAfterPerp = stablecoin.balanceOf(address(this));
        uint256 perpReturn = balAfterPerp - balBefore;

        // Calculate PnL vs original perp collateral
        perpPnl = int256(perpReturn) - int256(pos.perpCollateral);

        // ── Step 2: Repay vault debt ──
        uint256 totalDebt = vault.getUserTotalDebt(address(this));
        uint256 repayAmount = perpReturn >= totalDebt ? totalDebt : perpReturn;

        stablecoin.forceApprove(address(vault), repayAmount);
        vault.repay(repayAmount);

        // ── Step 3: Withdraw RWA collateral ──
        //          (only succeeds if vault is now fully repaid OR
        //           remaining debt is still safely collateralized)
        uint256 remainingDebt = vault.getUserTotalDebt(address(this));
        if (remainingDebt == 0) {
            vault.withdraw(pos.rwaCollateral, pos.rwaAmount);
            IERC20(pos.rwaCollateral).safeTransfer(msg.sender, pos.rwaAmount);
        }
        // If remainingDebt > 0, the user is underwater on the thesis —
        // their RWA stays in the vault as partial collateral

        // ── Step 4: Return surplus stablecoin to user ──
        uint256 surplus = stablecoin.balanceOf(address(this)) - balBefore;
        if (surplus > 0) {
            stablecoin.safeTransfer(msg.sender, surplus);
            stableReturned = surplus;
        }

        (uint256 closeIndex, ) = oracle.latestPrice();
        delete thesisPositions[msg.sender];

        emit ThesisClosed(
            msg.sender, pos.openIndexValue, closeIndex,
            perpPnl, stableReturned
        );
    }

    // ════════════════════════════════════════════════════════════════
    //  FEE ROUTING LOOP — Oracle LP Rewards
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Route accumulated protocol fees to the oracle LP pool
     * @dev    Closes the value loop: traders pay fees → oracle stakers
     *         earn rewards → stakers back the measurement infrastructure
     *         → measurement enables trading → traders pay fees.
     *
     *         Anyone can call this (it's pure accounting) — KEEPER_ROLE
     *         is recommended for automation.
     */
    function routeFees() external nonReentrant {
        uint256 amount = pendingFees;
        if (amount == 0) revert ZeroAmount();

        pendingFees = 0;
        stablecoin.forceApprove(address(oracle), amount);
        oracle.depositRewards(amount);

        emit FeesRoutedToOracleLPs(amount);
    }

    // ════════════════════════════════════════════════════════════════
    //  VIEW FUNCTIONS — THESIS METRICS
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Calculate live PnL of a thesis position in oracle-relative terms
     * @dev    Pure index-change based PnL (doesn't account for funding,
     *         interest, or fees — use PerpetualEngine.getEquity() for exact)
     */
    function thesisPnLBps(address user) external view returns (int256) {
        ThesisPosition memory pos = thesisPositions[user];
        if (!pos.active) return 0;

        (uint256 currentIndex, ) = oracle.latestPrice();

        if (pos.isLong) {
            // Long profits when index rises
            int256 deltaBps = int256(
                ((currentIndex > pos.openIndexValue
                    ? currentIndex - pos.openIndexValue
                    : pos.openIndexValue - currentIndex)
                * BPS_DENOMINATOR) / pos.openIndexValue
            );
            return currentIndex >= pos.openIndexValue
                ? deltaBps * int256(pos.leverage)
                : -deltaBps * int256(pos.leverage);
        } else {
            // Short profits when index falls
            int256 deltaBps = int256(
                ((currentIndex > pos.openIndexValue
                    ? currentIndex - pos.openIndexValue
                    : pos.openIndexValue - currentIndex)
                * BPS_DENOMINATOR) / pos.openIndexValue
            );
            return currentIndex <= pos.openIndexValue
                ? deltaBps * int256(pos.leverage)
                : -deltaBps * int256(pos.leverage);
        }
    }

    /// @notice Check if a user has an active thesis position
    function hasActiveThesis(address user) external view returns (bool) {
        return thesisPositions[user].active;
    }

    /// @notice Current GDSI-denominated value of 1 sGDSI in stablecoin
    function sGdsiRedemptionValue() external view returns (uint256) {
        (uint256 price, ) = useEmaPrice
            ? oracle.latestEmaPrice()
            : oracle.latestPrice();
        return price / 1000;  // 1 sGDSI = (price/BASE) stable = price/1000 per PRECISION unit
    }

    /// @notice Protocol health: total sGDSI supply vs backing collateral
    function collateralizationRatio() external view returns (uint256) {
        uint256 supply = totalSupply();
        if (supply == 0) return type(uint256).max;

        (uint256 price, ) = oracle.latestPrice();
        uint256 notionalLiability = (supply * price) / BASE_INDEX;
        uint256 backing = stablecoin.balanceOf(address(this)) - pendingFees;

        return (backing * BPS_DENOMINATOR) / notionalLiability;
    }

    /// @notice Current stress level from oracle (0-5)
    function currentStressLevel() external view returns (uint8) {
        return oracle.stressLevel();
    }

    // ════════════════════════════════════════════════════════════════
    //  ADMIN
    // ════════════════════════════════════════════════════════════════

    function setMintFee(uint256 bps) external onlyRole(GOVERNOR_ROLE) {
        if (bps > MAX_MINT_FEE_BPS) revert FeeTooHigh(bps);
        mintFeeBps = bps;
        emit ConfigUpdated("mintFeeBps", bps);
    }

    function setBurnFee(uint256 bps) external onlyRole(GOVERNOR_ROLE) {
        if (bps > MAX_MINT_FEE_BPS) revert FeeTooHigh(bps);
        burnFeeBps = bps;
        emit ConfigUpdated("burnFeeBps", bps);
    }

    function setMaxSupply(uint256 cap) external onlyRole(GOVERNOR_ROLE) {
        maxSGdsiSupply = cap;
        emit ConfigUpdated("maxSGdsiSupply", cap);
    }

    function setMaxOracleAge(uint256 age) external onlyRole(GOVERNOR_ROLE) {
        maxOracleAge = age;
        emit ConfigUpdated("maxOracleAge", age);
    }

    function setUseEmaPrice(bool useEma) external onlyRole(GOVERNOR_ROLE) {
        useEmaPrice = useEma;
    }

    function pause() external onlyRole(GOVERNOR_ROLE) { _pause(); }
    function unpause() external onlyRole(GOVERNOR_ROLE) { _unpause(); }

    // ════════════════════════════════════════════════════════════════
    //  INTERNAL
    // ════════════════════════════════════════════════════════════════

    /// @dev Fetch oracle price with staleness validation
    function _getValidPrice() internal view returns (uint256 price) {
        uint256 updatedAt;
        (price, updatedAt) = useEmaPrice
            ? oracle.latestEmaPrice()
            : oracle.latestPrice();

        if (price == 0) revert OracleStale();
        if (block.timestamp - updatedAt > maxOracleAge) revert OracleStale();
        if (!oracle.isHeartbeatAlive()) revert OracleStale();
    }
}
