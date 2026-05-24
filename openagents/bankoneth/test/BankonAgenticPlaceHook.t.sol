// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {BankonAgenticPlaceHook} from "../contracts/BankonAgenticPlaceHook.sol";
import {IBankonAgenticPlaceHook} from "../contracts/interfaces/IBankonExtensions.sol";

contract BankonAgenticPlaceHookTest is Test {
    BankonAgenticPlaceHook hook;
    address admin  = makeAddr("admin");
    address lister = makeAddr("lister");

    function setUp() public {
        hook = new BankonAgenticPlaceHook(admin, "https://agenticplace.pythai.net/api/listings");
        vm.prank(admin);
        hook.grantLister(lister);
    }

    function test_InitialWebhook() public {
        assertEq(hook.webhookURL(), "https://agenticplace.pythai.net/api/listings");
    }

    function test_SetWebhookByAdmin() public {
        vm.prank(admin);
        hook.setWebhookURL("https://staging.agenticplace.pythai.net/api/listings");
        assertEq(hook.webhookURL(), "https://staging.agenticplace.pythai.net/api/listings");
    }

    function test_OnlyListerCanList() public {
        vm.prank(makeAddr("stranger"));
        vm.expectRevert();
        hook.list(
            bytes32(uint256(0xb017)),
            keccak256("alice"),
            makeAddr("tba"),
            42,
            "ipfs://meta",
            makeAddr("author")
        );
    }

    function test_ListEmitsEvent() public {
        vm.prank(lister);
        vm.expectEmit(true, true, true, true, address(hook));
        emit IBankonAgenticPlaceHook.AgenticPlaceListing(
            bytes32(uint256(0xb017)),
            keccak256("alice"),
            address(uint160(0xabba)),
            42,
            "ipfs://meta",
            address(uint160(0xfeed))
        );
        hook.list(
            bytes32(uint256(0xb017)),
            keccak256("alice"),
            address(uint160(0xabba)),
            42,
            "ipfs://meta",
            address(uint160(0xfeed))
        );
    }
}
