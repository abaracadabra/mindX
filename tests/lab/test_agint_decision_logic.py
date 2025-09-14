# tests/core/test_agint_decision_logic.py
"""
Unit test for the AGInt's rule-based decision logic.

This test validates that the AGInt's cognitive core makes the correct,
deterministic strategic decisions based on its perceived state, without
relying on a live LLM or a full BDI run.
"""
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from pytest_asyncio import fixture as pytest_asyncio_fixture

# Import the components to be tested and mocked
from core.agint import AGInt, DecisionType
from core.bdi_agent import BDIAgent
from core.belief_system import BeliefSystem
from llm.model_registry import ModelRegistry
from utils.config import Config

# Use pytest-asyncio to handle async test functions
pytestmark = pytest.mark.asyncio

@pytest_asyncio_fixture
def mock_dependencies() -> dict:
    """Provides a dictionary of mocked dependencies required by AGInt."""
    return {
        "bdi_agent": MagicMock(spec=BDIAgent),
        "model_registry": MagicMock(spec=ModelRegistry),
        "memory_agent": None, # We don't need a memory agent for this unit test
        "web_search_tool": None,
        "coordinator_agent": None,
    }

@pytest_asyncio_fixture
def agint_instance(mock_dependencies: dict) -> AGInt:
    """Creates a clean instance of the AGInt for each test."""
    config = Config(test_mode=True)
    
    # Mock the IDManagerAgent creation to avoid the initialization error
    with patch('core.id_manager_agent.IDManagerAgent') as mock_id_manager_class:
        mock_id_manager = MagicMock()
        mock_id_manager.create_new_wallet = MagicMock()
        mock_id_manager_class.return_value = mock_id_manager
        
        agint = AGInt(
            agent_id="test_agint",
            bdi_agent=mock_dependencies["bdi_agent"],
            model_registry=mock_dependencies["model_registry"],
            config=config
        )
    
    # The test will focus on the _decide_rule_based method, so we set a default directive
    agint.primary_directive = "Test directive"
    return agint

async def test_agint_chooses_self_repair_when_llm_is_not_operational(agint_instance: AGInt):
    """
    GIVEN an AGInt whose state summary indicates the LLM is not operational
    WHEN the AGInt makes a decision
    THEN the chosen decision MUST be SELF_REPAIR.
    """
    # ARRANGE
    agint = agint_instance
    agint.state_summary["llm_operational"] = False # Simulate LLM failure
    
    empty_perception = {} # No other perception data is needed for this rule

    # ACT
    decision = await agint._decide_rule_based(empty_perception)

    # ASSERT
    assert decision == DecisionType.SELF_REPAIR, \
        "When LLM is not operational, the only valid decision is SELF_REPAIR."

async def test_agint_chooses_research_after_a_failure(agint_instance: AGInt):
    """
    GIVEN an AGInt that perceives its last action has failed
    WHEN the AGInt makes a decision
    THEN the chosen decision MUST be RESEARCH.
    """
    # ARRANGE
    agint = agint_instance
    agint.state_summary["llm_operational"] = True # Ensure system health is OK

    # Simulate the perception of a prior failure
    perception_with_failure = {
        "last_action_failure_context": {
            "error": "BDI_TASK_FAILED",
            "details": "Subordinate task failed for some reason."
        }
    }

    # ACT
    decision = await agint._decide_rule_based(perception_with_failure)

    # ASSERT
    assert decision == DecisionType.RESEARCH, \
        "After any failure, the next logical decision must be RESEARCH to re-evaluate."

async def test_agint_chooses_bdi_delegation_when_healthy_and_no_failures(agint_instance: AGInt):
    """
    GIVEN a healthy AGint with no perception of recent failures
    WHEN the AGInt makes a decision
    THEN the chosen decision MUST be BDI_DELEGATION to pursue its directive.
    """
    # ARRANGE
    agint = agint_instance
    agint.state_summary["llm_operational"] = True # Ensure system health is OK
    
    # A clean perception with no failure context
    healthy_perception = {} 

    # ACT
    decision = await agint._decide_rule_based(healthy_perception)

    # ASSERT
    assert decision == DecisionType.BDI_DELEGATION, \
        "In a nominal state, the default action should be BDI_DELEGATION to make progress."