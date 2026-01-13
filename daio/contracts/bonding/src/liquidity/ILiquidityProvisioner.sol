// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Generic liquidity provision interface.
/// @dev Implementations should be simple, auditable, and swappable.
///      Supports Uniswap V2 (production), V3 (extension), and V4 (extension) with on/off switches.
interface ILiquidityProvisioner {
    enum DexMode { V2, V3, V4 }

    struct V2Params {
        address router; // UniswapV2Router02 compatible
        address weth;
        bool enabled;   // On/off switch for V2
    }

    struct V3Params {
        address positionManager; // NonfungiblePositionManager
        address weth;
        uint24 fee; // pool fee tier (500, 3000, 10000)
        int24 tickLower;
        int24 tickUpper;
        bool enabled;   // On/off switch for V3
    }

    struct V4Params {
        address poolManager;
        bytes32 poolId;
        address hook;
        bool enabled;   // On/off switch for V4
    }

    struct LiquidityRequest {
        DexMode mode;
        bool enabled;   // Master on/off switch

        V2Params v2;
        V3Params v3;
        V4Params v4;

        address token;
        uint256 tokenAmount;
        uint256 nativeAmount;
        address recipient;
        uint256 deadline;
    }

    /// @notice Adds liquidity. Implementations MAY revert if mode unsupported.
    /// @return lpTokenOrPosition Address of LP token (v2) or position manager (v3) or pool manager (v4).
    /// @return liquidityId LP token amount (v2) or tokenId (v3) or 0 (v4 stub).
    function addLiquidity(LiquidityRequest calldata r) external payable returns (address lpTokenOrPosition, uint256 liquidityId);
}
