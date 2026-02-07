// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title WETH
 * @notice Wrapped Ether: value-inheritance example; 1:1 ERC20 representation of native ETH
 * @dev Deposit ETH to mint WETH; burn WETH to withdraw ETH. Treasury or any contract
 *      can hold WETH as an ERC20 and use it in allocations (e.g. depositERC20 with WETH address).
 */
contract WETH is ERC20 {
    event Deposit(address indexed dst, uint256 wad);
    event Withdrawal(address indexed src, uint256 wad);

    constructor() ERC20("Wrapped Ether", "WETH") {}

    receive() external payable {
        deposit();
    }

    /**
     * @notice Wrap native ETH into WETH (mint 1:1)
     */
    function deposit() public payable {
        _mint(msg.sender, msg.value);
        emit Deposit(msg.sender, msg.value);
    }

    /**
     * @notice Unwrap WETH to native ETH (burn 1:1)
     */
    function withdraw(uint256 wad) external {
        require(balanceOf(msg.sender) >= wad, "Insufficient balance");
        _burn(msg.sender, wad);
        (bool ok,) = payable(msg.sender).call{value: wad}("");
        require(ok, "WETH: transfer failed");
        emit Withdrawal(msg.sender, wad);
    }
}
