// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {Whitelist} from "../src/whitelist.sol";

contract WhitelistTest is Test {
    Whitelist wl;
    address admin = makeAddr("admin");
    address gate = makeAddr("gate");
    address alice = makeAddr("alice");
    address bob = makeAddr("bob");

    function setUp() public {
        vm.prank(admin);
        wl = new Whitelist(admin);
        // register a gate authority that may expand rooms
        bytes32 gateRole = wl.GATE_ROLE();
        vm.prank(admin);
        wl.grantRole(gateRole, gate);
    }

    function test_CreateAdmitCheck() public {
        vm.prank(admin);
        wl.createRoom(1, 1, false); // 1 databank = 65536 capacity
        vm.prank(admin);
        wl.admit(1, alice);
        assertTrue(wl.isWhitelisted(1, alice));
        assertFalse(wl.isWhitelisted(1, bob));
        (, , uint64 cap, uint64 count,) = wl.room(1);
        assertEq(cap, 65_536);
        assertEq(count, 1);
    }

    function test_DatabankExpansionGatedByAuthority() public {
        vm.prank(admin);
        wl.createRoom(7, 0, false); // capacity 0
        assertEq(wl.remaining(7), 0);

        // unauthorized cannot expand
        vm.prank(bob);
        vm.expectRevert(Whitelist.NotAuthority.selector);
        wl.addDatabank(7);

        // gate authority expands by one databank
        vm.prank(gate);
        wl.addDatabank(7);
        assertEq(wl.remaining(7), 65_536);
        (, , , , uint64 banks) = wl.room(7);
        assertEq(banks, 1);
    }

    function test_RoomFull_WhenCapacityZero() public {
        vm.prank(admin);
        wl.createRoom(9, 0, false);
        vm.prank(admin);
        vm.expectRevert(Whitelist.RoomFull.selector);
        wl.admit(9, alice);
    }

    function test_OpenRoom_SelfJoin() public {
        vm.prank(admin);
        wl.createRoom(2, 1, true);
        vm.prank(alice);
        wl.join(2);
        assertTrue(wl.isWhitelisted(2, alice));
    }

    function test_RevokeDecrementsCount() public {
        vm.prank(admin);
        wl.createRoom(3, 1, false);
        vm.prank(admin);
        wl.admit(3, alice);
        vm.prank(admin);
        wl.revoke(3, alice);
        assertFalse(wl.isWhitelisted(3, alice));
        (, , , uint64 count,) = wl.room(3);
        assertEq(count, 0);
    }

    function test_AdmitMany() public {
        vm.prank(admin);
        wl.createRoom(4, 1, false);
        address[] memory xs = new address[](2);
        xs[0] = alice;
        xs[1] = bob;
        vm.prank(admin);
        wl.admitMany(4, xs);
        assertTrue(wl.isWhitelisted(4, alice));
        assertTrue(wl.isWhitelisted(4, bob));
    }
}
