// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "./ExecutiveRoles.sol";
import "./WeightedVotingEngine.sol";
import "./EmergencyTimelock.sol";
import "./KnowledgeHierarchyDAIO.sol";
import "../constitution/DAIO_Constitution.sol";
import "../settings/GovernanceSettings.sol";

/**
 * @title ExecutiveGovernance
 * @notice Main hierarchical governance contract extending KnowledgeHierarchyDAIO
 * @dev Implements CEO + Seven Soldiers executive structure with constitutional constraints
 */
contract ExecutiveGovernance is Ownable, ReentrancyGuard {

    // Proposal types for executive governance
    enum ExecutiveProposalType {
        OPERATIONAL,        // 0 - Day-to-day operations (simple majority)
        STRATEGIC,          // 1 - Strategic decisions (2/3 majority)
        FINANCIAL,          // 2 - Treasury/financial decisions (CFO + 2/3 majority)
        SECURITY,           // 3 - Security decisions (CISO + 2/3 majority)
        CONSTITUTIONAL,     // 4 - Constitutional changes (unanimous)
        EMERGENCY_RESPONSE, // 5 - Emergency responses (CEO or 2/3 majority)
        CROSS_PROJECT      // 6 - Cross-project coordination (2/3 majority)
    }

    // Proposal structure
    struct ExecutiveProposal {
        uint256 id;
        string title;
        string description;
        ExecutiveProposalType proposalType;
        address proposer;
        address target;           // Contract to call
        uint256 value;           // ETH value to send
        bytes callData;          // Function call data
        uint256 createdAt;
        uint256 votingEndTime;
        uint256 executionDelay;
        bool executed;
        bool cancelled;
        bool requiresSpecialistApproval; // CFO for financial, CISO for security, etc.
        address requiredSpecialist;     // Specific role required for approval
        bool specialistApproved;
    }

    // Executive voting state
    struct ExecutiveVoting {
        mapping(address => WeightedVotingEngine.VoteChoice) votes;
        uint256 participationWeight;
        uint256 forWeight;
        uint256 againstWeight;
        uint256 abstainWeight;
        bool finalized;
        bool passed;
    }

    // Integration contracts
    ExecutiveRoles public immutable executiveRoles;
    WeightedVotingEngine public immutable votingEngine;
    EmergencyTimelock public immutable emergencyTimelock;
    KnowledgeHierarchyDAIO public immutable knowledgeHierarchy;
    DAIO_Constitution public immutable constitution;
    GovernanceSettings public immutable settings;

    // State
    uint256 public proposalCounter;
    mapping(uint256 => ExecutiveProposal) public proposals;
    mapping(uint256 => ExecutiveVoting) public executiveVotings;

    // Proposal thresholds by type
    mapping(ExecutiveProposalType => uint256) public proposalThresholds;
    mapping(ExecutiveProposalType => uint256) public executionDelays;

    // Events
    event ExecutiveProposalCreated(
        uint256 indexed proposalId,
        ExecutiveProposalType indexed proposalType,
        address indexed proposer,
        string title,
        address target,
        uint256 votingEndTime
    );

    event ExecutiveVoteCast(
        uint256 indexed proposalId,
        address indexed voter,
        ExecutiveRoles.ExecutiveRole indexed role,
        WeightedVotingEngine.VoteChoice choice,
        uint256 weight
    );

    event SpecialistApprovalGiven(
        uint256 indexed proposalId,
        address indexed specialist,
        ExecutiveRoles.ExecutiveRole indexed role
    );

    event ExecutiveProposalExecuted(
        uint256 indexed proposalId,
        address indexed executor,
        bool success
    );

    event CEOEmergencyOverride(
        uint256 indexed proposalId,
        address indexed ceo,
        string reason
    );

    event ProposalDelegatedToCommunity(
        uint256 indexed proposalId,
        string reason
    );

    constructor(
        address _executiveRoles,
        address _votingEngine,
        address payable _emergencyTimelock,
        address _knowledgeHierarchy,
        address _constitution,
        address _settings
    ) Ownable(msg.sender) {
        require(_executiveRoles != address(0), "Invalid ExecutiveRoles");
        require(_votingEngine != address(0), "Invalid VotingEngine");
        require(_emergencyTimelock != address(0), "Invalid EmergencyTimelock");
        require(_knowledgeHierarchy != address(0), "Invalid KnowledgeHierarchy");
        require(_constitution != address(0), "Invalid Constitution");
        require(_settings != address(0), "Invalid Settings");

        executiveRoles = ExecutiveRoles(_executiveRoles);
        votingEngine = WeightedVotingEngine(_votingEngine);
        emergencyTimelock = EmergencyTimelock(_emergencyTimelock);
        knowledgeHierarchy = KnowledgeHierarchyDAIO(_knowledgeHierarchy);
        constitution = DAIO_Constitution(_constitution);
        settings = GovernanceSettings(_settings);

        _initializeProposalThresholds();
    }

    /**
     * @notice Initialize default proposal thresholds
     */
    function _initializeProposalThresholds() internal {
        proposalThresholds[ExecutiveProposalType.OPERATIONAL] = 5000;      // 50%
        proposalThresholds[ExecutiveProposalType.STRATEGIC] = 6667;        // 66.67%
        proposalThresholds[ExecutiveProposalType.FINANCIAL] = 6667;        // 66.67%
        proposalThresholds[ExecutiveProposalType.SECURITY] = 6667;         // 66.67%
        proposalThresholds[ExecutiveProposalType.CONSTITUTIONAL] = 10000;  // 100%
        proposalThresholds[ExecutiveProposalType.EMERGENCY_RESPONSE] = 6667; // 66.67%
        proposalThresholds[ExecutiveProposalType.CROSS_PROJECT] = 6667;    // 66.67%

        executionDelays[ExecutiveProposalType.OPERATIONAL] = 1 days;
        executionDelays[ExecutiveProposalType.STRATEGIC] = 3 days;
        executionDelays[ExecutiveProposalType.FINANCIAL] = 3 days;
        executionDelays[ExecutiveProposalType.SECURITY] = 2 days;
        executionDelays[ExecutiveProposalType.CONSTITUTIONAL] = 7 days;
        executionDelays[ExecutiveProposalType.EMERGENCY_RESPONSE] = 0; // Immediate
        executionDelays[ExecutiveProposalType.CROSS_PROJECT] = 2 days;
    }

    /**
     * @notice Create executive-level proposal
     * @param title Proposal title
     * @param description Detailed description
     * @param proposalType Type of proposal
     * @param target Contract to execute against
     * @param value ETH value to send
     * @param callData Function call data
     */
    function createExecutiveProposal(
        string memory title,
        string memory description,
        ExecutiveProposalType proposalType,
        address target,
        uint256 value,
        bytes memory callData
    ) external returns (uint256) {
        require(bytes(title).length > 0, "Title required");
        require(bytes(description).length > 0, "Description required");
        require(target != address(0), "Invalid target");

        // Check if proposer is active executive
        require(
            executiveRoles.isActiveExecutive(msg.sender) ||
            executiveRoles.hasRole(executiveRoles.GOVERNANCE_ROLE(), msg.sender),
            "Only active executives can create proposals"
        );

        // Validate constitutional constraints
        require(
            constitution.validateAction(target, callData, value),
            "Proposal violates constitutional constraints"
        );

        proposalCounter++;
        uint256 proposalId = proposalCounter;

        // Determine if specialist approval is required
        bool requiresSpecialist = false;
        address requiredSpecialist = address(0);

        if (proposalType == ExecutiveProposalType.FINANCIAL) {
            requiredSpecialist = executiveRoles.getRoleHolder(ExecutiveRoles.ExecutiveRole.CFO);
            requiresSpecialist = requiredSpecialist != address(0);
        } else if (proposalType == ExecutiveProposalType.SECURITY) {
            requiredSpecialist = executiveRoles.getRoleHolder(ExecutiveRoles.ExecutiveRole.CISO);
            requiresSpecialist = requiredSpecialist != address(0);
        }

        // Calculate voting end time (3 days for most proposals)
        uint256 votingPeriod = 3 days;
        if (proposalType == ExecutiveProposalType.CONSTITUTIONAL) {
            votingPeriod = 7 days; // Longer period for constitutional changes
        } else if (proposalType == ExecutiveProposalType.EMERGENCY_RESPONSE) {
            votingPeriod = 24 hours; // Faster for emergencies
        }

        proposals[proposalId] = ExecutiveProposal({
            id: proposalId,
            title: title,
            description: description,
            proposalType: proposalType,
            proposer: msg.sender,
            target: target,
            value: value,
            callData: callData,
            createdAt: block.timestamp,
            votingEndTime: block.timestamp + votingPeriod,
            executionDelay: executionDelays[proposalType],
            executed: false,
            cancelled: false,
            requiresSpecialistApproval: requiresSpecialist,
            requiredSpecialist: requiredSpecialist,
            specialistApproved: !requiresSpecialist // Auto-approve if no specialist required
        });

        emit ExecutiveProposalCreated(
            proposalId,
            proposalType,
            msg.sender,
            title,
            target,
            block.timestamp + votingPeriod
        );

        return proposalId;
    }

    /**
     * @notice Cast executive vote on proposal
     * @param proposalId Proposal to vote on
     * @param choice Vote choice
     */
    function castExecutiveVote(
        uint256 proposalId,
        WeightedVotingEngine.VoteChoice choice
    ) external nonReentrant {
        ExecutiveProposal storage proposal = proposals[proposalId];
        require(proposal.id != 0, "Proposal doesn't exist");
        require(block.timestamp <= proposal.votingEndTime, "Voting period ended");
        require(!proposal.executed && !proposal.cancelled, "Proposal not active");

        // Get executive details
        ExecutiveRoles.Executive memory exec = executiveRoles.getExecutive(msg.sender);
        require(exec.active && exec.role != ExecutiveRoles.ExecutiveRole.NONE, "Not active executive");
        require(exec.role != ExecutiveRoles.ExecutiveRole.CEO, "CEO uses emergency override");

        ExecutiveVoting storage voting = executiveVotings[proposalId];
        require(voting.votes[msg.sender] == WeightedVotingEngine.VoteChoice.NONE, "Already voted");

        // Cast vote through voting engine
        votingEngine.castVote(proposalId, choice);

        // Update local voting state
        voting.votes[msg.sender] = choice;
        voting.participationWeight += exec.weight;

        if (choice == WeightedVotingEngine.VoteChoice.FOR) {
            voting.forWeight += exec.weight;
        } else if (choice == WeightedVotingEngine.VoteChoice.AGAINST) {
            voting.againstWeight += exec.weight;
        } else if (choice == WeightedVotingEngine.VoteChoice.ABSTAIN) {
            voting.abstainWeight += exec.weight;
        }

        emit ExecutiveVoteCast(proposalId, msg.sender, exec.role, choice, exec.weight);
    }

    /**
     * @notice Specialist approval for financial/security proposals
     * @param proposalId Proposal to approve
     */
    function giveSpecialistApproval(uint256 proposalId) external {
        ExecutiveProposal storage proposal = proposals[proposalId];
        require(proposal.id != 0, "Proposal doesn't exist");
        require(proposal.requiresSpecialistApproval, "No specialist approval required");
        require(!proposal.specialistApproved, "Already approved by specialist");
        require(msg.sender == proposal.requiredSpecialist, "Not the required specialist");

        proposal.specialistApproved = true;

        ExecutiveRoles.Executive memory exec = executiveRoles.getExecutive(msg.sender);
        emit SpecialistApprovalGiven(proposalId, msg.sender, exec.role);
    }

    /**
     * @notice Execute approved executive proposal
     * @param proposalId Proposal to execute
     */
    function executeExecutiveProposal(uint256 proposalId) external nonReentrant {
        ExecutiveProposal storage proposal = proposals[proposalId];
        require(proposal.id != 0, "Proposal doesn't exist");
        require(!proposal.executed, "Already executed");
        require(!proposal.cancelled, "Proposal cancelled");
        require(block.timestamp > proposal.votingEndTime, "Voting still active");
        require(proposal.specialistApproved, "Specialist approval required");

        // Check execution delay
        require(
            block.timestamp >= proposal.votingEndTime + proposal.executionDelay,
            "Execution delay not met"
        );

        // Check if proposal passed
        bool passed = _checkProposalPassed(proposalId);
        require(passed, "Proposal did not pass");

        // Final constitutional validation
        require(
            constitution.validateAction(proposal.target, proposal.callData, proposal.value),
            "Constitutional validation failed at execution"
        );

        // Mark as executed before external call
        proposal.executed = true;
        executiveVotings[proposalId].finalized = true;
        executiveVotings[proposalId].passed = true;

        // Execute the proposal
        (bool success, ) = proposal.target.call{value: proposal.value}(proposal.callData);

        emit ExecutiveProposalExecuted(proposalId, msg.sender, success);

        // Revert if execution failed (after event for transparency)
        require(success, "Proposal execution failed");
    }

    /**
     * @notice CEO emergency override of executive voting
     * @param proposalId Proposal to override
     * @param reason Emergency reason
     */
    function ceoEmergencyOverride(
        uint256 proposalId,
        string memory reason
    ) external nonReentrant {
        require(
            executiveRoles.hasRole(executiveRoles.CEO_ROLE(), msg.sender),
            "Only CEO can emergency override"
        );
        require(bytes(reason).length > 0, "Reason required");

        ExecutiveProposal storage proposal = proposals[proposalId];
        require(proposal.id != 0, "Proposal doesn't exist");
        require(!proposal.executed, "Already executed");
        require(!proposal.cancelled, "Proposal cancelled");

        // Emergency override still requires constitutional validation
        require(
            constitution.validateAction(proposal.target, proposal.callData, proposal.value),
            "CEO cannot override constitutional constraints"
        );

        // Mark as executed via emergency override
        proposal.executed = true;
        executiveVotings[proposalId].finalized = true;
        executiveVotings[proposalId].passed = true;

        emit CEOEmergencyOverride(proposalId, msg.sender, reason);

        // Execute the proposal
        (bool success, ) = proposal.target.call{value: proposal.value}(proposal.callData);

        emit ExecutiveProposalExecuted(proposalId, msg.sender, success);
        require(success, "Emergency override execution failed");
    }

    /**
     * @notice Delegate proposal to community governance
     * @param proposalId Executive proposal to delegate
     * @param reason Reason for delegation
     */
    function delegateToKnowledgeHierarchy(
        uint256 proposalId,
        string memory reason
    ) external {
        require(
            executiveRoles.isActiveExecutive(msg.sender) ||
            executiveRoles.hasRole(executiveRoles.GOVERNANCE_ROLE(), msg.sender),
            "Not authorized to delegate"
        );
        require(bytes(reason).length > 0, "Delegation reason required");

        ExecutiveProposal storage proposal = proposals[proposalId];
        require(proposal.id != 0, "Proposal doesn't exist");
        require(!proposal.executed, "Already executed");

        // Cancel executive proposal
        proposal.cancelled = true;

        // Create equivalent proposal in KnowledgeHierarchy
        uint256 communityProposalId = knowledgeHierarchy.createProposal(
            string(abi.encodePacked("Delegated: ", proposal.title, " - ", reason))
        );

        emit ProposalDelegatedToCommunity(proposalId, reason);
    }

    /**
     * @notice Check if executive proposal passed voting
     * @param proposalId Proposal to check
     * @return passed Whether proposal passed
     */
    function _checkProposalPassed(uint256 proposalId) internal view returns (bool passed) {
        ExecutiveProposal storage proposal = proposals[proposalId];
        ExecutiveVoting storage voting = executiveVotings[proposalId];

        uint256 threshold = proposalThresholds[proposal.proposalType];
        uint256 totalActiveWeight = executiveRoles.totalActiveWeight();

        // Check quorum (50% participation)
        bool hasQuorum = (voting.participationWeight * 10000) >= (totalActiveWeight * 5000);
        if (!hasQuorum) return false;

        // Check threshold based on proposal type
        uint256 totalVotes = voting.forWeight + voting.againstWeight;
        if (totalVotes == 0) return false;

        bool meetsThreshold = (voting.forWeight * 10000) >= (totalVotes * threshold);

        return meetsThreshold;
    }

    /**
     * @notice Get proposal details
     * @param proposalId Proposal to query
     * @return proposal Proposal struct
     */
    function getExecutiveProposal(uint256 proposalId) external view returns (ExecutiveProposal memory proposal) {
        return proposals[proposalId];
    }

    /**
     * @notice Get voting details for proposal
     * @param proposalId Proposal to query
     * @return forWeight Weight voting FOR
     * @return againstWeight Weight voting AGAINST
     * @return abstainWeight Weight abstaining
     * @return participation Total participation
     * @return passed Whether proposal passed
     */
    function getVotingResults(uint256 proposalId) external view returns (
        uint256 forWeight,
        uint256 againstWeight,
        uint256 abstainWeight,
        uint256 participation,
        bool passed
    ) {
        ExecutiveVoting storage voting = executiveVotings[proposalId];
        forWeight = voting.forWeight;
        againstWeight = voting.againstWeight;
        abstainWeight = voting.abstainWeight;
        participation = voting.participationWeight;
        passed = _checkProposalPassed(proposalId);
    }

    /**
     * @notice Update proposal thresholds (governance only)
     * @param proposalType Type to update
     * @param newThreshold New threshold in basis points
     */
    function updateProposalThreshold(
        ExecutiveProposalType proposalType,
        uint256 newThreshold
    ) external {
        require(
            executiveRoles.hasRole(executiveRoles.GOVERNANCE_ROLE(), msg.sender),
            "Only governance can update thresholds"
        );
        require(newThreshold <= 10000, "Threshold cannot exceed 100%");

        proposalThresholds[proposalType] = newThreshold;
    }

    /**
     * @notice Get comprehensive governance statistics
     * @return totalProposals Total proposals created
     * @return activeProposals Proposals currently being voted on
     * @return executedProposals Successfully executed proposals
     * @return totalWeight Current total executive voting weight
     */
    function getGovernanceStatistics() external view returns (
        uint256 totalProposals,
        uint256 activeProposals,
        uint256 executedProposals,
        uint256 totalWeight
    ) {
        totalProposals = proposalCounter;
        totalWeight = executiveRoles.totalActiveWeight();

        // Count active and executed proposals
        for (uint256 i = 1; i <= proposalCounter; i++) {
            if (!proposals[i].executed && !proposals[i].cancelled &&
                block.timestamp <= proposals[i].votingEndTime) {
                activeProposals++;
            } else if (proposals[i].executed) {
                executedProposals++;
            }
        }
    }
}