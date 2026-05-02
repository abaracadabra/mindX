// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {Vm}   from "forge-std/Vm.sol";

import {X402Receipt}            from "../X402Receipt.sol";
import {IBankonPaymentRouter}   from "../../ens/v1/interfaces/IBankon.sol";

/// @notice EOA signer test fixture. Tests the EVM half of the cross-chain pair.
///         The AVM half is tested separately under `daio/contracts/algorand/`.
contract X402ReceiptTest is Test {
    X402Receipt internal receipt;
    address internal admin = address(0xA11CE);
    Vm.Wallet internal payer;

    address internal payee   = address(0xBEEF);
    address internal asset   = address(0xC0DE);
    uint256 internal amount  = 2_000_000;            // 2 USDC
    bytes32 internal resourceHash = keccak256("https://example.com/paid");
    bytes32 internal nonce        = keccak256("nonce-1");

    function setUp() public {
        payer = vm.createWallet("payer");
        // Deploy with no router cascade — keeps the test self-contained.
        receipt = new X402Receipt(admin, IBankonPaymentRouter(address(0)));
    }

    function _signAs(Vm.Wallet memory w, bytes32 receiptHash) internal returns (bytes memory) {
        bytes32 digest = keccak256(
            abi.encodePacked("\x19Ethereum Signed Message:\n32", receiptHash)
        );
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(w, digest);
        return abi.encodePacked(r, s, v);
    }

    function test_records_valid_receipt_with_eoa_signature() public {
        bytes32 h = receipt.canonicalReceiptHash(
            payer.addr, payee, asset, amount, resourceHash, nonce
        );
        bytes memory sig = _signAs(payer, h);

        vm.recordLogs();
        receipt.recordX402Receipt(
            h, payer.addr, payee, asset, amount, resourceHash, nonce, sig
        );
        Vm.Log[] memory logs = vm.getRecordedLogs();

        assertTrue(receipt.seenReceipt(h), "receipt not marked seen");
        assertEq(logs.length, 1, "exactly one event expected");
        assertEq(logs[0].topics[0], keccak256(
            "X402ReceiptRecorded(bytes32,bytes32,address,address,address,uint256,uint64,uint64)"
        ), "event signature mismatch");
        assertEq(logs[0].topics[1], h, "indexed receiptHash mismatch");
        assertEq(logs[0].topics[2], resourceHash, "indexed resourceHash mismatch");
    }

    function test_rejects_duplicate_receipt() public {
        bytes32 h = receipt.canonicalReceiptHash(
            payer.addr, payee, asset, amount, resourceHash, nonce
        );
        bytes memory sig = _signAs(payer, h);
        receipt.recordX402Receipt(h, payer.addr, payee, asset, amount, resourceHash, nonce, sig);

        vm.expectRevert(abi.encodeWithSelector(X402Receipt.ReceiptAlreadyRecorded.selector, h));
        receipt.recordX402Receipt(h, payer.addr, payee, asset, amount, resourceHash, nonce, sig);
    }

    function test_rejects_mismatched_receipt_hash() public {
        bytes32 wrong = keccak256("not the canonical hash");
        bytes memory sig = _signAs(payer, wrong);

        vm.expectRevert(); // ReceiptHashMismatch — selector args are dynamic
        receipt.recordX402Receipt(
            wrong, payer.addr, payee, asset, amount, resourceHash, nonce, sig
        );
    }

    function test_rejects_signature_from_wrong_signer() public {
        bytes32 h = receipt.canonicalReceiptHash(
            payer.addr, payee, asset, amount, resourceHash, nonce
        );
        Vm.Wallet memory attacker = vm.createWallet("attacker");
        bytes memory badSig = _signAs(attacker, h);

        vm.expectRevert(X402Receipt.InvalidSignature.selector);
        receipt.recordX402Receipt(
            h, payer.addr, payee, asset, amount, resourceHash, nonce, badSig
        );
    }

    function test_rejects_zero_payer() public {
        bytes32 h = receipt.canonicalReceiptHash(
            address(0), payee, asset, amount, resourceHash, nonce
        );
        vm.expectRevert(X402Receipt.ZeroPayer.selector);
        receipt.recordX402Receipt(
            h, address(0), payee, asset, amount, resourceHash, nonce, hex""
        );
    }

    /// @notice Demonstrates the canonical hash is deterministic across calls
    ///         given the same fields on the same chain — the property the
    ///         off-chain composer relies on when constructing receipts.
    function test_canonical_hash_is_deterministic() public view {
        bytes32 h1 = receipt.canonicalReceiptHash(
            payer.addr, payee, asset, amount, resourceHash, nonce
        );
        bytes32 h2 = receipt.canonicalReceiptHash(
            payer.addr, payee, asset, amount, resourceHash, nonce
        );
        assertEq(h1, h2, "canonical hash should be stable");
    }
}
