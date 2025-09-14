# mindx/tools/system_analyzer_tool.py
"""
SystemAnalyzerTool for the MindX Strategic Evolution Agent.

This tool performs holistic analysis of the MindX system's state, including
codebase structure, performance metrics, resource usage, and improvement backlogs,
to generate actionable insights and improvement suggestions.
"""

import json
from typing import Dict, Any, Optional

from utils.config import Config
from utils.logging_config import get_logger
from core.belief_system import BeliefSystem
from llm.llm_interface import LLMHandlerInterface
from llm.model_selector import ModelSelector
from orchestration.coordinator_agent import CoordinatorAgent

logger = get_logger(__name__)

class SystemAnalyzerTool:
    """
    A specialized tool for analyzing the overall state of the MindX system.
    """
    def __init__(self,
                 belief_system: BeliefSystem,
                 llm_handler: LLMHandlerInterface,
                 coordinator_ref: CoordinatorAgent, # FIXED: Now takes coordinator_ref
                 model_selector: Optional[ModelSelector] = None,
                 config: Optional[Config] = None):
        """
        Initializes the SystemAnalyzerTool.

        Args:
            belief_system: The shared BeliefSystem.
            llm_handler: The primary LLM handler for analysis.
            coordinator_ref: A reference to the live CoordinatorAgent to access monitors and backlogs.
            model_selector: (Optional) For selecting specialized models for sub-tasks.
            config: The system configuration object.
        """
        self.belief_system = belief_system
        self.llm_handler = llm_handler
        self.coordinator_ref = coordinator_ref
        self.model_selector = model_selector
        self.config = config or Config()
        self.log_prefix = "SystemAnalyzerTool:"
        
        # Monitors are now accessed via the coordinator reference
        self.performance_monitor = self.coordinator_ref.performance_monitor
        self.resource_monitor = self.coordinator_ref.resource_monitor
        
        logger.info(f"{self.log_prefix} Initialized with integrated monitoring capabilities via Coordinator.")

    async def execute(self, analysis_focus_hint: Optional[str] = None) -> Dict[str, Any]:
        return await self.analyze_system_for_improvements(analysis_focus_hint)

    async def analyze_system_for_improvements(self, analysis_focus_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Performs a comprehensive system analysis and generates improvement suggestions.
        """
        logger.info(f"{self.log_prefix} Starting comprehensive system analysis. Focus: {analysis_focus_hint or 'General'}")
        
        # 1. Gather data from all relevant sources
        system_state = {
            "performance_metrics": self.performance_monitor.get_all_metrics() if self.performance_monitor else {},
            "resource_usage": self.resource_monitor.get_resource_usage() if self.resource_monitor else {},
            "improvement_backlog": self.coordinator_ref.improvement_backlog[:10], # Get top 10 backlog items
            "recent_campaign_history": self.coordinator_ref.improvement_campaign_history[-5:] # Get last 5 campaigns
        }

        # 2. Formulate a prompt for the LLM to analyze the state
        prompt = (
            "You are a Senior Systems Architect AI analyzing the MindX self-improving system.\n"
            "Your goal is to identify the most impactful areas for improvement based on the following system snapshot.\n\n"
            f"**System State Snapshot:**\n```json\n{json.dumps(system_state, indent=2, default=str)}\n```\n\n"
        )
        if analysis_focus_hint:
            prompt += f"**Specific Analysis Focus:** {analysis_focus_hint}\n\n"
        
        prompt += (
            "**Analysis Task:**\n"
            "1. Synthesize the provided data to identify key patterns, bottlenecks, or recurring failures.\n"
            "2. Propose 2-4 concrete, high-priority 'improvement_suggestions'.\n"
            "3. For each suggestion, provide a 'target_component_path', a 'suggestion' (clear description of the change), a 'justification' (why it's important), and a 'priority' (integer 1-10).\n\n"
            "Respond ONLY with a single JSON object containing the key 'improvement_suggestions', which holds a list of your suggestion objects."
        )

        # 3. Use the LLM to generate insights
        try:
            response_str = await self.llm_handler.generate_text(
                prompt,
                model=self.llm_handler.model_name_for_api,
                max_tokens=2000,
                temperature=0.2,
                json_mode=True
            )
            if not response_str:
                 raise ValueError(f"Analysis LLM returned empty response")

            analysis_result = json.loads(response_str)
            
            # Check if the result has the expected structure
            if "improvement_suggestions" not in analysis_result:
                raise ValueError(f"Analysis LLM response missing 'improvement_suggestions': {response_str}")
            logger.info(f"{self.log_prefix} Successfully generated {len(analysis_result.get('improvement_suggestions', []))} improvement suggestions.")
            return analysis_result

        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to perform system analysis: {e}", exc_info=True)
            return {"error": str(e), "improvement_suggestions": []}
