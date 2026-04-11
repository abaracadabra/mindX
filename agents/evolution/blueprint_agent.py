# mindx/evolution/blueprint_agent.py
"""
BlueprintAgent for MindX Strategic Evolution Planning.

This agent analyzes the current state of the mindX system, including its
cognitive resources (available LLMs), and uses its own LLM to propose a
strategic blueprint for the next iteration of MindX's self-improvement,
focusing on capability, resilience, and perpetuity.
"""
import logging
import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from agents.core.belief_system import BeliefSystem, BeliefSource
from llm.llm_interface import LLMHandlerInterface
from llm.model_registry import ModelRegistry, get_model_registry_async
from agents.orchestration.coordinator_agent import CoordinatorAgent, InteractionType
from agents.memory_agent import MemoryAgent
from agents.utility.base_gen_agent import BaseGenAgent

logger = get_logger(__name__)

class BlueprintAgent:
    """
    Generates a strategic blueprint for the next iteration of MindX's development
    and self-improvement capabilities.
    """
    _instance = None
    _lock = asyncio.Lock()

    def __init__(self,
                 belief_system: BeliefSystem,
                 coordinator_ref: CoordinatorAgent,
                 model_registry_ref: ModelRegistry,
                 memory_agent: MemoryAgent,
                 base_gen_agent: BaseGenAgent,
                 config_override: Optional[Config] = None,
                 test_mode: bool = False):
        
        if hasattr(self, '_initialized') and self._initialized and not test_mode:
            return

        self.config = config_override or Config()
        self.agent_id: str = self.config.get("evolution.blueprint_agent.agent_id", "blueprint_agent_mindx_v2")
        self.belief_system = belief_system
        self.coordinator_ref = coordinator_ref
        self.model_registry = model_registry_ref
        self.memory_agent = memory_agent
        self.base_gen_agent = base_gen_agent
        
        self.llm_handler: Optional[LLMHandlerInterface] = None
        try:
            self.llm_handler = self.model_registry.get_handler_for_purpose("reasoning")
        except Exception as e:
            logger.warning(f"BlueprintAgent '{self.agent_id}' model_registry handler failed: {e}")

        # Fallback: try Ollama handler directly if registry selection failed
        if not self.llm_handler:
            try:
                self.llm_handler = self.model_registry.get_handler("ollama")
            except Exception:
                pass

        if not self.llm_handler:
            logger.warning(f"BlueprintAgent '{self.agent_id}' could not acquire a reasoning LLM. Will retry on first use.")
        else:
            logger.info(f"BlueprintAgent '{self.agent_id}' initialized. Using LLM: {self.llm_handler.provider_name}/{self.llm_handler.model_name_for_api}")
        
        self._initialized = True

    async def _gather_mindx_system_state_summary(self) -> Dict[str, Any]:
        """Gathers a comprehensive summary of the current MindX system state for analysis."""
        summary = {"timestamp": time.time(), "mindx_version": self.config.get("system.version", "unknown")}

        # 1. Cognitive Resources from ModelRegistry
        summary["cognitive_resources"] = {
            "available_providers": self.model_registry.list_available_providers(),
            "available_models": list(self.model_registry.capabilities.keys())
        }

        # 2. Improvement Backlog from Coordinator
        backlog = self.coordinator_ref.improvement_backlog
        summary["improvement_backlog"] = {
            "total_items": len(backlog),
            "pending_items": len([item for item in backlog if item.get("status") == "PENDING"]),
            "recent_items": backlog[-5:]
        }

        # 3. Known Limitations from BeliefSystem
        conceptual_todos = await self.belief_system.query_beliefs(partial_key="mindx.system.known_limitation")
        summary["known_limitations_from_beliefs"] = [belief.value for _, belief in conceptual_todos[:5]]
        
        # 4. Recent Agent Actions from MemoryAgent
        try:
            trace_dir = self.memory_agent.process_trace_path
            recent_traces = sorted(trace_dir.glob("*.trace.json"), key=os.path.getmtime, reverse=True)
            summary["recent_agent_actions"] = []
            for trace_file in recent_traces[:10]:
                with open(trace_file, "r") as f:
                    trace_data = json.load(f)
                    summary["recent_agent_actions"].append({
                        "process": trace_data.get("process_name"),
                        "agent": trace_data.get("metadata", {}).get("agent_id"),
                        "timestamp": trace_data.get("timestamp_utc")
                    })
        except Exception as e:
            summary["recent_agent_actions"] = f"Error reading traces: {e}"

        # 5. Codebase Snapshot from BaseGenAgent
        try:
            codebase_report = self.base_gen_agent.generate_markdown_summary(root_path_str=str(PROJECT_ROOT))
            if codebase_report["status"] == "SUCCESS":
                summary["codebase_snapshot_path"] = codebase_report["output_file"]
            else:
                summary["codebase_snapshot_path"] = f"Error: {codebase_report['message']}"
        except Exception as e:
            summary["codebase_snapshot_path"] = f"Error generating codebase snapshot: {e}"

        return summary

    async def generate_next_evolution_blueprint(self, context_override: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Generates a blueprint for the next self-improvement iteration of MindX.
        Returns blueprint dict on success, None on failure (never raises).
        context_override may include mindx_sh_commands and agent_authority_list from mindXagent.
        """
        logger.info(f"{self.agent_id}: Generating next evolution blueprint...")

        # Heuristic fallback: if no LLM, build blueprint from coordinator backlog
        if not self.llm_handler:
            logger.warning(f"{self.agent_id}: No LLM — generating heuristic blueprint from backlog")
            return self._heuristic_blueprint()

        system_state = await self._gather_mindx_system_state_summary()
        if context_override:
            system_state.update(context_override)

        prompt = (
            f"You are a Chief Architect AI for the MindX Self-Improving System (Project Chimaiera).\n"
            f"Your philosophical goals are **Resilience** and **Perpetuity**.\n"
            f"Analyze the current system state and define a strategic blueprint for the NEXT evolution.\n"
            f"Current MindX System State:\n{json.dumps(system_state, indent=2, default=str)}\n\n"
            "**Blueprint Requirements:**\n"
            "1. Identify 2-3 strategic **Focus Areas**.\n"
            "2. For each Focus Area, define 1-3 specific, actionable **Development Goals**.\n"
            "3. Based on these goals, create a `bdi_todo_list`: a JSON list of objects, where each object has 'goal_description' and 'priority' keys.\n"
            "4. Propose 1-2 **Key Performance Indicators (KPIs)** to measure success.\n"
            "5. Note any **Potential Risks**.\n\n"
            "Respond ONLY with a single, valid JSON object with keys: 'blueprint_title', 'target_mindx_version_increment', 'focus_areas', 'bdi_todo_list', 'key_performance_indicators', 'potential_risks'."
        )

        blueprint = None
        try:
            response_str = await self.llm_handler.generate_text(
                prompt, model=self.llm_handler.model_name_for_api,
                max_tokens=4000, temperature=0.2, json_mode=True
            )

            if not response_str or "error" in str(response_str).lower()[:50]:
                logger.warning(f"{self.agent_id}: LLM returned empty/error — using heuristic blueprint")
                blueprint = self._heuristic_blueprint()
            else:
                try:
                    blueprint = json.loads(response_str)
                except json.JSONDecodeError:
                    logger.warning(f"{self.agent_id}: LLM returned invalid JSON — using heuristic blueprint")
                    blueprint = self._heuristic_blueprint()

            # Validate essential keys — if missing, use heuristic
            if blueprint and not all(k in blueprint for k in ["blueprint_title", "focus_areas", "bdi_todo_list"]):
                logger.warning(f"{self.agent_id}: Blueprint missing essential keys — using heuristic")
                blueprint = self._heuristic_blueprint()

        except Exception as e:
            logger.warning(f"{self.agent_id}: Blueprint generation error: {e} — using heuristic")
            blueprint = self._heuristic_blueprint()

        if not blueprint:
            return None

        # Store in belief system
        try:
            logger.info(f"{self.agent_id}: Blueprint generated: '{blueprint.get('blueprint_title', 'untitled')}'")
            await self.belief_system.add_belief(
                "mindx.evolution.blueprint.latest", blueprint, 0.95, BeliefSource.SELF_ANALYSIS,
                metadata={"generated_at": time.time()}
            )
        except Exception:
            pass

        # Log to memory_agent
        if self.memory_agent:
            try:
                await self.memory_agent.log_process(
                    "blueprint_generated",
                    {"title": blueprint.get("blueprint_title", ""), "todos": len(blueprint.get("bdi_todo_list", []))},
                    {"agent_id": self.agent_id, "domain": "evolution.blueprint"}
                )
            except Exception:
                pass

        # Add todos to coordinator backlog (non-blocking — errors don't fail the blueprint)
        try:
            bdi_todos = blueprint.get("bdi_todo_list", [])
            for todo in bdi_todos[:5]:  # Limit to 5 todos per blueprint to prevent backlog flooding
                if isinstance(todo, dict) and "goal_description" in todo:
                    await self.coordinator_ref.handle_user_input(
                        content=todo["goal_description"],
                        user_id=self.agent_id,
                        interaction_type=InteractionType.COMPONENT_IMPROVEMENT,
                        metadata={
                            "source": "blueprint_agent",
                            "priority": todo.get("priority", 5),
                            "target_component": todo.get("target_component", "general")
                        }
                    )
        except Exception as e:
            logger.debug(f"{self.agent_id}: Error adding todos to backlog: {e}")

        return blueprint

    def _heuristic_blueprint(self) -> Dict[str, Any]:
        """Generate a blueprint from coordinator backlog when LLM is unavailable.
        Blueprint agent emerged as a solution — this ensures it works even without inference."""
        backlog = []
        try:
            backlog = self.coordinator_ref.improvement_backlog[:5]
        except Exception:
            pass

        todos = []
        for item in backlog:
            desc = item.get("description", item.get("suggestion", str(item)))[:200]
            todos.append({"goal_description": desc, "priority": item.get("priority", 5)})

        if not todos:
            todos = [{"goal_description": "Review system health and identify improvement opportunities", "priority": 5}]

        return {
            "blueprint_title": "Heuristic Blueprint (from improvement backlog)",
            "target_mindx_version_increment": "0.0.1",
            "focus_areas": ["System Resilience", "Continuous Improvement"],
            "bdi_todo_list": todos,
            "key_performance_indicators": ["Improvement cycle completion rate"],
            "potential_risks": ["Operating without LLM-driven strategic planning"],
            "source": "heuristic",
        }

# Factory function to get the singleton instance
async def get_blueprint_agent_async(
    belief_system: BeliefSystem, 
    coordinator_ref: CoordinatorAgent,
    model_registry_ref: ModelRegistry,
    config_override: Optional[Config] = None, 
    test_mode: bool = False
) -> BlueprintAgent:
    async with BlueprintAgent._lock:
        if not BlueprintAgent._instance or test_mode:
            BlueprintAgent._instance = BlueprintAgent(
                belief_system=belief_system, 
                coordinator_ref=coordinator_ref,
                model_registry_ref=model_registry_ref,
                config_override=config_override, 
                test_mode=test_mode)
    return BlueprintAgent._instance
