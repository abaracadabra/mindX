// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../ERC721Extended.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title UtilityNFT
 * @notice Production example: Access control NFT for services and utilities
 * @dev Demonstrates utility-focused NFTs for gating access to services, features, or content
 */
contract UtilityNFT is ERC721Extended {

    // Access level definitions
    enum AccessLevel { NONE, BASIC, PREMIUM, VIP, LIFETIME }

    // Service configuration
    struct ServiceConfig {
        string serviceName;
        string description;
        AccessLevel requiredLevel;
        uint256 usageLimit;         // Uses per period (0 = unlimited)
        uint256 periodDuration;     // Period in seconds
        bool active;
    }

    // Token access information
    struct TokenAccess {
        AccessLevel level;
        uint256 expirationTime;     // 0 = never expires
        bool transferable;
        mapping(bytes32 => uint256) serviceUsage;      // serviceId => usage count
        mapping(bytes32 => uint256) lastUsageReset;    // serviceId => last reset time
    }

    mapping(uint256 => TokenAccess) private _tokenAccess;
    mapping(bytes32 => ServiceConfig) public services;
    mapping(AccessLevel => uint256) public accessPrices;
    mapping(AccessLevel => string) public accessLevelNames;

    bytes32[] public serviceIds;

    // Events
    event ServiceAdded(bytes32 indexed serviceId, string serviceName, AccessLevel requiredLevel);
    event ServiceUsed(uint256 indexed tokenId, bytes32 indexed serviceId, address indexed user);
    event AccessLevelUpgraded(uint256 indexed tokenId, AccessLevel oldLevel, AccessLevel newLevel);
    event AccessExpired(uint256 indexed tokenId);

    /**
     * @notice Initialize Utility NFT
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
    ) ERC721Extended(name, symbol, baseURI, 0, admin) {
        // Initialize access level names
        accessLevelNames[AccessLevel.NONE] = "None";
        accessLevelNames[AccessLevel.BASIC] = "Basic";
        accessLevelNames[AccessLevel.PREMIUM] = "Premium";
        accessLevelNames[AccessLevel.VIP] = "VIP";
        accessLevelNames[AccessLevel.LIFETIME] = "Lifetime";

        // Initialize access prices
        accessPrices[AccessLevel.BASIC] = 0.01 ether;
        accessPrices[AccessLevel.PREMIUM] = 0.05 ether;
        accessPrices[AccessLevel.VIP] = 0.1 ether;
        accessPrices[AccessLevel.LIFETIME] = 0.5 ether;
    }

    /**
     * @notice Mint access token with specified level
     * @param to Address to mint to
     * @param level Access level
     * @param duration Access duration in seconds (0 = lifetime)
     * @param transferable Whether token can be transferred
     */
    function mintAccess(
        address to,
        AccessLevel level,
        uint256 duration,
        bool transferable
    ) public onlyRole(MINTER_ROLE) returns (uint256) {
        require(to != address(0), "Cannot mint to zero address");
        require(level != AccessLevel.NONE, "Cannot mint NONE level");

        uint256 tokenId = nextTokenId();
        mint(to, "");

        uint256 expirationTime = 0;
        if (duration > 0) {
            expirationTime = block.timestamp + duration;
        }

        TokenAccess storage access = _tokenAccess[tokenId];
        access.level = level;
        access.expirationTime = expirationTime;
        access.transferable = transferable;

        return tokenId;
    }

    /**
     * @notice Public mint access token
     * @param level Access level to purchase
     * @param duration Access duration in seconds (0 = lifetime)
     */
    function purchaseAccess(
        AccessLevel level,
        uint256 duration
    ) external payable nonReentrant returns (uint256) {
        require(mintConfig.publicSaleActive, "Public sale not active");
        require(level != AccessLevel.NONE, "Cannot purchase NONE level");

        uint256 price = _calculatePrice(level, duration);
        require(msg.value >= price, "Insufficient payment");

        uint256 tokenId = mintAccess(msg.sender, level, duration, true);

        // Refund excess payment
        if (msg.value > price) {
            payable(msg.sender).transfer(msg.value - price);
        }

        return tokenId;
    }

    /**
     * @notice Add a new service
     * @param serviceId Unique service identifier
     * @param serviceName Human-readable service name
     * @param description Service description
     * @param requiredLevel Minimum access level required
     * @param usageLimit Uses per period (0 = unlimited)
     * @param periodDuration Period duration in seconds
     */
    function addService(
        bytes32 serviceId,
        string memory serviceName,
        string memory description,
        AccessLevel requiredLevel,
        uint256 usageLimit,
        uint256 periodDuration
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(serviceId != bytes32(0), "Invalid service ID");
        require(bytes(serviceName).length > 0, "Service name cannot be empty");
        require(!services[serviceId].active, "Service already exists");

        services[serviceId] = ServiceConfig({
            serviceName: serviceName,
            description: description,
            requiredLevel: requiredLevel,
            usageLimit: usageLimit,
            periodDuration: periodDuration,
            active: true
        });

        serviceIds.push(serviceId);
        emit ServiceAdded(serviceId, serviceName, requiredLevel);
    }

    /**
     * @notice Use a service (called by service provider)
     * @param tokenId Token ID
     * @param serviceId Service to use
     */
    function useService(uint256 tokenId, bytes32 serviceId) external returns (bool) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");
        require(services[serviceId].active, "Service not active");

        address tokenOwner = ownerOf(tokenId);
        TokenAccess storage access = _tokenAccess[tokenId];
        ServiceConfig memory service = services[serviceId];

        // Check access level
        require(access.level >= service.requiredLevel, "Insufficient access level");

        // Check expiration
        if (access.expirationTime > 0) {
            require(block.timestamp <= access.expirationTime, "Access expired");
        }

        // Check usage limits
        if (service.usageLimit > 0) {
            uint256 currentPeriodStart = (block.timestamp / service.periodDuration) * service.periodDuration;

            if (access.lastUsageReset[serviceId] < currentPeriodStart) {
                access.serviceUsage[serviceId] = 0;
                access.lastUsageReset[serviceId] = currentPeriodStart;
            }

            require(access.serviceUsage[serviceId] < service.usageLimit, "Usage limit exceeded");
            access.serviceUsage[serviceId]++;
        }

        emit ServiceUsed(tokenId, serviceId, tokenOwner);
        return true;
    }

    /**
     * @notice Check if token has access to service
     * @param tokenId Token ID
     * @param serviceId Service ID
     * @return hasAccess Whether token has access
     * @return usageRemaining Remaining uses in current period
     */
    function checkAccess(uint256 tokenId, bytes32 serviceId) external view returns (
        bool hasAccess,
        uint256 usageRemaining
    ) {
        if (_ownerOf(tokenId) == address(0)) {
            return (false, 0);
        }

        TokenAccess storage access = _tokenAccess[tokenId];
        ServiceConfig memory service = services[serviceId];

        if (!service.active) {
            return (false, 0);
        }

        // Check access level
        if (access.level < service.requiredLevel) {
            return (false, 0);
        }

        // Check expiration
        if (access.expirationTime > 0 && block.timestamp > access.expirationTime) {
            return (false, 0);
        }

        // Calculate remaining usage
        uint256 remaining = type(uint256).max;
        if (service.usageLimit > 0) {
            uint256 currentPeriodStart = (block.timestamp / service.periodDuration) * service.periodDuration;
            uint256 currentUsage = access.serviceUsage[serviceId];

            if (access.lastUsageReset[serviceId] < currentPeriodStart) {
                currentUsage = 0;
            }

            remaining = service.usageLimit > currentUsage ? service.usageLimit - currentUsage : 0;
        }

        return (true, remaining);
    }

    /**
     * @notice Upgrade access level for existing token
     * @param tokenId Token ID
     * @param newLevel New access level
     * @param additionalDuration Additional duration in seconds
     */
    function upgradeAccess(
        uint256 tokenId,
        AccessLevel newLevel,
        uint256 additionalDuration
    ) external payable nonReentrant {
        require(ownerOf(tokenId) == msg.sender, "Not token owner");

        TokenAccess storage access = _tokenAccess[tokenId];
        require(newLevel > access.level, "Cannot downgrade access level");

        uint256 upgradeCost = _calculateUpgradePrice(access.level, newLevel, additionalDuration);
        require(msg.value >= upgradeCost, "Insufficient payment");

        AccessLevel oldLevel = access.level;
        access.level = newLevel;

        // Extend expiration time
        if (additionalDuration > 0) {
            if (access.expirationTime == 0) {
                access.expirationTime = block.timestamp + additionalDuration;
            } else {
                access.expirationTime += additionalDuration;
            }
        }

        emit AccessLevelUpgraded(tokenId, oldLevel, newLevel);

        // Refund excess payment
        if (msg.value > upgradeCost) {
            payable(msg.sender).transfer(msg.value - upgradeCost);
        }
    }

    /**
     * @notice Get token access information
     * @param tokenId Token ID
     * @return level Access level
     * @return expirationTime Expiration timestamp (0 = never expires)
     * @return transferable Whether token is transferable
     */
    function getTokenAccess(uint256 tokenId) external view returns (
        AccessLevel level,
        uint256 expirationTime,
        bool transferable
    ) {
        require(_ownerOf(tokenId) != address(0), "Token does not exist");

        TokenAccess storage access = _tokenAccess[tokenId];
        return (access.level, access.expirationTime, access.transferable);
    }

    /**
     * @notice Get all service IDs
     * @return Array of service IDs
     */
    function getAllServices() external view returns (bytes32[] memory) {
        return serviceIds;
    }

    /**
     * @notice Set access price for a level
     * @param level Access level
     * @param price Price in wei
     */
    function setAccessPrice(AccessLevel level, uint256 price) external onlyRole(DEFAULT_ADMIN_ROLE) {
        accessPrices[level] = price;
    }

    // Internal functions

    function _calculatePrice(AccessLevel level, uint256 duration) internal view returns (uint256) {
        uint256 basePrice = accessPrices[level];

        if (duration == 0) {
            // Lifetime access costs 3x the base price
            return basePrice * 3;
        }

        // Price scales with duration (minimum 1 day)
        uint256 days = duration / 86400;
        if (days == 0) days = 1;

        return basePrice * days / 30; // Price per 30-day period
    }

    function _calculateUpgradePrice(
        AccessLevel fromLevel,
        AccessLevel toLevel,
        uint256 duration
    ) internal view returns (uint256) {
        uint256 fromPrice = accessPrices[fromLevel];
        uint256 toPrice = accessPrices[toLevel];

        uint256 baseUpgradeCost = toPrice > fromPrice ? toPrice - fromPrice : 0;

        if (duration == 0) {
            return baseUpgradeCost;
        }

        uint256 days = duration / 86400;
        if (days == 0) days = 1;

        return baseUpgradeCost + (toPrice * days / 30);
    }

    // Override transfer to check transferability
    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal override returns (address) {
        address from = _ownerOf(tokenId);

        // Check transferability for existing tokens
        if (from != address(0) && to != address(0)) {
            TokenAccess storage access = _tokenAccess[tokenId];
            require(access.transferable, "Token not transferable");
        }

        return super._update(to, tokenId, auth);
    }
}