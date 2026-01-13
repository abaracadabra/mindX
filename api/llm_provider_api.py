"""
LLM Provider API Management for mindX

This module provides API endpoints and utilities for managing LLM providers,
API keys, model selection, and performance monitoring.
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path
from pydantic import BaseModel

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from llm.llm_factory import create_llm_handler
from llm.model_registry import get_model_registry_async
from llm.model_selector import TaskType
from llm.ollama_handler import OllamaHandler
from agents.monitoring.performance_monitor import PerformanceMonitor
from api.provider_registry import get_provider_registry, ProviderRegistry

logger = get_logger(__name__)


class APIKeyConfig(BaseModel):
    """API key configuration model"""
    provider: str
    api_key: str
    base_url: Optional[str] = None
    enabled: bool = True


class OllamaModelInfo(BaseModel):
    """Ollama model information"""
    name: str
    size: Optional[int] = None
    digest: Optional[str] = None
    modified_at: Optional[str] = None


class LLMProviderManager:
    """Manages LLM provider configurations and API keys"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.env_file_path = PROJECT_ROOT / ".env"
        self.config_file_path = PROJECT_ROOT / "data" / "config" / "llm_providers.json"
        self.config_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry: Optional[ProviderRegistry] = None
    
    def _load_env_file(self) -> Dict[str, str]:
        """Load environment variables from .env file"""
        env_vars = {}
        if self.env_file_path.exists():
            try:
                with open(self.env_file_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip().strip('"').strip("'")
            except Exception as e:
                logger.error(f"Error loading .env file: {e}")
        return env_vars
    
    def _save_env_file(self, env_vars: Dict[str, str]):
        """Save environment variables to .env file"""
        try:
            # Read existing .env file
            existing_lines = []
            if self.env_file_path.exists():
                with open(self.env_file_path, 'r') as f:
                    existing_lines = f.readlines()
            
            # Update or add new variables
            updated_vars = set()
            new_lines = []
            
            for line in existing_lines:
                line_stripped = line.strip()
                if line_stripped and not line_stripped.startswith('#') and '=' in line_stripped:
                    key = line_stripped.split('=', 1)[0].strip()
                    if key in env_vars:
                        new_lines.append(f"{key}=\"{env_vars[key]}\"\n")
                        updated_vars.add(key)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            
            # Add new variables that weren't in the file
            for key, value in env_vars.items():
                if key not in updated_vars:
                    new_lines.append(f"{key}=\"{value}\"\n")
            
            # Write back to file
            with open(self.env_file_path, 'w') as f:
                f.writelines(new_lines)
            
            logger.info(f"Updated .env file with {len(env_vars)} variables")
        except Exception as e:
            logger.error(f"Error saving .env file: {e}")
            raise
    
    async def get_api_keys(self) -> Dict[str, Dict[str, Any]]:
        """Get all configured API keys (masked) from registry"""
        if not self.registry:
            self.registry = await get_provider_registry()
        
        env_vars = self._load_env_file()
        providers = {}
        
        # Get providers from registry
        for provider_config in self.registry.list_providers():
            name = provider_config['name']
            
            # Get API key or base URL
            api_key = None
            base_url = None
            
            if provider_config.get('api_key_env_var'):
                api_key = env_vars.get(provider_config['api_key_env_var'])
            
            if provider_config.get('base_url_env_var'):
                base_url = env_vars.get(provider_config['base_url_env_var'])
            
            providers[name] = {
                "api_key": api_key,
                "base_url": base_url,
                "enabled": provider_config.get('enabled', False),
                "status": provider_config.get('status', 'disabled'),
                "display_name": provider_config.get('display_name', name),
                "requires_api_key": provider_config.get('requires_api_key', True),
                "requires_base_url": provider_config.get('requires_base_url', False),
                "default_rate_limit_rpm": provider_config.get('default_rate_limit_rpm', 60),
                "default_rate_limit_tpm": provider_config.get('default_rate_limit_tpm', 100000),
            }
            
            # Mask API keys for display
            if providers[name]["api_key"]:
                masked_key = self._mask_api_key(providers[name]["api_key"])
                providers[name]["api_key_masked"] = masked_key
                providers[name]["api_key"] = None  # Don't return actual key
        
        return providers
    
    def _mask_api_key(self, api_key: str) -> str:
        """Mask API key for display (show first 4 and last 4 characters)"""
        if len(api_key) <= 8:
            return "****"
        return f"{api_key[:4]}...{api_key[-4:]}"
    
    async def set_api_key(self, provider: str, api_key: str, base_url: Optional[str] = None) -> Dict[str, Any]:
        """Set API key for a provider"""
        provider_lower = provider.lower()
        
        # Map provider names to environment variable names
        env_var_mapping = {
            "gemini": ["GEMINI_API_KEY", "MINDX_LLM__GEMINI__API_KEY"],
            "mistral": ["MISTRAL_API_KEY", "MINDX_LLM__MISTRAL__API_KEY"],
            "openai": ["OPENAI_API_KEY", "MINDX_LLM__OPENAI__API_KEY"],
            "anthropic": ["ANTHROPIC_API_KEY", "MINDX_LLM__ANTHROPIC__API_KEY"],
            "groq": ["GROQ_API_KEY", "MINDX_LLM__GROQ__API_KEY"],
        }
        
        env_vars = self._load_env_file()
        
        if provider_lower == "ollama":
            # Ollama uses base_url instead of API key
            if base_url:
                env_vars["MINDX_LLM__OLLAMA__BASE_URL"] = base_url
                self._save_env_file(env_vars)
                return {
                    "success": True,
                    "message": f"Ollama base URL set to {base_url}",
                    "provider": provider_lower
                }
            else:
                return {
                    "success": False,
                    "error": "Ollama requires base_url, not api_key"
                }
        
        if provider_lower not in env_var_mapping:
            return {
                "success": False,
                "error": f"Unknown provider: {provider}"
            }
        
        # Set both standard and prefixed environment variables
        for env_var in env_var_mapping[provider_lower]:
            env_vars[env_var] = api_key
        
        # Also set base_url if provided
        if base_url:
            env_vars[f"MINDX_LLM__{provider_lower.upper()}__BASE_URL"] = base_url
        
        self._save_env_file(env_vars)
        
        # Update environment variables in current process
        for env_var in env_var_mapping[provider_lower]:
            os.environ[env_var] = api_key
        
        logger.info(f"API key set for provider: {provider_lower}")
        
        return {
            "success": True,
            "message": f"API key set for {provider}",
            "provider": provider_lower,
            "api_key_masked": self._mask_api_key(api_key)
        }
    
    async def test_api_key(self, provider: str) -> Dict[str, Any]:
        """Test if API key is valid by making a test request"""
        try:
            if not self.registry:
                self.registry = await get_provider_registry()
            
            # Create provider instance
            instance = await self.registry.create_provider_instance(provider)
            if not instance:
                return {
                    "success": False,
                    "error": f"Could not create instance for {provider}"
                }
            
            # Test connection
            if hasattr(instance, 'test_connection'):
                result = await instance.test_connection()
                return result
            else:
                # Fallback to handler test
                handler = await create_llm_handler(provider_name=provider)
                if not handler:
                    return {
                        "success": False,
                        "error": f"Could not create handler for {provider}"
                    }
                
                test_prompt = "Hello"
                result = await handler.generate_text(
                    prompt=test_prompt,
                    model=handler.model_name_for_api or "test",
                    max_tokens=10
                )
                
                if result and not result.startswith("Error:") and not result.startswith('{"error"'):
                    return {
                        "success": True,
                        "message": f"API key for {provider} is valid",
                        "provider": provider
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API key test failed: {result}",
                        "provider": provider
                    }
        except Exception as e:
            logger.error(f"Error testing API key for {provider}: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider": provider
            }


class OllamaManager:
    """Manages Ollama server connections and model listing"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("MINDX_LLM__OLLAMA__BASE_URL", "http://localhost:11434")
        self.handler: Optional[OllamaHandler] = None
    
    async def get_handler(self) -> OllamaHandler:
        """Get or create Ollama handler"""
        if not self.handler:
            self.handler = OllamaHandler(
                model_name_for_api=None,
                base_url=self.base_url
            )
        return self.handler
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List all available models from Ollama server"""
        try:
            handler = await self.get_handler()
            models = await handler.list_local_models_api()
            
            if not models:
                return []
            
            # Format models for API response
            formatted_models = []
            for model in models:
                if isinstance(model, dict) and "error" not in model:
                    formatted_models.append({
                        "name": model.get("name", "unknown"),
                        "size": model.get("size"),
                        "digest": model.get("digest"),
                        "modified_at": model.get("modified_at"),
                        "details": model.get("details", {})
                    })
            
            logger.info(f"Found {len(formatted_models)} Ollama models")
            return formatted_models
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            return []
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Ollama server"""
        try:
            handler = await self.get_handler()
            models = await handler.list_local_models_api()
            
            if models and len(models) > 0 and not any("error" in str(m) for m in models):
                return {
                    "success": True,
                    "message": f"Connected to Ollama server at {self.base_url}",
                    "base_url": self.base_url,
                    "model_count": len(models)
                }
            else:
                return {
                    "success": False,
                    "error": "Could not connect to Ollama server or no models found",
                    "base_url": self.base_url
                }
        except Exception as e:
            logger.error(f"Error testing Ollama connection: {e}")
            return {
                "success": False,
                "error": str(e),
                "base_url": self.base_url
            }


class ModelSelectionAPI:
    """API for model selection and hierarchical chooser"""
    
    def __init__(self):
        self.model_registry = None
        self.performance_monitor = PerformanceMonitor()
    
    async def get_model_registry(self):
        """Get or initialize model registry"""
        if not self.model_registry:
            self.model_registry = await get_model_registry_async()
        return self.model_registry
    
    async def get_best_model_for_task(
        self,
        task_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get the best model for a given task using hierarchical chooser"""
        try:
            registry = await self.get_model_registry()
            
            # Convert task_type string to TaskType enum
            task_type_enum = None
            for tt in TaskType:
                if tt.value == task_type.lower() or tt.name.lower() == task_type.lower():
                    task_type_enum = tt
                    break
            
            if not task_type_enum:
                task_type_enum = TaskType.SIMPLE_CHAT  # Default
            
            # Get handler using hierarchical selection
            handler = registry.get_handler_for_purpose(task_type_enum, context)
            
            if not handler:
                return {
                    "success": False,
                    "error": f"No suitable model found for task type: {task_type}"
                }
            
            # Get model capabilities
            capabilities = registry.capabilities.get(f"{handler.provider}/{handler.model_name_for_api}", {})
            
            return {
                "success": True,
                "task_type": task_type,
                "selected_provider": handler.provider,
                "selected_model": handler.model_name_for_api,
                "capabilities": capabilities,
                "reasoning": "Selected using hierarchical model chooser based on capability, cost, latency, and performance"
            }
        except Exception as e:
            logger.error(f"Error selecting model for task: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_model_selection_info(self) -> Dict[str, Any]:
        """Get information about model selection system"""
        try:
            registry = await self.get_model_registry()
            
            # Get all available models
            all_models = []
            for model_id, capability in registry.capabilities.items():
                all_models.append({
                    "model_id": model_id,
                    "provider": capability.provider if hasattr(capability, 'provider') else model_id.split('/')[0],
                    "capabilities": capability.task_scores if hasattr(capability, 'task_scores') else {},
                    "cost_per_kilo_input": capability.cost_per_kilo_input if hasattr(capability, 'cost_per_kilo_input') else 0.0,
                    "cost_per_kilo_output": capability.cost_per_kilo_output if hasattr(capability, 'cost_per_kilo_output') else 0.0,
                })
            
            return {
                "success": True,
                "total_models": len(all_models),
                "models": all_models,
                "selection_weights": registry.model_selector.selection_weights if hasattr(registry, 'model_selector') else {},
                "task_types": [tt.value for tt in TaskType]
            }
        except Exception as e:
            logger.error(f"Error getting model selection info: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class LLMPerformanceAPI:
    """API for LLM performance metrics and usage tracking"""
    
    def __init__(self):
        self.performance_monitor = PerformanceMonitor()
    
    async def get_performance_metrics(
        self,
        model_name: Optional[str] = None,
        task_type: Optional[str] = None,
        time_range: Optional[str] = "24h"
    ) -> Dict[str, Any]:
        """Get performance metrics for LLM usage"""
        try:
            # Access metrics directly from performance monitor
            metrics = self.performance_monitor.metrics
            
            # Filter by model_name and task_type if provided
            filtered_metrics = {}
            for key, data in metrics.items():
                parts = key.split('|')
                if len(parts) >= 3:
                    m_name, t_type, agent_id = parts[0], parts[1], parts[2]
                    
                    if model_name and m_name != model_name:
                        continue
                    if task_type and t_type != task_type:
                        continue
                    
                    filtered_metrics[key] = data
            
            # Calculate totals
            total_calls = sum(m.get("total_calls", 0) for m in filtered_metrics.values())
            total_cost = sum(m.get("total_cost", 0.0) for m in filtered_metrics.values())
            total_tokens_input = sum(m.get("total_prompt_tokens", 0) for m in filtered_metrics.values())
            total_tokens_output = sum(m.get("total_completion_tokens", 0) for m in filtered_metrics.values())
            
            return {
                "success": True,
                "time_range": time_range,
                "total_calls": total_calls,
                "total_cost_usd": total_cost,
                "total_tokens_input": total_tokens_input,
                "total_tokens_output": total_tokens_output,
                "total_tokens": total_tokens_input + total_tokens_output,
                "metrics_by_model": filtered_metrics,
                "summary": {
                    "average_cost_per_call": total_cost / total_calls if total_calls > 0 else 0.0,
                    "average_tokens_per_call": (total_tokens_input + total_tokens_output) / total_calls if total_calls > 0 else 0,
                    "cost_per_1k_tokens": total_cost / ((total_tokens_input + total_tokens_output) / 1000) if (total_tokens_input + total_tokens_output) > 0 else 0.0
                }
            }
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get rate limit status for all providers"""
        # This would integrate with rate limiters if they expose status
        return {
            "success": True,
            "rate_limits": {
                "note": "Rate limit tracking is handled internally by handlers"
            }
        }

