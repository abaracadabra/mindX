// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "@openzeppelin/contracts/token/ERC1155/extensions/ERC1155Burnable.sol";
import "@openzeppelin/contracts/token/ERC1155/extensions/ERC1155Supply.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title ERC1155BurnableToken
 * @notice Enhanced ERC1155 implementation with advanced burning mechanisms
 * @dev Adds burn rewards, burn events tracking, and controlled burning functionality
 */
contract ERC1155BurnableToken is
    ERC1155,
    ERC1155Burnable,
    ERC1155Supply,
    AccessControl,
    ReentrancyGuard
{
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant BURNER_ROLE = keccak256("BURNER_ROLE");
    bytes32 public constant BURN_MANAGER_ROLE = keccak256("BURN_MANAGER_ROLE");

    // Burn rewards configuration
    struct BurnReward {
        address rewardToken;        // Address of reward token (address(0) = ETH)
        uint256 rewardAmount;       // Reward amount per burned token
        bool enabled;               // Whether burn rewards are enabled
        uint256 totalRewarded;      // Total rewards distributed
        uint256 maxRewards;         // Maximum total rewards (0 = unlimited)
    }

    mapping(uint256 => BurnReward) public burnRewards;

    // Burn tracking
    mapping(uint256 => uint256) public totalBurned;
    mapping(uint256 => mapping(address => uint256)) public userBurned;
    mapping(address => uint256) public totalUserBurns;

    // Token configuration
    mapping(uint256 => bool) private _tokenExists;
    mapping(uint256 => string) private _tokenNames;
    mapping(uint256 => bool) private _burnableTokens;
    mapping(uint256 => uint256) private _burnCooldowns;
    mapping(uint256 => mapping(address => uint256)) private _lastBurnTime;

    // Collection information
    string private _name;
    string private _symbol;
    uint256 private _nextTokenId = 1;

    // Events
    event TokenCreated(uint256 indexed tokenId, string name, bool burnable);
    event BurnRewardSet(uint256 indexed tokenId, address rewardToken, uint256 rewardAmount);
    event BurnRewardClaimed(
        uint256 indexed tokenId,
        address indexed user,
        uint256 burnedAmount,
        uint256 rewardAmount
    );
    event TokensBurned(
        address indexed account,
        uint256 indexed tokenId,
        uint256 amount,
        address indexed burner
    );
    event BatchTokensBurned(
        address indexed account,
        uint256[] tokenIds,
        uint256[] amounts,
        address indexed burner
    );

    /**
     * @notice Initialize ERC1155Burnable
     * @param uri Base URI for tokens
     * @param name_ Collection name
     * @param symbol_ Collection symbol
     * @param admin Admin address
     */
    constructor(
        string memory uri,
        string memory name_,
        string memory symbol_,
        address admin
    ) ERC1155(uri) {
        require(admin != address(0), "Admin cannot be zero address");

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
        _grantRole(BURNER_ROLE, admin);
        _grantRole(BURN_MANAGER_ROLE, admin);

        _name = name_;
        _symbol = symbol_;
    }

    /**
     * @notice Create a new burnable token
     * @param name Token name
     * @param burnable Whether token can be burned by holders
     * @param burnCooldown Cooldown period between burns (seconds)
     */
    function createToken(
        string memory name,
        bool burnable,
        uint256 burnCooldown
    ) public onlyRole(MINTER_ROLE) returns (uint256) {
        require(bytes(name).length > 0, "Name cannot be empty");

        uint256 tokenId = _nextTokenId++;
        _tokenExists[tokenId] = true;
        _tokenNames[tokenId] = name;
        _burnableTokens[tokenId] = burnable;
        _burnCooldowns[tokenId] = burnCooldown;

        emit TokenCreated(tokenId, name, burnable);
        return tokenId;
    }

    /**
     * @notice Mint tokens
     * @param to Address to mint to
     * @param tokenId Token ID
     * @param amount Amount to mint
     * @param data Additional data
     */
    function mint(
        address to,
        uint256 tokenId,
        uint256 amount,
        bytes memory data
    ) public onlyRole(MINTER_ROLE) {
        require(to != address(0), "Cannot mint to zero address");
        require(_tokenExists[tokenId], "Token does not exist");
        require(amount > 0, "Amount must be greater than 0");

        _mint(to, tokenId, amount, data);
    }

    /**
     * @notice Batch mint tokens
     * @param to Address to mint to
     * @param tokenIds Array of token IDs
     * @param amounts Array of amounts
     * @param data Additional data
     */
    function mintBatch(
        address to,
        uint256[] memory tokenIds,
        uint256[] memory amounts,
        bytes memory data
    ) public onlyRole(MINTER_ROLE) {
        require(to != address(0), "Cannot mint to zero address");
        require(tokenIds.length == amounts.length, "Arrays length mismatch");

        for (uint256 i = 0; i < tokenIds.length; i++) {
            require(_tokenExists[tokenIds[i]], "Token does not exist");
            require(amounts[i] > 0, "Amount must be greater than 0");
        }

        _mintBatch(to, tokenIds, amounts, data);
    }

    /**
     * @notice Burn tokens with rewards
     * @param account Account to burn from
     * @param tokenId Token ID
     * @param amount Amount to burn
     */
    function burn(
        address account,
        uint256 tokenId,
        uint256 amount
    ) public override nonReentrant {
        require(_tokenExists[tokenId], "Token does not exist");
        require(_burnableTokens[tokenId], "Token not burnable");
        require(amount > 0, "Amount must be greater than 0");

        // Check permissions
        require(
            hasRole(BURNER_ROLE, msg.sender) ||
            account == msg.sender ||
            isApprovedForAll(account, msg.sender),
            "Not authorized to burn"
        );

        // Check cooldown
        uint256 cooldown = _burnCooldowns[tokenId];
        if (cooldown > 0 && account == msg.sender) {
            require(
                block.timestamp >= _lastBurnTime[tokenId][account] + cooldown,
                "Burn cooldown not expired"
            );
            _lastBurnTime[tokenId][account] = block.timestamp;
        }

        // Update burn tracking
        totalBurned[tokenId] += amount;
        userBurned[tokenId][account] += amount;
        totalUserBurns[account] += amount;

        // Process burn rewards
        _processBurnReward(account, tokenId, amount);

        // Burn the tokens
        super.burn(account, tokenId, amount);

        emit TokensBurned(account, tokenId, amount, msg.sender);
    }

    /**
     * @notice Batch burn tokens with rewards
     * @param account Account to burn from
     * @param tokenIds Array of token IDs
     * @param amounts Array of amounts
     */
    function burnBatch(
        address account,
        uint256[] memory tokenIds,
        uint256[] memory amounts
    ) public override nonReentrant {
        require(tokenIds.length == amounts.length, "Arrays length mismatch");

        // Check permissions
        require(
            hasRole(BURNER_ROLE, msg.sender) ||
            account == msg.sender ||
            isApprovedForAll(account, msg.sender),
            "Not authorized to burn"
        );

        for (uint256 i = 0; i < tokenIds.length; i++) {
            require(_tokenExists[tokenIds[i]], "Token does not exist");
            require(_burnableTokens[tokenIds[i]], "Token not burnable");
            require(amounts[i] > 0, "Amount must be greater than 0");

            uint256 tokenId = tokenIds[i];
            uint256 amount = amounts[i];

            // Check cooldown
            uint256 cooldown = _burnCooldowns[tokenId];
            if (cooldown > 0 && account == msg.sender) {
                require(
                    block.timestamp >= _lastBurnTime[tokenId][account] + cooldown,
                    "Burn cooldown not expired"
                );
                _lastBurnTime[tokenId][account] = block.timestamp;
            }

            // Update burn tracking
            totalBurned[tokenId] += amount;
            userBurned[tokenId][account] += amount;
            totalUserBurns[account] += amount;

            // Process burn rewards
            _processBurnReward(account, tokenId, amount);
        }

        // Burn the tokens
        super.burnBatch(account, tokenIds, amounts);

        emit BatchTokensBurned(account, tokenIds, amounts, msg.sender);
    }

    /**
     * @notice Set burn reward for a token
     * @param tokenId Token ID
     * @param rewardToken Reward token address (address(0) for ETH)
     * @param rewardAmount Reward amount per burned token
     * @param maxRewards Maximum total rewards (0 = unlimited)
     */
    function setBurnReward(
        uint256 tokenId,
        address rewardToken,
        uint256 rewardAmount,
        uint256 maxRewards
    ) external onlyRole(BURN_MANAGER_ROLE) {
        require(_tokenExists[tokenId], "Token does not exist");

        burnRewards[tokenId] = BurnReward({
            rewardToken: rewardToken,
            rewardAmount: rewardAmount,
            enabled: rewardAmount > 0,
            totalRewarded: burnRewards[tokenId].totalRewarded, // Preserve existing total
            maxRewards: maxRewards
        });

        emit BurnRewardSet(tokenId, rewardToken, rewardAmount);
    }

    /**
     * @notice Toggle burn rewards for a token
     * @param tokenId Token ID
     * @param enabled Whether burn rewards are enabled
     */
    function setBurnRewardEnabled(
        uint256 tokenId,
        bool enabled
    ) external onlyRole(BURN_MANAGER_ROLE) {
        require(_tokenExists[tokenId], "Token does not exist");
        burnRewards[tokenId].enabled = enabled;
    }

    /**
     * @notice Set token burnability
     * @param tokenId Token ID
     * @param burnable Whether token can be burned
     */
    function setBurnable(uint256 tokenId, bool burnable) external onlyRole(BURN_MANAGER_ROLE) {
        require(_tokenExists[tokenId], "Token does not exist");
        _burnableTokens[tokenId] = burnable;
    }

    /**
     * @notice Set burn cooldown for a token
     * @param tokenId Token ID
     * @param cooldown Cooldown period in seconds
     */
    function setBurnCooldown(uint256 tokenId, uint256 cooldown) external onlyRole(BURN_MANAGER_ROLE) {
        require(_tokenExists[tokenId], "Token does not exist");
        _burnCooldowns[tokenId] = cooldown;
    }

    /**
     * @notice Emergency withdraw of reward tokens
     * @param token Token address (address(0) for ETH)
     * @param amount Amount to withdraw
     */
    function emergencyWithdraw(address token, uint256 amount) external onlyRole(DEFAULT_ADMIN_ROLE) {
        if (token == address(0)) {
            require(address(this).balance >= amount, "Insufficient ETH balance");
            payable(msg.sender).transfer(amount);
        } else {
            IERC20(token).transfer(msg.sender, amount);
        }
    }

    /**
     * @notice Get token information
     * @param tokenId Token ID
     * @return name Token name
     * @return burnable Whether token is burnable
     * @return burnCooldown Burn cooldown period
     */
    function getTokenInfo(uint256 tokenId) external view returns (
        string memory name,
        bool burnable,
        uint256 burnCooldown
    ) {
        require(_tokenExists[tokenId], "Token does not exist");
        return (_tokenNames[tokenId], _burnableTokens[tokenId], _burnCooldowns[tokenId]);
    }

    /**
     * @notice Get burn statistics for a user and token
     * @param user User address
     * @param tokenId Token ID
     * @return burned Amount burned by user
     * @return lastBurn Last burn timestamp
     * @return canBurn Whether user can burn now (cooldown expired)
     */
    function getBurnStats(address user, uint256 tokenId) external view returns (
        uint256 burned,
        uint256 lastBurn,
        bool canBurn
    ) {
        burned = userBurned[tokenId][user];
        lastBurn = _lastBurnTime[tokenId][user];
        canBurn = block.timestamp >= lastBurn + _burnCooldowns[tokenId];

        return (burned, lastBurn, canBurn);
    }

    /**
     * @notice Get collection name
     * @return Collection name
     */
    function name() public view returns (string memory) {
        return _name;
    }

    /**
     * @notice Get collection symbol
     * @return Collection symbol
     */
    function symbol() public view returns (string memory) {
        return _symbol;
    }

    /**
     * @notice Check if token exists
     * @param tokenId Token ID
     * @return Whether token exists
     */
    function tokenExists(uint256 tokenId) public view returns (bool) {
        return _tokenExists[tokenId];
    }

    // Internal functions

    function _processBurnReward(address account, uint256 tokenId, uint256 amount) internal {
        BurnReward storage reward = burnRewards[tokenId];

        if (!reward.enabled || reward.rewardAmount == 0) {
            return;
        }

        uint256 rewardAmount = amount * reward.rewardAmount;

        // Check if max rewards would be exceeded
        if (reward.maxRewards > 0 && reward.totalRewarded + rewardAmount > reward.maxRewards) {
            rewardAmount = reward.maxRewards - reward.totalRewarded;
        }

        if (rewardAmount == 0) {
            return;
        }

        reward.totalRewarded += rewardAmount;

        // Distribute reward
        if (reward.rewardToken == address(0)) {
            // ETH reward
            require(address(this).balance >= rewardAmount, "Insufficient ETH for reward");
            payable(account).transfer(rewardAmount);
        } else {
            // Token reward
            IERC20(reward.rewardToken).transfer(account, rewardAmount);
        }

        emit BurnRewardClaimed(tokenId, account, amount, rewardAmount);
    }

    // Required overrides

    function _update(
        address from,
        address to,
        uint256[] memory ids,
        uint256[] memory values
    ) internal override(ERC1155, ERC1155Supply) {
        super._update(from, to, ids, values);
    }

    function supportsInterface(
        bytes4 interfaceId
    ) public view override(ERC1155, AccessControl) returns (bool) {
        return super.supportsInterface(interfaceId);
    }

    // Allow contract to receive ETH for rewards
    receive() external payable {}
}

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
}