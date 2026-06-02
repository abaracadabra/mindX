// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/token/ERC1155/IERC1155.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "./UniversalDAIO.sol";

/**
 * @title VotingAssetManager
 * @notice Universal voting asset management supporting any token type as voting power
 * @dev Handles ERC20/ERC721/ERC1155/Native/Hybrid assets with delegation and time-locking
 */
contract VotingAssetManager is AccessControl, ReentrancyGuard, Pausable {

    bytes32 public constant ASSET_ADMIN_ROLE = keccak256("ASSET_ADMIN_ROLE");
    bytes32 public constant VOTING_MANAGER_ROLE = keccak256("VOTING_MANAGER_ROLE");
    bytes32 public constant DELEGATION_MANAGER_ROLE = keccak256("DELEGATION_MANAGER_ROLE");
    bytes32 public constant LOCK_MANAGER_ROLE = keccak256("LOCK_MANAGER_ROLE");

    using SafeERC20 for IERC20;

    UniversalDAIO public immutable universalDAIO;

    // Voting asset types supported by the system
    enum VotingAssetType {
        ERC20,              // Token-based voting (balance weighted)
        ERC721,             // NFT-based voting (1 vote per NFT or weighted)
        ERC1155,            // Multi-token voting (balance of specific token IDs)
        NATIVE,             // Native blockchain token (ETH, MATIC, etc.)
        HYBRID,             // Combination of multiple asset types
        REPUTATION,         // Reputation-based voting (off-chain calculated)
        STAKED,             // Staked assets with lock periods
        LIQUID_STAKING,     // Liquid staking tokens with derivative assets
        GOVERNANCE_TOKEN,   // Dedicated governance tokens
        SYNTHETIC           // Synthetic/derived voting power
    }

    // Voting formula types for power calculation
    enum VotingFormula {
        LINEAR,             // 1:1 asset to voting power
        QUADRATIC,          // Square root of asset balance
        LOGARITHMIC,        // Logarithmic scaling to reduce whale influence
        WEIGHTED,           // Custom weight multipliers
        TIME_WEIGHTED,      // Weighted by holding duration
        STAKE_WEIGHTED,     // Weighted by stake amount and duration
        REPUTATION_ADJUSTED, // Adjusted by reputation score
        CUSTOM              // Custom formula implementation
    }

    // Comprehensive voting asset configuration
    struct VotingAsset {
        address contractAddress;        // Asset contract address (0x0 for native)
        VotingAssetType assetType;      // Type of voting asset
        VotingFormula votingFormula;    // Formula for power calculation
        uint256 votingWeight;          // Base weight multiplier
        uint256 minHolding;            // Minimum holding to vote
        uint256 maxVotingPower;        // Maximum voting power per address
        uint256 lockDuration;          // Required lock duration for voting
        uint256 lockBonusMultiplier;   // Bonus multiplier for locking
        bool requiresLocking;          // Must lock assets to vote
        bool delegationAllowed;        // Delegation enabled
        bool crossChainEnabled;        // Cross-chain asset support
        bool vestingVotingEnabled;     // Vesting tokens can vote
        uint256 vestingVotingRatio;    // Ratio of vesting tokens that can vote (0-100)
        mapping(uint256 => uint256) tokenWeights; // Per-token weights for NFTs/1155
        mapping(address => uint256) userLockBonus; // Per-user lock bonuses
        mapping(address => uint256) userReputation; // Per-user reputation scores
        uint256[] supportedTokenIds;   // Supported token IDs for ERC1155
        bool active;                   // Asset is active for voting
        uint256 totalVotingPower;      // Total voting power from this asset
        uint256 registeredAt;          // Registration timestamp
        address registeredBy;          // Address that registered asset
    }

    // Voting power calculation and tracking
    struct VotingPower {
        address voter;                 // Voter address
        uint256 totalPower;           // Total voting power across all assets
        uint256 lastCalculated;       // Last calculation timestamp
        uint256 lastVoteTime;         // Last vote timestamp
        mapping(address => uint256) assetPower; // Power from each asset
        mapping(address => uint256) lockedAmount; // Locked amount per asset
        mapping(address => uint256) lockExpiry; // Lock expiry per asset
        mapping(address => address) delegatedTo; // Delegation per asset
        mapping(address => uint256) delegatedAmount; // Delegated amount per asset
        mapping(address => address[]) delegatedFrom; // Addresses delegating to this voter
        mapping(address => mapping(address => uint256)) delegationAmount; // Specific delegation amounts
        bool calculationValid;        // Whether calculation is up to date
        uint256 powerDecayRate;       // Power decay rate over time
        uint256 powerBoostEnd;        // End time of any power boosts
    }

    // Asset delegation system
    struct AssetDelegation {
        address delegator;            // Address delegating voting power
        address delegate;             // Address receiving voting power
        address assetAddress;         // Asset being delegated
        uint256 amount;               // Amount being delegated (0 = all)
        uint256 startTime;            // Delegation start time
        uint256 endTime;              // Delegation end time (0 = indefinite)
        uint256 delegatedPower;       // Calculated delegated power
        bool allowSubDelegation;      // Can delegate further
        bool revocable;               // Can be revoked early
        bool active;                  // Delegation is active
        string conditions;            // Delegation conditions/restrictions
        bytes32 delegationHash;       // Unique delegation identifier
    }

    // Asset locking for enhanced voting power
    struct AssetLock {
        address locker;               // Address that locked assets
        address assetAddress;         // Asset contract address
        uint256 amount;               // Amount locked
        uint256 lockStart;            // Lock start time
        uint256 lockDuration;         // Lock duration
        uint256 lockEnd;              // Lock end time
        uint256 bonusMultiplier;      // Bonus multiplier for this lock
        uint256 lockVotingPower;      // Voting power from lock
        bool earlyUnlockAllowed;      // Can unlock early (with penalty)
        uint256 earlyUnlockPenalty;   // Penalty for early unlock (%)
        bool autoRenewal;             // Automatically renew lock
        uint256 renewalDuration;      // Duration for auto-renewal
        LockType lockType;            // Type of lock
        bytes lockData;               // Additional lock data
    }

    // Lock types with different behaviors
    enum LockType {
        STANDARD,           // Standard lock with fixed duration
        VESTING,            // Vesting lock with gradual release
        STAKING,            // Staking lock with rewards
        GOVERNANCE,         // Governance-specific lock
        PENALTY,            // Penalty-based lock (slashing)
        EMERGENCY,          // Emergency lock (protocol security)
        CUSTOM              // Custom lock implementation
    }

    // Cross-chain asset coordination
    struct CrossChainAsset {
        uint256 homeChainId;          // Original chain of asset
        address homeAddress;          // Original contract address
        uint256[] supportedChains;    // Chains where asset is recognized
        mapping(uint256 => address) chainAddresses; // Contract addresses per chain
        mapping(uint256 => uint256) chainWeights;   // Weight per chain
        mapping(uint256 => bool) chainActive;       // Chain status
        uint256 totalCrossChainPower; // Total power across all chains
        bool bridgingEnabled;         // Asset can be bridged
        uint256 bridgingDelay;        // Delay for cross-chain voting
    }

    // Hybrid asset combination for complex voting systems
    struct HybridAssetConfig {
        address[] assetAddresses;     // Component asset addresses
        uint256[] assetWeights;       // Weight per asset in hybrid
        VotingFormula combinationFormula; // How to combine asset powers
        uint256 totalWeight;          // Total weight (should equal 100)
        uint256 minComponentHolding;  // Min holding per component
        bool requireAllComponents;    // Must hold all components
        mapping(address => bool) requiredAssets; // Required vs optional assets
        uint256 hybridVotingPower;    // Total hybrid voting power
        string hybridName;            // Name for hybrid configuration
    }

    // Storage
    mapping(uint256 => mapping(address => VotingAsset)) public votingAssets;
    mapping(uint256 => mapping(address => VotingPower)) public votingPowers;
    mapping(bytes32 => AssetDelegation) public assetDelegations;
    mapping(bytes32 => AssetLock) public assetLocks;
    mapping(uint256 => mapping(address => CrossChainAsset)) public crossChainAssets;
    mapping(uint256 => mapping(string => HybridAssetConfig)) public hybridAssets;

    // Asset registry and lookup
    mapping(uint256 => address[]) public configAssets; // Assets per configuration
    mapping(address => uint256[]) public assetConfigs; // Configurations using asset
    mapping(uint256 => uint256) public totalConfigVotingPower; // Total power per config
    mapping(address => mapping(address => uint256)) public userAssetBalance; // Cached balances

    // Delegation tracking
    mapping(address => mapping(address => bytes32[])) public userDelegations; // User's delegations per asset
    mapping(address => mapping(address => bytes32[])) public receivedDelegations; // Delegations received per asset

    // Lock tracking
    mapping(address => mapping(address => bytes32[])) public userLocks; // User's locks per asset
    mapping(address => uint256) public totalLockedAmount; // Total locked per asset

    // Global settings
    uint256 public defaultLockDuration = 30 days;
    uint256 public maxLockBonusMultiplier = 300; // 3x maximum bonus
    uint256 public powerCalculationDelay = 1 hours;
    uint256 public delegationCooldown = 1 hours;
    uint256 public crossChainVotingDelay = 6 hours;
    bool public globalAssetLock = false;

    // Statistics
    uint256 public totalAssetConfigurations;
    uint256 public totalDelegations;
    uint256 public totalLocks;
    uint256 public totalCrossChainAssets;
    mapping(VotingAssetType => uint256) public assetTypeUsage;

    // Events
    event VotingAssetRegistered(
        uint256 indexed configId,
        address indexed assetAddress,
        VotingAssetType assetType,
        uint256 votingWeight,
        address indexed registeredBy
    );

    event VotingPowerCalculated(
        uint256 indexed configId,
        address indexed voter,
        uint256 totalPower,
        uint256 calculatedAt
    );

    event AssetDelegated(
        bytes32 indexed delegationId,
        address indexed delegator,
        address indexed delegate,
        address assetAddress,
        uint256 amount,
        uint256 endTime
    );

    event AssetLocked(
        bytes32 indexed lockId,
        address indexed locker,
        address indexed assetAddress,
        uint256 amount,
        uint256 lockDuration,
        uint256 bonusMultiplier
    );

    event VotingPowerDelegated(
        uint256 indexed configId,
        address indexed delegator,
        address indexed delegate,
        uint256 delegatedPower
    );

    event CrossChainAssetRegistered(
        address indexed assetAddress,
        uint256 indexed homeChainId,
        uint256[] supportedChains
    );

    event HybridAssetCreated(
        uint256 indexed configId,
        string indexed hybridName,
        address[] assetAddresses,
        uint256[] assetWeights
    );

    event AssetPowerRecalculated(
        uint256 indexed configId,
        address indexed assetAddress,
        uint256 oldTotalPower,
        uint256 newTotalPower
    );

    modifier onlyAssetAdmin() {
        require(hasRole(ASSET_ADMIN_ROLE, msg.sender), "Not asset admin");
        _;
    }

    modifier validConfig(uint256 configId) {
        require(configId > 0, "Invalid config ID");
        _;
    }

    modifier assetExists(uint256 configId, address assetAddress) {
        require(votingAssets[configId][assetAddress].registeredAt > 0, "Asset not registered");
        _;
    }

    modifier notGloballyLocked() {
        require(!globalAssetLock, "Asset system globally locked");
        _;
    }

    constructor(address _universalDAIO) {
        require(_universalDAIO != address(0), "Invalid UniversalDAIO address");
        universalDAIO = UniversalDAIO(_universalDAIO);

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(ASSET_ADMIN_ROLE, msg.sender);
        _grantRole(VOTING_MANAGER_ROLE, msg.sender);
        _grantRole(DELEGATION_MANAGER_ROLE, msg.sender);
        _grantRole(LOCK_MANAGER_ROLE, msg.sender);
    }

    /**
     * @notice Register voting asset for configuration
     * @param configId Configuration ID
     * @param assetAddress Asset contract address (0x0 for native)
     * @param assetType Type of voting asset
     * @param votingFormula Formula for power calculation
     * @param votingWeight Base weight multiplier
     * @param minHolding Minimum holding to vote
     * @param maxVotingPower Maximum voting power per address
     * @param requiresLocking Whether locking is required
     * @param delegationAllowed Whether delegation is allowed
     */
    function registerVotingAsset(
        uint256 configId,
        address assetAddress,
        VotingAssetType assetType,
        VotingFormula votingFormula,
        uint256 votingWeight,
        uint256 minHolding,
        uint256 maxVotingPower,
        bool requiresLocking,
        bool delegationAllowed
    ) external validConfig(configId) onlyAssetAdmin notGloballyLocked {
        require(votingAssets[configId][assetAddress].registeredAt == 0, "Asset already registered");
        require(votingWeight > 0 && votingWeight <= 10000, "Invalid voting weight"); // Max 100x

        VotingAsset storage asset = votingAssets[configId][assetAddress];
        asset.contractAddress = assetAddress;
        asset.assetType = assetType;
        asset.votingFormula = votingFormula;
        asset.votingWeight = votingWeight;
        asset.minHolding = minHolding;
        asset.maxVotingPower = maxVotingPower;
        asset.requiresLocking = requiresLocking;
        asset.delegationAllowed = delegationAllowed;
        asset.lockDuration = defaultLockDuration;
        asset.lockBonusMultiplier = 100; // 1x base multiplier
        asset.active = true;
        asset.registeredAt = block.timestamp;
        asset.registeredBy = msg.sender;

        // Add to registries
        configAssets[configId].push(assetAddress);
        assetConfigs[assetAddress].push(configId);

        totalAssetConfigurations++;
        assetTypeUsage[assetType]++;

        emit VotingAssetRegistered(configId, assetAddress, assetType, votingWeight, msg.sender);
    }

    /**
     * @notice Calculate voting power for user across all assets
     * @param configId Configuration ID
     * @param voter Voter address
     * @return totalPower Total calculated voting power
     */
    function calculateVotingPower(
        uint256 configId,
        address voter
    ) external validConfig(configId) returns (uint256 totalPower) {
        require(!paused(), "Asset system paused");
        require(voter != address(0), "Invalid voter address");

        VotingPower storage power = votingPowers[configId][voter];

        // Check if recalculation needed
        if (power.calculationValid &&
            block.timestamp < power.lastCalculated + powerCalculationDelay) {
            return power.totalPower;
        }

        totalPower = 0;
        address[] memory assets = configAssets[configId];

        for (uint i = 0; i < assets.length; i++) {
            address assetAddress = assets[i];
            VotingAsset storage asset = votingAssets[configId][assetAddress];

            if (!asset.active) continue;

            uint256 assetPower = _calculateAssetVotingPower(configId, voter, assetAddress);
            power.assetPower[assetAddress] = assetPower;
            totalPower += assetPower;

            // Apply maximum voting power limit
            if (asset.maxVotingPower > 0 && assetPower > asset.maxVotingPower) {
                power.assetPower[assetAddress] = asset.maxVotingPower;
                totalPower = totalPower - assetPower + asset.maxVotingPower;
            }
        }

        // Include delegated power
        totalPower += _calculateDelegatedPower(configId, voter);

        // Apply any time-based decay or boosts
        totalPower = _applyPowerModifiers(configId, voter, totalPower);

        // Update power tracking
        power.totalPower = totalPower;
        power.lastCalculated = block.timestamp;
        power.calculationValid = true;
        power.voter = voter;

        emit VotingPowerCalculated(configId, voter, totalPower, block.timestamp);

        return totalPower;
    }

    /**
     * @notice Lock assets for enhanced voting power
     * @param configId Configuration ID
     * @param assetAddress Asset to lock
     * @param amount Amount to lock (0 for all available)
     * @param lockDuration Lock duration in seconds
     * @return lockId Lock identifier
     */
    function lockAssets(
        uint256 configId,
        address assetAddress,
        uint256 amount,
        uint256 lockDuration
    ) external validConfig(configId) assetExists(configId, assetAddress) nonReentrant returns (bytes32 lockId) {
        require(!paused(), "Asset system paused");
        require(lockDuration >= 1 days && lockDuration <= 1095 days, "Invalid lock duration"); // 1 day to 3 years

        VotingAsset storage asset = votingAssets[configId][assetAddress];
        require(asset.active, "Asset not active");

        // Get user balance
        uint256 userBalance = _getUserAssetBalance(msg.sender, assetAddress, asset.assetType);
        if (amount == 0) amount = userBalance;
        require(amount > 0 && amount <= userBalance, "Insufficient balance");

        // Generate lock ID
        lockId = keccak256(abi.encode(msg.sender, assetAddress, amount, block.timestamp));

        // Calculate bonus multiplier based on lock duration
        uint256 bonusMultiplier = _calculateLockBonus(lockDuration);

        // Create lock
        AssetLock storage lock = assetLocks[lockId];
        lock.locker = msg.sender;
        lock.assetAddress = assetAddress;
        lock.amount = amount;
        lock.lockStart = block.timestamp;
        lock.lockDuration = lockDuration;
        lock.lockEnd = block.timestamp + lockDuration;
        lock.bonusMultiplier = bonusMultiplier;
        lock.lockVotingPower = _calculateLockVotingPower(amount, bonusMultiplier, asset.votingWeight);
        lock.lockType = LockType.STANDARD;

        // Transfer assets to lock (if not native)
        if (asset.assetType != VotingAssetType.NATIVE) {
            _transferAssetsToLock(assetAddress, asset.assetType, amount);
        }

        // Update tracking
        userLocks[msg.sender][assetAddress].push(lockId);
        totalLockedAmount[assetAddress] += amount;

        VotingPower storage power = votingPowers[configId][msg.sender];
        power.lockedAmount[assetAddress] += amount;
        power.lockExpiry[assetAddress] = lock.lockEnd;
        power.calculationValid = false; // Trigger recalculation

        totalLocks++;

        emit AssetLocked(lockId, msg.sender, assetAddress, amount, lockDuration, bonusMultiplier);

        return lockId;
    }

    /**
     * @notice Delegate voting power to another address
     * @param configId Configuration ID
     * @param assetAddress Asset to delegate
     * @param delegate Address to delegate to
     * @param amount Amount to delegate (0 for all available)
     * @param endTime Delegation end time (0 for indefinite)
     * @return delegationId Delegation identifier
     */
    function delegateAsset(
        uint256 configId,
        address assetAddress,
        address delegate,
        uint256 amount,
        uint256 endTime
    ) external validConfig(configId) assetExists(configId, assetAddress) returns (bytes32 delegationId) {
        require(!paused(), "Asset system paused");
        require(delegate != address(0) && delegate != msg.sender, "Invalid delegate");
        require(endTime == 0 || endTime > block.timestamp, "Invalid end time");

        VotingAsset storage asset = votingAssets[configId][assetAddress];
        require(asset.delegationAllowed, "Delegation not allowed");
        require(asset.active, "Asset not active");

        // Check delegation cooldown
        VotingPower storage power = votingPowers[configId][msg.sender];
        require(
            block.timestamp >= power.lastVoteTime + delegationCooldown,
            "Delegation cooldown active"
        );

        // Get available balance for delegation
        uint256 availableBalance = _getAvailableDelegationBalance(configId, msg.sender, assetAddress);
        if (amount == 0) amount = availableBalance;
        require(amount > 0 && amount <= availableBalance, "Insufficient available balance");

        // Generate delegation ID
        delegationId = keccak256(abi.encode(msg.sender, delegate, assetAddress, amount, block.timestamp));

        // Create delegation
        AssetDelegation storage delegation = assetDelegations[delegationId];
        delegation.delegator = msg.sender;
        delegation.delegate = delegate;
        delegation.assetAddress = assetAddress;
        delegation.amount = amount;
        delegation.startTime = block.timestamp;
        delegation.endTime = endTime;
        delegation.delegatedPower = _calculateDelegationPower(configId, assetAddress, amount);
        delegation.revocable = true;
        delegation.active = true;
        delegation.delegationHash = delegationId;

        // Update tracking
        userDelegations[msg.sender][assetAddress].push(delegationId);
        receivedDelegations[delegate][assetAddress].push(delegationId);

        power.delegatedTo[assetAddress] = delegate;
        power.delegatedAmount[assetAddress] += amount;

        VotingPower storage delegatePower = votingPowers[configId][delegate];
        delegatePower.delegatedFrom[assetAddress].push(msg.sender);
        delegatePower.delegationAmount[assetAddress][msg.sender] = amount;
        delegatePower.calculationValid = false; // Trigger recalculation

        // Invalidate voting power calculations
        power.calculationValid = false;

        totalDelegations++;

        emit AssetDelegated(delegationId, msg.sender, delegate, assetAddress, amount, endTime);
        emit VotingPowerDelegated(configId, msg.sender, delegate, delegation.delegatedPower);

        return delegationId;
    }

    /**
     * @notice Create hybrid asset configuration
     * @param configId Configuration ID
     * @param hybridName Name for hybrid configuration
     * @param assetAddresses Component asset addresses
     * @param assetWeights Weight per asset (total must equal 100)
     * @param combinationFormula How to combine asset powers
     * @param requireAllComponents Whether all components are required
     */
    function createHybridAsset(
        uint256 configId,
        string memory hybridName,
        address[] memory assetAddresses,
        uint256[] memory assetWeights,
        VotingFormula combinationFormula,
        bool requireAllComponents
    ) external validConfig(configId) onlyAssetAdmin {
        require(bytes(hybridName).length > 0, "Hybrid name required");
        require(assetAddresses.length >= 2, "Need at least 2 assets");
        require(assetAddresses.length == assetWeights.length, "Array length mismatch");

        // Validate weights sum to 100
        uint256 totalWeight = 0;
        for (uint i = 0; i < assetWeights.length; i++) {
            totalWeight += assetWeights[i];
        }
        require(totalWeight == 100, "Weights must sum to 100");

        // Ensure all assets are registered
        for (uint i = 0; i < assetAddresses.length; i++) {
            require(votingAssets[configId][assetAddresses[i]].registeredAt > 0, "Asset not registered");
        }

        HybridAssetConfig storage hybrid = hybridAssets[configId][hybridName];
        hybrid.assetAddresses = assetAddresses;
        hybrid.assetWeights = assetWeights;
        hybrid.combinationFormula = combinationFormula;
        hybrid.totalWeight = totalWeight;
        hybrid.requireAllComponents = requireAllComponents;
        hybrid.hybridName = hybridName;

        // Set required assets mapping
        for (uint i = 0; i < assetAddresses.length; i++) {
            hybrid.requiredAssets[assetAddresses[i]] = requireAllComponents;
        }

        emit HybridAssetCreated(configId, hybridName, assetAddresses, assetWeights);
    }

    /**
     * @notice Register cross-chain asset support
     * @param assetAddress Asset address on current chain
     * @param homeChainId Original chain ID
     * @param supportedChains Supported chain IDs
     * @param chainAddresses Contract addresses per chain
     */
    function registerCrossChainAsset(
        address assetAddress,
        uint256 homeChainId,
        uint256[] memory supportedChains,
        address[] memory chainAddresses
    ) external onlyAssetAdmin {
        require(assetAddress != address(0), "Invalid asset address");
        require(supportedChains.length == chainAddresses.length, "Array length mismatch");

        CrossChainAsset storage crossChain = crossChainAssets[homeChainId][assetAddress];
        crossChain.homeChainId = homeChainId;
        crossChain.homeAddress = assetAddress;
        crossChain.supportedChains = supportedChains;
        crossChain.bridgingEnabled = true;
        crossChain.bridgingDelay = crossChainVotingDelay;

        // Set chain addresses and weights
        for (uint i = 0; i < supportedChains.length; i++) {
            uint256 chainId = supportedChains[i];
            crossChain.chainAddresses[chainId] = chainAddresses[i];
            crossChain.chainWeights[chainId] = 100; // Equal weight initially
            crossChain.chainActive[chainId] = true;
        }

        totalCrossChainAssets++;

        emit CrossChainAssetRegistered(assetAddress, homeChainId, supportedChains);
    }

    /**
     * @notice Get voting power for user and asset
     * @param configId Configuration ID
     * @param voter Voter address
     * @param assetAddress Asset address
     * @return assetPower Voting power from specific asset
     */
    function getAssetVotingPower(
        uint256 configId,
        address voter,
        address assetAddress
    ) external view validConfig(configId) returns (uint256 assetPower) {
        return votingPowers[configId][voter].assetPower[assetAddress];
    }

    /**
     * @notice Get total voting power for user
     * @param configId Configuration ID
     * @param voter Voter address
     * @return totalPower Total voting power across all assets
     */
    function getTotalVotingPower(
        uint256 configId,
        address voter
    ) external view validConfig(configId) returns (uint256 totalPower) {
        return votingPowers[configId][voter].totalPower;
    }

    /**
     * @notice Get voting assets for configuration
     * @param configId Configuration ID
     * @return assets Array of registered asset addresses
     */
    function getVotingAssets(uint256 configId) external view validConfig(configId) returns (address[] memory assets) {
        return configAssets[configId];
    }

    /**
     * @notice Get asset delegation details
     * @param delegationId Delegation ID
     * @return delegation Delegation details
     */
    function getAssetDelegation(bytes32 delegationId) external view returns (AssetDelegation memory delegation) {
        return assetDelegations[delegationId];
    }

    /**
     * @notice Get asset lock details
     * @param lockId Lock ID
     * @return lock Lock details
     */
    function getAssetLock(bytes32 lockId) external view returns (AssetLock memory lock) {
        return assetLocks[lockId];
    }

    /**
     * @notice Update global asset settings
     */
    function updateGlobalSettings(
        uint256 _defaultLockDuration,
        uint256 _maxLockBonusMultiplier,
        uint256 _powerCalculationDelay,
        uint256 _delegationCooldown,
        uint256 _crossChainVotingDelay
    ) external onlyAssetAdmin {
        defaultLockDuration = _defaultLockDuration;
        maxLockBonusMultiplier = _maxLockBonusMultiplier;
        powerCalculationDelay = _powerCalculationDelay;
        delegationCooldown = _delegationCooldown;
        crossChainVotingDelay = _crossChainVotingDelay;
    }

    /**
     * @notice Set global asset lock
     * @param locked Whether assets are globally locked
     */
    function setGlobalAssetLock(bool locked) external onlyAssetAdmin {
        globalAssetLock = locked;
    }

    /**
     * @notice Pause asset system
     */
    function pauseAssetSystem() external onlyAssetAdmin {
        _pause();
    }

    /**
     * @notice Unpause asset system
     */
    function unpauseAssetSystem() external onlyAssetAdmin {
        _unpause();
    }

    // Internal Functions

    /**
     * @notice Calculate voting power for specific asset
     */
    function _calculateAssetVotingPower(
        uint256 configId,
        address voter,
        address assetAddress
    ) internal view returns (uint256 power) {
        VotingAsset storage asset = votingAssets[configId][assetAddress];
        uint256 balance = _getUserAssetBalance(voter, assetAddress, asset.assetType);

        // Check minimum holding
        if (balance < asset.minHolding) return 0;

        // Apply voting formula
        if (asset.votingFormula == VotingFormula.LINEAR) {
            power = balance * asset.votingWeight / 100;
        } else if (asset.votingFormula == VotingFormula.QUADRATIC) {
            power = _sqrt(balance) * asset.votingWeight / 100;
        } else if (asset.votingFormula == VotingFormula.LOGARITHMIC) {
            power = _log2(balance) * asset.votingWeight / 100;
        } else if (asset.votingFormula == VotingFormula.TIME_WEIGHTED) {
            power = _calculateTimeWeightedPower(configId, voter, assetAddress, balance);
        } else if (asset.votingFormula == VotingFormula.STAKE_WEIGHTED) {
            power = _calculateStakeWeightedPower(configId, voter, assetAddress, balance);
        }

        // Apply lock bonus
        VotingPower storage userPower = votingPowers[configId][voter];
        if (userPower.lockedAmount[assetAddress] > 0) {
            uint256 lockBonus = _calculateLockPowerBonus(configId, voter, assetAddress);
            power = power * lockBonus / 100;
        }

        return power;
    }

    /**
     * @notice Calculate delegated power for user
     */
    function _calculateDelegatedPower(uint256 configId, address voter) internal view returns (uint256 delegatedPower) {
        delegatedPower = 0;
        VotingPower storage power = votingPowers[configId][voter];

        address[] memory assets = configAssets[configId];
        for (uint i = 0; i < assets.length; i++) {
            address assetAddress = assets[i];
            address[] memory delegators = power.delegatedFrom[assetAddress];

            for (uint j = 0; j < delegators.length; j++) {
                address delegator = delegators[j];
                uint256 delegationAmount = power.delegationAmount[assetAddress][delegator];

                if (delegationAmount > 0) {
                    uint256 delegationPower = _calculateDelegationPower(configId, assetAddress, delegationAmount);
                    delegatedPower += delegationPower;
                }
            }
        }

        return delegatedPower;
    }

    /**
     * @notice Apply time-based power modifiers
     */
    function _applyPowerModifiers(
        uint256 configId,
        address voter,
        uint256 basePower
    ) internal view returns (uint256 modifiedPower) {
        VotingPower storage power = votingPowers[configId][voter];

        modifiedPower = basePower;

        // Apply power decay if applicable
        if (power.powerDecayRate > 0) {
            uint256 timeDecay = (block.timestamp - power.lastCalculated) * power.powerDecayRate / 100;
            modifiedPower = modifiedPower > timeDecay ? modifiedPower - timeDecay : 0;
        }

        // Apply power boost if active
        if (power.powerBoostEnd > block.timestamp) {
            modifiedPower = modifiedPower * 110 / 100; // 10% boost
        }

        return modifiedPower;
    }

    /**
     * @notice Get user balance for asset
     */
    function _getUserAssetBalance(
        address user,
        address assetAddress,
        VotingAssetType assetType
    ) internal view returns (uint256 balance) {
        if (assetType == VotingAssetType.ERC20) {
            balance = IERC20(assetAddress).balanceOf(user);
        } else if (assetType == VotingAssetType.ERC721) {
            balance = IERC721(assetAddress).balanceOf(user);
        } else if (assetType == VotingAssetType.NATIVE) {
            balance = user.balance;
        }
        // Additional asset types would be implemented here

        return balance;
    }

    /**
     * @notice Calculate lock bonus multiplier
     */
    function _calculateLockBonus(uint256 lockDuration) internal view returns (uint256 bonusMultiplier) {
        // Base: 100% (1x multiplier)
        // +1% per day locked, max at maxLockBonusMultiplier
        uint256 bonusPerDay = 1;
        uint256 days = lockDuration / 1 days;
        uint256 bonus = days * bonusPerDay;

        bonusMultiplier = 100 + (bonus > maxLockBonusMultiplier - 100 ? maxLockBonusMultiplier - 100 : bonus);
        return bonusMultiplier;
    }

    /**
     * @notice Calculate voting power from lock
     */
    function _calculateLockVotingPower(
        uint256 amount,
        uint256 bonusMultiplier,
        uint256 assetWeight
    ) internal pure returns (uint256 lockPower) {
        return amount * bonusMultiplier * assetWeight / 10000; // Normalize
    }

    /**
     * @notice Calculate delegation power
     */
    function _calculateDelegationPower(
        uint256 configId,
        address assetAddress,
        uint256 amount
    ) internal view returns (uint256 delegationPower) {
        VotingAsset storage asset = votingAssets[configId][assetAddress];
        return amount * asset.votingWeight / 100;
    }

    /**
     * @notice Get available balance for delegation
     */
    function _getAvailableDelegationBalance(
        uint256 configId,
        address user,
        address assetAddress
    ) internal view returns (uint256 availableBalance) {
        VotingAsset storage asset = votingAssets[configId][assetAddress];
        uint256 totalBalance = _getUserAssetBalance(user, assetAddress, asset.assetType);

        VotingPower storage power = votingPowers[configId][user];
        uint256 lockedAmount = power.lockedAmount[assetAddress];
        uint256 delegatedAmount = power.delegatedAmount[assetAddress];

        availableBalance = totalBalance > (lockedAmount + delegatedAmount) ?
                          totalBalance - lockedAmount - delegatedAmount : 0;

        return availableBalance;
    }

    /**
     * @notice Transfer assets to lock contract
     */
    function _transferAssetsToLock(
        address assetAddress,
        VotingAssetType assetType,
        uint256 amount
    ) internal {
        if (assetType == VotingAssetType.ERC20) {
            IERC20(assetAddress).safeTransferFrom(msg.sender, address(this), amount);
        } else if (assetType == VotingAssetType.ERC721) {
            // Implementation would handle NFT transfers
        } else if (assetType == VotingAssetType.ERC1155) {
            // Implementation would handle ERC1155 transfers
        }
    }

    /**
     * @notice Calculate time-weighted power
     */
    function _calculateTimeWeightedPower(
        uint256 configId,
        address voter,
        address assetAddress,
        uint256 balance
    ) internal view returns (uint256 power) {
        // Implementation would calculate based on holding duration
        VotingAsset storage asset = votingAssets[configId][assetAddress];
        return balance * asset.votingWeight / 100; // Simplified
    }

    /**
     * @notice Calculate stake-weighted power
     */
    function _calculateStakeWeightedPower(
        uint256 configId,
        address voter,
        address assetAddress,
        uint256 balance
    ) internal view returns (uint256 power) {
        // Implementation would calculate based on stake amount and duration
        VotingAsset storage asset = votingAssets[configId][assetAddress];
        return balance * asset.votingWeight / 100; // Simplified
    }

    /**
     * @notice Calculate lock power bonus
     */
    function _calculateLockPowerBonus(
        uint256 configId,
        address voter,
        address assetAddress
    ) internal view returns (uint256 bonus) {
        VotingPower storage power = votingPowers[configId][voter];

        if (power.lockExpiry[assetAddress] > block.timestamp) {
            return 150; // 50% bonus for locked assets
        }

        return 100; // No bonus
    }

    // Mathematical helper functions
    function _sqrt(uint256 x) internal pure returns (uint256 y) {
        uint256 z = (x + 1) / 2;
        y = x;
        while (z < y) {
            y = z;
            z = (x / z + z) / 2;
        }
    }

    function _log2(uint256 x) internal pure returns (uint256 y) {
        assembly {
            let arg := x
            x := sub(x, 1)
            x := or(x, div(x, 0x02))
            x := or(x, div(x, 0x04))
            x := or(x, div(x, 0x10))
            x := or(x, div(x, 0x100))
            x := or(x, div(x, 0x10000))
            x := or(x, div(x, 0x100000000))
            x := or(x, div(x, 0x10000000000000000))
            x := or(x, div(x, 0x100000000000000000000000000000000))
            x := add(x, 1)
            let m := mload(0x40)
            mstore(m, 0xf8f9cbfae6cc78fbefe7cdc3a1793dfcf4f0e8bbd8cec470b6a28a7a5a3e1efd)
            mstore(add(m, 0x20), 0xf5ecf1b3e9debc68e1d9cfabc5997135bfb7a7a3938b7b606b5b4b3f2f1f0f0f)
            mstore(add(m, 0x40), 0xf6e4ed9ff2d6b458eadcdf97bd91692de2d4da8fd2d0ac50c6ae9a8272523616)
            mstore(add(m, 0x60), 0xc8c0b887b0a8a4489c948c7f847c6125746c645c544c444038302820181008ff)
            mstore(add(m, 0x80), 0xf7cae577eec2a03cf3bad76fb589591debb2dd67e0aa9834bea6925f6a4a2e0e)
            mstore(add(m, 0xa0), 0xe39ed557db96902cd38ed14fad815115c786af479b7e83247363534337271707)
            mstore(add(m, 0xc0), 0xc976c13bb96e881cb166a933a55e490d9d56952b8d4e801485467d2362422606)
            mstore(add(m, 0xe0), 0x753a6d1b65325d0c552a4d1345224105391a310b29122104190a110309020100)
            mstore(0x40, add(m, 0x100))
            let magic := 0x818283848586878889
            let shift := 0x100000000000000000000000000000001
            let a := div(mul(x, magic), shift)
            y := div(mload(add(m, sub(255, a))), shift)
            y := add(y, mul(256, gt(arg, 0x8000000000000000000000000000000000000000000000000000000000000000)))
        }
    }
}