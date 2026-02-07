// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

/**
 * @title XMindTreasuryReceiver
 * @notice Recipient for DAIO treasury allocations (BoardroomExtension / DAIOGovernance); hold and withdraw funds
 * @dev Use this contract address as recipient in treasury allocation proposals; owner can withdraw to mindX ops
 */
contract XMindTreasuryReceiver is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    event Received(address indexed from, uint256 amount);
    event WithdrawNative(address indexed to, uint256 amount);
    event WithdrawToken(address indexed token, address indexed to, uint256 amount);

    receive() external payable {
        emit Received(msg.sender, msg.value);
    }

    function withdrawNative(address payable to, uint256 amount) external onlyOwner nonReentrant {
        require(to != address(0), "Invalid recipient");
        require(address(this).balance >= amount, "Insufficient balance");
        (bool sent, ) = to.call{value: amount}("");
        require(sent, "Transfer failed");
        emit WithdrawNative(to, amount);
    }

    function withdrawToken(address token, address to, uint256 amount) external onlyOwner nonReentrant {
        require(token != address(0) && to != address(0), "Invalid address");
        IERC20(token).safeTransfer(to, amount);
        emit WithdrawToken(token, to, amount);
    }

    function balanceNative() external view returns (uint256) {
        return address(this).balance;
    }

    function balanceToken(address token) external view returns (uint256) {
        return token == address(0) ? 0 : IERC20(token).balanceOf(address(this));
    }
}
