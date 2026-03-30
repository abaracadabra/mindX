// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "../settings/DAIO_ConfigurationEngine.sol";
import "../../DAIO_Core.sol";

/**
 * @title DAIO_BranchManager
 * @notice Manages organizational branches and arms for self-extending DAIO
 * @dev Enables DAIO to spawn subsidiaries and departments dynamically
 */
contract DAIO_BranchManager is AccessControl, ReentrancyGuard {

    bytes32 public constant BRANCH_CREATOR_ROLE = keccak256("BRANCH_CREATOR_ROLE");
    bytes32 public constant PARENT_GOVERNANCE_ROLE = keccak256("PARENT_GOVERNANCE_ROLE");

    enum BranchType {
        SUBSIDIARY,     // Independent subsidiary DAIO
        DEPARTMENT,     // Internal department/arm
        FEDERATION,     // Federated partnership
        UMBRELLA_CHILD  // Child under umbrella structure
    }

    enum BranchStatus {
        PROPOSED,
        APPROVED,
        DEPLOYED,
        ACTIVE,
        SUSPENDED,
        TERMINATED
    }

    struct Branch {
        uint256 id;
        string name;
        string description;
        BranchType branchType;
        BranchStatus status;
        address branchAddress;      // Deployed DAIO Core address
        address parentAddress;      // Parent DAIO address
        uint256 autonomyLevel;      // 0-100, higher = more autonomous
        uint256 resourceAllocation; // Percentage of parent resources
        uint256 createdAt;
        uint256 lastActivity;
        address createdBy;
        bytes32 configurationHash;  // Configuration template used
    }

    struct BranchProposal {
        uint256 id;
        string name;
        string description;
        string justification;
        BranchType proposedType;
        uint256 requestedAutonomy;
        uint256 requestedResources;
        uint256 estimatedCost;      // Deployment cost in wei
        address proposedBy;
        uint256 proposedAt;
        uint256 votingEndsAt;
        bool approved;
        bool executed;
        uint256 supportVotes;
        uint256 totalVotes;
    }

    struct ResourceAllocation {
        address branchAddress;
        uint256 allocatedAmount;
        uint256 totalBudget;
        uint256 spentAmount;
        uint256 lastAllocation;
        bool active;
    }

    struct ArmExtension {
        uint256 id;
        string name;
        string functionality;
        address contractAddress;
        bool active;
        uint256 deployedAt;
        uint256 resourceCost;
    }

    // Storage
    mapping(uint256 => Branch) public branches;
    mapping(uint256 => BranchProposal) public branchProposals;
    mapping(address => ResourceAllocation) public resourceAllocations;
    mapping(uint256 => ArmExtension) public armExtensions;
    mapping(address => uint256[]) public parentToBranches;
    mapping(address => address) public branchToParent;
    mapping(uint256 => mapping(address => bool)) public hasVotedOnProposal;

    uint256 public branchCount;
    uint256 public proposalCount;
    uint256 public armCount;
    uint256 public maxBranchesPerParent = 10;
    uint256 public minAutonomyLevel = 25; // Minimum 25% autonomy
    uint256 public maxResourceAllocation = 75; // Maximum 75% of parent resources

    DAIO_ConfigurationEngine public configEngine;
    address public parentDAIOCore;

    // Events
    event BranchProposed(
        uint256 indexed proposalId,
        string name,
        BranchType branchType,
        address indexed proposedBy
    );

    event BranchApproved(
        uint256 indexed proposalId,
        uint256 indexed branchId,
        address indexed branchAddress
    );

    event BranchDeployed(
        uint256 indexed branchId,
        address indexed branchAddress,
        string name,
        BranchType branchType
    );

    event BranchStatusChanged(
        uint256 indexed branchId,
        BranchStatus oldStatus,
        BranchStatus newStatus
    );

    event ResourcesAllocated(
        address indexed branchAddress,
        uint256 amount,
        uint256 totalBudget
    );

    event ArmExtensionDeployed(
        uint256 indexed armId,
        string name,
        address contractAddress
    );

    event BranchVoteCast(
        uint256 indexed proposalId,
        address indexed voter,
        bool support,
        uint256 weight
    );

    modifier onlyParentGovernance() {
        require(hasRole(PARENT_GOVERNANCE_ROLE, msg.sender), "Not parent governance");
        _;
    }

    modifier onlyBranchCreator() {
        require(hasRole(BRANCH_CREATOR_ROLE, msg.sender), "Not branch creator");
        _;
    }

    modifier validBranch(uint256 branchId) {
        require(branchId > 0 && branchId <= branchCount, "Invalid branch ID");
        _;
    }

    modifier validProposal(uint256 proposalId) {
        require(proposalId > 0 && proposalId <= proposalCount, "Invalid proposal ID");
        _;
    }

    constructor(
        address _configEngine,
        address _parentDAIOCore
    ) {
        require(_configEngine != address(0), "Invalid config engine");
        require(_parentDAIOCore != address(0), "Invalid parent DAIO");

        configEngine = DAIO_ConfigurationEngine(_configEngine);
        parentDAIOCore = _parentDAIOCore;

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(BRANCH_CREATOR_ROLE, msg.sender);
        _grantRole(PARENT_GOVERNANCE_ROLE, msg.sender);
    }

    /**
     * @notice Propose creation of new branch
     * @param name Branch name
     * @param description Branch description
     * @param justification Justification for branch creation
     * @param branchType Type of branch to create
     * @param autonomyLevel Requested autonomy level (0-100)
     * @param resourcePercentage Requested resource allocation percentage
     */
    function proposeBranch(
        string memory name,
        string memory description,
        string memory justification,
        BranchType branchType,
        uint256 autonomyLevel,
        uint256 resourcePercentage
    ) external returns (uint256 proposalId) {
        require(bytes(name).length > 0, "Name required");
        require(autonomyLevel >= minAutonomyLevel && autonomyLevel <= 100, "Invalid autonomy level");
        require(resourcePercentage <= maxResourceAllocation, "Resource allocation too high");
        require(parentToBranches[parentDAIOCore].length < maxBranchesPerParent, "Max branches reached");

        proposalCount++;
        uint256 votingPeriod = configEngine.getParameter("proposal_period");

        branchProposals[proposalCount] = BranchProposal({
            id: proposalCount,
            name: name,
            description: description,
            justification: justification,
            proposedType: branchType,
            requestedAutonomy: autonomyLevel,
            requestedResources: resourcePercentage,
            estimatedCost: _calculateDeploymentCost(branchType),
            proposedBy: msg.sender,
            proposedAt: block.timestamp,
            votingEndsAt: block.timestamp + (votingPeriod * 13), // Convert blocks to seconds
            approved: false,
            executed: false,
            supportVotes: 0,
            totalVotes: 0
        });

        emit BranchProposed(proposalCount, name, branchType, msg.sender);
        return proposalCount;
    }

    /**
     * @notice Vote on branch proposal
     * @param proposalId Proposal ID
     * @param support True for support, false for opposition
     * @param votingWeight Voting weight of the voter
     */
    function voteOnBranchProposal(
        uint256 proposalId,
        bool support,
        uint256 votingWeight
    ) external validProposal(proposalId) nonReentrant {
        BranchProposal storage proposal = branchProposals[proposalId];
        require(block.timestamp < proposal.votingEndsAt, "Voting ended");
        require(!hasVotedOnProposal[proposalId][msg.sender], "Already voted");
        require(!proposal.executed, "Proposal already executed");

        hasVotedOnProposal[proposalId][msg.sender] = true;
        proposal.totalVotes += votingWeight;

        if (support) {
            proposal.supportVotes += votingWeight;
        }

        emit BranchVoteCast(proposalId, msg.sender, support, votingWeight);

        // Check if proposal passes 2/3 threshold
        uint256 threshold = configEngine.getParameter("voting_threshold");
        if (proposal.supportVotes * 100 >= proposal.totalVotes * threshold) {
            proposal.approved = true;
        }
    }

    /**
     * @notice Execute approved branch proposal
     * @param proposalId Proposal ID
     */
    function executeBranchProposal(uint256 proposalId) external validProposal(proposalId) onlyBranchCreator {
        BranchProposal storage proposal = branchProposals[proposalId];
        require(proposal.approved, "Proposal not approved");
        require(!proposal.executed, "Proposal already executed");
        require(block.timestamp >= proposal.votingEndsAt, "Voting still active");

        proposal.executed = true;
        uint256 branchId = _deployBranch(proposal);

        emit BranchApproved(proposalId, branchId, branches[branchId].branchAddress);
    }

    /**
     * @notice Deploy arm extension to existing DAIO
     * @param name Arm name
     * @param functionality Arm functionality description
     * @param contractBytecode Compiled contract bytecode
     * @param constructorParams Constructor parameters
     */
    function deployArm(
        string memory name,
        string memory functionality,
        bytes memory contractBytecode,
        bytes memory constructorParams
    ) external onlyBranchCreator returns (uint256 armId) {
        require(bytes(name).length > 0, "Name required");

        // Deploy contract using CREATE2 for deterministic addresses
        bytes memory deploymentData = abi.encodePacked(contractBytecode, constructorParams);
        bytes32 salt = keccak256(abi.encodePacked(name, block.timestamp, armCount));
        address armAddress;

        assembly {
            armAddress := create2(0, add(deploymentData, 0x20), mload(deploymentData), salt)
            if iszero(extcodesize(armAddress)) { revert(0, 0) }
        }

        armCount++;
        armExtensions[armCount] = ArmExtension({
            id: armCount,
            name: name,
            functionality: functionality,
            contractAddress: armAddress,
            active: true,
            deployedAt: block.timestamp,
            resourceCost: tx.gasprice * gasleft() // Approximate deployment cost
        });

        emit ArmExtensionDeployed(armCount, name, armAddress);
        return armCount;
    }

    /**
     * @notice Allocate resources to branch
     * @param branchAddress Branch address
     * @param amount Amount to allocate
     */
    function allocateResources(
        address branchAddress,
        uint256 amount
    ) external onlyParentGovernance nonReentrant {
        require(branchAddress != address(0), "Invalid branch address");
        require(amount > 0, "Amount must be positive");

        ResourceAllocation storage allocation = resourceAllocations[branchAddress];
        allocation.branchAddress = branchAddress;
        allocation.allocatedAmount += amount;
        allocation.lastAllocation = block.timestamp;
        allocation.active = true;

        // Transfer funds (would integrate with treasury)
        // payable(branchAddress).transfer(amount);

        emit ResourcesAllocated(branchAddress, amount, allocation.totalBudget);
    }

    /**
     * @notice Update branch status
     * @param branchId Branch ID
     * @param newStatus New status
     */
    function updateBranchStatus(
        uint256 branchId,
        BranchStatus newStatus
    ) external validBranch(branchId) onlyParentGovernance {
        Branch storage branch = branches[branchId];
        BranchStatus oldStatus = branch.status;
        branch.status = newStatus;
        branch.lastActivity = block.timestamp;

        emit BranchStatusChanged(branchId, oldStatus, newStatus);
    }

    /**
     * @notice Get branch details
     * @param branchId Branch ID
     * @return branch Branch struct
     */
    function getBranch(uint256 branchId) external view validBranch(branchId) returns (Branch memory) {
        return branches[branchId];
    }

    /**
     * @notice Get branch proposal details
     * @param proposalId Proposal ID
     * @return proposal BranchProposal struct
     */
    function getBranchProposal(uint256 proposalId) external view validProposal(proposalId) returns (BranchProposal memory) {
        return branchProposals[proposalId];
    }

    /**
     * @notice Get all branches for a parent
     * @param parentAddress Parent DAIO address
     * @return branchIds Array of branch IDs
     */
    function getBranchesByParent(address parentAddress) external view returns (uint256[] memory) {
        return parentToBranches[parentAddress];
    }

    /**
     * @notice Get resource allocation for branch
     * @param branchAddress Branch address
     * @return allocation ResourceAllocation struct
     */
    function getResourceAllocation(address branchAddress) external view returns (ResourceAllocation memory) {
        return resourceAllocations[branchAddress];
    }

    /**
     * @notice Deploy branch from approved proposal
     * @param proposal Approved branch proposal
     * @return branchId New branch ID
     */
    function _deployBranch(BranchProposal storage proposal) internal returns (uint256) {
        branchCount++;

        // Deploy new DAIO_Core instance
        DAIO_Core newDAIO = new DAIO_Core();
        address branchAddress = address(newDAIO);

        // Initialize branch
        branches[branchCount] = Branch({
            id: branchCount,
            name: proposal.name,
            description: proposal.description,
            branchType: proposal.proposedType,
            status: BranchStatus.DEPLOYED,
            branchAddress: branchAddress,
            parentAddress: parentDAIOCore,
            autonomyLevel: proposal.requestedAutonomy,
            resourceAllocation: proposal.requestedResources,
            createdAt: block.timestamp,
            lastActivity: block.timestamp,
            createdBy: proposal.proposedBy,
            configurationHash: keccak256(abi.encode(proposal.requestedAutonomy, proposal.requestedResources))
        });

        // Update parent-child mappings
        parentToBranches[parentDAIOCore].push(branchCount);
        branchToParent[branchAddress] = parentDAIOCore;

        // Initialize resource allocation
        resourceAllocations[branchAddress] = ResourceAllocation({
            branchAddress: branchAddress,
            allocatedAmount: 0,
            totalBudget: (proposal.requestedResources * address(this).balance) / 100,
            spentAmount: 0,
            lastAllocation: block.timestamp,
            active: true
        });

        emit BranchDeployed(branchCount, branchAddress, proposal.name, proposal.proposedType);
        return branchCount;
    }

    /**
     * @notice Calculate deployment cost based on branch type
     * @param branchType Type of branch
     * @return cost Estimated deployment cost in wei
     */
    function _calculateDeploymentCost(BranchType branchType) internal view returns (uint256) {
        uint256 baseCost = 1 ether; // Base deployment cost

        if (branchType == BranchType.SUBSIDIARY) {
            return baseCost * 2; // Higher cost for subsidiary
        } else if (branchType == BranchType.DEPARTMENT) {
            return baseCost / 2; // Lower cost for department
        } else if (branchType == BranchType.UMBRELLA_CHILD) {
            return baseCost * 3; // Highest cost for umbrella child
        }

        return baseCost; // Default cost for federation
    }

    /**
     * @notice Update configuration parameters
     * @param maxBranches Maximum branches per parent
     * @param minAutonomy Minimum autonomy level
     * @param maxResources Maximum resource allocation percentage
     */
    function updateLimits(
        uint256 maxBranches,
        uint256 minAutonomy,
        uint256 maxResources
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(minAutonomy <= 100, "Invalid autonomy level");
        require(maxResources <= 100, "Invalid resource percentage");

        maxBranchesPerParent = maxBranches;
        minAutonomyLevel = minAutonomy;
        maxResourceAllocation = maxResources;
    }
}