# mindx/tools/tool_factory_tool.py
"""
Tool Factory Tool for MindX.
This tool enables the BDI agent to create new tools dynamically.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from core.bdi_agent import BaseTool
from agents.memory_agent import MemoryAgent
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

class ToolFactoryTool(BaseTool):
    """Tool for creating new tools dynamically."""
    
    def __init__(self, memory_agent: MemoryAgent, config: Optional[Config] = None, **kwargs):
        super().__init__(config=config, **kwargs)
        self.memory_agent = memory_agent
        self.config = config or Config()
        self.tools_registry_path = PROJECT_ROOT / "data" / "config" / "official_tools_registry.json"
        self.log_prefix = "ToolFactoryTool:"
        logger.info(f"{self.log_prefix} Initialized with tool creation capabilities.")

    async def execute(self, action: str, tool_id: str = None, tool_config: Optional[Dict[str, Any]] = None, **kwargs) -> Tuple[bool, Any]:
        """Execute tool factory operations."""
        try:
            if action == "create_tool":
                return await self._create_tool(tool_id, tool_config or {})
            else:
                return False, f"Unknown action: {action}"
        except Exception as e:
            logger.error(f"{self.log_prefix} Error executing action '{action}': {e}", exc_info=True)
            return False, f"Tool factory error: {e}"

    async def _create_tool(self, tool_id: str, tool_config: Dict[str, Any]) -> Tuple[bool, Any]:
        """Create a new tool with basic template."""
        logger.info(f"{self.log_prefix} Creating new tool: {tool_id}")
        
        try:
            # Generate basic tool code
            tool_code_path = await self._generate_tool_code(tool_id, tool_config)
            if not tool_code_path:
                return False, "Failed to generate tool code"
            
            # Register in tools registry
            registration_result = await self._register_tool_in_registry(tool_id, tool_config)
            if not registration_result[0]:
                return False, f"Tool registration failed: {registration_result[1]}"
            
            tool_metadata = {
                "tool_id": tool_id,
                "name": tool_config.get("name", tool_id),
                "description": tool_config.get("description", "Dynamically created tool"),
                "code_path": str(tool_code_path),
                "created_at": time.time(),
                "created_by": "tool_factory_tool",
                "status": "active"
            }
            
            logger.info(f"{self.log_prefix} Successfully created tool {tool_id}")
            return True, tool_metadata
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to create tool {tool_id}: {e}", exc_info=True)
            return False, f"Tool creation failed: {e}"

    async def _generate_tool_code(self, tool_id: str, tool_config: Dict[str, Any]) -> Optional[Path]:
        """Generate tool code from basic template."""
        try:
            tool_class_name = f"{tool_id.replace('_', '').title()}Tool"
            tool_description = tool_config.get("description", "Dynamically created tool")
            
            tool_code = f'''# mindx/tools/{tool_id}.py
"""
{tool_class_name} - Dynamically created tool.
Description: {tool_description}
"""

import time
from typing import Dict, Any, Tuple, Optional

from core.bdi_agent import BaseTool
from agents.memory_agent import MemoryAgent
from utils.config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)

class {tool_class_name}(BaseTool):
    """Dynamically created tool: {tool_description}"""
    
    def __init__(self, memory_agent: MemoryAgent, config: Optional[Config] = None, **kwargs):
        super().__init__(config=config, **kwargs)
        self.memory_agent = memory_agent
        self.config = config or Config()
        self.tool_id = "{tool_id}"
        self.log_prefix = f"{tool_class_name}:"
        logger.info(f"{{self.log_prefix}} Initialized tool {{self.tool_id}}")
    
    async def execute(self, operation: str, parameters: Dict[str, Any] = None, **kwargs) -> Tuple[bool, Any]:
        """Execute the tool operation."""
        logger.info(f"{{self.log_prefix}} Executing operation: {{operation}}")
        
        try:
            parameters = parameters or {{}}
            
            if operation == "test":
                return await self._test_operation(parameters)
            elif operation == "status":
                return await self._status_operation()
            else:
                return await self._custom_operation(operation, parameters)
                
        except Exception as e:
            logger.error(f"{{self.log_prefix}} Operation '{{operation}}' failed: {{e}}", exc_info=True)
            return False, f"Tool operation error: {{e}}"
    
    async def _test_operation(self, parameters: Dict[str, Any]) -> Tuple[bool, Any]:
        """Test operation for validation."""
        result = {{
            "status": "SUCCESS",
            "tool_id": self.tool_id,
            "operation": "test",
            "message": "Tool test completed successfully",
            "timestamp": time.time()
        }}
        return True, result
    
    async def _status_operation(self) -> Tuple[bool, Any]:
        """Get tool status."""
        status = {{
            "tool_id": self.tool_id,
            "status": "active",
            "description": "{tool_description}",
            "timestamp": time.time()
        }}
        return True, status
    
    async def _custom_operation(self, operation: str, parameters: Dict[str, Any]) -> Tuple[bool, Any]:
        """Custom operation implementation."""
        result = {{
            "status": "SUCCESS",
            "tool_id": self.tool_id,
            "operation": operation,
            "parameters": parameters,
            "message": f"Custom operation '{{operation}}' executed",
            "timestamp": time.time()
        }}
        return True, result
'''
            
            # Save to tools directory
            tool_code_path = PROJECT_ROOT / "tools" / f"{tool_id}.py"
            with tool_code_path.open("w", encoding="utf-8") as f:
                f.write(tool_code)
            
            logger.info(f"{self.log_prefix} Generated tool code at {tool_code_path}")
            return tool_code_path
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to generate tool code: {e}")
            return None

    async def _register_tool_in_registry(self, tool_id: str, tool_config: Dict[str, Any]) -> Tuple[bool, Any]:
        """Register the tool in the official tools registry."""
        logger.info(f"{self.log_prefix} Registering tool {tool_id} in registry")
        
        try:
            registry = {}
            if self.tools_registry_path.exists():
                with self.tools_registry_path.open("r", encoding="utf-8") as f:
                    registry = json.load(f)
            
            if "registered_tools" not in registry:
                registry["registered_tools"] = {}
            
            tool_entry = {
                "id": tool_id,
                "name": tool_config.get("name", tool_id),
                "description": tool_config.get("description", "Dynamically created tool"),
                "module_path": f"tools.{tool_id}",
                "class_name": f"{tool_id.replace('_', '').title()}Tool",
                "version": tool_config.get("version", "1.0.0"),
                "enabled": tool_config.get("enabled", True),
                "commands": [{
                    "name": "execute",
                    "description": "Execute tool operation",
                    "parameters": [
                        {"name": "operation", "type": "str", "required": True},
                        {"name": "parameters", "type": "dict", "required": False}
                    ]
                }],
                "access_control": {"allowed_agents": ["*"]},
                "identity": {"public_key": None, "signature": None},
                "created_by": "tool_factory_tool",
                "created_at": time.time()
            }
            
            registry["registered_tools"][tool_id] = tool_entry
            registry["last_updated_at"] = time.time()
            registry["last_updated_by"] = "tool_factory_tool"
            
            with self.tools_registry_path.open("w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2)
            
            logger.info(f"{self.log_prefix} Successfully registered tool {tool_id}")
            return True, tool_entry
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to register tool {tool_id}: {e}")
            return False, f"Tool registration error: {e}"
