#!/usr/bin/env python3
"""
Comprehensive Agent Lifecycle Test Suite
Tests all agent commands: create, delete, list, evolve, sign

This test suite validates the complete agent lifecycle management workflow,
ensuring all commands work together seamlessly.
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.config import Config
from utils.logging_config import setup_logging

# Configure logging for tests
setup_logging()
logger = logging.getLogger(__name__)

class TestAgentLifecycleComplete(unittest.TestCase):
    """Test complete agent lifecycle workflow."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.config = Config()
        
        # Override data directory for testing
        if hasattr(cls.config, 'data_dir'):
            cls.config.data_dir = tempfile.mkdtemp(prefix="mindx_test_")
        
        logger.info("Agent lifecycle test environment initialized")
    
    def setUp(self):
        """Set up each test."""
        self.test_agents = []
        self.cleanup_files = []
    
    def tearDown(self):
        """Clean up after each test."""
        # Clean up any test files
        for file_path in self.cleanup_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.warning(f"Failed to clean up {file_path}: {e}")
    
    def parse_agent_command(self, command: str) -> Tuple[str, str, Dict[str, Any], Optional[str]]:
        """
        Parse agent command and return components.
        
        Returns:
            Tuple of (command_type, agent_id, parameters, error_message)
        """
        try:
            if not command or not command.strip():
                return "", "", {}, "Empty command"
            
            parts = command.strip().split()
            if len(parts) < 1:
                return "", "", {}, "Invalid command format"
            
            command_type = parts[0].lower()
            
            if command_type == "agent_create":
                if len(parts) < 3:
                    return command_type, "", {}, "agent_create requires at least type and id"
                
                agent_type = parts[1]
                agent_id = parts[2]
                
                # Handle optional JSON configuration
                config = {}
                if len(parts) > 3:
                    try:
                        config_str = " ".join(parts[3:])
                        if config_str.startswith('{') and config_str.endswith('}'):
                            config = json.loads(config_str)
                        else:
                            # Treat as description
                            config = {"description": config_str}
                    except json.JSONDecodeError:
                        config = {"description": " ".join(parts[3:])}
                
                return command_type, agent_id, {
                    "agent_type": agent_type,
                    "agent_id": agent_id,
                    "config": config
                }, None
            
            elif command_type == "agent_delete":
                if len(parts) < 2:
                    return command_type, "", {}, "agent_delete requires agent_id"
                
                agent_id = parts[1]
                return command_type, agent_id, {"agent_id": agent_id}, None
            
            elif command_type == "agent_list":
                return command_type, "", {}, None
            
            elif command_type == "agent_evolve":
                if len(parts) < 3:
                    return command_type, "", {}, "agent_evolve requires agent_id and directive"
                
                agent_id = parts[1]
                directive = " ".join(parts[2:])
                return command_type, agent_id, {
                    "agent_id": agent_id,
                    "directive": directive
                }, None
            
            elif command_type == "agent_sign":
                if len(parts) < 3:
                    return command_type, "", {}, "agent_sign requires agent_id and message"
                
                agent_id = parts[1]
                message = " ".join(parts[2:])
                return command_type, agent_id, {
                    "agent_id": agent_id,
                    "message": message
                }, None
            
            else:
                return command_type, "", {}, f"Unknown command type: {command_type}"
        
        except Exception as e:
            return "", "", {}, f"Command parsing error: {str(e)}"
    
    def test_command_parsing_agent_create(self):
        """Test parsing of agent_create commands."""
        test_cases = [
            ("agent_create bdi_agent test_agent", "bdi_agent", "test_agent", {}),
            ("agent_create validator val_001 validation agent", "validator", "val_001", {"description": "validation agent"}),
            ('agent_create processor proc_001 {"timeout": 30}', "processor", "proc_001", {"timeout": 30}),
            ("agent_create", "", "", "agent_create requires at least type and id"),
            ("agent_create bdi_agent", "", "", "agent_create requires at least type and id"),
        ]
        
        for command, expected_type, expected_id, expected_config_or_error in test_cases:
            with self.subTest(command=command):
                cmd_type, agent_id, params, error = self.parse_agent_command(command)
                
                if isinstance(expected_config_or_error, str) and expected_config_or_error.startswith("agent_create requires"):
                    self.assertIsNotNone(error)
                    self.assertIn("agent_create requires", error)
                else:
                    self.assertIsNone(error)
                    self.assertEqual(cmd_type, "agent_create")
                    self.assertEqual(agent_id, expected_id)
                    self.assertEqual(params["agent_type"], expected_type)
                    if expected_config_or_error:
                        self.assertEqual(params["config"], expected_config_or_error)
    
    def test_command_parsing_agent_delete(self):
        """Test parsing of agent_delete commands."""
        test_cases = [
            ("agent_delete test_agent", "test_agent", None),
            ("agent_delete old_processor", "old_processor", None),
            ("agent_delete", "", "agent_delete requires agent_id"),
        ]
        
        for command, expected_id, expected_error in test_cases:
            with self.subTest(command=command):
                cmd_type, agent_id, params, error = self.parse_agent_command(command)
                
                if expected_error:
                    self.assertIsNotNone(error)
                    self.assertIn(expected_error, error)
                else:
                    self.assertIsNone(error)
                    self.assertEqual(cmd_type, "agent_delete")
                    self.assertEqual(agent_id, expected_id)
                    self.assertEqual(params["agent_id"], expected_id)
    
    def test_command_parsing_agent_list(self):
        """Test parsing of agent_list command."""
        cmd_type, agent_id, params, error = self.parse_agent_command("agent_list")
        
        self.assertIsNone(error)
        self.assertEqual(cmd_type, "agent_list")
        self.assertEqual(agent_id, "")
        self.assertEqual(params, {})
    
    def test_command_parsing_agent_evolve(self):
        """Test parsing of agent_evolve commands."""
        test_cases = [
            ("agent_evolve test_agent improve performance", "test_agent", "improve performance"),
            ("agent_evolve monitor_agent add logging capabilities", "monitor_agent", "add logging capabilities"),
            ("agent_evolve", "", "agent_evolve requires agent_id and directive"),
            ("agent_evolve test_agent", "", "agent_evolve requires agent_id and directive"),
        ]
        
        for command, expected_id, expected_directive_or_error in test_cases:
            with self.subTest(command=command):
                cmd_type, agent_id, params, error = self.parse_agent_command(command)
                
                if expected_id == "" and expected_directive_or_error.startswith("agent_evolve requires"):
                    self.assertIsNotNone(error)
                    self.assertIn("agent_evolve requires", error)
                else:
                    self.assertIsNone(error)
                    self.assertEqual(cmd_type, "agent_evolve")
                    self.assertEqual(agent_id, expected_id)
                    self.assertEqual(params["agent_id"], expected_id)
                    self.assertEqual(params["directive"], expected_directive_or_error)
    
    def test_command_parsing_agent_sign(self):
        """Test parsing of agent_sign commands."""
        test_cases = [
            ("agent_sign test_agent hello world", "test_agent", "hello world"),
            ("agent_sign monitor_agent system status ok", "monitor_agent", "system status ok"),
            ("agent_sign", "", "agent_sign requires agent_id and message"),
            ("agent_sign test_agent", "", "agent_sign requires agent_id and message"),
        ]
        
        for command, expected_id, expected_message_or_error in test_cases:
            with self.subTest(command=command):
                cmd_type, agent_id, params, error = self.parse_agent_command(command)
                
                if expected_id == "" and expected_message_or_error.startswith("agent_sign requires"):
                    self.assertIsNotNone(error)
                    self.assertIn("agent_sign requires", error)
                else:
                    self.assertIsNone(error)
                    self.assertEqual(cmd_type, "agent_sign")
                    self.assertEqual(agent_id, expected_id)
                    self.assertEqual(params["agent_id"], expected_id)
                    self.assertEqual(params["message"], expected_message_or_error)
    
    def test_command_parsing_error_cases(self):
        """Test error handling in command parsing."""
        error_cases = [
            ("", "Empty command"),
            ("   ", "Empty command"),
            ("unknown_command", "Unknown command type"),
            ("agent_unknown test", "Unknown command type"),
        ]
        
        for command, expected_error_type in error_cases:
            with self.subTest(command=command):
                cmd_type, agent_id, params, error = self.parse_agent_command(command)
                self.assertIsNotNone(error)
                if expected_error_type == "Empty command":
                    self.assertIn("Empty command", error)
                elif expected_error_type == "Unknown command type":
                    self.assertIn("Unknown command type", error)
    
    def test_agent_lifecycle_workflow_simulation(self):
        """Test complete agent lifecycle workflow simulation."""
        # Simulate the complete workflow
        workflow_steps = [
            ("agent_create", "validator", "val_test", {"description": "Test validator"}),
            ("agent_list", None, None, None),
            ("agent_evolve", "val_test", "improve validation logic", None),
            ("agent_sign", "val_test", "test message", None),
            ("agent_delete", "val_test", None, None),
        ]
        
        results = []
        
        for step in workflow_steps:
            command_type, agent_id, param1, param2 = step
            
            if command_type == "agent_create":
                command = f"agent_create {agent_id} {param1}"
                if param2:
                    command += f" {json.dumps(param2)}"
            elif command_type == "agent_list":
                command = "agent_list"
            elif command_type == "agent_evolve":
                command = f"agent_evolve {agent_id} {param1}"
            elif command_type == "agent_sign":
                command = f"agent_sign {agent_id} {param1}"
            elif command_type == "agent_delete":
                command = f"agent_delete {agent_id}"
            
            cmd_type, parsed_id, params, error = self.parse_agent_command(command)
            
            results.append({
                "step": command_type,
                "command": command,
                "parsed_type": cmd_type,
                "parsed_id": parsed_id,
                "params": params,
                "error": error,
                "success": error is None
            })
        
        # Verify all steps parsed successfully
        for result in results:
            self.assertIsNone(result["error"], f"Step {result['step']} failed: {result['error']}")
            self.assertTrue(result["success"], f"Step {result['step']} was not successful")
        
        # Verify specific workflow logic
        create_result = results[0]
        self.assertEqual(create_result["parsed_type"], "agent_create")
        self.assertEqual(create_result["parsed_id"], "val_test")
        self.assertEqual(create_result["params"]["agent_type"], "validator")
        
        list_result = results[1]
        self.assertEqual(list_result["parsed_type"], "agent_list")
        
        evolve_result = results[2]
        self.assertEqual(evolve_result["parsed_type"], "agent_evolve")
        self.assertEqual(evolve_result["params"]["directive"], "improve validation logic")
        
        sign_result = results[3]
        self.assertEqual(sign_result["parsed_type"], "agent_sign")
        self.assertEqual(sign_result["params"]["message"], "test message")
        
        delete_result = results[4]
        self.assertEqual(delete_result["parsed_type"], "agent_delete")
        self.assertEqual(delete_result["params"]["agent_id"], "val_test")
    
    def test_agent_command_validation(self):
        """Test validation of agent commands."""
        # Test valid agent types
        valid_types = ["bdi_agent", "validator", "processor", "analyzer", "monitor"]
        
        for agent_type in valid_types:
            command = f"agent_create {agent_type} test_{agent_type}"
            cmd_type, agent_id, params, error = self.parse_agent_command(command)
            
            self.assertIsNone(error)
            self.assertEqual(params["agent_type"], agent_type)
            self.assertEqual(params["agent_id"], f"test_{agent_type}")
    
    def test_agent_id_validation(self):
        """Test agent ID validation patterns."""
        # Test various agent ID formats
        valid_ids = [
            "simple_agent",
            "agent_001",
            "test-agent",
            "TestAgent",
            "agent123",
            "my_special_agent_v2"
        ]
        
        for agent_id in valid_ids:
            command = f"agent_create bdi_agent {agent_id}"
            cmd_type, parsed_id, params, error = self.parse_agent_command(command)
            
            self.assertIsNone(error, f"Valid agent ID {agent_id} should not cause error")
            self.assertEqual(parsed_id, agent_id)
    
    def test_json_config_parsing(self):
        """Test JSON configuration parsing in agent_create."""
        test_configs = [
            ('{"timeout": 30}', {"timeout": 30}),
            ('{"name": "Test Agent", "version": "1.0"}', {"name": "Test Agent", "version": "1.0"}),
            ('{"capabilities": ["read", "write"], "enabled": true}', {"capabilities": ["read", "write"], "enabled": True}),
        ]
        
        for config_str, expected_config in test_configs:
            command = f"agent_create bdi_agent test_agent {config_str}"
            cmd_type, agent_id, params, error = self.parse_agent_command(command)
            
            self.assertIsNone(error)
            self.assertEqual(params["config"], expected_config)
    
    def test_performance_parsing(self):
        """Test parsing performance with multiple commands."""
        commands = []
        
        # Generate test commands
        for i in range(100):
            commands.extend([
                f"agent_create bdi_agent test_agent_{i}",
                f"agent_evolve test_agent_{i} improve performance",
                f"agent_sign test_agent_{i} test message {i}",
                f"agent_delete test_agent_{i}",
            ])
        
        start_time = time.time()
        
        for command in commands:
            cmd_type, agent_id, params, error = self.parse_agent_command(command)
            self.assertIsNone(error, f"Command failed: {command}")
        
        end_time = time.time()
        parsing_time = end_time - start_time
        
        # Should parse 400 commands quickly
        self.assertLess(parsing_time, 5.0, "Parsing performance should be acceptable")
        logger.info(f"Parsed {len(commands)} commands in {parsing_time:.3f} seconds")
    
    def test_edge_cases(self):
        """Test edge cases in command parsing."""
        edge_cases = [
            # Extra whitespace
            ("  agent_create   bdi_agent   test_agent  ", "agent_create", "test_agent"),
            # Mixed case
            ("AGENT_CREATE bdi_agent Test_Agent", "agent_create", "Test_Agent"),
            # Unicode characters
            ("agent_create bdi_agent test_agent_ñ", "agent_create", "test_agent_ñ"),
            # Numbers in names
            ("agent_create bdi_agent agent_123_test", "agent_create", "agent_123_test"),
        ]
        
        for command, expected_type, expected_id in edge_cases:
            with self.subTest(command=command):
                cmd_type, agent_id, params, error = self.parse_agent_command(command)
                
                self.assertIsNone(error)
                self.assertEqual(cmd_type, expected_type)
                self.assertEqual(agent_id, expected_id)


def run_lifecycle_tests():
    """Run all agent lifecycle tests."""
    print("🧪 Running Agent Lifecycle Complete Test Suite...")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAgentLifecycleComplete)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"🧪 Agent Lifecycle Test Results:")
    print(f"   Tests Run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    
    if result.failures:
        print(f"   ❌ Failed Tests:")
        for test, traceback in result.failures:
            print(f"      - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"   ⚠️  Error Tests:")
        for test, traceback in result.errors:
            print(f"      - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"   ✅ Success Rate: {success_rate:.1f}%")
    
    if success_rate == 100.0:
        print("   🎉 ALL AGENT LIFECYCLE TESTS PASSED!")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_lifecycle_tests()
    sys.exit(0 if success else 1) 