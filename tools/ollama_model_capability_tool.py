# mindx/tools/ollama_model_capability_tool.py
"""
Ollama Model Capability Tool: Stores and manages Ollama model capabilities for task-specific selection.

This tool maintains a registry of Ollama models with their capabilities, performance metrics,
and task-specific suitability scores. It enables mindX to intelligently select the best
Ollama model for each task.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict, field
from datetime import datetime

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from api.ollama_url import create_ollama_api, OllamaAPI

logger = get_logger(__name__)


@dataclass
class ModelCapability:
    """Capability profile for an Ollama model"""
    model_name: str
    size_gb: float = 0.0
    context_size: int = 0
    capabilities: List[str] = field(default_factory=list)  # e.g., ["code", "reasoning", "chat"]
    task_scores: Dict[str, float] = field(default_factory=dict)  # Task type -> score (0-1)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    last_tested: Optional[str] = None
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OllamaModelCapabilityTool:
    """
    Tool for managing Ollama model capabilities and enabling intelligent model selection.
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.log_prefix = "OllamaModelCapabilityTool:"
        
        # Storage path
        self.capabilities_file = PROJECT_ROOT / "data" / "config" / "ollama_model_capabilities.json"
        self.capabilities_file.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache
        self.model_capabilities: Dict[str, ModelCapability] = {}
        
        # Load existing capabilities
        self._load_capabilities()
        
        logger.info(f"{self.log_prefix} Initialized. {len(self.model_capabilities)} models registered.")
    
    def _load_capabilities(self):
        """Load model capabilities from file"""
        try:
            if self.capabilities_file.exists():
                with open(self.capabilities_file, 'r') as f:
                    data = json.load(f)
                    for model_name, cap_data in data.items():
                        self.model_capabilities[model_name] = ModelCapability(**cap_data)
                logger.info(f"{self.log_prefix} Loaded {len(self.model_capabilities)} model capabilities")
        except Exception as e:
            logger.warning(f"{self.log_prefix} Failed to load capabilities: {e}")
            self.model_capabilities = {}
    
    def _save_capabilities(self):
        """Save model capabilities to file"""
        try:
            data = {
                model_name: cap.to_dict()
                for model_name, cap in self.model_capabilities.items()
            }
            with open(self.capabilities_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"{self.log_prefix} Saved {len(self.model_capabilities)} model capabilities")
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to save capabilities: {e}")
    
    async def discover_models(self, base_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Discover available Ollama models and their basic information.
        
        Args:
            base_url: Ollama server base URL (uses config if not provided)
            
        Returns:
            List of model information dictionaries
        """
        try:
            if base_url:
                ollama_api = create_ollama_api(base_url=base_url)
            else:
                # Get from config
                env_base_url = self.config.get("llm.ollama.base_url")
                if env_base_url:
                    ollama_api = create_ollama_api(base_url=env_base_url)
                else:
                    ollama_api = create_ollama_api()
            
            models = await ollama_api.list_models()
            
            logger.info(f"{self.log_prefix} Discovered {len(models)} models from Ollama")
            return models
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to discover models: {e}")
            return []
    
    async def register_model(
        self,
        model_name: str,
        capabilities: Optional[List[str]] = None,
        task_scores: Optional[Dict[str, float]] = None,
        size_gb: Optional[float] = None,
        context_size: Optional[int] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Register or update a model's capabilities.
        
        Args:
            model_name: Name of the Ollama model
            capabilities: List of capability tags (e.g., ["code", "reasoning", "chat"])
            task_scores: Dictionary mapping task types to suitability scores (0-1)
            size_gb: Model size in GB
            context_size: Context window size
            notes: Additional notes about the model
            
        Returns:
            True if successful
        """
        try:
            # Get or create capability record
            if model_name in self.model_capabilities:
                cap = self.model_capabilities[model_name]
            else:
                cap = ModelCapability(model_name=model_name)
            
            # Update fields
            if capabilities is not None:
                cap.capabilities = capabilities
            if task_scores is not None:
                cap.task_scores.update(task_scores)
            if size_gb is not None:
                cap.size_gb = size_gb
            if context_size is not None:
                cap.context_size = context_size
            if notes is not None:
                cap.notes = notes
            
            cap.last_tested = datetime.now().isoformat()
            
            self.model_capabilities[model_name] = cap
            self._save_capabilities()
            
            logger.info(f"{self.log_prefix} Registered capabilities for {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to register model: {e}")
            return False
    
    async def auto_discover_and_register(
        self,
        base_url: Optional[str] = None,
        auto_score: bool = True
    ) -> Dict[str, Any]:
        """
        Automatically discover models and register their capabilities with intelligent scoring.
        
        Args:
            base_url: Ollama server base URL
            auto_score: Whether to automatically assign task scores based on model name/type
            
        Returns:
            Dictionary with discovery results
        """
        try:
            models = await self.discover_models(base_url)
            
            registered = 0
            updated = 0
            
            for model in models:
                model_name = model.get("name", "")
                if not model_name:
                    continue
                
                size_gb = model.get("size", 0) / (1024**3) if model.get("size") else 0
                
                # Auto-detect capabilities from model name
                capabilities = []
                task_scores = {}
                
                model_lower = model_name.lower()
                
                # Code generation models
                if any(x in model_lower for x in ["code", "coder", "codellama", "deepseek-coder", "starcoder"]):
                    capabilities.append("code")
                    task_scores["code_generation"] = 0.9
                    task_scores["debugging"] = 0.85
                
                # Reasoning models
                if any(x in model_lower for x in ["reason", "reasoning", "phi", "mistral", "llama"]):
                    capabilities.append("reasoning")
                    task_scores["reasoning"] = 0.8
                    task_scores["analysis"] = 0.75
                
                # Chat models
                if any(x in model_lower for x in ["chat", "instruct", "nemo", "gemma"]):
                    capabilities.append("chat")
                    task_scores["simple_chat"] = 0.9
                    task_scores["conversation"] = 0.85
                
                # Writing models
                if any(x in model_lower for x in ["write", "writing", "text"]):
                    capabilities.append("writing")
                    task_scores["writing"] = 0.9
                
                # Default capabilities if none detected
                if not capabilities:
                    capabilities = ["general"]
                    task_scores["simple_chat"] = 0.7
                    task_scores["reasoning"] = 0.6
                
                # Check if already registered
                was_new = model_name not in self.model_capabilities
                
                await self.register_model(
                    model_name=model_name,
                    capabilities=capabilities,
                    task_scores=task_scores if auto_score else None,
                    size_gb=size_gb
                )
                
                if was_new:
                    registered += 1
                else:
                    updated += 1
            
            result = {
                "success": True,
                "models_discovered": len(models),
                "registered": registered,
                "updated": updated
            }
            
            logger.info(f"{self.log_prefix} Auto-discovery complete: {registered} new, {updated} updated")
            return result
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Auto-discovery failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_best_model_for_task(
        self,
        task_type: str,
        min_score: float = 0.5
    ) -> Optional[str]:
        """
        Get the best model for a specific task type.
        
        Args:
            task_type: Type of task (e.g., "code_generation", "reasoning", "simple_chat")
            min_score: Minimum score threshold
            
        Returns:
            Model name or None if no suitable model found
        """
        best_model = None
        best_score = min_score
        
        for model_name, cap in self.model_capabilities.items():
            score = cap.task_scores.get(task_type, 0.0)
            if score > best_score:
                best_score = score
                best_model = model_name
        
        if best_model:
            logger.debug(f"{self.log_prefix} Selected {best_model} for task {task_type} (score: {best_score:.2f})")
        
        return best_model
    
    def get_all_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered model capabilities"""
        return {
            model_name: cap.to_dict()
            for model_name, cap in self.model_capabilities.items()
        }
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get capability information for a specific model"""
        if model_name in self.model_capabilities:
            return self.model_capabilities[model_name].to_dict()
        return None
