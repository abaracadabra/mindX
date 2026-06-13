// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

import {IBankonEntitlement} from "./interfaces/IPay2Play.sol";

/// @title  BankonEntitlement — identity-management ledger for pay-to-play.
/// @author cypherpunk2048
/// @notice Records, per wallet, which service entitlements it holds and until
///         when. The wallet address is the identity (proof of private-key
///         ownership happens at the router via signature). Only an address
///         holding GRANTER_ROLE (the router) may write; everyone may read.
///
///         This is the on-chain answer to "does this identity have access?" —
///         the gate any BANKON-as-a-Service surface (bankon.pythai.net,
///         allchain, hosting) checks before serving.
contract BankonEntitlement is AccessControl, IBankonEntitlement {
    /// @notice Held by the payment router(s) that may grant access.
    bytes32 public constant GRANTER_ROLE = keccak256("GRANTER_ROLE");

    uint64 internal constant PERMANENT = type(uint64).max;

    /// user => service => unix expiry (0 = none, PERMANENT = never expires)
    mapping(address => mapping(bytes32 => uint64)) internal _expiry;

    /// user => highest tier ever conferred (monotonic; identity reputation floor)
    mapping(address => uint8) internal _tier;

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    /// @notice Grant `user` access to `service` until `until` (PERMANENT for
    ///         one-time purchases) and raise their tier if higher.
    function grant(address user, bytes32 service, uint8 tier, uint64 until)
        external
        onlyRole(GRANTER_ROLE)
    {
        _expiry[user][service] = until;
        if (tier > _tier[user]) _tier[user] = tier;
        emit EntitlementGranted(user, service, tier, until);
    }

    /// @notice True iff `user` currently holds `service` (permanent or unexpired).
    function hasAccess(address user, bytes32 service) public view returns (bool) {
        uint64 e = _expiry[user][service];
        return e == PERMANENT || e > block.timestamp;
    }

    function expiryOf(address user, bytes32 service) external view returns (uint64) {
        return _expiry[user][service];
    }

    function tierOf(address user) external view returns (uint8) {
        return _tier[user];
    }
}
