// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "./Treasury.sol";

/**
 * @title TreasuryFeeCollector
 * @notice Automated fee collection and gas cost coverage for DAIO operations
 * @dev Manages fee collection from proposals and distributes to treasury and operational costs
 */
contract TreasuryFeeCollector is AccessControl, ReentrancyGuard {

    bytes32 public constant FEE_COLLECTOR_ROLE = keccak256("FEE_COLLECTOR_ROLE");
    bytes32 public constant TREASURY_MANAGER_ROLE = keccak256("TREASURY_MANAGER_ROLE");
    bytes32 public constant GAS_REFUNDER_ROLE = keccak256("GAS_REFUNDER_ROLE");

    enum FeeType {
        PROPOSAL_FEE,       // Proposal submission fees
        BRANCH_CREATION,    // Branch creation fees
        CONFIGURATION,      // Configuration change fees
        AI_PROPOSAL,        // AI proposal fees (spam prevention)
        COMPETITION_POOL,   // Competition pool treasury share
        GAS_REFUND,         // Gas cost coverage
        EMERGENCY_FEE       // Emergency action fees
    }

    struct FeeSchedule {
        uint256 baseAmount;     // Base fee amount in wei
        uint256 percentage;     // Percentage fee (for percentage-based fees)
        bool isPercentageBased; // Whether this is percentage or fixed amount
        uint256 minAmount;      // Minimum fee amount
        uint256 maxAmount;      // Maximum fee amount
        bool active;            // Whether this fee type is active
        uint256 lastUpdated;    // Last update timestamp
    }

    struct FeeCollection {
        uint256 collectionId;
        FeeType feeType;
        uint256 amount;
        address payer;
        uint256 timestamp;
        string purpose;         // Description of fee purpose
        uint256 referenceId;    // Reference to proposal/operation ID
        bool processed;         // Whether fee has been processed
    }

    struct GasRefund {
        address recipient;
        uint256 gasUsed;
        uint256 gasPrice;
        uint256 refundAmount;
        uint256 timestamp;
        string operation;       // Description of operation
        bool processed;
    }

    struct TreasuryAllocation {
        uint256 operationalReserve;  // Reserve for gas costs and operations
        uint256 treasuryShare;       // Amount allocated to main treasury
        uint256 emergencyReserve;    // Emergency fund reserve
        uint256 lastAllocation;      // Last allocation timestamp
    }

    // Storage
    mapping(FeeType => FeeSchedule) public feeSchedules;
    mapping(uint256 => FeeCollection) public feeCollections;
    mapping(uint256 => GasRefund) public gasRefunds;
    mapping(address => uint256) public totalFeesCollectedFrom;
    mapping(address => uint256) public totalGasRefunded;
    mapping(FeeType => uint256) public totalCollectedByType;

    uint256 public collectionCount;
    uint256 public refundCount;
    uint256 public totalFeesCollected;
    uint256 public totalGasRefundedGlobal;
    uint256 public operationalBalance;
    uint256 public emergencyReserve;

    TreasuryAllocation public allocation;

    // Configuration
    uint256 public constant BASIS_POINTS = 10000;
    uint256 public treasuryAllocationPercentage = 6000;    // 60% to treasury
    uint256 public operationalReservePercentage = 3000;    // 30% to operations
    uint256 public emergencyReservePercentage = 1000;      // 10% to emergency

    uint256 public maxGasRefundPerTx = 0.1 ether;         // Maximum gas refund per transaction
    uint256 public gasBufferMultiplier = 110;              // 110% of actual gas cost
    uint256 public minOperationalReserve = 10 ether;       // Minimum operational reserve

    Treasury public treasury;

    // Events
    event FeeCollected(
        uint256 indexed collectionId,
        FeeType indexed feeType,
        address indexed payer,
        uint256 amount,
        string purpose
    );

    event FeeScheduleUpdated(
        FeeType indexed feeType,
        uint256 baseAmount,
        uint256 percentage,
        bool isPercentageBased
    );

    event GasRefundProcessed(
        uint256 indexed refundId,
        address indexed recipient,
        uint256 gasUsed,
        uint256 refundAmount,
        string operation
    );

    event TreasuryAllocationProcessed(
        uint256 treasuryAmount,
        uint256 operationalAmount,
        uint256 emergencyAmount,
        uint256 timestamp
    );

    event EmergencyWithdrawal(
        address indexed recipient,
        uint256 amount,
        string reason
    );

    event OperationalReserveLow(
        uint256 currentReserve,
        uint256 requiredMinimum,
        uint256 timestamp
    );

    modifier onlyFeeCollector() {
        require(hasRole(FEE_COLLECTOR_ROLE, msg.sender), "Not fee collector");
        _;
    }

    modifier onlyTreasuryManager() {
        require(hasRole(TREASURY_MANAGER_ROLE, msg.sender), "Not treasury manager");
        _;
    }

    modifier onlyGasRefunder() {
        require(hasRole(GAS_REFUNDER_ROLE, msg.sender), "Not gas refunder");
        _;
    }

    constructor(address _treasury) {
        require(_treasury != address(0), "Invalid treasury address");

        treasury = Treasury(payable(_treasury));

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(FEE_COLLECTOR_ROLE, msg.sender);
        _grantRole(TREASURY_MANAGER_ROLE, msg.sender);
        _grantRole(GAS_REFUNDER_ROLE, msg.sender);

        _initializeFeeSchedule();
    }

    /**
     * @notice Collect fee with automatic categorization
     * @param purpose Description of fee purpose
     * @param referenceId Reference ID (proposal, operation, etc.)
     * @return collectionId Fee collection ID
     */
    function collectFee(
        string memory purpose,
        uint256 referenceId
    ) external payable onlyFeeCollector returns (uint256 collectionId) {
        require(msg.value > 0, "Fee amount must be greater than 0");

        collectionCount++;

        // Auto-determine fee type based on purpose (simplified logic)
        FeeType feeType = _determineFeeType(purpose);

        feeCollections[collectionCount] = FeeCollection({
            collectionId: collectionCount,
            feeType: feeType,
            amount: msg.value,
            payer: msg.sender,
            timestamp: block.timestamp,
            purpose: purpose,
            referenceId: referenceId,
            processed: false
        });

        totalFeesCollected += msg.value;
        totalFeesCollectedFrom[msg.sender] += msg.value;
        totalCollectedByType[feeType] += msg.value;

        emit FeeCollected(collectionCount, feeType, msg.sender, msg.value, purpose);

        _processAllocation(msg.value);

        return collectionCount;
    }

    /**
     * @notice Collect fee with explicit type specification
     * @param feeType Type of fee being collected
     * @param purpose Description of fee purpose
     * @param referenceId Reference ID
     * @return collectionId Fee collection ID
     */
    function collectTypedFee(
        FeeType feeType,
        string memory purpose,
        uint256 referenceId
    ) external payable onlyFeeCollector returns (uint256 collectionId) {
        require(msg.value > 0, "Fee amount must be greater than 0");
        require(feeSchedules[feeType].active, "Fee type not active");

        // Validate fee amount against schedule
        FeeSchedule memory schedule = feeSchedules[feeType];
        if (schedule.isPercentageBased) {
            require(msg.value >= schedule.minAmount && msg.value <= schedule.maxAmount, "Fee amount out of range");
        } else {
            require(msg.value >= schedule.baseAmount, "Fee amount below minimum");
        }

        collectionCount++;

        feeCollections[collectionCount] = FeeCollection({
            collectionId: collectionCount,
            feeType: feeType,
            amount: msg.value,
            payer: msg.sender,
            timestamp: block.timestamp,
            purpose: purpose,
            referenceId: referenceId,
            processed: false
        });

        totalFeesCollected += msg.value;
        totalFeesCollectedFrom[msg.sender] += msg.value;
        totalCollectedByType[feeType] += msg.value;

        emit FeeCollected(collectionCount, feeType, msg.sender, msg.value, purpose);

        _processAllocation(msg.value);

        return collectionCount;
    }

    /**
     * @notice Process gas refund for operation
     * @param recipient Address to receive refund
     * @param gasUsed Amount of gas used
     * @param operation Description of operation
     */
    function processGasRefund(
        address recipient,
        uint256 gasUsed,
        string memory operation
    ) external onlyGasRefunder nonReentrant {
        require(recipient != address(0), "Invalid recipient");
        require(gasUsed > 0, "Gas used must be positive");

        uint256 gasPrice = tx.gasprice;
        uint256 refundAmount = (gasUsed * gasPrice * gasBufferMultiplier) / 100;

        // Cap refund amount
        if (refundAmount > maxGasRefundPerTx) {
            refundAmount = maxGasRefundPerTx;
        }

        require(operationalBalance >= refundAmount, "Insufficient operational reserve");
        require(operationalBalance - refundAmount >= minOperationalReserve, "Would breach minimum reserve");

        refundCount++;

        gasRefunds[refundCount] = GasRefund({
            recipient: recipient,
            gasUsed: gasUsed,
            gasPrice: gasPrice,
            refundAmount: refundAmount,
            timestamp: block.timestamp,
            operation: operation,
            processed: true
        });

        operationalBalance -= refundAmount;
        totalGasRefundedGlobal += refundAmount;
        totalGasRefunded[recipient] += refundAmount;

        payable(recipient).transfer(refundAmount);

        emit GasRefundProcessed(refundCount, recipient, gasUsed, refundAmount, operation);

        // Check if operational reserve is getting low
        if (operationalBalance < minOperationalReserve * 2) {
            emit OperationalReserveLow(operationalBalance, minOperationalReserve, block.timestamp);
        }
    }

    /**
     * @notice Calculate required fee for operation
     * @param feeType Type of fee
     * @param value Value for percentage-based fees
     * @return feeAmount Required fee amount
     */
    function calculateFee(FeeType feeType, uint256 value) external view returns (uint256 feeAmount) {
        FeeSchedule memory schedule = feeSchedules[feeType];
        require(schedule.active, "Fee type not active");

        if (schedule.isPercentageBased) {
            feeAmount = (value * schedule.percentage) / BASIS_POINTS;
            if (feeAmount < schedule.minAmount) {
                feeAmount = schedule.minAmount;
            }
            if (feeAmount > schedule.maxAmount) {
                feeAmount = schedule.maxAmount;
            }
        } else {
            feeAmount = schedule.baseAmount;
        }
    }

    /**
     * @notice Estimate gas cost for operation
     * @param estimatedGas Estimated gas usage
     * @return estimatedCost Estimated cost in wei
     */
    function estimateGasCost(uint256 estimatedGas) external view returns (uint256 estimatedCost) {
        uint256 gasPrice = tx.gasprice > 0 ? tx.gasprice : 20 gwei; // Fallback gas price
        estimatedCost = (estimatedGas * gasPrice * gasBufferMultiplier) / 100;

        if (estimatedCost > maxGasRefundPerTx) {
            estimatedCost = maxGasRefundPerTx;
        }
    }

    /**
     * @notice Update fee schedule for specific fee type
     * @param feeType Type of fee
     * @param baseAmount Base fee amount
     * @param percentage Percentage for percentage-based fees
     * @param isPercentageBased Whether fee is percentage-based
     * @param minAmount Minimum fee amount
     * @param maxAmount Maximum fee amount
     */
    function updateFeeSchedule(
        FeeType feeType,
        uint256 baseAmount,
        uint256 percentage,
        bool isPercentageBased,
        uint256 minAmount,
        uint256 maxAmount
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(minAmount <= maxAmount, "Invalid amount range");
        if (isPercentageBased) {
            require(percentage <= BASIS_POINTS, "Percentage too high");
        }

        feeSchedules[feeType] = FeeSchedule({
            baseAmount: baseAmount,
            percentage: percentage,
            isPercentageBased: isPercentageBased,
            minAmount: minAmount,
            maxAmount: maxAmount,
            active: true,
            lastUpdated: block.timestamp
        });

        emit FeeScheduleUpdated(feeType, baseAmount, percentage, isPercentageBased);
    }

    /**
     * @notice Update allocation percentages
     * @param treasuryPercent Percentage to treasury
     * @param operationalPercent Percentage to operational reserve
     * @param emergencyPercent Percentage to emergency reserve
     */
    function updateAllocationPercentages(
        uint256 treasuryPercent,
        uint256 operationalPercent,
        uint256 emergencyPercent
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(treasuryPercent + operationalPercent + emergencyPercent == BASIS_POINTS, "Percentages must sum to 100%");

        treasuryAllocationPercentage = treasuryPercent;
        operationalReservePercentage = operationalPercent;
        emergencyReservePercentage = emergencyPercent;
    }

    /**
     * @notice Transfer treasury share to main treasury
     */
    function transferToTreasury() external onlyTreasuryManager nonReentrant {
        uint256 treasuryShare = allocation.treasuryShare;
        require(treasuryShare > 0, "No treasury share to transfer");

        allocation.treasuryShare = 0;
        allocation.lastAllocation = block.timestamp;

        // Transfer to treasury contract
        payable(address(treasury)).transfer(treasuryShare);
    }

    /**
     * @notice Emergency withdrawal from reserves
     * @param amount Amount to withdraw
     * @param reason Reason for emergency withdrawal
     */
    function emergencyWithdraw(
        uint256 amount,
        string memory reason
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(amount <= emergencyReserve, "Insufficient emergency reserve");
        require(bytes(reason).length > 0, "Reason required");

        emergencyReserve -= amount;
        payable(msg.sender).transfer(amount);

        emit EmergencyWithdrawal(msg.sender, amount, reason);
    }

    /**
     * @notice Get fee collection details
     * @param collectionId Collection ID
     * @return Fee collection details
     */
    function getFeeCollection(uint256 collectionId) external view returns (FeeCollection memory) {
        return feeCollections[collectionId];
    }

    /**
     * @notice Get gas refund details
     * @param refundId Refund ID
     * @return Gas refund details
     */
    function getGasRefund(uint256 refundId) external view returns (GasRefund memory) {
        return gasRefunds[refundId];
    }

    /**
     * @notice Get fee schedule for type
     * @param feeType Fee type
     * @return Fee schedule details
     */
    function getFeeSchedule(FeeType feeType) external view returns (FeeSchedule memory) {
        return feeSchedules[feeType];
    }

    /**
     * @notice Get treasury allocation details
     * @return Treasury allocation structure
     */
    function getTreasuryAllocation() external view returns (TreasuryAllocation memory) {
        return allocation;
    }

    /**
     * @notice Get contract balance and reserves
     * @return totalBalance Total contract balance
     * @return operationalReserve Operational reserve amount
     * @return treasuryPending Treasury pending transfer
     * @return emergencyFund Emergency fund amount
     */
    function getBalanceBreakdown() external view returns (
        uint256 totalBalance,
        uint256 operationalReserve,
        uint256 treasuryPending,
        uint256 emergencyFund
    ) {
        return (
            address(this).balance,
            operationalBalance,
            allocation.treasuryShare,
            emergencyReserve
        );
    }

    /**
     * @notice Initialize fee schedule with default values
     */
    function _initializeFeeSchedule() internal {
        // Proposal fees: 0.1-1 ETH
        feeSchedules[FeeType.PROPOSAL_FEE] = FeeSchedule({
            baseAmount: 0.1 ether,
            percentage: 0,
            isPercentageBased: false,
            minAmount: 0.1 ether,
            maxAmount: 1 ether,
            active: true,
            lastUpdated: block.timestamp
        });

        // Branch creation fees: 5-50 ETH
        feeSchedules[FeeType.BRANCH_CREATION] = FeeSchedule({
            baseAmount: 5 ether,
            percentage: 0,
            isPercentageBased: false,
            minAmount: 5 ether,
            maxAmount: 50 ether,
            active: true,
            lastUpdated: block.timestamp
        });

        // Configuration fees: 0.01-0.5 ETH
        feeSchedules[FeeType.CONFIGURATION] = FeeSchedule({
            baseAmount: 0.01 ether,
            percentage: 0,
            isPercentageBased: false,
            minAmount: 0.01 ether,
            maxAmount: 0.5 ether,
            active: true,
            lastUpdated: block.timestamp
        });

        // AI proposal fees: 0.01 ETH (spam prevention)
        feeSchedules[FeeType.AI_PROPOSAL] = FeeSchedule({
            baseAmount: 0.01 ether,
            percentage: 0,
            isPercentageBased: false,
            minAmount: 0.01 ether,
            maxAmount: 0.01 ether,
            active: true,
            lastUpdated: block.timestamp
        });

        // Competition pool: 20% of pool
        feeSchedules[FeeType.COMPETITION_POOL] = FeeSchedule({
            baseAmount: 0,
            percentage: 2000, // 20%
            isPercentageBased: true,
            minAmount: 0.01 ether,
            maxAmount: 100 ether,
            active: true,
            lastUpdated: block.timestamp
        });
    }

    /**
     * @notice Process fee allocation to different buckets
     * @param amount Amount to allocate
     */
    function _processAllocation(uint256 amount) internal {
        uint256 treasuryAmount = (amount * treasuryAllocationPercentage) / BASIS_POINTS;
        uint256 operationalAmount = (amount * operationalReservePercentage) / BASIS_POINTS;
        uint256 emergencyAmount = (amount * emergencyReservePercentage) / BASIS_POINTS;

        allocation.treasuryShare += treasuryAmount;
        operationalBalance += operationalAmount;
        emergencyReserve += emergencyAmount;

        emit TreasuryAllocationProcessed(treasuryAmount, operationalAmount, emergencyAmount, block.timestamp);
    }

    /**
     * @notice Determine fee type from purpose string
     * @param purpose Purpose description
     * @return Determined fee type
     */
    function _determineFeeType(string memory purpose) internal pure returns (FeeType) {
        bytes32 purposeHash = keccak256(abi.encodePacked(purpose));

        if (purposeHash == keccak256("branch_creation") || purposeHash == keccak256("arm_deployment")) {
            return FeeType.BRANCH_CREATION;
        } else if (purposeHash == keccak256("ai_proposal") || purposeHash == keccak256("agent_proposal")) {
            return FeeType.AI_PROPOSAL;
        } else if (purposeHash == keccak256("configuration_change") || purposeHash == keccak256("parameter_update")) {
            return FeeType.CONFIGURATION;
        } else if (purposeHash == keccak256("competition_treasury_fee")) {
            return FeeType.COMPETITION_POOL;
        } else if (purposeHash == keccak256("emergency_action")) {
            return FeeType.EMERGENCY_FEE;
        }

        return FeeType.PROPOSAL_FEE; // Default
    }

    /**
     * @notice Receive function to accept ETH
     */
    receive() external payable {
        // Accept ETH transfers
    }
}