# mindx/llm/model_registry.py
"""
ModelRegistry for mindX Augmentic Intelligence

A centralized, singleton service for initializing, caching, and providing access to
all configured LLM handlers. It discovers providers dynamically by looking for
defined model capabilities in the master configuration.
"""
import asyncio
from typing import Dict, List, Any, Optional

from utils.config import Config
from utils.logging_config import get_logger
from .llm_interface import LLMHandlerInterface
from .llm_factory import create_llm_handler
from .model_selector import ModelSelector, ModelCapability, TaskType

logger = get_logger(__name__)

class ModelRegistry:
    """Manages the lifecycle and access to all LLM handlers."""
    _instance = None
    _lock = asyncio.Lock()

    def __init__(self, config: Optional[Config] = None, test_mode: bool = False):
        if hasattr(self, '_initialized') and self._initialized and not test_mode:
            return
        
        self.config = config or Config()
        self.log_prefix = "ModelRegistry:"
        self.handlers: Dict[str, LLMHandlerInterface] = {}
        self.capabilities: Dict[str, ModelCapability] = {}
        self.model_selector = ModelSelector(self.config)
        self._initialized = False
        logger.info(f"{self.log_prefix} Instance created. Awaiting async initialization.")

    async def _async_init(self):
        """Asynchronously loads and initializes all providers that have models defined in the config."""
        if self._initialized:
            return
        
        logger.info(f"{self.log_prefix} Starting asynchronous initialization...")
        llm_config = self.config.get("llm", {})
        if not llm_config:
            logger.error(f"{self.log_prefix} 'llm' section not found in configuration. No providers will be loaded.")
            return

        init_tasks = []
        # UPDATED LOGIC: Dynamically find providers by looking for a "models" key.
        for provider_name, provider_config in llm_config.items():
            if isinstance(provider_config, dict) and "models" in provider_config:
                logger.info(f"{self.log_prefix} Found model definitions for provider '{provider_name}'. Initializing handler.")
                task = self._initialize_provider(provider_name, provider_config)
                init_tasks.append(task)
        
        if not init_tasks:
            logger.warning(f"{self.log_prefix} No providers with model definitions found in config.")

        await asyncio.gather(*init_tasks)
        
        self._initialized = True
        logger.info(f"{self.log_prefix} Initialization complete. Available providers: {self.list_available_providers()}")

    async def _initialize_provider(self, provider_name: str, provider_config: Dict):
        """Creates a handler and registers its models and capabilities."""
        try:
            handler = await create_llm_handler(provider_name=provider_name)
            if handler:
                self.handlers[provider_name] = handler
                models_data = provider_config.get("models", {})
                for model_id, model_data in models_data.items():
                    self.capabilities[model_id] = ModelCapability(model_id, provider_name, model_data)
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to initialize provider '{provider_name}': {e}", exc_info=True)

    def list_available_providers(self) -> List[str]:
        return list(self.handlers.keys())

    def get_handler(self, provider_name: str) -> Optional[LLMHandlerInterface]:
        return self.handlers.get(provider_name.lower())
        
    def get_handler_for_purpose(self, task_type: TaskType, context: Optional[Dict] = None) -> Optional[LLMHandlerInterface]:
        """
        Selects the best model for a given purpose and returns an initialized handler for it.
        """
        capability_list = list(self.capabilities.values())
        if not capability_list:
             logger.warning(f"{self.log_prefix} No model capabilities loaded. Cannot select handler for purpose '{task_type.name}'.")
             return None

        ranked_models = self.model_selector.select_model(capability_list, task_type)
        if not ranked_models:
             logger.warning(f"{self.log_prefix} ModelSelector returned no suitable models for purpose '{task_type.name}'.")
             return None

        best_model_id = ranked_models[0]
        provider = self.capabilities[best_model_id].provider
        logger.info(f"{self.log_prefix} Selected provider '{provider}' (model: {best_model_id}) for purpose '{task_type}'.")
        return self.get_handler(provider)

    async def force_reload(self):
        """Forces a complete re-initialization of the model registry."""
        logger.info(f"{self.log_prefix} Forcing a full reload of all providers and capabilities...")
        self._initialized = False
        self.handlers.clear()
        self.capabilities.clear()
        await self._async_init()

# Factory function to get the singleton instance
async def get_model_registry_async(config: Optional[Config] = None, test_mode: bool = False) -> ModelRegistry:
    async with ModelRegistry._lock:
        if ModelRegistry._instance is None or test_mode:
            ModelRegistry._instance = ModelRegistry(config=config, test_mode=test_mode)
            await ModelRegistry._instance._async_init()
    return ModelRegistry._instance
