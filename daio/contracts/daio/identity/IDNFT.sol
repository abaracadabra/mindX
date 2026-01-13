// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./SoulBadger.sol";

/**
 * @title IDNFT - Identity NFT with Optional Soulbound
 * @dev Enhanced agent identity management with prompt, persona, model dataset, and THOT support
 * @notice Supports both transferable and soulbound identities via SoulBadger integration
 */
contract IDNFT is ERC721, ERC721URIStorage, ReentrancyGuard, AccessControl {
    using ECDSA for bytes32;

    bytes32 public constant CREDENTIAL_ISSUER_ROLE = keccak256("CREDENTIAL_ISSUER_ROLE");
    bytes32 public constant VERIFIER_ROLE = keccak256("VERIFIER_ROLE");
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    uint256 private _tokenIdCounter;
    SoulBadger public immutable soulBadger; // Optional soulbound integration
    bool public soulboundEnabled;

    struct AgentIdentity {
        bytes32 agentId;          // Unique identifier
        address primaryWallet;    // Primary wallet address
        string agentType;         // Type of agent
        string prompt;            // System prompt from AutoMINDXAgent
        string persona;           // JSON-encoded persona metadata
        string modelDatasetCID;   // IPFS CID for model weights/dataset (optional)
        uint40 creationTime;      // Creation timestamp
        uint40 lastUpdate;        // Last update timestamp
        bool isActive;            // Active status
        uint16 trustScore;        // Agent trust score (0-10000)
        string metadataURI;       // Additional metadata URI
        bool isSoulbound;         // Soulbound flag
    }

    struct THOTTensor {
        bytes32 cid;              // IPFS CID for THOT tensor
        uint8 dimensions;         // 64, 512, or 768
        uint8 parallelUnits;      // Processing units
        uint40 attachedAt;        // Attachment timestamp
    }

    struct Credential {
        bytes32 credentialId;     // Unique credential identifier
        string credentialType;    // Type of credential
        bytes32 issuer;           // Issuer identifier
        uint40 issuanceTime;      // Issuance timestamp
        uint40 expirationTime;    // Expiration timestamp
        bytes signature;          // Issuer signature
        bool isRevoked;           // Revocation status
    }

    // Storage
    mapping(uint256 => AgentIdentity) private _identities;
    mapping(uint256 => THOTTensor[]) private _thotTensors; // Array of THOT tensors per identity
    mapping(address => uint256) private _walletToTokenId;
    mapping(bytes32 => uint256) private _agentIdToTokenId;
    mapping(uint256 => mapping(bytes32 => Credential)) private _credentials;
    mapping(uint256 => bytes32[]) private _credentialsList;
    mapping(bytes32 => bool) private _usedNonces;

    // Events
    event AgentIdentityCreated(
        uint256 indexed tokenId,
        bytes32 indexed agentId,
        address indexed primaryWallet,
        bool isSoulbound
    );

    event THOTTensorAttached(
        uint256 indexed tokenId,
        bytes32 indexed thotCID,
        uint8 dimensions
    );

    event CredentialIssued(
        uint256 indexed tokenId,
        bytes32 indexed credentialId,
        string credentialType
    );

    event CredentialRevoked(
        uint256 indexed tokenId,
        bytes32 indexed credentialId,
        uint40 timestamp
    );

    event TrustScoreUpdated(
        uint256 indexed tokenId,
        uint16 oldScore,
        uint16 newScore
    );

    event PersonaUpdated(
        uint256 indexed tokenId,
        string newPersona
    );

    constructor(address _soulBadgerAddress) ERC721("Agent Identity NFT", "IDNFT") {
        if (_soulBadgerAddress != address(0)) {
            soulBadger = SoulBadger(_soulBadgerAddress);
            soulboundEnabled = true;
        }
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(CREDENTIAL_ISSUER_ROLE, msg.sender);
        _grantRole(VERIFIER_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
    }

    /**
     * @dev Create new agent identity with full iNFT metadata
     * @param primaryWallet Ethereum wallet address for agent
     * @param agentType Type/category of agent
     * @param prompt System prompt from AutoMINDXAgent
     * @param persona JSON-encoded persona metadata
     * @param modelDatasetCID IPFS CID for model dataset (empty string if not applicable)
     * @param metadataURI Additional metadata URI
     * @param nonce Nonce for uniqueness
     * @param useSoulbound Whether to create soulbound identity
     */
    function mintAgentIdentity(
        address primaryWallet,
        string memory agentType,
        string memory prompt,
        string memory persona,
        string memory modelDatasetCID,
        string memory metadataURI,
        bytes32 nonce,
        bool useSoulbound
    ) external nonReentrant onlyRole(MINTER_ROLE) returns (uint256) {
        require(!_usedNonces[nonce], "Nonce already used");
        require(primaryWallet != address(0), "Invalid wallet");
        require(_walletToTokenId[primaryWallet] == 0, "Wallet already registered");
        require(bytes(prompt).length > 0, "Prompt required");
        require(bytes(persona).length > 0, "Persona required");

        if (useSoulbound && soulboundEnabled) {
            require(address(soulBadger) != address(0), "SoulBadger not configured");
        }

        _usedNonces[nonce] = true;
        _tokenIdCounter++;
        uint256 tokenId = _tokenIdCounter;

        bytes32 agentId = keccak256(abi.encodePacked(
            primaryWallet,
            agentType,
            prompt,
            nonce,
            block.timestamp
        ));

        AgentIdentity memory identity = AgentIdentity({
            agentId: agentId,
            primaryWallet: primaryWallet,
            agentType: agentType,
            prompt: prompt,
            persona: persona,
            modelDatasetCID: modelDatasetCID,
            creationTime: uint40(block.timestamp),
            lastUpdate: uint40(block.timestamp),
            isActive: true,
            trustScore: 5000, // Initial middle trust score
            metadataURI: metadataURI,
            isSoulbound: useSoulbound
        });

        _identities[tokenId] = identity;
        _walletToTokenId[primaryWallet] = tokenId;
        _agentIdToTokenId[agentId] = tokenId;

        _safeMint(primaryWallet, tokenId);
        _setTokenURI(tokenId, metadataURI);

        // If soulbound, also mint in SoulBadger
        if (useSoulbound && soulboundEnabled) {
            // SoulBadger integration would happen here
            // This requires SoulBadger contract to have a mint function
        }

        emit AgentIdentityCreated(tokenId, agentId, primaryWallet, useSoulbound);
        return tokenId;
    }

    /**
     * @dev Attach THOT tensor to agent identity
     * @param tokenId Agent identity token ID
     * @param thotCID IPFS CID for THOT tensor
     * @param dimensions THOT dimensions (64, 512, or 768)
     * @param parallelUnits Number of parallel processing units
     */
    function attachTHOT(
        uint256 tokenId,
        bytes32 thotCID,
        uint8 dimensions,
        uint8 parallelUnits
    ) external onlyRole(MINTER_ROLE) returns (bool) {
        require(ownerOf(tokenId) != address(0), "Identity doesn't exist");
        require(
            dimensions == 64 || dimensions == 512 || dimensions == 768,
            "Invalid dimensions"
        );

        THOTTensor memory tensor = THOTTensor({
            cid: thotCID,
            dimensions: dimensions,
            parallelUnits: parallelUnits,
            attachedAt: uint40(block.timestamp)
        });

        _thotTensors[tokenId].push(tensor);
        emit THOTTensorAttached(tokenId, thotCID, dimensions);
        return true;
    }

    /**
     * @dev Update agent persona
     * @param tokenId Agent identity token ID
     * @param newPersona New persona JSON metadata
     */
    function updatePersona(
        uint256 tokenId,
        string memory newPersona
    ) external {
        require(ownerOf(tokenId) != address(0), "Identity doesn't exist");
        require(
            msg.sender == _identities[tokenId].primaryWallet ||
            hasRole(DEFAULT_ADMIN_ROLE, msg.sender),
            "Not authorized"
        );
        require(bytes(newPersona).length > 0, "Empty persona");

        _identities[tokenId].persona = newPersona;
        _identities[tokenId].lastUpdate = uint40(block.timestamp);
        emit PersonaUpdated(tokenId, newPersona);
    }

    /**
     * @dev Issue credential to agent
     */
    function issueCredential(
        uint256 tokenId,
        string memory credentialType,
        uint40 validityPeriod,
        bytes memory credentialData,
        bytes memory issuerSignature
    ) external onlyRole(CREDENTIAL_ISSUER_ROLE) {
        require(ownerOf(tokenId) != address(0), "Identity doesn't exist");
        require(_identities[tokenId].isActive, "Identity not active");

        bytes32 credentialId = keccak256(abi.encodePacked(
            tokenId,
            credentialType,
            block.timestamp,
            credentialData
        ));

        Credential memory credential = Credential({
            credentialId: credentialId,
            credentialType: credentialType,
            issuer: keccak256(abi.encodePacked(msg.sender)),
            issuanceTime: uint40(block.timestamp),
            expirationTime: uint40(block.timestamp + validityPeriod),
            signature: issuerSignature,
            isRevoked: false
        });

        _credentials[tokenId][credentialId] = credential;
        _credentialsList[tokenId].push(credentialId);

        emit CredentialIssued(tokenId, credentialId, credentialType);
    }

    /**
     * @dev Request credential verification
     */
    function verifyCredential(
        uint256 tokenId,
        bytes32 credentialId
    ) external view returns (bool isValid, string memory credentialType) {
        require(ownerOf(tokenId) != address(0), "Identity doesn't exist");
        
        Credential memory credential = _credentials[tokenId][credentialId];
        
        bool valid = (
            !credential.isRevoked &&
            credential.expirationTime > block.timestamp &&
            credential.issuanceTime > 0
        );

        return (valid, credential.credentialType);
    }

    /**
     * @dev Update agent trust score
     */
    function updateTrustScore(
        uint256 tokenId,
        uint16 newScore
    ) external onlyRole(VERIFIER_ROLE) {
        require(ownerOf(tokenId) != address(0), "Identity doesn't exist");
        require(newScore <= 10000, "Invalid score range");

        AgentIdentity storage identity = _identities[tokenId];
        uint16 oldScore = identity.trustScore;
        identity.trustScore = newScore;
        identity.lastUpdate = uint40(block.timestamp);

        emit TrustScoreUpdated(tokenId, oldScore, newScore);
    }

    /**
     * @dev Get agent identity data
     */
    function getAgentIdentity(uint256 tokenId)
        external
        view
        returns (AgentIdentity memory)
    {
        require(ownerOf(tokenId) != address(0), "Identity doesn't exist");
        return _identities[tokenId];
    }

    /**
     * @dev Get THOT tensors for agent
     */
    function getTHOTTensors(uint256 tokenId)
        external
        view
        returns (THOTTensor[] memory)
    {
        require(ownerOf(tokenId) != address(0), "Identity doesn't exist");
        return _thotTensors[tokenId];
    }

    /**
     * @dev Get agent credentials
     */
    function getAgentCredentials(uint256 tokenId)
        external
        view
        returns (bytes32[] memory)
    {
        require(ownerOf(tokenId) != address(0), "Identity doesn't exist");
        return _credentialsList[tokenId];
    }

    /**
     * @dev Get credential details
     */
    function getCredentialDetails(
        uint256 tokenId,
        bytes32 credentialId
    ) external view returns (Credential memory) {
        require(ownerOf(tokenId) != address(0), "Identity doesn't exist");
        return _credentials[tokenId][credentialId];
    }

    /**
     * @dev Get token ID by wallet address
     */
    function getTokenIdByWallet(address wallet)
        external
        view
        returns (uint256)
    {
        return _walletToTokenId[wallet];
    }

    /**
     * @dev Check if identity is soulbound
     */
    function isSoulbound(uint256 tokenId) external view returns (bool) {
        require(ownerOf(tokenId) != address(0), "Identity doesn't exist");
        return _identities[tokenId].isSoulbound;
    }

    /**
     * @dev Enable soulbound for existing identity (one-way operation)
     */
    function enableSoulbound(uint256 tokenId) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(ownerOf(tokenId) != address(0), "Identity doesn't exist");
        require(!_identities[tokenId].isSoulbound, "Already soulbound");
        require(soulboundEnabled && address(soulBadger) != address(0), "Soulbound not enabled");

        _identities[tokenId].isSoulbound = true;
        _identities[tokenId].lastUpdate = uint40(block.timestamp);
    }

    /**
     * @dev Revoke credential
     */
    function revokeCredential(
        uint256 tokenId,
        bytes32 credentialId
    ) external onlyRole(CREDENTIAL_ISSUER_ROLE) {
        require(ownerOf(tokenId) != address(0), "Identity doesn't exist");
        
        Credential storage credential = _credentials[tokenId][credentialId];
        require(!credential.isRevoked, "Already revoked");
        require(credential.issuanceTime > 0, "Credential doesn't exist");

        credential.isRevoked = true;
        emit CredentialRevoked(tokenId, credentialId, uint40(block.timestamp));
    }

    /**
     * @dev Override transfer to prevent soulbound transfers and handle URI clearing
     */
    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal override returns (address) {
        address from = _ownerOf(tokenId);
        
        // Prevent transfer if soulbound (except minting)
        if (from != address(0) && _identities[tokenId].isSoulbound && to != address(0)) {
            revert("Soulbound token cannot be transferred");
        }
        
        address result = super._update(to, tokenId, auth);
        
        // Clear URI if burning
        if (to == address(0) && from != address(0)) {
            _setTokenURI(tokenId, "");
        }
        
        return result;
    }

    /**
     * @dev Support interface check
     */
    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721URIStorage, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }

    function tokenURI(uint256 tokenId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (string memory)
    {
        return super.tokenURI(tokenId);
    }
}
