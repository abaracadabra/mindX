// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
//
// bankon_autoconvert — "take any token → settlement" using the Uniswap V3
// SwapRouter (reuse of Uniswap's open-source swap stack = the Uniswap Stack
// Contribution). Charges the golden-ratio BANKON fee (φ, 18 dp, SCIENTIFIC-
// precision math) on the input, routes the fee to RAKE (→ bankon.eth when it
// beats the chain cost), and swaps the remainder to the settlement token for the
// payer's purchase (subname / iNFT / agent listing). Works on every chain that
// hosts a Uniswap V3 router.
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {scientific_math} from "./scientific_math.sol";

interface ISwapRouterV3 {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        address recipient;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }
    function exactInputSingle(ExactInputSingleParams calldata p) external payable returns (uint256 amountOut);
}

contract bankon_autoconvert is Ownable {
    using SafeERC20 for IERC20;

    ISwapRouterV3 public router;   // Uniswap V3 SwapRouter on this chain
    address public rake;           // RAKE collector (golden fee → bankon.eth)
    uint256 public feeDiv;         // golden-fee divisor (φ-1 / feeDiv); 0 disables fee

    event Converted(
        address indexed payer, address indexed tokenIn, uint256 amountIn,
        address indexed tokenOut, uint256 amountOut, uint256 feeWad
    );
    event Config(address router, address rake, uint256 feeDiv);

    constructor(address admin_, ISwapRouterV3 router_, address rake_, uint256 feeDiv_) Ownable(admin_) {
        router = router_; rake = rake_; feeDiv = feeDiv_;
    }

    function configure(ISwapRouterV3 r, address rk, uint256 fd) external onlyOwner {
        router = r; rake = rk; feeDiv = fd; emit Config(address(r), rk, fd);
    }

    /// @notice Pull `amountIn` of `tokenIn`, take the golden fee → RAKE, swap the
    ///         rest to `tokenOut` via Uniswap V3, deliver to `recipient`.
    /// @param poolFee Uniswap V3 pool fee tier (e.g. 500/3000/10000).
    function convert(
        address tokenIn,
        uint256 amountIn,
        address tokenOut,
        uint24 poolFee,
        uint256 minOut,
        address recipient
    ) external returns (uint256 amountOut) {
        IERC20(tokenIn).safeTransferFrom(msg.sender, address(this), amountIn);

        // golden-ratio fee on the input, routed to RAKE (collected home when it beats chain cost)
        uint256 feeWad = feeDiv == 0 ? 0 : scientific_math.goldenFeeWad(amountIn, feeDiv);
        if (feeWad > 0 && rake != address(0)) {
            IERC20(tokenIn).safeTransfer(rake, feeWad);
        }
        uint256 swapAmt = amountIn - feeWad;

        if (tokenIn == tokenOut) {
            IERC20(tokenOut).safeTransfer(recipient, swapAmt);
            amountOut = swapAmt;
        } else {
            IERC20(tokenIn).forceApprove(address(router), swapAmt);
            amountOut = router.exactInputSingle(ISwapRouterV3.ExactInputSingleParams({
                tokenIn: tokenIn, tokenOut: tokenOut, fee: poolFee, recipient: recipient,
                amountIn: swapAmt, amountOutMinimum: minOut, sqrtPriceLimitX96: 0
            }));
        }
        emit Converted(msg.sender, tokenIn, amountIn, tokenOut, amountOut, feeWad);
    }
}
