// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Test } from "forge-std/Test.sol";

import { X402PaymentGateway } from "../../src/integrations/X402PaymentGateway.sol";
import { IX402 }              from "../../src/interfaces/IX402.sol";

contract X402PaymentGatewayTest is Test {
    X402PaymentGateway gate;
    address admin = address(0xA11CE);
    uint256 facilitatorPk = 0xA40C17A770;
    address facilitator;
    address payer = address(0xC0FFEE);

    bytes32 constant SCOPE = keccak256("iDEBT.open");
    bytes32 constant ASSET = bytes32("USDCa");

    function setUp() public {
        facilitator = vm.addr(facilitatorPk);
        gate = new X402PaymentGateway(admin);

        vm.startPrank(admin);
        gate.setFacilitator(facilitator, true);
        gate.setPrice(SCOPE, 1_000_000, ASSET); // 1 USDC (6dp)
        vm.stopPrank();
    }

    function _sign(IX402.Receipt memory r) internal view returns (bytes memory) {
        bytes32 structHash = keccak256(abi.encode(
            keccak256(
                "Receipt(address facilitator,address payer,uint256 amount,bytes32 asset,bytes32 scope,uint64 nonce,uint64 expiry,bytes32 algoTxId)"
            ),
            r.facilitator, r.payer, r.amount, r.asset, r.scope, r.nonce, r.expiry, r.algoTxId
        ));
        bytes32 domain = gate.domainSeparator();
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", domain, structHash));
        (uint8 v, bytes32 r_, bytes32 s) = vm.sign(facilitatorPk, digest);
        return abi.encodePacked(r_, s, v);
    }

    function test_Consume_Succeeds() public {
        IX402.Receipt memory r = IX402.Receipt({
            facilitator: facilitator,
            payer:       payer,
            amount:      2_000_000,
            asset:       ASSET,
            scope:       SCOPE,
            nonce:       1,
            expiry:      uint64(block.timestamp + 1 hours),
            algoTxId:    bytes32("ALGO_TX_1")
        });
        bytes memory sig = _sign(r);
        gate.consume(r, sig);
        assertTrue(gate.hasPaid(payer, SCOPE));
    }

    function test_RevertOnReplay() public {
        IX402.Receipt memory r = IX402.Receipt({
            facilitator: facilitator,
            payer:       payer,
            amount:      2_000_000,
            asset:       ASSET,
            scope:       SCOPE,
            nonce:       1,
            expiry:      uint64(block.timestamp + 1 hours),
            algoTxId:    bytes32("ALGO_TX_1")
        });
        bytes memory sig = _sign(r);
        gate.consume(r, sig);
        vm.expectRevert(IX402.ReceiptReplayed.selector);
        gate.consume(r, sig);
    }

    function test_RevertOnExpired() public {
        IX402.Receipt memory r = IX402.Receipt({
            facilitator: facilitator,
            payer:       payer,
            amount:      2_000_000,
            asset:       ASSET,
            scope:       SCOPE,
            nonce:       1,
            expiry:      uint64(block.timestamp + 1 hours),
            algoTxId:    bytes32("ALGO_TX_1")
        });
        bytes memory sig = _sign(r);
        vm.warp(block.timestamp + 2 hours);
        vm.expectRevert(IX402.ReceiptExpired.selector);
        gate.consume(r, sig);
    }

    function test_RevertOnInsufficient() public {
        IX402.Receipt memory r = IX402.Receipt({
            facilitator: facilitator,
            payer:       payer,
            amount:      500_000, // below price
            asset:       ASSET,
            scope:       SCOPE,
            nonce:       1,
            expiry:      uint64(block.timestamp + 1 hours),
            algoTxId:    bytes32("ALGO_TX_1")
        });
        bytes memory sig = _sign(r);
        vm.expectRevert(IX402.InsufficientPayment.selector);
        gate.consume(r, sig);
    }

    function test_RevertOnUnauthorisedFacilitator() public {
        uint256 roguePk = 0xDEAD;
        vm.prank(admin);
        gate.setFacilitator(facilitator, false);

        IX402.Receipt memory r = IX402.Receipt({
            facilitator: vm.addr(roguePk),
            payer:       payer,
            amount:      2_000_000,
            asset:       ASSET,
            scope:       SCOPE,
            nonce:       1,
            expiry:      uint64(block.timestamp + 1 hours),
            algoTxId:    bytes32("X")
        });
        bytes32 structHash = keccak256(abi.encode(
            keccak256(
                "Receipt(address facilitator,address payer,uint256 amount,bytes32 asset,bytes32 scope,uint64 nonce,uint64 expiry,bytes32 algoTxId)"
            ),
            r.facilitator, r.payer, r.amount, r.asset, r.scope, r.nonce, r.expiry, r.algoTxId
        ));
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", gate.domainSeparator(), structHash));
        (uint8 v, bytes32 r_, bytes32 s) = vm.sign(roguePk, digest);
        bytes memory sig = abi.encodePacked(r_, s, v);

        vm.expectRevert(IX402.UnauthorisedFacilitator.selector);
        gate.consume(r, sig);
    }
}
