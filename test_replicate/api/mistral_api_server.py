# mindx/api/mistral_api_server.py
"""
Mistral API Server for MindX Augmentic Intelligence System

This server provides a dedicated API for Mistral AI integration,
combining the best features from minimal_api_server.py and optimized_api_server.py
with comprehensive Mistral AI capabilities.
"""

import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

# Third-party imports
from fastapi import FastAPI, HTTPException, APIRouter, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Path Setup ---
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# --- MindX Core Imports ---
try:
    from utils.config import Config
    from utils.logging_config import setup_logging, get_logger
    from api.mistral_api import MistralIntegration, MistralConfig
except ImportError as e:
    print(f"CRITICAL ERROR: Failed to import MindX modules: {e}")
    sys.exit(1)

# --- Global Configuration and Logging ---
setup_logging()
logger = get_logger(__name__)
config = Config()

# --- Global State ---
class AppState:
    def __init__(self):
        self.initialized = False
        self.mistral_integration = None
        self.mistral_config = None

app_state = AppState()

# --- API Schemas ---
class MistralTestRequest(BaseModel):
    message: str = Field(..., description="Test message to send to Mistral")
    model: Optional[str] = Field(None, description="Specific model to use")

class MistralTestResponse(BaseModel):
    success: bool
    response: str
    model_used: str
    tokens_used: Optional[int] = None

class MistralChatRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(..., description="Chat messages")
    model: Optional[str] = Field(None, description="Model to use")
    temperature: Optional[float] = Field(0.7, description="Temperature for generation")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")

class MistralChatResponse(BaseModel):
    success: bool
    response: str
    model_used: str
    tokens_used: Optional[int] = None

class MistralEmbeddingRequest(BaseModel):
    text: str = Field(..., description="Text to embed")
    model: Optional[str] = Field("mistral-embed", description="Embedding model to use")

class MistralEmbeddingResponse(BaseModel):
    success: bool
    embedding: List[float]
    model_used: str
    dimensions: int

# --- Startup and Shutdown ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Mistral API Server...")
    try:
        # Initialize Mistral configuration
        app_state.mistral_config = MistralConfig(
            api_key=config.get("MISTRAL_API_KEY") or config.get("llm.mistral.api_key"),
            base_url=config.get("llm.mistral.base_url", "https://api.mistral.ai/v1")
        )
        
        # Initialize Mistral integration
        app_state.mistral_integration = MistralIntegration(app_state.mistral_config)
        app_state.initialized = True
        
        logger.info("Mistral API Server initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Mistral API Server: {e}")
        app_state.initialized = False
    
    yield
    
    # Shutdown
    logger.info("Shutting down Mistral API Server...")

# --- FastAPI App Creation ---
app = FastAPI(
    title="MindX Mistral API Server",
    description="Dedicated API server for Mistral AI integration with MindX",
    version="1.0.0",
    lifespan=lifespan
)

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependency Functions ---
def get_mistral_integration() -> MistralIntegration:
    """Get the Mistral integration instance"""
    if not app_state.initialized or not app_state.mistral_integration:
        raise HTTPException(status_code=503, detail="Mistral integration not available")
    return app_state.mistral_integration

# --- Health Check ---
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if app_state.initialized else "unhealthy",
        "mistral_available": app_state.mistral_integration.api_available if app_state.mistral_integration else False,
        "initialized": app_state.initialized
    }

# --- Mistral API Endpoints ---
@app.post("/test", response_model=MistralTestResponse)
async def test_mistral(
    request: MistralTestRequest,
    mistral: MistralIntegration = Depends(get_mistral_integration)
):
    """Test Mistral API connectivity and basic functionality"""
    try:
        if not mistral.api_available:
            return MistralTestResponse(
                success=False,
                response="Mistral API key not configured",
                model_used="none"
            )
        
        # Use the specified model or default
        model = request.model or "mistral-large-latest"
        
        # Simple test message
        test_message = f"Test message: {request.message}. Please respond with 'OK' if you can process this."
        
        # Get model info
        model_info = mistral.get_model_info(model)
        if not model_info:
            return MistralTestResponse(
                success=False,
                response=f"Model {model} not found in catalog",
                model_used=model
            )
        
        # Make actual API call to Mistral
        try:
            import aiohttp
            headers = {
                "Authorization": f"Bearer {mistral.config.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": request.message}
                ],
                "temperature": 0.7,
                "max_tokens": 100
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{mistral.config.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return MistralTestResponse(
                            success=True,
                            response=data["choices"][0]["message"]["content"],
                            model_used=model,
                            tokens_used=data.get("usage", {}).get("total_tokens", 0)
                        )
                    else:
                        error_text = await response.text()
                        return MistralTestResponse(
                            success=False,
                            response=f"API Error {response.status}: {error_text}",
                            model_used=model
                        )
        except Exception as e:
            return MistralTestResponse(
                success=False,
                response=f"Request failed: {str(e)}",
                model_used=model
            )
        
    except Exception as e:
        logger.error(f"Test Mistral failed: {e}")
        return MistralTestResponse(
            success=False,
            response=f"Error: {str(e)}",
            model_used=request.model or "unknown"
        )

@app.post("/chat", response_model=MistralChatResponse)
async def chat_with_mistral(
    request: MistralChatRequest,
    mistral: MistralIntegration = Depends(get_mistral_integration)
):
    """Chat with Mistral AI"""
    try:
        if not mistral.api_available:
            return MistralChatResponse(
                success=False,
                response="Mistral API key not configured",
                model_used="none"
            )
        
        # Use the specified model or default
        model = request.model or "mistral-large-latest"
        
        # Get model info
        model_info = mistral.get_model_info(model)
        if not model_info:
            return MistralChatResponse(
                success=False,
                response=f"Model {model} not found in catalog",
                model_used=model
            )
        
        # Make actual API call to Mistral
        try:
            import aiohttp
            headers = {
                "Authorization": f"Bearer {mistral.config.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": [{"role": msg["role"], "content": msg["content"]} for msg in request.messages],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{mistral.config.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return MistralChatResponse(
                            success=True,
                            response=data["choices"][0]["message"]["content"],
                            model_used=model,
                            tokens_used=data.get("usage", {}).get("total_tokens", 0)
                        )
                    else:
                        error_text = await response.text()
                        return MistralChatResponse(
                            success=False,
                            response=f"API Error {response.status}: {error_text}",
                            model_used=model
                        )
        except Exception as e:
            return MistralChatResponse(
                success=False,
                response=f"Request failed: {str(e)}",
                model_used=model
            )
        
    except Exception as e:
        logger.error(f"Chat with Mistral failed: {e}")
        return MistralChatResponse(
            success=False,
            response=f"Error: {str(e)}",
            model_used=request.model or "unknown"
        )

@app.post("/embed", response_model=MistralEmbeddingResponse)
async def get_embeddings(
    request: MistralEmbeddingRequest,
    mistral: MistralIntegration = Depends(get_mistral_integration)
):
    """Get embeddings from Mistral"""
    try:
        if not mistral.api_available:
            return MistralEmbeddingResponse(
                success=False,
                embedding=[],
                model_used="none",
                dimensions=0
            )
        
        # Use the specified model or default
        model = request.model or "mistral-embed"
        
        # Get model info
        model_info = mistral.get_model_info(model)
        if not model_info:
            return MistralEmbeddingResponse(
                success=False,
                embedding=[],
                model_used=model,
                dimensions=0
            )
        
        # Make actual API call to Mistral for embeddings
        try:
            import aiohttp
            headers = {
                "Authorization": f"Bearer {mistral.config.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "input": [request.text]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{mistral.config.base_url}/embeddings",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        embedding = data["data"][0]["embedding"]
                        return MistralEmbeddingResponse(
                            success=True,
                            embedding=embedding,
                            model_used=model,
                            dimensions=len(embedding)
                        )
                    else:
                        error_text = await response.text()
                        return MistralEmbeddingResponse(
                            success=False,
                            embedding=[],
                            model_used=model,
                            dimensions=0
                        )
        except Exception as e:
            return MistralEmbeddingResponse(
                success=False,
                embedding=[],
                model_used=model,
                dimensions=0
            )
        
    except Exception as e:
        logger.error(f"Get embeddings failed: {e}")
        return MistralEmbeddingResponse(
            success=False,
            embedding=[],
            model_used=request.model or "unknown",
            dimensions=0
        )

@app.get("/models")
async def list_models(mistral: MistralIntegration = Depends(get_mistral_integration)):
    """List available Mistral models"""
    try:
        if not mistral.api_available:
            return {"success": False, "models": [], "error": "Mistral API key not configured"}
        
        # Return available models from the catalog
        models = list(mistral.model_catalog.keys())
        return {
            "success": True,
            "models": models,
            "count": len(models)
        }
        
    except Exception as e:
        logger.error(f"List models failed: {e}")
        return {"success": False, "models": [], "error": str(e)}

@app.get("/models/{model_name}")
async def get_model_info(
    model_name: str,
    mistral: MistralIntegration = Depends(get_mistral_integration)
):
    """Get information about a specific model"""
    try:
        if not mistral.api_available:
            return {"success": False, "model_info": None, "error": "Mistral API key not configured"}
        
        model_info = mistral.get_model_info(model_name)
        if not model_info:
            return {"success": False, "model_info": None, "error": f"Model {model_name} not found"}
        
        return {
            "success": True,
            "model_info": model_info,
            "model_name": model_name
        }
        
    except Exception as e:
        logger.error(f"Get model info failed: {e}")
        return {"success": False, "model_info": None, "error": str(e)}

# --- Root endpoint ---
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "MindX Mistral API Server",
        "version": "1.0.0",
        "status": "running",
        "mistral_available": app_state.mistral_integration.api_available if app_state.mistral_integration else False,
        "endpoints": [
            "/health",
            "/test",
            "/chat", 
            "/embed",
            "/models",
            "/models/{model_name}"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
