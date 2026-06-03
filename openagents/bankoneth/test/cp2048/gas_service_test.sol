// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {bankon_gas_service} from "../../contracts/cp2048/bankon_gas_service.sol";

contract gas_service_test is Test {
    address admin = address(0xC0DE);
    address beneficiary = address(0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169); // bankon.eth
    address bridge = address(0xB41D6E);  // stand-in bridge_collect allocator
    address payable arriving = payable(address(0xA221E));

    uint256 constant UNITS = 150_000;
    uint256 constant CAP = 1 ether;

    bankon_gas_service gs;

    function setUp() public {
        gs = new bankon_gas_service(admin, beneficiary, UNITS, CAP);
        vm.deal(address(gs), 10 ether);     // fund the reservoir
        vm.prank(admin); gs.set_allocator(bridge, true);
    }

    function test_drop_equals_basefee_times_units() public {
        vm.fee(2 gwei);
        uint256 expected = uint256(2 gwei) * UNITS;
        assertEq(gs.quote_drop(), expected, "quote tracks basefee");

        vm.prank(bridge);
        uint256 amt = gs.allocate_gas(arriving);
        assertEq(amt, expected, "dropped one tx of gas");
        assertEq(arriving.balance, expected, "arriving funded");
    }

    function test_cap_clamps_drop() public {
        vm.fee(10_000 gwei); // 1e13 * 150000 = 1.5e18 > CAP
        assertEq(gs.quote_drop(), CAP, "clamped to cap");
        vm.prank(bridge);
        assertEq(gs.allocate_gas(arriving), CAP);
    }

    function test_one_shot_blocks_second_drop() public {
        vm.fee(2 gwei);
        vm.prank(bridge); gs.allocate_gas(arriving);
        vm.prank(bridge);
        vm.expectRevert(bankon_gas_service.already_funded.selector);
        gs.allocate_gas(arriving);
    }

    function test_one_shot_off_allows_repeat() public {
        vm.fee(2 gwei);
        vm.prank(admin); gs.set_one_shot(false);
        vm.prank(bridge); gs.allocate_gas(arriving);
        vm.prank(bridge); gs.allocate_gas(arriving);   // no revert
        assertEq(arriving.balance, uint256(2 gwei) * UNITS * 2);
    }

    function test_only_allocator_or_owner() public {
        vm.fee(2 gwei);
        vm.prank(address(0xBAD));
        vm.expectRevert(bankon_gas_service.not_allocator.selector);
        gs.allocate_gas(arriving);
    }

    function test_reservoir_empty_reverts() public {
        bankon_gas_service empty = new bankon_gas_service(admin, beneficiary, UNITS, CAP);
        vm.prank(admin); empty.set_allocator(bridge, true);
        vm.fee(2 gwei);
        vm.prank(bridge);
        vm.expectRevert(bankon_gas_service.reservoir_empty.selector);
        empty.allocate_gas(arriving);
    }

    function test_quote_fee_golden_example() public view {
        // cost 0.001 ETH, single side: fee = 0.001 x phi/10 = 0.000161803398874989 ETH ("0.00016 etc").
        uint256 fee = gs.quote_fee(0.001 ether, 1);
        assertEq(fee, 161803398874989, "golden gas fee = cost x phi/10");
        // user's example: total = cost + fee = 0.001161803398874989 ETH ("0.00116 etc")
        assertEq(0.001 ether + fee, 1161803398874989, "total = cost + golden fee");
        // each side of a cross-chain tx: 2 calls of 0.001 == 1 call of 0.002
        assertEq(gs.quote_fee(0.001 ether, 2), gs.quote_fee(0.002 ether, 1), "two-sided == double cost");
        assertEq(gs.quote_fee(0.001 ether, 2), 323606797749978, "two-sided golden fee");
    }

    function test_buy_gas_client_pays() public {
        uint256 gasWei = 0.001 ether;
        (uint256 issue, uint256 fee, uint256 total) = gs.quote_buy(gasWei, 1);
        assertEq(issue, gasWei);
        assertEq(fee, 161803398874989);

        address client = address(0xC11E47);
        vm.deal(client, 1 ether);
        uint256 reservoirBefore = address(gs).balance;

        vm.prank(client);
        uint256 paidFee = gs.buy_gas{value: total}(arriving, gasWei, 1);

        assertEq(paidFee, fee);
        assertEq(arriving.balance, gasWei, "client-bought gas delivered");
        assertEq(address(gs).balance, reservoirBefore + fee, "fee retained in reservoir for bankon.eth");
    }

    function test_buy_gas_underpaid_reverts() public {
        uint256 gasWei = 0.001 ether;
        address client = address(0xC11E47);
        vm.deal(client, 1 ether);
        vm.prank(client);
        vm.expectRevert(bankon_gas_service.underpaid.selector);
        gs.buy_gas{value: gasWei}(arriving, gasWei, 1);   // missing the fee
    }

    function test_self_purge_only_to_beneficiary() public {
        uint256 before = beneficiary.balance;
        vm.prank(address(0xA11CE));
        gs.self_purge();                         // permissionless
        assertEq(beneficiary.balance, before + 10 ether, "reservoir swept home");
        assertEq(address(gs).balance, 0);
    }
}
