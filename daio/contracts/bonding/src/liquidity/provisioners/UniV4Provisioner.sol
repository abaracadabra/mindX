// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { ILiquidityProvisioner } from "../ILiquidityProvisioner.sol";

/// @notice Uniswap V4 provisioner extension stub.
/// @dev v4 liquidity management is hook/pool-manager dependent; shipped as a hard-off extension.
///      Can be enabled by implementing full V4 logic and setting enabled flag to true.
///      V4 uses hooks and pool manager architecture with different liquidity model.
contract UniV4Provisioner is ILiquidityProvisioner {
    error NotImplemented();
    error Disabled();

    /// @notice Adds liquidity via Uniswap V4 (stub implementation).
    /// @dev Reverts unless explicitly enabled and fully implemented.
    ///      V4 requires:
    ///      - PoolManager contract
    ///      - Pool ID calculation
    ///      - Hook integration (if applicable)
    ///      - Different liquidity accounting model
    function addLiquidity(LiquidityRequest calldata r) 
        external 
        payable 
        override 
        returns (address lpTokenOrPosition, uint256 liquidityId) 
    {
        if (!r.enabled) revert Disabled();
        if (r.mode != DexMode.V4) revert NotImplemented();
        if (!r.v4.enabled) revert Disabled();
        
        // TODO: Implement V4 liquidity provision
        // Requires:
        // - IPoolManager interface
        // - Pool ID calculation
        // - Hook integration
        // - V4-specific liquidity accounting
        
        revert NotImplemented();
    }
}
