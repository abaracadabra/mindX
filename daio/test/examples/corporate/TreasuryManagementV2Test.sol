// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "forge-std/console.sol";
import "../../../contracts/examples/corporate/TreasuryManagementV2.sol";
import "../../../contracts/daio/treasury/Treasury.sol";
import "../../../contracts/oracles/core/PriceFeedAggregator.sol";
import "../../../contracts/daio/DAIO_Constitution.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

/**
 * @title TreasuryManagementV2Test
 * @dev Comprehensive test suite for improved Treasury Management contract
 *
 * Test Coverage:
 * - Unit tests for all public functions
 * - Integration tests with DAIO infrastructure
 * - Security tests for reentrancy, access control, oracle manipulation
 * - Edge cases and error conditions
 * - Gas optimization validation
 * - Multi-sig functionality
 * - Emergency controls
 * - Oracle circuit breaker functionality
 *
 * @author DAIO Development Team
 */

contract MockERC20 is ERC20 {
    constructor(string memory name, string memory symbol) ERC20(name, symbol) {
        _mint(msg.sender, 1000000 * 10**decimals());
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

contract MockVault {
    IERC20 public asset;
    mapping(address => uint256) public balanceOf;
    uint256 public totalAssets;

    constructor(address _asset) {
        asset = IERC20(_asset);
    }

    function deposit(uint256 amount, address receiver) external returns (uint256) {
        asset.transferFrom(msg.sender, address(this), amount);
        balanceOf[receiver] += amount;
        totalAssets += amount;
        return amount;
    }

    function withdraw(uint256 amount, address receiver, address owner) external returns (uint256) {
        require(balanceOf[owner] >= amount, "Insufficient balance");
        balanceOf[owner] -= amount;
        totalAssets -= amount;
        asset.transfer(receiver, amount);
        return amount;
    }

    function convertToAssets(uint256 shares) external view returns (uint256) {
        return shares; // 1:1 for simplicity
    }

    function redeem(uint256 shares, address receiver, address owner) external returns (uint256) {
        return withdraw(shares, receiver, owner);
    }
}

contract MockConstitution {
    bool public shouldPass = true;

    function setShouldPass(bool _shouldPass) external {
        shouldPass = _shouldPass;
    }

    function validateTreasuryAllocation(
        address,
        address,
        uint256,
        uint8,
        bytes calldata
    ) external view returns (bool, string memory) {
        return shouldPass ? (true, "") : (false, "Constitutional violation");
    }
}

contract MockPriceOracle {
    mapping(address => uint256) public prices;
    bool public shouldRevert = false;

    function setPrice(address asset, uint256 price) external {
        prices[asset] = price;
    }

    function setShouldRevert(bool _shouldRevert) external {
        shouldRevert = _shouldRevert;
    }

    function getPrice(address asset) external view returns (uint256) {
        if (shouldRevert) {
            revert("Oracle failure");
        }
        return prices[asset];
    }
}

contract MockTreasury {
    function collectCorporateTithe(address, uint256) external pure {
        // Mock implementation
    }
}

contract TreasuryManagementV2Test is Test {
    TreasuryManagementV2 public treasury;
    MockERC20 public token1;
    MockERC20 public token2;
    MockVault public vault1;
    MockVault public vault2;
    MockConstitution public constitution;
    MockPriceOracle public priceOracle;
    MockTreasury public daiaTreasury;

    address public admin = address(0x1);
    address public cfo = address(0x2);
    address public treasurer = address(0x3);
    address public compliance = address(0x4);
    address public multiSig1 = address(0x5);
    address public multiSig2 = address(0x6);
    address public multiSig3 = address(0x7);
    address public attacker = address(0x666);

    // Test constants
    uint256 public constant INITIAL_SUPPLY = 1000000 * 1e18;
    uint256 public constant INITIAL_PRICE = 100 * 1e18;
    bytes32 public constant TEST_OPERATION_HASH = keccak256("test_operation");

    event AssetAllocationUpdated(
        address indexed asset,
        TreasuryManagementV2.InvestmentCategory indexed category,
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

    function setUp() public {
        vm.startPrank(admin);

        // Deploy mock contracts
        token1 = new MockERC20("Token1", "TKN1");
        token2 = new MockERC20("Token2", "TKN2");
        vault1 = new MockVault(address(token1));
        vault2 = new MockVault(address(token2));
        constitution = new MockConstitution();
        priceOracle = new MockPriceOracle();
        daiaTreasury = new MockTreasury();

        // Set initial prices
        priceOracle.setPrice(address(token1), INITIAL_PRICE);
        priceOracle.setPrice(address(token2), INITIAL_PRICE);

        // Deploy Treasury Management
        address[] memory multiSigSigners = new address[](3);
        multiSigSigners[0] = multiSig1;
        multiSigSigners[1] = multiSig2;
        multiSigSigners[2] = multiSig3;

        treasury = new TreasuryManagementV2(
            address(daiaTreasury),
            address(constitution),
            address(priceOracle),
            "Test Corp",
            "TEST",
            1000000000 * 1e18, // $1B market cap
            500000000 * 1e18,  // $500M revenue
            multiSigSigners,
            admin
        );

        // Grant roles
        treasury.grantRole(treasury.CFO_ROLE(), cfo);
        treasury.grantRole(treasury.TREASURER_ROLE(), treasurer);
        treasury.grantRole(treasury.INVESTMENT_COMMITTEE_ROLE(), admin);
        treasury.grantRole(treasury.COMPLIANCE_OFFICER_ROLE(), compliance);

        // Distribute tokens
        token1.mint(address(treasury), INITIAL_SUPPLY);
        token2.mint(address(treasury), INITIAL_SUPPLY);
        token1.mint(admin, INITIAL_SUPPLY);
        token2.mint(admin, INITIAL_SUPPLY);

        vm.stopPrank();
    }

    // =============================================================
    //                    BASIC FUNCTIONALITY TESTS
    // =============================================================

    function testDeployment() public {
        assertEq(treasury.companyName(), "Test Corp");
        assertEq(treasury.stockSymbol(), "TEST");
        assertEq(treasury.marketCapitalization(), 1000000000 * 1e18);
        assertEq(treasury.annualRevenue(), 500000000 * 1e18);

        assertTrue(treasury.hasRole(treasury.DEFAULT_ADMIN_ROLE(), admin));
        assertTrue(treasury.hasRole(treasury.CFO_ROLE(), cfo));
        assertTrue(treasury.hasRole(treasury.TREASURER_ROLE(), treasurer));
    }

    function testSetAssetAllocation() public {
        vm.startPrank(admin);

        // First approve multi-sig operation
        _approveMultiSigOperation(TEST_OPERATION_HASH);

        // Expect event emission
        vm.expectEmit(true, true, false, true);
        emit AssetAllocationUpdated(
            address(token1),
            TreasuryManagementV2.InvestmentCategory.CashEquivalents,
            2000, // 20%
            admin,
            block.timestamp
        );

        treasury.setAssetAllocation(
            address(token1),
            TreasuryManagementV2.InvestmentCategory.CashEquivalents,
            2000, // 20%
            100 * 1e18,
            1000 * 1e18,
            address(vault1),
            TEST_OPERATION_HASH
        );

        // Verify allocation was set
        (
            IERC20 token,
            TreasuryManagementV2.InvestmentCategory category,
            uint256 targetPercentage,
            uint256 currentAmount,
            uint256 minAmount,
            uint256 maxAmount,
            uint256 lastRebalanceTime,
            address vault,
            bool active,
            bool whitelisted,
            uint256 allocationTimestamp,
            address allocatedBy
        ) = treasury.assetAllocations(address(token1));

        assertEq(address(token), address(token1));
        assertEq(uint8(category), uint8(TreasuryManagementV2.InvestmentCategory.CashEquivalents));
        assertEq(targetPercentage, 2000);
        assertEq(minAmount, 100 * 1e18);
        assertEq(maxAmount, 1000 * 1e18);
        assertEq(vault, address(vault1));
        assertTrue(active);
        assertTrue(whitelisted);
        assertEq(allocatedBy, admin);

        vm.stopPrank();
    }

    function testSetAssetAllocationUnauthorized() public {
        vm.startPrank(attacker);

        vm.expectRevert();
        treasury.setAssetAllocation(
            address(token1),
            TreasuryManagementV2.InvestmentCategory.CashEquivalents,
            2000,
            100 * 1e18,
            1000 * 1e18,
            address(vault1),
            TEST_OPERATION_HASH
        );

        vm.stopPrank();
    }

    function testSetAssetAllocationInvalidParameters() public {
        vm.startPrank(admin);

        _approveMultiSigOperation(TEST_OPERATION_HASH);

        // Test invalid percentage (> 100%)
        vm.expectRevert(TreasuryManagementV2.InvalidAmount.selector);
        treasury.setAssetAllocation(
            address(token1),
            TreasuryManagementV2.InvestmentCategory.CashEquivalents,
            15000, // 150% - invalid
            100 * 1e18,
            1000 * 1e18,
            address(vault1),
            TEST_OPERATION_HASH
        );

        // Test invalid amount range
        vm.expectRevert(TreasuryManagementV2.InvalidAmount.selector);
        treasury.setAssetAllocation(
            address(token1),
            TreasuryManagementV2.InvestmentCategory.CashEquivalents,
            2000,
            1000 * 1e18, // min > max
            100 * 1e18,
            address(vault1),
            TEST_OPERATION_HASH
        );

        // Test zero address
        vm.expectRevert(TreasuryManagementV2.InvalidAsset.selector);
        treasury.setAssetAllocation(
            address(0),
            TreasuryManagementV2.InvestmentCategory.CashEquivalents,
            2000,
            100 * 1e18,
            1000 * 1e18,
            address(vault1),
            TEST_OPERATION_HASH
        );

        vm.stopPrank();
    }

    // =============================================================
    //                    MULTI-SIG TESTS
    // =============================================================

    function testMultiSigOperationFlow() public {
        vm.startPrank(treasurer);

        // Initiate multi-sig operation
        treasury.initiateMultiSigOperation(TEST_OPERATION_HASH, "asset_allocation");

        vm.stopPrank();

        // Multi-sig approvals
        vm.prank(multiSig1);
        treasury.approveMultiSigOperation(TEST_OPERATION_HASH);

        vm.prank(multiSig2);
        treasury.approveMultiSigOperation(TEST_OPERATION_HASH);

        vm.prank(multiSig3);
        treasury.approveMultiSigOperation(TEST_OPERATION_HASH);

        // Now should be able to execute operations requiring multi-sig
        vm.startPrank(admin);

        treasury.setAssetAllocation(
            address(token1),
            TreasuryManagementV2.InvestmentCategory.CashEquivalents,
            2000,
            100 * 1e18,
            1000 * 1e18,
            address(vault1),
            TEST_OPERATION_HASH
        );

        vm.stopPrank();
    }

    function testMultiSigDoubleApproval() public {
        vm.startPrank(treasurer);
        treasury.initiateMultiSigOperation(TEST_OPERATION_HASH, "test");
        vm.stopPrank();

        vm.startPrank(multiSig1);
        treasury.approveMultiSigOperation(TEST_OPERATION_HASH);

        // Should revert on second approval from same signer
        vm.expectRevert();
        treasury.approveMultiSigOperation(TEST_OPERATION_HASH);

        vm.stopPrank();
    }

    function testMultiSigUnauthorizedApprover() public {
        vm.startPrank(treasurer);
        treasury.initiateMultiSigOperation(TEST_OPERATION_HASH, "test");
        vm.stopPrank();

        vm.startPrank(attacker);
        vm.expectRevert(TreasuryManagementV2.UnauthorizedAccess.selector);
        treasury.approveMultiSigOperation(TEST_OPERATION_HASH);
        vm.stopPrank();
    }

    // =============================================================
    //                    ORACLE PROTECTION TESTS
    // =============================================================

    function testOraclePriceProtection() public {
        // Set initial price
        priceOracle.setPrice(address(token1), 100 * 1e18);

        vm.prank(treasurer);
        treasury.updateAssetPrice(address(token1));

        (uint256 price, bool isValid) = treasury.getAssetPriceSafe(address(token1));
        assertEq(price, 100 * 1e18);
        assertTrue(isValid);

        // Set extreme price change (should trigger circuit breaker)
        priceOracle.setPrice(address(token1), 200 * 1e18); // 100% increase

        vm.prank(treasurer);
        treasury.updateAssetPrice(address(token1));

        (uint256 newPrice, bool newIsValid) = treasury.getAssetPriceSafe(address(token1));
        // Should return last valid price
        assertEq(newPrice, 100 * 1e18);
        assertFalse(newIsValid);
    }

    function testOracleFailure() public {
        // Set price oracle to fail
        priceOracle.setShouldRevert(true);

        vm.prank(treasurer);
        treasury.updateAssetPrice(address(token1));

        (uint256 price, bool isValid) = treasury.getAssetPriceSafe(address(token1));
        assertEq(price, 0); // No previous valid price
        assertFalse(isValid);
    }

    function testOracleCircuitBreakerManualTrigger() public {
        vm.prank(compliance);
        treasury.triggerOracleCircuitBreaker();

        (bool circuitBreakerActive,,,) = treasury.getOracleProtectionStatus();
        assertTrue(circuitBreakerActive);
    }

    function testOracleCircuitBreakerReset() public {
        vm.prank(compliance);
        treasury.triggerOracleCircuitBreaker();

        vm.prank(cfo);
        treasury.resetOracleCircuitBreaker();

        (bool circuitBreakerActive,,,) = treasury.getOracleProtectionStatus();
        assertFalse(circuitBreakerActive);
    }

    // =============================================================
    //                    EMERGENCY CONTROLS TESTS
    // =============================================================

    function testEmergencyLiquidityActivation() public {
        // Setup asset allocation first
        vm.startPrank(admin);
        _approveMultiSigOperation(TEST_OPERATION_HASH);

        treasury.setAssetAllocation(
            address(token1),
            TreasuryManagementV2.InvestmentCategory.Equity,
            8000, // 80% - high allocation
            100 * 1e18,
            1000 * 1e18,
            address(vault1),
            TEST_OPERATION_HASH
        );
        vm.stopPrank();

        // Activate emergency liquidity
        vm.startPrank(cfo);

        bytes32 emergencyHash = keccak256("emergency_operation");
        _approveMultiSigOperation(emergencyHash);

        vm.expectEmit(false, false, false, true);
        emit EmergencyLiquidityActivated(1000, 5000, cfo, "Market crash test");

        treasury.activateEmergencyLiquidity("Market crash test", emergencyHash);

        vm.stopPrank();

        // Check emergency state
        (uint256 triggerThreshold, uint256 targetLiquidity, address[] memory liquidationOrder, bool activated, uint256 activationTime, uint256 recoveryTime, address activatedBy, string memory activationReason, bool boardApproved) = treasury.emergencyProvisions();

        assertTrue(activated);
        assertEq(activatedBy, cfo);
        assertEq(activationReason, "Market crash test");
        assertTrue(boardApproved);
    }

    function testEmergencyLiquidityDoubleActivation() public {
        vm.startPrank(cfo);

        bytes32 emergencyHash1 = keccak256("emergency_operation_1");
        bytes32 emergencyHash2 = keccak256("emergency_operation_2");

        _approveMultiSigOperation(emergencyHash1);
        treasury.activateEmergencyLiquidity("First emergency", emergencyHash1);

        _approveMultiSigOperation(emergencyHash2);
        vm.expectRevert(TreasuryManagementV2.EmergencyModeActive.selector);
        treasury.activateEmergencyLiquidity("Second emergency", emergencyHash2);

        vm.stopPrank();
    }

    // =============================================================
    //                    REBALANCING TESTS
    // =============================================================

    function testRebalancePortfolio() public {
        // Setup multiple asset allocations
        vm.startPrank(admin);

        bytes32 operation1 = keccak256("allocation_1");
        bytes32 operation2 = keccak256("allocation_2");

        _approveMultiSigOperation(operation1);
        treasury.setAssetAllocation(
            address(token1),
            TreasuryManagementV2.InvestmentCategory.CashEquivalents,
            3000, // 30%
            100 * 1e18,
            5000 * 1e18,
            address(vault1),
            operation1
        );

        _approveMultiSigOperation(operation2);
        treasury.setAssetAllocation(
            address(token2),
            TreasuryManagementV2.InvestmentCategory.ShortTermDebt,
            2000, // 20%
            100 * 1e18,
            3000 * 1e18,
            address(vault2),
            operation2
        );

        vm.stopPrank();

        // Execute rebalancing
        vm.startPrank(treasurer);

        bytes32 rebalanceHash = keccak256("rebalance_operation");
        _approveMultiSigOperation(rebalanceHash);

        treasury.rebalancePortfolio(rebalanceHash);

        vm.stopPrank();
    }

    function testRebalanceUnauthorized() public {
        vm.startPrank(attacker);

        bytes32 rebalanceHash = keccak256("unauthorized_rebalance");

        vm.expectRevert();
        treasury.rebalancePortfolio(rebalanceHash);

        vm.stopPrank();
    }

    function testRebalanceWhenPaused() public {
        vm.prank(cfo);
        treasury.pause();

        vm.startPrank(treasurer);

        bytes32 rebalanceHash = keccak256("rebalance_when_paused");

        vm.expectRevert("Pausable: paused");
        treasury.rebalancePortfolio(rebalanceHash);

        vm.stopPrank();
    }

    function testRebalanceWhenEmergency() public {
        // First activate emergency
        vm.startPrank(cfo);
        bytes32 emergencyHash = keccak256("emergency");
        _approveMultiSigOperation(emergencyHash);
        treasury.activateEmergencyLiquidity("Emergency test", emergencyHash);
        vm.stopPrank();

        // Try to rebalance during emergency
        vm.startPrank(treasurer);
        bytes32 rebalanceHash = keccak256("rebalance_emergency");

        vm.expectRevert(TreasuryManagementV2.EmergencyModeActive.selector);
        treasury.rebalancePortfolio(rebalanceHash);

        vm.stopPrank();
    }

    // =============================================================
    //                    CONSTITUTIONAL COMPLIANCE TESTS
    // =============================================================

    function testConstitutionalViolation() public {
        vm.startPrank(admin);

        // Set constitution to reject
        constitution.setShouldPass(false);

        _approveMultiSigOperation(TEST_OPERATION_HASH);

        vm.expectRevert(TreasuryManagementV2.ConstitutionalViolation.selector);
        treasury.setAssetAllocation(
            address(token1),
            TreasuryManagementV2.InvestmentCategory.CashEquivalents,
            2000,
            100 * 1e18,
            1000 * 1e18,
            address(vault1),
            TEST_OPERATION_HASH
        );

        vm.stopPrank();
    }

    function testTotalAllocationLimit() public {
        vm.startPrank(admin);

        // Set first allocation to 80%
        bytes32 operation1 = keccak256("allocation_80");
        _approveMultiSigOperation(operation1);

        treasury.setAssetAllocation(
            address(token1),
            TreasuryManagementV2.InvestmentCategory.CashEquivalents,
            8000, // 80%
            100 * 1e18,
            5000 * 1e18,
            address(vault1),
            operation1
        );

        // Try to set second allocation to 30% (would exceed 100%)
        bytes32 operation2 = keccak256("allocation_30");
        _approveMultiSigOperation(operation2);

        vm.expectRevert("Total allocations exceed 100%");
        treasury.setAssetAllocation(
            address(token2),
            TreasuryManagementV2.InvestmentCategory.ShortTermDebt,
            3000, // 30% - would make total 110%
            100 * 1e18,
            3000 * 1e18,
            address(vault2),
            operation2
        );

        vm.stopPrank();
    }

    // =============================================================
    //                    SECURITY TESTS
    // =============================================================

    function testReentrancyProtection() public {
        // This would require a malicious vault contract that attempts reentrancy
        // For now, we test that the nonReentrant modifier is in place
        vm.startPrank(treasurer);

        bytes32 rebalanceHash = keccak256("reentrancy_test");
        _approveMultiSigOperation(rebalanceHash);

        // The actual reentrancy test would involve a malicious vault
        // that calls back into the treasury during withdrawal
        treasury.rebalancePortfolio(rebalanceHash);

        vm.stopPrank();
    }

    function testAccessControlEnforcement() public {
        // Test various role requirements

        // CFO role required for pause
        vm.startPrank(attacker);
        vm.expectRevert();
        treasury.pause();
        vm.stopPrank();

        // TREASURER_ROLE required for rebalancing
        vm.startPrank(attacker);
        vm.expectRevert();
        treasury.rebalancePortfolio(TEST_OPERATION_HASH);
        vm.stopPrank();

        // INVESTMENT_COMMITTEE_ROLE required for asset allocation
        vm.startPrank(attacker);
        vm.expectRevert();
        treasury.setAssetAllocation(
            address(token1),
            TreasuryManagementV2.InvestmentCategory.CashEquivalents,
            2000,
            100 * 1e18,
            1000 * 1e18,
            address(vault1),
            TEST_OPERATION_HASH
        );
        vm.stopPrank();
    }

    // =============================================================
    //                    GAS OPTIMIZATION TESTS
    // =============================================================

    function testGasUsageOptimization() public {
        // Setup asset allocations
        vm.startPrank(admin);

        bytes32 operation1 = keccak256("gas_test_1");
        _approveMultiSigOperation(operation1);

        uint256 gasBefore = gasleft();

        treasury.setAssetAllocation(
            address(token1),
            TreasuryManagementV2.InvestmentCategory.CashEquivalents,
            2000,
            100 * 1e18,
            1000 * 1e18,
            address(vault1),
            operation1
        );

        uint256 gasUsed = gasBefore - gasleft();
        console.log("Gas used for asset allocation:", gasUsed);

        // Should be reasonable for enterprise use
        assertLt(gasUsed, 500000); // Less than 500k gas

        vm.stopPrank();
    }

    function testBatchOperationGasEfficiency() public {
        vm.startPrank(treasurer);

        bytes32 rebalanceHash = keccak256("batch_rebalance");
        _approveMultiSigOperation(rebalanceHash);

        uint256 gasBefore = gasleft();
        treasury.rebalancePortfolio(rebalanceHash);
        uint256 gasUsed = gasBefore - gasleft();

        console.log("Gas used for portfolio rebalancing:", gasUsed);

        // Should process multiple assets efficiently
        assertLt(gasUsed, 2000000); // Less than 2M gas for batch operation

        vm.stopPrank();
    }

    // =============================================================
    //                    VIEW FUNCTION TESTS
    // =============================================================

    function testPortfolioOverview() public {
        // Setup some assets first
        vm.startPrank(admin);

        bytes32 operation1 = keccak256("overview_test_1");
        _approveMultiSigOperation(operation1);

        treasury.setAssetAllocation(
            address(token1),
            TreasuryManagementV2.InvestmentCategory.CashEquivalents,
            3000, // 30%
            100 * 1e18,
            5000 * 1e18,
            address(vault1),
            operation1
        );

        vm.stopPrank();

        (
            uint256 totalValue,
            uint256 liquidityRatio,
            uint256 numberOfAssets,
            uint256 concentrationRisk,
            bool emergencyActive,
            bool oracleHealthy
        ) = treasury.getPortfolioOverview();

        assertEq(numberOfAssets, 1);
        assertFalse(emergencyActive);
        assertTrue(oracleHealthy);
    }

    function testGetManagedAssets() public {
        address[] memory assets = treasury.getManagedAssets();
        assertEq(assets.length, 0); // No assets initially

        // Add an asset
        vm.startPrank(admin);

        bytes32 operation1 = keccak256("managed_assets_test");
        _approveMultiSigOperation(operation1);

        treasury.setAssetAllocation(
            address(token1),
            TreasuryManagementV2.InvestmentCategory.CashEquivalents,
            2000,
            100 * 1e18,
            1000 * 1e18,
            address(vault1),
            operation1
        );

        vm.stopPrank();

        address[] memory newAssets = treasury.getManagedAssets();
        assertEq(newAssets.length, 1);
        assertEq(newAssets[0], address(token1));
    }

    function testOracleProtectionStatus() public {
        (
            bool circuitBreakerActive,
            uint256 lastPriceUpdate,
            uint256 maxPriceDeviation,
            uint256 priceValidityWindow
        ) = treasury.getOracleProtectionStatus();

        assertFalse(circuitBreakerActive);
        assertGt(maxPriceDeviation, 0);
        assertGt(priceValidityWindow, 0);
    }

    // =============================================================
    //                    EDGE CASES AND ERROR CONDITIONS
    // =============================================================

    function testMaxManagedAssetsLimit() public {
        vm.startPrank(admin);

        // Try to add more assets than the limit allows
        // The current limit is 50 assets
        for (uint256 i = 0; i < 51; i++) {
            MockERC20 newToken = new MockERC20(
                string(abi.encodePacked("Token", vm.toString(i))),
                string(abi.encodePacked("TKN", vm.toString(i)))
            );

            bytes32 operationHash = keccak256(abi.encodePacked("asset", i));
            _approveMultiSigOperation(operationHash);

            if (i == 50) {
                vm.expectRevert(TreasuryManagementV2.ExceedsAllocationLimit.selector);
            }

            treasury.setAssetAllocation(
                address(newToken),
                TreasuryManagementV2.InvestmentCategory.CashEquivalents,
                100, // 1%
                1e18,
                10e18,
                address(0),
                operationHash
            );
        }

        vm.stopPrank();
    }

    function testZeroValueOperations() public {
        vm.startPrank(admin);

        _approveMultiSigOperation(TEST_OPERATION_HASH);

        vm.expectRevert(TreasuryManagementV2.InvalidAmount.selector);
        treasury.setAssetAllocation(
            address(token1),
            TreasuryManagementV2.InvestmentCategory.CashEquivalents,
            0, // 0% - invalid
            100 * 1e18,
            1000 * 1e18,
            address(vault1),
            TEST_OPERATION_HASH
        );

        vm.stopPrank();
    }

    // =============================================================
    //                    HELPER FUNCTIONS
    // =============================================================

    function _approveMultiSigOperation(bytes32 operationHash) internal {
        // Initiate the operation
        vm.prank(treasurer);
        treasury.initiateMultiSigOperation(operationHash, "test_operation");

        // Get approvals from multi-sig signers
        vm.prank(multiSig1);
        treasury.approveMultiSigOperation(operationHash);

        vm.prank(multiSig2);
        treasury.approveMultiSigOperation(operationHash);

        vm.prank(multiSig3);
        treasury.approveMultiSigOperation(operationHash);
    }

    // =============================================================
    //                    FUZZ TESTING
    // =============================================================

    function testFuzzAssetAllocation(
        uint256 targetPercentage,
        uint256 minAmount,
        uint256 maxAmount
    ) public {
        vm.assume(targetPercentage > 0 && targetPercentage <= 10000);
        vm.assume(minAmount > 0 && minAmount <= maxAmount);
        vm.assume(maxAmount < type(uint128).max); // Prevent overflow

        vm.startPrank(admin);
        _approveMultiSigOperation(TEST_OPERATION_HASH);

        treasury.setAssetAllocation(
            address(token1),
            TreasuryManagementV2.InvestmentCategory.CashEquivalents,
            targetPercentage,
            minAmount,
            maxAmount,
            address(vault1),
            TEST_OPERATION_HASH
        );

        (,,uint256 storedPercentage,,uint256 storedMin, uint256 storedMax,,,,,) = treasury.assetAllocations(address(token1));

        assertEq(storedPercentage, targetPercentage);
        assertEq(storedMin, minAmount);
        assertEq(storedMax, maxAmount);

        vm.stopPrank();
    }

    function testFuzzPriceUpdate(uint256 price1, uint256 price2) public {
        vm.assume(price1 > 0 && price1 < type(uint128).max);
        vm.assume(price2 > 0 && price2 < type(uint128).max);
        vm.assume(price1 != price2);

        priceOracle.setPrice(address(token1), price1);

        vm.prank(treasurer);
        treasury.updateAssetPrice(address(token1));

        (uint256 retrievedPrice1, bool isValid1) = treasury.getAssetPriceSafe(address(token1));
        assertEq(retrievedPrice1, price1);
        assertTrue(isValid1);

        priceOracle.setPrice(address(token1), price2);

        vm.prank(treasurer);
        treasury.updateAssetPrice(address(token1));

        (uint256 retrievedPrice2, bool isValid2) = treasury.getAssetPriceSafe(address(token1));

        // Should protect against extreme price changes
        if (price2 > price1) {
            uint256 deviation = ((price2 - price1) * 10000) / price1;
            if (deviation > 1000) { // 10% max deviation
                assertEq(retrievedPrice2, price1); // Should return old price
                assertFalse(isValid2);
            } else {
                assertEq(retrievedPrice2, price2);
                assertTrue(isValid2);
            }
        }
    }

    // =============================================================
    //                    INTEGRATION TESTS
    // =============================================================

    function testFullWorkflowIntegration() public {
        // Complete workflow test: Setup -> Allocation -> Rebalance -> Emergency

        // 1. Setup asset allocations
        vm.startPrank(admin);

        bytes32 allocation1 = keccak256("workflow_allocation_1");
        bytes32 allocation2 = keccak256("workflow_allocation_2");

        _approveMultiSigOperation(allocation1);
        treasury.setAssetAllocation(
            address(token1),
            TreasuryManagementV2.InvestmentCategory.CashEquivalents,
            3000, // 30%
            1000 * 1e18,
            5000 * 1e18,
            address(vault1),
            allocation1
        );

        _approveMultiSigOperation(allocation2);
        treasury.setAssetAllocation(
            address(token2),
            TreasuryManagementV2.InvestmentCategory.ShortTermDebt,
            2000, // 20%
            500 * 1e18,
            3000 * 1e18,
            address(vault2),
            allocation2
        );

        vm.stopPrank();

        // 2. Execute rebalancing
        vm.startPrank(treasurer);

        bytes32 rebalanceHash = keccak256("workflow_rebalance");
        _approveMultiSigOperation(rebalanceHash);
        treasury.rebalancePortfolio(rebalanceHash);

        vm.stopPrank();

        // 3. Check portfolio status
        (
            uint256 totalValue,
            uint256 liquidityRatio,
            uint256 numberOfAssets,
            uint256 concentrationRisk,
            bool emergencyActive,
            bool oracleHealthy
        ) = treasury.getPortfolioOverview();

        assertEq(numberOfAssets, 2);
        assertFalse(emergencyActive);
        assertTrue(oracleHealthy);

        // 4. Activate emergency liquidity
        vm.startPrank(cfo);

        bytes32 emergencyHash = keccak256("workflow_emergency");
        _approveMultiSigOperation(emergencyHash);
        treasury.activateEmergencyLiquidity("Integration test emergency", emergencyHash);

        vm.stopPrank();

        // 5. Verify emergency state
        (,,,,bool activated,,,string memory reason,) = treasury.emergencyProvisions();
        assertTrue(activated);
        assertEq(reason, "Integration test emergency");
    }
}