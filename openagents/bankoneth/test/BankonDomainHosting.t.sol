// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {BankonDomainHosting} from "../contracts/BankonDomainHosting.sol";
import {BankonX402Attestor}  from "../contracts/BankonX402Attestor.sol";
import {BankonPaymentRouter} from "../contracts/BankonPaymentRouter.sol";

import {MockNameWrapper} from "./mocks/MockNameWrapper.sol";
import {MockResolver}    from "./mocks/MockResolver.sol";
import {X402Sig}         from "./helpers/X402Sig.sol";

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
        hosting.enroll(PARENT_NODE, 5_000_000, 0.001 ether, 0, uint64(block.timestamp + 365 days), 5000);

        BankonDomainHosting.EnrolledParent memory p = hosting.parentOf(PARENT_NODE);
        assertTrue(p.active);
        assertEq(p.parentOwner, parentOwner);
        assertEq(p.ownerShareBps, 5000);
    }

    function test_EnrollRequiresCannotUnwrapBurned() public {
        wrapper.adminSetParent(PARENT_NODE, parentOwner, 0, type(uint64).max); // fuses=0
        vm.prank(parentOwner);
        vm.expectRevert(BankonDomainHosting.CannotUnwrapNotBurned.selector);
        hosting.enroll(PARENT_NODE, 5_000_000, 0.001 ether, 0, uint64(block.timestamp + 365 days), 5000);
    }

    function test_OnlyParentOwnerCanEnroll() public {
        vm.prank(buyer);
        vm.expectRevert(BankonDomainHosting.NotParentOwner.selector);
        hosting.enroll(PARENT_NODE, 5_000_000, 0.001 ether, 0, uint64(block.timestamp + 365 days), 5000);
    }

    function test_IssueSubname() public {
        vm.prank(parentOwner);
        hosting.enroll(PARENT_NODE, 5_000_000, 0.001 ether, 0, uint64(block.timestamp + 365 days), 5000);

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
        hosting.enroll(PARENT_NODE, 5_000_000, 0.001 ether, 0, uint64(block.timestamp + 365 days), 5000);

        vm.prank(parentOwner);
        hosting.disenroll(PARENT_NODE);
        assertFalse(hosting.parentOf(PARENT_NODE).active);
    }

    // ── Phase 0.4a additions ───────────────────────────────────────

    function test_SetPrices_updatesBothFloors_byOwner() public {
        vm.prank(parentOwner);
        hosting.enroll(PARENT_NODE, 5_000_000, 0.001 ether, 0, uint64(block.timestamp + 365 days), 5000);

        vm.prank(parentOwner);
        hosting.setPrices(PARENT_NODE, 7_500_000, 0.01 ether);

        BankonDomainHosting.EnrolledParent memory p = hosting.parentOf(PARENT_NODE);
        assertEq(p.pricePerLabel6, 7_500_000);
        assertEq(p.priceEthWei,    0.01 ether);
    }

    function test_SetPrices_revertsForNonOwner() public {
        vm.prank(parentOwner);
        hosting.enroll(PARENT_NODE, 5_000_000, 0.001 ether, 0, uint64(block.timestamp + 365 days), 5000);

        vm.prank(buyer);
        vm.expectRevert(BankonDomainHosting.NotParentOwner.selector);
        hosting.setPrices(PARENT_NODE, 1, 1);
    }

    function test_SetPrices_revertsOnUnenrolled() public {
        vm.prank(parentOwner);
        vm.expectRevert(BankonDomainHosting.ParentNotEnrolled.selector);
        hosting.setPrices(PARENT_NODE, 1, 1);
    }

    function test_SetHostShareBps_byAdmin() public {
        vm.prank(admin);
        hosting.setHostShareBps(1_000);
        assertEq(hosting.hostShareBps(), 1_000);
    }

    function test_SetHostShareBps_revertsOver5000() public {
        vm.prank(admin);
        vm.expectRevert(bytes("host share > 50%"));
        hosting.setHostShareBps(5_001);
    }

    function test_SetHostShareBps_revertsForNonAdmin() public {
        vm.expectRevert();
        hosting.setHostShareBps(1_000);
    }

    function test_Pause_blocksEnroll() public {
        vm.prank(admin);
        hosting.pause();
        vm.prank(parentOwner);
        vm.expectRevert(abi.encodeWithSignature("EnforcedPause()"));
        hosting.enroll(PARENT_NODE, 5_000_000, 0.001 ether, 0, uint64(block.timestamp + 365 days), 5000);
    }

    function test_Pause_blocksIssue() public {
        vm.prank(parentOwner);
        hosting.enroll(PARENT_NODE, 5_000_000, 0.001 ether, 0, uint64(block.timestamp + 365 days), 5000);
        vm.prank(admin);
        hosting.pause();

        vm.deal(buyer, 1 ether);
        vm.prank(buyer);
        vm.expectRevert(abi.encodeWithSignature("EnforcedPause()"));
        hosting.issue{value: 0.1 ether}(PARENT_NODE, "alice", buyer, "");
    }

    function test_Unpause_restoresEnroll() public {
        vm.startPrank(admin);
        hosting.pause();
        hosting.unpause();
        vm.stopPrank();

        vm.prank(parentOwner);
        hosting.enroll(PARENT_NODE, 5_000_000, 0.001 ether, 0, uint64(block.timestamp + 365 days), 5000);
        assertTrue(hosting.parentOf(PARENT_NODE).active);
    }

    function test_Issue_emptyPaymentBytes_treatedAsEth() public {
        vm.prank(parentOwner);
        hosting.enroll(PARENT_NODE, 5_000_000, 0.001 ether, 0, uint64(block.timestamp + 365 days), 5000);

        vm.deal(buyer, 1 ether);
        vm.prank(buyer);
        // Empty `payment` bytes — issue defaults to the ETH rail. priceEthWei
        // is 0.001 ether, so 0.001 ether exactly is enough.
        hosting.issue{value: 0.001 ether}(PARENT_NODE, "bob", buyer, "");

        bytes32 expected = keccak256(abi.encodePacked(PARENT_NODE, keccak256("bob")));
        (address subOwner,,) = wrapper.getData(uint256(expected));
        assertEq(subOwner, buyer);
    }

    function test_Enroll_revertsOnDouble() public {
        vm.startPrank(parentOwner);
        hosting.enroll(PARENT_NODE, 5_000_000, 0.001 ether, 0, uint64(block.timestamp + 365 days), 5000);
        vm.expectRevert(BankonDomainHosting.AlreadyEnrolled.selector);
        hosting.enroll(PARENT_NODE, 5_000_000, 0.001 ether, 0, uint64(block.timestamp + 365 days), 5000);
        vm.stopPrank();
    }

    function test_Issue_x402Rail() public {
        // Configure facilitator + consumer role on the attestor.
        uint256 facilitatorPk = uint256(keccak256("domain-hosting-facilitator"));
        address facilitator   = vm.addr(facilitatorPk);
        bytes32 consumerRole  = attestor.CONSUMER_ROLE();
        vm.startPrank(admin);
        attestor.setFacilitator(facilitator, true);
        attestor.grantRole(consumerRole, address(hosting));
        vm.stopPrank();

        vm.prank(parentOwner);
        hosting.enroll(PARENT_NODE, 5_000_000, 0.001 ether, 0, uint64(block.timestamp + 365 days), 5000);

        // Build + sign the receipt.
        IBankonX402Attestor.X402Receipt memory r = IBankonX402Attestor.X402Receipt({
            receiptHash: keccak256("hosting-x402-1"),
            claimant:    buyer,
            usd6:        5_000_000,
            nonce:       1,
            expiresAt:   uint64(block.timestamp + 1 hours),
            signature:   ""
        });
        r.signature = X402Sig.sign(vm, facilitatorPk, address(attestor), r);

        bytes memory payment = abi.encodePacked(bytes1(0x02), abi.encode(r));

        vm.prank(buyer);
        hosting.issue(PARENT_NODE, "carol", buyer, payment);

        bytes32 expected = keccak256(abi.encodePacked(PARENT_NODE, keccak256("carol")));
        (address subOwner,,) = wrapper.getData(uint256(expected));
        assertEq(subOwner, buyer);
        assertTrue(attestor.isReceiptSpent(r.receiptHash));
    }

    function test_Issue_x402Rail_revertsOnUnderpaidUsd() public {
        uint256 facilitatorPk = uint256(keccak256("domain-hosting-facilitator-underpay"));
        address facilitator   = vm.addr(facilitatorPk);
        bytes32 consumerRole  = attestor.CONSUMER_ROLE();
        vm.startPrank(admin);
        attestor.setFacilitator(facilitator, true);
        attestor.grantRole(consumerRole, address(hosting));
        vm.stopPrank();

        vm.prank(parentOwner);
        hosting.enroll(PARENT_NODE, 5_000_000, 0.001 ether, 0, uint64(block.timestamp + 365 days), 5000);

        IBankonX402Attestor.X402Receipt memory r = IBankonX402Attestor.X402Receipt({
            receiptHash: keccak256("hosting-x402-underpay"),
            claimant:    buyer,
            usd6:        4_999_999,   // 1 below floor
            nonce:       2,
            expiresAt:   uint64(block.timestamp + 1 hours),
            signature:   ""
        });
        r.signature = X402Sig.sign(vm, facilitatorPk, address(attestor), r);
        bytes memory payment = abi.encodePacked(bytes1(0x02), abi.encode(r));

        vm.prank(buyer);
        vm.expectRevert(bytes("x402 underpay"));
        hosting.issue(PARENT_NODE, "dora", buyer, payment);
    }
}
