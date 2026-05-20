// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {Vm} from "forge-std/Vm.sol";

import {AgentRegistry} from "../agentregistry/AgentRegistry.sol";
import {THOT_v1} from "../THOT/v1/THOT.sol";
import {X402Receipt} from "../x402/X402Receipt.sol";
import {IBankonPaymentRouter} from "../ens/v1/interfaces/IBankon.sol";
import {iNFT_7857} from "../inft/iNFT_7857.sol";
import {BankonSubnameRegistrar} from "../ens/v1/BankonSubnameRegistrar.sol";

/// @notice Deploys the 5 production-grade Tier-1 contracts to a target chain.
///
/// Required env (see `.env.deploy.sample`):
///   DEPLOYER_PRIVATE_KEY   — operator EOA, only used for this run
///   OWNER_MULTISIG         — Gnosis Safe that owns each deployed contract
///   ROYALTY_RECEIVER       — for iNFT_7857 ERC2981
///   TREASURY_ADDR          — for iNFT_7857 cloneFee receipt
///   IDENTITY_REGISTRY_8004 — canonical ERC-8004 identity registry (per chain)
///
/// Optional (BankonSubnameRegistrar; deploys are skipped if any external
/// dependency is unset, since the registrar requires real ENS infra):
///   ENS_NAME_WRAPPER, ENS_DEFAULT_RESOLVER, BANKON_PARENT_NODE,
///   BANKON_PAYMENT_ROUTER, BANKON_PRICE_ORACLE, BANKON_REPUTATION_GATE
///
/// Toggles (skip a deployment leg by setting the corresponding env to "0"):
///   DEPLOY_AGENT_REGISTRY, DEPLOY_THOT, DEPLOY_X402, DEPLOY_INFT,
///   DEPLOY_BANKON
///
/// Output: a JSON receipt at `deployments/<chainId>/tier1.json` capturing
/// the deployed addresses + the deployer + the block number.
contract DeployTier1 is Script {
    struct DeployedAddresses {
        address agentRegistry;
        address thot;
        address x402Receipt;
        address inft7857;
        address bankonSubnameRegistrar;
    }

    /// @notice Read an env var with a string default.
    function _envOr(string memory key, string memory dflt) internal view returns (string memory) {
        try vm.envString(key) returns (string memory v) {
            return v;
        } catch {
            return dflt;
        }
    }

    /// @notice Read an env var that defaults to "1" (deploy on) unless explicitly "0".
    function _flagOn(string memory key) internal view returns (bool) {
        return keccak256(bytes(_envOr(key, "1"))) != keccak256(bytes("0"));
    }

    /// @notice Read an address env, returning address(0) if unset (caller decides whether that's fatal).
    function _envAddrOr0(string memory key) internal view returns (address) {
        try vm.envAddress(key) returns (address a) {
            return a;
        } catch {
            return address(0);
        }
    }

    function run() external {
        uint256 deployerPk = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address deployer = vm.addr(deployerPk);
        address owner = vm.envAddress("OWNER_MULTISIG");
        require(owner != address(0), "OWNER_MULTISIG required");

        address royaltyReceiver = vm.envAddress("ROYALTY_RECEIVER");
        address treasury = vm.envAddress("TREASURY_ADDR");
        require(royaltyReceiver != address(0), "ROYALTY_RECEIVER required");
        require(treasury != address(0), "TREASURY_ADDR required");

        DeployedAddresses memory out;

        console2.log("=== DeployTier1 ===");
        console2.log("chainid:  ", block.chainid);
        console2.log("deployer: ", deployer);
        console2.log("owner:    ", owner);

        vm.startBroadcast(deployerPk);

        if (_flagOn("DEPLOY_AGENT_REGISTRY")) {
            AgentRegistry r = new AgentRegistry("BANKON Agent Registry", "BAR", owner);
            out.agentRegistry = address(r);
            console2.log("AgentRegistry            :", out.agentRegistry);
        }

        if (_flagOn("DEPLOY_THOT")) {
            THOT_v1 t = new THOT_v1("THOT Memory Anchor", "THOT", owner);
            out.thot = address(t);
            console2.log("THOT_v1                  :", out.thot);
        }

        if (_flagOn("DEPLOY_X402")) {
            // X402Receipt accepts an optional downstream router. If not set,
            // pass address(0) — receipts won't cascade until setRouter is called
            // post-deploy by the multisig.
            address routerAddr = _envAddrOr0("BANKON_PAYMENT_ROUTER");
            X402Receipt x = new X402Receipt(owner, IBankonPaymentRouter(routerAddr));
            out.x402Receipt = address(x);
            console2.log("X402Receipt              :", out.x402Receipt);
        }

        if (_flagOn("DEPLOY_INFT")) {
            uint96 royaltyBps = uint96(vm.envOr("ROYALTY_FEE_BPS", uint256(500))); // 5% default
            uint256 cloneFeeWei = vm.envOr("CLONE_FEE_WEI", uint256(0));
            address oracle = _envAddrOr0("INFT_ORACLE"); // optional: address(0) disables 7857 sealed-key oracle
            iNFT_7857 n = new iNFT_7857(
                "Intelligent NFT 7857",
                "iNFT",
                owner,
                royaltyReceiver,
                royaltyBps,
                oracle,
                treasury,
                cloneFeeWei
            );
            out.inft7857 = address(n);
            console2.log("iNFT_7857                :", out.inft7857);
        }

        if (_flagOn("DEPLOY_BANKON")) {
            address nameWrapper = _envAddrOr0("ENS_NAME_WRAPPER");
            address defaultResolver = _envAddrOr0("ENS_DEFAULT_RESOLVER");
            address paymentRouter = _envAddrOr0("BANKON_PAYMENT_ROUTER");
            address priceOracle = _envAddrOr0("BANKON_PRICE_ORACLE");
            address reputationGate = _envAddrOr0("BANKON_REPUTATION_GATE");
            address identityRegistry = vm.envAddress("IDENTITY_REGISTRY_8004");
            bytes32 parentNode = vm.envBytes32("BANKON_PARENT_NODE");

            // Bankon registrar requires real ENS infra; skip if any of the
            // ENS-side or Bankon-internal deps are unset — operator can
            // re-run with DEPLOY_BANKON=1 once they're available.
            if (nameWrapper == address(0) || defaultResolver == address(0)
                || paymentRouter == address(0) || priceOracle == address(0)
                || reputationGate == address(0) || parentNode == bytes32(0))
            {
                console2.log("BankonSubnameRegistrar   : SKIPPED (missing ENS / Bankon deps)");
            } else {
                BankonSubnameRegistrar b = new BankonSubnameRegistrar(
                    nameWrapper,
                    defaultResolver,
                    parentNode,
                    paymentRouter,
                    priceOracle,
                    reputationGate,
                    identityRegistry,
                    owner
                );
                out.bankonSubnameRegistrar = address(b);
                console2.log("BankonSubnameRegistrar   :", out.bankonSubnameRegistrar);
            }
        }

        vm.stopBroadcast();

        _writeReceipt(out, deployer);
    }

    function _writeReceipt(DeployedAddresses memory out, address deployer) internal {
        string memory chainDir = string.concat(
            "deployments/", vm.toString(block.chainid)
        );
        // Foundry's vm.createDir is not universally available; the build
        // script (`verify_tier1.sh`) creates the dir before invoking forge.

        string memory key = "tier1";
        string memory body;
        body = vm.serializeUint(key, "chainId", block.chainid);
        body = vm.serializeUint(key, "blockNumber", block.number);
        body = vm.serializeAddress(key, "deployer", deployer);
        body = vm.serializeAddress(key, "agentRegistry", out.agentRegistry);
        body = vm.serializeAddress(key, "thot", out.thot);
        body = vm.serializeAddress(key, "x402Receipt", out.x402Receipt);
        body = vm.serializeAddress(key, "inft7857", out.inft7857);
        body = vm.serializeAddress(key, "bankonSubnameRegistrar", out.bankonSubnameRegistrar);

        string memory path = string.concat(chainDir, "/tier1.json");
        vm.writeJson(body, path);
        console2.log("receipt written         :", path);
    }
}
