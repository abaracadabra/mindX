// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
//
// bankon_oracle — prices an asset STRAIGHT from its Uniswap liquidity pair
// (no external feed). RAKE + the autoconvert router read this to value accrued
// fees in USD before deciding whether collection beats the chain's cost.
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {IERC20Metadata} from "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";

interface IUniV2Pair {
    function getReserves() external view returns (uint112 r0, uint112 r1, uint32 ts);
    function token0() external view returns (address);
    function token1() external view returns (address);
}

contract bankon_oracle is Ownable {
    /// @notice asset → the Uniswap V2 pair quoting it against USDC.
    mapping(address => address) public pairOf;
    /// @notice the USDC token on this chain (6 decimals), the USD quote asset.
    address public usdc;

    event PairSet(address indexed asset, address indexed pair);
    event UsdcSet(address indexed usdc);

    constructor(address admin_, address usdc_) Ownable(admin_) { usdc = usdc_; }

    function setUsdc(address u) external onlyOwner { usdc = u; emit UsdcSet(u); }
    function setPair(address asset, address pair) external onlyOwner { pairOf[asset] = pair; emit PairSet(asset, pair); }

    /// @notice USD value (6 dp) of `amount` of `asset`, read live from the pair reserves.
    ///         `asset == usdc` returns amount directly. Returns 0 if no pair registered.
    function valueUsd6(address asset, uint256 amount) public view returns (uint256) {
        if (asset == usdc) return amount; // already USDC-6
        address pair = pairOf[asset];
        if (pair == address(0) || amount == 0) return 0;
        (uint112 r0, uint112 r1, ) = IUniV2Pair(pair).getReserves();
        address t0 = IUniV2Pair(pair).token0();
        (uint256 rAsset, uint256 rUsdc) = (t0 == asset) ? (uint256(r0), uint256(r1)) : (uint256(r1), uint256(r0));
        if (rAsset == 0) return 0;
        // price = rUsdc / rAsset (both raw); value = amount * rUsdc / rAsset, decimals cancel
        // because USDC is the output unit (6 dp) directly from reserves.
        return (amount * rUsdc) / rAsset;
    }
}
