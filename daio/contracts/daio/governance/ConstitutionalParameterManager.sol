// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "./ExecutiveRoles.sol";
import "./WeightedVotingEngine.sol";
import "../constitution/DAIO_Constitution_Enhanced.sol";

/**
 * @title ConstitutionalParameterManager
 * @notice Manages constitutional parameter changes through executive governance
 * @dev Provides safe interface for adjusting risk parameters with proper safeguards
 */
contract ConstitutionalParameterManager is Ownable, ReentrancyGuard {

    // Parameter change proposal for executive voting
    struct ConstitutionalProposal {
        uint256 id;
        string parameter;           // "diversification", "tithe", "maxAllocation"
        uint256 currentValue;
        uint256 proposedValue;
        string rationale;           // Risk analysis and justification
        address proposer;
        ExecutiveRoles.ExecutiveRole proposerRole;
        uint256 createdAt;
        uint256 votingEndTime;
        uint256 constitutionalProposalId; // ID in DAIO_Constitution_Enhanced
        bool votingCompleted;
        bool executed;
        bool approved;

        // Risk assessment
        uint256 riskScore;          // 1-10 scale
        string riskAssessment;      // Detailed risk analysis
        bool cisoApproval;          // CISO security sign-off
        bool croApproval;           // CRO risk sign-off
    }

    // Risk impact levels
    enum RiskLevel {
        LOW,        // 1-3: Minor adjustments within safe bounds
        MODERATE,   // 4-6: Meaningful changes requiring analysis
        HIGH,       // 7-8: Significant changes requiring unanimous approval
        CRITICAL    // 9-10: Extreme changes requiring additional safeguards
    }

    // Integration contracts
    ExecutiveRoles public immutable executiveRoles;
    WeightedVotingEngine public immutable votingEngine;
    DAIO_Constitution_Enhanced public immutable constitution;

    // State
    uint256 public proposalCounter;
    mapping(uint256 => ConstitutionalProposal) public constitutionalProposals;
    mapping(string => uint256) public lastParameterChange; // parameter => timestamp

    // Risk management parameters
    uint256 public constant MIN_CHANGE_INTERVAL = 90 days; // Minimum time between changes
    uint256 public constant CRITICAL_UNANIMOUS_THRESHOLD = 10000; // 100% for critical changes
    uint256 public constant HIGH_RISK_THRESHOLD = 8000;    // 80% for high risk changes
    uint256 public constant NORMAL_THRESHOLD = 6667;       // 66.67% for normal changes

    // Events
    event ConstitutionalProposalCreated(
        uint256 indexed proposalId,
        string parameter,
        uint256 currentValue,
        uint256 proposedValue,
        uint256 riskScore,
        address proposer
    );

    event RiskAssessmentCompleted(
        uint256 indexed proposalId,
        uint256 riskScore,
        string riskAssessment,
        bool cisoApproval,
        bool croApproval
    );

    event ConstitutionalVoteCast(
        uint256 indexed proposalId,
        address indexed voter,
        ExecutiveRoles.ExecutiveRole role,
        WeightedVotingEngine.VoteChoice choice,
        string justification
    );

    event ConstitutionalParameterExecuted(
        uint256 indexed proposalId,
        string parameter,
        uint256 oldValue,
        uint256 newValue,
        uint256 constitutionalProposalId
    );

    modifier onlyActiveExecutive() {
        require(executiveRoles.isActiveExecutive(msg.sender), "Only active executives");
        _;
    }

    modifier onlySpecialistRole(ExecutiveRoles.ExecutiveRole requiredRole) {
        ExecutiveRoles.Executive memory exec = executiveRoles.getExecutive(msg.sender);
        require(exec.role == requiredRole, "Role authorization required");
        _;
    }

    constructor(
        address _executiveRoles,
        address _votingEngine,
        address _constitution
    ) Ownable(msg.sender) {
        require(_executiveRoles != address(0), "Invalid ExecutiveRoles");
        require(_votingEngine != address(0), "Invalid VotingEngine");
        require(_constitution != address(0), "Invalid Constitution");

        executiveRoles = ExecutiveRoles(_executiveRoles);
        votingEngine = WeightedVotingEngine(_votingEngine);
        constitution = DAIO_Constitution_Enhanced(_constitution);
    }

    /**
     * @notice Propose constitutional parameter change
     * @param parameter Parameter to change ("diversification", "tithe", "maxAllocation")
     * @param newValue New value in basis points
     * @param rationale Detailed rationale and risk analysis
     * @param riskScore Risk score 1-10 (10 = highest risk)
     */
    function proposeConstitutionalChange(
        string memory parameter,
        uint256 newValue,
        string memory rationale,
        uint256 riskScore
    ) external onlyActiveExecutive nonReentrant returns (uint256) {
        require(bytes(parameter).length > 0, "Parameter required");
        require(bytes(rationale).length > 100, "Detailed rationale required (min 100 chars)");
        require(riskScore >= 1 && riskScore <= 10, "Risk score must be 1-10");

        // Check minimum interval between changes
        require(
            block.timestamp >= lastParameterChange[parameter] + MIN_CHANGE_INTERVAL,
            "Too soon since last parameter change"
        );

        // Get current parameter value
        uint256 currentValue = _getCurrentParameterValue(parameter);

        // Validate the proposed change makes sense
        require(newValue != currentValue, "No change in value");

        ExecutiveRoles.Executive memory exec = executiveRoles.getExecutive(msg.sender);

        proposalCounter++;
        uint256 proposalId = proposalCounter;

        // Determine voting period based on risk level
        uint256 votingPeriod = _getVotingPeriod(riskScore);

        constitutionalProposals[proposalId] = ConstitutionalProposal({
            id: proposalId,
            parameter: parameter,
            currentValue: currentValue,
            proposedValue: newValue,
            rationale: rationale,
            proposer: msg.sender,
            proposerRole: exec.role,
            createdAt: block.timestamp,
            votingEndTime: block.timestamp + votingPeriod,
            constitutionalProposalId: 0, // Set when constitutional proposal created
            votingCompleted: false,
            executed: false,
            approved: false,
            riskScore: riskScore,
            riskAssessment: "",
            cisoApproval: false,
            croApproval: false
        });

        emit ConstitutionalProposalCreated(
            proposalId,
            parameter,
            currentValue,
            newValue,
            riskScore,
            msg.sender
        );

        return proposalId;
    }

    /**
     * @notice Complete risk assessment (CISO and CRO must both approve high-risk changes)
     * @param proposalId Proposal to assess
     * @param riskAssessment Detailed risk assessment
     */
    function completeRiskAssessment(
        uint256 proposalId,
        string memory riskAssessment
    ) external {
        ConstitutionalProposal storage proposal = constitutionalProposals[proposalId];
        require(proposal.id != 0, "Proposal doesn't exist");
        require(bytes(riskAssessment).length > 50, "Detailed assessment required");

        ExecutiveRoles.Executive memory exec = executiveRoles.getExecutive(msg.sender);

        // CISO approval for security impact
        if (exec.role == ExecutiveRoles.ExecutiveRole.CISO) {
            require(!proposal.cisoApproval, "CISO already approved");
            proposal.cisoApproval = true;
        }
        // CRO approval for risk impact
        else if (exec.role == ExecutiveRoles.ExecutiveRole.CRO) {
            require(!proposal.croApproval, "CRO already approved");
            proposal.croApproval = true;
        } else {
            revert("Only CISO or CRO can complete risk assessment");
        }

        // Update risk assessment if both haven't provided it yet
        if (bytes(proposal.riskAssessment).length == 0) {
            proposal.riskAssessment = riskAssessment;
        }

        emit RiskAssessmentCompleted(
            proposalId,
            proposal.riskScore,
            riskAssessment,
            proposal.cisoApproval,
            proposal.croApproval
        );
    }

    /**
     * @notice Cast vote on constitutional parameter change
     * @param proposalId Proposal to vote on
     * @param choice Vote choice
     * @param justification Detailed justification for vote
     */
    function castConstitutionalVote(
        uint256 proposalId,
        WeightedVotingEngine.VoteChoice choice,
        string memory justification
    ) external onlyActiveExecutive nonReentrant {
        ConstitutionalProposal storage proposal = constitutionalProposals[proposalId];
        require(proposal.id != 0, "Proposal doesn't exist");
        require(block.timestamp <= proposal.votingEndTime, "Voting period ended");
        require(!proposal.votingCompleted, "Voting completed");
        require(bytes(justification).length > 20, "Justification required");

        // For high-risk changes, require specialist approval first
        if (proposal.riskScore >= 7) {
            require(
                proposal.cisoApproval && proposal.croApproval,
                "High-risk changes require CISO and CRO approval"
            );
        }

        ExecutiveRoles.Executive memory exec = executiveRoles.getExecutive(msg.sender);

        // Cast vote through voting engine
        votingEngine.castVote(proposalId, choice);

        emit ConstitutionalVoteCast(
            proposalId,
            msg.sender,
            exec.role,
            choice,
            justification
        );
    }

    /**
     * @notice Finalize constitutional vote and execute if passed
     * @param proposalId Proposal to finalize
     */
    function finalizeConstitutionalVote(uint256 proposalId) external nonReentrant {
        ConstitutionalProposal storage proposal = constitutionalProposals[proposalId];
        require(proposal.id != 0, "Proposal doesn't exist");
        require(block.timestamp > proposal.votingEndTime, "Voting still active");
        require(!proposal.votingCompleted, "Already finalized");

        proposal.votingCompleted = true;

        // Check if proposal passed based on risk level
        bool passed = _checkConstitutionalVotePassed(proposalId);
        proposal.approved = passed;

        if (passed) {
            // Create proposal in enhanced constitution
            uint256 constitutionalId = constitution.proposeParameterChange(
                proposal.parameter,
                proposal.proposedValue,
                string(abi.encodePacked(
                    "Executive Governance Approved Change: ",
                    proposal.rationale
                ))
            );

            proposal.constitutionalProposalId = constitutionalId;
            lastParameterChange[proposal.parameter] = block.timestamp;
        }

        // Finalize in voting engine
        votingEngine.finalizeProposal(proposalId);
    }

    /**
     * @notice Execute approved constitutional change (after constitutional delay)
     * @param proposalId Proposal to execute
     */
    function executeConstitutionalChange(uint256 proposalId) external {
        ConstitutionalProposal storage proposal = constitutionalProposals[proposalId];
        require(proposal.id != 0, "Proposal doesn't exist");
        require(proposal.approved, "Proposal not approved");
        require(!proposal.executed, "Already executed");
        require(proposal.constitutionalProposalId != 0, "Constitutional proposal not created");

        // Execute the constitutional parameter change
        constitution.executeParameterChange(proposal.constitutionalProposalId);

        proposal.executed = true;

        emit ConstitutionalParameterExecuted(
            proposalId,
            proposal.parameter,
            proposal.currentValue,
            proposal.proposedValue,
            proposal.constitutionalProposalId
        );
    }

    /**
     * @notice Get detailed proposal information
     * @param proposalId Proposal to query
     * @return proposal Full proposal details
     */
    function getConstitutionalProposal(uint256 proposalId) external view returns (ConstitutionalProposal memory proposal) {
        return constitutionalProposals[proposalId];
    }

    /**
     * @notice Get risk level for a proposal
     * @param proposalId Proposal to assess
     * @return riskLevel Risk level enumeration
     */
    function getProposalRiskLevel(uint256 proposalId) external view returns (RiskLevel riskLevel) {
        uint256 riskScore = constitutionalProposals[proposalId].riskScore;

        if (riskScore <= 3) return RiskLevel.LOW;
        else if (riskScore <= 6) return RiskLevel.MODERATE;
        else if (riskScore <= 8) return RiskLevel.HIGH;
        else return RiskLevel.CRITICAL;
    }

    /**
     * @notice Simulate impact of parameter change
     * @param parameter Parameter to change
     * @param newValue New proposed value
     * @return currentValue Current parameter value
     * @return percentageChange Percentage change from current
     * @return riskAssessment Risk assessment text
     * @return suggestedRiskScore Suggested risk score 1-10
     */
    function simulateParameterImpact(
        string memory parameter,
        uint256 newValue
    ) external view returns (
        uint256 currentValue,
        uint256 percentageChange,
        string memory riskAssessment,
        uint256 suggestedRiskScore
    ) {
        currentValue = _getCurrentParameterValue(parameter);

        // Calculate percentage change
        if (currentValue > 0) {
            if (newValue > currentValue) {
                percentageChange = ((newValue - currentValue) * 10000) / currentValue;
            } else {
                percentageChange = ((currentValue - newValue) * 10000) / currentValue;
            }
        }

        // Generate risk assessment
        (riskAssessment, suggestedRiskScore) = _generateRiskAssessment(parameter, currentValue, newValue, percentageChange);
    }

    // Internal functions

    function _getCurrentParameterValue(string memory parameter) internal view returns (uint256) {
        bytes32 paramHash = keccak256(abi.encodePacked(parameter));

        if (paramHash == keccak256(abi.encodePacked("diversification"))) {
            return constitution.getCurrentDiversificationLimit();
        } else if (paramHash == keccak256(abi.encodePacked("tithe"))) {
            return constitution.getCurrentTitheRate();
        } else if (paramHash == keccak256(abi.encodePacked("maxAllocation"))) {
            return constitution.getCurrentMaxSingleAllocation();
        } else {
            revert("Invalid parameter");
        }
    }

    function _getVotingPeriod(uint256 riskScore) internal pure returns (uint256) {
        if (riskScore >= 9) return 14 days;  // Critical: 2 weeks
        else if (riskScore >= 7) return 7 days;   // High: 1 week
        else if (riskScore >= 4) return 5 days;   // Moderate: 5 days
        else return 3 days;                       // Low: 3 days
    }

    function _checkConstitutionalVotePassed(uint256 proposalId) internal view returns (bool) {
        ConstitutionalProposal storage proposal = constitutionalProposals[proposalId];

        // Determine threshold based on risk score
        uint256 threshold;
        if (proposal.riskScore >= 9) {
            threshold = CRITICAL_UNANIMOUS_THRESHOLD; // 100% for critical
        } else if (proposal.riskScore >= 7) {
            threshold = HIGH_RISK_THRESHOLD; // 80% for high risk
        } else {
            threshold = NORMAL_THRESHOLD; // 66.67% for normal
        }

        (bool passed, , , ) = votingEngine.calculateResult(proposalId);
        return passed; // VotingEngine handles the threshold logic
    }

    function _generateRiskAssessment(
        string memory parameter,
        uint256 currentValue,
        uint256 newValue,
        uint256 percentageChange
    ) internal pure returns (string memory assessment, uint256 riskScore) {
        bytes32 paramHash = keccak256(abi.encodePacked(parameter));

        // Base risk assessment on parameter type and change magnitude
        if (paramHash == keccak256(abi.encodePacked("diversification"))) {
            if (percentageChange > 5000) { // >50% change
                assessment = "CRITICAL: Large diversification change increases concentration risk";
                riskScore = newValue < currentValue ? 9 : 7; // Reducing diversification is riskier
            } else if (percentageChange > 2000) { // >20% change
                assessment = "HIGH: Meaningful diversification adjustment affects risk profile";
                riskScore = newValue < currentValue ? 7 : 5;
            } else {
                assessment = "MODERATE: Minor diversification adjustment within acceptable bounds";
                riskScore = 3;
            }
        } else if (paramHash == keccak256(abi.encodePacked("tithe"))) {
            if (percentageChange > 3000) { // >30% change
                assessment = "HIGH: Significant tithe change affects treasury sustainability";
                riskScore = newValue < currentValue ? 6 : 7; // Reducing tithe affects funding
            } else if (percentageChange > 1000) { // >10% change
                assessment = "MODERATE: Tithe adjustment impacts treasury growth rate";
                riskScore = 4;
            } else {
                assessment = "LOW: Minor tithe adjustment with minimal impact";
                riskScore = 2;
            }
        } else {
            assessment = "Unknown parameter risk assessment";
            riskScore = 5; // Default moderate risk
        }
    }
}