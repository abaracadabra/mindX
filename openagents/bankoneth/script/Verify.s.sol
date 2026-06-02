// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";

/// @title  Verify
/// @notice Etherscan + Sourcify + 0G explorer verification driver.
///
///         For each deployed contract, build the constructor-args ABI encoding
///         and emit the `forge verify-contract` command line. Operator runs
///         the emitted commands; verification keys come from env.
///
///         This script doesn't actually call out to Etherscan — that's
///         operator-gated and lives in `docs/DEPLOYMENT.md`. The job here is
///         to print canonical commands so operators don't typo them.
contract Verify is Script {
    function run() external view {
        address subnameRegistrar = vm.envAddress("SUBNAME_REGISTRAR_ADDR");
        address ethRegistrar     = vm.envAddress("ETH_REGISTRAR_ADDR");
        address domainHosting    = vm.envAddress("DOMAIN_HOSTING_ADDR");
        address resolver         = vm.envAddress("RESOLVER_ADDR");
        address inftAdapter      = vm.envAddress("INFT_ADAPTER_ADDR");
        address x402Attestor     = vm.envAddress("X402_ATTESTOR_ADDR");
        address hook             = vm.envAddress("AGENTICPLACE_HOOK_ADDR");
        address zeroGiNFT        = vm.envAddress("ZEROG_INFT_ADDR");

        console.log("# Run each command from openagents/bankoneth/");
        console.log("forge verify-contract", subnameRegistrar, "contracts/BankonSubnameRegistrar.sol:BankonSubnameRegistrar --chain $CHAIN");
        console.log("forge verify-contract", ethRegistrar,     "contracts/BankonEthRegistrar.sol:BankonEthRegistrar --chain $CHAIN");
        console.log("forge verify-contract", domainHosting,    "contracts/BankonDomainHosting.sol:BankonDomainHosting --chain $CHAIN");
        console.log("forge verify-contract", resolver,         "contracts/BankonSubnameResolver.sol:BankonSubnameResolver --chain $CHAIN");
        console.log("forge verify-contract", inftAdapter,      "contracts/BankonInftAdapter.sol:BankonInftAdapter --chain $CHAIN");
        console.log("forge verify-contract", x402Attestor,     "contracts/BankonX402Attestor.sol:BankonX402Attestor --chain $CHAIN");
        console.log("forge verify-contract", hook,             "contracts/BankonAgenticPlaceHook.sol:BankonAgenticPlaceHook --chain $CHAIN");
        console.log("# 0G chain:");
        console.log("forge verify-contract", zeroGiNFT,        "contracts/inft/iNFT_7857.sol:iNFT_7857 --chain 16601");
    }
}
