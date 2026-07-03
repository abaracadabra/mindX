// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Script, console2 } from "forge-std/Script.sol";
import { TimelockController } from "@openzeppelin/contracts/governance/TimelockController.sol";
import { IVotes }           from "@openzeppelin/contracts/governance/utils/IVotes.sol";

import { DeltaVerseDebtOracle }  from "../../src/core/DeltaVerseDebtOracle.sol";
import { GlobalDebtStressIndex } from "../../src/core/GlobalDebtStressIndex.sol";
import { iDEBT }                 from "../../src/core/iDEBT.sol";
import { X402PaymentGateway }   from "../../src/integrations/X402PaymentGateway.sol";
import { MindXBridge }           from "../../src/integrations/MindXBridge.sol";
import { AgenticPlaceRegistry }  from "../../src/integrations/AgenticPlaceRegistry.sol";
import { BANKONConnector }       from "../../src/integrations/BANKONConnector.sol";
import { DAIO }                  from "../../src/governance/DAIO.sol";
import { DAIOTreasury }          from "../../src/governance/DAIOTreasury.sol";
import { iDEBTVoteToken }        from "../../src/tokens/iDEBTVoteToken.sol";
import { ChainMapping }          from "../../src/libraries/ChainMapping.sol";

/// @title Deploy
/// @notice Canonical deployment script. Reads configuration from env vars and
///         broadcasts every contract in the iDEBT stack in one transaction
///         bundle.
///
///         Usage:
///           forge script script/deploy/Deploy.s.sol \
///             --rpc-url $NETWORK --broadcast --verify -vvvv
contract Deploy is Script {
    struct Addresses {
        address voteToken;
        address treasury;
        address governor;
        address oracle;
        address index;
        address debtToken;
        address x402;
        address mindx;
        address agents;
        address bankon;
    }

    function run() external returns (Addresses memory a) {
        address deployer = vm.envAddress("DEPLOYER_ADDRESS");
        uint256 pk       = vm.envUint("PRIVATE_KEY");
        address settlement = vm.envOr("SETTLEMENT_TOKEN", address(0));
        address mindxKey   = vm.envOr("MINDX_SIGNING_KEY", deployer);
        address bankonKey  = vm.envOr("BANKON_SIGNER", deployer);

        require(ChainMapping.isEvm(block.chainid), "chain not supported by iDEBT");

        vm.startBroadcast(pk);

        // 1. Governance stack
        a.voteToken = address(new iDEBTVoteToken(deployer, 100_000_000e18));

        address[] memory proposers = new address[](1); proposers[0] = deployer;
        address[] memory executors = new address[](1); executors[0] = address(0); // open executor
        a.treasury = address(new DAIOTreasury(
            vm.envOr("DAIO_TIMELOCK_DELAY", uint256(2 days)),
            proposers, executors, deployer
        ));

        a.governor = address(new DAIO(
            IVotes(a.voteToken),
            TimelockController(payable(a.treasury)),
            uint48(vm.envOr("DAIO_VOTING_DELAY",  uint256(7_200))),
            uint32(vm.envOr("DAIO_VOTING_PERIOD", uint256(50_400))),
            vm.envOr("DAIO_PROPOSAL_THRESHOLD", uint256(100_000e18)),
            uint8 (vm.envOr("DAIO_QUORUM_PCT",   uint256(20)))
        ));

        // Let the governor queue and execute through the treasury.
        TimelockController(payable(a.treasury)).grantRole(
            keccak256("PROPOSER_ROLE"),
            a.governor
        );
        TimelockController(payable(a.treasury)).grantRole(
            keccak256("CANCELLER_ROLE"),
            a.governor
        );

        // 2. Oracle stack — admin is the treasury.
        a.oracle = address(new DeltaVerseDebtOracle(a.treasury));
        a.index  = address(new GlobalDebtStressIndex(a.oracle, a.treasury));

        // 3. Integrations
        a.x402   = address(new X402PaymentGateway(a.treasury));
        a.mindx  = address(new MindXBridge(a.treasury, mindxKey));
        a.agents = address(new AgenticPlaceRegistry(a.treasury));
        a.bankon = address(new BANKONConnector(a.treasury, bankonKey));

        // 4. Core debt token
        require(settlement != address(0), "SETTLEMENT_TOKEN env required");
        a.debtToken = address(new iDEBT(a.index, settlement, a.treasury, a.treasury));

        vm.stopBroadcast();

        _log(a);
    }

    function _log(Addresses memory a) internal pure {
        console2.log("iDEBT deployment complete:");
        console2.log("  voteToken     ", a.voteToken);
        console2.log("  treasury      ", a.treasury);
        console2.log("  governor      ", a.governor);
        console2.log("  oracle        ", a.oracle);
        console2.log("  stressIndex   ", a.index);
        console2.log("  debtToken     ", a.debtToken);
        console2.log("  x402 gateway  ", a.x402);
        console2.log("  mindx bridge  ", a.mindx);
        console2.log("  agent registry", a.agents);
        console2.log("  bankon conn   ", a.bankon);
    }
}
