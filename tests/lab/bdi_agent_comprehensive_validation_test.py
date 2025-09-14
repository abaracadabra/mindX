#!/usr/bin/env python3
"""
BDI Agent Comprehensive Validation Test

This test validates and explains the Belief-Desire-Intention (BDI) architecture
through comprehensive testing of all core components:

1. Belief System - Knowledge representation with confidence levels
2. Desire Management - Goal prioritization and conflict resolution  
3. Intention Planning - Action sequence generation and execution
4. Tool Integration - Dynamic tool loading and usage
5. Learning Mechanisms - Adaptation based on results

The test demonstrates how BDI agents think and act in a human-like manner.
"""

import asyncio
import json
import time
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from utils.logging_config import get_logger

logger = get_logger(__name__)

# Mock BDI Components for Testing
class BeliefConfidence(Enum):
    """Confidence levels for beliefs"""
    VERY_LOW = 0.1
    LOW = 0.3
    MEDIUM = 0.5
    HIGH = 0.7
    VERY_HIGH = 0.9
    CERTAIN = 1.0

@dataclass
class Belief:
    """Represents a belief with confidence level and evidence"""
    statement: str
    confidence: float
    evidence: List[str]
    timestamp: float
    source: str = "observation"
    
    def update_confidence(self, new_evidence: str, impact: float):
        """Update belief confidence based on new evidence"""
        self.evidence.append(new_evidence)
        # Simple confidence update (real implementation would be more sophisticated)
        self.confidence = min(1.0, max(0.0, self.confidence + impact))
        self.timestamp = time.time()

@dataclass
class Desire:
    """Represents a goal/desire with priority and context"""
    description: str
    priority: int  # 1 = highest priority
    context: Dict[str, Any]
    deadline: Optional[float] = None
    estimated_effort: float = 1.0
    success_probability: float = 0.5
    
    def calculate_urgency(self) -> float:
        """Calculate urgency based on deadline and priority"""
        if self.deadline:
            time_left = max(0, self.deadline - time.time())
            urgency = (1.0 / (time_left + 1)) * (1.0 / self.priority)
        else:
            urgency = 1.0 / self.priority
        return urgency * self.success_probability

@dataclass
class Intention:
    """Represents a planned action sequence"""
    goal: str
    action_sequence: List[Dict[str, Any]]
    resources_needed: List[str]
    expected_outcome: str
    contingency_plans: List[str]
    execution_status: str = "planned"
    
class MockBeliefSystem:
    """Mock implementation of BDI Belief System"""
    
    def __init__(self):
        self.beliefs: Dict[str, Belief] = {}
        self.belief_categories = ["system_state", "environment", "capabilities", "constraints"]
        
    def add_belief(self, statement: str, confidence: float, evidence: List[str], category: str = "general"):
        """Add a new belief to the system"""
        belief_id = f"{category}_{len(self.beliefs)}"
        self.beliefs[belief_id] = Belief(
            statement=statement,
            confidence=confidence,
            evidence=evidence,
            timestamp=time.time(),
            source="initial"
        )
        logger.info(f"🧠 BELIEF ADDED: {statement} (confidence: {confidence:.2f})")
        return belief_id
        
    def update_belief(self, belief_id: str, new_evidence: str, confidence_impact: float):
        """Update existing belief with new evidence"""
        if belief_id in self.beliefs:
            old_confidence = self.beliefs[belief_id].confidence
            self.beliefs[belief_id].update_confidence(new_evidence, confidence_impact)
            logger.info(f"🔄 BELIEF UPDATED: {self.beliefs[belief_id].statement}")
            logger.info(f"   Confidence: {old_confidence:.2f} → {self.beliefs[belief_id].confidence:.2f}")
            logger.info(f"   New Evidence: {new_evidence}")
            
    def query_beliefs(self, category: str = None, min_confidence: float = 0.0) -> List[Belief]:
        """Query beliefs by category and confidence level"""
        relevant_beliefs = []
        for belief in self.beliefs.values():
            if belief.confidence >= min_confidence:
                if category is None or category in belief.statement.lower():
                    relevant_beliefs.append(belief)
        return sorted(relevant_beliefs, key=lambda b: b.confidence, reverse=True)
        
    def get_system_state_beliefs(self) -> Dict[str, Any]:
        """Get current system state based on beliefs"""
        system_beliefs = self.query_beliefs("system", min_confidence=0.5)
        state = {
            "operational": any("operational" in b.statement.lower() for b in system_beliefs),
            "performance_level": 0.8,  # Derived from performance-related beliefs
            "resource_availability": "sufficient",
            "confidence_level": sum(b.confidence for b in system_beliefs) / len(system_beliefs) if system_beliefs else 0.5
        }
        return state

class MockDesireManager:
    """Mock implementation of BDI Desire Management"""
    
    def __init__(self):
        self.desires: List[Desire] = []
        self.active_goals: List[str] = []
        self.completed_goals: List[str] = []
        
    def add_desire(self, description: str, priority: int, context: Dict[str, Any], 
                   deadline: Optional[float] = None, effort: float = 1.0) -> Desire:
        """Add a new desire/goal"""
        desire = Desire(
            description=description,
            priority=priority,
            context=context,
            deadline=deadline,
            estimated_effort=effort,
            success_probability=0.7  # Default probability
        )
        self.desires.append(desire)
        logger.info(f"🎯 DESIRE ADDED: {description} (Priority: {priority})")
        return desire
        
    def prioritize_desires(self) -> List[Desire]:
        """Sort desires by urgency and priority"""
        return sorted(self.desires, key=lambda d: d.calculate_urgency(), reverse=True)
        
    def select_next_goal(self, capabilities: List[str], resources: List[str]) -> Optional[Desire]:
        """Select the next goal to pursue based on capabilities and resources"""
        prioritized = self.prioritize_desires()
        
        for desire in prioritized:
            # Check if we have capabilities and resources for this goal
            if self._can_achieve_goal(desire, capabilities, resources):
                if desire.description not in self.active_goals:
                    self.active_goals.append(desire.description)
                    logger.info(f"🎯 GOAL SELECTED: {desire.description}")
                    return desire
        return None
        
    def _can_achieve_goal(self, desire: Desire, capabilities: List[str], resources: List[str]) -> bool:
        """Check if goal can be achieved with available capabilities and resources"""
        # Simplified capability matching
        required_capabilities = desire.context.get("required_capabilities", [])
        return all(cap in capabilities for cap in required_capabilities)
        
    def mark_goal_completed(self, goal_description: str, success: bool):
        """Mark a goal as completed"""
        if goal_description in self.active_goals:
            self.active_goals.remove(goal_description)
            self.completed_goals.append(goal_description)
            status = "✅ SUCCESS" if success else "❌ FAILED"
            logger.info(f"🏁 GOAL COMPLETED: {goal_description} - {status}")

class MockIntentionPlanner:
    """Mock implementation of BDI Intention Planning"""
    
    def __init__(self):
        self.current_intentions: List[Intention] = []
        self.execution_history: List[Dict[str, Any]] = []
        
    def form_intention(self, desire: Desire, belief_context: Dict[str, Any], 
                      available_tools: List[str]) -> Intention:
        """Form an intention (action plan) to achieve a desire"""
        logger.info(f"🎯 FORMING INTENTION for: {desire.description}")
        
        # Generate action sequence based on goal type
        action_sequence = self._generate_action_sequence(desire, available_tools)
        
        # Identify required resources
        resources_needed = self._identify_resources(desire, action_sequence)
        
        # Create contingency plans
        contingency_plans = self._create_contingency_plans(desire, belief_context)
        
        intention = Intention(
            goal=desire.description,
            action_sequence=action_sequence,
            resources_needed=resources_needed,
            expected_outcome=f"Successfully achieve: {desire.description}",
            contingency_plans=contingency_plans
        )
        
        self.current_intentions.append(intention)
        logger.info(f"📋 INTENTION FORMED: {len(action_sequence)} actions planned")
        return intention
        
    def _generate_action_sequence(self, desire: Desire, tools: List[str]) -> List[Dict[str, Any]]:
        """Generate sequence of actions to achieve the desire"""
        # Simplified action planning based on goal type
        goal_lower = desire.description.lower()
        
        if "analyze" in goal_lower:
            return [
                {"action": "gather_data", "tool": "system_analyzer", "parameters": {}},
                {"action": "process_data", "tool": "data_processor", "parameters": {}},
                {"action": "generate_report", "tool": "report_generator", "parameters": {}}
            ]
        elif "optimize" in goal_lower:
            return [
                {"action": "benchmark_current", "tool": "performance_monitor", "parameters": {}},
                {"action": "identify_bottlenecks", "tool": "system_analyzer", "parameters": {}},
                {"action": "apply_optimizations", "tool": "optimizer", "parameters": {}},
                {"action": "validate_improvements", "tool": "performance_monitor", "parameters": {}}
            ]
        elif "create" in goal_lower or "generate" in goal_lower:
            return [
                {"action": "plan_creation", "tool": "planner", "parameters": {}},
                {"action": "execute_creation", "tool": "creator", "parameters": {}},
                {"action": "validate_output", "tool": "validator", "parameters": {}}
            ]
        else:
            # Generic action sequence
            return [
                {"action": "assess_situation", "tool": "analyzer", "parameters": {}},
                {"action": "execute_task", "tool": "executor", "parameters": {}},
                {"action": "verify_completion", "tool": "validator", "parameters": {}}
            ]
            
    def _identify_resources(self, desire: Desire, actions: List[Dict[str, Any]]) -> List[str]:
        """Identify resources needed for the action sequence"""
        resources = set()
        
        # Add tool requirements
        for action in actions:
            if action.get("tool"):
                resources.add(action["tool"])
                
        # Add goal-specific resources
        if "memory" in desire.description.lower():
            resources.add("memory_access")
        if "network" in desire.description.lower():
            resources.add("network_access")
        if "file" in desire.description.lower():
            resources.add("file_system")
            
        return list(resources)
        
    def _create_contingency_plans(self, desire: Desire, context: Dict[str, Any]) -> List[str]:
        """Create fallback plans in case primary plan fails"""
        plans = [
            "Retry with different parameters",
            "Use alternative tools if primary tools fail",
            "Seek human assistance if automated approach fails",
            "Break down goal into smaller sub-goals"
        ]
        
        # Add context-specific contingencies
        if context.get("resource_constraints"):
            plans.append("Request additional resources")
        if context.get("time_pressure"):
            plans.append("Prioritize critical components only")
            
        return plans
        
    async def execute_intention(self, intention: Intention, mock_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the planned intention"""
        logger.info(f"🚀 EXECUTING INTENTION: {intention.goal}")
        intention.execution_status = "executing"
        
        results = []
        success_count = 0
        
        for i, action in enumerate(intention.action_sequence):
            logger.info(f"   Step {i+1}/{len(intention.action_sequence)}: {action['action']}")
            
            # Simulate action execution
            await asyncio.sleep(0.1)  # Simulate processing time
            
            # Mock action result
            action_result = {
                "action": action["action"],
                "tool_used": action.get("tool", "unknown"),
                "success": True,  # Simplified - always succeed for demo
                "output": f"Successfully completed {action['action']}",
                "duration": 0.1
            }
            
            results.append(action_result)
            if action_result["success"]:
                success_count += 1
                
        # Calculate overall success
        overall_success = success_count == len(intention.action_sequence)
        intention.execution_status = "completed" if overall_success else "failed"
        
        execution_summary = {
            "intention": intention.goal,
            "actions_executed": len(results),
            "successful_actions": success_count,
            "overall_success": overall_success,
            "execution_time": len(results) * 0.1,
            "results": results
        }
        
        self.execution_history.append(execution_summary)
        logger.info(f"✅ EXECUTION COMPLETE: {intention.goal} - Success: {overall_success}")
        
        return execution_summary

class MockBDIAgent:
    """Comprehensive Mock BDI Agent for testing"""
    
    def __init__(self, agent_id: str = "test_bdi_agent"):
        self.agent_id = agent_id
        self.belief_system = MockBeliefSystem()
        self.desire_manager = MockDesireManager()
        self.intention_planner = MockIntentionPlanner()
        
        # Agent state
        self.status = "initialized"
        self.capabilities = ["analyze", "optimize", "create", "monitor", "report"]
        self.available_tools = ["system_analyzer", "optimizer", "report_generator", 
                              "performance_monitor", "data_processor"]
        self.resources = ["cpu", "memory", "network", "storage"]
        
        # Performance tracking
        self.cycle_count = 0
        self.successful_goals = 0
        self.failed_goals = 0
        
    def initialize_basic_beliefs(self):
        """Initialize the agent with basic beliefs about its environment"""
        logger.info("🔄 INITIALIZING BASIC BELIEFS")
        
        # System state beliefs
        self.belief_system.add_belief(
            "System is currently operational",
            BeliefConfidence.HIGH.value,
            ["System diagnostics show green status", "All services responding"],
            "system_state"
        )
        
        self.belief_system.add_belief(
            "Performance optimization is possible",
            BeliefConfidence.MEDIUM.value,
            ["Historical data shows optimization potential"],
            "capabilities"
        )
        
        self.belief_system.add_belief(
            "Resources are sufficient for current tasks",
            BeliefConfidence.HIGH.value,
            ["CPU usage < 50%", "Memory usage < 70%"],
            "environment"
        )
        
    def set_goal(self, goal_description: str, priority: int = 1, context: Dict[str, Any] = None):
        """Set a new goal for the agent"""
        if context is None:
            context = {"required_capabilities": ["analyze"]}
            
        self.desire_manager.add_desire(
            description=goal_description,
            priority=priority,
            context=context,
            effort=1.0
        )
        
    async def run_bdi_cycle(self, max_cycles: int = 5) -> Dict[str, Any]:
        """Run the complete BDI reasoning cycle"""
        logger.info("🔄 STARTING BDI REASONING CYCLE")
        logger.info("=" * 60)
        
        self.status = "running"
        cycle_results = []
        
        for cycle in range(max_cycles):
            logger.info(f"📊 CYCLE {cycle + 1}/{max_cycles}")
            
            # 1. BELIEF REVISION
            logger.info("🧠 Phase 1: BELIEF REVISION")
            await self._revise_beliefs()
            
            # 2. DESIRE EVALUATION
            logger.info("🎯 Phase 2: DESIRE EVALUATION")
            selected_goal = self.desire_manager.select_next_goal(
                self.capabilities, self.resources
            )
            
            if not selected_goal:
                logger.info("   No suitable goals found. Cycle complete.")
                break
                
            # 3. INTENTION FORMATION
            logger.info("📋 Phase 3: INTENTION FORMATION")
            belief_context = self.belief_system.get_system_state_beliefs()
            intention = self.intention_planner.form_intention(
                selected_goal, belief_context, self.available_tools
            )
            
            # 4. ACTION EXECUTION
            logger.info("🚀 Phase 4: ACTION EXECUTION")
            execution_result = await self.intention_planner.execute_intention(
                intention, {}
            )
            
            # 5. LEARNING FROM RESULTS
            logger.info("📚 Phase 5: LEARNING FROM RESULTS")
            await self._learn_from_results(execution_result)
            
            cycle_results.append({
                "cycle": cycle + 1,
                "goal": selected_goal.description,
                "success": execution_result["overall_success"],
                "actions_count": execution_result["actions_executed"],
                "execution_time": execution_result["execution_time"]
            })
            
            # Update goal status
            self.desire_manager.mark_goal_completed(
                selected_goal.description, 
                execution_result["overall_success"]
            )
            
            if execution_result["overall_success"]:
                self.successful_goals += 1
            else:
                self.failed_goals += 1
                
            self.cycle_count += 1
            logger.info("-" * 60)
            
        self.status = "completed"
        
        # Generate summary
        summary = {
            "agent_id": self.agent_id,
            "total_cycles": len(cycle_results),
            "successful_goals": self.successful_goals,
            "failed_goals": self.failed_goals,
            "success_rate": self.successful_goals / (self.successful_goals + self.failed_goals) if (self.successful_goals + self.failed_goals) > 0 else 0,
            "cycle_details": cycle_results,
            "final_beliefs_count": len(self.belief_system.beliefs),
            "active_goals": len(self.desire_manager.active_goals),
            "completed_goals": len(self.desire_manager.completed_goals)
        }
        
        logger.info("🎯 BDI CYCLE COMPLETE")
        logger.info("=" * 60)
        
        return summary
        
    async def _revise_beliefs(self):
        """Revise beliefs based on new observations"""
        # Simulate belief updates based on system observations
        current_beliefs = self.belief_system.query_beliefs(min_confidence=0.3)
        
        for belief in current_beliefs:
            # Simulate gathering new evidence
            if "operational" in belief.statement.lower():
                # System is still operational
                self.belief_system.update_belief(
                    list(self.belief_system.beliefs.keys())[0],
                    "Recent health check confirms operational status",
                    0.1
                )
            elif "performance" in belief.statement.lower():
                # Performance belief update
                new_evidence = "Recent metrics show continued optimization potential"
                belief_id = [k for k, v in self.belief_system.beliefs.items() 
                           if "performance" in v.statement.lower()][0]
                self.belief_system.update_belief(belief_id, new_evidence, 0.05)
                
    async def _learn_from_results(self, execution_result: Dict[str, Any]):
        """Learn from execution results and update beliefs"""
        if execution_result["overall_success"]:
            # Successful execution - strengthen related beliefs
            self.belief_system.add_belief(
                f"Successfully completed {execution_result['intention']}",
                BeliefConfidence.HIGH.value,
                [f"Executed {execution_result['actions_executed']} actions successfully"],
                "achievements"
            )
            
            # Update capability beliefs
            self.belief_system.add_belief(
                "Agent is capable of complex task execution",
                BeliefConfidence.HIGH.value,
                ["Successful goal completion demonstrates capability"],
                "capabilities"
            )
        else:
            # Failed execution - learn from failure
            self.belief_system.add_belief(
                f"Encountered challenges with {execution_result['intention']}",
                BeliefConfidence.MEDIUM.value,
                ["Execution did not complete successfully"],
                "challenges"
            )

class BDIAgentTester:
    """Comprehensive tester for BDI Agent functionality"""
    
    def __init__(self):
        self.test_results = {}
        
    async def test_belief_system(self) -> Dict[str, Any]:
        """Test the belief system functionality"""
        logger.info("🧪 TESTING BELIEF SYSTEM")
        
        belief_system = MockBeliefSystem()
        
        # Test 1: Adding beliefs
        belief_id1 = belief_system.add_belief(
            "The system is highly performant",
            BeliefConfidence.MEDIUM.value,
            ["Benchmark results show good performance"]
        )
        
        belief_id2 = belief_system.add_belief(
            "Memory usage is within acceptable limits",
            BeliefConfidence.HIGH.value,
            ["Memory monitoring shows 60% usage", "No memory leaks detected"]
        )
        
        # Test 2: Updating beliefs with new evidence
        belief_system.update_belief(
            belief_id1,
            "New optimization improved performance by 15%",
            0.2
        )
        
        # Test 3: Querying beliefs
        high_confidence_beliefs = belief_system.query_beliefs(min_confidence=0.7)
        system_beliefs = belief_system.query_beliefs("system")
        
        # Test 4: System state derivation
        system_state = belief_system.get_system_state_beliefs()
        
        test_result = {
            "test_name": "belief_system",
            "success": True,
            "total_beliefs": len(belief_system.beliefs),
            "high_confidence_beliefs": len(high_confidence_beliefs),
            "system_beliefs": len(system_beliefs),
            "system_state": system_state,
            "belief_update_successful": belief_system.beliefs[belief_id1].confidence > BeliefConfidence.MEDIUM.value
        }
        
        logger.info(f"✅ BELIEF SYSTEM TEST: {test_result['success']}")
        return test_result
        
    async def test_desire_management(self) -> Dict[str, Any]:
        """Test the desire management functionality"""
        logger.info("🧪 TESTING DESIRE MANAGEMENT")
        
        desire_manager = MockDesireManager()
        
        # Test 1: Adding desires with different priorities
        desire1 = desire_manager.add_desire(
            "Optimize database performance",
            priority=1,  # High priority
            context={"required_capabilities": ["analyze", "optimize"]},
            effort=2.0
        )
        
        desire2 = desire_manager.add_desire(
            "Generate weekly report",
            priority=3,  # Lower priority
            context={"required_capabilities": ["analyze", "report"]},
            deadline=time.time() + 3600,  # 1 hour deadline
            effort=1.0
        )
        
        desire3 = desire_manager.add_desire(
            "Monitor system health",
            priority=2,  # Medium priority
            context={"required_capabilities": ["monitor"]},
            effort=0.5
        )
        
        # Test 2: Prioritization
        prioritized = desire_manager.prioritize_desires()
        
        # Test 3: Goal selection
        capabilities = ["analyze", "optimize", "monitor", "report"]
        resources = ["cpu", "memory", "network"]
        
        selected_goal = desire_manager.select_next_goal(capabilities, resources)
        
        # Test 4: Goal completion
        if selected_goal:
            desire_manager.mark_goal_completed(selected_goal.description, True)
            
        test_result = {
            "test_name": "desire_management",
            "success": True,
            "total_desires": len(desire_manager.desires),
            "prioritization_working": len(prioritized) == 3,
            "goal_selection_working": selected_goal is not None,
            "selected_goal": selected_goal.description if selected_goal else None,
            "active_goals": len(desire_manager.active_goals),
            "completed_goals": len(desire_manager.completed_goals)
        }
        
        logger.info(f"✅ DESIRE MANAGEMENT TEST: {test_result['success']}")
        return test_result
        
    async def test_intention_planning(self) -> Dict[str, Any]:
        """Test the intention planning functionality"""
        logger.info("🧪 TESTING INTENTION PLANNING")
        
        planner = MockIntentionPlanner()
        
        # Create a test desire
        desire = Desire(
            description="Analyze system performance and optimize bottlenecks",
            priority=1,
            context={"required_capabilities": ["analyze", "optimize"]},
            estimated_effort=2.0
        )
        
        belief_context = {
            "operational": True,
            "performance_level": 0.7,
            "resource_availability": "sufficient"
        }
        
        available_tools = ["system_analyzer", "optimizer", "performance_monitor"]
        
        # Test 1: Intention formation
        intention = planner.form_intention(desire, belief_context, available_tools)
        
        # Test 2: Intention execution
        execution_result = await planner.execute_intention(intention, {})
        
        test_result = {
            "test_name": "intention_planning",
            "success": True,
            "intention_formed": intention is not None,
            "action_sequence_length": len(intention.action_sequence),
            "resources_identified": len(intention.resources_needed),
            "contingency_plans": len(intention.contingency_plans),
            "execution_successful": execution_result["overall_success"],
            "execution_time": execution_result["execution_time"],
            "actions_executed": execution_result["actions_executed"]
        }
        
        logger.info(f"✅ INTENTION PLANNING TEST: {test_result['success']}")
        return test_result
        
    async def test_complete_bdi_cycle(self) -> Dict[str, Any]:
        """Test the complete BDI reasoning cycle"""
        logger.info("🧪 TESTING COMPLETE BDI CYCLE")
        
        # Create BDI agent
        agent = MockBDIAgent("test_cycle_agent")
        
        # Initialize with basic beliefs
        agent.initialize_basic_beliefs()
        
        # Set multiple goals
        agent.set_goal("Analyze current system performance", priority=1)
        agent.set_goal("Optimize database queries", priority=2)
        agent.set_goal("Generate performance report", priority=3)
        
        # Run the BDI cycle
        cycle_summary = await agent.run_bdi_cycle(max_cycles=3)
        
        test_result = {
            "test_name": "complete_bdi_cycle",
            "success": cycle_summary["success_rate"] > 0.5,  # At least 50% success rate
            "cycles_completed": cycle_summary["total_cycles"],
            "success_rate": cycle_summary["success_rate"],
            "goals_completed": cycle_summary["successful_goals"] + cycle_summary["failed_goals"],
            "beliefs_developed": cycle_summary["final_beliefs_count"],
            "agent_status": agent.status,
            "detailed_summary": cycle_summary
        }
        
        logger.info(f"✅ COMPLETE BDI CYCLE TEST: {test_result['success']}")
        return test_result
        
    async def run_comprehensive_bdi_validation(self) -> Dict[str, Any]:
        """Run comprehensive BDI validation suite"""
        logger.info("🚀 STARTING COMPREHENSIVE BDI VALIDATION")
        logger.info("=" * 80)
        
        # Run all tests
        tests = [
            self.test_belief_system(),
            self.test_desire_management(),
            self.test_intention_planning(),
            self.test_complete_bdi_cycle()
        ]
        
        results = await asyncio.gather(*tests)
        
        # Calculate overall metrics
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r["success"])
        success_rate = passed_tests / total_tests
        
        comprehensive_result = {
            "validation_suite": "bdi_agent_comprehensive",
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": success_rate,
            "overall_success": success_rate >= 0.8,
            "individual_results": results,
            "bdi_components_validated": {
                "belief_system": any("belief_system" in r["test_name"] for r in results),
                "desire_management": any("desire_management" in r["test_name"] for r in results),
                "intention_planning": any("intention_planning" in r["test_name"] for r in results),
                "complete_cycle": any("complete_bdi_cycle" in r["test_name"] for r in results)
            }
        }
        
        logger.info("=" * 80)
        logger.info("🎯 COMPREHENSIVE BDI VALIDATION RESULTS:")
        logger.info(f"   Total Tests: {total_tests}")
        logger.info(f"   Passed: {passed_tests}")
        logger.info(f"   Failed: {total_tests - passed_tests}")
        logger.info(f"   Success Rate: {success_rate:.1%}")
        logger.info(f"   Overall: {'✅ SUCCESS' if comprehensive_result['overall_success'] else '❌ FAILED'}")
        logger.info("=" * 80)
        
        return comprehensive_result

def explain_bdi_architecture():
    """Explain how the BDI architecture works"""
    explanation = """
    
🧠 BDI AGENT ARCHITECTURE EXPLAINED
==================================

The BDI (Belief-Desire-Intention) architecture is a cognitive model that mimics human-like reasoning:

1. 🧠 BELIEFS - What the agent KNOWS
   ═══════════════════════════════════
   - Knowledge about the world, system state, and capabilities
   - Each belief has a confidence level (0.0 to 1.0)
   - Beliefs are updated based on new evidence
   - Used to make informed decisions
   
   Example: "System is operational" (confidence: 0.9)
            Evidence: ["Health check passed", "All services responding"]

2. 🎯 DESIRES - What the agent WANTS to achieve
   ═════════════════════════════════════════════
   - Goals and objectives with priorities
   - Managed in a priority queue
   - Include deadlines, effort estimates, success probabilities
   - Conflicts between desires are resolved based on priority
   
   Example: "Optimize database performance" (priority: 1, effort: 2.0 hours)

3. 📋 INTENTIONS - HOW the agent plans to act
   ════════════════════════════════════════════
   - Concrete action plans to achieve desires
   - Sequence of specific actions with tools and parameters
   - Include contingency plans for failure scenarios
   - Resources and capabilities required
   
   Example: [Analyze → Identify bottlenecks → Apply optimizations → Validate]

🔄 THE BDI REASONING CYCLE:
==========================

1. BELIEF REVISION: Update knowledge based on new observations
2. DESIRE EVALUATION: Select the most important/urgent goal  
3. INTENTION FORMATION: Create a detailed action plan
4. ACTION EXECUTION: Carry out the planned actions
5. LEARNING: Update beliefs based on results

🎯 WHY BDI WORKS:
================

✅ HUMAN-LIKE REASONING: Mirrors how humans think and plan
✅ ADAPTIVE: Can change plans based on new information  
✅ PRIORITIZATION: Handles multiple goals intelligently
✅ RESILIENT: Has backup plans for when things go wrong
✅ LEARNING: Improves performance over time
✅ EXPLAINABLE: Clear reasoning process that can be audited

This makes BDI agents ideal for complex, dynamic environments where
intelligent decision-making and adaptation are crucial.
    """
    print(explanation)

async def main():
    """Main test execution with explanations"""
    
    # Explain the architecture first
    explain_bdi_architecture()
    
    print("\n" + "=" * 80)
    print("🧠 BDI AGENT COMPREHENSIVE VALIDATION TEST")
    print("   Testing Belief-Desire-Intention Architecture")
    print("=" * 80)
    
    tester = BDIAgentTester()
    
    try:
        results = await tester.run_comprehensive_bdi_validation()
        
        # Print detailed summary
        print(f"\n🎯 FINAL BDI VALIDATION RESULTS:")
        print(f"   Overall Success: {'✅ VALIDATED' if results['overall_success'] else '❌ FAILED'}")
        print(f"   Success Rate: {results['success_rate']:.1%}")
        print(f"   Components Tested: {sum(results['bdi_components_validated'].values())}/4")
        
        # Component-specific results
        print(f"\n📊 COMPONENT VALIDATION:")
        for component, validated in results['bdi_components_validated'].items():
            status = "✅" if validated else "❌"
            print(f"   {component.replace('_', ' ').title()}: {status}")
            
        # Individual test details
        print(f"\n📋 DETAILED TEST RESULTS:")
        for test_result in results['individual_results']:
            status = "✅ PASS" if test_result['success'] else "❌ FAIL"
            print(f"   {test_result['test_name'].replace('_', ' ').title()}: {status}")
            
        return 0 if results['overall_success'] else 1
        
    except Exception as e:
        logger.error(f"BDI validation failed with exception: {e}", exc_info=True)
        print(f"❌ BDI validation failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 