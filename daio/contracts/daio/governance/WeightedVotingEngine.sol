// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "./ExecutiveRoles.sol";

/**
 * @title WeightedVotingEngine
 * @notice Implements sophisticated consensus calculations for executive voting
 * @dev Handles weighted voting with 2/3 supermajority and veto powers for Seven Soldiers
 */
contract WeightedVotingEngine is Ownable, ReentrancyGuard {

    // Voting status enumeration
    enum VoteChoice {
        NONE,       // 0 - No vote cast
        FOR,        // 1 - Vote in favor
        AGAINST,    // 2 - Vote against
        ABSTAIN     // 3 - Abstain from voting
    }

    // Proposal voting state
    struct ProposalVote {
        uint256 totalWeightFor;        // Total weight voting FOR
        uint256 totalWeightAgainst;    // Total weight voting AGAINST
        uint256 totalWeightAbstain;    // Total weight abstaining
        uint256 totalParticipation;    // Total weight that participated
        mapping(address => VoteChoice) votes;  // Individual votes
        mapping(address => uint256) voteWeights;  // Weight used per voter
        bool hasSecurityVeto;          // CISO security veto activated
        bool hasRiskVeto;              // CRO risk veto activated
        uint256 vetoTimestamp;         // When veto was activated
    }

    // Consensus thresholds
    uint256 public constant SUPERMAJORITY_THRESHOLD = 6667;  // 66.67% in basis points
    uint256 public constant QUORUM_THRESHOLD = 5000;         // 50% in basis points
    uint256 public constant BASIS_POINTS = 10000;            // 100% = 10000 basis points
    uint256 public constant VETO_OVERRIDE_DELAY = 7 days;    // Time to override veto

    // Integration with ExecutiveRoles
    ExecutiveRoles public immutable executiveRoles;

    // Storage
    mapping(uint256 => ProposalVote) public proposalVotes;
    mapping(uint256 => bool) public proposalFinalized;

    // Events
    event VoteCast(
        uint256 indexed proposalId,
        address indexed voter,
        ExecutiveRoles.ExecutiveRole indexed role,
        VoteChoice choice,
        uint256 weight
    );
    event VetoActivated(
        uint256 indexed proposalId,
        address indexed vetoer,
        ExecutiveRoles.ExecutiveRole indexed role,
        string reason
    );
    event VetoOverridden(
        uint256 indexed proposalId,
        string reason
    );
    event ProposalResultCalculated(
        uint256 indexed proposalId,
        bool passed,
        uint256 totalFor,
        uint256 totalAgainst,
        uint256 participation,
        bool securityVeto,
        bool riskVeto
    );

    constructor(address _executiveRoles) Ownable(msg.sender) {
        require(_executiveRoles != address(0), "Invalid ExecutiveRoles address");
        executiveRoles = ExecutiveRoles(_executiveRoles);
    }

    /**
     * @notice Cast a vote on a proposal
     * @param proposalId Proposal to vote on
     * @param choice Vote choice (FOR, AGAINST, ABSTAIN)
     */
    function castVote(
        uint256 proposalId,
        VoteChoice choice
    ) public nonReentrant {
        require(choice != VoteChoice.NONE, "Invalid vote choice");
        require(!proposalFinalized[proposalId], "Proposal already finalized");

        // Get executive details
        ExecutiveRoles.Executive memory exec = executiveRoles.getExecutive(msg.sender);
        require(exec.active && exec.role != ExecutiveRoles.ExecutiveRole.NONE, "Not an active executive");
        require(exec.role != ExecutiveRoles.ExecutiveRole.CEO, "CEO votes via emergency override");

        ProposalVote storage proposal = proposalVotes[proposalId];

        // Check if already voted
        require(proposal.votes[msg.sender] == VoteChoice.NONE, "Already voted");

        // Record vote
        proposal.votes[msg.sender] = choice;
        proposal.voteWeights[msg.sender] = exec.weight;

        // Update vote tallies
        if (choice == VoteChoice.FOR) {
            proposal.totalWeightFor += exec.weight;
        } else if (choice == VoteChoice.AGAINST) {
            proposal.totalWeightAgainst += exec.weight;
        } else if (choice == VoteChoice.ABSTAIN) {
            proposal.totalWeightAbstain += exec.weight;
        }

        proposal.totalParticipation += exec.weight;

        emit VoteCast(proposalId, msg.sender, exec.role, choice, exec.weight);
    }

    /**
     * @notice Activate security or risk veto power
     * @param proposalId Proposal to veto
     * @param reason Reason for the veto
     */
    function activateVeto(
        uint256 proposalId,
        string memory reason
    ) external nonReentrant {
        require(bytes(reason).length > 0, "Veto reason required");
        require(!proposalFinalized[proposalId], "Proposal already finalized");

        // Get executive details
        ExecutiveRoles.Executive memory exec = executiveRoles.getExecutive(msg.sender);
        require(exec.active && exec.hasVetoPower, "No veto power");

        ProposalVote storage proposal = proposalVotes[proposalId];

        // Activate appropriate veto
        if (exec.role == ExecutiveRoles.ExecutiveRole.CISO) {
            require(!proposal.hasSecurityVeto, "Security veto already active");
            proposal.hasSecurityVeto = true;
        } else if (exec.role == ExecutiveRoles.ExecutiveRole.CRO) {
            require(!proposal.hasRiskVeto, "Risk veto already active");
            proposal.hasRiskVeto = true;
        } else {
            revert("Invalid veto role");
        }

        proposal.vetoTimestamp = block.timestamp;

        emit VetoActivated(proposalId, msg.sender, exec.role, reason);
    }

    /**
     * @notice Override veto with supermajority after delay period
     * @param proposalId Proposal to override veto for
     * @param reason Reason for override
     */
    function overrideVeto(
        uint256 proposalId,
        string memory reason
    ) external {
        require(bytes(reason).length > 0, "Override reason required");
        require(!proposalFinalized[proposalId], "Proposal already finalized");

        // Only governance or CEO can override veto
        require(
            executiveRoles.hasRole(executiveRoles.GOVERNANCE_ROLE(), msg.sender) ||
            executiveRoles.hasRole(executiveRoles.CEO_ROLE(), msg.sender),
            "Not authorized to override"
        );

        ProposalVote storage proposal = proposalVotes[proposalId];
        require(
            proposal.hasSecurityVeto || proposal.hasRiskVeto,
            "No active veto to override"
        );
        require(
            block.timestamp >= proposal.vetoTimestamp + VETO_OVERRIDE_DELAY,
            "Veto override delay not met"
        );

        // Check if supermajority supports override
        (bool hasMajority, , , ) = calculateResult(proposalId);
        require(hasMajority, "Supermajority required for veto override");

        // Clear vetoes
        proposal.hasSecurityVeto = false;
        proposal.hasRiskVeto = false;

        emit VetoOverridden(proposalId, reason);
    }

    /**
     * @notice Calculate voting result for a proposal
     * @param proposalId Proposal to calculate result for
     * @return passed Whether proposal passed
     * @return totalFor Total weight voting FOR
     * @return totalAgainst Total weight voting AGAINST
     * @return participation Total participation weight
     */
    function calculateResult(uint256 proposalId) public view returns (
        bool passed,
        uint256 totalFor,
        uint256 totalAgainst,
        uint256 participation
    ) {
        ProposalVote storage proposal = proposalVotes[proposalId];

        totalFor = proposal.totalWeightFor;
        totalAgainst = proposal.totalWeightAgainst;
        participation = proposal.totalParticipation;

        // Get total active executive weight
        uint256 totalActiveWeight = executiveRoles.totalActiveWeight();

        // Check quorum (50% participation)
        bool hasQuorum = (participation * BASIS_POINTS) >= (totalActiveWeight * QUORUM_THRESHOLD);

        // Check supermajority (66.67% of votes cast)
        bool hasMajority = false;
        if (totalFor + totalAgainst > 0) {
            hasMajority = (totalFor * BASIS_POINTS) >= ((totalFor + totalAgainst) * SUPERMAJORITY_THRESHOLD);
        }

        // Check vetoes
        bool vetoActive = proposal.hasSecurityVeto || proposal.hasRiskVeto;

        // Proposal passes if: quorum met, supermajority achieved, no active vetoes
        passed = hasQuorum && hasMajority && !vetoActive;
    }

    /**
     * @notice Get detailed voting information for a proposal
     * @param proposalId Proposal to get info for
     * @return totalFor Total weight voting FOR
     * @return totalAgainst Total weight voting AGAINST
     * @return totalAbstain Total weight abstaining
     * @return participation Total participation weight
     * @return totalActiveWeight Total active executive weight
     * @return quorumThreshold Quorum threshold required
     * @return majorityThreshold Majority threshold required
     * @return hasQuorum Whether quorum is met
     * @return hasMajority Whether majority is achieved
     * @return securityVeto Whether security veto is active
     * @return riskVeto Whether risk veto is active
     * @return canOverrideVeto Whether veto can be overridden
     */
    function getVotingInfo(uint256 proposalId) external view returns (
        uint256 totalFor,
        uint256 totalAgainst,
        uint256 totalAbstain,
        uint256 participation,
        uint256 totalActiveWeight,
        uint256 quorumThreshold,
        uint256 majorityThreshold,
        bool hasQuorum,
        bool hasMajority,
        bool securityVeto,
        bool riskVeto,
        bool canOverrideVeto
    ) {
        ProposalVote storage proposal = proposalVotes[proposalId];

        totalFor = proposal.totalWeightFor;
        totalAgainst = proposal.totalWeightAgainst;
        totalAbstain = proposal.totalWeightAbstain;
        participation = proposal.totalParticipation;
        totalActiveWeight = executiveRoles.totalActiveWeight();

        // Calculate thresholds
        quorumThreshold = (totalActiveWeight * QUORUM_THRESHOLD) / BASIS_POINTS;
        majorityThreshold = ((totalFor + totalAgainst) * SUPERMAJORITY_THRESHOLD) / BASIS_POINTS;

        // Check conditions
        hasQuorum = participation >= quorumThreshold;
        hasMajority = totalFor >= majorityThreshold && (totalFor + totalAgainst) > 0;
        securityVeto = proposal.hasSecurityVeto;
        riskVeto = proposal.hasRiskVeto;
        canOverrideVeto = (securityVeto || riskVeto) &&
                         (block.timestamp >= proposal.vetoTimestamp + VETO_OVERRIDE_DELAY) &&
                         hasMajority;
    }

    /**
     * @notice Get individual vote details
     * @param proposalId Proposal ID
     * @param voter Executive address
     * @return choice Vote choice made
     * @return weight Voting weight used
     */
    function getIndividualVote(uint256 proposalId, address voter) external view returns (
        VoteChoice choice,
        uint256 weight
    ) {
        ProposalVote storage proposal = proposalVotes[proposalId];
        choice = proposal.votes[voter];
        weight = proposal.voteWeights[voter];
    }

    /**
     * @notice Check if proposal meets all Seven Soldiers consensus requirements
     * @param proposalId Proposal to check
     * @return meetsConsensus Whether 2/3 supermajority consensus is achieved
     */
    function meetsSevenSoldiersConsensus(uint256 proposalId) external view returns (bool) {
        (bool passed, , , ) = calculateResult(proposalId);
        return passed;
    }

    /**
     * @notice Finalize a proposal vote (can only be called by governance)
     * @param proposalId Proposal to finalize
     */
    function finalizeProposal(uint256 proposalId) external {
        require(
            executiveRoles.hasRole(executiveRoles.GOVERNANCE_ROLE(), msg.sender),
            "Only governance can finalize"
        );
        require(!proposalFinalized[proposalId], "Already finalized");

        (bool passed, uint256 totalFor, uint256 totalAgainst, uint256 participation) = calculateResult(proposalId);

        ProposalVote storage proposal = proposalVotes[proposalId];

        proposalFinalized[proposalId] = true;

        emit ProposalResultCalculated(
            proposalId,
            passed,
            totalFor,
            totalAgainst,
            participation,
            proposal.hasSecurityVeto,
            proposal.hasRiskVeto
        );
    }

    /**
     * @notice Batch vote casting for multiple proposals
     * @param proposalIds Array of proposal IDs
     * @param choices Array of vote choices
     */
    function batchVote(
        uint256[] memory proposalIds,
        VoteChoice[] memory choices
    ) external {
        require(proposalIds.length == choices.length, "Array length mismatch");
        require(proposalIds.length <= 10, "Too many proposals");

        for (uint i = 0; i < proposalIds.length; i++) {
            castVote(proposalIds[i], choices[i]);
        }
    }

    /**
     * @notice Emergency CEO override (bypasses Seven Soldiers consensus)
     * @param proposalId Proposal to override
     * @param reason Emergency reason
     */
    function emergencyOverride(
        uint256 proposalId,
        string memory reason
    ) external {
        require(
            executiveRoles.hasRole(executiveRoles.CEO_ROLE(), msg.sender),
            "Only CEO can emergency override"
        );
        require(bytes(reason).length > 0, "Emergency reason required");
        require(!proposalFinalized[proposalId], "Proposal already finalized");

        // Note: Emergency override still subject to constitutional constraints
        // This is validated in ExecutiveGovernance contract

        proposalFinalized[proposalId] = true;

        emit ProposalResultCalculated(
            proposalId,
            true,  // CEO override passes proposal
            0, 0, 0,  // Vote tallies not relevant for override
            false, false  // Vetoes bypassed
        );
    }

    /**
     * @notice Get voting statistics across all active executives
     * @return totalExecutives Total number of executives
     * @return activeExecutives Number of active executives
     * @return totalWeight Total voting weight
     * @return quorumWeight Weight needed for quorum
     * @return majorityWeight Weight needed for majority
     */
    function getExecutiveVotingStats() external view returns (
        uint256 totalExecutives,
        uint256 activeExecutives,
        uint256 totalWeight,
        uint256 quorumWeight,
        uint256 majorityWeight
    ) {
        totalWeight = executiveRoles.totalActiveWeight();
        quorumWeight = (totalWeight * QUORUM_THRESHOLD) / BASIS_POINTS;
        majorityWeight = (totalWeight * SUPERMAJORITY_THRESHOLD) / BASIS_POINTS;

        // Count executives
        (totalWeight, majorityWeight, activeExecutives) = executiveRoles.getVotingStats();
        totalExecutives = activeExecutives; // Reusing variable, this is active count
    }

    /**
     * @notice Check if specific role combination can achieve consensus
     * @param roles Array of roles that would vote FOR
     * @return canAchieveMajority Whether this combination achieves 2/3 majority
     */
    function simulateVotingOutcome(
        ExecutiveRoles.ExecutiveRole[] memory roles
    ) external view returns (bool canAchieveMajority) {
        uint256 totalWeight = 0;

        // Calculate total weight of specified roles
        for (uint i = 0; i < roles.length; i++) {
            address holder = executiveRoles.getRoleHolder(roles[i]);
            if (holder != address(0)) {
                ExecutiveRoles.Executive memory exec = executiveRoles.getExecutive(holder);
                if (exec.active && exec.role != ExecutiveRoles.ExecutiveRole.CEO) {
                    totalWeight += exec.weight;
                }
            }
        }

        // Check if this weight achieves majority threshold
        uint256 majorityThreshold = executiveRoles.calculateMajorityThreshold();
        canAchieveMajority = totalWeight >= majorityThreshold;
    }
}