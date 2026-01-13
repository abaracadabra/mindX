// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { UD60x18, ud, unwrap } from "prb-math/UD60x18.sol";

/// @notice Curve math for protocol-first bonding curves.
///         v1 implements a power curve:
///           spot price: P(S) = k * S^p
///         where k and p are UD60x18 fixed-point.
///         Mint/burn uses integral and inverse integral for accurate multi-unit trades.
library CurveMath {
    struct PowerParams {
        UD60x18 k; // coefficient (reserve per token^(p+1))
        UD60x18 p; // exponent (can be fractional)
    }

    UD60x18 internal constant ONE = UD60x18.wrap(1e18);

    /// @dev Safe pow wrapper for UD60x18:
    ///      - 0^x = 0 for x>0
    ///      - 0^0 = 1
    function _pow(UD60x18 a, UD60x18 b) internal pure returns (UD60x18) {
        uint256 av = unwrap(a);
        uint256 bv = unwrap(b);
        if (av == 0) {
            // b == 0 => 1, else 0
            return bv == 0 ? ONE : UD60x18.wrap(0);
        }
        return a.pow(b);
    }

    /// @notice spot price at supply S: k * S^p
    function spotPrice(PowerParams memory pp, UD60x18 supply18) internal pure returns (UD60x18) {
        // if p==0 => S^0 = 1; handled by pow
        return pp.k.mul(_pow(supply18, pp.p));
    }

    /// @notice cost to mint Δ starting at S:
    ///   cost = k/(p+1) * ( (S+Δ)^(p+1) - S^(p+1) )
    function costToMint(PowerParams memory pp, UD60x18 supply18, UD60x18 delta18) internal pure returns (UD60x18) {
        UD60x18 p1 = pp.p.add(ONE);
        UD60x18 a = _pow(supply18.add(delta18), p1);
        UD60x18 b = _pow(supply18, p1);
        return pp.k.mul(a.sub(b)).div(p1);
    }

    /// @notice refund to burn Δ from supply S:
    ///   refund = k/(p+1) * ( S^(p+1) - (S-Δ)^(p+1) )
    function refundToBurn(PowerParams memory pp, UD60x18 supply18, UD60x18 delta18) internal pure returns (UD60x18) {
        UD60x18 p1 = pp.p.add(ONE);
        UD60x18 a = _pow(supply18, p1);
        UD60x18 b = _pow(supply18.sub(delta18), p1);
        return pp.k.mul(a.sub(b)).div(p1);
    }

    /// @notice Given cost, solve for Δ:
    ///   Δ = ( S^(p+1) + cost*(p+1)/k )^(1/(p+1)) - S
    function mintAmountForCost(PowerParams memory pp, UD60x18 supply18, UD60x18 costReserve18) internal pure returns (UD60x18) {
        if (unwrap(costReserve18) == 0) return UD60x18.wrap(0);

        UD60x18 p1 = pp.p.add(ONE);      // p+1
        UD60x18 invP1 = ONE.div(p1);     // 1/(p+1)

        UD60x18 sPow = _pow(supply18, p1);
        UD60x18 addTerm = costReserve18.mul(p1).div(pp.k);
        UD60x18 term = sPow.add(addTerm);

        UD60x18 newS = _pow(term, invP1);
        if (newS.lte(supply18)) return UD60x18.wrap(0);
        return newS.sub(supply18);
    }
}
