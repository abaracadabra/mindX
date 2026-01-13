// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { ERC20 } from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract MockPair is ERC20 {
    constructor() ERC20("LP", "LP") {}
    function mint(address to, uint256 amt) external { _mint(to, amt); }
}
