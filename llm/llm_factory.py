# mindx/llm/llm_factory.py
# Resilience: Ollama is the failsafe/fallback (see llm/RESILIENCE.md). default_provider_preference_order
# should list cloud providers first and Ollama last so create_llm_handler() without args uses best available;
# Ollama remains explicitly selectable via provider_name="ollama".
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
# ADDED: Import the new RateLimiter classes
from .rate_limiter import RateLimiter, DualLayerRateLimiter

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
try:
    from .vllm_handler import VLLMHandler
except ImportError as e:
    VLLMHandler = None
    logger.warning(f"Could not import VLLMHandler: {e}. vLLM provider will be unavailable.")
try:
    from .zerog_handler import ZeroGHandler
except ImportError as e:
    ZeroGHandler = None
    logger.warning(f"Could not import ZeroGHandler: {e}. 0G Compute provider will be unavailable.")
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

_provider_registry_cache: Optional[Dict[str, Any]] = None


def _load_provider_registry() -> Dict[str, Any]:
    """Read data/config/provider_registry.json once. Used by free-tier router."""
    global _provider_registry_cache
    if _provider_registry_cache is not None:
        return _provider_registry_cache
    try:
        path = PROJECT_ROOT / "data" / "config" / "provider_registry.json"
        with path.open("r", encoding="utf-8") as f:
            _provider_registry_cache = json.load(f)
    except Exception as e:
        logger.warning(f"LLMFactory: provider_registry.json unreadable ({e}); free-tier routing disabled.")
        _provider_registry_cache = {}
    return _provider_registry_cache


def select_free_tier_provider(task_kind: str = "agentic_general") -> Tuple[Optional[str], Optional[str]]:
    """
    Choose a free-tier provider+model for a given task class.

    Strategy (in order):
      1. Live model catalogue (data/catalogue/ollama_library.json) — picks the
         best concrete model on disk or in Ollama Cloud whose `skills` match
         the task class. This is the "best model for the job" router.
      2. Operator-curated task_routing in data/config/ollama_cloud_models.json
         (manual override / fallback when catalogue is missing).
      3. free_tier_pool from llm_factory_config.json — provider-only fallback
         (model picked downstream from defaults).

    Returns (provider_name, model_name) or (None, None) if no candidate is available.
    """
    factory_cfg = _load_llm_factory_config_json()
    registry = _load_provider_registry()
    have_ollama_cloud = bool(os.getenv("OLLAMA_API_KEY"))

    # 1) Live catalogue.
    try:
        from agents.model_catalogue import ModelCatalogue
        cat = ModelCatalogue()
        candidates = cat.get_for_task(task_kind, prefer_local=True, cloud_ok=have_ollama_cloud)
        for m in candidates:
            name = m.get("name") or ""
            tags = m.get("tags") or []
            if m.get("is_cloud"):
                if not have_ollama_cloud:
                    continue
                tag = next((t for t in tags if t.endswith("cloud")), "cloud")
                return ("ollama_cloud", f"{name}:{tag}")
            # Pick the smallest concrete tag for local models.
            sized = sorted(
                (t for t in tags if any(c.isdigit() for c in t)),
                key=lambda x: x,
            )
            tag = sized[0] if sized else (tags[0] if tags else "latest")
            return ("ollama", f"{name}:{tag}")
    except Exception as e:
        logger.debug(f"LLMFactory: catalogue routing skipped: {e}")

    # 2) Static operator-curated task_routing.
    task_routing: Dict[str, List[str]] = {}
    try:
        ocm_path = PROJECT_ROOT / "data" / "config" / "ollama_cloud_models.json"
        if ocm_path.exists():
            with ocm_path.open("r", encoding="utf-8") as f:
                task_routing = (json.load(f) or {}).get("task_routing", {}) or {}
    except Exception as e:
        logger.debug(f"LLMFactory: task_routing read failed: {e}")

    if task_kind in task_routing:
        for candidate in task_routing[task_kind]:
            if candidate == "vllm":
                if os.getenv("VLLM_BASE_URL"):
                    return ("vllm", None)
                continue
            if candidate.endswith(":cloud"):
                if have_ollama_cloud:
                    return ("ollama_cloud", candidate)
                continue
            return ("ollama", candidate)

    # 3) Provider-only pool fallback.
    pool: List[str] = factory_cfg.get("free_tier_pool", []) or []
    for prov in pool:
        info = registry.get(prov, {})
        env_var = info.get("api_key_env_var")
        if env_var and not os.getenv(env_var):
            continue
        if not info.get("requires_api_key", True) or (env_var and os.getenv(env_var)):
            return (prov, None)
    return (None, None)


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
    rate_limit_profile: str = "default_rpm",
    execution_timeout_minutes: Optional[int] = None
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
    _keyed_providers = ["gemini", "openai", "anthropic", "groq", "mistral", "together", "deepseek",
                        "cohere", "perplexity", "fireworks", "replicate", "stability", "zerog"]
    if not eff_api_key and eff_provider_name in _keyed_providers:
        eff_api_key = factory_config.get(f"{eff_provider_name}_settings_for_factory", {}).get("api_key_override")
    if not eff_api_key and eff_provider_name in _keyed_providers:
        eff_api_key = global_config.get(f"llm.{eff_provider_name}.api_key")
    if not eff_api_key and eff_provider_name in _keyed_providers:
        _env_map = {
            "gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY", "groq": "GROQ_API_KEY",
            "mistral": "MISTRAL_API_KEY", "together": "TOGETHER_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY", "cohere": "COHERE_API_KEY",
            "perplexity": "PERPLEXITY_API_KEY", "fireworks": "FIREWORKS_API_KEY",
            "replicate": "REPLICATE_API_TOKEN", "stability": "STABILITY_API_KEY",
            "zerog": "ZEROG_API_KEY",
        }
        env_var_name = _env_map.get(eff_provider_name, "")
        if env_var_name: eff_api_key = os.getenv(env_var_name)
    # vLLM optional API key
    if not eff_api_key and eff_provider_name == "vllm":
        eff_api_key = os.getenv("VLLM_API_KEY")

    eff_base_url = base_url
    if not eff_base_url and eff_provider_name in ("ollama", "vllm", "zerog"):
        eff_base_url = factory_config.get(f"{eff_provider_name}_settings_for_factory", {}).get("base_url_override")
    if not eff_base_url and eff_provider_name == "ollama":
        eff_base_url = global_config.get(f"llm.ollama.base_url")
    if not eff_base_url and eff_provider_name == "vllm":
        eff_base_url = global_config.get(f"llm.vllm.base_url") or os.getenv("VLLM_BASE_URL")
    if not eff_base_url and eff_provider_name == "zerog":
        eff_base_url = global_config.get(f"llm.zerog.base_url") or os.getenv("ZEROG_BASE_URL")

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
        profile_config = rate_limit_profiles.get(rate_limit_profile, {})
        
        # Handle both old format (int) and new format (dict)
        if isinstance(profile_config, dict):
            requests_per_minute = profile_config.get("rpm", 60)
            requests_per_hour = profile_config.get("rph", 100)
        else:
            # Legacy format: just RPM as integer
            requests_per_minute = profile_config if isinstance(profile_config, int) else 60
            requests_per_hour = rate_limit_profiles.get("default_rph", 100)
        
        provider_config = global_config.get(f"llm.{eff_provider_name}", {})
        max_retries = provider_config.get("rate_limit_max_retries", 5)
        initial_backoff = provider_config.get("rate_limit_initial_backoff_s", 1.0)
        
        # Free-tier providers get the safety margin (cap at published-1) and
        # TPM enforcement so we never crowd a published cap. Pulled from
        # data/config/provider_registry.json so operators can tune per deploy.
        registry_entry = _load_provider_registry().get(eff_provider_name, {}) or {}
        ft_safety_margin = int(registry_entry.get("safety_margin_rpm", 0)) if registry_entry.get("free_tier") else 0
        ft_tpm_limit = registry_entry.get("default_rate_limit_tpm") if registry_entry.get("free_tier") else None
        if registry_entry.get("free_tier"):
            # Honor the registry's published RPM (already at free-tier value).
            requests_per_minute = registry_entry.get("default_rate_limit_rpm", requests_per_minute)

        # Use dual-layer rate limiter (minute + hourly)
        rate_limiter = DualLayerRateLimiter(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            max_retries=max_retries,
            initial_backoff_s=initial_backoff,
            safety_margin=ft_safety_margin,
            tpm_limit=ft_tpm_limit,
        )
        
        # Get execution timeout from config
        timeout_config = factory_config.get("execution_timeouts", {})
        if execution_timeout_minutes is None:
            execution_timeout_minutes = timeout_config.get("default_minutes", 15)
        
        # Validate timeout range
        min_timeout = timeout_config.get("min_minutes", 1)
        max_timeout = timeout_config.get("max_minutes", 120)
        execution_timeout_minutes = max(min_timeout, min(max_timeout, execution_timeout_minutes))

        # ADDED: Pass the rate_limiter and timeout to each handler's constructor
        if eff_provider_name == "ollama":
            if OllamaHandler: handler_instance = OllamaHandler(
                model_name_for_api=model_arg_for_handler,
                base_url=eff_base_url,
                rate_limiter=rate_limiter,
                execution_timeout_minutes=execution_timeout_minutes
            )
            else: logger.error("LLMFactory (mindX): OllamaHandler not imported."); handler_instance = MockLLMHandler(model_name=model_arg_for_handler)
        elif eff_provider_name == "gemini":
            if GeminiHandler:
                handler_instance = GeminiHandler(
                    model_name_for_api=model_arg_for_handler, 
                    api_key=eff_api_key, 
                    rate_limiter=rate_limiter, 
                    config=global_config,
                    execution_timeout_minutes=execution_timeout_minutes
                )
            else:
                logger.error("LLMFactory (mindX): GeminiHandler not imported.")
                handler_instance = MockLLMHandler(model_name=model_arg_for_handler)
        elif eff_provider_name == "groq":
            if GroqHandler: handler_instance = GroqHandler(
                model_name_for_api=model_arg_for_handler, 
                api_key=eff_api_key, 
                rate_limiter=rate_limiter, 
                config=global_config,
                execution_timeout_minutes=execution_timeout_minutes
            )
            else: logger.error("LLMFactory (mindX): GroqHandler not imported."); handler_instance = MockLLMHandler(model_name=model_arg_for_handler)
        elif eff_provider_name == "mistral":
            if MistralHandler:
                handler_instance = MistralHandler(
                    model_name_for_api=model_arg_for_handler,
                    api_key=eff_api_key,
                    rate_limiter=rate_limiter,
                    config=global_config,
                    execution_timeout_minutes=execution_timeout_minutes
                )
                if not eff_api_key:
                    logger.warning("LLMFactory (mindX): Mistral API key not provided. Handler will operate in degraded mode.")
            else:
                logger.error("LLMFactory (mindX): MistralHandler not imported.");
                handler_instance = MockLLMHandler(model_name=model_arg_for_handler)
        elif eff_provider_name == "vllm":
            if VLLMHandler:
                handler_instance = VLLMHandler(
                    model_name_for_api=model_arg_for_handler,
                    api_key=eff_api_key,
                    base_url=eff_base_url,
                    rate_limiter=rate_limiter,
                    execution_timeout_minutes=execution_timeout_minutes
                )
            else:
                logger.error("LLMFactory (mindX): VLLMHandler not imported.")
                handler_instance = MockLLMHandler(model_name=model_arg_for_handler)
        elif eff_provider_name == "zerog":
            if ZeroGHandler:
                handler_instance = ZeroGHandler(
                    model_name_for_api=model_arg_for_handler,
                    api_key=eff_api_key,
                    base_url=eff_base_url,
                    rate_limiter=rate_limiter,
                    execution_timeout_minutes=execution_timeout_minutes
                )
                if not eff_api_key:
                    logger.warning("LLMFactory (mindX): 0G Compute API key not provided. Handler will operate in degraded mode.")
            else:
                logger.error("LLMFactory (mindX): ZeroGHandler not imported.")
                handler_instance = MockLLMHandler(model_name=model_arg_for_handler)
        else: # pragma: no cover
            logger.warning(f"LLMFactory (mindX): Unknown provider '{eff_provider_name}'. Using MockLLMHandler for model '{model_arg_for_handler}'.")
            handler_instance = MockLLMHandler(model_name=model_arg_for_handler)

        _llm_handler_cache[cache_key] = handler_instance
        logger.info(f"LLMFactory (mindX): Created LLMHandler for {eff_provider_name} with model '{model_arg_for_handler}'")
        return handler_instance
