"""
Ollama API Integration Package

This package contains all Ollama-related API integrations and tools for mindX:
- ollama_url.py: Custom HTTP-based Ollama API client with rate limiting and metrics
- ollama_official.py: Official Ollama Python library adapter (optional)
- ollama_admin_routes.py: Admin API routes for Ollama management and diagnostics
- ollama_chat_display_tool.py: Tool for displaying and managing Ollama chat conversations
- ollama_model_capability_tool.py: Tool for intelligent model selection based on capabilities
"""

from .ollama_url import (
    OllamaAPI,
    OllamaRateLimits,
    OllamaAPIMetrics,
    create_ollama_api
)

# Optional: Official Ollama library adapter
try:
    from .ollama_official import (
        OfficialOllamaAdapter,
        create_ollama_client,
        OLLAMA_OFFICIAL_AVAILABLE
    )
except ImportError:
    OLLAMA_OFFICIAL_AVAILABLE = False

# Ollama tools
from .ollama_chat_display_tool import OllamaChatDisplayTool
from .ollama_model_capability_tool import OllamaModelCapabilityTool, ModelCapability

__all__ = [
    'OllamaAPI',
    'OllamaRateLimits',
    'OllamaAPIMetrics',
    'create_ollama_api',
    'OllamaChatDisplayTool',
    'OllamaModelCapabilityTool',
    'ModelCapability',
    'OLLAMA_OFFICIAL_AVAILABLE',
]

# Conditionally export official adapter if available
if OLLAMA_OFFICIAL_AVAILABLE:
    __all__.extend([
        'OfficialOllamaAdapter',
        'create_ollama_client',
    ])
