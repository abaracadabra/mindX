// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Test }     from "forge-std/Test.sol";
import { DebtMath } from "../../src/libraries/DebtMath.sol";

contract DebtMathFuzzTest is Test {
    function testFuzz_Clamp(uint256 x) public pure {
        uint256 c = DebtMath.clamp(x);
        assertLe(c, 1e18);
    }

    function testFuzz_WmulIdentity(uint128 a) public pure {
        uint256 z = DebtMath.wmul(uint256(a), 1e18);
        assertEq(z, uint256(a));
    }

    function testFuzz_WdivWmulRoundTrip(uint128 a, uint128 b) public pure {
        vm.assume(b > 0);
        uint256 ratio = DebtMath.wdiv(a, b);
        uint256 back  = DebtMath.wmul(ratio, b);
        // Allow one-wei rounding.
        assertApproxEqAbs(back, uint256(a), 1);
    }

    function testFuzz_LogisticMonotone(int64 x1, int64 x2) public pure {
        vm.assume(x1 < x2);
        uint256 s1 = DebtMath.logistic(int256(x1) * 1e8);
        uint256 s2 = DebtMath.logistic(int256(x2) * 1e8);
        assertLe(s1, s2);
    }

    function testFuzz_LogisticInRange(int64 x) public pure {
        uint256 s = DebtMath.logistic(int256(x));
        assertLe(s, 1e18);
    }

    function testFuzz_BpsToWad(uint16 bps) public pure {
        vm.assume(bps <= 10_000);
        uint256 w = DebtMath.bpsToWad(bps);
        assertLe(w, 1e18);
        assertEq(w, (uint256(bps) * 1e18) / 10_000);
    }
}
