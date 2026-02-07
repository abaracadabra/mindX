// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title CustomERC20Minter
 * @notice ERC20 token with minter role for use by Treasury or governance
 * @dev Grant MINTER_ROLE to Treasury, governance, or other contracts to allow minting.
 *      Example working contracts can be substituted or extended later.
 */
contract CustomERC20Minter is ERC20, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    constructor(
        string memory name_,
        string memory symbol_,
        address defaultAdmin
    ) ERC20(name_, symbol_) {
        require(defaultAdmin != address(0), "Invalid admin");
        _grantRole(DEFAULT_ADMIN_ROLE, defaultAdmin);
        _grantRole(MINTER_ROLE, defaultAdmin);
    }

    /**
     * @notice Mint tokens to an address (caller must have MINTER_ROLE)
     */
    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        _mint(to, amount);
    }

    /**
     * @notice Burn tokens from caller
     */
    function burn(uint256 amount) external {
        _burn(msg.sender, amount);
    }
}
