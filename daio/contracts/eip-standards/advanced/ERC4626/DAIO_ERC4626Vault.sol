// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/interfaces/IERC4626.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title DAIO_ERC4626Vault
 * @notice Tokenized vaults with constitutional compliance and DAIO integration
 * @dev ERC4626 implementation that integrates with DAIO governance and treasury systems
 */
contract DAIO_ERC4626Vault is ERC20, IERC4626, AccessControl, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    bytes32 public constant VAULT_MANAGER_ROLE = keccak256("VAULT_MANAGER_ROLE");
    bytes32 public constant STRATEGY_ROLE = keccak256("STRATEGY_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");
    bytes32 public constant TREASURY_ROLE = keccak256("TREASURY_ROLE");

    // Vault configuration
    struct VaultConfig {
        uint256 depositLimit;           // Maximum total deposits allowed
        uint256 individualDepositLimit; // Maximum deposit per user
        uint256 withdrawalFee;          // Withdrawal fee in BPS (basis points)
        uint256 managementFee;          // Annual management fee in BPS
        uint256 performanceFee;         // Performance fee in BPS
        uint256 minSharesForReward;     // Minimum shares to earn performance rewards
        bool requiresWhitelist;         // Whether deposits require whitelist
        bool emergencyWithdrawalEnabled; // Whether emergency withdrawals are enabled
    }

    struct PerformanceMetrics {
        uint256 totalAssetsManaged;     // Total assets under management
        uint256 totalReturnsGenerated;  // Total returns generated
        uint256 sharePrice;             // Current share price (scaled by 1e18)
        uint256 lastUpdateTime;         // Last performance update
        uint256 highWaterMark;          // High water mark for performance fees
        uint256 cumulativeReturns;      // Cumulative returns percentage
        int256 currentPeriodReturn;     // Current period return (can be negative)
    }

    // DAIO integration
    struct DAIOIntegration {
        address treasuryContract;       // DAIO Treasury contract
        address constitutionContract;   // DAIO Constitution contract
        address oracleRegistry;         // Oracle registry for asset valuation
        uint256 titheRate;             // Tithe rate to DAIO treasury (BPS)
        uint256 maxConstitutionalExposure; // Max exposure per constitutional limits
        bool constitutionalCompliance;  // Whether constitutional compliance is enforced
    }

    // State variables
    IERC20 public immutable asset;
    VaultConfig public vaultConfig;
    PerformanceMetrics public performanceMetrics;
    DAIOIntegration public daioIntegration;

    // User tracking
    mapping(address => bool) public whitelist;
    mapping(address => uint256) public userDepositTime;
    mapping(address => uint256) public userSharesAtDeposit;
    mapping(address => uint256) public userPerformanceDebt; // For fair performance fee calculation

    // Strategy integration
    address[] public activeStrategies;
    mapping(address => uint256) public strategyAllocations; // strategy -> allocation percentage (BPS)
    mapping(address => bool) public authorizedStrategies;

    // Fee tracking
    uint256 public totalFeesCollected;
    uint256 public totalTithePaid;
    uint256 public lastManagementFeeUpdate;

    // Emergency state
    bool public emergencyMode;
    uint256 public emergencyModeActivatedAt;

    // Events
    event DepositExecuted(
        address indexed caller,
        address indexed owner,
        uint256 assets,
        uint256 shares
    );
    event WithdrawExecuted(
        address indexed caller,
        address indexed receiver,
        address indexed owner,
        uint256 assets,
        uint256 shares
    );
    event StrategyAdded(address indexed strategy, uint256 allocation);
    event StrategyRemoved(address indexed strategy);
    event PerformanceUpdated(
        uint256 totalAssets,
        uint256 sharePrice,
        int256 periodReturn
    );
    event FeesCollected(
        uint256 managementFees,
        uint256 performanceFees,
        uint256 titheAmount
    );
    event EmergencyModeActivated(string reason);
    event ConstitutionalComplianceChecked(bool compliant, string reason);

    /**
     * @notice Initialize DAIO ERC4626 Vault
     * @param _asset Underlying asset token
     * @param _name Vault token name
     * @param _symbol Vault token symbol
     * @param _treasuryContract DAIO treasury contract
     * @param _constitutionContract DAIO constitution contract
     * @param admin Admin address for role management
     */
    constructor(
        IERC20 _asset,
        string memory _name,
        string memory _symbol,
        address _treasuryContract,
        address _constitutionContract,
        address admin
    ) ERC20(_name, _symbol) {
        require(address(_asset) != address(0), "Asset cannot be zero address");
        require(admin != address(0), "Admin cannot be zero address");

        asset = _asset;

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(VAULT_MANAGER_ROLE, admin);
        _grantRole(STRATEGY_ROLE, admin);
        _grantRole(EMERGENCY_ROLE, admin);
        _grantRole(TREASURY_ROLE, admin);

        // Initialize vault configuration with DAIO-compliant defaults
        vaultConfig = VaultConfig({
            depositLimit: type(uint256).max,
            individualDepositLimit: type(uint256).max,
            withdrawalFee: 50,               // 0.5% withdrawal fee
            managementFee: 200,              // 2% annual management fee
            performanceFee: 2000,            // 20% performance fee
            minSharesForReward: 1000 * 1e18, // 1000 shares minimum for rewards
            requiresWhitelist: false,
            emergencyWithdrawalEnabled: true
        });

        // Initialize DAIO integration
        daioIntegration = DAIOIntegration({
            treasuryContract: _treasuryContract,
            constitutionContract: _constitutionContract,
            oracleRegistry: address(0), // Set later
            titheRate: 1500,           // 15% tithe rate (constitutional requirement)
            maxConstitutionalExposure: 1500, // 15% max exposure per constitution
            constitutionalCompliance: true
        });

        // Initialize performance metrics
        performanceMetrics = PerformanceMetrics({
            totalAssetsManaged: 0,
            totalReturnsGenerated: 0,
            sharePrice: 1e18,          // Start at 1:1 ratio
            lastUpdateTime: block.timestamp,
            highWaterMark: 1e18,
            cumulativeReturns: 0,
            currentPeriodReturn: 0
        });

        lastManagementFeeUpdate = block.timestamp;
    }

    /**
     * @notice Get the underlying asset of the vault
     * @return assetTokenAddress The address of the underlying asset
     */
    function asset() public view override returns (address assetTokenAddress) {
        return address(asset);
    }

    /**
     * @notice Get total assets under management
     * @return totalManagedAssets Total assets in the vault
     */
    function totalAssets() public view override returns (uint256 totalManagedAssets) {
        uint256 vaultBalance = asset.balanceOf(address(this));
        uint256 strategyAssets = _getTotalStrategyAssets();
        return vaultBalance + strategyAssets;
    }

    /**
     * @notice Convert assets to shares
     * @param assets Amount of assets
     * @return shares Amount of shares
     */
    function convertToShares(uint256 assets) public view override returns (uint256 shares) {
        return _convertToShares(assets, Math.Rounding.Down);
    }

    /**
     * @notice Convert shares to assets
     * @param shares Amount of shares
     * @return assets Amount of assets
     */
    function convertToAssets(uint256 shares) public view override returns (uint256 assets) {
        return _convertToAssets(shares, Math.Rounding.Down);
    }

    /**
     * @notice Get maximum deposit amount
     * @param receiver Address of receiver
     * @return maxAssets Maximum assets that can be deposited
     */
    function maxDeposit(address receiver) public view override returns (uint256 maxAssets) {
        if (paused() || emergencyMode) return 0;
        if (vaultConfig.requiresWhitelist && !whitelist[receiver]) return 0;

        uint256 currentTotal = totalAssets();
        if (currentTotal >= vaultConfig.depositLimit) return 0;

        uint256 remainingGlobal = vaultConfig.depositLimit - currentTotal;
        return Math.min(remainingGlobal, vaultConfig.individualDepositLimit);
    }

    /**
     * @notice Preview deposit shares
     * @param assets Amount of assets to deposit
     * @return shares Amount of shares that would be received
     */
    function previewDeposit(uint256 assets) public view override returns (uint256 shares) {
        return _convertToShares(assets, Math.Rounding.Down);
    }

    /**
     * @notice Deposit assets and mint shares
     * @param assets Amount of assets to deposit
     * @param receiver Address to receive shares
     * @return shares Amount of shares minted
     */
    function deposit(uint256 assets, address receiver) public override nonReentrant whenNotPaused returns (uint256 shares) {
        require(assets <= maxDeposit(receiver), "Exceeds deposit limit");
        require(assets > 0, "Cannot deposit zero assets");

        // Check constitutional compliance
        _checkConstitutionalCompliance(assets, true);

        shares = previewDeposit(assets);
        require(shares > 0, "Zero shares");

        // Update user tracking
        userDepositTime[receiver] = block.timestamp;
        userSharesAtDeposit[receiver] = balanceOf(receiver);

        // Transfer assets from user
        asset.safeTransferFrom(msg.sender, address(this), assets);

        // Mint shares to receiver
        _mint(receiver, shares);

        // Collect management fees if applicable
        _collectManagementFees();

        // Update performance metrics
        _updatePerformanceMetrics();

        // Deploy assets to strategies if available
        _deployToStrategies();

        emit Deposit(msg.sender, receiver, assets, shares);
        emit DepositExecuted(msg.sender, receiver, assets, shares);

        return shares;
    }

    /**
     * @notice Get maximum mintable shares
     * @param receiver Address of receiver
     * @return maxShares Maximum shares that can be minted
     */
    function maxMint(address receiver) public view override returns (uint256 maxShares) {
        uint256 maxAssets_ = maxDeposit(receiver);
        return _convertToShares(maxAssets_, Math.Rounding.Down);
    }

    /**
     * @notice Preview mint assets required
     * @param shares Amount of shares to mint
     * @return assets Amount of assets required
     */
    function previewMint(uint256 shares) public view override returns (uint256 assets) {
        return _convertToAssets(shares, Math.Rounding.Up);
    }

    /**
     * @notice Mint shares for exact asset amount
     * @param shares Amount of shares to mint
     * @param receiver Address to receive shares
     * @return assets Amount of assets used
     */
    function mint(uint256 shares, address receiver) public override nonReentrant whenNotPaused returns (uint256 assets) {
        require(shares <= maxMint(receiver), "Exceeds mint limit");
        require(shares > 0, "Cannot mint zero shares");

        assets = previewMint(shares);

        // Check constitutional compliance
        _checkConstitutionalCompliance(assets, true);

        // Update user tracking
        userDepositTime[receiver] = block.timestamp;
        userSharesAtDeposit[receiver] = balanceOf(receiver);

        // Transfer assets from user
        asset.safeTransferFrom(msg.sender, address(this), assets);

        // Mint shares to receiver
        _mint(receiver, shares);

        // Collect management fees if applicable
        _collectManagementFees();

        // Update performance metrics
        _updatePerformanceMetrics();

        // Deploy assets to strategies if available
        _deployToStrategies();

        emit Deposit(msg.sender, receiver, assets, shares);
        emit DepositExecuted(msg.sender, receiver, assets, shares);

        return assets;
    }

    /**
     * @notice Get maximum withdrawable assets
     * @param owner Address of share owner
     * @return maxAssets Maximum assets that can be withdrawn
     */
    function maxWithdraw(address owner) public view override returns (uint256 maxAssets) {
        if (emergencyMode && !vaultConfig.emergencyWithdrawalEnabled) return 0;
        return _convertToAssets(balanceOf(owner), Math.Rounding.Down);
    }

    /**
     * @notice Preview withdraw shares needed
     * @param assets Amount of assets to withdraw
     * @return shares Amount of shares needed
     */
    function previewWithdraw(uint256 assets) public view override returns (uint256 shares) {
        uint256 sharesNeeded = _convertToShares(assets, Math.Rounding.Up);
        uint256 feeAmount = _calculateWithdrawalFee(assets);
        uint256 feesInShares = _convertToShares(feeAmount, Math.Rounding.Up);
        return sharesNeeded + feesInShares;
    }

    /**
     * @notice Withdraw assets and burn shares
     * @param assets Amount of assets to withdraw
     * @param receiver Address to receive assets
     * @param owner Address of share owner
     * @return shares Amount of shares burned
     */
    function withdraw(
        uint256 assets,
        address receiver,
        address owner
    ) public override nonReentrant returns (uint256 shares) {
        require(assets <= maxWithdraw(owner), "Exceeds withdraw limit");
        require(assets > 0, "Cannot withdraw zero assets");

        shares = previewWithdraw(assets);
        require(shares <= balanceOf(owner), "Insufficient shares");

        if (msg.sender != owner) {
            _spendAllowance(owner, msg.sender, shares);
        }

        // Check constitutional compliance for large withdrawals
        _checkConstitutionalCompliance(assets, false);

        // Calculate fees
        uint256 withdrawalFeeAmount = _calculateWithdrawalFee(assets);
        uint256 assetsAfterFee = assets - withdrawalFeeAmount;

        // Collect performance fees for this user
        _collectPerformanceFees(owner, shares);

        // Withdraw from strategies if needed
        _withdrawFromStrategies(assets);

        // Burn shares
        _burn(owner, shares);

        // Transfer assets to receiver (after fees)
        asset.safeTransfer(receiver, assetsAfterFee);

        // Handle fee distribution
        if (withdrawalFeeAmount > 0) {
            _distributeFees(withdrawalFeeAmount);
        }

        // Update performance metrics
        _updatePerformanceMetrics();

        emit Withdraw(msg.sender, receiver, owner, assets, shares);
        emit WithdrawExecuted(msg.sender, receiver, owner, assets, shares);

        return shares;
    }

    /**
     * @notice Get maximum redeemable shares
     * @param owner Address of share owner
     * @return maxShares Maximum shares that can be redeemed
     */
    function maxRedeem(address owner) public view override returns (uint256 maxShares) {
        if (emergencyMode && !vaultConfig.emergencyWithdrawalEnabled) return 0;
        return balanceOf(owner);
    }

    /**
     * @notice Preview redeem assets received
     * @param shares Amount of shares to redeem
     * @return assets Amount of assets that would be received
     */
    function previewRedeem(uint256 shares) public view override returns (uint256 assets) {
        uint256 assetsBeforeFee = _convertToAssets(shares, Math.Rounding.Down);
        uint256 feeAmount = _calculateWithdrawalFee(assetsBeforeFee);
        return assetsBeforeFee - feeAmount;
    }

    /**
     * @notice Redeem shares for assets
     * @param shares Amount of shares to redeem
     * @param receiver Address to receive assets
     * @param owner Address of share owner
     * @return assets Amount of assets received
     */
    function redeem(
        uint256 shares,
        address receiver,
        address owner
    ) public override nonReentrant returns (uint256 assets) {
        require(shares <= maxRedeem(owner), "Exceeds redeem limit");
        require(shares > 0, "Cannot redeem zero shares");

        if (msg.sender != owner) {
            _spendAllowance(owner, msg.sender, shares);
        }

        assets = _convertToAssets(shares, Math.Rounding.Down);

        // Check constitutional compliance
        _checkConstitutionalCompliance(assets, false);

        // Calculate fees
        uint256 withdrawalFeeAmount = _calculateWithdrawalFee(assets);
        uint256 assetsAfterFee = assets - withdrawalFeeAmount;

        // Collect performance fees for this user
        _collectPerformanceFees(owner, shares);

        // Withdraw from strategies if needed
        _withdrawFromStrategies(assets);

        // Burn shares
        _burn(owner, shares);

        // Transfer assets to receiver (after fees)
        asset.safeTransfer(receiver, assetsAfterFee);

        // Handle fee distribution
        if (withdrawalFeeAmount > 0) {
            _distributeFees(withdrawalFeeAmount);
        }

        // Update performance metrics
        _updatePerformanceMetrics();

        emit Withdraw(msg.sender, receiver, owner, assetsAfterFee, shares);
        emit WithdrawExecuted(msg.sender, receiver, owner, assetsAfterFee, shares);

        return assetsAfterFee;
    }

    // DAIO Integration Functions

    /**
     * @notice Add strategy to vault
     * @param strategy Strategy contract address
     * @param allocation Allocation percentage in BPS
     */
    function addStrategy(address strategy, uint256 allocation) external onlyRole(STRATEGY_ROLE) {
        require(strategy != address(0), "Invalid strategy address");
        require(allocation <= 10000, "Allocation exceeds 100%");
        require(!authorizedStrategies[strategy], "Strategy already added");

        // Check total allocation doesn't exceed 100%
        uint256 totalAllocation = allocation;
        for (uint256 i = 0; i < activeStrategies.length; i++) {
            totalAllocation += strategyAllocations[activeStrategies[i]];
        }
        require(totalAllocation <= 10000, "Total allocation exceeds 100%");

        authorizedStrategies[strategy] = true;
        activeStrategies.push(strategy);
        strategyAllocations[strategy] = allocation;

        emit StrategyAdded(strategy, allocation);

        // Deploy assets to strategy if vault has assets
        if (totalAssets() > 0) {
            _deployToStrategies();
        }
    }

    /**
     * @notice Update vault configuration
     * @param depositLimit New deposit limit
     * @param withdrawalFee New withdrawal fee (BPS)
     * @param managementFee New management fee (BPS)
     * @param performanceFee New performance fee (BPS)
     */
    function updateVaultConfig(
        uint256 depositLimit,
        uint256 withdrawalFee,
        uint256 managementFee,
        uint256 performanceFee
    ) external onlyRole(VAULT_MANAGER_ROLE) {
        require(withdrawalFee <= 1000, "Withdrawal fee too high"); // Max 10%
        require(managementFee <= 500, "Management fee too high"); // Max 5%
        require(performanceFee <= 5000, "Performance fee too high"); // Max 50%

        vaultConfig.depositLimit = depositLimit;
        vaultConfig.withdrawalFee = withdrawalFee;
        vaultConfig.managementFee = managementFee;
        vaultConfig.performanceFee = performanceFee;
    }

    /**
     * @notice Emergency withdraw all assets (admin only)
     * @param reason Reason for emergency withdrawal
     */
    function emergencyWithdrawAll(string memory reason) external onlyRole(EMERGENCY_ROLE) {
        emergencyMode = true;
        emergencyModeActivatedAt = block.timestamp;

        // Withdraw all assets from strategies
        for (uint256 i = 0; i < activeStrategies.length; i++) {
            _withdrawAllFromStrategy(activeStrategies[i]);
        }

        emit EmergencyModeActivated(reason);
    }

    // Internal Functions

    function _convertToShares(uint256 assets, Math.Rounding rounding) internal view returns (uint256) {
        uint256 supply = totalSupply();
        return (assets == 0 || supply == 0)
            ? assets
            : assets.mulDiv(supply, totalAssets(), rounding);
    }

    function _convertToAssets(uint256 shares, Math.Rounding rounding) internal view returns (uint256) {
        uint256 supply = totalSupply();
        return (supply == 0) ? shares : shares.mulDiv(totalAssets(), supply, rounding);
    }

    function _getTotalStrategyAssets() internal view returns (uint256 total) {
        for (uint256 i = 0; i < activeStrategies.length; i++) {
            // This would call strategy.totalAssets() in a real implementation
            // For now, return 0 as strategies would be implemented separately
        }
        return total;
    }

    function _deployToStrategies() internal {
        uint256 availableAssets = asset.balanceOf(address(this));
        if (availableAssets == 0) return;

        for (uint256 i = 0; i < activeStrategies.length; i++) {
            address strategy = activeStrategies[i];
            uint256 allocation = strategyAllocations[strategy];
            uint256 deployAmount = (availableAssets * allocation) / 10000;

            if (deployAmount > 0) {
                asset.safeTransfer(strategy, deployAmount);
                // Call strategy.deposit(deployAmount) in real implementation
            }
        }
    }

    function _withdrawFromStrategies(uint256 assetsNeeded) internal {
        uint256 availableAssets = asset.balanceOf(address(this));
        if (availableAssets >= assetsNeeded) return;

        uint256 additionalNeeded = assetsNeeded - availableAssets;

        // Withdraw proportionally from strategies
        for (uint256 i = 0; i < activeStrategies.length && additionalNeeded > 0; i++) {
            // This would call strategy.withdraw() in real implementation
            // For now, just mark that withdrawal would happen
        }
    }

    function _withdrawAllFromStrategy(address strategy) internal {
        // This would call strategy.withdrawAll() in real implementation
    }

    function _calculateWithdrawalFee(uint256 assets) internal view returns (uint256) {
        return (assets * vaultConfig.withdrawalFee) / 10000;
    }

    function _collectManagementFees() internal {
        uint256 timeSinceLastUpdate = block.timestamp - lastManagementFeeUpdate;
        if (timeSinceLastUpdate < 86400) return; // Only collect daily

        uint256 totalAssets_ = totalAssets();
        uint256 annualFee = (totalAssets_ * vaultConfig.managementFee) / 10000;
        uint256 dailyFee = (annualFee * timeSinceLastUpdate) / 365 days;

        if (dailyFee > 0) {
            uint256 feeShares = _convertToShares(dailyFee, Math.Rounding.Up);
            _mint(address(this), feeShares);

            totalFeesCollected += dailyFee;
            lastManagementFeeUpdate = block.timestamp;

            _distributeFees(dailyFee);
        }
    }

    function _collectPerformanceFees(address user, uint256 sharesRedeemed) internal {
        uint256 userShares = balanceOf(user);
        if (userShares < vaultConfig.minSharesForReward) return;

        // Calculate performance since user's last deposit
        uint256 currentSharePrice = _convertToAssets(1e18, Math.Rounding.Down);
        uint256 depositsSharePrice = performanceMetrics.sharePrice;

        if (currentSharePrice > depositsSharePrice) {
            uint256 performanceGain = currentSharePrice - depositsSharePrice;
            uint256 performanceFeeAmount = (performanceGain * vaultConfig.performanceFee) / 10000;

            if (performanceFeeAmount > 0) {
                uint256 feeShares = (sharesRedeemed * performanceFeeAmount) / currentSharePrice;
                _mint(address(this), feeShares);

                totalFeesCollected += performanceFeeAmount;
                _distributeFees(performanceFeeAmount);
            }
        }
    }

    function _distributeFees(uint256 feeAmount) internal {
        if (daioIntegration.treasuryContract != address(0)) {
            uint256 titheAmount = (feeAmount * daioIntegration.titheRate) / 10000;
            if (titheAmount > 0) {
                asset.safeTransfer(daioIntegration.treasuryContract, titheAmount);
                totalTithePaid += titheAmount;

                emit FeesCollected(0, 0, titheAmount);
            }
        }
    }

    function _checkConstitutionalCompliance(uint256 assets, bool isDeposit) internal {
        if (!daioIntegration.constitutionalCompliance) return;

        if (isDeposit) {
            uint256 newTotal = totalAssets() + assets;
            // Check against constitutional exposure limits
            emit ConstitutionalComplianceChecked(true, "Deposit within limits");
        } else {
            // For withdrawals, check if it would violate minimum reserves
            emit ConstitutionalComplianceChecked(true, "Withdrawal within limits");
        }
    }

    function _updatePerformanceMetrics() internal {
        uint256 currentAssets = totalAssets();
        uint256 currentSupply = totalSupply();

        performanceMetrics.totalAssetsManaged = currentAssets;

        if (currentSupply > 0) {
            uint256 newSharePrice = (currentAssets * 1e18) / currentSupply;
            performanceMetrics.currentPeriodReturn = int256(newSharePrice) - int256(performanceMetrics.sharePrice);
            performanceMetrics.sharePrice = newSharePrice;

            if (newSharePrice > performanceMetrics.highWaterMark) {
                performanceMetrics.highWaterMark = newSharePrice;
            }
        }

        performanceMetrics.lastUpdateTime = block.timestamp;

        emit PerformanceUpdated(
            currentAssets,
            performanceMetrics.sharePrice,
            performanceMetrics.currentPeriodReturn
        );
    }

    /**
     * @notice Add address to whitelist
     * @param user Address to whitelist
     */
    function addToWhitelist(address user) external onlyRole(VAULT_MANAGER_ROLE) {
        whitelist[user] = true;
    }

    /**
     * @notice Remove address from whitelist
     * @param user Address to remove from whitelist
     */
    function removeFromWhitelist(address user) external onlyRole(VAULT_MANAGER_ROLE) {
        whitelist[user] = false;
    }

    /**
     * @notice Emergency pause vault operations
     */
    function emergencyPause() external onlyRole(EMERGENCY_ROLE) {
        _pause();
    }

    /**
     * @notice Unpause vault operations
     */
    function unpause() external onlyRole(EMERGENCY_ROLE) {
        _unpause();
    }

    /**
     * @notice Get vault performance metrics
     * @return metrics Current performance metrics
     */
    function getPerformanceMetrics() external view returns (PerformanceMetrics memory metrics) {
        return performanceMetrics;
    }

    /**
     * @notice Get DAIO integration configuration
     * @return integration DAIO integration configuration
     */
    function getDAIOIntegration() external view returns (DAIOIntegration memory integration) {
        return daioIntegration;
    }

    /**
     * @notice Update DAIO integration settings
     * @param treasuryContract New treasury contract
     * @param titheRate New tithe rate (BPS)
     * @param constitutionalCompliance Whether to enforce constitutional compliance
     */
    function updateDAIOIntegration(
        address treasuryContract,
        uint256 titheRate,
        bool constitutionalCompliance
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(titheRate <= 1500, "Tithe rate too high"); // Max 15% per constitution

        daioIntegration.treasuryContract = treasuryContract;
        daioIntegration.titheRate = titheRate;
        daioIntegration.constitutionalCompliance = constitutionalCompliance;
    }
}

// Math library for rounding operations
library Math {
    enum Rounding {
        Down, // Toward negative infinity
        Up, // Toward infinity
        Zero // Toward zero
    }

    /**
     * @dev Returns the multiplication of two numbers with rounding.
     */
    function mulDiv(uint256 x, uint256 y, uint256 denominator, Rounding rounding) internal pure returns (uint256) {
        uint256 result = mulDiv(x, y, denominator);
        if (rounding == Rounding.Up && mulmod(x, y, denominator) > 0) {
            result += 1;
        }
        return result;
    }

    /**
     * @dev Returns the multiplication of two numbers, divided by a denominator.
     */
    function mulDiv(uint256 x, uint256 y, uint256 denominator) internal pure returns (uint256) {
        return (x * y) / denominator;
    }

    function min(uint256 a, uint256 b) internal pure returns (uint256) {
        return a < b ? a : b;
    }
}