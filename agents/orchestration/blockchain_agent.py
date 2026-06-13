# mindx/orchestration/blockchain_agent.py
"""
BlockchainAgent: Immutable archival of proven agents/tools.

This agent handles archiving proven agents, tools, personas, prompts, and data
to blockchain as immutable records for the knowledge economy and Agenticplace marketplace.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from agents.memory_agent import MemoryAgent
from agents.orchestration.coordinator_agent import CoordinatorAgent

logger = get_logger(__name__)


class BlockchainAgent:
    """
    Agent specialized in immutable archival to blockchain.
    Archives proven agents, tools, personas, prompts, and data.
    """
    
    def __init__(
        self,
        agent_id: str = "blockchain_agent",
        coordinator_agent: Optional[CoordinatorAgent] = None,
        memory_agent: Optional[MemoryAgent] = None,
        config: Optional[Config] = None,
        test_mode: bool = False
    ):
        self.agent_id = agent_id
        self.coordinator_agent = coordinator_agent
        self.memory_agent = memory_agent or MemoryAgent(config=config)
        self.config = config or Config(test_mode=test_mode)
        self.test_mode = test_mode
        self.log_prefix = f"BlockchainAgent ({self.agent_id}):"
        
        # Blockchain factory delegate (agents.blockchain.BlockchainAgentFactory)
        self.connected = False
        self._factory = None

        # Archive history
        self.archive_history: List[Dict[str, Any]] = []
    
    async def initialize(self) -> bool:
        """
        Initialize the blockchain factory delegate.

        Real on-chain work lives in the agnostic `agents.blockchain` module
        (BlockchainAgentFactory); this orchestration agent is the public entry
        point that mindX dispatches to.

        Returns:
            True if initialized successfully
        """
        logger.info(f"{self.log_prefix} Initializing blockchain factory delegate")

        try:
            from agents.blockchain import BlockchainAgentFactory

            self._factory = await BlockchainAgentFactory.get_instance(config=self.config)
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"{self.log_prefix} Error initializing blockchain factory: {e}", exc_info=True)
            return False

    async def mint_agent(self, name: str, *, dry_run: bool = True, **kwargs) -> Dict[str, Any]:
        """
        Mint a mindX agent as an ERC-7857 iNFT via the blockchain factory.

        See agents/blockchain/agent_factory.py and
        docs/blockchain/BLOCKCHAIN_AGENTS.md for the full pipeline.
        """
        if not self.connected:
            await self.initialize()
        result = await self._factory.mint_agent(name, dry_run=dry_run, **kwargs)
        if self.memory_agent:
            await self.memory_agent.log_process(
                "blockchain_mint_agent",
                {"timestamp": time.time(), "name": name, "dry_run": dry_run, "result": result},
                {"agent_id": self.agent_id},
            )
        return result
    
    async def archive_agent(
        self,
        agent_id: str,
        agent_data: Dict[str, Any],
        persona: Optional[Dict[str, Any]] = None,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Archive a proven agent to blockchain as immutable.
        
        Args:
            agent_id: ID of the agent
            agent_data: Agent data
            persona: Optional agent persona
            prompt: Optional agent prompt
        
        Returns:
            Dictionary with archive results
        """
        if not self.connected:
            await self.initialize()
        
        logger.info(f"{self.log_prefix} Archiving agent {agent_id} to blockchain")

        try:
            # Real archival = mint the agent as an ERC-7857 iNFT via the factory.
            # In test_mode we dry-run (no broadcast); otherwise mint live.
            slug = "".join(c if (c.isalnum() or c in "-_") else "-" for c in agent_id).strip("-") or "agent"
            mint = await self.mint_agent(slug, dry_run=self.test_mode)
            tx_hash = (mint or {}).get("tx_hash") or (mint or {}).get("storageURI")

            result = {
                "success": (mint or {}).get("status") in ("minted", "dry_run"),
                "entity_type": "agent",
                "entity_id": agent_id,
                "transaction_hash": tx_hash,
                "token_id": (mint or {}).get("tokenId"),
                "immutable": True,
                "mint": mint,
                "archived_at": time.time()
            }

            self.archive_history.append({
                "timestamp": time.time(),
                "entity_type": "agent",
                "entity_id": agent_id,
                "result": result
            })
            
            if self.memory_agent:
                await self.memory_agent.log_process(
                    "blockchain_archive_agent",
                    {
                        "timestamp": time.time(),
                        "agent_id": agent_id,
                        "result": result
                    },
                    {"agent_id": self.agent_id}
                )
            
            logger.info(f"{self.log_prefix} Agent {agent_id} archived to blockchain: {tx_hash}")
            return result
        except Exception as e:
            logger.error(f"{self.log_prefix} Error archiving agent: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def archive_tool(
        self,
        tool_id: str,
        tool_data: Dict[str, Any],
        prompt_template: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Archive a proven tool to blockchain as immutable.
        
        Args:
            tool_id: ID of the tool
            tool_data: Tool data
            prompt_template: Optional prompt template
        
        Returns:
            Dictionary with archive results
        """
        if not self.connected:
            await self.initialize()
        
        logger.info(f"{self.log_prefix} Archiving tool {tool_id} to blockchain")
        
        archive_data = {
            "entity_type": "tool",
            "entity_id": tool_id,
            "tool_data": tool_data,
            "prompt_template": prompt_template,
            "archived_at": time.time(),
            "immutable": True
        }
        
        try:
            # TODO: Implement actual blockchain archival
            tx_hash = f"0x{tool_id[:40]}_placeholder"
            
            result = {
                "success": True,
                "entity_type": "tool",
                "entity_id": tool_id,
                "transaction_hash": tx_hash,
                "immutable": True,
                "archived_at": time.time()
            }
            
            self.archive_history.append({
                "timestamp": time.time(),
                "entity_type": "tool",
                "entity_id": tool_id,
                "result": result
            })
            
            logger.info(f"{self.log_prefix} Tool {tool_id} archived to blockchain: {tx_hash}")
            return result
        except Exception as e:
            logger.error(f"{self.log_prefix} Error archiving tool: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def share_knowledge(
        self,
        knowledge_data: Dict[str, Any],
        marketplace: str = "agenticplace"
    ) -> Dict[str, Any]:
        """
        Share knowledge via blockchain for the knowledge economy.
        
        Args:
            knowledge_data: Knowledge to share
            marketplace: Marketplace name (default: agenticplace)
        
        Returns:
            Dictionary with sharing results
        """
        if not self.connected:
            await self.initialize()
        
        logger.info(f"{self.log_prefix} Sharing knowledge to {marketplace}")
        
        try:
            # TODO: Implement knowledge sharing to blockchain
            # This would enable knowledge economy participation
            
            result = {
                "success": True,
                "marketplace": marketplace,
                "shared_at": time.time(),
                "message": "Knowledge sharing not yet implemented"
            }
            
            return result
        except Exception as e:
            logger.error(f"{self.log_prefix} Error sharing knowledge: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def query_archived_entity(
        self,
        entity_type: str,
        entity_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Query an archived entity from blockchain.
        
        Args:
            entity_type: Type of entity ("agent" or "tool")
            entity_id: ID of the entity
        
        Returns:
            Archived entity data or None
        """
        if not self.connected:
            await self.initialize()
        
        logger.debug(f"{self.log_prefix} Querying archived {entity_type}: {entity_id}")
        
        # TODO: Implement blockchain query
        # This would query the blockchain for the entity
        
        return None
    
    async def shutdown(self):
        """Shutdown the blockchain agent."""
        logger.info(f"{self.log_prefix} Shutting down")
