// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";

import {BankonSubnameRegistrar} from "../contracts/BankonSubnameRegistrar.sol";
import {BankonPriceOracle}      from "../contracts/BankonPriceOracle.sol";
import {BankonReputationGate}   from "../contracts/BankonReputationGate.sol";
import {BankonPaymentRouter}    from "../contracts/BankonPaymentRouter.sol";
import {BankonSubnameResolver}   from "../contracts/BankonSubnameResolver.sol";
import {BankonSubnameResolverV2} from "../contracts/BankonSubnameResolverV2.sol";
import {BankonInftAdapter}      from "../contracts/BankonInftAdapter.sol";
import {BankonX402Attestor}     from "../contracts/BankonX402Attestor.sol";
import {BankonAgenticPlaceHook} from "../contracts/BankonAgenticPlaceHook.sol";
import {BankonEthRegistrar, IETHRegistrarController} from "../contracts/BankonEthRegistrar.sol";
import {BankonDomainHosting}    from "../contracts/BankonDomainHosting.sol";

import {AgentRegistry} from "../contracts/identity/AgentRegistry.sol";
import {X402Receipt}   from "../contracts/x402/X402Receipt.sol";

import {INameWrapper, IPublicResolver, IBankonPriceOracle, IBankonReputationGate, IBankonPaymentRouter}
    from "../contracts/interfaces/IBankon.sol";
import {IBankonSubnameResolver, IBankonInftAdapter, IBankonX402Attestor, IBankonAgenticPlaceHook}
    from "../contracts/interfaces/IBankonExtensions.sol";

/// @title  DeployEthereum
/// @notice Tier-1 Ethereum deploy. Mainnet or Sepolia, env-flagged.
///
///         Env vars consumed:
///           - DEPLOYER_PK              private key of the deploy EOA
///           - TREASURY_ADDR            BANKON Treasury Safe address (admin)
///           - NAME_WRAPPER_ADDR        ENS NameWrapper (mainnet 0xD4416b…, sepolia 0x0635…)
///           - ETH_REGISTRAR_CONTROLLER ENS ETHRegistrarController (mainnet 0x59E1…)
///           - BANKON_ETH_NODE          bytes32 namehash("bankon.eth")
///           - WEBHOOK_URL              AgenticPlace indexer webhook URL
///           - SUBNAME_NODE_EXPIRY      (optional) default expiry seconds for new bankon.eth children
///
///         The script reverts on any address-reference mismatch against
///         docs/ADDR_REFERENCE.md to catch the Sepolia-vs-mainnet drift the ENS
///         docs warn about. Re-verify manually before mainnet deploy.
contract DeployEthereum is Script {
    struct Deployed {
        address agentRegistry;
        address x402Receipt;
        address resolver;       // V1 — legacy compatibility, BankonSubnameRegistrar binds to this
        address resolverV2;     // V2 — ENSIP-10 wildcard + full profile (Phase 2.1)
        address inftAdapter;
        address x402Attestor;
        address agenticPlaceHook;
        address priceOracle;
        address reputationGate;
        address paymentRouter;
        address subnameRegistrar;
        address ethRegistrar;
        address domainHosting;
    }

    function run() external returns (Deployed memory d) {
        uint256 pk          = vm.envUint("DEPLOYER_PK");
        address treasury    = vm.envAddress("TREASURY_ADDR");
        address nameWrapper = vm.envAddress("NAME_WRAPPER_ADDR");
        address ensController = vm.envAddress("ETH_REGISTRAR_CONTROLLER");
        string  memory webhook = vm.envString("WEBHOOK_URL");

        // Sanity check against the docs/ADDR_REFERENCE.md canonical mainnet
        // addresses. Mismatch => reverts. Sepolia is allowed via env override
        // only.
        _verifyChainAddresses(nameWrapper, ensController);

        vm.startBroadcast(pk);

        // Tier-1 order:
        d.priceOracle    = address(new BankonPriceOracle(treasury));
        d.reputationGate = address(new BankonReputationGate(treasury));
        d.paymentRouter  = address(new BankonPaymentRouter(treasury));

        d.agentRegistry    = address(new AgentRegistry("BANKON Agent Registry", "AGENT", treasury));
        d.x402Receipt      = address(new X402Receipt(treasury, IBankonPaymentRouter(d.paymentRouter)));
        d.x402Attestor     = address(new BankonX402Attestor(treasury));
        d.agenticPlaceHook = address(new BankonAgenticPlaceHook(treasury, webhook));

        // Resolver first as adapter-less shell, then InftAdapter, then wire them.
        d.resolver = address(new BankonSubnameResolver(treasury, IBankonInftAdapter(address(0))));
        d.inftAdapter = address(new BankonInftAdapter(treasury, IBankonSubnameResolver(d.resolver)));
        BankonSubnameResolver(d.resolver).setInftAdapter(IBankonInftAdapter(d.inftAdapter));

        // V2 resolver — co-deployed (Phase 2.1). New registrations should bind
        // here for ENSIP-10 wildcard + full profile interfaces; legacy names
        // stay on V1 until explicit migration.
        d.resolverV2 = address(new BankonSubnameResolverV2(treasury, IBankonInftAdapter(d.inftAdapter)));

        // BankonSubnameRegistrar takes plain addresses, not interface types.
        // Constructor: (nameWrapper, defaultResolver, parentNode, paymentRouter,
        //   priceOracle, reputationGate, identityRegistry8004, admin)
        d.subnameRegistrar = address(new BankonSubnameRegistrar(
            nameWrapper,
            d.resolver,
            vm.envBytes32("BANKON_ETH_NODE"),
            d.paymentRouter,
            d.priceOracle,
            d.reputationGate,
            d.agentRegistry,
            treasury
        ));

        d.ethRegistrar = address(new BankonEthRegistrar(
            treasury,
            IETHRegistrarController(ensController),
            IBankonPriceOracle(d.priceOracle),
            IBankonPaymentRouter(d.paymentRouter),
            IBankonX402Attestor(d.x402Attestor)
        ));

        d.domainHosting = address(new BankonDomainHosting(
            treasury,
            INameWrapper(nameWrapper),
            IPublicResolver(d.resolver),
            IBankonPaymentRouter(d.paymentRouter),
            IBankonX402Attestor(d.x402Attestor)
        ));

        // Grant roles — the resolver and the inftAdapter need to know who can call them.
        BankonSubnameResolver(d.resolver).grantRegistrar(d.subnameRegistrar);
        BankonSubnameResolver(d.resolver).grantRegistrar(d.domainHosting);

        // Same grants on V2 so operators can flip the registrar pointer
        // without re-granting roles in a separate transaction.
        BankonSubnameResolverV2(d.resolverV2).grantRegistrar(d.subnameRegistrar);
        BankonSubnameResolverV2(d.resolverV2).grantRegistrar(d.domainHosting);
        BankonInftAdapter(d.inftAdapter).grantRegistrar(d.subnameRegistrar);
        BankonAgenticPlaceHook(d.agenticPlaceHook).grantLister(d.subnameRegistrar);
        BankonAgenticPlaceHook(d.agenticPlaceHook).grantLister(d.ethRegistrar);
        BankonAgenticPlaceHook(d.agenticPlaceHook).grantLister(d.domainHosting);
        BankonX402Attestor(d.x402Attestor).grantConsumer(d.subnameRegistrar);
        BankonX402Attestor(d.x402Attestor).grantConsumer(d.ethRegistrar);
        BankonX402Attestor(d.x402Attestor).grantConsumer(d.domainHosting);

        vm.stopBroadcast();

        console.log("BankonSubnameRegistrar deployed:", d.subnameRegistrar);
        console.log("BankonEthRegistrar deployed:",     d.ethRegistrar);
        console.log("BankonDomainHosting deployed:",    d.domainHosting);
        console.log("BankonSubnameResolver   (v1) :",   d.resolver);
        console.log("BankonSubnameResolverV2 (v2) :",   d.resolverV2);
        console.log("BankonInftAdapter deployed:",      d.inftAdapter);
        console.log("BankonX402Attestor deployed:",     d.x402Attestor);
        console.log("BankonAgenticPlaceHook deployed:", d.agenticPlaceHook);
        console.log("BankonPriceOracle deployed:",      d.priceOracle);
        console.log("BankonReputationGate deployed:",   d.reputationGate);
        console.log("BankonPaymentRouter deployed:",    d.paymentRouter);
        console.log("AgentRegistry deployed:",          d.agentRegistry);
        console.log("X402Receipt deployed:",            d.x402Receipt);
    }

    /// @dev Catches the Sepolia/mainnet address drift the ENS docs warn about
    ///      ("ETHRegistrarController earlier sources cited 0xfb3cE5… which is
    ///      Sepolia"). Skips the check when ALLOW_TESTNET=true.
    function _verifyChainAddresses(address nameWrapper, address ensController) internal view {
        bool allowTestnet = vm.envOr("ALLOW_TESTNET", false);
        if (allowTestnet) return;

        address expectedNameWrapper = 0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401;
        address expectedController  = 0x59E16fcCd424Cc24e280Be16E11Bcd56fb0CE547;

        require(
            nameWrapper == expectedNameWrapper,
            "NAME_WRAPPER_ADDR mismatch: see docs/ADDR_REFERENCE.md"
        );
        require(
            ensController == expectedController,
            "ETH_REGISTRAR_CONTROLLER mismatch: see docs/ADDR_REFERENCE.md"
        );
    }
}
