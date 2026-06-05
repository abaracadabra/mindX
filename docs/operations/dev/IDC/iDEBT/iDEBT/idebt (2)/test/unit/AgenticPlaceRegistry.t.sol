// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import { Test }                  from "forge-std/Test.sol";
import { AgenticPlaceRegistry }  from "../../src/integrations/AgenticPlaceRegistry.sol";
import { IAgenticPlace }         from "../../src/interfaces/IAgenticPlace.sol";

contract AgenticPlaceRegistryTest is Test {
    AgenticPlaceRegistry reg;
    address admin = address(0xA11CE);
    address agentOwner = address(0xBEEF);
    bytes32 agentId = keccak256("agent-1");

    function setUp() public {
        reg = new AgenticPlaceRegistry(admin);
    }

    function test_Register_Succeeds() public {
        vm.prank(agentOwner);
        reg.register(agentId, "https://agent.pythai.net/a/1");

        IAgenticPlace.Agent memory a = reg.agentOf(agentId);
        assertEq(a.owner, agentOwner);
        assertEq(a.reputation, 1e18);
    }

    function test_DoubleRegisterReverts() public {
        vm.prank(agentOwner);
        reg.register(agentId, "x");
        vm.prank(address(0xDEAD));
        vm.expectRevert(IAgenticPlace.AgentExists.selector);
        reg.register(agentId, "y");
    }

    function test_AttestIncreasesReputation() public {
        vm.prank(agentOwner);
        reg.register(agentId, "x");
        vm.prank(admin);
        reg.attest(agentId, 5e17);

        assertEq(reg.reputationOf(agentId), 1.5e18);
    }

    function test_ReputationDecaysOverTime() public {
        vm.prank(agentOwner);
        reg.register(agentId, "x");
        uint128 start = reg.reputationOf(agentId);
        vm.warp(block.timestamp + 365 days);
        uint128 decayed = reg.reputationOf(agentId);
        assertLt(decayed, start);
    }

    function test_Slash_ReducesReputation() public {
        vm.prank(agentOwner);
        reg.register(agentId, "x");
        vm.prank(admin);
        reg.slash(agentId, 5e17, "misconduct");
        assertEq(reg.reputationOf(agentId), 0.5e18);
    }
}
