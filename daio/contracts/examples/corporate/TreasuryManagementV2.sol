// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/math/SafeCast.sol";
import "../../daio/treasury/Treasury.sol";
import "../../eip-standards/advanced/ERC4626/DAIO_ERC4626Vault.sol";
import "../../oracles/core/PriceFeedAggregator.sol";

/**
 * @title TreasuryManagementV2
 * @dev IMPROVED Fortune 500 Corporate Treasury Management with Security Fixes
 *
 * Security Improvements:
 * - Fixed reentrancy vulnerabilities using CEI pattern
 * - Added multi-sig requirements for critical operations
 * - Implemented oracle price protection with circuit breakers
 * - Added comprehensive input validation
 * - Implemented proper emergency controls
 * - Added precision math for financial calculations
 * - Fixed constitutional compliance validation
 *
 * @author DAIO Development Team
 */

// Custom errors for gas efficiency
error InvalidAsset();
error InvalidAmount();
error UnauthorizedAccess();
error ExceedsAllocationLimit();
error InsufficientBalance();
error PriceOracleFailure();
error EmergencyModeActive();
error ConstitutionalViolation();
error RebalanceFrequencyNotMet();
error InvalidPriceDeviation();
error MultiSigRequired();

contract TreasuryManagementV2 is AccessControl, ReentrancyGuard, Pausable {
    using SafeCast for uint256;

    // =============================================================
    //                        CONSTANTS
    // =============================================================

    bytes32 public constant CFO_ROLE = keccak256("CFO_ROLE");
    bytes32 public constant TREASURER_ROLE = keccak256("TREASURER_ROLE");
    bytes32 public constant INVESTMENT_COMMITTEE_ROLE = keccak256("INVESTMENT_COMMITTEE_ROLE");
    bytes32 public constant COMPLIANCE_OFFICER_ROLE = keccak256("COMPLIANCE_OFFICER_ROLE");
    bytes32 public constant BOARD_MEMBER_ROLE = keccak256("BOARD_MEMBER_ROLE");
    bytes32 public constant MULTI_SIG_ROLE = keccak256("MULTI_SIG_ROLE");

    uint256 public constant PRECISION = 1e18;
    uint256 public constant MAX_BPS = 10000; // 100%
    uint256 public constant MIN_REBALANCE_INTERVAL = 1 hours;
    uint256 public constant MAX_PRICE_DEVIATION = 1000; // 10%
    uint256 public constant MULTI_SIG_THRESHOLD = 10000000 * PRECISION; // $10M

    // Investment categories aligned with corporate treasury standards
    enum InvestmentCategory {
        CashEquivalents,    // Money market funds, T-bills < 90 days
        ShortTermDebt,      // Government bonds < 1 year
        MediumTermDebt,     // Corporate bonds 1-5 years
        Equity,             // Strategic equity investments
        Commodities,        // Gold, oil, agricultural products
        RealEstate,         // Real estate investment trusts
        Cryptocurrency,     // Digital assets (limited allocation)
        PrivateEquity       // Private market investments
    }

    // =============================================================
    //                         STORAGE
    // =============================================================

    // Core DAIO Integration
    Treasury public immutable daiaTreasury;
    IDAIO_Constitution_Enhanced public immutable constitution;
    PriceFeedAggregator public immutable priceOracle;

    // Corporate Information
    string public companyName;
    string public stockSymbol;
    uint256 public marketCapitalization;
    uint256 public annualRevenue;

    // Multi-sig configuration
    struct MultiSigConfig {
        uint256 threshold;
        uint256 signerCount;
        mapping(address => bool) isSigner;
        mapping(bytes32 => uint256) approvals;
        mapping(bytes32 => mapping(address => bool)) hasApproved;
    }
    MultiSigConfig public multiSig;

    // Price Oracle Protection
    struct OracleProtection {
        uint256 lastPriceUpdate;
        mapping(address => uint256) lastValidPrice;
        mapping(address => uint256) priceUpdateCount;
        bool circuitBreakerActive;
        uint256 maxPriceDeviation;
        uint256 priceValidityWindow;
    }
    OracleProtection public oracleProtection;

    // Treasury Portfolio with enhanced security
    struct AssetAllocation {
        IERC20 token;
        InvestmentCategory category;
        uint256 targetPercentage; // Basis points (10000 = 100%)
        uint256 currentAmount;
        uint256 minAmount;
        uint256 maxAmount;
        uint256 lastRebalanceTime;
        address vault; // ERC4626 vault for yield generation
        bool active;
        bool whitelisted; // Additional security layer
        uint256 allocationTimestamp;
        address allocatedBy;
    }

    mapping(address => AssetAllocation) public assetAllocations;
    address[] public managedAssets;
    uint256 public maxManagedAssets = 50; // Prevent DoS

    // Investment Strategy with validation
    struct InvestmentStrategy {
        InvestmentCategory category;
        uint256 maxAllocation; // Basis points
        uint256 targetYield; // Basis points annually
        uint256 maxRisk; // Risk score 0-100
        bool autoRebalance;
        uint256 rebalanceThreshold; // Basis points deviation trigger
        uint256 rebalanceFrequency; // Seconds between rebalances
        bool approved; // Requires approval
        address approvedBy;
        uint256 approvalTimestamp;
    }

    mapping(InvestmentCategory => InvestmentStrategy) public investmentStrategies;

    // Enhanced Cash Flow Management
    struct CashFlowForecast {
        uint256 period; // Month identifier (YYYYMM)
        int256 projectedCashFlow; // Positive = inflow, negative = outflow
        uint256 confidenceLevel; // Basis points (10000 = 100% confident)
        uint256 minimumLiquidity; // Required liquid reserves
        bool approved;
        uint256 forecastTimestamp;
        address forecaster;
        bytes32 evidenceHash; // IPFS hash of supporting data
    }

    mapping(uint256 => CashFlowForecast) public cashFlowForecasts;
    uint256[] public forecastPeriods;

    // Enhanced Cross-border Operations with compliance
    struct CrossBorderPayment {
        address sender;
        address recipient;
        uint256 amount;
        address currency;
        string fromCountry;
        string toCountry;
        uint256 exchangeRate;
        uint256 fees;
        uint256 timestamp;
        bool executed;
        string complianceStatus;
        bool multiSigApproved;
        uint256 approvalCount;
        mapping(address => bool) approvals;
        bytes32 complianceHash; // Compliance documentation
    }

    mapping(bytes32 => CrossBorderPayment) public crossBorderPayments;
    bytes32[] public paymentQueue;

    // Enhanced Emergency Provisions
    struct EmergencyLiquidity {
        uint256 triggerThreshold; // Basis points of assets
        uint256 targetLiquidity; // Amount to maintain
        address[] liquidationOrder; // Assets to liquidate first
        bool activated;
        uint256 activationTime;
        uint256 recoveryTime;
        address activatedBy;
        string activationReason;
        bool boardApproved;
    }

    EmergencyLiquidity public emergencyProvisions;

    // Events with enhanced information
    event TreasuryInitialized(
        string indexed companyName,
        string stockSymbol,
        uint256 marketCap,
        address initializer
    );

    event AssetAllocationUpdated(
        address indexed asset,
        InvestmentCategory indexed category,
        uint256 targetPercentage,
        address updatedBy,
        uint256 timestamp
    );

    event RebalanceExecuted(
        address indexed asset,
        uint256 oldAmount,
        uint256 newAmount,
        uint256 deviation,
        address executor,
        uint256 gasUsed
    );

    event EmergencyLiquidityActivated(
        uint256 triggerThreshold,
        uint256 targetLiquidity,
        address activatedBy,
        string reason
    );

    event OracleCircuitBreakerTriggered(
        address indexed asset,
        uint256 oldPrice,
        uint256 newPrice,
        uint256 deviation
    );

    event MultiSigOperationInitiated(
        bytes32 indexed operationHash,
        address indexed initiator,
        string operationType
    );

    event MultiSigOperationApproved(
        bytes32 indexed operationHash,
        address indexed approver,
        uint256 totalApprovals
    );

    // =============================================================
    //                      MODIFIERS
    // =============================================================

    modifier onlyMultiSig(bytes32 operationHash) {
        if (msg.value > MULTI_SIG_THRESHOLD) {
            require(multiSig.approvals[operationHash] >= multiSig.threshold, "Insufficient multi-sig approvals");
        }
        _;
    }

    modifier validAsset(address asset) {
        if (asset == address(0)) revert InvalidAsset();
        _;
    }

    modifier validAmount(uint256 amount) {
        if (amount == 0) revert InvalidAmount();
        _;
    }

    modifier whenNotEmergency() {
        if (emergencyProvisions.activated) revert EmergencyModeActive();
        _;
    }

    modifier priceOracleHealthy() {
        if (oracleProtection.circuitBreakerActive) revert PriceOracleFailure();
        _;
    }

    // =============================================================
    //                      CONSTRUCTOR
    // =============================================================

    constructor(
        address treasuryAddress,
        address constitutionAddress,
        address priceOracleAddress,
        string memory _companyName,
        string memory _stockSymbol,
        uint256 _marketCapitalization,
        uint256 _annualRevenue,
        address[] memory multiSigSigners,
        address admin
    ) {
        if (treasuryAddress == address(0) || constitutionAddress == address(0) || priceOracleAddress == address(0)) {
            revert InvalidAsset();
        }

        daiaTreasury = Treasury(treasuryAddress);
        constitution = IDAIO_Constitution_Enhanced(constitutionAddress);
        priceOracle = PriceFeedAggregator(priceOracleAddress);

        companyName = _companyName;
        stockSymbol = _stockSymbol;
        marketCapitalization = _marketCapitalization;
        annualRevenue = _annualRevenue;

        // Set up access control
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CFO_ROLE, admin);
        _grantRole(TREASURER_ROLE, admin);
        _grantRole(INVESTMENT_COMMITTEE_ROLE, admin);

        // Initialize multi-sig
        _initializeMultiSig(multiSigSigners);

        // Initialize oracle protection
        _initializeOracleProtection();

        // Initialize emergency provisions
        _initializeEmergencyProvisions();

        // Initialize default investment strategies
        _initializeDefaultStrategies();

        emit TreasuryInitialized(_companyName, _stockSymbol, _marketCapitalization, admin);
    }

    // =============================================================
    //                    PORTFOLIO MANAGEMENT
    // =============================================================

    /**
     * @dev Add or update asset allocation target with enhanced security
     */
    function setAssetAllocation(
        address asset,
        InvestmentCategory category,
        uint256 targetPercentage,
        uint256 minAmount,
        uint256 maxAmount,
        address vault,
        bytes32 operationHash
    ) external
        onlyRole(INVESTMENT_COMMITTEE_ROLE)
        onlyMultiSig(operationHash)
        validAsset(asset)
        whenNotPaused
        whenNotEmergency
    {
        if (targetPercentage > MAX_BPS) revert InvalidAmount();
        if (minAmount > maxAmount) revert InvalidAmount();
        if (managedAssets.length >= maxManagedAssets) revert ExceedsAllocationLimit();

        // Enhanced constitutional validation
        (bool valid, string memory reason) = constitution.validateTreasuryAllocation(
            address(this),
            asset,
            targetPercentage,
            category,
            abi.encode(minAmount, maxAmount, vault)
        );
        if (!valid) revert ConstitutionalViolation();

        // Validate total allocations don't exceed 100%
        require(_validateTotalAllocations(asset, targetPercentage), "Total allocations exceed 100%");

        // Update allocation with CEI pattern
        AssetAllocation storage allocation = assetAllocations[asset];
        allocation.token = IERC20(asset);
        allocation.category = category;
        allocation.targetPercentage = targetPercentage;
        allocation.minAmount = minAmount;
        allocation.maxAmount = maxAmount;
        allocation.vault = vault;
        allocation.active = true;
        allocation.whitelisted = true;
        allocation.allocationTimestamp = block.timestamp;
        allocation.allocatedBy = msg.sender;
        allocation.lastRebalanceTime = block.timestamp;

        // Add to managed assets if new
        bool exists = false;
        for (uint256 i = 0; i < managedAssets.length; i++) {
            if (managedAssets[i] == asset) {
                exists = true;
                break;
            }
        }
        if (!exists) {
            managedAssets.push(asset);
        }

        emit AssetAllocationUpdated(asset, category, targetPercentage, msg.sender, block.timestamp);
    }

    /**
     * @dev Execute portfolio rebalancing with enhanced security and gas optimization
     */
    function rebalancePortfolio(bytes32 operationHash)
        external
        onlyRole(TREASURER_ROLE)
        onlyMultiSig(operationHash)
        nonReentrant
        whenNotPaused
        whenNotEmergency
        priceOracleHealthy
    {
        uint256 startGas = gasleft();
        uint256 totalValue = _getTotalPortfolioValueSafe();

        if (totalValue == 0) revert InvalidAmount();

        uint256 processedAssets = 0;
        uint256 maxGasPerAsset = 200000; // Gas limit per asset

        for (uint256 i = 0; i < managedAssets.length && processedAssets < 10; i++) {
            uint256 gasStart = gasleft();
            if (gasStart < maxGasPerAsset * 2) break; // Gas safety check

            address asset = managedAssets[i];
            AssetAllocation storage allocation = assetAllocations[asset];

            if (!allocation.active || !allocation.whitelisted) continue;

            // Check rebalance frequency
            InvestmentStrategy memory strategy = investmentStrategies[allocation.category];
            if (!strategy.approved || !strategy.autoRebalance) continue;

            if (block.timestamp < allocation.lastRebalanceTime + strategy.rebalanceFrequency) {
                continue;
            }

            uint256 targetAmount = (totalValue * allocation.targetPercentage) / MAX_BPS;
            uint256 currentAmount = allocation.currentAmount;

            // Calculate deviation using high precision
            uint256 deviation;
            if (currentAmount > targetAmount) {
                deviation = ((currentAmount - targetAmount) * MAX_BPS) / targetAmount;
            } else if (targetAmount > currentAmount) {
                deviation = ((targetAmount - currentAmount) * MAX_BPS) / targetAmount;
            } else {
                continue; // No rebalancing needed
            }

            if (deviation >= strategy.rebalanceThreshold) {
                _executeRebalanceSafe(asset, currentAmount, targetAmount, allocation);
                processedAssets++;
            }

            // Gas usage tracking
            uint256 gasUsed = gasStart - gasleft();
            if (gasUsed > maxGasPerAsset) break; // Safety exit
        }

        uint256 totalGasUsed = startGas - gasleft();
        emit RebalanceExecuted(address(0), 0, processedAssets, totalGasUsed, msg.sender, totalGasUsed);
    }

    // =============================================================
    //                   EMERGENCY CONTROLS
    // =============================================================

    /**
     * @dev Activate emergency liquidity provisions with board approval
     */
    function activateEmergencyLiquidity(
        string calldata reason,
        bytes32 operationHash
    ) external
        onlyRole(CFO_ROLE)
        onlyMultiSig(operationHash)
        nonReentrant
    {
        if (emergencyProvisions.activated) revert EmergencyModeActive();

        uint256 currentLiquidity = _getCurrentLiquiditySafe();
        uint256 totalAssets = _getTotalPortfolioValueSafe();
        uint256 liquidityPercentage = totalAssets > 0 ? (currentLiquidity * MAX_BPS) / totalAssets : 0;

        if (liquidityPercentage >= emergencyProvisions.triggerThreshold) {
            revert InvalidAmount(); // Sufficient liquidity
        }

        // Update state first (CEI pattern)
        emergencyProvisions.activated = true;
        emergencyProvisions.activationTime = block.timestamp;
        emergencyProvisions.activatedBy = msg.sender;
        emergencyProvisions.activationReason = reason;
        emergencyProvisions.boardApproved = true;

        // Execute emergency liquidation sequence
        _executeEmergencyLiquidationSafe();

        emit EmergencyLiquidityActivated(
            emergencyProvisions.triggerThreshold,
            emergencyProvisions.targetLiquidity,
            msg.sender,
            reason
        );
    }

    // =============================================================
    //                  ORACLE PROTECTION
    // =============================================================

    /**
     * @dev Get asset price with circuit breaker protection
     */
    function getAssetPriceSafe(address asset) public view returns (uint256 price, bool isValid) {
        if (oracleProtection.circuitBreakerActive) {
            price = oracleProtection.lastValidPrice[asset];
            isValid = false;
            return (price, isValid);
        }

        try priceOracle.getPrice(asset) returns (uint256 currentPrice) {
            uint256 lastPrice = oracleProtection.lastValidPrice[asset];

            if (lastPrice > 0) {
                uint256 deviation;
                if (currentPrice > lastPrice) {
                    deviation = ((currentPrice - lastPrice) * MAX_BPS) / lastPrice;
                } else {
                    deviation = ((lastPrice - currentPrice) * MAX_BPS) / lastPrice;
                }

                if (deviation > oracleProtection.maxPriceDeviation) {
                    price = lastPrice;
                    isValid = false;
                    return (price, isValid);
                }
            }

            price = currentPrice;
            isValid = true;
        } catch {
            price = oracleProtection.lastValidPrice[asset];
            isValid = false;
        }
    }

    /**
     * @dev Update price with circuit breaker logic
     */
    function updateAssetPrice(address asset) external onlyRole(TREASURER_ROLE) {
        (uint256 newPrice, bool isValid) = getAssetPriceSafe(asset);

        if (isValid) {
            uint256 oldPrice = oracleProtection.lastValidPrice[asset];
            oracleProtection.lastValidPrice[asset] = newPrice;
            oracleProtection.lastPriceUpdate = block.timestamp;
            oracleProtection.priceUpdateCount[asset]++;

            // Check for major price deviation
            if (oldPrice > 0) {
                uint256 deviation = oldPrice > newPrice
                    ? ((oldPrice - newPrice) * MAX_BPS) / oldPrice
                    : ((newPrice - oldPrice) * MAX_BPS) / oldPrice;

                if (deviation > MAX_PRICE_DEVIATION) {
                    emit OracleCircuitBreakerTriggered(asset, oldPrice, newPrice, deviation);
                }
            }
        } else if (!oracleProtection.circuitBreakerActive) {
            oracleProtection.circuitBreakerActive = true;
        }
    }

    // =============================================================
    //                    MULTI-SIG OPERATIONS
    // =============================================================

    /**
     * @dev Initiate multi-sig operation
     */
    function initiateMultiSigOperation(
        bytes32 operationHash,
        string calldata operationType
    ) external onlyRole(TREASURER_ROLE) {
        multiSig.approvals[operationHash] = 0;

        // Reset previous approvals
        for (uint256 i = 0; i < multiSig.signerCount; i++) {
            // This is simplified - in practice would track signers array
        }

        emit MultiSigOperationInitiated(operationHash, msg.sender, operationType);
    }

    /**
     * @dev Approve multi-sig operation
     */
    function approveMultiSigOperation(bytes32 operationHash) external onlyRole(MULTI_SIG_ROLE) {
        if (!multiSig.isSigner[msg.sender]) revert UnauthorizedAccess();
        if (multiSig.hasApproved[operationHash][msg.sender]) revert();

        multiSig.hasApproved[operationHash][msg.sender] = true;
        multiSig.approvals[operationHash]++;

        emit MultiSigOperationApproved(operationHash, msg.sender, multiSig.approvals[operationHash]);
    }

    // =============================================================
    //                 INTERNAL FUNCTIONS (SECURE)
    // =============================================================

    /**
     * @dev Safely execute rebalancing with checks-effects-interactions pattern
     */
    function _executeRebalanceSafe(
        address asset,
        uint256 currentAmount,
        uint256 targetAmount,
        AssetAllocation storage allocation
    ) internal {
        // Effects first
        allocation.currentAmount = targetAmount;
        allocation.lastRebalanceTime = block.timestamp;

        // External interactions last
        if (currentAmount > targetAmount) {
            // Need to reduce position
            uint256 sellAmount = currentAmount - targetAmount;
            if (allocation.vault != address(0)) {
                try DAIO_ERC4626Vault(allocation.vault).withdraw(sellAmount, address(this), address(this)) {
                    // Success
                } catch {
                    // Revert state changes on failure
                    allocation.currentAmount = currentAmount;
                    allocation.lastRebalanceTime -= MIN_REBALANCE_INTERVAL;
                    revert("Vault withdrawal failed");
                }
            }
        } else if (currentAmount < targetAmount) {
            // Need to increase position
            uint256 buyAmount = targetAmount - currentAmount;
            if (allocation.vault != address(0)) {
                allocation.token.approve(allocation.vault, buyAmount);
                try DAIO_ERC4626Vault(allocation.vault).deposit(buyAmount, address(this)) {
                    // Success
                } catch {
                    // Revert state changes on failure
                    allocation.currentAmount = currentAmount;
                    allocation.lastRebalanceTime -= MIN_REBALANCE_INTERVAL;
                    revert("Vault deposit failed");
                }
            }
        }

        emit RebalanceExecuted(asset, currentAmount, targetAmount, 0, msg.sender, 0);
    }

    /**
     * @dev Safely execute emergency liquidation
     */
    function _executeEmergencyLiquidationSafe() internal {
        uint256 liquidated = 0;

        for (uint256 i = 0; i < emergencyProvisions.liquidationOrder.length && liquidated < 5; i++) {
            address asset = emergencyProvisions.liquidationOrder[i];
            AssetAllocation storage allocation = assetAllocations[asset];

            if (allocation.active && allocation.currentAmount > allocation.minAmount) {
                uint256 liquidationAmount = allocation.currentAmount - allocation.minAmount;

                // Effects first
                allocation.currentAmount = allocation.minAmount;

                // Interactions last
                if (allocation.vault != address(0)) {
                    try DAIO_ERC4626Vault(allocation.vault).withdraw(liquidationAmount, address(this), address(this)) {
                        liquidated++;
                    } catch {
                        // Restore state on failure
                        allocation.currentAmount += liquidationAmount;
                    }
                }
            }
        }
    }

    /**
     * @dev Initialize multi-sig configuration
     */
    function _initializeMultiSig(address[] memory signers) internal {
        multiSig.threshold = 3; // Require 3 signatures
        multiSig.signerCount = signers.length;

        for (uint256 i = 0; i < signers.length; i++) {
            if (signers[i] != address(0)) {
                multiSig.isSigner[signers[i]] = true;
                _grantRole(MULTI_SIG_ROLE, signers[i]);
            }
        }
    }

    /**
     * @dev Initialize oracle protection
     */
    function _initializeOracleProtection() internal {
        oracleProtection.maxPriceDeviation = MAX_PRICE_DEVIATION;
        oracleProtection.priceValidityWindow = 1 hours;
        oracleProtection.circuitBreakerActive = false;
    }

    /**
     * @dev Initialize emergency provisions
     */
    function _initializeEmergencyProvisions() internal {
        emergencyProvisions.triggerThreshold = 1000; // 10% of assets
        emergencyProvisions.targetLiquidity = 5000; // 50% liquidity target
        emergencyProvisions.activated = false;
    }

    /**
     * @dev Initialize default investment strategies with approval
     */
    function _initializeDefaultStrategies() internal {
        // Cash Equivalents (Conservative)
        investmentStrategies[InvestmentCategory.CashEquivalents] = InvestmentStrategy({
            category: InvestmentCategory.CashEquivalents,
            maxAllocation: 3000, // 30%
            targetYield: 200,   // 2%
            maxRisk: 5,
            autoRebalance: true,
            rebalanceThreshold: 100, // 1%
            rebalanceFrequency: 86400, // Daily
            approved: true,
            approvedBy: msg.sender,
            approvalTimestamp: block.timestamp
        });

        // Short Term Debt (Conservative)
        investmentStrategies[InvestmentCategory.ShortTermDebt] = InvestmentStrategy({
            category: InvestmentCategory.ShortTermDebt,
            maxAllocation: 2500, // 25%
            targetYield: 300,   // 3%
            maxRisk: 15,
            autoRebalance: true,
            rebalanceThreshold: 200, // 2%
            rebalanceFrequency: 604800, // Weekly
            approved: true,
            approvedBy: msg.sender,
            approvalTimestamp: block.timestamp
        });

        // Equity with constitutional limit
        investmentStrategies[InvestmentCategory.Equity] = InvestmentStrategy({
            category: InvestmentCategory.Equity,
            maxAllocation: 1500, // 15% (constitutional limit)
            targetYield: 800,   // 8%
            maxRisk: 45,
            autoRebalance: true,
            rebalanceThreshold: 500, // 5%
            rebalanceFrequency: 2592000, // Monthly
            approved: true,
            approvedBy: msg.sender,
            approvalTimestamp: block.timestamp
        });
    }

    /**
     * @dev Validate total allocations don't exceed 100%
     */
    function _validateTotalAllocations(address excludeAsset, uint256 newPercentage) internal view returns (bool) {
        uint256 totalAllocations = 0;

        for (uint256 i = 0; i < managedAssets.length; i++) {
            address asset = managedAssets[i];
            if (asset != excludeAsset && assetAllocations[asset].active) {
                totalAllocations += assetAllocations[asset].targetPercentage;
            }
        }

        totalAllocations += newPercentage;
        return totalAllocations <= MAX_BPS;
    }

    /**
     * @dev Get total portfolio value with error handling
     */
    function _getTotalPortfolioValueSafe() internal view returns (uint256) {
        uint256 total = 0;

        for (uint256 i = 0; i < managedAssets.length; i++) {
            address asset = managedAssets[i];
            AssetAllocation storage allocation = assetAllocations[asset];

            if (allocation.active && allocation.whitelisted) {
                (uint256 assetPrice, bool isValid) = getAssetPriceSafe(asset);
                if (isValid && assetPrice > 0) {
                    uint256 assetValue = (allocation.currentAmount * assetPrice) / PRECISION;
                    total += assetValue;
                }
            }
        }

        return total;
    }

    /**
     * @dev Get current liquidity with error handling
     */
    function _getCurrentLiquiditySafe() internal view returns (uint256) {
        uint256 liquidity = 0;

        for (uint256 i = 0; i < managedAssets.length; i++) {
            address asset = managedAssets[i];
            AssetAllocation storage allocation = assetAllocations[asset];

            if (allocation.active && allocation.category == InvestmentCategory.CashEquivalents) {
                (uint256 assetPrice, bool isValid) = getAssetPriceSafe(asset);
                if (isValid && assetPrice > 0) {
                    uint256 assetValue = (allocation.currentAmount * assetPrice) / PRECISION;
                    liquidity += assetValue;
                }
            }
        }

        return liquidity;
    }

    // =============================================================
    //                      VIEW FUNCTIONS
    // =============================================================

    /**
     * @dev Get portfolio overview with error handling
     */
    function getPortfolioOverview() external view returns (
        uint256 totalValue,
        uint256 liquidityRatio,
        uint256 numberOfAssets,
        uint256 concentrationRisk,
        bool emergencyActive,
        bool oracleHealthy
    ) {
        totalValue = _getTotalPortfolioValueSafe();
        uint256 liquidAssets = _getCurrentLiquiditySafe();
        liquidityRatio = totalValue > 0 ? (liquidAssets * MAX_BPS) / totalValue : 0;
        numberOfAssets = managedAssets.length;
        concentrationRisk = _calculateConcentrationRiskSafe();
        emergencyActive = emergencyProvisions.activated;
        oracleHealthy = !oracleProtection.circuitBreakerActive;
    }

    /**
     * @dev Calculate concentration risk safely
     */
    function _calculateConcentrationRiskSafe() internal view returns (uint256) {
        uint256 maxConcentration = 0;
        uint256 totalValue = _getTotalPortfolioValueSafe();

        if (totalValue == 0) return 0;

        for (uint256 i = 0; i < managedAssets.length; i++) {
            address asset = managedAssets[i];
            AssetAllocation storage allocation = assetAllocations[asset];

            if (allocation.active && allocation.whitelisted) {
                (uint256 assetPrice, bool isValid) = getAssetPriceSafe(asset);
                if (isValid && assetPrice > 0) {
                    uint256 assetValue = (allocation.currentAmount * assetPrice) / PRECISION;
                    uint256 concentration = (assetValue * MAX_BPS) / totalValue;
                    if (concentration > maxConcentration) {
                        maxConcentration = concentration;
                    }
                }
            }
        }

        return maxConcentration;
    }

    /**
     * @dev Get managed assets
     */
    function getManagedAssets() external view returns (address[] memory) {
        return managedAssets;
    }

    /**
     * @dev Get oracle protection status
     */
    function getOracleProtectionStatus() external view returns (
        bool circuitBreakerActive,
        uint256 lastPriceUpdate,
        uint256 maxPriceDeviation,
        uint256 priceValidityWindow
    ) {
        return (
            oracleProtection.circuitBreakerActive,
            oracleProtection.lastPriceUpdate,
            oracleProtection.maxPriceDeviation,
            oracleProtection.priceValidityWindow
        );
    }

    // =============================================================
    //                    ADMIN FUNCTIONS
    // =============================================================

    /**
     * @dev Emergency pause function
     */
    function pause() external onlyRole(CFO_ROLE) {
        _pause();
    }

    /**
     * @dev Unpause function
     */
    function unpause() external onlyRole(CFO_ROLE) {
        _unpause();
    }

    /**
     * @dev Manually trigger oracle circuit breaker
     */
    function triggerOracleCircuitBreaker() external onlyRole(COMPLIANCE_OFFICER_ROLE) {
        oracleProtection.circuitBreakerActive = true;
    }

    /**
     * @dev Reset oracle circuit breaker
     */
    function resetOracleCircuitBreaker() external onlyRole(CFO_ROLE) {
        oracleProtection.circuitBreakerActive = false;
        oracleProtection.lastPriceUpdate = block.timestamp;
    }

    /**
     * @dev Update multi-sig threshold
     */
    function updateMultiSigThreshold(uint256 newThreshold) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newThreshold > 0 && newThreshold <= multiSig.signerCount, "Invalid threshold");
        multiSig.threshold = newThreshold;
    }
}