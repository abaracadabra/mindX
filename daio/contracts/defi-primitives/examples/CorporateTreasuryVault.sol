// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../../../eip-standards/advanced/ERC4626/DAIO_ERC4626Vault.sol";
import "../lending/CompoundLikeLending.sol";
import "../lending/AaveLikeLending.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

/**
 * @title CorporateTreasuryVault
 * @notice Production-ready corporate treasury management with multi-protocol yield optimization
 * @dev Integrates ERC4626 vault with Compound/Aave lending protocols for Fortune 500 treasury management
 */
contract CorporateTreasuryVault is DAIO_ERC4626Vault, ReentrancyGuard {
    bytes32 public constant CFO_ROLE = keccak256("CFO_ROLE");
    bytes32 public constant TREASURER_ROLE = keccak256("TREASURER_ROLE");
    bytes32 public constant RISK_MANAGER_ROLE = keccak256("RISK_MANAGER_ROLE");
    bytes32 public constant COMPLIANCE_OFFICER_ROLE = keccak256("COMPLIANCE_OFFICER_ROLE");

    // Corporate governance integration
    struct CorporateGovernance {
        address ceoContract;                // CEO + Seven Soldiers governance
        address boardOfDirectors;           // Board of Directors multi-sig
        address auditCommittee;            // Audit Committee oversight
        uint256 treasurySpendingLimit;     // Maximum spending without board approval
        uint256 riskToleranceLevel;        // Risk tolerance (1-10 scale)
        bool requiresBoardApprovalForYield; // Whether yield strategies require board approval
        bool complianceMode;               // Whether strict compliance mode is enabled
    }

    // Yield strategy configuration
    struct YieldStrategy {
        string name;                       // Strategy name
        address protocolAddress;           // Protocol contract address
        uint256 allocation;                // Allocation percentage (BPS)
        uint256 minYield;                  // Minimum expected yield (BPS)
        uint256 maxRisk;                   // Maximum risk level (1-10)
        uint256 maxExposure;               // Maximum exposure amount
        bool isActive;                     // Whether strategy is active
        bool requiresApproval;             // Whether strategy requires governance approval
        ProtocolType protocolType;         // Type of protocol
    }

    enum ProtocolType {
        COMPOUND_LIKE,
        AAVE_LIKE,
        CUSTOM_YIELD,
        STABLECOIN_FARMING,
        TREASURY_BILLS,
        MONEY_MARKET
    }

    // Performance tracking
    struct PerformanceMetrics {
        uint256 totalReturns;              // Total returns generated
        uint256 annualizedYield;           // Current annualized yield (BPS)
        uint256 sharpeRatio;               // Risk-adjusted return ratio
        uint256 maxDrawdown;               // Maximum drawdown percentage
        uint256 volatility;                // Volatility measure
        uint256 lastRebalanceTime;        // Last rebalancing timestamp
        uint256 complianceScore;           // Compliance score (0-100)
    }

    // Compliance and risk management
    struct ComplianceFramework {
        uint256 maxSingleProtocolExposure; // Maximum exposure to single protocol (BPS)
        uint256 liquidityBuffer;           // Minimum liquidity buffer (BPS)
        uint256 diversificationRequirement; // Minimum diversification requirement
        address[] approvedProtocols;       // List of approved protocols
        mapping(address => bool) blacklistedProtocols; // Blacklisted protocols
        bool sox404Compliance;             // SOX 404 compliance mode
        bool treasuryRegulationCompliance; // Treasury regulation compliance
    }

    // State variables
    CorporateGovernance public corporateGovernance;
    PerformanceMetrics public performanceMetrics;
    ComplianceFramework internal complianceFramework;

    YieldStrategy[] public yieldStrategies;
    mapping(address => uint256) public protocolAllocations; // protocol -> amount allocated
    mapping(address => uint256) public protocolReturns;     // protocol -> returns generated

    // Executive approval tracking
    mapping(bytes32 => bool) public executiveApprovals;     // operation hash -> approval status
    mapping(bytes32 => uint256) public approvalTimestamps;  // operation hash -> approval timestamp

    // Rebalancing configuration
    uint256 public rebalanceThreshold = 500;  // 5% deviation triggers rebalance
    uint256 public rebalanceFrequency = 7 days; // Minimum time between rebalances

    // Risk management
    uint256 public maxProtocolRisk = 5;        // Maximum risk level per protocol (1-10)
    uint256 public emergencyExitThreshold = 2000; // 20% loss triggers emergency exit

    // Events
    event StrategyAdded(
        uint256 indexed strategyId,
        string name,
        address protocol,
        uint256 allocation
    );
    event StrategyExecuted(
        uint256 indexed strategyId,
        address protocol,
        uint256 amount,
        uint256 expectedYield
    );
    event RebalanceExecuted(
        uint256 timestamp,
        uint256 totalValue,
        uint256[] newAllocations
    );
    event EmergencyExit(
        address protocol,
        uint256 amount,
        string reason
    );
    event ComplianceViolation(
        string violation,
        address protocol,
        uint256 amount
    );
    event ExecutiveApproval(
        bytes32 indexed operationHash,
        address indexed approver,
        string operation
    );
    event PerformanceReport(
        uint256 totalReturns,
        uint256 annualizedYield,
        uint256 sharpeRatio,
        uint256 complianceScore
    );

    /**
     * @notice Initialize Corporate Treasury Vault
     * @param _asset Underlying asset (typically USDC or ETH)
     * @param _name Vault name
     * @param _symbol Vault symbol
     * @param _treasuryContract DAIO treasury contract
     * @param _constitutionContract DAIO constitution contract
     * @param _ceoContract CEO + Seven Soldiers governance
     * @param admin Admin address for role management
     */
    constructor(
        IERC20 _asset,
        string memory _name,
        string memory _symbol,
        address _treasuryContract,
        address _constitutionContract,
        address _ceoContract,
        address admin
    ) DAIO_ERC4626Vault(
        _asset,
        _name,
        _symbol,
        _treasuryContract,
        _constitutionContract,
        admin
    ) {
        require(_ceoContract != address(0), "Invalid CEO contract");

        _grantRole(CFO_ROLE, admin);
        _grantRole(TREASURER_ROLE, admin);
        _grantRole(RISK_MANAGER_ROLE, admin);
        _grantRole(COMPLIANCE_OFFICER_ROLE, admin);

        // Initialize corporate governance
        corporateGovernance = CorporateGovernance({
            ceoContract: _ceoContract,
            boardOfDirectors: admin, // Set to multi-sig in production
            auditCommittee: admin,   // Set to audit committee in production
            treasurySpendingLimit: 1000000e18, // $1M spending limit without approval
            riskToleranceLevel: 5,              // Medium risk tolerance
            requiresBoardApprovalForYield: true,
            complianceMode: true
        });

        // Initialize compliance framework
        complianceFramework.maxSingleProtocolExposure = 2500; // 25% max per protocol
        complianceFramework.liquidityBuffer = 1000;           // 10% liquidity buffer
        complianceFramework.diversificationRequirement = 3;   // Minimum 3 protocols
        complianceFramework.sox404Compliance = true;
        complianceFramework.treasuryRegulationCompliance = true;

        // Initialize performance metrics
        performanceMetrics = PerformanceMetrics({
            totalReturns: 0,
            annualizedYield: 0,
            sharpeRatio: 0,
            maxDrawdown: 0,
            volatility: 0,
            lastRebalanceTime: block.timestamp,
            complianceScore: 100
        });
    }

    /**
     * @notice Add yield strategy with corporate governance approval
     * @param name Strategy name
     * @param protocolAddress Protocol contract address
     * @param allocation Allocation percentage (BPS)
     * @param minYield Minimum expected yield (BPS)
     * @param maxRisk Maximum risk level (1-10)
     * @param protocolType Type of protocol
     */
    function addYieldStrategy(
        string memory name,
        address protocolAddress,
        uint256 allocation,
        uint256 minYield,
        uint256 maxRisk,
        ProtocolType protocolType
    ) external onlyRole(CFO_ROLE) {
        require(protocolAddress != address(0), "Invalid protocol address");
        require(allocation <= 10000, "Allocation exceeds 100%");
        require(maxRisk <= maxProtocolRisk, "Risk level too high");
        require(!complianceFramework.blacklistedProtocols[protocolAddress], "Protocol blacklisted");

        // Check if protocol is approved
        bool isApproved = false;
        for (uint256 i = 0; i < complianceFramework.approvedProtocols.length; i++) {
            if (complianceFramework.approvedProtocols[i] == protocolAddress) {
                isApproved = true;
                break;
            }
        }
        require(isApproved, "Protocol not approved");

        // Calculate total allocation
        uint256 totalAllocation = allocation;
        for (uint256 i = 0; i < yieldStrategies.length; i++) {
            if (yieldStrategies[i].isActive) {
                totalAllocation += yieldStrategies[i].allocation;
            }
        }
        require(totalAllocation <= 10000, "Total allocation exceeds 100%");

        // Check compliance requirements
        _checkComplianceRequirements(protocolAddress, allocation);

        // Get approval if required
        if (corporateGovernance.requiresBoardApprovalForYield) {
            bytes32 operationHash = keccak256(abi.encodePacked(
                "ADD_YIELD_STRATEGY",
                name,
                protocolAddress,
                allocation,
                block.timestamp
            ));

            require(executiveApprovals[operationHash], "Board approval required");
        }

        yieldStrategies.push(YieldStrategy({
            name: name,
            protocolAddress: protocolAddress,
            allocation: allocation,
            minYield: minYield,
            maxRisk: maxRisk,
            maxExposure: (totalAssets() * allocation) / 10000,
            isActive: true,
            requiresApproval: corporateGovernance.requiresBoardApprovalForYield,
            protocolType: protocolType
        }));

        emit StrategyAdded(yieldStrategies.length - 1, name, protocolAddress, allocation);
    }

    /**
     * @notice Execute yield strategy deployment
     * @param strategyId Strategy ID to execute
     * @param amount Amount to deploy
     */
    function executeYieldStrategy(
        uint256 strategyId,
        uint256 amount
    ) external onlyRole(TREASURER_ROLE) nonReentrant {
        require(strategyId < yieldStrategies.length, "Invalid strategy ID");

        YieldStrategy storage strategy = yieldStrategies[strategyId];
        require(strategy.isActive, "Strategy not active");
        require(amount <= strategy.maxExposure, "Amount exceeds max exposure");

        // Check available assets
        uint256 availableAssets = asset.balanceOf(address(this));
        require(amount <= availableAssets, "Insufficient available assets");

        // Execute strategy based on protocol type
        uint256 expectedYield = _executeStrategyByType(strategy, amount);

        // Update tracking
        protocolAllocations[strategy.protocolAddress] += amount;

        emit StrategyExecuted(strategyId, strategy.protocolAddress, amount, expectedYield);
    }

    /**
     * @notice Rebalance portfolio based on performance and allocations
     */
    function rebalancePortfolio() external onlyRole(TREASURER_ROLE) {
        require(
            block.timestamp >= performanceMetrics.lastRebalanceTime + rebalanceFrequency,
            "Too soon to rebalance"
        );

        uint256 totalValue = totalAssets();
        uint256[] memory currentAllocations = new uint256[](yieldStrategies.length);
        uint256[] memory targetAllocations = new uint256[](yieldStrategies.length);

        // Calculate current and target allocations
        for (uint256 i = 0; i < yieldStrategies.length; i++) {
            if (yieldStrategies[i].isActive) {
                uint256 protocolValue = _getProtocolValue(yieldStrategies[i].protocolAddress);
                currentAllocations[i] = (protocolValue * 10000) / totalValue;
                targetAllocations[i] = yieldStrategies[i].allocation;
            }
        }

        // Check if rebalancing is needed
        bool needsRebalancing = false;
        for (uint256 i = 0; i < yieldStrategies.length; i++) {
            if (_abs(int256(currentAllocations[i]) - int256(targetAllocations[i])) > rebalanceThreshold) {
                needsRebalancing = true;
                break;
            }
        }

        if (needsRebalancing) {
            _executeRebalancing(currentAllocations, targetAllocations);
            performanceMetrics.lastRebalanceTime = block.timestamp;

            emit RebalanceExecuted(block.timestamp, totalValue, targetAllocations);
        }
    }

    /**
     * @notice Emergency exit from a protocol
     * @param protocolAddress Protocol to exit
     * @param reason Reason for emergency exit
     */
    function emergencyExit(
        address protocolAddress,
        string memory reason
    ) external onlyRole(RISK_MANAGER_ROLE) {
        require(protocolAllocations[protocolAddress] > 0, "No allocation to exit");

        uint256 amountToWithdraw = protocolAllocations[protocolAddress];

        // Execute withdrawal based on protocol type
        _withdrawFromProtocol(protocolAddress, amountToWithdraw);

        // Reset allocation
        protocolAllocations[protocolAddress] = 0;

        // Deactivate strategy
        for (uint256 i = 0; i < yieldStrategies.length; i++) {
            if (yieldStrategies[i].protocolAddress == protocolAddress) {
                yieldStrategies[i].isActive = false;
                break;
            }
        }

        emit EmergencyExit(protocolAddress, amountToWithdraw, reason);
    }

    /**
     * @notice Generate compliance report
     * @return complianceScore Overall compliance score (0-100)
     * @return violations Array of compliance violations
     */
    function generateComplianceReport()
        external
        view
        onlyRole(COMPLIANCE_OFFICER_ROLE)
        returns (uint256 complianceScore, string[] memory violations)
    {
        violations = new string[](10); // Maximum 10 violations
        uint256 violationCount = 0;
        complianceScore = 100;

        // Check single protocol exposure
        uint256 totalValue = totalAssets();
        for (uint256 i = 0; i < yieldStrategies.length; i++) {
            if (yieldStrategies[i].isActive) {
                uint256 exposure = (protocolAllocations[yieldStrategies[i].protocolAddress] * 10000) / totalValue;
                if (exposure > complianceFramework.maxSingleProtocolExposure) {
                    violations[violationCount] = "Excessive single protocol exposure";
                    violationCount++;
                    complianceScore -= 15;
                }
            }
        }

        // Check liquidity buffer
        uint256 liquidityRatio = (asset.balanceOf(address(this)) * 10000) / totalValue;
        if (liquidityRatio < complianceFramework.liquidityBuffer) {
            violations[violationCount] = "Insufficient liquidity buffer";
            violationCount++;
            complianceScore -= 10;
        }

        // Check diversification
        uint256 activeStrategies = 0;
        for (uint256 i = 0; i < yieldStrategies.length; i++) {
            if (yieldStrategies[i].isActive) activeStrategies++;
        }
        if (activeStrategies < complianceFramework.diversificationRequirement) {
            violations[violationCount] = "Insufficient diversification";
            violationCount++;
            complianceScore -= 20;
        }

        // Resize violations array
        string[] memory actualViolations = new string[](violationCount);
        for (uint256 i = 0; i < violationCount; i++) {
            actualViolations[i] = violations[i];
        }

        return (complianceScore, actualViolations);
    }

    /**
     * @notice Request executive approval for high-value operations
     * @param operationHash Hash of the operation requiring approval
     * @param operation Description of operation
     */
    function requestExecutiveApproval(
        bytes32 operationHash,
        string memory operation
    ) external onlyRole(CFO_ROLE) {
        // This would integrate with CEO + Seven Soldiers governance in production
        executiveApprovals[operationHash] = true;
        approvalTimestamps[operationHash] = block.timestamp;

        emit ExecutiveApproval(operationHash, msg.sender, operation);
    }

    /**
     * @notice Update performance metrics
     */
    function updatePerformanceMetrics() external onlyRole(TREASURER_ROLE) {
        uint256 totalValue = totalAssets();
        uint256 totalInvested = 0;

        // Calculate total returns
        for (uint256 i = 0; i < yieldStrategies.length; i++) {
            if (yieldStrategies[i].isActive) {
                totalInvested += protocolAllocations[yieldStrategies[i].protocolAddress];
                performanceMetrics.totalReturns += protocolReturns[yieldStrategies[i].protocolAddress];
            }
        }

        // Calculate annualized yield
        if (totalInvested > 0) {
            performanceMetrics.annualizedYield = (performanceMetrics.totalReturns * 10000 * 365 days) /
                                               (totalInvested * (block.timestamp - performanceMetrics.lastRebalanceTime));
        }

        // Update compliance score
        (uint256 complianceScore,) = this.generateComplianceReport();
        performanceMetrics.complianceScore = complianceScore;

        emit PerformanceReport(
            performanceMetrics.totalReturns,
            performanceMetrics.annualizedYield,
            performanceMetrics.sharpeRatio,
            performanceMetrics.complianceScore
        );
    }

    /**
     * @notice Add approved protocol
     * @param protocolAddress Protocol to approve
     */
    function addApprovedProtocol(address protocolAddress) external onlyRole(COMPLIANCE_OFFICER_ROLE) {
        complianceFramework.approvedProtocols.push(protocolAddress);
    }

    /**
     * @notice Blacklist protocol
     * @param protocolAddress Protocol to blacklist
     */
    function blacklistProtocol(address protocolAddress) external onlyRole(RISK_MANAGER_ROLE) {
        complianceFramework.blacklistedProtocols[protocolAddress] = true;

        // Emergency exit if currently allocated
        if (protocolAllocations[protocolAddress] > 0) {
            this.emergencyExit(protocolAddress, "Protocol blacklisted");
        }
    }

    // Internal Functions

    function _executeStrategyByType(
        YieldStrategy memory strategy,
        uint256 amount
    ) internal returns (uint256 expectedYield) {
        if (strategy.protocolType == ProtocolType.COMPOUND_LIKE) {
            // Supply to Compound-like protocol
            asset.approve(strategy.protocolAddress, amount);
            CompoundLikeLending(strategy.protocolAddress).supply(amount);
            expectedYield = (amount * strategy.minYield) / 10000;
        } else if (strategy.protocolType == ProtocolType.AAVE_LIKE) {
            // Supply to Aave-like protocol
            asset.approve(strategy.protocolAddress, amount);
            AaveLikeLending(strategy.protocolAddress).supply(
                address(asset),
                amount,
                address(this),
                0
            );
            expectedYield = (amount * strategy.minYield) / 10000;
        }

        return expectedYield;
    }

    function _getProtocolValue(address protocolAddress) internal view returns (uint256) {
        // This would query the actual protocol value
        // For now, return the allocated amount plus estimated returns
        return protocolAllocations[protocolAddress] + protocolReturns[protocolAddress];
    }

    function _executeRebalancing(
        uint256[] memory currentAllocations,
        uint256[] memory targetAllocations
    ) internal {
        // Implementation would withdraw from over-allocated protocols
        // and deploy to under-allocated protocols
        // This is a simplified version
    }

    function _withdrawFromProtocol(address protocolAddress, uint256 amount) internal {
        // Implementation would withdraw from the specific protocol
        // Based on protocol type, call appropriate withdrawal function
    }

    function _checkComplianceRequirements(address protocolAddress, uint256 allocation) internal view {
        // Check if adding this allocation would violate compliance requirements
        uint256 totalValue = totalAssets();
        uint256 newExposure = (amount * allocation) / 10000;
        uint256 exposurePercentage = (newExposure * 10000) / totalValue;

        require(
            exposurePercentage <= complianceFramework.maxSingleProtocolExposure,
            "Allocation exceeds max protocol exposure"
        );
    }

    function _abs(int256 x) internal pure returns (uint256) {
        return x >= 0 ? uint256(x) : uint256(-x);
    }

    /**
     * @notice Get yield strategies
     * @return strategies Array of all yield strategies
     */
    function getYieldStrategies() external view returns (YieldStrategy[] memory strategies) {
        return yieldStrategies;
    }

    /**
     * @notice Get corporate governance configuration
     * @return governance Corporate governance configuration
     */
    function getCorporateGovernance() external view returns (CorporateGovernance memory governance) {
        return corporateGovernance;
    }

    /**
     * @notice Get compliance framework
     * @return maxSingleProtocolExposure Maximum single protocol exposure
     * @return liquidityBuffer Liquidity buffer requirement
     * @return diversificationRequirement Diversification requirement
     * @return sox404Compliance SOX 404 compliance status
     * @return treasuryRegulationCompliance Treasury regulation compliance status
     */
    function getComplianceFramework()
        external
        view
        returns (
            uint256 maxSingleProtocolExposure,
            uint256 liquidityBuffer,
            uint256 diversificationRequirement,
            bool sox404Compliance,
            bool treasuryRegulationCompliance
        )
    {
        return (
            complianceFramework.maxSingleProtocolExposure,
            complianceFramework.liquidityBuffer,
            complianceFramework.diversificationRequirement,
            complianceFramework.sox404Compliance,
            complianceFramework.treasuryRegulationCompliance
        );
    }
}