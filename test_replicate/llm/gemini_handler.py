# mindx/llm/gemini_handler.py (c) 2025 PYTHAI MIT license
"""
Definitive, Dynamic Gemini Handler for the MindX Augmentic Intelligence Framework.

gemini_handler is a pure runtime component dynamically loading its configuration from the central `gemini.yaml`
file maintained by the `scripts/audit_gemini.py` tool.

The mindX architecture allows the framework's capabilities to be upgraded without
modifying this file's code, fulfilling a key principle of augmentic systems.
"""
import sys

if __name__ == "__main__":
    print("FATAL: This file is a library for the mindX framework and cannot be run directly.", file=sys.stderr)
    print("Please use the dedicated tool at `scripts/audit_gemini.py` for auditing and configuration.", file=sys.stderr)
    sys.exit(1)

import json
import os
import asyncio
from pathlib import Path
from typing import Optional, Any, Dict, List
import re

import google.generativeai as genai
from llm.llm_interface import LLMHandlerInterface
from llm.rate_limiter import RateLimiter
from utils.config import Config
from utils.logging_config import get_logger

framework_logger = get_logger(__name__)

class GeminiHandler(LLMHandlerInterface):
    """An intelligent Gemini text generation handler for the mindX framework."""

    def __init__(self, model_name_for_api: str, api_key: Optional[str], **kwargs: Any):
        super().__init__(
            provider_name="gemini", model_name_for_api=model_name_for_api, api_key=api_key, **kwargs
        )

        self.log_prefix = "GeminiHandler:"
        self.config = kwargs.get("config") or Config()
        
        self.model_catalog: Dict[str, Any] = {}
        self._load_config_from_yaml()

        self.api_key = self.api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            framework_logger.error(f"{self.log_prefix} API key not found (GEMINI_API_KEY).")
        else:
            genai.configure(api_key=self.api_key)

    def _load_config_from_yaml(self):
        """Loads the model catalog and settings from the central gemini.yaml file."""
        try:
            import yaml
            
            config_path = Path(__file__).parent.parent / "models" / "gemini.yaml"
            framework_logger.info(f"Dynamically loading Gemini configuration from: {config_path}")
            
            if not config_path.exists():
                framework_logger.error(f"gemini.yaml not found at {config_path}. Handler will have no models.")
                return

            with open(config_path, "r") as f:
                self.model_catalog = yaml.safe_load(f) or {}

        except ImportError:
            framework_logger.critical("The 'PyYAML' library is required to load model configs. Please run `pip install pyyaml`.")
        except Exception as e:
            framework_logger.error(f"Error parsing gemini.yaml: {e}", exc_info=True)

    async def generate_text(
        self, prompt: str, model: str, max_tokens: Optional[int] = 2048,
        temperature: Optional[float] = 0.7, json_mode: Optional[bool] = False, **kwargs: Any
    ) -> Optional[str]:
        """
        Generates text using a single specified Gemini model, with automatic retries on rate limit errors.
        """
        if not self.api_key:
            return json.dumps({"error": "ClientNotConfigured", "message": "Gemini API key not configured."})
        if not self.model_catalog:
            return json.dumps({"error": "ModelCatalogNotLoaded", "message": "Gemini model catalog is empty."})

        sanitized_model = f"gemini/{model}" if not model.startswith("gemini/") else model
        model_info = self.model_catalog.get(sanitized_model)
        if not model_info or not model_info.get("api_name"):
            msg = f"Model ID '{sanitized_model}' not found in gemini.yaml or is missing 'api_name'."
            framework_logger.warning(f"{self.log_prefix} {msg}")
            return json.dumps({"error": "ModelNotFoundInCatalog", "message": msg})

        config_dict = {"max_output_tokens": max_tokens, "temperature": temperature}
        if json_mode:
            config_dict["response_mime_type"] = "application/json"
        
        model_api_name = model_info['api_name']
        model_instance = genai.GenerativeModel(model_api_name)
        generation_config = genai.types.GenerationConfig(**config_dict)

        max_retries = self.config.get("llm.gemini.rate_limit_max_retries", 3)
        base_delay = self.config.get("llm.gemini.rate_limit_base_delay_seconds", 2.0)

        for attempt in range(max_retries):
            if self.rate_limiter and not await self.rate_limiter.wait():
                 return json.dumps({"error": "RateLimitRetriesExceeded", "message": "Internal rate limiter retries exceeded."})

            framework_logger.debug(f"{self.log_prefix} Attempting API call (Attempt {attempt + 1}/{max_retries}) with model: {model_api_name}")
            try:
                response = await asyncio.to_thread(
                    model_instance.generate_content,
                    contents=prompt,
                    generation_config=generation_config,
                    **kwargs
                )
                return response.text
            except Exception as e:
                error_message = str(e)
                is_rate_limit_error = "429" in error_message

                if is_rate_limit_error and attempt < max_retries - 1:
                    retry_delay_match = re.search(r'retry_delay {\s*seconds: (\d+)\s*}', error_message)
                    if retry_delay_match:
                        delay = int(retry_delay_match.group(1))
                        framework_logger.warning(f"{self.log_prefix} Rate limit hit. API suggests retrying in {delay}s. Waiting...")
                        await asyncio.sleep(delay)
                    else:
                        delay = base_delay * (2 ** attempt)
                        framework_logger.warning(f"{self.log_prefix} Rate limit hit. Retrying in {delay:.2f}s (exponential backoff).")
                        await asyncio.sleep(delay)
                else:
                    framework_logger.warning(f"{self.log_prefix} API call for '{model_api_name}' failed permanently: {error_message}.")
                    return json.dumps({"error": "ApiCallFailed", "message": error_message})
        
        return json.dumps({"error": "ApiCallFailedAfterRetries", "message": "API call failed after multiple retries."})
