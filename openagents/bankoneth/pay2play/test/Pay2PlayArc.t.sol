// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";

import {BankonServiceRegistry}  from "../src/BankonServiceRegistry.sol";
import {BankonEntitlement}      from "../src/BankonEntitlement.sol";
import {Pay2PlayArcSettlement}  from "../src/Pay2PlayArcSettlement.sol";
import {IBankonServiceRegistry, IPay2PlayArcSettlement} from "../src/interfaces/IPay2Play.sol";

contract Pay2PlayArcTest is Test {
    BankonServiceRegistry  registry;
    BankonEntitlement      ent;
    Pay2PlayArcSettlement   arc;

    address admin   = address(0xA11CE);
    address bene    = address(0xB0B);
    address payer   = address(0xCAFE);
    address arcUsdc = address(0x05DC); // USDC on ARC (mock address)
    uint64  arcChainId = 9001;         // ARC chain id (placeholder, settable)

    address facilitator;
    uint256 facilitatorPk;

    bytes32 constant SVC = keccak256("allchain.access");

    bytes32 constant RECEIPT_TYPEHASH = keccak256(
        "ArcReceipt(bytes32 serviceId,address payer,address asset,uint256 amount,uint64 srcChainId,uint64 nonce,uint64 deadline)"
    );

    function setUp() public {
        (facilitator, facilitatorPk) = makeAddrAndKey("arcFacilitator");
        vm.startPrank(admin);
        registry = new BankonServiceRegistry(admin);
        ent      = new BankonEntitlement(admin);
        arc      = new Pay2PlayArcSettlement(admin, registry, ent, arcChainId, arcUsdc);
        ent.grantRole(ent.GRANTER_ROLE(), address(arc));
        arc.setFacilitator(facilitator, true);
        registry.setService(SVC, IBankonServiceRegistry.Service({
            beneficiary: bene, asset: arcUsdc, price: 10e6,
            period: 30 days, tier: 3, active: true, name: "allchain.access"
        }));
        vm.stopPrank();
    }

    function _receipt(uint64 nonce, uint256 amount) internal view returns (IPay2PlayArcSettlement.ArcReceipt memory r) {
        r = IPay2PlayArcSettlement.ArcReceipt({
            serviceId: SVC, payer: payer, asset: arcUsdc, amount: amount,
            srcChainId: arcChainId, nonce: nonce, deadline: uint64(block.timestamp + 1 hours)
        });
    }

    function _sign(IPay2PlayArcSettlement.ArcReceipt memory r) internal view returns (bytes memory) {
        bytes32 structHash = keccak256(abi.encode(
            RECEIPT_TYPEHASH, r.serviceId, r.payer, r.asset, r.amount, r.srcChainId, r.nonce, r.deadline
        ));
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", arc.domainSeparator(), structHash));
        (uint8 v, bytes32 rr, bytes32 ss) = vm.sign(facilitatorPk, digest);
        return abi.encodePacked(rr, ss, v);
    }

    function test_Settle_grantsEntitlement_noTokenMove() public {
        IPay2PlayArcSettlement.ArcReceipt memory r = _receipt(1, 10e6);
        arc.settle(r, facilitator, _sign(r));

        assertTrue(ent.hasAccess(payer, SVC), "payer has access after ARC settlement");
        assertEq(ent.tierOf(payer), 3, "tier");
        assertEq(arc.lastNonce(facilitator), 1, "nonce advanced");
    }

    function test_Replay_reverts() public {
        IPay2PlayArcSettlement.ArcReceipt memory r = _receipt(1, 10e6);
        bytes memory sig = _sign(r);
        arc.settle(r, facilitator, sig);
        vm.expectRevert(); // NonceNotMonotonic (nonce 1 <= lastNonce 1) catches replay first
        arc.settle(r, facilitator, sig);
    }

    function test_NonceMustBeMonotonic() public {
        IPay2PlayArcSettlement.ArcReceipt memory r2 = _receipt(2, 10e6);
        arc.settle(r2, facilitator, _sign(r2));
        IPay2PlayArcSettlement.ArcReceipt memory r1 = _receipt(1, 10e6);
        bytes memory sig1 = _sign(r1); // precompute (signing reads domainSeparator)
        vm.expectRevert(abi.encodeWithSelector(Pay2PlayArcSettlement.NonceNotMonotonic.selector, uint64(1), uint64(2)));
        arc.settle(r1, facilitator, sig1);
    }

    function test_UnknownFacilitator_reverts() public {
        (address rogue, uint256 roguePk) = makeAddrAndKey("rogue");
        IPay2PlayArcSettlement.ArcReceipt memory r = _receipt(1, 10e6);
        bytes32 structHash = keccak256(abi.encode(RECEIPT_TYPEHASH, r.serviceId, r.payer, r.asset, r.amount, r.srcChainId, r.nonce, r.deadline));
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", arc.domainSeparator(), structHash));
        (uint8 v, bytes32 rr, bytes32 ss) = vm.sign(roguePk, digest);
        vm.expectRevert(abi.encodeWithSelector(Pay2PlayArcSettlement.UnknownFacilitator.selector, rogue));
        arc.settle(r, rogue, abi.encodePacked(rr, ss, v));
    }

    function test_WrongChain_and_WrongAsset_revert() public {
        IPay2PlayArcSettlement.ArcReceipt memory r = _receipt(1, 10e6);
        r.srcChainId = 1; // not ARC
        bytes memory sig = _sign(r);
        vm.expectRevert(abi.encodeWithSelector(Pay2PlayArcSettlement.WrongChain.selector, uint64(1), arcChainId));
        arc.settle(r, facilitator, sig);

        IPay2PlayArcSettlement.ArcReceipt memory r2 = _receipt(1, 10e6);
        r2.asset = address(0xDEAD);
        bytes memory sig2 = _sign(r2);
        vm.expectRevert(abi.encodeWithSelector(Pay2PlayArcSettlement.WrongAsset.selector, address(0xDEAD), arcUsdc));
        arc.settle(r2, facilitator, sig2);
    }

    function test_Underpaid_reverts() public {
        IPay2PlayArcSettlement.ArcReceipt memory r = _receipt(1, 9e6); // < 10e6 price
        bytes memory sig = _sign(r);
        vm.expectRevert(abi.encodeWithSelector(Pay2PlayArcSettlement.Underpaid.selector, uint256(9e6), uint256(10e6)));
        arc.settle(r, facilitator, sig);
    }
}
