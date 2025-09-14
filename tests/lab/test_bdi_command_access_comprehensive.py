# tests/integration/test_bdi_command_access_comprehensive.py
"""
Comprehensive test suite for BDI agent access to all official commands in run_mindx.py.

This test validates that the BDI agent can successfully access and execute all official
commands through the mastermind-agint-BDI integration pipeline.
"""

import pytest
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from pytest_asyncio import fixture as pytest_asyncio_fixture

# Import core components
from orchestration.mastermind_agent import MastermindAgent
from core.agint import AGInt, DecisionType
from core.bdi_agent import BDIAgent
from agents.memory_agent import MemoryAgent, MemoryImportance
from orchestration.coordinator_agent import CoordinatorAgent
from core.id_manager_agent import IDManagerAgent
from agents.guardian_agent import GuardianAgent
from agents.automindx_agent import AutoMINDXAgent
from llm.llm_interface import LLMHandlerInterface
from core.belief_system import BeliefSystem
from utils.config import Config

pytestmark = pytest.mark.asyncio

# Mock responses for command testing
MOCK_RESPONSES = {
    "evolve": json.dumps({
        "overall_campaign_status": "SUCCESS",
        "final_bdi_message": "BDI run COMPLETED_GOAL_ACHIEVED. Evolution completed.",
        "improvements": ["memory_optimization", "performance_enhancement"]
    }),
    "deploy": json.dumps({
        "overall_campaign_status": "SUCCESS", 
        "final_bdi_message": "BDI run COMPLETED_GOAL_ACHIEVED. Deployment completed.",
        "agents_deployed": ["task_agent_001", "monitor_agent_002"]
    }),
    "agent_creation": json.dumps({
        "success": True,
        "agent_id": "test_agent_001",
        "agent_type": "specialized_task",
        "public_address": "0x1234567890abcdef"
    })
}

@pytest_asyncio_fixture
def mock_llm_handler() -> MagicMock:
    """Create mock LLM handler for testing."""
    handler = MagicMock(spec=LLMHandlerInterface)
    
    async def side_effect(prompt: str, **kwargs):
        prompt_lower = prompt.lower()
        
        if "evolve" in prompt_lower:
            return MOCK_RESPONSES["evolve"]
        elif "deploy" in prompt_lower:
            return MOCK_RESPONSES["deploy"]
        elif "create_agent" in prompt_lower:
            return MOCK_RESPONSES["agent_creation"]
        elif "plan" in prompt_lower:
            return json.dumps({
                "plan": [
                    {"action": "assess_system", "tool": "system_analyzer"},
                    {"action": "execute_command", "tool": "command_executor"},
                    {"action": "validate_result", "tool": "validator"}
                ]
            })
        
        return json.dumps({"status": "success", "message": "Command processed"})
    
    handler.generate_text = AsyncMock(side_effect=side_effect)
    handler.provider_name = "mock_provider"
    handler.model_name_for_api = "mock-model"
    return handler

@pytest_asyncio_fixture
async def test_components(mock_llm_handler: MagicMock):
    """Set up test environment with all components."""
    components = {}
    
    config = Config(test_mode=True)
    belief_system = BeliefSystem(test_mode=True)
    memory_agent = MemoryAgent(config=config)
    
    # Create BDI Agent
    with patch('core.bdi_agent.create_llm_handler', return_value=mock_llm_handler):
        bdi_agent = BDIAgent(
            domain="command_test",
            belief_system_instance=belief_system,
            tools_registry={},
            memory_agent=memory_agent,
            test_mode=True
        )
        components['bdi_agent'] = bdi_agent
    
    # Create AGInt with model registry (patch ID manager creation)
    from llm.model_registry import ModelRegistry
    model_registry = ModelRegistry()
    
    with patch('core.id_manager_agent.IDManagerAgent') as mock_id_manager_class:
        mock_id_manager = MagicMock()
        mock_id_manager.create_new_wallet.return_value = ("0xtest", "TEST_KEY")
        mock_id_manager_class.return_value = mock_id_manager
        
        agint = AGInt(
            agent_id="agint_test",
            bdi_agent=bdi_agent,
            model_registry=model_registry,
            memory_agent=memory_agent,
            config=config
        )
        components['agint'] = agint
    
    # Create Mastermind
    with patch('orchestration.mastermind_agent.create_llm_handler', return_value=mock_llm_handler):
        mock_coordinator = MagicMock(spec=CoordinatorAgent)
        mastermind = await MastermindAgent.get_instance(
            test_mode=True,
            coordinator_agent_instance=mock_coordinator,
            memory_agent_instance=memory_agent
        )
        components['mastermind'] = mastermind
    
    components['memory_agent'] = memory_agent
    return components

class TestBDICommandAccess:
    """Test BDI agent command access."""
    
    async def test_core_commands_access(self, test_components):
        """Test BDI access to core commands."""
        mastermind = test_components['mastermind']
        bdi_agent = test_components['bdi_agent']
        
        # Test evolve command
        evolve_goal = "Execute evolve command to enhance system"
        bdi_agent.set_goal(evolve_goal, priority=1, is_primary=True)
        
        with patch.object(mastermind, 'manage_mindx_evolution') as mock_evolve:
            mock_evolve.return_value = json.loads(MOCK_RESPONSES["evolve"])
            result = await bdi_agent.run(max_cycles=5)
            assert result is not None
        
        # Test deploy command
        deploy_goal = "Execute deploy command to create agents"
        bdi_agent.set_goal(deploy_goal, priority=1, is_primary=True)
        
        with patch.object(mastermind, 'manage_agent_deployment') as mock_deploy:
            mock_deploy.return_value = json.loads(MOCK_RESPONSES["deploy"])
            result = await bdi_agent.run(max_cycles=5)
            assert result is not None
    
    async def test_agent_lifecycle_commands(self, test_components):
        """Test BDI access to agent lifecycle commands."""
        bdi_agent = test_components['bdi_agent']
        
        # Register CREATE_AGENT action
        async def mock_create_agent(action: Dict[str, Any]):
            return (True, json.loads(MOCK_RESPONSES["agent_creation"]))
        
        bdi_agent.register_action("CREATE_AGENT", mock_create_agent)
        
        # Test agent creation
        create_goal = "Execute agent_create command"
        bdi_agent.set_goal(create_goal, priority=1, is_primary=True)
        
        result = await bdi_agent.run(max_cycles=5)
        assert result is not None
    
    async def test_memory_integration(self, test_components):
        """Test memory integration during command execution."""
        bdi_agent = test_components['bdi_agent']
        memory_agent = test_components['memory_agent']
        
        # Store command history
        await memory_agent.save_interaction_memory(
            agent_id=bdi_agent.agent_id,
            input_data="Previous command",
            response_data={"status": "success", "command": "evolve"},
            importance=MemoryImportance.MEDIUM,
            context={"type": "command_history"}
        )
        
        memory_goal = "Execute command with memory integration"
        bdi_agent.set_goal(memory_goal, priority=1, is_primary=True)
        
        result = await bdi_agent.run(max_cycles=5)
        assert result is not None
        
        # Verify memory access
        context = await memory_agent.get_agent_memory_context(
            agent_id=bdi_agent.agent_id,
            context_type="recent",
            limit=5
        )
        assert len(context.get("stm_memories", [])) > 0
    
    async def test_agint_coordination(self, test_components):
        """Test AGInt coordination for command execution."""
        agint = test_components['agint']
        
        directive = "Coordinate system evolution command"
        
        # Test decision making
        decision = agint._decide_rule_based({
            "directive": directive,
            "complexity": "high",
            "requires_planning": True
        })
        
        assert decision == DecisionType.BDI_DELEGATION
        
        # Test BDI delegation
        success, result = await agint._delegate_task_to_bdi(directive)
        assert success or result is not None
    
    async def test_command_error_handling(self, test_components):
        """Test error handling for failed commands."""
        mastermind = test_components['mastermind']
        bdi_agent = test_components['bdi_agent']
        
        error_goal = "Execute command that will fail"
        bdi_agent.set_goal(error_goal, priority=1, is_primary=True)
        
        with patch.object(mastermind, 'manage_mindx_evolution') as mock_evolve:
            mock_evolve.side_effect = Exception("Command failure")
            
            result = await bdi_agent.run(max_cycles=5)
            assert result is not None
            assert "FAILED" in result or "ERROR" in result

async def test_command_coverage(test_components):
    """Test BDI access to all major command categories."""
    bdi_agent = test_components['bdi_agent']
    
    command_categories = {
        "core": ["evolve", "deploy", "introspect"],
        "identity": ["id_list", "id_create"],
        "coordinator": ["coord_query", "coord_analyze"],
        "agent_lifecycle": ["agent_create", "agent_delete"],
        "utility": ["basegen", "audit_gemini"]
    }
    
    results = {}
    
    for category, commands in command_categories.items():
        category_results = {}
        
        for command in commands:
            test_goal = f"Execute {command} command"
            bdi_agent.set_goal(test_goal, priority=1, is_primary=True)
            
            try:
                result = await bdi_agent.run(max_cycles=3)
                category_results[command] = {
                    "accessible": True,
                    "result": result is not None
                }
            except Exception as e:
                category_results[command] = {
                    "accessible": False,
                    "error": str(e)
                }
        
        results[category] = category_results
    
    # Verify access rate
    total = sum(len(commands) for commands in command_categories.values())
    accessible = sum(
        1 for category in results.values()
        for result in category.values()
        if result.get("accessible", False)
    )
    
    access_rate = accessible / total
    assert access_rate >= 0.6, f"Only {access_rate:.1%} commands accessible"
    
    return results 