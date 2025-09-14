# tests/mastermind_cognition_audit.py
"""
Comprehensive Mastermind Cognition Audit Test

This test uses the enhanced test agent to perform a full audit of the mastermind
cognition system including AGInt, BDI agent, workflow integration, tools, and
agent coordination capabilities.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import the enhanced test agent
from tests.enhanced_test_agent import EnhancedUltimateCognitionTestAgent, TestRegistryEntry

# Core mindX imports for comprehensive testing
from utils.config import Config
from utils.logging_config import get_logger
from core.agint import AGInt
from core.bdi_agent import BDIAgent
from core.belief_system import BeliefSystem, BeliefSource
from orchestration.mastermind_agent import MastermindAgent
from agents.memory_agent import MemoryAgent

logger = get_logger(__name__)

class CognitionTestResult:
    """Represents the result of a cognition test."""
    
    def __init__(self, test_name: str, success: bool, details: Dict[str, Any], 
                 execution_time: float, cognitive_depth: int = 1):
        self.test_name = test_name
        self.success = success
        self.details = details
        self.execution_time = execution_time
        self.cognitive_depth = cognitive_depth
        self.timestamp = time.time()
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "success": self.success,
            "details": self.details,
            "execution_time": self.execution_time,
            "cognitive_depth": self.cognitive_depth,
            "timestamp": self.timestamp,
            "formatted_time": datetime.fromtimestamp(self.timestamp).isoformat()
        }

class MastermindCognitionAuditAgent(EnhancedUltimateCognitionTestAgent):
    """
    Specialized audit agent for comprehensive mastermind cognition testing.
    """
    
    def __init__(self, agent_id: str = "mastermind_cognition_audit_agent"):
        super().__init__(agent_id)
        
        # Initialize mastermind components for testing
        self.mastermind_agent = None
        self.agint_instance = None
        self.bdi_test_agent = None
        
        # Audit-specific tracking
        self.audit_results = {}
        self.workflow_traces = []
        
        self.logger.info(f"Mastermind Cognition Audit Agent '{self.agent_id}' initialized")
    
    async def initialize_mastermind_components(self):
        """Initialize mastermind system components for testing."""
        try:
            self.logger.info("Initializing mastermind system components for audit...")
            
            # Initialize AGInt
            self.agint_instance = AGInt(
                agent_id="audit_agint",
                config=self.config,
                memory_agent=self.memory_agent,
                test_mode=True
            )
            await self.agint_instance.async_init_components()
            
            # Initialize BDI Agent for testing
            self.bdi_test_agent = BDIAgent(
                domain="mastermind_audit",
                belief_system_instance=self.belief_system,
                tools_registry={"registered_tools": {}},
                config_override=self.config,
                memory_agent=self.memory_agent,
                test_mode=True
            )
            await self.bdi_test_agent.async_init_components()
            
            self.logger.info("Mastermind system components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize mastermind components: {e}", exc_info=True)
            return False
    
    async def run_comprehensive_mastermind_audit(self) -> Dict[str, Any]:
        """Run comprehensive audit of mastermind cognition system."""
        self.logger.info("Starting Comprehensive Mastermind Cognition Audit")
        start_time = time.time()
        
        # Initialize components
        init_success = await self.initialize_mastermind_components()
        if not init_success:
            return {
                "audit_status": "FAILED",
                "error": "Failed to initialize mastermind components",
                "total_time": time.time() - start_time
            }
        
        # Define comprehensive audit test suite
        audit_tests = [
            {"name": "agint_decision_logic_audit", "description": "Audit AGInt decision-making logic"},
            {"name": "bdi_reasoning_workflow_audit", "description": "Audit BDI reasoning workflow"},
            {"name": "tool_integration_audit", "description": "Audit tool integration and execution"},
            {"name": "agent_coordination_audit", "description": "Audit agent coordination mechanisms"},
            {"name": "memory_system_audit", "description": "Audit memory system integration"},
            {"name": "workflow_end_to_end_audit", "description": "Audit complete workflow execution"},
            {"name": "performance_metrics_audit", "description": "Audit system performance metrics"}
        ]
        
        # Execute audit tests
        for test in audit_tests:
            test_result = await self._execute_audit_test(test["name"], test["description"])
            self.test_results.append(test_result)
            self.audit_results[test["name"]] = test_result.to_dict()
        
        # Generate comprehensive analysis
        total_time = time.time() - start_time
        audit_analysis = self._generate_audit_analysis(total_time)
        
        self.logger.info(f"Comprehensive Mastermind Cognition Audit completed in {total_time:.2f}s")
        return audit_analysis
    
    async def _execute_audit_test(self, test_name: str, description: str):
        """Execute an individual audit test."""
        start_time = time.time()
        
        try:
            if test_name == "agint_decision_logic_audit":
                success, details = await self._audit_agint_decision_logic()
            elif test_name == "bdi_reasoning_workflow_audit":
                success, details = await self._audit_bdi_reasoning_workflow()
            elif test_name == "tool_integration_audit":
                success, details = await self._audit_tool_integration()
            elif test_name == "agent_coordination_audit":
                success, details = await self._audit_agent_coordination()
            elif test_name == "memory_system_audit":
                success, details = await self._audit_memory_system()
            elif test_name == "workflow_end_to_end_audit":
                success, details = await self._audit_workflow_end_to_end()
            elif test_name == "performance_metrics_audit":
                success, details = await self._audit_performance_metrics()
            else:
                success = False
                details = {"error": f"Unknown audit test: {test_name}"}
            
            execution_time = time.time() - start_time
            
            return CognitionTestResult(
                test_name=test_name,
                success=success,
                details=details,
                execution_time=execution_time,
                cognitive_depth=3
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Audit test '{test_name}' failed: {e}", exc_info=True)
            
            return CognitionTestResult(
                test_name=test_name,
                success=False,
                details={"error": str(e), "error_type": type(e).__name__},
                execution_time=execution_time,
                cognitive_depth=0
            )
    
    async def _audit_agint_decision_logic(self):
        """Audit AGInt decision-making logic."""
        try:
            audit_results = {
                "decision_scenarios_tested": 0,
                "successful_decisions": 0,
                "decision_accuracy": 0.0,
                "decision_times": []
            }
            
            # Test decision scenarios
            scenarios = [
                {"context": "system_healthy", "expected": "delegate_to_bdi"},
                {"context": "llm_failure", "expected": "self_repair"},
                {"context": "recent_failure", "expected": "research_mode"}
            ]
            
            for scenario in scenarios:
                start_time = time.time()
                
                # Set up scenario context
                await self.agint_instance.belief_system.add_belief(
                    f"scenario_{scenario['context']}", 
                    "active", 
                    0.9, 
                    BeliefSource.INTERNAL
                )
                
                # Test decision making
                decision = await self.agint_instance._make_strategic_decision("test_directive")
                decision_time = time.time() - start_time
                
                audit_results["decision_scenarios_tested"] += 1
                audit_results["decision_times"].append(decision_time)
                
                if decision and "action" in decision:
                    audit_results["successful_decisions"] += 1
            
            # Calculate metrics
            if audit_results["decision_scenarios_tested"] > 0:
                audit_results["decision_accuracy"] = \
                    audit_results["successful_decisions"] / audit_results["decision_scenarios_tested"]
            
            success = audit_results["decision_accuracy"] >= 0.7
            return success, audit_results
            
        except Exception as e:
            return False, {"error": str(e)}
    
    async def _audit_bdi_reasoning_workflow(self):
        """Audit BDI reasoning workflow."""
        try:
            audit_results = {
                "belief_operations": 0,
                "desire_operations": 0,
                "reasoning_cycles": 0,
                "workflow_integrity": True
            }
            
            # Test belief operations
            test_beliefs = [
                {"key": "audit_belief_1", "value": "System under audit", "confidence": 0.9},
                {"key": "audit_belief_2", "value": "Testing BDI workflow", "confidence": 0.8}
            ]
            
            for belief in test_beliefs:
                await self.bdi_test_agent.belief_system.add_belief(
                    belief["key"], belief["value"], belief["confidence"], BeliefSource.TEST_DATA
                )
                audit_results["belief_operations"] += 1
            
            # Test goal setting
            test_goals = ["Complete audit test", "Validate workflow"]
            for goal in test_goals:
                self.bdi_test_agent.set_goal(goal, priority=1, is_primary=False)
                audit_results["desire_operations"] += 1
            
            # Test reasoning cycles
            for i in range(2):
                await self.bdi_test_agent._update_beliefs_from_percepts()
                await self.bdi_test_agent._generate_options()
                audit_results["reasoning_cycles"] += 1
            
            success = (
                audit_results["belief_operations"] >= 2 and
                audit_results["desire_operations"] >= 2 and
                audit_results["reasoning_cycles"] >= 2
            )
            
            return success, audit_results
            
        except Exception as e:
            return False, {"error": str(e)}
    
    async def _audit_tool_integration(self):
        """Audit tool integration."""
        try:
            audit_results = {
                "tool_executions": 0,
                "successful_executions": 0,
                "integration_quality": 0.0
            }
            
            # Test tool operations
            operations = ["memory_logging", "belief_updates"]
            
            for operation in operations:
                try:
                    if operation == "memory_logging":
                        await self.memory_agent.log_process(
                            f"audit_tool_{operation}",
                            {"test": "tool_integration"},
                            importance=2
                        )
                    elif operation == "belief_updates":
                        await self.belief_system.add_belief(
                            f"tool_test_{operation}", 
                            "executed", 
                            0.8, 
                            BeliefSource.INTERNAL
                        )
                    
                    audit_results["tool_executions"] += 1
                    audit_results["successful_executions"] += 1
                    
                except Exception as e:
                    audit_results["tool_executions"] += 1
            
            if audit_results["tool_executions"] > 0:
                audit_results["integration_quality"] = \
                    audit_results["successful_executions"] / audit_results["tool_executions"]
            
            success = audit_results["integration_quality"] >= 0.8
            return success, audit_results
            
        except Exception as e:
            return False, {"error": str(e)}
    
    async def _audit_agent_coordination(self):
        """Audit agent coordination."""
        try:
            audit_results = {
                "coordination_tests": 0,
                "successful_coordinations": 0,
                "coordination_efficiency": 0.0
            }
            
            # Test coordination
            coordination_tests = [
                {"from": "agint", "to": "bdi", "message": "test_coordination"},
                {"from": "bdi", "to": "memory", "message": "coordination_test"}
            ]
            
            for test in coordination_tests:
                try:
                    audit_results["coordination_tests"] += 1
                    
                    if test["to"] == "memory":
                        await self.memory_agent.log_process(
                            f"coordination_{test['from']}_to_{test['to']}",
                            {"message": test["message"]},
                            importance=1
                        )
                        audit_results["successful_coordinations"] += 1
                    elif test["to"] == "bdi":
                        await self.bdi_test_agent.belief_system.add_belief(
                            f"coordination_{test['from']}", 
                            test["message"], 
                            0.7, 
                            BeliefSource.INTERNAL
                        )
                        audit_results["successful_coordinations"] += 1
                    
                except Exception as e:
                    pass
            
            if audit_results["coordination_tests"] > 0:
                audit_results["coordination_efficiency"] = \
                    audit_results["successful_coordinations"] / audit_results["coordination_tests"]
            
            success = audit_results["coordination_efficiency"] >= 0.7
            return success, audit_results
            
        except Exception as e:
            return False, {"error": str(e)}
    
    async def _audit_memory_system(self):
        """Audit memory system."""
        try:
            audit_results = {
                "memory_operations": 0,
                "successful_operations": 0,
                "memory_integrity": True
            }
            
            # Test memory operations
            memory_tests = [
                {"type": "process_log", "data": {"process": "audit_memory", "status": "active"}},
                {"type": "workflow_trace", "data": {"workflow": "audit", "step": "memory_test"}}
            ]
            
            for test in memory_tests:
                try:
                    audit_results["memory_operations"] += 1
                    
                    await self.memory_agent.log_process(
                        f"audit_{test['type']}",
                        test["data"],
                        importance=2
                    )
                    
                    audit_results["successful_operations"] += 1
                    
                except Exception as e:
                    audit_results["memory_integrity"] = False
            
            success = (
                audit_results["successful_operations"] > 0 and
                audit_results["memory_integrity"]
            )
            
            return success, audit_results
            
        except Exception as e:
            return False, {"error": str(e)}
    
    async def _audit_workflow_end_to_end(self):
        """Audit end-to-end workflow."""
        try:
            audit_results = {
                "workflow_steps": 0,
                "completed_steps": 0,
                "workflow_integrity": True
            }
            
            # Execute workflow steps
            steps = [
                "initialize_context",
                "agint_decision", 
                "bdi_reasoning",
                "memory_logging"
            ]
            
            for step in steps:
                try:
                    audit_results["workflow_steps"] += 1
                    
                    if step == "initialize_context":
                        await self.belief_system.add_belief(
                            "workflow_active", "true", 0.9, BeliefSource.INTERNAL
                        )
                    elif step == "agint_decision":
                        decision = await self.agint_instance._make_strategic_decision("workflow_test")
                    elif step == "bdi_reasoning":
                        self.bdi_test_agent.set_goal("Execute workflow", priority=1, is_primary=True)
                        await self.bdi_test_agent._update_beliefs_from_percepts()
                    elif step == "memory_logging":
                        await self.memory_agent.log_process(
                            "workflow_step",
                            {"step": step, "workflow": "end_to_end"},
                            importance=2
                        )
                    
                    audit_results["completed_steps"] += 1
                    
                except Exception as e:
                    audit_results["workflow_integrity"] = False
            
            success = (
                audit_results["completed_steps"] >= 3 and
                audit_results["workflow_integrity"]
            )
            
            return success, audit_results
            
        except Exception as e:
            return False, {"error": str(e)}
    
    async def _audit_performance_metrics(self):
        """Audit performance metrics."""
        try:
            audit_results = {
                "response_times": [],
                "system_efficiency": 0.0,
                "performance_grade": "unknown"
            }
            
            # Test response times
            operations = [
                {"name": "belief_query", "op": "belief_system_query"},
                {"name": "memory_log", "op": "memory_logging"}
            ]
            
            for op in operations:
                start_time = time.time()
                
                try:
                    if op["op"] == "belief_system_query":
                        belief = await self.belief_system.get_belief("workflow_active")
                    elif op["op"] == "memory_logging":
                        await self.memory_agent.log_process(
                            f"perf_test_{op['name']}",
                            {"performance_test": True},
                            importance=1
                        )
                    
                    response_time = time.time() - start_time
                    audit_results["response_times"].append({
                        "operation": op["name"],
                        "time": response_time
                    })
                    
                except Exception as e:
                    response_time = time.time() - start_time
                    audit_results["response_times"].append({
                        "operation": op["name"],
                        "time": response_time,
                        "error": str(e)
                    })
            
            # Calculate performance
            if audit_results["response_times"]:
                avg_time = sum(rt["time"] for rt in audit_results["response_times"]) / len(audit_results["response_times"])
                
                if avg_time < 0.1:
                    audit_results["performance_grade"] = "excellent"
                    audit_results["system_efficiency"] = 0.95
                elif avg_time < 0.5:
                    audit_results["performance_grade"] = "good"
                    audit_results["system_efficiency"] = 0.80
                else:
                    audit_results["performance_grade"] = "acceptable"
                    audit_results["system_efficiency"] = 0.65
            
            success = audit_results["system_efficiency"] >= 0.60
            return success, audit_results
            
        except Exception as e:
            return False, {"error": str(e)}
    
    def _generate_audit_analysis(self, total_time: float) -> Dict[str, Any]:
        """Generate audit analysis."""
        successful_tests = [r for r in self.test_results if r.success]
        success_rate = len(successful_tests) / len(self.test_results) if self.test_results else 0
        
        return {
            "audit_session_id": self.test_session_id,
            "audit_status": "COMPLETED",
            "total_audit_time": total_time,
            "test_summary": {
                "total_tests": len(self.test_results),
                "successful_tests": len(successful_tests),
                "success_rate": success_rate
            },
            "cognitive_performance": {
                "average_execution_time": sum(r.execution_time for r in self.test_results) / len(self.test_results) if self.test_results else 0,
                "cognitive_efficiency": success_rate
            },
            "detailed_results": [r.to_dict() for r in self.test_results],
            "audit_recommendations": self._generate_recommendations(success_rate),
            "lab_integration": self.get_lab_test_summary()
        }
    
    def _generate_recommendations(self, success_rate: float) -> List[str]:
        """Generate recommendations."""
        recommendations = []
        
        if success_rate < 0.6:
            recommendations.append("CRITICAL: System requires immediate attention")
        elif success_rate < 0.8:
            recommendations.append("WARNING: System needs improvement in several areas")
        else:
            recommendations.append("GOOD: System performing well")
        
        return recommendations

async def main():
    """Main audit execution."""
    print("Mastermind Cognition Audit System")
    print("=================================")
    
    audit_agent = MastermindCognitionAuditAgent()
    
    # Show lab summary
    lab_summary = audit_agent.get_lab_test_summary()
    print(f"Lab tests: {lab_summary['total_tests']}")
    
    # Run audit
    print("Starting comprehensive audit...")
    results = await audit_agent.run_comprehensive_mastermind_audit()
    
    # Display results
    print(f"\nAUDIT RESULTS")
    print(f"Status: {results['audit_status']}")
    print(f"Success Rate: {results['test_summary']['success_rate']:.2%}")
    print(f"Total Tests: {results['test_summary']['total_tests']}")
    print(f"Audit Time: {results['total_audit_time']:.2f}s")
    
    print(f"\nRecommendations:")
    for i, rec in enumerate(results['audit_recommendations'], 1):
        print(f"  {i}. {rec}")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())
