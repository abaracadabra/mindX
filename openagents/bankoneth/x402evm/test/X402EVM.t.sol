// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {X402ChainRegistry} from "../src/X402ChainRegistry.sol";
import {X402EVMFacilitator} from "../src/X402EVMFacilitator.sol";
import {IX402EVM, X402EVMReceipt} from "../src/interfaces/IX402EVM.sol";

contract X402EVMTest is Test {
    address admin = address(0xA11CE);
    uint256 fpk = 0xFAC11; address facilitator;
    address payer = address(0xBEEF);

    // canonical USDC on the two headline rails
    uint64 constant BASE = 8453;     address constant USDC_BASE = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    uint64 constant ARC  = 5042002;  address constant USDC_ARC  = 0x3600000000000000000000000000000000000000;

    X402ChainRegistry reg;
    X402EVMFacilitator fac;

    function setUp() public {
        facilitator = vm.addr(fpk);
        reg = new X402ChainRegistry(admin);
        vm.startPrank(admin);
        reg.setChain(BASE, USDC_BASE);
        reg.setChain(ARC, USDC_ARC);
        fac = new X402EVMFacilitator(admin, reg);
        fac.setFacilitator(facilitator, true);
        vm.stopPrank();
    }

    function _receipt(uint64 chainId, address asset, uint64 nonce) internal view returns (X402EVMReceipt memory) {
        return X402EVMReceipt({
            resourceHash: keccak256("mindx://service/inference"),
            payer: payer, asset: asset, amount: 1_000000, // $1 USDC (6dp)
            srcChainId: chainId, nonce: nonce, expiresAt: uint64(block.timestamp + 600)
        });
    }
    function _sig(X402EVMReceipt memory r) internal view returns (bytes memory) {
        (uint8 v, bytes32 s1, bytes32 s2) = vm.sign(fpk, fac.digestOf(r));
        return abi.encodePacked(s1, s2, v);
    }

    function test_settle_on_base() public {
        X402EVMReceipt memory r = _receipt(BASE, USDC_BASE, 1);
        bytes32 d = fac.settle(r, facilitator, _sig(r));   // permissionless submit
        assertTrue(fac.isSettled(d), "base x402 settled");
        assertEq(fac.lastNonce(facilitator), 1);
    }

    function test_settle_on_arc() public {
        X402EVMReceipt memory r = _receipt(ARC, USDC_ARC, 1);
        bytes32 d = fac.settle(r, facilitator, _sig(r));
        assertTrue(fac.isSettled(d), "arc x402 settled");
    }

    function test_replay_and_nonce_guards() public {
        X402EVMReceipt memory r = _receipt(BASE, USDC_BASE, 5);
        bytes memory sig = _sig(r);
        fac.settle(r, facilitator, sig);
        assertTrue(fac.isSettled(fac.digestOf(r)));
        // replay (same receipt) is caught by the monotonic-nonce guard — the first line of defense;
        // the spent-digest set is belt-and-suspenders behind it.
        vm.expectRevert(X402EVMFacilitator.stale_nonce.selector);
        fac.settle(r, facilitator, sig);
        // any receipt at a stale nonce is rejected
        X402EVMReceipt memory r2 = _receipt(BASE, USDC_BASE, 4); r2.resourceHash = keccak256("other");
        bytes memory sig2 = _sig(r2);
        vm.expectRevert(X402EVMFacilitator.stale_nonce.selector);
        fac.settle(r2, facilitator, sig2);
        // a higher nonce proceeds
        X402EVMReceipt memory r3 = _receipt(BASE, USDC_BASE, 6); r3.resourceHash = keccak256("next");
        bytes memory sig3 = _sig(r3);
        fac.settle(r3, facilitator, sig3);
        assertEq(fac.lastNonce(facilitator), 6);
    }

    function test_rejects_unregistered_chain_or_asset() public {
        X402EVMReceipt memory r = _receipt(BASE, address(0xDEAD), 1); // wrong asset on Base
        bytes memory sig = _sig(r);
        vm.expectRevert(X402EVMFacilitator.bad_chain_or_asset.selector);
        fac.settle(r, facilitator, sig);
    }

    function test_rejects_expired_and_unknown_facilitator() public {
        X402EVMReceipt memory r = _receipt(BASE, USDC_BASE, 1);
        r.expiresAt = uint64(block.timestamp - 1);
        bytes memory sig = _sig(r);
        vm.expectRevert(X402EVMFacilitator.expired.selector);
        fac.settle(r, facilitator, sig);

        X402EVMReceipt memory ok = _receipt(BASE, USDC_BASE, 1);
        bytes memory sigok = _sig(ok);
        vm.expectRevert(X402EVMFacilitator.not_facilitator.selector);
        fac.settle(ok, address(0x1234), sigok);
    }

    function test_rejects_forged_signature() public {
        X402EVMReceipt memory r = _receipt(BASE, USDC_BASE, 1);
        (uint8 v, bytes32 s1, bytes32 s2) = vm.sign(0xBAD, fac.digestOf(r)); // not the facilitator
        vm.expectRevert(X402EVMFacilitator.bad_sig.selector);
        fac.settle(r, facilitator, abi.encodePacked(s1, s2, v));
    }
}
