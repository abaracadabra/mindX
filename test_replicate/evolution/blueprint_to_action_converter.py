# mindx/evolution/blueprint_to_action_converter.py
"""
BlueprintToActionConverter for MindX Strategic Evolution.

This converter takes high-level strategic blueprints from the BlueprintAgent
and converts them into detailed, executable BDI-compatible action sequences
with proper parameter extraction, dependency management, and validation steps.
"""

import json
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

from utils.config import Config
from utils.logging_config import get_logger
from core.belief_system import BeliefSystem, BeliefSource
from llm.llm_interface import LLMHandlerInterface
from agents.memory_agent import MemoryAgent

logger = get_logger(__name__)

@dataclass
class ActionDependency:
    """Represents a dependency between actions."""
    action_id: str
    depends_on: str
    dependency_type: str  # "sequential", "parallel", "conditional"
    condition: Optional[str] = None

@dataclass 
class ValidationCriteria:
    """Defines validation criteria for an action."""
    success_indicators: List[str]
    failure_indicators: List[str]
    timeout_seconds: int = 300
    rollback_required: bool = False

@dataclass
class DetailedAction:
    """Enhanced action with dependencies and validation."""
    id: str
    type: str
    description: str
    parameters: Dict[str, Any]
    dependencies: List[ActionDependency]
    validation: ValidationCriteria
    priority: int = 5
    estimated_cost_usd: float = 0.0
    estimated_duration_seconds: int = 60
    safety_level: str = "standard"  # "low", "standard", "high", "critical"

class BlueprintToActionConverter:
    """
    Converts high-level strategic blueprints into detailed, executable BDI action sequences
    with proper dependency management, validation, and safety controls.
    """
    
    def __init__(self,
                 llm_handler: LLMHandlerInterface,
                 memory_agent: MemoryAgent,
                 belief_system: BeliefSystem,
                 config: Optional[Config] = None):
        self.llm_handler = llm_handler
        self.memory_agent = memory_agent
        self.belief_system = belief_system
        self.config = config or Config()
        self.log_prefix = "BlueprintToActionConverter:"
        
        # Action type mappings for enhanced conversion
        self.action_type_mappings = {
            "system_analysis": ["ANALYZE_SYSTEM", "ANALYZE_PERFORMANCE", "ANALYZE_LOGS"],
            "code_improvement": ["GENERATE_CODE", "ANALYZE_CODE", "WRITE_FILE", "READ_FILE"],
            "tool_development": ["CREATE_TOOL", "TEST_TOOL", "REGISTER_TOOL"],
            "monitoring": ["SETUP_MONITORING", "CHECK_METRICS", "GENERATE_REPORT"],
            "economic_optimization": ["ANALYZE_COSTS", "OPTIMIZE_USAGE", "SET_BUDGET_LIMITS"],
            "safety_enhancement": ["CREATE_ROLLBACK_PLAN", "VALIDATE_CHANGES", "IMPLEMENT_SAFEGUARDS"]
        }
        
        logger.info(f"{self.log_prefix} Initialized with enhanced blueprint-to-action conversion capabilities")

    async def convert_blueprint_to_actions(self, blueprint: Dict[str, Any]) -> Tuple[bool, List[DetailedAction]]:
        """
        Convert a strategic blueprint into detailed, executable BDI actions.
        
        Args:
            blueprint: Strategic blueprint from BlueprintAgent
            
        Returns:
            Tuple of (success, list of DetailedAction objects)
        """
        try:
            logger.info(f"{self.log_prefix} Converting blueprint '{blueprint.get('blueprint_title', 'Unknown')}' to detailed actions")
            
            # Extract blueprint components
            focus_areas = blueprint.get("focus_areas", [])
            bdi_todo_list = blueprint.get("bdi_todo_list", [])
            kpis = blueprint.get("key_performance_indicators", [])
            risks = blueprint.get("potential_risks", [])
            
            # Generate detailed actions for each todo item
            detailed_actions = []
            action_counter = 0
            
            for todo_item in bdi_todo_list:
                action_counter += 1
                goal_description = todo_item.get("goal_description", "")
                priority = todo_item.get("priority", 5)
                target_component = todo_item.get("target_component", "general")
                
                # Use LLM to decompose high-level goal into detailed actions
                decomposed_actions = await self._decompose_goal_to_actions(
                    goal_description, target_component, priority, action_counter
                )
                
                if decomposed_actions:
                    detailed_actions.extend(decomposed_actions)
            
            # Add blueprint validation and monitoring actions
            validation_actions = await self._generate_validation_actions(blueprint, len(detailed_actions))
            detailed_actions.extend(validation_actions)
            
            # Optimize action dependencies and sequencing
            optimized_actions = await self._optimize_action_sequence(detailed_actions)
            
            # Save conversion results to memory
            await self._save_conversion_results(blueprint, optimized_actions)
            
            logger.info(f"{self.log_prefix} Successfully converted blueprint to {len(optimized_actions)} detailed actions")
            return True, optimized_actions
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to convert blueprint to actions: {e}", exc_info=True)
            return False, []

    async def _decompose_goal_to_actions(self, goal_description: str, target_component: str, 
                                       priority: int, sequence_id: int) -> List[DetailedAction]:
        """Use LLM to decompose a high-level goal into detailed BDI actions."""
        
        available_actions = [
            "ANALYZE_SYSTEM", "ANALYZE_CODE", "GENERATE_CODE", "WRITE_FILE", "READ_FILE",
            "LIST_FILES", "CREATE_DIRECTORY", "EXECUTE_BASH_COMMAND", "EXECUTE_LLM_BASH_TASK",
            "GET_CODING_SUGGESTIONS", "CREATE_ROLLBACK_PLAN", "VALIDATE_CHANGES",
            "SETUP_MONITORING", "CHECK_METRICS", "GENERATE_REPORT", "OPTIMIZE_COSTS"
        ]
        
        action_examples = {
            "ANALYZE_CODE": {"file_path": "path/to/file.py", "analysis_type": "quality"},
            "GENERATE_CODE": {"description": "Create a new function", "file_path": "path/to/file.py"},
            "WRITE_FILE": {"file_path": "path/to/file.py", "content": "code content"},
            "EXECUTE_BASH_COMMAND": {"command": "ls -la", "working_directory": "."}
        }
        
        prompt = f"""
You are an expert BDI action planner for the mindX system. Convert this high-level goal into a detailed sequence of BDI actions.

Goal: {goal_description}
Target Component: {target_component}  
Priority: {priority}
Sequence ID: {sequence_id}

Available Actions: {', '.join(available_actions)}

Example Action Formats: {json.dumps(action_examples, indent=2)}

Requirements:
1. Create 2-5 specific, executable actions that accomplish the goal
2. Include proper parameters for each action
3. Consider safety: add validation/rollback actions for risky operations
4. Estimate cost (0.0-5.0 USD) and duration (30-1800 seconds) for each action
5. Set safety level: "low", "standard", "high", or "critical"

Respond with a JSON array of action objects with these fields:
- id: unique action identifier
- type: action type from available actions
- description: clear description of what the action does
- parameters: dict of parameters for the action
- priority: 1-10 priority level
- estimated_cost_usd: estimated cost in USD
- estimated_duration_seconds: estimated duration
- safety_level: safety level string
- success_indicators: list of strings indicating success
- failure_indicators: list of strings indicating failure

Respond ONLY with the JSON array.
"""
        
        try:
            response = await self.llm_handler.generate_text(
                prompt=prompt,
                model=self.llm_handler.model_name_for_api,
                temperature=0.2,
                json_mode=True,
                max_tokens=2000
            )
            
            actions_data = json.loads(response)
            detailed_actions = []
            
            for i, action_data in enumerate(actions_data):
                # Create validation criteria
                validation = ValidationCriteria(
                    success_indicators=action_data.get("success_indicators", ["Operation completed"]),
                    failure_indicators=action_data.get("failure_indicators", ["Error occurred"]),
                    timeout_seconds=action_data.get("estimated_duration_seconds", 300) + 60,
                    rollback_required=action_data.get("safety_level") in ["high", "critical"]
                )
                
                # Create action with enhanced details
                detailed_action = DetailedAction(
                    id=action_data.get("id", f"action_{sequence_id}_{i}"),
                    type=action_data.get("type", "NO_OP"),
                    description=action_data.get("description", ""),
                    parameters=action_data.get("parameters", {}),
                    dependencies=[],  # Will be populated later
                    validation=validation,
                    priority=action_data.get("priority", priority),
                    estimated_cost_usd=action_data.get("estimated_cost_usd", 0.0),
                    estimated_duration_seconds=action_data.get("estimated_duration_seconds", 60),
                    safety_level=action_data.get("safety_level", "standard")
                )
                detailed_actions.append(detailed_action)
            
            return detailed_actions
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to decompose goal '{goal_description}': {e}")
            return []

    async def _generate_validation_actions(self, blueprint: Dict[str, Any], 
                                         action_count: int) -> List[DetailedAction]:
        """Generate blueprint-level validation and monitoring actions."""
        
        validation_actions = []
        
        # KPI monitoring action
        kpis = blueprint.get("key_performance_indicators", [])
        if kpis:
            kpi_action = DetailedAction(
                id=f"validate_kpis_{int(time.time())}",
                type="CHECK_METRICS",
                description=f"Monitor KPIs: {', '.join(kpis)}",
                parameters={"metrics": kpis, "monitoring_duration_hours": 24},
                dependencies=[],
                validation=ValidationCriteria(
                    success_indicators=["KPI metrics collected", "Performance improved"],
                    failure_indicators=["KPI metrics declined", "Performance degraded"],
                    timeout_seconds=300
                ),
                priority=8,
                estimated_cost_usd=0.1,
                estimated_duration_seconds=180,
                safety_level="standard"
            )
            validation_actions.append(kpi_action)
        
        # Risk mitigation action
        risks = blueprint.get("potential_risks", [])
        if risks:
            risk_action = DetailedAction(
                id=f"mitigate_risks_{int(time.time())}",
                type="CREATE_ROLLBACK_PLAN", 
                description=f"Create mitigation plan for risks: {', '.join(risks[:3])}",
                parameters={"risks": risks, "mitigation_strategy": "rollback_and_alert"},
                dependencies=[],
                validation=ValidationCriteria(
                    success_indicators=["Rollback plan created", "Risk mitigation active"],
                    failure_indicators=["Rollback plan failed", "Risk mitigation unavailable"],
                    timeout_seconds=300,
                    rollback_required=True
                ),
                priority=9,
                estimated_cost_usd=0.05,
                estimated_duration_seconds=120,
                safety_level="high"
            )
            validation_actions.append(risk_action)
        
        # Blueprint completion report
        report_action = DetailedAction(
            id=f"blueprint_report_{int(time.time())}",
            type="GENERATE_REPORT",
            description=f"Generate completion report for blueprint: {blueprint.get('blueprint_title', 'Unknown')}",
            parameters={
                "report_type": "blueprint_completion",
                "blueprint_title": blueprint.get("blueprint_title"),
                "actions_executed": action_count,
                "focus_areas": blueprint.get("focus_areas", [])
            },
            dependencies=[],
            validation=ValidationCriteria(
                success_indicators=["Report generated", "Blueprint status updated"],
                failure_indicators=["Report generation failed"],
                timeout_seconds=120
            ),
            priority=3,
            estimated_cost_usd=0.02,
            estimated_duration_seconds=60,
            safety_level="low"
        )
        validation_actions.append(report_action)
        
        return validation_actions

    async def _optimize_action_sequence(self, actions: List[DetailedAction]) -> List[DetailedAction]:
        """Optimize action sequencing and add proper dependencies."""
        
        # Sort by priority (higher priority first) and safety level
        safety_order = {"critical": 0, "high": 1, "standard": 2, "low": 3}
        
        optimized_actions = sorted(
            actions, 
            key=lambda a: (safety_order.get(a.safety_level, 2), -a.priority, a.estimated_duration_seconds)
        )
        
        # Add sequential dependencies for safety-critical actions
        for i, action in enumerate(optimized_actions):
            if action.safety_level in ["high", "critical"] and i > 0:
                # High-safety actions depend on previous action completion
                prev_action = optimized_actions[i-1] 
                dependency = ActionDependency(
                    action_id=action.id,
                    depends_on=prev_action.id,
                    dependency_type="sequential",
                    condition="previous_action_success"
                )
                action.dependencies.append(dependency)
        
        return optimized_actions

    async def _save_conversion_results(self, blueprint: Dict[str, Any], 
                                     actions: List[DetailedAction]) -> None:
        """Save conversion results to memory for tracking and analysis."""
        
        conversion_data = {
            "timestamp": time.time(),
            "blueprint_title": blueprint.get("blueprint_title", "Unknown"),
            "blueprint_version": blueprint.get("target_mindx_version_increment", "Unknown"),
            "actions_count": len(actions),
            "total_estimated_cost": sum(a.estimated_cost_usd for a in actions),
            "total_estimated_duration": sum(a.estimated_duration_seconds for a in actions),
            "safety_levels": {level: len([a for a in actions if a.safety_level == level]) 
                            for level in ["low", "standard", "high", "critical"]},
            "action_types": list(set(a.type for a in actions)),
            "conversion_id": str(uuid.uuid4())
        }
        
        # Save to memory agent
        await self.memory_agent.log_process(
            process_name="blueprint_to_action_conversion", 
            data=conversion_data,
            metadata={"agent_id": "blueprint_to_action_converter"}
        )
        
        # Save to belief system for future reference
        await self.belief_system.add_belief(
            key="evolution.blueprint_conversion.latest",
            value=conversion_data,
            confidence=0.9,
            source=BeliefSource.SELF_ANALYSIS,
            ttl_seconds=3600*24  # 24 hours
        )
        
        logger.info(f"{self.log_prefix} Saved conversion results: {len(actions)} actions, "
                   f"${conversion_data['total_estimated_cost']:.3f} estimated cost")

    def actions_to_bdi_format(self, actions: List[DetailedAction]) -> List[Dict[str, Any]]:
        """Convert DetailedAction objects to standard BDI action format."""
        
        bdi_actions = []
        for action in actions:
            bdi_action = {
                "type": action.type,
                "params": action.parameters.copy()
            }
            
            # Add metadata for BDI processing
            bdi_action["params"]["_meta"] = {
                "action_id": action.id,
                "description": action.description,
                "priority": action.priority,
                "estimated_cost_usd": action.estimated_cost_usd,
                "estimated_duration_seconds": action.estimated_duration_seconds,
                "safety_level": action.safety_level,
                "dependencies": [asdict(dep) for dep in action.dependencies],
                "validation": asdict(action.validation)
            }
            
            bdi_actions.append(bdi_action)
        
        return bdi_actions

    async def validate_action_sequence(self, actions: List[DetailedAction]) -> Tuple[bool, List[str]]:
        """Validate that the action sequence is safe and executable."""
        
        validation_errors = []
        
        # Check for circular dependencies
        action_ids = {action.id for action in actions}
        for action in actions:
            for dep in action.dependencies:
                if dep.depends_on not in action_ids:
                    validation_errors.append(f"Action {action.id} depends on non-existent action {dep.depends_on}")
        
        # Check cost limits
        total_cost = sum(a.estimated_cost_usd for a in actions)
        cost_limit = self.config.get("economic_controls.cost_per_improvement_limit_usd", 2.0)
        if total_cost > cost_limit:
            validation_errors.append(f"Total estimated cost ${total_cost:.3f} exceeds limit ${cost_limit:.3f}")
        
        # Check for required safety actions
        critical_actions = [a for a in actions if a.safety_level == "critical"]
        rollback_actions = [a for a in actions if "rollback" in a.type.lower() or "ROLLBACK" in a.type]
        
        if critical_actions and not rollback_actions:
            validation_errors.append("Critical actions present but no rollback actions found")
        
        is_valid = len(validation_errors) == 0
        return is_valid, validation_errors 