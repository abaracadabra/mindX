// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";

import {BankonOffchainRegistrar}  from "../contracts/BankonOffchainRegistrar.sol";
import {BankonPriceOracle}        from "../contracts/BankonPriceOracle.sol";
import {BankonPaymentRouter}      from "../contracts/BankonPaymentRouter.sol";
import {BankonX402Attestor}       from "../contracts/BankonX402Attestor.sol";

import {IBankonPriceOracle, IBankonPaymentRouter} from "../contracts/interfaces/IBankon.sol";
import {IBankonX402Attestor}                       from "../contracts/interfaces/IBankonExtensions.sol";

import {X402Sig} from "./helpers/X402Sig.sol";

abstract contract OffchainRegistrarHarness is Test {
    BankonOffchainRegistrar reg;
    BankonPriceOracle       oracle;
    BankonPaymentRouter     router;
    BankonX402Attestor      attestor;

    address admin    = makeAddr("admin");
    address treasury = makeAddr("treasury");
    address buyer    = makeAddr("buyer");

    uint256 facilitatorPk;
    address facilitator;

    bytes32 constant BANKON_ETH = keccak256(abi.encodePacked(
        keccak256(abi.encodePacked(bytes32(0), keccak256("eth"))),
        keccak256("bankon")
    ));

    function setUp() public virtual {
        oracle   = new BankonPriceOracle(admin);
        router   = new BankonPaymentRouter(admin);
        attestor = new BankonX402Attestor(admin);

        reg = new BankonOffchainRegistrar(
            admin, BANKON_ETH,
            IBankonPriceOracle(address(oracle)),
            IBankonPaymentRouter(address(router)),
            IBankonX402Attestor(address(attestor))
        );

        bytes32 treasurerRole = router.TREASURER_ROLE();
        bytes32 consumerRole  = attestor.CONSUMER_ROLE();
        bytes32 regTreasurer  = reg.TREASURER_ROLE();

        facilitatorPk = uint256(keccak256("offchain-facilitator"));
        facilitator   = vm.addr(facilitatorPk);

        vm.startPrank(admin);
        router.grantRole(treasurerRole, address(reg));
        router.setRecipients(treasury, address(0), address(0), address(0), address(0));
        attestor.grantRole(consumerRole, address(reg));
        attestor.setFacilitator(facilitator, true);
        reg.grantRole(regTreasurer, admin);
        vm.stopPrank();
    }
}

// ── ETH rail + dup guard + length checks ────────────────────────

contract OffchainRegistrarClaimTest is OffchainRegistrarHarness {
    function test_Claim_ethRail_happyPath() public {
        vm.deal(buyer, 1 ether);
        vm.prank(buyer);

        vm.expectEmit(true, true, true, false);
        emit BankonOffchainRegistrar.OffchainSubnameClaimed(
            BANKON_ETH,
            keccak256(bytes("alice")),
            "alice",
            buyer,
            "bafy...stub",
            oracle.priceUSD("alice", 1)
        );
        reg.claim{value: 0.001 ether}("alice", buyer, "bafy...stub", "");
    }

    function test_Claim_revertsOnEmptyLabel() public {
        vm.deal(buyer, 1 ether);
        vm.prank(buyer);
        vm.expectRevert(BankonOffchainRegistrar.LabelEmpty.selector);
        reg.claim{value: 0.001 ether}("", buyer, "", "");
    }

    function test_Claim_revertsOnShortLabel() public {
        vm.deal(buyer, 1 ether);
        vm.prank(buyer);
        vm.expectRevert(BankonOffchainRegistrar.LabelTooShort.selector);
        reg.claim{value: 0.001 ether}("ab", buyer, "", "");
    }

    function test_Claim_revertsOnDuplicateLabel() public {
        vm.deal(buyer, 1 ether);
        vm.startPrank(buyer);
        reg.claim{value: 0.001 ether}("alice", buyer, "", "");
        vm.expectRevert(BankonOffchainRegistrar.LabelAlreadyClaimed.selector);
        reg.claim{value: 0.001 ether}("alice", buyer, "", "");
        vm.stopPrank();
    }

    function test_Claim_revertsOnZeroEth() public {
        vm.deal(buyer, 1 ether);
        vm.prank(buyer);
        vm.expectRevert(
            abi.encodeWithSelector(BankonOffchainRegistrar.InsufficientPayment.selector, 0, 1)
        );
        reg.claim("alice", buyer, "", "");
    }
}

// ── x402 rail ───────────────────────────────────────────────────

contract OffchainRegistrarX402Test is OffchainRegistrarHarness {
    function _mkReceipt(bytes32 hash_, uint256 usd6, uint64 nonce_)
        internal view
        returns (IBankonX402Attestor.X402Receipt memory r)
    {
        r.receiptHash = hash_;
        r.claimant    = buyer;
        r.usd6        = usd6;
        r.nonce       = nonce_;
        r.expiresAt   = uint64(block.timestamp + 1 hours);
        r.signature   = X402Sig.sign(vm, facilitatorPk, address(attestor), r);
    }

    function test_Claim_x402_happyPath() public {
        uint256 usd6 = oracle.priceUSD("alice", 1);
        IBankonX402Attestor.X402Receipt memory rcpt = _mkReceipt(keccak256("offchain-1"), usd6, 1);
        bytes memory payment = abi.encodePacked(bytes1(0x02), abi.encode(rcpt));

        vm.prank(buyer);
        reg.claim("alice", buyer, "bafy...rec", payment);

        assertTrue(attestor.isReceiptSpent(rcpt.receiptHash));
    }

    function test_Claim_x402_revertsOnUnderpay() public {
        uint256 usd6 = oracle.priceUSD("alice", 1);
        IBankonX402Attestor.X402Receipt memory rcpt = _mkReceipt(keccak256("offchain-2"), usd6 - 1, 2);
        bytes memory payment = abi.encodePacked(bytes1(0x02), abi.encode(rcpt));

        vm.prank(buyer);
        vm.expectRevert(bytes("x402 underpay"));
        reg.claim("alice", buyer, "", payment);
    }
}

// ── Admin / sweep / pause ───────────────────────────────────────

contract OffchainRegistrarAdminTest is OffchainRegistrarHarness {
    function test_SetMarkupBps_byAdmin() public {
        vm.prank(admin);
        reg.setMarkupBps(2_000);
        assertEq(reg.markupBps(), 2_000);
    }

    function test_SetMarkupBps_revertsOver5000() public {
        vm.prank(admin);
        vm.expectRevert(bytes("markup > 50%"));
        reg.setMarkupBps(5_001);
    }

    function test_Sweep_routesEthToRouter() public {
        // Seed via a claim.
        vm.deal(buyer, 1 ether);
        vm.prank(buyer);
        reg.claim{value: 0.001 ether}("alice", buyer, "", "");

        uint256 bal = address(reg).balance;
        assertGt(bal, 0);

        uint256 treasuryBefore = treasury.balance;
        vm.prank(admin);
        reg.sweep();
        assertEq(address(reg).balance, 0);
        assertEq(treasury.balance - treasuryBefore, bal);
    }

    function test_Pause_blocksClaim() public {
        vm.prank(admin);
        reg.pause();
        vm.deal(buyer, 1 ether);
        vm.prank(buyer);
        vm.expectRevert(abi.encodeWithSignature("EnforcedPause()"));
        reg.claim{value: 0.001 ether}("alice", buyer, "", "");
    }

    function test_Quote_mirrorsOracle() public view {
        assertEq(reg.quote("alice"), oracle.priceUSD("alice", 1));
    }
}
