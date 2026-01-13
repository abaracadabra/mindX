// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { ERC20 } from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import { Ownable } from "@openzeppelin/contracts/access/Ownable.sol";

/// @notice Curve-issued token. Mint/burn is restricted to the associated bonding curve pool.
///         Optionally mints an initial amount to the owner at deployment (configurable by factory).
/// @dev Default name: "REFLECT REWARD", default symbol: "REWARD" (can be overridden in factory)
contract CurveToken is ERC20, Ownable {
    address public pool;

    error NotPool();

    constructor(
        string memory name_,
        string memory symbol_,
        address owner_,
        uint256 initialMintToOwner
    ) ERC20(name_, symbol_) Ownable(owner_) {
        if (initialMintToOwner > 0) {
            _mint(owner_, initialMintToOwner);
        }
    }

    function setPool(address pool_) external onlyOwner {
        pool = pool_;
    }

    function mint(address to, uint256 amount) external {
        if (msg.sender != pool) revert NotPool();
        _mint(to, amount);
    }

    function burn(address from, uint256 amount) external {
        if (msg.sender != pool) revert NotPool();
        _burn(from, amount);
    }
}
