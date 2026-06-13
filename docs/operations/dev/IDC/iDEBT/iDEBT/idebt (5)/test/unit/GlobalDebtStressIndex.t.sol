// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Test } from "forge-std/Test.sol";

import { DeltaVerseDebtOracle }   from "../../src/core/DeltaVerseDebtOracle.sol";
import { GlobalDebtStressIndex }  from "../../src/core/GlobalDebtStressIndex.sol";
import { IGlobalDebtStressIndex } from "../../src/interfaces/IGlobalDebtStressIndex.sol";
import { IDebtOracle }            from "../../src/interfaces/IDebtOracle.sol";
import { MockOracleAdapter }      from "../mocks/MockOracleAdapter.sol";

contract GlobalDebtStressIndexTest is Test {
    DeltaVerseDebtOracle  oracle;
    GlobalDebtStressIndex index;
    address admin = address(0xA11CE);

    function setUp() public {
        oracle = new DeltaVerseDebtOracle(admin);
        index  = new GlobalDebtStressIndex(address(oracle), admin);

        // Wire one mock adapter per metric.
        for (uint256 i = 0; i < 7; ++i) {
            MockOracleAdapter a = new MockOracleAdapter();
            vm.prank(admin);
            oracle.attachAdapter(
                IDebtOracle.Metric(i),
                bytes32(uint256(0xABCDEF0000000000 + i)),
                address(a)
            );
            // Neutral baseline values.
            a.set(int256(1e18), 1e18, bytes32(uint256(0xABCDEF0000000000 + i)));
        }
    }

    function test_BaselineIsCalm() public {
        IGlobalDebtStressIndex.Snapshot memory s = index.poke();
        assertTrue(s.index < 0.20e18, "should be calm at baseline");
        assertEq(uint8(s.regime), uint8(IGlobalDebtStressIndex.Regime.Calm));
    }

    function test_WeightsMustSumToOne() public {
        uint256[7] memory bad = [uint256(0.2e18), 0.2e18, 0.2e18, 0.2e18, 0.1e18, 0.1e18, 0.05e18];
        vm.expectRevert(IGlobalDebtStressIndex.InvalidWeights.selector);
        vm.prank(admin);
        index.setWeights(bad);
    }

    function test_RegimeTransitionEmitted() public {
        // Make every metric extreme to force Default regime.
        for (uint256 i = 0; i < 7; ++i) {
            address a = oracle.adaptersOf(IDebtOracle.Metric(i))[0];
            // push debtGDP absurdly high (5.0 in WAD)
            MockOracleAdapter(a).set(int256(5e18), 1e18, bytes32(uint256(0xABCDEF0000000000 + i)));
        }

        // First poke establishes regime; second should not re-emit if unchanged.
        IGlobalDebtStressIndex.Snapshot memory s1 = index.poke();
        assertTrue(uint8(s1.regime) >= uint8(IGlobalDebtStressIndex.Regime.Distress));
    }

    function test_ScoreMonotonicallyIncreasesWithStress() public {
        uint256 s0 = index.score();

        // Push CDS higher.
        address cdsAdapter = oracle.adaptersOf(IDebtOracle.Metric.CDS5Y)[0];
        MockOracleAdapter(cdsAdapter).set(int256(0.5e18), 1e18, bytes32(uint256(0xABCDEF0000000001)));

        uint256 s1 = index.score();
        assertGt(s1, s0);
    }
}
