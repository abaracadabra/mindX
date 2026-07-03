// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Test} from "forge-std/Test.sol";
import {OpenBDKDeployer} from "../src/OpenBDKDeployer.sol";
import {OpenBDKValidatorRegistry} from "../src/governance/OpenBDKValidatorRegistry.sol";
import {OpenBDKAllocations} from "../src/allocations/OpenBDKAllocations.sol";
import {TimelockController} from "@openzeppelin/contracts/governance/TimelockController.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract Tok is ERC20 {
    constructor() ERC20("Stake", "STK") { _mint(msg.sender, 1e24); }
}

/// @notice Proves the non-custodial invariant: after deploy, the OWNER's timelock
///         holds all admin and the deploy/software path holds nothing.
contract OpenBDKDeployerTest is Test {
    Tok staking;
    Tok allocTok;
    address owner = makeAddr("owner");
    address software = address(this); // the "deploy key" that broadcasts

    function setUp() public {
        staking = new Tok();
        allocTok = new Tok();
    }

    function test_OwnerHoldsEverything_SoftwareHoldsNothing() public {
        OpenBDKDeployer d = new OpenBDKDeployer(
            owner, 2 days, address(staking), 1000e18, 100, address(allocTok)
        );

        TimelockController tl = TimelockController(payable(d.timelock()));
        OpenBDKValidatorRegistry vr = OpenBDKValidatorRegistry(d.validatorRegistry());
        OpenBDKAllocations alloc = OpenBDKAllocations(d.allocations());

        bytes32 ADMIN = 0x00; // DEFAULT_ADMIN_ROLE
        // ValidatorRegistry admin is the timelock — NOT the factory, NOT software.
        assertTrue(vr.hasRole(ADMIN, address(tl)));
        assertFalse(vr.hasRole(ADMIN, address(d)));
        assertFalse(vr.hasRole(ADMIN, software));
        assertFalse(vr.hasRole(ADMIN, owner)); // owner acts THROUGH the timelock

        // Allocations vault is owned by the timelock.
        assertEq(alloc.owner(), address(tl));

        // The OWNER is the sole proposer/executor of the OVERLORD timelock.
        assertTrue(tl.hasRole(tl.PROPOSER_ROLE(), owner));
        assertTrue(tl.hasRole(tl.EXECUTOR_ROLE(), owner));
        assertFalse(tl.hasRole(tl.PROPOSER_ROLE(), software));
        assertFalse(tl.hasRole(tl.PROPOSER_ROLE(), address(d)));

        // Timelock self-administers (no external admin backdoor).
        assertTrue(tl.hasRole(ADMIN, address(tl)));
        assertFalse(tl.hasRole(ADMIN, software));
        assertEq(tl.getMinDelay(), 2 days);
    }
}
