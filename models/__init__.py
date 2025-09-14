"""
Model Configurations for mindX

This module contains model configuration files for various LLM providers.
It includes configurations for Mistral AI, OpenAI, Anthropic, and other providers.

Key Files:
- mistral.yaml: Mistral AI model configurations
- gemini.yaml: Google Gemini model configurations (legacy)
- Model selection and optimization settings
"""

# Model configuration files are loaded dynamically
# This module provides access to model configurations

__all__ = [
    "load_mistral_config",
    "load_gemini_config", 
    "get_model_config",
]
