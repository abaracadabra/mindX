// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { SafeERC20 } from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import { MockFactory } from "./MockFactory.sol";
import { MockPair } from "./MockPair.sol";

contract MockUniswapV2Router {
    using SafeERC20 for IERC20;

    address public immutable factory;
    address public immutable WETH;

    MockPair public immutable pair;

    constructor(address weth_) {
        WETH = weth_;
        MockFactory f = new MockFactory();
        factory = address(f);
        pair = new MockPair();
    }

    function wirePair(address token) external {
        MockFactory(factory).setPair(token, WETH, address(pair));
    }

    function addLiquidityETH(
        address token,
        uint amountTokenDesired,
        uint,
        uint,
        address to,
        uint
    ) external payable returns (uint amountToken, uint amountETH, uint liquidity) {
        // pull tokens
        IERC20(token).safeTransferFrom(msg.sender, address(this), amountTokenDesired);

        // mint LP to `to`
        liquidity = amountTokenDesired; // simplistic
        pair.mint(to, liquidity);

        return (amountTokenDesired, msg.value, liquidity);
    }
}
