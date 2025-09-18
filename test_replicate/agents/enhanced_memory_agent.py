# mindx/agents/enhanced_memory_agent.py
"""
Enhanced MemoryAgent with timestamped memory, context management, and self-awareness.
"""
from __future__ import annotations
import asyncio
import aiofiles
import re
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict

try:
    import ujson as json_lib
    UJSON_AVAILABLE = True
except ImportError:
    import json as json_lib
    UJSON_AVAILABLE = False

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger, setup_logging

logger = get_logger(__name__)

class MemoryType(Enum):
    INTERACTION = "interaction"
    CONTEXT = "context"
    LEARNING = "learning"
    SYSTEM_STATE = "system_state"
    PERFORMANCE = "performance"
    ERROR = "error"
    GOAL = "goal"
    BELIEF = "belief"
    PLAN = "plan"

class MemoryImportance(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

@dataclass
class MemoryRecord:
    timestamp: str
    memory_type: MemoryType
    importance: MemoryImportance
    agent_id: str
    content: Dict[str, Any]
    context: Dict[str, Any]
    tags: List[str]
    parent_memory_id: Optional[str] = None
    memory_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.memory_id:
            content_str = json_lib.dumps(self.content, sort_keys=True)
            hash_obj = hashlib.sha256(f"{self.timestamp}:{self.agent_id}:{content_str}".encode())
            self.memory_id = hash_obj.hexdigest()[:16]

class EnhancedMemoryAgent:
    """Enhanced memory agent with timestamped records and context management."""

    def __init__(self, config: Optional[Config] = None, log_level: str = "INFO"):
        self.config = config or Config()
        
        # Setup logging
        log_file_enabled = self.config.get("logging.file.enabled", True)
        setup_logging(log_level=log_level, console=True, log_file=log_file_enabled)

        # Define base paths
        self.data_path = PROJECT_ROOT / self.config.get("system.data_path", "data")
        self.memory_base_path = self.data_path / "memory"
        self.context_path = self.memory_base_path / "context"
        self.timestamped_path = self.memory_base_path / "timestamped"
        self.log_path = self.data_path / "logs"

        # In-memory caches
        self.memory_cache: Dict[str, MemoryRecord] = {}
        self.memory_stats = {
            "total_memories": 0,
            "memories_by_type": defaultdict(int),
            "memories_by_agent": defaultdict(int),
        }

        self._initialize_storage()
        logger.info("Enhanced MemoryAgent initialized with timestamped memory capabilities.")

    def _initialize_storage(self):
        """Initialize the memory storage structure."""
        try:
            directories = [
                self.memory_base_path,
                self.context_path,
                self.timestamped_path,
                self.log_path,
                self.memory_base_path / "agent_workspaces",
                self.memory_base_path / "analytics"
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Enhanced MemoryAgent storage initialized under '{self.data_path}'.")
        except OSError as e:
            logger.critical(f"FATAL: Failed to create memory directory structure: {e}", exc_info=True)
            raise

    async def save_timestamped_memory(
        self, 
        agent_id: str,
        memory_type: MemoryType,
        content: Dict[str, Any],
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        parent_memory_id: Optional[str] = None
    ) -> Optional[str]:
        """Save a timestamped memory record."""
        try:
            timestamp = datetime.now().isoformat()
            
            memory_record = MemoryRecord(
                timestamp=timestamp,
                memory_type=memory_type,
                importance=importance,
                agent_id=agent_id,
                content=content,
                context=context or {},
                tags=tags or [],
                parent_memory_id=parent_memory_id
            )
            
            # Determine file path
            date_str = datetime.now().strftime("%Y%m%d")
            agent_dir = self.timestamped_path / agent_id / date_str
            agent_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{timestamp.replace(':', '-')}.{memory_type.value}.memory.json"
            filepath = agent_dir / filename
            
            # Save to file
            async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                await f.write(json_lib.dumps(asdict(memory_record), indent=2))
            
            # Update cache and stats
            if memory_record.memory_id:
                self.memory_cache[memory_record.memory_id] = memory_record
            self.memory_stats["total_memories"] += 1
            self.memory_stats["memories_by_type"][memory_type.value] += 1
            self.memory_stats["memories_by_agent"][agent_id] += 1
            
            logger.debug(f"Timestamped memory saved: {filepath}")
            return memory_record.memory_id
            
        except Exception as e:
            logger.error(f"Failed to save timestamped memory: {e}", exc_info=True)
            return None

    async def save_interaction_memory(
        self,
        agent_id: str,
        input_content: str,
        response_content: str,
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[str]:
        """Save an input-response interaction as a memory."""
        interaction_data = {
            "input": input_content,
            "response": response_content,
            "interaction_timestamp": datetime.now().isoformat(),
            "success": context.get("success", True) if context else True
        }
        
        if context:
            interaction_data.update(context)
        
        return await self.save_timestamped_memory(
            agent_id=agent_id,
            memory_type=MemoryType.INTERACTION,
            content=interaction_data,
            importance=MemoryImportance.HIGH,
            context=context,
            tags=tags
        )

    async def get_recent_memories(
        self,
        agent_id: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 50,
        days_back: int = 7
    ) -> List[MemoryRecord]:
        """Retrieve recent memories for an agent with optional filtering."""
        try:
            memories = []
            agent_dir = self.timestamped_path / agent_id
            if not agent_dir.exists():
                return []
            
            # Get files from the last N days
            for day_offset in range(days_back):
                date_str = (datetime.now() - timedelta(days=day_offset)).strftime("%Y%m%d")
                day_dir = agent_dir / date_str
                
                if not day_dir.exists():
                    continue
                
                # Get all memory files for this day
                pattern = f"*.{memory_type.value}.memory.json" if memory_type else "*.memory.json"
                files = sorted(day_dir.glob(pattern), reverse=True)
                
                for file_path in files:
                    if len(memories) >= limit:
                        break
                    
                    try:
                        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                            content = await f.read()
                            record_data = json_lib.loads(content)
                            
                        # Convert back to MemoryRecord
                        record_data["memory_type"] = MemoryType(record_data["memory_type"])
                        record_data["importance"] = MemoryImportance(record_data["importance"])
                        memory_record = MemoryRecord(**record_data)
                        
                        memories.append(memory_record)
                    except Exception as e:
                        logger.warning(f"Failed to load memory file {file_path}: {e}")
                        continue
                
                if len(memories) >= limit:
                    break
            
            return memories[:limit]
            
        except Exception as e:
            logger.error(f"Failed to retrieve recent memories for {agent_id}: {e}", exc_info=True)
            return []

    async def analyze_agent_patterns(self, agent_id: str, days_back: int = 7) -> Dict[str, Any]:
        """Analyze patterns in an agent's memory for self-awareness."""
        try:
            memories = await self.get_recent_memories(agent_id, days_back=days_back, limit=1000)
            
            if not memories:
                return {"error": "No memories found for analysis"}
            
            # Analyze patterns
            analysis = {
                "total_memories": len(memories),
                "memory_types": defaultdict(int),
                "activity_by_hour": defaultdict(int),
                "error_patterns": [],
                "success_patterns": [],
                "insights": []
            }
            
            for memory in memories:
                # Count by type
                analysis["memory_types"][memory.memory_type.value] += 1
                
                # Activity by hour
                hour = datetime.fromisoformat(memory.timestamp).hour
                analysis["activity_by_hour"][hour] += 1
                
                # Error analysis
                if memory.memory_type == MemoryType.ERROR:
                    analysis["error_patterns"].append({
                        "timestamp": memory.timestamp,
                        "content": memory.content,
                        "tags": memory.tags
                    })
                
                # Success patterns
                if (memory.memory_type == MemoryType.INTERACTION and 
                    memory.content.get("success", False)):
                    analysis["success_patterns"].append({
                        "timestamp": memory.timestamp,
                        "input": memory.content.get("input", ""),
                        "tags": memory.tags
                    })
            
            # Convert defaultdicts to regular dicts
            analysis["memory_types"] = dict(analysis["memory_types"])
            analysis["activity_by_hour"] = dict(analysis["activity_by_hour"])
            
            # Generate insights
            analysis["insights"] = await self._generate_insights(analysis, agent_id)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze patterns for {agent_id}: {e}", exc_info=True)
            return {"error": str(e)}

    async def _generate_insights(self, analysis: Dict[str, Any], agent_id: str) -> List[str]:
        """Generate insights from memory analysis."""
        insights = []
        
        # Activity patterns
        if analysis["total_memories"] == 0:
            insights.append("Agent has no recent memory activity")
        elif analysis["total_memories"] > 100:
            insights.append("Agent shows high activity levels")
        
        # Error analysis
        error_count = len(analysis["error_patterns"])
        total_memories = analysis["total_memories"]
        if error_count > 0 and total_memories > 0:
            error_rate = error_count / total_memories
            if error_rate > 0.1:
                insights.append(f"High error rate detected: {error_rate:.1%}")
            elif error_rate > 0.05:
                insights.append(f"Moderate error rate: {error_rate:.1%}")
        
        # Activity timing
        activity_hours = analysis["activity_by_hour"]
        if activity_hours:
            peak_hour = max(activity_hours, key=activity_hours.get)
            insights.append(f"Peak activity hour: {peak_hour}:00")
        
        return insights

    async def get_system_health_summary(self) -> Dict[str, Any]:
        """Generate a comprehensive system health summary from memory data."""
        try:
            summary = {
                "timestamp": datetime.now().isoformat(),
                "memory_stats": dict(self.memory_stats),
                "agent_activity": {},
                "alerts": [],
                "recommendations": []
            }
            
            # Analyze activity per agent
            for agent_id in self.memory_stats["memories_by_agent"]:
                patterns = await self.analyze_agent_patterns(agent_id, days_back=1)
                summary["agent_activity"][agent_id] = {
                    "memory_count": patterns.get("total_memories", 0),
                    "types": patterns.get("memory_types", {}),
                    "errors": len(patterns.get("error_patterns", [])),
                    "successes": len(patterns.get("success_patterns", []))
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate system health summary: {e}", exc_info=True)
            return {"error": str(e)}

    async def generate_human_readable_summary(self, agent_id: str, days_back: int = 1) -> str:
        """Generate a human-readable summary of agent activity."""
        try:
            analysis = await self.analyze_agent_patterns(agent_id, days_back)
            
            if "error" in analysis:
                return f"Error generating summary for {agent_id}: {analysis['error']}"
            
            summary_lines = [
                f"# Memory Summary for {agent_id}",
                f"Time Period: Last {days_back} day(s)",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                f"## Activity Overview",
                f"- Total memories: {analysis['total_memories']}",
                f"- Memory types: {', '.join(analysis['memory_types'].keys())}",
                f"- Errors encountered: {len(analysis['error_patterns'])}",
                f"- Successful interactions: {len(analysis['success_patterns'])}",
                ""
            ]
            
            if analysis["insights"]:
                summary_lines.extend([
                    "## Key Insights",
                    *[f"- {insight}" for insight in analysis["insights"]],
                    ""
                ])
            
            return "\n".join(summary_lines)
            
        except Exception as e:
            logger.error(f"Failed to generate human-readable summary: {e}", exc_info=True)
            return f"Error generating summary: {e}"

    # Compatibility methods with original MemoryAgent
    async def get_agent_data_directory(self, agent_id: str, ensure_exists: bool = True) -> Path:
        """Get agent-specific data directory."""
        safe_agent_id = re.sub(r'[^\w\-\.]', '_', agent_id)
        agent_dir = self.memory_base_path / "agent_workspaces" / safe_agent_id
        
        if ensure_exists:
            try:
                agent_dir.mkdir(parents=True, exist_ok=True)
                (agent_dir / "process_traces").mkdir(exist_ok=True)
            except OSError as e:
                logger.error(f"Failed to create data directory for agent '{agent_id}': {e}", exc_info=True)
        
        return agent_dir

    async def log_process(self, process_name: str, data: Dict[str, Any], metadata: Dict[str, Any]) -> Optional[Path]:
        """Log process information (compatibility method)."""
        agent_id = metadata.get("agent_id", "unknown")
        
        # Save as timestamped memory
        memory_id = await self.save_timestamped_memory(
            agent_id=agent_id,
            memory_type=MemoryType.SYSTEM_STATE,
            content={"process_name": process_name, "data": data},
            context=metadata,
            tags=[process_name, "process_log"]
        )
        
        # Also maintain compatibility with original format
        try:
            agent_workspace = await self.get_agent_data_directory(agent_id)
            filepath = agent_workspace / "process_trace.jsonl"
            
            timestamp = datetime.now()
            log_record = {
                "timestamp_utc": timestamp.utcnow().isoformat(),
                "process_name": process_name,
                "metadata": metadata,
                "process_data": data,
                "memory_id": memory_id
            }
            
            log_line = json_lib.dumps(log_record) + "\n"
            
            async with aiofiles.open(filepath, "a", encoding="utf-8") as f:
                await f.write(log_line)
            
            return filepath
        except Exception as e:
            logger.error(f"Failed to write process log: {e}", exc_info=True)
            return None

    async def log_terminal_output(self, output: str) -> Optional[Path]:
        """Log terminal output (compatibility method)."""
        try:
            log_file = self.log_path / "mindx_terminal.log"
            async with aiofiles.open(log_file, "a", encoding="utf-8") as f:
                await f.write(f"[{datetime.now().isoformat()}] {output}\n")
            return log_file
        except Exception as e:
            logger.error(f"Failed to write terminal log: {e}", exc_info=True)
            return None 