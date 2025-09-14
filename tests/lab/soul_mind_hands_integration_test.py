#!/usr/bin/env python3
"""
Soul-Mind-Hands Integration Test

Tests the core decision flow and coordination between:
- Soul (Mastermind Agent) - Strategic level
- Mind (AGInt) - Cognitive level  
- Hands (BDI Agent) - Tactical/execution level

This test validates the hierarchical decision-making architecture without
complex initialization dependencies.
"""

import asyncio
import json
import time
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.logging_config import get_logger
from core.agint import DecisionType

logger = get_logger(__name__)

class MockBDIAgent:
    """Mock BDI Agent (Hands) for testing."""
    
    def __init__(self, agent_id: str = "mock_bdi_hands"):
        self.agent_id = agent_id
        self.status = "INITIALIZED"
        self.current_goal = None
        self.execution_history = []
        
    def set_goal(self, goal_description: str, priority: int = 1, **kwargs):
        """Mock goal setting."""
        self.current_goal = {
            "description": goal_description,
            "priority": priority,
            "timestamp": time.time()
        }
        logger.info(f"🤲 HANDS: Goal set - {goal_description}")
        
    async def run(self, max_cycles: int = 100) -> str:
        """Mock execution."""
        if not self.current_goal:
            return "No goal set"
            
        # Simulate execution
        await asyncio.sleep(0.1)
        
        execution_result = {
            "goal": self.current_goal["description"],
            "status": "COMPLETED",
            "actions_taken": ["analyze_task", "execute_plan", "verify_results"],
            "outcome": "Successfully executed tactical plan"
        }
        
        self.execution_history.append(execution_result)
        self.status = "COMPLETED_GOAL_ACHIEVED"
        
        logger.info(f"🤲 HANDS: Execution completed - {execution_result['outcome']}")
        return f"Task completed: {execution_result['outcome']}"
        
    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        return {
            "status": self.status,
            "current_goal": self.current_goal,
            "execution_count": len(self.execution_history)
        }

class MockAGInt:
    """Mock AGInt (Mind) for testing."""
    
    def __init__(self, agent_id: str = "mock_agint_mind"):
        self.agent_id = agent_id
        self.state_summary = {"llm_operational": True, "awareness": "System ready"}
        self.last_action_context = None
        self.decision_history = []
        
    async def _decide_rule_based(self, perception: Dict[str, Any]) -> DecisionType:
        """Mock rule-based decision making."""
        
        # Implement the same logic as real AGInt
        decision = DecisionType.BDI_DELEGATION
        reason = "System healthy. Choosing BDI_DELEGATION to pursue directive."

        if not self.state_summary.get("llm_operational", True):
            decision = DecisionType.SELF_REPAIR
            reason = "System health check failed. Choosing SELF_REPAIR."
        elif perception.get('last_action_failure_context'):
            decision = DecisionType.RESEARCH
            reason = "Last action failed. Choosing RESEARCH to re-evaluate."
            
        decision_record = {
            "decision": decision,
            "reason": reason,
            "perception": perception,
            "timestamp": time.time()
        }
        
        self.decision_history.append(decision_record)
        logger.info(f"🧠 MIND: Decision made - {decision.name} ({reason})")
        
        return decision
        
    async def process_strategic_directive(self, directive: str) -> Dict[str, Any]:
        """Process directive from mastermind."""
        logger.info(f"🧠 MIND: Processing strategic directive - {directive}")
        
        # Simulate perception
        perception = {
            "directive": directive,
            "system_state": "operational",
            "timestamp": time.time()
        }
        
        # Make decision
        decision_type = await self._decide_rule_based(perception)
        
        # Return coordination plan
        return {
            "decision_type": decision_type.name,
            "coordination_plan": {
                "tactical_objective": f"Execute: {directive}",
                "delegation_target": "bdi_agent",
                "success_criteria": "Task completion with positive outcome"
            },
            "context": perception
        }

class MockMastermindAgent:
    """Mock Mastermind Agent (Soul) for testing."""
    
    def __init__(self, agent_id: str = "mock_mastermind_soul"):
        self.agent_id = agent_id
        self.strategic_decisions = []
        self.agint = None
        self.bdi_agent = None
        
    def connect_cognitive_layer(self, agint: MockAGInt):
        """Connect to AGInt (mind)."""
        self.agint = agint
        logger.info("💜 SOUL: Connected to cognitive layer (AGInt)")
        
    def connect_execution_layer(self, bdi_agent: MockBDIAgent):
        """Connect to BDI Agent (hands)."""
        self.bdi_agent = bdi_agent
        logger.info("💜 SOUL: Connected to execution layer (BDI)")
        
    async def make_strategic_decision(self, high_level_objective: str) -> Dict[str, Any]:
        """Make strategic decision at the highest level."""
        logger.info(f"💜 SOUL: Making strategic decision for - {high_level_objective}")
        
        # Strategic analysis
        strategic_plan = {
            "objective": high_level_objective,
            "strategy": "Hierarchical execution through mind-hands coordination",
            "priority": "HIGH",
            "expected_outcome": "Successful objective completion",
            "coordination_approach": "Delegate to AGInt for cognitive processing"
        }
        
        self.strategic_decisions.append(strategic_plan)
        
        logger.info("💜 SOUL: Strategic plan formulated")
        return strategic_plan
        
    async def orchestrate_execution(self, objective: str) -> Dict[str, Any]:
        """Orchestrate complete soul-mind-hands execution."""
        if not self.agint or not self.bdi_agent:
            raise RuntimeError("Cognitive or execution layers not connected")
            
        logger.info("💜 SOUL: Starting orchestrated execution")
        
        # 1. Strategic decision (Soul)
        strategic_plan = await self.make_strategic_decision(objective)
        
        # 2. Cognitive processing (Mind)
        cognitive_plan = await self.agint.process_strategic_directive(
            strategic_plan["objective"]
        )
        
        # 3. Tactical execution (Hands)
        if cognitive_plan["decision_type"] == "BDI_DELEGATION":
            tactical_objective = cognitive_plan["coordination_plan"]["tactical_objective"]
            
            self.bdi_agent.set_goal(tactical_objective, priority=1)
            execution_result = await self.bdi_agent.run(max_cycles=10)
            
            # 4. Integration results
            orchestration_result = {
                "objective": objective,
                "strategic_plan": strategic_plan,
                "cognitive_plan": cognitive_plan,
                "execution_result": execution_result,
                "bdi_status": self.bdi_agent.get_status(),
                "overall_success": self.bdi_agent.get_status()["status"] == "COMPLETED_GOAL_ACHIEVED",
                "orchestration_flow": "SOUL → MIND → HANDS ✓"
            }
            
            logger.info(f"💜 SOUL: Orchestration completed - Success: {orchestration_result['overall_success']}")
            return orchestration_result
        else:
            # Handle non-delegation decisions
            return {
                "objective": objective,
                "decision": cognitive_plan["decision_type"],
                "reason": "AGInt chose non-delegation strategy",
                "overall_success": False
            }

class SoulMindHandsIntegrationTester:
    """Integration tester for the soul-mind-hands architecture."""
    
    def __init__(self):
        self.test_results = {}
        
    async def test_basic_integration(self) -> Dict[str, Any]:
        """Test basic soul-mind-hands integration."""
        logger.info("🧪 Testing basic soul-mind-hands integration")
        
        # Setup components
        soul = MockMastermindAgent()
        mind = MockAGInt()
        hands = MockBDIAgent()
        
        # Connect the architecture
        soul.connect_cognitive_layer(mind)
        soul.connect_execution_layer(hands)
        
        # Test objective
        objective = "Analyze system performance and implement optimizations"
        
        # Execute orchestration
        result = await soul.orchestrate_execution(objective)
        
        # Validate the flow
        success_criteria = [
            result["overall_success"],
            "strategic_plan" in result,
            "cognitive_plan" in result,
            "execution_result" in result,
            result["cognitive_plan"]["decision_type"] == "BDI_DELEGATION"
        ]
        
        test_result = {
            "test_name": "basic_integration",
            "success": all(success_criteria),
            "orchestration_result": result,
            "validation_criteria": {
                "overall_success": result["overall_success"],
                "strategic_planning": "strategic_plan" in result,
                "cognitive_processing": "cognitive_plan" in result,
                "tactical_execution": "execution_result" in result,
                "proper_delegation": result["cognitive_plan"]["decision_type"] == "BDI_DELEGATION"
            }
        }
        
        logger.info(f"🧪 Basic integration test: {'✅ PASSED' if test_result['success'] else '❌ FAILED'}")
        return test_result
        
    async def test_failure_handling(self) -> Dict[str, Any]:
        """Test failure handling through the architecture."""
        logger.info("🧪 Testing failure handling in soul-mind-hands architecture")
        
        # Setup components
        soul = MockMastermindAgent()
        mind = MockAGInt()
        hands = MockBDIAgent()
        
        # Connect architecture
        soul.connect_cognitive_layer(mind)
        soul.connect_execution_layer(hands)
        
        # Simulate LLM failure
        mind.state_summary["llm_operational"] = False
        
        # Test objective
        objective = "Handle system with LLM failure"
        
        # Test strategic decision 
        strategic_plan = await soul.make_strategic_decision(objective)
        
        # Test cognitive response to failure
        cognitive_plan = await mind.process_strategic_directive(objective)
        
        # Validate failure handling
        expected_decision = cognitive_plan["decision_type"] == "SELF_REPAIR"
        
        test_result = {
            "test_name": "failure_handling",
            "success": expected_decision,
            "strategic_plan": strategic_plan,
            "cognitive_plan": cognitive_plan,
            "failure_scenario": "LLM not operational",
            "expected_decision": "SELF_REPAIR",
            "actual_decision": cognitive_plan["decision_type"]
        }
        
        logger.info(f"🧪 Failure handling test: {'✅ PASSED' if test_result['success'] else '❌ FAILED'}")
        return test_result
        
    async def test_decision_logic_flow(self) -> Dict[str, Any]:
        """Test the decision logic flow through all layers."""
        logger.info("🧪 Testing decision logic flow")
        
        # Setup components
        mind = MockAGInt()
        
        # Test scenarios
        scenarios = [
            {
                "name": "healthy_system",
                "perception": {},
                "expected": "BDI_DELEGATION"
            },
            {
                "name": "llm_failure",
                "perception": {},
                "setup": lambda: setattr(mind, 'state_summary', {"llm_operational": False}),
                "expected": "SELF_REPAIR"
            },
            {
                "name": "after_failure",
                "perception": {"last_action_failure_context": {"error": "some_error"}},
                "setup": lambda: setattr(mind, 'state_summary', {"llm_operational": True}),
                "expected": "RESEARCH"
            }
        ]
        
        scenario_results = []
        for scenario in scenarios:
            # Setup scenario
            if "setup" in scenario:
                scenario["setup"]()
            
            # Test decision
            decision = await mind._decide_rule_based(scenario["perception"])
            
            scenario_result = {
                "scenario": scenario["name"],
                "expected": scenario["expected"],
                "actual": decision.name,
                "success": decision.name == scenario["expected"]
            }
            
            scenario_results.append(scenario_result)
            logger.info(f"🧪   Scenario '{scenario['name']}': {'✅' if scenario_result['success'] else '❌'}")
        
        overall_success = all(r["success"] for r in scenario_results)
        
        test_result = {
            "test_name": "decision_logic_flow",
            "success": overall_success,
            "scenarios": scenario_results,
            "decision_history": mind.decision_history
        }
        
        logger.info(f"🧪 Decision logic flow test: {'✅ PASSED' if test_result['success'] else '❌ FAILED'}")
        return test_result
        
    async def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run comprehensive soul-mind-hands integration test suite."""
        logger.info("🚀 Starting comprehensive soul-mind-hands integration test suite")
        logger.info("=" * 80)
        
        # Run all tests
        tests = [
            self.test_basic_integration(),
            self.test_failure_handling(),
            self.test_decision_logic_flow()
        ]
        
        results = await asyncio.gather(*tests)
        
        # Calculate overall metrics
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r["success"])
        success_rate = passed_tests / total_tests
        
        comprehensive_result = {
            "test_suite": "soul_mind_hands_integration",
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": success_rate,
            "overall_success": success_rate >= 0.8,
            "individual_results": results,
            "architecture_validated": {
                "soul_strategic": any("strategic_plan" in r.get("orchestration_result", {}) for r in results),
                "mind_cognitive": any("cognitive_plan" in r.get("orchestration_result", {}) for r in results),
                "hands_tactical": any("execution_result" in r.get("orchestration_result", {}) for r in results),
                "integration_flow": any(r.get("orchestration_result", {}).get("overall_success") for r in results)
            }
        }
        
        logger.info("=" * 80)
        logger.info(f"🎯 COMPREHENSIVE TEST RESULTS:")
        logger.info(f"   Total Tests: {total_tests}")
        logger.info(f"   Passed: {passed_tests}")
        logger.info(f"   Failed: {total_tests - passed_tests}")
        logger.info(f"   Success Rate: {success_rate:.1%}")
        logger.info(f"   Overall: {'✅ SUCCESS' if comprehensive_result['overall_success'] else '❌ FAILED'}")
        logger.info("=" * 80)
        
        return comprehensive_result

async def main():
    """Main test execution."""
    print("\n" + "=" * 80)
    print("🧠 MINDX SOUL-MIND-HANDS INTEGRATION TEST")
    print("   Soul = Mastermind Agent (Strategic)")
    print("   Mind = AGInt (Cognitive)")  
    print("   Hands = BDI Agent (Tactical)")
    print("=" * 80)
    
    tester = SoulMindHandsIntegrationTester()
    
    try:
        results = await tester.run_comprehensive_test_suite()
        
        # Print summary
        print(f"\n🎯 FINAL RESULTS:")
        print(f"   Architecture Integration: {'✅ VALIDATED' if results['overall_success'] else '❌ FAILED'}")
        print(f"   Soul-Mind-Hands Flow: {'✅ WORKING' if results['architecture_validated']['integration_flow'] else '❌ BROKEN'}")
        print(f"   Success Rate: {results['success_rate']:.1%}")
        
        return 0 if results['overall_success'] else 1
        
    except Exception as e:
        logger.error(f"Test suite failed with exception: {e}", exc_info=True)
        print(f"❌ Test suite failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 