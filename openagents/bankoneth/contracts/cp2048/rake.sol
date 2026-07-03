// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
//
// rake — the per-chain fee-collection contract. The golden-ratio BANKON fee
// accrues here (from bankon_autoconvert / the registrars). rake(asset) sweeps it
// to the single immutable owner (bankon.eth) ONLY when the accrued value, priced
// by bankon_oracle straight from the Uniswap pair, beats this chain's cost
// threshold — so collection never costs more than it returns. Deployable to every
// chain; every chain rakes home to the same owner address.
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {bankon_oracle} from "./bankon_oracle.sol";

contract rake is Ownable {
    using SafeERC20 for IERC20;

    /// @notice immutable home — the single owner address all chains rake to (bankon.eth).
    address public immutable BENEFICIARY;
    /// @notice this chain's cost threshold in USD-6: rake only when value > this.
    uint256 public chainCostThresholdUsd6;
    bankon_oracle public oracle;

    event Raked(address indexed asset, uint256 amount, uint256 valueUsd6, address indexed to);
    event ThresholdSet(uint256 usd6);
    event OracleSet(address oracle);

    constructor(address admin_, address beneficiary, bankon_oracle oracle_, uint256 thresholdUsd6_)
        Ownable(admin_)
    {
        require(beneficiary != address(0), "zero");
        BENEFICIARY = beneficiary;
        oracle = oracle_;
        chainCostThresholdUsd6 = thresholdUsd6_;
    }

    function setThreshold(uint256 usd6) external onlyOwner { chainCostThresholdUsd6 = usd6; emit ThresholdSet(usd6); }
    function setOracle(bankon_oracle o) external onlyOwner { oracle = o; emit OracleSet(address(o)); }

    /// @notice USD-6 value currently held in `asset` (for off-chain UIs / keepers).
    function pendingValueUsd6(address asset) public view returns (uint256) {
        return oracle.valueUsd6(asset, IERC20(asset).balanceOf(address(this)));
    }

    /// @notice Sweep `asset` to the beneficiary iff its value beats this chain's cost.
    ///         Permissionless — anyone (a keeper) may trigger; funds only go home.
    function collect(address asset) external returns (bool swept) {
        uint256 bal = IERC20(asset).balanceOf(address(this));
        if (bal == 0) return false;
        uint256 v = oracle.valueUsd6(asset, bal);
        if (v <= chainCostThresholdUsd6) return false; // not worth the gas on this chain
        IERC20(asset).safeTransfer(BENEFICIARY, bal);
        emit Raked(asset, bal, v, BENEFICIARY);
        return true;
    }

    /// @notice Native-ETH variant. Values via the wrapped-native pair if registered
    ///         (pass the WETH address); otherwise sweeps unconditionally above a wei floor.
    function collect_native(address wethForPricing, uint256 weiFloor) external returns (bool swept) {
        uint256 bal = address(this).balance;
        if (bal == 0 || bal < weiFloor) return false;
        if (wethForPricing != address(0)) {
            uint256 v = oracle.valueUsd6(wethForPricing, bal);
            if (v != 0 && v <= chainCostThresholdUsd6) return false;
        }
        (bool ok, ) = BENEFICIARY.call{value: bal}("");
        require(ok, "eth rake failed");
        emit Raked(address(0), bal, 0, BENEFICIARY);
        return true;
    }

    receive() external payable {}
}
