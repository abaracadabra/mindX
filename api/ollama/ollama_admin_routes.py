"""
Ollama Admin API Routes

Professional admin interface for Ollama connection management, diagnostics,
and interaction testing. Supports multiple agents connecting to Ollama at 10.0.0.155:18080.
"""

from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
from pathlib import Path
import json

from .ollama_url import OllamaAPI, create_ollama_api
from agents.memory_agent import MemoryAgent, MemoryType, MemoryImportance
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/admin/ollama", tags=["Ollama Admin"])

# Global Ollama API instance (shared across agents)
_ollama_api: Optional[OllamaAPI] = None
_memory_agent: Optional[MemoryAgent] = None

# Diagnostic log storage
DIAGNOSTIC_LOG_DIR = PROJECT_ROOT / "data" / "logs" / "ollama_diagnostics"
DIAGNOSTIC_LOG_DIR.mkdir(parents=True, exist_ok=True)


def get_ollama_api() -> OllamaAPI:
    """Get or create shared Ollama API instance"""
    global _ollama_api
    if _ollama_api is None:
        config = Config()
        _ollama_api = create_ollama_api(
            host="10.0.0.155",
            port=18080,
            config=config
        )
    return _ollama_api


def get_memory_agent() -> Optional[MemoryAgent]:
    """Get or create MemoryAgent for diagnostic logging"""
    global _memory_agent
    if _memory_agent is None:
        try:
            config = Config()
            _memory_agent = MemoryAgent(config=config)
        except Exception as e:
            logger.warning(f"MemoryAgent not available for diagnostics: {e}")
    return _memory_agent


async def log_diagnostic(
    agent_id: str,
    event_type: str,
    data: Dict[str, Any],
    log_level: str = "INFO"
) -> None:
    """Log diagnostic information to memory agent and file"""
    try:
        memory_agent = get_memory_agent()
        if memory_agent:
            await memory_agent.save_timestamped_memory_with_embedding(
                agent_id=agent_id,
                memory_type=MemoryType.PERFORMANCE,
                content={
                    "event_type": event_type,
                    "log_level": log_level,
                    **data
                },
                importance=MemoryImportance.MEDIUM,
                context={"source": "ollama_admin", "timestamp": datetime.now().isoformat()},
                tags=["ollama", "diagnostics", log_level.lower()]
            )
        
        # Also log to file for admin UI
        log_file = DIAGNOSTIC_LOG_DIR / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "event_type": event_type,
            "log_level": log_level,
            **data
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to log diagnostic: {e}")


class OllamaTestRequest(BaseModel):
    """Request model for testing Ollama connection"""
    base_url: Optional[str] = None
    try_fallback: bool = True


class OllamaInteractionRequest(BaseModel):
    """Request model for Ollama interaction"""
    prompt: str
    model: str = "llama3:8b"
    agent_id: Optional[str] = None
    use_chat: bool = True
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048


class OllamaDiagnosticRequest(BaseModel):
    """Request model for diagnostic queries"""
    agent_id: Optional[str] = None
    log_level: Optional[str] = None  # INFO, DEBUG, WARNING, ERROR
    limit: int = 100
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@router.get("/status", summary="Get Ollama connection status")
async def get_ollama_status():
    """Get current Ollama connection status and metrics"""
    try:
        ollama_api = get_ollama_api()
        metrics = ollama_api.get_metrics()
        
        # Test connection
        test_result = await ollama_api.test_connection(try_fallback=False)
        
        await log_diagnostic(
            "admin",
            "status_check",
            {
                "base_url": ollama_api.base_url,
                "using_fallback": ollama_api.using_fallback,
                "connection_test": test_result
            }
        )
        
        return {
            "success": True,
            "connection": {
                "base_url": ollama_api.base_url,
                "fallback_url": ollama_api.fallback_url,
                "using_fallback": ollama_api.using_fallback,
                "connected": test_result.get("success", False),
                "model_count": test_result.get("model_count", 0)
            },
            "metrics": metrics,
            "test_result": test_result
        }
    except Exception as e:
        logger.error(f"Error getting Ollama status: {e}", exc_info=True)
        await log_diagnostic("admin", "status_error", {"error": str(e)}, "ERROR")
        raise HTTPException(status_code=500, detail=f"Failed to get Ollama status: {e}")


@router.post("/test", summary="Test Ollama connection")
async def test_ollama_connection(request: OllamaTestRequest = Body(...)):
    """Test connection to Ollama server with detailed feedback"""
    try:
        ollama_api = get_ollama_api()
        
        # Override base URL if provided
        if request.base_url:
            # Create temporary instance for testing
            config = Config()
            test_api = create_ollama_api(base_url=request.base_url, config=config)
            test_result = await test_api.test_connection(try_fallback=request.try_fallback)
            await test_api.shutdown()
        else:
            test_result = await ollama_api.test_connection(try_fallback=request.try_fallback)
        
        await log_diagnostic(
            "admin",
            "connection_test",
            {
                "base_url": request.base_url or ollama_api.base_url,
                "success": test_result.get("success", False),
                "result": test_result
            },
            "INFO" if test_result.get("success") else "WARNING"
        )
        
        return {
            "success": True,
            "test_result": test_result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error testing Ollama connection: {e}", exc_info=True)
        await log_diagnostic("admin", "test_error", {"error": str(e)}, "ERROR")
        raise HTTPException(status_code=500, detail=f"Failed to test connection: {e}")


@router.post("/interact", summary="Interact with Ollama (input/response)")
async def interact_with_ollama(request: OllamaInteractionRequest = Body(...)):
    """Send a prompt to Ollama and get response (for admin testing)"""
    try:
        ollama_api = get_ollama_api()
        agent_id = request.agent_id or "admin"
        
        start_time = datetime.now()
        
        await log_diagnostic(
            agent_id,
            "interaction_start",
            {
                "prompt": request.prompt[:100],  # First 100 chars
                "model": request.model,
                "use_chat": request.use_chat
            }
        )
        
        # Generate response
        if request.use_chat:
            messages = [{"role": "user", "content": request.prompt}]
            response = await ollama_api.generate_text(
                prompt=request.prompt,
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                use_chat=True,
                messages=messages
            )
        else:
            response = await ollama_api.generate_text(
                prompt=request.prompt,
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                use_chat=False
            )
        
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        # Get metrics
        metrics = ollama_api.get_metrics()
        
        await log_diagnostic(
            agent_id,
            "interaction_complete",
            {
                "model": request.model,
                "response_length": len(response) if response else 0,
                "duration_ms": duration_ms,
                "success": response is not None and not response.startswith('{"error"')
            },
            "INFO" if response and not response.startswith('{"error"') else "ERROR"
        )
        
        return {
            "success": True,
            "request": {
                "prompt": request.prompt,
                "model": request.model,
                "agent_id": agent_id
            },
            "response": response,
            "metrics": {
                "duration_ms": duration_ms,
                "timestamp": end_time.isoformat()
            },
            "api_metrics": metrics
        }
    except Exception as e:
        logger.error(f"Error interacting with Ollama: {e}", exc_info=True)
        await log_diagnostic(agent_id or "admin", "interaction_error", {"error": str(e)}, "ERROR")
        raise HTTPException(status_code=500, detail=f"Failed to interact with Ollama: {e}")


@router.get("/models", summary="List available Ollama models")
async def list_ollama_models():
    """List all available models on Ollama server"""
    try:
        ollama_api = get_ollama_api()
        models = await ollama_api.list_models()
        
        await log_diagnostic("admin", "models_listed", {"model_count": len(models)})
        
        return {
            "success": True,
            "models": models,
            "count": len(models),
            "base_url": ollama_api.base_url
        }
    except Exception as e:
        logger.error(f"Error listing Ollama models: {e}", exc_info=True)
        await log_diagnostic("admin", "models_error", {"error": str(e)}, "ERROR")
        raise HTTPException(status_code=500, detail=f"Failed to list models: {e}")


@router.get("/diagnostics", summary="Get diagnostic logs")
async def get_diagnostics(
    agent_id: Optional[str] = Query(None),
    log_level: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Get diagnostic logs from memory agent and file system"""
    try:
        logs = []
        
        # Read from file logs
        log_files = sorted(DIAGNOSTIC_LOG_DIR.glob("*.jsonl"), reverse=True)
        for log_file in log_files[:7]:  # Last 7 days
            try:
                with open(log_file, "r") as f:
                    for line in f:
                        if line.strip():
                            log_entry = json.loads(line)
                            
                            # Filter by agent_id
                            if agent_id and log_entry.get("agent_id") != agent_id:
                                continue
                            
                            # Filter by log_level
                            if log_level and log_entry.get("log_level") != log_level.upper():
                                continue
                            
                            # Filter by date range
                            if start_date and log_entry.get("timestamp", "") < start_date:
                                continue
                            if end_date and log_entry.get("timestamp", "") > end_date:
                                continue
                            
                            logs.append(log_entry)
            except Exception as e:
                logger.warning(f"Error reading log file {log_file}: {e}")
        
        # Sort by timestamp (newest first) and limit
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        logs = logs[:limit]
        
        # Also query memory agent if available
        memory_logs = []
        memory_agent = get_memory_agent()
        if memory_agent:
            try:
                # Query memory for Ollama diagnostics
                memory_results = await memory_agent.query_memories_semantic(
                    query="ollama diagnostics",
                    agent_id=agent_id,
                    limit=min(limit, 50),
                    min_similarity=0.5
                )
                for memory in memory_results:
                    memory_logs.append({
                        "timestamp": memory.timestamp_utc.isoformat() if hasattr(memory.timestamp_utc, 'isoformat') else str(memory.timestamp_utc),
                        "agent_id": memory.metadata.get("agent", "unknown"),
                        "event_type": memory.content.get("event_type", "unknown"),
                        "log_level": memory.content.get("log_level", "INFO"),
                        "data": memory.content,
                        "source": "memory_agent"
                    })
            except Exception as e:
                logger.warning(f"Error querying memory agent: {e}")
        
        # Combine and sort
        all_logs = logs + memory_logs
        all_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        all_logs = all_logs[:limit]
        
        return {
            "success": True,
            "logs": all_logs,
            "count": len(all_logs),
            "filters": {
                "agent_id": agent_id,
                "log_level": log_level,
                "limit": limit,
                "start_date": start_date,
                "end_date": end_date
            }
        }
    except Exception as e:
        logger.error(f"Error getting diagnostics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get diagnostics: {e}")


@router.get("/metrics", summary="Get Ollama API metrics")
async def get_ollama_metrics():
    """Get detailed Ollama API metrics"""
    try:
        ollama_api = get_ollama_api()
        metrics = ollama_api.get_metrics()
        
        return {
            "success": True,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {e}")
