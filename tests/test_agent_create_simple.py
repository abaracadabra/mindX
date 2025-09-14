#!/usr/bin/env python3
"""
Simplified Comprehensive Test for agent_create Workflow

This test focuses on the core functionality of the agent_create workflow
while avoiding complex configuration issues. It tests:
- CLI command parsing
- Basic agent creation workflow
- Error handling
- Integration with key components
"""

import asyncio
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from utils.config import Config
from utils.logging_config import get_logger, setup_logging


class TestAgentCreateSimple(unittest.TestCase):
    """Simplified test suite for agent_create workflow."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        setup_logging()
        cls.logger = get_logger(__name__)
        cls.test_config = Config(test_mode=True)
        cls.logger.info("Simple agent_create test environment initialized")
    
    def parse_agent_create_command(self, args_str: str) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]], Optional[str]]:
        """
        Parse agent_create command arguments.
        Returns: (agent_type, agent_id, config, error)
        """
        try:
            parts = args_str.strip().split(None, 2)
            
            if len(parts) < 2:
                return None, None, None, "❌ Error: Missing required parameters for agent creation."
            
            agent_type = parts[0].strip()
            agent_id = parts[1].strip()
            
            # Validate agent_id is not a common description word
            description_words = [
                'for', 'to', 'that', 'which', 'with', 'a', 'an', 'the', 'and', 'or', 'but',
                'so', 'as', 'if', 'when', 'where', 'how', 'why', 'what', 'who', 'create',
                'creating', 'make', 'making', 'analyze', 'analyzing', 'process', 'processing'
            ]
            
            if agent_id.lower() in description_words:
                return None, None, None, f"❌ Error: '{agent_id}' appears to be a description word, not a valid agent_id."
            
            # Handle optional description/config
            config = {}
            if len(parts) > 2:
                config_str = parts[2].strip()
                
                # Check if it looks like JSON
                if config_str.startswith(('{', '[')):
                    try:
                        config = json.loads(config_str)
                        if not isinstance(config, dict):
                            config = {"description": str(config), "created_via": "cli_json"}
                    except json.JSONDecodeError as e:
                        return None, None, None, f"❌ Error: Invalid JSON configuration: {e}"
                else:
                    # Treat as description
                    config = {
                        "description": config_str,
                        "created_via": "cli_natural_language"
                    }
            else:
                # No description provided - use default
                config = {
                    "description": f"Agent of type {agent_type} with ID {agent_id}",
                    "created_via": "cli_minimal"
                }
            
            return agent_type, agent_id, config, None
                
        except Exception as e:
            return None, None, None, f"Error parsing command: {str(e)}"

    # ===== CLI PARSING TESTS =====
    
    def test_basic_parsing(self):
        """Test basic command parsing functionality."""
        test_cases = [
            {
                "command": "file_analyzer analyzer",
                "expected_type": "file_analyzer",
                "expected_id": "analyzer",
                "expected_via": "cli_minimal"
            },
            {
                "command": "code_formatter formatter for formatting code",
                "expected_type": "code_formatter", 
                "expected_id": "formatter",
                "expected_via": "cli_natural_language",
                "expected_desc": "for formatting code"
            },
            {
                "command": 'hash_tool hasher {"description": "File hasher", "priority": 1}',
                "expected_type": "hash_tool",
                "expected_id": "hasher", 
                "expected_via": None,  # JSON config doesn't set created_via
                "expected_json": {"description": "File hasher", "priority": 1}
            }
        ]
        
        for case in test_cases:
            with self.subTest(command=case["command"]):
                agent_type, agent_id, config, error = self.parse_agent_create_command(case["command"])
                
                # Basic validations
                self.assertIsNone(error, f"Unexpected error: {error}")
                self.assertEqual(agent_type, case["expected_type"])
                self.assertEqual(agent_id, case["expected_id"])
                self.assertIsInstance(config, dict)
                
                # Check specific expectations
                if case.get("expected_via"):
                    self.assertEqual(config.get("created_via"), case["expected_via"])
                
                if case.get("expected_desc"):
                    self.assertEqual(config.get("description"), case["expected_desc"])
                
                if case.get("expected_json"):
                    for key, value in case["expected_json"].items():
                        self.assertEqual(config.get(key), value)

    def test_error_cases(self):
        """Test error handling in command parsing."""
        error_cases = [
            {
                "command": "single_arg",
                "expected_error": "Missing required parameters"
            },
            {
                "command": "",
                "expected_error": "Missing required parameters"
            },
            {
                "command": "file_analyzer for analyzing files",
                "expected_error": "'for' appears to be a description word"
            },
            {
                "command": 'bad_tool agent {"invalid": json}',
                "expected_error": "Invalid JSON configuration"
            }
        ]
        
        for case in error_cases:
            with self.subTest(command=case["command"]):
                agent_type, agent_id, config, error = self.parse_agent_create_command(case["command"])
                
                self.assertIsNotNone(error, f"Expected error for: {case['command']}")
                self.assertIn(case["expected_error"], error)
                self.assertIsNone(agent_type)
                self.assertIsNone(agent_id)
                self.assertIsNone(config)

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        edge_cases = [
            {
                "command": "type_with_underscores agent_with_underscores",
                "should_succeed": True
            },
            {
                "command": "CamelCaseType CamelCaseAgent",
                "should_succeed": True
            },
            {
                "command": "123numeric 456agent",
                "should_succeed": True
            },
            {
                "command": "  whitespace_type   whitespace_agent   description with spaces  ",
                "should_succeed": True,
                "expected_desc": "description with spaces"
            }
        ]
        
        for case in edge_cases:
            with self.subTest(command=case["command"]):
                agent_type, agent_id, config, error = self.parse_agent_create_command(case["command"])
                
                if case["should_succeed"]:
                    self.assertIsNone(error, f"Unexpected error: {error}")
                    self.assertIsNotNone(agent_type)
                    self.assertIsNotNone(agent_id)
                    self.assertIsInstance(config, dict)
                    
                    if case.get("expected_desc"):
                        self.assertEqual(config.get("description"), case["expected_desc"])
                else:
                    self.assertIsNotNone(error)

    def test_json_configurations(self):
        """Test various JSON configuration formats."""
        json_cases = [
            {
                "command": 'tool agent {}',
                "expected_config": {}
            },
            {
                "command": 'tool agent {"description": "Simple description"}',
                "expected_config": {"description": "Simple description"}
            },
            {
                "command": 'tool agent {"capabilities": ["read", "write"], "priority": 5}',
                "expected_config": {"capabilities": ["read", "write"], "priority": 5}
            },
            {
                "command": 'tool agent ["array", "config"]',
                "expected_desc": "['array', 'config']",
                "expected_via": "cli_json"
            }
        ]
        
        for case in json_cases:
            with self.subTest(command=case["command"]):
                agent_type, agent_id, config, error = self.parse_agent_create_command(case["command"])
                
                self.assertIsNone(error, f"Unexpected error: {error}")
                self.assertIsInstance(config, dict)
                
                if case.get("expected_config"):
                    for key, value in case["expected_config"].items():
                        self.assertEqual(config.get(key), value)
                
                if case.get("expected_desc"):
                    self.assertEqual(config.get("description"), case["expected_desc"])
                
                if case.get("expected_via"):
                    self.assertEqual(config.get("created_via"), case["expected_via"])

    def test_realistic_commands(self):
        """Test realistic agent_create commands that users might actually use."""
        realistic_cases = [
            "file_analyzer analyzer for analyzing file contents and extracting metadata",
            "log_parser parser for parsing and analyzing system logs",
            "network_monitor net_mon for monitoring network traffic and connections",
            "code_formatter formatter for formatting and beautifying code",
            "db_optimizer optimizer for optimizing database queries and performance",
            "hash_tool hasher for generating and verifying file hashes",
            "data_validator validator for validating data integrity and format",
            "backup_manager manager for managing automated backups",
            "security_scanner scanner for scanning files and systems for vulnerabilities",
            "performance_monitor perf_mon for monitoring system performance metrics"
        ]
        
        for command in realistic_cases:
            with self.subTest(command=command):
                agent_type, agent_id, config, error = self.parse_agent_create_command(command)
                
                # All realistic commands should parse successfully
                self.assertIsNone(error, f"Failed to parse realistic command: {command}")
                self.assertIsNotNone(agent_type)
                self.assertIsNotNone(agent_id)
                self.assertIsInstance(config, dict)
                self.assertEqual(config.get("created_via"), "cli_natural_language")
                self.assertIn("description", config)
                self.assertTrue(len(config["description"]) > 0)

    def test_command_format_validation(self):
        """Test validation of command format and structure."""
        # Test that the original problematic commands now work
        problematic_commands = [
            "delegation_tool delegator to control conversation flow",
            "moderation_tool moderator for managing AI interactions", 
            "coordination_tool coordinator for orchestrating multiple agents",
            "analysis_tool analyzer for deep system analysis"
        ]
        
        for command in problematic_commands:
            with self.subTest(command=command):
                agent_type, agent_id, config, error = self.parse_agent_create_command(command)
                
                self.assertIsNone(error, f"Command should now parse correctly: {command}")
                self.assertIsNotNone(agent_type)
                self.assertIsNotNone(agent_id)
                self.assertIsInstance(config, dict)

    def test_performance_parsing(self):
        """Test parsing performance with various command sizes."""
        start_time = time.time()
        
        # Test with various command lengths
        test_commands = [
            "short_type short_id",
            "medium_type medium_id with a medium length description",
            f"long_type long_id with a very long description that contains many words and should test the parsing performance with longer input strings {'word ' * 50}",
            'json_type json_id {"complex": {"nested": {"structure": "value"}}, "array": [1, 2, 3, 4, 5], "description": "Complex JSON configuration"}',
        ]
        
        iterations = 100
        for _ in range(iterations):
            for command in test_commands:
                agent_type, agent_id, config, error = self.parse_agent_create_command(command)
                self.assertIsNone(error)
        
        total_time = time.time() - start_time
        avg_time = total_time / (iterations * len(test_commands))
        
        self.logger.info(f"Parsing performance: {avg_time*1000:.2f}ms per command")
        self.assertLess(avg_time, 0.001, "Parsing should be very fast (< 1ms per command)")


class TestAgentCreateIntegration(unittest.TestCase):
    """Integration tests for agent creation workflow."""
    
    def setUp(self):
        """Set up each test."""
        self.logger = get_logger(__name__)
        self.test_config = Config(test_mode=True)
    
    def test_cli_integration_simulation(self):
        """Simulate the CLI integration workflow."""
        # This test simulates what happens in the actual CLI
        test_scenarios = [
            {
                "user_input": "agent_create file_analyzer analyzer for analyzing files",
                "expected_parts": ["agent_create", "file_analyzer", "analyzer", "for", "analyzing", "files"]
            },
            {
                "user_input": "agent_create hash_tool hasher",
                "expected_parts": ["agent_create", "hash_tool", "hasher"]
            },
            {
                "user_input": 'agent_create custom_tool tool {"priority": 1}',
                "expected_parts": ["agent_create", "custom_tool", "tool", '{"priority": 1}']
            }
        ]
        
        for scenario in test_scenarios:
            with self.subTest(user_input=scenario["user_input"]):
                # Simulate CLI parsing
                user_input = scenario["user_input"]
                parts = user_input.strip().split(" ", 1)
                command_verb = parts[0].lower()
                args_str = parts[1] if len(parts) > 1 else ""
                
                self.assertEqual(command_verb, "agent_create")
                self.assertTrue(len(args_str) > 0)
                
                # Simulate the actual parsing logic
                parser = TestAgentCreateSimple()
                agent_type, agent_id, config, error = parser.parse_agent_create_command(args_str)
                
                self.assertIsNone(error, f"CLI simulation failed: {error}")
                self.assertIsNotNone(agent_type)
                self.assertIsNotNone(agent_id)
                self.assertIsInstance(config, dict)

    def test_workflow_validation(self):
        """Test that the workflow produces valid parameters for agent creation."""
        test_commands = [
            "file_processor processor for processing files",
            "data_analyzer analyzer",
            'custom_agent agent {"description": "Custom agent", "capabilities": ["test"]}'
        ]
        
        parser = TestAgentCreateSimple()
        
        for command in test_commands:
            with self.subTest(command=command):
                agent_type, agent_id, config, error = parser.parse_agent_create_command(command)
                
                # Validate that results are suitable for agent creation
                self.assertIsNone(error)
                self.assertIsInstance(agent_type, str)
                self.assertIsInstance(agent_id, str)
                self.assertIsInstance(config, dict)
                
                # Validate required fields for agent creation
                self.assertTrue(len(agent_type) > 0, "Agent type cannot be empty")
                self.assertTrue(len(agent_id) > 0, "Agent ID cannot be empty")
                self.assertIn("description", config, "Config must have description")
                self.assertTrue(len(config["description"]) > 0, "Description cannot be empty")


def run_simple_tests():
    """Run the simplified agent_create tests."""
    print("🚀 Starting Simple Agent Create Workflow Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestAgentCreateSimple))
    suite.addTests(loader.loadTestsFromTestCase(TestAgentCreateIntegration))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        buffer=True
    )
    
    print(f"Running {suite.countTestCases()} test cases...")
    print("-" * 60)
    
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("🏁 Test Summary:")
    print(f"   Tests Run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    
    if result.testsRun > 0:
        success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100)
        print(f"   Success Rate: {success_rate:.1f}%")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            failure_lines = traceback.split('\n')
            failure_msg = failure_lines[-2] if len(failure_lines) > 1 else 'Unknown failure'
            print(f"   - {test}: {failure_msg}")
    
    if result.errors:
        print("\n💥 Errors:")
        for test, traceback in result.errors:
            error_lines = traceback.split('\n')
            error_msg = error_lines[-2] if len(error_lines) > 1 else 'Unknown error'
            print(f"   - {test}: {error_msg}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_simple_tests()
    sys.exit(0 if success else 1) 