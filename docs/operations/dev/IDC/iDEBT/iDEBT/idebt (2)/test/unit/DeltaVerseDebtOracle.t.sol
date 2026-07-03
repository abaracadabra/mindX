// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Test } from "forge-std/Test.sol";

import { DeltaVerseDebtOracle } from "../../src/core/DeltaVerseDebtOracle.sol";
import { IDebtOracle }          from "../../src/interfaces/IDebtOracle.sol";
import { MockOracleAdapter }    from "../mocks/MockOracleAdapter.sol";

contract DeltaVerseDebtOracleTest is Test {
    DeltaVerseDebtOracle oracle;
    MockOracleAdapter    chainlinkAdapter;
    MockOracleAdapter    pythAdapter;
    MockOracleAdapter    synthetixAdapter;

    address admin  = address(0xA11CE);

    function setUp() public {
        oracle           = new DeltaVerseDebtOracle(admin);
        chainlinkAdapter = new MockOracleAdapter();
        pythAdapter      = new MockOracleAdapter();
        synthetixAdapter = new MockOracleAdapter();

        vm.startPrank(admin);
        oracle.attachAdapter(IDebtOracle.Metric.SovereignDebtGDP, bytes32("CHAINLINK"), address(chainlinkAdapter));
        oracle.attachAdapter(IDebtOracle.Metric.SovereignDebtGDP, bytes32("PYTH"),      address(pythAdapter));
        oracle.attachAdapter(IDebtOracle.Metric.SovereignDebtGDP, bytes32("SYNTHETIX"), address(synthetixAdapter));
        vm.stopPrank();
    }

    function test_Blended_WeightsByConfidence() public {
        chainlinkAdapter.set(1.2e18, 1e18,   bytes32("CHAINLINK"));
        pythAdapter.set     (1.1e18, 0.5e18, bytes32("PYTH"));
        synthetixAdapter.set(1.0e18, 1e18,   bytes32("SYNTHETIX"));

        // Expected = (1.2*1 + 1.1*0.5 + 1.0*1) / (1 + 0.5 + 1) = 2.75/2.5 = 1.1
        int256 blended = oracle.blended(IDebtOracle.Metric.SovereignDebtGDP);
        assertApproxEqAbs(blended, int256(1.1e18), 1e10);
    }

    function test_Latest_PicksFreshestAboveMinConfidence() public {
        chainlinkAdapter.set(1.0e18, 1e18, bytes32("CHAINLINK"));
        vm.warp(block.timestamp + 10);
        pythAdapter.set(1.5e18, 1e18, bytes32("PYTH"));

        IDebtOracle.Observation memory best = oracle.latest(IDebtOracle.Metric.SovereignDebtGDP);
        assertEq(best.source, bytes32("PYTH"));
        assertEq(best.value, int256(1.5e18));
    }

    function test_Blended_RevertsWhenAllStale() public {
        chainlinkAdapter.setStale(1.0e18, 1e18, bytes32("CHAINLINK"), 1);
        pythAdapter.setStale     (1.0e18, 1e18, bytes32("PYTH"),      1);
        synthetixAdapter.setStale(1.0e18, 1e18, bytes32("SYNTHETIX"), 1);
        vm.warp(10_000);

        vm.expectRevert();
        oracle.blended(IDebtOracle.Metric.SovereignDebtGDP);
    }

    function test_MinConfidence_FiltersOutLowConf() public {
        chainlinkAdapter.set(2.0e18, 0.1e18, bytes32("CHAINLINK")); // below floor 0.25
        pythAdapter.set     (1.0e18, 1e18,   bytes32("PYTH"));
        synthetixAdapter.set(1.0e18, 1e18,   bytes32("SYNTHETIX"));

        int256 blended = oracle.blended(IDebtOracle.Metric.SovereignDebtGDP);
        // chainlink is filtered; average is 1e18
        assertEq(blended, int256(1e18));
    }

    function test_OnlyAdminCanAttach() public {
        vm.expectRevert();
        oracle.attachAdapter(IDebtOracle.Metric.CDS5Y, bytes32("X"), address(chainlinkAdapter));
    }
}
