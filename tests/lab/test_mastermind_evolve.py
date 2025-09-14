# tests/integration/test_mastermind_evolve.py (Corrected Version)

import pytest
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

# Add project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from pytest_asyncio import fixture as pytest_asyncio_fixture

# Import the core components to be tested and mocked
from orchestration.mastermind_agent import MastermindAgent
from llm.llm_interface import LLMHandlerInterface
from core.bdi_agent import BDIAgent
from orchestration.coordinator_agent import CoordinatorAgent

# Use pytest-asyncio to handle async test functions
pytestmark = pytest.mark.asyncio

# --- Mock LLM Responses ---

MOCK_PLAN_RESPONSE = json.dumps([
    {"type": "ASSESS_TOOL_SUITE_EFFECTIVENESS", "params": {}},
    {"type": "PROPOSE_TOOL_STRATEGY", "params": {"assessment_belief_key": "assessment.tool_suite.latest"}},
    {"type": "CONCEPTUALIZE_NEW_TOOL", "params": {"strategic_proposal_belief_key": "strategy.tool_proposal.latest"}}
])

MOCK_ASSESSMENT_RESPONSE = json.dumps({
    "overall_assessment": "The current tool suite is minimal and lacks specialized capabilities for data generation or encoding.",
    "identified_gaps": ["No tool for generating standardized data formats like QR codes."]
})

MOCK_STRATEGY_RESPONSE = json.dumps({
    "recommendations": [{
        "action": "CONCEPTUALIZE_NEW_TOOL",
        "target": "QR Code Generation",
        "justification": "Fulfills the identified gap for data encoding."
    }]
})

# ** FIX APPLIED HERE: The mock response now includes all required keys. **
MOCK_CONCEPT_RESPONSE = json.dumps({
    "tool_id": "qr_code_generator_v1",
    "display_name": "QR Code Generator",
    "description": "A tool to generate QR code images from a given text string or URL.",
    "module_path": "tools.media.qr_generator",
    "class_name": "QRCodeGeneratorTool",
    "capabilities": [{
        "name": "generate_qr_code",
        "description": "Takes a string and saves a QR code image to a specified file path.",
        "input_schema": {"type": "object", "properties": {"text_data": {"type": "string"}, "output_path": {"type": "string"}}, "required": ["text_data", "output_path"]},
        "output_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "size_bytes": {"type": "integer"}}}
    }],
    # --- ADDED MISSING KEYS ---
    "needs_identity": False,
    "initial_version": "0.1.0",
    "initial_status": "conceptual",
    "prompt_template_for_llm_interaction": "Generate a QR code for the following data: {{text_data}}",
    "metadata": {
        "author": "mindX_augmentic_intelligence",
        "tags": ["media", "generator", "qr_code"]
    }
})

@pytest_asyncio_fixture
def mock_llm_handler() -> MagicMock:
    """Creates a mock LLM handler that returns predefined responses based on the prompt."""
    handler = MagicMock(spec=LLMHandlerInterface)
    
    async def side_effect_func(prompt: str, **kwargs):
        if "Generate a sequence of actions (a plan)" in prompt:
            return MOCK_PLAN_RESPONSE
        elif "Assess the current tool suite's effectiveness" in prompt:
            return MOCK_ASSESSMENT_RESPONSE
        elif "propose a list of concrete strategic actions" in prompt:
            return MOCK_STRATEGY_RESPONSE
        elif "Conceptualize a new tool" in prompt:
            return MOCK_CONCEPT_RESPONSE
        return "{}" # Fallback

    handler.generate_text = AsyncMock(side_effect=side_effect_func)
    handler.provider_name = "mock_provider"
    handler.model_name_for_api = "mock-model"
    return handler

@pytest_asyncio_fixture
async def mastermind_agent_instance(mock_llm_handler: MagicMock) -> MastermindAgent:
    """Sets up a MastermindAgent instance, injecting our mock LLM handler."""
    with patch('orchestration.mastermind_agent.create_llm_handler', return_value=mock_llm_handler):
        with patch('core.bdi_agent.create_llm_handler', return_value=mock_llm_handler):
            mock_coordinator = MagicMock(spec=CoordinatorAgent)
            custom_handlers = {
                "ASSESS_TOOL_SUITE_EFFECTIVENESS": MastermindAgent._bdi_action_assess_tool_suite,
                "PROPOSE_TOOL_STRATEGY": MastermindAgent._bdi_action_propose_tool_strategy,
                "CONCEPTUALIZE_NEW_TOOL": MastermindAgent._bdi_action_conceptualize_new_tool
            }
            mastermind = await MastermindAgent.get_instance(
                test_mode=True,
                coordinator_agent_instance=mock_coordinator,
                extra_bdi_action_handlers=custom_handlers
            )
            return mastermind

async def test_evolve_command_conceptualizes_new_tool(mastermind_agent_instance: MastermindAgent):
    """
    GIVEN a Mastermind agent with a mocked LLM
    WHEN the `evolve` command is run with a directive to create a new tool
    THEN the agent should complete a campaign successfully and store the new tool concept.
    """
    # ARRANGE
    mastermind = mastermind_agent_instance
    directive = "analyze the current tool suite for capability gaps and conceptualize a new tool to generate QR codes"

    # ACT
    campaign_result = await mastermind.manage_mindx_evolution(top_level_directive=directive)

    # ASSERT
    
    # 1. Assert the overall campaign was successful
    assert campaign_result is not None
    assert campaign_result.get("overall_campaign_status") == "SUCCESS", "The overall campaign should succeed."

    # 2. Assert the BDI agent reached its goal
    bdi_status = mastermind.bdi_agent.get_status().get('status')
    assert bdi_status == "COMPLETED_GOAL_ACHIEVED", f"BDI agent should achieve its goal, but status was {bdi_status}"

    # 3. Assert that the final concept was correctly stored in the belief system
    final_concept_belief = await mastermind.belief_system.get_belief(
        f"mindx.new_tool_concept.qr_code_generator_v1"
    )

    assert final_concept_belief is not None, "The final tool concept should be stored as a belief."
    final_concept_data = final_concept_belief.value
    assert final_concept_data["tool_id"] == "qr_code_generator_v1"
    assert "generate_qr_code" in [cap["name"] for cap in final_concept_data["capabilities"]]
