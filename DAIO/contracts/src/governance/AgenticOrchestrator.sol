// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "../identity/IDNFT.sol";

/**
 * @title AgenticOrchestrator
 * @dev Orchestration system for agent lifecycle and consensus management
 * @notice Manages agent creation, destruction, and updates through consensus mechanisms
 * @notice Integrates with IDNFT for agent identity management
 */
contract AgenticOrchestrator is ReentrancyGuard, Pausable, AccessControl {
    using ECDSA for bytes32;

    // Hierarchical Roles
    bytes32 public constant ORCHESTRATOR_ROLE = keccak256("ORCHESTRATOR_ROLE");
    bytes32 public constant CONSENSUS_ROLE = keccak256("CONSENSUS_ROLE");
    bytes32 public constant AGENT_CREATOR_ROLE = keccak256("AGENT_CREATOR_ROLE");
    bytes32 public constant AGENT_DESTROYER_ROLE = keccak256("AGENT_DESTROYER_ROLE");

    IDNFT public immutable idNFT; // Agent identity contract
    
    // Track minter role for IDNFT
    bool private _hasMinterRole;

    enum AgentState { 
        NonExistent, 
        Proposed, 
        Active, 
        Suspended, 
        Deprecated 
    }

    struct ConsensusThreshold {
        uint8 createThreshold;    // Percentage needed for creation (0-100)
        uint8 destroyThreshold;   // Percentage needed for destruction (0-100)
        uint8 updateThreshold;    // Percentage needed for updates (0-100)
        uint32 timelock;          // Time required before execution (seconds)
    }

    struct Agent {
        bytes32 agentId;
        address controller;       // Primary controlling address
        string agentType;         // Type/category of agent
        string purpose;           // Defined purpose/scope
        AgentState state;         // Current state
        uint256 idNFTTokenId;     // Linked IDNFT token ID
        uint40 creationTime;      // Creation timestamp
        uint40 lastUpdate;        // Last update timestamp
        bytes32[] capabilities;  // Assigned capabilities
        address[] authorizedCallers; // Addresses that can call this agent
        bool consensusRequired;   // Whether consensus is needed for actions
        mapping(bytes32 => bool) activeCapabilities;
    }

    struct Proposal {
        bytes32 proposalId;
        bytes32 targetAgentId;
        address proposer;
        string action;           // "create", "destroy", "update"
        bytes parameters;         // Encoded parameters for the action
        uint40 proposalTime;
        uint40 executionTime;
        uint16 approvalCount;
        uint16 rejectionCount;
        bool executed;
        bool canceled;
        mapping(address => bool) hasVoted;
    }

    // Storage
    mapping(bytes32 => Agent) private _agents;
    mapping(bytes32 => Proposal) private _proposals;
    mapping(string => ConsensusThreshold) private _consensusThresholds;
    mapping(bytes32 => bytes32[]) private _agentHierarchy;  // parent -> children
    mapping(bytes32 => bytes32) private _parentAgent;       // child -> parent
    mapping(bytes32 => uint256) private _proposalCount;
    
    // Events
    event AgentProposed(
        bytes32 indexed agentId, 
        address indexed proposer,
        bytes32 indexed proposalId
    );
    event AgentCreated(
        bytes32 indexed agentId, 
        address indexed controller,
        uint256 indexed idNFTTokenId
    );
    event AgentDestroyed(
        bytes32 indexed agentId, 
        uint40 timestamp
    );
    event AgentUpdated(
        bytes32 indexed agentId,
        string action,
        uint40 timestamp
    );
    event ConsensusReached(
        bytes32 indexed proposalId, 
        string action
    );
    event HierarchyUpdated(
        bytes32 indexed parentId, 
        bytes32 indexed childId
    );
    event CapabilityGranted(
        bytes32 indexed agentId, 
        bytes32 capability
    );
    event StateChanged(
        bytes32 indexed agentId, 
        AgentState oldState,
        AgentState newState
    );
    event VoteCast(
        bytes32 indexed proposalId,
        address indexed voter,
        bool support
    );

    constructor(address _idNFTAddress) {
        require(_idNFTAddress != address(0), "Invalid IDNFT address");
        idNFT = IDNFT(_idNFTAddress);
        
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(ORCHESTRATOR_ROLE, msg.sender);
        
        // Set default consensus thresholds
        _consensusThresholds["create"] = ConsensusThreshold(70, 0, 0, 1 days);
        _consensusThresholds["destroy"] = ConsensusThreshold(0, 80, 0, 2 days);
        _consensusThresholds["update"] = ConsensusThreshold(0, 0, 60, 12 hours);
    }

    /**
     * @notice IMPORTANT: After deploying this contract, the admin must grant
     *         MINTER_ROLE to this contract's address in the IDNFT contract.
     *         This is done via: idNFT.grantRole(idNFT.MINTER_ROLE(), address(this))
     *         This cannot be done automatically as it requires admin action in IDNFT.
     */

    /**
     * @dev Propose new agent creation
     * @param agentType Type/category of agent
     * @param purpose Defined purpose/scope
     * @param consensusRequired Whether consensus is needed
     * @param parameters Encoded parameters (controller, prompt, persona, etc.)
     */
    function proposeAgent(
        string memory agentType,
        string memory purpose,
        bool consensusRequired,
        bytes memory parameters
    ) external whenNotPaused onlyRole(AGENT_CREATOR_ROLE) returns (bytes32) {
        bytes32 agentId = keccak256(abi.encodePacked(
            agentType,
            purpose,
            block.timestamp,
            msg.sender
        ));

        require(_agents[agentId].agentId == bytes32(0), "Agent ID exists");

        bytes32 proposalId = keccak256(abi.encodePacked(
            "create",
            agentId,
            block.timestamp,
            _proposalCount[agentId]++
        ));

        Proposal storage proposal = _proposals[proposalId];
        proposal.proposalId = proposalId;
        proposal.targetAgentId = agentId;
        proposal.proposer = msg.sender;
        proposal.action = "create";
        proposal.parameters = parameters;
        proposal.proposalTime = uint40(block.timestamp);
        proposal.executionTime = uint40(block.timestamp + _consensusThresholds["create"].timelock);

        emit AgentProposed(agentId, msg.sender, proposalId);
        return proposalId;
    }

    /**
     * @dev Vote on agent proposal
     */
    function voteOnProposal(
        bytes32 proposalId,
        bool support
    ) external whenNotPaused onlyRole(CONSENSUS_ROLE) {
        Proposal storage proposal = _proposals[proposalId];
        require(proposal.proposalId != bytes32(0), "Proposal doesn't exist");
        require(!proposal.hasVoted[msg.sender], "Already voted");
        require(!proposal.executed && !proposal.canceled, "Proposal finalized");

        proposal.hasVoted[msg.sender] = true;
        if (support) {
            proposal.approvalCount++;
        } else {
            proposal.rejectionCount++;
        }

        emit VoteCast(proposalId, msg.sender, support);

        // Check if consensus is reached
        if (_isConsensusReached(proposal)) {
            _executeProposal(proposalId);
        }
    }

    /**
     * @dev Execute consensus-approved action
     */
    function _executeProposal(bytes32 proposalId) internal {
        Proposal storage proposal = _proposals[proposalId];
        ConsensusThreshold memory threshold = _consensusThresholds[proposal.action];
        
        require(
            block.timestamp >= proposal.executionTime,
            "Timelock not expired"
        );
        require(!proposal.executed, "Already executed");

        if (keccak256(bytes(proposal.action)) == keccak256(bytes("create"))) {
            _createAgent(proposal.targetAgentId, proposal.parameters);
        } else if (keccak256(bytes(proposal.action)) == keccak256(bytes("destroy"))) {
            _destroyAgent(proposal.targetAgentId);
        } else if (keccak256(bytes(proposal.action)) == keccak256(bytes("update"))) {
            _updateAgent(proposal.targetAgentId, proposal.parameters);
        }

        proposal.executed = true;
        emit ConsensusReached(proposalId, proposal.action);
    }

    /**
     * @dev Internal agent creation with IDNFT integration
     */
    function _createAgent(bytes32 agentId, bytes memory parameters) internal {
        (
            address controller,
            string memory agentType,
            string memory purpose,
            string memory prompt,
            string memory persona,
            string memory modelDatasetCID,
            string memory metadataURI,
            bool useSoulbound
        ) = abi.decode(parameters, (address, string, string, string, string, string, string, bool));

        // Mint IDNFT for agent identity
        // Note: This contract must have MINTER_ROLE in IDNFT contract
        bytes32 nonce = keccak256(abi.encodePacked(agentId, block.timestamp));
        uint256 idNFTTokenId = idNFT.mintAgentIdentity(
            controller,
            agentType,
            prompt,
            persona,
            modelDatasetCID,
            metadataURI,
            nonce,
            useSoulbound
        );

        Agent storage agent = _agents[agentId];
        agent.agentId = agentId;
        agent.controller = controller;
        agent.agentType = agentType;
        agent.purpose = purpose;
        agent.state = AgentState.Active;
        agent.idNFTTokenId = idNFTTokenId;
        agent.creationTime = uint40(block.timestamp);
        agent.lastUpdate = uint40(block.timestamp);
        agent.consensusRequired = true;

        emit AgentCreated(agentId, controller, idNFTTokenId);
    }

    /**
     * @dev Internal agent destruction
     */
    function _destroyAgent(bytes32 agentId) internal {
        Agent storage agent = _agents[agentId];
        require(agent.state == AgentState.Active, "Agent not active");
        
        AgentState oldState = agent.state;
        agent.state = AgentState.Deprecated;
        agent.lastUpdate = uint40(block.timestamp);
        
        // Remove from hierarchy
        bytes32 parentId = _parentAgent[agentId];
        if (parentId != bytes32(0)) {
            _removeFromHierarchy(parentId, agentId);
        }

        emit StateChanged(agentId, oldState, AgentState.Deprecated);
        emit AgentDestroyed(agentId, uint40(block.timestamp));
    }

    /**
     * @dev Internal agent update
     */
    function _updateAgent(bytes32 agentId, bytes memory parameters) internal {
        Agent storage agent = _agents[agentId];
        require(agent.state == AgentState.Active, "Agent not active");

        // Decode update parameters
        (string memory newPurpose, bytes32[] memory newCapabilities) = 
            abi.decode(parameters, (string, bytes32[]));

        if (bytes(newPurpose).length > 0) {
            agent.purpose = newPurpose;
        }

        // Update capabilities
        for (uint i = 0; i < newCapabilities.length; i++) {
            if (!agent.activeCapabilities[newCapabilities[i]]) {
                agent.capabilities.push(newCapabilities[i]);
                agent.activeCapabilities[newCapabilities[i]] = true;
                emit CapabilityGranted(agentId, newCapabilities[i]);
            }
        }

        agent.lastUpdate = uint40(block.timestamp);
        emit AgentUpdated(agentId, "update", uint40(block.timestamp));
    }

    /**
     * @dev Manage agent hierarchy
     */
    function setAgentHierarchy(
        bytes32 parentId,
        bytes32 childId
    ) external whenNotPaused onlyRole(ORCHESTRATOR_ROLE) {
        require(_agents[parentId].state == AgentState.Active, "Parent not active");
        require(_agents[childId].state == AgentState.Active, "Child not active");
        require(_parentAgent[childId] == bytes32(0), "Child already has parent");
        
        _agentHierarchy[parentId].push(childId);
        _parentAgent[childId] = parentId;
        
        emit HierarchyUpdated(parentId, childId);
    }

    /**
     * @dev Remove agent from hierarchy
     */
    function _removeFromHierarchy(bytes32 parentId, bytes32 childId) internal {
        bytes32[] storage children = _agentHierarchy[parentId];
        for (uint i = 0; i < children.length; i++) {
            if (children[i] == childId) {
                children[i] = children[children.length - 1];
                children.pop();
                delete _parentAgent[childId];
                break;
            }
        }
    }

    /**
     * @dev Check consensus threshold
     */
    function _isConsensusReached(Proposal storage proposal) 
        internal 
        view 
        returns (bool) 
    {
        ConsensusThreshold memory threshold = _consensusThresholds[proposal.action];
        uint16 totalVotes = proposal.approvalCount + proposal.rejectionCount;
        
        if (totalVotes == 0) return false;
        
        uint8 approvalPercentage = uint8((proposal.approvalCount * 100) / totalVotes);
        
        if (keccak256(bytes(proposal.action)) == keccak256(bytes("create"))) {
            return approvalPercentage >= threshold.createThreshold;
        } else if (keccak256(bytes(proposal.action)) == keccak256(bytes("destroy"))) {
            return approvalPercentage >= threshold.destroyThreshold;
        } else {
            return approvalPercentage >= threshold.updateThreshold;
        }
    }

    /**
     * @dev Update consensus thresholds
     */
    function updateConsensusThreshold(
        string memory action,
        uint8 createThreshold,
        uint8 destroyThreshold,
        uint8 updateThreshold,
        uint32 timelock
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _consensusThresholds[action] = ConsensusThreshold(
            createThreshold,
            destroyThreshold,
            updateThreshold,
            timelock
        );
    }

    /**
     * @dev Grant capability to agent
     */
    function grantCapability(
        bytes32 agentId,
        bytes32 capability
    ) external onlyRole(ORCHESTRATOR_ROLE) {
        Agent storage agent = _agents[agentId];
        require(agent.state == AgentState.Active, "Agent not active");
        require(!agent.activeCapabilities[capability], "Capability already granted");

        agent.capabilities.push(capability);
        agent.activeCapabilities[capability] = true;
        emit CapabilityGranted(agentId, capability);
    }

    /**
     * @dev Update agent state
     */
    function updateAgentState(
        bytes32 agentId,
        AgentState newState
    ) external onlyRole(ORCHESTRATOR_ROLE) {
        Agent storage agent = _agents[agentId];
        AgentState oldState = agent.state;
        
        require(oldState != newState, "State unchanged");
        require(newState != AgentState.NonExistent, "Cannot set to NonExistent");

        agent.state = newState;
        agent.lastUpdate = uint40(block.timestamp);
        emit StateChanged(agentId, oldState, newState);
    }

    /**
     * @dev Authorize caller for agent
     */
    function authorizeCaller(
        bytes32 agentId,
        address caller
    ) external onlyRole(ORCHESTRATOR_ROLE) {
        Agent storage agent = _agents[agentId];
        require(agent.state == AgentState.Active, "Agent not active");
        agent.authorizedCallers[caller] = true;
    }

    /**
     * @dev Revoke caller authorization
     */
    function revokeCaller(
        bytes32 agentId,
        address caller
    ) external onlyRole(ORCHESTRATOR_ROLE) {
        Agent storage agent = _agents[agentId];
        agent.authorizedCallers[caller] = false;
    }

    // View functions
    function getAgent(bytes32 agentId) external view returns (
        address controller,
        string memory agentType,
        string memory purpose,
        AgentState state,
        uint256 idNFTTokenId,
        uint40 creationTime,
        bool consensusRequired
    ) {
        Agent storage agent = _agents[agentId];
        return (
            agent.controller,
            agent.agentType,
            agent.purpose,
            agent.state,
            agent.idNFTTokenId,
            agent.creationTime,
            agent.consensusRequired
        );
    }

    function getProposal(bytes32 proposalId) external view returns (
        bytes32 targetAgentId,
        address proposer,
        string memory action,
        uint40 proposalTime,
        uint40 executionTime,
        uint16 approvalCount,
        uint16 rejectionCount,
        bool executed,
        bool canceled
    ) {
        Proposal storage proposal = _proposals[proposalId];
        require(proposal.proposalId != bytes32(0), "Proposal doesn't exist");
        return (
            proposal.targetAgentId,
            proposal.proposer,
            proposal.action,
            proposal.proposalTime,
            proposal.executionTime,
            proposal.approvalCount,
            proposal.rejectionCount,
            proposal.executed,
            proposal.canceled
        );
    }

    function getAgentHierarchy(bytes32 agentId) 
        external 
        view 
        returns (bytes32[] memory) 
    {
        return _agentHierarchy[agentId];
    }

    function getParentAgent(bytes32 agentId) external view returns (bytes32) {
        return _parentAgent[agentId];
    }

    function getConsensusThreshold(string memory action)
        external
        view
        returns (ConsensusThreshold memory)
    {
        return _consensusThresholds[action];
    }

    function isAuthorizedCaller(bytes32 agentId, address caller)
        external
        view
        returns (bool)
    {
        return _agents[agentId].authorizedCallers[caller];
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }
}
