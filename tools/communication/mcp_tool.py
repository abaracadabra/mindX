# mindx/tools/mcp_tool.py
"""
MCP (Model Context Protocol) Tool for MindX.

This tool enables the Model Context Protocol for providing structured context
to agents for actions. MCP allows agents to receive rich, structured context
about their environment, available tools, and action requirements.

Following mindX doctrine:
- Memory is infrastructure (MCP contexts are stored and versioned)
- Structured context enables better agent actions
- Protocol-based approach ensures interoperability
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict

from agents.core.bdi_agent import BaseTool
from agents.memory_agent import MemoryAgent
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)


class MCPContextType(Enum):
    """Types of MCP contexts."""
    TOOL_DEFINITION = "tool_definition"
    ACTION_CONTEXT = "action_context"
    ENVIRONMENT_STATE = "environment_state"
    CAPABILITY_DESCRIPTION = "capability_description"
    EXECUTION_PARAMETERS = "execution_parameters"
    RESULT_SCHEMA = "result_schema"


class MCPProtocolVersion(Enum):
    """MCP protocol versions."""
    V1_0 = "1.0"
    V2_0 = "2.0"


@dataclass
class MCPContext:
    """MCP context structure."""
    context_id: str
    context_type: MCPContextType
    protocol_version: str
    agent_id: str
    tool_id: Optional[str] = None
    action_id: Optional[str] = None
    context_data: Dict[str, Any] = None
    schema: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if self.context_data is None:
            self.context_data = {}
        if self.metadata is None:
            self.metadata = {}
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.utcnow().isoformat()


@dataclass
class MCPToolDefinition:
    """MCP tool definition structure."""
    tool_id: str
    name: str
    description: str
    parameters: Dict[str, Any]
    returns: Dict[str, Any]
    examples: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.examples is None:
            self.examples = []
        if self.metadata is None:
            self.metadata = {}


class MCPTool(BaseTool):
    """
    MCP Tool - Provides Model Context Protocol support.
    
    This tool enables structured context provision for agents:
    - Tool definitions with schemas
    - Action context with parameters
    - Environment state descriptions
    - Capability descriptions
    - Execution parameters
    - Result schemas
    """
    
    def __init__(self,
                 memory_agent: MemoryAgent,
                 config: Optional[Config] = None,
                 **kwargs):
        super().__init__(config=config, **kwargs)
        self.memory_agent = memory_agent
        self.config = config or Config()
        self.project_root = PROJECT_ROOT
        
        # MCP storage
        self.mcp_path = self.project_root / "data" / "mcp"
        self.mcp_path.mkdir(parents=True, exist_ok=True)
        self.contexts_path = self.mcp_path / "contexts"
        self.tool_definitions_path = self.mcp_path / "tool_definitions"
        self.contexts_path.mkdir(exist_ok=True)
        self.tool_definitions_path.mkdir(exist_ok=True)
        
        # Registry files
        self.contexts_registry_path = self.mcp_path / "contexts_registry.json"
        self.tool_definitions_registry_path = self.mcp_path / "tool_definitions_registry.json"
        
        # In-memory registries
        self.contexts: Dict[str, MCPContext] = {}
        self.tool_definitions: Dict[str, MCPToolDefinition] = {}
        
        # Protocol version
        self.protocol_version = MCPProtocolVersion.V2_0.value
        
        # Load existing data
        self._load_registries()
        
        logger.info("MCPTool initialized")
    
    def _load_registries(self):
        """Load contexts and tool definitions from disk."""
        # Load contexts
        if self.contexts_registry_path.exists():
            try:
                with open(self.contexts_registry_path, 'r') as f:
                    data = json.load(f)
                    for context_id, ctx_dict in data.items():
                        ctx_dict['context_type'] = MCPContextType(ctx_dict['context_type'])
                        self.contexts[context_id] = MCPContext(**ctx_dict)
                logger.info(f"Loaded {len(self.contexts)} MCP contexts")
            except Exception as e:
                logger.error(f"Error loading MCP contexts: {e}")
        
        # Load tool definitions
        if self.tool_definitions_registry_path.exists():
            try:
                with open(self.tool_definitions_registry_path, 'r') as f:
                    data = json.load(f)
                    for tool_id, tool_dict in data.items():
                        self.tool_definitions[tool_id] = MCPToolDefinition(**tool_dict)
                logger.info(f"Loaded {len(self.tool_definitions)} tool definitions")
            except Exception as e:
                logger.error(f"Error loading tool definitions: {e}")
    
    def _save_registries(self):
        """Save contexts and tool definitions to disk."""
        # Save contexts
        try:
            data = {}
            for context_id, context in self.contexts.items():
                ctx_dict = asdict(context)
                ctx_dict['context_type'] = context.context_type.value
                data[context_id] = ctx_dict
            with open(self.contexts_registry_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving MCP contexts: {e}")
        
        # Save tool definitions
        try:
            data = {}
            for tool_id, tool_def in self.tool_definitions.items():
                data[tool_id] = asdict(tool_def)
            with open(self.tool_definitions_registry_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving tool definitions: {e}")
    
    async def execute(self, operation: str, **kwargs) -> Dict[str, Any]:
        """
        Execute MCP tool operations.
        
        Operations:
        - create_context: Create a new MCP context
        - get_context: Get context by ID
        - update_context: Update an existing context
        - delete_context: Delete a context
        - list_contexts: List all contexts (with filters)
        - register_tool: Register a tool definition
        - get_tool_definition: Get tool definition
        - list_tools: List all tool definitions
        - get_action_context: Get context for an action
        - get_tool_context: Get context for a tool
        """
        try:
            if operation == "create_context":
                return await self._create_context(**kwargs)
            elif operation == "get_context":
                return await self._get_context(**kwargs)
            elif operation == "update_context":
                return await self._update_context(**kwargs)
            elif operation == "delete_context":
                return await self._delete_context(**kwargs)
            elif operation == "list_contexts":
                return await self._list_contexts(**kwargs)
            elif operation == "register_tool":
                return await self._register_tool(**kwargs)
            elif operation == "get_tool_definition":
                return await self._get_tool_definition(**kwargs)
            elif operation == "list_tools":
                return await self._list_tools(**kwargs)
            elif operation == "get_action_context":
                return await self._get_action_context(**kwargs)
            elif operation == "get_tool_context":
                return await self._get_tool_context(**kwargs)
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {operation}"
                }
        except Exception as e:
            logger.error(f"Error executing MCP operation {operation}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _create_context(self,
                             context_type: str,
                             agent_id: str,
                             context_data: Dict[str, Any],
                             tool_id: Optional[str] = None,
                             action_id: Optional[str] = None,
                             schema: Optional[Dict[str, Any]] = None,
                             **kwargs) -> Dict[str, Any]:
        """Create a new MCP context."""
        try:
            # Generate context ID
            context_id = hashlib.sha256(
                f"{agent_id}:{context_type}:{tool_id}:{action_id}:{datetime.utcnow()}".encode()
            ).hexdigest()[:16]
            
            # Create context
            context = MCPContext(
                context_id=context_id,
                context_type=MCPContextType(context_type),
                protocol_version=self.protocol_version,
                agent_id=agent_id,
                tool_id=tool_id,
                action_id=action_id,
                context_data=context_data,
                schema=schema,
                metadata=kwargs.get("metadata", {})
            )
            
            # Save context
            self.contexts[context_id] = context
            self._save_registries()
            
            # Save individual context file
            context_file = self.contexts_path / f"{context_id}.json"
            with open(context_file, 'w') as f:
                ctx_dict = asdict(context)
                ctx_dict['context_type'] = context.context_type.value
                json.dump(ctx_dict, f, indent=2)
            
            # Store in memory
            await self.memory_agent.store_memory(
                agent_id="mcp_tool",
                memory_type="system_state",
                content={
                    "action": "mcp_context_created",
                    "context_id": context_id,
                    "context_type": context_type,
                    "agent_id": agent_id
                },
                importance="high"
            )
            
            logger.info(f"Created MCP context: {context_id} ({context_type})")
            
            return {
                "success": True,
                "context_id": context_id,
                "context": asdict(context)
            }
        except Exception as e:
            logger.error(f"Error creating MCP context: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_context(self,
                          context_id: str,
                          **kwargs) -> Dict[str, Any]:
        """Get context by ID."""
        if context_id not in self.contexts:
            return {
                "success": False,
                "error": f"Context not found: {context_id}"
            }
        
        context = self.contexts[context_id]
        ctx_dict = asdict(context)
        ctx_dict['context_type'] = context.context_type.value
        
        return {
            "success": True,
            "context": ctx_dict
        }
    
    async def _update_context(self,
                             context_id: str,
                             context_data: Optional[Dict[str, Any]] = None,
                             schema: Optional[Dict[str, Any]] = None,
                             **kwargs) -> Dict[str, Any]:
        """Update an existing context."""
        if context_id not in self.contexts:
            return {
                "success": False,
                "error": f"Context not found: {context_id}"
            }
        
        context = self.contexts[context_id]
        
        if context_data is not None:
            context.context_data.update(context_data)
        if schema is not None:
            context.schema = schema
        
        context.updated_at = datetime.utcnow().isoformat()
        self._save_registries()
        
        return {
            "success": True,
            "context": asdict(context)
        }
    
    async def _delete_context(self,
                              context_id: str,
                              **kwargs) -> Dict[str, Any]:
        """Delete a context."""
        if context_id not in self.contexts:
            return {
                "success": False,
                "error": f"Context not found: {context_id}"
            }
        
        # Delete file
        context_file = self.contexts_path / f"{context_id}.json"
        if context_file.exists():
            context_file.unlink()
        
        # Remove from registry
        del self.contexts[context_id]
        self._save_registries()
        
        return {
            "success": True,
            "message": f"Context {context_id} deleted"
        }
    
    async def _list_contexts(self,
                            agent_id: Optional[str] = None,
                            context_type: Optional[str] = None,
                            tool_id: Optional[str] = None,
                            **kwargs) -> Dict[str, Any]:
        """List all contexts with optional filters."""
        contexts = []
        
        for context_id, context in self.contexts.items():
            # Apply filters
            if agent_id and context.agent_id != agent_id:
                continue
            if context_type and context.context_type.value != context_type:
                continue
            if tool_id and context.tool_id != tool_id:
                continue
            
            ctx_dict = asdict(context)
            ctx_dict['context_type'] = context.context_type.value
            contexts.append(ctx_dict)
        
        return {
            "success": True,
            "contexts": contexts,
            "count": len(contexts)
        }
    
    async def _register_tool(self,
                            tool_id: str,
                            name: str,
                            description: str,
                            parameters: Dict[str, Any],
                            returns: Dict[str, Any],
                            examples: Optional[List[Dict[str, Any]]] = None,
                            **kwargs) -> Dict[str, Any]:
        """Register a tool definition."""
        try:
            tool_definition = MCPToolDefinition(
                tool_id=tool_id,
                name=name,
                description=description,
                parameters=parameters,
                returns=returns,
                examples=examples or [],
                metadata=kwargs.get("metadata", {})
            )
            
            # Save tool definition
            self.tool_definitions[tool_id] = tool_definition
            self._save_registries()
            
            # Save individual tool file
            tool_file = self.tool_definitions_path / f"{tool_id}.json"
            with open(tool_file, 'w') as f:
                json.dump(asdict(tool_definition), f, indent=2)
            
            # Store in memory
            await self.memory_agent.store_memory(
                agent_id="mcp_tool",
                memory_type="system_state",
                content={
                    "action": "tool_registered",
                    "tool_id": tool_id,
                    "name": name
                },
                importance="high"
            )
            
            logger.info(f"Registered tool: {tool_id} ({name})")
            
            return {
                "success": True,
                "tool_id": tool_id,
                "tool_definition": asdict(tool_definition)
            }
        except Exception as e:
            logger.error(f"Error registering tool: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_tool_definition(self,
                                   tool_id: str,
                                   **kwargs) -> Dict[str, Any]:
        """Get tool definition."""
        if tool_id not in self.tool_definitions:
            return {
                "success": False,
                "error": f"Tool definition not found: {tool_id}"
            }
        
        return {
            "success": True,
            "tool_definition": asdict(self.tool_definitions[tool_id])
        }
    
    async def _list_tools(self,
                         **kwargs) -> Dict[str, Any]:
        """List all tool definitions."""
        tools = []
        for tool_id, tool_def in self.tool_definitions.items():
            tools.append({
                "tool_id": tool_id,
                "name": tool_def.name,
                "description": tool_def.description,
                "parameters": tool_def.parameters,
                "returns": tool_def.returns
            })
        
        return {
            "success": True,
            "tools": tools,
            "count": len(tools)
        }
    
    async def _get_action_context(self,
                                 agent_id: str,
                                 action_id: str,
                                 **kwargs) -> Dict[str, Any]:
        """Get context for an action."""
        # Find contexts for this action
        contexts = [
            ctx for ctx in self.contexts.values()
            if ctx.agent_id == agent_id and ctx.action_id == action_id
        ]
        
        if not contexts:
            return {
                "success": False,
                "error": f"No context found for action {action_id}"
            }
        
        # Return most relevant (action_context type preferred)
        action_contexts = [ctx for ctx in contexts if ctx.context_type == MCPContextType.ACTION_CONTEXT]
        if action_contexts:
            context = action_contexts[0]
        else:
            context = contexts[0]
        
        ctx_dict = asdict(context)
        ctx_dict['context_type'] = context.context_type.value
        
        return {
            "success": True,
            "context": ctx_dict
        }
    
    async def _get_tool_context(self,
                               agent_id: str,
                               tool_id: str,
                               **kwargs) -> Dict[str, Any]:
        """Get context for a tool."""
        # Find contexts for this tool
        contexts = [
            ctx for ctx in self.contexts.values()
            if ctx.agent_id == agent_id and ctx.tool_id == tool_id
        ]
        
        if not contexts:
            # Try to get tool definition as context
            if tool_id in self.tool_definitions:
                tool_def = self.tool_definitions[tool_id]
                return {
                    "success": True,
                    "context": {
                        "context_type": "tool_definition",
                        "tool_id": tool_id,
                        "name": tool_def.name,
                        "description": tool_def.description,
                        "parameters": tool_def.parameters,
                        "returns": tool_def.returns,
                        "examples": tool_def.examples
                    }
                }
            
            return {
                "success": False,
                "error": f"No context found for tool {tool_id}"
            }
        
        # Return most relevant (tool_definition type preferred)
        tool_contexts = [ctx for ctx in contexts if ctx.context_type == MCPContextType.TOOL_DEFINITION]
        if tool_contexts:
            context = tool_contexts[0]
        else:
            context = contexts[0]
        
        ctx_dict = asdict(context)
        ctx_dict['context_type'] = context.context_type.value
        
        return {
            "success": True,
            "context": ctx_dict
        }



