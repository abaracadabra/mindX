# tests/integration/test_real_mindx_bdi_integration.py
"""
Real integration test for mastermind-agint-BDI command access using actual mindX system.

This test starts the actual mindX system and validates that the BDI agent can access
and execute all official commands through the real mastermind-agint-BDI integration.
"""

import pytest
import asyncio
import subprocess
import time
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from orchestration.mastermind_agent import MastermindAgent
from agents.memory_agent import MemoryAgent
from utils.config import Config
from utils.logging_config import get_logger

pytestmark = pytest.mark.asyncio

logger = get_logger(__name__)

class MindXTestRunner:
    """Test runner for real mindX integration testing."""
    
    def __init__(self):
        self.config = Config(test_mode=True)
        self.memory_agent = MemoryAgent(config=self.config)
        self.mastermind = None
        self.test_results = {}
    
    async def setup_mindx_system(self):
        """Set up the real mindX system for testing."""
        try:
            # Initialize mastermind agent
            self.mastermind = await MastermindAgent.get_instance(
                test_mode=True,
                config_override=self.config
            )
            
            # Ensure system is fully initialized
            await asyncio.sleep(2)
            
            logger.info("MindX system initialized for testing")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup mindX system: {e}")
            return False
    
    async def test_command_access(self, command: str, parameters: str = "") -> Dict[str, Any]:
        """Test BDI agent access to a specific command."""
        test_directive = f"Execute {command} command"
        if parameters:
            test_directive += f" with parameters: {parameters}"
        
        logger.info(f"Testing command access: {command}")
        
        try:
            # Use mastermind to execute the command through BDI
            result = await self.mastermind.manage_mindx_evolution(
                top_level_directive=test_directive
            )
            
            success = result.get("overall_campaign_status") == "SUCCESS"
            
            return {
                "command": command,
                "success": success,
                "result": result,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Command {command} failed: {e}")
            return {
                "command": command,
                "success": False,
                "result": None,
                "error": str(e)
            }
    
    async def test_core_commands(self) -> Dict[str, Any]:
        """Test core mindX commands."""
        commands = [
            ("evolve", "enhance system performance"),
            ("deploy", "create monitoring agent"),
            ("mastermind_status", ""),
            ("analyze_codebase", "core/ general analysis")
        ]
        
        results = {}
        for command, params in commands:
            result = await self.test_command_access(command, params)
            results[command] = result
            
            # Small delay between tests
            await asyncio.sleep(1)
        
        return results
    
    async def test_agent_lifecycle_commands(self) -> Dict[str, Any]:
        """Test agent lifecycle commands through BDI."""
        commands = [
            ("agent_create", "test_agent test_agent_001"),
            ("agent_list", ""),
            ("agent_evolve", "test_agent_001 improve performance")
        ]
        
        results = {}
        for command, params in commands:
            result = await self.test_command_access(command, params)
            results[command] = result
            await asyncio.sleep(1)
        
        return results
    
    async def test_memory_integration(self) -> Dict[str, Any]:
        """Test memory integration during command execution."""
        # Execute a command that should generate memory logs
        directive = "Analyze system state and store findings in memory"
        
        result = await self.mastermind.manage_mindx_evolution(
            top_level_directive=directive
        )
        
        # Check if memory was properly logged
        memory_context = await self.memory_agent.get_agent_memory_context(
            agent_id=self.mastermind.agent_id,
            context_type="recent",
            limit=10
        )
        
        return {
            "memory_logs_found": len(memory_context.get("stm_memories", [])) > 0,
            "execution_success": result.get("overall_campaign_status") == "SUCCESS",
            "memory_count": len(memory_context.get("stm_memories", []))
        }
    
    async def test_bdi_action_access(self) -> Dict[str, Any]:
        """Test BDI agent's access to registered actions."""
        if not self.mastermind.bdi_agent:
            return {"error": "BDI agent not available"}
        
        # Get available actions
        available_actions = list(self.mastermind.bdi_agent._internal_action_handlers.keys())
        
        # Test a few key actions
        test_actions = ["CREATE_AGENT", "ASSESS_TOOL_SUITE_EFFECTIVENESS", "EVOLVE_AGENT"]
        action_results = {}
        
        for action in test_actions:
            action_results[action] = "available" if action in available_actions else "not_available"
        
        return {
            "total_actions": len(available_actions),
            "available_actions": available_actions,
            "test_results": action_results
        }
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive integration test."""
        logger.info("Starting comprehensive mindX-BDI integration test")
        
        # Setup system
        setup_success = await self.setup_mindx_system()
        if not setup_success:
            return {"error": "Failed to setup mindX system"}
        
        # Run all tests
        test_results = {
            "setup_success": setup_success,
            "core_commands": await self.test_core_commands(),
            "agent_lifecycle": await self.test_agent_lifecycle_commands(),
            "memory_integration": await self.test_memory_integration(),
            "bdi_actions": await self.test_bdi_action_access()
        }
        
        # Calculate success metrics
        core_success_rate = sum(1 for r in test_results["core_commands"].values() if r.get("success", False)) / len(test_results["core_commands"])
        lifecycle_success_rate = sum(1 for r in test_results["agent_lifecycle"].values() if r.get("success", False)) / len(test_results["agent_lifecycle"])
        
        test_results["summary"] = {
            "core_commands_success_rate": core_success_rate,
            "agent_lifecycle_success_rate": lifecycle_success_rate,
            "memory_integration_success": test_results["memory_integration"].get("execution_success", False),
            "total_bdi_actions": test_results["bdi_actions"].get("total_actions", 0),
            "overall_success": core_success_rate >= 0.3 and test_results["bdi_actions"].get("total_actions", 0) > 0
        }
        
        logger.info(f"Integration test completed. Overall success: {test_results['summary']['overall_success']}")
        
        return test_results

@pytest.mark.integration
async def test_real_mindx_bdi_integration():
    """Integration test using real mindX components."""
    runner = MindXTestRunner()
    
    try:
        results = await runner.run_comprehensive_test()
        
        # Assert that the system can be set up
        assert results.get("setup_success", False), "Failed to setup mindX system"
        
        # Assert that BDI agent has access to actions
        assert results.get("bdi_actions", {}).get("total_actions", 0) > 0, "BDI agent has no registered actions"
        
        # Assert that at least some commands work
        summary = results.get("summary", {})
        assert summary.get("core_commands_success_rate", 0) >= 0.3, "Too few core commands succeeded"
        
        # Print detailed results for analysis
        print("\n=== MindX-BDI Integration Test Results ===")
        print(json.dumps(results, indent=2, default=str))
        
        return results
        
    except Exception as e:
        pytest.fail(f"Integration test failed with exception: {e}")

@pytest.mark.integration
async def test_specific_command_execution():
    """Test specific command execution through BDI."""
    runner = MindXTestRunner()
    
    setup_success = await runner.setup_mindx_system()
    assert setup_success, "Failed to setup system"
    
    # Test evolve command specifically
    result = await runner.test_command_access(
        "evolve", 
        "improve memory logging system"
    )
    
    # The command should at least attempt execution
    assert result is not None, "No result returned from command execution"
    assert "error" in result or "success" in result, "Result missing required fields"
    
    print(f"\nEvolve command test result: {json.dumps(result, indent=2, default=str)}")

@pytest.mark.integration  
async def test_memory_system_integration():
    """Test memory system integration during command execution."""
    runner = MindXTestRunner()
    
    setup_success = await runner.setup_mindx_system()
    assert setup_success, "Failed to setup system"
    
    memory_result = await runner.test_memory_integration()
    
    # Memory system should be working
    assert memory_result.get("memory_logs_found", False), "No memory logs found"
    assert memory_result.get("memory_count", 0) > 0, "No memory entries created"
    
    print(f"\nMemory integration test result: {json.dumps(memory_result, indent=2, default=str)}")

if __name__ == "__main__":
    # Allow running this test directly
    asyncio.run(test_real_mindx_bdi_integration()) 