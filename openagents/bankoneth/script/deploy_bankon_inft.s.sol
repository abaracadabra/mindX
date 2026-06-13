// SPDX-License-Identifier: Apache-2.0
// (c) 2026 BANKON — all rights reserved
// Deploys the modular canonical EIP-7857 + ERC-6551 stack (contracts/inft7857/).
// Verified mainnet ENS addresses (Doc 1; Doc 2's 0x0635…/0xfb3cE5… are Sepolia).
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {INameWrapper, IERC6551Registry} from "../contracts/inft7857/bankon_interfaces.sol";
import {bankon_inft_oracle} from "../contracts/inft7857/bankon_inft_oracle.sol";
import {bankon_inft_subname} from "../contracts/inft7857/bankon_inft_subname.sol";
import {bankon_inft_extension} from "../contracts/inft7857/bankon_inft_extension.sol";
import {bankon_inft_registrar} from "../contracts/inft7857/bankon_inft_registrar.sol";
import {bankon_tba_account} from "../contracts/inft7857/bankon_tba_account.sol";
import {bankon_tba_registry_proxy} from "../contracts/inft7857/bankon_tba_registry_proxy.sol";

contract deploy_bankon_inft is Script {
    address constant ERC6551_REGISTRY = 0x000000006551c19487814612e58FE06813775758;
    // L1 mainnet ENS — VERIFIED on-chain
    INameWrapper constant L1_WRAPPER = INameWrapper(0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401);

    function run() external {
        uint256 pk       = vm.envUint("DEPLOYER_PK");
        address admin    = vm.envAddress("BANKON_ADMIN");
        address treasury = vm.envAddress("BANKON_TREASURY");
        address facil    = vm.envAddress("BANKON_FACILITATOR");

        address[] memory signers = new address[](3);
        signers[0] = vm.envAddress("ORACLE_SIGNER_1");
        signers[1] = vm.envAddress("ORACLE_SIGNER_2");
        signers[2] = vm.envAddress("ORACLE_SIGNER_3");

        // NameWrapper: mainnet uses the verified L1 wrapper; a testnet/fork can override.
        address nwOverride = vm.envOr("NAME_WRAPPER_ADDR", address(0));
        INameWrapper wrapper = nwOverride == address(0) ? L1_WRAPPER : INameWrapper(nwOverride);

        vm.startBroadcast(pk);

        bankon_inft_oracle oracle = new bankon_inft_oracle(admin, signers, 2);
        bankon_tba_account tbaImpl = new bankon_tba_account();
        bankon_tba_registry_proxy proxy = new bankon_tba_registry_proxy();

        bankon_inft_subname unified = new bankon_inft_subname(
            "BANKON Agent", "BANK",
            "ipfs://bankon-storage", "https://bankon.eth/contract-metadata.json",
            admin, address(0), wrapper, oracle, treasury, 250
        );
        bankon_inft_extension parallel = new bankon_inft_extension(
            "BANKON Agent Extension", "BANKX",
            "ipfs://bankon-ext", admin, wrapper, oracle, treasury, 250
        );
        bankon_inft_registrar reg = new bankon_inft_registrar(
            admin, wrapper, unified, parallel,
            IERC6551Registry(ERC6551_REGISTRY), address(tbaImpl), facil
        );
        unified.setMinter(address(reg));

        console.log("oracle   =", address(oracle));
        console.log("tbaImpl  =", address(tbaImpl));
        console.log("proxy    =", address(proxy));
        console.log("unified  =", address(unified));
        console.log("parallel =", address(parallel));
        console.log("registrar=", address(reg));
        vm.stopBroadcast();
    }
}
