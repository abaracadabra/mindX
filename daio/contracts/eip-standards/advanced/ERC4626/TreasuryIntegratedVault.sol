// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./DAIO_ERC4626Vault.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title TreasuryIntegratedVault
 * @notice Direct integration with existing Treasury.sol for DAIO ecosystem vaults
 * @dev Extends DAIO_ERC4626Vault with specialized treasury management features
 */
contract TreasuryIntegratedVault is DAIO_ERC4626Vault {

    // Treasury integration specifics
    struct TreasuryIntegration {
        address treasuryContract;           // Existing DAIO Treasury contract
        uint256 projectId;                  // Project ID in treasury system
        bool autoTitheEnabled;              // Whether automatic tithe is enabled
        uint256 minTreasuryReserve;        // Minimum reserve for treasury operations
        uint256 maxTreasuryExposure;       // Maximum exposure to single vault
        uint256 treasuryAllocationTarget;  // Target allocation from treasury
        bool treasuryWithdrawalEnabled;    // Whether treasury can withdraw
    }

    // Multi-project support (as per existing Treasury.sol)
    struct ProjectMetrics {
        string projectName;                 // Project name (e.g., "mindX", "FinancialMind")
        uint256 totalDeposits;             // Total deposits from this project
        uint256 totalWithdrawals;          // Total withdrawals to this project
        uint256 currentBalance;            // Current balance for this project
        uint256 performanceContribution;   // Performance generated for project
        uint256 lastInteractionTime;      // Last interaction timestamp
        bool isActive;                     // Whether project is active
    }

    // Advanced treasury operations
    struct TreasuryOperation {
        uint256 operationId;               // Unique operation ID
        string operationType;              // "DEPOSIT", "WITHDRAW", "REBALANCE", "TITHE"
        uint256 amount;                    // Operation amount
        address initiator;                 // Who initiated the operation
        uint256 executionTime;             // When operation was executed
        bool requiresMultiSig;             // Whether operation needs multi-sig approval
        bool executed;                     // Whether operation was executed
        mapping(address => bool) signerApprovals; // Multi-sig approvals
    }

    // State variables
    TreasuryIntegration public treasuryIntegration;
    mapping(string => ProjectMetrics) public projectMetrics; // project name -> metrics
    mapping(uint256 => TreasuryOperation) public treasuryOperations;
    string[] public activeProjects;

    // Treasury-specific tracking
    uint256 public totalTreasuryDeposits;
    uint256 public totalTreasuryWithdrawals;
    uint256 public nextOperationId = 1;
    uint256 public lastTitheCollection;
    uint256 public cumulativeTitheCollected;

    // Multi-sig configuration for large operations
    uint256 public constant MULTISIG_THRESHOLD = 3;      // Require 3 signatures
    uint256 public constant LARGE_OPERATION_THRESHOLD = 100000 * 1e18; // 100,000 tokens
    mapping(address => bool) public treasurySigners;
    uint256 public signerCount;

    // Events
    event TreasuryDeposit(
        string indexed projectName,
        uint256 amount,
        uint256 shares,
        address indexed depositor
    );
    event TreasuryWithdrawal(
        string indexed projectName,
        uint256 amount,
        uint256 shares,
        address indexed recipient
    );
    event TitheCollected(
        uint256 amount,
        uint256 timestamp,
        string reason
    );
    event TreasuryOperationCreated(
        uint256 indexed operationId,
        string operationType,
        uint256 amount,
        address indexed initiator
    );
    event TreasuryOperationExecuted(
        uint256 indexed operationId,
        bool success,
        uint256 timestamp
    );
    event ProjectActivated(
        string indexed projectName,
        uint256 initialDeposit
    );
    event ProjectDeactivated(
        string indexed projectName,
        string reason
    );
    event MultiSigSignerAdded(address indexed signer);
    event MultiSigApprovalGiven(
        uint256 indexed operationId,
        address indexed signer
    );

    /**
     * @notice Initialize TreasuryIntegratedVault
     * @param _asset Underlying asset token
     * @param _name Vault token name
     * @param _symbol Vault token symbol
     * @param _treasuryContract Existing DAIO Treasury contract
     * @param _constitutionContract DAIO Constitution contract
     * @param _projectId Project ID in treasury system
     * @param admin Admin address
     */
    constructor(
        IERC20 _asset,
        string memory _name,
        string memory _symbol,
        address _treasuryContract,
        address _constitutionContract,
        uint256 _projectId,
        address admin
    ) DAIO_ERC4626Vault(
        _asset,
        _name,
        _symbol,
        _treasuryContract,
        _constitutionContract,
        admin
    ) {
        require(_treasuryContract != address(0), "Treasury contract cannot be zero address");

        treasuryIntegration = TreasuryIntegration({
            treasuryContract: _treasuryContract,
            projectId: _projectId,
            autoTitheEnabled: true,
            minTreasuryReserve: 1000000 * 1e18,      // 1M token minimum reserve
            maxTreasuryExposure: 25000000 * 1e18,    // 25M token maximum exposure
            treasuryAllocationTarget: 10000000 * 1e18, // 10M token target allocation
            treasuryWithdrawalEnabled: true
        });

        // Initialize default projects (mindX, FinancialMind, cryptoAGI)
        _initializeDefaultProjects();

        // Set up initial multi-sig signers
        _addTreasurySigner(admin);

        lastTitheCollection = block.timestamp;
    }

    /**
     * @notice Treasury deposit with project allocation
     * @param projectName Project name for allocation tracking
     * @param assets Amount of assets to deposit
     * @param receiver Address to receive shares
     * @return shares Amount of shares minted
     */
    function treasuryDeposit(
        string memory projectName,
        uint256 assets,
        address receiver
    ) external onlyRole(TREASURY_ROLE) nonReentrant whenNotPaused returns (uint256 shares) {
        require(bytes(projectName).length > 0, "Project name cannot be empty");
        require(assets > 0, "Cannot deposit zero assets");

        // Ensure project is active or activate it
        if (!projectMetrics[projectName].isActive) {
            _activateProject(projectName);
        }

        // Check treasury exposure limits
        require(
            totalTreasuryDeposits + assets <= treasuryIntegration.maxTreasuryExposure,
            "Exceeds treasury exposure limit"
        );

        // Execute the deposit through parent contract
        shares = deposit(assets, receiver);

        // Update treasury-specific tracking
        ProjectMetrics storage project = projectMetrics[projectName];
        project.totalDeposits += assets;
        project.currentBalance += assets;
        project.lastInteractionTime = block.timestamp;

        totalTreasuryDeposits += assets;

        // Create treasury operation record
        uint256 operationId = _createTreasuryOperation(
            "DEPOSIT",
            assets,
            msg.sender,
            false // Normal deposits don't require multi-sig
        );

        _executeTreasuryOperation(operationId);

        emit TreasuryDeposit(projectName, assets, shares, receiver);

        return shares;
    }

    /**
     * @notice Treasury withdrawal with project tracking
     * @param projectName Project name for withdrawal tracking
     * @param assets Amount of assets to withdraw
     * @param receiver Address to receive assets
     * @return shares Amount of shares burned
     */
    function treasuryWithdraw(
        string memory projectName,
        uint256 assets,
        address receiver
    ) external onlyRole(TREASURY_ROLE) nonReentrant returns (uint256 shares) {
        require(treasuryIntegration.treasuryWithdrawalEnabled, "Treasury withdrawal disabled");
        require(bytes(projectName).length > 0, "Project name cannot be empty");
        require(projectMetrics[projectName].isActive, "Project not active");

        // Check minimum reserve requirements
        uint256 remainingAssets = totalAssets() - assets;
        require(
            remainingAssets >= treasuryIntegration.minTreasuryReserve,
            "Would violate minimum treasury reserve"
        );

        // Check if operation requires multi-sig
        bool requiresMultiSig = assets >= LARGE_OPERATION_THRESHOLD;

        if (requiresMultiSig) {
            // Create operation for multi-sig approval
            uint256 operationId = _createTreasuryOperation(
                "WITHDRAW",
                assets,
                msg.sender,
                true
            );

            // Require multi-sig approval before execution
            require(_hasMultiSigApproval(operationId), "Multi-sig approval required");
            _executeTreasuryOperation(operationId);
        }

        // Calculate shares needed for withdrawal
        shares = previewWithdraw(assets);

        // Execute the withdrawal through parent contract
        uint256 actualAssets = withdraw(assets, receiver, address(this));

        // Update treasury-specific tracking
        ProjectMetrics storage project = projectMetrics[projectName];
        project.totalWithdrawals += actualAssets;
        project.currentBalance -= actualAssets;
        project.lastInteractionTime = block.timestamp;

        totalTreasuryWithdrawals += actualAssets;

        emit TreasuryWithdrawal(projectName, actualAssets, shares, receiver);

        return shares;
    }

    /**
     * @notice Automatic tithe collection (15% constitutional requirement)
     */
    function collectTithe() external nonReentrant {
        require(
            block.timestamp >= lastTitheCollection + 86400, // Daily collection
            "Tithe collection too frequent"
        );

        uint256 currentAssets = totalAssets();
        uint256 titheAmount = _calculateTitheAmount(currentAssets);

        if (titheAmount > 0 && treasuryIntegration.autoTitheEnabled) {
            // Create tithe operation
            uint256 operationId = _createTreasuryOperation(
                "TITHE",
                titheAmount,
                msg.sender,
                false // Tithe doesn't require multi-sig
            );

            // Transfer tithe to treasury
            asset.safeTransfer(treasuryIntegration.treasuryContract, titheAmount);

            cumulativeTitheCollected += titheAmount;
            lastTitheCollection = block.timestamp;

            _executeTreasuryOperation(operationId);

            emit TitheCollected(titheAmount, block.timestamp, "Automatic constitutional tithe");
        }
    }

    /**
     * @notice Rebalance vault allocation across projects
     * @param projectAllocations Array of project names
     * @param targetAllocations Array of target allocation percentages (BPS)
     */
    function rebalanceProjectAllocations(
        string[] memory projectAllocations,
        uint256[] memory targetAllocations
    ) external onlyRole(VAULT_MANAGER_ROLE) {
        require(projectAllocations.length == targetAllocations.length, "Array length mismatch");

        uint256 totalAllocation = 0;
        for (uint256 i = 0; i < targetAllocations.length; i++) {
            totalAllocation += targetAllocations[i];
        }
        require(totalAllocation <= 10000, "Total allocation exceeds 100%");

        uint256 currentAssets = totalAssets();

        for (uint256 i = 0; i < projectAllocations.length; i++) {
            string memory projectName = projectAllocations[i];
            uint256 targetAllocation = targetAllocations[i];

            if (!projectMetrics[projectName].isActive) {
                _activateProject(projectName);
            }

            uint256 targetBalance = (currentAssets * targetAllocation) / 10000;
            ProjectMetrics storage project = projectMetrics[projectName];

            project.currentBalance = targetBalance;
            project.lastInteractionTime = block.timestamp;
        }

        // Create rebalance operation
        uint256 operationId = _createTreasuryOperation(
            "REBALANCE",
            currentAssets,
            msg.sender,
            true // Rebalancing requires multi-sig
        );

        _executeTreasuryOperation(operationId);
    }

    /**
     * @notice Multi-sig approval for treasury operations
     * @param operationId Operation ID to approve
     */
    function approveTreasuryOperation(uint256 operationId) external {
        require(treasurySigners[msg.sender], "Not authorized signer");
        require(treasuryOperations[operationId].operationId != 0, "Operation does not exist");
        require(!treasuryOperations[operationId].executed, "Operation already executed");

        TreasuryOperation storage operation = treasuryOperations[operationId];
        operation.signerApprovals[msg.sender] = true;

        emit MultiSigApprovalGiven(operationId, msg.sender);

        // Auto-execute if enough approvals
        if (_hasMultiSigApproval(operationId)) {
            _executeTreasuryOperation(operationId);
        }
    }

    /**
     * @notice Get project metrics
     * @param projectName Project name
     * @return metrics Project performance metrics
     */
    function getProjectMetrics(string memory projectName) external view returns (ProjectMetrics memory metrics) {
        return projectMetrics[projectName];
    }

    /**
     * @notice Get treasury integration status
     * @return integration Treasury integration configuration
     */
    function getTreasuryIntegration() external view returns (TreasuryIntegration memory integration) {
        return treasuryIntegration;
    }

    /**
     * @notice Get all active projects
     * @return projects Array of active project names
     */
    function getActiveProjects() external view returns (string[] memory projects) {
        return activeProjects;
    }

    /**
     * @notice Add treasury signer for multi-sig operations
     * @param signer Address to add as signer
     */
    function addTreasurySigner(address signer) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _addTreasurySigner(signer);
    }

    /**
     * @notice Remove treasury signer
     * @param signer Address to remove as signer
     */
    function removeTreasurySigner(address signer) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(treasurySigners[signer], "Not a signer");
        require(signerCount > MULTISIG_THRESHOLD, "Cannot remove - would break multi-sig");

        treasurySigners[signer] = false;
        signerCount--;
    }

    /**
     * @notice Update treasury integration settings
     * @param autoTitheEnabled Whether automatic tithe is enabled
     * @param minTreasuryReserve Minimum treasury reserve
     * @param maxTreasuryExposure Maximum treasury exposure
     * @param treasuryWithdrawalEnabled Whether treasury withdrawals are enabled
     */
    function updateTreasuryIntegration(
        bool autoTitheEnabled,
        uint256 minTreasuryReserve,
        uint256 maxTreasuryExposure,
        bool treasuryWithdrawalEnabled
    ) external onlyRole(VAULT_MANAGER_ROLE) {
        treasuryIntegration.autoTitheEnabled = autoTitheEnabled;
        treasuryIntegration.minTreasuryReserve = minTreasuryReserve;
        treasuryIntegration.maxTreasuryExposure = maxTreasuryExposure;
        treasuryIntegration.treasuryWithdrawalEnabled = treasuryWithdrawalEnabled;
    }

    // Internal Functions

    function _initializeDefaultProjects() internal {
        // mindX project
        projectMetrics["mindX"] = ProjectMetrics({
            projectName: "mindX",
            totalDeposits: 0,
            totalWithdrawals: 0,
            currentBalance: 0,
            performanceContribution: 0,
            lastInteractionTime: block.timestamp,
            isActive: true
        });

        // FinancialMind project
        projectMetrics["FinancialMind"] = ProjectMetrics({
            projectName: "FinancialMind",
            totalDeposits: 0,
            totalWithdrawals: 0,
            currentBalance: 0,
            performanceContribution: 0,
            lastInteractionTime: block.timestamp,
            isActive: true
        });

        // cryptoAGI project
        projectMetrics["cryptoAGI"] = ProjectMetrics({
            projectName: "cryptoAGI",
            totalDeposits: 0,
            totalWithdrawals: 0,
            currentBalance: 0,
            performanceContribution: 0,
            lastInteractionTime: block.timestamp,
            isActive: true
        });

        activeProjects.push("mindX");
        activeProjects.push("FinancialMind");
        activeProjects.push("cryptoAGI");
    }

    function _activateProject(string memory projectName) internal {
        require(!projectMetrics[projectName].isActive, "Project already active");

        projectMetrics[projectName] = ProjectMetrics({
            projectName: projectName,
            totalDeposits: 0,
            totalWithdrawals: 0,
            currentBalance: 0,
            performanceContribution: 0,
            lastInteractionTime: block.timestamp,
            isActive: true
        });

        activeProjects.push(projectName);

        emit ProjectActivated(projectName, 0);
    }

    function _createTreasuryOperation(
        string memory operationType,
        uint256 amount,
        address initiator,
        bool requiresMultiSig
    ) internal returns (uint256 operationId) {
        operationId = nextOperationId++;

        TreasuryOperation storage operation = treasuryOperations[operationId];
        operation.operationId = operationId;
        operation.operationType = operationType;
        operation.amount = amount;
        operation.initiator = initiator;
        operation.executionTime = block.timestamp;
        operation.requiresMultiSig = requiresMultiSig;
        operation.executed = false;

        emit TreasuryOperationCreated(operationId, operationType, amount, initiator);

        return operationId;
    }

    function _executeTreasuryOperation(uint256 operationId) internal {
        TreasuryOperation storage operation = treasuryOperations[operationId];
        require(!operation.executed, "Operation already executed");

        if (operation.requiresMultiSig) {
            require(_hasMultiSigApproval(operationId), "Insufficient multi-sig approvals");
        }

        operation.executed = true;
        operation.executionTime = block.timestamp;

        emit TreasuryOperationExecuted(operationId, true, block.timestamp);
    }

    function _hasMultiSigApproval(uint256 operationId) internal view returns (bool) {
        TreasuryOperation storage operation = treasuryOperations[operationId];
        if (!operation.requiresMultiSig) return true;

        uint256 approvalCount = 0;
        // In a real implementation, we'd iterate through all signers
        // For now, just check if threshold is met conceptually
        return approvalCount >= MULTISIG_THRESHOLD;
    }

    function _addTreasurySigner(address signer) internal {
        require(signer != address(0), "Invalid signer address");
        require(!treasurySigners[signer], "Already a signer");

        treasurySigners[signer] = true;
        signerCount++;

        emit MultiSigSignerAdded(signer);
    }

    function _calculateTitheAmount(uint256 totalAssets_) internal view returns (uint256) {
        // Calculate 15% tithe on growth since last collection
        uint256 timeSinceLastTithe = block.timestamp - lastTitheCollection;
        if (timeSinceLastTithe == 0) return 0;

        // Simple growth calculation - in production would be more sophisticated
        uint256 estimatedGrowth = (totalAssets_ * timeSinceLastTithe) / (365 days);
        return (estimatedGrowth * 1500) / 10000; // 15% of estimated growth
    }

    /**
     * @notice Override deposit to include treasury tracking
     */
    function deposit(
        uint256 assets,
        address receiver
    ) public override returns (uint256 shares) {
        shares = super.deposit(assets, receiver);

        // Update treasury-specific performance tracking
        _updateTreasuryPerformanceMetrics();

        return shares;
    }

    /**
     * @notice Override withdraw to include treasury tracking
     */
    function withdraw(
        uint256 assets,
        address receiver,
        address owner
    ) public override returns (uint256 shares) {
        shares = super.withdraw(assets, receiver, owner);

        // Update treasury-specific performance tracking
        _updateTreasuryPerformanceMetrics();

        return shares;
    }

    function _updateTreasuryPerformanceMetrics() internal {
        uint256 currentTotalAssets = totalAssets();

        // Update performance contribution for each active project
        for (uint256 i = 0; i < activeProjects.length; i++) {
            string memory projectName = activeProjects[i];
            ProjectMetrics storage project = projectMetrics[projectName];

            if (project.isActive && project.currentBalance > 0) {
                // Calculate proportional performance contribution
                uint256 projectShare = (project.currentBalance * 10000) / currentTotalAssets;
                uint256 currentPeriodReturn = uint256(performanceMetrics.currentPeriodReturn);

                if (performanceMetrics.currentPeriodReturn > 0) {
                    project.performanceContribution += (currentPeriodReturn * projectShare) / 10000;
                }
            }
        }
    }

    /**
     * @notice Emergency treasury withdrawal (admin only)
     * @param amount Amount to withdraw to treasury
     * @param reason Reason for emergency withdrawal
     */
    function emergencyTreasuryWithdrawal(
        uint256 amount,
        string memory reason
    ) external onlyRole(EMERGENCY_ROLE) {
        require(amount <= totalAssets(), "Insufficient assets");

        asset.safeTransfer(treasuryIntegration.treasuryContract, amount);

        uint256 operationId = _createTreasuryOperation(
            "EMERGENCY_WITHDRAW",
            amount,
            msg.sender,
            false // Emergency doesn't require multi-sig
        );

        _executeTreasuryOperation(operationId);

        emit TitheCollected(amount, block.timestamp, reason);
    }

    /**
     * @notice Get treasury operation details
     * @param operationId Operation ID
     * @return operationType Type of operation
     * @return amount Operation amount
     * @return initiator Who initiated the operation
     * @return executed Whether operation was executed
     */
    function getTreasuryOperation(uint256 operationId) external view returns (
        string memory operationType,
        uint256 amount,
        address initiator,
        bool executed
    ) {
        TreasuryOperation storage operation = treasuryOperations[operationId];
        return (
            operation.operationType,
            operation.amount,
            operation.initiator,
            operation.executed
        );
    }
}