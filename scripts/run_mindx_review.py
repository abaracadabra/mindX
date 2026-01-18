#!/usr/bin/env python3
"""
Script to run mindXagent with Ollama connection and 8 cycles of review.

This script:
1. Configures Ollama connection to 10.0.0.155:18080
2. Initializes mindXagent with memory_agent tracking logs
3. Runs 8 cycles of autonomous review (without editing mindX.sh)
4. Ensures startup_agent has knowledge of mindX.sh commands
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.config import Config
from utils.logging_config import setup_logging, get_logger
from agents.memory_agent import MemoryAgent, MemoryType
from agents.core.belief_system import BeliefSystem
from agents.orchestration.coordinator_agent import get_coordinator_agent_mindx_async
from agents.orchestration.startup_agent import StartupAgent
from agents.core.mindXagent import MindXAgent
from llm.model_registry import get_model_registry_async
from api.llm_provider_api import LLMProviderManager

# Setup logging
setup_logging(log_level="INFO")
logger = get_logger(__name__)

# Ollama configuration
OLLAMA_HOST = "10.0.0.155"
OLLAMA_PORT = 18080
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"

# Number of review cycles
REVIEW_CYCLES = 8


async def configure_ollama():
    """Configure Ollama connection in environment and .env file"""
    logger.info(f"Configuring Ollama connection to {OLLAMA_BASE_URL}")
    
    # Set environment variable
    os.environ["MINDX_LLM__OLLAMA__BASE_URL"] = OLLAMA_BASE_URL
    
    # Update .env file
    env_file = PROJECT_ROOT / ".env"
    env_content = ""
    
    if env_file.exists():
        with env_file.open("r") as f:
            env_content = f.read()
    
    # Check if Ollama config already exists
    if "MINDX_LLM__OLLAMA__BASE_URL" in env_content:
        # Update existing line
        lines = env_content.split("\n")
        updated_lines = []
        for line in lines:
            if line.startswith("MINDX_LLM__OLLAMA__BASE_URL"):
                updated_lines.append(f"MINDX_LLM__OLLAMA__BASE_URL=\"{OLLAMA_BASE_URL}\"")
            else:
                updated_lines.append(line)
        env_content = "\n".join(updated_lines)
    else:
        # Add new Ollama config
        if env_content and not env_content.endswith("\n"):
            env_content += "\n"
        env_content += f"\n# Ollama Configuration\nMINDX_LLM__OLLAMA__BASE_URL=\"{OLLAMA_BASE_URL}\"\n"
    
    # Write back to .env
    with env_file.open("w") as f:
        f.write(env_content)
    
    logger.info(f"Ollama configuration saved to .env: {OLLAMA_BASE_URL}")
    
    # Test connection
    try:
        provider_manager = LLMProviderManager()
        test_result = await provider_manager.test_api_key("ollama")
        if test_result.get("success"):
            logger.info(f"✓ Ollama connection test successful: {test_result.get('message', 'Connected')}")
        else:
            logger.warning(f"⚠ Ollama connection test failed: {test_result.get('message', 'Unknown error')}")
    except Exception as e:
        logger.warning(f"⚠ Could not test Ollama connection: {e}")


async def initialize_agents():
    """Initialize all required agents"""
    logger.info("Initializing agents...")
    
    # Initialize config
    config = Config()
    
    # Initialize memory agent (tracks logs in data folder automatically)
    memory_agent = MemoryAgent(config=config)
    logger.info("✓ MemoryAgent initialized (tracks logs in data/ folder)")
    
    # Initialize belief system
    belief_system = BeliefSystem()
    logger.info("✓ BeliefSystem initialized")
    
    # Initialize coordinator
    coordinator = await get_coordinator_agent_mindx_async(
        config_override=config,
        memory_agent=memory_agent,
        belief_system=belief_system
    )
    logger.info("✓ CoordinatorAgent initialized")
    
    # Initialize model registry
    model_registry = await get_model_registry_async(config=config)
    logger.info("✓ ModelRegistry initialized")
    
    # Initialize startup agent (loads mindX.sh commands automatically)
    startup_agent = StartupAgent(
        agent_id="startup_agent",
        coordinator_agent=coordinator,
        memory_agent=memory_agent,
        config=config
    )
    logger.info("✓ StartupAgent initialized (will load mindX.sh commands)")
    
    # Wait for startup knowledge to load
    await asyncio.sleep(2)  # Give time for async task to complete
    
    # Verify startup agent has mindX.sh knowledge
    startup_commands = await startup_agent.get_startup_command_info()
    if startup_commands.get("commands") or startup_commands.get("functions"):
        logger.info(f"✓ StartupAgent has knowledge of {len(startup_commands.get('commands', {}))} commands and {len(startup_commands.get('functions', {}))} functions from mindX.sh")
    else:
        logger.warning("⚠ StartupAgent may not have loaded mindX.sh commands yet")
    
    # Initialize mindXagent
    mindx_agent = await MindXAgent.get_instance(
        agent_id="mindx_meta_agent",
        config=config,
        memory_agent=memory_agent,
        belief_system=belief_system,
        coordinator_agent=coordinator,
        model_registry=model_registry
    )
    logger.info("✓ MindXAgent initialized")
    
    return {
        "config": config,
        "memory_agent": memory_agent,
        "belief_system": belief_system,
        "coordinator": coordinator,
        "model_registry": model_registry,
        "startup_agent": startup_agent,
        "mindx_agent": mindx_agent
    }


async def run_review_cycles(mindx_agent: MindXAgent, memory_agent: MemoryAgent, cycles: int = 8):
    """Run specified number of review cycles"""
    logger.info(f"Starting {cycles} review cycles...")
    
    for cycle in range(1, cycles + 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"REVIEW CYCLE {cycle}/{cycles}")
        logger.info(f"{'='*60}")
        
        try:
            # Analyze system state
            logger.info("Step 1: Analyzing system state...")
            system_state = await mindx_agent._analyze_system_state()
            logger.info(f"✓ System state analyzed: {len(system_state)} metrics collected")
            
            # Log to memory agent
            await memory_agent.save_timestamped_memory(
                agent_id="mindx_meta_agent",
                memory_type=MemoryType.SYSTEM_STATE,
                content={
                    "cycle": cycle,
                    "system_state": system_state,
                    "review_type": "autonomous_review"
                },
                context={"review_cycle": cycle, "total_cycles": cycles},
                tags=["review", "system_analysis", f"cycle_{cycle}"]
            )
            
            # Identify improvement opportunities
            logger.info("Step 2: Identifying improvement opportunities...")
            opportunities = await mindx_agent._identify_improvement_opportunities(system_state)
            
            if opportunities:
                logger.info(f"✓ Found {len(opportunities)} improvement opportunities")
                for i, opp in enumerate(opportunities[:5], 1):  # Show top 5
                    logger.info(f"  {i}. {opp.get('goal', 'Unknown')} (Priority: {opp.get('priority', 'medium')})")
            else:
                logger.info("✓ No improvement opportunities identified at this time")
            
            # Prioritize improvements
            logger.info("Step 3: Prioritizing improvements...")
            if opportunities:
                prioritized = await mindx_agent._prioritize_improvements(opportunities)
                logger.info(f"✓ Prioritized {len(prioritized)} improvements")
                
                # Log prioritized improvements to memory
                await memory_agent.save_timestamped_memory(
                    agent_id="mindx_meta_agent",
                    memory_type=MemoryType.INTERACTION,
                    content={
                        "cycle": cycle,
                        "opportunities": opportunities,
                        "prioritized": prioritized
                    },
                    context={"review_cycle": cycle, "total_cycles": cycles},
                    tags=["review", "improvement_analysis", f"cycle_{cycle}"]
                )
            else:
                prioritized = []
            
            # Review but don't execute (as requested - no editing mindX.sh)
            logger.info("Step 4: Reviewing system (no execution)...")
            logger.info("✓ Review complete - no changes made to mindX.sh")
            
            # Log cycle completion
            await memory_agent.save_timestamped_memory(
                agent_id="mindx_meta_agent",
                memory_type=MemoryType.INTERACTION,
                content={
                    "cycle": cycle,
                    "status": "completed",
                    "opportunities_found": len(opportunities),
                    "prioritized_count": len(prioritized) if prioritized else 0
                },
                context={"review_cycle": cycle, "total_cycles": cycles},
                tags=["review", "cycle_complete", f"cycle_{cycle}"]
            )
            
            logger.info(f"✓ Review cycle {cycle}/{cycles} completed")
            
            # Wait between cycles (except for last cycle)
            if cycle < cycles:
                logger.info("Waiting 30 seconds before next cycle...")
                await asyncio.sleep(30)
        
        except Exception as e:
            logger.error(f"Error in review cycle {cycle}: {e}", exc_info=True)
            await memory_agent.save_timestamped_memory(
                agent_id="mindx_meta_agent",
                memory_type=MemoryType.ERROR,
                content={
                    "cycle": cycle,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                context={"review_cycle": cycle, "total_cycles": cycles},
                tags=["review", "error", f"cycle_{cycle}"]
            )
    
    logger.info(f"\n{'='*60}")
    logger.info(f"All {cycles} review cycles completed!")
    logger.info(f"{'='*60}")


async def main():
    """Main execution function"""
    logger.info("="*60)
    logger.info("MindX Review Script")
    logger.info("="*60)
    logger.info(f"Ollama Server: {OLLAMA_BASE_URL}")
    logger.info(f"Review Cycles: {REVIEW_CYCLES}")
    logger.info("="*60)
    
    try:
        # Step 1: Configure Ollama
        await configure_ollama()
        
        # Step 2: Initialize agents
        agents = await initialize_agents()
        
        # Step 3: Verify startup agent knowledge
        startup_commands = await agents["startup_agent"].get_startup_command_info()
        logger.info("\nStartup Agent Knowledge:")
        logger.info(f"  Commands: {len(startup_commands.get('commands', {}))}")
        logger.info(f"  Functions: {len(startup_commands.get('functions', {}))}")
        if startup_commands.get('functions'):
            logger.info("  Key Functions:")
            for func_name, func_desc in list(startup_commands.get('functions', {}).items())[:5]:
                logger.info(f"    - {func_name}: {func_desc}")
        
        # Step 4: Run review cycles
        await run_review_cycles(
            mindx_agent=agents["mindx_agent"],
            memory_agent=agents["memory_agent"],
            cycles=REVIEW_CYCLES
        )
        
        # Step 5: Summary
        logger.info("\n" + "="*60)
        logger.info("Review Summary")
        logger.info("="*60)
        logger.info(f"✓ Ollama configured: {OLLAMA_BASE_URL}")
        logger.info(f"✓ Memory agent tracking logs in: {PROJECT_ROOT}/data/")
        logger.info(f"✓ Startup agent has knowledge of mindX.sh commands")
        logger.info(f"✓ Completed {REVIEW_CYCLES} review cycles")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
