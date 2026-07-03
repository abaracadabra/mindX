// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
//
// scientific_token (SCIENTIFIC / SCIEN) — the cypherpunk2048 precision rail.
// A fixed-supply ERC-20 (18 decimals) whose accounting partners with
// scientific_math's 36-dp rail for golden-ratio fee precision. Properties the
// standard requires:
//   • total supply minted ONCE to a single issuance address (constructor);
//   • the beneficiary address is held in IMMUTABLE storage (never mutable);
//   • Ownable control is renounced after issuance + Uniswap pairing;
//   • tradeable + Uniswap-pairable (plain ERC-20, no transfer hooks/taxes);
//   • self_purge(): permissionless sweep of ANY token/ETH the contract holds —
//     funds can only ever leave to the immutable beneficiary (no other path).
pragma solidity ^0.8.24;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

contract scientific_token is ERC20, Ownable {
    using SafeERC20 for IERC20;

    /// @notice The only address funds purged from this contract can ever reach.
    ///         Immutable — set once, derived from the owner's public key (bankon.eth).
    address public immutable BENEFICIARY;

    event SelfPurged(address indexed asset, uint256 amount, address indexed to);

    /// @param issuance        single address that receives the entire supply
    /// @param supply          fixed total supply (18 decimals)
    /// @param beneficiary     immutable self_purge beneficiary (e.g. bankon.eth owner)
    constructor(address issuance, uint256 supply, address beneficiary)
        ERC20("SCIENTIFIC", "SCIEN") Ownable(msg.sender)
    {
        require(issuance != address(0) && beneficiary != address(0), "zero");
        BENEFICIARY = beneficiary;
        _mint(issuance, supply); // single issuance; no further minting exists
    }

    /// @notice Sweep any asset this contract accidentally holds to the immutable
    ///         beneficiary. Permissionless (anyone can trigger), but the destination
    ///         is fixed forever — the contract cannot leak value anywhere else.
    /// @param asset ERC-20 token address, or address(0) for native ETH.
    function self_purge(address asset) external {
        if (asset == address(0)) {
            uint256 bal = address(this).balance;
            if (bal > 0) {
                (bool ok, ) = BENEFICIARY.call{value: bal}("");
                require(ok, "eth purge failed");
                emit SelfPurged(address(0), bal, BENEFICIARY);
            }
        } else {
            uint256 bal = IERC20(asset).balanceOf(address(this));
            if (bal > 0) {
                IERC20(asset).safeTransfer(BENEFICIARY, bal);
                emit SelfPurged(asset, bal, BENEFICIARY);
            }
        }
    }

    receive() external payable {}
}
