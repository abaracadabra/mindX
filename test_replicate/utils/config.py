# mindx/utils/config.py (Corrected)
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

# --- THE FIX IS HERE ---
# The package is installed as 'python-dotenv', but imported as 'dotenv'.
from dotenv import load_dotenv

from .logging_config import get_logger
from .yaml_config_loader import load_yaml_file # IMPORT THE NEW LOADER

# --- Constants ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
logger = get_logger(__name__)

class Config:
    """
    Handles loading and accessing hierarchical configuration for the MindX system.
    It now supports loading from multiple JSON files, a models directory with YAML files,
    and environment variables.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance

    def __init__(self, test_mode=False):
        if hasattr(self, '_initialized') and self._initialized and not test_mode:
            return

        self.config_data: Dict[str, Any] = {}
        self._load_environment_variables()
        self._load_config_files()
        
        # ADDED: Load model capability configurations from the 'models' directory
        self._load_model_capability_configs()

        self._initialized = True
        logger.info("Configuration loaded successfully.")

    def _load_environment_variables(self):
        env_path = PROJECT_ROOT / '.env'
        if env_path.exists():
            # Use the corrected import here
            load_dotenv(dotenv_path=env_path, override=True)
            logger.info(f"Loaded environment variables from {env_path}")

    def _load_config_files(self):
        config_dir = PROJECT_ROOT / "data" / "config"
        if not config_dir.is_dir():
            logger.warning(f"Configuration directory not found at {config_dir}, skipping JSON config load.")
            return

        config_files = [f for f in config_dir.glob("*.json")]
        
        for config_file in sorted(config_files):
            try:
                with config_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._deep_merge(self.config_data, data)
                logger.info(f"Loaded and merged config from {config_file.name}")
            except Exception as e:
                logger.error(f"Failed to load config file {config_file}: {e}")

    def _load_model_capability_configs(self):
        """Loads all .yaml model capability files from the /models directory."""
        models_dir = PROJECT_ROOT / "models"
        if not models_dir.is_dir():
            logger.info("No 'models' directory found for YAML capabilities, skipping.")
            return

        for yaml_file in models_dir.glob("*.yaml"):
            provider_name = yaml_file.stem  # e.g., 'gemini.yaml' -> 'gemini'
            model_data = load_yaml_file(yaml_file)
            
            if model_data:
                # Structure the data to be merged into the main config
                # Expected structure: llm.<provider>.models
                provider_config = {
                    "llm": {
                        provider_name: {
                            "models": model_data
                        }
                    }
                }
                self._deep_merge(self.config_data, provider_config)

    def _deep_merge(self, source, destination):
        """Recursively merges dictionary `destination` into `source`."""
        for key, value in destination.items():
            if isinstance(value, dict) and key in source and isinstance(source[key], dict):
                self._deep_merge(source[key], value)
            else:
                source[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        # Environment variables have the highest priority.
        # e.g., key 'llm.gemini.api_key' -> env var 'MINDX_LLM_GEMINI_API_KEY'
        env_var_key = "MINDX_" + key.upper().replace('.', '_')
        env_value = os.getenv(env_var_key)
        if env_value is not None:
            return env_value

        # If not in env, check the loaded config data.
        keys = key.split('.')
        value = self.config_data
        try:
            for k in keys:
                value = value[k]
            
            # Handle placeholder substitution, e.g., "env:GEMINI_API_KEY"
            if isinstance(value, str) and value.lower().startswith("env:"):
                env_var = value[4:]
                return os.environ.get(env_var, default)
            
            return value
        except (KeyError, TypeError):
            return default

    @classmethod
    def reset_instance(cls):
        cls._instance = None
