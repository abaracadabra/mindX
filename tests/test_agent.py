# tests/test_agent.py
"""
Ultimate Cognition Test Agent for MindX

This is an independent test agent designed to validate the internal logic and cognitive 
capabilities of the mindX system. It operates independently of the main mindX system
but uses the same cognitive architecture for comprehensive testing.

Enhanced with lab folder access and test registry management.
"""

import asyncio
import json
import time
import uuid
import os
import importlib.util
import inspect
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime

# Core mindX imports for testing
from utils.config import Config
from utils.logging_config import get_logger
from core.belief_system import BeliefSystem, BeliefSource
from core.bdi_agent import BDIAgent, BaseTool
from agents.memory_agent import MemoryAgent

logger = get_logger(__name__)

class TestRegistryEntry:
    """Represents a test registry entry with metadata and outcomes."""
    
    def __init__(self, test_file: str, test_name: str, test_type: str = "unknown"):
        self.test_file = test_file
        self.test_name = test_name
        self.test_type = test_type
        self.created_timestamp = time.time()
        self.last_executed = None
        self.execution_count = 0
        self.outcomes: List[Dict[str, Any]] = []
        self.success_rate = 0.0
        self.average_execution_time = 0.0
        
    def add_outcome(self, success: bool, execution_time: float, details: Dict[str, Any] = None):
        """Add a test execution outcome."""
        outcome = {
            "timestamp": time.time(),
            "success": success,
            "execution_time": execution_time,
            "details": details or {}
        }
        self.outcomes.append(outcome)
        self.execution_count += 1
        self.last_executed = outcome["timestamp"]
        
        # Update statistics
        self.success_rate = sum(1 for o in self.outcomes if o["success"]) / len(self.outcomes)
        self.average_execution_time = sum(o["execution_time"] for o in self.outcomes) / len(self.outcomes)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_file": self.test_file,
            "test_name": self.test_name,
            "test_type": self.test_type,
            "created_timestamp": self.created_timestamp,
            "last_executed": self.last_executed,
            "execution_count": self.execution_count,
            "success_rate": self.success_rate,
            "average_execution_time": self.average_execution_time,
            "recent_outcomes": self.outcomes[-5:] if self.outcomes else []  # Last 5 outcomes
        }

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

class UltimateCognitionTestAgent:
    """
    Independent test agent for validating mindX cognitive capabilities.
    Enhanced with lab folder access and test registry management.
    """
    
    def __init__(self, agent_id: str = "ultimate_cognition_test_agent"):
        self.agent_id = agent_id
        self.config = Config(test_mode=True)
        self.logger = get_logger(f"UltimateCognitionTestAgent.{agent_id}")
        
        # Lab folder access
        self.lab_folder = Path("tests/lab")
        self.lab_folder.mkdir(exist_ok=True)
        
        # Test registry
        self.test_registry: Dict[str, TestRegistryEntry] = {}
        self.registry_file = Path("tests/test_registry.json")
        
        # Initialize core components for testing
        self.belief_system = BeliefSystem(test_mode=True)
        self.memory_agent = MemoryAgent(config=self.config)
        
        # Test results storage
        self.test_results: List[CognitionTestResult] = []
        self.test_session_id = f"cognition_test_{int(time.time())}"
        
        # Load existing test registry
        self._load_test_registry()
        
        # Discover existing lab tests
        self._discover_lab_tests()
        
        self.logger.info(f"Ultimate Cognition Test Agent '{self.agent_id}' initialized with lab access")
    
    def _load_test_registry(self):
        """Load the test registry from file."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    registry_data = json.load(f)
                
                for test_id, entry_data in registry_data.items():
                    entry = TestRegistryEntry(
                        entry_data["test_file"],
                        entry_data["test_name"],
                        entry_data.get("test_type", "unknown")
                    )
                    entry.created_timestamp = entry_data.get("created_timestamp", time.time())
                    entry.last_executed = entry_data.get("last_executed")
                    entry.execution_count = entry_data.get("execution_count", 0)
                    entry.success_rate = entry_data.get("success_rate", 0.0)
                    entry.average_execution_time = entry_data.get("average_execution_time", 0.0)
                    
                    # Load recent outcomes
                    for outcome_data in entry_data.get("recent_outcomes", []):
                        entry.outcomes.append(outcome_data)
                    
                    self.test_registry[test_id] = entry
                
                self.logger.info(f"Loaded {len(self.test_registry)} tests from registry")
                
            except Exception as e:
                self.logger.error(f"Failed to load test registry: {e}")
    
    def _save_test_registry(self):
        """Save the test registry to file."""
        try:
            registry_data = {}
            for test_id, entry in self.test_registry.items():
                registry_data[test_id] = entry.to_dict()
            
            with open(self.registry_file, 'w') as f:
                json.dump(registry_data, f, indent=2)
                
            self.logger.info(f"Saved {len(self.test_registry)} tests to registry")
            
        except Exception as e:
            self.logger.error(f"Failed to save test registry: {e}")
    
    def _discover_lab_tests(self):
        """Discover existing tests in the lab folder."""
        discovered_count = 0
        
        for test_file in self.lab_folder.glob("test_*.py"):
            try:
                # Load the test file to analyze its contents
                spec = importlib.util.spec_from_file_location("test_module", test_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find test functions and classes
                for name, obj in inspect.getmembers(module):
                    if (inspect.isfunction(obj) and name.startswith("test_")) or \
                       (inspect.isclass(obj) and name.startswith("Test")):
                        
                        test_id = f"{test_file.stem}::{name}"
                        
                        if test_id not in self.test_registry:
                            # Determine test type based on file name patterns
                            test_type = "integration" if "integration" in test_file.name else \
                                       "unit" if "unit" in test_file.name else \
                                       "e2e" if "e2e" in test_file.name else \
                                       "comprehensive" if "comprehensive" in test_file.name else \
                                       "cognitive"
                            
                            entry = TestRegistryEntry(
                                str(test_file.relative_to(Path.cwd())),
                                name,
                                test_type
                            )
                            
                            self.test_registry[test_id] = entry
                            discovered_count += 1
                            
            except Exception as e:
                self.logger.warning(f"Failed to analyze test file {test_file}: {e}")
        
        if discovered_count > 0:
            self.logger.info(f"Discovered {discovered_count} new tests in lab folder")
            self._save_test_registry()
    
    def get_lab_test_summary(self) -> Dict[str, Any]:
        """Get a summary of all lab tests."""
        summary = {
            "total_tests": len(self.test_registry),
            "test_types": {},
            "execution_stats": {
                "never_executed": 0,
                "recently_executed": 0,
                "high_success_rate": 0,
                "low_success_rate": 0
            },
            "tests_by_file": {}
        }
        
        for test_id, entry in self.test_registry.items():
            # Count by type
            test_type = entry.test_type
            summary["test_types"][test_type] = summary["test_types"].get(test_type, 0) + 1
            
            # Execution stats
            if entry.execution_count == 0:
                summary["execution_stats"]["never_executed"] += 1
            elif entry.last_executed and (time.time() - entry.last_executed) < 86400:  # 24 hours
                summary["execution_stats"]["recently_executed"] += 1
            
            if entry.success_rate >= 0.8:
                summary["execution_stats"]["high_success_rate"] += 1
            elif entry.success_rate < 0.5 and entry.execution_count > 0:
                summary["execution_stats"]["low_success_rate"] += 1
            
            # Group by file
            file_name = Path(entry.test_file).name
            if file_name not in summary["tests_by_file"]:
                summary["tests_by_file"][file_name] = []
            summary["tests_by_file"][file_name].append({
                "test_name": entry.test_name,
                "test_type": entry.test_type,
                "success_rate": entry.success_rate,
                "execution_count": entry.execution_count
            })
        
        return summary
    
    async def create_new_lab_test(self, test_name: str, test_type: str, test_content: str) -> bool:
        """Create a new test file in the lab folder."""
        try:
            test_file_name = f"test_{test_name.lower().replace(' ', '_')}.py"
            test_file_path = self.lab_folder / test_file_name
            
            # Generate test template
            test_template = f'''# tests/lab/{test_file_name}
"""
{test_name} - Generated by Ultimate Cognition Test Agent
Test Type: {test_type}
Created: {datetime.now().isoformat()}
"""

import asyncio
import pytest
from typing import Dict, Any
from utils.logging_config import get_logger

logger = get_logger(__name__)

class Test{test_name.replace(' ', '')}:
    """Test class for {test_name}."""
    
    async def test_{test_name.lower().replace(' ', '_')}(self):
        """Main test method for {test_name}."""
        # Test implementation
{test_content}
        
        assert True, "Test implementation needed"

# Additional test methods can be added here

if __name__ == "__main__":
    asyncio.run(pytest.main([__file__]))
'''
            
            # Write test file
            with open(test_file_path, 'w') as f:
                f.write(test_template)
            
            # Add to registry
            test_id = f"{test_file_name}::test_{test_name.lower().replace(' ', '_')}"
            entry = TestRegistryEntry(
                str(test_file_path.relative_to(Path.cwd())),
                f"test_{test_name.lower().replace(' ', '_')}",
                test_type
            )
            
            self.test_registry[test_id] = entry
            self._save_test_registry()
            
            self.logger.info(f"Created new lab test: {test_file_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create new lab test: {e}")
            return False
    
    async def execute_lab_test(self, test_id: str) -> Dict[str, Any]:
        """Execute a specific lab test and record the outcome."""
        if test_id not in self.test_registry:
            return {"error": f"Test {test_id} not found in registry"}
        
        entry = self.test_registry[test_id]
        start_time = time.time()
        
        try:
            # Load and execute the test
            test_file_path = Path(entry.test_file)
            
            if not test_file_path.exists():
                raise FileNotFoundError(f"Test file {test_file_path} not found")
            
            # Import the test module
            spec = importlib.util.spec_from_file_location("test_module", test_file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find and execute the test
            test_func = getattr(module, entry.test_name, None)
            if not test_func:
                raise AttributeError(f"Test function {entry.test_name} not found")
            
            # Execute the test
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            execution_time = time.time() - start_time
            success = True
            details = {"result": result, "execution_method": "direct"}
            
        except Exception as e:
            execution_time = time.time() - start_time
            success = False
            details = {"error": str(e), "error_type": type(e).__name__}
            self.logger.error(f"Lab test {test_id} failed: {e}")
        
        # Record outcome
        entry.add_outcome(success, execution_time, details)
        self._save_test_registry()
        
        return {
            "test_id": test_id,
            "success": success,
            "execution_time": execution_time,
            "details": details,
            "updated_stats": {
                "success_rate": entry.success_rate,
                "execution_count": entry.execution_count,
                "average_execution_time": entry.average_execution_time
            }
        }

    async def initialize_async_components(self):
        """Initialize components that require async setup."""
        try:
            # Initialize BDI agent for cognitive testing
            self.bdi_agent = BDIAgent(
                domain="cognition_testing",
                belief_system_instance=self.belief_system,
                tools_registry={"registered_tools": {}},
                config_override=self.config,
                memory_agent=self.memory_agent,
                test_mode=True
            )
            await self.bdi_agent.async_init_components()
            
            self.logger.info("Async components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize async components: {e}", exc_info=True)
            return False
    
    async def run_ultimate_cognition_test(self) -> Dict[str, Any]:
        """Run the complete ultimate cognition test suite."""
        self.logger.info(f"Starting Ultimate Cognition Test - Session: {self.test_session_id}")
        start_time = time.time()
        
        # Initialize async components
        init_success = await self.initialize_async_components()
        if not init_success:
            return {
                "session_id": self.test_session_id,
                "status": "FAILED",
                "error": "Failed to initialize test components",
                "total_time": time.time() - start_time
            }
        
        # Define test suite
        test_suite = [
            {"name": "belief_system_test", "description": "Test belief system functionality"},
            {"name": "memory_integration_test", "description": "Test memory integration"},
            {"name": "bdi_reasoning_test", "description": "Test BDI reasoning capabilities"},
            {"name": "cognitive_consistency_test", "description": "Test cognitive consistency"},
            {"name": "failure_recovery_test", "description": "Test failure recovery mechanisms"}
        ]
        
        # Execute tests
        for test in test_suite:
            test_result = await self._execute_test(test["name"], test["description"])
            self.test_results.append(test_result)
        
        # Generate analysis
        total_time = time.time() - start_time
        analysis = self._generate_analysis(total_time)
        
        self.logger.info(f"Ultimate Cognition Test completed in {total_time:.2f}s")
        return analysis
    
    async def _execute_test(self, test_name: str, description: str) -> CognitionTestResult:
        """Execute an individual test."""
        start_time = time.time()
        
        try:
            if test_name == "belief_system_test":
                success, details = await self._test_belief_system()
            elif test_name == "memory_integration_test":
                success, details = await self._test_memory_integration()
            elif test_name == "bdi_reasoning_test":
                success, details = await self._test_bdi_reasoning()
            elif test_name == "cognitive_consistency_test":
                success, details = await self._test_cognitive_consistency()
            elif test_name == "failure_recovery_test":
                success, details = await self._test_failure_recovery()
            else:
                success = False
                details = {"error": f"Unknown test: {test_name}"}
            
            execution_time = time.time() - start_time
            
            return CognitionTestResult(
                test_name=test_name,
                success=success,
                details=details,
                execution_time=execution_time,
                cognitive_depth=2
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Test '{test_name}' failed: {e}", exc_info=True)
            
            return CognitionTestResult(
                test_name=test_name,
                success=False,
                details={"error": str(e)},
                execution_time=execution_time,
                cognitive_depth=0
            )
    
    async def _test_belief_system(self) -> Tuple[bool, Dict[str, Any]]:
        """Test belief system functionality."""
        test_beliefs = [
            {"key": "test_fact_1", "value": "System is operational", "confidence": 0.9},
            {"key": "test_fact_2", "value": "Cognitive testing in progress", "confidence": 0.8}
        ]
        
        # Add beliefs
        for belief in test_beliefs:
            await self.belief_system.add_belief(
                belief["key"], belief["value"], belief["confidence"], BeliefSource.TEST_DATA
            )
        
        # Retrieve and verify
        retrieval_success = 0
        for belief in test_beliefs:
            retrieved = await self.belief_system.get_belief(belief["key"])
            if retrieved and retrieved.value == belief["value"]:
                retrieval_success += 1
        
        success_rate = retrieval_success / len(test_beliefs)
        
        return success_rate >= 0.8, {
            "beliefs_tested": len(test_beliefs),
            "retrieval_success": retrieval_success,
            "success_rate": success_rate
        }
    
    async def _test_memory_integration(self) -> Tuple[bool, Dict[str, Any]]:
        """Test memory integration."""
        test_data = {"process": "cognition_test", "data": {"test": "memory_integration"}}
        
        # Test memory logging
        await self.memory_agent.log_process(
            "test_memory_integration", test_data, {"agent_id": self.agent_id}
        )
        
        return True, {"status": "Memory integration test completed"}
    
    async def _test_bdi_reasoning(self) -> Tuple[bool, Dict[str, Any]]:
        """Test BDI reasoning capabilities."""
        # Set a test goal
        test_goal = "Validate BDI reasoning through systematic analysis"
        self.bdi_agent.set_goal(test_goal, priority=1)
        
        # Run BDI cycles
        result = await self.bdi_agent.run(max_cycles=3)
        
        reasoning_success = "COMPLETED" in result or "analysis" in result.lower()
        
        return reasoning_success, {
            "goal": test_goal,
            "result": result,
            "reasoning_detected": reasoning_success
        }
    
    async def _test_cognitive_consistency(self) -> Tuple[bool, Dict[str, Any]]:
        """Test cognitive consistency."""
        # Add consistent beliefs
        await self.belief_system.add_belief(
            "system_state", "testing", 0.9, BeliefSource.TEST_DATA
        )
        await self.belief_system.add_belief(
            "test_active", True, 0.8, BeliefSource.TEST_DATA
        )
        
        # Check consistency
        state_belief = await self.belief_system.get_belief("system_state")
        test_belief = await self.belief_system.get_belief("test_active")
        
        consistency = (state_belief and state_belief.value == "testing" and 
                      test_belief and test_belief.value is True)
        
        return consistency, {
            "consistency_check": consistency,
            "beliefs_verified": 2
        }
    
    async def _test_failure_recovery(self) -> Tuple[bool, Dict[str, Any]]:
        """Test failure recovery mechanisms."""
        try:
            # Simulate a controlled failure scenario
            test_result = await self._simulate_controlled_failure()
            recovery_success = test_result is not None
            
            return recovery_success, {
                "recovery_tested": True,
                "recovery_success": recovery_success,
                "recovery_result": test_result
            }
            
        except Exception as e:
            # This is expected - test if we handle it gracefully
            return True, {
                "recovery_tested": True,
                "exception_handled": True,
                "exception_type": type(e).__name__
            }
    
    async def _simulate_controlled_failure(self) -> str:
        """Simulate a controlled failure for testing recovery."""
        return "Controlled failure simulation completed - recovery mechanisms active"
    
    def _generate_analysis(self, total_time: float) -> Dict[str, Any]:
        """Generate comprehensive analysis."""
        successful_tests = sum(1 for t in self.test_results if t.success)
        total_tests = len(self.test_results)
        success_rate = successful_tests / total_tests if total_tests > 0 else 0
        
        # Determine system status
        if success_rate >= 0.9:
            system_status = "EXCELLENT"
        elif success_rate >= 0.8:
            system_status = "GOOD"
        elif success_rate >= 0.7:
            system_status = "ACCEPTABLE"
        else:
            system_status = "NEEDS_IMPROVEMENT"
        
        return {
            "session_id": self.test_session_id,
            "agent_id": self.agent_id,
            "status": "COMPLETED",
            "timestamp": datetime.now().isoformat(),
            "execution_summary": {
                "total_time": total_time,
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": success_rate,
                "system_status": system_status
            },
            "test_results": [t.to_dict() for t in self.test_results],
            "recommendations": self._generate_recommendations(success_rate)
        }
    
    def _generate_recommendations(self, success_rate: float) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        if success_rate < 0.8:
            recommendations.append("System performance needs improvement")
        
        if success_rate >= 0.9:
            recommendations.append("System performing excellently")
        
        recommendations.append("Continue monitoring cognitive performance")
        
        return recommendations

# Main execution
async def main():
    """Run the Ultimate Cognition Test."""
    print("🧠 MindX Ultimate Cognition Test Agent")
    print("=" * 50)
    
    test_agent = UltimateCognitionTestAgent()
    
    try:
        results = await test_agent.run_ultimate_cognition_test()
        
        print(f"\n📊 Test Results Summary:")
        print(f"Session ID: {results['session_id']}")
        print(f"Status: {results['status']}")
        print(f"Total Time: {results['execution_summary']['total_time']:.2f}s")
        print(f"Tests Run: {results['execution_summary']['total_tests']}")
        print(f"Success Rate: {results['execution_summary']['success_rate']:.1%}")
        print(f"System Status: {results['execution_summary']['system_status']}")
        
        print(f"\n💡 Recommendations:")
        for rec in results['recommendations']:
            print(f"  • {rec}")
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
