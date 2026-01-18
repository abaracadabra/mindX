"""
Connection Manager Tool for mindXagent

This tool manages LLM provider connections, checks for API keys,
and defaults to Ollama when no API keys are found.
"""

import os
from typing import Dict, Any, Optional, List
from utils.logging_config import get_logger
from utils.config import Config
from tools.base_tool import BaseTool

logger = get_logger(__name__)


class ConnectionManagerTool(BaseTool):
    """
    Tool for managing LLM provider connections and defaulting to Ollama.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize Connection Manager Tool"""
        super().__init__(
            name="connection_manager",
            description="Manages LLM provider connections, checks API keys, and defaults to Ollama",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["check_connections", "get_available_providers", "default_to_ollama"],
                        "description": "Action to perform"
                    }
                },
                "required": ["action"]
            }
        )
        self.config = config or Config()
        self.log_prefix = "ConnectionManagerTool:"
    
    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Execute connection management action.
        
        Args:
            action: Action to perform (check_connections, get_available_providers, default_to_ollama)
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with action results
        """
        if action == "check_connections":
            return await self._check_connections()
        elif action == "get_available_providers":
            return await self._get_available_providers()
        elif action == "default_to_ollama":
            return await self._default_to_ollama()
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}"
            }
    
    async def _check_connections(self) -> Dict[str, Any]:
        """
        Check all LLM provider connections and API key availability.
        
        Returns:
            Dictionary with connection status for each provider
        """
        providers_status = {}
        
        # Check common LLM providers
        providers = [
            {
                "name": "openai",
                "api_key_env": "OPENAI_API_KEY",
                "requires_api_key": True,
                "requires_base_url": False
            },
            {
                "name": "gemini",
                "api_key_env": "GEMINI_API_KEY",
                "config_key": "llm.gemini.api_key",
                "requires_api_key": True,
                "requires_base_url": False
            },
            {
                "name": "mistral",
                "api_key_env": "MISTRAL_API_KEY",
                "config_key": "llm.mistral.api_key",
                "requires_api_key": True,
                "requires_base_url": False
            },
            {
                "name": "anthropic",
                "api_key_env": "ANTHROPIC_API_KEY",
                "requires_api_key": True,
                "requires_base_url": False
            },
            {
                "name": "ollama",
                "api_key_env": None,
                "base_url_env": "MINDX_LLM__OLLAMA__BASE_URL",
                "config_key": "llm.ollama.base_url",
                "requires_api_key": False,
                "requires_base_url": True,
                "default_base_url": "http://localhost:11434"
            }
        ]
        
        for provider in providers:
            provider_name = provider["name"]
            has_api_key = False
            has_base_url = False
            api_key_source = None
            base_url = None
            
            # Check API key
            if provider.get("requires_api_key"):
                env_key = provider.get("api_key_env")
                config_key = provider.get("config_key")
                
                if env_key and os.getenv(env_key):
                    has_api_key = True
                    api_key_source = "environment"
                elif config_key and self.config.get(config_key):
                    has_api_key = True
                    api_key_source = "config"
            
            # Check base URL (for Ollama)
            if provider.get("requires_base_url"):
                env_url = provider.get("base_url_env")
                config_key = provider.get("config_key")
                
                if env_url and os.getenv(env_url):
                    base_url = os.getenv(env_url)
                    has_base_url = True
                elif config_key and self.config.get(config_key):
                    base_url = self.config.get(config_key)
                    has_base_url = True
                elif provider.get("default_base_url"):
                    base_url = provider["default_base_url"]
                    has_base_url = True  # Default is available
            
            providers_status[provider_name] = {
                "available": has_api_key or (has_base_url if provider.get("requires_base_url") else False),
                "has_api_key": has_api_key,
                "has_base_url": has_base_url,
                "api_key_source": api_key_source,
                "base_url": base_url,
                "requires_api_key": provider.get("requires_api_key", False),
                "requires_base_url": provider.get("requires_base_url", False)
            }
        
        # Determine recommended provider
        recommended_provider = None
        if providers_status.get("ollama", {}).get("available"):
            recommended_provider = "ollama"
        else:
            # Find first provider with API key
            for name, status in providers_status.items():
                if name != "ollama" and status.get("available"):
                    recommended_provider = name
                    break
        
        return {
            "success": True,
            "providers": providers_status,
            "recommended_provider": recommended_provider,
            "has_any_provider": any(s.get("available") for s in providers_status.values())
        }
    
    async def _get_available_providers(self) -> Dict[str, Any]:
        """
        Get list of available providers with their status.
        
        Returns:
            Dictionary with available providers list
        """
        connections = await self._check_connections()
        available = []
        
        for name, status in connections.get("providers", {}).items():
            if status.get("available"):
                available.append({
                    "name": name,
                    "has_api_key": status.get("has_api_key", False),
                    "has_base_url": status.get("has_base_url", False),
                    "base_url": status.get("base_url")
                })
        
        return {
            "success": True,
            "available_providers": available,
            "count": len(available)
        }
    
    async def _default_to_ollama(self) -> Dict[str, Any]:
        """
        Check if we should default to Ollama (no API keys found).
        
        Returns:
            Dictionary with default recommendation
        """
        connections = await self._check_connections()
        providers = connections.get("providers", {})
        
        # Check if any API key-based provider is available
        has_api_key_provider = False
        for name, status in providers.items():
            if name != "ollama" and status.get("has_api_key"):
                has_api_key_provider = True
                break
        
        # Check Ollama availability
        ollama_available = providers.get("ollama", {}).get("available", False)
        ollama_base_url = providers.get("ollama", {}).get("base_url", "http://localhost:11434")
        
        should_default_to_ollama = not has_api_key_provider and ollama_available
        
        return {
            "success": True,
            "should_default_to_ollama": should_default_to_ollama,
            "ollama_available": ollama_available,
            "ollama_base_url": ollama_base_url,
            "has_api_key_providers": has_api_key_provider,
            "recommendation": "ollama" if should_default_to_ollama else (connections.get("recommended_provider") or "none")
        }
