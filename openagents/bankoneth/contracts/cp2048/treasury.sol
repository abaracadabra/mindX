// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / cypherpunk2048 — Apache-2.0
//
// treasury — the BANKON long-term multi-asset vault. Holds native, ERC-20, ERC-721
// and ERC-1155 on any chain; value redeems ONLY to the immutable founder (bankon.eth).
// Governance begins as the single-owner dictator (bankon.eth) and can migrate to a
// 2-of-2 / 2-of-3 / 3-of-3 multisig consensus, or renounce. See bankon_custody.
pragma solidity ^0.8.24;

import {bankon_custody} from "./bankon_custody.sol";

contract treasury is bankon_custody {
    constructor(address founder_) bankon_custody(founder_) {}
}
