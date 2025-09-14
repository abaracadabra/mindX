#!/usr/bin/env python3
"""
Augmentic Simple - Autonomous Agentic Development for MindX
==========================================================

A simplified version of the augmentic system that handles dependency issues gracefully
and provides core augmentic development functionality without complex monitoring.

Usage:
    python3 augmentic_simple.py "Improve the system's error handling and resilience"
    python3 augmentic_simple.py "Enhance the learning capabilities of the strategic evolution agent"
    python3 augmentic_simple.py  # Uses default augmentic directive
"""

import asyncio
import sys
import os
import argparse
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import core components with error handling
try:
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
    CORE_IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Core imports not available: {e}")
    CORE_IMPORTS_AVAILABLE = False
    # Define fallback classes
    class Config:
        def __init__(self):
            pass
        def set(self, key, value):
            pass
        def load_from_file(self, path):
            pass
    
    def get_logger(name):
        import logging
        return logging.getLogger(name)
    
    def setup_logging():
        import logging
        logging.basicConfig(level=logging.INFO)

logger = None

class AugmenticSimple:
    """Simplified Augmentic Development System with graceful error handling"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config() if CORE_IMPORTS_AVAILABLE else None
        self.mastermind: Optional[MastermindAgent] = None
        self.coordinator = None
        self.audit_coordinator: Optional[AutonomousAuditCoordinator] = None
        self.memory_agent: Optional[MemoryAgent] = None
        self.belief_system: Optional[BeliefSystem] = None
        self.model_registry = None
        self.is_running = False
        
    async def initialize(self):
        """Initialize MindX components with graceful error handling"""
        global logger
        logger = get_logger(__name__)
        
        if not CORE_IMPORTS_AVAILABLE:
            print("❌ Core MindX components not available. Please check dependencies.")
            return False
            
        logger.info("🧠 Initializing MindX Augmentic Development System (Simple Mode)...")
        
        try:
            # Initialize core components
            print("🔧 Initializing core components...")
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
            print("🌐 Initializing Coordinator Agent...")
            self.coordinator = await get_coordinator_agent_mindx_async(
                config_override=self.config,
                memory_agent=self.memory_agent,
                belief_system=self.belief_system
            )
            
            if not self.coordinator:
                raise RuntimeError("Failed to initialize CoordinatorAgent")
            
            # Configure tools registry for augmentic development
            print("🔧 Configuring augmentic tools registry...")
            self.config.set("mastermind_agent.augmentic_mastermind.tools_registry_path", "data/config/augmentic_tools_registry.json")
            
            # Initialize Mastermind Agent with full tool integration
            print("🧠 Initializing Mastermind Agent with full tool integration...")
            self.mastermind = await MastermindAgent.get_instance(
                agent_id="augmentic_mastermind",
                config_override=self.config,
                coordinator_agent_instance=self.coordinator,
                memory_agent=self.memory_agent,
                model_registry=self.model_registry,
                test_mode=False
            )
            
            if not self.mastermind:
                raise RuntimeError("Failed to initialize MastermindAgent")
            
            # Initialize Autonomous Audit Coordinator (simplified)
            print("🔍 Initializing Autonomous Audit Coordinator...")
            self.audit_coordinator = AutonomousAuditCoordinator(
                coordinator_agent=self.coordinator,
                memory_agent=self.memory_agent,
                belief_system=self.belief_system,
                model_registry=self.model_registry,
                config=self.config
            )
            
            # Register core agents
            print("📋 Registering core agents...")
            core_agents = {
                "mastermind": self.mastermind,
                "coordinator": self.coordinator,
                "memory": self.memory_agent,
                "strategic_evolution": self.mastermind.strategic_evolution_agent,
                "blueprint": self.mastermind.strategic_evolution_agent.blueprint_agent if self.mastermind.strategic_evolution_agent else None,
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
                    print(f"  ✅ Registered {name}: {instance.agent_id}")
            
            # Setup audit campaigns for augmentic development
            print("🔍 Setting up augmentic audit campaigns...")
            self.audit_coordinator.add_audit_campaign(
                campaign_id="augmentic_development_audit",
                audit_scope="augmentic_development_capabilities_and_tool_effectiveness",
                target_components=["mastermind_agent", "bdi_agent", "tools", "agents"],
                interval_hours=1,  # Every hour for active augmentic development
                priority=9
            )
            
            # Setup tool-specific audit campaigns
            self.audit_coordinator.add_audit_campaign(
                campaign_id="tool_effectiveness_audit",
                audit_scope="tool_effectiveness_and_creation_opportunities",
                target_components=["audit_and_improve_tool", "augmentic_intelligence_tool", "system_analyzer_tool"],
                interval_hours=2,  # Every 2 hours
                priority=8
            )
            
            logger.info("✅ MindX Augmentic Development System Initialized Successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize MindX: {e}", exc_info=True)
            print(f"❌ Initialization failed: {e}")
            return False
    
    async def execute_augmentic_directive(self, directive: str):
        """Execute augmentic development directive"""
        print(f"🎯 Executing augmentic directive: '{directive}'")
        print("=" * 60)
        
        # Start audit loop
        print("🔍 Starting autonomous audit loop...")
        self.audit_coordinator.start_autonomous_audit_loop(check_interval_seconds=60)
        
        # Execute through mastermind
        result = await self.mastermind.command_augmentic_intelligence(directive)
        
        print("=" * 60)
        print("🎉 AUGMENTIC DEVELOPMENT RESULT:")
        print("=" * 60)
        print(f"Status: {result.get('overall_campaign_status', 'Unknown')}")
        print(f"Message: {result.get('final_bdi_message', 'No message')}")
        print("=" * 60)
        
        return result
    
    async def show_system_status(self):
        """Show comprehensive system status"""
        print("\n📊 COMPREHENSIVE SYSTEM STATUS:")
        print("=" * 60)
        
        # Core system status
        print("🧠 Core System:")
        print(f"  - Mastermind Agent: {'✅ Active' if self.mastermind else '❌ Inactive'}")
        print(f"  - BDI Agent: {'✅ Active' if self.mastermind and self.mastermind.bdi_agent else '❌ Inactive'}")
        print(f"  - Strategic Evolution Agent: {'✅ Active' if self.mastermind and self.mastermind.strategic_evolution_agent else '❌ Inactive'}")
        print(f"  - Blueprint Agent: {'✅ Active' if self.mastermind and self.mastermind.strategic_evolution_agent and self.mastermind.strategic_evolution_agent.blueprint_agent else '❌ Inactive'}")
        print(f"  - LLM Handler: {'✅ Active' if self.mastermind and self.mastermind.llm_handler else '❌ Inactive'}")
        print(f"  - Audit Coordinator: {'✅ Active' if self.audit_coordinator else '❌ Inactive'}")
        
        # Available tools for augmentic development
        if self.mastermind and self.mastermind.bdi_agent and hasattr(self.mastermind.bdi_agent, 'available_tools'):
            print(f"\n🔧 AVAILABLE TOOLS FOR AUGMENTIC DEVELOPMENT:")
            for tool_name, tool_instance in self.mastermind.bdi_agent.available_tools.items():
                print(f"  - {tool_name}: {'✅ Active' if tool_instance else '❌ Inactive'}")
        
        # Campaign history
        if self.mastermind and self.mastermind.strategic_campaigns_history:
            print(f"\n📈 AUGMENTIC CAMPAIGN HISTORY ({len(self.mastermind.strategic_campaigns_history)} campaigns):")
            for i, campaign in enumerate(self.mastermind.strategic_campaigns_history[-3:], 1):
                print(f"  {i}. {campaign.get('run_id', 'Unknown')}: {campaign.get('overall_campaign_status', 'Unknown')}")
    
    async def interactive_cli(self):
        """Start interactive CLI mode"""
        print("\n🖥️  Starting Interactive CLI Mode...")
        print("Type 'help' for available commands, 'quit' to exit")
        
        while True:
            try:
                user_input = await asyncio.to_thread(input, "augmentic > ")
                await self.memory_agent.log_terminal_output(f"USER_INPUT: {user_input}")
                
                if not user_input.strip():
                    continue
                
                if user_input.lower() in ["quit", "exit"]:
                    print("Exiting interactive mode...")
                    break
                
                if user_input.lower() == "help":
                    self.print_help()
                    continue
                
                if user_input.lower() == "status":
                    await self.show_system_status()
                    continue
                
                # Execute as augmentic directive
                if user_input.startswith("augmentic "):
                    directive = user_input[10:].strip()
                else:
                    directive = user_input
                
                result = await self.execute_augmentic_directive(directive)
                await self.memory_agent.log_terminal_output(f"SYSTEM_OUTPUT: {json.dumps(result, default=str)}")
                
            except (EOFError, KeyboardInterrupt):
                print("\nExiting interactive mode...")
                break
            except Exception as e:
                print(f"Error: {e}")
                if logger:
                    logger.error(f"Interactive CLI error: {e}", exc_info=True)
    
    def print_help(self):
        """Print help information"""
        print("\n🧠 Augmentic Development System Commands:")
        print("=" * 50)
        print("  augmentic <directive>  - Execute augmentic development directive")
        print("  status                 - Show comprehensive system status")
        print("  help                   - Show this help message")
        print("  quit/exit              - Exit interactive mode")
        print("\nExamples:")
        print("  augmentic Improve error handling across all agents")
        print("  augmentic Enhance learning capabilities")
        print("  augmentic Analyze system and create new tools")
        print("=" * 50)
    
    async def shutdown(self):
        """Shutdown the augmentic system"""
        print("🛑 Shutting down Augmentic Development System...")
        
        # Stop audit loop
        if self.audit_coordinator:
            self.audit_coordinator.stop_autonomous_audit_loop()
        
        # Shutdown mastermind
        if self.mastermind:
            await self.mastermind.shutdown()
        
        print("✅ Augmentic Development System shutdown complete")

async def main():
    """Main entry point for augmentic development"""
    parser = argparse.ArgumentParser(description="MindX Augmentic Development System (Simple)")
    parser.add_argument("directive", nargs="?", help="Augmentic development directive")
    parser.add_argument("--interactive", "-i", action="store_true", help="Start interactive CLI mode")
    parser.add_argument("--config", help="Path to config file")
    
    args = parser.parse_args()
    
    # Setup logging
    if CORE_IMPORTS_AVAILABLE:
        setup_logging()
        logger = get_logger(__name__)
    else:
        print("⚠️  Running in limited mode due to missing dependencies")
    
    # Load config
    config = Config() if CORE_IMPORTS_AVAILABLE else None
    if args.config and config:
        config.load_from_file(args.config)
    
    # Create augmentic system
    augmentic_system = AugmenticSimple(config)
    
    try:
        # Initialize system
        if not await augmentic_system.initialize():
            print("❌ Failed to initialize MindX Augmentic System")
            return 1
        
        # Handle different modes
        if args.interactive:
            await augmentic_system.interactive_cli()
        else:
            # Execute augmentic directive
            directive = args.directive or "Enhance the system's autonomous agentic development capabilities"
            
            print("🧠 MindX Augmentic - Autonomous Agentic Development")
            print("=" * 60)
            print(f"Augmentic Directive: {directive}")
            print("=" * 60)
            
            result = await augmentic_system.execute_augmentic_directive(directive)
            
            # Show system status
            await augmentic_system.show_system_status()
            
            print("\n🎉 MindX Augmentic Development Complete!")
            print("The system is now running with autonomous agentic development capabilities.")
            
            # Run for a bit then stop
            print("\n🔄 Running autonomous systems for 30 seconds...")
            await asyncio.sleep(30)
            await augmentic_system.shutdown()
        
        return 0
        
    except KeyboardInterrupt:
        if logger:
            logger.info("Received keyboard interrupt")
        await augmentic_system.shutdown()
        return 0
    except Exception as e:
        if logger:
            logger.error(f"Fatal error: {e}", exc_info=True)
        else:
            print(f"Fatal error: {e}")
        await augmentic_system.shutdown()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
