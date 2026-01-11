// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title SoulBadger
 * @dev Soulbound token implementation for permanent agent credentials (ERC-5484 inspired).
 *
 * Features:
 * - Non-transferable (soulbound) tokens
 * - Agent identity binding
 * - Credential and badge management
 * - Integration with IDNFT for optional soulbound identities
 */
contract SoulBadger is ERC721, ERC721URIStorage, AccessControl, ReentrancyGuard {
    // Roles
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");

    // Burn authorization types (ERC-5484)
    enum BurnAuth {
        IssuerOnly,
        OwnerOnly,
        Both,
        Neither
    }

    // Badge/Credential structure
    struct SoulboundBadge {
        bytes32 badgeType;           // Type identifier
        address issuer;              // Who issued the badge
        address boundTo;             // Permanently bound to this address
        uint40 issuedAt;             // Issuance timestamp
        uint40 expiresAt;            // Expiration (0 = never)
        BurnAuth burnAuth;           // Who can burn this badge
        string metadataURI;          // Badge metadata
        bool isActive;               // Active status
    }

    // Agent credential data
    struct AgentCredentials {
        string agentType;            // Type of agent
        uint32 trustLevel;           // Trust level (0-10000)
        uint32 knowledgeLevel;       // Knowledge level (0-100)
        uint32 achievementCount;     // Number of achievements
        bytes32 domainHash;          // Domain specialization hash
        bool verified;               // Verification status
    }

    // State
    uint256 private _nextBadgeId;
    mapping(uint256 => SoulboundBadge) private _badges;
    mapping(uint256 => AgentCredentials) private _credentials;
    mapping(address => uint256[]) private _addressToBadges;
    mapping(bytes32 => uint256) private _badgeTypeCount;

    // Base URI for metadata
    string private _baseBadgeURI;

    // Events
    event SoulboundBadgeMinted(
        uint256 indexed badgeId,
        address indexed boundTo,
        bytes32 indexed badgeType,
        address issuer
    );

    event BadgeRevoked(
        uint256 indexed badgeId,
        address indexed revokedBy,
        string reason
    );

    event CredentialsUpdated(
        uint256 indexed badgeId,
        uint32 trustLevel,
        uint32 knowledgeLevel
    );

    event BadgeExpired(uint256 indexed badgeId);

    // Errors
    error TransferNotAllowed();
    error BadgeNotActive();
    error NotAuthorizedToBurn();
    error BadgeExpiredError();
    error InvalidBadgeType();

    constructor(
        string memory name_,
        string memory symbol_,
        string memory baseBadgeURI_
    ) ERC721(name_, symbol_) {
        _baseBadgeURI = baseBadgeURI_;
        _nextBadgeId = 1;

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
    }

    // ============ Minting Functions ============

    /**
     * @dev Mints a soulbound badge to an address
     * @param to Address to bind the badge to
     * @param badgeType Type identifier for the badge
     * @param expiresAt Expiration timestamp (0 = never expires)
     * @param burnAuthType Who can burn this badge
     * @param metadataURI Metadata URI for the badge
     * @return badgeId The ID of the minted badge
     */
    function mintSoulboundBadge(
        address to,
        bytes32 badgeType,
        uint40 expiresAt,
        BurnAuth burnAuthType,
        string memory metadataURI
    ) public onlyRole(MINTER_ROLE) nonReentrant returns (uint256 badgeId) {
        return _mintBadgeInternal(to, badgeType, expiresAt, burnAuthType, metadataURI);
    }

    /**
     * @dev Internal minting logic
     */
    function _mintBadgeInternal(
        address to,
        bytes32 badgeType,
        uint40 expiresAt,
        BurnAuth burnAuthType,
        string memory metadataURI
    ) internal returns (uint256 badgeId) {
        require(to != address(0), "Cannot mint to zero address");
        require(badgeType != bytes32(0), "Invalid badge type");

        badgeId = _nextBadgeId++;

        _badges[badgeId] = SoulboundBadge({
            badgeType: badgeType,
            issuer: msg.sender,
            boundTo: to,
            issuedAt: uint40(block.timestamp),
            expiresAt: expiresAt,
            burnAuth: burnAuthType,
            metadataURI: metadataURI,
            isActive: true
        });

        _addressToBadges[to].push(badgeId);
        _badgeTypeCount[badgeType]++;

        _safeMint(to, badgeId);

        emit SoulboundBadgeMinted(badgeId, to, badgeType, msg.sender);
        return badgeId;
    }

    /**
     * @dev Mints a soulbound badge with agent credentials
     * @param to Address to bind the badge to
     * @param badgeType Type identifier for the badge
     * @param agentType Type of agent
     * @param trustLevel Initial trust level
     * @param knowledgeLevel Initial knowledge level
     * @param domainHash Domain specialization hash
     * @param metadataURI Metadata URI
     * @return badgeId The ID of the minted badge
     */
    function mintAgentCredentialBadge(
        address to,
        bytes32 badgeType,
        string memory agentType,
        uint32 trustLevel,
        uint32 knowledgeLevel,
        bytes32 domainHash,
        string memory metadataURI
    ) external onlyRole(MINTER_ROLE) nonReentrant returns (uint256 badgeId) {
        require(trustLevel <= 10000, "Trust level out of range");
        require(knowledgeLevel <= 100, "Knowledge level out of range");

        badgeId = _mintBadgeInternal(
            to,
            badgeType,
            0, // Never expires
            BurnAuth.Neither, // Permanent credential
            metadataURI
        );

        _credentials[badgeId] = AgentCredentials({
            agentType: agentType,
            trustLevel: trustLevel,
            knowledgeLevel: knowledgeLevel,
            achievementCount: 0,
            domainHash: domainHash,
            verified: true
        });

        emit CredentialsUpdated(badgeId, trustLevel, knowledgeLevel);
        return badgeId;
    }

    // ============ Credential Management ============

    /**
     * @dev Updates agent credentials for a badge
     * @param badgeId Badge to update
     * @param trustLevel New trust level
     * @param knowledgeLevel New knowledge level
     */
    function updateCredentials(
        uint256 badgeId,
        uint32 trustLevel,
        uint32 knowledgeLevel
    ) external onlyRole(ADMIN_ROLE) {
        require(_badges[badgeId].isActive, "Badge not active");
        require(trustLevel <= 10000, "Trust level out of range");
        require(knowledgeLevel <= 100, "Knowledge level out of range");

        _credentials[badgeId].trustLevel = trustLevel;
        _credentials[badgeId].knowledgeLevel = knowledgeLevel;

        emit CredentialsUpdated(badgeId, trustLevel, knowledgeLevel);
    }

    /**
     * @dev Increments achievement count for a badge
     * @param badgeId Badge to update
     */
    function addAchievement(uint256 badgeId) external onlyRole(ADMIN_ROLE) {
        require(_badges[badgeId].isActive, "Badge not active");
        _credentials[badgeId].achievementCount++;
    }

    /**
     * @dev Verifies or unverifies a badge
     * @param badgeId Badge to update
     * @param verified New verification status
     */
    function setVerificationStatus(
        uint256 badgeId,
        bool verified
    ) external onlyRole(ADMIN_ROLE) {
        require(_badges[badgeId].isActive, "Badge not active");
        _credentials[badgeId].verified = verified;
    }

    // ============ Badge Revocation ============

    /**
     * @dev Revokes (burns) a soulbound badge
     * @param badgeId Badge to revoke
     * @param reason Reason for revocation
     */
    function revokeBadge(
        uint256 badgeId,
        string calldata reason
    ) external nonReentrant {
        SoulboundBadge storage badge = _badges[badgeId];
        require(badge.isActive, "Badge not active");

        // Check burn authorization
        bool authorized = false;
        if (badge.burnAuth == BurnAuth.IssuerOnly) {
            authorized = msg.sender == badge.issuer || hasRole(ADMIN_ROLE, msg.sender);
        } else if (badge.burnAuth == BurnAuth.OwnerOnly) {
            authorized = msg.sender == badge.boundTo;
        } else if (badge.burnAuth == BurnAuth.Both) {
            authorized = msg.sender == badge.issuer ||
                         msg.sender == badge.boundTo ||
                         hasRole(ADMIN_ROLE, msg.sender);
        } else if (badge.burnAuth == BurnAuth.Neither) {
            authorized = false; // Truly soulbound
        }

        require(authorized, "Not authorized to revoke");

        badge.isActive = false;
        _burn(badgeId);

        emit BadgeRevoked(badgeId, msg.sender, reason);
    }

    // ============ Query Functions ============

    /**
     * @dev Checks if a badge is expired
     * @param badgeId Badge to check
     * @return expired Whether the badge is expired
     */
    function isBadgeExpired(uint256 badgeId) public view returns (bool expired) {
        SoulboundBadge storage badge = _badges[badgeId];
        if (badge.expiresAt == 0) return false;
        return block.timestamp > badge.expiresAt;
    }

    /**
     * @dev Checks if a badge is valid (active and not expired)
     * @param badgeId Badge to check
     * @return valid Whether the badge is valid
     */
    function isBadgeValid(uint256 badgeId) public view returns (bool valid) {
        SoulboundBadge storage badge = _badges[badgeId];
        return badge.isActive && !isBadgeExpired(badgeId);
    }

    /**
     * @dev Gets badge data
     * @param badgeId Badge to query
     * @return badge The badge data
     */
    function getBadge(uint256 badgeId) external view returns (SoulboundBadge memory badge) {
        return _badges[badgeId];
    }

    /**
     * @dev Gets agent credentials for a badge
     * @param badgeId Badge to query
     * @return credentials The agent credentials
     */
    function getCredentials(uint256 badgeId) external view returns (AgentCredentials memory credentials) {
        return _credentials[badgeId];
    }

    /**
     * @dev Gets all badge IDs for an address
     * @param owner Address to query
     * @return badgeIds Array of badge IDs
     */
    function getBadgesForAddress(address owner) external view returns (uint256[] memory badgeIds) {
        return _addressToBadges[owner];
    }

    /**
     * @dev Gets burn authorization for a badge (ERC-5484)
     * @param badgeId Badge to query
     * @return burnAuth The burn authorization type
     */
    function burnAuth(uint256 badgeId) external view returns (BurnAuth) {
        return _badges[badgeId].burnAuth;
    }

    /**
     * @dev Gets total count of a specific badge type
     * @param badgeType Badge type to query
     * @return count Number of badges of this type
     */
    function getBadgeTypeCount(bytes32 badgeType) external view returns (uint256 count) {
        return _badgeTypeCount[badgeType];
    }

    // ============ Soulbound Enforcement ============

    /**
     * @dev Prevents transfers - soulbound tokens cannot be transferred
     */
    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal virtual override returns (address) {
        address from = _ownerOf(tokenId);

        // Allow minting and burning only
        if (from != address(0) && to != address(0)) {
            revert TransferNotAllowed();
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
        SoulboundBadge storage badge = _badges[tokenId];
        if (bytes(badge.metadataURI).length > 0) {
            return badge.metadataURI;
        }
        return super.tokenURI(tokenId);
    }

    function _baseURI() internal view override returns (string memory) {
        return _baseBadgeURI;
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
