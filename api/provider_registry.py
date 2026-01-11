"""
Provider Registry System for mindX

This module manages dynamic registration, configuration, and lifecycle of LLM API providers.
Allows easy addition and removal of providers from UI and enables mindX to manage providers autonomously.
"""

import json
import os
import asyncio
from typing import Dict, List, Optional, Any, Type, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

from utils.logging_config import get_logger
from utils.config import Config, PROJECT_ROOT

logger = get_logger(__name__)


class ProviderStatus(Enum):
    """Provider status"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    TESTING = "testing"


@dataclass
class ProviderConfig:
    """Configuration for an API provider"""
    name: str
    display_name: str
    module_path: str  # e.g., "api.gemini_api"
    factory_function: str  # e.g., "create_gemini_api"
    api_key_env_var: Optional[str] = None
    base_url_env_var: Optional[str] = None
    requires_api_key: bool = True
    requires_base_url: bool = False
    default_rate_limit_rpm: int = 60
    default_rate_limit_tpm: int = 100000
    status: ProviderStatus = ProviderStatus.DISABLED
    enabled: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ProviderRegistry:
    """
    Central registry for managing LLM API providers.
    
    Supports dynamic registration, configuration, and lifecycle management.
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.registry_file = PROJECT_ROOT / "data" / "config" / "provider_registry.json"
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.providers: Dict[str, ProviderConfig] = {}
        self.provider_instances: Dict[str, Any] = {}  # Cached instances
        
        # Load registry
        self._load_registry()
        
        # Register default providers
        self._register_default_providers()
    
    def _load_registry(self):
        """Load provider registry from file"""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                    for name, provider_data in data.items():
                        provider_data['status'] = ProviderStatus(provider_data.get('status', 'disabled'))
                        self.providers[name] = ProviderConfig(**provider_data)
                logger.info(f"Loaded {len(self.providers)} providers from registry")
            except Exception as e:
                logger.error(f"Error loading provider registry: {e}")
    
    def _save_registry(self):
        """Save provider registry to file"""
        try:
            data = {}
            for name, provider in self.providers.items():
                provider_dict = asdict(provider)
                provider_dict['status'] = provider.status.value
                data[name] = provider_dict
            
            with open(self.registry_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.providers)} providers to registry")
        except Exception as e:
            logger.error(f"Error saving provider registry: {e}")
    
    def _register_default_providers(self):
        """Register default providers"""
        default_providers = [
            ProviderConfig(
                name="gemini",
                display_name="Google Gemini",
                module_path="api.gemini_api",
                factory_function="create_gemini_api",
                api_key_env_var="GEMINI_API_KEY",
                requires_api_key=True,
                default_rate_limit_rpm=60,
                default_rate_limit_tpm=1000000,
                status=ProviderStatus.DISABLED
            ),
            ProviderConfig(
                name="openai",
                display_name="OpenAI",
                module_path="api.openai_api",
                factory_function="create_openai_api",
                api_key_env_var="OPENAI_API_KEY",
                requires_api_key=True,
                default_rate_limit_rpm=3,  # Free tier default
                default_rate_limit_tpm=40000,
                status=ProviderStatus.DISABLED
            ),
            ProviderConfig(
                name="anthropic",
                display_name="Anthropic Claude",
                module_path="api.anthropic_api",
                factory_function="create_anthropic_api",
                api_key_env_var="ANTHROPIC_API_KEY",
                requires_api_key=True,
                default_rate_limit_rpm=50,
                default_rate_limit_tpm=40000,
                status=ProviderStatus.DISABLED
            ),
            ProviderConfig(
                name="mistral",
                display_name="Mistral AI",
                module_path="api.mistral_api",
                factory_function="MistralAPIClient",  # Uses class directly
                api_key_env_var="MISTRAL_API_KEY",
                requires_api_key=True,
                default_rate_limit_rpm=10,
                default_rate_limit_tpm=100000,
                status=ProviderStatus.DISABLED
            ),
            ProviderConfig(
                name="together",
                display_name="Together AI",
                module_path="api.together_api",
                factory_function="create_together_api",
                api_key_env_var="TOGETHER_API_KEY",
                requires_api_key=True,
                default_rate_limit_rpm=60,
                default_rate_limit_tpm=1000000,
                status=ProviderStatus.DISABLED
            ),
            ProviderConfig(
                name="ollama",
                display_name="Ollama (Local)",
                module_path="api.ollama_url",
                factory_function="create_ollama_api",
                base_url_env_var="MINDX_LLM__OLLAMA__BASE_URL",
                requires_api_key=False,
                requires_base_url=True,
                default_rate_limit_rpm=1000,
                default_rate_limit_tpm=10000000,
                status=ProviderStatus.DISABLED
            ),
        ]
        
        # Only add if not already registered
        for provider in default_providers:
            if provider.name not in self.providers:
                self.providers[provider.name] = provider
        
        self._save_registry()
    
    def register_provider(
        self,
        name: str,
        display_name: str,
        module_path: str,
        factory_function: str,
        api_key_env_var: Optional[str] = None,
        base_url_env_var: Optional[str] = None,
        requires_api_key: bool = True,
        requires_base_url: bool = False,
        default_rate_limit_rpm: int = 60,
        default_rate_limit_tpm: int = 100000,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Register a new provider dynamically.
        
        Returns True if successful, False otherwise.
        """
        try:
            # Validate module can be imported
            try:
                module = __import__(module_path, fromlist=[factory_function])
                if not hasattr(module, factory_function):
                    logger.error(f"Factory function {factory_function} not found in {module_path}")
                    return False
            except ImportError as e:
                logger.error(f"Cannot import module {module_path}: {e}")
                return False
            
            provider = ProviderConfig(
                name=name,
                display_name=display_name,
                module_path=module_path,
                factory_function=factory_function,
                api_key_env_var=api_key_env_var,
                base_url_env_var=base_url_env_var,
                requires_api_key=requires_api_key,
                requires_base_url=requires_base_url,
                default_rate_limit_rpm=default_rate_limit_rpm,
                default_rate_limit_tpm=default_rate_limit_tpm,
                status=ProviderStatus.DISABLED,
                metadata=metadata or {}
            )
            
            self.providers[name] = provider
            self._save_registry()
            logger.info(f"Registered new provider: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering provider {name}: {e}")
            return False
    
    def unregister_provider(self, name: str) -> bool:
        """Remove a provider from registry"""
        if name not in self.providers:
            return False
        
        # Remove instance if exists
        if name in self.provider_instances:
            del self.provider_instances[name]
        
        del self.providers[name]
        self._save_registry()
        logger.info(f"Unregistered provider: {name}")
        return True
    
    def get_provider(self, name: str) -> Optional[ProviderConfig]:
        """Get provider configuration"""
        return self.providers.get(name)
    
    def list_providers(self) -> List[Dict[str, Any]]:
        """List all registered providers"""
        result = []
        for name, provider in self.providers.items():
            provider_dict = asdict(provider)
            provider_dict['status'] = provider.status.value
            result.append(provider_dict)
        return result
    
    async def create_provider_instance(self, name: str, **kwargs) -> Optional[Any]:
        """Create an instance of a provider"""
        provider = self.providers.get(name)
        if not provider:
            logger.error(f"Provider {name} not found")
            return None
        
        # Check if already instantiated
        if name in self.provider_instances:
            return self.provider_instances[name]
        
        try:
            # Import module
            module = __import__(provider.module_path, fromlist=[provider.factory_function])
            factory = getattr(module, provider.factory_function)
            
            # Get API key and base URL from environment or kwargs
            api_key = kwargs.get('api_key')
            if not api_key and provider.api_key_env_var:
                api_key = os.getenv(provider.api_key_env_var)
            
            base_url = kwargs.get('base_url')
            if not base_url and provider.base_url_env_var:
                base_url = os.getenv(provider.base_url_env_var)
            
            # Create instance
            if provider.requires_base_url:
                instance = factory(base_url=base_url, config=self.config)
            elif provider.requires_api_key:
                instance = factory(api_key=api_key, config=self.config)
            else:
                instance = factory(config=self.config)
            
            self.provider_instances[name] = instance
            logger.info(f"Created instance for provider: {name}")
            return instance
            
        except Exception as e:
            logger.error(f"Error creating provider instance {name}: {e}")
            return None
    
    def enable_provider(self, name: str) -> bool:
        """Enable a provider"""
        if name not in self.providers:
            return False
        
        self.providers[name].enabled = True
        self.providers[name].status = ProviderStatus.ENABLED
        self._save_registry()
        return True
    
    def disable_provider(self, name: str) -> bool:
        """Disable a provider"""
        if name not in self.providers:
            return False
        
        self.providers[name].enabled = False
        self.providers[name].status = ProviderStatus.DISABLED
        
        # Remove instance
        if name in self.provider_instances:
            del self.provider_instances[name]
        
        self._save_registry()
        return True
    
    def update_provider_rate_limits(self, name: str, rpm: Optional[int] = None, tpm: Optional[int] = None) -> bool:
        """Update rate limits for a provider"""
        if name not in self.providers:
            return False
        
        if rpm:
            self.providers[name].default_rate_limit_rpm = rpm
        if tpm:
            self.providers[name].default_rate_limit_tpm = tpm
        
        # Update instance if exists
        if name in self.provider_instances:
            instance = self.provider_instances[name]
            if hasattr(instance, 'update_rate_limits'):
                instance.update_rate_limits(rpm=rpm, tpm=tpm)
        
        self._save_registry()
        return True


# Global registry instance
_registry_instance: Optional[ProviderRegistry] = None
_registry_lock = asyncio.Lock()


async def get_provider_registry() -> ProviderRegistry:
    """Get or create global provider registry instance"""
    global _registry_instance
    async with _registry_lock:
        if _registry_instance is None:
            _registry_instance = ProviderRegistry()
        return _registry_instance


