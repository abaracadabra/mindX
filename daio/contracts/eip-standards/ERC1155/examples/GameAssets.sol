// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../ERC1155Extended.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title GameAssets
 * @notice Production example: Gaming assets collection with rarity, crafting, and upgrades
 * @dev Demonstrates real-world gaming use case with ERC1155 multi-tokens
 */
contract GameAssets is ERC1155Extended {

    // Asset rarity levels
    enum Rarity { COMMON, UNCOMMON, RARE, EPIC, LEGENDARY }

    // Asset categories
    enum AssetType { WEAPON, ARMOR, CONSUMABLE, MATERIAL, COLLECTIBLE }

    // Asset properties
    struct AssetData {
        string name;
        AssetType assetType;
        Rarity rarity;
        uint256 attack;
        uint256 defense;
        uint256 durability;
        uint256 craftingCost;
        bool craftable;
        bool upgradeable;
        uint256[] craftingMaterials;    // Token IDs for materials
        uint256[] materialAmounts;      // Amounts needed for each material
    }

    mapping(uint256 => AssetData) public assetData;

    // Crafting system
    mapping(address => mapping(uint256 => uint256)) public craftingProgress;
    mapping(uint256 => uint256) public craftingTime; // Time required to craft (seconds)

    // Player stats
    mapping(address => uint256) public playerLevel;
    mapping(address => uint256) public playerExperience;
    mapping(address => uint256) public totalAssetsOwned;

    // Game configuration
    uint256 public constant MAX_LEVEL = 100;
    uint256 public constant EXP_PER_CRAFT = 10;
    uint256 public constant EXP_PER_LEVEL = 1000;

    // Rarity multipliers for drop rates
    mapping(Rarity => uint256) public rarityMultipliers;
    mapping(Rarity => uint256) public rarityPrices;

    // Events
    event AssetCreated(
        uint256 indexed tokenId,
        string name,
        AssetType assetType,
        Rarity rarity
    );
    event CraftingStarted(address indexed player, uint256 indexed tokenId, uint256 finishTime);
    event CraftingCompleted(address indexed player, uint256 indexed tokenId, uint256 amount);
    event AssetUpgraded(uint256 indexed tokenId, address indexed player, uint256 newStats);
    event PlayerLevelUp(address indexed player, uint256 newLevel);

    /**
     * @notice Initialize GameAssets
     * @param uri Base URI for asset metadata
     * @param admin Admin address
     */
    constructor(
        string memory uri,
        address admin
    ) ERC1155Extended(uri, "Game Assets", "ASSET", admin) {
        // Initialize rarity multipliers (for drop calculations)
        rarityMultipliers[Rarity.COMMON] = 1000;      // 100%
        rarityMultipliers[Rarity.UNCOMMON] = 500;     // 50%
        rarityMultipliers[Rarity.RARE] = 200;         // 20%
        rarityMultipliers[Rarity.EPIC] = 50;          // 5%
        rarityMultipliers[Rarity.LEGENDARY] = 10;     // 1%

        // Initialize rarity prices
        rarityPrices[Rarity.COMMON] = 0.001 ether;
        rarityPrices[Rarity.UNCOMMON] = 0.005 ether;
        rarityPrices[Rarity.RARE] = 0.01 ether;
        rarityPrices[Rarity.EPIC] = 0.05 ether;
        rarityPrices[Rarity.LEGENDARY] = 0.1 ether;
    }

    /**
     * @notice Create a new game asset
     * @param name Asset name
     * @param assetType Asset category
     * @param rarity Asset rarity
     * @param attack Attack stat
     * @param defense Defense stat
     * @param durability Durability stat
     * @param maxSupply Maximum supply
     * @param craftable Whether asset can be crafted
     * @param craftingMaterials Required materials for crafting
     * @param materialAmounts Required amounts for each material
     */
    function createAsset(
        string memory name,
        AssetType assetType,
        Rarity rarity,
        uint256 attack,
        uint256 defense,
        uint256 durability,
        uint256 maxSupply,
        bool craftable,
        uint256[] memory craftingMaterials,
        uint256[] memory materialAmounts
    ) external onlyRole(MINTER_ROLE) returns (uint256) {
        require(bytes(name).length > 0, "Name cannot be empty");
        require(craftingMaterials.length == materialAmounts.length, "Arrays length mismatch");

        uint256 basePrice = rarityPrices[rarity];
        uint256 craftingCost = basePrice / 2; // Crafting costs half the market price

        uint256 tokenId = createToken(
            name,
            maxSupply,
            basePrice,
            100, // maxPerWallet
            10,  // maxPerTransaction
            true, // transferable
            msg.sender // creator
        );

        assetData[tokenId] = AssetData({
            name: name,
            assetType: assetType,
            rarity: rarity,
            attack: attack,
            defense: defense,
            durability: durability,
            craftingCost: craftingCost,
            craftable: craftable,
            upgradeable: true,
            craftingMaterials: craftingMaterials,
            materialAmounts: materialAmounts
        });

        // Set crafting time based on rarity
        uint256 baseCraftingTime = 300; // 5 minutes
        craftingTime[tokenId] = baseCraftingTime * (uint256(rarity) + 1);

        emit AssetCreated(tokenId, name, assetType, rarity);
        return tokenId;
    }

    /**
     * @notice Start crafting an asset
     * @param tokenId Asset to craft
     */
    function startCrafting(uint256 tokenId) external nonReentrant {
        require(tokenExists(tokenId), "Asset does not exist");
        require(assetData[tokenId].craftable, "Asset not craftable");
        require(craftingProgress[msg.sender][tokenId] == 0, "Already crafting this asset");

        AssetData memory asset = assetData[tokenId];

        // Check player level requirement (higher rarity = higher level)
        uint256 requiredLevel = uint256(asset.rarity) * 10 + 1;
        require(playerLevel[msg.sender] >= requiredLevel, "Insufficient player level");

        // Check and consume materials
        for (uint256 i = 0; i < asset.craftingMaterials.length; i++) {
            uint256 materialId = asset.craftingMaterials[i];
            uint256 requiredAmount = asset.materialAmounts[i];

            require(
                balanceOf(msg.sender, materialId) >= requiredAmount,
                "Insufficient materials"
            );

            _burn(msg.sender, materialId, requiredAmount);
        }

        // Set crafting finish time
        uint256 finishTime = block.timestamp + craftingTime[tokenId];
        craftingProgress[msg.sender][tokenId] = finishTime;

        emit CraftingStarted(msg.sender, tokenId, finishTime);
    }

    /**
     * @notice Complete crafting and claim asset
     * @param tokenId Asset being crafted
     */
    function completeCrafting(uint256 tokenId) external nonReentrant {
        uint256 finishTime = craftingProgress[msg.sender][tokenId];
        require(finishTime > 0, "No active crafting for this asset");
        require(block.timestamp >= finishTime, "Crafting not completed yet");

        // Clear crafting progress
        craftingProgress[msg.sender][tokenId] = 0;

        // Mint the crafted asset
        mint(msg.sender, tokenId, 1, "");

        // Award experience and check for level up
        _awardExperience(msg.sender, EXP_PER_CRAFT);

        emit CraftingCompleted(msg.sender, tokenId, 1);
    }

    /**
     * @notice Upgrade an asset (enhance stats)
     * @param tokenId Asset to upgrade
     * @param materialId Material token used for upgrade
     * @param materialAmount Amount of material to consume
     */
    function upgradeAsset(
        uint256 tokenId,
        uint256 materialId,
        uint256 materialAmount
    ) external nonReentrant {
        require(tokenExists(tokenId), "Asset does not exist");
        require(balanceOf(msg.sender, tokenId) > 0, "Don't own this asset");
        require(assetData[tokenId].upgradeable, "Asset not upgradeable");

        // Consume upgrade materials
        require(
            balanceOf(msg.sender, materialId) >= materialAmount,
            "Insufficient upgrade materials"
        );
        _burn(msg.sender, materialId, materialAmount);

        // Calculate stat improvements based on material amount and rarity
        AssetData storage asset = assetData[tokenId];
        uint256 improvement = materialAmount * (uint256(asset.rarity) + 1);

        asset.attack += improvement;
        asset.defense += improvement;
        asset.durability += improvement;

        // Award experience
        _awardExperience(msg.sender, materialAmount * 5);

        uint256 newStats = asset.attack + asset.defense + asset.durability;
        emit AssetUpgraded(tokenId, msg.sender, newStats);
    }

    /**
     * @notice Admin mint for rewards and events
     * @param to Address to mint to
     * @param tokenId Asset ID
     * @param amount Amount to mint
     */
    function adminMint(
        address to,
        uint256 tokenId,
        uint256 amount
    ) external onlyRole(MINTER_ROLE) {
        require(tokenExists(tokenId), "Asset does not exist");
        mint(to, tokenId, amount, "");

        totalAssetsOwned[to] += amount;
    }

    /**
     * @notice Batch mint multiple assets (for starter packs, etc.)
     * @param to Address to mint to
     * @param tokenIds Array of token IDs
     * @param amounts Array of amounts
     */
    function batchMintAssets(
        address to,
        uint256[] memory tokenIds,
        uint256[] memory amounts
    ) external onlyRole(MINTER_ROLE) {
        mintBatch(to, tokenIds, amounts, "");

        uint256 totalAmount = 0;
        for (uint256 i = 0; i < amounts.length; i++) {
            totalAmount += amounts[i];
        }
        totalAssetsOwned[to] += totalAmount;
    }

    /**
     * @notice Get player statistics
     * @param player Player address
     * @return level Current level
     * @return experience Current experience
     * @return expToNext Experience needed for next level
     * @return assetsOwned Total assets owned
     */
    function getPlayerStats(address player) external view returns (
        uint256 level,
        uint256 experience,
        uint256 expToNext,
        uint256 assetsOwned
    ) {
        level = playerLevel[player];
        experience = playerExperience[player];
        expToNext = (level + 1) * EXP_PER_LEVEL - experience;
        assetsOwned = totalAssetsOwned[player];

        return (level, experience, expToNext, assetsOwned);
    }

    /**
     * @notice Get asset stats
     * @param tokenId Asset ID
     * @return attack Attack stat
     * @return defense Defense stat
     * @return durability Durability stat
     * @return totalPower Total power (sum of stats)
     */
    function getAssetStats(uint256 tokenId) external view returns (
        uint256 attack,
        uint256 defense,
        uint256 durability,
        uint256 totalPower
    ) {
        require(tokenExists(tokenId), "Asset does not exist");

        AssetData memory asset = assetData[tokenId];
        attack = asset.attack;
        defense = asset.defense;
        durability = asset.durability;
        totalPower = attack + defense + durability;

        return (attack, defense, durability, totalPower);
    }

    /**
     * @notice Check crafting status
     * @param player Player address
     * @param tokenId Asset ID
     * @return isCrafting Whether actively crafting
     * @return finishTime When crafting will complete
     * @return timeRemaining Seconds remaining
     */
    function getCraftingStatus(address player, uint256 tokenId) external view returns (
        bool isCrafting,
        uint256 finishTime,
        uint256 timeRemaining
    ) {
        finishTime = craftingProgress[player][tokenId];
        isCrafting = finishTime > 0;

        if (isCrafting) {
            if (block.timestamp >= finishTime) {
                timeRemaining = 0;
            } else {
                timeRemaining = finishTime - block.timestamp;
            }
        }

        return (isCrafting, finishTime, timeRemaining);
    }

    /**
     * @notice Set rarity prices (admin only)
     * @param rarity Rarity level
     * @param price New price
     */
    function setRarityPrice(Rarity rarity, uint256 price) external onlyRole(DEFAULT_ADMIN_ROLE) {
        rarityPrices[rarity] = price;
    }

    /**
     * @notice Emergency pause crafting (admin only)
     * @param player Player address
     * @param tokenId Asset ID
     */
    function emergencyCancelCrafting(
        address player,
        uint256 tokenId
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        craftingProgress[player][tokenId] = 0;
    }

    // Internal functions

    function _awardExperience(address player, uint256 exp) internal {
        playerExperience[player] += exp;

        // Check for level up
        uint256 currentLevel = playerLevel[player];
        uint256 requiredExp = (currentLevel + 1) * EXP_PER_LEVEL;

        if (playerExperience[player] >= requiredExp && currentLevel < MAX_LEVEL) {
            playerLevel[player] = currentLevel + 1;
            emit PlayerLevelUp(player, currentLevel + 1);
        }
    }

    // Override to track asset ownership
    function _update(
        address from,
        address to,
        uint256[] memory ids,
        uint256[] memory values
    ) internal override {
        super._update(from, to, ids, values);

        // Update total assets owned tracking
        if (from != address(0) && to != address(0)) {
            for (uint256 i = 0; i < ids.length; i++) {
                if (totalAssetsOwned[from] >= values[i]) {
                    totalAssetsOwned[from] -= values[i];
                }
                totalAssetsOwned[to] += values[i];
            }
        } else if (from == address(0)) {
            // Minting
            for (uint256 i = 0; i < ids.length; i++) {
                totalAssetsOwned[to] += values[i];
            }
        } else if (to == address(0)) {
            // Burning
            for (uint256 i = 0; i < ids.length; i++) {
                if (totalAssetsOwned[from] >= values[i]) {
                    totalAssetsOwned[from] -= values[i];
                }
            }
        }
    }
}