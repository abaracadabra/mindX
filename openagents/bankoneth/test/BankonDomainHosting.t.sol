// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {BankonDomainHosting} from "../contracts/BankonDomainHosting.sol";
import {BankonX402Attestor}  from "../contracts/BankonX402Attestor.sol";
import {BankonPaymentRouter} from "../contracts/BankonPaymentRouter.sol";

import {MockNameWrapper} from "./mocks/MockNameWrapper.sol";
import {MockResolver}    from "./mocks/MockResolver.sol";

import {INameWrapper, IPublicResolver, IBankonPaymentRouter}
    from "../contracts/interfaces/IBankon.sol";
import {IBankonX402Attestor, IBankonDomainHosting}
    from "../contracts/interfaces/IBankonExtensions.sol";

contract BankonDomainHostingTest is Test {
    BankonDomainHosting hosting;
    BankonX402Attestor  attestor;
    BankonPaymentRouter router;
    MockNameWrapper     wrapper;
    MockResolver        resolver;

    address admin       = makeAddr("admin");
    address parentOwner = makeAddr("parentOwner");
    address buyer       = makeAddr("buyer");

    bytes32 constant PARENT_NODE = bytes32(uint256(0xdadd1e));
    uint32  constant CANNOT_UNWRAP = 1;

    function setUp() public {
        wrapper  = new MockNameWrapper();
        resolver = new MockResolver();
        router   = new BankonPaymentRouter(admin);
        attestor = new BankonX402Attestor(admin);

        hosting = new BankonDomainHosting(
            admin,
            INameWrapper(address(wrapper)),
            IPublicResolver(address(resolver)),
            IBankonPaymentRouter(address(router)),
            IBankonX402Attestor(address(attestor))
        );

        // Mark parent as wrapped (owner non-zero => isWrapped == true in the mock)
        // with CANNOT_UNWRAP fuse burned and owner = parentOwner.
        wrapper.adminSetParent(PARENT_NODE, parentOwner, CANNOT_UNWRAP, type(uint64).max);

        // distribute() requires TREASURER_ROLE on the router AND at least one
        // recipient configured (else NoRecipients reverts). DeployEthereum.s.sol
        // does this at deploy time; mirror it here. NB: cache role + recipient
        // values before prank so view getters don't consume the prank token.
        bytes32 treasurerRole = router.TREASURER_ROLE();
        address treasurySink  = makeAddr("treasury-sink");
        vm.startPrank(admin);
        router.grantRole(treasurerRole, address(hosting));
        router.setRecipients(treasurySink, address(0), address(0), address(0), address(0));
        vm.stopPrank();
    }

    function test_EnrollHappyPath() public {
        vm.prank(parentOwner);
        hosting.enroll(PARENT_NODE, 5_000_000, 0, uint64(block.timestamp + 365 days), 5000);

        BankonDomainHosting.EnrolledParent memory p = hosting.parentOf(PARENT_NODE);
        assertTrue(p.active);
        assertEq(p.parentOwner, parentOwner);
        assertEq(p.ownerShareBps, 5000);
    }

    function test_EnrollRequiresCannotUnwrapBurned() public {
        wrapper.adminSetParent(PARENT_NODE, parentOwner, 0, type(uint64).max); // fuses=0
        vm.prank(parentOwner);
        vm.expectRevert(BankonDomainHosting.CannotUnwrapNotBurned.selector);
        hosting.enroll(PARENT_NODE, 5_000_000, 0, uint64(block.timestamp + 365 days), 5000);
    }

    function test_OnlyParentOwnerCanEnroll() public {
        vm.prank(buyer);
        vm.expectRevert(BankonDomainHosting.NotParentOwner.selector);
        hosting.enroll(PARENT_NODE, 5_000_000, 0, uint64(block.timestamp + 365 days), 5000);
    }

    function test_IssueSubname() public {
        vm.prank(parentOwner);
        hosting.enroll(PARENT_NODE, 5_000_000, 0, uint64(block.timestamp + 365 days), 5000);

        vm.deal(buyer, 1 ether);
        vm.prank(buyer);
        hosting.issue{value: 0.1 ether}(PARENT_NODE, "alice", buyer, "");

        // Computed subnameNode = keccak256(parentNode || keccak256("alice"))
        bytes32 expected = keccak256(abi.encodePacked(PARENT_NODE, keccak256("alice")));
        // Mock records the subnode mint — verify by calling getData.
        (address subOwner,,) = wrapper.getData(uint256(expected));
        assertEq(subOwner, buyer);
    }

    function test_DisenrollByOwner() public {
        vm.prank(parentOwner);
        hosting.enroll(PARENT_NODE, 5_000_000, 0, uint64(block.timestamp + 365 days), 5000);

        vm.prank(parentOwner);
        hosting.disenroll(PARENT_NODE);
        assertFalse(hosting.parentOf(PARENT_NODE).active);
    }
}
