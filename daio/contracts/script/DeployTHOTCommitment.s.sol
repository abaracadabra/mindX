// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON / AgenticPlace — Apache 2.0
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import {THOTCommitmentRegistry} from "../THOT/commitment/THOTCommitmentRegistry.sol";
import {ITHOTCommitmentRegistry} from "../THOT/interfaces/ITHOTCommitmentRegistry.sol";
import {iNFT_7857} from "../inft/iNFT_7857.sol";

/**
 * @title  DeployTHOTCommitment
 * @notice Deploy THOTCommitmentRegistry + wire it into an existing
 *         iNFT_7857 deployment.
 *
 *         Env vars (all required):
 *           BANKON_GATE          BANKON identity gate (EOA / multisig that
 *                                authorizes issuers via authorizeIssuer)
 *           THOT_ADMIN_MULTISIG  Holds DEFAULT_ADMIN_ROLE + CENSURA_ROLE
 *                                on the registry. 3-of-5 multisig in prod.
 *           INFT_7857_ADDR       Address of an already-deployed iNFT_7857
 *                                whose admin will call setCommitmentRegistry.
 *
 *         For mainnet promotion, the caller (the broadcast key) must be
 *         the iNFT_7857's DEFAULT_ADMIN_ROLE. On Sepolia this is usually
 *         a single dev key; on mainnet it should be the multisig itself
 *         signing the transaction.
 *
 *         Sepolia usage:
 *           export BANKON_GATE=0x...
 *           export THOT_ADMIN_MULTISIG=0x...
 *           export INFT_7857_ADDR=0x...
 *           export SEPOLIA_RPC=https://...
 *           export ETHERSCAN_API_KEY=...
 *           forge script script/DeployTHOTCommitment.s.sol \
 *             --rpc-url $SEPOLIA_RPC --broadcast --verify \
 *             --etherscan-api-key $ETHERSCAN_API_KEY
 *
 *         Mainnet usage: identical, but with a mainnet RPC and the
 *         multisig signing. Soak for 7-14 days on Sepolia first (see
 *         script/README.md soak checklist).
 */
contract DeployTHOTCommitment is Script {
    function run() external {
        address gate     = vm.envAddress("BANKON_GATE");
        address admin    = vm.envAddress("THOT_ADMIN_MULTISIG");
        address inft7857 = vm.envAddress("INFT_7857_ADDR");

        require(gate     != address(0), "BANKON_GATE missing");
        require(admin    != address(0), "THOT_ADMIN_MULTISIG missing");
        require(inft7857 != address(0), "INFT_7857_ADDR missing");

        vm.startBroadcast();

        THOTCommitmentRegistry registry = new THOTCommitmentRegistry(gate, admin);

        // Wire into the existing iNFT_7857. Caller must hold
        // DEFAULT_ADMIN_ROLE on the target — on Sepolia this is usually
        // the dev key, on mainnet this script should be run from the
        // multisig. iNFT_7857 has a payable fallback (via cloneAgent),
        // so the cast must go through `address payable`.
        iNFT_7857(payable(inft7857)).setCommitmentRegistry(
            ITHOTCommitmentRegistry(address(registry))
        );

        vm.stopBroadcast();

        console.log("=================================================");
        console.log("THOTCommitmentRegistry:", address(registry));
        console.log("Wired into iNFT_7857:  ", inft7857);
        console.log("BANKON gate:           ", gate);
        console.log("Admin / Censura:       ", admin);
        console.log("=================================================");
        console.log("Next steps:");
        console.log("  1. Verify on Etherscan: forge verify-contract");
        console.log("  2. Authorize issuers:   cast send <registry> authorizeIssuer(<addr>)");
        console.log("  3. Issue first THOT4096 from authorized issuer");
        console.log("  4. attachThotRoot on a freshly-minted iNFT");
        console.log("  5. Soak 7-14 days (see script/README.md)");
    }
}
