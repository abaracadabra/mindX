// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title RWAToken — Compliant Real World Asset Token (Audited v2)
 * @author Professor Codephreak — DELTAVERSE Ecosystem
 * @notice ERC-20 with KYC whitelist, yield distribution, freeze/seize, pause
 * @dev Designed for tokenizing sovereign debt, corporate bonds, real estate
 *
 * Part of: "The Cryptographic Inheritance of Global Debt"
 * Contract I of III — RWA Tokenization Primitive
 *
 * Audit Fixes (v2):
 *   [CRITICAL] Fixed double yield accounting in mint/burn paths
 *   [CRITICAL] seize() now bypasses freeze checks via internal flag
 *   [MEDIUM]   Added Pausable emergency stop
 *   [MEDIUM]   Added supply cap enforcement
 *   [MEDIUM]   Added batch whitelist for gas-efficient onboarding
 *   [MEDIUM]   Added ERC-20 yield token support (ETH or stablecoin)
 *   [LOW]      Added maturity enforcement on transfers
 *   [LOW]      Custom errors for gas efficiency
 *   [LOW]      Added totalYieldDistributed accounting
 */
contract RWAToken is ERC20, AccessControl, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ════════════════════════════════════════════════════════════════
    //  ROLES
    // ════════════════════════════════════════════════════════════════

    bytes32 public constant ISSUER_ROLE     = keccak256("ISSUER_ROLE");
    bytes32 public constant COMPLIANCE_ROLE = keccak256("COMPLIANCE_ROLE");

    // ════════════════════════════════════════════════════════════════
    //  CUSTOM ERRORS (gas-efficient vs revert strings)
    // ════════════════════════════════════════════════════════════════

    error NotWhitelisted(address account);
    error AccountFrozen(address account);
    error ZeroAddress();
    error ZeroAmount();
    error SupplyCapExceeded(uint256 requested, uint256 cap, uint256 current);
    error AssetMatured(uint256 maturity, uint256 current);
    error AssetNotMatured(uint256 maturity, uint256 current);
    error NoYieldPending();
    error NoSupply();
    error BatchLengthMismatch();
    error BatchTooLarge();
    error YieldTransferFailed();

    // ════════════════════════════════════════════════════════════════
    //  ASSET METADATA
    // ════════════════════════════════════════════════════════════════

    string  public assetDescription;            // e.g. "US Treasury 10Y Note"
    string  public assetISIN;                   // ISIN / CUSIP identifier
    uint256 public immutable maturityTimestamp;  // 0 = perpetual / equity-like
    uint256 public immutable faceValueBps;       // basis-point coupon / yield
    uint256 public immutable supplyCap;          // max mintable supply (0 = unlimited)

    // ════════════════════════════════════════════════════════════════
    //  COMPLIANCE STATE
    // ════════════════════════════════════════════════════════════════

    mapping(address => bool) public whitelisted;
    mapping(address => bool) public frozen;

    /// @dev Internal flag — when true, _update skips freeze/whitelist checks
    ///      Used exclusively by seize() for regulatory force-transfers
    bool private _bypassCompliance;

    // ════════════════════════════════════════════════════════════════
    //  YIELD ACCOUNTING
    // ════════════════════════════════════════════════════════════════

    /// @notice The ERC-20 token used to pay yield (address(0) = native ETH)
    address public yieldToken;

    uint256 public accYieldPerToken;            // accumulated yield per token (scaled 1e18)
    uint256 public lastYieldTimestamp;
    uint256 public totalYieldDistributed;       // lifetime yield distributed

    mapping(address => uint256) public yieldDebt;
    mapping(address => uint256) public pendingYield;

    // ════════════════════════════════════════════════════════════════
    //  CONSTANTS
    // ════════════════════════════════════════════════════════════════

    uint256 private constant PRECISION = 1e18;
    uint256 private constant MAX_BATCH = 200;

    // ════════════════════════════════════════════════════════════════
    //  EVENTS
    // ════════════════════════════════════════════════════════════════

    event WhitelistUpdated(address indexed account, bool status);
    event FrozenUpdated(address indexed account, bool status);
    event BatchWhitelistUpdated(uint256 count);
    event YieldDistributed(uint256 amount, uint256 timestamp, address yieldToken);
    event YieldClaimed(address indexed account, uint256 amount);
    event AssetSeized(address indexed from, address indexed to, uint256 amount, string reason);
    event YieldTokenUpdated(address indexed oldToken, address indexed newToken);
    event Redeemed(address indexed holder, uint256 amount);

    // ════════════════════════════════════════════════════════════════
    //  CONSTRUCTOR
    // ════════════════════════════════════════════════════════════════

    /**
     * @param name_        Token name (e.g. "Tokenized US Treasury 10Y")
     * @param symbol_      Token symbol (e.g. "tUST10Y")
     * @param description_ Human-readable asset description
     * @param isin_        ISIN / CUSIP identifier
     * @param maturity_    Maturity timestamp (0 for perpetual)
     * @param couponBps_   Annual coupon in basis points (e.g. 425 = 4.25%)
     * @param supplyCap_   Maximum token supply (0 = unlimited)
     * @param yieldToken_  ERC-20 for yield payments (address(0) = native ETH)
     */
    constructor(
        string memory name_,
        string memory symbol_,
        string memory description_,
        string memory isin_,
        uint256 maturity_,
        uint256 couponBps_,
        uint256 supplyCap_,
        address yieldToken_
    ) ERC20(name_, symbol_) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(ISSUER_ROLE, msg.sender);
        _grantRole(COMPLIANCE_ROLE, msg.sender);

        assetDescription    = description_;
        assetISIN           = isin_;
        maturityTimestamp    = maturity_;
        faceValueBps        = couponBps_;
        supplyCap           = supplyCap_;
        yieldToken          = yieldToken_;
        lastYieldTimestamp   = block.timestamp;
    }

    // ════════════════════════════════════════════════════════════════
    //  MODIFIERS
    // ════════════════════════════════════════════════════════════════

    /// @dev Revert if asset has NOT matured (for redemption only)
    modifier afterMaturity() {
        if (maturityTimestamp != 0 && block.timestamp < maturityTimestamp)
            revert AssetNotMatured(maturityTimestamp, block.timestamp);
        _;
    }

    // ════════════════════════════════════════════════════════════════
    //  COMPLIANCE FUNCTIONS
    // ════════════════════════════════════════════════════════════════

    /// @notice Add or remove a single address from the KYC whitelist
    function setWhitelist(address account, bool status)
        external
        onlyRole(COMPLIANCE_ROLE)
    {
        if (account == address(0)) revert ZeroAddress();
        whitelisted[account] = status;
        emit WhitelistUpdated(account, status);
    }

    /// @notice Batch whitelist update — gas-efficient onboarding
    /// @param accounts Array of addresses to update
    /// @param statuses Array of whitelist statuses (true/false)
    function batchSetWhitelist(address[] calldata accounts, bool[] calldata statuses)
        external
        onlyRole(COMPLIANCE_ROLE)
    {
        if (accounts.length != statuses.length) revert BatchLengthMismatch();
        if (accounts.length > MAX_BATCH) revert BatchTooLarge();

        for (uint256 i; i < accounts.length; ) {
            if (accounts[i] == address(0)) revert ZeroAddress();
            whitelisted[accounts[i]] = statuses[i];
            unchecked { ++i; }
        }
        emit BatchWhitelistUpdated(accounts.length);
    }

    /// @notice Freeze an account — blocks all transfers in and out
    function setFrozen(address account, bool status)
        external
        onlyRole(COMPLIANCE_ROLE)
    {
        if (account == address(0)) revert ZeroAddress();
        frozen[account] = status;
        emit FrozenUpdated(account, status);
    }

    /**
     * @notice Regulatory seizure — force-transfer tokens between accounts
     * @dev    Bypasses freeze and whitelist checks via internal flag.
     *         This is intentional: a compliance officer must be able to
     *         seize tokens FROM a frozen account TO any designated address
     *         (e.g. court-appointed receiver, treasury, burn address).
     * @param from   Source account (may be frozen)
     * @param to     Destination account (need not be whitelisted)
     * @param amount Number of tokens to seize
     * @param reason Regulatory reason string for audit trail
     */
    function seize(address from, address to, uint256 amount, string calldata reason)
        external
        onlyRole(COMPLIANCE_ROLE)
    {
        if (from == address(0) || to == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();

        _bypassCompliance = true;
        _transfer(from, to, amount);
        _bypassCompliance = false;

        emit AssetSeized(from, to, amount, reason);
    }

    // ════════════════════════════════════════════════════════════════
    //  ISSUANCE
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Mint new RWA tokens to a whitelisted address
     * @dev    Yield accounting is handled entirely by _update() hook.
     *         No explicit _updateYield call here — fixes the double-
     *         accounting bug from v1.
     */
    function mint(address to, uint256 amount)
        external
        onlyRole(ISSUER_ROLE)
        whenNotPaused
    {
        if (to == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();
        if (!whitelisted[to]) revert NotWhitelisted(to);

        if (supplyCap != 0 && totalSupply() + amount > supplyCap)
            revert SupplyCapExceeded(amount, supplyCap, totalSupply());

        _mint(to, amount);
    }

    /**
     * @notice Burn RWA tokens (issuer-initiated)
     * @dev    Yield accounting handled by _update() hook.
     */
    function burn(address from, uint256 amount)
        external
        onlyRole(ISSUER_ROLE)
    {
        if (from == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();
        _burn(from, amount);
    }

    /**
     * @notice Holder-initiated redemption at maturity
     * @dev    Only available after maturityTimestamp. Burns caller's tokens.
     *         Off-chain settlement delivers the underlying asset value.
     */
    function redeem(uint256 amount)
        external
        nonReentrant
        afterMaturity
    {
        if (amount == 0) revert ZeroAmount();
        _burn(msg.sender, amount);
        emit Redeemed(msg.sender, amount);
    }

    // ════════════════════════════════════════════════════════════════
    //  YIELD DISTRIBUTION
    // ════════════════════════════════════════════════════════════════

    /**
     * @notice Distribute yield to all token holders pro-rata
     * @dev    Supports both native ETH (msg.value) and ERC-20 (yieldToken).
     *         If yieldToken == address(0), yield is distributed as ETH.
     *         If yieldToken != address(0), caller must have approved this
     *         contract and `amount` is pulled via safeTransferFrom.
     * @param amount The amount of ERC-20 yield to distribute (ignored for ETH)
     */
    function distributeYield(uint256 amount)
        external
        payable
        onlyRole(ISSUER_ROLE)
        whenNotPaused
    {
        if (totalSupply() == 0) revert NoSupply();

        uint256 yieldAmount;

        if (yieldToken == address(0)) {
            // Native ETH yield
            if (msg.value == 0) revert ZeroAmount();
            yieldAmount = msg.value;
        } else {
            // ERC-20 yield (e.g. USDC, USDT)
            if (amount == 0) revert ZeroAmount();
            IERC20(yieldToken).safeTransferFrom(msg.sender, address(this), amount);
            yieldAmount = amount;
        }

        accYieldPerToken += (yieldAmount * PRECISION) / totalSupply();
        lastYieldTimestamp = block.timestamp;
        totalYieldDistributed += yieldAmount;

        emit YieldDistributed(yieldAmount, block.timestamp, yieldToken);
    }

    /// @notice Claim all accumulated yield
    function claimYield()
        external
        nonReentrant
        whenNotPaused
    {
        if (frozen[msg.sender]) revert AccountFrozen(msg.sender);

        _updateYield(msg.sender);
        uint256 amount = pendingYield[msg.sender];
        if (amount == 0) revert NoYieldPending();

        pendingYield[msg.sender] = 0;

        if (yieldToken == address(0)) {
            (bool ok, ) = payable(msg.sender).call{value: amount}("");
            if (!ok) revert YieldTransferFailed();
        } else {
            IERC20(yieldToken).safeTransfer(msg.sender, amount);
        }

        emit YieldClaimed(msg.sender, amount);
    }

    /// @notice View pending (unclaimed) yield for an account
    function viewPendingYield(address account) external view returns (uint256) {
        uint256 acc = (balanceOf(account) * accYieldPerToken) / PRECISION;
        return pendingYield[account] + acc - yieldDebt[account];
    }

    // ════════════════════════════════════════════════════════════════
    //  ADMIN / CONFIGURATION
    // ════════════════════════════════════════════════════════════════

    /// @notice Update the yield payment token (admin only)
    /// @dev    Existing unclaimed yield must be claimed under old token first
    function setYieldToken(address newYieldToken)
        external
        onlyRole(DEFAULT_ADMIN_ROLE)
    {
        address old = yieldToken;
        yieldToken = newYieldToken;
        emit YieldTokenUpdated(old, newYieldToken);
    }

    /// @notice Emergency pause — halts minting, yield distribution, and claims
    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    /// @notice Unpause the contract
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    // ════════════════════════════════════════════════════════════════
    //  TRANSFER HOOKS (compliance-gated)
    // ════════════════════════════════════════════════════════════════

    /**
     * @dev    Core transfer hook — handles:
     *         1. Compliance checks (whitelist, freeze) unless _bypassCompliance
     *         2. Yield accounting for sender and recipient
     *         3. Maturity enforcement for secondary-market transfers
     *
     *         This is the SINGLE source of truth for yield accounting.
     *         mint(), burn(), transfer(), and seize() all flow through here.
     *         No other function should call _updateYield directly before
     *         invoking _mint/_burn/_transfer to prevent double accounting.
     */
    function _update(address from, address to, uint256 amount)
        internal
        override
    {
        // ── Compliance checks (skipped during seize) ──
        if (!_bypassCompliance) {
            if (from != address(0)) {
                if (frozen[from]) revert AccountFrozen(from);
            }
            if (to != address(0)) {
                if (!whitelisted[to]) revert NotWhitelisted(to);
                if (frozen[to]) revert AccountFrozen(to);
            }
            // Enforce maturity on secondary transfers only (not mint/burn)
            if (from != address(0) && to != address(0)) {
                if (maturityTimestamp != 0 && block.timestamp >= maturityTimestamp)
                    revert AssetMatured(maturityTimestamp, block.timestamp);
            }
        }

        // ── Yield accounting BEFORE balance change ──
        if (from != address(0) && balanceOf(from) > 0) {
            _updateYield(from);
        }
        if (to != address(0) && balanceOf(to) > 0) {
            _updateYield(to);
        }

        // ── Execute the balance change ──
        super._update(from, to, amount);

        // ── Recalculate yield debt AFTER balance change ──
        if (from != address(0)) {
            yieldDebt[from] = (balanceOf(from) * accYieldPerToken) / PRECISION;
        }
        if (to != address(0)) {
            yieldDebt[to] = (balanceOf(to) * accYieldPerToken) / PRECISION;
        }
    }

    /// @dev Snapshot pending yield for an account based on current accumulator
    function _updateYield(address account) private {
        uint256 acc = (balanceOf(account) * accYieldPerToken) / PRECISION;
        uint256 debt = yieldDebt[account];
        if (acc > debt) {
            pendingYield[account] += acc - debt;
        }
        yieldDebt[account] = acc;
    }

    // ════════════════════════════════════════════════════════════════
    //  RECEIVE
    // ════════════════════════════════════════════════════════════════

    /// @dev Accept ETH for yield distribution
    receive() external payable {}
}
