#!/usr/bin/env python3
"""
Test Script: BDI Agent Enhanced Simple Coder Integration

This script tests the integration between BDI Agent and Enhanced Simple Coder
to ensure the BDI agent can successfully write code using SimpleCoder.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.bdi_agent import BDIAgent
from core.belief_system import BeliefSystem
from agents.memory_agent import MemoryAgent
from utils.config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)

async def test_simple_coder_integration():
    """Test the enhanced simple coder integration with BDI agent."""
    logger.info("🚀 Testing SimpleCoder-BDI Integration...")
    
    try:
        # Setup minimal BDI agent
        config = Config()
        memory_agent = MemoryAgent(config=config, log_level="INFO")
        belief_system = BeliefSystem(test_mode=True)
        
        bdi_agent = BDIAgent(
            domain="simple_coder_test",
            belief_system_instance=belief_system,
            tools_registry={"registered_tools": {}},
            config_override=config,
            memory_agent=memory_agent,
            test_mode=True
        )
        
        await bdi_agent.async_init_components()
        
        logger.info(f"✅ BDI agent initialized. Enhanced Simple Coder available: {bdi_agent.enhanced_simple_coder is not None}")
        
        if not bdi_agent.enhanced_simple_coder:
            logger.error("❌ Enhanced Simple Coder not available!")
            return False
        
        # Test 1: Basic file operation
        logger.info("📝 Testing file write operation...")
        write_action = {
            "type": "WRITE_FILE",
            "id": "test_write",
            "params": {
                "path": "test_hello.py",
                "content": "print('Hello from BDI Agent via SimpleCoder!')\n"
            }
        }
        
        success, result = await bdi_agent._execute_write_file(write_action)
        logger.info(f"Write file result: Success={success}, Result={result}")
        
        if success:
            logger.info("✅ File write operation successful!")
        else:
            logger.error("❌ File write operation failed!")
            return False
        
        # Test 2: Code generation
        logger.info("🧠 Testing code generation...")
        generate_action = {
            "type": "GENERATE_CODE", 
            "id": "test_generate",
            "params": {
                "description": "Create a simple function to add two numbers",
                "language": "python"
            }
        }
        
        success, result = await bdi_agent._execute_generate_code(generate_action)
        logger.info(f"Generate code result: Success={success}")
        
        if success:
            logger.info("✅ Code generation successful!")
        else:
            logger.error("❌ Code generation failed!")
            return False
        
        # Test 3: Set a coding goal
        logger.info("🎯 Testing goal setting for coding task...")
        goal_description = "Write a Python function to calculate factorial"
        bdi_agent.set_goal(goal_description, priority=1, is_primary=True)
        
        current_goal = bdi_agent.get_current_goal_entry()
        if current_goal:
            logger.info(f"✅ Goal set successfully: {current_goal['goal']}")
        else:
            logger.error("❌ Goal setting failed!")
            return False
        
        logger.info("🎉 ALL TESTS PASSED! SimpleCoder-BDI integration is working!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = asyncio.run(test_simple_coder_integration())
    if success:
        print("\n🎉 SUCCESS: BDI agent can now write code using SimpleCoder!")
    else:
        print("\n❌ FAILED: Integration needs debugging.")
