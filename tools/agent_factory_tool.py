# mindx/tools/agent_factory_tool.py
"""
Agent Factory Tool for MindX.
This tool enables the BDI agent to create new agents with proper lifecycle management.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from core.bdi_agent import BaseTool
from core.id_manager_agent import IDManagerAgent
from agents.guardian_agent import GuardianAgent
from agents.memory_agent import MemoryAgent
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

class AgentFactoryTool(BaseTool):
    """Tool for creating new agents with full lifecycle management."""
    
    def __init__(self, 
                 memory_agent: MemoryAgent,
                 coordinator_ref: Optional[Any] = None,
                 guardian_ref: Optional[GuardianAgent] = None,
                 config: Optional[Config] = None,
                 **kwargs):
        super().__init__(config=config, **kwargs)
        self.memory_agent = memory_agent
        self.coordinator_ref = coordinator_ref
        self.guardian_ref = guardian_ref
        self.config = config or Config()
        
        # Agent templates directory
        self.agent_templates_dir = PROJECT_ROOT / "agents" / "templates"
        self.agent_templates_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_prefix = "AgentFactoryTool:"
        logger.info(f"{self.log_prefix} Initialized with agent creation capabilities.")

    async def execute(self, 
                     action: str,
                     agent_type: str = None,
                     agent_id: str = None,
                     agent_config: Optional[Dict[str, Any]] = None,
                     **kwargs) -> Tuple[bool, Any]:
        """Execute agent factory operations."""
        try:
            if action == "create_agent":
                return await self._create_agent(agent_type, agent_id, agent_config or {})
            elif action == "validate_agent":
                return await self._validate_agent(agent_id)
            else:
                return False, f"Unknown action: {action}"
                
        except Exception as e:
            logger.error(f"{self.log_prefix} Error executing action '{action}': {e}", exc_info=True)
            return False, f"Agent factory error: {e}"

    async def _create_agent(self, agent_type: str, agent_id: str, agent_config: Dict[str, Any]) -> Tuple[bool, Any]:
        """Create a new agent with full lifecycle management."""
        logger.info(f"{self.log_prefix} Creating new agent: {agent_id} of type {agent_type}")
        
        try:
            # Step 1: Get ID Manager and create identity
            id_manager = await IDManagerAgent.get_instance()
            public_key, env_var_name = await id_manager.create_new_wallet(entity_id=agent_id)
            
            # Step 2: Guardian validation
            if self.guardian_ref:
                guardian_validation = await self._validate_with_guardian(agent_id, public_key)
                if not guardian_validation[0]:
                    return False, f"Guardian validation failed: {guardian_validation[1]}"
            
            # Step 3: Create agent workspace
            agent_workspace = self.memory_agent.get_agent_data_directory(agent_id)
            agent_workspace.mkdir(parents=True, exist_ok=True)
            
            # Step 4: Generate agent code
            agent_code_path = await self._generate_agent_code(agent_type, agent_id, agent_config)
            
            # Step 5: Register with coordinator
            if self.coordinator_ref:
                registration_result = await self.coordinator_ref.create_and_register_agent(
                    agent_type, agent_id, agent_config
                )
                if registration_result.get("status") != "SUCCESS":
                    return False, f"Coordinator registration failed: {registration_result}"
            
            # Step 6: Create agent metadata
            agent_metadata = {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "public_key": public_key,
                "env_var_name": env_var_name,
                "workspace_path": str(agent_workspace),
                "code_path": str(agent_code_path) if agent_code_path else None,
                "created_at": time.time(),
                "created_by": "agent_factory_tool",
                "config": agent_config,
                "status": "active"
            }
            
            # Step 7: Save agent metadata
            metadata_path = agent_workspace / "agent_metadata.json"
            with metadata_path.open("w", encoding="utf-8") as f:
                json.dump(agent_metadata, f, indent=2)
            
            logger.info(f"{self.log_prefix} Successfully created agent {agent_id}")
            return True, agent_metadata
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to create agent {agent_id}: {e}", exc_info=True)
            return False, f"Agent creation failed: {e}"

    async def _validate_with_guardian(self, agent_id: str, public_key: str) -> Tuple[bool, Any]:
        """Validate new agent with Guardian agent."""
        try:
            if not self.guardian_ref:
                return True, "No guardian validation required"
            
            # Get challenge from guardian
            challenge = self.guardian_ref.get_challenge(agent_id)
            
            # Sign challenge with agent's private key
            id_manager = await IDManagerAgent.get_instance()
            signature = await id_manager.sign_message(agent_id, challenge)
            
            if not signature:
                return False, "Failed to sign challenge"
            
            # Verify with guardian
            private_key = await self.guardian_ref.get_private_key(agent_id, challenge, signature)
            
            if private_key:
                logger.info(f"{self.log_prefix} Guardian validation successful for {agent_id}")
                return True, "Guardian validation successful"
            else:
                return False, "Guardian validation failed"
                
        except Exception as e:
            logger.error(f"{self.log_prefix} Guardian validation error for {agent_id}: {e}")
            return False, f"Guardian validation error: {e}"

    async def _generate_agent_code(self, agent_type: str, agent_id: str, agent_config: Dict[str, Any]) -> Optional[Path]:
        """Generate agent code from template."""
        try:
            agent_class_name = f"{agent_id.replace('_', '').title()}Agent"
            agent_description = agent_config.get("description", f"Dynamically created {agent_type}")
            
            agent_code = f'''# mindx/agents/{agent_id}.py
"""
{agent_class_name} - Dynamically created agent.
Type: {agent_type}
Description: {agent_description}
"""

import time
from typing import Dict, Any, Optional

from core.id_manager_agent import IDManagerAgent
from agents.memory_agent import MemoryAgent
from utils.config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)

class {agent_class_name}:
    """Dynamically created {agent_type} agent."""
    
    def __init__(self, 
                 agent_id: str = "{agent_id}",
                 config: Optional[Config] = None,
                 memory_agent: Optional[MemoryAgent] = None,
                 **kwargs):
        self.agent_id = agent_id
        self.config = config or Config()
        self.memory_agent = memory_agent or MemoryAgent(config=self.config)
        self.log_prefix = f"{agent_class_name}:"
        
        # Initialize identity
        self._init_identity()
        
        logger.info(f"{{self.log_prefix}} Initialized agent {{self.agent_id}}")
    
    def _init_identity(self):
        """Initialize agent identity."""
        try:
            from core.id_manager_agent import IDManagerAgent
            id_manager = IDManagerAgent.get_instance()
            id_manager.create_new_wallet(entity_id=self.agent_id)
        except Exception as e:
            logger.error(f"{{self.log_prefix}} Failed to initialize identity: {{e}}")
    
    async def execute_task(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a task assigned to this agent."""
        logger.info(f"{{self.log_prefix}} Executing task: {{task}}")
        
        try:
            # Basic task execution logic
            result = {{
                "status": "SUCCESS",
                "agent_id": self.agent_id,
                "task": task,
                "context": context or {{}},
                "result": f"Task '{{task}}' executed successfully",
                "timestamp": time.time()
            }}
            
            # Log to memory
            await self.memory_agent.save_timestampmemory(
                self.agent_id,
                "TASK_EXECUTION",
                result,
                importance="MEDIUM"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"{{self.log_prefix}} Task execution failed: {{e}}")
            return {{
                "status": "ERROR",
                "agent_id": self.agent_id,
                "task": task,
                "error": str(e),
                "timestamp": time.time()
            }}

# Factory function for easy instantiation
async def create_{agent_id}(**kwargs) -> {agent_class_name}:
    """Factory function to create {agent_class_name} instance."""
    return {agent_class_name}(**kwargs)
'''
            
            # Save to agents directory
            agent_code_path = PROJECT_ROOT / "agents" / f"{agent_id}.py"
            with agent_code_path.open("w", encoding="utf-8") as f:
                f.write(agent_code)
            
            logger.info(f"{self.log_prefix} Generated agent code at {agent_code_path}")
            return agent_code_path
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to generate agent code: {e}")
            return None

    async def _validate_agent(self, agent_id: str) -> Tuple[bool, Any]:
        """Validate agent identity and workspace."""
        try:
            # Check if agent has valid identity
            id_manager = await IDManagerAgent.get_instance()
            public_key = await id_manager.get_public_address(agent_id)
            if not public_key:
                return False, "No valid identity found"
            
            # Check if agent workspace exists
            agent_workspace = self.memory_agent.get_agent_data_directory(agent_id)
            if not agent_workspace.exists():
                return False, "Agent workspace not found"
            
            # Check if agent code exists
            agent_code_path = PROJECT_ROOT / "agents" / f"{agent_id}.py"
            if not agent_code_path.exists():
                return False, "Agent code not found"
            
            return True, {
                "agent_id": agent_id,
                "public_key": public_key,
                "workspace_path": str(agent_workspace),
                "code_path": str(agent_code_path),
                "validation_status": "PASSED"
            }
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Agent validation failed for {agent_id}: {e}")
            return False, f"Agent validation error: {e}"
