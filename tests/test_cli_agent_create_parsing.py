#!/usr/bin/env python3
"""
Test module for CLI agent_create command parsing fix.

This module validates the fixes implemented to handle JSON parsing errors
in the mindX CLI, specifically for the agent_create command. It tests:
- Natural language descriptions
- Valid JSON configurations  
- Invalid JSON handling
- Edge cases and error conditions
"""

import json
import unittest
from typing import Dict, Any, Tuple, Optional


class TestCLIAgentCreateParsing(unittest.TestCase):
    """Test cases for CLI agent_create command parsing."""
    
    def parse_agent_create_command(self, args_str: str) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]], Optional[str]]:
        """
        Parse agent_create command arguments with improved error handling.
        
        Returns: (agent_type, agent_id, config, error)
        """
        try:
            parts = args_str.strip().split(None, 2)
            
            if len(parts) < 2:
                return None, None, None, "Missing required arguments: agent_type and agent_id"
            
            agent_type = parts[0]
            agent_id = parts[1]
            
            # Check if we have a third part (configuration)
            if len(parts) >= 3:
                config_str = parts[2]
                
                # Smart JSON detection - only try to parse as JSON if it looks like JSON
                if config_str.strip().startswith(('{', '[')):
                    try:
                        config = json.loads(config_str)
                        if isinstance(config, dict):
                            return agent_type, agent_id, config, None
                        else:
                            # Convert non-dict JSON to dict with description
                            return agent_type, agent_id, {"description": str(config), "created_via": "cli_json"}, None
                    except json.JSONDecodeError as e:
                        return None, None, None, f"Invalid JSON configuration: {str(e)}"
                else:
                    # Treat as natural language description
                    config = {
                        "description": config_str,
                        "created_via": "cli_natural_language"
                    }
                    return agent_type, agent_id, config, None
            else:
                # No configuration provided, use empty dict
                config = {"created_via": "cli_minimal"}
                return agent_type, agent_id, config, None
                
        except Exception as e:
            return None, None, None, f"Error parsing command: {str(e)}"

    def test_original_problematic_command(self):
        """Test the original command that caused the JSON error."""
        test_cmd = "delegation_tool to control how much of an ai is allowed to dominate a conversation"
        agent_type, agent_id, config, error = self.parse_agent_create_command(test_cmd)
        
        self.assertIsNone(error)
        self.assertIsNotNone(agent_type)
        self.assertIsNotNone(agent_id)
        self.assertIsNotNone(config)
        
        # Now we can safely access the values since we've asserted they're not None
        assert agent_type is not None
        assert agent_id is not None
        assert config is not None
        
        self.assertEqual(agent_type, "delegation_tool")
        self.assertEqual(agent_id, "to")
        self.assertIsInstance(config, dict)
        self.assertEqual(config["description"], "control how much of an ai is allowed to dominate a conversation")
        self.assertEqual(config["created_via"], "cli_natural_language")

    def test_valid_json_command(self):
        """Test parsing of valid JSON configuration."""
        test_cmd = 'my_tool my_agent {"description": "My custom agent", "priority": 1}'
        agent_type, agent_id, config, error = self.parse_agent_create_command(test_cmd)
        
        self.assertIsNone(error)
        self.assertIsNotNone(agent_type)
        self.assertIsNotNone(agent_id)
        self.assertIsNotNone(config)
        
        # Type narrowing assertions
        assert agent_type is not None
        assert agent_id is not None
        assert config is not None
        
        self.assertEqual(agent_type, "my_tool")
        self.assertEqual(agent_id, "my_agent")
        self.assertIsInstance(config, dict)
        self.assertEqual(config["description"], "My custom agent")
        self.assertEqual(config["priority"], 1)

    def test_invalid_json_command(self):
        """Test handling of invalid JSON configuration."""
        test_cmd = 'bad_tool bad_agent {"invalid": json, "missing": quotes}'
        agent_type, agent_id, config, error = self.parse_agent_create_command(test_cmd)
        
        self.assertIsNotNone(error)
        self.assertIsNone(agent_type)
        self.assertIsNone(agent_id)
        self.assertIsNone(config)
        
        # Type narrowing assertion
        assert error is not None
        self.assertIn("Invalid JSON configuration", error)

    def test_minimal_command(self):
        """Test command with only agent_type and agent_id."""
        test_cmd = "simple_tool simple_agent"
        agent_type, agent_id, config, error = self.parse_agent_create_command(test_cmd)
        
        self.assertIsNone(error)
        self.assertIsNotNone(agent_type)
        self.assertIsNotNone(agent_id)
        self.assertIsNotNone(config)
        
        # Type narrowing assertions
        assert agent_type is not None
        assert agent_id is not None
        assert config is not None
        
        self.assertEqual(agent_type, "simple_tool")
        self.assertEqual(agent_id, "simple_agent")
        self.assertIsInstance(config, dict)
        self.assertEqual(config["created_via"], "cli_minimal")

    def test_empty_json_command(self):
        """Test command with empty JSON configuration."""
        test_cmd = "empty_tool empty_agent {}"
        agent_type, agent_id, config, error = self.parse_agent_create_command(test_cmd)
        
        self.assertIsNone(error)
        self.assertIsNotNone(agent_type)
        self.assertIsNotNone(agent_id)
        self.assertIsNotNone(config)
        
        # Type narrowing assertions
        assert agent_type is not None
        assert agent_id is not None
        assert config is not None
        
        self.assertEqual(agent_type, "empty_tool")
        self.assertEqual(agent_id, "empty_agent")
        self.assertIsInstance(config, dict)

    def test_json_array_command(self):
        """Test command with JSON array configuration."""
        test_cmd = 'array_tool array_agent ["item1", "item2"]'
        agent_type, agent_id, config, error = self.parse_agent_create_command(test_cmd)
        
        self.assertIsNone(error)
        self.assertIsNotNone(agent_type)
        self.assertIsNotNone(agent_id)
        self.assertIsNotNone(config)
        
        # Type narrowing assertions
        assert agent_type is not None
        assert agent_id is not None
        assert config is not None
        
        self.assertEqual(agent_type, "array_tool")
        self.assertEqual(agent_id, "array_agent")
        self.assertIsInstance(config, dict)
        self.assertEqual(config["description"], "['item1', 'item2']")
        self.assertEqual(config["created_via"], "cli_json")

    def test_insufficient_arguments(self):
        """Test command with insufficient arguments."""
        test_cmd = "only_one_arg"
        agent_type, agent_id, config, error = self.parse_agent_create_command(test_cmd)
        
        self.assertIsNotNone(error)
        self.assertIsNone(agent_type)
        self.assertIsNone(agent_id)
        self.assertIsNone(config)
        
        # Type narrowing assertion
        assert error is not None
        self.assertIn("Missing required arguments", error)

    def test_complex_natural_language(self):
        """Test complex natural language description."""
        test_cmd = "conversation_tool chat_manager This agent manages conversation flow and ensures balanced participation among multiple AI entities in collaborative discussions"
        agent_type, agent_id, config, error = self.parse_agent_create_command(test_cmd)
        
        self.assertIsNone(error)
        self.assertIsNotNone(agent_type)
        self.assertIsNotNone(agent_id)
        self.assertIsNotNone(config)
        
        # Type narrowing assertions
        assert agent_type is not None
        assert agent_id is not None
        assert config is not None
        
        self.assertEqual(agent_type, "conversation_tool")
        self.assertEqual(agent_id, "chat_manager")
        self.assertIsInstance(config, dict)
        expected_desc = "This agent manages conversation flow and ensures balanced participation among multiple AI entities in collaborative discussions"
        self.assertEqual(config["description"], expected_desc)
        self.assertEqual(config["created_via"], "cli_natural_language")

    def test_malformed_json_with_braces(self):
        """Test malformed JSON that starts with braces."""
        test_cmd = 'malformed_tool bad_agent {this is not valid json at all}'
        agent_type, agent_id, config, error = self.parse_agent_create_command(test_cmd)
        
        self.assertIsNotNone(error)
        self.assertIsNone(agent_type)
        self.assertIsNone(agent_id)
        self.assertIsNone(config)
        
        # Type narrowing assertion
        assert error is not None
        self.assertIn("Invalid JSON configuration", error)

    def test_edge_case_whitespace(self):
        """Test command with extra whitespace."""
        test_cmd = "  whitespace_tool   whitespace_agent   extra spaces in description  "
        agent_type, agent_id, config, error = self.parse_agent_create_command(test_cmd)
        
        self.assertIsNone(error)
        self.assertIsNotNone(agent_type)
        self.assertIsNotNone(agent_id)
        self.assertIsNotNone(config)
        
        # Type narrowing assertions
        assert agent_type is not None
        assert agent_id is not None
        assert config is not None
        
        self.assertEqual(agent_type, "whitespace_tool")
        self.assertEqual(agent_id, "whitespace_agent")
        self.assertIsInstance(config, dict)
        self.assertEqual(config["description"], "extra spaces in description")
        self.assertEqual(config["created_via"], "cli_natural_language")


if __name__ == "__main__":
    unittest.main() 