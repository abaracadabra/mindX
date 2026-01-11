// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title AgentToken
 * @dev Custom ERC20 token for each agent
 */
contract AgentToken is ERC20 {
    address public immutable factory;
    address public immutable agentAddress;

    constructor(
        string memory name_,
        string memory symbol_,
        address _agentAddress,
        uint256 initialSupply
    ) ERC20(name_, symbol_) {
        factory = msg.sender;
        agentAddress = _agentAddress;
        _mint(_agentAddress, initialSupply);
    }

    function mint(address to, uint256 amount) external {
        require(msg.sender == factory, "Only factory can mint");
        _mint(to, amount);
    }

    function burn(uint256 amount) external {
        _burn(msg.sender, amount);
    }
}

/**
 * @title AgentFactory
 * @dev On-chain agent creation and lifecycle management.
 *
 * Features:
 * - Creates custom ERC20 tokens per agent
 * - Mints fractionalized NFTs for governance rights
 * - Manages agent lifecycle (creation, destruction, reactivation)
 * - Integrates with KnowledgeHierarchyDAIO for governance
 */
contract AgentFactory is ERC721, ERC721URIStorage, AccessControl, ReentrancyGuard, Pausable {
    // Roles
    bytes32 public constant GOVERNANCE_ROLE = keccak256("GOVERNANCE_ROLE");
    bytes32 public constant AGENT_CREATOR_ROLE = keccak256("AGENT_CREATOR_ROLE");

    // Agent structure
    struct Agent {
        bytes32 agentId;               // Unique identifier
        address agentAddress;          // Agent wallet address
        address tokenAddress;          // Custom ERC20 token address
        uint256 nftId;                 // NFT ID for governance rights
        bytes32 metadataHash;          // Hash of agent metadata
        string agentType;              // Type of agent
        uint40 createdAt;              // Creation timestamp
        uint40 lastUpdate;             // Last update timestamp
        bool active;                   // Active status
    }

    // Agent creation parameters
    struct AgentCreationParams {
        address agentAddress;
        string agentType;
        string tokenName;
        string tokenSymbol;
        uint256 initialTokenSupply;
        string nftMetadata;
        bytes32 metadataHash;
    }

    // State
    address public immutable governanceContract;
    uint256 public agentCount;
    uint256 public totalActiveAgents;
    uint256 public constant DEFAULT_TOKEN_SUPPLY = 1_000_000 * 10**18;

    mapping(address => Agent) public agents;
    mapping(uint256 => address) public nftToAgent;
    mapping(address => address) public agentToToken;
    address[] public allAgents;

    // Events
    event AgentCreated(
        address indexed agentAddress,
        bytes32 indexed agentId,
        address tokenAddress,
        uint256 nftId,
        string agentType
    );

    event AgentDestroyed(
        address indexed agentAddress,
        uint40 timestamp
    );

    event AgentReactivated(
        address indexed agentAddress,
        uint40 timestamp
    );

    event AgentMetadataUpdated(
        uint256 indexed nftId,
        string newMetadata
    );

    event AgentTokenMinted(
        address indexed agentAddress,
        address indexed tokenAddress,
        uint256 amount
    );

    // Errors
    error AgentAlreadyExists();
    error AgentDoesNotExist();
    error AgentAlreadyActive();
    error AgentNotActive();
    error InvalidGovernanceAddress();
    error OnlyGovernance();

    modifier onlyGovernance() {
        if (!hasRole(GOVERNANCE_ROLE, msg.sender)) revert OnlyGovernance();
        _;
    }

    constructor(
        address _governanceContract
    ) ERC721("DAIO Agent NFT", "DAGENT") {
        if (_governanceContract == address(0)) revert InvalidGovernanceAddress();
        governanceContract = _governanceContract;

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(GOVERNANCE_ROLE, _governanceContract);
        _grantRole(GOVERNANCE_ROLE, msg.sender);
        _grantRole(AGENT_CREATOR_ROLE, msg.sender);
    }

    // ============ Agent Creation ============

    /**
     * @dev Creates a new agent with ERC20 token and NFT
     * @param params Agent creation parameters
     * @return agentId Unique identifier for the agent
     * @return tokenAddress Address of the created token
     * @return nftId ID of the minted NFT
     */
    function createAgent(
        AgentCreationParams memory params
    ) external onlyRole(AGENT_CREATOR_ROLE) nonReentrant whenNotPaused returns (
        bytes32 agentId,
        address tokenAddress,
        uint256 nftId
    ) {
        if (agents[params.agentAddress].createdAt != 0) revert AgentAlreadyExists();
        require(params.agentAddress != address(0), "Invalid agent address");

        // Generate unique agent ID
        agentId = keccak256(abi.encodePacked(
            params.agentAddress,
            params.agentType,
            block.timestamp,
            agentCount
        ));

        // Create custom ERC20 token for the agent
        uint256 supply = params.initialTokenSupply > 0 ?
            params.initialTokenSupply : DEFAULT_TOKEN_SUPPLY;

        AgentToken token = new AgentToken(
            params.tokenName,
            params.tokenSymbol,
            params.agentAddress,
            supply
        );
        tokenAddress = address(token);

        // Mint NFT for governance rights
        agentCount++;
        nftId = agentCount;
        _safeMint(params.agentAddress, nftId);
        _setTokenURI(nftId, params.nftMetadata);

        // Store agent details
        agents[params.agentAddress] = Agent({
            agentId: agentId,
            agentAddress: params.agentAddress,
            tokenAddress: tokenAddress,
            nftId: nftId,
            metadataHash: params.metadataHash,
            agentType: params.agentType,
            createdAt: uint40(block.timestamp),
            lastUpdate: uint40(block.timestamp),
            active: true
        });

        nftToAgent[nftId] = params.agentAddress;
        agentToToken[params.agentAddress] = tokenAddress;
        allAgents.push(params.agentAddress);
        totalActiveAgents++;

        emit AgentCreated(
            params.agentAddress,
            agentId,
            tokenAddress,
            nftId,
            params.agentType
        );

        return (agentId, tokenAddress, nftId);
    }

    /**
     * @dev Simplified agent creation with defaults
     * @param agentAddress Agent's wallet address
     * @param agentType Type of agent
     * @param tokenName Name for the agent's token
     * @param tokenSymbol Symbol for the agent's token
     * @param nftMetadata NFT metadata URI
     * @return agentId Unique identifier
     */
    function createAgentSimple(
        address agentAddress,
        string memory agentType,
        string memory tokenName,
        string memory tokenSymbol,
        string memory nftMetadata
    ) external onlyRole(AGENT_CREATOR_ROLE) returns (bytes32 agentId) {
        AgentCreationParams memory params = AgentCreationParams({
            agentAddress: agentAddress,
            agentType: agentType,
            tokenName: tokenName,
            tokenSymbol: tokenSymbol,
            initialTokenSupply: DEFAULT_TOKEN_SUPPLY,
            nftMetadata: nftMetadata,
            metadataHash: keccak256(abi.encodePacked(nftMetadata))
        });

        (agentId, , ) = this.createAgent(params);
        return agentId;
    }

    // ============ Agent Lifecycle ============

    /**
     * @dev Destroys (deactivates) an agent
     * @param agentAddress Address of the agent to destroy
     */
    function destroyAgent(
        address agentAddress
    ) external onlyGovernance nonReentrant {
        Agent storage agent = agents[agentAddress];

        if (agent.createdAt == 0) revert AgentDoesNotExist();
        if (!agent.active) revert AgentNotActive();

        agent.active = false;
        agent.lastUpdate = uint40(block.timestamp);
        totalActiveAgents--;

        emit AgentDestroyed(agentAddress, uint40(block.timestamp));
    }

    /**
     * @dev Reactivates a destroyed agent
     * @param agentAddress Address of the agent to reactivate
     */
    function reactivateAgent(
        address agentAddress
    ) external onlyGovernance nonReentrant {
        Agent storage agent = agents[agentAddress];

        if (agent.createdAt == 0) revert AgentDoesNotExist();
        if (agent.active) revert AgentAlreadyActive();

        agent.active = true;
        agent.lastUpdate = uint40(block.timestamp);
        totalActiveAgents++;

        emit AgentReactivated(agentAddress, uint40(block.timestamp));
    }

    // ============ Metadata Management ============

    /**
     * @dev Updates NFT metadata for an agent
     * @param nftId NFT ID to update
     * @param newMetadata New metadata URI
     */
    function updateNFTMetadata(
        uint256 nftId,
        string memory newMetadata
    ) external {
        require(
            ownerOf(nftId) == msg.sender || hasRole(GOVERNANCE_ROLE, msg.sender),
            "Not authorized"
        );

        address agentAddress = nftToAgent[nftId];
        require(agents[agentAddress].active, "Agent not active");

        _setTokenURI(nftId, newMetadata);
        agents[agentAddress].lastUpdate = uint40(block.timestamp);
        agents[agentAddress].metadataHash = keccak256(abi.encodePacked(newMetadata));

        emit AgentMetadataUpdated(nftId, newMetadata);
    }

    // ============ Token Management ============

    /**
     * @dev Mints additional tokens for an agent
     * @param agentAddress Agent's address
     * @param amount Amount to mint
     */
    function mintAgentTokens(
        address agentAddress,
        uint256 amount
    ) external onlyGovernance {
        Agent storage agent = agents[agentAddress];
        require(agent.active, "Agent not active");

        AgentToken(agent.tokenAddress).mint(agentAddress, amount);

        emit AgentTokenMinted(agentAddress, agent.tokenAddress, amount);
    }

    // ============ View Functions ============

    /**
     * @dev Gets agent details
     * @param agentAddress Agent's address
     * @return agent The agent data
     */
    function getAgent(address agentAddress) external view returns (Agent memory agent) {
        return agents[agentAddress];
    }

    /**
     * @dev Checks if an agent is active
     * @param agentAddress Agent's address
     * @return active Whether the agent is active
     */
    function isAgentActive(address agentAddress) external view returns (bool active) {
        return agents[agentAddress].active;
    }

    /**
     * @dev Gets the agent's token address
     * @param agentAddress Agent's address
     * @return tokenAddress The token address
     */
    function getAgentToken(address agentAddress) external view returns (address tokenAddress) {
        return agents[agentAddress].tokenAddress;
    }

    /**
     * @dev Gets the agent's NFT ID
     * @param agentAddress Agent's address
     * @return nftId The NFT ID
     */
    function getAgentNFT(address agentAddress) external view returns (uint256 nftId) {
        return agents[agentAddress].nftId;
    }

    /**
     * @dev Gets agent address by NFT ID
     * @param nftId NFT ID
     * @return agentAddress The agent's address
     */
    function getAgentByNFT(uint256 nftId) external view returns (address agentAddress) {
        return nftToAgent[nftId];
    }

    /**
     * @dev Gets all agent addresses
     * @return Array of agent addresses
     */
    function getAllAgents() external view returns (address[] memory) {
        return allAgents;
    }

    /**
     * @dev Gets the number of agents
     * @return total Total agents created
     * @return active Currently active agents
     */
    function getAgentCounts() external view returns (uint256 total, uint256 active) {
        return (agentCount, totalActiveAgents);
    }

    // ============ Admin Functions ============

    /**
     * @dev Pauses agent creation
     */
    function pause() external onlyRole(GOVERNANCE_ROLE) {
        _pause();
    }

    /**
     * @dev Unpauses agent creation
     */
    function unpause() external onlyRole(GOVERNANCE_ROLE) {
        _unpause();
    }

    // ============ Override Functions ============

    function tokenURI(uint256 tokenId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (string memory)
    {
        return super.tokenURI(tokenId);
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721URIStorage, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
