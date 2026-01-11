// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title SoulBadger - Soulbound Token Implementation
 * @dev Non-transferable NFTs for permanent agent credentials
 * @notice Inspired by ERC-5484, provides soulbound functionality for DAIO
 */
contract SoulBadger is ERC721, AccessControl {
    bytes32 public constant BADGE_ISSUER_ROLE = keccak256("BADGE_ISSUER_ROLE");

    struct UserIdentity {
        string username;
        string class;
        uint32 level;
        uint32 health;
        uint32 stamina;
        uint32 strength;
        uint32 intelligence;
        uint32 dexterity;
    }

    mapping(uint256 => UserIdentity) private _userIdentities;
    mapping(uint256 => address) private _badgeOwners;
    mapping(uint256 => uint256) private _badgeToTokenId; // Link to IDNFT token ID
    string private _baseBadgeUri;
    uint256 private _nextBadgeId;

    event BadgeMinted(
        uint256 indexed badgeId,
        address indexed to,
        uint256 indexed linkedTokenId
    );

    constructor(
        string memory name_,
        string memory symbol_,
        string memory baseBadgeUri_
    ) ERC721(name_, symbol_) {
        _baseBadgeUri = baseBadgeUri_;
        _nextBadgeId = 1;
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(BADGE_ISSUER_ROLE, msg.sender);
    }

    function safeMint(
        address to,
        string memory username,
        string memory class_,
        uint32 level,
        uint32 health,
        uint32 stamina,
        uint32 strength,
        uint32 intelligence,
        uint32 dexterity,
        uint256 linkedTokenId
    ) external onlyRole(BADGE_ISSUER_ROLE) returns (uint256) {
        uint256 badgeId = _nextBadgeId++;
        _safeMint(to, badgeId);

        _userIdentities[badgeId] = UserIdentity(
            username,
            class_,
            level,
            health,
            stamina,
            strength,
            intelligence,
            dexterity
        );

        _badgeOwners[badgeId] = to;
        if (linkedTokenId > 0) {
            _badgeToTokenId[badgeId] = linkedTokenId;
        }

        emit BadgeMinted(badgeId, to, linkedTokenId);
        return badgeId;
    }

    function getUserIdentity(uint256 badgeId)
        external
        view
        returns (
            string memory,
            string memory,
            uint32,
            uint32,
            uint32,
            uint32,
            uint32,
            uint32
        )
    {
        address owner = _badgeOwners[badgeId];
        require(owner != address(0), "Nonexistent badge");
        UserIdentity storage identity = _userIdentities[badgeId];
        return (
            identity.username,
            identity.class,
            identity.level,
            identity.health,
            identity.stamina,
            identity.strength,
            identity.intelligence,
            identity.dexterity
        );
    }

    function ownerOf(uint256 badgeId) public view override returns (address) {
        address owner = _badgeOwners[badgeId];
        require(owner != address(0), "Owner query for nonexistent token");
        return owner;
    }

    function getLinkedTokenId(uint256 badgeId) external view returns (uint256) {
        return _badgeToTokenId[badgeId];
    }

    function _baseURI() internal view override returns (string memory) {
        return _baseBadgeUri;
    }

    // Prevent transfers to enforce soulbound behavior
    function _beforeTokenTransfer(
        address from,
        address /* to */,
        uint256 /* tokenId */,
        uint256 /* batchSize */
    ) internal virtual override {
        require(from == address(0), "Soulbound: token transfer is BLOCKED");
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, AccessControl)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
