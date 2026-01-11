// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/utils/Strings.sol";
import "@openzeppelin/contracts/utils/Base64.sol";

/**
 * @title NFPrompT - Agent Prompt NFT
 * @dev Agent Prompt NFT for agentic marketplace integration
 * @notice Represents agent prompts and capabilities as NFTs
 */
contract NFPrompT is ERC721, ReentrancyGuard {
    using Counters for Counters.Counter;
    using Strings for uint256;
    using ECDSA for bytes32;

    Counters.Counter private _promptIdCounter;

    struct AgentData {
        bytes32 agentId;          // Unique agent identifier
        address agentWallet;      // Agent's wallet address
        string basePrompt;        // Core prompt template
        string[] modifiers;       // Prompt modifiers/parameters
        uint40 creationTime;      // Creation timestamp
        uint40 lastUpdate;        // Last update timestamp
        bool isActive;            // Agent active status
        mapping(string => string) capabilities; // Agent capabilities
    }

    struct ActionData {
        string actionType;        // Type of action
        bytes parameters;         // Encoded parameters
        uint40 timestamp;        // Action timestamp
        bool requiresApproval;    // Whether action needs approval
        bool isExecuted;          // Execution status
    }

    // Storage
    mapping(uint256 => AgentData) private _agentData;
    mapping(bytes32 => uint256) private _agentIdToTokenId;
    mapping(uint256 => ActionData[]) private _agentActions;
    mapping(uint256 => mapping(string => bool)) private _agentPermissions;
    mapping(address => mapping(string => uint256)) private _agentBuilderCredits;

    // Events
    event AgentPromptCreated(
        uint256 indexed tokenId,
        bytes32 indexed agentId,
        address indexed agentWallet
    );

    event AgentActionRegistered(
        uint256 indexed tokenId,
        string actionType,
        uint40 timestamp
    );

    event AgentCapabilityAdded(
        uint256 indexed tokenId,
        string capability,
        string value
    );

    event AgentBuilderMinted(
        uint256 indexed tokenId,
        address indexed builder,
        string builderType
    );

    constructor() ERC721("Agent Prompt NFT", "NFPrompT") {}

    /**
     * @dev Create new agent prompt
     */
    function createAgentPrompt(
        bytes32 agentId,
        string memory basePrompt,
        string[] memory initialModifiers,
        string[] memory initialCapabilities,
        string[] memory capabilityValues
    ) external nonReentrant returns (uint256) {
        require(agentId != bytes32(0), "Invalid agent ID");
        require(bytes(basePrompt).length > 0, "Empty prompt");
        require(
            initialCapabilities.length == capabilityValues.length,
            "Capability mismatch"
        );

        _promptIdCounter.increment();
        uint256 tokenId = _promptIdCounter.current();

        AgentData storage agent = _agentData[tokenId];
        agent.agentId = agentId;
        agent.agentWallet = msg.sender;
        agent.basePrompt = basePrompt;
        agent.modifiers = initialModifiers;
        agent.creationTime = uint40(block.timestamp);
        agent.lastUpdate = uint40(block.timestamp);
        agent.isActive = true;

        for (uint i = 0; i < initialCapabilities.length; i++) {
            agent.capabilities[initialCapabilities[i]] = capabilityValues[i];
        }

        _agentIdToTokenId[agentId] = tokenId;
        _safeMint(msg.sender, tokenId);

        emit AgentPromptCreated(tokenId, agentId, msg.sender);
        return tokenId;
    }

    /**
     * @dev Register agent action
     */
    function registerAgentAction(
        uint256 tokenId,
        string memory actionType,
        bytes memory parameters,
        bool requiresApproval
    ) external {
        require(_exists(tokenId), "Token doesn't exist");
        require(_agentData[tokenId].isActive, "Agent not active");
        require(
            msg.sender == _agentData[tokenId].agentWallet,
            "Not agent wallet"
        );

        ActionData memory action = ActionData({
            actionType: actionType,
            parameters: parameters,
            timestamp: uint40(block.timestamp),
            requiresApproval: requiresApproval,
            isExecuted: false
        });

        _agentActions[tokenId].push(action);
        emit AgentActionRegistered(tokenId, actionType, uint40(block.timestamp));
    }

    /**
     * @dev Mint agent builder NFT
     */
    function mintAgentBuilder(
        string memory builderType,
        uint256 parentTokenId
    ) external nonReentrant returns (uint256) {
        require(_exists(parentTokenId), "Parent doesn't exist");
        require(
            _agentBuilderCredits[msg.sender][builderType] > 0,
            "No builder credits"
        );

        _promptIdCounter.increment();
        uint256 tokenId = _promptIdCounter.current();

        // Create builder agent
        AgentData storage builder = _agentData[tokenId];
        builder.agentId = keccak256(abi.encodePacked(
            "BUILDER",
            builderType,
            block.timestamp,
            msg.sender
        ));
        builder.agentWallet = msg.sender;
        builder.basePrompt = string(abi.encodePacked(
            "BUILDER_TYPE:",
            builderType,
            ";PARENT:",
            parentTokenId.toString()
        ));
        builder.creationTime = uint40(block.timestamp);
        builder.isActive = true;

        _agentBuilderCredits[msg.sender][builderType]--;
        _safeMint(msg.sender, tokenId);

        emit AgentBuilderMinted(tokenId, msg.sender, builderType);
        return tokenId;
    }

    /**
     * @dev Add agent capability
     */
    function addAgentCapability(
        uint256 tokenId,
        string memory capability,
        string memory value
    ) external {
        require(_exists(tokenId), "Token doesn't exist");
        require(
            msg.sender == _agentData[tokenId].agentWallet,
            "Not agent wallet"
        );

        _agentData[tokenId].capabilities[capability] = value;
        emit AgentCapabilityAdded(tokenId, capability, value);
    }

    /**
     * @dev Get agent data
     */
    function getAgentData(uint256 tokenId)
        external
        view
        returns (
            bytes32 agentId,
            address agentWallet,
            string memory basePrompt,
            string[] memory modifiers,
            uint40 creationTime,
            uint40 lastUpdate,
            bool isActive
        )
    {
        require(_exists(tokenId), "Token doesn't exist");
        AgentData storage agent = _agentData[tokenId];
        return (
            agent.agentId,
            agent.agentWallet,
            agent.basePrompt,
            agent.modifiers,
            agent.creationTime,
            agent.lastUpdate,
            agent.isActive
        );
    }

    /**
     * @dev Get agent actions
     */
    function getAgentActions(uint256 tokenId)
        external
        view
        returns (ActionData[] memory)
    {
        require(_exists(tokenId), "Token doesn't exist");
        return _agentActions[tokenId];
    }

    /**
     * @dev Get agent capability
     */
    function getAgentCapability(uint256 tokenId, string memory capability)
        external
        view
        returns (string memory)
    {
        require(_exists(tokenId), "Token doesn't exist");
        return _agentData[tokenId].capabilities[capability];
    }

    /**
     * @dev Check agent permission
     */
    function hasPermission(uint256 tokenId, string memory permission)
        external
        view
        returns (bool)
    {
        require(_exists(tokenId), "Token doesn't exist");
        return _agentPermissions[tokenId][permission];
    }

    /**
     * @dev Generate token URI with agent data
     */
    function tokenURI(uint256 tokenId)
        public
        view
        override
        returns (string memory)
    {
        require(_exists(tokenId), "Token doesn't exist");
        AgentData storage agent = _agentData[tokenId];
        
        return string(abi.encodePacked(
            "data:application/json;base64,",
            Base64.encode(bytes(abi.encodePacked(
                '{"name":"Agent #',
                tokenId.toString(),
                '","description":"',
                agent.basePrompt,
                '","agent_id":"',
                _toHexString(agent.agentId),
                '","creation_time":',
                agent.creationTime.toString(),
                '}'
            )))
        ));
    }

    // Helper function to convert bytes32 to hex string
    function _toHexString(bytes32 data)
        internal
        pure
        returns (string memory)
    {
        bytes memory alphabet = "0123456789abcdef";
        bytes memory str = new bytes(64);
        for (uint256 i = 0; i < 32; i++) {
            str[i*2] = alphabet[uint8(data[i] >> 4)];
            str[i*2+1] = alphabet[uint8(data[i] & 0x0f)];
        }
        return string(str);
    }
}
