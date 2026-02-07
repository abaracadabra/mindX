// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../DAIOBridge.sol";
import "../XMindAgentRegistry.sol";
import "../XMindProposer.sol";
import "../XMindTreasuryReceiver.sol";
import "../test/mocks/MockDAIOGovernance.sol";
import "../test/mocks/MockIDNFT.sol";

/**
 * Deploy xmind contracts. On Anvil (or when env USE_MOCKS=1), deploys mocks and then xmind.
 * Otherwise expects DAIO_GOVERNANCE, IDNFT, AGENT_FACTORY, KNOWLEDGE_HIERARCHY in env.
 */
contract DeployXmind is Script {
    function run() external {
        address daioGov = vm.envOr("DAIO_GOVERNANCE", address(0));
        address idNFT = vm.envOr("IDNFT", address(0));
        address agentFactory = vm.envOr("AGENT_FACTORY", address(0));
        address knowledgeHierarchy = vm.envOr("KNOWLEDGE_HIERARCHY", address(0));
        bool useMocks = vm.envOr("USE_MOCKS", uint256(1)) == 1;

        if (useMocks || daioGov == address(0)) {
            vm.startBroadcast();
            MockDAIOGovernance mockGov = new MockDAIOGovernance();
            daioGov = address(mockGov);
            vm.stopBroadcast();
        }
        if (useMocks || idNFT == address(0)) {
            vm.startBroadcast();
            MockIDNFT mockIdNFT = new MockIDNFT();
            idNFT = address(mockIdNFT);
            agentFactory = agentFactory != address(0) ? agentFactory : address(0xFa);
            vm.stopBroadcast();
        }
        if (agentFactory == address(0)) agentFactory = address(0xFa);
        if (knowledgeHierarchy == address(0)) knowledgeHierarchy = address(0xKh);

        vm.startBroadcast();
        DAIOBridge bridge = new DAIOBridge(daioGov);
        XMindAgentRegistry registry = new XMindAgentRegistry(idNFT, agentFactory);
        XMindProposer proposer = new XMindProposer(knowledgeHierarchy);
        XMindTreasuryReceiver treasuryReceiver = new XMindTreasuryReceiver();
        vm.stopBroadcast();

        console.log("DAIOBridge", address(bridge));
        console.log("XMindAgentRegistry", address(registry));
        console.log("XMindProposer", address(proposer));
        console.log("XMindTreasuryReceiver", address(treasuryReceiver));
    }
}
