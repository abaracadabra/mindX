// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface ISpinTradePair {
    event LiquidityAdded(address indexed provider, uint256 amount0, uint256 amount1, uint256 lpMinted);
    event LiquidityRemoved(address indexed provider, uint256 lpBurned, uint256 amount0, uint256 amount1);
    event Swap(
        address indexed trader,
        address indexed tokenIn,
        uint256 amountIn,
        uint256 amountOut,
        address indexed to
    );

    error ZeroAmount();
    error InvalidToken();
    error InsufficientLiquidity();
    error InsufficientOutput();
    error TransferFailed();

    function token0() external view returns (address);
    function token1() external view returns (address);
    function reserves() external view returns (uint256 r0, uint256 r1, uint32 lastUpdate);
    function quote(uint256 amountIn, address tokenIn) external view returns (uint256 amountOut);

    function addLiquidity(uint256 amount0, uint256 amount1, address to) external returns (uint256 lpMinted);
    function removeLiquidity(uint256 lpAmount, address to) external returns (uint256 amount0, uint256 amount1);
    function swap(uint256 amountIn, address tokenIn, uint256 minAmountOut, address to) external returns (uint256 amountOut);
}
