// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
//
// cp2048_constants — the golden-ratio fee constant and fixed-point scales for
// the cypherpunk2048 financial primitives. The BANKON fee is φ (the golden
// ratio) carried to the maximum precision EVM allows today (18 decimals), and
// extendable to 36 decimals via the SCIENTIFIC precision rail (scientific_math).
pragma solidity ^0.8.24;

library cp2048_constants {
    /// @notice 1e18 fixed-point unit (EVM-native max precision).
    uint256 internal constant WAD = 1e18;
    /// @notice 1e36 fixed-point unit — "18 places on both sides" (SCIENTIFIC rail).
    uint256 internal constant E36 = 1e36;

    /// @notice φ = (1+√5)/2 to 18 dp = 1.618033988749894848
    uint256 internal constant PHI_WAD = 1_618033988749894848;
    /// @notice φ to 36 dp (SCIENTIFIC precision) = 1.618033988749894848204586834365638118
    uint256 internal constant PHI_E36 = 1_618033988749894848204586834365638118;

    /// @notice φ-1 = 1/φ to 18 dp = 0.618033988749894848 — the canonical golden fraction.
    uint256 internal constant PHI_MINUS_ONE_WAD = 618033988749894848;
}
