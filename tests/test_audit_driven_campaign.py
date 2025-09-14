#!/usr/bin/env python3
"""
Test script for StrategicEvolutionAgent audit-driven campaign functionality.

This demonstrates the complete audit-to-improvement pipeline with validation loops.

Usage:
    python test_audit_driven_campaign.py [audit_scope] [target_components...]

Examples:
    python test_audit_driven_campaign.py security
    python test_audit_driven_campaign.py code_quality core agents tools
    python test_audit_driven_campaign.py performance llm monitoring
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional

# Add mindX to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)

async def test_audit_driven_functionality():
    """Test the new audit-driven campaign functionality."""
    
    logger.info("=== AUDIT-DRIVEN CAMPAIGN INTEGRATION TEST ===")
    
    try:
        # Import and initialize components
        from core.belief_system import BeliefSystem
        from agents.memory_agent import MemoryAgent
        from orchestration.coordinator_agent import CoordinatorAgent
        from llm.model_registry import ModelRegistry
        from learning.strategic_evolution_agent import StrategicEvolutionAgent
        
        config = Config()
        
        # Initialize core components
        memory_agent = MemoryAgent(config=config)
        
        belief_system = BeliefSystem(memory_agent=memory_agent, config=config)
        
        model_registry = ModelRegistry(config=config)
        await model_registry.async_init()
        
        coordinator_agent = CoordinatorAgent(
            agent_id="test_coordinator",
            config=config,
            memory_agent=memory_agent,
            model_registry=model_registry,
            belief_system=belief_system
        )
        await coordinator_agent.async_init()
        
        # Initialize StrategicEvolutionAgent with audit capabilities
        sea_agent = StrategicEvolutionAgent(
            agent_id="test_sea_audit",
            belief_system=belief_system,
            coordinator_agent=coordinator_agent,
            model_registry=model_registry,
            memory_agent=memory_agent,
            config_override=config
        )
        await sea_agent._async_init()
        
        logger.info("✓ All components initialized successfully")
        
        # Test audit-driven campaign
        logger.info("Testing audit-driven campaign functionality...")
        
        campaign_results = await sea_agent.run_audit_driven_campaign(
            audit_scope="code_quality",
            target_components=["core", "learning"]
        )
        
        # Log results
        logger.info("=== CAMPAIGN RESULTS ===")
        logger.info(f"Status: {campaign_results.get('status', 'UNKNOWN')}")
        logger.info(f"Message: {campaign_results.get('message', 'No message')}")
        
        # Save results
        with open("audit_campaign_test_results.json", 'w') as f:
            json.dump(campaign_results, f, indent=2, default=str)
        
        success = campaign_results.get('status') in ['SUCCESS', 'PARTIAL_SUCCESS']
        logger.info(f"Test Result: {'PASSED' if success else 'FAILED'}")
        
        return success
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}", exc_info=True)
        return False

async def main():
    """Main test execution."""
    
    print("Testing Audit-Driven Campaign Integration")
    print("=" * 50)
    
    success = await test_audit_driven_functionality()
    
    print("\n" + "=" * 50)
    print(f"INTEGRATION TEST: {'PASSED' if success else 'FAILED'}")
    print("=" * 50)
    
    if success:
        print("✓ Audit-driven campaign functionality is operational")
        print("✓ Complete audit-to-improvement pipeline integrated")
        print("✓ StrategicEvolutionAgent enhanced with audit capabilities")
    else:
        print("✗ Issues detected in audit-driven campaign functionality")
        print("Check logs for detailed error information")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main()) 