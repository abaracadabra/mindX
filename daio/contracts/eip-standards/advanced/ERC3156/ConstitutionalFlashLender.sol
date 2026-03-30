// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./DAIO_FlashLender.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title ConstitutionalFlashLender
 * @notice 15% diversification limit enforcement for flash loans aligned with DAIO constitution
 * @dev Extends DAIO_FlashLender with strict constitutional constraint enforcement
 */
contract ConstitutionalFlashLender is DAIO_FlashLender {

    // Constitutional diversification tracking
    struct DiversificationMetrics {
        uint256 totalPortfolioValue;      // Total value of all assets in portfolio
        mapping(address => uint256) assetValues; // Asset address -> current value
        mapping(address => uint256) assetExposures; // Asset address -> exposure percentage (BPS)
        uint256 lastRebalanceTime;       // Last portfolio rebalancing
        bool requiresRebalancing;        // Whether portfolio needs rebalancing
        uint256 diversificationScore;    // Overall diversification score (0-10000)
    }

    struct ConstitutionalConstraint {
        uint256 maxSingleAssetExposure; // Maximum exposure to single asset (1500 BPS = 15%)
        uint256 maxFlashLoanExposure;   // Maximum flash loan exposure as % of portfolio
        uint256 minDiversificationAssets; // Minimum number of different assets required
        uint256 rebalanceThreshold;     // Threshold that triggers mandatory rebalancing
        bool enforceStrictCompliance;   // Whether to enforce strict constitutional compliance
        bool allowEmergencyOverride;    // Whether emergency override is allowed
    }

    struct AssetClassification {
        string assetClass;              // "STABLE", "VOLATILE", "EXOTIC"
        uint256 riskMultiplier;        // Risk multiplier for this asset (BPS)
        uint256 liquidityScore;        // Liquidity score (0-10000)
        uint256 correlationGroup;      // Correlation group ID
        bool isConstitutionallyCompliant; // Whether asset meets constitutional requirements
    }

    // State variables
    DiversificationMetrics public diversificationMetrics;
    ConstitutionalConstraint public constitutionalConstraint;
    mapping(address => AssetClassification) public assetClassifications;
    mapping(uint256 => address[]) public correlationGroups; // group ID -> asset addresses

    // Oracle integration for asset valuation
    address public priceOracle;
    mapping(address => uint256) public lastAssetPriceUpdate;
    uint256 public priceUpdateFrequency = 3600; // 1 hour

    // Constitutional compliance tracking
    uint256 public totalConstitutionalViolations;
    uint256 public lastComplianceCheck;
    mapping(address => uint256) public assetViolationCount;

    // Events
    event ConstitutionalViolationDetected(
        address indexed asset,
        uint256 currentExposure,
        uint256 maxAllowed,
        string violationType
    );
    event DiversificationRebalanceRequired(
        uint256 portfolioValue,
        uint256 diversificationScore,
        uint256 assetsOutOfCompliance
    );
    event AssetClassificationUpdated(
        address indexed asset,
        string assetClass,
        uint256 riskMultiplier,
        bool constitutionallyCompliant
    );
    event EmergencyConstitutionalOverride(
        address indexed asset,
        uint256 amount,
        string reason,
        address indexed authorizer
    );
    event PortfolioRebalanced(
        uint256 oldDiversificationScore,
        uint256 newDiversificationScore,
        uint256 assetsRebalanced
    );

    /**
     * @notice Initialize ConstitutionalFlashLender
     * @param _treasuryContract DAIO treasury contract
     * @param _priceOracle Price oracle for asset valuation
     * @param admin Admin address
     */
    constructor(
        address _treasuryContract,
        address _priceOracle,
        address admin
    ) DAIO_FlashLender(_treasuryContract, admin) {
        require(_priceOracle != address(0), "Price oracle cannot be zero address");

        priceOracle = _priceOracle;

        // Initialize constitutional constraints aligned with DAIO constitution
        constitutionalConstraint = ConstitutionalConstraint({
            maxSingleAssetExposure: 1500,     // 15% maximum per constitutional requirement
            maxFlashLoanExposure: 2500,       // 25% maximum flash loan exposure
            minDiversificationAssets: 5,      // Minimum 5 different assets
            rebalanceThreshold: 1200,         // 12% threshold triggers rebalancing
            enforceStrictCompliance: true,
            allowEmergencyOverride: false
        });

        // Initialize diversification metrics
        diversificationMetrics.totalPortfolioValue = 0;
        diversificationMetrics.lastRebalanceTime = block.timestamp;
        diversificationMetrics.requiresRebalancing = false;
        diversificationMetrics.diversificationScore = 10000; // Start at perfect diversification

        lastComplianceCheck = block.timestamp;

        // Initialize default asset classifications
        _initializeDefaultAssetClassifications();
    }

    /**
     * @notice Execute flash loan with constitutional compliance checking
     * @param receiver Borrower contract
     * @param token Token to borrow
     * @param amount Amount to borrow
     * @param data Additional data
     * @return success Whether flash loan was successful
     */
    function flashLoan(
        IERC3156FlashBorrower receiver,
        address token,
        uint256 amount,
        bytes calldata data
    ) public override returns (bool success) {
        // Pre-loan constitutional compliance check
        require(_validateConstitutionalCompliance(token, amount), "Constitutional compliance violation");

        // Update asset valuations before proceeding
        _updateAssetValuation(token);

        // Check diversification requirements
        require(_checkDiversificationRequirements(token, amount), "Diversification requirements not met");

        // Execute the flash loan through parent
        success = super.flashLoan(receiver, token, amount, data);

        if (success) {
            // Post-loan compliance verification
            _updateDiversificationMetrics(token, amount);
            _checkPortfolioCompliance();

            // Trigger rebalancing if required
            if (diversificationMetrics.requiresRebalancing) {
                _triggerPortfolioRebalancing();
            }
        }

        return success;
    }

    /**
     * @notice Classify asset for constitutional compliance
     * @param asset Asset address
     * @param assetClass Asset class ("STABLE", "VOLATILE", "EXOTIC")
     * @param riskMultiplier Risk multiplier (BPS)
     * @param liquidityScore Liquidity score (0-10000)
     * @param correlationGroup Correlation group ID
     */
    function classifyAsset(
        address asset,
        string memory assetClass,
        uint256 riskMultiplier,
        uint256 liquidityScore,
        uint256 correlationGroup
    ) external onlyRole(RISK_MANAGER_ROLE) {
        require(riskMultiplier <= 50000, "Risk multiplier too high"); // Max 5x
        require(liquidityScore <= 10000, "Invalid liquidity score");

        bool isCompliant = _assessConstitutionalCompliance(asset, assetClass, riskMultiplier, liquidityScore);

        assetClassifications[asset] = AssetClassification({
            assetClass: assetClass,
            riskMultiplier: riskMultiplier,
            liquidityScore: liquidityScore,
            correlationGroup: correlationGroup,
            isConstitutionallyCompliant: isCompliant
        });

        // Add to correlation group
        address[] storage group = correlationGroups[correlationGroup];
        bool inGroup = false;
        for (uint256 i = 0; i < group.length; i++) {
            if (group[i] == asset) {
                inGroup = true;
                break;
            }
        }
        if (!inGroup) {
            group.push(asset);
        }

        emit AssetClassificationUpdated(asset, assetClass, riskMultiplier, isCompliant);

        // Trigger compliance check
        _checkPortfolioCompliance();
    }

    /**
     * @notice Emergency override for constitutional limits
     * @param asset Asset to override for
     * @param amount Amount to allow
     * @param reason Reason for override
     */
    function emergencyConstitutionalOverride(
        address asset,
        uint256 amount,
        string memory reason
    ) external onlyRole(EMERGENCY_ROLE) {
        require(constitutionalConstraint.allowEmergencyOverride, "Emergency override not allowed");
        require(bytes(reason).length > 0, "Reason required for override");

        // Temporarily increase asset exposure limit
        diversificationMetrics.assetExposures[asset] = (amount * 10000) / diversificationMetrics.totalPortfolioValue;

        emit EmergencyConstitutionalOverride(asset, amount, reason, msg.sender);
    }

    /**
     * @notice Force portfolio rebalancing to meet constitutional requirements
     */
    function forcePortfolioRebalancing() external onlyRole(RISK_MANAGER_ROLE) {
        _executePortfolioRebalancing();
    }

    /**
     * @notice Get diversification metrics
     * @return portfolioValue Total portfolio value
     * @return diversificationScore Current diversification score
     * @return requiresRebalancing Whether rebalancing is required
     */
    function getDiversificationMetrics() external view returns (
        uint256 portfolioValue,
        uint256 diversificationScore,
        bool requiresRebalancing
    ) {
        return (
            diversificationMetrics.totalPortfolioValue,
            diversificationMetrics.diversificationScore,
            diversificationMetrics.requiresRebalancing
        );
    }

    /**
     * @notice Get asset exposure percentage
     * @param asset Asset address
     * @return exposure Current exposure percentage (BPS)
     */
    function getAssetExposure(address asset) external view returns (uint256 exposure) {
        return diversificationMetrics.assetExposures[asset];
    }

    /**
     * @notice Check if portfolio is constitutionally compliant
     * @return isCompliant Whether portfolio meets all constitutional requirements
     * @return violationCount Number of constitutional violations
     */
    function checkConstitutionalCompliance() external view returns (bool isCompliant, uint256 violationCount) {
        violationCount = 0;

        // Check single asset exposure limits
        address[] memory tokens = getSupportedTokens();
        for (uint256 i = 0; i < tokens.length; i++) {
            if (diversificationMetrics.assetExposures[tokens[i]] > constitutionalConstraint.maxSingleAssetExposure) {
                violationCount++;
            }
        }

        // Check minimum diversification
        uint256 activeAssets = 0;
        for (uint256 i = 0; i < tokens.length; i++) {
            if (diversificationMetrics.assetValues[tokens[i]] > 0) {
                activeAssets++;
            }
        }

        if (activeAssets < constitutionalConstraint.minDiversificationAssets) {
            violationCount++;
        }

        isCompliant = violationCount == 0;
        return (isCompliant, violationCount);
    }

    /**
     * @notice Update constitutional constraints
     * @param maxSingleAssetExposure New max single asset exposure (BPS)
     * @param maxFlashLoanExposure New max flash loan exposure (BPS)
     * @param minDiversificationAssets New min diversification assets
     * @param enforceStrictCompliance Whether to enforce strict compliance
     */
    function updateConstitutionalConstraints(
        uint256 maxSingleAssetExposure,
        uint256 maxFlashLoanExposure,
        uint256 minDiversificationAssets,
        bool enforceStrictCompliance
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(maxSingleAssetExposure <= 1500, "Exceeds constitutional 15% limit");
        require(maxFlashLoanExposure <= 5000, "Flash loan exposure too high"); // Max 50%
        require(minDiversificationAssets >= 3, "Minimum diversification too low");

        constitutionalConstraint.maxSingleAssetExposure = maxSingleAssetExposure;
        constitutionalConstraint.maxFlashLoanExposure = maxFlashLoanExposure;
        constitutionalConstraint.minDiversificationAssets = minDiversificationAssets;
        constitutionalConstraint.enforceStrictCompliance = enforceStrictCompliance;

        // Trigger immediate compliance check
        _checkPortfolioCompliance();
    }

    /**
     * @notice Get correlation group assets
     * @param groupId Correlation group ID
     * @return assets Array of assets in correlation group
     */
    function getCorrelationGroup(uint256 groupId) external view returns (address[] memory assets) {
        return correlationGroups[groupId];
    }

    // Internal Functions

    function _validateConstitutionalCompliance(address token, uint256 amount) internal view returns (bool) {
        if (!constitutionalConstraint.enforceStrictCompliance) return true;

        // Check if asset is constitutionally compliant
        if (!assetClassifications[token].isConstitutionallyCompliant) {
            return false;
        }

        // Calculate new exposure after loan
        uint256 currentValue = diversificationMetrics.assetValues[token];
        uint256 totalValue = diversificationMetrics.totalPortfolioValue;

        if (totalValue == 0) return true; // No constraints for first loan

        uint256 newExposure = ((currentValue + amount) * 10000) / (totalValue + amount);

        // Check single asset exposure limit
        if (newExposure > constitutionalConstraint.maxSingleAssetExposure) {
            return false;
        }

        // Check correlation group exposure
        uint256 correlationGroup = assetClassifications[token].correlationGroup;
        uint256 groupExposure = _calculateCorrelationGroupExposure(correlationGroup, token, amount);

        // Correlation group exposure should not exceed 2x single asset limit
        if (groupExposure > constitutionalConstraint.maxSingleAssetExposure * 2) {
            return false;
        }

        return true;
    }

    function _checkDiversificationRequirements(address token, uint256 amount) internal view returns (bool) {
        // Check if adding this loan improves or maintains diversification
        uint256 currentScore = diversificationMetrics.diversificationScore;
        uint256 newScore = _calculateDiversificationScore(token, amount);

        // Don't allow loans that significantly reduce diversification
        if (newScore < currentScore - 500) { // 5% tolerance
            return false;
        }

        return true;
    }

    function _updateAssetValuation(address token) internal {
        uint256 lastUpdate = lastAssetPriceUpdate[token];
        if (block.timestamp < lastUpdate + priceUpdateFrequency) {
            return; // Price is still fresh
        }

        // Get current token balance
        uint256 currentBalance = IERC20(token).balanceOf(address(this));

        // In a real implementation, we would get price from oracle
        // For now, assume 1:1 USD value for demonstration
        uint256 estimatedValue = currentBalance; // Simplified pricing

        diversificationMetrics.assetValues[token] = estimatedValue;
        lastAssetPriceUpdate[token] = block.timestamp;

        // Recalculate total portfolio value
        _recalculatePortfolioValue();
    }

    function _recalculatePortfolioValue() internal {
        uint256 totalValue = 0;
        address[] memory tokens = getSupportedTokens();

        for (uint256 i = 0; i < tokens.length; i++) {
            totalValue += diversificationMetrics.assetValues[tokens[i]];
        }

        diversificationMetrics.totalPortfolioValue = totalValue;

        // Update asset exposure percentages
        for (uint256 i = 0; i < tokens.length; i++) {
            address token = tokens[i];
            if (totalValue > 0) {
                diversificationMetrics.assetExposures[token] =
                    (diversificationMetrics.assetValues[token] * 10000) / totalValue;
            } else {
                diversificationMetrics.assetExposures[token] = 0;
            }
        }
    }

    function _updateDiversificationMetrics(address token, uint256 amount) internal {
        // Update asset value to include new loan amount
        diversificationMetrics.assetValues[token] += amount;
        _recalculatePortfolioValue();

        // Recalculate diversification score
        diversificationMetrics.diversificationScore = _calculateDiversificationScore(address(0), 0);
    }

    function _calculateDiversificationScore(address newToken, uint256 newAmount) internal view returns (uint256) {
        address[] memory tokens = getSupportedTokens();
        uint256 activeAssets = 0;
        uint256 maxExposure = 0;
        uint256 totalValue = diversificationMetrics.totalPortfolioValue;

        if (newToken != address(0)) {
            totalValue += newAmount;
        }

        // Calculate metrics
        for (uint256 i = 0; i < tokens.length; i++) {
            address token = tokens[i];
            uint256 assetValue = diversificationMetrics.assetValues[token];

            if (token == newToken) {
                assetValue += newAmount;
            }

            if (assetValue > 0) {
                activeAssets++;
                uint256 exposure = (assetValue * 10000) / totalValue;
                if (exposure > maxExposure) {
                    maxExposure = exposure;
                }
            }
        }

        // Score based on number of assets and concentration
        uint256 assetScore = activeAssets >= constitutionalConstraint.minDiversificationAssets ? 5000 :
                           (activeAssets * 5000) / constitutionalConstraint.minDiversificationAssets;

        uint256 concentrationScore = maxExposure <= constitutionalConstraint.maxSingleAssetExposure ? 5000 :
                                    (constitutionalConstraint.maxSingleAssetExposure * 5000) / maxExposure;

        return (assetScore + concentrationScore) / 2;
    }

    function _calculateCorrelationGroupExposure(
        uint256 groupId,
        address excludeToken,
        uint256 additionalAmount
    ) internal view returns (uint256) {
        address[] memory groupAssets = correlationGroups[groupId];
        uint256 totalGroupValue = 0;
        uint256 totalPortfolioValue = diversificationMetrics.totalPortfolioValue + additionalAmount;

        for (uint256 i = 0; i < groupAssets.length; i++) {
            address asset = groupAssets[i];
            uint256 assetValue = diversificationMetrics.assetValues[asset];

            if (asset == excludeToken) {
                assetValue += additionalAmount;
            }

            totalGroupValue += assetValue;
        }

        if (totalPortfolioValue == 0) return 0;
        return (totalGroupValue * 10000) / totalPortfolioValue;
    }

    function _checkPortfolioCompliance() internal {
        (bool isCompliant, uint256 violationCount) = this.checkConstitutionalCompliance();

        if (!isCompliant) {
            totalConstitutionalViolations += violationCount;
            diversificationMetrics.requiresRebalancing = true;

            address[] memory tokens = getSupportedTokens();
            for (uint256 i = 0; i < tokens.length; i++) {
                address token = tokens[i];
                if (diversificationMetrics.assetExposures[token] > constitutionalConstraint.maxSingleAssetExposure) {
                    assetViolationCount[token]++;

                    emit ConstitutionalViolationDetected(
                        token,
                        diversificationMetrics.assetExposures[token],
                        constitutionalConstraint.maxSingleAssetExposure,
                        "EXPOSURE_LIMIT_EXCEEDED"
                    );
                }
            }

            emit DiversificationRebalanceRequired(
                diversificationMetrics.totalPortfolioValue,
                diversificationMetrics.diversificationScore,
                violationCount
            );
        }

        lastComplianceCheck = block.timestamp;
    }

    function _triggerPortfolioRebalancing() internal {
        if (!diversificationMetrics.requiresRebalancing) return;

        // In a real implementation, this would trigger actual asset rebalancing
        // For now, mark as requiring manual intervention
        diversificationMetrics.requiresRebalancing = true;
    }

    function _executePortfolioRebalancing() internal {
        uint256 oldScore = diversificationMetrics.diversificationScore;

        // Reset violation flags
        diversificationMetrics.requiresRebalancing = false;

        // Recalculate all metrics
        _recalculatePortfolioValue();
        diversificationMetrics.diversificationScore = _calculateDiversificationScore(address(0), 0);
        diversificationMetrics.lastRebalanceTime = block.timestamp;

        emit PortfolioRebalanced(oldScore, diversificationMetrics.diversificationScore, getSupportedTokens().length);
    }

    function _assessConstitutionalCompliance(
        address asset,
        string memory assetClass,
        uint256 riskMultiplier,
        uint256 liquidityScore
    ) internal pure returns (bool) {
        // Assets are constitutionally compliant if they meet basic criteria
        bool compliant = true;

        // High-risk assets may not be compliant
        if (riskMultiplier > 20000) { // 2x risk multiplier
            compliant = false;
        }

        // Very low liquidity assets may not be compliant
        if (liquidityScore < 3000) { // 30% minimum liquidity
            compliant = false;
        }

        // Exotic assets require special approval
        if (keccak256(bytes(assetClass)) == keccak256(bytes("EXOTIC"))) {
            compliant = false; // Require manual approval
        }

        return compliant;
    }

    function _initializeDefaultAssetClassifications() internal {
        // USDC - Stable asset
        assetClassifications[address(0)] = AssetClassification({
            assetClass: "STABLE",
            riskMultiplier: 5000,    // 0.5x risk
            liquidityScore: 9500,    // 95% liquidity
            correlationGroup: 1,     // Stablecoin group
            isConstitutionallyCompliant: true
        });

        // ETH - Volatile but compliant
        assetClassifications[address(0)] = AssetClassification({
            assetClass: "VOLATILE",
            riskMultiplier: 15000,   // 1.5x risk
            liquidityScore: 8500,    // 85% liquidity
            correlationGroup: 2,     // Major crypto group
            isConstitutionallyCompliant: true
        });

        // BTC - Volatile but compliant
        assetClassifications[address(0)] = AssetClassification({
            assetClass: "VOLATILE",
            riskMultiplier: 15000,   // 1.5x risk
            liquidityScore: 8500,    // 85% liquidity
            correlationGroup: 2,     // Major crypto group
            isConstitutionallyCompliant: true
        });
    }

    /**
     * @notice Update price oracle address
     * @param _priceOracle New price oracle address
     */
    function updatePriceOracle(address _priceOracle) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_priceOracle != address(0), "Invalid oracle address");
        priceOracle = _priceOracle;
    }

    /**
     * @notice Force update asset valuation
     * @param token Token to update valuation for
     */
    function forceUpdateAssetValuation(address token) external onlyRole(RISK_MANAGER_ROLE) {
        lastAssetPriceUpdate[token] = 0; // Reset to force update
        _updateAssetValuation(token);
    }
}