// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Test } from "forge-std/Test.sol";

import { iDEBT }                  from "../../src/core/iDEBT.sol";
import { IiDEBT }                 from "../../src/interfaces/IiDEBT.sol";
import { DeltaVerseDebtOracle }   from "../../src/core/DeltaVerseDebtOracle.sol";
import { GlobalDebtStressIndex }  from "../../src/core/GlobalDebtStressIndex.sol";
import { IDebtOracle }            from "../../src/interfaces/IDebtOracle.sol";
import { MockOracleAdapter }      from "../mocks/MockOracleAdapter.sol";
import { MockERC20 }              from "../mocks/MockERC20.sol";

contract iDEBTTest is Test {
    iDEBT                 debtToken;
    DeltaVerseDebtOracle  oracle;
    GlobalDebtStressIndex index;
    MockERC20             usdc;

    address admin   = address(0xA11CE);
    address alice   = address(0xA11);
    address heir1   = address(0xBEEF);
    address heir2   = address(0xCAFE);
    address feeSink = address(0xF33);

    function setUp() public {
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

        usdc.mint(alice, 2_000_000e18);
        vm.prank(alice);
        usdc.approve(address(debtToken), type(uint256).max);
    }

    // ------ Helpers ------

    function _heirLeaf(address s, uint16 bps) internal pure returns (bytes32) {
        return keccak256(abi.encode(s, bps));
    }

    function _merklePair(bytes32 a, bytes32 b) internal pure returns (bytes32) {
        return a < b ? keccak256(abi.encodePacked(a, b)) : keccak256(abi.encodePacked(b, a));
    }

    // ------ Tests ------

    function test_OpenPosition_Succeeds() public {
        // Two-heir Merkle tree.
        bytes32 leaf1 = _heirLeaf(heir1, 6_000);
        bytes32 leaf2 = _heirLeaf(heir2, 4_000);
        bytes32 root  = _merklePair(leaf1, leaf2);

        IiDEBT.Heir[] memory heirs = new IiDEBT.Heir[](2);
        heirs[0] = IiDEBT.Heir({ successor: heir1, sharesBps: 6_000, proofRoot: root });
        heirs[1] = IiDEBT.Heir({ successor: heir2, sharesBps: 4_000, proofRoot: root });

        vm.prank(alice);
        uint256 id = debtToken.openPosition(
            100_000e18,
            uint64(block.timestamp + 365 days),
            30 days,
            heirs
        );

        assertEq(debtToken.ownerOf(id), alice);
        IiDEBT.Position memory p = debtToken.positionOf(id);
        assertEq(p.principal, 100_000e18);
        assertEq(p.holder, alice);
    }

    function test_Inheritance_MaturedHeirCanClaim() public {
        bytes32 leaf1 = _heirLeaf(heir1, 6_000);
        bytes32 leaf2 = _heirLeaf(heir2, 4_000);
        bytes32 root  = _merklePair(leaf1, leaf2);

        IiDEBT.Heir[] memory heirs = new IiDEBT.Heir[](2);
        heirs[0] = IiDEBT.Heir({ successor: heir1, sharesBps: 6_000, proofRoot: root });
        heirs[1] = IiDEBT.Heir({ successor: heir2, sharesBps: 4_000, proofRoot: root });

        vm.prank(alice);
        uint256 id = debtToken.openPosition(
            100_000e18,
            uint64(block.timestamp + 365 days),
            30 days,
            heirs
        );

        // Fast forward past dormancy without any heartbeat.
        vm.warp(block.timestamp + 31 days);

        bytes32[] memory proof1 = new bytes32[](1);
        proof1[0] = leaf2;
        bytes memory hp = abi.encode(heir1, uint16(6_000), proof1);

        vm.prank(heir1);
        uint256 payout = debtToken.claimInheritance(id, hp);

        assertGt(payout, 0);
        assertEq(usdc.balanceOf(heir1), payout);
    }

    function test_Heartbeat_PreventsInheritance() public {
        bytes32 leaf1 = _heirLeaf(heir1, 6_000);
        bytes32 leaf2 = _heirLeaf(heir2, 4_000);
        bytes32 root  = _merklePair(leaf1, leaf2);

        IiDEBT.Heir[] memory heirs = new IiDEBT.Heir[](2);
        heirs[0] = IiDEBT.Heir({ successor: heir1, sharesBps: 6_000, proofRoot: root });
        heirs[1] = IiDEBT.Heir({ successor: heir2, sharesBps: 4_000, proofRoot: root });

        vm.prank(alice);
        uint256 id = debtToken.openPosition(
            100_000e18,
            uint64(block.timestamp + 365 days),
            30 days,
            heirs
        );

        vm.warp(block.timestamp + 20 days);
        vm.prank(alice);
        debtToken.heartbeat(id);

        // Not dormant yet.
        vm.warp(block.timestamp + 25 days); // 45 days from mint, 25 from heartbeat
        bytes32[] memory proof1 = new bytes32[](1);
        proof1[0] = leaf2;
        vm.prank(heir1);
        vm.expectRevert(IiDEBT.NotDormant.selector);
        debtToken.claimInheritance(id, abi.encode(heir1, uint16(6_000), proof1));
    }

    function test_RejectBadShareSum() public {
        bytes32 leaf1 = _heirLeaf(heir1, 5_000);
        bytes32 leaf2 = _heirLeaf(heir2, 4_000); // sums to 9000
        bytes32 root  = _merklePair(leaf1, leaf2);

        IiDEBT.Heir[] memory heirs = new IiDEBT.Heir[](2);
        heirs[0] = IiDEBT.Heir({ successor: heir1, sharesBps: 5_000, proofRoot: root });
        heirs[1] = IiDEBT.Heir({ successor: heir2, sharesBps: 4_000, proofRoot: root });

        vm.prank(alice);
        vm.expectRevert(IiDEBT.InvalidHeirs.selector);
        debtToken.openPosition(1_000e18, uint64(block.timestamp + 1 days), 1 days, heirs);
    }

    function test_MarkToMarket_DecreasesWithStress() public {
        bytes32 leaf1 = _heirLeaf(heir1, 10_000);
        IiDEBT.Heir[] memory heirs = new IiDEBT.Heir[](1);
        heirs[0] = IiDEBT.Heir({ successor: heir1, sharesBps: 10_000, proofRoot: leaf1 });

        vm.prank(alice);
        uint256 id = debtToken.openPosition(
            100_000e18,
            uint64(block.timestamp + 365 days),
            30 days,
            heirs
        );

        uint256 before_ = debtToken.markToMarket(id);

        // Elevate stress dramatically.
        for (uint256 i = 0; i < 7; ++i) {
            address a = oracle.adaptersOf(IDebtOracle.Metric(i))[0];
            MockOracleAdapter(a).set(int256(5e18), 1e18, bytes32(uint256(0xFEED0000 + i)));
        }

        uint256 after_ = debtToken.markToMarket(id);
        assertLt(after_, before_);
    }
}
