// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { ILiquidityProvisioner } from "../ILiquidityProvisioner.sol";

/// @notice Uniswap V3 provisioner extension stub.
/// @dev Included as an extension placeholder. Intentionally reverts by default for safety.
///      Can be enabled by implementing full V3 logic and setting enabled flag to true.
///      V3 uses concentrated liquidity with tick ranges and position NFTs.
contract UniV3Provisioner is ILiquidityProvisioner {
    error NotImplemented();
    error Disabled();

    /// @notice Adds liquidity via Uniswap V3 (stub implementation).
    /// @dev Reverts unless explicitly enabled and fully implemented.
    ///      V3 requires:
    ///      - NonfungiblePositionManager
    ///      - Fee tier selection (500, 3000, 10000)
    ///      - Tick range calculation (tickLower, tickUpper)
    ///      - Position NFT minting
    function addLiquidity(LiquidityRequest calldata r) 
        external 
        payable 
        override 
        returns (address lpTokenOrPosition, uint256 liquidityId) 
    {
        if (!r.enabled) revert Disabled();
        if (r.mode != DexMode.V3) revert NotImplemented();
        if (!r.v3.enabled) revert Disabled();
        
        // TODO: Implement V3 liquidity provision
        // Requires:
        // - IUniswapV3PositionManager interface
        // - Tick math for range calculation
        // - Position minting logic
        // - NFT tokenId return
        
        revert NotImplemented();
    }
}
