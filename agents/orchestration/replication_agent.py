# mindx/orchestration/replication_agent.py
"""
ReplicationAgent: Handles replication (local + GitHub backup + blockchain).

This agent coordinates replication across multiple systems:
- Local replication events (pgvectorscale sync)
- GitHub agent backup push events
- Replicate proven agents/tools to blockchain
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


class ReplicationAgent:
    """
    Agent specialized in handling replication across multiple systems.
    Coordinates local, GitHub, and blockchain replication.
    """
    
    def __init__(
        self,
        agent_id: str = "replication_agent",
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
        self.log_prefix = f"ReplicationAgent ({self.agent_id}):"
        
        # System state tracker
        self.state_tracker = SystemStateTracker(
            memory_agent=self.memory_agent,
            config=self.config,
            test_mode=test_mode
        )
        
        # Replication history
        self.replication_history: List[Dict[str, Any]] = []
        
        # Subscribe to coordinator events
        if self.coordinator_agent:
            self._subscribe_to_events()
    
    def _subscribe_to_events(self):
        """Subscribe to coordinator events for replication triggers."""
        if not self.coordinator_agent:
            return
        
        try:
            # Subscribe to agent/tool creation events
            self.coordinator_agent.subscribe("agent.created", self._on_agent_created)
            self.coordinator_agent.subscribe("agent.registered", self._on_agent_registered)
            self.coordinator_agent.subscribe("tool.created", self._on_tool_created)
            self.coordinator_agent.subscribe("identity.created", self._on_identity_created)
            logger.info(f"{self.log_prefix} Subscribed to coordinator events")
        except Exception as e:
            logger.error(f"{self.log_prefix} Error subscribing to events: {e}", exc_info=True)
    
    async def replicate_to_local(
        self,
        entity_type: str,
        entity_id: str,
        entity_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Replicate to local pgvectorscale database.
        
        Args:
            entity_type: Type of entity ("agent" or "tool")
            entity_id: ID of the entity
            entity_data: Data to replicate
        
        Returns:
            Dictionary with replication results
        """
        logger.info(f"{self.log_prefix} Replicating {entity_type} {entity_id} to local pgvectorscale")
        
        # TODO: Implement pgvectorscale integration
        # For now, save to local file as placeholder
        try:
            local_path = PROJECT_ROOT / "data" / "replication" / f"{entity_type}s" / f"{entity_id}.json"
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            with local_path.open("w", encoding="utf-8") as f:
                json.dump({
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "data": entity_data,
                    "replicated_at": time.time()
                }, f, indent=2)
            
            result = {
                "success": True,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "location": "local_file",
                "path": str(local_path)
            }
            
            self.replication_history.append({
                "timestamp": time.time(),
                "type": "local",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "result": result
            })
            
            return result
        except Exception as e:
            logger.error(f"{self.log_prefix} Error replicating to local: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def replicate_to_github(
        self,
        entity_type: str,
        entity_id: str,
        entity_data: Dict[str, Any],
        backup_type: str = "agent_creation"
    ) -> Dict[str, Any]:
        """
        Replicate to GitHub via GitHub agent backup.
        
        Args:
            entity_type: Type of entity ("agent" or "tool")
            entity_id: ID of the entity
            entity_data: Data to replicate
            backup_type: Type of backup
        
        Returns:
            Dictionary with replication results
        """
        logger.info(f"{self.log_prefix} Replicating {entity_type} {entity_id} to GitHub")
        
        if not self.github_agent:
            # Try to get GitHub agent from coordinator
            if self.coordinator_agent and hasattr(self.coordinator_agent, 'github_agent'):
                self.github_agent = self.coordinator_agent.github_agent
            
            if not self.github_agent:
                logger.warning(f"{self.log_prefix} GitHub agent not available, skipping GitHub replication")
                return {
                    "success": False,
                    "error": "GitHub agent not available"
                }
        
        try:
            # Create backup via GitHub agent
            success, result = await self.github_agent.execute(
                action="create_backup",
                backup_type=backup_type,
                reason=f"Replication: {entity_type} {entity_id} created"
            )
            
            if success:
                replication_result = {
                    "success": True,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "backup_type": backup_type,
                    "github_result": result
                }
                
                self.replication_history.append({
                    "timestamp": time.time(),
                    "type": "github",
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "result": replication_result
                })
                
                return replication_result
            else:
                return {
                    "success": False,
                    "error": result if isinstance(result, str) else "GitHub backup failed"
                }
        except Exception as e:
            logger.error(f"{self.log_prefix} Error replicating to GitHub: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def replicate_to_blockchain(
        self,
        entity_type: str,
        entity_id: str,
        entity_data: Dict[str, Any],
        proven: bool = False
    ) -> Dict[str, Any]:
        """
        Replicate proven agents/tools to blockchain as immutable.
        
        Args:
            entity_type: Type of entity ("agent" or "tool")
            entity_id: ID of the entity
            entity_data: Data to replicate
            proven: Whether the entity is proven effective
        
        Returns:
            Dictionary with replication results
        """
        if not proven:
            logger.info(f"{self.log_prefix} Entity {entity_id} not yet proven, skipping blockchain replication")
            return {
                "success": False,
                "reason": "Entity not yet proven"
            }
        
        logger.info(f"{self.log_prefix} Replicating proven {entity_type} {entity_id} to blockchain")
        
        # TODO: Implement blockchain integration
        # This would archive to blockchain as immutable
        
        try:
            # Placeholder for blockchain archival
            result = {
                "success": True,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "blockchain_tx": "placeholder_tx_hash",
                "immutable": True
            }
            
            self.replication_history.append({
                "timestamp": time.time(),
                "type": "blockchain",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "result": result
            })
            
            if self.memory_agent:
                await self.memory_agent.log_process(
                    "blockchain_replication",
                    {
                        "timestamp": time.time(),
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "result": result
                    },
                    {"agent_id": self.agent_id}
                )
            
            return result
        except Exception as e:
            logger.error(f"{self.log_prefix} Error replicating to blockchain: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def replicate_entity(
        self,
        entity_type: str,
        entity_id: str,
        entity_data: Dict[str, Any],
        proven: bool = False,
        replicate_local: bool = True,
        replicate_github: bool = True,
        replicate_blockchain: bool = False
    ) -> Dict[str, Any]:
        """
        Replicate an entity across all configured systems with comprehensive logging.
        
        Args:
            entity_type: Type of entity ("agent" or "tool")
            entity_id: ID of the entity
            entity_data: Data to replicate
            proven: Whether the entity is proven effective
            replicate_local: Whether to replicate to local
            replicate_github: Whether to replicate to GitHub
            replicate_blockchain: Whether to replicate to blockchain
        
        Returns:
            Dictionary with replication results
        """
        start_time = time.time()
        
        # Capture system state before replication
        before_state = await self.state_tracker.capture_system_state(
            SystemEventType.REPLICATION,
            coordinator_agent=self.coordinator_agent,
            metadata={
                "phase": "before_replication",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "proven": proven
            }
        )
        
        # Log replication initiation
        await self.memory_agent.log_process(
            "replication_initiation",
            {
                "timestamp": time.time(),
                "entity_type": entity_type,
                "entity_id": entity_id,
                "proven": proven,
                "replicate_local": replicate_local,
                "replicate_github": replicate_github,
                "replicate_blockchain": replicate_blockchain
            },
            {"agent_id": self.agent_id, "event": "replication_initiation"}
        )
        
        results = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "replications": {},
            "duration_seconds": 0
        }
        
        try:
            # Local replication
            if replicate_local:
                local_result = await self.replicate_to_local(entity_type, entity_id, entity_data)
                results["replications"]["local"] = local_result
            
            # GitHub replication
            if replicate_github:
                github_result = await self.replicate_to_github(entity_type, entity_id, entity_data)
                results["replications"]["github"] = github_result
            
            # Blockchain replication (only if proven)
            if replicate_blockchain and proven:
                blockchain_result = await self.replicate_to_blockchain(entity_type, entity_id, entity_data, proven)
                results["replications"]["blockchain"] = blockchain_result
            
            results["all_successful"] = all(
                r.get("success", False) for r in results["replications"].values()
            )
            results["duration_seconds"] = time.time() - start_time
            
            # Capture system state after replication
            after_state = await self.state_tracker.capture_system_state(
                SystemEventType.REPLICATION,
                coordinator_agent=self.coordinator_agent,
                metadata={
                    "phase": "after_replication",
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "duration_seconds": results["duration_seconds"],
                    "all_successful": results["all_successful"]
                }
            )
            
            # Comprehensive replication record
            replication_record = {
                "timestamp": time.time(),
                "duration": results["duration_seconds"],
                "entity_type": entity_type,
                "entity_id": entity_id,
                "proven": proven,
                "replications": results["replications"],
                "all_successful": results["all_successful"],
                "before_state": {
                    "resource_snapshot": asdict(before_state.resource_snapshot) if before_state.resource_snapshot else None,
                    "performance_snapshot": asdict(before_state.performance_snapshot) if before_state.performance_snapshot else None
                },
                "after_state": {
                    "resource_snapshot": asdict(after_state.resource_snapshot) if after_state.resource_snapshot else None,
                    "performance_snapshot": asdict(after_state.performance_snapshot) if after_state.performance_snapshot else None
                }
            }
            
            # Log comprehensive replication data to memory agent
            await self.memory_agent.log_process(
                "replication_complete",
                replication_record,
                {"agent_id": self.agent_id, "event": "replication_complete"}
            )
            
            # Have mindXagent review replication data for self-improvement
            if self.mindxagent:
                try:
                    await self._review_replication_with_mindxagent(replication_record, before_state, after_state)
                except Exception as e:
                    logger.warning(f"{self.log_prefix} Error in mindXagent review: {e}", exc_info=True)
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error during replication: {e}", exc_info=True)
            results["error"] = str(e)
            results["all_successful"] = False
        
        return results
    
    async def _on_agent_created(self, data: Dict[str, Any]):
        """Handle agent creation event - trigger replication."""
        agent_id = data.get("agent_id")
        agent_type = data.get("agent_type")
        
        if agent_id:
            logger.info(f"{self.log_prefix} Agent created: {agent_id}, triggering replication")
            await self.replicate_entity(
                entity_type="agent",
                entity_id=agent_id,
                entity_data=data,
                proven=False,  # New agents are not yet proven
                replicate_local=True,
                replicate_github=True,
                replicate_blockchain=False
            )
    
    async def _on_agent_registered(self, data: Dict[str, Any]):
        """Handle agent registration event."""
        agent_id = data.get("agent_id")
        if agent_id:
            logger.debug(f"{self.log_prefix} Agent registered: {agent_id}")
    
    async def _on_tool_created(self, data: Dict[str, Any]):
        """Handle tool creation event - trigger replication."""
        tool_id = data.get("tool_id")
        if tool_id:
            logger.info(f"{self.log_prefix} Tool created: {tool_id}, triggering replication")
            await self.replicate_entity(
                entity_type="tool",
                entity_id=tool_id,
                entity_data=data,
                proven=False,
                replicate_local=True,
                replicate_github=True,
                replicate_blockchain=False
            )
    
    async def _on_identity_created(self, data: Dict[str, Any]):
        """Handle identity creation event."""
        agent_id = data.get("agent_id")
        if agent_id:
            logger.debug(f"{self.log_prefix} Identity created for: {agent_id}")
    
    async def mark_entity_as_proven(
        self,
        entity_type: str,
        entity_id: str,
        effectiveness_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Mark an entity as proven effective and trigger blockchain replication.
        
        Args:
            entity_type: Type of entity ("agent" or "tool")
            entity_id: ID of the entity
            effectiveness_metrics: Metrics showing effectiveness
        
        Returns:
            Dictionary with marking results
        """
        logger.info(f"{self.log_prefix} Marking {entity_type} {entity_id} as proven")
        
        # Get entity data
        entity_data = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "proven": True,
            "proven_at": time.time(),
            "effectiveness_metrics": effectiveness_metrics or {}
        }
        
        # Replicate to blockchain as immutable
        result = await self.replicate_to_blockchain(
            entity_type=entity_type,
            entity_id=entity_id,
            entity_data=entity_data,
            proven=True
        )
        
        return result
    
    async def _review_replication_with_mindxagent(
        self,
        replication_record: Dict[str, Any],
        before_state: Any,
        after_state: Any
    ):
        """
        Have mindXagent review replication data for self-awareness and self-improvement.
        
        Args:
            replication_record: Complete replication record
            before_state: System state before replication
            after_state: System state after replication
        """
        if not self.mindxagent:
            return
        
        logger.info(f"{self.log_prefix} Requesting mindXagent review of replication data")
        
        try:
            # Prepare review data
            review_data = {
                "replication_record": replication_record,
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
                "mindxagent_replication_review",
                review_data,
                {"agent_id": self.agent_id, "reviewer": "mindxagent"}
            )
            
            # Call mindXagent review method if available
            if hasattr(self.mindxagent, 'review_system_state'):
                await self.mindxagent.review_system_state(
                    event_type="replication",
                    data=review_data
                )
            
            logger.info(f"{self.log_prefix} mindXagent review completed")
        except Exception as e:
            logger.error(f"{self.log_prefix} Error in mindXagent review: {e}", exc_info=True)
    
    async def shutdown(self):
        """Shutdown the replication agent."""
        logger.info(f"{self.log_prefix} Shutting down")
