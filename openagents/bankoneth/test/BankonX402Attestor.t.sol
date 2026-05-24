// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {BankonX402Attestor} from "../contracts/BankonX402Attestor.sol";
import {IBankonX402Attestor} from "../contracts/interfaces/IBankonExtensions.sol";

contract BankonX402AttestorTest is Test {
    BankonX402Attestor attestor;
    address admin    = makeAddr("admin");
    address consumer = makeAddr("consumer");
    address claimant = makeAddr("claimant");

    uint256 facilitatorPk;
    address facilitator;

    function setUp() public {
        vm.prank(admin);
        attestor = new BankonX402Attestor(admin);

        facilitatorPk = uint256(keccak256("facilitator-pk"));
        facilitator   = vm.addr(facilitatorPk);

        vm.startPrank(admin);
        attestor.setFacilitator(facilitator, true);
        attestor.grantConsumer(consumer);
        vm.stopPrank();
    }

    function _signReceipt(IBankonX402Attestor.X402Receipt memory r) internal view returns (bytes memory sig) {
        bytes32 typeHash = keccak256(
            "X402Receipt(bytes32 receiptHash,address claimant,uint256 usd6,uint64 nonce,uint64 expiresAt)"
        );
        bytes32 structHash = keccak256(abi.encode(typeHash, r.receiptHash, r.claimant, r.usd6, r.nonce, r.expiresAt));
        bytes32 domain = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("BankonX402Attestor")),
                keccak256(bytes("1")),
                block.chainid,
                address(attestor)
            )
        );
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", domain, structHash));
        (uint8 v, bytes32 r_, bytes32 s) = vm.sign(facilitatorPk, digest);
        sig = abi.encodePacked(r_, s, v);
    }

    function test_VerifyHappyPath() public {
        IBankonX402Attestor.X402Receipt memory r = IBankonX402Attestor.X402Receipt({
            receiptHash: keccak256("receipt-1"),
            claimant:    claimant,
            usd6:        5_000_000,
            nonce:       1,
            expiresAt:   uint64(block.timestamp + 1 hours),
            signature:   ""
        });
        r.signature = _signReceipt(r);

        vm.prank(consumer);
        bool ok = attestor.verify(r);
        assertTrue(ok);
        assertTrue(attestor.isReceiptSpent(r.receiptHash));
    }

    function test_RejectReplay() public {
        IBankonX402Attestor.X402Receipt memory r = IBankonX402Attestor.X402Receipt({
            receiptHash: keccak256("receipt-replay"),
            claimant:    claimant,
            usd6:        1_000_000,
            nonce:       1,
            expiresAt:   uint64(block.timestamp + 1 hours),
            signature:   ""
        });
        r.signature = _signReceipt(r);

        vm.prank(consumer);
        attestor.verify(r);

        vm.prank(consumer);
        vm.expectRevert(
            abi.encodeWithSelector(BankonX402Attestor.ReceiptAlreadyConsumed.selector, r.receiptHash)
        );
        attestor.verify(r);
    }

    function test_RejectExpired() public {
        IBankonX402Attestor.X402Receipt memory r = IBankonX402Attestor.X402Receipt({
            receiptHash: keccak256("expired"),
            claimant:    claimant,
            usd6:        1_000_000,
            nonce:       1,
            expiresAt:   uint64(block.timestamp - 1),
            signature:   ""
        });
        r.signature = _signReceipt(r);

        vm.prank(consumer);
        vm.expectRevert(BankonX402Attestor.ReceiptExpired.selector);
        attestor.verify(r);
    }

    function test_RejectUnregisteredFacilitator() public {
        uint256 rogue = uint256(keccak256("rogue"));
        address rogueAddr = vm.addr(rogue);

        IBankonX402Attestor.X402Receipt memory r = IBankonX402Attestor.X402Receipt({
            receiptHash: keccak256("rogue-receipt"),
            claimant:    claimant,
            usd6:        1_000_000,
            nonce:       1,
            expiresAt:   uint64(block.timestamp + 1 hours),
            signature:   ""
        });
        bytes32 typeHash = keccak256(
            "X402Receipt(bytes32 receiptHash,address claimant,uint256 usd6,uint64 nonce,uint64 expiresAt)"
        );
        bytes32 structHash = keccak256(abi.encode(typeHash, r.receiptHash, r.claimant, r.usd6, r.nonce, r.expiresAt));
        bytes32 domain = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("BankonX402Attestor")),
                keccak256(bytes("1")),
                block.chainid,
                address(attestor)
            )
        );
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", domain, structHash));
        (uint8 v, bytes32 r_, bytes32 s) = vm.sign(rogue, digest);
        r.signature = abi.encodePacked(r_, s, v);

        vm.prank(consumer);
        vm.expectRevert(
            abi.encodeWithSelector(BankonX402Attestor.FacilitatorNotRegistered.selector, rogueAddr)
        );
        attestor.verify(r);
    }

    function test_MonotonicNonce() public {
        IBankonX402Attestor.X402Receipt memory r1 = IBankonX402Attestor.X402Receipt({
            receiptHash: keccak256("r1"),
            claimant:    claimant,
            usd6:        1_000_000,
            nonce:       5,
            expiresAt:   uint64(block.timestamp + 1 hours),
            signature:   ""
        });
        r1.signature = _signReceipt(r1);
        vm.prank(consumer);
        attestor.verify(r1);

        IBankonX402Attestor.X402Receipt memory r2 = IBankonX402Attestor.X402Receipt({
            receiptHash: keccak256("r2"),
            claimant:    claimant,
            usd6:        1_000_000,
            nonce:       4, // OLDER
            expiresAt:   uint64(block.timestamp + 1 hours),
            signature:   ""
        });
        r2.signature = _signReceipt(r2);

        vm.prank(consumer);
        vm.expectRevert(
            abi.encodeWithSelector(BankonX402Attestor.NonceTooOld.selector, uint64(4), uint64(5))
        );
        attestor.verify(r2);
    }
}
