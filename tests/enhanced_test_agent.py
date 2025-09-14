# tests/enhanced_test_agent.py
"""
Enhanced Ultimate Cognition Test Agent for MindX

This is an enhanced test agent with lab folder access and test registry management.
It can review previous tests, create new ones, and maintain a comprehensive registry
of test outcomes and performance metrics.
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
            "recent_outcomes": self.outcomes[-5:] if self.outcomes else []
        }

class EnhancedUltimateCognitionTestAgent:
    """
    Enhanced test agent for validating mindX cognitive capabilities.
    Features lab folder access and comprehensive test registry management.
    """
    
    def __init__(self, agent_id: str = "enhanced_cognition_test_agent"):
        self.agent_id = agent_id
        self.config = Config(test_mode=True)
        self.logger = get_logger(f"EnhancedUltimateCognitionTestAgent.{agent_id}")
        
        # Lab folder access
        self.lab_folder = Path("lab")
        self.lab_folder.mkdir(exist_ok=True)
        
        # Test registry
        self.test_registry: Dict[str, TestRegistryEntry] = {}
        self.registry_file = Path("tests/test_registry.json")
        
        # Initialize core components for testing
        self.belief_system = BeliefSystem(test_mode=True)
        self.memory_agent = MemoryAgent(config=self.config)
        
        # Test results storage
        self.test_results = []
        self.test_session_id = f"cognition_test_{int(time.time())}"
        
        # Load existing test registry
        self._load_test_registry()
        
        # Discover existing lab tests
        self._discover_lab_tests()
        
        self.logger.info(f"Enhanced Ultimate Cognition Test Agent '{self.agent_id}' initialized with lab access")
    
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

async def main():
    """Main function to run the enhanced ultimate cognition test."""
    agent = EnhancedUltimateCognitionTestAgent()
    
    print("Enhanced Ultimate Cognition Test Agent")
    print("=====================================")
    
    # Show lab test summary
    lab_summary = agent.get_lab_test_summary()
    print(f"\nLab Test Summary:")
    print(f"Total tests: {lab_summary['total_tests']}")
    print(f"Test types: {lab_summary['test_types']}")
    print(f"Never executed: {lab_summary['execution_stats']['never_executed']}")
    
    return agent

if __name__ == "__main__":
    asyncio.run(main())
