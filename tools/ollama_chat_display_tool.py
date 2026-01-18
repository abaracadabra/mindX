# mindx/tools/ollama_chat_display_tool.py
"""
Ollama Chat Display Tool: Manages and displays Ollama chat conversations for mindXagent.

This tool provides a unified interface for displaying, managing, and interacting with
Ollama chat conversations. It integrates with mindXagent to show real-time conversations
between mindXagent and Ollama models.

Related: aGLM (AutoGLM) - https://github.com/autoglm
OpenSea Collection: https://opensea.io/collection/aglm
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)


class OllamaChatDisplayTool:
    """
    Tool for displaying and managing Ollama chat conversations.
    
    This tool provides:
    - Real-time conversation display
    - Conversation history management
    - Message formatting and rendering
    - Integration with mindXagent's Ollama chat manager
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the Ollama Chat Display Tool"""
        self.config = config or Config()
        self.data_dir = PROJECT_ROOT / "data" / "tools" / "ollama_chat_display"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
    async def get_conversation_history(
        self, 
        conversation_id: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get conversation history for display.
        
        Args:
            conversation_id: Optional conversation ID, defaults to mindXagent default
            limit: Maximum number of messages to return
            
        Returns:
            Dictionary with conversation_id, messages, and metadata
        """
        try:
            from agents.core.mindXagent import MindXAgent
            
            mindxagent = await MindXAgent.get_instance()
            if not mindxagent:
                return {
                    "success": False,
                    "error": "mindXagent not initialized",
                    "conversation_id": None,
                    "messages": [],
                    "total_count": 0
                }
            
            # Get conversation history from mindXagent
            conv_id = conversation_id or f"{mindxagent.agent_id}_default"
            history = mindxagent.get_ollama_conversation_history(conv_id)
            
            # Format messages for display
            formatted_messages = []
            if history:
                for msg in history[-limit:]:
                    # Ensure message has required fields
                    if isinstance(msg, dict):
                        formatted_msg = {
                            "role": msg.get("role", "unknown"),
                            "content": msg.get("content", msg.get("message", "")),
                            "timestamp": msg.get("timestamp", datetime.now().timestamp())
                        }
                        formatted_messages.append(formatted_msg)
                    elif isinstance(msg, str):
                        # Handle string messages (legacy format)
                        formatted_messages.append({
                            "role": "assistant",
                            "content": msg,
                            "timestamp": datetime.now().timestamp()
                        })
            
            return {
                "success": True,
                "conversation_id": conv_id,
                "messages": formatted_messages,
                "total_count": len(history) if history else 0,
                "last_updated": datetime.now().isoformat(),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting conversation history: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "conversation_id": None,
                "messages": [],
                "total_count": 0
            }
    
    async def format_message_for_display(
        self,
        message: Dict[str, Any],
        index: int
    ) -> Dict[str, Any]:
        """
        Format a message for UI display.
        
        Args:
            message: Message dictionary with role and content
            index: Message index in conversation
            
        Returns:
            Formatted message dictionary for display
        """
        role = message.get("role", "unknown")
        content = message.get("content", "")
        
        is_user = role == "user"
        is_assistant = role == "assistant"
        
        return {
            "index": index,
            "role": role,
            "content": content,
            "label": "mindXagent → Ollama" if is_user else "Ollama → mindXagent" if is_assistant else "System",
            "is_user": is_user,
            "is_assistant": is_assistant,
            "timestamp": message.get("timestamp", datetime.now().isoformat()),
            "formatted": {
                "bg_color": "rgba(0, 168, 255, 0.15)" if is_user else "rgba(0, 255, 136, 0.15)" if is_assistant else "rgba(255, 255, 255, 0.05)",
                "border_color": "rgba(0, 168, 255, 0.4)" if is_user else "rgba(0, 255, 136, 0.4)" if is_assistant else "rgba(255, 255, 255, 0.2)",
                "text_color": "#00a8ff" if is_user else "#00ff88" if is_assistant else "#ffffff"
            }
        }
    
    async def clear_conversation(
        self,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Clear conversation history.
        
        Args:
            conversation_id: Optional conversation ID to clear
            
        Returns:
            Success status
        """
        try:
            from agents.core.mindXagent import MindXAgent
            
            mindxagent = await MindXAgent.get_instance()
            if not mindxagent:
                return {
                    "success": False,
                    "error": "mindXagent not initialized"
                }
            
            mindxagent.clear_ollama_conversation(conversation_id)
            
            return {
                "success": True,
                "message": "Conversation cleared",
                "conversation_id": conversation_id or f"{mindxagent.agent_id}_default"
            }
        except Exception as e:
            self.logger.error(f"Error clearing conversation: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_display_status(self) -> Dict[str, Any]:
        """
        Get current display status and configuration.
        
        Returns:
            Status dictionary with connection info, model info, etc.
        """
        try:
            from agents.core.mindXagent import MindXAgent
            
            mindxagent = await MindXAgent.get_instance()
            if not mindxagent:
                return {
                    "success": False,
                    "error": "mindXagent not initialized"
                }
            
            ollama_status = await mindxagent.get_ollama_status()
            
            return {
                "success": True,
                "ollama_connected": ollama_status.get("connected", False),
                "available_models": ollama_status.get("models_count", 0),
                "current_model": ollama_status.get("current_model"),
                "conversation_count": ollama_status.get("conversation_count", 0),
                "base_url": ollama_status.get("base_url")
            }
        except Exception as e:
            self.logger.error(f"Error getting display status: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Get tool information and metadata"""
        return {
            "name": "Ollama Chat Display Tool",
            "description": "Manages and displays Ollama chat conversations for mindXagent",
            "version": "1.0.0",
            "author": "mindX",
            "related": {
                "aGLM": {
                    "github": "https://github.com/autoglm",
                    "opensea_collection": "https://opensea.io/collection/aglm",
                    "opensea_nft": "https://opensea.io/item/polygon/0x2953399124f0cbb46d2cbacd8a89cf0599974963/7675060345879017836756807061815685501584179421371855056758523054876166031008",
                    "description": "aGLM (AutoGLM) - 100k ERC1155 collection on Polygon. AGLM Investor information: https://bankon.gitbook.io/aglm-investor/aglm"
                }
            }
        }
