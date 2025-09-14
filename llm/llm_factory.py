# mindx/llm/llm_factory.py
from typing import Optional, Any, Dict, List, Tuple
import json
import asyncio
import importlib
import os
from pathlib import Path
import logging

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from .llm_interface import LLMHandlerInterface
# ADDED: Import the new RateLimiter class
from .rate_limiter import RateLimiter

logger = get_logger(__name__)

try:
    from .ollama_handler import OllamaHandler
except ImportError as e: # pragma: no cover
    OllamaHandler = None # type: ignore
    logger.warning(f"Could not import OllamaHandler: {e}. Ollama provider will be unavailable.")
try:
    from .gemini_handler import GeminiHandler
except ImportError as e:
    GeminiHandler = None
    logger.warning(f"Could not import GeminiHandler: {e}. Gemini provider will be unavailable.")
try:
    from .groq_handler import GroqHandler
except ImportError as e: # pragma: no cover
    GroqHandler = None # type: ignore
    logger.warning(f"Could not import GroqHandler: {e}. Groq provider will be unavailable.")
try:
    from .mistral_handler import MistralHandler
except ImportError as e:
    MistralHandler = None
    logger.warning(f"Could not import MistralHandler: {e}. Mistral provider will be unavailable.")
from .mock_llm_handler import MockLLMHandler


DEFAULT_OLLAMA_CLOUD_RUN_MODELS_PY = {
    "excellent_fit": [
        {"id": "phi3_py", "ollama_name": "phi3:mini", "type": "general/reasoning", "est_memory_needed_gb": 4, "notes": "Default Python list: Microsoft Phi-3 Mini."},
        {"id": "gemma_2b_py", "ollama_name": "gemma:2b", "type": "general", "est_memory_needed_gb": 3, "notes": "Default Python list: Google's 2B model."},
        {"id": "codegemma_2b_py", "ollama_name": "codegemma:2b", "type": "coding", "est_memory_needed_gb": 3, "notes": "Default Python list: Google's 2B code model."},
    ],
    "good_fit": [
        {"id": "llama3_8b_py", "ollama_name": "llama3:8b", "type": "general/chat", "est_memory_needed_gb": 8, "notes": "Default Python list: Meta's 8B model."},
        {"id": "mistral_7b_py", "ollama_name": "mistral:7b", "type": "general/chat", "est_memory_needed_gb": 8, "notes": "Default Python list: Mistral 7B model."},
        {"id": "codegemma_7b_py", "ollama_name": "codegemma:7b-it", "type": "coding", "est_memory_needed_gb": 8, "notes": "Default Python list: Google's 7B code model."},
    ],
    "default_coding_preference_order": ["codegemma_7b_py", "codegemma_2b_py", "phi3_py"],
    "default_general_preference_order": ["llama3_8b_py", "mistral_7b_py", "phi3_py", "gemma_2b_py"]
}

_llm_handler_cache: Dict[Tuple[str, str, Optional[str], Optional[str]], LLMHandlerInterface] = {}
_llm_handler_cache_lock = asyncio.Lock()
_factory_config_data: Optional[Dict[str, Any]] = None
_factory_config_loaded_flag = False

def _load_llm_factory_config_json() -> Dict[str, Any]: # pragma: no cover
    global _factory_config_data, _factory_config_loaded_flag
    if _factory_config_loaded_flag:
        return _factory_config_data if _factory_config_data is not None else {}

    app_config = Config()
    default_factory_config_path = PROJECT_ROOT / "data" / "config" / "llm_factory_config.json"
    factory_config_path_str = app_config.get("llm.factory_config_path", str(default_factory_config_path))
    factory_config_path = Path(factory_config_path_str)

    logger.info(f"LLMFactory (mindX): Attempting to load specific configuration from {factory_config_path}")
    if factory_config_path.exists() and factory_config_path.is_file():
        try:
            with factory_config_path.open("r", encoding="utf-8") as f:
                _factory_config_data = json.load(f)
            logger.info(f"LLMFactory (mindX): Loaded specific configuration from {factory_config_path}")
        except Exception as e:
            logger.error(f"LLMFactory (mindX): Error loading config file {factory_config_path}: {e}. Using empty factory config.")
            _factory_config_data = {}
    else:
        logger.info(f"LLMFactory (mindX): Specific config file {factory_config_path} not found. Using global Config and internal defaults only.")
        _factory_config_data = {}

    _factory_config_loaded_flag = True
    return _factory_config_data if _factory_config_data is not None else {}

async def create_llm_handler(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    rate_limit_profile: str = "default_rpm"
) -> LLMHandlerInterface:
    global_config = Config() # Get a Config instance to pass to handlers if needed
    factory_config = _load_llm_factory_config_json()

    eff_provider_name = provider_name
    if not eff_provider_name:
        pref_order = factory_config.get("default_provider_preference_order")
        eff_provider_name = pref_order[0] if pref_order and isinstance(pref_order, list) and len(pref_order) > 0 else None
    if not eff_provider_name:
        eff_provider_name = global_config.get("llm.default_provider", "ollama")
    eff_provider_name = eff_provider_name.lower()

    eff_model_name_for_api = model_name
    if not eff_model_name_for_api:
        eff_model_name_for_api = factory_config.get(f"{eff_provider_name}_settings_for_factory", {}).get("default_model_override")
    if not eff_model_name_for_api:
        eff_model_name_for_api = global_config.get(f"llm.{eff_provider_name}.default_model")

    if not eff_model_name_for_api and eff_provider_name == "ollama": # pragma: no cover
        logger.info(f"LLMFactory (mindX): No specific Ollama model set. Selecting Cloud Run friendly default.")
        cr_models_config_source = factory_config.get("ollama_settings_for_factory", {}).get("cloud_run_friendly_models", DEFAULT_OLLAMA_CLOUD_RUN_MODELS_PY)
        coding_pref_order = cr_models_config_source.get("default_coding_preference_order", [])
        all_cr_models_list = cr_models_config_source.get("good_fit", []) + cr_models_config_source.get("excellent_fit", [])
        for cr_model_id_pref in coding_pref_order:
            model_detail = next((m_dict for m_dict in all_cr_models_list if m_dict.get("id") == cr_model_id_pref), None)
            if model_detail and model_detail.get("ollama_name"):
                eff_model_name_for_api = model_detail["ollama_name"]; break
        if not eff_model_name_for_api:
            general_pref_order = cr_models_config_source.get("default_general_preference_order", [])
            for cr_model_id_pref in general_pref_order:
                model_detail = next((m_dict for m_dict in all_cr_models_list if m_dict.get("id") == cr_model_id_pref), None)
                if model_detail and model_detail.get("ollama_name"):
                    eff_model_name_for_api = model_detail["ollama_name"]; break
        if eff_model_name_for_api:
            logger.info(f"LLMFactory (mindX): Defaulting Ollama to Cloud Run friendly model: '{eff_model_name_for_api}'")
        else:
            eff_model_name_for_api = global_config.get("llm.ollama.default_model", "phi3:mini")
            logger.warning(f"LLMFactory (mindX): No Cloud Run preferred model for Ollama, using global/hardcoded fallback: '{eff_model_name_for_api}'.")
    elif not eff_model_name_for_api:
        eff_model_name_for_api = global_config.get(f"llm.{eff_provider_name}.default_model", f"default_model_for_{eff_provider_name}")

    eff_api_key = api_key
    if not eff_api_key and eff_provider_name in ["gemini", "openai", "anthropic", "groq", "mistral"]:
        eff_api_key = factory_config.get(f"{eff_provider_name}_settings_for_factory", {}).get("api_key_override")
    if not eff_api_key and eff_provider_name in ["gemini", "openai", "anthropic", "groq", "mistral"]:
        eff_api_key = global_config.get(f"llm.{eff_provider_name}.api_key")
    if not eff_api_key and eff_provider_name in ["gemini", "openai", "anthropic", "groq", "mistral"]:
        env_var_name = ""
        if eff_provider_name == "gemini": env_var_name = "GEMINI_API_KEY"
        elif eff_provider_name == "openai": env_var_name = "OPENAI_API_KEY"
        elif eff_provider_name == "anthropic": env_var_name = "ANTHROPIC_API_KEY"
        elif eff_provider_name == "groq": env_var_name = "GROQ_API_KEY"
        elif eff_provider_name == "mistral": env_var_name = "MISTRAL_API_KEY"
        if env_var_name: eff_api_key = os.getenv(env_var_name)

    eff_base_url = base_url
    if not eff_base_url and eff_provider_name == "ollama":
        eff_base_url = factory_config.get(f"{eff_provider_name}_settings_for_factory", {}).get("base_url_override")
    if not eff_base_url and eff_provider_name == "ollama":
        eff_base_url = global_config.get(f"llm.ollama.base_url")

    final_model_name_for_handler_constructor = factory_config.get("provider_specific_handler_config", {}).get(eff_provider_name, {}).get("default_model_for_api_call", eff_model_name_for_api)
    cache_key_model_name = final_model_name_for_handler_constructor or f"implicit_default_for_{eff_provider_name}"
    cache_key = (eff_provider_name, cache_key_model_name, eff_api_key or "no_key_for_handler", eff_base_url or "no_url_for_handler")

    async with _llm_handler_cache_lock:
        if cache_key in _llm_handler_cache: # pragma: no cover
            logger.debug(f"LLMFactory (mindX): Returning cached LLMHandler for key: {cache_key}")
            return _llm_handler_cache[cache_key]

        handler_instance: LLMHandlerInterface
        model_arg_for_handler = final_model_name_for_handler_constructor

        # ADDED: Create the rate limiter instance based on provider config
        rate_limit_profiles = factory_config.get("rate_limit_profiles", {})
        requests_per_minute = rate_limit_profiles.get(rate_limit_profile, 2)
        provider_config = global_config.get(f"llm.{eff_provider_name}", {})
        max_retries = provider_config.get("rate_limit_max_retries", 5)
        initial_backoff = provider_config.get("rate_limit_initial_backoff_s", 1.0)
        
        rate_limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            max_retries=max_retries,
            initial_backoff_s=initial_backoff
        )

        # ADDED: Pass the rate_limiter to each handler's constructor
        if eff_provider_name == "ollama":
            if OllamaHandler: handler_instance = OllamaHandler(model_name_for_api=model_arg_for_handler, base_url=eff_base_url, rate_limiter=rate_limiter, config=global_config)
            else: logger.error("LLMFactory (mindX): OllamaHandler not imported."); handler_instance = MockLLMHandler(model_name=model_arg_for_handler)
        elif eff_provider_name == "gemini":
            if GeminiHandler:
                handler_instance = GeminiHandler(model_name_for_api=model_arg_for_handler, api_key=eff_api_key, rate_limiter=rate_limiter, config=global_config)
            else:
                logger.error("LLMFactory (mindX): GeminiHandler not imported.")
                handler_instance = MockLLMHandler(model_name=model_arg_for_handler)
        elif eff_provider_name == "groq":
            if GroqHandler: handler_instance = GroqHandler(model_name_for_api=model_arg_for_handler, api_key=eff_api_key, rate_limiter=rate_limiter, config=global_config)
            else: logger.error("LLMFactory (mindX): GroqHandler not imported."); handler_instance = MockLLMHandler(model_name=model_arg_for_handler)
        elif eff_provider_name == "mistral":
            if MistralHandler: 
                handler_instance = MistralHandler(model_name_for_api=model_arg_for_handler, api_key=eff_api_key, rate_limiter=rate_limiter, config=global_config)
                if not eff_api_key:
                    logger.warning("LLMFactory (mindX): Mistral API key not provided. Handler will operate in degraded mode.")
            else: 
                logger.error("LLMFactory (mindX): MistralHandler not imported."); 
                handler_instance = MockLLMHandler(model_name=model_arg_for_handler)
        else: # pragma: no cover
            logger.warning(f"LLMFactory (mindX): Unknown provider '{eff_provider_name}'. Using MockLLMHandler for model '{model_arg_for_handler}'.")
            handler_instance = MockLLMHandler(model_name=model_arg_for_handler)

        _llm_handler_cache[cache_key] = handler_instance
        logger.info(f"LLMFactory (mindX): Created LLMHandler for {eff_provider_name} with model '{model_arg_for_handler}'")
        return handler_instance
