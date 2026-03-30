// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "../../daio/treasury/Treasury.sol";
import "../../eip-standards/advanced/ERC4626/DAIO_ERC4626Vault.sol";
import "../../oracles/core/PriceFeedAggregator.sol";

/**
 * @title TreasuryManagement
 * @dev Fortune 500 Corporate Treasury Management Example
 *
 * This contract demonstrates how a Fortune 500 company can use DAIO
 * infrastructure for comprehensive treasury management:
 *
 * USE CASE: Global Technology Corporation (Fortune 500)
 * - $50B+ annual revenue, $15B+ cash reserves
 * - Multi-currency operations across 50+ countries
 * - Complex investment portfolio management
 * - Regulatory compliance across multiple jurisdictions
 * - Automated treasury operations with governance oversight
 *
 * Key Features:
 * - Multi-asset portfolio management with constitutional constraints
 * - Automated yield farming with risk management
 * - Cross-border payment automation
 * - Regulatory compliance reporting
 * - Emergency liquidity provisions
 * - Board-level governance integration
 *
 * @author DAIO Development Team
 */

contract TreasuryManagement is AccessControl, ReentrancyGuard {
    // =============================================================
    //                        CONSTANTS
    // =============================================================

    bytes32 public constant CFO_ROLE = keccak256("CFO_ROLE");
    bytes32 public constant TREASURER_ROLE = keccak256("TREASURER_ROLE");
    bytes32 public constant INVESTMENT_COMMITTEE_ROLE = keccak256("INVESTMENT_COMMITTEE_ROLE");
    bytes32 public constant COMPLIANCE_OFFICER_ROLE = keccak256("COMPLIANCE_OFFICER_ROLE");
    bytes32 public constant BOARD_MEMBER_ROLE = keccak256("BOARD_MEMBER_ROLE");

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
    DAIO_Constitution public immutable constitution;
    PriceFeedAggregator public immutable priceOracle;

    // Corporate Information
    string public companyName;
    string public stockSymbol;
    uint256 public marketCapitalization;
    uint256 public annualRevenue;

    // Treasury Portfolio
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
    }

    mapping(address => AssetAllocation) public assetAllocations;
    address[] public managedAssets;

    // Investment Strategy
    struct InvestmentStrategy {
        InvestmentCategory category;
        uint256 maxAllocation; // Basis points
        uint256 targetYield; // Basis points annually
        uint256 maxRisk; // Risk score 0-100
        bool autoRebalance;
        uint256 rebalanceThreshold; // Basis points deviation trigger
        uint256 rebalanceFrequency; // Seconds between rebalances
    }

    mapping(InvestmentCategory => InvestmentStrategy) public investmentStrategies;

    // Cash Flow Management
    struct CashFlowForecast {
        uint256 period; // Month identifier (YYYYMM)
        int256 projectedCashFlow; // Positive = inflow, negative = outflow
        uint256 confidenceLevel; // Basis points (10000 = 100% confident)
        uint256 minimumLiquidity; // Required liquid reserves
        bool approved;
    }

    mapping(uint256 => CashFlowForecast) public cashFlowForecasts;
    uint256[] public forecastPeriods;

    // Cross-border Operations
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
    }

    mapping(bytes32 => CrossBorderPayment) public crossBorderPayments;
    bytes32[] public paymentQueue;

    // Regulatory Compliance
    struct ComplianceMetrics {
        uint256 reportingPeriod;
        uint256 totalAssets;
        uint256 liquidityRatio; // Basis points
        uint256 concentrationRisk; // Max single asset percentage
        uint256 geographicDiversification; // Number of countries
        uint256 currencyExposure; // Non-base currency percentage
        bool auditCompliant;
        string regulatoryFramework; // "SOX", "IFRS", "GAAP", etc.
    }

    mapping(uint256 => ComplianceMetrics) public complianceReports;

    // Emergency Provisions
    struct EmergencyLiquidity {
        uint256 triggerThreshold; // Basis points of assets
        uint256 targetLiquidity; // Amount to maintain
        address[] liquidationOrder; // Assets to liquidate first
        bool activated;
        uint256 activationTime;
        uint256 recoveryTime;
    }

    EmergencyLiquidity public emergencyProvisions;

    // Events
    event TreasuryInitialized(string companyName, string stockSymbol, uint256 marketCap);
    event AssetAllocationUpdated(address indexed asset, InvestmentCategory category, uint256 targetPercentage);
    event InvestmentStrategySet(InvestmentCategory indexed category, uint256 maxAllocation, uint256 targetYield);
    event RebalanceExecuted(address indexed asset, uint256 oldAmount, uint256 newAmount);
    event CashFlowForecastSubmitted(uint256 indexed period, int256 projectedCashFlow, uint256 confidenceLevel);
    event CrossBorderPaymentInitiated(bytes32 indexed paymentId, address sender, address recipient, uint256 amount);
    event ComplianceReportGenerated(uint256 indexed period, uint256 totalAssets, uint256 liquidityRatio);
    event EmergencyLiquidityActivated(uint256 triggerThreshold, uint256 targetLiquidity);
    event YieldHarvested(address indexed asset, uint256 amount, address vault);

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
        address cfo,
        address treasurer
    ) {
        daiaTreasury = Treasury(treasuryAddress);
        constitution = DAIO_Constitution(constitutionAddress);
        priceOracle = PriceFeedAggregator(priceOracleAddress);

        companyName = _companyName;
        stockSymbol = _stockSymbol;
        marketCapitalization = _marketCapitalization;
        annualRevenue = _annualRevenue;

        // Set up corporate governance roles
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(CFO_ROLE, cfo);
        _grantRole(TREASURER_ROLE, treasurer);

        // Initialize default investment strategies
        _initializeDefaultStrategies();

        // Set up emergency provisions
        emergencyProvisions.triggerThreshold = 1000; // 10% of assets
        emergencyProvisions.targetLiquidity = 5000; // 50% liquidity target

        emit TreasuryInitialized(_companyName, _stockSymbol, _marketCapitalization);
    }

    // =============================================================
    //                    PORTFOLIO MANAGEMENT
    // =============================================================

    /**
     * @dev Add or update asset allocation target
     */
    function setAssetAllocation(
        address asset,
        InvestmentCategory category,
        uint256 targetPercentage,
        uint256 minAmount,
        uint256 maxAmount,
        address vault
    ) external onlyRole(INVESTMENT_COMMITTEE_ROLE) {
        require(asset != address(0), "Invalid asset");
        require(targetPercentage <= 10000, "Target percentage too high");
        require(minAmount <= maxAmount, "Invalid amount range");

        // Validate with constitutional constraints
        require(_validateAllocationCompliance(asset, targetPercentage), "Allocation violates constitution");

        AssetAllocation storage allocation = assetAllocations[asset];
        allocation.token = IERC20(asset);
        allocation.category = category;
        allocation.targetPercentage = targetPercentage;
        allocation.minAmount = minAmount;
        allocation.maxAmount = maxAmount;
        allocation.vault = vault;
        allocation.active = true;
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

        emit AssetAllocationUpdated(asset, category, targetPercentage);
    }

    /**
     * @dev Set investment strategy for a category
     */
    function setInvestmentStrategy(
        InvestmentCategory category,
        uint256 maxAllocation,
        uint256 targetYield,
        uint256 maxRisk,
        bool autoRebalance,
        uint256 rebalanceThreshold,
        uint256 rebalanceFrequency
    ) external onlyRole(INVESTMENT_COMMITTEE_ROLE) {
        require(maxAllocation <= 10000, "Max allocation too high");
        require(targetYield <= 5000, "Target yield too high"); // Max 50% annually
        require(maxRisk <= 100, "Max risk out of range");

        InvestmentStrategy storage strategy = investmentStrategies[category];
        strategy.category = category;
        strategy.maxAllocation = maxAllocation;
        strategy.targetYield = targetYield;
        strategy.maxRisk = maxRisk;
        strategy.autoRebalance = autoRebalance;
        strategy.rebalanceThreshold = rebalanceThreshold;
        strategy.rebalanceFrequency = rebalanceFrequency;

        emit InvestmentStrategySet(category, maxAllocation, targetYield);
    }

    /**
     * @dev Execute portfolio rebalancing
     */
    function rebalancePortfolio() external onlyRole(TREASURER_ROLE) nonReentrant {
        uint256 totalValue = _getTotalPortfolioValue();
        require(totalValue > 0, "No assets to rebalance");

        for (uint256 i = 0; i < managedAssets.length; i++) {
            address asset = managedAssets[i];
            AssetAllocation storage allocation = assetAllocations[asset];

            if (!allocation.active) continue;

            uint256 targetAmount = (totalValue * allocation.targetPercentage) / 10000;
            uint256 currentAmount = allocation.currentAmount;

            // Check if rebalancing is needed
            InvestmentStrategy memory strategy = investmentStrategies[allocation.category];
            if (strategy.autoRebalance) {
                uint256 deviation = currentAmount > targetAmount ?
                    ((currentAmount - targetAmount) * 10000) / targetAmount :
                    ((targetAmount - currentAmount) * 10000) / targetAmount;

                if (deviation >= strategy.rebalanceThreshold &&
                    block.timestamp >= allocation.lastRebalanceTime + strategy.rebalanceFrequency) {

                    _executeRebalance(asset, currentAmount, targetAmount, allocation);
                }
            }
        }
    }

    // =============================================================
    //                   CASH FLOW MANAGEMENT
    // =============================================================

    /**
     * @dev Submit cash flow forecast
     */
    function submitCashFlowForecast(
        uint256 period,
        int256 projectedCashFlow,
        uint256 confidenceLevel,
        uint256 minimumLiquidity
    ) external onlyRole(TREASURER_ROLE) {
        require(period > 202400, "Invalid period"); // Must be after 2024
        require(confidenceLevel <= 10000, "Invalid confidence level");

        CashFlowForecast storage forecast = cashFlowForecasts[period];
        forecast.period = period;
        forecast.projectedCashFlow = projectedCashFlow;
        forecast.confidenceLevel = confidenceLevel;
        forecast.minimumLiquidity = minimumLiquidity;
        forecast.approved = false;

        // Add to forecast periods if new
        bool exists = false;
        for (uint256 i = 0; i < forecastPeriods.length; i++) {
            if (forecastPeriods[i] == period) {
                exists = true;
                break;
            }
        }
        if (!exists) {
            forecastPeriods.push(period);
        }

        emit CashFlowForecastSubmitted(period, projectedCashFlow, confidenceLevel);
    }

    /**
     * @dev Approve cash flow forecast (requires CFO approval)
     */
    function approveCashFlowForecast(uint256 period) external onlyRole(CFO_ROLE) {
        CashFlowForecast storage forecast = cashFlowForecasts[period];
        require(forecast.period == period, "Forecast not found");

        forecast.approved = true;

        // Trigger liquidity planning if negative cash flow projected
        if (forecast.projectedCashFlow < 0) {
            _planLiquidityProvision(period, uint256(-forecast.projectedCashFlow));
        }
    }

    // =============================================================
    //                  CROSS-BORDER PAYMENTS
    // =============================================================

    /**
     * @dev Initiate cross-border payment
     */
    function initiateCrossBorderPayment(
        address recipient,
        uint256 amount,
        address currency,
        string calldata fromCountry,
        string calldata toCountry
    ) external onlyRole(TREASURER_ROLE) returns (bytes32 paymentId) {
        require(recipient != address(0), "Invalid recipient");
        require(amount > 0, "Invalid amount");

        paymentId = keccak256(abi.encodePacked(
            msg.sender,
            recipient,
            amount,
            currency,
            block.timestamp
        ));

        // Get current exchange rate from oracle
        uint256 exchangeRate = priceOracle.getPrice(currency);

        CrossBorderPayment storage payment = crossBorderPayments[paymentId];
        payment.sender = msg.sender;
        payment.recipient = recipient;
        payment.amount = amount;
        payment.currency = currency;
        payment.fromCountry = fromCountry;
        payment.toCountry = toCountry;
        payment.exchangeRate = exchangeRate;
        payment.fees = _calculateCrossBorderFees(amount, fromCountry, toCountry);
        payment.timestamp = block.timestamp;
        payment.executed = false;
        payment.complianceStatus = "PENDING";

        paymentQueue.push(paymentId);

        emit CrossBorderPaymentInitiated(paymentId, msg.sender, recipient, amount);

        // Auto-execute if within limits and compliant
        if (_checkPaymentCompliance(paymentId)) {
            _executeCrossBorderPayment(paymentId);
        }
    }

    /**
     * @dev Execute approved cross-border payment
     */
    function executeCrossBorderPayment(bytes32 paymentId) external onlyRole(COMPLIANCE_OFFICER_ROLE) {
        require(_checkPaymentCompliance(paymentId), "Payment not compliant");
        _executeCrossBorderPayment(paymentId);
    }

    // =============================================================
    //                REGULATORY COMPLIANCE
    // =============================================================

    /**
     * @dev Generate compliance report
     */
    function generateComplianceReport(
        uint256 reportingPeriod,
        string calldata regulatoryFramework
    ) external onlyRole(COMPLIANCE_OFFICER_ROLE) returns (
        uint256 totalAssets,
        uint256 liquidityRatio,
        uint256 concentrationRisk,
        bool auditCompliant
    ) {
        totalAssets = _getTotalPortfolioValue();
        liquidityRatio = _calculateLiquidityRatio();
        concentrationRisk = _calculateConcentrationRisk();
        auditCompliant = _performAuditCheck();

        ComplianceMetrics storage report = complianceReports[reportingPeriod];
        report.reportingPeriod = reportingPeriod;
        report.totalAssets = totalAssets;
        report.liquidityRatio = liquidityRatio;
        report.concentrationRisk = concentrationRisk;
        report.geographicDiversification = _calculateGeographicDiversification();
        report.currencyExposure = _calculateCurrencyExposure();
        report.auditCompliant = auditCompliant;
        report.regulatoryFramework = regulatoryFramework;

        emit ComplianceReportGenerated(reportingPeriod, totalAssets, liquidityRatio);

        return (totalAssets, liquidityRatio, concentrationRisk, auditCompliant);
    }

    // =============================================================
    //                  EMERGENCY PROVISIONS
    // =============================================================

    /**
     * @dev Activate emergency liquidity provisions
     */
    function activateEmergencyLiquidity() external onlyRole(CFO_ROLE) {
        require(!emergencyProvisions.activated, "Already activated");

        uint256 currentLiquidity = _getCurrentLiquidity();
        uint256 totalAssets = _getTotalPortfolioValue();
        uint256 liquidityPercentage = (currentLiquidity * 10000) / totalAssets;

        require(liquidityPercentage < emergencyProvisions.triggerThreshold, "Liquidity sufficient");

        emergencyProvisions.activated = true;
        emergencyProvisions.activationTime = block.timestamp;

        // Execute emergency liquidation sequence
        _executeEmergencyLiquidation();

        emit EmergencyLiquidityActivated(emergencyProvisions.triggerThreshold, emergencyProvisions.targetLiquidity);
    }

    /**
     * @dev Deactivate emergency provisions when liquidity restored
     */
    function deactivateEmergencyLiquidity() external onlyRole(CFO_ROLE) {
        require(emergencyProvisions.activated, "Not activated");

        uint256 currentLiquidity = _getCurrentLiquidity();
        uint256 totalAssets = _getTotalPortfolioValue();
        uint256 liquidityPercentage = (currentLiquidity * 10000) / totalAssets;

        require(liquidityPercentage >= emergencyProvisions.targetLiquidity, "Target liquidity not reached");

        emergencyProvisions.activated = false;
        emergencyProvisions.recoveryTime = block.timestamp;
    }

    // =============================================================
    //                     YIELD HARVESTING
    // =============================================================

    /**
     * @dev Harvest yield from all vaults
     */
    function harvestAllYield() external onlyRole(TREASURER_ROLE) nonReentrant {
        for (uint256 i = 0; i < managedAssets.length; i++) {
            address asset = managedAssets[i];
            AssetAllocation storage allocation = assetAllocations[asset];

            if (allocation.vault != address(0) && allocation.active) {
                _harvestYieldFromVault(asset, allocation.vault);
            }
        }
    }

    /**
     * @dev Harvest yield from specific vault
     */
    function harvestYield(address asset) external onlyRole(TREASURER_ROLE) nonReentrant {
        AssetAllocation storage allocation = assetAllocations[asset];
        require(allocation.vault != address(0), "No vault configured");
        require(allocation.active, "Asset not active");

        _harvestYieldFromVault(asset, allocation.vault);
    }

    // =============================================================
    //                   INTERNAL FUNCTIONS
    // =============================================================

    /**
     * @dev Initialize default investment strategies
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
            rebalanceFrequency: 86400 // Daily
        });

        // Short Term Debt (Conservative)
        investmentStrategies[InvestmentCategory.ShortTermDebt] = InvestmentStrategy({
            category: InvestmentCategory.ShortTermDebt,
            maxAllocation: 2500, // 25%
            targetYield: 300,   // 3%
            maxRisk: 15,
            autoRebalance: true,
            rebalanceThreshold: 200, // 2%
            rebalanceFrequency: 604800 // Weekly
        });

        // Medium Term Debt (Moderate)
        investmentStrategies[InvestmentCategory.MediumTermDebt] = InvestmentStrategy({
            category: InvestmentCategory.MediumTermDebt,
            maxAllocation: 2000, // 20%
            targetYield: 500,   // 5%
            maxRisk: 25,
            autoRebalance: true,
            rebalanceThreshold: 300, // 3%
            rebalanceFrequency: 2592000 // Monthly
        });

        // Equity (Moderate to Aggressive)
        investmentStrategies[InvestmentCategory.Equity] = InvestmentStrategy({
            category: InvestmentCategory.Equity,
            maxAllocation: 1500, // 15% (constitutional limit enforced)
            targetYield: 800,   // 8%
            maxRisk: 45,
            autoRebalance: true,
            rebalanceThreshold: 500, // 5%
            rebalanceFrequency: 2592000 // Monthly
        });

        // Cryptocurrency (High Risk, Limited)
        investmentStrategies[InvestmentCategory.Cryptocurrency] = InvestmentStrategy({
            category: InvestmentCategory.Cryptocurrency,
            maxAllocation: 500,  // 5%
            targetYield: 1500,  // 15%
            maxRisk: 90,
            autoRebalance: false, // Manual rebalancing due to volatility
            rebalanceThreshold: 1000, // 10%
            rebalanceFrequency: 2592000 // Monthly
        });
    }

    /**
     * @dev Validate allocation compliance with DAIO constitution
     */
    function _validateAllocationCompliance(address asset, uint256 targetPercentage) internal view returns (bool) {
        // Enforce 15% diversification limit from constitution
        if (targetPercentage > 1500) { // 15%
            return false;
        }

        // Check total allocations don't exceed 100%
        uint256 totalAllocations = 0;
        for (uint256 i = 0; i < managedAssets.length; i++) {
            if (managedAssets[i] != asset) {
                totalAllocations += assetAllocations[managedAssets[i]].targetPercentage;
            }
        }
        totalAllocations += targetPercentage;

        return totalAllocations <= 10000; // 100%
    }

    /**
     * @dev Execute rebalancing for a specific asset
     */
    function _executeRebalance(
        address asset,
        uint256 currentAmount,
        uint256 targetAmount,
        AssetAllocation storage allocation
    ) internal {
        if (currentAmount > targetAmount) {
            // Need to reduce position
            uint256 sellAmount = currentAmount - targetAmount;
            if (allocation.vault != address(0)) {
                DAIO_ERC4626Vault(allocation.vault).withdraw(sellAmount, address(this), address(this));
            } else {
                // Direct asset sale logic would go here
            }
        } else if (currentAmount < targetAmount) {
            // Need to increase position
            uint256 buyAmount = targetAmount - currentAmount;
            if (allocation.vault != address(0)) {
                allocation.token.approve(allocation.vault, buyAmount);
                DAIO_ERC4626Vault(allocation.vault).deposit(buyAmount, address(this));
            } else {
                // Direct asset purchase logic would go here
            }
        }

        allocation.currentAmount = targetAmount;
        allocation.lastRebalanceTime = block.timestamp;

        emit RebalanceExecuted(asset, currentAmount, targetAmount);
    }

    /**
     * @dev Calculate cross-border payment fees
     */
    function _calculateCrossBorderFees(
        uint256 amount,
        string memory fromCountry,
        string memory toCountry
    ) internal pure returns (uint256) {
        // Simplified fee calculation - in practice this would use
        // complex routing and regulatory fee structures
        uint256 baseFee = amount * 25 / 10000; // 0.25%

        // Higher fees for certain corridors
        if (keccak256(bytes(fromCountry)) != keccak256(bytes(toCountry))) {
            baseFee += amount * 50 / 10000; // Additional 0.5%
        }

        return baseFee;
    }

    /**
     * @dev Check payment compliance
     */
    function _checkPaymentCompliance(bytes32 paymentId) internal view returns (bool) {
        CrossBorderPayment storage payment = crossBorderPayments[paymentId];

        // Simplified compliance check
        // In practice this would integrate with KYC/AML systems
        if (payment.amount > 1000000 * 1e18) { // $1M threshold
            return false; // Requires manual approval
        }

        return true;
    }

    /**
     * @dev Execute cross-border payment
     */
    function _executeCrossBorderPayment(bytes32 paymentId) internal {
        CrossBorderPayment storage payment = crossBorderPayments[paymentId];
        require(!payment.executed, "Payment already executed");

        IERC20 currency = IERC20(payment.currency);
        require(currency.balanceOf(address(this)) >= payment.amount + payment.fees, "Insufficient balance");

        // Execute transfer
        currency.transfer(payment.recipient, payment.amount);

        // Pay fees to DAIO treasury (15% tithe)
        uint256 daiaTithe = payment.fees * 1500 / 10000;
        currency.transfer(address(daiaTreasury), daiaTithe);

        payment.executed = true;
        payment.complianceStatus = "COMPLETED";
    }

    /**
     * @dev Plan liquidity provision based on cash flow forecast
     */
    function _planLiquidityProvision(uint256 period, uint256 requiredLiquidity) internal {
        // Simplified liquidity planning
        // In practice this would optimize across multiple funding sources
        uint256 currentLiquidity = _getCurrentLiquidity();

        if (currentLiquidity < requiredLiquidity) {
            // Need to liquidate assets or arrange credit facilities
            uint256 shortfall = requiredLiquidity - currentLiquidity;
            // Would trigger rebalancing or credit line activation
        }
    }

    /**
     * @dev Execute emergency liquidation sequence
     */
    function _executeEmergencyLiquidation() internal {
        // Liquidate assets in predefined order to raise emergency liquidity
        for (uint256 i = 0; i < emergencyProvisions.liquidationOrder.length; i++) {
            address asset = emergencyProvisions.liquidationOrder[i];
            AssetAllocation storage allocation = assetAllocations[asset];

            if (allocation.active && allocation.currentAmount > allocation.minAmount) {
                uint256 liquidationAmount = allocation.currentAmount - allocation.minAmount;

                if (allocation.vault != address(0)) {
                    DAIO_ERC4626Vault(allocation.vault).withdraw(liquidationAmount, address(this), address(this));
                }

                allocation.currentAmount = allocation.minAmount;
            }
        }
    }

    /**
     * @dev Harvest yield from ERC4626 vault
     */
    function _harvestYieldFromVault(address asset, address vault) internal {
        DAIO_ERC4626Vault erc4626Vault = DAIO_ERC4626Vault(vault);

        // Calculate accrued yield
        uint256 shares = erc4626Vault.balanceOf(address(this));
        uint256 assets = erc4626Vault.convertToAssets(shares);
        AssetAllocation storage allocation = assetAllocations[asset];

        if (assets > allocation.currentAmount) {
            uint256 yield = assets - allocation.currentAmount;

            // Withdraw yield while keeping principal invested
            uint256 sharesToWithdraw = erc4626Vault.convertToShares(yield);
            erc4626Vault.redeem(sharesToWithdraw, address(this), address(this));

            // Update current amount
            allocation.currentAmount = assets - yield;

            emit YieldHarvested(asset, yield, vault);
        }
    }

    // View functions for calculations
    function _getTotalPortfolioValue() internal view returns (uint256) {
        uint256 total = 0;
        for (uint256 i = 0; i < managedAssets.length; i++) {
            address asset = managedAssets[i];
            AssetAllocation storage allocation = assetAllocations[asset];
            if (allocation.active) {
                uint256 assetPrice = priceOracle.getPrice(asset);
                total += (allocation.currentAmount * assetPrice) / 1e18;
            }
        }
        return total;
    }

    function _getCurrentLiquidity() internal view returns (uint256) {
        uint256 liquidity = 0;
        for (uint256 i = 0; i < managedAssets.length; i++) {
            address asset = managedAssets[i];
            AssetAllocation storage allocation = assetAllocations[asset];
            if (allocation.active && allocation.category == InvestmentCategory.CashEquivalents) {
                uint256 assetPrice = priceOracle.getPrice(asset);
                liquidity += (allocation.currentAmount * assetPrice) / 1e18;
            }
        }
        return liquidity;
    }

    function _calculateLiquidityRatio() internal view returns (uint256) {
        uint256 totalAssets = _getTotalPortfolioValue();
        uint256 liquidAssets = _getCurrentLiquidity();
        return totalAssets > 0 ? (liquidAssets * 10000) / totalAssets : 0;
    }

    function _calculateConcentrationRisk() internal view returns (uint256) {
        uint256 maxConcentration = 0;
        uint256 totalValue = _getTotalPortfolioValue();

        for (uint256 i = 0; i < managedAssets.length; i++) {
            address asset = managedAssets[i];
            AssetAllocation storage allocation = assetAllocations[asset];
            if (allocation.active) {
                uint256 assetValue = (allocation.currentAmount * priceOracle.getPrice(asset)) / 1e18;
                uint256 concentration = (assetValue * 10000) / totalValue;
                if (concentration > maxConcentration) {
                    maxConcentration = concentration;
                }
            }
        }
        return maxConcentration;
    }

    function _calculateGeographicDiversification() internal pure returns (uint256) {
        // Simplified - would track actual geographic exposure
        return 25; // Assume operations in 25 countries
    }

    function _calculateCurrencyExposure() internal pure returns (uint256) {
        // Simplified - would calculate actual foreign currency exposure
        return 3500; // 35% non-base currency exposure
    }

    function _performAuditCheck() internal view returns (bool) {
        // Simplified audit compliance check
        uint256 concentrationRisk = _calculateConcentrationRisk();
        uint256 liquidityRatio = _calculateLiquidityRatio();

        // Basic compliance: max 15% concentration, min 10% liquidity
        return concentrationRisk <= 1500 && liquidityRatio >= 1000;
    }

    // =============================================================
    //                      VIEW FUNCTIONS
    // =============================================================

    /**
     * @dev Get portfolio overview
     */
    function getPortfolioOverview() external view returns (
        uint256 totalValue,
        uint256 liquidityRatio,
        uint256 numberOfAssets,
        uint256 concentrationRisk
    ) {
        totalValue = _getTotalPortfolioValue();
        liquidityRatio = _calculateLiquidityRatio();
        numberOfAssets = managedAssets.length;
        concentrationRisk = _calculateConcentrationRisk();
    }

    /**
     * @dev Get managed assets list
     */
    function getManagedAssets() external view returns (address[] memory) {
        return managedAssets;
    }

    /**
     * @dev Get forecast periods
     */
    function getForecastPeriods() external view returns (uint256[] memory) {
        return forecastPeriods;
    }

    /**
     * @dev Get payment queue
     */
    function getPaymentQueue() external view returns (bytes32[] memory) {
        return paymentQueue;
    }

    /**
     * @dev Get company information
     */
    function getCompanyInfo() external view returns (
        string memory name,
        string memory symbol,
        uint256 marketCap,
        uint256 revenue
    ) {
        return (companyName, stockSymbol, marketCapitalization, annualRevenue);
    }
}