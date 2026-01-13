// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./settings/GovernanceSettings.sol";
import "./constitution/DAIO_Constitution.sol";
import "./treasury/Treasury.sol";

/**
 * @title DAIOGovernance
 * @notice Core governance contract for Decentralized Autonomous Intelligence Organization
 * @dev Modular orchestration system for multiple projects (FinancialMind, mindX, cryptoAGI, etc.)
 * @dev Integrates with GovernanceSettings, DAIO_Constitution, and Treasury
 */
contract DAIOGovernance {
    enum ProposalType {
        Generic,           // Generic proposal
        Treasury,          // Treasury allocation
        AgentRegistry,     // Agent registration/removal
        ProjectExtension,  // Project-specific extension
        CrossProject       // Cross-project coordination
    }
    
    enum ProposalStatus {
        Pending,      // Proposal created, voting not started
        Active,       // Voting active
        Succeeded,    // Voting succeeded, ready for execution
        Defeated,     // Voting failed
        Executed,     // Proposal executed
        Cancelled     // Proposal cancelled
    }
    
    struct Proposal {
        uint256 proposalId;
        address proposer;
        string title;
        string description;
        ProposalType proposalType;
        string projectId;          // Project identifier (e.g., "financialmind", "mindx", "cryptoagi")
        uint256 startBlock;
        uint256 endBlock;
        uint256 forVotes;
        uint256 againstVotes;
        uint256 abstainVotes;
        ProposalStatus status;
        bytes executionCalldata;   // Execution calldata
        address target;           // Target contract for execution
        mapping(address => bool) hasVoted;
        mapping(address => uint256) votes;  // Votes cast by each address
    }
    
    mapping(uint256 => Proposal) public proposals;
    mapping(string => bool) public registeredProjects;  // Registered project IDs
    mapping(address => uint256) public votingPower;      // Voting power per address
    
    // Treasury allocation parameters storage
    struct TreasuryAllocationParams {
        string projectId;
        address recipient;
        uint256 amount;
        address token;
    }
    mapping(uint256 => TreasuryAllocationParams) public treasuryAllocations;
    
    uint256 public proposalCount;
    
    // Integrated contracts
    GovernanceSettings public settings;
    DAIO_Constitution public constitution;
    address public treasury;
    
    address public owner;
    
    event ProposalCreated(
        uint256 indexed proposalId,
        address proposer,
        string title,
        ProposalType proposalType,
        string projectId
    );
    event VoteCast(
        uint256 indexed proposalId,
        address voter,
        uint256 votes,
        bool support
    );
    event ProposalExecuted(uint256 indexed proposalId);
    event ProposalCancelled(uint256 indexed proposalId);
    event ProjectRegistered(string projectId, address registrar);
    event SettingsUpdated(string indexed projectId);
    event TreasuryAllocationCreated(uint256 indexed proposalId, string indexed projectId, address recipient, uint256 amount);
    
    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner");
        _;
    }
    
    modifier onlyRegisteredProject(string memory projectId) {
        require(registeredProjects[projectId], "Project not registered");
        _;
    }
    
    constructor(
        address _settings,
        address _constitution,
        address _treasury
    ) {
        require(_settings != address(0), "Invalid settings");
        require(_constitution != address(0), "Invalid constitution");
        require(_treasury != address(0), "Invalid treasury");
        
        owner = msg.sender;
        settings = GovernanceSettings(_settings);
        constitution = DAIO_Constitution(_constitution);
        treasury = _treasury;
    }
    
    /**
     * @notice Register a project with DAIO
     * @param projectId Project identifier (e.g., "financialmind", "mindx", "cryptoagi")
     */
    function registerProject(string memory projectId) external onlyOwner {
        require(!registeredProjects[projectId], "Project already registered");
        registeredProjects[projectId] = true;
        emit ProjectRegistered(projectId, msg.sender);
    }
    
    /**
     * @notice Set voting power for an address
     * @param voter Address to set voting power for
     * @param power Voting power amount
     */
    function setVotingPower(address voter, uint256 power) external onlyOwner {
        votingPower[voter] = power;
    }
    
    /**
     * @notice Create a new proposal
     * @param title Proposal title
     * @param description Proposal description
     * @param proposalType Type of proposal
     * @param projectId Project identifier (empty for cross-project)
     * @param target Target contract address for execution
     * @param executionData Execution calldata
     * @return proposalId The created proposal ID
     */
    function createProposal(
        string memory title,
        string memory description,
        ProposalType proposalType,
        string memory projectId,
        address target,
        bytes memory executionData
    ) external returns (uint256) {
        if (bytes(projectId).length > 0) {
            require(registeredProjects[projectId], "Project not registered");
        }
        
        // Check proposal threshold
        GovernanceSettings.Settings memory projectSettings = settings.getSettings(projectId);
        require(
            votingPower[msg.sender] >= projectSettings.proposalThreshold,
            "Insufficient voting power"
        );
        
        proposalCount++;
        uint256 proposalId = proposalCount;
        
        Proposal storage proposal = proposals[proposalId];
        proposal.proposalId = proposalId;
        proposal.proposer = msg.sender;
        proposal.title = title;
        proposal.description = description;
        proposal.proposalType = proposalType;
        proposal.projectId = projectId;
        proposal.startBlock = block.number;
        proposal.endBlock = block.number + projectSettings.votingPeriod;
        proposal.status = ProposalStatus.Active;
        proposal.target = target;
        proposal.executionCalldata = executionData;
        
        emit ProposalCreated(proposalId, msg.sender, title, proposalType, projectId);
        return proposalId;
    }
    
    /**
     * @notice Create treasury allocation proposal
     */
    function createTreasuryAllocationProposal(
        string memory title,
        string memory description,
        string memory projectId,
        address recipient,
        uint256 amount,
        address token
    ) external returns (uint256) {
        require(registeredProjects[projectId], "Project not registered");
        require(recipient != address(0), "Invalid recipient");
        require(amount > 0, "Invalid amount");
        
        // Create proposal
        bytes memory executionData = abi.encodeWithSignature(
            "createAllocation(uint256,string,address,uint256,address)",
            0,  // Will be set after proposal creation
            projectId,
            recipient,
            amount,
            token
        );
        
        // Get settings for proposal threshold check
        GovernanceSettings.Settings memory projectSettings = settings.getSettings(projectId);
        require(
            votingPower[msg.sender] >= projectSettings.proposalThreshold,
            "Insufficient voting power"
        );
        
        proposalCount++;
        uint256 proposalId = proposalCount;
        
        Proposal storage proposal = proposals[proposalId];
        proposal.proposalId = proposalId;
        proposal.proposer = msg.sender;
        proposal.title = title;
        proposal.description = description;
        proposal.proposalType = ProposalType.Treasury;
        proposal.projectId = projectId;
        proposal.startBlock = block.number;
        proposal.endBlock = block.number + projectSettings.votingPeriod;
        proposal.status = ProposalStatus.Active;
        proposal.target = treasury;
        proposal.executionCalldata = executionData;
        
        // Store treasury allocation parameters
        treasuryAllocations[proposalId] = TreasuryAllocationParams({
            projectId: projectId,
            recipient: recipient,
            amount: amount,
            token: token
        });
        
        emit ProposalCreated(proposalId, msg.sender, title, ProposalType.Treasury, projectId);
        emit TreasuryAllocationCreated(proposalId, projectId, recipient, amount);
        return proposalId;
    }
    
    /**
     * @notice Vote on a proposal
     * @param proposalId Proposal identifier
     * @param support True for yes, false for no
     */
    function vote(uint256 proposalId, bool support) external {
        Proposal storage proposal = proposals[proposalId];
        require(proposal.status == ProposalStatus.Active, "Proposal not active");
        require(block.number < proposal.endBlock, "Voting ended");
        require(!proposal.hasVoted[msg.sender], "Already voted");
        
        GovernanceSettings.Settings memory projectSettings = settings.getSettings(proposal.projectId);
        require(
            votingPower[msg.sender] >= projectSettings.minVotingPower,
            "Insufficient voting power"
        );
        
        uint256 votes = votingPower[msg.sender];
        proposal.hasVoted[msg.sender] = true;
        proposal.votes[msg.sender] = votes;
        
        if (support) {
            proposal.forVotes += votes;
        } else {
            proposal.againstVotes += votes;
        }
        
        emit VoteCast(proposalId, msg.sender, votes, support);
        
        // Check if voting should end
        _checkProposalStatus(proposalId);
    }
    
    /**
     * @notice Check and update proposal status (public function for status updates)
     * @param proposalId Proposal identifier
     */
    function checkProposalStatus(uint256 proposalId) external {
        Proposal storage proposal = proposals[proposalId];
        require(block.number >= proposal.endBlock, "Voting not ended");
        _checkProposalStatus(proposalId);
    }
    
    /**
     * @notice Execute a successful proposal
     * @param proposalId Proposal identifier
     */
    function executeProposal(uint256 proposalId) external {
        Proposal storage proposal = proposals[proposalId];
        require(block.number >= proposal.endBlock, "Voting not ended");
        
        // Check and update proposal status if still active
        if (proposal.status == ProposalStatus.Active) {
            _checkProposalStatus(proposalId);
        }
        
        require(proposal.status == ProposalStatus.Succeeded, "Proposal not succeeded");
        
        proposal.status = ProposalStatus.Executed;
        
        // Handle treasury allocations specially
        if (proposal.proposalType == ProposalType.Treasury && proposal.target == address(treasury)) {
            TreasuryAllocationParams memory params = treasuryAllocations[proposalId];
            require(params.recipient != address(0), "Treasury allocation params not found");
            
            // Validate against constitution
            require(
                constitution.validateAction(params.recipient, proposal.executionCalldata, params.amount),
                "Constitutional violation"
            );
            
            Treasury(payable(treasury)).createAllocation(proposalId, params.projectId, params.recipient, params.amount, params.token);
        } else if (proposal.target != address(0) && proposal.executionCalldata.length > 0) {
            // Execute other proposals
            (bool success, ) = proposal.target.call(proposal.executionCalldata);
            require(success, "Execution failed");
        }
        
        emit ProposalExecuted(proposalId);
    }
    
    /**
     * @notice Update governance settings (requires proposal)
     */
    function updateGovernanceSettings(
        string memory projectId,
        uint256 votingPeriod,
        uint256 quorumThreshold,
        uint256 approvalThreshold,
        uint256 timelockDelay,
        uint256 proposalThreshold,
        uint256 minVotingPower
    ) external onlyOwner {
        settings.updateProjectSettings(
            projectId,
            votingPeriod,
            quorumThreshold,
            approvalThreshold,
            timelockDelay,
            proposalThreshold,
            minVotingPower
        );
        emit SettingsUpdated(projectId);
    }
    
    /**
     * @notice Cancel a proposal (only proposer or owner)
     * @param proposalId Proposal identifier
     */
    function cancelProposal(uint256 proposalId) external {
        Proposal storage proposal = proposals[proposalId];
        require(
            proposal.proposer == msg.sender || msg.sender == owner,
            "Not authorized"
        );
        require(
            proposal.status == ProposalStatus.Pending || proposal.status == ProposalStatus.Active,
            "Cannot cancel"
        );
        
        proposal.status = ProposalStatus.Cancelled;
        emit ProposalCancelled(proposalId);
    }
    
    /**
     * @notice Check and update proposal status
     * @param proposalId Proposal identifier
     */
    function _checkProposalStatus(uint256 proposalId) internal {
        Proposal storage proposal = proposals[proposalId];
        
        if (block.number >= proposal.endBlock) {
            uint256 totalVotes = proposal.forVotes + proposal.againstVotes;
            uint256 totalPower = _getTotalVotingPower();
            
            // Get project-specific settings
            GovernanceSettings.Settings memory projectSettings = settings.getSettings(proposal.projectId);
            
            // Check quorum
            uint256 quorum = totalPower > 0 ? (totalVotes * 10000) / totalPower : 0;
            bool hasQuorum = quorum >= projectSettings.quorumThreshold;
            
            // Check approval
            uint256 approval = totalVotes > 0 ? (proposal.forVotes * 10000) / totalVotes : 0;
            bool isApproved = approval >= projectSettings.approvalThreshold;
            
            if (hasQuorum && isApproved) {
                proposal.status = ProposalStatus.Succeeded;
            } else {
                proposal.status = ProposalStatus.Defeated;
            }
        }
    }
    
    /**
     * @notice Get total voting power (simplified - should be calculated from token holdings, etc.)
     * @return total Total voting power
     */
    function _getTotalVotingPower() internal view returns (uint256) {
        // Simplified implementation - should integrate with token contract
        return 1000000;  // Placeholder
    }
    
    /**
     * @notice Get proposal details
     * @param proposalId Proposal identifier
     * @return proposer Proposer address
     * @return title Proposal title
     * @return status Proposal status
     * @return forVotes For votes
     * @return againstVotes Against votes
     */
    function getProposal(uint256 proposalId) external view returns (
        address proposer,
        string memory title,
        ProposalStatus status,
        uint256 forVotes,
        uint256 againstVotes
    ) {
        Proposal storage proposal = proposals[proposalId];
        return (
            proposal.proposer,
            proposal.title,
            proposal.status,
            proposal.forVotes,
            proposal.againstVotes
        );
    }
}
