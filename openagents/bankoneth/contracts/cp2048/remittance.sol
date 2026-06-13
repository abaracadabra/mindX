// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
//
// remittance — the BANKON collection / remittance contract. Same safe multi-asset
// custody as the treasury (holds + receives any asset on any chain; redeems ONLY to
// the immutable founder bankon.eth; dictator → 2:2/2:3/3:3 consensus → renounce),
// but oriented to COLLECT and forward: a one-call batch `remit()` sweeps native +
// listed ERC-20s home to the founder. Begins life as dictator/admin of one owner
// address; can migrate to multisig consensus exactly like the treasury.
pragma solidity ^0.8.24;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {bankon_custody} from "./bankon_custody.sol";

contract remittance is bankon_custody {
    using SafeERC20 for IERC20;

    event Remitted(uint256 nativeWei, uint256 tokenCount);

    constructor(address founder_) bankon_custody(founder_) {}

    /// @notice Permissionless batch sweep home: all native + the full balance of each listed
    ///         ERC-20 goes to the immutable FOUNDER (bankon.eth) in a single call.
    function remit(address[] calldata erc20s) external nonReentrant {
        uint256 nativeWei = address(this).balance;
        if (nativeWei > 0) {
            (bool ok, ) = payable(FOUNDER).call{value: nativeWei}("");
            require(ok, "native remit failed");
        }
        for (uint256 i = 0; i < erc20s.length; i++) {
            uint256 b = IERC20(erc20s[i]).balanceOf(address(this));
            if (b > 0) IERC20(erc20s[i]).safeTransfer(FOUNDER, b);
        }
        emit Remitted(nativeWei, erc20s.length);
    }
}
