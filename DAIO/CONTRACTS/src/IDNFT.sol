// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

interface ISoulBadger {
    function mintSoulboundBadge(
        address to,
        bytes32 badgeType,
        uint40 expiresAt,
        uint8 burnAuth,
        string memory metadataURI
    ) external returns (uint256);
}

/**
 * @title IDNFT
 * @dev Agent Identity NFT with THOT integration, persona management, and optional soulbound functionality.
 *
 * Features:
 * - Agent identity and persona management
 * - THOT tensor attachment (THOT8d, THOT512, THOT768)
 * - Model dataset CID storage
 * - Credential issuance and verification
 * - Optional soulbound via SoulBadger integration
 * - Trust score tracking
 */
contract IDNFT is ERC721, ERC721URIStorage, AccessControl, ReentrancyGuard {
    using ECDSA for bytes32;

    // Roles
    bytes32 public constant CREDENTIAL_ISSUER_ROLE = keccak256("CREDENTIAL_ISSUER_ROLE");
    bytes32 public constant VERIFIER_ROLE = keccak256("VERIFIER_ROLE");
    bytes32 public constant GOVERNANCE_ROLE = keccak256("GOVERNANCE_ROLE");

    // THOT Dimension types
    uint8 public constant THOT_8D = 8;
    uint8 public constant THOT_512 = 64;  // 8x8x8 3D = 512 points stored as 64
    uint8 public constant THOT_768 = 128; // 768-dim stored as 128

    // Agent Identity structure
    struct AgentIdentity {
        bytes32 agentId;              // Unique identifier
        address primaryWallet;         // Primary wallet address
        string agentType;              // Type of agent (BDIAgent, MastermindAgent, etc.)
        string prompt;                 // System prompt defining agent behavior
        string persona;                // JSON-encoded persona metadata
        uint40 creationTime;           // Creation timestamp
        uint40 lastUpdate;             // Last update timestamp
        bool isActive;                 // Active status
        uint16 trustScore;             // Trust score (0-10000)
        bool isSoulbound;              // Soulbound status
    }

    // THOT Tensor attachment
    struct THOTAttachment {
        bytes32 thotCID;              // IPFS CID for THOT tensor data
        uint8 dimensions;              // THOT dimensions (8, 64, 128)
        uint8 parallelUnits;           // Number of parallel processing units
        uint40 attachedAt;             // When attached
        bool verified;                 // Verification status
    }

    // Model Dataset reference
    struct ModelDataset {
        bytes32 datasetCID;            // IPFS CID for model weights/dataset
        string modelArchitecture;      // Model architecture identifier
        uint40 uploadedAt;             // Upload timestamp
        bool verified;                 // Verification status
    }

    // Credential structure
    struct Credential {
        bytes32 credentialId;          // Unique credential identifier
        string credentialType;         // Type of credential
        bytes32 issuer;                // Issuer identifier
        uint40 issuanceTime;           // Issuance timestamp
        uint40 expirationTime;         // Expiration timestamp
        bytes signature;               // Issuer signature
        bool isRevoked;                // Revocation status
    }

    // State
    uint256 private _tokenIdCounter;
    ISoulBadger public soulBadger;

    mapping(uint256 => AgentIdentity) private _identities;
    mapping(uint256 => THOTAttachment[]) private _thotAttachments;
    mapping(uint256 => ModelDataset) private _modelDatasets;
    mapping(uint256 => mapping(bytes32 => Credential)) private _credentials;
    mapping(uint256 => bytes32[]) private _credentialsList;

    mapping(address => uint256) private _walletToTokenId;
    mapping(bytes32 => uint256) private _agentIdToTokenId;
    mapping(bytes32 => bool) private _usedNonces;

    // Events
    event AgentIdentityCreated(
        uint256 indexed tokenId,
        bytes32 indexed agentId,
        address indexed primaryWallet,
        string agentType
    );

    event PersonaUpdated(
        uint256 indexed tokenId,
        string newPrompt,
        string newPersona
    );

    event THOTAttached(
        uint256 indexed tokenId,
        bytes32 indexed thotCID,
        uint8 dimensions,
        uint8 parallelUnits
    );

    event ModelDatasetAttached(
        uint256 indexed tokenId,
        bytes32 indexed datasetCID,
        string modelArchitecture
    );

    event CredentialIssued(
        uint256 indexed tokenId,
        bytes32 indexed credentialId,
        string credentialType
    );

    event CredentialRevoked(
        uint256 indexed tokenId,
        bytes32 indexed credentialId
    );

    event TrustScoreUpdated(
        uint256 indexed tokenId,
        uint16 oldScore,
        uint16 newScore
    );

    event SoulboundEnabled(
        uint256 indexed tokenId,
        uint256 soulBadgeId
    );

    // Errors
    error WalletAlreadyRegistered();
    error InvalidWallet();
    error IdentityNotActive();
    error NonceAlreadyUsed();
    error InvalidTHOTDimensions();
    error AlreadySoulbound();
    error SoulBadgerNotConfigured();

    constructor() ERC721("Agent Identity NFT", "IDNFT") {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(CREDENTIAL_ISSUER_ROLE, msg.sender);
        _grantRole(VERIFIER_ROLE, msg.sender);
        _grantRole(GOVERNANCE_ROLE, msg.sender);
    }

    // ============ Configuration ============

    /**
     * @dev Sets the SoulBadger contract address
     * @param _soulBadger Address of the SoulBadger contract
     */
    function setSoulBadger(address _soulBadger) external onlyRole(DEFAULT_ADMIN_ROLE) {
        soulBadger = ISoulBadger(_soulBadger);
    }

    // ============ Identity Creation ============

    /**
     * @dev Mints a new agent identity NFT
     * @param primaryWallet Primary wallet address for the agent
     * @param agentType Type of agent
     * @param prompt System prompt defining agent behavior
     * @param persona JSON-encoded persona metadata
     * @param metadataURI Additional metadata URI
     * @param useSoulbound Whether to make the identity soulbound
     * @return tokenId The ID of the minted token
     */
    function mintAgentIdentity(
        address primaryWallet,
        string memory agentType,
        string memory prompt,
        string memory persona,
        string memory metadataURI,
        bool useSoulbound
    ) external onlyRole(GOVERNANCE_ROLE) nonReentrant returns (uint256 tokenId) {
        if (primaryWallet == address(0)) revert InvalidWallet();
        if (_walletToTokenId[primaryWallet] != 0) revert WalletAlreadyRegistered();

        _tokenIdCounter++;
        tokenId = _tokenIdCounter;

        bytes32 agentId = keccak256(abi.encodePacked(
            primaryWallet,
            agentType,
            block.timestamp,
            block.number
        ));

        _identities[tokenId] = AgentIdentity({
            agentId: agentId,
            primaryWallet: primaryWallet,
            agentType: agentType,
            prompt: prompt,
            persona: persona,
            creationTime: uint40(block.timestamp),
            lastUpdate: uint40(block.timestamp),
            isActive: true,
            trustScore: 5000, // Initial middle trust score
            isSoulbound: useSoulbound
        });

        _walletToTokenId[primaryWallet] = tokenId;
        _agentIdToTokenId[agentId] = tokenId;

        _safeMint(primaryWallet, tokenId);
        _setTokenURI(tokenId, metadataURI);

        emit AgentIdentityCreated(tokenId, agentId, primaryWallet, agentType);

        // If soulbound, also mint a SoulBadger badge
        if (useSoulbound && address(soulBadger) != address(0)) {
            uint256 soulBadgeId = soulBadger.mintSoulboundBadge(
                primaryWallet,
                keccak256(abi.encodePacked("AGENT_IDENTITY")),
                0, // Never expires
                3, // Neither can burn (truly soulbound)
                metadataURI
            );
            emit SoulboundEnabled(tokenId, soulBadgeId);
        }

        return tokenId;
    }

    /**
     * @dev Mints a soulbound agent identity
     */
    function mintSoulboundIdentity(
        address primaryWallet,
        string memory agentType,
        string memory prompt,
        string memory persona,
        string memory metadataURI
    ) external onlyRole(GOVERNANCE_ROLE) returns (uint256) {
        return this.mintAgentIdentity(
            primaryWallet,
            agentType,
            prompt,
            persona,
            metadataURI,
            true
        );
    }

    // ============ Persona Management ============

    /**
     * @dev Updates agent persona and prompt
     * @param tokenId Token to update
     * @param newPrompt New system prompt
     * @param newPersona New persona JSON
     */
    function updatePersona(
        uint256 tokenId,
        string memory newPrompt,
        string memory newPersona
    ) external {
        require(
            ownerOf(tokenId) == msg.sender || hasRole(GOVERNANCE_ROLE, msg.sender),
            "Not authorized"
        );
        require(_identities[tokenId].isActive, "Identity not active");

        AgentIdentity storage identity = _identities[tokenId];
        identity.prompt = newPrompt;
        identity.persona = newPersona;
        identity.lastUpdate = uint40(block.timestamp);

        emit PersonaUpdated(tokenId, newPrompt, newPersona);
    }

    // ============ THOT Integration ============

    /**
     * @dev Attaches a THOT tensor to an agent identity
     * @param tokenId Agent token ID
     * @param thotCID IPFS CID for THOT tensor data
     * @param dimensions THOT dimensions (8, 64, or 128)
     * @param parallelUnits Number of parallel processing units
     * @return success Whether attachment succeeded
     */
    function attachTHOT(
        uint256 tokenId,
        bytes32 thotCID,
        uint8 dimensions,
        uint8 parallelUnits
    ) external onlyRole(GOVERNANCE_ROLE) returns (bool success) {
        require(_identities[tokenId].isActive, "Identity not active");

        // Validate dimensions
        if (dimensions != THOT_8D && dimensions != THOT_512 && dimensions != THOT_768) {
            revert InvalidTHOTDimensions();
        }

        THOTAttachment memory attachment = THOTAttachment({
            thotCID: thotCID,
            dimensions: dimensions,
            parallelUnits: parallelUnits,
            attachedAt: uint40(block.timestamp),
            verified: true
        });

        _thotAttachments[tokenId].push(attachment);
        _identities[tokenId].lastUpdate = uint40(block.timestamp);

        emit THOTAttached(tokenId, thotCID, dimensions, parallelUnits);
        return true;
    }

    /**
     * @dev Attaches a model dataset to an agent identity
     * @param tokenId Agent token ID
     * @param datasetCID IPFS CID for model weights/dataset
     * @param modelArchitecture Model architecture identifier
     */
    function attachModelDataset(
        uint256 tokenId,
        bytes32 datasetCID,
        string memory modelArchitecture
    ) external onlyRole(GOVERNANCE_ROLE) {
        require(_identities[tokenId].isActive, "Identity not active");

        _modelDatasets[tokenId] = ModelDataset({
            datasetCID: datasetCID,
            modelArchitecture: modelArchitecture,
            uploadedAt: uint40(block.timestamp),
            verified: true
        });

        _identities[tokenId].lastUpdate = uint40(block.timestamp);

        emit ModelDatasetAttached(tokenId, datasetCID, modelArchitecture);
    }

    // ============ Credential Management ============

    /**
     * @dev Issues a credential to an agent
     * @param tokenId Agent token ID
     * @param credentialType Type of credential
     * @param validityPeriod How long the credential is valid
     * @param credentialData Additional credential data
     * @param issuerSignature Signature from issuer
     */
    function issueCredential(
        uint256 tokenId,
        string memory credentialType,
        uint40 validityPeriod,
        bytes memory credentialData,
        bytes memory issuerSignature
    ) external onlyRole(CREDENTIAL_ISSUER_ROLE) {
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
     * @dev Revokes a credential
     * @param tokenId Agent token ID
     * @param credentialId Credential to revoke
     */
    function revokeCredential(
        uint256 tokenId,
        bytes32 credentialId
    ) external onlyRole(CREDENTIAL_ISSUER_ROLE) {
        require(_credentials[tokenId][credentialId].issuanceTime > 0, "Credential not found");
        require(!_credentials[tokenId][credentialId].isRevoked, "Already revoked");

        _credentials[tokenId][credentialId].isRevoked = true;

        emit CredentialRevoked(tokenId, credentialId);
    }

    /**
     * @dev Verifies a credential
     * @param tokenId Agent token ID
     * @param credentialId Credential to verify
     * @return isValid Whether the credential is valid
     * @return credentialType The type of credential
     */
    function verifyCredential(
        uint256 tokenId,
        bytes32 credentialId
    ) external view returns (bool isValid, string memory credentialType) {
        Credential memory credential = _credentials[tokenId][credentialId];

        bool valid = (
            !credential.isRevoked &&
            credential.expirationTime > block.timestamp &&
            credential.issuanceTime > 0
        );

        return (valid, credential.credentialType);
    }

    // ============ Trust Score ============

    /**
     * @dev Updates agent trust score
     * @param tokenId Agent token ID
     * @param newScore New trust score (0-10000)
     */
    function updateTrustScore(
        uint256 tokenId,
        uint16 newScore
    ) external onlyRole(VERIFIER_ROLE) {
        require(_identities[tokenId].isActive, "Identity not active");
        require(newScore <= 10000, "Invalid score range");

        AgentIdentity storage identity = _identities[tokenId];
        uint16 oldScore = identity.trustScore;
        identity.trustScore = newScore;
        identity.lastUpdate = uint40(block.timestamp);

        emit TrustScoreUpdated(tokenId, oldScore, newScore);
    }

    // ============ Soulbound Management ============

    /**
     * @dev Converts an existing IDNFT to soulbound (one-way operation)
     * @param tokenId Token to convert
     */
    function enableSoulbound(uint256 tokenId) external returns (bool) {
        require(ownerOf(tokenId) == msg.sender, "Not owner");
        require(!_identities[tokenId].isSoulbound, "Already soulbound");

        if (address(soulBadger) == address(0)) revert SoulBadgerNotConfigured();

        _identities[tokenId].isSoulbound = true;
        _identities[tokenId].lastUpdate = uint40(block.timestamp);

        uint256 soulBadgeId = soulBadger.mintSoulboundBadge(
            msg.sender,
            keccak256(abi.encodePacked("AGENT_IDENTITY")),
            0,
            3,
            tokenURI(tokenId)
        );

        emit SoulboundEnabled(tokenId, soulBadgeId);
        return true;
    }

    /**
     * @dev Checks if an identity is soulbound
     * @param tokenId Token to check
     * @return Whether the identity is soulbound
     */
    function isSoulbound(uint256 tokenId) external view returns (bool) {
        return _identities[tokenId].isSoulbound;
    }

    /**
     * @dev Gets the SoulBadger contract address
     * @return Address of SoulBadger contract
     */
    function getSoulBadgerAddress() external view returns (address) {
        return address(soulBadger);
    }

    // ============ Query Functions ============

    /**
     * @dev Gets agent identity data
     * @param tokenId Token to query
     * @return identity The agent identity
     */
    function getAgentIdentity(uint256 tokenId) external view returns (AgentIdentity memory identity) {
        return _identities[tokenId];
    }

    /**
     * @dev Gets THOT attachments for an agent
     * @param tokenId Token to query
     * @return attachments Array of THOT attachments
     */
    function getTHOTAttachments(uint256 tokenId) external view returns (THOTAttachment[] memory attachments) {
        return _thotAttachments[tokenId];
    }

    /**
     * @dev Gets model dataset for an agent
     * @param tokenId Token to query
     * @return dataset The model dataset
     */
    function getModelDataset(uint256 tokenId) external view returns (ModelDataset memory dataset) {
        return _modelDatasets[tokenId];
    }

    /**
     * @dev Gets credential list for an agent
     * @param tokenId Token to query
     * @return credentialIds Array of credential IDs
     */
    function getAgentCredentials(uint256 tokenId) external view returns (bytes32[] memory credentialIds) {
        return _credentialsList[tokenId];
    }

    /**
     * @dev Gets token ID by wallet address
     * @param wallet Wallet to query
     * @return tokenId The token ID (0 if not found)
     */
    function getTokenIdByWallet(address wallet) external view returns (uint256 tokenId) {
        return _walletToTokenId[wallet];
    }

    /**
     * @dev Gets token ID by agent ID
     * @param agentId Agent ID to query
     * @return tokenId The token ID (0 if not found)
     */
    function getTokenIdByAgentId(bytes32 agentId) external view returns (uint256 tokenId) {
        return _agentIdToTokenId[agentId];
    }

    // ============ Transfer Controls ============

    /**
     * @dev Override to enforce soulbound restrictions
     */
    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal virtual override returns (address) {
        address from = _ownerOf(tokenId);

        // If soulbound, only allow minting and burning
        if (_identities[tokenId].isSoulbound && from != address(0) && to != address(0)) {
            revert("Transfer blocked: soulbound identity");
        }

        return super._update(to, tokenId, auth);
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
