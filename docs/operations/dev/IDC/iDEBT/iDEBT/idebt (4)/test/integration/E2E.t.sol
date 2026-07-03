// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Test } from "forge-std/Test.sol";

import { iDEBT }                  from "../../src/core/iDEBT.sol";
import { IiDEBT }                 from "../../src/interfaces/IiDEBT.sol";
import { DeltaVerseDebtOracle }   from "../../src/core/DeltaVerseDebtOracle.sol";
import { GlobalDebtStressIndex }  from "../../src/core/GlobalDebtStressIndex.sol";
import { IDebtOracle }            from "../../src/interfaces/IDebtOracle.sol";
import { X402PaymentGateway }    from "../../src/integrations/X402PaymentGateway.sol";
import { IX402 }                  from "../../src/interfaces/IX402.sol";
import { MockOracleAdapter }      from "../mocks/MockOracleAdapter.sol";
import { MockERC20 }              from "../mocks/MockERC20.sol";

contract E2ETest is Test {
    iDEBT                 debtToken;
    DeltaVerseDebtOracle  oracle;
    GlobalDebtStressIndex index;
    X402PaymentGateway    gate;
    MockERC20             usdc;

    address admin   = address(0xA11CE);
    address alice   = address(0xA11);
    address feeSink = address(0xF33);
    uint256 facilitatorPk = 0xFAC;
    address facilitator;

    bytes32 constant SCOPE = keccak256("iDEBT.open");

    function setUp() public {
        facilitator = vm.addr(facilitatorPk);

        oracle = new DeltaVerseDebtOracle(admin);
        for (uint256 i = 0; i < 7; ++i) {
            MockOracleAdapter a = new MockOracleAdapter();
            vm.prank(admin);
            oracle.attachAdapter(
                IDebtOracle.Metric(i),
                bytes32(uint256(0xFEED0000 + i)),
                address(a)
            );
            a.set(int256(1e18), 1e18, bytes32(uint256(0xFEED0000 + i)));
        }
        index = new GlobalDebtStressIndex(address(oracle), admin);
        usdc  = new MockERC20("USDC", "USDC", 18);
        debtToken = new iDEBT(address(index), address(usdc), feeSink, admin);
        gate  = new X402PaymentGateway(admin);

        vm.startPrank(admin);
        gate.setFacilitator(facilitator, true);
        gate.setPrice(SCOPE, 1_000_000, bytes32("USDCa"));
        debtToken.setX402(address(gate));
        vm.stopPrank();

        usdc.mint(alice, 1_000_000e18);
        vm.prank(alice);
        usdc.approve(address(debtToken), type(uint256).max);
    }

    function _signReceipt(IX402.Receipt memory r) internal view returns (bytes memory) {
        bytes32 structHash = keccak256(abi.encode(
            keccak256(
                "Receipt(address facilitator,address payer,uint256 amount,bytes32 asset,bytes32 scope,uint64 nonce,uint64 expiry,bytes32 algoTxId)"
            ),
            r.facilitator, r.payer, r.amount, r.asset, r.scope, r.nonce, r.expiry, r.algoTxId
        ));
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", gate.domainSeparator(), structHash));
        (uint8 v, bytes32 r_, bytes32 s) = vm.sign(facilitatorPk, digest);
        return abi.encodePacked(r_, s, v);
    }

    function test_EndToEnd_PayThenOpenPosition() public {
        // Alice pays off-chain on Algorand; Parsec signs a receipt.
        IX402.Receipt memory r = IX402.Receipt({
            facilitator: facilitator,
            payer:       alice,
            amount:      2_000_000,
            asset:       bytes32("USDCa"),
            scope:       SCOPE,
            nonce:       1,
            expiry:      uint64(block.timestamp + 1 hours),
            algoTxId:    bytes32("ALGO_TX_1")
        });
        bytes memory sig = _signReceipt(r);
        gate.consume(r, sig);
        assertTrue(gate.hasPaid(alice, SCOPE));

        bytes32 leaf = keccak256(abi.encode(alice, uint16(10_000)));
        IiDEBT.Heir[] memory heirs = new IiDEBT.Heir[](1);
        heirs[0] = IiDEBT.Heir({ successor: alice, sharesBps: 10_000, proofRoot: leaf });

        vm.prank(alice);
        uint256 id = debtToken.openPosition(
            50_000e18,
            uint64(block.timestamp + 180 days),
            14 days,
            heirs
        );
        assertEq(debtToken.ownerOf(id), alice);
    }

    function test_EndToEnd_RevertsWithoutPayment() public {
        bytes32 leaf = keccak256(abi.encode(alice, uint16(10_000)));
        IiDEBT.Heir[] memory heirs = new IiDEBT.Heir[](1);
        heirs[0] = IiDEBT.Heir({ successor: alice, sharesBps: 10_000, proofRoot: leaf });

        vm.prank(alice);
        vm.expectRevert(IiDEBT.PaymentRequired.selector);
        debtToken.openPosition(50_000e18, uint64(block.timestamp + 180 days), 14 days, heirs);
    }
}
