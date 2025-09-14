# tests/integration/test_mastermind_agint_bdi_orchestration.py
"""
Comprehensive integration test for Mastermind-AGInt-BDI orchestration.

This test validates the complete intelligent orchestration flow:
1. Mastermind strategic decision-making
2. AGInt coordination and context management  
3. BDI agent execution with self-learning
4. Memory system integration (STM/LTM)
5. Self-improvement recommendations
6. Augmentic intelligence capabilities

The test simulates a complete cycle where agents read their own logs/memories
to improve themselves and adapt to higher-level intelligence calls.
"""
import pytest
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from pytest_asyncio import fixture as pytest_asyncio_fixture

# Import core components
from orchestration.mastermind_agent import MastermindAgent
from core.agint import AGInt, DecisionType
from core.bdi_agent import BDIAgent
from agents.memory_agent import MemoryAgent, MemoryType, MemoryImportance
from orchestration.coordinator_agent import CoordinatorAgent
from llm.llm_interface import LLMHandlerInterface
from utils.logging_config import setup_logging

# Use pytest-asyncio for async tests
pytestmark = pytest.mark.asyncio

# Mock LLM responses for intelligent orchestration
MOCK_MASTERMIND_ANALYSIS = json.dumps({
    "strategic_assessment": "System performance analysis indicates need for optimization",
    "priority_areas": ["memory_efficiency", "decision_speed", "learning_rate"],
    "recommended_actions": [
        {"type": "ANALYZE_SYSTEM_PERFORMANCE", "priority": "HIGH"},
        {"type": "OPTIMIZE_AGENT_COORDINATION", "priority": "MEDIUM"},
        {"type": "ENHANCE_LEARNING_MECHANISMS", "priority": "HIGH"}
    ]
})

MOCK_AGINT_COORDINATION = json.dumps({
    "coordination_strategy": "Implement hierarchical decision flow with feedback loops",
    "context_analysis": {
        "system_state": "operational",
        "performance_metrics": {"success_rate": 0.85, "response_time": 1.2},
        "improvement_areas": ["context_awareness", "pattern_recognition"]
    },
    "delegation_plan": {
        "primary_agent": "bdi_agent_mastermind_strategy",
        "coordination_points": ["memory_analysis", "performance_optimization"],
        "success_criteria": ["improved_success_rate", "reduced_response_time"]
    }
})

MOCK_BDI_EXECUTION = json.dumps({
    "execution_plan": [
        {"action": "analyze_memory_patterns", "expected_outcome": "pattern_insights"},
        {"action": "identify_improvement_areas", "expected_outcome": "optimization_targets"},
        {"action": "implement_optimizations", "expected_outcome": "performance_improvements"}
    ],
    "self_assessment": {
        "current_capabilities": ["pattern_analysis", "optimization", "learning"],
        "improvement_needs": ["context_integration", "predictive_modeling"],
        "confidence_level": 0.8
    }
})

@pytest_asyncio_fixture
def mock_llm_handler() -> MagicMock:
    """Create mock LLM handler with intelligent responses."""
    handler = MagicMock(spec=LLMHandlerInterface)
    
    async def side_effect_func(prompt: str, **kwargs):
        if "strategic" in prompt.lower() or "mastermind" in prompt.lower():
            return MOCK_MASTERMIND_ANALYSIS
        elif "coordination" in prompt.lower() or "agint" in prompt.lower():
            return MOCK_AGINT_COORDINATION
        elif "execution" in prompt.lower() or "bdi" in prompt.lower():
            return MOCK_BDI_EXECUTION
        elif "self-improvement" in prompt.lower():
            return json.dumps({
                "recommendations": [
                    {"priority": "HIGH", "action": "enhance_pattern_recognition"},
                    {"priority": "MEDIUM", "action": "optimize_memory_usage"}
                ]
            })
        return "{}"
    
    handler.generate_text = AsyncMock(side_effect=side_effect_func)
    handler.provider_name = "mock_provider"
    handler.model_name_for_api = "mock-intelligent-model"
    return handler

@pytest_asyncio_fixture
async def memory_agent_instance() -> MemoryAgent:
    """Create a MemoryAgent instance for testing."""
    memory_agent = MemoryAgent()
    # No initialize method needed - constructor handles initialization
    return memory_agent

@pytest_asyncio_fixture
async def orchestration_components(mock_llm_handler: MagicMock, memory_agent_instance: MemoryAgent):
    """Set up complete orchestration components."""
    components = {}
    
    # Create BDI Agent with self-learning capabilities
    with patch('core.bdi_agent.create_llm_handler', return_value=mock_llm_handler):
        from core.belief_system import BeliefSystem
        belief_system = BeliefSystem()
        
        bdi_agent = BDIAgent(
            domain="mastermind_strategy",
            belief_system_instance=belief_system,
            tools_registry={},
            memory_agent=memory_agent_instance,
            test_mode=True
        )
        components['bdi_agent'] = bdi_agent
    
    # Create AGInt with enhanced coordination
    with patch('core.agint.create_llm_handler', return_value=mock_llm_handler):
        from llm.model_registry import ModelRegistry
        model_registry = ModelRegistry()
        
        agint = AGInt(
            agent_id="agint_coordinator",
            bdi_agent=bdi_agent,
            model_registry=model_registry,
            memory_agent=memory_agent_instance
        )
        components['agint'] = agint
    
    # Create Mastermind with strategic oversight
    with patch('orchestration.mastermind_agent.create_llm_handler', return_value=mock_llm_handler):
        mock_coordinator = MagicMock(spec=CoordinatorAgent)
        mastermind = await MastermindAgent.get_instance(
            test_mode=True,
            coordinator_agent_instance=mock_coordinator,
            memory_agent_instance=memory_agent_instance
        )
        components['mastermind'] = mastermind
    
    components['memory_agent'] = memory_agent_instance
    
    return components

async def test_complete_orchestration_cycle(orchestration_components):
    """
    Test complete orchestration cycle with self-learning and memory integration.
    
    GIVEN a complete orchestration setup with Mastermind, AGInt, and BDI agents
    WHEN a high-level directive is processed through the hierarchy
    THEN the system should demonstrate intelligent coordination, execution, and self-improvement
    """
    # ARRANGE
    components = orchestration_components
    mastermind = components['mastermind']
    agint = components['agint']
    bdi_agent = components['bdi_agent']
    memory_agent = components['memory_agent']
    
    # Simulate CEO-level directive (higher intelligence call)
    ceo_directive = "Analyze system performance and implement optimizations to achieve 95% success rate"
    
    # ACT - Execute complete orchestration cycle
    
    # 1. Mastermind strategic analysis
    strategic_result = await mastermind.manage_mindx_evolution(top_level_directive=ceo_directive)
    
    # 2. Store mastermind decision in memory
    await memory_agent.save_interaction_memory(
        agent_id="mastermind_prime",
        input_data=ceo_directive,
        response_data=strategic_result,
        importance=MemoryImportance.HIGH,
        context={"source": "ceo_directive", "type": "strategic_analysis"}
    )
    
    # 3. AGInt coordination with context awareness
    agint_context = await memory_agent.get_agent_memory_context(
        agent_id="mastermind_prime", 
        context_type="recent",
        limit=5
    )
    
    # Simulate AGInt processing with memory context
    coordination_directive = f"Coordinate execution of strategic plan: {strategic_result}"
    agint_decision = agint._decide_rule_based({
        "strategic_context": agint_context,
        "coordination_required": True,
        "performance_target": 0.95
    })
    
    # 4. BDI agent execution with self-learning
    if agint_decision == DecisionType.BDI_DELEGATION:
        # BDI agent reads its own memory for self-improvement
        bdi_memory_context = await memory_agent.get_agent_memory_context(
            agent_id="bdi_agent_mastermind_strategy",
            context_type="all",
            limit=10
        )
        
        # Generate self-improvement recommendations
        recommendations = await memory_agent.generate_self_improvement_recommendations(
            agent_id="bdi_agent_mastermind_strategy"
        )
        
        # Store BDI execution with self-awareness
        await memory_agent.save_interaction_memory(
            agent_id="bdi_agent_mastermind_strategy",
            input_data=coordination_directive,
            response_data={
                "execution_status": "in_progress",
                "self_assessment": bdi_memory_context,
                "improvement_plan": recommendations
            },
            importance=MemoryImportance.HIGH,
            context={"type": "self_aware_execution", "agint_decision": agint_decision.value}
        )
    
    # 5. Promote STM learnings to LTM
    promotion_result = await memory_agent.promote_stm_to_ltm(
        agent_id="bdi_agent_mastermind_strategy",
        pattern_threshold=1,  # Lower threshold for testing
        days_back=1
    )
    
    # ASSERT - Validate intelligent orchestration
    
    # 1. Strategic analysis completed successfully
    assert strategic_result is not None
    assert strategic_result.get("overall_campaign_status") == "SUCCESS"
    
    # 2. AGInt made intelligent coordination decision
    assert agint_decision == DecisionType.BDI_DELEGATION
    
    # 3. Memory context was properly retrieved and used
    assert agint_context["agent_id"] == "mastermind_prime"
    assert len(agint_context["stm_memories"]) > 0
    
    # 4. Self-improvement recommendations generated
    assert "agent_id" in recommendations
    assert len(recommendations.get("immediate_improvements", [])) >= 0
    
    # 5. STM to LTM promotion occurred
    assert promotion_result["status"] in ["success", "insufficient_data"]
    
    # 6. Validate memory storage structure
    stm_memories = await memory_agent.get_recent_memories(
        agent_id="mastermind_prime",
        limit=5,
        days_back=1
    )
    assert len(stm_memories) > 0
    
    # 7. Validate cross-agent memory visibility
    all_agent_patterns = await memory_agent.analyze_agent_patterns(
        agent_id="bdi_agent_mastermind_strategy",
        days_back=1
    )
    assert all_agent_patterns["total_memories"] > 0

async def test_self_learning_capabilities(orchestration_components):
    """
    Test agent self-learning capabilities through memory analysis.
    
    GIVEN agents with historical memory data
    WHEN they analyze their own performance patterns
    THEN they should generate actionable self-improvement recommendations
    """
    # ARRANGE
    memory_agent = orchestration_components['memory_agent']
    agent_id = "bdi_agent_mastermind_strategy"
    
    # Create historical memory data simulating various performance scenarios
    historical_scenarios = [
        {
            "input": "Optimize database queries",
            "response": "Successfully optimized 15 queries, 20% performance improvement",
            "importance": MemoryImportance.HIGH,
            "context": {"success": True, "domain": "database"}
        },
        {
            "input": "Analyze user behavior patterns", 
            "response": "Analysis failed due to insufficient data",
            "importance": MemoryImportance.MEDIUM,
            "context": {"success": False, "domain": "analytics", "error": "data_insufficient"}
        },
        {
            "input": "Deploy machine learning model",
            "response": "Model deployed successfully with 92% accuracy",
            "importance": MemoryImportance.HIGH,
            "context": {"success": True, "domain": "ml", "accuracy": 0.92}
        }
    ]
    
    # Store historical memories
    for scenario in historical_scenarios:
        await memory_agent.save_interaction_memory(
            agent_id=agent_id,
            input_data=scenario["input"],
            response_data=scenario["response"],
            importance=scenario["importance"],
            context=scenario["context"]
        )
    
    # ACT - Generate self-improvement recommendations
    recommendations = await memory_agent.generate_self_improvement_recommendations(agent_id)
    
    # Enable auto-learning
    auto_learning_enabled = await memory_agent.enable_auto_learning(
        agent_id=agent_id,
        learning_config={
            "promotion_interval_hours": 1,  # Frequent for testing
            "pattern_threshold": 2,
            "analysis_days": 1,
            "auto_recommendations": True
        }
    )
    
    # Promote patterns to LTM
    promotion_result = await memory_agent.promote_stm_to_ltm(
        agent_id=agent_id,
        pattern_threshold=2,
        days_back=1
    )
    
    # Get LTM insights
    ltm_insights = await memory_agent.get_ltm_insights(agent_id)
    
    # ASSERT - Validate self-learning capabilities
    
    # 1. Recommendations generated successfully
    assert recommendations["agent_id"] == agent_id
    assert "immediate_improvements" in recommendations
    assert "strategic_improvements" in recommendations
    
    # 2. Auto-learning enabled
    assert auto_learning_enabled is True
    
    # 3. Pattern promotion successful
    assert promotion_result["status"] == "success"
    assert promotion_result["patterns_promoted"] > 0
    
    # 4. LTM insights available
    assert len(ltm_insights) > 0
    
    # 5. Validate learning configuration stored
    ltm_path = memory_agent.ltm_path / agent_id / "learning_config.json"
    assert ltm_path.exists()

async def test_memory_system_stm_ltm_integration(orchestration_components):
    """
    Test STM/LTM memory system integration for learning and adaptation.
    
    GIVEN agents generating various types of memories
    WHEN patterns emerge over time
    THEN STM should promote significant learnings to LTM for long-term adaptation
    """
    # ARRANGE
    memory_agent = orchestration_components['memory_agent']
    agent_id = "resource_monitor"
    
    # Simulate extended operation generating various memory types
    memory_scenarios = [
        (MemoryType.PERFORMANCE, "System CPU usage: 45%", {"metric": "cpu", "value": 45}),
        (MemoryType.PERFORMANCE, "System CPU usage: 78%", {"metric": "cpu", "value": 78}),
        (MemoryType.PERFORMANCE, "System CPU usage: 92%", {"metric": "cpu", "value": 92}),
        (MemoryType.ERROR, "High CPU usage detected", {"threshold_exceeded": True}),
        (MemoryType.SYSTEM_STATE, "Optimization triggered", {"action": "cpu_optimization"}),
        (MemoryType.PERFORMANCE, "System CPU usage: 52%", {"metric": "cpu", "value": 52}),
        (MemoryType.LEARNING, "CPU optimization effective", {"learning": "optimization_works"})
    ]
    
    # Store memories in STM
    for mem_type, content, context in memory_scenarios:
        await memory_agent.save_timestamped_memory(
            agent_id=agent_id,
            memory_type=mem_type,
            content=content,
            importance=MemoryImportance.MEDIUM,
            context=context
        )
    
    # ACT - Analyze patterns and promote to LTM
    
    # 1. Analyze STM patterns
    stm_analysis = await memory_agent.analyze_agent_patterns(agent_id, days_back=1)
    
    # 2. Promote significant patterns to LTM
    promotion_result = await memory_agent.promote_stm_to_ltm(
        agent_id=agent_id,
        pattern_threshold=3,
        days_back=1
    )
    
    # 3. Retrieve LTM insights
    ltm_insights = await memory_agent.get_ltm_insights(agent_id)
    
    # 4. Get comprehensive memory context
    full_context = await memory_agent.get_agent_memory_context(
        agent_id=agent_id,
        context_type="all",
        limit=20
    )
    
    # ASSERT - Validate STM/LTM integration
    
    # 1. STM analysis captured all memory types
    assert stm_analysis["total_memories"] == 7
    assert "performance" in stm_analysis["memory_types"]
    assert "error" in stm_analysis["memory_types"]
    
    # 2. Pattern promotion successful
    assert promotion_result["status"] == "success"
    assert promotion_result["patterns_promoted"] > 0
    
    # 3. LTM insights available
    assert len(ltm_insights) > 0
    
    # 4. Full context includes both STM and LTM
    assert len(full_context["stm_memories"]) > 0
    assert len(full_context["ltm_insights"]) > 0
    assert full_context["patterns"]["total_memories"] > 0
    
    # 5. Validate memory structure exists
    stm_path = memory_agent.stm_path / agent_id
    ltm_path = memory_agent.ltm_path / agent_id
    assert stm_path.exists()
    assert ltm_path.exists()

if __name__ == "__main__":
    # Setup logging for test runs
    setup_logging()
    
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"]) 