// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";

/// @notice Minimal AccessControl surface — every bankon admin contract is an
///         OpenZeppelin AccessControl, so grantRole(bytes32,address) suffices.
interface IAccessControl {
    function grantRole(bytes32 role, address account) external;
    function hasRole(bytes32 role, address account) external view returns (bool);
}

/// @title  GrantOwnerRoles
/// @notice Phase 0 of the tiered-login work: make "owns bankon.eth" mean "can
///         administer the contracts." The contracts grant every admin role to
///         the deploy `treasury`; this script re-grants the page-admin roles to
///         the bankon.eth owner (read live via NameWrapper.ownerOf — see
///         deployments/<chain>.json rootName.owner / BANKON_OWNER_ADDR) so the
///         admin console's setter txs succeed from the owner's wallet.
///
///         Run BY the current role-holder (treasury/deployer):
///           forge script script/GrantOwnerRoles.s.sol \
///             --rpc-url $RPC --broadcast
///
///         Env:
///           DEPLOYER_PK            current admin (treasury) key — must hold DEFAULT_ADMIN_ROLE
///           BANKON_OWNER_ADDR      grantee (the bankon.eth owner)
///           PRICE_ORACLE_ADDR, REPUTATION_GATE_ADDR, PAYMENT_ROUTER_ADDR,
///           DOMAIN_HOSTING_ADDR, SUBNAME_REGISTRAR_ADDR
contract GrantOwnerRoles is Script {
    bytes32 constant DEFAULT_ADMIN_ROLE = 0x00;
    bytes32 constant GOV_ROLE           = keccak256("GOV_ROLE");
    bytes32 constant TREASURER_ROLE     = keccak256("TREASURER_ROLE");
    bytes32 constant BANKON_OPS_ROLE    = keccak256("BANKON_OPS_ROLE");
    bytes32 constant BONAFIDE_GOV_ROLE  = keccak256("BONAFIDE_GOV_ROLE");

    function run() external {
        uint256 pk    = vm.envUint("DEPLOYER_PK");
        address owner = vm.envAddress("BANKON_OWNER_ADDR");

        address priceOracle    = vm.envAddress("PRICE_ORACLE_ADDR");
        address reputationGate = vm.envAddress("REPUTATION_GATE_ADDR");
        address paymentRouter  = vm.envAddress("PAYMENT_ROUTER_ADDR");
        address domainHosting  = vm.envAddress("DOMAIN_HOSTING_ADDR");
        address subnameReg     = vm.envAddress("SUBNAME_REGISTRAR_ADDR");

        require(owner != address(0), "BANKON_OWNER_ADDR=0");

        vm.startBroadcast(pk);

        // Pricing — set length-tiered prices + PYTHAI discount.
        _grant(priceOracle, GOV_ROLE, owner);
        _grant(priceOracle, DEFAULT_ADMIN_ROLE, owner);

        // Free-tier eligibility thresholds.
        _grant(reputationGate, GOV_ROLE, owner);

        // Fee splits + recipients + revenue sweep.
        _grant(paymentRouter, DEFAULT_ADMIN_ROLE, owner);
        _grant(paymentRouter, TREASURER_ROLE, owner);

        // Hosting global settings (hostShareBps, pause). Per-parent enrollment is
        // already gated by NameWrapper ownership, which the owner has.
        _grant(domainHosting, DEFAULT_ADMIN_ROLE, owner);

        // Registrar ops + governance + admin.
        _grant(subnameReg, DEFAULT_ADMIN_ROLE, owner);
        _grant(subnameReg, BANKON_OPS_ROLE, owner);
        _grant(subnameReg, BONAFIDE_GOV_ROLE, owner);

        vm.stopBroadcast();

        console.log("Granted bankon.eth owner admin roles:", owner);
    }

    function _grant(address target, bytes32 role, address account) internal {
        if (target == address(0)) return; // skip unset slots
        IAccessControl(target).grantRole(role, account);
    }
}
