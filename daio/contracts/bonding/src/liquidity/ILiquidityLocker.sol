// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface ILiquidityLocker {
    function lockLP(IERC20 lpToken, uint256 amount, address beneficiary, uint256 lockDurationDays) external;
    function withdrawLP(IERC20 lpToken) external;
    function getLockDetails(IERC20 lpToken, address beneficiary) external view returns (uint256 lockedAmount, uint256 releaseTime, bool isLocked);
}
