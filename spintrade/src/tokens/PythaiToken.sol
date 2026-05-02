// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/// @title PYTHAI test token for SPINTRADE local testing
/// @notice ERC20 with owner-mint. Local-only — DO NOT deploy to mainnet.
contract PythaiToken is ERC20, Ownable {
    constructor(address initialOwner) ERC20("PYTHAI", "PYTHAI") Ownable(initialOwner) {
        _mint(initialOwner, 1_000_000 ether);
    }

    function mint(address to, uint256 amt) external onlyOwner {
        _mint(to, amt);
    }
}
