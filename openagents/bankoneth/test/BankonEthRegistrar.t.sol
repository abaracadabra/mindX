// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";

import {BankonEthRegistrar, IETHRegistrarController} from "../contracts/BankonEthRegistrar.sol";
import {BankonPriceOracle}                           from "../contracts/BankonPriceOracle.sol";
import {BankonPaymentRouter}                         from "../contracts/BankonPaymentRouter.sol";
import {BankonX402Attestor}                          from "../contracts/BankonX402Attestor.sol";

import {MockEthRegistrarController} from "./mocks/MockEthRegistrarController.sol";
import {X402Sig}                    from "./helpers/X402Sig.sol";

import {IBankonPriceOracle, IBankonPaymentRouter}
    from "../contracts/interfaces/IBankon.sol";
import {IBankonEthRegistrar, IBankonX402Attestor}
    from "../contracts/interfaces/IBankonExtensions.sol";

/// @notice Shared deploy + role-wire harness for the BankonEthRegistrar
///         test contracts. Kept abstract so each test contract is small
///         enough for the via_ir optimizer to fit in the stack.
abstract contract BankonEthRegistrarHarness is Test {
    BankonEthRegistrar         registrar;
    BankonPriceOracle          oracle;
    BankonPaymentRouter        router;
    BankonX402Attestor         attestor;
    MockEthRegistrarController controller;

    address admin    = makeAddr("admin");
    address treasury = makeAddr("treasury");
    address buyer    = makeAddr("buyer");
    address relayer  = makeAddr("relayer");

    uint256 facilitatorPk;
    address facilitator;

    string  constant LABEL    = "newdomain";
    uint256 constant DURATION = 1;
    bytes32 constant SECRET   = bytes32(uint256(0xc0ffee));
    address constant RESOLVER = address(0xdead);

    function setUp() public virtual {
        controller = new MockEthRegistrarController();
        oracle     = new BankonPriceOracle(admin);
        router     = new BankonPaymentRouter(admin);
        attestor   = new BankonX402Attestor(admin);

        registrar = new BankonEthRegistrar(
            admin,
            IETHRegistrarController(address(controller)),
            IBankonPriceOracle(address(oracle)),
            IBankonPaymentRouter(address(router)),
            IBankonX402Attestor(address(attestor))
        );

        bytes32 treasurerRole = router.TREASURER_ROLE();
        bytes32 consumerRole  = attestor.CONSUMER_ROLE();
        bytes32 regTreasurer  = registrar.TREASURER_ROLE();

        facilitatorPk = uint256(keccak256("eth-registrar-facilitator"));
        facilitator   = vm.addr(facilitatorPk);

        vm.startPrank(admin);
        router.grantRole(treasurerRole, address(registrar));
        router.setRecipients(treasury, address(0), address(0), address(0), address(0));
        attestor.grantRole(consumerRole, address(registrar));
        attestor.setFacilitator(facilitator, true);
        registrar.grantRole(regTreasurer, admin);
        vm.stopPrank();
    }

    function _params() internal view returns (IBankonEthRegistrar.CommitParams memory p) {
        p.label                = LABEL;
        p.owner                = buyer;
        p.durationYears        = DURATION;
        p.secret               = SECRET;
        p.resolver             = RESOLVER;
        p.reverseRecord        = false;
        p.ownerControlledFuses = 0;
    }

    /// @dev Commits a fresh params object and warps past `minCommitmentAge`.
    function _committed() internal returns (IBankonEthRegistrar.CommitParams memory p) {
        p = _params();
        registrar.commit(p);
        vm.warp(block.timestamp + controller.MIN_COMMITMENT_AGE() + 1);
    }

    receive() external payable {}
}

/// ─── Admin / quote branches ────────────────────────────────────────

contract BankonEthRegistrarAdminTest is BankonEthRegistrarHarness {
    function test_Constructor_grantsAdmin() public view {
        assertTrue(registrar.hasRole(registrar.DEFAULT_ADMIN_ROLE(), admin));
    }

    function test_SetMarkupBps_byAdmin() public {
        vm.prank(admin);
        registrar.setMarkupBps(2_000);
        assertEq(registrar.markupBps(), 2_000);
    }

    function test_SetMarkupBps_revertsOver5000() public {
        vm.prank(admin);
        vm.expectRevert(bytes("markup > 50%"));
        registrar.setMarkupBps(5_001);
    }

    function test_Quote_returnsEnsPriceWithMarkup() public view {
        (uint256 weiQuoted, uint256 usd6) = registrar.quote(LABEL, DURATION);
        uint256 durationSec = DURATION * 365 days;
        uint256 ensWei      = durationSec * controller.basePricePerSec();
        uint256 expected    = ensWei + (ensWei * registrar.markupBps()) / 10_000;
        assertEq(weiQuoted, expected, "wei");
        assertEq(usd6, oracle.priceUSD(LABEL, DURATION), "usd6 mirrors oracle");
    }

    function test_Quote_revertsOnInvalidLabel() public {
        controller.setInvalid(true);
        vm.expectRevert(BankonEthRegistrar.LabelInvalid.selector);
        registrar.quote(LABEL, DURATION);
    }
}

/// ─── Commit branches ───────────────────────────────────────────────

contract BankonEthRegistrarCommitTest is BankonEthRegistrarHarness {
    function test_Commit_revertsOnInvalidLabel() public {
        controller.setInvalid(true);
        vm.expectRevert(BankonEthRegistrar.LabelInvalid.selector);
        registrar.commit(_params());
    }

    function test_Commit_revertsOnUnavailable() public {
        controller.setUnavailable(true);
        vm.expectRevert(BankonEthRegistrar.LabelUnavailable.selector);
        registrar.commit(_params());
    }

    function test_Commit_storesTimestamp() public {
        IBankonEthRegistrar.CommitParams memory p = _params();
        bytes32 cm = registrar.commit(p);
        assertEq(registrar.committedAt(cm), block.timestamp);
        assertEq(controller.commitments(cm), block.timestamp);
    }
}

/// ─── Reveal: commit window + ETH rail ──────────────────────────────

contract BankonEthRegistrarRevealEthTest is BankonEthRegistrarHarness {
    function test_Reveal_revertsOnCommitmentNotFound() public {
        IBankonEthRegistrar.CommitParams memory p = _params();
        vm.deal(address(this), 1 ether);
        vm.expectRevert(BankonEthRegistrar.CommitmentNotFound.selector);
        registrar.reveal{value: 1 ether}(p, "");
    }

    function test_Reveal_revertsOnCommitmentTooYoung() public {
        IBankonEthRegistrar.CommitParams memory p = _params();
        registrar.commit(p);
        vm.deal(address(this), 1 ether);
        vm.expectRevert(BankonEthRegistrar.CommitmentTooYoung.selector);
        registrar.reveal{value: 1 ether}(p, "");
    }

    function test_Reveal_revertsOnCommitmentTooOld() public {
        IBankonEthRegistrar.CommitParams memory p = _params();
        registrar.commit(p);
        vm.warp(block.timestamp + controller.MAX_COMMITMENT_AGE() + 1);
        vm.deal(address(this), 1 ether);
        vm.expectRevert(BankonEthRegistrar.CommitmentTooOld.selector);
        registrar.reveal{value: 1 ether}(p, "");
    }

    function test_Reveal_ethHappyPath() public {
        IBankonEthRegistrar.CommitParams memory p = _committed();
        (uint256 weiOwed, ) = registrar.quote(LABEL, DURATION);

        vm.deal(buyer, weiOwed);
        vm.prank(buyer);
        registrar.reveal{value: weiOwed}(p, "");

        assertEq(controller.lastOwner(), buyer);
        assertEq(controller.lastDuration(), DURATION * 365 days);
    }

    function test_Reveal_revertsOnEthUnderpayment() public {
        IBankonEthRegistrar.CommitParams memory p = _committed();
        (uint256 weiOwed, ) = registrar.quote(LABEL, DURATION);
        vm.deal(buyer, weiOwed);
        vm.prank(buyer);
        vm.expectRevert(
            abi.encodeWithSelector(BankonEthRegistrar.InsufficientPayment.selector, weiOwed - 1, weiOwed)
        );
        registrar.reveal{value: weiOwed - 1}(p, "");
    }

    function test_Reveal_refundsEthOverpayment() public {
        IBankonEthRegistrar.CommitParams memory p = _committed();
        (uint256 weiOwed, ) = registrar.quote(LABEL, DURATION);

        uint256 overpay = 0.1 ether;
        vm.deal(buyer, weiOwed + overpay);

        uint256 balBefore = buyer.balance;
        vm.prank(buyer);
        registrar.reveal{value: weiOwed + overpay}(p, "");

        assertEq(buyer.balance, balBefore - weiOwed);

        uint256 ensCost = DURATION * 365 days * controller.basePricePerSec();
        uint256 markup  = (ensCost * registrar.markupBps()) / 10_000;
        assertEq(address(registrar).balance, markup, "markup retained");
    }
}

/// ─── Reveal: x402 rail ─────────────────────────────────────────────

contract BankonEthRegistrarRevealX402Test is BankonEthRegistrarHarness {
    function _signReceipt(IBankonX402Attestor.X402Receipt memory r) internal view returns (bytes memory) {
        return X402Sig.sign(vm, facilitatorPk, address(attestor), r);
    }

    function _mkReceipt(bytes32 hash_, uint256 usd6, uint64 nonce_)
        internal view
        returns (IBankonX402Attestor.X402Receipt memory r)
    {
        r.receiptHash = hash_;
        r.claimant    = buyer;
        r.usd6        = usd6;
        r.nonce       = nonce_;
        r.expiresAt   = uint64(block.timestamp + 1 hours);
        r.signature   = _signReceipt(r);
    }

    function test_Reveal_x402HappyPath_relayerCoversEth() public {
        IBankonEthRegistrar.CommitParams memory p = _committed();
        (uint256 weiOwed, uint256 usd6Owed) = registrar.quote(LABEL, DURATION);

        IBankonX402Attestor.X402Receipt memory r = _mkReceipt(keccak256("x402-1"), usd6Owed, 1);
        bytes memory payment = abi.encodePacked(bytes1(0x02), abi.encode(r));

        vm.deal(relayer, weiOwed);
        vm.prank(relayer);
        registrar.reveal{value: weiOwed}(p, payment);

        assertTrue(attestor.isReceiptSpent(r.receiptHash));
    }

    function test_Reveal_x402_revertsOnUnderpaidUsd() public {
        IBankonEthRegistrar.CommitParams memory p = _committed();
        (uint256 weiOwed, uint256 usd6Owed) = registrar.quote(LABEL, DURATION);

        IBankonX402Attestor.X402Receipt memory r = _mkReceipt(keccak256("x402-2"), usd6Owed - 1, 2);
        bytes memory payment = abi.encodePacked(bytes1(0x02), abi.encode(r));

        vm.deal(relayer, weiOwed);
        vm.prank(relayer);
        vm.expectRevert(bytes("x402 underpay"));
        registrar.reveal{value: weiOwed}(p, payment);
    }

    function test_Reveal_x402_revertsOnRelayerUnderfunded() public {
        IBankonEthRegistrar.CommitParams memory p = _committed();
        (uint256 weiOwed, uint256 usd6Owed) = registrar.quote(LABEL, DURATION);

        IBankonX402Attestor.X402Receipt memory r = _mkReceipt(keccak256("x402-3"), usd6Owed, 3);
        bytes memory payment = abi.encodePacked(bytes1(0x02), abi.encode(r));

        vm.deal(relayer, weiOwed - 1);
        vm.prank(relayer);
        vm.expectRevert(bytes("relayer underfunded"));
        registrar.reveal{value: weiOwed - 1}(p, payment);
    }
}

/// ─── Sweep + Pause ─────────────────────────────────────────────────

contract BankonEthRegistrarSweepPauseTest is BankonEthRegistrarHarness {
    function test_Sweep_routesBalanceToRouter() public {
        IBankonEthRegistrar.CommitParams memory p = _committed();
        (uint256 weiOwed, ) = registrar.quote(LABEL, DURATION);
        vm.deal(buyer, weiOwed);
        vm.prank(buyer);
        registrar.reveal{value: weiOwed}(p, "");

        uint256 markup = address(registrar).balance;
        assertGt(markup, 0, "markup retained");

        uint256 treasuryBefore = treasury.balance;
        vm.prank(admin);
        registrar.sweep();

        assertEq(address(registrar).balance, 0, "swept");
        assertEq(treasury.balance - treasuryBefore, markup, "treasury credited");
    }

    function test_Sweep_revertsForNonTreasurer() public {
        bytes32 role = registrar.TREASURER_ROLE();
        vm.expectRevert(
            abi.encodeWithSignature("AccessControlUnauthorizedAccount(address,bytes32)", address(this), role)
        );
        registrar.sweep();
    }

    function test_Sweep_noopOnZeroBalance() public {
        vm.prank(admin);
        registrar.sweep();
        assertEq(address(registrar).balance, 0);
    }

    function test_Pause_blocksCommit() public {
        vm.prank(admin);
        registrar.pause();
        vm.expectRevert(abi.encodeWithSignature("EnforcedPause()"));
        registrar.commit(_params());
    }

    function test_Pause_blocksReveal() public {
        IBankonEthRegistrar.CommitParams memory p = _committed();
        (uint256 weiOwed, ) = registrar.quote(LABEL, DURATION);
        vm.prank(admin);
        registrar.pause();
        vm.deal(buyer, weiOwed);
        vm.prank(buyer);
        vm.expectRevert(abi.encodeWithSignature("EnforcedPause()"));
        registrar.reveal{value: weiOwed}(p, "");
    }

    function test_Unpause_restoresFlow() public {
        vm.prank(admin);
        registrar.pause();
        vm.prank(admin);
        registrar.unpause();
        registrar.commit(_params());
    }
}
