// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {OpenBDKAllocations} from "../src/allocations/OpenBDKAllocations.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockToken is ERC20 {
    constructor() ERC20("Mock", "MOCK") {
        _mint(msg.sender, 1_000_000e18);
    }
}

contract AllocationsTest is Test {
    OpenBDKAllocations alloc;
    MockToken token;
    address owner = makeAddr("owner");
    address bob = makeAddr("bob");

    uint64 start;

    function setUp() public {
        token = new MockToken();
        alloc = new OpenBDKAllocations(address(token), owner);
        token.transfer(address(alloc), 100_000e18);
        start = uint64(block.timestamp);
    }

    function test_CliffThenLinearVest() public {
        // 30-day cliff, 100-day linear from start
        vm.prank(owner);
        alloc.createAllocation(bob, 100_000e18, start, start + 30 days, 100 days, true);

        // before cliff -> nothing
        vm.warp(start + 10 days);
        assertEq(alloc.releasable(bob), 0);

        // after cliff, at 50 days -> 50%
        vm.warp(start + 50 days);
        assertApproxEqAbs(alloc.releasable(bob), 50_000e18, 1e15);

        // release pays the beneficiary
        alloc.release(bob);
        assertApproxEqAbs(token.balanceOf(bob), 50_000e18, 1e15);

        // fully vested after window
        vm.warp(start + 100 days);
        alloc.release(bob);
        assertEq(token.balanceOf(bob), 100_000e18);
    }

    function test_RevokeReturnsUnvested() public {
        vm.prank(owner);
        alloc.createAllocation(bob, 100_000e18, start, start, 100 days, true);
        vm.warp(start + 25 days); // 25% vested
        vm.prank(owner);
        alloc.revoke(bob);
        // owner got the unvested 75%
        assertApproxEqAbs(token.balanceOf(owner), 75_000e18, 1e15);
        // beneficiary can still claim the vested 25%
        alloc.release(bob);
        assertApproxEqAbs(token.balanceOf(bob), 25_000e18, 1e15);
    }

    function test_CannotOverAllocateBeyondBalance() public {
        vm.prank(owner);
        vm.expectRevert(OpenBDKAllocations.InsufficientUnallocatedBalance.selector);
        alloc.createAllocation(bob, 200_000e18, start, start, 100 days, false); // only 100k funded
    }
}
