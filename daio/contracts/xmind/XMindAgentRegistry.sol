// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @notice Minimal interface for IDNFT mint used by XMindAgentRegistry (enables mocks in tests)
 */
interface IIDNFTMint {
    function mintAgentIdentity(
        address primaryWallet,
        string memory agentType,
        string memory prompt,
        string memory persona,
        string memory modelDatasetCID,
        string memory metadataURI,
        bytes32 nonce,
        bool useSoulbound
    ) external returns (uint256);
}

/**
 * @title XMindAgentRegistry
 * @notice Registry for mindX agents with IDNFT and AgentFactory integration
 * @dev Registers agents (optional IDNFT mint if this contract has MINTER_ROLE); AgentFactory.createAgent is governance-only and triggered off-chain or via governance
 */
contract XMindAgentRegistry is Ownable {
    IIDNFTMint public immutable idNFT;
    address public immutable agentFactory;

    struct RegisteredAgent {
        address agentAddress;
        uint256 idNFTTokenId;  // 0 if not minted via this registry
        uint256 registeredAt;
        bool active;
    }

    mapping(address => RegisteredAgent) public agents;
    address[] public agentList;
    mapping(address => uint256) public agentIndex;  // 1-based index in agentList, 0 = not in list

    event AgentRegistered(
        address indexed agentAddress,
        uint256 idNFTTokenId,
        uint256 registeredAt
    );
    event AgentDeactivated(address indexed agentAddress);
    event AgentCreationRequested(
        address indexed agentAddress,
        bytes32 metadataHash,
        string tokenName,
        string tokenSymbol,
        string nftMetadata,
        uint256 idNFTTokenId
    );

    constructor(address _idNFT, address _agentFactory) Ownable(msg.sender) {
        require(_idNFT != address(0), "Invalid IDNFT");
        require(_agentFactory != address(0), "Invalid AgentFactory");
        idNFT = IIDNFTMint(_idNFT);
        agentFactory = _agentFactory;
    }

    /**
     * @notice Register a mindX agent; optionally mint IDNFT identity if this contract has MINTER_ROLE
     */
    function registerAgent(
        address primaryWallet,
        string memory agentType,
        string memory prompt,
        string memory persona,
        string memory modelDatasetCID,
        string memory metadataURI,
        bytes32 nonce,
        bool useSoulbound
    ) external onlyOwner returns (uint256 idNFTTokenId) {
        require(primaryWallet != address(0), "Invalid wallet");
        require(!agents[primaryWallet].active, "Agent already registered");

        idNFTTokenId = 0;
        try idNFT.mintAgentIdentity(
            primaryWallet,
            agentType,
            prompt,
            persona,
            modelDatasetCID,
            metadataURI,
            nonce,
            useSoulbound
        ) returns (uint256 tokenId) {
            idNFTTokenId = tokenId;
        } catch {}

        agents[primaryWallet] = RegisteredAgent({
            agentAddress: primaryWallet,
            idNFTTokenId: idNFTTokenId,
            registeredAt: block.timestamp,
            active: true
        });
        agentList.push(primaryWallet);
        agentIndex[primaryWallet] = agentList.length;

        emit AgentRegistered(primaryWallet, idNFTTokenId, block.timestamp);
        return idNFTTokenId;
    }

    /**
     * @notice Emit a request for governance to create agent in AgentFactory (createAgent is onlyGovernance)
     */
    function requestAgentCreation(
        address agentAddress,
        bytes32 metadataHash,
        string memory tokenName,
        string memory tokenSymbol,
        string memory nftMetadata,
        uint256 idNFTTokenId
    ) external onlyOwner {
        require(agents[agentAddress].active, "Agent not registered");
        emit AgentCreationRequested(
            agentAddress,
            metadataHash,
            tokenName,
            tokenSymbol,
            nftMetadata,
            idNFTTokenId
        );
    }

    function deactivateAgent(address agentAddress) external onlyOwner {
        RegisteredAgent storage a = agents[agentAddress];
        require(a.active, "Not active");
        a.active = false;
        emit AgentDeactivated(agentAddress);
    }

    function getAgentCount() external view returns (uint256) {
        return agentList.length;
    }

    function getAgentAt(uint256 index) external view returns (address agentAddress, uint256 idNFTTokenId, uint256 registeredAt, bool active) {
        require(index < agentList.length, "Index out of bounds");
        address a = agentList[index];
        RegisteredAgent storage r = agents[a];
        return (r.agentAddress, r.idNFTTokenId, r.registeredAt, r.active);
    }
}
