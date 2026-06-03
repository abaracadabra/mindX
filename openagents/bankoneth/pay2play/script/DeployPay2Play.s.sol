// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";

import {BankonServiceRegistry}  from "../src/BankonServiceRegistry.sol";
import {BankonEntitlement}      from "../src/BankonEntitlement.sol";
import {BANKONPaymentRouter}    from "../src/BANKONPaymentRouter.sol";
import {Pay2PlayArcSettlement}  from "../src/Pay2PlayArcSettlement.sol";
import {IBankonServiceRegistry, IBankonEntitlement} from "../src/interfaces/IPay2Play.sol";

/// @notice Deploys the pay-to-play rails and wires the GRANTER_ROLE so the
///         router can grant entitlements. Optionally seeds one BANKON-as-a-Service
///         row (identity.register). Env:
///           ADMIN          — admin/treasurer (defaults to broadcaster)
///           FEE_RECIPIENT  — where the fair/nominal fee accrues (defaults to ADMIN)
///           SERVICE_BENEFICIARY — net-payment recipient for the seed service
///         Run:
///           forge script script/DeployPay2Play.s.sol --rpc-url $RPC --broadcast
contract DeployPay2Play is Script {
    function run() external {
        address admin = vm.envOr("ADMIN", msg.sender);
        address feeRecipient = vm.envOr("FEE_RECIPIENT", admin);
        address beneficiary = vm.envOr("SERVICE_BENEFICIARY", admin);

        vm.startBroadcast();

        BankonServiceRegistry registry = new BankonServiceRegistry(admin);
        BankonEntitlement     ent      = new BankonEntitlement(admin);
        BANKONPaymentRouter   router   = new BANKONPaymentRouter(
            admin, registry, ent, feeRecipient
        );

        // ARC-chain USDC x402 settlement layer (Circle ARC). Env:
        //   ARC_CHAIN_ID   — ARC chain id (default 0 → operator sets via setArcConfig)
        //   ARC_USDC       — USDC token address on ARC (default ADMIN as placeholder)
        //   ARC_FACILITATOR— the x402 facilitator signing key (default ADMIN)
        uint64  arcChainId  = uint64(vm.envOr("ARC_CHAIN_ID", uint256(0)));
        address arcUsdc     = vm.envOr("ARC_USDC", admin);
        address facilitator = vm.envOr("ARC_FACILITATOR", admin);

        Pay2PlayArcSettlement arc = new Pay2PlayArcSettlement(
            admin, registry, ent, arcChainId, arcUsdc
        );

        // Both the router and the ARC settlement layer must be able to grant.
        ent.grantRole(ent.GRANTER_ROLE(), address(router));
        ent.grantRole(ent.GRANTER_ROLE(), address(arc));
        arc.setFacilitator(facilitator, true);

        // Seed services: native identity.register (permanent, tier 1) and a
        // USDC allchain.access (30d, tier 3) settleable on ARC.
        registry.setService(
            keccak256("identity.register"),
            IBankonServiceRegistry.Service({
                beneficiary: beneficiary,
                asset:       address(0),       // native
                price:       0.01 ether,
                period:      0,                // permanent
                tier:        1,
                active:      true,
                name:        "identity.register"
            })
        );
        registry.setService(
            keccak256("allchain.access"),
            IBankonServiceRegistry.Service({
                beneficiary: beneficiary,
                asset:       arcUsdc,          // USDC on ARC
                price:       10e6,             // 10 USDC (6dp)
                period:      30 days,
                tier:        3,
                active:      true,
                name:        "allchain.access"
            })
        );

        vm.stopBroadcast();

        console2.log("BankonServiceRegistry: ", address(registry));
        console2.log("BankonEntitlement:     ", address(ent));
        console2.log("BANKONPaymentRouter:   ", address(router));
        console2.log("Pay2PlayArcSettlement: ", address(arc));
    }
}
