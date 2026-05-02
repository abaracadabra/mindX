// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2}      from "forge-std/Script.sol";
import {X402Receipt}            from "../X402Receipt.sol";
import {IBankonPaymentRouter}   from "../../ens/v1/interfaces/IBankon.sol";

/// @title  Deploy — single source of truth for X402Receipt deploy across chains.
/// @notice Designed for "deploy once, deploy carefully":
///         - `predict()`             — print the CREATE2 address before any TX
///         - `deployTestnet()`       — broadcast on a known testnet (Sepolia,
///                                     Base Sepolia, Polygon Amoy, ...)
///         - `deployMainnet()`       — broadcast on Base / Polygon / Ethereum
///                                     mainnet, gated by an explicit
///                                     X402_DEPLOY_MAINNET=true env flag and
///                                     a deployer-balance check.
///
/// @dev    EVM-side singletons get the same predictable address across chains
///         when they go through the canonical SingletonFactory at
///         `0x8A791620dd6260079BF849Dc5567aDC3F2FdC318`. We do NOT take that
///         hard dependency here — Foundry's `vm.broadcast` is enough for
///         "deploy once, log address, verify". If the operator wants
///         cross-chain identical addresses, run with `--create2-deployer
///         0x8A791620...` and a fixed salt.
///
/// Env vars consumed:
///   PRIVATE_KEY                 — deployer EOA (testnet) or hot multisig deploy key (mainnet)
///   X402_ADMIN                  — DEFAULT_ADMIN_ROLE recipient (recommend a Safe / multisig on mainnet)
///   BANKON_PAYMENT_ROUTER       — existing router address; address(0) disables cascade
///   X402_DEPLOY_MAINNET         — must equal "true" for `deployMainnet()` to broadcast
///   MIN_DEPLOYER_BALANCE_WEI    — pre-deploy gate (default: 0.05 ETH)
///
/// Run:
///   FOUNDRY_PROFILE=x402 forge script daio/contracts/x402/script/Deploy.s.sol \
///       --sig "predict()" --rpc-url $RPC --private-key $PRIVATE_KEY
///   FOUNDRY_PROFILE=x402 forge script daio/contracts/x402/script/Deploy.s.sol \
///       --sig "deployTestnet()" --rpc-url $RPC --private-key $PRIVATE_KEY --broadcast
///   FOUNDRY_PROFILE=x402 forge script daio/contracts/x402/script/Deploy.s.sol \
///       --sig "deployMainnet()" --rpc-url $RPC --private-key $PRIVATE_KEY --broadcast --verify
contract Deploy is Script {
    /// Mainnet chain IDs that `deployMainnet()` accepts. Adding new chains is
    /// an explicit code change — keeps surprise deploys impossible.
    uint256 internal constant CHAIN_BASE_MAINNET     = 8453;
    uint256 internal constant CHAIN_POLYGON_MAINNET  = 137;
    uint256 internal constant CHAIN_ETHEREUM_MAINNET = 1;
    uint256 internal constant CHAIN_ARBITRUM_MAINNET = 42161;
    uint256 internal constant CHAIN_OPTIMISM_MAINNET = 10;

    error WrongChainForMainnet(uint256 chainId);
    error MainnetGateClosed();
    error DeployerUnderfunded(uint256 have, uint256 want);
    error AdminNotSet();

    /// @notice Print the predicted CREATE address (nonce-based) and the salt-based
    ///         CREATE2 address derived from the X402Receipt creation code. No state
    ///         is touched — safe to call against any chain.
    function predict() external view {
        address deployer = msg.sender;
        address admin    = _envAddressOrSender("X402_ADMIN");
        IBankonPaymentRouter router = IBankonPaymentRouter(_envAddressOr("BANKON_PAYMENT_ROUTER", address(0)));

        // CREATE-based predicted address (uses next nonce).
        uint256 nonce = vm.getNonce(deployer);
        address createPredicted = vm.computeCreateAddress(deployer, nonce);

        // CREATE2-based predicted address using a deterministic salt + the
        // canonical EIP-2470 SingletonFactory at 0x8A79... Replace `salt` with
        // your operator-chosen salt for the actual deploy.
        bytes memory init = abi.encodePacked(
            type(X402Receipt).creationCode,
            abi.encode(admin, router)
        );
        bytes32 salt = keccak256(abi.encodePacked("x402-receipt-v1", admin));
        address singletonFactory = 0x8A791620dd6260079BF849Dc5567aDC3F2FdC318;
        address create2Predicted = vm.computeCreate2Address(
            salt, keccak256(init), singletonFactory
        );

        console2.log("=== X402Receipt deploy prediction ===");
        console2.log("chainId          ", block.chainid);
        console2.log("deployer         ", deployer);
        console2.log("deployer nonce   ", nonce);
        console2.log("admin            ", admin);
        console2.log("router           ", address(router));
        console2.log("CREATE predicted ", createPredicted);
        console2.log("CREATE2 salt     ", vm.toString(salt));
        console2.log("CREATE2 predicted", create2Predicted);
        console2.log("(CREATE2 assumes EIP-2470 SingletonFactory at 0x8A79...dC318)");
    }

    /// @notice Broadcast the X402Receipt deploy on a testnet. No chain-id guard;
    ///         relies on the operator pointing `--rpc-url` at the right RPC.
    function deployTestnet() external {
        (X402Receipt receipt, address admin, IBankonPaymentRouter router) = _deploy();
        console2.log("=== TESTNET deploy complete ===");
        console2.log("chainId  ", block.chainid);
        console2.log("contract ", address(receipt));
        console2.log("admin    ", admin);
        console2.log("router   ", address(router));
        console2.log("(grant REGISTRAR_ROLE on router to the contract addr to enable cascade)");
    }

    /// @notice Broadcast the X402Receipt deploy on mainnet. Two safety gates:
    ///         1. Chain ID must match a known mainnet (Base/Polygon/Eth/Arb/Op).
    ///         2. `X402_DEPLOY_MAINNET=true` env flag must be set explicitly.
    ///         3. Deployer balance >= MIN_DEPLOYER_BALANCE_WEI (default 0.05 ETH).
    ///
    ///         The script does NOT auto-grant REGISTRAR_ROLE on the router —
    ///         that's a separate, deliberate post-deploy TX (see X402_DEPLOY.md).
    function deployMainnet() external {
        _assertMainnetChainAllowed();
        _assertMainnetGateOpen();
        _assertDeployerFunded();

        (X402Receipt receipt, address admin, IBankonPaymentRouter router) = _deploy();
        console2.log("=== MAINNET deploy complete (single shot) ===");
        console2.log("chainId  ", block.chainid);
        console2.log("contract ", address(receipt));
        console2.log("admin    ", admin);
        console2.log("router   ", address(router));
        console2.log("(verify on Etherscan/Basescan; THEN grant REGISTRAR_ROLE on router.)");
    }

    // ─────────────────────────────────────────────────────────────────
    // Internal
    // ─────────────────────────────────────────────────────────────────

    function _deploy() internal returns (
        X402Receipt receipt, address admin, IBankonPaymentRouter router
    ) {
        admin  = _envAddressOrSender("X402_ADMIN");
        if (admin == address(0)) revert AdminNotSet();
        router = IBankonPaymentRouter(_envAddressOr("BANKON_PAYMENT_ROUTER", address(0)));

        vm.startBroadcast();
        receipt = new X402Receipt(admin, router);
        vm.stopBroadcast();
    }

    function _assertMainnetChainAllowed() internal view {
        uint256 id = block.chainid;
        if (
            id != CHAIN_BASE_MAINNET &&
            id != CHAIN_POLYGON_MAINNET &&
            id != CHAIN_ETHEREUM_MAINNET &&
            id != CHAIN_ARBITRUM_MAINNET &&
            id != CHAIN_OPTIMISM_MAINNET
        ) revert WrongChainForMainnet(id);
    }

    function _assertMainnetGateOpen() internal view {
        string memory flag;
        try vm.envString("X402_DEPLOY_MAINNET") returns (string memory v) {
            flag = v;
        } catch {
            revert MainnetGateClosed();
        }
        if (keccak256(bytes(flag)) != keccak256("true")) revert MainnetGateClosed();
    }

    function _assertDeployerFunded() internal view {
        uint256 minBal = 0.05 ether;
        try vm.envUint("MIN_DEPLOYER_BALANCE_WEI") returns (uint256 v) {
            if (v > 0) minBal = v;
        } catch {}
        uint256 bal = msg.sender.balance;
        if (bal < minBal) revert DeployerUnderfunded(bal, minBal);
    }

    function _envAddressOrSender(string memory key) internal view returns (address) {
        try vm.envAddress(key) returns (address v) {
            return v;
        } catch {
            return msg.sender;
        }
    }

    function _envAddressOr(string memory key, address fallback_) internal view returns (address) {
        try vm.envAddress(key) returns (address v) {
            return v;
        } catch {
            return fallback_;
        }
    }
}
