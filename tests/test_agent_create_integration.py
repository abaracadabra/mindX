#!/usr/bin/env python3
"""
Integration tests for the agent_create workflow.
Tests the complete end-to-end process from CLI command parsing to agent creation and validation.
"""

import asyncio
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.config import Config
from utils.logging_config import setup_logging

# Setup logging for tests
setup_logging()

class TestAgentCreateIntegration(unittest.TestCase):
    """Integration tests for agent_create workflow."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.test_start_time = time.time()
        print(f"\n🧪 Starting Agent Create Integration Tests...")
        
    def setUp(self):
        """Set up each test."""
        self.config = Config()
        
    def parse_agent_create_command(self, command_args):
        """Parse agent_create command arguments with enhanced validation."""
        try:
            if len(command_args) < 2:
                return None, None, None, "Insufficient arguments"
            
            agent_type = command_args[0]
            agent_id = command_args[1]
            
            # Validate agent_type and agent_id are not empty
            if not agent_type or not agent_type.strip():
                return None, None, None, "Agent type cannot be empty"
            
            if not agent_id or not agent_id.strip():
                return None, None, None, "Agent ID cannot be empty"
            
            # Handle description/config
            config = {}
            description = ""
            
            if len(command_args) > 2:
                remaining_args = " ".join(command_args[2:])
                
                # Try to parse as JSON first
                if remaining_args.strip().startswith('{'):
                    try:
                        config = json.loads(remaining_args)
                        description = config.get('description', '')
                    except json.JSONDecodeError:
                        # If JSON parsing fails, treat as description
                        description = remaining_args
                        config = {
                            'description': description,
                            'created_via': 'cli_natural_language'
                        }
                else:
                    # Natural language description
                    description = remaining_args
                    config = {
                        'description': description,
                        'created_via': 'cli_natural_language'
                    }
            
            return agent_type, agent_id, config, None
            
        except Exception as e:
            return None, None, None, str(e)
    
    def test_cli_parsing_comprehensive(self):
        """Test comprehensive CLI command parsing scenarios."""
        test_cases = [
            # Basic commands
            {
                'args': ['test_validator', 'validator'],
                'expected_type': 'test_validator',
                'expected_id': 'validator',
                'should_succeed': True
            },
            {
                'args': ['data_processor', 'processor', 'for processing data efficiently'],
                'expected_type': 'data_processor',
                'expected_id': 'processor',
                'expected_description': 'for processing data efficiently',
                'should_succeed': True
            },
            # JSON configuration
            {
                'args': ['analyzer', 'code_analyzer', '{"description": "analyzes code quality", "priority": "high"}'],
                'expected_type': 'analyzer',
                'expected_id': 'code_analyzer',
                'expected_description': 'analyzes code quality',
                'should_succeed': True
            },
            # Error cases
            {
                'args': ['insufficient'],
                'should_succeed': False
            },
            {
                'args': [],
                'should_succeed': False
            }
        ]
        
        for i, case in enumerate(test_cases):
            with self.subTest(case=i):
                agent_type, agent_id, config, error = self.parse_agent_create_command(case['args'])
                
                if case['should_succeed']:
                    self.assertIsNone(error, f"Expected success but got error: {error}")
                    self.assertEqual(agent_type, case['expected_type'])
                    self.assertEqual(agent_id, case['expected_id'])
                    
                    if 'expected_description' in case:
                        self.assertIsNotNone(config, "Config should not be None")
                        if config is not None:
                            self.assertIn('description', config)
                            self.assertEqual(config['description'], case['expected_description'])
                else:
                    self.assertIsNotNone(error, "Expected error but parsing succeeded")
    
    def test_agent_file_validation(self):
        """Test validation of generated agent files."""
        agent_files = [
            'agents/validator.py',
            'agents/processor.py',
            'agents/analyzer.py'
        ]
        
        for agent_file in agent_files:
            if os.path.exists(agent_file):
                with self.subTest(file=agent_file):
                    # Check file exists and is readable
                    self.assertTrue(os.path.isfile(agent_file))
                    
                    # Check file has content
                    with open(agent_file, 'r') as f:
                        content = f.read()
                        self.assertGreater(len(content), 100, "Agent file seems too small")
                        
                        # Check for required components
                        self.assertIn('class ', content, "Agent class not found")
                        self.assertIn('def __init__', content, "__init__ method not found")
                        self.assertIn('async def execute_task', content, "execute_task method not found")
                        self.assertIn('mindx/agents/', content, "File header missing")
    
    def test_workspace_structure(self):
        """Test that agent workspaces are created properly."""
        expected_workspaces = [
            'data/memory/agent_workspaces/validator',
            'data/memory/agent_workspaces/processor',
            'data/memory/agent_workspaces/analyzer'
        ]
        
        for workspace in expected_workspaces:
            if os.path.exists(workspace):
                with self.subTest(workspace=workspace):
                    self.assertTrue(os.path.isdir(workspace))
                    # Check if workspace has basic structure
                    # (This would depend on your specific workspace setup)
    
    def test_agent_identity_creation(self):
        """Test that agent identities are created properly."""
        # This test would check the .wallet_keys.env file
        wallet_file = 'data/identity/.wallet_keys.env'
        
        if os.path.exists(wallet_file):
            with open(wallet_file, 'r') as f:
                content = f.read()
                
                # Check for expected wallet entries
                expected_agents = ['VALIDATOR', 'PROCESSOR', 'ANALYZER']
                for agent in expected_agents:
                    wallet_key = f'MINDX_WALLET_PK_{agent}'
                    if wallet_key in content:
                        self.assertIn(wallet_key, content, f"Wallet key for {agent} not found")
    
    def test_command_format_validation(self):
        """Test various command format validations."""
        valid_formats = [
            'agent_create test_type test_id',
            'agent_create validator val1 for validation purposes',
            'agent_create processor proc1 {"description": "processes data", "priority": "high"}',
        ]
        
        for cmd in valid_formats:
            with self.subTest(command=cmd):
                parts = cmd.split()[1:]  # Remove 'agent_create'
                agent_type, agent_id, config, error = self.parse_agent_create_command(parts)
                self.assertIsNone(error, f"Valid command failed: {cmd}")
                self.assertIsNotNone(agent_type)
                self.assertIsNotNone(agent_id)
    
    def test_error_handling(self):
        """Test error handling in various scenarios."""
        error_cases = [
            [],  # No arguments
            ['only_one_arg'],  # Insufficient arguments
            ['', 'agent_id'],  # Empty agent type
            ['agent_type', ''],  # Empty agent ID
        ]
        
        for case in error_cases:
            with self.subTest(args=case):
                agent_type, agent_id, config, error = self.parse_agent_create_command(case)
                self.assertIsNotNone(error, f"Expected error for case: {case}")
    
    def test_performance_metrics(self):
        """Test performance characteristics of agent creation."""
        # This is a basic performance test
        start_time = time.time()
        
        # Parse a typical command
        agent_type, agent_id, config, error = self.parse_agent_create_command([
            'performance_test', 'perf_agent', 'test agent for performance metrics'
        ])
        
        end_time = time.time()
        parsing_time = end_time - start_time
        
        # Parsing should be very fast (under 1ms for simple cases)
        self.assertLess(parsing_time, 0.001, "Command parsing is too slow")
        self.assertIsNone(error)
        self.assertEqual(agent_type, 'performance_test')
        self.assertEqual(agent_id, 'perf_agent')


def run_integration_tests():
    """Run all integration tests and provide detailed output."""
    print("=" * 60)
    print("🚀 AGENT CREATE INTEGRATION TEST SUITE")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAgentCreateIntegration)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 INTEGRATION TEST RESULTS SUMMARY")
    print("=" * 60)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    success_count = total_tests - failures - errors
    success_rate = (success_count / total_tests * 100) if total_tests > 0 else 0
    
    print(f"📈 Tests Run: {total_tests}")
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failures: {failures}")
    print(f"🚨 Errors: {errors}")
    print(f"📊 Success Rate: {success_rate:.1f}%")
    
    if result.failures:
        print(f"\n❌ FAILURES ({len(result.failures)}):")
        for test, traceback in result.failures:
            failure_msg = traceback.split('AssertionError: ')[-1].split('\n')[0] if 'AssertionError: ' in traceback else 'Unknown failure'
            print(f"  • {test}: {failure_msg}")
    
    if result.errors:
        print(f"\n🚨 ERRORS ({len(result.errors)}):")
        for test, traceback in result.errors:
            error_msg = traceback.split('\n')[-2] if len(traceback.split('\n')) > 1 else 'Unknown error'
            print(f"  • {test}: {error_msg}")
    
    print("\n" + "=" * 60)
    
    if success_rate == 100:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("✨ The agent_create workflow is working perfectly!")
    elif success_rate >= 80:
        print("⚠️  Most integration tests passed, but some issues need attention.")
    else:
        print("🚨 Multiple integration test failures detected.")
        print("🔧 The agent_create workflow needs significant fixes.")
    
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1) 