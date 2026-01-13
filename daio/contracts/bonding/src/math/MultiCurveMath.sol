// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { UD60x18, ud, unwrap } from "prb-math/UD60x18.sol";
import { CurveType } from "./CurveType.sol";
import { CurveMath } from "./CurveMath.sol";

/// @notice Multi-curve math library supporting different bonding curve types
library MultiCurveMath {
    using CurveMath for CurveMath.PowerParams;

    UD60x18 internal constant ONE = UD60x18.wrap(1e18);

    struct CurveParams {
        CurveType curveType;
        UD60x18 k;
        UD60x18 p;
        UD60x18 a;
        UD60x18 threshold1;
        UD60x18 threshold2;
        UD60x18 k2;
    }

    function spotPrice(CurveParams memory params, UD60x18 supply18) internal pure returns (UD60x18) {
        if (unwrap(supply18) == 0) return UD60x18.wrap(0);
        if (params.curveType == CurveType.POWER) {
            CurveMath.PowerParams memory pp = CurveMath.PowerParams({k: params.k, p: params.p});
            return CurveMath.spotPrice(pp, supply18);
        } else if (params.curveType == CurveType.LINEAR) {
            return params.k.mul(supply18);
        } else if (params.curveType == CurveType.DECELERATING) {
            CurveMath.PowerParams memory pp = CurveMath.PowerParams({k: params.k, p: ud(5e17)});
            return CurveMath.spotPrice(pp, supply18);
        } else if (params.curveType == CurveType.TIERED) {
            if (supply18.lt(params.threshold1)) {
                return params.k.mul(supply18);
            } else if (supply18.lt(params.threshold2)) {
                return params.k.mul(params.threshold1);
            } else {
                UD60x18 flatPrice = params.k.mul(params.threshold1);
                UD60x18 excess = supply18.sub(params.threshold2);
                return flatPrice.add(params.k2.mul(excess));
            }
        }
        revert("Invalid curve type");
    }

    function costToMint(CurveParams memory params, UD60x18 supply18, UD60x18 delta18) internal pure returns (UD60x18) {
        if (unwrap(delta18) == 0) return UD60x18.wrap(0);
        if (params.curveType == CurveType.POWER) {
            CurveMath.PowerParams memory pp = CurveMath.PowerParams({k: params.k, p: params.p});
            return CurveMath.costToMint(pp, supply18, delta18);
        } else if (params.curveType == CurveType.LINEAR) {
            UD60x18 deltaSq = delta18.mul(delta18).div(ONE);
            UD60x18 term1 = deltaSq.div(ud(2e18));
            UD60x18 term2 = supply18.mul(delta18).div(ONE);
            return params.k.mul(term1.add(term2));
        } else if (params.curveType == CurveType.DECELERATING) {
            CurveMath.PowerParams memory pp = CurveMath.PowerParams({k: params.k.mul(ud(2e18)).div(ud(3e18)), p: ud(15e17)});
            return CurveMath.costToMint(pp, supply18, delta18);
        } else if (params.curveType == CurveType.TIERED) {
            return _costToMintTiered(params, supply18, delta18);
        }
        revert("Invalid curve type");
    }

    function refundToBurn(CurveParams memory params, UD60x18 supply18, UD60x18 delta18) internal pure returns (UD60x18) {
        if (unwrap(delta18) == 0) return UD60x18.wrap(0);
        if (supply18.lte(delta18)) return UD60x18.wrap(0);
        UD60x18 newSupply = supply18.sub(delta18);
        return costToMint(params, newSupply, delta18);
    }

    function mintAmountForCost(CurveParams memory params, UD60x18 supply18, UD60x18 costReserve18) internal pure returns (UD60x18) {
        if (unwrap(costReserve18) == 0) return UD60x18.wrap(0);
        if (params.curveType == CurveType.POWER) {
            CurveMath.PowerParams memory pp = CurveMath.PowerParams({k: params.k, p: params.p});
            return CurveMath.mintAmountForCost(pp, supply18, costReserve18);
        } else if (params.curveType == CurveType.LINEAR) {
            UD60x18 sSq = supply18.mul(supply18).div(ONE);
            UD60x18 costTerm = costReserve18.mul(ud(2e18)).div(params.k);
            UD60x18 discriminant = sSq.add(costTerm);
            UD60x18 sqrtDisc = _sqrt(discriminant);
            if (sqrtDisc.lt(supply18)) return UD60x18.wrap(0);
            return sqrtDisc.sub(supply18);
        } else if (params.curveType == CurveType.DECELERATING) {
            CurveMath.PowerParams memory pp = CurveMath.PowerParams({k: params.k.mul(ud(2e18)).div(ud(3e18)), p: ud(15e17)});
            return CurveMath.mintAmountForCost(pp, supply18, costReserve18);
        } else if (params.curveType == CurveType.TIERED) {
            return _mintAmountForCostTiered(params, supply18, costReserve18);
        }
        revert("Invalid curve type");
    }

    function _sqrt(UD60x18 x) private pure returns (UD60x18) {
        if (unwrap(x) == 0) return UD60x18.wrap(0);
        if (unwrap(x) == 1e18) return ONE;
        UD60x18 guess = x.div(ud(2e18));
        for (uint256 i = 0; i < 20; i++) {
            UD60x18 newGuess = guess.add(x.div(guess)).div(ud(2e18));
            if (newGuess.eq(guess)) break;
            guess = newGuess;
        }
        return guess;
    }
    /// @dev Calculate cost to mint for tiered curve (handles phase transitions)
    function _costToMintTiered(CurveParams memory params, UD60x18 supply18, UD60x18 delta18) private pure returns (UD60x18) {
        UD60x18 endSupply = supply18.add(delta18);
        UD60x18 totalCost = UD60x18.wrap(0);
        if (supply18.lt(params.threshold1)) {
            UD60x18 phase1End = endSupply.lt(params.threshold1) ? endSupply : params.threshold1;
            UD60x18 phase1Delta = phase1End.sub(supply18);
            UD60x18 deltaSq = phase1Delta.mul(phase1Delta).div(ONE);
            UD60x18 term1 = deltaSq.div(ud(2e18));
            UD60x18 term2 = supply18.mul(phase1Delta).div(ONE);
            totalCost = totalCost.add(params.k.mul(term1.add(term2)));
        }
        if (endSupply.gt(params.threshold1) && supply18.lt(params.threshold2)) {
            UD60x18 phase2Start = supply18.gt(params.threshold1) ? supply18 : params.threshold1;
            UD60x18 phase2End = endSupply.lt(params.threshold2) ? endSupply : params.threshold2;
            UD60x18 phase2Delta = phase2End.sub(phase2Start);
            UD60x18 flatPrice = params.k.mul(params.threshold1);
            totalCost = totalCost.add(flatPrice.mul(phase2Delta).div(ONE));
        }
        if (endSupply.gt(params.threshold2)) {
            UD60x18 phase3Start = supply18.gt(params.threshold2) ? supply18 : params.threshold2;
            UD60x18 phase3Delta = endSupply.sub(phase3Start);
            UD60x18 flatPrice = params.k.mul(params.threshold1);
            UD60x18 flatCost = flatPrice.mul(phase3Delta).div(ONE);
            UD60x18 offset = phase3Start.sub(params.threshold2);
            UD60x18 deltaSq = phase3Delta.mul(phase3Delta).div(ONE);
            UD60x18 term1 = deltaSq.div(ud(2e18));
            UD60x18 term2 = offset.mul(phase3Delta).div(ONE);
            totalCost = totalCost.add(flatCost).add(params.k2.mul(term1.add(term2)));
        }
        return totalCost;
    }

    /// @dev Iterative solution for tiered curve
    function _mintAmountForCostTiered(CurveParams memory params, UD60x18 supply18, UD60x18 costReserve18) private pure returns (UD60x18) {
        UD60x18 low = UD60x18.wrap(0);
        UD60x18 high = ud(1e24);
        UD60x18 mid;
        for (uint256 i = 0; i < 50; i++) {
            mid = low.add(high).div(ud(2e18));
            UD60x18 cost = costToMint(params, supply18, mid);
            if (cost.eq(costReserve18) || unwrap(high.sub(low)) < 1e15) break;
            if (cost.lt(costReserve18)) {
                low = mid;
            } else {
                high = mid;
            }
        }
        return mid;
    }
}

    /// @dev Calculate cost to mint for tiered curve (handles phase transitions)
    function _costToMintTiered(CurveParams memory params, UD60x18 supply18, UD60x18 delta18) private pure returns (UD60x18) {
        UD60x18 endSupply = supply18.add(delta18);
        UD60x18 totalCost = UD60x18.wrap(0);

        // Phase 1: Linear (0 to threshold1)
        if (supply18.lt(params.threshold1)) {
            UD60x18 phase1End = endSupply.lt(params.threshold1) ? endSupply : params.threshold1;
            UD60x18 phase1Delta = phase1End.sub(supply18);
            // Integral: k * (Δ^2/2 + S*Δ)
            UD60x18 deltaSq = phase1Delta.mul(phase1Delta).div(ONE);
            UD60x18 term1 = deltaSq.div(ud(2e18));
            UD60x18 term2 = supply18.mul(phase1Delta).div(ONE);
            totalCost = totalCost.add(params.k.mul(term1.add(term2)));
        }

        // Phase 2: Flatline (threshold1 to threshold2)
        if (endSupply.gt(params.threshold1) && supply18.lt(params.threshold2)) {
            UD60x18 phase2Start = supply18.gt(params.threshold1) ? supply18 : params.threshold1;
            UD60x18 phase2End = endSupply.lt(params.threshold2) ? endSupply : params.threshold2;
            UD60x18 phase2Delta = phase2End.sub(phase2Start);
            // Constant price: k * threshold1 * Δ
            UD60x18 flatPrice = params.k.mul(params.threshold1);
            totalCost = totalCost.add(flatPrice.mul(phase2Delta).div(ONE));
        }

        // Phase 3: Linear again (threshold2+)
        if (endSupply.gt(params.threshold2)) {
            UD60x18 phase3Start = supply18.gt(params.threshold2) ? supply18 : params.threshold2;
            UD60x18 phase3Delta = endSupply.sub(phase3Start);
            // Integral: flatPrice * Δ + k2 * (Δ^2/2 + (S - threshold2) * Δ)
            UD60x18 flatPrice = params.k.mul(params.threshold1);
            UD60x18 flatCost = flatPrice.mul(phase3Delta).div(ONE);
            
            UD60x18 offset = phase3Start.sub(params.threshold2);
            UD60x18 deltaSq = phase3Delta.mul(phase3Delta).div(ONE);
            UD60x18 term1 = deltaSq.div(ud(2e18));
            UD60x18 term2 = offset.mul(phase3Delta).div(ONE);
            UD60x18 linearCost = params.k2.mul(term1.add(term2));
            
            totalCost = totalCost.add(flatCost).add(linearCost);
        }

        return totalCost;
    }

    /// @dev Iterative solution for tiered curve
    function _mintAmountForCostTiered(CurveParams memory params, UD60x18 supply18, UD60x18 costReserve18) private pure returns (UD60x18) {
        UD60x18 low = UD60x18.wrap(0);
        UD60x18 high = ud(1e24);
        UD60x18 mid;
        
        for (uint256 i = 0; i < 50; i++) {
            mid = low.add(high).div(ud(2e18));
            UD60x18 cost = costToMint(params, supply18, mid);
            if (cost.eq(costReserve18) || unwrap(high.sub(low)) < 1e15) break;
            if (cost.lt(costReserve18)) {
                low = mid;
            } else {
                high = mid;
            }
        }
        return mid;
    }
    /// @dev Calculate cost to mint for tiered curve (handles phase transitions)
    function _costToMintTiered(CurveParams memory params, UD60x18 supply18, UD60x18 delta18) private pure returns (UD60x18) {
        UD60x18 endSupply = supply18.add(delta18);
        UD60x18 totalCost = UD60x18.wrap(0);
        if (supply18.lt(params.threshold1)) {
            UD60x18 phase1End = endSupply.lt(params.threshold1) ? endSupply : params.threshold1;
            UD60x18 phase1Delta = phase1End.sub(supply18);
            UD60x18 deltaSq = phase1Delta.mul(phase1Delta).div(ONE);
            UD60x18 term1 = deltaSq.div(ud(2e18));
            UD60x18 term2 = supply18.mul(phase1Delta).div(ONE);
            totalCost = totalCost.add(params.k.mul(term1.add(term2)));
        }
        if (endSupply.gt(params.threshold1) && supply18.lt(params.threshold2)) {
            UD60x18 phase2Start = supply18.gt(params.threshold1) ? supply18 : params.threshold1;
            UD60x18 phase2End = endSupply.lt(params.threshold2) ? endSupply : params.threshold2;
            UD60x18 phase2Delta = phase2End.sub(phase2Start);
            UD60x18 flatPrice = params.k.mul(params.threshold1);
            totalCost = totalCost.add(flatPrice.mul(phase2Delta).div(ONE));
        }
        if (endSupply.gt(params.threshold2)) {
            UD60x18 phase3Start = supply18.gt(params.threshold2) ? supply18 : params.threshold2;
            UD60x18 phase3Delta = endSupply.sub(phase3Start);
            UD60x18 flatPrice = params.k.mul(params.threshold1);
            UD60x18 flatCost = flatPrice.mul(phase3Delta).div(ONE);
            UD60x18 offset = phase3Start.sub(params.threshold2);
            UD60x18 deltaSq = phase3Delta.mul(phase3Delta).div(ONE);
            UD60x18 term1 = deltaSq.div(ud(2e18));
            UD60x18 term2 = offset.mul(phase3Delta).div(ONE);
            totalCost = totalCost.add(flatCost).add(params.k2.mul(term1.add(term2)));
        }
        return totalCost;
    }

    /// @dev Iterative solution for tiered curve
    function _mintAmountForCostTiered(CurveParams memory params, UD60x18 supply18, UD60x18 costReserve18) private pure returns (UD60x18) {
        UD60x18 low = UD60x18.wrap(0);
        UD60x18 high = ud(1e24);
        UD60x18 mid;
        for (uint256 i = 0; i < 50; i++) {
            mid = low.add(high).div(ud(2e18));
            UD60x18 cost = costToMint(params, supply18, mid);
            if (cost.eq(costReserve18) || unwrap(high.sub(low)) < 1e15) break;
            if (cost.lt(costReserve18)) {
                low = mid;
            } else {
                high = mid;
            }
        }
        return mid;
    }

    /// @dev Calculate cost to mint for tiered curve (handles phase transitions)
    function _costToMintTiered(CurveParams memory params, UD60x18 supply18, UD60x18 delta18) private pure returns (UD60x18) {
        UD60x18 endSupply = supply18.add(delta18);
        UD60x18 totalCost = UD60x18.wrap(0);
        if (supply18.lt(params.threshold1)) {
            UD60x18 phase1End = endSupply.lt(params.threshold1) ? endSupply : params.threshold1;
            UD60x18 phase1Delta = phase1End.sub(supply18);
            UD60x18 deltaSq = phase1Delta.mul(phase1Delta).div(ONE);
            UD60x18 term1 = deltaSq.div(ud(2e18));
            UD60x18 term2 = supply18.mul(phase1Delta).div(ONE);
            totalCost = totalCost.add(params.k.mul(term1.add(term2)));
        }
        if (endSupply.gt(params.threshold1) && supply18.lt(params.threshold2)) {
            UD60x18 phase2Start = supply18.gt(params.threshold1) ? supply18 : params.threshold1;
            UD60x18 phase2End = endSupply.lt(params.threshold2) ? endSupply : params.threshold2;
            UD60x18 phase2Delta = phase2End.sub(phase2Start);
            UD60x18 flatPrice = params.k.mul(params.threshold1);
            totalCost = totalCost.add(flatPrice.mul(phase2Delta).div(ONE));
        }
        if (endSupply.gt(params.threshold2)) {
            UD60x18 phase3Start = supply18.gt(params.threshold2) ? supply18 : params.threshold2;
            UD60x18 phase3Delta = endSupply.sub(phase3Start);
            UD60x18 flatPrice = params.k.mul(params.threshold1);
            UD60x18 flatCost = flatPrice.mul(phase3Delta).div(ONE);
            UD60x18 offset = phase3Start.sub(params.threshold2);
            UD60x18 deltaSq = phase3Delta.mul(phase3Delta).div(ONE);
            UD60x18 term1 = deltaSq.div(ud(2e18));
            UD60x18 term2 = offset.mul(phase3Delta).div(ONE);
            totalCost = totalCost.add(flatCost).add(params.k2.mul(term1.add(term2)));
        }
        return totalCost;
    }

    /// @dev Iterative solution for tiered curve
    function _mintAmountForCostTiered(CurveParams memory params, UD60x18 supply18, UD60x18 costReserve18) private pure returns (UD60x18) {
        UD60x18 low = UD60x18.wrap(0);
        UD60x18 high = ud(1e24);
        UD60x18 mid;
        for (uint256 i = 0; i < 50; i++) {
            mid = low.add(high).div(ud(2e18));
            UD60x18 cost = costToMint(params, supply18, mid);
            if (cost.eq(costReserve18) || unwrap(high.sub(low)) < 1e15) break;
            if (cost.lt(costReserve18)) {
                low = mid;
            } else {
                high = mid;
            }
        }
        return mid;
    }

}
