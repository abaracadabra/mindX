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
}
