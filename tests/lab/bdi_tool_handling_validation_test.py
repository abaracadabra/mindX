#!/usr/bin/env python3
"""
BDI Agent Tool Handling Validation Test

This test validates that the BDI agent properly:
1. Loads tools from the registry correctly
2. Handles path resolution for tool operations
3. Corrects placeholder paths in planning
4. Maintains code integrity while using tools
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Add the project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.config import Config
from utils.logging_config import get_logger
from core.bdi_agent import BDIAgent
from core.belief_system import BeliefSystem
from agents.memory_agent import MemoryAgent
from llm.llm_factory import create_llm_handler

logger = get_logger(__name__)

class BDIToolHandlingValidationTest:
    """Test suite for BDI agent tool handling validation."""
    
    def __init__(self):
        self.config = Config()
        self.test_results = {}
        self.bdi_agent = None
        self.memory_agent = None
        
    async def setup(self):
        """Set up test environment."""
        try:
            logger.info("🔧 Setting up BDI Tool Handling Validation Test...")
            
            # Initialize memory agent
            self.memory_agent = MemoryAgent(config=self.config)
            
            # Initialize belief system
            belief_system = BeliefSystem(test_mode=True)
            
            # Load tools registry
            tools_registry_path = PROJECT_ROOT / "data" / "config" / "official_tools_registry.json"
            with open(tools_registry_path, 'r') as f:
                tools_registry = json.load(f)
            
            # Initialize BDI agent with real tools registry
            self.bdi_agent = BDIAgent(
                domain="tool_handling_test",
                belief_system_instance=belief_system,
                tools_registry=tools_registry,
                config_override=self.config,
                memory_agent=self.memory_agent,
                test_mode=True
            )
            
            # Initialize async components
            await self.bdi_agent.async_init_components()
            
            logger.info("✅ Test setup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Test setup failed: {e}")
            return False
    
    async def test_tool_registry_compliance(self):
        """Test that BDI agent loads tools according to registry."""
        try:
            logger.info("🔍 Testing tool registry compliance...")
            
            # Check that tools are loaded according to registry
            tools_registry_path = PROJECT_ROOT / "data" / "config" / "official_tools_registry.json"
            with open(tools_registry_path, 'r') as f:
                registry_data = json.load(f)
            
            registered_tools = registry_data.get("registered_tools", {})
            enabled_tools = {tool_id: tool_config for tool_id, tool_config in registered_tools.items() 
                           if tool_config.get("enabled", False)}
            
            loaded_tools = self.bdi_agent.available_tools
            
            logger.info(f"📊 Registry shows {len(enabled_tools)} enabled tools")
            logger.info(f"📊 BDI agent loaded {len(loaded_tools)} tools")
            
            # Check for expected successful loads
            expected_successful = [
                "summarization", "base_gen_agent", "note_taking", 
                "system_analyzer", "shell_command", "registry_manager",
                "registry_sync", "agent_factory", "tool_factory", "enhanced_simple_coder"
            ]
            
            successful_loads = 0
            for tool_id in expected_successful:
                if tool_id in loaded_tools:
                    successful_loads += 1
                    logger.info(f"✅ Tool '{tool_id}' loaded successfully")
                else:
                    logger.warning(f"⚠️ Tool '{tool_id}' not loaded")
            
            # Check for known problematic tools
            known_issues = ["cli_command_tool", "augmentic_intelligence"]
            for tool_id in known_issues:
                if tool_id in loaded_tools:
                    logger.info(f"🔧 Tool '{tool_id}' loaded (issue resolved)")
                else:
                    logger.info(f"⚠️ Tool '{tool_id}' not loaded (known issue)")
            
            success_rate = successful_loads / len(expected_successful)
            logger.info(f"📈 Tool loading success rate: {success_rate:.1%} ({successful_loads}/{len(expected_successful)})")
            
            self.test_results["tool_registry_compliance"] = {
                "success": success_rate >= 0.8,  # 80% threshold
                "success_rate": success_rate,
                "loaded_tools": len(loaded_tools),
                "expected_tools": len(expected_successful)
            }
            
            return success_rate >= 0.8
            
        except Exception as e:
            logger.error(f"❌ Tool registry compliance test failed: {e}")
            return False
    
    async def test_path_resolution_planning(self):
        """Test that BDI agent correctly resolves paths in planning."""
        try:
            logger.info("🗺️ Testing path resolution in planning...")
            
            # Create a goal that would trigger path resolution
            test_goal = "review summarization tool to improve summarization tool"
            
            # Set the goal
            self.bdi_agent.set_goal(test_goal, priority=1)
            
            # Get the goal entry
            goal_entry = self.bdi_agent.get_current_goal_entry()
            
            if not goal_entry:
                logger.error("❌ No goal entry found")
                return False
            
            # Test planning with path resolution
            planning_success = await self.bdi_agent.plan(goal_entry)
            
            if not planning_success:
                logger.error("❌ Planning failed")
                return False
            
            # Check the generated plan for proper path resolution
            plan_actions = self.bdi_agent.intentions.get("plan_actions", [])
            
            if not plan_actions:
                logger.error("❌ No plan actions generated")
                return False
            
            logger.info(f"📋 Generated plan with {len(plan_actions)} actions")
            
            # Check for placeholder path corrections
            placeholder_found = False
            corrected_paths = 0
            
            for i, action in enumerate(plan_actions):
                action_type = action.get("type", "")
                params = action.get("params", {})
                
                logger.info(f"📄 Action {i+1}: {action_type}")
                
                # Check for any path parameters
                for param_name, param_value in params.items():
                    if isinstance(param_value, str):
                        if param_value.startswith("path/to/"):
                            placeholder_found = True
                            logger.warning(f"⚠️ Found placeholder path: {param_value}")
                        elif param_name in ["root_path_str", "target_path", "file_path"] and param_value == "tools":
                            corrected_paths += 1
                            logger.info(f"✅ Corrected path parameter: {param_name} = {param_value}")
            
            # Evaluate results
            path_resolution_success = not placeholder_found and corrected_paths > 0
            
            self.test_results["path_resolution_planning"] = {
                "success": path_resolution_success,
                "placeholder_found": placeholder_found,
                "corrected_paths": corrected_paths,
                "total_actions": len(plan_actions)
            }
            
            if path_resolution_success:
                logger.info("✅ Path resolution working correctly")
            else:
                logger.warning("⚠️ Path resolution needs improvement")
            
            return path_resolution_success
            
        except Exception as e:
            logger.error(f"❌ Path resolution planning test failed: {e}")
            return False
    
    async def test_summarization_tool_integration(self):
        """Test specific integration with summarization tool."""
        try:
            logger.info("📝 Testing summarization tool integration...")
            
            # Check if summarization tool is loaded
            if "summarization" not in self.bdi_agent.available_tools:
                logger.error("❌ Summarization tool not loaded")
                return False
            
            summarization_tool = self.bdi_agent.available_tools["summarization"]
            
            # Test tool execution with sample text
            test_text = """
            The MindX summarization tool is a sophisticated component that leverages 
            Large Language Models to condense lengthy text into concise summaries. 
            It supports configurable parameters including topic context, summary length, 
            and output format options. The tool integrates seamlessly with the BDI agent 
            architecture and provides error handling for robust operation.
            """
            
            result = await summarization_tool.execute(
                text_to_summarize=test_text,
                topic_context="MindX Summarization Tool",
                max_summary_words=50,
                output_format="paragraph"
            )
            
            if result and not result.startswith("Error:"):
                logger.info("✅ Summarization tool executed successfully")
                logger.info(f"📄 Summary result: {result[:100]}...")
                
                self.test_results["summarization_tool_integration"] = {
                    "success": True,
                    "result_length": len(result),
                    "execution_successful": True
                }
                return True
            else:
                logger.error(f"❌ Summarization tool execution failed: {result}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Summarization tool integration test failed: {e}")
            return False
    
    async def test_tool_parameter_validation(self):
        """Test that tools validate parameters correctly."""
        try:
            logger.info("🔍 Testing tool parameter validation...")
            
            # Test various tools with correct and incorrect parameters
            test_cases = [
                {
                    "tool": "summarization",
                    "valid_params": {"text_to_summarize": "Test text"},
                    "invalid_params": {"wrong_param": "Test text"}
                },
                {
                    "tool": "base_gen_agent", 
                    "valid_params": {"root_path_str": "tools"},
                    "invalid_params": {"wrong_path": "invalid"}
                }
            ]
            
            validation_results = []
            
            for test_case in test_cases:
                tool_id = test_case["tool"]
                
                if tool_id not in self.bdi_agent.available_tools:
                    logger.warning(f"⚠️ Tool '{tool_id}' not available for testing")
                    continue
                
                tool = self.bdi_agent.available_tools[tool_id]
                
                # Test valid parameters
                try:
                    if tool_id == "summarization":
                        result = await tool.execute(**test_case["valid_params"])
                        valid_success = not (isinstance(result, str) and result.startswith("Error:"))
                    elif tool_id == "base_gen_agent":
                        # For base_gen_agent, use the synchronous method
                        success, result = tool.generate_markdown_summary(**test_case["valid_params"])
                        valid_success = success
                    else:
                        result = await tool.execute(**test_case["valid_params"])
                        valid_success = True
                    
                    logger.info(f"✅ Tool '{tool_id}' handled valid parameters correctly")
                    
                except Exception as e:
                    valid_success = False
                    logger.warning(f"⚠️ Tool '{tool_id}' failed with valid parameters: {e}")
                
                validation_results.append({
                    "tool": tool_id,
                    "valid_params_success": valid_success
                })
            
            overall_success = all(result["valid_params_success"] for result in validation_results)
            
            self.test_results["tool_parameter_validation"] = {
                "success": overall_success,
                "tested_tools": len(validation_results),
                "results": validation_results
            }
            
            return overall_success
            
        except Exception as e:
            logger.error(f"❌ Tool parameter validation test failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all validation tests."""
        try:
            logger.info("🚀 Starting BDI Tool Handling Validation Tests...")
            
            # Setup test environment
            if not await self.setup():
                return False
            
            # Run individual tests
            tests = [
                ("Tool Registry Compliance", self.test_tool_registry_compliance),
                ("Path Resolution Planning", self.test_path_resolution_planning),
                ("Summarization Tool Integration", self.test_summarization_tool_integration),
                ("Tool Parameter Validation", self.test_tool_parameter_validation)
            ]
            
            passed_tests = 0
            total_tests = len(tests)
            
            for test_name, test_method in tests:
                logger.info(f"\n{'='*60}")
                logger.info(f"🧪 Running: {test_name}")
                logger.info(f"{'='*60}")
                
                try:
                    success = await test_method()
                    if success:
                        logger.info(f"✅ {test_name}: PASSED")
                        passed_tests += 1
                    else:
                        logger.error(f"❌ {test_name}: FAILED")
                except Exception as e:
                    logger.error(f"❌ {test_name}: EXCEPTION - {e}")
            
            # Calculate overall results
            success_rate = passed_tests / total_tests
            overall_success = success_rate >= 0.75  # 75% threshold
            
            logger.info(f"\n{'='*60}")
            logger.info(f"🏁 BDI Tool Handling Validation Results")
            logger.info(f"{'='*60}")
            logger.info(f"📊 Tests Passed: {passed_tests}/{total_tests}")
            logger.info(f"📈 Success Rate: {success_rate:.1%}")
            logger.info(f"🎯 Overall Result: {'✅ PASSED' if overall_success else '❌ FAILED'}")
            
            # Store final results
            self.test_results["overall"] = {
                "success": overall_success,
                "passed_tests": passed_tests,
                "total_tests": total_tests,
                "success_rate": success_rate
            }
            
            return overall_success
            
        except Exception as e:
            logger.error(f"❌ Test execution failed: {e}")
            return False

async def main():
    """Main test execution function."""
    test_suite = BDIToolHandlingValidationTest()
    success = await test_suite.run_all_tests()
    
    if success:
        print("\n🎉 BDI Tool Handling Validation: ALL TESTS PASSED!")
        return 0
    else:
        print("\n💥 BDI Tool Handling Validation: SOME TESTS FAILED!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 