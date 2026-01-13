// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { SafeERC20 } from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import { ILiquidityProvisioner } from "../ILiquidityProvisioner.sol";

interface IUniswapV2Router02Like {
    function factory() external view returns (address);
    function addLiquidityETH(
        address token,
        uint amountTokenDesired,
        uint amountTokenMin,
        uint amountETHMin,
        address to,
        uint deadline
    ) external payable returns (uint amountToken, uint amountETH, uint liquidity);
}

interface IUniswapV2FactoryLike {
    function getPair(address tokenA, address tokenB) external view returns (address pair);
}

/// @notice Uniswap V2 liquidity provisioner (Production Ready).
/// @dev Keeps the presale contract small; this module can be swapped/mocked in tests.
///      V2 is the default and production-ready implementation.
contract UniV2Provisioner is ILiquidityProvisioner {
    using SafeERC20 for IERC20;

    error Disabled();
    error UnsupportedMode();
    error ZeroAddress();
    error NoPair();

    /// @notice Adds liquidity via Uniswap V2.
    /// @dev Requires V2 mode, enabled flag, and valid router/WETH addresses.
    function addLiquidity(LiquidityRequest calldata r)
        external
        payable
        override
        returns (address lpTokenOrPosition, uint256 liquidityId)
    {
        if (!r.enabled) revert Disabled();
        if (r.mode != DexMode.V2) revert UnsupportedMode();
        if (!r.v2.enabled) revert Disabled();
        if (r.v2.router == address(0) || r.v2.weth == address(0)) revert ZeroAddress();

        // Transfer tokens from sender to this contract
        IERC20(r.token).safeTransferFrom(msg.sender, address(this), r.tokenAmount);
        IERC20(r.token).safeIncreaseAllowance(r.v2.router, r.tokenAmount);

        // Add liquidity via Uniswap V2 Router
        (,, uint liq) = IUniswapV2Router02Like(r.v2.router).addLiquidityETH{value: r.nativeAmount}(
            r.token,
            r.tokenAmount,
            0, // amountTokenMin - slippage handled by caller
            0, // amountETHMin - slippage handled by caller
            r.recipient,
            r.deadline
        );

        // Get pair address
        address pair = IUniswapV2FactoryLike(IUniswapV2Router02Like(r.v2.router).factory()).getPair(r.token, r.v2.weth);
        if (pair == address(0)) revert NoPair();

        return (pair, liq);
    }
}
