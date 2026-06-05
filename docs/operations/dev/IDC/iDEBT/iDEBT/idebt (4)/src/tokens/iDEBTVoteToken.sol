// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { ERC20 }        from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import { ERC20Permit }  from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import { ERC20Votes }   from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import { AccessControl } from "@openzeppelin/contracts/access/AccessControl.sol";
import { Nonces }       from "@openzeppelin/contracts/utils/Nonces.sol";

/// @title iDEBTVoteToken
/// @notice Governance token fed into the DAIO. In the DELTAVERSE ecosystem
///         this is the locked-checkpoint adapter around PAI / PAIMINT. For
///         standalone deployments the token is mintable by a GOVERNOR role
///         until minting is renounced.
contract iDEBTVoteToken is ERC20, ERC20Permit, ERC20Votes, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    constructor(address admin, uint256 initialSupply)
        ERC20("iDEBT Vote", "iVOTE")
        ERC20Permit("iDEBT Vote")
    {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(MINTER_ROLE, admin);
        if (initialSupply > 0) _mint(admin, initialSupply);
    }

    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        _mint(to, amount);
    }

    // ---- OpenZeppelin v5 hooks ----

    function _update(address from, address to, uint256 value)
        internal
        override(ERC20, ERC20Votes)
    { super._update(from, to, value); }

    function nonces(address owner)
        public
        view
        override(ERC20Permit, Nonces)
        returns (uint256)
    { return super.nonces(owner); }
}
