// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "../governance/DAIO_BranchManager.sol";
import "../settings/DAIO_ConfigurationEngine.sol";
import "../treasury/TreasuryFeeCollector.sol";

/**
 * @title UmbrellaCoordinator
 * @notice Coordinates umbrella organizations with multiple DAIOs
 * @dev Manages multi-DAIO coordination, resource sharing, and conflict arbitration
 */
contract UmbrellaCoordinator is AccessControl, ReentrancyGuard {

    bytes32 public constant UMBRELLA_ADMIN_ROLE = keccak256("UMBRELLA_ADMIN_ROLE");
    bytes32 public constant BRANCH_COORDINATOR_ROLE = keccak256("BRANCH_COORDINATOR_ROLE");
    bytes32 public constant ARBITRATOR_ROLE = keccak256("ARBITRATOR_ROLE");

    enum UmbrellaType {
        CENTRALIZED,    // Central control with subsidiary branches
        FEDERATED,      // Equal partners with shared governance
        HIERARCHICAL,   // Multi-level hierarchy with regional branches
        MATRIX,         // Cross-functional matrix organization
        NETWORK         // Decentralized network of autonomous DAIOs
    }

    enum ConflictType {
        RESOURCE_ALLOCATION,  // Disputes over resource distribution
        GOVERNANCE_OVERLAP,   // Overlapping governance authority
        STRATEGIC_DIRECTION,  // Disagreements on strategic direction
        OPERATIONAL,          // Operational coordination conflicts
        CONSTITUTIONAL        // Constitutional interpretation disputes
    }

    enum ConflictStatus {
        REPORTED,       // Conflict reported but not yet addressed
        INVESTIGATING,  // Under investigation
        ARBITRATING,    // In arbitration process
        RESOLVED,       // Successfully resolved
        ESCALATED,      // Escalated to higher authority
        DEADLOCKED      // Unable to resolve
    }

    struct UmbrellaOrganization {
        uint256 orgId;
        string name;
        string description;
        UmbrellaType orgType;
        address parentDAO;         // Parent DAIO (if any)
        address[] memberDAOs;      // All member DAIOs
        mapping(address => bool) isMember;
        mapping(address => uint256) memberWeight; // Voting weight per member
        uint256 totalWeight;

        // Governance structure
        uint256 consensusThreshold;   // Required consensus percentage
        bool allowsNewMembers;
        uint256 membershipFee;
        uint256 createdAt;
        bool active;

        // Resource coordination
        uint256 sharedTreasuryBalance;
        mapping(address => uint256) resourceAllocations;
        uint256 lastResourceDistribution;
    }

    struct SharedResource {
        uint256 resourceId;
        string resourceName;
        string description;
        address resourceContract;  // Contract managing the resource
        uint256 totalValue;
        mapping(uint256 => uint256) allocationByOrg; // OrgId => allocation
        mapping(address => bool) accessPermissions; // DAIO => has access
        uint256 lastUpdate;
        bool active;
    }

    struct ConflictReport {
        uint256 conflictId;
        uint256 umbrellaOrgId;
        ConflictType conflictType;
        address reportedBy;
        address[] involvedParties;
        string description;
        string evidenceHash;      // IPFS hash of evidence

        ConflictStatus status;
        address assignedArbitrator;
        uint256 reportedAt;
        uint256 resolutionDeadline;
        uint256 resolvedAt;

        string resolutionDetails;
        mapping(address => bool) partyAgreement; // Whether each party agrees to resolution
        uint256 agreementCount;

        // Arbitration voting
        mapping(address => bool) arbitratorVotes; // For multi-arbitrator cases
        uint256 votesForResolution;
        uint256 totalArbitrators;
    }

    struct CrossDAOProposal {
        uint256 proposalId;
        uint256 umbrellaOrgId;
        string title;
        string description;
        address proposer;
        address[] targetDAOs;     // DAIOs that need to implement this

        mapping(address => bool) daoApproval; // DAIO => approved
        uint256 approvalsReceived;
        uint256 requiredApprovals;

        uint256 createdAt;
        uint256 votingDeadline;
        bool executed;
        bool cancelled;

        // Resource implications
        uint256 totalCost;
        mapping(address => uint256) costByDAO;
    }

    struct CoordinationMetrics {
        uint256 totalProposalsProcessed;
        uint256 successfulCoordinations;
        uint256 conflictsResolved;
        uint256 averageResolutionTime;
        uint256 resourceUtilizationRate;
        uint256 memberSatisfactionScore;
    }

    // Storage
    mapping(uint256 => UmbrellaOrganization) public umbrellaOrgs;
    mapping(uint256 => SharedResource) public sharedResources;
    mapping(uint256 => ConflictReport) public conflicts;
    mapping(uint256 => CrossDAOProposal) public crossDAOProposals;
    mapping(address => uint256[]) public daoToOrgs; // DAIO => Umbrella Org IDs
    mapping(uint256 => uint256[]) public orgToResources; // Org ID => Resource IDs
    mapping(uint256 => CoordinationMetrics) public metrics;

    uint256 public orgCount;
    uint256 public resourceCount;
    uint256 public conflictCount;
    uint256 public crossProposalCount;

    // Configuration
    uint256 public constant MAX_MEMBERS_PER_ORG = 50;
    uint256 public constant DEFAULT_CONSENSUS_THRESHOLD = 67; // 67%
    uint256 public constant MAX_ARBITRATION_PERIOD = 30 days;
    uint256 public constant MIN_ARBITRATORS = 3;
    uint256 public defaultMembershipFee = 1 ether;

    // Integration contracts
    DAIO_BranchManager public branchManager;
    DAIO_ConfigurationEngine public configEngine;
    TreasuryFeeCollector public feeCollector;

    // Events
    event UmbrellaOrganizationCreated(
        uint256 indexed orgId,
        string name,
        UmbrellaType orgType,
        address indexed creator
    );

    event MemberDAOAdded(
        uint256 indexed orgId,
        address indexed daoAddress,
        uint256 weight
    );

    event MemberDAORemoved(
        uint256 indexed orgId,
        address indexed daoAddress
    );

    event SharedResourceCreated(
        uint256 indexed resourceId,
        uint256 indexed orgId,
        string resourceName,
        uint256 totalValue
    );

    event ConflictReported(
        uint256 indexed conflictId,
        uint256 indexed orgId,
        ConflictType conflictType,
        address indexed reportedBy
    );

    event ConflictResolved(
        uint256 indexed conflictId,
        address indexed arbitrator,
        uint256 resolutionTime
    );

    event CrossDAOProposalCreated(
        uint256 indexed proposalId,
        uint256 indexed orgId,
        string title,
        address indexed proposer
    );

    event CrossDAOProposalApproved(
        uint256 indexed proposalId,
        address indexed daoAddress,
        uint256 approvalsReceived
    );

    event ResourceDistributed(
        uint256 indexed orgId,
        uint256 indexed resourceId,
        uint256 totalDistributed,
        uint256 timestamp
    );

    event EmergencyIntervention(
        uint256 indexed orgId,
        address indexed interventionBy,
        string reason,
        uint256 timestamp
    );

    modifier validOrganization(uint256 orgId) {
        require(orgId > 0 && orgId <= orgCount, "Invalid organization ID");
        require(umbrellaOrgs[orgId].active, "Organization not active");
        _;
    }

    modifier onlyMemberDAO(uint256 orgId) {
        require(umbrellaOrgs[orgId].isMember[msg.sender], "Not a member DAO");
        _;
    }

    modifier onlyUmbrellaAdmin() {
        require(hasRole(UMBRELLA_ADMIN_ROLE, msg.sender), "Not umbrella admin");
        _;
    }

    modifier onlyArbitrator() {
        require(hasRole(ARBITRATOR_ROLE, msg.sender), "Not arbitrator");
        _;
    }

    constructor(
        address _branchManager,
        address _configEngine,
        address _feeCollector
    ) {
        require(_branchManager != address(0), "Invalid branch manager");
        require(_configEngine != address(0), "Invalid config engine");
        require(_feeCollector != address(0), "Invalid fee collector");

        branchManager = DAIO_BranchManager(_branchManager);
        configEngine = DAIO_ConfigurationEngine(_configEngine);
        feeCollector = TreasuryFeeCollector(payable(_feeCollector));

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(UMBRELLA_ADMIN_ROLE, msg.sender);
        _grantRole(ARBITRATOR_ROLE, msg.sender);
        _grantRole(BRANCH_COORDINATOR_ROLE, msg.sender);
    }

    /**
     * @notice Create new umbrella organization
     * @param name Organization name
     * @param description Organization description
     * @param orgType Type of umbrella organization
     * @param consensusThreshold Required consensus percentage
     * @param membershipFee Fee to join organization
     */
    function createUmbrellaOrganization(
        string memory name,
        string memory description,
        UmbrellaType orgType,
        uint256 consensusThreshold,
        uint256 membershipFee
    ) external onlyUmbrellaAdmin returns (uint256 orgId) {
        require(bytes(name).length > 0, "Name required");
        require(consensusThreshold >= 51 && consensusThreshold <= 100, "Invalid consensus threshold");

        orgCount++;

        UmbrellaOrganization storage org = umbrellaOrgs[orgCount];
        org.orgId = orgCount;
        org.name = name;
        org.description = description;
        org.orgType = orgType;
        org.parentDAO = msg.sender;
        org.consensusThreshold = consensusThreshold;
        org.allowsNewMembers = true;
        org.membershipFee = membershipFee;
        org.createdAt = block.timestamp;
        org.active = true;

        emit UmbrellaOrganizationCreated(orgCount, name, orgType, msg.sender);
        return orgCount;
    }

    /**
     * @notice Add member DAO to umbrella organization
     * @param orgId Organization ID
     * @param daoAddress DAO address to add
     * @param weight Voting weight for this DAO
     */
    function addMemberDAO(
        uint256 orgId,
        address daoAddress,
        uint256 weight
    ) external payable validOrganization(orgId) onlyUmbrellaAdmin {
        require(daoAddress != address(0), "Invalid DAO address");
        require(weight > 0, "Weight must be positive");

        UmbrellaOrganization storage org = umbrellaOrgs[orgId];
        require(org.allowsNewMembers, "Not accepting new members");
        require(!org.isMember[daoAddress], "Already a member");
        require(org.memberDAOs.length < MAX_MEMBERS_PER_ORG, "Maximum members reached");
        require(msg.value >= org.membershipFee, "Insufficient membership fee");

        org.memberDAOs.push(daoAddress);
        org.isMember[daoAddress] = true;
        org.memberWeight[daoAddress] = weight;
        org.totalWeight += weight;

        daoToOrgs[daoAddress].push(orgId);

        if (msg.value > 0) {
            org.sharedTreasuryBalance += msg.value;
        }

        emit MemberDAOAdded(orgId, daoAddress, weight);
    }

    /**
     * @notice Remove member DAO from umbrella organization
     * @param orgId Organization ID
     * @param daoAddress DAO address to remove
     */
    function removeMemberDAO(
        uint256 orgId,
        address daoAddress
    ) external validOrganization(orgId) onlyUmbrellaAdmin {
        UmbrellaOrganization storage org = umbrellaOrgs[orgId];
        require(org.isMember[daoAddress], "Not a member");

        // Find and remove from memberDAOs array
        for (uint i = 0; i < org.memberDAOs.length; i++) {
            if (org.memberDAOs[i] == daoAddress) {
                org.memberDAOs[i] = org.memberDAOs[org.memberDAOs.length - 1];
                org.memberDAOs.pop();
                break;
            }
        }

        org.totalWeight -= org.memberWeight[daoAddress];
        org.isMember[daoAddress] = false;
        org.memberWeight[daoAddress] = 0;

        // Remove from daoToOrgs mapping
        uint256[] storage orgIds = daoToOrgs[daoAddress];
        for (uint i = 0; i < orgIds.length; i++) {
            if (orgIds[i] == orgId) {
                orgIds[i] = orgIds[orgIds.length - 1];
                orgIds.pop();
                break;
            }
        }

        emit MemberDAORemoved(orgId, daoAddress);
    }

    /**
     * @notice Create shared resource for umbrella organization
     * @param orgId Organization ID
     * @param resourceName Resource name
     * @param description Resource description
     * @param resourceContract Contract managing the resource
     * @param totalValue Total value of resource
     */
    function createSharedResource(
        uint256 orgId,
        string memory resourceName,
        string memory description,
        address resourceContract,
        uint256 totalValue
    ) external validOrganization(orgId) onlyUmbrellaAdmin returns (uint256 resourceId) {
        require(bytes(resourceName).length > 0, "Resource name required");
        require(resourceContract != address(0), "Invalid resource contract");

        resourceCount++;

        SharedResource storage resource = sharedResources[resourceCount];
        resource.resourceId = resourceCount;
        resource.resourceName = resourceName;
        resource.description = description;
        resource.resourceContract = resourceContract;
        resource.totalValue = totalValue;
        resource.lastUpdate = block.timestamp;
        resource.active = true;

        orgToResources[orgId].push(resourceCount);

        emit SharedResourceCreated(resourceCount, orgId, resourceName, totalValue);
        return resourceCount;
    }

    /**
     * @notice Report conflict within umbrella organization
     * @param orgId Organization ID
     * @param conflictType Type of conflict
     * @param involvedParties Addresses involved in conflict
     * @param description Conflict description
     * @param evidenceHash IPFS hash of evidence
     */
    function reportConflict(
        uint256 orgId,
        ConflictType conflictType,
        address[] memory involvedParties,
        string memory description,
        string memory evidenceHash
    ) external validOrganization(orgId) onlyMemberDAO(orgId) returns (uint256 conflictId) {
        require(involvedParties.length >= 2, "Need at least 2 parties");
        require(bytes(description).length > 0, "Description required");

        conflictCount++;

        ConflictReport storage conflict = conflicts[conflictCount];
        conflict.conflictId = conflictCount;
        conflict.umbrellaOrgId = orgId;
        conflict.conflictType = conflictType;
        conflict.reportedBy = msg.sender;
        conflict.involvedParties = involvedParties;
        conflict.description = description;
        conflict.evidenceHash = evidenceHash;
        conflict.status = ConflictStatus.REPORTED;
        conflict.reportedAt = block.timestamp;
        conflict.resolutionDeadline = block.timestamp + MAX_ARBITRATION_PERIOD;

        emit ConflictReported(conflictCount, orgId, conflictType, msg.sender);
        return conflictCount;
    }

    /**
     * @notice Assign arbitrator to conflict
     * @param conflictId Conflict ID
     * @param arbitrator Arbitrator address
     */
    function assignArbitrator(
        uint256 conflictId,
        address arbitrator
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(conflictId > 0 && conflictId <= conflictCount, "Invalid conflict ID");
        require(hasRole(ARBITRATOR_ROLE, arbitrator), "Not a valid arbitrator");

        ConflictReport storage conflict = conflicts[conflictId];
        require(conflict.status == ConflictStatus.REPORTED, "Conflict not in reported status");

        conflict.assignedArbitrator = arbitrator;
        conflict.status = ConflictStatus.INVESTIGATING;
        conflict.totalArbitrators = 1; // Single arbitrator for now
    }

    /**
     * @notice Resolve conflict
     * @param conflictId Conflict ID
     * @param resolutionDetails Details of resolution
     */
    function resolveConflict(
        uint256 conflictId,
        string memory resolutionDetails
    ) external onlyArbitrator {
        require(conflictId > 0 && conflictId <= conflictCount, "Invalid conflict ID");

        ConflictReport storage conflict = conflicts[conflictId];
        require(conflict.assignedArbitrator == msg.sender, "Not assigned arbitrator");
        require(conflict.status == ConflictStatus.INVESTIGATING, "Not in investigation");
        require(block.timestamp <= conflict.resolutionDeadline, "Resolution deadline passed");

        conflict.status = ConflictStatus.RESOLVED;
        conflict.resolutionDetails = resolutionDetails;
        conflict.resolvedAt = block.timestamp;

        uint256 resolutionTime = conflict.resolvedAt - conflict.reportedAt;

        // Update metrics
        CoordinationMetrics storage orgMetrics = metrics[conflict.umbrellaOrgId];
        orgMetrics.conflictsResolved++;
        if (orgMetrics.conflictsResolved > 1) {
            orgMetrics.averageResolutionTime = (orgMetrics.averageResolutionTime + resolutionTime) / 2;
        } else {
            orgMetrics.averageResolutionTime = resolutionTime;
        }

        emit ConflictResolved(conflictId, msg.sender, resolutionTime);
    }

    /**
     * @notice Create cross-DAO proposal
     * @param orgId Organization ID
     * @param title Proposal title
     * @param description Proposal description
     * @param targetDAOs DAIOs that need to implement this proposal
     * @param totalCost Total cost of proposal
     */
    function createCrossDAOProposal(
        uint256 orgId,
        string memory title,
        string memory description,
        address[] memory targetDAOs,
        uint256 totalCost
    ) external validOrganization(orgId) onlyMemberDAO(orgId) returns (uint256 proposalId) {
        require(bytes(title).length > 0, "Title required");
        require(targetDAOs.length > 0, "Must specify target DAOs");

        crossProposalCount++;

        CrossDAOProposal storage proposal = crossDAOProposals[crossProposalCount];
        proposal.proposalId = crossProposalCount;
        proposal.umbrellaOrgId = orgId;
        proposal.title = title;
        proposal.description = description;
        proposal.proposer = msg.sender;
        proposal.targetDAOs = targetDAOs;
        proposal.requiredApprovals = (targetDAOs.length * umbrellaOrgs[orgId].consensusThreshold) / 100;
        proposal.createdAt = block.timestamp;
        proposal.votingDeadline = block.timestamp + (7 days); // 7-day voting period
        proposal.totalCost = totalCost;

        // Distribute cost across target DAIOs
        if (totalCost > 0 && targetDAOs.length > 0) {
            uint256 costPerDAO = totalCost / targetDAOs.length;
            for (uint i = 0; i < targetDAOs.length; i++) {
                proposal.costByDAO[targetDAOs[i]] = costPerDAO;
            }
        }

        emit CrossDAOProposalCreated(crossProposalCount, orgId, title, msg.sender);
        return crossProposalCount;
    }

    /**
     * @notice Approve cross-DAO proposal
     * @param proposalId Proposal ID
     */
    function approveCrossDAOProposal(uint256 proposalId) external {
        require(proposalId > 0 && proposalId <= crossProposalCount, "Invalid proposal ID");

        CrossDAOProposal storage proposal = crossDAOProposals[proposalId];
        require(block.timestamp <= proposal.votingDeadline, "Voting period ended");
        require(!proposal.executed && !proposal.cancelled, "Proposal finalized");

        // Check if sender is in target DAOs
        bool isTargetDAO = false;
        for (uint i = 0; i < proposal.targetDAOs.length; i++) {
            if (proposal.targetDAOs[i] == msg.sender) {
                isTargetDAO = true;
                break;
            }
        }
        require(isTargetDAO, "Not a target DAO");
        require(!proposal.daoApproval[msg.sender], "Already approved");

        proposal.daoApproval[msg.sender] = true;
        proposal.approvalsReceived++;

        emit CrossDAOProposalApproved(proposalId, msg.sender, proposal.approvalsReceived);

        // Check if proposal passes
        if (proposal.approvalsReceived >= proposal.requiredApprovals) {
            proposal.executed = true;
            _executeCrossDAOProposal(proposalId);
        }
    }

    /**
     * @notice Emergency intervention capability
     * @param orgId Organization ID
     * @param reason Reason for intervention
     */
    function emergencyIntervention(
        uint256 orgId,
        string memory reason
    ) external validOrganization(orgId) onlyRole(DEFAULT_ADMIN_ROLE) {
        require(bytes(reason).length > 0, "Reason required");

        // Emergency powers would be implemented here
        // This could include:
        // - Temporarily suspending voting
        // - Freezing resource transfers
        // - Implementing emergency governance
        // - Calling emergency meetings

        emit EmergencyIntervention(orgId, msg.sender, reason, block.timestamp);
    }

    /**
     * @notice Distribute resources within organization
     * @param orgId Organization ID
     * @param resourceId Resource ID
     */
    function distributeResource(
        uint256 orgId,
        uint256 resourceId
    ) external validOrganization(orgId) onlyUmbrellaAdmin nonReentrant {
        require(resourceId > 0 && resourceId <= resourceCount, "Invalid resource ID");

        SharedResource storage resource = sharedResources[resourceId];
        require(resource.active, "Resource not active");

        UmbrellaOrganization storage org = umbrellaOrgs[orgId];
        uint256 totalDistributed = 0;

        // Distribute based on member weights
        for (uint i = 0; i < org.memberDAOs.length; i++) {
            address memberDAO = org.memberDAOs[i];
            uint256 allocation = (resource.totalValue * org.memberWeight[memberDAO]) / org.totalWeight;

            resource.allocationByOrg[orgId] = allocation;
            org.resourceAllocations[memberDAO] += allocation;
            totalDistributed += allocation;
        }

        org.lastResourceDistribution = block.timestamp;
        resource.lastUpdate = block.timestamp;

        emit ResourceDistributed(orgId, resourceId, totalDistributed, block.timestamp);
    }

    /**
     * @notice Get umbrella organization details
     * @param orgId Organization ID
     * @return name Organization name
     * @return description Organization description
     * @return orgType Organization type
     * @return parentDAO Parent DAO address
     * @return memberCount Number of members
     * @return totalWeight Total voting weight
     * @return consensusThreshold Consensus threshold percentage
     * @return allowsNewMembers Whether accepting new members
     * @return membershipFee Membership fee amount
     * @return sharedTreasuryBalance Shared treasury balance
     */
    function getUmbrellaOrganization(uint256 orgId) external view validOrganization(orgId) returns (
        string memory name,
        string memory description,
        UmbrellaType orgType,
        address parentDAO,
        uint256 memberCount,
        uint256 totalWeight,
        uint256 consensusThreshold,
        bool allowsNewMembers,
        uint256 membershipFee,
        uint256 sharedTreasuryBalance
    ) {
        UmbrellaOrganization storage org = umbrellaOrgs[orgId];
        return (
            org.name,
            org.description,
            org.orgType,
            org.parentDAO,
            org.memberDAOs.length,
            org.totalWeight,
            org.consensusThreshold,
            org.allowsNewMembers,
            org.membershipFee,
            org.sharedTreasuryBalance
        );
    }

    /**
     * @notice Get member DAOs of organization
     * @param orgId Organization ID
     * @return Array of member DAO addresses
     */
    function getMemberDAOs(uint256 orgId) external view validOrganization(orgId) returns (address[] memory) {
        return umbrellaOrgs[orgId].memberDAOs;
    }

    /**
     * @notice Get shared resources of organization
     * @param orgId Organization ID
     * @return Array of resource IDs
     */
    function getSharedResources(uint256 orgId) external view validOrganization(orgId) returns (uint256[] memory) {
        return orgToResources[orgId];
    }

    /**
     * @notice Get organizations for a DAO
     * @param daoAddress DAO address
     * @return Array of organization IDs
     */
    function getDAOOrganizations(address daoAddress) external view returns (uint256[] memory) {
        return daoToOrgs[daoAddress];
    }

    /**
     * @notice Get conflict details
     * @param conflictId Conflict ID
     * @return umbrellaOrgId Umbrella organization ID
     * @return conflictType Type of conflict
     * @return reportedBy Who reported the conflict
     * @return involvedParties Involved parties
     * @return description Conflict description
     * @return status Conflict status
     * @return assignedArbitrator Assigned arbitrator
     * @return reportedAt When reported
     * @return resolvedAt When resolved
     */
    function getConflict(uint256 conflictId) external view returns (
        uint256 umbrellaOrgId,
        ConflictType conflictType,
        address reportedBy,
        address[] memory involvedParties,
        string memory description,
        ConflictStatus status,
        address assignedArbitrator,
        uint256 reportedAt,
        uint256 resolvedAt
    ) {
        require(conflictId > 0 && conflictId <= conflictCount, "Invalid conflict ID");

        ConflictReport storage conflict = conflicts[conflictId];
        return (
            conflict.umbrellaOrgId,
            conflict.conflictType,
            conflict.reportedBy,
            conflict.involvedParties,
            conflict.description,
            conflict.status,
            conflict.assignedArbitrator,
            conflict.reportedAt,
            conflict.resolvedAt
        );
    }

    /**
     * @notice Execute approved cross-DAO proposal
     * @param proposalId Proposal ID
     */
    function _executeCrossDAOProposal(uint256 proposalId) internal {
        // Implementation would coordinate execution across multiple DAIOs
        // This might involve:
        // - Sending execution instructions to each DAO
        // - Coordinating resource transfers
        // - Managing inter-DAO dependencies

        CoordinationMetrics storage orgMetrics = metrics[crossDAOProposals[proposalId].umbrellaOrgId];
        orgMetrics.totalProposalsProcessed++;
        orgMetrics.successfulCoordinations++;
    }
}