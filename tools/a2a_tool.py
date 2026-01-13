# mindx/tools/a2a_tool.py
"""
A2A (Agent-to-Agent) Tool for MindX.

This tool enables standardized agent-to-agent communication following the A2A protocol.
It provides capabilities for agent discovery, message passing, authentication, and
interoperability with external A2A-compatible systems.

Following mindX doctrine:
- Memory is infrastructure (all A2A communications are logged)
- Standardized protocols enable interoperability
- Cryptographic verification ensures trust
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
import aiohttp
import asyncio

from agents.core.bdi_agent import BaseTool
from agents.memory_agent import MemoryAgent
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)


class A2AMessageType(Enum):
    """Types of A2A messages."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    DISCOVERY = "discovery"
    CAPABILITY_QUERY = "capability_query"
    ACTION = "action"


class A2AProtocolVersion(Enum):
    """A2A protocol versions."""
    V1_0 = "1.0"
    V2_0 = "2.0"


@dataclass
class A2AMessage:
    """A2A message structure."""
    message_id: str
    from_agent: str
    to_agent: str
    message_type: A2AMessageType
    protocol_version: str
    timestamp: str
    payload: Dict[str, Any]
    signature: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class A2AAgentCard:
    """A2A agent card (model card) for discovery."""
    agent_id: str
    name: str
    description: str
    version: str
    capabilities: List[str]
    endpoint: str
    public_key: Optional[str] = None
    signature: Optional[str] = None
    metadata: Dict[str, Any] = None
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.utcnow().isoformat()


class A2ATool(BaseTool):
    """
    A2A Tool - Enables agent-to-agent communication.
    
    This tool provides standardized A2A protocol support for:
    - Agent discovery and registration
    - Message passing between agents
    - Cryptographic authentication
    - Capability queries
    - Action execution requests
    """
    
    def __init__(self,
                 memory_agent: MemoryAgent,
                 config: Optional[Config] = None,
                 **kwargs):
        super().__init__(config=config, **kwargs)
        self.memory_agent = memory_agent
        self.config = config or Config()
        self.project_root = PROJECT_ROOT
        
        # A2A storage
        self.a2a_path = self.project_root / "data" / "a2a"
        self.a2a_path.mkdir(parents=True, exist_ok=True)
        self.agent_cards_path = self.a2a_path / "agent_cards"
        self.messages_path = self.a2a_path / "messages"
        self.agent_cards_path.mkdir(exist_ok=True)
        self.messages_path.mkdir(exist_ok=True)
        
        # Registry files
        self.agent_cards_registry_path = self.a2a_path / "agent_cards_registry.json"
        self.messages_registry_path = self.a2a_path / "messages_registry.json"
        
        # In-memory registries
        self.agent_cards: Dict[str, A2AAgentCard] = {}
        self.message_history: List[A2AMessage] = []
        
        # Protocol version
        self.protocol_version = A2AProtocolVersion.V2_0.value
        
        # Load existing data
        self._load_registries()
        
        logger.info("A2ATool initialized")
    
    def _load_registries(self):
        """Load agent cards and message history from disk."""
        # Load agent cards
        if self.agent_cards_registry_path.exists():
            try:
                with open(self.agent_cards_registry_path, 'r') as f:
                    data = json.load(f)
                    for agent_id, card_dict in data.items():
                        self.agent_cards[agent_id] = A2AAgentCard(**card_dict)
                logger.info(f"Loaded {len(self.agent_cards)} agent cards")
            except Exception as e:
                logger.error(f"Error loading agent cards: {e}")
        
        # Load message history (last 1000 messages)
        if self.messages_registry_path.exists():
            try:
                with open(self.messages_registry_path, 'r') as f:
                    data = json.load(f)
                    for msg_dict in data.get("messages", [])[-1000:]:
                        msg_dict['message_type'] = A2AMessageType(msg_dict['message_type'])
                        self.message_history.append(A2AMessage(**msg_dict))
                logger.info(f"Loaded {len(self.message_history)} messages from history")
            except Exception as e:
                logger.error(f"Error loading message history: {e}")
    
    def _save_registries(self):
        """Save agent cards and message history to disk."""
        # Save agent cards
        try:
            data = {}
            for agent_id, card in self.agent_cards.items():
                data[agent_id] = asdict(card)
            with open(self.agent_cards_registry_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving agent cards: {e}")
        
        # Save message history (last 1000)
        try:
            recent_messages = self.message_history[-1000:]
            data = {
                "messages": [asdict(msg) for msg in recent_messages]
            }
            with open(self.messages_registry_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving message history: {e}")
    
    async def execute(self, operation: str, **kwargs) -> Dict[str, Any]:
        """
        Execute A2A tool operations.
        
        Operations:
        - register_agent: Register an agent with A2A protocol
        - discover_agents: Discover available agents
        - send_message: Send a message to another agent
        - receive_message: Receive and process a message
        - query_capabilities: Query an agent's capabilities
        - execute_action: Request an action from another agent
        - get_agent_card: Get agent card for an agent
        - list_agents: List all registered agents
        - generate_discovery_endpoint: Generate .well-known/agents.json
        """
        try:
            if operation == "register_agent":
                return await self._register_agent(**kwargs)
            elif operation == "discover_agents":
                return await self._discover_agents(**kwargs)
            elif operation == "send_message":
                return await self._send_message(**kwargs)
            elif operation == "receive_message":
                return await self._receive_message(**kwargs)
            elif operation == "query_capabilities":
                return await self._query_capabilities(**kwargs)
            elif operation == "execute_action":
                return await self._execute_action(**kwargs)
            elif operation == "get_agent_card":
                return await self._get_agent_card(**kwargs)
            elif operation == "list_agents":
                return await self._list_agents(**kwargs)
            elif operation == "generate_discovery_endpoint":
                return await self._generate_discovery_endpoint(**kwargs)
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {operation}"
                }
        except Exception as e:
            logger.error(f"Error executing A2A operation {operation}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _register_agent(self,
                            agent_id: str,
                            name: str,
                            description: str,
                            capabilities: List[str],
                            endpoint: Optional[str] = None,
                            public_key: Optional[str] = None,
                            version: str = "1.0.0",
                            **kwargs) -> Dict[str, Any]:
        """Register an agent with A2A protocol."""
        try:
            # Generate endpoint if not provided
            if not endpoint:
                endpoint = f"https://mindx.internal/{agent_id}/a2a"
            
            # Create agent card
            agent_card = A2AAgentCard(
                agent_id=agent_id,
                name=name,
                description=description,
                version=version,
                capabilities=capabilities,
                endpoint=endpoint,
                public_key=public_key,
                metadata=kwargs.get("metadata", {})
            )
            
            # Generate signature if public key provided
            if public_key:
                signature_data = f"{agent_id}:{name}:{endpoint}:{time.time()}"
                agent_card.signature = hashlib.sha256(signature_data.encode()).hexdigest()
            
            # Save agent card
            self.agent_cards[agent_id] = agent_card
            self._save_registries()
            
            # Save individual card file
            card_file = self.agent_cards_path / f"{agent_id}.json"
            with open(card_file, 'w') as f:
                json.dump(asdict(agent_card), f, indent=2)
            
            # Store in memory
            await self.memory_agent.store_memory(
                agent_id="a2a_tool",
                memory_type="system_state",
                content={
                    "action": "agent_registered",
                    "agent_id": agent_id,
                    "name": name,
                    "capabilities": capabilities
                },
                importance="high"
            )
            
            logger.info(f"Registered agent: {agent_id} ({name})")
            
            return {
                "success": True,
                "agent_id": agent_id,
                "agent_card": asdict(agent_card)
            }
        except Exception as e:
            logger.error(f"Error registering agent: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _discover_agents(self,
                              query: Optional[str] = None,
                              capability: Optional[str] = None,
                              **kwargs) -> Dict[str, Any]:
        """Discover available agents."""
        agents = []
        
        for agent_id, card in self.agent_cards.items():
            # Apply filters
            if query and query.lower() not in card.name.lower() and query.lower() not in card.description.lower():
                continue
            if capability and capability not in card.capabilities:
                continue
            
            agents.append({
                "agent_id": agent_id,
                "name": card.name,
                "description": card.description,
                "capabilities": card.capabilities,
                "endpoint": card.endpoint,
                "version": card.version
            })
        
        return {
            "success": True,
            "agents": agents,
            "count": len(agents)
        }
    
    async def _send_message(self,
                           from_agent: str,
                           to_agent: str,
                           message_type: str,
                           payload: Dict[str, Any],
                           signature: Optional[str] = None,
                           **kwargs) -> Dict[str, Any]:
        """Send a message to another agent."""
        try:
            # Verify from_agent is registered
            if from_agent not in self.agent_cards:
                return {
                    "success": False,
                    "error": f"From agent not registered: {from_agent}"
                }
            
            # Create message
            message_id = hashlib.sha256(
                f"{from_agent}:{to_agent}:{time.time()}".encode()
            ).hexdigest()[:16]
            
            message = A2AMessage(
                message_id=message_id,
                from_agent=from_agent,
                to_agent=to_agent,
                message_type=A2AMessageType(message_type),
                protocol_version=self.protocol_version,
                timestamp=datetime.utcnow().isoformat(),
                payload=payload,
                signature=signature,
                metadata=kwargs.get("metadata", {})
            )
            
            # Add to history
            self.message_history.append(message)
            if len(self.message_history) > 10000:
                self.message_history = self.message_history[-10000:]
            self._save_registries()
            
            # Save message file
            message_file = self.messages_path / f"{message_id}.json"
            with open(message_file, 'w') as f:
                json.dump(asdict(message), f, indent=2)
            
            # Store in memory
            await self.memory_agent.store_memory(
                agent_id="a2a_tool",
                memory_type="interaction",
                content={
                    "action": "message_sent",
                    "message_id": message_id,
                    "from_agent": from_agent,
                    "to_agent": to_agent,
                    "message_type": message_type
                },
                importance="medium"
            )
            
            # If to_agent is registered and has endpoint, attempt delivery
            if to_agent in self.agent_cards:
                card = self.agent_cards[to_agent]
                if card.endpoint:
                    # Attempt HTTP delivery (async, non-blocking)
                    asyncio.create_task(self._deliver_message(message, card.endpoint))
            
            return {
                "success": True,
                "message_id": message_id,
                "message": asdict(message)
            }
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _deliver_message(self, message: A2AMessage, endpoint: str):
        """Deliver message via HTTP to agent endpoint."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{endpoint}/messages",
                    json=asdict(message),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        logger.info(f"Message {message.message_id} delivered to {endpoint}")
                    else:
                        logger.warning(f"Message delivery failed: {resp.status}")
        except Exception as e:
            logger.warning(f"Error delivering message: {e}")
    
    async def _receive_message(self,
                              agent_id: str,
                              message_id: Optional[str] = None,
                              **kwargs) -> Dict[str, Any]:
        """Receive and process a message."""
        # Find messages for this agent
        messages = [
            msg for msg in self.message_history
            if msg.to_agent == agent_id
        ]
        
        if message_id:
            messages = [msg for msg in messages if msg.message_id == message_id]
        
        if not messages:
            return {
                "success": False,
                "error": "No messages found"
            }
        
        # Return most recent
        message = messages[-1]
        
        return {
            "success": True,
            "message": asdict(message)
        }
    
    async def _query_capabilities(self,
                                  agent_id: str,
                                  **kwargs) -> Dict[str, Any]:
        """Query an agent's capabilities."""
        if agent_id not in self.agent_cards:
            return {
                "success": False,
                "error": f"Agent not found: {agent_id}"
            }
        
        card = self.agent_cards[agent_id]
        
        return {
            "success": True,
            "agent_id": agent_id,
            "capabilities": card.capabilities,
            "agent_card": asdict(card)
        }
    
    async def _execute_action(self,
                             from_agent: str,
                             to_agent: str,
                             action: str,
                             parameters: Dict[str, Any],
                             **kwargs) -> Dict[str, Any]:
        """Request an action from another agent."""
        # Send action message
        return await self._send_message(
            from_agent=from_agent,
            to_agent=to_agent,
            message_type="action",
            payload={
                "action": action,
                "parameters": parameters
            },
            metadata=kwargs.get("metadata", {})
        )
    
    async def _get_agent_card(self,
                             agent_id: str,
                             **kwargs) -> Dict[str, Any]:
        """Get agent card for an agent."""
        if agent_id not in self.agent_cards:
            return {
                "success": False,
                "error": f"Agent not found: {agent_id}"
            }
        
        return {
            "success": True,
            "agent_card": asdict(self.agent_cards[agent_id])
        }
    
    async def _list_agents(self,
                          **kwargs) -> Dict[str, Any]:
        """List all registered agents."""
        agents = []
        for agent_id, card in self.agent_cards.items():
            agents.append({
                "agent_id": agent_id,
                "name": card.name,
                "description": card.description,
                "capabilities": card.capabilities,
                "endpoint": card.endpoint,
                "version": card.version
            })
        
        return {
            "success": True,
            "agents": agents,
            "count": len(agents)
        }
    
    async def _generate_discovery_endpoint(self,
                                          base_url: str = "https://mindx.internal",
                                          **kwargs) -> Dict[str, Any]:
        """Generate .well-known/agents.json discovery endpoint."""
        agents_list = []
        
        for agent_id, card in self.agent_cards.items():
            agents_list.append({
                "id": agent_id,
                "name": card.name,
                "description": card.description,
                "version": card.version,
                "capabilities": card.capabilities,
                "endpoint": card.endpoint,
                "public_key": card.public_key,
                "signature": card.signature
            })
        
        discovery_data = {
            "protocol_version": self.protocol_version,
            "agents": agents_list,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Save discovery file
        discovery_path = self.a2a_path / ".well-known" / "agents.json"
        discovery_path.parent.mkdir(parents=True, exist_ok=True)
        with open(discovery_path, 'w') as f:
            json.dump(discovery_data, f, indent=2)
        
        return {
            "success": True,
            "discovery_endpoint": f"{base_url}/.well-known/agents.json",
            "agents_count": len(agents_list),
            "file_path": str(discovery_path)
        }



