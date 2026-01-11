// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "@openzeppelin/contracts/governance/TimelockController.sol";

import "../src/DAIO_Constitution.sol";
import "../src/SoulBadger.sol";
import "../src/IDNFT.sol";
import "../src/KnowledgeHierarchyDAIO.sol";
import "../src/AgentFactory.sol";
import "../src/Treasury.sol";

/**
 * @title DeployDAIO
 * @dev Deployment script for DAIO smart contracts
 *
 * Deployment Order:
 * 1. TimelockController
 * 2. DAIO_Constitution
 * 3. SoulBadger (optional)
 * 4. IDNFT
 * 5. KnowledgeHierarchyDAIO
 * 6. AgentFactory
 * 7. Treasury
 */
contract DeployDAIO is Script {
    // Deployment addresses
    TimelockController public timelock;
    DAIO_Constitution public constitution;
    SoulBadger public soulBadger;
    IDNFT public idnft;
    KnowledgeHierarchyDAIO public knowledgeHierarchy;
    AgentFactory public agentFactory;
    Treasury public treasury;

    // Configuration
    uint256 public constant TIMELOCK_MIN_DELAY = 2 days;
    string public constant SOUL_BADGER_NAME = "DAIO Soul Badger";
    string public constant SOUL_BADGER_SYMBOL = "DSOUL";
    string public constant SOUL_BADGER_BASE_URI = "https://daio.mindx.io/soulbadger/";

    function run() external virtual {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console.log("Deploying DAIO contracts...");
        console.log("Deployer:", deployer);

        vm.startBroadcast(deployerPrivateKey);

        // 1. Deploy TimelockController
        address[] memory proposers = new address[](1);
        address[] memory executors = new address[](1);
        proposers[0] = deployer;
        executors[0] = deployer;

        timelock = new TimelockController(
            TIMELOCK_MIN_DELAY,
            proposers,
            executors,
            deployer
        );
        console.log("TimelockController deployed:", address(timelock));

        // 2. Deploy DAIO_Constitution
        constitution = new DAIO_Constitution(deployer, address(timelock));
        console.log("DAIO_Constitution deployed:", address(constitution));

        // 3. Deploy SoulBadger
        soulBadger = new SoulBadger(
            SOUL_BADGER_NAME,
            SOUL_BADGER_SYMBOL,
            SOUL_BADGER_BASE_URI
        );
        console.log("SoulBadger deployed:", address(soulBadger));

        // 4. Deploy IDNFT
        idnft = new IDNFT();
        idnft.setSoulBadger(address(soulBadger));
        console.log("IDNFT deployed:", address(idnft));

        // 5. Deploy KnowledgeHierarchyDAIO
        knowledgeHierarchy = new KnowledgeHierarchyDAIO(timelock);
        console.log("KnowledgeHierarchyDAIO deployed:", address(knowledgeHierarchy));

        // 6. Deploy AgentFactory
        agentFactory = new AgentFactory(address(knowledgeHierarchy));
        console.log("AgentFactory deployed:", address(agentFactory));

        // 7. Deploy Treasury
        treasury = new Treasury(address(constitution));
        console.log("Treasury deployed:", address(treasury));

        // Grant roles for integration
        _setupRoles(deployer);

        vm.stopBroadcast();

        // Log deployment summary
        _logDeploymentSummary();
    }

    function _setupRoles(address admin) internal {
        // Grant MINTER_ROLE to IDNFT on SoulBadger
        soulBadger.grantRole(soulBadger.MINTER_ROLE(), address(idnft));

        // Grant GOVERNANCE_ROLE to timelock on constitution
        constitution.grantRole(constitution.GOVERNANCE_ROLE(), address(timelock));

        // Grant AGENT_MANAGER_ROLE to AgentFactory on KnowledgeHierarchy
        knowledgeHierarchy.grantRole(
            knowledgeHierarchy.AGENT_MANAGER_ROLE(),
            address(agentFactory)
        );

        // Grant GOVERNANCE_ROLE to KnowledgeHierarchy on IDNFT
        idnft.grantRole(idnft.GOVERNANCE_ROLE(), address(knowledgeHierarchy));

        // Grant TREASURER_ROLE and SIGNER_ROLE on Treasury
        treasury.grantRole(treasury.TREASURER_ROLE(), admin);
        treasury.grantRole(treasury.SIGNER_ROLE(), admin);

        console.log("Roles configured successfully");
    }

    function _logDeploymentSummary() internal view {
        console.log("");
        console.log("=== DAIO Deployment Summary ===");
        console.log("");
        console.log("Contract Addresses:");
        console.log("  TimelockController:      ", address(timelock));
        console.log("  DAIO_Constitution:       ", address(constitution));
        console.log("  SoulBadger:              ", address(soulBadger));
        console.log("  IDNFT:                   ", address(idnft));
        console.log("  KnowledgeHierarchyDAIO:  ", address(knowledgeHierarchy));
        console.log("  AgentFactory:            ", address(agentFactory));
        console.log("  Treasury:                ", address(treasury));
        console.log("");
        console.log("================================");
    }
}

/**
 * @title DeployDAIOTestnet
 * @dev Testnet deployment with reduced timelock delay
 */
contract DeployDAIOTestnet is DeployDAIO {
    function run() external override {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console.log("Deploying DAIO contracts (TESTNET)...");
        console.log("Deployer:", deployer);

        vm.startBroadcast(deployerPrivateKey);

        // Use shorter timelock for testnet
        address[] memory proposers = new address[](1);
        address[] memory executors = new address[](1);
        proposers[0] = deployer;
        executors[0] = deployer;

        timelock = new TimelockController(
            1 hours, // Reduced for testing
            proposers,
            executors,
            deployer
        );
        console.log("TimelockController deployed:", address(timelock));

        // Deploy remaining contracts
        constitution = new DAIO_Constitution(deployer, address(timelock));
        console.log("DAIO_Constitution deployed:", address(constitution));

        soulBadger = new SoulBadger(
            "DAIO Soul Badger (Testnet)",
            "tDSOUL",
            "https://testnet.daio.mindx.io/soulbadger/"
        );
        console.log("SoulBadger deployed:", address(soulBadger));

        idnft = new IDNFT();
        idnft.setSoulBadger(address(soulBadger));
        console.log("IDNFT deployed:", address(idnft));

        knowledgeHierarchy = new KnowledgeHierarchyDAIO(timelock);
        console.log("KnowledgeHierarchyDAIO deployed:", address(knowledgeHierarchy));

        agentFactory = new AgentFactory(address(knowledgeHierarchy));
        console.log("AgentFactory deployed:", address(agentFactory));

        treasury = new Treasury(address(constitution));
        console.log("Treasury deployed:", address(treasury));

        _setupRoles(deployer);

        vm.stopBroadcast();

        _logDeploymentSummary();
    }
}
