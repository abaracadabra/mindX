# tools/memory_analysis_tool.py
"""
Memory Analysis Tool for MindX Self-Improvement

This tool provides comprehensive analysis of agent memory logs to identify
patterns, performance metrics, and improvement opportunities for the BDI agent.
"""
import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
import re

from core.bdi_agent import BaseTool
from agents.memory_agent import MemoryAgent
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

class MemoryAnalysisTool(BaseTool):
    """Comprehensive memory analysis tool for agent self-improvement."""

    def __init__(self, memory_agent: MemoryAgent, config: Optional[Config] = None, **kwargs):
        super().__init__(**kwargs)
        self.memory_agent = memory_agent
        self.config = config or Config()
        self.agent_id = "memory_analysis_tool"
        self.log_prefix = "MemoryAnalysisTool:"
        
        # Analysis categories
        self.analysis_categories = {
            "performance": ["success_rate", "execution_time", "error_patterns"],
            "behavior": ["decision_patterns", "goal_completion", "tool_usage"],
            "collaboration": ["agent_interactions", "coordination_patterns", "communication_efficiency"],
            "evolution": ["improvement_trends", "capability_growth", "adaptation_patterns"],
            "system_health": ["resource_usage", "error_frequency", "recovery_patterns"]
        }
        
        logger.info(f"{self.log_prefix} Memory analysis tool initialized")

    async def execute(self, action: str, **kwargs) -> Tuple[bool, Any]:
        """Execute memory analysis actions."""
        start_time = time.time()
        
        try:
            if action == "analyze_agent_performance":
                return await self._analyze_agent_performance(**kwargs)
            elif action == "analyze_system_patterns":
                return await self._analyze_system_patterns(**kwargs)
            elif action == "identify_improvement_opportunities":
                return await self._identify_improvement_opportunities(**kwargs)
            elif action == "generate_self_improvement_report":
                return await self._generate_self_improvement_report(**kwargs)
            elif action == "analyze_agent_collaboration":
                return await self._analyze_agent_collaboration(**kwargs)
            elif action == "track_evolution_progress":
                return await self._track_evolution_progress(**kwargs)
            elif action == "analyze_memory_patterns":
                return await self._analyze_memory_patterns(**kwargs)
            else:
                return False, f"Unknown action: {action}"
        except Exception as e:
            logger.error(f"{self.log_prefix} Action execution error: {e}")
            return False, f"Action execution failed: {e}"
        finally:
            # Log performance
            duration = time.time() - start_time
            await self._log_performance(action, duration, kwargs.get("agent_id") or "system")

    async def _analyze_agent_performance(self, agent_id: Optional[str] = None, days_back: int = 7) -> Tuple[bool, Any]:
        """Analyze performance metrics for specific agent or all agents."""
        try:
            analysis = {
                "timestamp": datetime.now().isoformat(),
                "analysis_type": "agent_performance",
                "days_back": days_back,
                "agents_analyzed": []
            }
            
            # Get agent list
            if agent_id:
                agents_to_analyze = [agent_id]
            else:
                agents_to_analyze = await self._get_active_agents(days_back)
            
            for target_agent in agents_to_analyze:
                agent_analysis = await self._analyze_single_agent_performance(target_agent, days_back)
                analysis["agents_analyzed"].append(agent_analysis)
            
            # Generate aggregate insights
            analysis["aggregate_insights"] = await self._generate_aggregate_insights(analysis["agents_analyzed"])
            
            # Log analysis completion
            await self.memory_agent.log_process(
                process_name="memory_analysis_agent_performance",
                data=analysis,
                metadata={"agent_id": self.agent_id}
            )
            
            return True, analysis
            
        except Exception as e:
            return False, f"Agent performance analysis failed: {e}"

    async def _analyze_single_agent_performance(self, agent_id: str, days_back: int) -> Dict[str, Any]:
        """Analyze performance for a single agent."""
        agent_analysis = {
            "agent_id": agent_id,
            "success_metrics": {},
            "error_patterns": {},
            "execution_patterns": {},
            "improvement_trends": {}
        }
        
        # Get memory records for the agent
        memories = await self._get_agent_memories(agent_id, days_back)
        
        # Analyze success rates
        agent_analysis["success_metrics"] = await self._analyze_success_rates(memories)
        
        # Analyze error patterns
        agent_analysis["error_patterns"] = await self._analyze_error_patterns(memories)
        
        # Analyze execution patterns
        agent_analysis["execution_patterns"] = await self._analyze_execution_patterns(memories)
        
        # Analyze improvement trends
        agent_analysis["improvement_trends"] = await self._analyze_improvement_trends(memories)
        
        return agent_analysis

    async def _analyze_system_patterns(self, days_back: int = 7) -> Tuple[bool, Any]:
        """Analyze system-wide patterns and interactions."""
        try:
            analysis = {
                "timestamp": datetime.now().isoformat(),
                "analysis_type": "system_patterns",
                "days_back": days_back,
                "interaction_patterns": {},
                "coordination_patterns": {},
                "resource_patterns": {},
                "evolution_patterns": {}
            }
            
            # Analyze interaction patterns
            analysis["interaction_patterns"] = await self._analyze_interaction_patterns(days_back)
            
            # Analyze coordination patterns
            analysis["coordination_patterns"] = await self._analyze_coordination_patterns(days_back)
            
            # Analyze resource patterns
            analysis["resource_patterns"] = await self._analyze_resource_patterns(days_back)
            
            # Analyze evolution patterns
            analysis["evolution_patterns"] = await self._analyze_evolution_patterns(days_back)
            
            # Log analysis completion
            await self.memory_agent.log_process(
                process_name="memory_analysis_system_patterns",
                data=analysis,
                metadata={"agent_id": self.agent_id}
            )
            
            return True, analysis
            
        except Exception as e:
            return False, f"System pattern analysis failed: {e}"

    async def _identify_improvement_opportunities(self, focus_area: str = "all") -> Tuple[bool, Any]:
        """Identify specific improvement opportunities based on memory analysis."""
        try:
            opportunities = {
                "timestamp": datetime.now().isoformat(),
                "focus_area": focus_area,
                "opportunities": [],
                "priority_matrix": {},
                "implementation_suggestions": []
            }
            
            # Get recent system performance data
            performance_data = await self._get_recent_performance_data()
            
            # Identify performance bottlenecks
            bottlenecks = await self._identify_performance_bottlenecks(performance_data)
            
            # Identify collaboration inefficiencies
            collaboration_issues = await self._identify_collaboration_inefficiencies(performance_data)
            
            # Identify capability gaps
            capability_gaps = await self._identify_capability_gaps(performance_data)
            
            # Identify resource optimization opportunities
            resource_optimizations = await self._identify_resource_optimizations(performance_data)
            
            # Consolidate opportunities
            all_opportunities = bottlenecks + collaboration_issues + capability_gaps + resource_optimizations
            
            # Prioritize opportunities
            opportunities["opportunities"] = await self._prioritize_opportunities(all_opportunities)
            opportunities["priority_matrix"] = await self._create_priority_matrix(opportunities["opportunities"])
            opportunities["implementation_suggestions"] = await self._generate_implementation_suggestions(opportunities["opportunities"])
            
            # Log analysis completion
            await self.memory_agent.log_process(
                process_name="memory_analysis_improvement_opportunities",
                data=opportunities,
                metadata={"agent_id": self.agent_id}
            )
            
            return True, opportunities
            
        except Exception as e:
            return False, f"Improvement opportunity analysis failed: {e}"

    async def _generate_self_improvement_report(self, target_agent: str = "bdi_agent") -> Tuple[bool, Any]:
        """Generate comprehensive self-improvement report for BDI agent."""
        try:
            report = {
                "timestamp": datetime.now().isoformat(),
                "target_agent": target_agent,
                "report_type": "self_improvement",
                "executive_summary": {},
                "detailed_analysis": {},
                "recommendations": {},
                "action_plan": {}
            }
            
            # Executive summary
            report["executive_summary"] = await self._generate_executive_summary(target_agent)
            
            # Detailed analysis sections
            report["detailed_analysis"] = {
                "performance_analysis": await self._analyze_single_agent_performance(target_agent, 30),
                "decision_quality": await self._analyze_decision_quality(target_agent),
                "tool_effectiveness": await self._analyze_tool_effectiveness(target_agent),
                "learning_progress": await self._analyze_learning_progress(target_agent),
                "collaboration_effectiveness": await self._analyze_collaboration_effectiveness(target_agent)
            }
            
            # Generate recommendations
            report["recommendations"] = await self._generate_recommendations(report["detailed_analysis"])
            
            # Create action plan
            report["action_plan"] = await self._create_action_plan(report["recommendations"])
            
            # Log report generation
            await self.memory_agent.log_process(
                process_name="memory_analysis_self_improvement_report",
                data=report,
                metadata={"agent_id": self.agent_id}
            )
            
            return True, report
            
        except Exception as e:
            return False, f"Self-improvement report generation failed: {e}"

    async def _get_agent_memories(self, agent_id: str, days_back: int) -> List[Dict[str, Any]]:
        """Retrieve memory records for an agent within the specified timeframe."""
        memories = []
        
        # Get STM memories
        stm_path = self.memory_agent.stm_path / agent_id
        if stm_path.exists():
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            for day_dir in stm_path.iterdir():
                if day_dir.is_dir():
                    try:
                        day_date = datetime.strptime(day_dir.name, "%Y%m%d")
                        if day_date >= cutoff_date:
                            for memory_file in day_dir.glob("*.memory.json"):
                                try:
                                    with memory_file.open('r') as f:
                                        memory_data = json.load(f)
                                        memories.append(memory_data)
                                except Exception as e:
                                    logger.warning(f"Failed to load memory file {memory_file}: {e}")
                    except ValueError:
                        # Skip directories that don't match date format
                        continue
        
        return memories

    async def _analyze_success_rates(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze success rates from memory records."""
        success_metrics = {
            "total_operations": len(memories),
            "successful_operations": 0,
            "failed_operations": 0,
            "success_rate": 0.0,
            "success_by_process": {},
            "failure_reasons": Counter()
        }
        
        process_stats = defaultdict(lambda: {"total": 0, "success": 0})
        
        for memory in memories:
            content = memory.get("content", {})
            process_name = content.get("process_name", "unknown")
            
            # Determine success based on content
            is_success = self._determine_operation_success(content)
            
            process_stats[process_name]["total"] += 1
            if is_success:
                success_metrics["successful_operations"] += 1
                process_stats[process_name]["success"] += 1
            else:
                success_metrics["failed_operations"] += 1
                # Extract failure reason
                failure_reason = self._extract_failure_reason(content)
                success_metrics["failure_reasons"][failure_reason] += 1
        
        # Calculate success rate
        if success_metrics["total_operations"] > 0:
            success_metrics["success_rate"] = success_metrics["successful_operations"] / success_metrics["total_operations"]
        
        # Calculate success rates by process
        for process, stats in process_stats.items():
            if stats["total"] > 0:
                success_metrics["success_by_process"][process] = {
                    "success_rate": stats["success"] / stats["total"],
                    "total_operations": stats["total"],
                    "successful_operations": stats["success"]
                }
        
        return success_metrics

    async def _analyze_error_patterns(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze error patterns from memory records."""
        error_patterns = {
            "error_frequency": {},
            "error_categories": Counter(),
            "error_trends": {},
            "common_error_sequences": [],
            "recovery_patterns": {}
        }
        
        errors_by_time = []
        error_sequences = []
        current_sequence = []
        
        for memory in memories:
            content = memory.get("content", {})
            timestamp = memory.get("timestamp")
            
            # Check if this is an error-related memory
            if self._is_error_memory(content):
                error_info = {
                    "timestamp": timestamp,
                    "process": content.get("process_name", "unknown"),
                    "error": self._extract_error_info(content)
                }
                errors_by_time.append(error_info)
                current_sequence.append(error_info)
            else:
                # End of error sequence
                if current_sequence:
                    error_sequences.append(current_sequence)
                    current_sequence = []
        
        # Analyze error frequency
        error_patterns["error_frequency"] = self._calculate_error_frequency(errors_by_time)
        
        # Categorize errors
        for error in errors_by_time:
            category = self._categorize_error(error["error"])
            error_patterns["error_categories"][category] += 1
        
        # Analyze error trends
        error_patterns["error_trends"] = self._analyze_error_trends(errors_by_time)
        
        # Identify common error sequences
        error_patterns["common_error_sequences"] = self._identify_common_sequences(error_sequences)
        
        return error_patterns

    async def _log_performance(self, action: str, duration: float, context: str):
        """Log performance metrics for the analysis tool."""
        await self.memory_agent.log_process(
            process_name="memory_analysis_tool_performance",
            data={
                "action": action,
                "duration_seconds": duration,
                "context": context,
                "timestamp": datetime.now().isoformat()
            },
            metadata={"agent_id": self.agent_id}
        )

    # Helper methods for analysis
    def _determine_operation_success(self, content: Dict[str, Any]) -> bool:
        """Determine if an operation was successful based on content."""
        # Check for explicit success indicators
        if "success" in content:
            return content["success"]
        
        # Check for failure indicators in process name
        process_name = content.get("process_name", "").lower()
        if any(word in process_name for word in ["failed", "error", "exception"]):
            return False
        
        # Check for success indicators in process name
        if any(word in process_name for word in ["completed", "success", "finished"]):
            return True
        
        # Check for error in data
        data = content.get("data", {})
        if isinstance(data, dict):
            if "error" in data or "exception" in data:
                return False
            if data.get("status") == "SUCCESS":
                return True
            if data.get("status") == "FAILURE":
                return False
        
        # Default to success if no clear indicators
        return True

    def _extract_failure_reason(self, content: Dict[str, Any]) -> str:
        """Extract failure reason from content."""
        data = content.get("data", {})
        
        if isinstance(data, dict):
            if "reason" in data:
                return data["reason"]
            if "error" in data:
                return str(data["error"])
            if "exception" in data:
                return str(data["exception"])
        
        process_name = content.get("process_name", "")
        if "failed" in process_name:
            return process_name
        
        return "unknown"

    def _is_error_memory(self, content: Dict[str, Any]) -> bool:
        """Check if a memory record represents an error."""
        process_name = content.get("process_name", "").lower()
        return any(word in process_name for word in ["failed", "error", "exception"])

    def _extract_error_info(self, content: Dict[str, Any]) -> str:
        """Extract error information from content."""
        data = content.get("data", {})
        if isinstance(data, dict) and "error" in data:
            return str(data["error"])
        return content.get("process_name", "unknown_error")

    def _categorize_error(self, error_info: str) -> str:
        """Categorize error based on error information."""
        error_lower = error_info.lower()
        
        if any(word in error_lower for word in ["llm", "model", "generation"]):
            return "llm_error"
        elif any(word in error_lower for word in ["network", "connection", "timeout"]):
            return "network_error"
        elif any(word in error_lower for word in ["memory", "storage", "file"]):
            return "storage_error"
        elif any(word in error_lower for word in ["validation", "guardian", "security"]):
            return "security_error"
        elif any(word in error_lower for word in ["agent", "creation", "registration"]):
            return "agent_lifecycle_error"
        else:
            return "general_error"

    async def _get_active_agents(self, days_back: int) -> List[str]:
        """Get list of agents that have been active in the specified timeframe."""
        active_agents = set()
        
        stm_base = self.memory_agent.stm_path
        if stm_base.exists():
            for agent_dir in stm_base.iterdir():
                if agent_dir.is_dir():
                    # Check if agent has recent activity
                    cutoff_date = datetime.now() - timedelta(days=days_back)
                    has_recent_activity = False
                    
                    for day_dir in agent_dir.iterdir():
                        if day_dir.is_dir():
                            try:
                                day_date = datetime.strptime(day_dir.name, "%Y%m%d")
                                if day_date >= cutoff_date:
                                    has_recent_activity = True
                                    break
                            except ValueError:
                                continue
                    
                    if has_recent_activity:
                        active_agents.add(agent_dir.name)
        
        return list(active_agents)

    # Placeholder methods for additional analysis capabilities
    async def _generate_aggregate_insights(self, agent_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate aggregate insights from multiple agent analyses."""
        insights = {
            "system_wide_success_rate": 0.0,
            "most_active_agents": [],
            "common_failure_patterns": [],
            "performance_trends": {},
            "collaboration_health": {}
        }
        
        if not agent_analyses:
            return insights
        
        # Calculate system-wide success rate
        total_ops = sum(analysis.get("success_metrics", {}).get("total_operations", 0) for analysis in agent_analyses)
        total_success = sum(analysis.get("success_metrics", {}).get("successful_operations", 0) for analysis in agent_analyses)
        
        if total_ops > 0:
            insights["system_wide_success_rate"] = total_success / total_ops
        
        # Identify most active agents
        activity_scores = [(analysis["agent_id"], analysis.get("success_metrics", {}).get("total_operations", 0)) 
                          for analysis in agent_analyses]
        insights["most_active_agents"] = sorted(activity_scores, key=lambda x: x[1], reverse=True)[:5]
        
        return insights

    async def _analyze_execution_patterns(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze execution patterns from memories."""
        patterns = {
            "operation_frequency": Counter(),
            "time_distribution": {},
            "process_sequences": [],
            "execution_duration_trends": {}
        }
        
        # Count operation frequency
        for memory in memories:
            process_name = memory.get("content", {}).get("process_name", "unknown")
            patterns["operation_frequency"][process_name] += 1
        
        return patterns

    async def _analyze_improvement_trends(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze improvement trends from memories."""
        trends = {
            "success_rate_over_time": {},
            "error_reduction_trends": {},
            "capability_improvements": {},
            "learning_indicators": {}
        }
        
        # Group memories by time periods
        time_groups = defaultdict(list)
        for memory in memories:
            timestamp = memory.get("timestamp", "")
            if timestamp:
                try:
                    date = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date()
                    time_groups[str(date)].append(memory)
                except:
                    continue
        
        # Analyze trends over time
        for date, day_memories in sorted(time_groups.items()):
            day_success_metrics = await self._analyze_success_rates(day_memories)
            trends["success_rate_over_time"][date] = day_success_metrics["success_rate"]
        
        return trends

    async def _analyze_interaction_patterns(self, days_back: int) -> Dict[str, Any]:
        """Analyze interaction patterns across the system."""
        return {"pattern": "Interaction pattern analysis not yet implemented"}

    async def _analyze_coordination_patterns(self, days_back: int) -> Dict[str, Any]:
        """Analyze coordination patterns across agents."""
        return {"pattern": "Coordination pattern analysis not yet implemented"}

    async def _analyze_resource_patterns(self, days_back: int) -> Dict[str, Any]:
        """Analyze resource usage patterns."""
        return {"pattern": "Resource pattern analysis not yet implemented"}

    async def _analyze_evolution_patterns(self, days_back: int) -> Dict[str, Any]:
        """Analyze evolution patterns in the system."""
        return {"pattern": "Evolution pattern analysis not yet implemented"}

    async def _get_recent_performance_data(self) -> Dict[str, Any]:
        """Get recent performance data for analysis."""
        return {"data": "Performance data collection not yet implemented"}

    async def _identify_performance_bottlenecks(self, performance_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks."""
        return []

    async def _identify_collaboration_inefficiencies(self, performance_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify collaboration inefficiencies."""
        return []

    async def _identify_capability_gaps(self, performance_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify capability gaps."""
        return []

    async def _identify_resource_optimizations(self, performance_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify resource optimization opportunities."""
        return []

    async def _prioritize_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize improvement opportunities."""
        return opportunities

    async def _create_priority_matrix(self, opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create priority matrix for opportunities."""
        return {"matrix": "Priority matrix not yet implemented"}

    async def _generate_implementation_suggestions(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate implementation suggestions."""
        return []

    async def _generate_executive_summary(self, target_agent: str) -> Dict[str, Any]:
        """Generate executive summary for agent."""
        return {"summary": "Executive summary not yet implemented"}

    async def _analyze_decision_quality(self, agent_id: str) -> Dict[str, Any]:
        """Analyze decision quality for agent."""
        return {"quality": "Decision quality analysis not yet implemented"}

    async def _analyze_tool_effectiveness(self, agent_id: str) -> Dict[str, Any]:
        """Analyze tool effectiveness for agent."""
        return {"effectiveness": "Tool effectiveness analysis not yet implemented"}

    async def _analyze_learning_progress(self, agent_id: str) -> Dict[str, Any]:
        """Analyze learning progress for agent."""
        return {"progress": "Learning progress analysis not yet implemented"}

    async def _analyze_collaboration_effectiveness(self, agent_id: str) -> Dict[str, Any]:
        """Analyze collaboration effectiveness for agent."""
        return {"effectiveness": "Collaboration effectiveness analysis not yet implemented"}

    async def _generate_recommendations(self, detailed_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recommendations based on analysis."""
        return {"recommendations": "Recommendation generation not yet implemented"}

    async def _create_action_plan(self, recommendations: Dict[str, Any]) -> Dict[str, Any]:
        """Create action plan based on recommendations."""
        return {"plan": "Action plan creation not yet implemented"}

    def _calculate_error_frequency(self, errors_by_time: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate error frequency metrics."""
        return {"frequency": "Error frequency calculation not yet implemented"}

    def _analyze_error_trends(self, errors_by_time: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze error trends over time."""
        return {"trends": "Error trend analysis not yet implemented"}

    def _identify_common_sequences(self, error_sequences: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Identify common error sequences."""
        return [] 