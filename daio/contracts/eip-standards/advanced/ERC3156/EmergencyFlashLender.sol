// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./DAIO_FlashLender.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title EmergencyFlashLender
 * @notice Emergency liquidity via existing treasury with crisis response capabilities
 * @dev Extends DAIO_FlashLender for emergency situations with treasury backing
 */
contract EmergencyFlashLender is DAIO_FlashLender {
    using SafeERC20 for IERC20;

    // Emergency lending configuration
    struct EmergencyConfig {
        bool emergencyModeActive;       // Whether emergency mode is currently active
        uint256 emergencyActivatedAt;  // When emergency mode was activated
        uint256 emergencyDuration;     // Maximum duration of emergency mode (seconds)
        address emergencyActivator;    // Address that activated emergency mode
        string emergencyReason;        // Reason for emergency activation
        uint256 maxEmergencyLoanSize;  // Maximum loan size during emergency
        uint256 emergencyFeeMultiplier; // Fee multiplier during emergency (BPS)
        bool treasuryBackingEnabled;   // Whether treasury backing is enabled
    }

    // Treasury integration for emergency liquidity
    struct TreasuryLiquidityPool {
        address treasuryContract;      // Existing DAIO treasury contract
        mapping(address => uint256) reserveAmounts; // token -> reserve amount in treasury
        mapping(address => uint256) emergencyAllocations; // token -> allocated for emergency
        uint256 totalTreasuryBacking; // Total treasury backing available
        uint256 maxTreasuryUtilization; // Maximum treasury utilization percentage (BPS)
        uint256 treasuryReplenishmentRate; // Rate at which treasury is replenished
        bool autoReplenishEnabled;    // Whether automatic treasury replenishment is enabled
    }

    // Crisis response mechanisms
    struct CrisisResponse {
        uint256 crisisLevel;           // Crisis level (1-5, 5 being most severe)
        mapping(address => bool) approvedEmergencyBorrowers; // Pre-approved emergency borrowers
        mapping(address => uint256) emergencyLoanLimits; // Special limits for emergency borrowers
        uint256 systemwideUtilizationLimit; // System-wide utilization limit during crisis
        bool liquidationProtectionEnabled; // Whether liquidation protection is active
        uint256 priorityLoanQueue;     // Priority queue for emergency loans
    }

    // Multi-signature emergency controls (integrating with DAIO 3-of-5 pattern)
    struct EmergencyMultiSig {
        mapping(address => bool) emergencySigners; // Authorized emergency signers
        mapping(bytes32 => uint256) proposalVotes; // proposal hash -> vote count
        mapping(bytes32 => mapping(address => bool)) hasVoted; // proposal -> signer -> voted
        uint256 requiredSignatures;   // Required signatures (3 for DAIO compatibility)
        uint256 totalSigners;         // Total number of signers
    }

    // State variables
    EmergencyConfig public emergencyConfig;
    TreasuryLiquidityPool public treasuryPool;
    CrisisResponse public crisisResponse;
    EmergencyMultiSig public emergencyMultiSig;

    // Emergency loan tracking
    mapping(address => uint256) public emergencyLoansOutstanding; // borrower -> outstanding amount
    mapping(address => uint256) public lastEmergencyLoanTime;     // borrower -> last loan time
    uint256 public totalEmergencyLoansIssued;
    uint256 public totalTreasuryLiquidityUtilized;

    // Emergency governance
    bytes32 public constant EMERGENCY_COUNCIL_ROLE = keccak256("EMERGENCY_COUNCIL_ROLE");
    bytes32 public constant TREASURY_MANAGER_ROLE = keccak256("TREASURY_MANAGER_ROLE");
    bytes32 public constant CRISIS_RESPONDER_ROLE = keccak256("CRISIS_RESPONDER_ROLE");

    // Events
    event EmergencyModeActivated(
        address indexed activator,
        string reason,
        uint256 duration,
        uint256 timestamp
    );
    event EmergencyModeDeactivated(
        address indexed deactivator,
        uint256 totalLoansIssued,
        uint256 timestamp
    );
    event EmergencyLoanIssued(
        address indexed borrower,
        address indexed token,
        uint256 amount,
        uint256 emergencyFee,
        bool treasuryBacked
    );
    event TreasuryBackingUtilized(
        address indexed token,
        uint256 amount,
        uint256 remainingReserves
    );
    event CrisisLevelUpdated(
        uint256 oldLevel,
        uint256 newLevel,
        string reason
    );
    event EmergencyBorrowerApproved(
        address indexed borrower,
        uint256 emergencyLimit,
        address indexed approver
    );
    event EmergencyProposalCreated(
        bytes32 indexed proposalHash,
        string action,
        address indexed proposer
    );
    event EmergencyProposalExecuted(
        bytes32 indexed proposalHash,
        bool success,
        uint256 voteCount
    );

    /**
     * @notice Initialize EmergencyFlashLender with treasury backing
     * @param _treasuryContract Existing DAIO treasury contract
     * @param admin Admin address
     */
    constructor(
        address _treasuryContract,
        address admin
    ) DAIO_FlashLender(_treasuryContract, admin) {
        require(_treasuryContract != address(0), "Treasury contract cannot be zero address");

        _grantRole(EMERGENCY_COUNCIL_ROLE, admin);
        _grantRole(TREASURY_MANAGER_ROLE, admin);
        _grantRole(CRISIS_RESPONDER_ROLE, admin);

        // Initialize emergency configuration
        emergencyConfig = EmergencyConfig({
            emergencyModeActive: false,
            emergencyActivatedAt: 0,
            emergencyDuration: 7 days,        // 7-day maximum emergency duration
            emergencyActivator: address(0),
            emergencyReason: "",
            maxEmergencyLoanSize: 1000000 * 1e18, // 1M token max emergency loan
            emergencyFeeMultiplier: 5000,     // 50% fee reduction during emergency
            treasuryBackingEnabled: true
        });

        // Initialize treasury liquidity pool
        treasuryPool.treasuryContract = _treasuryContract;
        treasuryPool.maxTreasuryUtilization = 3000; // 30% max utilization
        treasuryPool.treasuryReplenishmentRate = 1000; // 10% daily replenishment
        treasuryPool.autoReplenishEnabled = true;

        // Initialize crisis response
        crisisResponse.crisisLevel = 1; // Start at level 1 (normal)
        crisisResponse.systemwideUtilizationLimit = 7500; // 75% system-wide limit
        crisisResponse.liquidationProtectionEnabled = false;

        // Initialize emergency multi-sig (compatible with DAIO 3-of-5 pattern)
        emergencyMultiSig.requiredSignatures = 3;
        emergencyMultiSig.totalSigners = 0;

        // Add admin as initial emergency signer
        _addEmergencySigner(admin);
    }

    /**
     * @notice Activate emergency mode with multi-sig approval
     * @param reason Reason for emergency activation
     * @param duration Duration of emergency mode (seconds)
     * @param maxLoanSize Maximum loan size during emergency
     */
    function activateEmergencyMode(
        string memory reason,
        uint256 duration,
        uint256 maxLoanSize
    ) external onlyRole(EMERGENCY_COUNCIL_ROLE) {
        require(!emergencyConfig.emergencyModeActive, "Emergency mode already active");
        require(duration <= 30 days, "Emergency duration too long"); // Max 30 days
        require(bytes(reason).length > 0, "Reason required");

        // Create proposal for emergency activation
        bytes32 proposalHash = keccak256(
            abi.encodePacked(
                "ACTIVATE_EMERGENCY",
                reason,
                duration,
                maxLoanSize,
                block.timestamp
            )
        );

        require(!emergencyMultiSig.hasVoted[proposalHash][msg.sender], "Already voted on proposal");

        emergencyMultiSig.proposalVotes[proposalHash]++;
        emergencyMultiSig.hasVoted[proposalHash][msg.sender] = true;

        emit EmergencyProposalCreated(proposalHash, "ACTIVATE_EMERGENCY", msg.sender);

        // Execute if enough votes
        if (emergencyMultiSig.proposalVotes[proposalHash] >= emergencyMultiSig.requiredSignatures) {
            _executeEmergencyActivation(reason, duration, maxLoanSize);
            emit EmergencyProposalExecuted(proposalHash, true, emergencyMultiSig.proposalVotes[proposalHash]);
        }
    }

    /**
     * @notice Execute flash loan with emergency provisions
     * @param receiver Borrower contract
     * @param token Token to borrow
     * @param amount Amount to borrow
     * @param data Additional data
     * @return success Whether flash loan was successful
     */
    function flashLoan(
        IERC3156FlashBorrower receiver,
        address token,
        uint256 amount,
        bytes calldata data
    ) public override nonReentrant whenNotPaused returns (bool success) {
        address borrower = address(receiver);

        // Check if this is an emergency loan
        bool isEmergencyLoan = _isEmergencyLoan(borrower, amount);

        if (isEmergencyLoan) {
            return _executeEmergencyFlashLoan(receiver, token, amount, data);
        } else {
            // Standard flash loan with potential treasury backing
            return _executeStandardFlashLoan(receiver, token, amount, data);
        }
    }

    /**
     * @notice Approve borrower for emergency lending
     * @param borrower Borrower address
     * @param emergencyLimit Emergency loan limit
     */
    function approveEmergencyBorrower(
        address borrower,
        uint256 emergencyLimit
    ) external onlyRole(CRISIS_RESPONDER_ROLE) {
        require(borrower != address(0), "Invalid borrower address");
        require(emergencyLimit > 0, "Emergency limit must be positive");

        crisisResponse.approvedEmergencyBorrowers[borrower] = true;
        crisisResponse.emergencyLoanLimits[borrower] = emergencyLimit;

        emit EmergencyBorrowerApproved(borrower, emergencyLimit, msg.sender);
    }

    /**
     * @notice Update crisis level
     * @param newLevel New crisis level (1-5)
     * @param reason Reason for level change
     */
    function updateCrisisLevel(
        uint256 newLevel,
        string memory reason
    ) external onlyRole(CRISIS_RESPONDER_ROLE) {
        require(newLevel >= 1 && newLevel <= 5, "Invalid crisis level");

        uint256 oldLevel = crisisResponse.crisisLevel;
        crisisResponse.crisisLevel = newLevel;

        // Adjust system parameters based on crisis level
        _adjustCrisisParameters(newLevel);

        emit CrisisLevelUpdated(oldLevel, newLevel, reason);
    }

    /**
     * @notice Allocate treasury funds for emergency lending
     * @param token Token to allocate
     * @param amount Amount to allocate
     */
    function allocateTreasuryFunds(
        address token,
        uint256 amount
    ) external onlyRole(TREASURY_MANAGER_ROLE) {
        require(treasuryPool.treasuryContract != address(0), "Treasury not configured");
        require(amount > 0, "Amount must be positive");

        // Check maximum utilization
        uint256 currentUtilization = (treasuryPool.emergencyAllocations[token] * 10000) /
                                    treasuryPool.reserveAmounts[token];

        require(
            currentUtilization + (amount * 10000 / treasuryPool.reserveAmounts[token]) <=
            treasuryPool.maxTreasuryUtilization,
            "Treasury utilization limit exceeded"
        );

        // Transfer from treasury to this contract
        IERC20(token).safeTransferFrom(treasuryPool.treasuryContract, address(this), amount);

        treasuryPool.emergencyAllocations[token] += amount;
        treasuryPool.totalTreasuryBacking += amount;
    }

    /**
     * @notice Replenish treasury reserves
     * @param token Token to replenish
     * @param amount Amount to replenish
     */
    function replenishTreasuryReserves(
        address token,
        uint256 amount
    ) external onlyRole(TREASURY_MANAGER_ROLE) {
        require(amount > 0, "Amount must be positive");

        // Return funds to treasury
        IERC20(token).safeTransfer(treasuryPool.treasuryContract, amount);

        if (treasuryPool.emergencyAllocations[token] >= amount) {
            treasuryPool.emergencyAllocations[token] -= amount;
            treasuryPool.totalTreasuryBacking -= amount;
        }
    }

    /**
     * @notice Deactivate emergency mode
     */
    function deactivateEmergencyMode() external onlyRole(EMERGENCY_COUNCIL_ROLE) {
        require(emergencyConfig.emergencyModeActive, "Emergency mode not active");

        // Create proposal for emergency deactivation
        bytes32 proposalHash = keccak256(
            abi.encodePacked(
                "DEACTIVATE_EMERGENCY",
                block.timestamp
            )
        );

        require(!emergencyMultiSig.hasVoted[proposalHash][msg.sender], "Already voted on proposal");

        emergencyMultiSig.proposalVotes[proposalHash]++;
        emergencyMultiSig.hasVoted[proposalHash][msg.sender] = true;

        emit EmergencyProposalCreated(proposalHash, "DEACTIVATE_EMERGENCY", msg.sender);

        // Execute if enough votes
        if (emergencyMultiSig.proposalVotes[proposalHash] >= emergencyMultiSig.requiredSignatures) {
            _executeEmergencyDeactivation();
            emit EmergencyProposalExecuted(proposalHash, true, emergencyMultiSig.proposalVotes[proposalHash]);
        }
    }

    /**
     * @notice Add emergency signer to multi-sig
     * @param signer Signer address to add
     */
    function addEmergencySigner(address signer) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _addEmergencySigner(signer);
    }

    /**
     * @notice Remove emergency signer from multi-sig
     * @param signer Signer address to remove
     */
    function removeEmergencySigner(address signer) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(emergencyMultiSig.emergencySigners[signer], "Not an emergency signer");
        require(emergencyMultiSig.totalSigners > emergencyMultiSig.requiredSignatures, "Cannot remove - would break multi-sig");

        emergencyMultiSig.emergencySigners[signer] = false;
        emergencyMultiSig.totalSigners--;
    }

    /**
     * @notice Get emergency configuration
     * @return config Emergency configuration
     */
    function getEmergencyConfig() external view returns (EmergencyConfig memory config) {
        return emergencyConfig;
    }

    /**
     * @notice Get treasury liquidity status
     * @return totalBacking Total treasury backing
     * @return utilizationRate Current utilization rate (BPS)
     * @return availableLiquidity Available liquidity
     */
    function getTreasuryLiquidityStatus() external view returns (
        uint256 totalBacking,
        uint256 utilizationRate,
        uint256 availableLiquidity
    ) {
        totalBacking = treasuryPool.totalTreasuryBacking;
        utilizationRate = totalBacking > 0 ?
            (totalTreasuryLiquidityUtilized * 10000) / totalBacking : 0;
        availableLiquidity = totalBacking > totalTreasuryLiquidityUtilized ?
            totalBacking - totalTreasuryLiquidityUtilized : 0;

        return (totalBacking, utilizationRate, availableLiquidity);
    }

    // Internal Functions

    function _executeEmergencyActivation(
        string memory reason,
        uint256 duration,
        uint256 maxLoanSize
    ) internal {
        emergencyConfig.emergencyModeActive = true;
        emergencyConfig.emergencyActivatedAt = block.timestamp;
        emergencyConfig.emergencyDuration = duration;
        emergencyConfig.emergencyActivator = msg.sender;
        emergencyConfig.emergencyReason = reason;
        emergencyConfig.maxEmergencyLoanSize = maxLoanSize;

        emit EmergencyModeActivated(msg.sender, reason, duration, block.timestamp);
    }

    function _executeEmergencyDeactivation() internal {
        emergencyConfig.emergencyModeActive = false;

        emit EmergencyModeDeactivated(
            msg.sender,
            totalEmergencyLoansIssued,
            block.timestamp
        );

        // Reset emergency state
        emergencyConfig.emergencyActivatedAt = 0;
        emergencyConfig.emergencyActivator = address(0);
        emergencyConfig.emergencyReason = "";
    }

    function _isEmergencyLoan(address borrower, uint256 amount) internal view returns (bool) {
        // Check if emergency mode is active
        if (!emergencyConfig.emergencyModeActive) return false;

        // Check if emergency mode has expired
        if (block.timestamp > emergencyConfig.emergencyActivatedAt + emergencyConfig.emergencyDuration) {
            return false;
        }

        // Check if borrower is pre-approved for emergency loans
        if (crisisResponse.approvedEmergencyBorrowers[borrower]) return true;

        // Check if amount qualifies as emergency (large loans during crisis)
        if (crisisResponse.crisisLevel >= 3 && amount >= emergencyConfig.maxEmergencyLoanSize / 2) {
            return true;
        }

        return false;
    }

    function _executeEmergencyFlashLoan(
        IERC3156FlashBorrower receiver,
        address token,
        uint256 amount,
        bytes calldata data
    ) internal returns (bool) {
        address borrower = address(receiver);

        // Additional emergency validations
        require(amount <= emergencyConfig.maxEmergencyLoanSize, "Emergency loan amount too large");

        if (crisisResponse.approvedEmergencyBorrowers[borrower]) {
            require(amount <= crisisResponse.emergencyLoanLimits[borrower], "Exceeds emergency limit");
        }

        // Check treasury backing availability
        bool useTreasuryBacking = false;
        if (treasuryPool.treasuryBackingEnabled &&
            treasuryPool.emergencyAllocations[token] >= amount) {
            useTreasuryBacking = true;
        }

        // Calculate emergency fee (reduced fee)
        uint256 standardFee = flashFee(token, amount);
        uint256 emergencyFee = (standardFee * emergencyConfig.emergencyFeeMultiplier) / 10000;
        uint256 totalRepayment = amount + emergencyFee;

        // Execute loan
        uint256 borrowerInitialBalance = IERC20(token).balanceOf(borrower);

        if (useTreasuryBacking) {
            // Use treasury backing
            treasuryPool.emergencyAllocations[token] -= amount;
            totalTreasuryLiquidityUtilized += amount;

            emit TreasuryBackingUtilized(
                token,
                amount,
                treasuryPool.emergencyAllocations[token]
            );
        } else {
            // Check if contract has sufficient balance
            require(IERC20(token).balanceOf(address(this)) >= amount, "Insufficient contract balance");
        }

        // Transfer tokens to borrower
        IERC20(token).safeTransfer(borrower, amount);

        // Call borrower's onFlashLoan function
        bytes32 callbackReturn = receiver.onFlashLoan(msg.sender, token, amount, emergencyFee, data);
        require(callbackReturn == keccak256("ERC3156FlashBorrower.onFlashLoan"), "Invalid callback return");

        // Verify repayment
        uint256 borrowerFinalBalance = IERC20(token).balanceOf(borrower);
        require(
            borrowerFinalBalance >= borrowerInitialBalance + emergencyFee ||
            IERC20(token).allowance(borrower, address(this)) >= totalRepayment,
            "Insufficient emergency loan repayment"
        );

        // Collect repayment
        IERC20(token).safeTransferFrom(borrower, address(this), totalRepayment);

        // Update tracking
        emergencyLoansOutstanding[borrower] += amount;
        lastEmergencyLoanTime[borrower] = block.timestamp;
        totalEmergencyLoansIssued++;

        if (useTreasuryBacking) {
            // Replenish treasury allocation
            treasuryPool.emergencyAllocations[token] += totalRepayment;
            totalTreasuryLiquidityUtilized -= amount;
        }

        emit EmergencyLoanIssued(borrower, token, amount, emergencyFee, useTreasuryBacking);

        return true;
    }

    function _executeStandardFlashLoan(
        IERC3156FlashBorrower receiver,
        address token,
        uint256 amount,
        bytes calldata data
    ) internal returns (bool) {
        // Check if treasury backing can supplement standard loans
        uint256 contractBalance = IERC20(token).balanceOf(address(this));
        bool needsTreasuryBacking = contractBalance < amount &&
                                   treasuryPool.treasuryBackingEnabled &&
                                   treasuryPool.emergencyAllocations[token] >= (amount - contractBalance);

        if (needsTreasuryBacking) {
            uint256 backingNeeded = amount - contractBalance;
            treasuryPool.emergencyAllocations[token] -= backingNeeded;
            totalTreasuryLiquidityUtilized += backingNeeded;
        }

        // Execute standard flash loan
        bool success = super.flashLoan(receiver, token, amount, data);

        if (needsTreasuryBacking && success) {
            // Replenish treasury allocation after successful loan
            uint256 backingNeeded = amount - contractBalance;
            treasuryPool.emergencyAllocations[token] += backingNeeded;
            totalTreasuryLiquidityUtilized -= backingNeeded;
        }

        return success;
    }

    function _adjustCrisisParameters(uint256 crisisLevel) internal {
        if (crisisLevel >= 4) {
            // High crisis - very restrictive
            treasuryPool.maxTreasuryUtilization = 2000; // 20%
            crisisResponse.systemwideUtilizationLimit = 6000; // 60%
            crisisResponse.liquidationProtectionEnabled = true;
        } else if (crisisLevel >= 3) {
            // Medium crisis - restrictive
            treasuryPool.maxTreasuryUtilization = 2500; // 25%
            crisisResponse.systemwideUtilizationLimit = 7000; // 70%
            crisisResponse.liquidationProtectionEnabled = true;
        } else if (crisisLevel >= 2) {
            // Low crisis - cautious
            treasuryPool.maxTreasuryUtilization = 3000; // 30%
            crisisResponse.systemwideUtilizationLimit = 7500; // 75%
            crisisResponse.liquidationProtectionEnabled = false;
        } else {
            // Normal - standard parameters
            treasuryPool.maxTreasuryUtilization = 3000; // 30%
            crisisResponse.systemwideUtilizationLimit = 8000; // 80%
            crisisResponse.liquidationProtectionEnabled = false;
        }
    }

    function _addEmergencySigner(address signer) internal {
        require(signer != address(0), "Invalid signer address");
        require(!emergencyMultiSig.emergencySigners[signer], "Already an emergency signer");

        emergencyMultiSig.emergencySigners[signer] = true;
        emergencyMultiSig.totalSigners++;

        _grantRole(EMERGENCY_COUNCIL_ROLE, signer);
    }

    /**
     * @notice Auto-replenish treasury reserves (daily)
     */
    function autoReplenishTreasury() external {
        require(treasuryPool.autoReplenishEnabled, "Auto-replenish disabled");
        require(block.timestamp >= lastTitheCollection + 86400, "Replenish frequency not met");

        address[] memory tokens = getSupportedTokens();

        for (uint256 i = 0; i < tokens.length; i++) {
            address token = tokens[i];
            uint256 contractBalance = IERC20(token).balanceOf(address(this));
            uint256 targetReserve = treasuryPool.reserveAmounts[token];

            if (contractBalance > targetReserve) {
                uint256 replenishAmount = (contractBalance - targetReserve) *
                                        treasuryPool.treasuryReplenishmentRate / 10000;

                if (replenishAmount > 0) {
                    IERC20(token).safeTransfer(treasuryPool.treasuryContract, replenishAmount);
                }
            }
        }

        lastTitheCollection = block.timestamp;
    }

    /**
     * @notice Check if signer is authorized for emergency multi-sig
     * @param signer Address to check
     * @return isAuthorized Whether signer is authorized
     */
    function isEmergencySigner(address signer) external view returns (bool isAuthorized) {
        return emergencyMultiSig.emergencySigners[signer];
    }

    /**
     * @notice Get emergency multi-sig status
     * @return requiredSigs Required signatures
     * @return totalSigners Total number of signers
     */
    function getEmergencyMultiSigStatus() external view returns (
        uint256 requiredSigs,
        uint256 totalSigners
    ) {
        return (emergencyMultiSig.requiredSignatures, emergencyMultiSig.totalSigners);
    }
}