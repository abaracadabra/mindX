#!/usr/bin/env python3
"""
Start Autonomous Evolution for MindX
====================================

This script provides a single call to start MindX for independent learning and evolution
from mastermind orchestration, including blueprint_agent.py integration.

Usage:
    python3 start_autonomous_evolution.py [--directive "evolution directive"] [--daemon]
"""

import asyncio
import sys
import os
import argparse
import signal
from pathlib import Path
from typing import Optional, Dict, Any

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestration.mastermind_agent import MastermindAgent
from orchestration.coordinator_agent import get_coordinator_agent_mindx_async
from orchestration.autonomous_audit_coordinator import AutonomousAuditCoordinator
from agents.memory_agent import MemoryAgent
from agents.guardian_agent import GuardianAgent
from agents.automindx_agent import AutoMINDXAgent
from core.id_manager_agent import IDManagerAgent
from core.belief_system import BeliefSystem
from llm.model_registry import get_model_registry_async
from utils.logging_config import get_logger, setup_logging
from utils.config import Config

logger = get_logger(__name__)

class AutonomousEvolutionManager:
    """Manages autonomous evolution and learning for MindX"""
    
    def __init__(self, config: Config):
        self.config = config
        self.mastermind: Optional[MastermindAgent] = None
        self.coordinator = None
        self.audit_coordinator: Optional[AutonomousAuditCoordinator] = None
        self.memory_agent: Optional[MemoryAgent] = None
        self.belief_system: Optional[BeliefSystem] = None
        self.model_registry = None
        self.is_running = False
        self.evolution_task: Optional[asyncio.Task] = None
        self.audit_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """Initialize all MindX components for autonomous evolution"""
        logger.info("🧠 Initializing MindX for Autonomous Evolution...")
        
        try:
            # Initialize core components
            self.memory_agent = MemoryAgent(config=self.config)
            self.belief_system = BeliefSystem()
            self.model_registry = await get_model_registry_async(config=self.config)
            
            # Initialize ID Manager
            id_manager = await IDManagerAgent.get_instance(
                config_override=self.config, 
                belief_system=self.belief_system
            )
            
            # Initialize AutoMINDX Agent
            automindx_instance = await AutoMINDXAgent.get_instance(
                memory_agent=self.memory_agent, 
                config_override=self.config
            )
            
            # Initialize Guardian Agent
            guardian_agent = await GuardianAgent.get_instance(
                id_manager=id_manager, 
                config_override=self.config
            )
            
            # Initialize Coordinator Agent
            self.coordinator = await get_coordinator_agent_mindx_async(
                config_override=self.config,
                memory_agent=self.memory_agent,
                belief_system=self.belief_system
            )
            
            if not self.coordinator:
                raise RuntimeError("Failed to initialize CoordinatorAgent")
            
            # Initialize Mastermind Agent
            self.mastermind = await MastermindAgent.get_instance(
                agent_id="autonomous_mastermind",
                config_override=self.config,
                coordinator_agent_instance=self.coordinator,
                memory_agent=self.memory_agent,
                model_registry=self.model_registry,
                test_mode=False
            )
            
            if not self.mastermind:
                raise RuntimeError("Failed to initialize MastermindAgent")
            
            # Initialize Autonomous Audit Coordinator
            self.audit_coordinator = AutonomousAuditCoordinator(
                coordinator_agent=self.coordinator,
                memory_agent=self.memory_agent,
                belief_system=self.belief_system,
                model_registry=self.model_registry,
                config=self.config
            )
            
            # Register core agents
            await self._register_core_agents()
            
            # Setup default audit campaigns
            await self._setup_audit_campaigns()
            
            logger.info("✅ MindX Autonomous Evolution System Initialized Successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize MindX: {e}", exc_info=True)
            return False
    
    async def _register_core_agents(self):
        """Register all core agents with the coordinator"""
        logger.info("📋 Registering Core Agents...")
        
        core_agents = {
            "mastermind": self.mastermind,
            "coordinator": self.coordinator,
            "memory": self.memory_agent,
            "strategic_evolution": self.mastermind.strategic_evolution_agent if self.mastermind else None,
            "blueprint": self.mastermind.strategic_evolution_agent.blueprint_agent if self.mastermind and self.mastermind.strategic_evolution_agent else None,
            "audit_coordinator": self.audit_coordinator
        }
        
        for name, instance in core_agents.items():
            if instance and hasattr(instance, 'agent_id'):
                if name != "coordinator":
                    self.coordinator.register_agent(
                        agent_id=instance.agent_id,
                        agent_type="core_service" if name != "mastermind" else "orchestrator",
                        description=f"Core {name.capitalize()} Agent",
                        instance=instance
                    )
                logger.info(f"  ✅ Registered {name}: {instance.agent_id}")
    
    async def _setup_audit_campaigns(self):
        """Setup default autonomous audit campaigns"""
        logger.info("🔍 Setting up Autonomous Audit Campaigns...")
        
        # Security and Performance Audit
        self.audit_coordinator.add_audit_campaign(
            campaign_id="security_performance_audit",
            audit_scope="security_vulnerabilities_and_performance_issues",
            target_components=["mastermind_agent", "coordinator_agent", "strategic_evolution_agent"],
            interval_hours=6,  # Every 6 hours
            priority=8
        )
        
        # Code Quality and Architecture Audit
        self.audit_coordinator.add_audit_campaign(
            campaign_id="code_quality_audit",
            audit_scope="code_quality_and_architecture_improvements",
            target_components=["orchestration", "learning", "evolution", "core"],
            interval_hours=12,  # Every 12 hours
            priority=6
        )
        
        # Learning and Evolution Audit
        self.audit_coordinator.add_audit_campaign(
            campaign_id="learning_evolution_audit",
            audit_scope="learning_capabilities_and_evolution_opportunities",
            target_components=["strategic_evolution_agent", "blueprint_agent", "bdi_agent"],
            interval_hours=24,  # Daily
            priority=7
        )
        
        logger.info("  ✅ Audit campaigns configured")
    
    async def start_autonomous_evolution(self, initial_directive: Optional[str] = None):
        """Start autonomous evolution with optional initial directive"""
        logger.info("🚀 Starting Autonomous Evolution...")
        
        self.is_running = True
        
        # Start autonomous audit loop
        self.audit_coordinator.start_autonomous_audit_loop(check_interval_seconds=300)  # 5 minutes
        logger.info("  ✅ Autonomous audit loop started")
        
        # Start evolution task
        self.evolution_task = asyncio.create_task(
            self._evolution_worker(initial_directive)
        )
        logger.info("  ✅ Evolution worker started")
        
        logger.info("🎉 Autonomous Evolution System is now running!")
        logger.info("   - Audit campaigns will run automatically")
        logger.info("   - Evolution cycles will execute based on audit findings")
        logger.info("   - System will continuously learn and improve")
    
    async def _evolution_worker(self, initial_directive: Optional[str] = None):
        """Main evolution worker loop"""
        logger.info("🔄 Evolution Worker Started")
        
        try:
            # Execute initial directive if provided
            if initial_directive:
                logger.info(f"🎯 Executing initial directive: '{initial_directive}'")
                result = await self.mastermind.command_augmentic_intelligence(initial_directive)
                logger.info(f"Initial evolution result: {result}")
            
            # Main evolution loop
            evolution_cycle = 0
            while self.is_running:
                try:
                    evolution_cycle += 1
                    logger.info(f"🔄 Evolution Cycle #{evolution_cycle}")
                    
                    # Check for high-priority backlog items
                    if self.coordinator.improvement_backlog:
                        high_priority_items = [
                            item for item in self.coordinator.improvement_backlog
                            if item.get("priority", 0) >= 7 and item.get("status") == "PENDING"
                        ]
                        
                        if high_priority_items:
                            # Process highest priority item
                            item = high_priority_items[0]
                            logger.info(f"🎯 Processing high-priority item: {item.get('description', 'Unknown')}")
                            
                            directive = f"Address improvement: {item.get('description', 'High priority improvement')}"
                            result = await self.mastermind.command_augmentic_intelligence(directive)
                            logger.info(f"Evolution result: {result}")
                            
                            # Mark item as processed
                            item["status"] = "IN_PROGRESS"
                    
                    # Wait before next cycle
                    await asyncio.sleep(3600)  # 1 hour between cycles
                    
                except Exception as e:
                    logger.error(f"Error in evolution cycle #{evolution_cycle}: {e}", exc_info=True)
                    await asyncio.sleep(300)  # 5 minute cooldown on error
                    
        except asyncio.CancelledError:
            logger.info("Evolution worker cancelled")
        except Exception as e:
            logger.error(f"Fatal error in evolution worker: {e}", exc_info=True)
    
    async def stop(self):
        """Stop autonomous evolution"""
        logger.info("🛑 Stopping Autonomous Evolution...")
        
        self.is_running = False
        
        # Stop audit coordinator
        if self.audit_coordinator:
            self.audit_coordinator.stop_autonomous_audit_loop()
            logger.info("  ✅ Audit coordinator stopped")
        
        # Cancel evolution task
        if self.evolution_task and not self.evolution_task.done():
            self.evolution_task.cancel()
            try:
                await self.evolution_task
            except asyncio.CancelledError:
                pass
            logger.info("  ✅ Evolution worker stopped")
        
        # Shutdown mastermind
        if self.mastermind:
            await self.mastermind.shutdown()
            logger.info("  ✅ Mastermind agent stopped")
        
        logger.info("✅ Autonomous Evolution System Stopped")

async def main():
    """Main entry point for autonomous evolution"""
    parser = argparse.ArgumentParser(description="Start MindX Autonomous Evolution")
    parser.add_argument("--directive", type=str, help="Initial evolution directive")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon (continuous)")
    parser.add_argument("--config", type=str, help="Path to config file")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    # Load config
    config = Config()
    if args.config:
        config.load_from_file(args.config)
    
    # Create evolution manager
    evolution_manager = AutonomousEvolutionManager(config)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(evolution_manager.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize system
        if not await evolution_manager.initialize():
            logger.error("Failed to initialize MindX")
            return 1
        
        # Start autonomous evolution
        await evolution_manager.start_autonomous_evolution(args.directive)
        
        if args.daemon:
            # Run continuously
            logger.info("Running in daemon mode...")
            while evolution_manager.is_running:
                await asyncio.sleep(1)
        else:
            # Run single evolution cycle
            logger.info("Running single evolution cycle...")
            await asyncio.sleep(60)  # Let it run for a minute
            await evolution_manager.stop()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        await evolution_manager.stop()
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        await evolution_manager.stop()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
