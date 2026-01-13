// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "../identity/IDNFT.sol";
import "./KnowledgeHierarchyDAIO.sol";

/**
 * @title AgentFactory
 * @notice Production agent creation factory with ERC20 token and NFT governance
 * @dev Creates agents with custom ERC20 tokens and fractionalized NFTs
 * @dev Integrates with IDNFT for identity and KnowledgeHierarchyDAIO for governance
 */
contract AgentFactory is Ownable, ERC721URIStorage {
    struct Agent {
        address agentAddress;
        bool active;
        uint256 createdAt;
        address tokenAddress;      // Custom ERC20 token address
        uint256 nftId;            // NFT ID for governance rights
        bytes32 metadataHash;      // Metadata hash for gas optimization
        uint256 idNFTTokenId;      // Linked IDNFT token ID (optional)
    }

    // Storage
    mapping(address => Agent) public agents;
    mapping(uint256 => address) public nftToAgent;  // NFT ID => Agent address
    
    address public immutable governanceContract;
    IDNFT public idNFT;
    KnowledgeHierarchyDAIO public knowledgeHierarchy;
    
    uint256 public agentCount;
    string private _baseTokenURI;

    // Events
    event AgentCreated(
        address indexed agentAddress,
        uint256 timestamp,
        bytes32 metadataHash,
        address tokenAddress,
        uint256 nftId,
        uint256 idNFTTokenId
    );
    event AgentDestroyed(address indexed agentAddress, uint256 timestamp);
    event AgentReactivated(address indexed agentAddress, uint256 timestamp);
    event NFTMetadataUpdated(uint256 indexed nftId, string newMetadata);

    modifier onlyGovernance() {
        require(
            msg.sender == governanceContract,
            "Only governance contract"
        );
        _;
    }

    constructor(
        address _governanceContract,
        address _idNFT,
        address _knowledgeHierarchy
    ) ERC721("AgentNFTCollection", "ANFT") Ownable(msg.sender) {
        require(_governanceContract != address(0), "Invalid governance");
        require(_idNFT != address(0), "Invalid IDNFT");
        require(_knowledgeHierarchy != address(0), "Invalid KnowledgeHierarchy");
        
        governanceContract = _governanceContract;
        idNFT = IDNFT(_idNFT);
        knowledgeHierarchy = KnowledgeHierarchyDAIO(_knowledgeHierarchy);
    }

    /**
     * @notice Create agent with ERC20 token and NFT
     * @param _agentAddress Agent address
     * @param _metadataHash Metadata hash
     * @param _tokenName ERC20 token name
     * @param _tokenSymbol ERC20 token symbol
     * @param _nftMetadata NFT metadata URI
     * @param _idNFTTokenId Optional IDNFT token ID for identity linking
     */
    function createAgent(
        address _agentAddress,
        bytes32 _metadataHash,
        string memory _tokenName,
        string memory _tokenSymbol,
        string memory _nftMetadata,
        uint256 _idNFTTokenId
    ) external onlyGovernance {
        require(_agentAddress != address(0), "Invalid agent address");
        require(!agents[_agentAddress].active, "Agent already exists");

        // Create custom ERC20 token for agent
        AgentToken customToken = new AgentToken(_tokenName, _tokenSymbol, _agentAddress);
        address tokenAddress = address(customToken);

        // Create fractionalized NFT for governance
        agentCount++;
        uint256 nftId = agentCount;
        _safeMint(_agentAddress, nftId);
        _setTokenURI(nftId, _nftMetadata);
        nftToAgent[nftId] = _agentAddress;

        // Store agent details
        agents[_agentAddress] = Agent({
            agentAddress: _agentAddress,
            active: true,
            createdAt: block.timestamp,
            tokenAddress: tokenAddress,
            nftId: nftId,
            metadataHash: _metadataHash,
            idNFTTokenId: _idNFTTokenId
        });

        emit AgentCreated(
            _agentAddress,
            block.timestamp,
            _metadataHash,
            tokenAddress,
            nftId,
            _idNFTTokenId
        );
    }

    /**
     * @notice Update NFT metadata
     * @param nftId NFT ID
     * @param newMetadata New metadata URI
     */
    function updateNFTMetadata(
        uint256 nftId,
        string memory newMetadata
    ) external {
        require(ownerOf(nftId) == msg.sender, "Only owner can update");
        _setTokenURI(nftId, newMetadata);
        emit NFTMetadataUpdated(nftId, newMetadata);
    }

    /**
     * @notice Reactivate inactive agent
     * @param _agentAddress Agent address
     */
    function reactivateAgent(address _agentAddress) external onlyGovernance {
        require(!agents[_agentAddress].active, "Agent already active");
        require(agents[_agentAddress].agentAddress != address(0), "Agent doesn't exist");

        agents[_agentAddress].active = true;
        emit AgentReactivated(_agentAddress, block.timestamp);
    }

    /**
     * @notice Destroy agent
     * @param _agentAddress Agent address
     */
    function destroyAgent(address _agentAddress) external onlyGovernance {
        require(agents[_agentAddress].active, "Agent already inactive");

        agents[_agentAddress].active = false;
        emit AgentDestroyed(_agentAddress, block.timestamp);
    }

    /**
     * @notice Check if agent is active
     * @param _agentAddress Agent address
     * @return bool Active status
     */
    function isAgentActive(address _agentAddress) external view returns (bool) {
        return agents[_agentAddress].active;
    }

    /**
     * @notice Get agent by NFT ID
     * @param nftId NFT ID
     * @return Agent struct
     */
    function getAgentByNFT(uint256 nftId) external view returns (Agent memory) {
        address agentAddress = nftToAgent[nftId];
        require(agentAddress != address(0), "NFT not linked to agent");
        return agents[agentAddress];
    }
}

/**
 * @title AgentToken
 * @notice Custom ERC20 token for agent governance
 */
contract AgentToken is ERC20 {
    address public immutable agentAddress;

    constructor(
        string memory name,
        string memory symbol,
        address _agentAddress
    ) ERC20(name, symbol) {
        agentAddress = _agentAddress;
        // Mint initial supply to agent
        _mint(_agentAddress, 1000000 * 10**decimals());
    }
}
