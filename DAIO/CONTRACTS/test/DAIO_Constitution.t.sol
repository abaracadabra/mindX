// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/DAIO_Constitution.sol";

contract DAIO_ConstitutionTest is Test {
    DAIO_Constitution public constitution;
    address public chairman;
    address public governance;
    address public validator;

    function setUp() public {
        chairman = makeAddr("chairman");
        governance = makeAddr("governance");
        validator = address(this);

        constitution = new DAIO_Constitution(chairman, governance);
        constitution.grantRole(constitution.VALIDATOR_ROLE(), validator);
    }

    function test_InitialState() public view {
        assertEq(constitution.DIVERSIFICATION_MANDATE(), 1500);
        assertEq(constitution.TREASURY_TITHE(), 1500);
        assertEq(constitution.VOTING_QUORUM(), 6667);
        assertFalse(constitution.paused());
    }

    function test_CalculateTithe() public view {
        uint256 profit = 100 ether;
        uint256 expectedTithe = 15 ether; // 15%
        assertEq(constitution.calculateTithe(profit), expectedTithe);
    }

    function test_ValidateTithe() public view {
        uint256 profit = 100 ether;
        uint256 sufficientTithe = 15 ether;
        uint256 insufficientTithe = 10 ether;

        assertTrue(constitution.validateTithe(profit, sufficientTithe));
        assertFalse(constitution.validateTithe(profit, insufficientTithe));
    }

    function test_ChairmanCanPause() public {
        vm.prank(chairman);
        constitution.pauseSystem("Emergency test");
        assertTrue(constitution.paused());
    }

    function test_ChairmanCanUnpause() public {
        vm.prank(chairman);
        constitution.pauseSystem("Emergency test");

        vm.prank(chairman);
        constitution.unpauseSystem();
        assertFalse(constitution.paused());
    }

    function test_NonChairmanCannotPause() public {
        vm.expectRevert();
        constitution.pauseSystem("Unauthorized");
    }

    function test_ValidateAction() public {
        bytes32 actionId = constitution.validateAction(
            DAIO_Constitution.ActionType.AgentCreation,
            governance,
            address(0x123),
            0,
            ""
        );

        assertTrue(actionId != bytes32(0));
        assertTrue(constitution.isActionPending(actionId));
    }

    function test_UpdateTreasuryState() public {
        vm.prank(governance);
        constitution.updateTreasuryState(100 ether, 20 ether);

        (bool compliant, uint256 total, uint256 diversified, ) = constitution.getTreasuryCompliance();
        assertTrue(compliant);
        assertEq(total, 100 ether);
        assertEq(diversified, 20 ether);
    }

    function test_DiversificationCompliance() public {
        // Set treasury state where diversification is met
        vm.prank(governance);
        constitution.updateTreasuryState(100 ether, 20 ether);
        assertTrue(constitution.checkDiversificationLimit());

        // Set treasury state where diversification is NOT met
        vm.prank(governance);
        constitution.updateTreasuryState(100 ether, 10 ether);
        assertFalse(constitution.checkDiversificationLimit());
    }

    function test_MarkActionExecuted() public {
        bytes32 actionId = constitution.validateAction(
            DAIO_Constitution.ActionType.TokenTransfer,
            governance,
            address(0x456),
            1 ether,
            ""
        );

        vm.prank(governance);
        constitution.markActionExecuted(actionId);

        assertFalse(constitution.isActionPending(actionId));
    }
}
