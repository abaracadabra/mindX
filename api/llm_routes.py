"""
LLM Provider API Routes for mindX

FastAPI router for LLM provider management, API keys, Ollama integration,
and performance monitoring.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from typing import Optional, Dict, Any
import time

from api.llm_provider_api import (
    LLMProviderManager,
    OllamaManager,
    ModelSelectionAPI,
    LLMPerformanceAPI
)
from api.provider_registry import get_provider_registry
from utils.logging_config import get_logger


class SetAPIKeyRequest(BaseModel):
    """Request model for setting API key"""
    api_key: str
    base_url: Optional[str] = None


class BestModelRequest(BaseModel):
    """Request model for getting best model"""
    task_type: str
    context: Optional[Dict[str, Any]] = None

logger = get_logger(__name__)

router = APIRouter(prefix="/api/llm", tags=["LLM Providers"])


@router.get("/providers", summary="Get all LLM provider configurations")
async def get_llm_providers():
    """
    Get all configured LLM providers and their API key status (masked).
    """
    try:
        manager = LLMProviderManager()
        providers = await manager.get_api_keys()
        return {
            "success": True,
            "providers": providers,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Failed to get LLM providers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve LLM providers: {e}")


@router.post("/providers/{provider}/api-key", summary="Set API key for a provider")
async def set_provider_api_key(
    provider: str,
    request: SetAPIKeyRequest
):
    """
    Set API key for a specific LLM provider.
    """
    try:
        manager = LLMProviderManager()
        result = await manager.set_api_key(provider, request.api_key, request.base_url)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to set API key"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set API key for {provider}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set API key: {e}")


@router.post("/providers/{provider}/test", summary="Test API key for a provider")
async def test_provider_api_key(provider: str):
    """
    Test if API key is valid for a provider.
    """
    try:
        manager = LLMProviderManager()
        result = await manager.test_api_key(provider)
        return result
    except Exception as e:
        logger.error(f"Failed to test API key for {provider}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test API key: {e}")


@router.get("/ollama/models", summary="List available Ollama models")
async def list_ollama_models(
    base_url: Optional[str] = Query(None, description="Ollama server base URL (e.g., http://10.0.0.155:108080)"),
    host: Optional[str] = Query(None, description="Ollama server host (e.g., 10.0.0.155)"),
    port: Optional[int] = Query(None, description="Ollama server port (e.g., 108080)")
):
    """
    List all available models from Ollama server.
    Supports both base_url and host/port configuration.
    """
    try:
        from api.ollama_url import create_ollama_api
        
        # Create API instance with host/port or base_url
        if base_url:
            ollama_api = create_ollama_api(base_url=base_url)
        elif host and port:
            ollama_api = create_ollama_api(host=host, port=port)
        else:
            ollama_api = create_ollama_api()
        
        models = await ollama_api.list_models()
        return {
            "success": True,
            "models": models,
            "count": len(models),
            "base_url": ollama_api.base_url,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Failed to list Ollama models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list Ollama models: {e}")


@router.get("/ollama/connection", summary="Test Ollama server connection")
async def test_ollama_connection(
    base_url: Optional[str] = Query(None, description="Ollama server base URL"),
    host: Optional[str] = Query(None, description="Ollama server host"),
    port: Optional[int] = Query(None, description="Ollama server port")
):
    """
    Test connection to Ollama server.
    Supports both base_url and host/port configuration.
    """
    try:
        from api.ollama_url import create_ollama_api
        
        if base_url:
            ollama_api = create_ollama_api(base_url=base_url)
        elif host and port:
            ollama_api = create_ollama_api(host=host, port=port)
        else:
            ollama_api = create_ollama_api()
        
        result = await ollama_api.test_connection()
        result["base_url"] = ollama_api.base_url
        result["timestamp"] = time.time()
        return result
    except Exception as e:
        logger.error(f"Failed to test Ollama connection: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test Ollama connection: {str(e)}"
        )


@router.get("/ollama/model/{model_name}", summary="Get model information")
async def get_ollama_model_info(
    model_name: str,
    base_url: Optional[str] = Query(None, description="Ollama server base URL"),
    host: Optional[str] = Query(None, description="Ollama server host"),
    port: Optional[int] = Query(None, description="Ollama server port")
):
    """Get detailed information about a specific Ollama model"""
    try:
        from api.ollama_url import create_ollama_api
        
        if base_url:
            ollama_api = create_ollama_api(base_url=base_url)
        elif host and port:
            ollama_api = create_ollama_api(host=host, port=port)
        else:
            ollama_api = create_ollama_api()
        
        info = await ollama_api.get_model_info(model_name)
        return {
            "success": True,
            "model": model_name,
            "info": info,
            "base_url": ollama_api.base_url
        }
    except Exception as e:
        logger.error(f"Failed to get model info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get model info: {e}")


@router.post("/ollama/config", summary="Set Ollama server configuration")
async def set_ollama_config(
    base_url: Optional[str] = Body(None),
    host: Optional[str] = Body(None),
    port: Optional[int] = Body(None)
):
    """
    Set Ollama server configuration.
    Can use base_url or host/port combination.
    """
    try:
        from api.ollama_url import create_ollama_api
        
        if base_url:
            ollama_api = create_ollama_api(base_url=base_url)
        elif host and port:
            ollama_api = create_ollama_api(host=host, port=port)
        else:
            raise HTTPException(status_code=400, detail="Must provide either base_url or host+port")
        
        # Test connection
        test_result = await ollama_api.test_connection()
        
        return {
            "success": test_result.get("success", False),
            "base_url": ollama_api.base_url,
            "message": test_result.get("message", "Configuration set"),
            "model_count": test_result.get("model_count", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set Ollama config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set Ollama config: {e}")


@router.post("/ollama/generate", summary="Generate text completion using Ollama")
async def generate_ollama_completion(
    base_url: Optional[str] = Query(None),
    host: Optional[str] = Query(None),
    port: Optional[int] = Query(None),
    model: str = Body(..., description="Model name"),
    prompt: str = Body(..., description="Prompt text"),
    max_tokens: Optional[int] = Body(500, description="Maximum tokens"),
    temperature: Optional[float] = Body(0.7, description="Temperature")
):
    """Generate text completion using Ollama"""
    try:
        from api.ollama_url import create_ollama_api
        
        if base_url:
            ollama_api = create_ollama_api(base_url=base_url)
        elif host and port:
            ollama_api = create_ollama_api(host=host, port=port)
        else:
            ollama_api = create_ollama_api()
        
        result = await ollama_api.generate_text(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        if result and not result.startswith('{"error"'):
            return {
                "success": True,
                "text": result,
                "model": model,
                "base_url": ollama_api.base_url
            }
        else:
            import json
            error_data = json.loads(result) if result.startswith('{') else {"error": result}
            return {
                "success": False,
                "error": error_data.get("error", "Generation failed"),
                "message": error_data.get("message", "Unknown error")
            }
    except Exception as e:
        logger.error(f"Failed to generate Ollama completion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate completion: {str(e)}")


@router.get("/model-selection/info", summary="Get model selection system information")
async def get_model_selection_info():
    """
    Get information about the hierarchical model selection system.
    """
    try:
        api = ModelSelectionAPI()
        result = await api.get_model_selection_info()
        return result
    except Exception as e:
        logger.error(f"Failed to get model selection info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get model selection info: {e}")


@router.post("/model-selection/best", summary="Get best model for a task")
async def get_best_model_for_task(request: BestModelRequest):
    """
    Use hierarchical model chooser to select the best model for a given task.
    """
    try:
        api = ModelSelectionAPI()
        result = await api.get_best_model_for_task(request.task_type, request.context)
        return result
    except Exception as e:
        logger.error(f"Failed to select best model: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to select best model: {e}")


@router.get("/performance/metrics", summary="Get LLM performance metrics")
async def get_llm_performance_metrics(
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    time_range: Optional[str] = Query("24h", description="Time range for metrics")
):
    """
    Get performance metrics for LLM usage including cost, tokens, and rate limits.
    """
    try:
        api = LLMPerformanceAPI()
        result = await api.get_performance_metrics(model_name, task_type, time_range)
        return result
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {e}")


@router.get("/performance/rate-limits", summary="Get rate limit status")
async def get_rate_limit_status():
    """
    Get rate limit status for all LLM providers.
    """
    try:
        api = LLMPerformanceAPI()
        result = await api.get_rate_limit_status()
        return result
    except Exception as e:
        logger.error(f"Failed to get rate limit status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get rate limit status: {e}")


@router.get("/providers/registry", summary="List all registered providers")
async def list_providers():
    """List all providers in the registry"""
    try:
        registry = await get_provider_registry()
        providers = registry.list_providers()
        return {
            "success": True,
            "providers": providers,
            "count": len(providers)
        }
    except Exception as e:
        logger.error(f"Failed to list providers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list providers: {e}")


@router.post("/providers/registry/register", summary="Register a new provider")
async def register_provider(
    name: str = Body(...),
    display_name: str = Body(...),
    module_path: str = Body(...),
    factory_function: str = Body(...),
    api_key_env_var: Optional[str] = Body(None),
    base_url_env_var: Optional[str] = Body(None),
    requires_api_key: bool = Body(True),
    requires_base_url: bool = Body(False),
    default_rate_limit_rpm: int = Body(60),
    default_rate_limit_tpm: int = Body(100000)
):
    """Register a new API provider dynamically"""
    try:
        registry = await get_provider_registry()
        success = registry.register_provider(
            name=name,
            display_name=display_name,
            module_path=module_path,
            factory_function=factory_function,
            api_key_env_var=api_key_env_var,
            base_url_env_var=base_url_env_var,
            requires_api_key=requires_api_key,
            requires_base_url=requires_base_url,
            default_rate_limit_rpm=default_rate_limit_rpm,
            default_rate_limit_tpm=default_rate_limit_tpm
        )
        
        if success:
            return {"success": True, "message": f"Provider {name} registered successfully"}
        else:
            raise HTTPException(status_code=400, detail=f"Failed to register provider {name}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register provider: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register provider: {e}")


@router.delete("/providers/registry/{provider_name}", summary="Unregister a provider")
async def unregister_provider(provider_name: str):
    """Remove a provider from the registry"""
    try:
        registry = await get_provider_registry()
        success = registry.unregister_provider(provider_name)
        
        if success:
            return {"success": True, "message": f"Provider {provider_name} unregistered"}
        else:
            raise HTTPException(status_code=404, detail=f"Provider {provider_name} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unregister provider: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unregister provider: {e}")


@router.post("/providers/{provider_name}/enable", summary="Enable a provider")
async def enable_provider(provider_name: str):
    """Enable a provider"""
    try:
        registry = await get_provider_registry()
        success = registry.enable_provider(provider_name)
        
        if success:
            return {"success": True, "message": f"Provider {provider_name} enabled"}
        else:
            raise HTTPException(status_code=404, detail=f"Provider {provider_name} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable provider: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to enable provider: {e}")


@router.post("/providers/{provider_name}/disable", summary="Disable a provider")
async def disable_provider(provider_name: str):
    """Disable a provider"""
    try:
        registry = await get_provider_registry()
        success = registry.disable_provider(provider_name)
        
        if success:
            return {"success": True, "message": f"Provider {provider_name} disabled"}
        else:
            raise HTTPException(status_code=404, detail=f"Provider {provider_name} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable provider: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to disable provider: {e}")


@router.post("/providers/{provider_name}/rate-limits", summary="Update provider rate limits")
async def update_provider_rate_limits(
    provider_name: str,
    rpm: Optional[int] = Body(None),
    tpm: Optional[int] = Body(None)
):
    """Update rate limits for a provider"""
    try:
        registry = await get_provider_registry()
        success = registry.update_provider_rate_limits(provider_name, rpm=rpm, tpm=tpm)
        
        if success:
            return {
                "success": True,
                "message": f"Rate limits updated for {provider_name}",
                "rpm": rpm,
                "tpm": tpm
            }
        else:
            raise HTTPException(status_code=404, detail=f"Provider {provider_name} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update rate limits: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update rate limits: {e}")


@router.get("/providers/{provider_name}/metrics", summary="Get provider metrics")
async def get_provider_metrics(provider_name: str):
    """Get metrics for a specific provider"""
    try:
        registry = await get_provider_registry()
        instance = await registry.create_provider_instance(provider_name)
        
        if not instance:
            raise HTTPException(status_code=404, detail=f"Provider {provider_name} not found or could not be instantiated")
        
        if hasattr(instance, 'get_metrics'):
            metrics = instance.get_metrics()
            return {"success": True, "provider": provider_name, "metrics": metrics}
        else:
            return {
                "success": True,
                "provider": provider_name,
                "metrics": {"note": "Metrics not available for this provider"}
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get provider metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get provider metrics: {e}")

