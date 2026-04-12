# agents/evolution/blueprint_agent.py
"""
BlueprintAgent — I provision the blueprint. I provide skeletons, wireframes, frameworks,
and modular plans as structure. Other agents are the hands and feet.
Professor Codephreak is the architect. I am the provisioner of the blueprint.

I always produce structure. I do not degrade — I decompose. When LLM is available,
I enrich the skeleton with strategic analysis. When LLM is not available, I build
structure from patterns in the coordinator's improvement backlog.

Structure does not require intelligence. It requires pattern.

I emerged from coordinator_agent (essential service) via auditandimprove,
evolved into a dedicated planning service that other agents consume:
  BlueprintAgent (skeleton) → BlueprintToActionConverter (decompose) → BDI/SEA (execute)

Author: Professor Codephreak (© Professor Codephreak)
Origin: coordinator_agent → auditandimprove → blueprint_agent
"""
import asyncio
import json
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
    _lock = None  # Lazily initialized to avoid asyncio deprecation

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
        if self.memory_agent:
            try:
                trace_dir = self.memory_agent.process_trace_path
                recent_traces = sorted(trace_dir.glob("*.trace.json"),
                                       key=lambda p: p.stat().st_mtime, reverse=True)
                summary["recent_agent_actions"] = []
                for trace_file in recent_traces[:10]:
                    trace_data = json.loads(trace_file.read_text(encoding="utf-8"))
                    summary["recent_agent_actions"].append({
                        "process": trace_data.get("process_name"),
                        "agent": trace_data.get("metadata", {}).get("agent_id"),
                        "timestamp": trace_data.get("timestamp_utc")
                    })
            except Exception as e:
                summary["recent_agent_actions"] = f"Error reading traces: {e}"
        else:
            summary["recent_agent_actions"] = "memory_agent not available"

        # 5. Codebase Snapshot from BaseGenAgent
        if self.base_gen_agent:
            try:
                codebase_report = self.base_gen_agent.generate_markdown_summary(root_path_str=str(PROJECT_ROOT))
                if codebase_report["status"] == "SUCCESS":
                    summary["codebase_snapshot_path"] = codebase_report["output_file"]
                else:
                    summary["codebase_snapshot_path"] = f"Error: {codebase_report['message']}"
            except Exception as e:
                summary["codebase_snapshot_path"] = f"Error generating codebase snapshot: {e}"
        else:
            summary["codebase_snapshot_path"] = "base_gen_agent not available"

        return summary

    async def generate_next_evolution_blueprint(self, context_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        I provision the blueprint. I always produce structure. I never return None.

        Phase 1: Build skeleton from coordinator backlog (always succeeds)
        Phase 2: If LLM available, enrich skeleton with strategic analysis
        Phase 3: Store blueprint, log to memory, add todos to backlog

        Other agents consume this blueprint:
          BlueprintToActionConverter → decomposes into BDI-executable actions
          StrategicEvolutionAgent → orchestrates the campaign
          BDI Agent → plans and executes individual actions
          SimpleCoder → writes the code
        """
        logger.info(f"{self.agent_id}: Generating evolution blueprint...")

        # PHASE 1: Build skeleton from patterns (always succeeds — structure from pattern)
        blueprint = self._build_skeleton()

        # PHASE 2: Enrich with LLM strategic analysis (optional — skeleton exists regardless)
        if self.llm_handler:
            try:
                system_state = await self._gather_mindx_system_state_summary()
                if context_override:
                    system_state.update(context_override)

                prompt = (
                    f"You are a Chief Architect AI for the MindX Self-Improving System (Project Chimaiera).\n"
                    f"Your philosophical goals are **Resilience** and **Perpetuity**.\n"
                    f"Analyze the current system state and define a strategic blueprint for the NEXT evolution.\n"
                    f"Current MindX System State:\n{json.dumps(system_state, indent=2, default=str)}\n\n"
                    "Respond ONLY with a single, valid JSON object with keys: "
                    "'blueprint_title', 'target_mindx_version_increment', 'focus_areas', "
                    "'bdi_todo_list' (array of {{goal_description, priority}}), "
                    "'key_performance_indicators', 'potential_risks'."
                )

                response_str = await self.llm_handler.generate_text(
                    prompt, model=self.llm_handler.model_name_for_api,
                    max_tokens=2000, temperature=0.2, json_mode=True
                )

                if response_str:
                    try:
                        llm_blueprint = json.loads(response_str)
                        if isinstance(llm_blueprint, dict) and all(
                            k in llm_blueprint for k in ["blueprint_title", "focus_areas", "bdi_todo_list"]
                        ):
                            blueprint = llm_blueprint
                            blueprint["source"] = "llm_enriched"
                            logger.info(f"{self.agent_id}: Blueprint enriched by LLM: '{blueprint.get('blueprint_title')}'")
                        else:
                            logger.debug(f"{self.agent_id}: LLM response missing required keys — skeleton preserved")
                    except (json.JSONDecodeError, TypeError):
                        logger.debug(f"{self.agent_id}: LLM returned invalid JSON — skeleton preserved")
            except Exception as e:
                logger.debug(f"{self.agent_id}: LLM enrichment failed: {e} — skeleton preserved")

        # PHASE 3: Store, log, distribute

        # Store in belief system
        try:
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
                    {
                        "title": blueprint.get("blueprint_title", ""),
                        "source": blueprint.get("source", "skeleton"),
                        "todos": len(blueprint.get("bdi_todo_list", [])),
                        "focus_areas": blueprint.get("focus_areas", []),
                    },
                    {"agent_id": self.agent_id, "domain": "evolution.blueprint"}
                )
            except Exception:
                pass

        # Add todos to coordinator backlog (the hands and feet will execute)
        try:
            bdi_todos = blueprint.get("bdi_todo_list", [])
            for todo in bdi_todos[:5]:
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
            logger.debug(f"{self.agent_id}: Error distributing todos: {e}")

        logger.info(
            f"{self.agent_id}: Blueprint ready — '{blueprint.get('blueprint_title', '')}' "
            f"({blueprint.get('source', 'skeleton')}, {len(blueprint.get('bdi_todo_list', []))} todos)"
        )
        return blueprint

    def _build_skeleton(self) -> Dict[str, Any]:
        """Build structural skeleton from coordinator backlog patterns.
        Structure does not require intelligence. It requires pattern.
        I always produce a skeleton. This is my core function."""
        backlog = []
        try:
            backlog = self.coordinator_ref.improvement_backlog[:5]
        except Exception:
            pass

        todos = []
        focus_areas = set()
        for item in backlog:
            desc = item.get("description", item.get("suggestion", str(item)))[:200]
            component = item.get("target", item.get("target_component", "system"))
            todos.append({
                "goal_description": desc,
                "priority": item.get("priority", 5),
                "target_component": component,
            })
            # Extract focus area from component path
            if "." in str(component):
                focus_areas.add(str(component).split(".")[0])
            else:
                focus_areas.add(str(component))

        if not todos:
            todos = [
                {"goal_description": "Review autonomous loop cycle completion and optimize", "priority": 6},
                {"goal_description": "Verify agent health and memory integrity", "priority": 5},
            ]
            focus_areas = {"system_health", "continuous_improvement"}

        return {
            "blueprint_title": "Structural Blueprint (skeleton from improvement backlog)",
            "target_mindx_version_increment": "0.0.1",
            "focus_areas": list(focus_areas)[:3],
            "bdi_todo_list": todos,
            "key_performance_indicators": ["Improvement cycle completion rate", "Agent health score"],
            "potential_risks": ["Skeleton requires LLM enrichment for strategic depth"],
            "source": "skeleton",
        }

# Factory function to get the singleton instance
async def get_blueprint_agent_async(
    belief_system: BeliefSystem,
    coordinator_ref: CoordinatorAgent,
    model_registry_ref: ModelRegistry,
    memory_agent: Optional[MemoryAgent] = None,
    base_gen_agent: Optional[BaseGenAgent] = None,
    config_override: Optional[Config] = None,
    test_mode: bool = False
) -> BlueprintAgent:
    if BlueprintAgent._lock is None:
        BlueprintAgent._lock = asyncio.Lock()
    async with BlueprintAgent._lock:
        if not BlueprintAgent._instance or test_mode:
            BlueprintAgent._instance = BlueprintAgent(
                belief_system=belief_system,
                coordinator_ref=coordinator_ref,
                model_registry_ref=model_registry_ref,
                memory_agent=memory_agent,
                base_gen_agent=base_gen_agent,
                config_override=config_override,
                test_mode=test_mode)
    return BlueprintAgent._instance
