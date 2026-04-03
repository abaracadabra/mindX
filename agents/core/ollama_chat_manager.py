"""
Ollama Chat Manager for MindXAgent

Provides persistent connections, dynamic model discovery, and chat capabilities
for mindXagent to interact with Ollama models.
"""

import asyncio
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict

from utils.config import Config
from utils.logging_config import get_logger
from api.ollama import OllamaAPI, create_ollama_api
from agents.core.inference_optimizer import InferenceOptimizer
from agents.core.model_scorer import HierarchicalModelScorer

logger = get_logger(__name__)


class OllamaChatManager:
    """
    Manages persistent Ollama connections, model discovery, and chat sessions.
    
    Features:
    - Persistent connections with keep_alive
    - Dynamic model discovery (periodic refresh)
    - Chat conversation history management
    - Model selection and adaptation
    - Automatic reconnection on failures
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        config: Optional[Config] = None,
        model_discovery_interval: int = 86400,  # 24 hours; use manual discover_models(force=True) or API to refresh sooner
        keep_alive: str = "10m",  # Keep models loaded for 10 minutes
        conversation_history_path: Optional[Path] = None
    ):
        self.config = config or Config()
        
        # Determine base_url following ollama_handler.py pattern
        if base_url is None:
            # Try to load from settings if available (matching ollama_handler.py pattern)
            try:
                from webmind.settings import SettingsManager
                settings = SettingsManager()
                base_url = settings.get('ollama_base_url', None)
            except:
                pass
            
            # Fall back to config or environment
            if not base_url:
                base_url = os.getenv("MINDX_LLM__OLLAMA__BASE_URL") or self.config.get("llm.ollama.base_url")
                # Use env var (loaded from BANKON vault at startup), then config, then localhost
                if not base_url:
                    base_url = "http://localhost:11434"
                    logger.info(f"Using local Ollama server: {base_url}")
        
        # Ensure base_url doesn't have trailing /api - we'll add it (matching ollama_handler.py pattern)
        base_url = base_url.rstrip('/')
        if base_url.endswith('/api'):
            base_url = base_url[:-4]
        
        self.base_url = base_url
        self.model_discovery_interval = model_discovery_interval
        self.keep_alive = keep_alive
        
        # Initialize Ollama API
        self.ollama_api: Optional[OllamaAPI] = None
        self._api_lock = asyncio.Lock()
        
        # Model management
        self.available_models: List[Dict[str, Any]] = []
        self.model_capabilities: Dict[str, Dict[str, Any]] = {}
        self.last_model_discovery: float = 0
        self._model_discovery_task: Optional[asyncio.Task] = None
        
        # Chat sessions (conversation history per model)
        self.chat_sessions: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        self.conversation_history_path = conversation_history_path or Path("data/ollama_chat_history.json")
        self._load_conversation_history()
        
        # Connection state
        self.connected = False
        self.connection_retries = 0
        self.max_retries = 3
        
        # Model selection callbacks
        self.model_selection_callbacks: List[Callable] = []
        
        # Inference optimizer for frequency optimization
        self.inference_optimizer: Optional[InferenceOptimizer] = None
        
        # Hierarchical model scorer for adaptive model selection
        self.model_scorer: Optional[HierarchicalModelScorer] = None
        self._init_model_scorer()
        
        logger.info(f"OllamaChatManager initialized for {self.base_url}")
    
    def update_base_url(self, base_url: str):
        """
        Update the base URL and rebuild API connection.
        Matches ollama_handler.py pattern.
        """
        # Ensure base_url doesn't have trailing /api - we'll add it
        base_url = base_url.rstrip('/')
        if base_url.endswith('/api'):
            base_url = base_url[:-4]
        
        old_base_url = self.base_url
        self.base_url = base_url
        
        # Reset API connection to use new URL
        self.ollama_api = None
        self.connected = False
        
        logger.info(f"Ollama base URL updated from {old_base_url} to {base_url}")
    
    def _init_model_scorer(self):
        """Initialize hierarchical model scorer"""
        try:
            metrics_file = Path("data/model_performance_metrics.json")
            self.model_scorer = HierarchicalModelScorer(metrics_file=metrics_file)
            logger.info("Hierarchical model scorer initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize model scorer: {e}")
            self.model_scorer = None
    
    async def initialize(self) -> bool:
        """Initialize connection and discover models"""
        try:
            async with self._api_lock:
                if not self.ollama_api:
                    self.ollama_api = create_ollama_api(base_url=self.base_url)
                    logger.info(f"Ollama API initialized: {self.ollama_api.base_url}")
            
            # Test connection
            if await self._test_connection():
                self.connected = True
                self.connection_retries = 0
                
                # Discover models immediately
                await self.discover_models()
                
                # Start periodic model discovery
                self._start_model_discovery()
                
                # Initialize inference optimizer
                await self._init_inference_optimizer()
                
                logger.info(f"✓ OllamaChatManager connected to {self.base_url}")
                return True
            else:
                logger.warning(f"⚠ OllamaChatManager connection test failed")
                return False
                
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"Failed to initialize OllamaChatManager ({error_type}): {error_msg}", exc_info=True)
            
            # Log initialization failure
            try:
                if hasattr(self, 'memory_agent') and self.memory_agent:
                    await self.memory_agent.log_process(
                        "ollama_init_error",
                        {
                            "error_type": error_type,
                            "error_message": error_msg,
                            "base_url": str(self.base_url),
                            "timestamp": time.time()
                        },
                        {"agent_id": "ollama_chat_manager", "error": True, "critical": True}
                    )
            except Exception as log_error:
                logger.debug(f"Failed to log initialization error: {log_error}")
            
            self.connected = False
            raise
            self.connected = False
            return False
    
    async def _test_connection(self) -> bool:
        """Test connection to Ollama server"""
        try:
            if not self.ollama_api:
                return False
            
            # Try to list models (lightweight operation)
            models = await self.ollama_api.list_models()
            return models is not None
        except Exception as e:
            logger.debug(f"Connection test failed: {e}")
            return False
    
    async def discover_models(self, force: bool = False) -> List[Dict[str, Any]]:
        """
        Discover available models from Ollama server.
        
        Args:
            force: Force discovery even if recently done
            
        Returns:
            List of available models
        """
        current_time = time.time()
        
        # Skip if recently discovered (unless forced). Throttle ad-hoc callers to 1/hour.
        if not force and (current_time - self.last_model_discovery) < 3600:
            return self.available_models
        
        try:
            if not self.ollama_api:
                async with self._api_lock:
                    self.ollama_api = create_ollama_api(base_url=self.base_url)
            
            models = await self.ollama_api.list_models()
            
            if models:
                old_model_names = {m.get("name") for m in self.available_models}
                new_model_names = {m.get("name") for m in models}
                
                # Detect new models
                new_models = new_model_names - old_model_names
                if new_models:
                    logger.info(f"🆕 Discovered {len(new_models)} new Ollama models: {', '.join(new_models)}")
                    # Notify callbacks about new models
                    for callback in self.model_selection_callbacks:
                        try:
                            await callback(new_models, models)
                        except Exception as e:
                            logger.warning(f"Model selection callback failed: {e}")
                
                # Update model capabilities
                for model in models:
                    model_name = model.get("name")
                    if model_name:
                        self.model_capabilities[model_name] = {
                            "size": model.get("size"),
                            "parameter_size": model.get("details", {}).get("parameter_size"),
                            "quantization": model.get("details", {}).get("quantization_level"),
                            "family": model.get("details", {}).get("family"),
                            "modified_at": model.get("modified_at"),
                            "discovered_at": datetime.now().isoformat()
                        }
                
                self.available_models = models
                self.last_model_discovery = current_time
                
                logger.info(f"✓ Discovered {len(models)} Ollama models")
                return models
            else:
                logger.warning("No models found on Ollama server")
                return []
                
        except Exception as e:
            logger.error(f"Failed to discover models: {e}")
            # Try to reconnect
            if self.connection_retries < self.max_retries:
                self.connection_retries += 1
                logger.info(f"Attempting reconnection ({self.connection_retries}/{self.max_retries})...")
                await asyncio.sleep(2)
                return await self.discover_models(force=True)
            return []
    
    def _start_model_discovery(self):
        """Start periodic model discovery task. No task if model_discovery_interval <= 0 (manual only)."""
        if self._model_discovery_task and not self._model_discovery_task.done():
            return
        if self.model_discovery_interval <= 0:
            logger.info("Periodic model discovery disabled (interval <= 0); use manual refresh only.")
            return

        async def _discovery_loop():
            while self.connected:
                try:
                    await asyncio.sleep(self.model_discovery_interval)
                    await self.discover_models()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Model discovery loop error: {e}")

        self._model_discovery_task = asyncio.create_task(_discovery_loop())
        logger.info(f"Started periodic model discovery (interval: {self.model_discovery_interval}s)")

    async def set_model_discovery_interval(self, seconds: int) -> None:
        """Update model discovery interval and restart the periodic task (0 = manual only)."""
        self.model_discovery_interval = max(0, int(seconds))
        if self._model_discovery_task and not self._model_discovery_task.done():
            self._model_discovery_task.cancel()
            try:
                await self._model_discovery_task
            except asyncio.CancelledError:
                pass
            self._model_discovery_task = None
        if self.connected and self.model_discovery_interval > 0:
            self._start_model_discovery()
    
    async def chat(
        self,
        message: str,
        model: Optional[str] = None,
        conversation_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a chat message to Ollama model.
        
        Args:
            message: User message
            model: Model name (if None, uses best available)
            conversation_id: Conversation ID for history (if None, uses model name)
            system_prompt: Optional system prompt
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters (format, tools, etc.)
            
        Returns:
            Response dictionary with content, model, and metadata
        """
        try:
            # Ensure connection with retry logic
            if not self.connected:
                logger.info("Connection not active, attempting to initialize...")
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        connected = await self.initialize()
                        if connected:
                            logger.info("Connection restored successfully")
                            break
                        else:
                            if attempt < max_retries - 1:
                                wait_time = 2 ** attempt  # Exponential backoff
                                logger.warning(f"Connection failed, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                                await asyncio.sleep(wait_time)
                            else:
                                logger.error("Failed to establish connection after retries")
                                return {
                                    "success": False,
                                    "error": "Failed to establish Ollama connection after retries"
                                }
                    except Exception as e:
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt
                            logger.warning(f"Connection attempt {attempt + 1} failed: {e}, retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                        else:
                            logger.error(f"Connection initialization failed after {max_retries} attempts: {e}")
                            return {
                                "success": False,
                                "error": f"Connection initialization failed: {str(e)}"
                            }
            
            # Select model if not provided
            if not model:
                model = await self.select_best_model()
                if not model:
                    return {
                        "success": False,
                        "error": "No models available"
                    }
            
            # Ensure model is discovered
            await self.discover_models()
            
            # Get or create conversation history
            conv_id = conversation_id or model
            messages = self.chat_sessions[conv_id].copy()
            
            # Add system prompt if provided
            if system_prompt and not any(m.get("role") == "system" for m in messages):
                messages.insert(0, {"role": "system", "content": system_prompt})
            
            # Add user message
            messages.append({"role": "user", "content": message})
            
            # Ensure API is initialized
            if not self.ollama_api:
                async with self._api_lock:
                    self.ollama_api = create_ollama_api(base_url=self.base_url)
            
            # Send chat request
            start_time = time.time()
            response = await self.ollama_api.generate_text(
                prompt=message,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                use_chat=True,
                messages=messages,
                keep_alive=self.keep_alive,
                **kwargs
            )
            
            latency = time.time() - start_time
            
            # Parse response
            if isinstance(response, str) and response.startswith('{"error"'):
                error_data = json.loads(response)
                return {
                    "success": False,
                    "error": error_data.get("error"),
                    "message": error_data.get("message")
                }
            
            # Add assistant response to history
            assistant_message = {"role": "assistant", "content": response}
            messages.append(assistant_message)
            self.chat_sessions[conv_id] = messages
            
            # Save conversation history
            self._save_conversation_history()
            
            # Calculate tokens per second (estimate)
            response_length = len(response.split()) if isinstance(response, str) else 0
            tokens_per_second = (response_length * 1.3) / latency if latency > 0 else 0  # Rough estimate
            
            # Record feedback for model scoring (successful request)
            if self.model_scorer:
                try:
                    # Extract task type from conversation context or default to "chat"
                    task_type = kwargs.get("task_type", "chat")
                    self.model_scorer.record_feedback(
                        model_name=model,
                        task_type=task_type,
                        success=True,
                        latency_ms=latency * 1000,
                        tokens_per_second=tokens_per_second,
                        response_quality=kwargs.get("response_quality"),  # Can be provided by caller
                        code_quality=kwargs.get("code_quality"),  # Can be provided by caller
                        memory_usage_mb=kwargs.get("memory_usage_mb")
                    )
                except Exception as e:
                    logger.debug(f"Failed to record model feedback: {e}")
            
            return {
                "success": True,
                "content": response,
                "model": model,
                "conversation_id": conv_id,
                "latency": latency,
                "tokens_per_second": tokens_per_second,
                "messages_count": len(messages)
            }
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"Chat error ({error_type}): {error_msg}", exc_info=True)
            
            # Log to memory if available
            try:
                if hasattr(self, 'memory_agent') and self.memory_agent:
                    await self.memory_agent.log_process(
                        "ollama_chat_error",
                        {
                            "error_type": error_type,
                            "error_message": error_msg,
                            "model": model,
                            "conversation_id": conv_id,
                            "timestamp": time.time()
                        },
                        {"agent_id": "ollama_chat_manager", "error": True}
                    )
            except Exception as log_error:
                logger.debug(f"Failed to log error to memory: {log_error}")
            
            # Record feedback for model scoring (failed request)
            if self.model_scorer and 'model' in locals():
                try:
                    task_type = kwargs.get("task_type", "chat")
                    self.model_scorer.record_feedback(
                        model_name=model,
                        task_type=task_type,
                        success=False,
                        latency_ms=0,
                        tokens_per_second=0
                    )
                except Exception as e:
                    logger.debug(f"Failed to record model feedback: {e}")
            
            # Check if it's a connection error and mark as disconnected
            if any(keyword in error_msg.lower() for keyword in [
                'connection', 'timeout', 'refused', 'unreachable', 'network'
            ]):
                self.connected = False
                logger.warning("Marking Ollama connection as disconnected due to error")
            
            return {
                "success": False,
                "error": error_msg,
                "error_type": error_type,
                "timestamp": time.time()
            }
    
    async def select_best_model(
        self,
        task_type: str = "chat",
        preferred_models: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Select best model for a task using hierarchical scoring.
        
        Args:
            task_type: Type of task (chat, reasoning, coding, etc.)
            preferred_models: List of preferred model names (in order)
            
        Returns:
            Selected model name or None
        """
        await self.discover_models()
        
        if not self.available_models:
            return None
        
        # Use hierarchical model scorer if available
        if self.model_scorer:
            selected = self.model_scorer.select_best_model(
                available_models=self.available_models,
                task_type=task_type,
                preferred_models=preferred_models
            )
            if selected:
                return selected
        
        # Fallback to simple selection if scorer not available
        # Use preferred models if provided
        if preferred_models:
            for preferred in preferred_models:
                for model in self.available_models:
                    if model.get("name") == preferred:
                        return preferred
        
        # Task-based selection
        task_keywords = {
            "chat": ["mistral", "llama", "chat"],
            "reasoning": ["nemo", "reasoning", "thinking", "deepseek"],
            "coding": ["code", "codellama", "deepseek-coder"],
            "multimodal": ["llava", "bakllava", "vision"]
        }
        
        keywords = task_keywords.get(task_type, [])
        
        # Try to find model matching task keywords
        for model in self.available_models:
            model_name = model.get("name", "").lower()
            if any(keyword in model_name for keyword in keywords):
                # Prefer smaller models (avoid 30b+ for speed)
                if "30b" not in model_name and "70b" not in model_name:
                    return model.get("name")
        
        # Fallback to first available model
        return self.available_models[0].get("name")
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, str]]:
        """Get conversation history for a conversation ID"""
        return self.chat_sessions.get(conversation_id, [])
    
    def clear_conversation(self, conversation_id: str):
        """Clear conversation history"""
        if conversation_id in self.chat_sessions:
            del self.chat_sessions[conversation_id]
            self._save_conversation_history()
            logger.info(f"Cleared conversation: {conversation_id}")
    
    def _load_conversation_history(self):
        """Load conversation history from disk"""
        try:
            if self.conversation_history_path.exists():
                with open(self.conversation_history_path, 'r') as f:
                    data = json.load(f)
                    self.chat_sessions = defaultdict(list, data.get("sessions", {}))
                    logger.info(f"Loaded {len(self.chat_sessions)} conversation sessions")
        except Exception as e:
            logger.warning(f"Failed to load conversation history: {e}")
    
    def _save_conversation_history(self):
        """Save conversation history to disk"""
        try:
            self.conversation_history_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "sessions": dict(self.chat_sessions),
                "last_saved": datetime.now().isoformat()
            }
            with open(self.conversation_history_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save conversation history: {e}")
    
    async def _init_inference_optimizer(self):
        """Initialize inference optimizer for frequency optimization"""
        try:
            optimizer_path = Path("data/inference_optimizer_metrics.json")
            self.inference_optimizer = InferenceOptimizer(
                config=self.config,
                metrics_file=optimizer_path,
                min_frequency=1.0,
                max_frequency=120.0,
                initial_frequency=10.0,
                window_duration=300,  # 5 minutes
                optimization_interval=600  # 10 minutes
            )
            await self.inference_optimizer.start_optimization_loop()
            logger.info("Inference optimizer initialized and started")
        except Exception as e:
            logger.warning(f"Failed to initialize inference optimizer: {e}")
            self.inference_optimizer = None
    
    def register_model_selection_callback(self, callback: Callable):
        """Register callback for new model discovery"""
        self.model_selection_callbacks.append(callback)
    
    async def close(self):
        """Close connections and cleanup"""
        self.connected = False
        
        if self._model_discovery_task:
            self._model_discovery_task.cancel()
            try:
                await self._model_discovery_task
            except asyncio.CancelledError:
                pass
        
        # Stop inference optimizer
        if self.inference_optimizer:
            await self.inference_optimizer.stop_optimization_loop()
        
        if self.ollama_api and hasattr(self.ollama_api, 'http_session'):
            if self.ollama_api.http_session and not self.ollama_api.http_session.closed:
                await self.ollama_api.http_session.close()
        
        self._save_conversation_history()
        logger.info("OllamaChatManager closed")
    
    def get_optimal_frequency(self) -> float:
        """Get current optimal inference frequency"""
        if self.inference_optimizer:
            return self.inference_optimizer.get_current_frequency()
        return 10.0  # Default
    
    def get_optimization_metrics(self) -> Dict[str, Any]:
        """Get inference optimization metrics"""
        if self.inference_optimizer:
            return self.inference_optimizer.get_metrics_summary()
        return {"status": "optimizer_not_initialized"}

    async def check_health(self) -> Dict[str, Any]:
        """
        Check the health of the Ollama connection and return detailed status.
        
        Returns:
            Dictionary with health status, connection info, and metrics
        """
        health = {
            "timestamp": time.time(),
            "healthy": False,
            "connected": False,
            "base_url": str(self.base_url),
            "available_models": 0,
            "issues": [],
            "metrics": {}
        }
        
        try:
            # Check connection status
            health["connected"] = self.connected
            
            if not self.connected:
                health["issues"].append("Not connected to Ollama server")
                return health
            
            # Check available models
            if self.available_models:
                health["available_models"] = len(self.available_models)
                health["metrics"]["models"] = [m.get("name", "unknown") for m in self.available_models[:5]]
            else:
                health["issues"].append("No models available")
            
            # Test connection with a simple request
            try:
                if self.ollama_api:
                    test_models = await self.ollama_api.list_models()
                    if test_models:
                        health["healthy"] = True
                        health["metrics"]["test_successful"] = True
                    else:
                        health["issues"].append("Connection test returned no models")
                else:
                    health["issues"].append("Ollama API not initialized")
            except Exception as e:
                health["issues"].append(f"Connection test failed: {str(e)}")
                health["metrics"]["test_error"] = str(e)
            
            # Check inference optimizer if available
            if hasattr(self, 'inference_optimizer') and self.inference_optimizer:
                try:
                    opt_metrics = self.inference_optimizer.get_metrics_summary()
                    health["metrics"]["optimization"] = {
                        "enabled": True,
                        "current_frequency": opt_metrics.get("current_frequency"),
                        "total_requests": opt_metrics.get("total_requests", 0),
                        "success_rate": opt_metrics.get("recent_success_rate", 0)
                    }
                except Exception as e:
                    health["issues"].append(f"Optimizer check failed: {str(e)}")
            
        except Exception as e:
            health["issues"].append(f"Health check error: {str(e)}")
            logger.error(f"Health check error: {e}", exc_info=True)
        
        return health
