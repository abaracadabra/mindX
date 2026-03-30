// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "../../daio/agents/AgentFactory.sol";
import "../../daio/identity/IDNFT.sol";
import "../../daio/constitution/DAIO_Constitution.sol";
import "../../executive-governance/ExecutiveGovernance.sol";

/**
 * @title EnhancedAgentFactory
 * @dev Enhanced agent creation with executive governance oversight and constitutional compliance
 *
 * Key Features:
 * - Executive approval for major agent deployments
 * - Constitutional compliance validation for all agents
 * - Agent types: Governance, Treasury, Risk Management, Compliance
 * - Integration with IDNFT for identity establishment
 * - Complete agent lifecycle management
 * - Emergency controls and CEO override capabilities
 */
contract EnhancedAgentFactory is AccessControl, ReentrancyGuard, Pausable {
    bytes32 public constant AGENT_CREATOR_ROLE = keccak256("AGENT_CREATOR_ROLE");
    bytes32 public constant AGENT_APPROVER_ROLE = keccak256("AGENT_APPROVER_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");

    // Core contracts
    AgentFactory public immutable baseFactory;
    IDNFT public immutable idnft;
    DAIO_Constitution public immutable constitution;
    ExecutiveGovernance public immutable executiveGovernance;

    // Agent type definitions
    enum AgentType {
        GOVERNANCE,        // Governance participation and proposal agents
        TREASURY,          // Treasury management and DeFi optimization agents
        RISK_MANAGEMENT,   // Risk assessment and monitoring agents
        COMPLIANCE,        // Regulatory compliance and audit agents
        OPERATIONAL,       // Day-to-day operational agents
        STRATEGIC,         // Strategic planning and analysis agents
        EMERGENCY          // Emergency response and crisis management agents
    }

    enum AgentCapabilityLevel {
        BASIC,            // Basic agent capabilities
        INTERMEDIATE,     // Moderate decision-making authority
        ADVANCED,         // High autonomy and significant authority
        EXECUTIVE         // Near-human level decision authority
    }

    struct AgentDeployment {
        uint256 id;
        address deployer;
        AgentType agentType;
        AgentCapabilityLevel capabilityLevel;
        string name;
        string description;
        bytes parameters;
        bool requiresExecutiveApproval;
        bool approved;
        bool deployed;
        address agentAddress;
        uint256 idnftTokenId;
        uint256 requestTime;
        uint256 approvalTime;
        uint256 deploymentTime;
        mapping(address => bool) executiveApprovals;
        uint256 approvalCount;
        string rejectionReason;
    }

    struct AgentStatistics {
        uint256 totalAgentsCreated;
        uint256 activeAgents;
        uint256 pendingApprovals;
        mapping(AgentType => uint256) agentsByType;
        mapping(AgentCapabilityLevel => uint256) agentsByCapability;
    }

    mapping(uint256 => AgentDeployment) public deployments;
    mapping(address => uint256[]) public deployerHistory;
    mapping(AgentType => bool) public requiresExecutiveApproval;
    mapping(AgentType => uint256) public requiredApprovals;
    mapping(AgentCapabilityLevel => uint256) public capabilityLimits;
    mapping(address => bool) public approvedAgents;

    AgentStatistics public agentStats;
    uint256 public nextDeploymentId = 1;
    uint256 public maxAgentsPerDeployer = 10;
    uint256 public maxTotalAgents = 1000;

    event AgentDeploymentRequested(
        uint256 indexed deploymentId,
        address indexed deployer,
        AgentType agentType,
        AgentCapabilityLevel capabilityLevel,
        string name
    );

    event ExecutiveApprovalReceived(
        uint256 indexed deploymentId,
        address indexed executive,
        uint256 approvalCount,
        uint256 required
    );

    event AgentDeployed(
        uint256 indexed deploymentId,
        address indexed agentAddress,
        uint256 indexed idnftTokenId,
        AgentType agentType
    );

    event AgentSuspended(
        address indexed agentAddress,
        string reason,
        address indexed suspender
    );

    event EmergencyAgentDeployment(
        address indexed agentAddress,
        address indexed deployer,
        string reason
    );

    constructor(
        address _baseFactory,
        address _idnft,
        address _constitution,
        address _executiveGovernance,
        address _admin
    ) {
        require(_baseFactory != address(0), "Invalid base factory");
        require(_idnft != address(0), "Invalid IDNFT");
        require(_constitution != address(0), "Invalid constitution");
        require(_executiveGovernance != address(0), "Invalid executive governance");
        require(_admin != address(0), "Invalid admin");

        baseFactory = AgentFactory(_baseFactory);
        idnft = IDNFT(_idnft);
        constitution = DAIO_Constitution(_constitution);
        executiveGovernance = ExecutiveGovernance(_executiveGovernance);

        _grantRole(DEFAULT_ADMIN_ROLE, _admin);
        _grantRole(AGENT_CREATOR_ROLE, _admin);
        _grantRole(AGENT_APPROVER_ROLE, _admin);
        _grantRole(EMERGENCY_ROLE, _admin);

        _initializeAgentTypes();
        _initializeCapabilityLimits();
    }

    /**
     * @dev Initialize agent type approval requirements
     */
    function _initializeAgentTypes() internal {
        // High-impact agent types require executive approval
        requiresExecutiveApproval[AgentType.GOVERNANCE] = true;
        requiresExecutiveApproval[AgentType.TREASURY] = true;
        requiresExecutiveApproval[AgentType.RISK_MANAGEMENT] = true;
        requiresExecutiveApproval[AgentType.COMPLIANCE] = true;
        requiresExecutiveApproval[AgentType.STRATEGIC] = true;
        requiresExecutiveApproval[AgentType.EMERGENCY] = true;

        // Operational agents can be deployed with reduced oversight
        requiresExecutiveApproval[AgentType.OPERATIONAL] = false;

        // Set required approval counts
        requiredApprovals[AgentType.GOVERNANCE] = 5;        // 5 of 8 executives
        requiredApprovals[AgentType.TREASURY] = 6;          // 6 of 8 executives
        requiredApprovals[AgentType.RISK_MANAGEMENT] = 4;   // 4 of 8 executives
        requiredApprovals[AgentType.COMPLIANCE] = 5;        // 5 of 8 executives
        requiredApprovals[AgentType.STRATEGIC] = 7;         // 7 of 8 executives
        requiredApprovals[AgentType.EMERGENCY] = 8;         // All executives
        requiredApprovals[AgentType.OPERATIONAL] = 2;       // 2 executives
    }

    /**
     * @dev Initialize capability level limits
     */
    function _initializeCapabilityLimits() internal {
        capabilityLimits[AgentCapabilityLevel.BASIC] = 100;        // Up to 100 basic agents
        capabilityLimits[AgentCapabilityLevel.INTERMEDIATE] = 50;  // Up to 50 intermediate agents
        capabilityLimits[AgentCapabilityLevel.ADVANCED] = 20;     // Up to 20 advanced agents
        capabilityLimits[AgentCapabilityLevel.EXECUTIVE] = 8;     // Up to 8 executive-level agents
    }

    /**
     * @dev Request agent deployment
     */
    function requestAgentDeployment(
        AgentType agentType,
        AgentCapabilityLevel capabilityLevel,
        string calldata name,
        string calldata description,
        bytes calldata parameters
    ) external nonReentrant whenNotPaused returns (uint256) {
        require(bytes(name).length > 0, "Name required");
        require(bytes(description).length > 0, "Description required");
        require(deployerHistory[msg.sender].length < maxAgentsPerDeployer, "Too many agents for deployer");
        require(agentStats.totalAgentsCreated < maxTotalAgents, "Maximum total agents reached");
        require(agentStats.agentsByCapability[capabilityLevel] < capabilityLimits[capabilityLevel], "Capability limit reached");

        // Constitutional validation
        require(constitution.validateAgentDeployment(agentType, capabilityLevel, parameters), "Constitutional violation");

        uint256 deploymentId = nextDeploymentId++;

        AgentDeployment storage deployment = deployments[deploymentId];
        deployment.id = deploymentId;
        deployment.deployer = msg.sender;
        deployment.agentType = agentType;
        deployment.capabilityLevel = capabilityLevel;
        deployment.name = name;
        deployment.description = description;
        deployment.parameters = parameters;
        deployment.requiresExecutiveApproval = requiresExecutiveApproval[agentType] ||
                                              capabilityLevel >= AgentCapabilityLevel.ADVANCED;
        deployment.requestTime = block.timestamp;

        deployerHistory[msg.sender].push(deploymentId);
        agentStats.pendingApprovals++;

        emit AgentDeploymentRequested(deploymentId, msg.sender, agentType, capabilityLevel, name);

        // Auto-approve for operational agents with basic/intermediate capability
        if (!deployment.requiresExecutiveApproval) {
            _approveAndDeploy(deploymentId);
        }

        return deploymentId;
    }

    /**
     * @dev Executive approval for agent deployment
     */
    function approveAgentDeployment(
        uint256 deploymentId
    ) external nonReentrant whenNotPaused {
        AgentDeployment storage deployment = deployments[deploymentId];
        require(!deployment.deployed, "Already deployed");
        require(!deployment.executiveApprovals[msg.sender], "Already approved");
        require(executiveGovernance.hasExecutiveRole(msg.sender), "Not an executive");

        deployment.executiveApprovals[msg.sender] = true;
        deployment.approvalCount++;

        emit ExecutiveApprovalReceived(
            deploymentId,
            msg.sender,
            deployment.approvalCount,
            requiredApprovals[deployment.agentType]
        );

        // Check if sufficient approvals received
        if (deployment.approvalCount >= requiredApprovals[deployment.agentType]) {
            _approveAndDeploy(deploymentId);
        }
    }

    /**
     * @dev Internal approval and deployment logic
     */
    function _approveAndDeploy(uint256 deploymentId) internal {
        AgentDeployment storage deployment = deployments[deploymentId];
        require(!deployment.deployed, "Already deployed");

        deployment.approved = true;
        deployment.approvalTime = block.timestamp;

        // Deploy the agent
        _deployAgent(deploymentId);
    }

    /**
     * @dev Deploy approved agent
     */
    function _deployAgent(uint256 deploymentId) internal {
        AgentDeployment storage deployment = deployments[deploymentId];

        // Create agent through base factory
        address agentAddress = baseFactory.createAgent(
            deployment.name,
            deployment.description,
            deployment.parameters
        );

        // Create IDNFT for agent identity
        uint256 idnftTokenId = idnft.mint(
            agentAddress,
            deployment.description, // prompt
            "", // persona
            new string[](0), // credentials
            "" // THOT CID
        );

        // Update deployment record
        deployment.deployed = true;
        deployment.agentAddress = agentAddress;
        deployment.idnftTokenId = idnftTokenId;
        deployment.deploymentTime = block.timestamp;

        // Update statistics
        agentStats.totalAgentsCreated++;
        agentStats.activeAgents++;
        agentStats.pendingApprovals--;
        agentStats.agentsByType[deployment.agentType]++;
        agentStats.agentsByCapability[deployment.capabilityLevel]++;

        // Mark as approved agent
        approvedAgents[agentAddress] = true;

        emit AgentDeployed(deploymentId, agentAddress, idnftTokenId, deployment.agentType);
    }

    /**
     * @dev Emergency agent deployment (CEO only)
     */
    function emergencyDeployAgent(
        AgentType agentType,
        string calldata name,
        string calldata description,
        bytes calldata parameters,
        string calldata reason
    ) external onlyRole(EMERGENCY_ROLE) nonReentrant returns (address) {
        require(executiveGovernance.isCEO(msg.sender), "Only CEO can emergency deploy");
        require(agentType == AgentType.EMERGENCY, "Only emergency agents can be deployed this way");

        // Constitutional emergency validation
        require(constitution.validateEmergencyAction(msg.sender, reason), "Emergency deployment rejected");

        // Deploy immediately
        address agentAddress = baseFactory.createAgent(name, description, parameters);

        // Create IDNFT
        uint256 idnftTokenId = idnft.mint(
            agentAddress,
            description,
            "EMERGENCY_AGENT",
            new string[](0),
            ""
        );

        // Update statistics
        agentStats.totalAgentsCreated++;
        agentStats.activeAgents++;
        agentStats.agentsByType[AgentType.EMERGENCY]++;
        agentStats.agentsByCapability[AgentCapabilityLevel.EXECUTIVE]++;

        approvedAgents[agentAddress] = true;

        emit EmergencyAgentDeployment(agentAddress, msg.sender, reason);

        return agentAddress;
    }

    /**
     * @dev Suspend agent (CEO or designated executives)
     */
    function suspendAgent(
        address agentAddress,
        string calldata reason
    ) external nonReentrant {
        require(approvedAgents[agentAddress], "Agent not found");
        require(
            executiveGovernance.isCEO(msg.sender) ||
            executiveGovernance.hasRole(executiveGovernance.CISO_ROLE(), msg.sender),
            "Not authorized to suspend"
        );

        // Call suspension on the agent (assuming it implements ISuspendable)
        (bool success, ) = agentAddress.call(abi.encodeWithSignature("suspend(string)", reason));
        require(success, "Suspension failed");

        // Update statistics
        agentStats.activeAgents--;

        emit AgentSuspended(agentAddress, reason, msg.sender);
    }

    /**
     * @dev Reactivate suspended agent
     */
    function reactivateAgent(
        address agentAddress
    ) external onlyRole(AGENT_APPROVER_ROLE) nonReentrant {
        require(approvedAgents[agentAddress], "Agent not found");

        // Call reactivation on the agent
        (bool success, ) = agentAddress.call(abi.encodeWithSignature("reactivate()"));
        require(success, "Reactivation failed");

        // Update statistics
        agentStats.activeAgents++;
    }

    /**
     * @dev Reject agent deployment
     */
    function rejectAgentDeployment(
        uint256 deploymentId,
        string calldata reason
    ) external onlyRole(AGENT_APPROVER_ROLE) {
        AgentDeployment storage deployment = deployments[deploymentId];
        require(!deployment.deployed, "Already deployed");
        require(!deployment.approved, "Already approved");

        deployment.rejectionReason = reason;
        agentStats.pendingApprovals--;
    }

    /**
     * @dev Get deployment details
     */
    function getDeploymentDetails(uint256 deploymentId) external view returns (
        address deployer,
        AgentType agentType,
        AgentCapabilityLevel capabilityLevel,
        string memory name,
        string memory description,
        bool approved,
        bool deployed,
        address agentAddress,
        uint256 approvalCount,
        uint256 requiredApprovalCount
    ) {
        AgentDeployment storage deployment = deployments[deploymentId];
        return (
            deployment.deployer,
            deployment.agentType,
            deployment.capabilityLevel,
            deployment.name,
            deployment.description,
            deployment.approved,
            deployment.deployed,
            deployment.agentAddress,
            deployment.approvalCount,
            requiredApprovals[deployment.agentType]
        );
    }

    /**
     * @dev Get agent statistics
     */
    function getAgentStatistics() external view returns (
        uint256 totalCreated,
        uint256 active,
        uint256 pending,
        uint256[7] memory byType,
        uint256[4] memory byCapability
    ) {
        totalCreated = agentStats.totalAgentsCreated;
        active = agentStats.activeAgents;
        pending = agentStats.pendingApprovals;

        // Convert mappings to arrays for return
        for (uint256 i = 0; i < 7; i++) {
            byType[i] = agentStats.agentsByType[AgentType(i)];
        }

        for (uint256 i = 0; i < 4; i++) {
            byCapability[i] = agentStats.agentsByCapability[AgentCapabilityLevel(i)];
        }

        return (totalCreated, active, pending, byType, byCapability);
    }

    /**
     * @dev Check if executive has approved deployment
     */
    function hasExecutiveApproved(
        uint256 deploymentId,
        address executive
    ) external view returns (bool) {
        return deployments[deploymentId].executiveApprovals[executive];
    }

    /**
     * @dev Get deployments by deployer
     */
    function getDeploymentsByDeployer(address deployer) external view returns (uint256[] memory) {
        return deployerHistory[deployer];
    }

    /**
     * @dev Update agent type approval requirements
     */
    function updateAgentTypeConfig(
        AgentType agentType,
        bool requiresApproval,
        uint256 requiredCount
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(requiredCount <= 8, "Cannot require more than 8 approvals");
        requiresExecutiveApproval[agentType] = requiresApproval;
        requiredApprovals[agentType] = requiredCount;
    }

    /**
     * @dev Update capability limits
     */
    function updateCapabilityLimit(
        AgentCapabilityLevel level,
        uint256 newLimit
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        capabilityLimits[level] = newLimit;
    }

    /**
     * @dev Update maximum agents per deployer
     */
    function updateMaxAgentsPerDeployer(
        uint256 newMax
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        maxAgentsPerDeployer = newMax;
    }

    /**
     * @dev Emergency pause
     */
    function emergencyPause() external onlyRole(EMERGENCY_ROLE) {
        _pause();
    }

    /**
     * @dev Unpause
     */
    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }
}