# tests/integration/test_mastermind_evolve_e2e.py
"""
End-to-End (E2E) test for the MastermindAgent's `evolve` command.

This test validates the entire cognitive-evolutionary loop against a LIVE
Large Language Model (Google Gemini). It verifies that the agent can correctly:
1. Receive a strategic directive.
2. Formulate a valid plan using a real LLM.
3. Execute the plan using its tools to interact with the filesystem.
4. Successfully complete its goal.

WARNING: This test makes real API calls and will incur costs.
It requires a valid GEMINI_API_KEY in the .env file.
"""
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from pytest_asyncio import fixture as pytest_asyncio_fixture

# Import the core components
from orchestration.mastermind_agent import MastermindAgent
from orchestration.coordinator_agent import CoordinatorAgent

# Use pytest-asyncio to handle async test functions
pytestmark = pytest.mark.asyncio

@pytest_asyncio_fixture
async def live_mastermind_agent_instance() -> MastermindAgent:
    """
    Sets up a fully-initialized MastermindAgent instance for testing.
    This fixture allows the agent to create a REAL LLM handler.
    """
    # We only mock the coordinator to prevent it from interfering with other systems.
    mock_coordinator = MagicMock(spec=CoordinatorAgent)
    
    # These are the custom, high-level actions the Mastermind's BDI agent can perform.
    # In a live test, the BDI agent will call the real implementations of these methods.
    custom_handlers = {
        "ASSESS_TOOL_SUITE_EFFECTIVENESS": MastermindAgent._bdi_action_assess_tool_suite,
        "PROPOSE_TOOL_STRATEGY": MastermindAgent._bdi_action_propose_tool_strategy,
        "CONCEPTUALIZE_NEW_TOOL": MastermindAgent._bdi_action_conceptualize_new_tool
    }
    
    # Get a clean instance of the Mastermind, allowing it to initialize its own dependencies,
    # including the live LLM handlers.
    mastermind = await MastermindAgent.get_instance(
        test_mode=True,
        coordinator_agent_instance=mock_coordinator,
        extra_bdi_action_handlers=custom_handlers
    )
    return mastermind

@pytest.mark.timeout(180) # 3 minutes timeout for real network calls
async def test_evolve_command_with_live_llm(live_mastermind_agent_instance: MastermindAgent):
    """
    GIVEN a Mastermind agent with a live connection to the Gemini LLM
    WHEN the `evolve` command is run with a directive to create a new tool
    THEN the agent should complete the campaign successfully by taking an appropriate
    action, such as writing a placeholder code file for the new tool.
    """
    # ARRANGE
    mastermind = live_mastermind_agent_instance
    directive = "Our system currently lacks the ability to generate QR codes. Analyze this gap and create a new tool file named 'QRCodeGenerator.py' to address it. The tool should be a basic placeholder."

    # Define the expected output path within the agent's sandboxed workspace
    # We access the tool via the BDI agent to get its configured sandbox root
    simple_coder_tool = mastermind.bdi_agent.available_tools.get('simple_coder')
    assert simple_coder_tool is not None, "SimpleCoder tool must be initialized."
    sandbox_path = simple_coder_tool.sandbox_root
    expected_file_path = sandbox_path / "QRCodeGenerator.py"

    # Ensure the file doesn't exist before the test for a clean run
    if expected_file_path.exists():
        expected_file_path.unlink()

    # ACT
    campaign_result = await mastermind.manage_mindx_evolution(top_level_directive=directive)

    # ASSERT
    
    # 1. Assert the overall campaign was successful.
    assert campaign_result is not None
    assert campaign_result.get("overall_campaign_status") == "SUCCESS", \
        f"The overall campaign should succeed. Final BDI message: {campaign_result.get('final_bdi_message')}"

    bdi_status = mastermind.bdi_agent.get_status().get('status')
    assert bdi_status == "COMPLETED_GOAL_ACHIEVED", \
        f"BDI agent should achieve its goal, but status was {bdi_status}"

    # 2. Verify the real-world outcome: the file was created.
    # This is the most important check.
    assert expected_file_path.exists(), \
        f"The agent should have created the file at {expected_file_path}"
    
    # 3. (Optional but good) Verify the content of the file to ensure it's not empty
    content = expected_file_path.read_text()
    assert len(content) > 10, "The created file should have some placeholder content."
    assert "qrcode" in content.lower() or "qr code" in content.lower(), \
        "File content should be related to QR code generation."

    # 4. Clean up the created file after a successful test
    if expected_file_path.exists():
        expected_file_path.unlink()
