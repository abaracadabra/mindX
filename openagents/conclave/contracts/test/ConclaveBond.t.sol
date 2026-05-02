// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {ConclaveBond} from "../src/ConclaveBond.sol";

/// @title ConclaveBond direct test suite
/// @notice The existing Conclave.t.sol exercises ConclaveBond.slash via
///         Conclave.slashForLeak. This file covers the rest: postBond,
///         attestAlgorandBond, releaseBond, bondOf, and every revert path.
contract ConclaveBondTest is Test {
    ConclaveBond internal bond;
    address internal conclave   = address(0xC07C1A0E);
    address internal algoBridge = address(0xA160B100);
    address internal alice      = address(0xA11CE);
    address internal bob        = address(0xB0B);

    bytes32 internal constant CID = bytes32(uint256(0x1));
    bytes32 internal constant ALGO_TX = bytes32(uint256(0xA160));

    function setUp() public {
        bond = new ConclaveBond(conclave, algoBridge);
        vm.deal(alice, 100 ether);
        vm.deal(bob, 100 ether);
        vm.deal(conclave, 0 ether);
    }

    // ── postBond ─────────────────────────────────────────────

    function test_postBond_storesAmount_andSetsReleasableAt() public {
        vm.prank(alice);
        bond.postBond{value: 1 ether}(CID, 1 ether);
        assertEq(bond.bondOf(CID, alice), 1 ether);
        assertEq(bond.releasableAt(CID, alice), uint64(block.timestamp + 30 days));
        assertEq(bond.algorandTxOf(CID, alice), bytes32(0));
    }

    function test_postBond_emitsBondPosted_withZeroAlgoTxid() public {
        vm.expectEmit(true, true, true, true);
        emit BondPosted(CID, alice, 2 ether, bytes32(0));
        vm.prank(alice);
        bond.postBond{value: 2 ether}(CID, 2 ether);
    }

    function test_postBond_zeroAmount_reverts() public {
        vm.prank(alice);
        vm.expectRevert(bytes("ConclaveBond: zero amount"));
        bond.postBond{value: 0}(CID, 0);
    }

    function test_postBond_valueMismatch_reverts() public {
        vm.prank(alice);
        vm.expectRevert(bytes("ConclaveBond: value mismatch"));
        bond.postBond{value: 0.5 ether}(CID, 1 ether);
    }

    function test_postBond_accumulates_onSecondCall() public {
        vm.startPrank(alice);
        bond.postBond{value: 1 ether}(CID, 1 ether);
        bond.postBond{value: 2 ether}(CID, 2 ether);
        vm.stopPrank();
        assertEq(bond.bondOf(CID, alice), 3 ether);
    }

    // ── attestAlgorandBond ──────────────────────────────────

    function test_attestAlgorandBond_onlyBridgeCanCall() public {
        vm.prank(alice);  // not the bridge
        vm.expectRevert(bytes("ConclaveBond: not bridge"));
        bond.attestAlgorandBond(CID, alice, 1 ether, ALGO_TX);
    }

    function test_attestAlgorandBond_setsTxidAndAmount() public {
        vm.prank(algoBridge);
        bond.attestAlgorandBond(CID, alice, 5 ether, ALGO_TX);
        assertEq(bond.bondOf(CID, alice), 5 ether);
        assertEq(bond.algorandTxOf(CID, alice), ALGO_TX);
        assertEq(bond.releasableAt(CID, alice), uint64(block.timestamp + 30 days));
    }

    function test_attestAlgorandBond_emitsWithAlgoTxid() public {
        vm.expectEmit(true, true, true, true);
        emit BondPosted(CID, alice, 5 ether, ALGO_TX);
        vm.prank(algoBridge);
        bond.attestAlgorandBond(CID, alice, 5 ether, ALGO_TX);
    }

    // ── releaseBond ─────────────────────────────────────────

    function test_releaseBond_noBond_reverts() public {
        vm.prank(alice);
        vm.expectRevert(ConclaveBond.NoBond.selector);
        bond.releaseBond(CID);
    }

    function test_releaseBond_tooEarly_reverts() public {
        vm.prank(alice);
        bond.postBond{value: 1 ether}(CID, 1 ether);
        // Still within RELEASE_DELAY window
        vm.prank(alice);
        vm.expectRevert(ConclaveBond.TooEarly.selector);
        bond.releaseBond(CID);
    }

    function test_releaseBond_native_returnsValueToCaller() public {
        vm.prank(alice);
        bond.postBond{value: 1 ether}(CID, 1 ether);
        // Skip ahead past RELEASE_DELAY
        vm.warp(block.timestamp + 30 days + 1);
        uint256 balBefore = alice.balance;
        vm.prank(alice);
        bond.releaseBond(CID);
        assertEq(alice.balance - balBefore, 1 ether);
        assertEq(bond.bondOf(CID, alice), 0);
    }

    function test_releaseBond_emitsBondReleased() public {
        vm.prank(alice);
        bond.postBond{value: 1 ether}(CID, 1 ether);
        vm.warp(block.timestamp + 30 days + 1);
        vm.expectEmit(true, true, true, true);
        emit BondReleased(CID, alice, 1 ether);
        vm.prank(alice);
        bond.releaseBond(CID);
    }

    function test_releaseBond_algorandPath_doesNotTransferEth() public {
        // Bridge attests an Algorand-side stake; no native ETH is locked.
        vm.prank(algoBridge);
        bond.attestAlgorandBond(CID, alice, 5 ether, ALGO_TX);
        vm.warp(block.timestamp + 30 days + 1);
        uint256 balBefore = alice.balance;
        vm.prank(alice);
        bond.releaseBond(CID);
        // Bond accounting cleared, but no ETH transferred (Algorand path)
        assertEq(bond.bondOf(CID, alice), 0);
        assertEq(alice.balance, balBefore);
    }

    // ── slash ───────────────────────────────────────────────

    function test_slash_onlyConclave_reverts() public {
        vm.prank(alice);  // not the conclave contract
        vm.expectRevert(ConclaveBond.NotConclave.selector);
        bond.slash(CID, alice);
    }

    function test_slash_zeroBond_returnsZero_doesNotRevert() public {
        // Slash a member with no bond posted — should return 0, not revert
        vm.prank(conclave);
        uint256 amt = bond.slash(CID, alice);
        assertEq(amt, 0);
    }

    function test_slash_clearsBond_andTransfersToConclave() public {
        vm.prank(alice);
        bond.postBond{value: 3 ether}(CID, 3 ether);

        uint256 conclaveBalBefore = conclave.balance;
        vm.prank(conclave);
        uint256 amt = bond.slash(CID, alice);
        assertEq(amt, 3 ether);
        assertEq(bond.bondOf(CID, alice), 0);
        assertEq(conclave.balance - conclaveBalBefore, 3 ether);
    }

    function test_slash_emitsBondSlashed() public {
        vm.prank(alice);
        bond.postBond{value: 1 ether}(CID, 1 ether);
        vm.expectEmit(true, true, true, true);
        emit BondSlashed(CID, alice, 1 ether);
        vm.prank(conclave);
        bond.slash(CID, alice);
    }

    // ── isolation ───────────────────────────────────────────

    function test_bonds_areIsolatedPerConclaveAndPerMember() public {
        bytes32 cid2 = bytes32(uint256(0x2));
        vm.prank(alice);
        bond.postBond{value: 1 ether}(CID, 1 ether);
        vm.prank(bob);
        bond.postBond{value: 2 ether}(cid2, 2 ether);
        // Cross checks
        assertEq(bond.bondOf(CID, alice), 1 ether);
        assertEq(bond.bondOf(cid2, alice), 0);
        assertEq(bond.bondOf(CID, bob), 0);
        assertEq(bond.bondOf(cid2, bob), 2 ether);
    }

    function test_receive_acceptsBareEthTransfer() public {
        // Test the receive() function so a slash callback or external rebalance
        // can fund the contract without reverting.
        (bool ok, ) = address(bond).call{value: 1 ether}("");
        assertTrue(ok);
        assertEq(address(bond).balance, 1 ether);
    }

    // ── events (re-declared for vm.expectEmit) ──────────────
    event BondPosted(bytes32 indexed conclave_id, address indexed member, uint256 amount, bytes32 algoTxid);
    event BondReleased(bytes32 indexed conclave_id, address indexed member, uint256 amount);
    event BondSlashed(bytes32 indexed conclave_id, address indexed member, uint256 amount);
}
