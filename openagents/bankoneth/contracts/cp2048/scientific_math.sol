// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
//
// scientific_math — 36-decimal fixed-point math (the SCIENTIFIC precision rail).
// EVM tokens cap at 18 decimals; this library carries values in 1e36 scale —
// "18 places on both sides" — so golden-ratio fee math keeps accuracy beyond the
// 18-dp ceiling. A value `x` (human units) is represented as `x * 1e36`.
pragma solidity ^0.8.24;

import {cp2048_constants as C} from "./cp2048_constants.sol";

library scientific_math {
    /// @notice multiply two E36-scaled values, result E36-scaled.
    function mul36(uint256 a, uint256 b) internal pure returns (uint256) {
        return (a * b) / C.E36;
    }

    /// @notice divide two E36-scaled values, result E36-scaled.
    function div36(uint256 a, uint256 b) internal pure returns (uint256) {
        return (a * C.E36) / b;
    }

    /// @notice lift a 1e18 (WAD) value into the E36 rail.
    function fromWad(uint256 w) internal pure returns (uint256) {
        return w * 1e18;
    }

    /// @notice lower an E36 value back to 1e18 (WAD), truncating the extra precision.
    function toWad(uint256 x) internal pure returns (uint256) {
        return x / 1e18;
    }

    /// @notice apply the golden-ratio fee fraction (φ-1 = 1/φ ≈ 0.618…) at full
    ///         36-dp precision, then return the fee in the input's own units (1e18-scaled
    ///         amounts in, 1e18-scaled fee out). `feeDiv` scales the golden fraction down
    ///         to a sane protocol micro-fee (e.g. 10_000 → ~0.00618% of amount).
    function goldenFeeWad(uint256 amountWad, uint256 feeDiv) internal pure returns (uint256) {
        if (feeDiv == 0) return 0;
        // amount(E36) * (φ-1)(E36) / E36 / feeDiv  → fee(E36) → toWad
        uint256 amtE36 = fromWad(amountWad);
        uint256 phiFracE36 = fromWad(C.PHI_MINUS_ONE_WAD); // 0.618…e36
        uint256 feeE36 = mul36(amtE36, phiFracE36) / feeDiv;
        return toWad(feeE36);
    }

    /// @notice the BANKON gas-service fee: the golden-ratio markup φ/10 = 0.1618033988749894848
    ///         (16.18%, to 18 dp via the 36-dp rail) on the gas `cost` of one contract call,
    ///         times the number of `sides` that need gas (1 same-chain, 2 cross-chain).
    ///         Scale-free — pass wei (or any 1e18-relative unit) in, same unit out.
    ///         e.g. cost 0.001 ETH, sides 1 → 0.000161803988749894848 ETH.
    function goldenGasFeeWad(uint256 cost, uint256 sides) internal pure returns (uint256) {
        // fee = cost * sides * φ/10. Multiply by PHI_WAD first, divide by 10*WAD last, so
        // the 18 dp survive even for small wei amounts (e.g. 1e15 wei → 161803398874989).
        return cost * sides * C.PHI_WAD / (10 * C.WAD);
    }

    /// @notice φ^tier in WAD (golden priority steps, via the Fibonacci identity φⁿ = Fₙφ + Fₙ₋₁).
    ///         tier 0 = 1.0 (normalized), each step multiplies the fee by φ. Clamps at tier 8.
    function goldenTierMult(uint256 tier) internal pure returns (uint256) {
        if (tier == 0) return 1_000000000000000000;   // φ⁰ = 1
        if (tier == 1) return C.PHI_WAD;              // φ
        if (tier == 2) return 2_618033988749894848;   // φ² = φ+1
        if (tier == 3) return 4_236067977499789696;   // φ³ = 2φ+1
        if (tier == 4) return 6_854101966249684544;   // φ⁴ = 3φ+2
        if (tier == 5) return 11_090169943749474240;  // φ⁵ = 5φ+3
        if (tier == 6) return 17_944271909999158784;  // φ⁶ = 8φ+5
        if (tier == 7) return 29_034441853748633024;  // φ⁷ = 13φ+8
        return 46_978713763747791808;                 // φ⁸ = 21φ+13 (fee still capped at 3× cost)
    }

    /// @notice The BANKON fee for `cost` across `sides` calls at priority `multWad` (1e18 = the
    ///         normalized golden rate φ/10). The fee ratio increases PROPORTIONALLY with priority
    ///         but is hard-capped at 3× the original contract cost (the expedited ceiling). The
    ///         caller supplies `cost` already normalized for chain + usage (e.g. an average basefee).
    function goldenFeePriority(uint256 cost, uint256 sides, uint256 multWad) internal pure returns (uint256) {
        uint256 fee = (cost * sides * C.PHI_WAD / (10 * C.WAD)) * multWad / C.WAD;
        uint256 cap = C.MAX_FEE_NUM * cost * sides;
        return fee > cap ? cap : fee;
    }
}
