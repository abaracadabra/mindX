# mindx/agents/enhanced_memory_agent.py
"""
Enhanced MemoryAgent with timestamped memory, context management, and self-awareness.

mindX architecture: all logs are memories in data, and all memories are logged.
Logging (Gödel choices, AGInt cycles, process traces) goes through this agent into
data/logs and data/memory; each log entry is also stored as timestamped memory and
process_trace so it is queryable as memory. Do not write logs directly to data/—use
memory_agent so the system stays consistent.
"""
from __future__ import annotations
import asyncio
import aiofiles
import aiofiles.os
import re
import json
import hashlib
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
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

class MemoryAgent:
    """
    Enhanced memory agent with timestamped records, context management, and backward compatibility.

    mindX architecture principle: all logs are memories in data, and all memories are logged.
    Logs (Gödel choices, AGInt cycles, process traces) are stored under data/logs and data/memory
    via this agent; each log entry is also recorded as timestamped memory and process_trace
    so it is queryable as memory. Do not write logs directly to data/—use memory_agent.
    """

    def __init__(self, config: Optional[Config] = None, log_level: str = "INFO"):
        self.config = config or Config()

        # Setup logging
        log_file_enabled = self.config.get("logging.file.enabled", True)
        setup_logging(log_level=log_level, console=True, log_file=log_file_enabled)

        # Verified identity — MemoryAgent is a sovereign entity in the mindX civilization
        self.agent_id = "memory_agent_main"
        self.wallet_address: Optional[str] = None
        self._verify_identity()

        # Define base paths (all logs and memories live under data/ via memory_agent)
        self.data_path = PROJECT_ROOT / self.config.get("system.data_path", "data")
        self.memory_base_path = self.data_path / "memory"
        self.context_path = self.memory_base_path / "context"
        self.stm_path = self.memory_base_path / "stm"  # Short Term Memory - real-time interactions
        self.ltm_path = self.memory_base_path / "ltm"  # Long Term Memory - learned patterns and insights
        self.log_path = self.data_path / "logs"
        self.process_trace_path = self.log_path / "process_traces"
        self.agint_log_path = self.log_path / "agint" / "agint_cognitive_cycles.log"

        # In-memory caches
        self.memory_cache: Dict[str, MemoryRecord] = {}
        self.memory_stats = {
            "total_memories": 0,
            "memories_by_type": defaultdict(int),
            "memories_by_agent": defaultdict(int),
        }

        # pgvector backend (DB primary, file backup)
        self._pg_available = False
        try:
            from agents import memory_pgvector as _mpg
            self._pg = _mpg
            self._pg_available = True
        except Exception:
            self._pg = None

        self._initialize_storage()
        if UJSON_AVAILABLE:
            logger.info("ujson library detected, will be used for faster JSON operations.")
        logger.info(f"MemoryAgent initialized (identity: {self.wallet_address or 'unverified'}, pgvector: {self._pg_available}).")

    def _verify_identity(self):
        """
        Verify MemoryAgent's cryptographic identity from BANKON Vault.
        The memory keeper must be a verified sovereign entity —
        every memory stored is attributable to a known identity.
        """
        try:
            from mindx_backend_service.bankon_vault.vault import BankonVault
            vault = BankonVault()
            vault.unlock_with_key_file()
            pk_hex = vault.retrieve(f"agent_pk_{self.agent_id}")
            vault.lock()
            if pk_hex:
                from eth_account import Account
                self.wallet_address = Account.from_key(pk_hex).address
                logger.info(f"MemoryAgent identity verified: {self.wallet_address}")
            else:
                logger.warning("MemoryAgent: no identity in BANKON Vault — operating without verified identity")
        except Exception as e:
            logger.warning(f"MemoryAgent: identity verification skipped ({e})")

    def _initialize_storage(self):
        """Initialize the memory storage structure."""
        try:
            directories = [
                self.memory_base_path,
                self.context_path,
                self.stm_path,
                self.ltm_path,
                self.log_path,
                self.process_trace_path,
                self.log_path / "agint",
                self.memory_base_path / "agent_workspaces",
                self.memory_base_path / "analytics"
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)

            # Ensure AGInt cognitive cycle log exists (all logs are memories; memory_agent owns this file)
            if not self.agint_log_path.exists():
                with open(self.agint_log_path, "w", encoding="utf-8") as f:
                    f.write("# AGInt Cognitive Loop Log\n")
                    f.write(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("# Format: [TIMESTAMP] CYCLE X - MESSAGE\n\n")
            
            logger.info(f"MemoryAgent Initialized: All memory and log directories verified/created under '{self.data_path}'.")
        except OSError as e:
            logger.critical(f"FATAL: Failed to create required directory structure under {self.data_path}. Check permissions. Error: {e}", exc_info=True)
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
            
            # Determine file path - store in STM for real-time interactions
            date_str = datetime.now().strftime("%Y%m%d")
            agent_dir = self.stm_path / agent_id / date_str
            agent_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{timestamp.replace(':', '-')}.{memory_type.value}.memory.json"
            filepath = agent_dir / filename
            
            # Save to file
            record_dict = asdict(memory_record)
            # Convert enums to strings for JSON serialization
            record_dict["memory_type"] = record_dict["memory_type"].value
            record_dict["importance"] = record_dict["importance"].value
            
            async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                await f.write(json_lib.dumps(record_dict, indent=2))
            
            # Update cache and stats
            if memory_record.memory_id:
                self.memory_cache[memory_record.memory_id] = memory_record
            self.memory_stats["total_memories"] += 1
            self.memory_stats["memories_by_type"][memory_type.value] += 1
            self.memory_stats["memories_by_agent"][agent_id] += 1

            # pgvector: store in PostgreSQL (non-blocking, file is already saved)
            if self._pg_available and self._pg and memory_record.memory_id:
                try:
                    await self._pg.store_memory(
                        memory_id=memory_record.memory_id,
                        agent_id=agent_id,
                        memory_type=memory_type.value,
                        importance=importance.value,
                        content=content,
                        context=context or {},
                        tags=tags or [],
                        parent_memory_id=parent_memory_id,
                    )
                    # Also embed the memory (best-effort, non-blocking)
                    try:
                        text = str(content)[:2000]
                        if len(text) > 50:
                            await self._pg.embed_memory(memory_record.memory_id, text)
                    except Exception:
                        pass
                except Exception:
                    pass  # File already saved — DB is best-effort

            logger.debug(f"Timestamped memory saved: {filepath}")

            # Catalogue mirror (Phase 0) — additive; failures never affect this call.
            try:
                from agents.catalogue import emit_catalogue_event
                await emit_catalogue_event(
                    kind="memory.write",
                    actor=agent_id,
                    payload=record_dict,
                    source_log=str(filepath.relative_to(self.data_path) if filepath.is_relative_to(self.data_path) else filepath.name),
                    source_ref=memory_record.memory_id,
                )
            except Exception:
                pass

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

    async def fetch_offloaded_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Lazy-load a memory whose content lives on IPFS.

        Looks up content_cid in pgvector, fetches the bundle via MultiProvider,
        iterates to find the matching memory_id. Returns the raw record dict
        or None on miss / error.

        Plan: ~/.claude/plans/whispering-floating-merkle.md (Phase E)
        """
        try:
            from agents import memory_pgvector
        except Exception:
            return None
        pool = await memory_pgvector.get_pool()
        if not pool:
            return None
        try:
            row = await pool.fetchrow(
                "SELECT content_cid, content_cid_mirror, offload_tier "
                "FROM memories WHERE memory_id=$1",
                memory_id,
            )
        except Exception:
            return None
        if not row or row["offload_tier"] != "ipfs" or not row["content_cid"]:
            return None
        try:
            from agents.storage.lighthouse_provider import LighthouseProvider
            from agents.storage.nftstorage_provider import NFTStorageProvider
            from agents.storage.multi_provider import MultiProvider
            from agents.storage.car_bundle import bundle_iter
            from agents.storage.provider import CID, ProviderError
        except Exception:
            return None
        primary = None
        mirror = None
        try:
            primary = LighthouseProvider()
        except ProviderError:
            primary = None
        try:
            mirror = NFTStorageProvider()
        except ProviderError:
            mirror = None
        if primary is None and mirror is None:
            return None
        if primary is None:
            provider = MultiProvider(mirror)
        elif mirror is None:
            provider = MultiProvider(primary)
        else:
            provider = MultiProvider(primary, mirror)
        try:
            blob = await provider.retrieve(CID(row["content_cid"]), timeout=12.0)
        except ProviderError:
            return None
        finally:
            await provider.close()
        for entry in bundle_iter(blob):
            rec = entry.get("record") or {}
            if rec.get("memory_id") == memory_id:
                return rec
        return None

    async def get_recent_memories(
        self,
        agent_id: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 50,
        days_back: int = 7
    ) -> List[MemoryRecord]:
        """Retrieve recent memories for an agent with optional filtering.

        Searches STM first, then falls back to archive if STM is empty.
        Memory philosophy: distribute don't constrain — archived data is still accessible.
        """
        try:
            memories = []
            # Search STM first, fall back to archive
            search_dirs = [self.stm_path / agent_id]
            archive_dir = self.memory_base_path / "archive" / agent_id
            if archive_dir.exists():
                search_dirs.append(archive_dir)

            for agent_dir in search_dirs:
                if not agent_dir.exists():
                    continue

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

                if len(memories) >= limit:
                    break

            return memories[:limit]

        except Exception as e:
            logger.error(f"Failed to retrieve recent memories for {agent_id}: {e}", exc_info=True)
            return []

    async def get_memories_by_agent(
        self,
        agent_id: str,
        limit: int = 50,
        memory_type: Optional[MemoryType] = None,
        days_back: int = 7
    ) -> List[MemoryRecord]:
        """Retrieve memories for a specific agent. Delegates to get_recent_memories.

        Used as fallback by RAGE routes when semantic search is unavailable.
        """
        return await self.get_recent_memories(
            agent_id=agent_id, memory_type=memory_type, limit=limit, days_back=days_back
        )

    async def analyze_agent_patterns(self, agent_id: str, days_back: int = 7) -> Dict[str, Any]:
        """Analyze patterns in an agent's memory for self-awareness.

        Actual memory format: MemoryRecord with memory_type (mostly system_state),
        content = {process_name: str, data: {..., success: bool, ...}}, tags = [process_name, ...].
        Success/failure is extracted from content.data.success and process_name suffixes.
        """
        try:
            memories = await self.get_recent_memories(agent_id, days_back=days_back, limit=1000)

            if not memories:
                return {"error": "No memories found for analysis"}

            analysis = {
                "total_memories": len(memories),
                "memory_types": defaultdict(int),
                "process_types": defaultdict(int),
                "activity_by_hour": defaultdict(int),
                "error_patterns": [],
                "success_patterns": [],
                "failure_patterns": [],
                "success_rate": 0.0,
                "insights": []
            }

            success_count = 0
            failure_count = 0

            for memory in memories:
                # Count by memory_type
                analysis["memory_types"][memory.memory_type.value] += 1

                # Activity by hour
                try:
                    hour = datetime.fromisoformat(memory.timestamp).hour
                    analysis["activity_by_hour"][hour] += 1
                except (ValueError, TypeError):
                    pass

                # Extract process_name from content
                process_name = memory.content.get("process_name", "") if isinstance(memory.content, dict) else ""
                if process_name:
                    analysis["process_types"][process_name] += 1

                # Extract success/failure from actual data structure
                data = memory.content.get("data", {}) if isinstance(memory.content, dict) else {}
                has_success_field = isinstance(data, dict) and "success" in data

                # Error patterns: explicit ERROR type OR process names ending in _error/_failed
                is_error = (
                    memory.memory_type == MemoryType.ERROR
                    or process_name.endswith("_error")
                    or process_name.endswith("_failed")
                    or (has_success_field and data.get("success") is False)
                )

                # Success patterns: explicit success=True OR process names ending in _completed/_success
                is_success = (
                    (has_success_field and data.get("success") is True)
                    or process_name.endswith("_completed")
                    or process_name.endswith("_success")
                )

                if is_error:
                    failure_count += 1
                    analysis["error_patterns"].append({
                        "timestamp": memory.timestamp,
                        "process": process_name,
                        "content": str(data)[:200] if data else str(memory.content)[:200],
                        "tags": memory.tags
                    })
                    analysis["failure_patterns"].append({
                        "timestamp": memory.timestamp,
                        "process": process_name,
                        "reason": data.get("message", data.get("result", {}).get("message", "")) if isinstance(data, dict) else ""
                    })
                elif is_success:
                    success_count += 1
                    analysis["success_patterns"].append({
                        "timestamp": memory.timestamp,
                        "process": process_name,
                        "tags": memory.tags
                    })

            # Calculate success rate from events that have a clear outcome
            outcome_count = success_count + failure_count
            if outcome_count > 0:
                analysis["success_rate"] = success_count / outcome_count
            else:
                analysis["success_rate"] = 0.0  # No measurable outcomes

            # Convert defaultdicts to regular dicts
            analysis["memory_types"] = dict(analysis["memory_types"])
            analysis["process_types"] = dict(analysis["process_types"])
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
        total = analysis["total_memories"]

        # Activity volume
        if total == 0:
            insights.append("Agent has no recent memory activity")
            return insights
        elif total > 500:
            insights.append(f"High activity: {total} memories")
        elif total > 100:
            insights.append(f"Active: {total} memories")

        # Success/failure analysis
        success_rate = analysis.get("success_rate", 0.0)
        success_count = len(analysis.get("success_patterns", []))
        failure_count = len(analysis.get("failure_patterns", []))
        if success_count + failure_count > 0:
            insights.append(f"Success rate: {success_rate:.1%} ({success_count} success, {failure_count} failure)")
            if success_rate < 0.5 and failure_count > 3:
                insights.append("Low success rate — review failure patterns for recurring issues")

        # Error analysis
        error_count = len(analysis.get("error_patterns", []))
        if error_count > 0:
            error_rate = error_count / total
            if error_rate > 0.1:
                insights.append(f"High error rate: {error_rate:.1%} ({error_count} errors)")
            elif error_rate > 0.05:
                insights.append(f"Moderate error rate: {error_rate:.1%}")

        # Process diversity
        process_types = analysis.get("process_types", {})
        if process_types:
            top_processes = sorted(process_types.items(), key=lambda x: x[1], reverse=True)[:5]
            top_names = [f"{name}({count})" for name, count in top_processes]
            insights.append(f"Top processes: {', '.join(top_names)}")

        # Activity timing
        activity_hours = analysis.get("activity_by_hour", {})
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
    def get_agent_data_directory(self, agent_id: str, ensure_exists: bool = True) -> Path:
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
            agent_workspace = self.get_agent_data_directory(agent_id)
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

    async def log_godel_choice(self, choice_record: Dict[str, Any]) -> Optional[Path]:
        """
        Append a single Gödel core choice to the global log (data/logs/godel_choices.jsonl).
        Used to audit mindX as a Gödel machine: perception, options, chosen option, rationale, outcome.
        Also stored as memory via log_process so all logs are memories.
        """
        try:
            self.log_path.mkdir(parents=True, exist_ok=True)
            filepath = self.log_path / "godel_choices.jsonl"
            ts = datetime.utcnow().isoformat() + "Z"
            record = dict(choice_record)
            if "timestamp_utc" not in record:
                record["timestamp_utc"] = ts
            log_line = json_lib.dumps(record, default=str) + "\n"
            async with aiofiles.open(filepath, "a", encoding="utf-8") as f:
                await f.write(log_line)
            await self.log_process(
                "godel_core_choice",
                record,
                {"agent_id": record.get("source_agent", "system")},
            )

            # Catalogue mirror (Phase 0)
            try:
                from agents.catalogue import emit_catalogue_event
                await emit_catalogue_event(
                    kind="godel.choice",
                    actor=record.get("source_agent", "system"),
                    payload=record,
                    source_log="logs/godel_choices.jsonl",
                    source_ref=record.get("cycle_id") and str(record.get("cycle_id")),
                )
            except Exception:
                pass

            return filepath
        except Exception as e:
            logger.error(f"Failed to write Gödel choice log: {e}", exc_info=True)
            return None

    async def log_agint_cycle(self, cycle_id: int, message_type: str, message: str) -> Optional[Path]:
        """
        Append an AGInt cognitive cycle log line. All logs are memories: also stored via log_process.
        Call this instead of writing directly to data/logs/agint/.
        """
        try:
            line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] CYCLE {cycle_id} - {message}\n"
            async with aiofiles.open(self.agint_log_path, "a", encoding="utf-8") as f:
                await f.write(line)
            await self.log_process(
                "agint_cycle_log",
                {"cycle_id": cycle_id, "message_type": message_type, "message": message},
                {"agent_id": "agint_system"},
            )
            return self.agint_log_path
        except Exception as e:
            logger.error(f"Failed to write AGInt cycle log: {e}", exc_info=True)
            return None

    def get_godel_choices(self, limit: int = 50, source_agent: Optional[str] = None) -> Tuple[List[Dict[str, Any]], int]:
        """
        Read last N Gödel core choices from data/logs/godel_choices.jsonl (newest first).
        All logs are in data and readable through memory_agent.
        """
        filepath = self.log_path / "godel_choices.jsonl"
        if not filepath.exists():
            return [], 0
        choices: List[Dict[str, Any]] = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json_lib.loads(line)
                        if source_agent is not None and record.get("source_agent") != source_agent:
                            continue
                        choices.append(record)
                    except (json.JSONDecodeError, TypeError):
                        continue
            total = len(choices)
            choices = choices[-limit:] if limit else choices
            choices.reverse()
            return choices, total
        except Exception as e:
            logger.warning(f"Failed to read Gödel choices: {e}")
            return [], 0

    def get_agint_cycle_log(self, last_n_lines: Optional[int] = None) -> List[str]:
        """Read AGInt cognitive cycle log from memory_agent-owned path. Returns lines (newest last if last_n_lines set)."""
        if not self.agint_log_path.exists():
            return []
        try:
            with open(self.agint_log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if last_n_lines is not None:
                lines = lines[-last_n_lines:]
            return [ln.rstrip("\n") for ln in lines]
        except Exception as e:
            logger.warning(f"Failed to read AGInt cycle log: {e}")
            return []

    async def store_memory(
        self,
        content: Any,
        memory_type: str = "interaction",
        importance: str = "medium",
        metadata: Optional[Dict[str, Any]] = None,
        agent_id: str = "system",
    ) -> Optional[str]:
        """
        Store a memory (compatibility with AgenticPlace, main_service, etc.).
        Maps to save_timestamped_memory. content can be str or dict.
        """
        try:
            mt = memory_type.lower() if isinstance(memory_type, str) else "interaction"
            imp = importance.lower() if isinstance(importance, str) else "medium"
            type_map = {
                "interaction": MemoryType.INTERACTION,
                "system_state": MemoryType.SYSTEM_STATE,
                "performance": MemoryType.PERFORMANCE,
                "error": MemoryType.ERROR,
                "learning": MemoryType.LEARNING,
                "context": MemoryType.CONTEXT,
            }
            imp_map = {
                "critical": MemoryImportance.CRITICAL,
                "high": MemoryImportance.HIGH,
                "medium": MemoryImportance.MEDIUM,
                "low": MemoryImportance.LOW,
            }
            mem_type = type_map.get(mt, MemoryType.INTERACTION)
            mem_imp = imp_map.get(imp, MemoryImportance.MEDIUM)
            payload = {"content": content} if isinstance(content, (str, int, float)) else content
            if not isinstance(payload, dict):
                payload = {"content": str(content)}
            return await self.save_timestamped_memory(
                agent_id=agent_id,
                memory_type=mem_type,
                content=payload,
                importance=mem_imp,
                context=metadata or {},
                tags=["store_memory", mt],
            )
        except Exception as e:
            logger.error(f"Failed to store memory: {e}", exc_info=True)
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

    async def save_memory(self, memory_type: str, category: str, data: Dict[str, Any], metadata: Dict[str, Any]) -> Optional[Path]:
        """
        Backward compatibility method for saving memory records.
        
        Args:
            memory_type: 'STM' for Short-Term, 'LTM' for Long-Term.
            category: A subfolder to organize memories.
            data: The core Python dictionary to be saved.
            metadata: A dictionary for extra context.

        Returns:
            The Path object of the newly created memory file, or None on failure.
        """
        try:
            base_path = self.memory_base_path / memory_type.lower() / category
            base_path.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now()
            filename = f"{timestamp.strftime('%Y%m%d%H%M%S_%f')}.{category.replace('/', '_')}.mem.json"
            filepath = base_path / filename

            memory_record = {
                "timestamp_utc": timestamp.utcnow().isoformat(),
                "memory_type": memory_type,
                "category": category,
                "metadata": metadata,
                "data": data,
            }

            async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                await f.write(json_lib.dumps(memory_record, indent=2))
            
            logger.debug(f"{memory_type} record saved: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save {memory_type} record: {e}", exc_info=True)
            return None

    async def save_timestampmemory(
        self,
        agent_id: str,
        input_content: str,
        response_content: str,
        context: Optional[Dict[str, Any]] = None,
        success: bool = True
    ) -> Optional[Path]:
        """
        Backward compatibility method for saving timestamped memory records.
        
        Args:
            agent_id: The agent that generated this interaction
            input_content: The input text or data
            response_content: The response text or data
            context: Additional context information
            success: Whether the interaction was successful
            
        Returns:
            The Path object of the saved memory file, or None on failure.
        """
        try:
            timestamp = datetime.now()
            
            # Create STM (short-term memory) directory structure
            agent_memory_dir = self.stm_path / agent_id
            date_dir = agent_memory_dir / timestamp.strftime("%Y%m%d")
            date_dir.mkdir(parents=True, exist_ok=True)
            
            # Create memory record
            memory_record = {
                "timestamp_utc": timestamp.utcnow().isoformat(),
                "timestamp_local": timestamp.isoformat(),
                "agent_id": agent_id,
                "memory_type": "interaction",
                "input": input_content,
                "response": response_content,
                "success": success,
                "context": context or {},
                "metadata": {
                    "memory_version": "1.0",
                    "created_by": "MemoryAgent.save_timestampmemory"
                }
            }
            
            # Generate filename with timestamp
            filename = f"{timestamp.strftime('%Y%m%d%H%M%S_%f')}.timestampmemory.json"
            filepath = date_dir / filename
            
            # Save to file
            async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                await f.write(json_lib.dumps(memory_record, indent=2))
            
            logger.debug(f"Timestamped memory saved: {filepath}")
            
            # Also save using enhanced memory system
            await self.save_interaction_memory(
                agent_id=agent_id,
                input_content=input_content,
                response_content=response_content,
                context=context,
                tags=["timestampmemory", "backward_compatibility"]
            )
            
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to save timestamped memory: {e}", exc_info=True)
            return None

    async def get_recent_timestampmemories(
        self,
        agent_id: str,
        limit: int = 50,
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Backward compatibility method for retrieving recent timestamped memories.
        
        Args:
            agent_id: The agent to retrieve memories for
            limit: Maximum number of memories to return
            days_back: Number of days to look back
            
        Returns:
            List of memory records
        """
        try:
            memories = []
            agent_memory_dir = self.stm_path / agent_id
            
            if not agent_memory_dir.exists():
                return []
            
            # Get files from the last N days
            for day_offset in range(days_back):
                date_str = (datetime.now() - timedelta(days=day_offset)).strftime("%Y%m%d")
                day_dir = agent_memory_dir / date_str
                
                if not day_dir.exists():
                    continue
                
                # Get all timestampmemory files for this day
                files = sorted(day_dir.glob("*.timestampmemory.json"), reverse=True)
                
                for file_path in files:
                    if len(memories) >= limit:
                        break
                    
                    try:
                        async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                            content = await f.read()
                            memory_record = json_lib.loads(content)
                            memories.append(memory_record)
                    except Exception as e:
                        logger.warning(f"Failed to load memory file {file_path}: {e}")
                        continue
                
                if len(memories) >= limit:
                    break
            
            return memories[:limit]
            
        except Exception as e:
            logger.error(f"Failed to retrieve timestamped memories for {agent_id}: {e}", exc_info=True)
            return []

    async def analyze_agent_memory_patterns(self, agent_id: str, days_back: int = 7) -> Dict[str, Any]:
        """
        Backward compatibility method for analyzing memory patterns.
        
        Args:
            agent_id: The agent to analyze
            days_back: Number of days to analyze
            
        Returns:
            Analysis results with patterns and insights
        """
        try:
            memories = await self.get_recent_timestampmemories(agent_id, limit=1000, days_back=days_back)
            
            if not memories:
                return {"error": f"No memories found for agent {agent_id}"}
            
            # Analyze patterns
            analysis = {
                "agent_id": agent_id,
                "total_memories": len(memories),
                "time_range_days": days_back,
                "success_rate": 0.0,
                "activity_by_hour": {},
                "daily_activity": {},
                "common_contexts": {},
                "error_patterns": [],
                "insights": []
            }
            
            successful_interactions = 0
            hourly_counts = {}
            daily_counts = {}
            context_patterns = {}
            
            for memory in memories:
                # Success rate analysis
                if memory.get("success", True):
                    successful_interactions += 1
                else:
                    analysis["error_patterns"].append({
                        "timestamp": memory.get("timestamp_local"),
                        "context": memory.get("context", {})
                    })
                
                # Time-based analysis
                timestamp_str = memory.get("timestamp_local", "")
                if timestamp_str:
                    try:
                        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        hour = dt.hour
                        date = dt.date().isoformat()
                        
                        hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
                        daily_counts[date] = daily_counts.get(date, 0) + 1
                    except:
                        pass
                
                # Context analysis
                context = memory.get("context", {})
                for key, value in context.items():
                    if isinstance(value, (str, int, float, bool)):
                        context_key = f"{key}:{value}"
                        context_patterns[context_key] = context_patterns.get(context_key, 0) + 1
            
            # Calculate metrics
            analysis["success_rate"] = successful_interactions / len(memories) if memories else 0
            analysis["activity_by_hour"] = hourly_counts
            analysis["daily_activity"] = daily_counts
            
            # Top context patterns
            sorted_contexts = sorted(context_patterns.items(), key=lambda x: x[1], reverse=True)
            analysis["common_contexts"] = dict(sorted_contexts[:10])
            
            # Generate insights
            insights = []
            if analysis["success_rate"] < 0.8:
                insights.append(f"Low success rate: {analysis['success_rate']:.1%}")
            if len(analysis["error_patterns"]) > len(memories) * 0.1:
                insights.append(f"High error rate: {len(analysis['error_patterns'])} errors out of {len(memories)} interactions")
            if hourly_counts:
                peak_hour = max(hourly_counts.keys(), key=lambda x: hourly_counts[x])
                insights.append(f"Peak activity hour: {peak_hour}:00 ({hourly_counts[peak_hour]} interactions)")
            
            analysis["insights"] = insights
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze memory patterns for {agent_id}: {e}", exc_info=True)
            return {"error": str(e)}

    async def generate_memory_summary(
        self,
        agent_id: str,
        days_back: int = 1,
        include_insights: bool = True
    ) -> str:
        """
        Generate a human-readable summary of agent memory patterns.
        
        Args:
            agent_id: The agent to analyze
            days_back: Number of days to analyze
            include_insights: Whether to include AI-generated insights
            
        Returns:
            Human-readable summary string
        """
        try:
            analysis = await self.analyze_agent_memory_patterns(agent_id, days_back)
            
            if "error" in analysis:
                return f"Unable to generate summary: {analysis['error']}"
            
            summary = f"""# Memory Summary for {agent_id}
Time Period: Last {days_back} day(s)
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Activity Overview
- Total memories: {analysis['total_memories']}
- Success rate: {analysis['success_rate']:.1%}
- Errors encountered: {len(analysis['error_patterns'])}

## Key Insights
"""
            
            for insight in analysis['insights']:
                summary += f"- {insight}\n"
            
            if analysis['activity_by_hour']:
                peak_hour = max(analysis['activity_by_hour'].keys(), key=lambda x: analysis['activity_by_hour'][x])
                summary += f"- Peak activity hour: {peak_hour}:00\n"
            
            if analysis['common_contexts']:
                summary += "\n## Common Context Patterns\n"
                for context, count in list(analysis['common_contexts'].items())[:5]:
                    summary += f"- {context}: {count} times\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate memory summary for {agent_id}: {e}", exc_info=True)
            return f"Error generating summary: {str(e)}"

    async def get_runtime_logs(self) -> List[str]:
        """
        Backward compatibility method for getting runtime logs.
        
        Returns:
            List of recent log entries
        """
        try:
            log_file = self.log_path / "mindx_runtime.log"
            if not log_file.exists():
                return []
            
            async with aiofiles.open(log_file, "r", encoding="utf-8") as f:
                content = await f.read()
                return content.split('\n')[-100:]  # Return last 100 lines
                
        except Exception as e:
            logger.error(f"Failed to get runtime logs: {e}", exc_info=True)
            return []

    # ================================
    # SELF-LEARNING AND LTM METHODS
    # ================================

    async def promote_stm_to_ltm(self, agent_id: str, pattern_threshold: int = 3, days_back: int = 7) -> Dict[str, Any]:
        """
        Analyze STM patterns and promote significant learnings to LTM.
        
        Args:
            agent_id: The agent to analyze
            pattern_threshold: Minimum occurrences to consider a pattern significant
            days_back: Days to analyze for patterns
            
        Returns:
            Dictionary with promotion results and insights
        """
        try:
            # Analyze STM patterns
            stm_analysis = await self.analyze_agent_patterns(agent_id, days_back)
            
            if stm_analysis.get("total_memories", 0) < pattern_threshold:
                return {"status": "insufficient_data", "message": f"Need at least {pattern_threshold} memories for pattern analysis"}
            
            # Extract significant patterns for LTM
            significant_patterns = {
                "success_patterns": [],
                "failure_patterns": [],
                "behavioral_insights": [],
                "performance_trends": []
            }
            
            # Success patterns — any measurable success rate is worth recording
            success_rate = stm_analysis.get("success_rate", 0)
            success_list = stm_analysis.get("success_patterns", [])
            if success_rate > 0 or success_list:
                significant_patterns["success_patterns"].append({
                    "pattern": "success_rate_observed",
                    "success_rate": success_rate,
                    "success_count": len(success_list),
                    "top_processes": [s.get("process", "") for s in success_list[:10]],
                    "timestamp": datetime.now().isoformat()
                })

            # Failure patterns — errors are always worth learning from
            failure_list = stm_analysis.get("failure_patterns", [])
            error_patterns = stm_analysis.get("error_patterns", [])
            if failure_list:
                significant_patterns["failure_patterns"] = failure_list[:20]
            elif error_patterns:
                significant_patterns["failure_patterns"] = error_patterns[:20]

            # Performance trends from memory type and process distribution
            memory_types = stm_analysis.get("memory_types", {})
            process_types = stm_analysis.get("process_types", {})
            if memory_types or process_types:
                significant_patterns["performance_trends"].append({
                    "memory_distribution": memory_types,
                    "process_distribution": dict(sorted(process_types.items(), key=lambda x: x[1], reverse=True)[:20]),
                    "total_memories": stm_analysis.get("total_memories", 0),
                    "timestamp": datetime.now().isoformat()
                })

            # Generate behavioral insights
            insights = stm_analysis.get("insights", [])
            if insights:
                significant_patterns["behavioral_insights"] = insights
            
            # Store in LTM
            ltm_record = {
                "agent_id": agent_id,
                "analysis_period": f"{days_back}_days",
                "stm_memories_analyzed": stm_analysis["total_memories"],
                "patterns": significant_patterns,
                "promoted_at": datetime.now().isoformat(),
                "promotion_criteria": {
                    "pattern_threshold": pattern_threshold,
                    "days_analyzed": days_back
                }
            }
            
            # Save to LTM
            ltm_file = self.ltm_path / agent_id / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_pattern_promotion.json"
            ltm_file.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(ltm_file, "w", encoding="utf-8") as f:
                await f.write(json_lib.dumps(ltm_record, indent=2))
            
            logger.info(f"Promoted STM patterns to LTM for {agent_id}: {ltm_file}")
            
            return {
                "status": "success",
                "ltm_file": str(ltm_file),
                "patterns_promoted": len(significant_patterns["success_patterns"]) + len(significant_patterns["failure_patterns"]),
                "insights_count": len(significant_patterns["behavioral_insights"])
            }
            
        except Exception as e:
            logger.error(f"Failed to promote STM to LTM for {agent_id}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def get_ltm_insights(self, agent_id: str, insight_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve long-term memory insights for an agent.
        
        Args:
            agent_id: The agent to get insights for
            insight_type: Optional filter for specific insight types
            
        Returns:
            List of LTM insights
        """
        try:
            ltm_dir = self.ltm_path / agent_id
            if not ltm_dir.exists():
                return []
            
            insights = []
            for ltm_file in ltm_dir.glob("*_pattern_promotion.json"):
                try:
                    async with aiofiles.open(ltm_file, "r", encoding="utf-8") as f:
                        content = await f.read()
                        ltm_record = json_lib.loads(content)
                        
                    if insight_type:
                        # Filter by insight type
                        filtered_patterns = ltm_record.get("patterns", {}).get(insight_type, [])
                        if filtered_patterns:
                            insights.extend(filtered_patterns)
                    else:
                        # Return all patterns
                        patterns = ltm_record.get("patterns", {})
                        for pattern_type, pattern_list in patterns.items():
                            if isinstance(pattern_list, list):
                                insights.extend(pattern_list)
                            
                except Exception as e:
                    logger.warning(f"Failed to load LTM file {ltm_file}: {e}")
                    continue
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get LTM insights for {agent_id}: {e}", exc_info=True)
            return []

    async def generate_self_improvement_recommendations(self, agent_id: str) -> Dict[str, Any]:
        """
        Generate self-improvement recommendations based on STM and LTM analysis.
        
        Args:
            agent_id: The agent to generate recommendations for
            
        Returns:
            Dictionary with improvement recommendations
        """
        try:
            # Get recent STM analysis
            stm_analysis = await self.analyze_agent_patterns(agent_id, days_back=7)
            
            # Get LTM insights
            ltm_insights = await self.get_ltm_insights(agent_id)
            
            recommendations = {
                "agent_id": agent_id,
                "analysis_timestamp": datetime.now().isoformat(),
                "immediate_improvements": [],
                "strategic_improvements": [],
                "behavioral_adjustments": [],
                "performance_optimizations": []
            }
            
            # Analyze current performance
            current_success_rate = stm_analysis.get("success_rate", 0)
            
            # Generate immediate improvements
            if current_success_rate < 0.8:
                recommendations["immediate_improvements"].append({
                    "priority": "HIGH",
                    "action": "investigate_failure_patterns",
                    "description": f"Success rate is {current_success_rate:.1%}, below optimal threshold",
                    "suggested_steps": [
                        "Review recent error patterns",
                        "Identify common failure contexts",
                        "Adjust decision-making parameters"
                    ]
                })
            
            # Analyze error patterns
            error_patterns = stm_analysis.get("error_patterns", [])
            if len(error_patterns) > len(stm_analysis.get("total_memories", 0)) * 0.1:
                recommendations["immediate_improvements"].append({
                    "priority": "MEDIUM",
                    "action": "reduce_error_frequency",
                    "description": f"High error rate detected: {len(error_patterns)} errors",
                    "suggested_steps": [
                        "Implement better input validation",
                        "Add error recovery mechanisms",
                        "Improve context awareness"
                    ]
                })
            
            # Generate strategic improvements from LTM
            success_patterns = [insight for insight in ltm_insights if insight.get("pattern") == "high_success_rate"]
            if success_patterns:
                latest_success = max(success_patterns, key=lambda x: x.get("timestamp", ""))
                recommendations["strategic_improvements"].append({
                    "priority": "LOW",
                    "action": "leverage_historical_success",
                    "description": f"Historical success rate: {latest_success.get('success_rate', 0):.1%}",
                    "suggested_steps": [
                        "Replicate successful context patterns",
                        "Apply proven decision strategies",
                        "Maintain successful behavioral patterns"
                    ]
                })
            
            # Generate behavioral adjustments
            insights = stm_analysis.get("insights", [])
            for insight in insights:
                if "peak activity hour" in insight.lower():
                    recommendations["behavioral_adjustments"].append({
                        "priority": "LOW",
                        "action": "optimize_activity_timing",
                        "description": insight,
                        "suggested_steps": [
                            "Schedule important tasks during peak hours",
                            "Reduce activity during low-performance periods",
                            "Adjust resource allocation based on timing"
                        ]
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate self-improvement recommendations for {agent_id}: {e}", exc_info=True)
            return {"error": str(e)}

    async def get_agent_memory_context(self, agent_id: str, context_type: str = "recent", limit: int = 10) -> Dict[str, Any]:
        """
        Get comprehensive memory context for an agent to inform decision-making.
        
        Args:
            agent_id: The agent to get context for
            context_type: Type of context ('recent', 'patterns', 'ltm', 'all')
            limit: Maximum number of items to return
            
        Returns:
            Dictionary with memory context
        """
        try:
            context = {
                "agent_id": agent_id,
                "context_type": context_type,
                "retrieved_at": datetime.now().isoformat(),
                "stm_memories": [],
                "ltm_insights": [],
                "patterns": {},
                "recommendations": {}
            }
            
            if context_type in ["recent", "all"]:
                # Get recent STM memories
                recent_memories = await self.get_recent_memories(agent_id, limit=limit, days_back=3)
                context["stm_memories"] = [
                    {
                        "timestamp": memory.timestamp,
                        "type": memory.memory_type.value,
                        "importance": memory.importance.value,
                        "content_summary": str(memory.content)[:200] + "..." if len(str(memory.content)) > 200 else str(memory.content),
                        "tags": memory.tags
                    }
                    for memory in recent_memories
                ]
            
            if context_type in ["patterns", "all"]:
                # Get pattern analysis
                patterns = await self.analyze_agent_patterns(agent_id, days_back=7)
                context["patterns"] = {
                    "total_memories": patterns.get("total_memories", 0),
                    "success_rate": patterns.get("success_rate", 0),
                    "memory_types": patterns.get("memory_types", {}),
                    "key_insights": patterns.get("insights", [])
                }
            
            if context_type in ["ltm", "all"]:
                # Get LTM insights
                ltm_insights = await self.get_ltm_insights(agent_id)
                context["ltm_insights"] = ltm_insights[:limit] if ltm_insights else []
            
            if context_type in ["all"]:
                # Get self-improvement recommendations
                recommendations = await self.generate_self_improvement_recommendations(agent_id)
                context["recommendations"] = recommendations
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get memory context for {agent_id}: {e}", exc_info=True)
            return {"error": str(e)}

    async def enable_auto_learning(self, agent_id: str, learning_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Enable automatic learning for an agent by setting up periodic STM to LTM promotion.
        
        Args:
            agent_id: The agent to enable auto-learning for
            learning_config: Configuration for learning parameters
            
        Returns:
            Success status
        """
        try:
            config = learning_config or {
                "promotion_interval_hours": 24,
                "pattern_threshold": 5,
                "analysis_days": 7,
                "auto_recommendations": True
            }
            
            # Store learning configuration
            config_file = self.ltm_path / agent_id / "learning_config.json"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            learning_record = {
                "agent_id": agent_id,
                "enabled_at": datetime.now().isoformat(),
                "config": config,
                "status": "active"
            }
            
            async with aiofiles.open(config_file, "w", encoding="utf-8") as f:
                await f.write(json_lib.dumps(learning_record, indent=2))
            
            logger.info(f"Auto-learning enabled for {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to enable auto-learning for {agent_id}: {e}", exc_info=True)
            return False

    async def prune_stm(self, max_age_days: int = 30) -> Dict[str, Any]:
        """
        Archive STM memories older than max_age_days.
        Moves old files to data/memory/archive/{agent_id}/{date}/ to keep STM lean.
        machine.dreaming will inevitably prune — this keeps the data/ structure sane.
        """
        cutoff = datetime.now() - timedelta(days=max_age_days)
        archive_base = self.memory_base_path / "archive"
        pruned = 0
        errors = 0
        agents_pruned = set()

        try:
            if not self.stm_path.is_dir():
                return {"pruned": 0, "status": "no_stm_directory"}

            for agent_dir in self.stm_path.iterdir():
                if not agent_dir.is_dir():
                    continue
                for date_dir in agent_dir.iterdir():
                    if not date_dir.is_dir():
                        continue
                    try:
                        dir_date = datetime.strptime(date_dir.name, "%Y%m%d")
                        if dir_date < cutoff:
                            # Move to archive
                            archive_dest = archive_base / agent_dir.name / date_dir.name
                            archive_dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(date_dir), str(archive_dest))
                            file_count = len(list(archive_dest.glob("*.json")))
                            pruned += file_count
                            agents_pruned.add(agent_dir.name)
                    except (ValueError, OSError) as e:
                        errors += 1
                        logger.debug(f"Prune skip {date_dir}: {e}")

            result = {
                "pruned": pruned,
                "agents_affected": list(agents_pruned),
                "max_age_days": max_age_days,
                "cutoff_date": cutoff.isoformat(),
                "errors": errors,
                "archive_path": str(archive_base),
            }
            if pruned > 0:
                logger.info(f"STM pruned: {pruned} memories archived from {len(agents_pruned)} agents (>{max_age_days} days)")
            return result

        except Exception as e:
            logger.error(f"STM pruning failed: {e}", exc_info=True)
            return {"pruned": 0, "error": str(e)}