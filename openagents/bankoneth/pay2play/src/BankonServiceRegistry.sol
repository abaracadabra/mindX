// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";

import {IBankonServiceRegistry} from "./interfaces/IPay2Play.sol";

/// @title  BankonServiceRegistry — the BANKON-as-a-Service collection.
/// @author cypherpunk2048
/// @notice The catalogue of purchasable services for the pay-to-play rails.
///         Each service is one row: price, asset, entitlement period, the tier
///         it confers, and the beneficiary that receives the net payment.
///         Adding a service is adding a row — never changing the router. That
///         is the modular boundary: the registry knows *what* is for sale, the
///         router knows *how* to charge, the entitlement ledger knows *who* holds
///         access.
contract BankonServiceRegistry is AccessControl, IBankonServiceRegistry {
    bytes32 public constant SERVICE_ADMIN_ROLE = keccak256("SERVICE_ADMIN_ROLE");

    mapping(bytes32 => Service) private _services;

    error ZeroBeneficiary();

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(SERVICE_ADMIN_ROLE, admin);
    }

    /// @notice Create or replace a service definition.
    /// @param id  Stable identifier, e.g. keccak256("identity.register").
    function setService(bytes32 id, Service calldata s) external onlyRole(SERVICE_ADMIN_ROLE) {
        if (s.beneficiary == address(0)) revert ZeroBeneficiary();
        _services[id] = s;
        emit ServiceSet(id, s.beneficiary, s.asset, s.price, s.period, s.tier, s.active, s.name);
    }

    /// @notice Toggle a service on/off without touching its economics.
    function setActive(bytes32 id, bool active) external onlyRole(SERVICE_ADMIN_ROLE) {
        Service storage s = _services[id];
        if (s.beneficiary == address(0)) revert ZeroBeneficiary();
        s.active = active;
        emit ServiceSet(id, s.beneficiary, s.asset, s.price, s.period, s.tier, active, s.name);
    }

    /// @notice Adjust price (kept fair/nominal by the operator; the router caps the fee).
    function setPrice(bytes32 id, uint256 price) external onlyRole(SERVICE_ADMIN_ROLE) {
        Service storage s = _services[id];
        if (s.beneficiary == address(0)) revert ZeroBeneficiary();
        s.price = price;
        emit ServiceSet(id, s.beneficiary, s.asset, price, s.period, s.tier, s.active, s.name);
    }

    function getService(bytes32 id) external view returns (Service memory) {
        return _services[id];
    }

    function isActive(bytes32 id) external view returns (bool) {
        return _services[id].active;
    }
}
