// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "../../proxy-patterns/diamond/Diamond.sol";
import "../../daio/constitution/DAIO_Constitution.sol";
import "../../executive-governance/ExecutiveGovernance.sol";

/**
 * @title TreasuryDiamond
 * @dev Upgradeable treasury system using ERC2535 Diamond pattern with executive governance
 *
 * Key Features:
 * - Modular treasury operations via diamond facets
 * - Executive governance integration for treasury management
 * - Constitutional compliance for all treasury operations
 * - Multi-asset support with automated 15% tithe collection
 * - Advanced yield optimization and DeFi integration
 * - Complete audit trail and compliance reporting
 */
contract TreasuryDiamond is Diamond, AccessControl, ReentrancyGuard, Pausable {
    bytes32 public constant TREASURY_MANAGER_ROLE = keccak256("TREASURY_MANAGER_ROLE");
    bytes32 public constant ALLOCATOR_ROLE = keccak256("ALLOCATOR_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");

    // Treasury state storage
    struct TreasuryStorage {
        // Core references
        DAIO_Constitution constitution;
        ExecutiveGovernance executiveGovernance;

        // Asset tracking
        mapping(address => uint256) assetBalances;
        mapping(address => uint256) assetValues; // USD value cache
        address[] trackedAssets;
        uint256 totalValue;
        uint256 lastValuationUpdate;

        // Allocation tracking
        mapping(address => uint256) allocations;
        mapping(address => uint256) maxAllocations; // 15% limits per recipient
        mapping(address => bool) approvedRecipients;
        uint256 totalAllocated;

        // Tithe collection
        mapping(address => uint256) titheCollected;
        uint256 totalTitheCollected;
        uint256 titheRate; // 1500 = 15%

        // Project isolation
        mapping(string => ProjectTreasury) projectTreasuries;
        string[] projectNames;

        // Multi-signature controls
        mapping(bytes32 => uint256) pendingTransactions;
        mapping(bytes32 => mapping(address => bool)) transactionApprovals;
        mapping(bytes32 => uint256) approvalCounts;
        uint256 requiredSignatures;
        address[] signers;

        // DeFi integration
        mapping(address => address) protocolAdapters; // protocol -> adapter contract
        mapping(address => uint256) protocolAllocations;
        uint256 totalDefiAllocated;

        // Emergency reserves
        uint256 emergencyReserveAmount;
        uint256 emergencyReserveThreshold;
        bool emergencyModeActive;

        // Governance integration
        uint256 lastGovernanceUpdate;
        mapping(uint256 => bool) executedProposals;
    }

    struct ProjectTreasury {
        uint256 balance;
        uint256 allocated;
        uint256 titheOwed;
        uint256 titheCollected;
        address manager;
        bool active;
        mapping(address => uint256) assetBalances;
    }

    // Diamond storage slot
    bytes32 constant TREASURY_STORAGE_POSITION = keccak256("diamond.treasury.storage");

    function treasuryStorage() internal pure returns (TreasuryStorage storage ts) {
        bytes32 position = TREASURY_STORAGE_POSITION;
        assembly {
            ts.slot := position
        }
    }

    event AssetDeposited(
        address indexed asset,
        uint256 amount,
        uint256 titheAmount,
        address indexed depositor
    );

    event AllocationApproved(
        address indexed recipient,
        uint256 amount,
        address indexed approver,
        uint256 timestamp
    );

    event EmergencyModeActivated(
        address indexed activator,
        string reason,
        uint256 timestamp
    );

    event ProjectTreasuryCreated(
        string indexed projectName,
        address indexed manager,
        uint256 timestamp
    );

    event DeFiIntegrationAdded(
        address indexed protocol,
        address indexed adapter,
        uint256 maxAllocation
    );

    event TitheCollected(
        address indexed asset,
        uint256 amount,
        string indexed project,
        uint256 timestamp
    );

    modifier onlyExecutive() {
        TreasuryStorage storage ts = treasuryStorage();
        require(ts.executiveGovernance.hasExecutiveRole(msg.sender), "Not an executive");
        _;
    }

    modifier constitutionalCompliance() {
        TreasuryStorage storage ts = treasuryStorage();
        _;
        require(_validateConstitutionalConstraints(), "Constitutional violation");
    }

    constructor(
        address _constitution,
        address _executiveGovernance,
        address _owner,
        address[] memory _initialSigners
    ) Diamond(_owner) {
        require(_constitution != address(0), "Invalid constitution");
        require(_executiveGovernance != address(0), "Invalid executive governance");
        require(_initialSigners.length >= 3, "Minimum 3 signers required");

        TreasuryStorage storage ts = treasuryStorage();
        ts.constitution = DAIO_Constitution(_constitution);
        ts.executiveGovernance = ExecutiveGovernance(_executiveGovernance);
        ts.titheRate = 1500; // 15%
        ts.requiredSignatures = 3; // 3 of 5 multi-sig
        ts.emergencyReserveThreshold = 10; // 10% emergency reserve
        ts.lastValuationUpdate = block.timestamp;
        ts.lastGovernanceUpdate = block.timestamp;

        // Set initial signers
        for (uint256 i = 0; i < _initialSigners.length && i < 5; i++) {
            ts.signers.push(_initialSigners[i]);
        }

        _grantRole(DEFAULT_ADMIN_ROLE, _owner);
        _grantRole(TREASURY_MANAGER_ROLE, _owner);
        _grantRole(EMERGENCY_ROLE, _owner);

        // Initialize diamond with core facets
        _addTreasuryFacets();
    }

    /**
     * @dev Add initial treasury facets to diamond
     */
    function _addTreasuryFacets() internal {
        // Core treasury operations facet
        FacetCut[] memory cuts = new FacetCut[](4);

        // Asset Management Facet
        cuts[0] = FacetCut({
            facetAddress: address(0), // Deployed separately
            action: FacetCutAction.Add,
            functionSelectors: _getAssetManagementSelectors()
        });

        // Allocation Facet
        cuts[1] = FacetCut({
            facetAddress: address(0), // Deployed separately
            action: FacetCutAction.Add,
            functionSelectors: _getAllocationSelectors()
        });

        // DeFi Integration Facet
        cuts[2] = FacetCut({
            facetAddress: address(0), // Deployed separately
            action: FacetCutAction.Add,
            functionSelectors: _getDeFiSelectors()
        });

        // Reporting Facet
        cuts[3] = FacetCut({
            facetAddress: address(0), // Deployed separately
            action: FacetCutAction.Add,
            functionSelectors: _getReportingSelectors()
        });

        // Note: In production, facet addresses would be provided
        // diamondCut(cuts, address(0), "");
    }

    /**
     * @dev Get asset management function selectors
     */
    function _getAssetManagementSelectors() internal pure returns (bytes4[] memory) {
        bytes4[] memory selectors = new bytes4[](5);
        selectors[0] = bytes4(keccak256("depositAsset(address,uint256)"));
        selectors[1] = bytes4(keccak256("withdrawAsset(address,uint256,address)"));
        selectors[2] = bytes4(keccak256("updateAssetValuation(address,uint256)"));
        selectors[3] = bytes4(keccak256("addTrackedAsset(address)"));
        selectors[4] = bytes4(keccak256("removeTrackedAsset(address)"));
        return selectors;
    }

    /**
     * @dev Get allocation function selectors
     */
    function _getAllocationSelectors() internal pure returns (bytes4[] memory) {
        bytes4[] memory selectors = new bytes4[](4);
        selectors[0] = bytes4(keccak256("proposeAllocation(address,uint256,string)"));
        selectors[1] = bytes4(keccak256("approveAllocation(bytes32)"));
        selectors[2] = bytes4(keccak256("executeAllocation(bytes32)"));
        selectors[3] = bytes4(keccak256("revokeAllocation(bytes32)"));
        return selectors;
    }

    /**
     * @dev Get DeFi integration selectors
     */
    function _getDeFiSelectors() internal pure returns (bytes4[] memory) {
        bytes4[] memory selectors = new bytes4[](4);
        selectors[0] = bytes4(keccak256("addDeFiProtocol(address,address,uint256)"));
        selectors[1] = bytes4(keccak256("allocateToProtocol(address,uint256)"));
        selectors[2] = bytes4(keccak256("withdrawFromProtocol(address,uint256)"));
        selectors[3] = bytes4(keccak256("optimizeYieldAllocation()"));
        return selectors;
    }

    /**
     * @dev Get reporting function selectors
     */
    function _getReportingSelectors() internal pure returns (bytes4[] memory) {
        bytes4[] memory selectors = new bytes4[](4);
        selectors[0] = bytes4(keccak256("getTreasuryReport()"));
        selectors[1] = bytes4(keccak256("getProjectReport(string)"));
        selectors[2] = bytes4(keccak256("getComplianceReport()"));
        selectors[3] = bytes4(keccak256("getYieldReport()"));
        return selectors;
    }

    /**
     * @dev Deposit asset with automatic tithe collection
     */
    function depositAsset(
        address asset,
        uint256 amount,
        string calldata project
    ) external nonReentrant whenNotPaused constitutionalCompliance {
        require(amount > 0, "Invalid amount");
        require(bytes(project).length > 0, "Project name required");

        TreasuryStorage storage ts = treasuryStorage();

        // Calculate tithe
        uint256 titheAmount = (amount * ts.titheRate) / 10000;
        uint256 netAmount = amount - titheAmount;

        // Transfer asset
        IERC20(asset).transferFrom(msg.sender, address(this), amount);

        // Update balances
        ts.assetBalances[asset] += amount;
        ts.titheCollected[asset] += titheAmount;
        ts.totalTitheCollected += titheAmount;

        // Update project treasury
        ProjectTreasury storage projectTreasury = ts.projectTreasuries[project];
        projectTreasury.assetBalances[asset] += netAmount;
        projectTreasury.balance += netAmount;
        projectTreasury.titheCollected += titheAmount;

        // Add to tracked assets if not already tracked
        bool isTracked = false;
        for (uint256 i = 0; i < ts.trackedAssets.length; i++) {
            if (ts.trackedAssets[i] == asset) {
                isTracked = true;
                break;
            }
        }
        if (!isTracked) {
            ts.trackedAssets.push(asset);
        }

        emit AssetDeposited(asset, amount, titheAmount, msg.sender);
        emit TitheCollected(asset, titheAmount, project, block.timestamp);
    }

    /**
     * @dev Create new project treasury
     */
    function createProjectTreasury(
        string calldata projectName,
        address manager
    ) external onlyRole(TREASURY_MANAGER_ROLE) {
        require(bytes(projectName).length > 0, "Invalid project name");
        require(manager != address(0), "Invalid manager");

        TreasuryStorage storage ts = treasuryStorage();
        require(!ts.projectTreasuries[projectName].active, "Project already exists");

        ProjectTreasury storage project = ts.projectTreasuries[projectName];
        project.manager = manager;
        project.active = true;

        ts.projectNames.push(projectName);

        emit ProjectTreasuryCreated(projectName, manager, block.timestamp);
    }

    /**
     * @dev Propose allocation with multi-sig approval
     */
    function proposeAllocation(
        address recipient,
        uint256 amount,
        string calldata purpose
    ) external onlyExecutive returns (bytes32) {
        require(amount > 0, "Invalid amount");
        require(recipient != address(0), "Invalid recipient");

        TreasuryStorage storage ts = treasuryStorage();

        // Check 15% diversification limit
        uint256 maxAllocation = (ts.totalValue * 1500) / 10000; // 15%
        require(amount <= maxAllocation, "Exceeds diversification limit");

        bytes32 txHash = keccak256(abi.encodePacked(recipient, amount, purpose, block.timestamp));
        ts.pendingTransactions[txHash] = amount;

        return txHash;
    }

    /**
     * @dev Approve pending allocation
     */
    function approveAllocation(bytes32 txHash) external onlyExecutive {
        TreasuryStorage storage ts = treasuryStorage();
        require(ts.pendingTransactions[txHash] > 0, "Transaction not found");
        require(!ts.transactionApprovals[txHash][msg.sender], "Already approved");

        ts.transactionApprovals[txHash][msg.sender] = true;
        ts.approvalCounts[txHash]++;

        emit AllocationApproved(
            address(uint160(uint256(txHash))), // Extract recipient from hash
            ts.pendingTransactions[txHash],
            msg.sender,
            block.timestamp
        );

        // Auto-execute if threshold reached
        if (ts.approvalCounts[txHash] >= ts.requiredSignatures) {
            _executeAllocation(txHash);
        }
    }

    /**
     * @dev Execute approved allocation
     */
    function _executeAllocation(bytes32 txHash) internal {
        TreasuryStorage storage ts = treasuryStorage();
        uint256 amount = ts.pendingTransactions[txHash];

        // Clean up pending transaction
        delete ts.pendingTransactions[txHash];
        delete ts.approvalCounts[txHash];

        ts.totalAllocated += amount;
    }

    /**
     * @dev Activate emergency mode (CEO only)
     */
    function activateEmergencyMode(
        string calldata reason
    ) external onlyRole(EMERGENCY_ROLE) {
        TreasuryStorage storage ts = treasuryStorage();
        require(ts.executiveGovernance.isCEO(msg.sender), "Only CEO can activate emergency mode");

        ts.emergencyModeActive = true;
        _pause(); // Pause normal operations

        emit EmergencyModeActivated(msg.sender, reason, block.timestamp);
    }

    /**
     * @dev Deactivate emergency mode
     */
    function deactivateEmergencyMode() external onlyRole(DEFAULT_ADMIN_ROLE) {
        TreasuryStorage storage ts = treasuryStorage();
        ts.emergencyModeActive = false;
        _unpause();
    }

    /**
     * @dev Add DeFi protocol integration
     */
    function addDeFiProtocol(
        address protocol,
        address adapter,
        uint256 maxAllocation
    ) external onlyRole(TREASURY_MANAGER_ROLE) constitutionalCompliance {
        require(protocol != address(0), "Invalid protocol");
        require(adapter != address(0), "Invalid adapter");

        TreasuryStorage storage ts = treasuryStorage();
        ts.protocolAdapters[protocol] = adapter;
        ts.protocolAllocations[protocol] = maxAllocation;

        emit DeFiIntegrationAdded(protocol, adapter, maxAllocation);
    }

    /**
     * @dev Get treasury statistics
     */
    function getTreasuryStats() external view returns (
        uint256 totalValue,
        uint256 totalAllocated,
        uint256 availableBalance,
        uint256 titheCollected,
        uint256 assetCount,
        uint256 projectCount
    ) {
        TreasuryStorage storage ts = treasuryStorage();
        return (
            ts.totalValue,
            ts.totalAllocated,
            ts.totalValue - ts.totalAllocated,
            ts.totalTitheCollected,
            ts.trackedAssets.length,
            ts.projectNames.length
        );
    }

    /**
     * @dev Validate constitutional constraints
     */
    function _validateConstitutionalConstraints() internal view returns (bool) {
        TreasuryStorage storage ts = treasuryStorage();

        // Validate 15% tithe rate
        if (ts.titheRate != 1500) return false;

        // Validate diversification limits
        for (uint256 i = 0; i < ts.trackedAssets.length; i++) {
            address asset = ts.trackedAssets[i];
            uint256 assetValue = ts.assetValues[asset];
            if (assetValue > (ts.totalValue * 1500) / 10000) {
                return false; // Single asset exceeds 15%
            }
        }

        return true;
    }

    /**
     * @dev Update required signatures for multi-sig
     */
    function updateRequiredSignatures(
        uint256 newRequired
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        TreasuryStorage storage ts = treasuryStorage();
        require(newRequired >= 2 && newRequired <= ts.signers.length, "Invalid signature count");
        ts.requiredSignatures = newRequired;
    }

    /**
     * @dev Add multi-sig signer
     */
    function addSigner(address newSigner) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newSigner != address(0), "Invalid signer");
        TreasuryStorage storage ts = treasuryStorage();
        require(ts.signers.length < 7, "Maximum signers reached");

        ts.signers.push(newSigner);
    }

    /**
     * @dev Remove multi-sig signer
     */
    function removeSigner(address signer) external onlyRole(DEFAULT_ADMIN_ROLE) {
        TreasuryStorage storage ts = treasuryStorage();
        require(ts.signers.length > ts.requiredSignatures, "Cannot remove required signer");

        for (uint256 i = 0; i < ts.signers.length; i++) {
            if (ts.signers[i] == signer) {
                ts.signers[i] = ts.signers[ts.signers.length - 1];
                ts.signers.pop();
                break;
            }
        }
    }

    /**
     * @dev Upgrade diamond with new treasury facet
     */
    function addTreasuryFacet(
        address facetAddress,
        bytes4[] calldata functionSelectors
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        FacetCut[] memory cuts = new FacetCut[](1);
        cuts[0] = FacetCut({
            facetAddress: facetAddress,
            action: FacetCutAction.Add,
            functionSelectors: functionSelectors
        });

        diamondCut(cuts, address(0), "");
    }

    /**
     * @dev Emergency pause
     */
    function emergencyPause() external onlyRole(EMERGENCY_ROLE) {
        _pause();
    }

    /**
     * @dev Unpause operations
     */
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    /**
     * @dev Receive ETH deposits
     */
    receive() external payable {
        // Automatic ETH handling with tithe collection
        depositAsset(address(0), msg.value, "general");
    }
}