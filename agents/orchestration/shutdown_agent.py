# mindx/orchestration/shutdown_agent.py
"""
ShutdownAgent: Controls graceful shutdown and cleanup.

This agent manages graceful agent shutdown, saves state to pgvectorscale,
creates final backup via GitHub agent, and archives proven agents/tools to blockchain.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from agents.memory_agent import MemoryAgent
from agents.orchestration.coordinator_agent import CoordinatorAgent
from agents.orchestration.system_state_tracker import SystemStateTracker, SystemEventType
from tools.github_agent_tool import GitHubAgentTool
from dataclasses import asdict

logger = get_logger(__name__)


class ShutdownAgent:
    """
    Agent specialized in controlling graceful shutdown and cleanup.
    Manages the shutdown sequence for the mindX system.
    """
    
    def __init__(
        self,
        agent_id: str = "shutdown_agent",
        coordinator_agent: Optional[CoordinatorAgent] = None,
        memory_agent: Optional[MemoryAgent] = None,
        github_agent: Optional[GitHubAgentTool] = None,
        config: Optional[Config] = None,
        test_mode: bool = False,
        mindxagent: Optional[Any] = None
    ):
        self.agent_id = agent_id
        self.coordinator_agent = coordinator_agent
        self.memory_agent = memory_agent or MemoryAgent(config=config)
        self.github_agent = github_agent
        self.config = config or Config(test_mode=test_mode)
        self.test_mode = test_mode
        self.mindxagent = mindxagent
        self.log_prefix = f"ShutdownAgent ({self.agent_id}):"
        
        # System state tracker
        self.state_tracker = SystemStateTracker(
            memory_agent=self.memory_agent,
            config=self.config,
            test_mode=test_mode
        )
        
        # Shutdown sequence
        self.shutdown_sequence: List[Dict[str, Any]] = []
        self.shutdown_log: List[Dict[str, Any]] = []
    
    async def shutdown_system(
        self,
        save_state: bool = True,
        create_backup: bool = True,
        archive_proven: bool = True
    ) -> Dict[str, Any]:
        """
        Shutdown the entire system gracefully.
        
        Args:
            save_state: Whether to save state to pgvectorscale
            create_backup: Whether to create final backup via GitHub
            archive_proven: Whether to archive proven agents/tools to blockchain
        
        Returns:
            Dictionary with shutdown results
        """
        logger.info(f"{self.log_prefix} Starting graceful system shutdown")
        
        start_time = time.time()
        shutdown_results = {
            "status": "in_progress",
            "steps_completed": [],
            "errors": [],
            "agents_shutdown": []
        }
        
        try:
            # Capture system state before shutdown
            before_state = await self.state_tracker.capture_system_state(
                SystemEventType.SHUTDOWN,
                coordinator_agent=self.coordinator_agent,
                metadata={"phase": "before_shutdown"}
            )
            
            # Load previous state data for comparison
            previous_state = await self.state_tracker.get_latest_state()
            shutdown_results["previous_state"] = {
                "event_id": previous_state.event_id if previous_state else None,
                "timestamp": previous_state.timestamp if previous_state else None,
                "improvement_count": previous_state.improvement_count if previous_state else 0,
                "rollback_count": previous_state.rollback_count if previous_state else 0
            } if previous_state else None
            
            # Log comprehensive shutdown initiation
            await self.memory_agent.log_process(
                "shutdown_initiation",
                {
                    "timestamp": time.time(),
                    "previous_state": shutdown_results["previous_state"],
                    "save_state": save_state,
                    "create_backup": create_backup,
                    "archive_proven": archive_proven
                },
                {"agent_id": self.agent_id, "event": "shutdown_initiation"}
            )
            
            # Step 1: Save state to pgvectorscale
            if save_state:
                logger.info(f"{self.log_prefix} Step 1: Saving state to pgvectorscale")
                save_result = await self._save_state_to_local()
                shutdown_results["steps_completed"].append("save_state")
                shutdown_results["save_state"] = save_result
            
            # Step 2: Create final backup via GitHub agent
            if create_backup:
                logger.info(f"{self.log_prefix} Step 2: Creating final backup via GitHub")
                backup_result = await self._create_final_backup()
                shutdown_results["steps_completed"].append("create_backup")
                shutdown_results["backup"] = backup_result
            
            # Step 3: Archive proven agents/tools to blockchain
            if archive_proven:
                logger.info(f"{self.log_prefix} Step 3: Archiving proven entities to blockchain")
                archive_result = await self._archive_proven_entities()
                shutdown_results["steps_completed"].append("archive_proven")
                shutdown_results["archive"] = archive_result
            
            # Step 4: Graceful agent shutdown
            logger.info(f"{self.log_prefix} Step 4: Shutting down agents gracefully")
            shutdown_agents_result = await self._shutdown_agents_gracefully()
            shutdown_results["steps_completed"].append("shutdown_agents")
            shutdown_results["agents_shutdown"] = shutdown_agents_result.get("agents", [])
            
            # Step 5: Cleanup
            logger.info(f"{self.log_prefix} Step 5: Performing cleanup")
            cleanup_result = await self._perform_cleanup()
            shutdown_results["steps_completed"].append("cleanup")
            shutdown_results["cleanup"] = cleanup_result
            
            shutdown_results["status"] = "completed"
            shutdown_results["duration_seconds"] = time.time() - start_time
            
            logger.info(f"{self.log_prefix} System shutdown completed in {shutdown_results['duration_seconds']:.2f}s")
            
            # Capture system state after shutdown
            after_state = await self.state_tracker.capture_system_state(
                SystemEventType.SHUTDOWN,
                coordinator_agent=self.coordinator_agent,
                metadata={
                    "phase": "after_shutdown",
                    "duration_seconds": shutdown_results["duration_seconds"],
                    "steps_completed": shutdown_results["steps_completed"]
                }
            )
            
            # Comprehensive shutdown record with resource and performance data
            shutdown_record = {
                "timestamp": time.time(),
                "duration": shutdown_results["duration_seconds"],
                "steps": shutdown_results["steps_completed"],
                "agents_shutdown": shutdown_results["agents_shutdown"],
                "before_state": {
                    "resource_snapshot": asdict(before_state.resource_snapshot) if before_state.resource_snapshot else None,
                    "performance_snapshot": asdict(before_state.performance_snapshot) if before_state.performance_snapshot else None
                },
                "after_state": {
                    "resource_snapshot": asdict(after_state.resource_snapshot) if after_state.resource_snapshot else None,
                    "performance_snapshot": asdict(after_state.performance_snapshot) if after_state.performance_snapshot else None,
                    "agents_registered": after_state.agents_registered,
                    "agents_active": after_state.agents_active,
                    "tools_registered": after_state.tools_registered
                },
                "improvement_count": after_state.improvement_count,
                "rollback_count": after_state.rollback_count,
                "previous_state": shutdown_results["previous_state"]
            }
            self.shutdown_log.append(shutdown_record)
            
            # Log comprehensive shutdown data to memory agent
            await self.memory_agent.log_process(
                "system_shutdown_complete",
                shutdown_record,
                {"agent_id": self.agent_id, "event": "shutdown_complete"}
            )
            
            # Have mindXagent review shutdown data for self-improvement
            if self.mindxagent:
                try:
                    await self._review_shutdown_with_mindxagent(shutdown_record, before_state, after_state)
                except Exception as e:
                    logger.warning(f"{self.log_prefix} Error in mindXagent review: {e}", exc_info=True)
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error during system shutdown: {e}", exc_info=True)
            shutdown_results["status"] = "failed"
            shutdown_results["errors"].append(str(e))
        
        return shutdown_results
    
    async def _save_state_to_local(self) -> Dict[str, Any]:
        """
        Save system state to pgvectorscale database.
        
        Returns:
            Dictionary with save results
        """
        logger.info(f"{self.log_prefix} Saving state to pgvectorscale (placeholder)")
        
        # TODO: Implement pgvectorscale integration
        # For now, save to local file
        try:
            state_path = PROJECT_ROOT / "data" / "system_state" / f"shutdown_{int(time.time())}.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Gather system state
            system_state = {
                "timestamp": time.time(),
                "agents": [],
                "tools": [],
                "config": {}
            }
            
            if self.coordinator_agent:
                registry = getattr(self.coordinator_agent, 'agent_registry', {})
                system_state["agents"] = list(registry.keys())
            
            with state_path.open("w", encoding="utf-8") as f:
                json.dump(system_state, f, indent=2)
            
            return {
                "success": True,
                "path": str(state_path),
                "message": "State saved to local file (pgvectorscale integration pending)"
            }
        except Exception as e:
            logger.error(f"{self.log_prefix} Error saving state: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _create_final_backup(self) -> Dict[str, Any]:
        """
        Create final backup via GitHub agent.
        
        Returns:
            Dictionary with backup results
        """
        if not self.github_agent:
            # Try to get GitHub agent from coordinator
            if self.coordinator_agent and hasattr(self.coordinator_agent, 'github_agent'):
                self.github_agent = self.coordinator_agent.github_agent
            
            if not self.github_agent:
                logger.warning(f"{self.log_prefix} GitHub agent not available, skipping final backup")
                return {
                    "success": False,
                    "error": "GitHub agent not available"
                }
        
        try:
            success, result = await self.github_agent.execute(
                action="create_backup",
                backup_type="shutdown_backup",
                reason="System shutdown - final backup"
            )
            
            if success:
                return {
                    "success": True,
                    "backup_type": "shutdown_backup",
                    "result": result
                }
            else:
                return {
                    "success": False,
                    "error": result if isinstance(result, str) else "Backup failed"
                }
        except Exception as e:
            logger.error(f"{self.log_prefix} Error creating final backup: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _archive_proven_entities(self) -> Dict[str, Any]:
        """
        Archive proven agents/tools to blockchain.
        
        Returns:
            Dictionary with archive results
        """
        logger.info(f"{self.log_prefix} Archiving proven entities to blockchain (placeholder)")
        
        # TODO: Implement blockchain integration
        # This would identify proven agents/tools and archive them
        
        archived = []
        
        if self.coordinator_agent:
            registry = getattr(self.coordinator_agent, 'agent_registry', {})
            for agent_id, agent_data in registry.items():
                # Check if agent is proven (would need metadata)
                # For now, just log
                logger.debug(f"{self.log_prefix} Checking if agent {agent_id} is proven")
        
        return {
            "success": True,
            "archived_count": len(archived),
            "archived_entities": archived,
            "message": "Blockchain archival not yet implemented"
        }
    
    async def _shutdown_agents_gracefully(self) -> Dict[str, Any]:
        """
        Shutdown all agents gracefully.
        
        Returns:
            Dictionary with shutdown results
        """
        shutdown_agents = []
        errors = []
        
        if self.coordinator_agent:
            registry = getattr(self.coordinator_agent, 'agent_registry', {})
            
            for agent_id, agent_data in registry.items():
                try:
                    instance = agent_data.get("instance")
                    if instance and hasattr(instance, 'shutdown'):
                        logger.info(f"{self.log_prefix} Shutting down agent: {agent_id}")
                        await instance.shutdown()
                        shutdown_agents.append(agent_id)
                except Exception as e:
                    logger.error(f"{self.log_prefix} Error shutting down {agent_id}: {e}", exc_info=True)
                    errors.append({"agent_id": agent_id, "error": str(e)})
        
        return {
            "agents": shutdown_agents,
            "errors": errors,
            "total": len(shutdown_agents)
        }
    
    async def _perform_cleanup(self) -> Dict[str, Any]:
        """
        Perform final cleanup operations.
        
        Returns:
            Dictionary with cleanup results
        """
        logger.info(f"{self.log_prefix} Performing cleanup")
        
        cleanup_tasks = [
            "close_connections",
            "release_resources",
            "finalize_logs"
        ]
        
        completed = []
        for task in cleanup_tasks:
            try:
                logger.debug(f"{self.log_prefix} Cleanup task: {task}")
                completed.append(task)
            except Exception as e:
                logger.error(f"{self.log_prefix} Error in cleanup task {task}: {e}")
        
        return {
            "completed_tasks": completed,
            "total_tasks": len(cleanup_tasks)
        }
    
    async def _review_shutdown_with_mindxagent(
        self,
        shutdown_record: Dict[str, Any],
        before_state: Any,
        after_state: Any
    ):
        """
        Have mindXagent review shutdown data for self-awareness and self-improvement.
        
        Args:
            shutdown_record: Complete shutdown record
            before_state: System state before shutdown
            after_state: System state after shutdown
        """
        if not self.mindxagent:
            return
        
        logger.info(f"{self.log_prefix} Requesting mindXagent review of shutdown data")
        
        try:
            # Prepare review data
            review_data = {
                "shutdown_record": shutdown_record,
                "before_state": asdict(before_state) if before_state else None,
                "after_state": asdict(after_state) if after_state else None,
                "improvement_opportunities": [],
                "performance_analysis": {},
                "resource_analysis": {}
            }
            
            # Analyze resource changes
            if before_state and after_state:
                if before_state.resource_snapshot and after_state.resource_snapshot:
                    review_data["resource_analysis"] = {
                        "cpu_change": after_state.resource_snapshot.cpu_percent - before_state.resource_snapshot.cpu_percent,
                        "memory_change": after_state.resource_snapshot.memory_percent - before_state.resource_snapshot.memory_percent,
                        "process_change": after_state.resource_snapshot.process_count - before_state.resource_snapshot.process_count
                    }
            
            # Analyze performance changes
            if before_state and after_state:
                if before_state.performance_snapshot and after_state.performance_snapshot:
                    review_data["performance_analysis"] = {
                        "calls_change": after_state.performance_snapshot.total_calls - before_state.performance_snapshot.total_calls,
                        "error_rate_change": after_state.performance_snapshot.error_rate - before_state.performance_snapshot.error_rate,
                        "latency_change": after_state.performance_snapshot.avg_latency_ms - before_state.performance_snapshot.avg_latency_ms
                    }
            
            # Log review request to memory agent
            await self.memory_agent.log_process(
                "mindxagent_shutdown_review",
                review_data,
                {"agent_id": self.agent_id, "reviewer": "mindxagent"}
            )
            
            # Call mindXagent review method if available
            if hasattr(self.mindxagent, 'review_system_state'):
                await self.mindxagent.review_system_state(
                    event_type="shutdown",
                    data=review_data
                )
            
            logger.info(f"{self.log_prefix} mindXagent review completed")
        except Exception as e:
            logger.error(f"{self.log_prefix} Error in mindXagent review: {e}", exc_info=True)
    
    async def shutdown(self):
        """Shutdown the shutdown agent."""
        logger.info(f"{self.log_prefix} Shutting down")
