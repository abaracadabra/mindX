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
        # UPDATED LOGIC: Initialize providers that are enabled, regardless of models key
        for provider_name, provider_config in llm_config.items():
            if isinstance(provider_config, dict) and provider_config.get("enabled", False):
                logger.info(f"{self.log_prefix} Found enabled provider '{provider_name}'. Initializing handler.")
                task = self._initialize_provider(provider_name, provider_config)
                init_tasks.append(task)
            elif isinstance(provider_config, dict) and "models" in provider_config:
                logger.info(f"{self.log_prefix} Found model definitions for provider '{provider_name}'. Initializing handler.")
                task = self._initialize_provider(provider_name, provider_config)
                init_tasks.append(task)
        
        if not init_tasks:
            logger.warning(f"{self.log_prefix} No enabled providers found in config.")

        await asyncio.gather(*init_tasks)
        
        self._initialized = True
        logger.info(f"{self.log_prefix} Initialization complete. Available providers: {self.list_available_providers()}")

    def _models_to_capabilities(self, provider_name: str, models_data: Any) -> None:
        """Register capabilities from models_data (dict or list, e.g. from ollama.yaml)."""
        if isinstance(models_data, list):
            # List format (e.g. models/ollama.yaml): [{ name, display_name, context_size, task_scores?, ... }]
            default_task_scores = {
                "reasoning": 0.65, "code_generation": 0.65, "simple_chat": 0.75,
                "data_analysis": 0.60, "writing": 0.70, "speed_sensitive": 0.80,
            }
            for m in models_data:
                model_id = m.get("name") or m.get("id")
                if not model_id:
                    continue
                # Normalize to dict expected by ModelCapability (task_scores, max_context_length, etc.)
                model_data = {
                    "task_scores": m.get("task_scores", default_task_scores),
                    "max_context_length": m.get("context_size", m.get("max_context_length", 8192)),
                    "supports_streaming": m.get("supports_streaming", True),
                    "supports_function_calling": m.get("supports_function_calling", False),
                    "cost_per_kilo_input_tokens": 0.0,
                    "cost_per_kilo_output_tokens": 0.0,
                }
                cap_id = f"{provider_name}/{model_id}" if "/" not in model_id else model_id
                self.capabilities[cap_id] = ModelCapability(cap_id, provider_name, model_data)
        elif isinstance(models_data, dict):
            default_task_scores = {
                "reasoning": 0.65, "code_generation": 0.65, "simple_chat": 0.75,
                "data_analysis": 0.60, "writing": 0.70, "speed_sensitive": 0.80,
            }
            for model_id, raw in models_data.items():
                if isinstance(raw, dict):
                    self.capabilities[model_id] = ModelCapability(model_id, provider_name, raw)
                else:
                    # Config passed a non-dict (e.g. string); normalize to minimal capability
                    self.capabilities[model_id] = ModelCapability(
                        model_id, provider_name,
                        {"task_scores": default_task_scores, "max_context_length": 8192}
                    )

    async def _initialize_provider(self, provider_name: str, provider_config: Dict):
        """Creates a handler and registers its models and capabilities."""
        try:
            handler = await create_llm_handler(provider_name=provider_name)
            if handler:
                self.handlers[provider_name] = handler
                
                # Load models from config if available (dict or list)
                models_data = provider_config.get("models", {})
                if models_data:
                    self._models_to_capabilities(provider_name, models_data)
                else:
                    # For providers that load models from YAML files (like Mistral)
                    # The handler should have loaded its own model catalog
                    if hasattr(handler, 'model_catalog') and handler.model_catalog:
                        for model_id, model_data in handler.model_catalog.items():
                            self.capabilities[model_id] = ModelCapability(model_id, provider_name, model_data)
                        logger.info(f"{self.log_prefix} Loaded {len(handler.model_catalog)} models from {provider_name} handler's catalog")
                    else:
                        logger.warning(f"{self.log_prefix} No models found for provider '{provider_name}'")
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

    def get_handler_and_model_for_purpose(self, task_type: TaskType, context: Optional[Dict] = None, num_candidates: int = 10) -> List[tuple]:
        """
        Returns a list of (handler, model_name) for the given task type, in selection order.
        Use for fallback chains: try first, on failure try next; Ollama is last (failsafe).
        model_name is the API model tag (e.g. 'llama3:8b' or 'mistral-nemo:latest').
        """
        capability_list = list(self.capabilities.values())
        if not capability_list:
            return []
        ranked_models = self.model_selector.select_model(
            capability_list, task_type, context=context, num_to_return=num_candidates
        )
        result: List[tuple] = []
        seen_provider_model: set = set()
        for model_id in ranked_models:
            cap = self.capabilities.get(model_id)
            if not cap:
                continue
            handler = self.get_handler(cap.provider)
            if not handler:
                continue
            model_name = model_id.split("/", 1)[-1] if "/" in model_id else model_id
            key = (cap.provider, model_name)
            if key not in seen_provider_model:
                seen_provider_model.add(key)
                result.append((handler, model_name))
        return result

    async def generate_with_fallback(
        self,
        prompt: str,
        task_type: TaskType,
        max_tokens: Optional[int] = 2048,
        temperature: Optional[float] = 0.7,
        json_mode: bool = False,
        context: Optional[Dict] = None,
        try_bootstrap_on_no_connection: bool = False,
        **kwargs: Any,
    ) -> Optional[str]:
        """
        Resilient generate: try handlers in graded order (best model for purpose first),
        then fall back through ranked list; Ollama is last (failsafe). Returns first successful
        non-error response, or None if all failed.
        When try_bootstrap_on_no_connection is True and all fail on Linux, runs
        llm/ollama_bootstrap (aion.sh) to install/configure Ollama, reloads registry, and retries once.
        """
        candidates = self.get_handler_and_model_for_purpose(task_type, context=context)
        if not candidates:
            if try_bootstrap_on_no_connection:
                ok = await self._bootstrap_ollama_if_linux()
                if ok:
                    return await self.generate_with_fallback(
                        prompt, task_type,
                        max_tokens=max_tokens, temperature=temperature,
                        json_mode=json_mode, context=context,
                        try_bootstrap_on_no_connection=False,
                        **kwargs,
                    )
            logger.warning(f"{self.log_prefix} No handler/model candidates for task_type={task_type.name}.")
            return None
        last_error: Optional[str] = None
        for handler, model_name in candidates:
            try:
                response = await handler.generate_text(
                    prompt=prompt,
                    model=model_name,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    json_mode=json_mode,
                    **kwargs,
                )
                if response is not None and not (isinstance(response, str) and response.strip().startswith("Error:")):
                    logger.info(f"{self.log_prefix} generate_with_fallback succeeded with {handler.provider_name}/{model_name}.")
                    return response
                if isinstance(response, str) and response.strip().startswith("Error:"):
                    last_error = response
            except Exception as e:
                last_error = str(e)
                logger.warning(f"{self.log_prefix} generate_with_fallback try {handler.provider_name}/{model_name} failed: {e}")
        if try_bootstrap_on_no_connection:
            ok = await self._bootstrap_ollama_if_linux()
            if ok:
                return await self.generate_with_fallback(
                    prompt, task_type,
                    max_tokens=max_tokens, temperature=temperature,
                    json_mode=json_mode, context=context,
                    try_bootstrap_on_no_connection=False,
                    **kwargs,
                )
        logger.warning(f"{self.log_prefix} generate_with_fallback all candidates failed. Last error: {last_error}")
        return None

    async def _bootstrap_ollama_if_linux(self) -> bool:
        """When no inference connection, try llm/ollama_bootstrap (aion.sh) on Linux; reload registry. Returns True if Ollama became available."""
        import sys
        if not sys.platform.startswith("linux"):
            return False
        try:
            from llm.ollama_bootstrap import ensure_ollama_available
            base_url = self.config.get("llm.ollama.base_url")
            fallback_url = self.config.get("llm.ollama.fallback_url")
            available, msg = await ensure_ollama_available(
                base_url=base_url,
                fallback_url=fallback_url,
                try_bootstrap_linux=True,
            )
            if available:
                logger.info(f"{self.log_prefix} Ollama bootstrap succeeded: {msg}. Reloading registry.")
                await self.force_reload()
                return True
        except Exception as e:
            logger.warning(f"{self.log_prefix} Ollama bootstrap failed: {e}")
        return False

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
