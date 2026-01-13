// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import { Ownable } from "@openzeppelin/contracts/access/Ownable.sol";
import { SafeERC20 } from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import { ILiquidityLocker } from "./ILiquidityLocker.sol";

/// @notice Time-locks LP tokens for a beneficiary.
/// @dev Owner is intended to be the deploying presale contract; ownership should be transferred
///      to the final owner after locks are created.
///      NOTE: For safety, this version does NOT include a generic ERC20 recovery function
///      (recovery is a common rug vector for locked LP).
contract LiquidityLocker is ILiquidityLocker, Ownable {
    using SafeERC20 for IERC20;

    struct LockInfo {
        uint256 amount;
        uint256 releaseTime;
        address beneficiary;
        bool isLocked;
    }

    mapping(address => mapping(address => LockInfo)) public locks;

    event LPLocked(address indexed lpTokenAddress, address indexed beneficiary, uint256 amount, uint256 releaseTime);
    event LPWithdrawn(address indexed lpTokenAddress, address indexed beneficiary, uint256 amount);
    event OwnerNativeBalanceRecovered(address indexed recipient, uint256 amount);

    error LockAlreadyActive(address lpToken, address beneficiary);
    error NoActiveLockOrNotBeneficiary(address lpToken, address caller);
    error LockPeriodNotExpired(uint256 releaseTime, uint256 currentTime);
    error AmountCannotBeZero();
    error DurationCannotBeZero();
    error BeneficiaryCannotBeZeroAddress();
    error InsufficientLPTokensHeldByLocker(uint256 requiredToLock, uint256 actualBalance);

    constructor(address initialOwner) Ownable(initialOwner) {}

    function lockLP(IERC20 lpToken, uint256 amount, address beneficiary, uint256 lockDurationDays) external override {
        if (locks[address(lpToken)][beneficiary].isLocked) revert LockAlreadyActive(address(lpToken), beneficiary);
        if (amount == 0) revert AmountCannotBeZero();
        if (lockDurationDays == 0) revert DurationCannotBeZero();
        if (beneficiary == address(0)) revert BeneficiaryCannotBeZeroAddress();

        uint256 bal = lpToken.balanceOf(address(this));
        if (bal < amount) revert InsufficientLPTokensHeldByLocker(amount, bal);

        uint256 releaseTime = block.timestamp + (lockDurationDays * 1 days);
        locks[address(lpToken)][beneficiary] = LockInfo({
            amount: amount,
            releaseTime: releaseTime,
            beneficiary: beneficiary,
            isLocked: true
        });

        emit LPLocked(address(lpToken), beneficiary, amount, releaseTime);
    }

    function withdrawLP(IERC20 lpToken) external override {
        LockInfo storage li = locks[address(lpToken)][msg.sender];
        if (!li.isLocked || li.beneficiary != msg.sender) revert NoActiveLockOrNotBeneficiary(address(lpToken), msg.sender);
        if (block.timestamp < li.releaseTime) revert LockPeriodNotExpired(li.releaseTime, block.timestamp);

        uint256 amt = li.amount;
        li.isLocked = false;
        li.amount = 0;

        lpToken.safeTransfer(msg.sender, amt);
        emit LPWithdrawn(address(lpToken), msg.sender, amt);
    }

    function getLockDetails(IERC20 lpToken, address beneficiary) external view override returns (uint256, uint256, bool) {
        LockInfo storage li = locks[address(lpToken)][beneficiary];
        return (li.amount, li.releaseTime, li.isLocked);
    }

    receive() external payable {}

    function ownerRecoverNativeBalance(address payable to, uint256 amount) external onlyOwner {
        require(to != address(0), "to=0");
        uint256 bal = address(this).balance;
        uint256 amt = amount == 0 ? bal : amount;
        require(bal >= amt, "insufficient");
        (bool ok,) = to.call{value: amt}("");
        require(ok, "transfer failed");
        emit OwnerNativeBalanceRecovered(to, amt);
    }
}
