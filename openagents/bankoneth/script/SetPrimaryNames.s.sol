// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";

import {BankonSubnameRegistrar}  from "../contracts/BankonSubnameRegistrar.sol";
import {BankonEthRegistrar}      from "../contracts/BankonEthRegistrar.sol";
import {BankonDomainHosting}     from "../contracts/BankonDomainHosting.sol";
import {IReverseRegistrar}       from "../contracts/interfaces/IReverseRegistrar.sol";

/// @notice ENSIP-15 — Phase 2.3. One-shot post-deploy script that wires
///         primary names to each bankoneth registrar contract via the
///         canonical ENS ReverseRegistrar
///         (mainnet 0xa58E81fe9b61B5c3fE2AFD33CF304c454AbFc7Cb).
///
///         After running, block explorers + wallets that perform reverse
///         resolution display:
///             - BankonSubnameRegistrar → "registrar.bankon.eth"
///             - BankonEthRegistrar     → "eth-registrar.bankon.eth"
///             - BankonDomainHosting    → "host.bankon.eth"
///         …instead of the raw 0x address.
///
/// @dev    Subnames must already be MINTED under bankon.eth (via the
///         BankonSubnameRegistrar, or manually via the ENS app) before this
///         script runs — otherwise the reverse record points at a name
///         nobody owns. Reference docs/REVERSE_REGISTRATION.md.
///
///         Env vars:
///             SUBNAME_REGISTRAR_ADDR   the deployed BankonSubnameRegistrar
///             ETH_REGISTRAR_ADDR       the deployed BankonEthRegistrar
///             DOMAIN_HOSTING_ADDR      the deployed BankonDomainHosting
///             REVERSE_REGISTRAR_ADDR   ENS ReverseRegistrar (mainnet pin in
///                                       packages/core/src/addresses.ts)
///             DEPLOYER_PK              the EOA with DEFAULT_ADMIN_ROLE on
///                                       the three registrars
///             SUBNAME_REGISTRAR_NAME   defaults to "registrar.bankon.eth"
///             ETH_REGISTRAR_NAME       defaults to "eth-registrar.bankon.eth"
///             DOMAIN_HOSTING_NAME      defaults to "host.bankon.eth"
contract SetPrimaryNames is Script {
    function run() external {
        uint256 pk = vm.envUint("DEPLOYER_PK");

        address subnameReg   = vm.envAddress("SUBNAME_REGISTRAR_ADDR");
        address ethReg       = vm.envAddress("ETH_REGISTRAR_ADDR");
        address domHosting   = vm.envAddress("DOMAIN_HOSTING_ADDR");
        IReverseRegistrar rr = IReverseRegistrar(vm.envAddress("REVERSE_REGISTRAR_ADDR"));

        string memory subnameName = vm.envOr("SUBNAME_REGISTRAR_NAME", string("registrar.bankon.eth"));
        string memory ethName     = vm.envOr("ETH_REGISTRAR_NAME",     string("eth-registrar.bankon.eth"));
        string memory hostName    = vm.envOr("DOMAIN_HOSTING_NAME",    string("host.bankon.eth"));

        vm.startBroadcast(pk);

        bytes32 n1 = BankonSubnameRegistrar(payable(subnameReg)).setReverseName(rr, subnameName);
        console.log("[reverse] BankonSubnameRegistrar  ->", subnameName);

        bytes32 n2 = BankonEthRegistrar(payable(ethReg)).setReverseName(rr, ethName);
        console.log("[reverse] BankonEthRegistrar      ->", ethName);

        bytes32 n3 = BankonDomainHosting(payable(domHosting)).setReverseName(rr, hostName);
        console.log("[reverse] BankonDomainHosting     ->", hostName);

        vm.stopBroadcast();

        // Sanity log — the returned bytes32 is the reverse-node namehash
        // of `[addr].addr.reverse` for each contract. Pin into the operator
        // notes for the next runbook step (e.g. forward-resolving each name
        // back to confirm the round-trip).
        console.log("subname reverse node :", uint256(n1));
        console.log("eth reverse node     :", uint256(n2));
        console.log("hosting reverse node :", uint256(n3));
    }
}
