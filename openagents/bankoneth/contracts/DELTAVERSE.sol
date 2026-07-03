// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// @title DELTAVERSE — the unit of access and reward of the DeltaVerse.
/// @notice Fixed-supply ERC-20. Entry to the DeltaVerse requires holding ≥1
///         DELTAVERSE (with BONA FIDE). Collection-from-payment accrues to the
///         bankon.eth overlord / BANKON treasury. The 1:1 inception NFT
///         (0x024b464ec595F20040002237680026bf006e8F90 token #1, Polygon) is
///         the genesis logo / project reference — distinct from this token.
/// @dev    18 decimals. Total supply minted once, at construction, to `treasury`.
contract DELTAVERSE is ERC20 {
    /// @notice 1,111,111,111,111.111111111111111111 DELTAVERSE (18 decimals).
    ///         = 1111111111111111111111111111111 base units (thirty-one 1s).
    uint256 public constant INITIAL_SUPPLY = 1_111_111_111_111_111_111_111_111_111_111;

    /// @param treasury the bankon.eth overlord / BANKON treasury that receives
    ///        the entire supply (resolved via the deployer's `from="owner"`).
    constructor(address treasury) ERC20("DeltaVerse", "DELTAVERSE") {
        require(treasury != address(0), "DELTAVERSE: zero treasury");
        _mint(treasury, INITIAL_SUPPLY);
    }
}
