// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/interfaces/IERC3156FlashLender.sol";
import "@openzeppelin/contracts/interfaces/IERC3156FlashBorrower.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title DAIO_FlashLender
 * @notice Flash loans with governance oversight and constitutional compliance
 * @dev ERC3156 implementation integrated with DAIO governance and risk management
 */
contract DAIO_FlashLender is IERC3156FlashLender, AccessControl, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    bytes32 public constant FLASH_LENDER_ROLE = keccak256("FLASH_LENDER_ROLE");
    bytes32 public constant RISK_MANAGER_ROLE = keccak256("RISK_MANAGER_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");
    bytes32 public constant TREASURY_ROLE = keccak256("TREASURY_ROLE");

    // Flash loan configuration per token
    struct FlashLoanConfig {
        bool enabled;                   // Whether flash loans are enabled for this token
        uint256 fee;                   // Flash loan fee in BPS (basis points)
        uint256 maxLoanAmount;         // Maximum loan amount
        uint256 maxLoanPercentage;     // Maximum loan as percentage of available balance (BPS)
        uint256 dailyLimit;            // Daily lending limit
        uint256 userDailyLimit;        // Per-user daily limit
        uint256 minLoanAmount;         // Minimum loan amount
        bool requiresWhitelist;        // Whether borrower must be whitelisted
    }

    // Borrower risk profile
    struct BorrowerProfile {
        uint256 totalBorrowed;         // Total amount ever borrowed
        uint256 totalRepaid;           // Total amount repaid
        uint256 successfulLoans;       // Number of successful loans
        uint256 failedLoans;          // Number of failed loans
        uint256 lastLoanTime;         // Last loan timestamp
        bool whitelisted;             // Whether borrower is whitelisted
        bool blacklisted;             // Whether borrower is blacklisted
        uint256 riskScore;            // Risk score (0-10000, higher = riskier)
    }

    // Flash loan metrics
    struct FlashLoanMetrics {
        uint256 totalLoansIssued;     // Total number of loans issued
        uint256 totalVolumeLoaned;    // Total volume loaned
        uint256 totalFeesCollected;   // Total fees collected
        uint256 totalLiquidationEvents; // Total liquidation events
        uint256 averageLoanSize;      // Average loan size
        uint256 utilizationRate;      // Current utilization rate (BPS)
    }

    // Constitutional compliance tracking
    struct ConstitutionalLimits {
        uint256 maxSingleLoanPercentage; // Max single loan as % of treasury (15% constitutional limit)
        uint256 maxTotalExposure;      // Maximum total flash loan exposure
        uint256 titheRate;            // Tithe rate on fees (15% constitutional requirement)
        address treasuryContract;     // DAIO treasury contract
        bool constitutionalCompliance; // Whether to enforce constitutional limits
    }

    // State variables
    mapping(address => FlashLoanConfig) public flashLoanConfigs;
    mapping(address => BorrowerProfile) public borrowerProfiles;
    mapping(address => mapping(uint256 => uint256)) public dailyBorrowedAmount; // borrower -> day -> amount
    mapping(address => mapping(uint256 => uint256)) public tokenDailyVolume;    // token -> day -> volume
    mapping(address => FlashLoanMetrics) public flashLoanMetrics;

    address[] public supportedTokens;
    ConstitutionalLimits public constitutionalLimits;

    // Flash loan state tracking
    mapping(bytes32 => bool) private _activeLoans; // Hash of (borrower, amount, token) -> active
    uint256 private _loanCounter;

    // Fee distribution
    mapping(address => uint256) public collectedFees; // token -> collected fees
    uint256 public totalTithePaid;

    // Emergency controls
    bool public emergencyShutdown;
    mapping(address => bool) public emergencyTokenSuspension;

    // Events
    event FlashLoanExecuted(
        address indexed borrower,
        address indexed token,
        uint256 amount,
        uint256 fee,
        bool success
    );
    event FlashLoanConfigUpdated(
        address indexed token,
        uint256 fee,
        uint256 maxLoanAmount,
        bool enabled
    );
    event BorrowerWhitelisted(address indexed borrower, bool whitelisted);
    event BorrowerBlacklisted(address indexed borrower, bool blacklisted);
    event FeesDistributed(
        address indexed token,
        uint256 totalFees,
        uint256 titheAmount,
        uint256 timestamp
    );
    event EmergencyShutdownToggled(bool shutdown);
    event TokenSuspended(address indexed token, bool suspended);
    event RiskScoreUpdated(address indexed borrower, uint256 oldScore, uint256 newScore);

    /**
     * @notice Initialize DAIO Flash Lender
     * @param _treasuryContract DAIO treasury contract
     * @param admin Admin address for role management
     */
    constructor(
        address _treasuryContract,
        address admin
    ) {
        require(admin != address(0), "Admin cannot be zero address");

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(FLASH_LENDER_ROLE, admin);
        _grantRole(RISK_MANAGER_ROLE, admin);
        _grantRole(EMERGENCY_ROLE, admin);
        _grantRole(TREASURY_ROLE, admin);

        // Initialize constitutional limits aligned with DAIO requirements
        constitutionalLimits = ConstitutionalLimits({
            maxSingleLoanPercentage: 1500,    // 15% constitutional limit
            maxTotalExposure: 5000000 * 1e18, // 5M token maximum exposure
            titheRate: 1500,                  // 15% tithe rate
            treasuryContract: _treasuryContract,
            constitutionalCompliance: true
        });
    }

    /**
     * @notice Configure flash loan parameters for a token
     * @param token Token address
     * @param fee Fee in BPS
     * @param maxLoanAmount Maximum loan amount
     * @param maxLoanPercentage Maximum loan percentage of balance
     * @param dailyLimit Daily lending limit
     * @param userDailyLimit Per-user daily limit
     * @param enabled Whether flash loans are enabled
     */
    function configureFlashLoan(
        address token,
        uint256 fee,
        uint256 maxLoanAmount,
        uint256 maxLoanPercentage,
        uint256 dailyLimit,
        uint256 userDailyLimit,
        bool enabled
    ) external onlyRole(FLASH_LENDER_ROLE) {
        require(token != address(0), "Invalid token address");
        require(fee <= 1000, "Fee too high"); // Max 10%
        require(maxLoanPercentage <= 10000, "Invalid max loan percentage");

        flashLoanConfigs[token] = FlashLoanConfig({
            enabled: enabled,
            fee: fee,
            maxLoanAmount: maxLoanAmount,
            maxLoanPercentage: maxLoanPercentage,
            dailyLimit: dailyLimit,
            userDailyLimit: userDailyLimit,
            minLoanAmount: 1e18, // 1 token minimum
            requiresWhitelist: false
        });

        // Add to supported tokens if not already present
        bool isSupported = false;
        for (uint256 i = 0; i < supportedTokens.length; i++) {
            if (supportedTokens[i] == token) {
                isSupported = true;
                break;
            }
        }

        if (!isSupported) {
            supportedTokens.push(token);
        }

        emit FlashLoanConfigUpdated(token, fee, maxLoanAmount, enabled);
    }

    /**
     * @notice Execute flash loan
     * @param receiver Borrower contract implementing IERC3156FlashBorrower
     * @param token Token to borrow
     * @param amount Amount to borrow
     * @param data Additional data for borrower
     * @return success Whether the flash loan was successful
     */
    function flashLoan(
        IERC3156FlashBorrower receiver,
        address token,
        uint256 amount,
        bytes calldata data
    ) external override nonReentrant whenNotPaused returns (bool success) {
        require(!emergencyShutdown, "Emergency shutdown active");
        require(!emergencyTokenSuspension[token], "Token suspended");
        require(flashLoanConfigs[token].enabled, "Flash loans not enabled for token");
        require(amount > 0, "Amount must be greater than zero");

        // Validate borrower
        address borrower = address(receiver);
        require(!borrowerProfiles[borrower].blacklisted, "Borrower blacklisted");

        if (flashLoanConfigs[token].requiresWhitelist) {
            require(borrowerProfiles[borrower].whitelisted, "Borrower not whitelisted");
        }

        // Check constitutional compliance
        require(_checkConstitutionalLimits(token, amount), "Constitutional limits exceeded");

        // Check loan limits
        require(amount >= flashLoanConfigs[token].minLoanAmount, "Amount below minimum");
        require(amount <= maxFlashLoan(token), "Amount exceeds maximum");

        // Check daily limits
        uint256 currentDay = block.timestamp / 86400;
        require(
            tokenDailyVolume[token][currentDay] + amount <= flashLoanConfigs[token].dailyLimit,
            "Daily token limit exceeded"
        );
        require(
            dailyBorrowedAmount[borrower][currentDay] + amount <= flashLoanConfigs[token].userDailyLimit,
            "User daily limit exceeded"
        );

        // Calculate fee
        uint256 fee = flashFee(token, amount);
        uint256 totalRepayment = amount + fee;

        // Create unique loan identifier
        bytes32 loanId = keccak256(abi.encodePacked(borrower, amount, token, block.timestamp, _loanCounter++));
        _activeLoans[loanId] = true;

        // Check initial borrower balance for fee payment
        uint256 borrowerInitialBalance = IERC20(token).balanceOf(borrower);

        // Transfer tokens to borrower
        IERC20(token).safeTransfer(borrower, amount);

        // Call borrower's onFlashLoan function
        bytes32 callbackReturn = receiver.onFlashLoan(msg.sender, token, amount, fee, data);
        require(callbackReturn == keccak256("ERC3156FlashBorrower.onFlashLoan"), "Invalid callback return");

        // Verify repayment
        uint256 borrowerFinalBalance = IERC20(token).balanceOf(borrower);
        require(
            borrowerFinalBalance >= borrowerInitialBalance + fee ||
            IERC20(token).allowance(borrower, address(this)) >= totalRepayment,
            "Insufficient repayment"
        );

        // Collect repayment
        IERC20(token).safeTransferFrom(borrower, address(this), totalRepayment);

        // Update tracking
        _updateBorrowerProfile(borrower, amount, true);
        _updateFlashLoanMetrics(token, amount, fee);
        _updateDailyLimits(borrower, token, amount, currentDay);

        // Distribute fees
        _distributeFees(token, fee);

        // Mark loan as completed
        _activeLoans[loanId] = false;

        emit FlashLoanExecuted(borrower, token, amount, fee, true);

        return true;
    }

    /**
     * @notice Get flash loan fee for amount
     * @param token Token address
     * @param amount Loan amount
     * @return fee Fee amount
     */
    function flashFee(address token, uint256 amount) public view override returns (uint256 fee) {
        require(flashLoanConfigs[token].enabled, "Flash loans not enabled for token");
        return (amount * flashLoanConfigs[token].fee) / 10000;
    }

    /**
     * @notice Get maximum flash loan amount
     * @param token Token address
     * @return maxLoan Maximum loan amount
     */
    function maxFlashLoan(address token) public view override returns (uint256 maxLoan) {
        if (!flashLoanConfigs[token].enabled) return 0;

        uint256 availableBalance = IERC20(token).balanceOf(address(this));
        uint256 maxByBalance = (availableBalance * flashLoanConfigs[token].maxLoanPercentage) / 10000;
        uint256 maxByConfig = flashLoanConfigs[token].maxLoanAmount;

        return maxByBalance < maxByConfig ? maxByBalance : maxByConfig;
    }

    /**
     * @notice Whitelist borrower
     * @param borrower Borrower address
     * @param whitelisted Whether to whitelist
     */
    function setWhitelist(address borrower, bool whitelisted) external onlyRole(RISK_MANAGER_ROLE) {
        borrowerProfiles[borrower].whitelisted = whitelisted;
        emit BorrowerWhitelisted(borrower, whitelisted);
    }

    /**
     * @notice Blacklist borrower
     * @param borrower Borrower address
     * @param blacklisted Whether to blacklist
     */
    function setBlacklist(address borrower, bool blacklisted) external onlyRole(RISK_MANAGER_ROLE) {
        borrowerProfiles[borrower].blacklisted = blacklisted;
        emit BorrowerBlacklisted(borrower, blacklisted);
    }

    /**
     * @notice Update borrower risk score
     * @param borrower Borrower address
     * @param newRiskScore New risk score (0-10000)
     */
    function updateRiskScore(address borrower, uint256 newRiskScore) external onlyRole(RISK_MANAGER_ROLE) {
        require(newRiskScore <= 10000, "Invalid risk score");

        uint256 oldScore = borrowerProfiles[borrower].riskScore;
        borrowerProfiles[borrower].riskScore = newRiskScore;

        emit RiskScoreUpdated(borrower, oldScore, newRiskScore);
    }

    /**
     * @notice Emergency shutdown toggle
     * @param shutdown Whether to enable emergency shutdown
     */
    function setEmergencyShutdown(bool shutdown) external onlyRole(EMERGENCY_ROLE) {
        emergencyShutdown = shutdown;
        emit EmergencyShutdownToggled(shutdown);
    }

    /**
     * @notice Suspend token for flash loans
     * @param token Token to suspend
     * @param suspended Whether token is suspended
     */
    function suspendToken(address token, bool suspended) external onlyRole(EMERGENCY_ROLE) {
        emergencyTokenSuspension[token] = suspended;
        emit TokenSuspended(token, suspended);
    }

    /**
     * @notice Distribute collected fees
     * @param token Token to distribute fees for
     */
    function distributeFees(address token) external nonReentrant {
        uint256 fees = collectedFees[token];
        require(fees > 0, "No fees to distribute");

        _distributeFees(token, fees);
    }

    /**
     * @notice Get borrower profile
     * @param borrower Borrower address
     * @return profile Borrower profile data
     */
    function getBorrowerProfile(address borrower) external view returns (BorrowerProfile memory profile) {
        return borrowerProfiles[borrower];
    }

    /**
     * @notice Get flash loan metrics for token
     * @param token Token address
     * @return metrics Flash loan metrics
     */
    function getFlashLoanMetrics(address token) external view returns (FlashLoanMetrics memory metrics) {
        return flashLoanMetrics[token];
    }

    /**
     * @notice Get supported tokens
     * @return tokens Array of supported token addresses
     */
    function getSupportedTokens() external view returns (address[] memory tokens) {
        return supportedTokens;
    }

    /**
     * @notice Get constitutional limits
     * @return limits Constitutional limits configuration
     */
    function getConstitutionalLimits() external view returns (ConstitutionalLimits memory limits) {
        return constitutionalLimits;
    }

    /**
     * @notice Update constitutional limits
     * @param maxSingleLoanPercentage New max single loan percentage
     * @param maxTotalExposure New max total exposure
     * @param titheRate New tithe rate
     * @param treasuryContract New treasury contract
     */
    function updateConstitutionalLimits(
        uint256 maxSingleLoanPercentage,
        uint256 maxTotalExposure,
        uint256 titheRate,
        address treasuryContract
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(maxSingleLoanPercentage <= 1500, "Single loan percentage too high"); // Max 15%
        require(titheRate <= 1500, "Tithe rate too high"); // Max 15%

        constitutionalLimits.maxSingleLoanPercentage = maxSingleLoanPercentage;
        constitutionalLimits.maxTotalExposure = maxTotalExposure;
        constitutionalLimits.titheRate = titheRate;
        constitutionalLimits.treasuryContract = treasuryContract;
    }

    /**
     * @notice Emergency withdrawal of tokens (admin only)
     * @param token Token to withdraw
     * @param amount Amount to withdraw
     * @param recipient Recipient address
     */
    function emergencyWithdraw(
        address token,
        uint256 amount,
        address recipient
    ) external onlyRole(EMERGENCY_ROLE) {
        require(recipient != address(0), "Invalid recipient");
        IERC20(token).safeTransfer(recipient, amount);
    }

    // Internal Functions

    function _checkConstitutionalLimits(address token, uint256 amount) internal view returns (bool) {
        if (!constitutionalLimits.constitutionalCompliance) return true;

        // Check single loan limit (15% of available balance)
        uint256 availableBalance = IERC20(token).balanceOf(address(this));
        uint256 maxSingleLoan = (availableBalance * constitutionalLimits.maxSingleLoanPercentage) / 10000;

        if (amount > maxSingleLoan) return false;

        // Check total exposure
        uint256 currentExposure = 0;
        for (uint256 i = 0; i < supportedTokens.length; i++) {
            currentExposure += flashLoanMetrics[supportedTokens[i]].totalVolumeLoaned;
        }

        if (currentExposure + amount > constitutionalLimits.maxTotalExposure) return false;

        return true;
    }

    function _updateBorrowerProfile(address borrower, uint256 amount, bool successful) internal {
        BorrowerProfile storage profile = borrowerProfiles[borrower];

        profile.totalBorrowed += amount;
        profile.lastLoanTime = block.timestamp;

        if (successful) {
            profile.successfulLoans++;
            profile.totalRepaid += amount;

            // Improve risk score for successful loans
            if (profile.riskScore > 100) {
                profile.riskScore -= 100; // Reduce risk by 1%
            }
        } else {
            profile.failedLoans++;

            // Increase risk score for failed loans
            if (profile.riskScore < 9500) {
                profile.riskScore += 500; // Increase risk by 5%
            }
        }

        // Auto-blacklist borrowers with very high risk scores
        if (profile.riskScore >= 9000) {
            profile.blacklisted = true;
        }
    }

    function _updateFlashLoanMetrics(address token, uint256 amount, uint256 fee) internal {
        FlashLoanMetrics storage metrics = flashLoanMetrics[token];

        metrics.totalLoansIssued++;
        metrics.totalVolumeLoaned += amount;
        metrics.totalFeesCollected += fee;

        // Update average loan size
        metrics.averageLoanSize = metrics.totalVolumeLoaned / metrics.totalLoansIssued;

        // Update utilization rate
        uint256 availableBalance = IERC20(token).balanceOf(address(this));
        if (availableBalance > 0) {
            metrics.utilizationRate = (amount * 10000) / availableBalance;
        }
    }

    function _updateDailyLimits(address borrower, address token, uint256 amount, uint256 currentDay) internal {
        dailyBorrowedAmount[borrower][currentDay] += amount;
        tokenDailyVolume[token][currentDay] += amount;
    }

    function _distributeFees(address token, uint256 totalFees) internal {
        if (totalFees == 0) return;

        uint256 titheAmount = 0;

        // Calculate and send tithe to treasury
        if (constitutionalLimits.treasuryContract != address(0) && constitutionalLimits.titheRate > 0) {
            titheAmount = (totalFees * constitutionalLimits.titheRate) / 10000;

            if (titheAmount > 0) {
                IERC20(token).safeTransfer(constitutionalLimits.treasuryContract, titheAmount);
                totalTithePaid += titheAmount;
            }
        }

        // Update collected fees tracking
        collectedFees[token] = 0; // Reset after distribution

        emit FeesDistributed(token, totalFees, titheAmount, block.timestamp);
    }

    /**
     * @notice Deposit tokens to enable flash lending
     * @param token Token to deposit
     * @param amount Amount to deposit
     */
    function depositTokens(address token, uint256 amount) external onlyRole(TREASURY_ROLE) {
        require(flashLoanConfigs[token].enabled, "Token not supported");
        IERC20(token).safeTransferFrom(msg.sender, address(this), amount);
    }

    /**
     * @notice Withdraw tokens from flash lending pool
     * @param token Token to withdraw
     * @param amount Amount to withdraw
     * @param recipient Recipient address
     */
    function withdrawTokens(
        address token,
        uint256 amount,
        address recipient
    ) external onlyRole(TREASURY_ROLE) {
        require(recipient != address(0), "Invalid recipient");
        IERC20(token).safeTransfer(recipient, amount);
    }

    /**
     * @notice Get current utilization rate for token
     * @param token Token address
     * @return utilizationRate Current utilization rate (BPS)
     */
    function getUtilizationRate(address token) external view returns (uint256 utilizationRate) {
        uint256 totalBalance = IERC20(token).balanceOf(address(this));
        if (totalBalance == 0) return 0;

        uint256 currentDay = block.timestamp / 86400;
        uint256 dailyVolume = tokenDailyVolume[token][currentDay];

        return (dailyVolume * 10000) / totalBalance;
    }

    /**
     * @notice Check if borrower can take flash loan
     * @param borrower Borrower address
     * @param token Token address
     * @param amount Loan amount
     * @return canBorrow Whether borrower can take the loan
     * @return reason Reason if borrower cannot take the loan
     */
    function canBorrow(
        address borrower,
        address token,
        uint256 amount
    ) external view returns (bool canBorrow, string memory reason) {
        if (emergencyShutdown) {
            return (false, "Emergency shutdown active");
        }

        if (emergencyTokenSuspension[token]) {
            return (false, "Token suspended");
        }

        if (!flashLoanConfigs[token].enabled) {
            return (false, "Flash loans not enabled for token");
        }

        if (borrowerProfiles[borrower].blacklisted) {
            return (false, "Borrower blacklisted");
        }

        if (flashLoanConfigs[token].requiresWhitelist && !borrowerProfiles[borrower].whitelisted) {
            return (false, "Borrower not whitelisted");
        }

        if (amount > maxFlashLoan(token)) {
            return (false, "Amount exceeds maximum");
        }

        if (!_checkConstitutionalLimits(token, amount)) {
            return (false, "Constitutional limits exceeded");
        }

        uint256 currentDay = block.timestamp / 86400;
        if (tokenDailyVolume[token][currentDay] + amount > flashLoanConfigs[token].dailyLimit) {
            return (false, "Daily token limit exceeded");
        }

        if (dailyBorrowedAmount[borrower][currentDay] + amount > flashLoanConfigs[token].userDailyLimit) {
            return (false, "User daily limit exceeded");
        }

        return (true, "");
    }

    /**
     * @notice Pause flash lending operations
     */
    function pause() external onlyRole(EMERGENCY_ROLE) {
        _pause();
    }

    /**
     * @notice Unpause flash lending operations
     */
    function unpause() external onlyRole(EMERGENCY_ROLE) {
        _unpause();
    }
}