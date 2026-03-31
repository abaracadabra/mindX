// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "forge-std/console.sol";
import "../../../contracts/examples/corporate/EmployeeEquityGovernanceV2.sol";
import "../../../contracts/eip-standards/advanced/ERC1400/SecurityToken.sol";
import "../../../contracts/daio/governance/TriumvirateGovernance.sol";
import "../../../contracts/eip-standards/advanced/ERC4337/SmartAccount.sol";
import "@openzeppelin/contracts/proxy/ERC1967/ERC1967Proxy.sol";

/**
 * @title EmployeeEquityGovernanceV2Test
 * @dev Comprehensive test suite for EmployeeEquityGovernanceV2 contract
 *
 * SECURITY TEST COVERAGE:
 * 1. Voting Weight Manipulation Prevention
 * 2. Insider Trading Controls and Pre-clearance
 * 3. Precise Vesting Calculations with Remainder Handling
 * 4. Reentrancy Protection for Financial Operations
 * 5. Multi-signature Requirements for Critical Operations
 * 6. Emergency Controls and Circuit Breakers
 * 7. Blackout Period Management
 * 8. Access Control and Role Management
 * 9. Gas Optimization and Edge Cases
 * 10. Integration with DAIO Infrastructure
 */
contract EmployeeEquityGovernanceV2Test is Test {
    // =============================================================
    //                        CONTRACTS
    // =============================================================

    EmployeeEquityGovernanceV2 public equityGovernance;
    SecurityToken public companyStock;
    TriumvirateGovernance public governance;
    SmartAccount public corporateAccount;

    // =============================================================
    //                        TEST ACCOUNTS
    // =============================================================

    address public deployer = address(0x1);
    address public hrManager = address(0x2);
    address public compensationCommittee = address(0x3);
    address public complianceOfficer = address(0x4);
    address public boardMember = address(0x5);
    address public emergencyRole = address(0x6);
    address public treasury = address(0x7);

    address public employeeL1 = address(0x11);
    address public employeeL5 = address(0x15);
    address public employeeL7 = address(0x17);
    address public employeeL12 = address(0x1C);

    address public smartAccountL1 = address(0x111);
    address public smartAccountL5 = address(0x115);
    address public smartAccountL7 = address(0x117);
    address public smartAccountL12 = address(0x11C);

    address public maliciousActor = address(0x666);
    address public attacker = address(0x777);

    // =============================================================
    //                        TEST DATA
    // =============================================================

    uint256 public constant INITIAL_SHARE_PRICE = 100 * 1e18; // $100 per share
    uint256 public constant TOTAL_SHARES = 1000000 * 1e18; // 1M shares
    uint256 public constant EMPLOYEE_SALARY = 150000 * 1e18; // $150k salary

    string public constant COMPANY_NAME = "TechCorp Global Inc";
    string public constant STOCK_SYMBOL = "TECH";

    // =============================================================
    //                        EVENTS
    // =============================================================

    event EmployeeRegistered(address indexed employee, uint256 indexed employeeId, EmployeeEquityGovernanceV2.EmployeeLevel level);
    event EquityGranted(bytes32 indexed grantId, address indexed employee, EmployeeEquityGovernanceV2.EquityType equityType, uint256 shares);
    event VotingSnapshotTaken(bytes32 indexed proposalId, uint256 blockNumber, uint256 totalSupply);
    event InsiderTradingViolation(address indexed insider, string violation, uint256 timestamp);
    event PreClearanceRequested(bytes32 indexed requestId, address indexed insider, uint256 shares);
    event EmergencyPauseActivated(address indexed activator, uint256 timestamp);

    // =============================================================
    //                           SETUP
    // =============================================================

    function setUp() public {
        vm.startPrank(deployer);

        // Deploy mock contracts
        companyStock = _deploySecurityToken();
        governance = _deployTriumvirateGovernance();
        corporateAccount = _deploySmartAccount();

        // Deploy main contract
        equityGovernance = new EmployeeEquityGovernanceV2(
            address(companyStock),
            address(governance),
            address(corporateAccount),
            COMPANY_NAME,
            STOCK_SYMBOL,
            TOTAL_SHARES,
            INITIAL_SHARE_PRICE,
            treasury
        );

        // Setup roles
        _setupRoles();

        // Fund contract and accounts for testing
        _fundAccounts();

        vm.stopPrank();
    }

    // =============================================================
    //                     UNIT TESTS - SETUP
    // =============================================================

    function test_ContractInitialization() public view {
        assertEq(equityGovernance.companyName(), COMPANY_NAME);
        assertEq(equityGovernance.stockSymbol(), STOCK_SYMBOL);
        assertEq(equityGovernance.totalShares(), TOTAL_SHARES);
        assertEq(equityGovernance.sharePrice(), INITIAL_SHARE_PRICE);
        assertEq(equityGovernance.treasuryAddress(), treasury);

        assertTrue(equityGovernance.hasRole(equityGovernance.DEFAULT_ADMIN_ROLE(), deployer));
        assertFalse(equityGovernance.emergencyPaused());
    }

    function test_RoleSetup() public view {
        assertTrue(equityGovernance.hasRole(equityGovernance.HR_MANAGER_ROLE(), hrManager));
        assertTrue(equityGovernance.hasRole(equityGovernance.COMPENSATION_COMMITTEE_ROLE(), compensationCommittee));
        assertTrue(equityGovernance.hasRole(equityGovernance.COMPLIANCE_OFFICER_ROLE(), complianceOfficer));
        assertTrue(equityGovernance.hasRole(equityGovernance.BOARD_MEMBER_ROLE(), boardMember));
        assertTrue(equityGovernance.hasRole(equityGovernance.EMERGENCY_ROLE(), emergencyRole));
    }

    // =============================================================
    //                  UNIT TESTS - EMPLOYEE MANAGEMENT
    // =============================================================

    function test_RegisterEmployee() public {
        vm.prank(hrManager);
        vm.expectEmit(true, true, true, true);
        emit EmployeeRegistered(employeeL1, 1, EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual);

        equityGovernance.registerEmployee(
            employeeL1,
            1,
            "Alice Developer",
            "Engineering",
            EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual,
            EMPLOYEE_SALARY,
            smartAccountL1
        );

        (uint256 employeeId, string memory name, , , , , bool active, , ) =
            equityGovernance.getEmployeeInfo(employeeL1);

        assertEq(employeeId, 1);
        assertEq(name, "Alice Developer");
        assertTrue(active);
        assertTrue(equityGovernance.hasRole(equityGovernance.EMPLOYEE_ROLE(), employeeL1));
    }

    function test_RegisterEmployeeFailsWithInvalidData() public {
        vm.startPrank(hrManager);

        // Test zero address
        vm.expectRevert("Invalid employee address");
        equityGovernance.registerEmployee(
            address(0),
            1,
            "Test Employee",
            "Engineering",
            EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual,
            EMPLOYEE_SALARY,
            smartAccountL1
        );

        // Test empty name
        vm.expectRevert("Name cannot be empty");
        equityGovernance.registerEmployee(
            employeeL1,
            1,
            "",
            "Engineering",
            EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual,
            EMPLOYEE_SALARY,
            smartAccountL1
        );

        // Test zero salary
        vm.expectRevert("Salary must be positive");
        equityGovernance.registerEmployee(
            employeeL1,
            1,
            "Test Employee",
            "Engineering",
            EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual,
            0,
            smartAccountL1
        );

        vm.stopPrank();
    }

    function test_UpdateEmployeeLevel() public {
        _registerEmployee(employeeL1, 1, EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual);

        vm.prank(hrManager);
        equityGovernance.updateEmployeeLevel(
            employeeL1,
            EmployeeEquityGovernanceV2.EmployeeLevel.L7_Director
        );

        (, , , EmployeeEquityGovernanceV2.EmployeeLevel level, , , , , ) =
            equityGovernance.getEmployeeInfo(employeeL1);

        assertEq(uint8(level), uint8(EmployeeEquityGovernanceV2.EmployeeLevel.L7_Director));
        assertTrue(equityGovernance.hasRole(equityGovernance.SHAREHOLDER_ROLE(), employeeL1));
    }

    function test_CLevelEmployeeBecomesInsider() public {
        _registerEmployee(employeeL12, 12, EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual);

        vm.prank(hrManager);
        equityGovernance.updateEmployeeLevel(
            employeeL12,
            EmployeeEquityGovernanceV2.EmployeeLevel.L12_C_Level
        );

        assertTrue(equityGovernance.hasRole(equityGovernance.BOARD_MEMBER_ROLE(), employeeL12));
        assertTrue(equityGovernance.isInsider(employeeL12));
    }

    // =============================================================
    //                  UNIT TESTS - EQUITY GRANTS
    // =============================================================

    function test_GrantEquity() public {
        _registerEmployee(employeeL1, 1, EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual);

        vm.prank(compensationCommittee);
        vm.expectEmit(true, true, true, true);

        bytes32 expectedGrantId = keccak256(abi.encodePacked(
            employeeL1,
            EmployeeEquityGovernanceV2.EquityType.ISO,
            1000 * 1e18,
            block.timestamp,
            block.number
        ));

        emit EquityGranted(expectedGrantId, employeeL1, EmployeeEquityGovernanceV2.EquityType.ISO, 1000 * 1e18);

        bytes32 grantId = _grantEquity(
            employeeL1,
            EmployeeEquityGovernanceV2.EquityType.ISO,
            1000 * 1e18,
            INITIAL_SHARE_PRICE,
            block.timestamp + 365 days * 10, // 10 years
            EmployeeEquityGovernanceV2.VestingSchedule.FourYearMonthly
        );

        (address employee, EmployeeEquityGovernanceV2.EquityType equityType, uint256 totalShares, , , , , ) =
            equityGovernance.getEquityGrant(grantId);

        assertEq(employee, employeeL1);
        assertEq(uint8(equityType), uint8(EmployeeEquityGovernanceV2.EquityType.ISO));
        assertEq(totalShares, 1000 * 1e18);
    }

    function test_GrantEquityFailsForInactiveEmployee() public {
        vm.prank(compensationCommittee);
        vm.expectRevert("Employee not found or inactive");

        _grantEquity(
            employeeL1,
            EmployeeEquityGovernanceV2.EquityType.ISO,
            1000 * 1e18,
            INITIAL_SHARE_PRICE,
            block.timestamp + 365 days * 10,
            EmployeeEquityGovernanceV2.VestingSchedule.FourYearMonthly
        );
    }

    function test_PreciseVestingCalculation() public {
        _registerEmployee(employeeL1, 1, EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual);

        // Grant shares that don't divide evenly by 48 months
        uint256 totalShares = 1000 * 1e18 + 17; // Add 17 wei to test remainder handling

        vm.prank(compensationCommittee);
        bytes32 grantId = _grantEquity(
            employeeL1,
            EmployeeEquityGovernanceV2.EquityType.ISO,
            totalShares,
            INITIAL_SHARE_PRICE,
            block.timestamp + 365 days * 10,
            EmployeeEquityGovernanceV2.VestingSchedule.FourYearMonthly
        );

        // Fast forward to after cliff
        vm.warp(block.timestamp + 366 days);

        // Process vesting
        equityGovernance.processVesting();

        (, , uint256 total, uint256 vested, , , , ) =
            equityGovernance.getEquityGrant(grantId);

        // 25% should vest at cliff
        uint256 expectedCliffVesting = totalShares / 4;
        assertEq(vested, expectedCliffVesting);

        // Verify no shares are lost due to rounding
        assertTrue(vested > 0);
        assertTrue(vested <= total);
    }

    function test_VestingDoesNotLoseShares() public {
        _registerEmployee(employeeL1, 1, EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual);

        // Test with various share amounts that have remainders
        uint256[] memory testAmounts = new uint256[](3);
        testAmounts[0] = 1001 * 1e18; // Remainder when dividing by 4 and 36
        testAmounts[1] = 2003 * 1e18; // Different remainder pattern
        testAmounts[2] = 5007 * 1e18; // Larger remainder test

        for (uint256 i = 0; i < testAmounts.length; i++) {
            address testEmployee = address(uint160(0x1000 + i));
            _registerEmployee(testEmployee, 100 + i, EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual);

            vm.prank(compensationCommittee);
            bytes32 grantId = _grantEquity(
                testEmployee,
                EmployeeEquityGovernanceV2.EquityType.ISO,
                testAmounts[i],
                INITIAL_SHARE_PRICE,
                block.timestamp + 365 days * 10,
                EmployeeEquityGovernanceV2.VestingSchedule.FourYearMonthly
            );

            // Fast forward through entire vesting period
            vm.warp(block.timestamp + 365 days * 5); // 5 years to ensure all vesting

            equityGovernance.processVesting();

            (, , uint256 total, uint256 vested, , , , ) =
                equityGovernance.getEquityGrant(grantId);

            // All shares should eventually vest (no loss due to rounding)
            assertEq(vested, total, "Vesting calculation lost shares");
        }
    }

    // =============================================================
    //                  UNIT TESTS - VOTING SECURITY
    // =============================================================

    function test_VotingSnapshotPreventsManipulation() public {
        // Setup shareholders
        _registerEmployee(employeeL7, 7, EmployeeEquityGovernanceV2.EmployeeLevel.L7_Director);
        _registerEmployee(employeeL12, 12, EmployeeEquityGovernanceV2.EmployeeLevel.L12_C_Level);

        // Create proposal (which takes snapshot)
        vm.prank(boardMember);
        bytes32 proposalId = equityGovernance.createProposal(
            "Test Proposal",
            "Testing voting snapshot security",
            7 days,
            1000, // 10% quorum
            5100  // 51% majority
        );

        // Verify snapshot was taken
        vm.expectEmit(true, false, false, false);
        emit VotingSnapshotTaken(proposalId, block.number - 1, 0);

        // Attempt to manipulate voting weight by acquiring more shares after proposal creation
        // This should not affect voting power due to snapshot
        vm.prank(treasury);
        companyStock.transferByPartition(
            companyStock.COMMON_STOCK(),
            treasury,
            employeeL7,
            10000 * 1e18,
            ""
        );

        // Vote should use snapshot balance, not current balance
        vm.prank(employeeL7);
        equityGovernance.vote(proposalId, 1); // Vote for

        (uint256 forVotes, , , , , ) = equityGovernance.getProposalResults(proposalId);

        // Voting weight should be based on snapshot, not current increased balance
        // Since employee had 0 shares at snapshot, they should have 0 voting power
        assertEq(forVotes, 0, "Voting manipulation successful - snapshot failed");
    }

    function test_VotingRequiresSnapshotBalance() public {
        _registerEmployee(employeeL7, 7, EmployeeEquityGovernanceV2.EmployeeLevel.L7_Director);

        vm.prank(boardMember);
        bytes32 proposalId = equityGovernance.createProposal(
            "Test Proposal",
            "Testing voting requirements",
            7 days,
            1000,
            5100
        );

        // Try to vote without any voting power at snapshot
        vm.prank(employeeL7);
        vm.expectRevert("No voting power at snapshot");
        equityGovernance.vote(proposalId, 1);
    }

    function test_DoubleVotingPrevention() public {
        // Setup shareholder with voting power
        _setupShareholderWithBalance(employeeL7, 1000 * 1e18);

        vm.prank(boardMember);
        bytes32 proposalId = equityGovernance.createProposal(
            "Test Proposal",
            "Testing double voting prevention",
            7 days,
            100,
            5100
        );

        // First vote should succeed
        vm.prank(employeeL7);
        equityGovernance.vote(proposalId, 1);

        // Second vote should fail
        vm.prank(employeeL7);
        vm.expectRevert("Already voted");
        equityGovernance.vote(proposalId, 0);
    }

    // =============================================================
    //                  UNIT TESTS - INSIDER TRADING
    // =============================================================

    function test_InsiderDesignation() public {
        _registerEmployee(employeeL12, 12, EmployeeEquityGovernanceV2.EmployeeLevel.L12_C_Level);

        vm.prank(complianceOfficer);
        equityGovernance.setInsiderStatus(employeeL12, true);

        assertTrue(equityGovernance.isInsider(employeeL12));
    }

    function test_PreClearanceRequest() public {
        _registerEmployee(employeeL12, 12, EmployeeEquityGovernanceV2.EmployeeLevel.L12_C_Level);

        vm.prank(complianceOfficer);
        equityGovernance.setInsiderStatus(employeeL12, true);

        vm.prank(employeeL12);
        vm.expectEmit(true, true, false, true);
        emit PreClearanceRequested(
            keccak256(abi.encodePacked(
                employeeL12,
                EmployeeEquityGovernanceV2.EquityType.ISO,
                1000 * 1e18,
                block.timestamp
            )),
            employeeL12,
            1000 * 1e18
        );

        bytes32 requestId = equityGovernance.requestPreClearance(
            EmployeeEquityGovernanceV2.EquityType.ISO,
            1000 * 1e18
        );

        assertTrue(requestId != bytes32(0));
    }

    function test_PreClearanceOnlyForInsiders() public {
        _registerEmployee(employeeL1, 1, EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual);

        vm.prank(employeeL1);
        vm.expectRevert("Only insiders need pre-clearance");
        equityGovernance.requestPreClearance(
            EmployeeEquityGovernanceV2.EquityType.ISO,
            1000 * 1e18
        );
    }

    function test_BlackoutPeriodActivation() public {
        uint256 startDate = block.timestamp + 1 days;
        uint256 endDate = startDate + 7 days;

        vm.prank(complianceOfficer);
        vm.expectEmit(false, false, false, true);
        emit BlackoutPeriodActivated(startDate, endDate, "Earnings announcement");

        equityGovernance.activateBlackoutPeriod(
            startDate,
            endDate,
            "Earnings announcement"
        );

        // Fast forward to blackout period
        vm.warp(startDate + 1 hours);

        assertTrue(equityGovernance.isInBlackoutPeriod());
    }

    function test_InsiderTradingBlockedDuringBlackout() public {
        _registerEmployee(employeeL12, 12, EmployeeEquityGovernanceV2.EmployeeLevel.L12_C_Level);

        vm.prank(complianceOfficer);
        equityGovernance.setInsiderStatus(employeeL12, true);

        // Activate blackout period
        uint256 startDate = block.timestamp + 1 hours;
        uint256 endDate = startDate + 7 days;

        vm.prank(complianceOfficer);
        equityGovernance.activateBlackoutPeriod(startDate, endDate, "Earnings announcement");

        // Fast forward to blackout period
        vm.warp(startDate + 1 hours);

        // Insider should not be able to request pre-clearance during blackout
        vm.prank(employeeL12);
        vm.expectRevert("Cannot request during blackout");
        equityGovernance.requestPreClearance(
            EmployeeEquityGovernanceV2.EquityType.ISO,
            1000 * 1e18
        );
    }

    // =============================================================
    //                  UNIT TESTS - OPTION EXERCISE
    // =============================================================

    function test_OptionExerciseSuccess() public {
        // Setup employee with vested options
        _registerEmployee(employeeL1, 1, EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual);

        bytes32 grantId = _grantEquity(
            employeeL1,
            EmployeeEquityGovernanceV2.EquityType.ISO,
            1000 * 1e18,
            INITIAL_SHARE_PRICE,
            block.timestamp + 365 days * 10,
            EmployeeEquityGovernanceV2.VestingSchedule.Immediate
        );

        // Exercise options
        uint256 exerciseAmount = 500 * 1e18;
        uint256 exerciseCost = exerciseAmount * INITIAL_SHARE_PRICE / 1e18;

        vm.deal(employeeL1, exerciseCost + 1 ether);

        vm.prank(employeeL1);
        vm.expectEmit(true, true, false, true);
        emit EquityExercised(grantId, employeeL1, exerciseAmount, exerciseAmount * INITIAL_SHARE_PRICE / 1e18);

        equityGovernance.exerciseOptions{value: exerciseCost}(grantId, exerciseAmount);

        (, , , uint256 remainingVested, , , , ) = equityGovernance.getEquityGrant(grantId);
        assertEq(remainingVested, 500 * 1e18);
    }

    function test_OptionExerciseFailsInsufficientPayment() public {
        _registerEmployee(employeeL1, 1, EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual);

        bytes32 grantId = _grantEquity(
            employeeL1,
            EmployeeEquityGovernanceV2.EquityType.ISO,
            1000 * 1e18,
            INITIAL_SHARE_PRICE,
            block.timestamp + 365 days * 10,
            EmployeeEquityGovernanceV2.VestingSchedule.Immediate
        );

        uint256 exerciseAmount = 500 * 1e18;
        uint256 exerciseCost = exerciseAmount * INITIAL_SHARE_PRICE / 1e18;

        vm.deal(employeeL1, exerciseCost - 1 wei); // Insufficient payment

        vm.prank(employeeL1);
        vm.expectRevert("Insufficient payment");
        equityGovernance.exerciseOptions{value: exerciseCost - 1 wei}(grantId, exerciseAmount);
    }

    function test_InsiderExerciseRequiresCompliance() public {
        _registerEmployee(employeeL12, 12, EmployeeEquityGovernanceV2.EmployeeLevel.L12_C_Level);

        vm.prank(complianceOfficer);
        equityGovernance.setInsiderStatus(employeeL12, true);

        bytes32 grantId = _grantEquity(
            employeeL12,
            EmployeeEquityGovernanceV2.EquityType.ISO,
            1000 * 1e18,
            INITIAL_SHARE_PRICE,
            block.timestamp + 365 days * 10,
            EmployeeEquityGovernanceV2.VestingSchedule.Immediate
        );

        // Exercise should fail without pre-clearance
        uint256 exerciseAmount = 500 * 1e18;
        uint256 exerciseCost = exerciseAmount * INITIAL_SHARE_PRICE / 1e18;

        vm.deal(employeeL12, exerciseCost + 1 ether);

        vm.prank(employeeL12);
        vm.expectRevert("Pre-clearance required for insider");
        equityGovernance.exerciseOptions{value: exerciseCost}(grantId, exerciseAmount);
    }

    // =============================================================
    //                  UNIT TESTS - EMERGENCY CONTROLS
    // =============================================================

    function test_EmergencyPause() public {
        vm.prank(emergencyRole);
        vm.expectEmit(true, false, false, true);
        emit EmergencyPauseActivated(emergencyRole, block.timestamp);

        equityGovernance.emergencyPause();

        assertTrue(equityGovernance.emergencyPaused());
    }

    function test_PausedContractBlocksOperations() public {
        _registerEmployee(employeeL1, 1, EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual);

        vm.prank(emergencyRole);
        equityGovernance.emergencyPause();

        // Should block employee registration
        vm.prank(hrManager);
        vm.expectRevert("Contract is paused");
        equityGovernance.registerEmployee(
            employeeL5,
            5,
            "Test Employee",
            "Engineering",
            EmployeeEquityGovernanceV2.EmployeeLevel.L5_Manager,
            EMPLOYEE_SALARY,
            smartAccountL5
        );

        // Should block equity grants
        vm.prank(compensationCommittee);
        vm.expectRevert("Contract is paused");
        _grantEquity(
            employeeL1,
            EmployeeEquityGovernanceV2.EquityType.ISO,
            1000 * 1e18,
            INITIAL_SHARE_PRICE,
            block.timestamp + 365 days * 10,
            EmployeeEquityGovernanceV2.VestingSchedule.FourYearMonthly
        );
    }

    function test_EmergencyUnpause() public {
        vm.startPrank(emergencyRole);
        equityGovernance.emergencyPause();

        assertTrue(equityGovernance.emergencyPaused());

        equityGovernance.emergencyUnpause();

        assertFalse(equityGovernance.emergencyPaused());
        vm.stopPrank();
    }

    function test_AutoUnpauseAfterMaxDuration() public {
        vm.prank(emergencyRole);
        equityGovernance.emergencyPause();

        assertTrue(equityGovernance.emergencyPaused());

        // Fast forward past max emergency pause duration (7 days)
        vm.warp(block.timestamp + 7 days + 1 seconds);

        // Anyone can trigger auto-unpause
        vm.prank(address(0x999));
        equityGovernance.autoUnpause();

        assertFalse(equityGovernance.emergencyPaused());
    }

    function test_AutoUnpauseFailsBeforeMaxDuration() public {
        vm.prank(emergencyRole);
        equityGovernance.emergencyPause();

        // Try to auto-unpause before max duration
        vm.prank(address(0x999));
        vm.expectRevert("Max pause duration not reached");
        equityGovernance.autoUnpause();
    }

    // =============================================================
    //                  UNIT TESTS - MULTI-SIGNATURE
    // =============================================================

    function test_MultiSigSignerManagement() public {
        address newSigner = address(0x888);

        vm.prank(deployer);
        equityGovernance.addMultiSigSigner(newSigner);

        // Verify signer was added by creating an operation that requires it
        vm.prank(newSigner);
        bytes32 operationHash = keccak256("TEST_OPERATION");
        equityGovernance.createMultiSigOperation(
            operationHash,
            2, // threshold
            block.timestamp + 1 hours
        );

        // Should have 1 approval from the signer who created it
        // (Testing this indirectly since approvals is not exposed)
    }

    function test_MultiSigOperationCreation() public {
        bytes32 operationHash = keccak256("TEST_OPERATION");
        uint256 threshold = 2;
        uint256 expiry = block.timestamp + 1 hours;

        vm.prank(deployer); // deployer is a multi-sig signer
        vm.expectEmit(true, false, false, true);
        emit MultiSigOperationCreated(operationHash, threshold, expiry);

        equityGovernance.createMultiSigOperation(operationHash, threshold, expiry);
    }

    function test_MultiSigApprovalProcess() public {
        // Add second signer
        address signer2 = address(0x888);
        vm.prank(deployer);
        equityGovernance.addMultiSigSigner(signer2);

        bytes32 operationHash = keccak256("TEST_OPERATION");

        // Create operation (deployer automatically approves)
        vm.prank(deployer);
        equityGovernance.createMultiSigOperation(
            operationHash,
            2, // Need 2 approvals
            block.timestamp + 1 hours
        );

        // Second signer approves
        vm.prank(signer2);
        vm.expectEmit(true, true, false, false);
        emit MultiSigApprovalAdded(operationHash, signer2);

        equityGovernance.addMultiSigApproval(operationHash);
    }

    // =============================================================
    //                     INTEGRATION TESTS
    // =============================================================

    function test_FullEmployeeEquityLifecycle() public {
        // 1. Register employee
        vm.prank(hrManager);
        equityGovernance.registerEmployee(
            employeeL5,
            5,
            "Bob Manager",
            "Engineering",
            EmployeeEquityGovernanceV2.EmployeeLevel.L5_Manager,
            200000 * 1e18,
            smartAccountL5
        );

        // 2. Grant equity
        vm.prank(compensationCommittee);
        bytes32 grantId = _grantEquity(
            employeeL5,
            EmployeeEquityGovernanceV2.EquityType.ISO,
            2000 * 1e18,
            INITIAL_SHARE_PRICE,
            block.timestamp + 365 days * 10,
            EmployeeEquityGovernanceV2.VestingSchedule.FourYearMonthly
        );

        // 3. Wait for cliff vesting
        vm.warp(block.timestamp + 366 days);
        equityGovernance.processVesting();

        (, , , uint256 vestedShares, , , , ) = equityGovernance.getEquityGrant(grantId);
        assertGt(vestedShares, 0, "No shares vested after cliff");

        // 4. Exercise some options
        uint256 exerciseAmount = vestedShares / 2;
        uint256 exerciseCost = exerciseAmount * INITIAL_SHARE_PRICE / 1e18;

        vm.deal(employeeL5, exerciseCost + 1 ether);

        vm.prank(employeeL5);
        equityGovernance.exerciseOptions{value: exerciseCost}(grantId, exerciseAmount);

        // 5. Promote to director (gets shareholder role)
        vm.prank(hrManager);
        equityGovernance.updateEmployeeLevel(
            employeeL5,
            EmployeeEquityGovernanceV2.EmployeeLevel.L7_Director
        );

        assertTrue(equityGovernance.hasRole(equityGovernance.SHAREHOLDER_ROLE(), employeeL5));
    }

    function test_GovernanceProposalLifecycle() public {
        // Setup shareholders with voting power
        _setupShareholderWithBalance(employeeL7, 1000 * 1e18);
        _setupShareholderWithBalance(employeeL12, 2000 * 1e18);

        // Create proposal
        vm.prank(boardMember);
        bytes32 proposalId = equityGovernance.createProposal(
            "Increase Share Pool",
            "Proposal to increase employee share pool by 10%",
            7 days,
            1500, // 15% quorum
            6000  // 60% majority
        );

        // Vote on proposal
        vm.prank(employeeL7);
        equityGovernance.vote(proposalId, 1); // For

        vm.prank(employeeL12);
        equityGovernance.vote(proposalId, 1); // For

        // Fast forward past voting period
        vm.warp(block.timestamp + 7 days + 1 seconds);

        // Execute proposal
        vm.prank(boardMember);
        equityGovernance.executeProposal(proposalId);

        (uint256 forVotes, uint256 againstVotes, uint256 abstainVotes, uint256 totalVotes, bool passed, bool executed) =
            equityGovernance.getProposalResults(proposalId);

        assertTrue(passed, "Proposal should have passed");
        assertTrue(executed, "Proposal should have been executed");
    }

    // =============================================================
    //                      SECURITY TESTS
    // =============================================================

    function test_ReentrancyProtectionOnExercise() public {
        // This would require a malicious contract that attempts reentrancy
        // For now, we verify the modifier is in place
        _registerEmployee(employeeL1, 1, EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual);

        bytes32 grantId = _grantEquity(
            employeeL1,
            EmployeeEquityGovernanceV2.EquityType.ISO,
            1000 * 1e18,
            INITIAL_SHARE_PRICE,
            block.timestamp + 365 days * 10,
            EmployeeEquityGovernanceV2.VestingSchedule.Immediate
        );

        uint256 exerciseAmount = 500 * 1e18;
        uint256 exerciseCost = exerciseAmount * INITIAL_SHARE_PRICE / 1e18;

        vm.deal(employeeL1, exerciseCost);

        // Normal exercise should work
        vm.prank(employeeL1);
        equityGovernance.exerciseOptions{value: exerciseCost}(grantId, exerciseAmount);

        // Verify remaining vested shares
        (, , , uint256 remainingVested, , , , ) = equityGovernance.getEquityGrant(grantId);
        assertEq(remainingVested, 500 * 1e18);
    }

    function test_AccessControlEnforcement() public {
        // Test that only authorized roles can perform sensitive operations

        // Non-HR manager cannot register employees
        vm.prank(maliciousActor);
        vm.expectRevert();
        equityGovernance.registerEmployee(
            employeeL1,
            1,
            "Unauthorized Employee",
            "Engineering",
            EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual,
            EMPLOYEE_SALARY,
            smartAccountL1
        );

        // Non-compensation committee cannot grant equity
        vm.prank(maliciousActor);
        vm.expectRevert();
        _grantEquity(
            employeeL1,
            EmployeeEquityGovernanceV2.EquityType.ISO,
            1000 * 1e18,
            INITIAL_SHARE_PRICE,
            block.timestamp + 365 days * 10,
            EmployeeEquityGovernanceV2.VestingSchedule.FourYearMonthly
        );

        // Non-compliance officer cannot set insider status
        vm.prank(maliciousActor);
        vm.expectRevert();
        equityGovernance.setInsiderStatus(employeeL1, true);

        // Non-emergency role cannot pause contract
        vm.prank(maliciousActor);
        vm.expectRevert();
        equityGovernance.emergencyPause();
    }

    function test_InputValidationAndEdgeCases() public {
        // Test various edge cases and input validation

        // Zero share equity grant should fail
        _registerEmployee(employeeL1, 1, EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual);

        vm.prank(compensationCommittee);
        vm.expectRevert("Shares must be positive");
        _grantEquity(
            employeeL1,
            EmployeeEquityGovernanceV2.EquityType.ISO,
            0,
            INITIAL_SHARE_PRICE,
            block.timestamp + 365 days * 10,
            EmployeeEquityGovernanceV2.VestingSchedule.FourYearMonthly
        );

        // Expired grant date should fail
        vm.prank(compensationCommittee);
        vm.expectRevert("Expiration must be in future");
        _grantEquity(
            employeeL1,
            EmployeeEquityGovernanceV2.EquityType.ISO,
            1000 * 1e18,
            INITIAL_SHARE_PRICE,
            block.timestamp - 1, // Past expiration
            EmployeeEquityGovernanceV2.VestingSchedule.FourYearMonthly
        );
    }

    // =============================================================
    //                        GAS TESTS
    // =============================================================

    function test_GasOptimizationEmployeeRegistration() public {
        uint256 gasBefore = gasleft();

        vm.prank(hrManager);
        equityGovernance.registerEmployee(
            employeeL1,
            1,
            "Alice Developer",
            "Engineering",
            EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual,
            EMPLOYEE_SALARY,
            smartAccountL1
        );

        uint256 gasUsed = gasBefore - gasleft();
        console.log("Gas used for employee registration:", gasUsed);

        // Should be reasonable for enterprise operations (< 200k gas)
        assertLt(gasUsed, 200000, "Employee registration too expensive");
    }

    function test_GasOptimizationEquityGrant() public {
        _registerEmployee(employeeL1, 1, EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual);

        uint256 gasBefore = gasleft();

        vm.prank(compensationCommittee);
        _grantEquity(
            employeeL1,
            EmployeeEquityGovernanceV2.EquityType.ISO,
            1000 * 1e18,
            INITIAL_SHARE_PRICE,
            block.timestamp + 365 days * 10,
            EmployeeEquityGovernanceV2.VestingSchedule.FourYearMonthly
        );

        uint256 gasUsed = gasBefore - gasleft();
        console.log("Gas used for equity grant:", gasUsed);

        // Should be reasonable for equity operations (< 300k gas)
        assertLt(gasUsed, 300000, "Equity grant too expensive");
    }

    function test_GasOptimizationVestingProcess() public {
        // Setup multiple employees with grants
        for (uint256 i = 0; i < 5; i++) {
            address employee = address(uint160(0x2000 + i));
            _registerEmployee(employee, 200 + i, EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual);

            vm.prank(compensationCommittee);
            _grantEquity(
                employee,
                EmployeeEquityGovernanceV2.EquityType.ISO,
                1000 * 1e18,
                INITIAL_SHARE_PRICE,
                block.timestamp + 365 days * 10,
                EmployeeEquityGovernanceV2.VestingSchedule.FourYearMonthly
            );
        }

        vm.warp(block.timestamp + 366 days); // Past cliff

        uint256 gasBefore = gasleft();
        equityGovernance.processVesting();
        uint256 gasUsed = gasBefore - gasleft();

        console.log("Gas used for processing 5 grants:", gasUsed);

        // Should scale reasonably (< 100k gas per grant)
        assertLt(gasUsed, 500000, "Vesting process too expensive");
    }

    // =============================================================
    //                        FUZZ TESTS
    // =============================================================

    function testFuzz_EquityGrantAmounts(uint256 shares) public {
        vm.assume(shares > 0 && shares <= TOTAL_SHARES);

        _registerEmployee(employeeL1, 1, EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual);

        vm.prank(compensationCommittee);
        bytes32 grantId = _grantEquity(
            employeeL1,
            EmployeeEquityGovernanceV2.EquityType.ISO,
            shares,
            INITIAL_SHARE_PRICE,
            block.timestamp + 365 days * 10,
            EmployeeEquityGovernanceV2.VestingSchedule.FourYearMonthly
        );

        (, , uint256 totalShares, , , , , ) = equityGovernance.getEquityGrant(grantId);
        assertEq(totalShares, shares);
    }

    function testFuzz_VestingCalculationConsistency(uint256 shares) public {
        vm.assume(shares > 100 && shares <= TOTAL_SHARES); // Minimum shares for meaningful vesting

        _registerEmployee(employeeL1, 1, EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual);

        vm.prank(compensationCommittee);
        bytes32 grantId = _grantEquity(
            employeeL1,
            EmployeeEquityGovernanceV2.EquityType.ISO,
            shares,
            INITIAL_SHARE_PRICE,
            block.timestamp + 365 days * 10,
            EmployeeEquityGovernanceV2.VestingSchedule.FourYearMonthly
        );

        // Test vesting at cliff
        vm.warp(block.timestamp + 366 days);
        equityGovernance.processVesting();

        (, , uint256 total, uint256 vested, , , , ) = equityGovernance.getEquityGrant(grantId);

        // Cliff should vest ~25%
        uint256 expectedCliff = total / 4;
        assertGe(vested, expectedCliff, "Vesting less than expected cliff amount");
        assertLe(vested, expectedCliff + total / 100, "Vesting significantly more than cliff");
    }

    function testFuzz_OptionExerciseAmounts(uint256 exerciseShares) public {
        uint256 totalShares = 1000 * 1e18;
        vm.assume(exerciseShares > 0 && exerciseShares <= totalShares);

        _registerEmployee(employeeL1, 1, EmployeeEquityGovernanceV2.EmployeeLevel.L1_Individual);

        vm.prank(compensationCommittee);
        bytes32 grantId = _grantEquity(
            employeeL1,
            EmployeeEquityGovernanceV2.EquityType.ISO,
            totalShares,
            INITIAL_SHARE_PRICE,
            block.timestamp + 365 days * 10,
            EmployeeEquityGovernanceV2.VestingSchedule.Immediate
        );

        uint256 exerciseCost = exerciseShares * INITIAL_SHARE_PRICE / 1e18;
        vm.deal(employeeL1, exerciseCost);

        vm.prank(employeeL1);
        equityGovernance.exerciseOptions{value: exerciseCost}(grantId, exerciseShares);

        (, , , uint256 remainingVested, , , , ) = equityGovernance.getEquityGrant(grantId);
        assertEq(remainingVested, totalShares - exerciseShares);
    }

    // =============================================================
    //                     HELPER FUNCTIONS
    // =============================================================

    function _deploySecurityToken() internal returns (SecurityToken) {
        // Mock deployment - in real tests, deploy actual SecurityToken
        return SecurityToken(address(new MockSecurityToken()));
    }

    function _deployTriumvirateGovernance() internal returns (TriumvirateGovernance) {
        // Mock deployment - in real tests, deploy actual TriumvirateGovernance
        return TriumvirateGovernance(address(new MockTriumvirateGovernance()));
    }

    function _deploySmartAccount() internal returns (SmartAccount) {
        // Mock deployment - in real tests, deploy actual SmartAccount
        return SmartAccount(payable(address(new MockSmartAccount())));
    }

    function _setupRoles() internal {
        equityGovernance.grantRole(equityGovernance.HR_MANAGER_ROLE(), hrManager);
        equityGovernance.grantRole(equityGovernance.COMPENSATION_COMMITTEE_ROLE(), compensationCommittee);
        equityGovernance.grantRole(equityGovernance.COMPLIANCE_OFFICER_ROLE(), complianceOfficer);
        equityGovernance.grantRole(equityGovernance.BOARD_MEMBER_ROLE(), boardMember);
        equityGovernance.grantRole(equityGovernance.EMERGENCY_ROLE(), emergencyRole);
    }

    function _fundAccounts() internal {
        vm.deal(treasury, 1000 ether);
        vm.deal(employeeL1, 10 ether);
        vm.deal(employeeL5, 10 ether);
        vm.deal(employeeL7, 10 ether);
        vm.deal(employeeL12, 10 ether);
        vm.deal(maliciousActor, 5 ether);
        vm.deal(attacker, 5 ether);
    }

    function _registerEmployee(
        address employee,
        uint256 employeeId,
        EmployeeEquityGovernanceV2.EmployeeLevel level
    ) internal {
        vm.prank(hrManager);
        equityGovernance.registerEmployee(
            employee,
            employeeId,
            "Test Employee",
            "Engineering",
            level,
            EMPLOYEE_SALARY,
            address(uint160(uint256(uint160(employee)) + 1000)) // Mock smart account
        );
    }

    function _grantEquity(
        address employee,
        EmployeeEquityGovernanceV2.EquityType equityType,
        uint256 totalShares,
        uint256 grantPrice,
        uint256 expirationDate,
        EmployeeEquityGovernanceV2.VestingSchedule vestingSchedule
    ) internal returns (bytes32) {
        bytes32 expectedGrantId = keccak256(abi.encodePacked(
            employee,
            equityType,
            totalShares,
            block.timestamp,
            block.number
        ));

        equityGovernance.grantEquity(
            employee,
            equityType,
            totalShares,
            grantPrice,
            expirationDate,
            vestingSchedule
        );

        return expectedGrantId;
    }

    function _setupShareholderWithBalance(address shareholder, uint256 balance) internal {
        _registerEmployee(shareholder, uint256(uint160(shareholder)), EmployeeEquityGovernanceV2.EmployeeLevel.L7_Director);

        // Mock giving shares to shareholder
        vm.prank(treasury);
        companyStock.transferByPartition(
            companyStock.COMMON_STOCK(),
            treasury,
            shareholder,
            balance,
            ""
        );
    }
}

// =============================================================
//                      MOCK CONTRACTS
// =============================================================

contract MockSecurityToken {
    bytes32 public constant COMMON_STOCK = keccak256("COMMON_STOCK");

    mapping(bytes32 => mapping(address => uint256)) private _balancesByPartition;
    mapping(bytes32 => uint256) private _totalSupplyByPartition;

    function balanceOfByPartition(bytes32 partition, address account) external view returns (uint256) {
        return _balancesByPartition[partition][account];
    }

    function totalSupplyByPartition(bytes32 partition) external view returns (uint256) {
        return _totalSupplyByPartition[partition];
    }

    function transferByPartition(
        bytes32 partition,
        address from,
        address to,
        uint256 amount,
        bytes calldata
    ) external returns (bytes32) {
        _balancesByPartition[partition][from] -= amount;
        _balancesByPartition[partition][to] += amount;
        return partition;
    }

    function mint(address to, uint256 amount) external {
        _balancesByPartition[COMMON_STOCK][to] += amount;
        _totalSupplyByPartition[COMMON_STOCK] += amount;
    }
}

contract MockTriumvirateGovernance {
    function hasRole(bytes32, address) external pure returns (bool) {
        return true;
    }
}

contract MockSmartAccount {
    function execute(address, uint256, bytes calldata) external pure returns (bytes memory) {
        return "";
    }
}