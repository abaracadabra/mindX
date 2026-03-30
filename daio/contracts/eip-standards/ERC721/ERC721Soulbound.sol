// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title ERC721Soulbound
 * @notice ERC721 implementation with ERC5192 soulbound functionality
 * @dev Implements minimal soulbound NFTs that cannot be transferred after binding
 */
contract ERC721Soulbound is ERC721, AccessControl, ReentrancyGuard {

    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant BINDER_ROLE = keccak256("BINDER_ROLE");
    bytes32 public constant AUTHORITY_ROLE = keccak256("AUTHORITY_ROLE");

    // ERC5192 Events
    event Locked(uint256 tokenId);
    event Unlocked(uint256 tokenId);

    // Soulbound state tracking
    mapping(uint256 => bool) private _locked;
    mapping(uint256 => bool) private _soulbound; // Permanently soulbound tokens

    // Token metadata
    mapping(uint256 => string) private _tokenURIs;
    string private _baseTokenURI;

    // Supply tracking
    uint256 private _nextTokenId = 1;
    uint256 private _totalSupply;

    // Soulbound configuration
    struct SoulboundConfig {
        bool lockOnMint;            // Whether to lock tokens immediately upon minting
        bool allowUnlocking;        // Whether tokens can be unlocked by authorities
        bool permanentBinding;      // Whether some tokens are permanently bound
        uint256 lockDelay;          // Delay before auto-locking (seconds)
    }

    SoulboundConfig public soulboundConfig;

    // Time-delayed locking
    mapping(uint256 => uint256) private _lockTimestamps;

    // Events
    event TokenMinted(uint256 indexed tokenId, address indexed to, bool locked);
    event SoulboundConfigUpdated(bool lockOnMint, bool allowUnlocking, bool permanentBinding, uint256 lockDelay);
    event PermanentlyBound(uint256 indexed tokenId);
    event DelayedLockSet(uint256 indexed tokenId, uint256 lockTime);

    /**
     * @notice Initialize soulbound ERC721
     * @param name Token name
     * @param symbol Token symbol
     * @param baseURI Base URI for metadata
     * @param admin Admin address
     */
    constructor(
        string memory name,
        string memory symbol,
        string memory baseURI,
        address admin
    ) ERC721(name, symbol) {
        require(admin != address(0), "Admin cannot be zero address");

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
        _grantRole(BINDER_ROLE, admin);
        _grantRole(AUTHORITY_ROLE, admin);

        _baseTokenURI = baseURI;

        // Default configuration
        soulboundConfig = SoulboundConfig({
            lockOnMint: true,
            allowUnlocking: false,
            permanentBinding: true,
            lockDelay: 0
        });
    }

    /**
     * @notice Mint soulbound token
     * @param to Address to mint to
     * @param tokenURI Optional custom token URI
     * @param lockImmediately Whether to lock the token immediately
     */
    function mint(
        address to,
        string memory tokenURI,
        bool lockImmediately
    ) public onlyRole(MINTER_ROLE) returns (uint256) {
        require(to != address(0), "Cannot mint to zero address");

        uint256 tokenId = _nextTokenId++;
        _totalSupply++;

        _mint(to, tokenId);

        if (bytes(tokenURI).length > 0) {
            _tokenURIs[tokenId] = tokenURI;
        }

        // Handle locking based on configuration
        bool isLocked = false;
        if (lockImmediately || soulboundConfig.lockOnMint) {
            if (soulboundConfig.permanentBinding) {
                _soulbound[tokenId] = true;
                emit PermanentlyBound(tokenId);
            }
            _locked[tokenId] = true;
            isLocked = true;
            emit Locked(tokenId);
        } else if (soulboundConfig.lockDelay > 0) {
            _lockTimestamps[tokenId] = block.timestamp + soulboundConfig.lockDelay;
            emit DelayedLockSet(tokenId, _lockTimestamps[tokenId]);
        }

        emit TokenMinted(tokenId, to, isLocked);
        return tokenId;
    }

    /**
     * @notice Batch mint soulbound tokens
     * @param recipients Array of addresses to mint to
     * @param lockImmediately Whether to lock all tokens immediately
     */
    function batchMint(
        address[] calldata recipients,
        bool lockImmediately
    ) external onlyRole(MINTER_ROLE) {
        require(recipients.length > 0 && recipients.length <= 50, "Invalid batch size");

        for (uint256 i = 0; i < recipients.length; i++) {
            mint(recipients[i], "", lockImmediately);
        }
    }

    /**
     * @notice Lock a token (make it soulbound)
     * @param tokenId Token ID to lock
     * @param permanent Whether to permanently bind the token
     */
    function lock(uint256 tokenId, bool permanent) external onlyRole(BINDER_ROLE) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        require(!_locked[tokenId], "Token already locked");

        _locked[tokenId] = true;

        if (permanent) {
            _soulbound[tokenId] = true;
            emit PermanentlyBound(tokenId);
        }

        // Clear any delayed lock timestamp
        delete _lockTimestamps[tokenId];

        emit Locked(tokenId);
    }

    /**
     * @notice Unlock a token (make it transferable again)
     * @param tokenId Token ID to unlock
     */
    function unlock(uint256 tokenId) external onlyRole(AUTHORITY_ROLE) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        require(_locked[tokenId], "Token not locked");
        require(soulboundConfig.allowUnlocking, "Unlocking not allowed");
        require(!_soulbound[tokenId], "Token is permanently soulbound");

        _locked[tokenId] = false;
        emit Unlocked(tokenId);
    }

    /**
     * @notice Check if token is locked (ERC5192)
     * @param tokenId Token ID
     * @return Whether token is locked
     */
    function locked(uint256 tokenId) external view returns (bool) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");

        // Check if delayed lock has expired
        if (!_locked[tokenId] && _lockTimestamps[tokenId] > 0 && block.timestamp >= _lockTimestamps[tokenId]) {
            return true;
        }

        return _locked[tokenId];
    }

    /**
     * @notice Check if token is permanently soulbound
     * @param tokenId Token ID
     * @return Whether token is permanently bound
     */
    function isPermanentlyBound(uint256 tokenId) external view returns (bool) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return _soulbound[tokenId];
    }

    /**
     * @notice Get delayed lock timestamp for a token
     * @param tokenId Token ID
     * @return Timestamp when token will be automatically locked (0 if no delay)
     */
    function getLockTimestamp(uint256 tokenId) external view returns (uint256) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        return _lockTimestamps[tokenId];
    }

    /**
     * @notice Process delayed locks for tokens
     * @param tokenIds Array of token IDs to process
     */
    function processDelayedLocks(uint256[] calldata tokenIds) external {
        for (uint256 i = 0; i < tokenIds.length; i++) {
            uint256 tokenId = tokenIds[i];

            if (_ownerOf(tokenId) != address(0) &&
                !_locked[tokenId] &&
                _lockTimestamps[tokenId] > 0 &&
                block.timestamp >= _lockTimestamps[tokenId]) {

                _locked[tokenId] = true;

                if (soulboundConfig.permanentBinding) {
                    _soulbound[tokenId] = true;
                    emit PermanentlyBound(tokenId);
                }

                delete _lockTimestamps[tokenId];
                emit Locked(tokenId);
            }
        }
    }

    /**
     * @notice Configure soulbound parameters
     * @param lockOnMint Whether to lock tokens on mint
     * @param allowUnlocking Whether unlocking is allowed
     * @param permanentBinding Whether permanent binding is enabled
     * @param lockDelay Delay before auto-locking (seconds)
     */
    function setSoulboundConfig(
        bool lockOnMint,
        bool allowUnlocking,
        bool permanentBinding,
        uint256 lockDelay
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        soulboundConfig = SoulboundConfig({
            lockOnMint: lockOnMint,
            allowUnlocking: allowUnlocking,
            permanentBinding: permanentBinding,
            lockDelay: lockDelay
        });

        emit SoulboundConfigUpdated(lockOnMint, allowUnlocking, permanentBinding, lockDelay);
    }

    /**
     * @notice Get total supply
     * @return Total number of tokens minted
     */
    function totalSupply() public view returns (uint256) {
        return _totalSupply;
    }

    /**
     * @notice Get next token ID
     * @return Next token ID to be minted
     */
    function nextTokenId() public view returns (uint256) {
        return _nextTokenId;
    }

    /**
     * @notice Update token URI
     * @param tokenId Token ID
     * @param tokenURI New token URI
     */
    function setTokenURI(uint256 tokenId, string memory tokenURI) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        _tokenURIs[tokenId] = tokenURI;
    }

    /**
     * @notice Set base URI
     * @param baseURI New base URI
     */
    function setBaseURI(string memory baseURI) external onlyRole(DEFAULT_ADMIN_ROLE) {
        _baseTokenURI = baseURI;
    }

    // Internal functions

    function _baseURI() internal view override returns (string memory) {
        return _baseTokenURI;
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");

        string memory customURI = _tokenURIs[tokenId];
        if (bytes(customURI).length > 0) {
            return customURI;
        }

        string memory baseURI = _baseURI();
        return bytes(baseURI).length > 0 ?
            string(abi.encodePacked(baseURI, tokenId.toString())) : "";
    }

    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal override returns (address) {
        address from = _ownerOf(tokenId);

        // Prevent transfers if token is locked or delayed lock has expired
        if (from != address(0) && to != address(0)) {
            bool isCurrentlyLocked = _locked[tokenId];

            // Check if delayed lock has expired
            if (!isCurrentlyLocked && _lockTimestamps[tokenId] > 0 && block.timestamp >= _lockTimestamps[tokenId]) {
                isCurrentlyLocked = true;
                // Auto-lock the token
                _locked[tokenId] = true;
                if (soulboundConfig.permanentBinding) {
                    _soulbound[tokenId] = true;
                    emit PermanentlyBound(tokenId);
                }
                delete _lockTimestamps[tokenId];
                emit Locked(tokenId);
            }

            require(!isCurrentlyLocked, "Token is soulbound");
        }

        return super._update(to, tokenId, auth);
    }

    // Required overrides

    using Strings for uint256;

    function supportsInterface(bytes4 interfaceId) public view override(ERC721, AccessControl) returns (bool) {
        // ERC5192 interface ID
        return interfaceId == 0xb45a3c0e || super.supportsInterface(interfaceId);
    }
}