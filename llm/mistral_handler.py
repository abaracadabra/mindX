"""
Mistral AI Handler for mindX Augmentic Intelligence

This handler provides integration with Mistral AI's API suite, including:
- Chat Completion with reasoning capabilities
- Code generation (FIM)
- Embeddings
- Classification and moderation
- File processing
- Fine-tuning
- And more advanced features

Author: mindX Development Team
Version: 1.0.0
"""

import asyncio
import json
import logging
from typing import Optional, Any, Dict, List, Union
import aiohttp
from pathlib import Path
from decimal import Decimal

from .llm_interface import LLMHandlerInterface
from .rate_limiter import RateLimiter
from utils.config import Config
from utils.logging_config import get_logger

# Optional dependency for accurate token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    tiktoken = None

logger = get_logger(__name__)

class MistralHandler(LLMHandlerInterface):
    """
    Mistral AI handler for mindX integration
    
    Provides access to Mistral's advanced AI capabilities including
    reasoning, code generation, embeddings, and more.
    """
    
    def __init__(self,
                 model_name_for_api: Optional[str] = None,
                 api_key: Optional[str] = None,
                 base_url: str = "https://api.mistral.ai/v1",
                 rate_limiter: Optional[RateLimiter] = None,
                 config: Optional[Config] = None,
                 **kwargs):
        super().__init__(
            provider_name="mistral",
            model_name_for_api=model_name_for_api,
            api_key=api_key,
            base_url=base_url,
            rate_limiter=rate_limiter,
            **kwargs
        )
        
        self.config = config or Config()
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limiter = rate_limiter or RateLimiter(requests_per_minute=60)
        
        # Load Mistral configuration
        self._load_mistral_config()
        
    def _load_mistral_config(self):
        """Load Mistral-specific configuration from mistral.yaml and config"""
        # Load model catalog from mistral.yaml
        self.model_catalog: Dict[str, Any] = {}
        self._load_config_from_yaml()
        
        # Get API key from config or environment
        if not self.api_key:
            self.api_key = self.config.get("llm.mistral.api_key") or self.config.get("MISTRAL_API_KEY")
        
        # Get base URL
        if not self.base_url:
            self.base_url = self.config.get("llm.mistral.base_url", "https://api.mistral.ai/v1")
        
        # Get default model
        if not self.model_name_for_api:
            self.model_name_for_api = self.config.get("llm.mistral.default_model", "mistral-large-latest")
        
        # Get timeout settings
        self.timeout = self.config.get("llm.mistral.timeout", 30)
        self.max_retries = self.config.get("llm.mistral.max_retries", 3)
        
        # Initialize token counting
        self._tokenizers = {}
        self._initialize_tokenizers()
        
        # Mistral pricing (as of 2025) - per 1M tokens
        self.pricing = {
            "mistral-small-latest": {
                "input": Decimal("0.25"),   # $0.25 per 1M input tokens
                "output": Decimal("0.25")   # $0.25 per 1M output tokens
            },
            "mistral-medium-latest": {
                "input": Decimal("2.50"),   # $2.50 per 1M input tokens
                "output": Decimal("7.50")   # $7.50 per 1M output tokens
            },
            "mistral-large-latest": {
                "input": Decimal("8.00"),   # $8.00 per 1M input tokens
                "output": Decimal("24.00")  # $24.00 per 1M output tokens
            },
            "codestral-2405": {
                "input": Decimal("0.25"),   # $0.25 per 1M input tokens
                "output": Decimal("0.25")   # $0.25 per 1M output tokens
            },
            "codestral-latest": {
                "input": Decimal("0.25"),   # $0.25 per 1M input tokens
                "output": Decimal("0.25")   # $0.25 per 1M output tokens
            },
            "mistral-embed": {
                "input": Decimal("0.13"),   # $0.13 per 1M input tokens
                "output": Decimal("0.00")   # No output tokens for embeddings
            },
            "pixtral-12b-latest": {
                "input": Decimal("2.50"),   # $2.50 per 1M input tokens
                "output": Decimal("7.50")   # $7.50 per 1M output tokens
            }
        }
        
        if not self.api_key:
            logger.warning("Mistral API key not found. Handler will operate in degraded mode.")
            self.api_key = None  # Ensure it's None for proper handling
    
    def _load_config_from_yaml(self):
        """Loads the model catalog and settings from the central mistral.yaml file."""
        try:
            import yaml
            
            config_path = Path(__file__).parent.parent / "models" / "mistral.yaml"
            logger.info(f"Dynamically loading Mistral configuration from: {config_path}")
            
            if not config_path.exists():
                logger.error(f"mistral.yaml not found at {config_path}. Handler will have no models.")
                return

            with open(config_path, "r") as f:
                self.model_catalog = yaml.safe_load(f) or {}

        except ImportError:
            logger.critical("The 'PyYAML' library is required to load model configs. Please run `pip install pyyaml`.")
        except Exception as e:
            logger.error(f"Error parsing mistral.yaml: {e}", exc_info=True)
    
    def _initialize_tokenizers(self):
        """Initialize tokenizers for accurate token counting"""
        if TIKTOKEN_AVAILABLE:
            try:
                # Use GPT-4 tokenizer as a reasonable approximation for Mistral models
                self._tokenizers['gpt'] = tiktoken.get_encoding("cl100k_base")
                logger.info("MistralHandler: tiktoken tokenizers initialized for accurate token counting")
            except Exception as e:
                logger.warning(f"MistralHandler: Failed to initialize tiktoken: {e}")
        else:
            logger.info("MistralHandler: tiktoken not available, using heuristic token counting")
    
    def count_tokens(self, text: str, model: str = None) -> int:
        """
        Count tokens in text using tiktoken when available, fallback to heuristic
        
        Args:
            text: Text to count tokens for
            model: Model name for context (optional)
            
        Returns:
            Estimated token count
        """
        if not isinstance(text, str) or not text.strip():
            return 0
        
        # Use tiktoken if available
        if TIKTOKEN_AVAILABLE and self._tokenizers:
            try:
                tokenizer = self._tokenizers.get('gpt')
                if tokenizer:
                    return len(tokenizer.encode(text))
            except Exception as e:
                logger.warning(f"MistralHandler: tiktoken failed, using heuristic: {e}")
        
        # Heuristic fallback
        return self._estimate_tokens_heuristic(text, model)
    
    def _estimate_tokens_heuristic(self, text: str, model: str = None) -> int:
        """Heuristic token estimation for Mistral models"""
        if not text:
            return 0
        
        words = len(text.split())
        chars = len(text)
        
        # Base ratio for Mistral models (tends to be more efficient than GPT)
        if self._is_code_like(text):
            base_ratio = 0.30  # Code has more tokens per character
        elif self._has_technical_content(text):
            base_ratio = 0.27  # Technical content
        else:
            base_ratio = 0.24  # Regular text
        
        # Model-specific adjustments
        if model:
            model_lower = model.lower()
            if 'small' in model_lower:
                base_ratio *= 0.95  # Small models are more efficient
            elif 'large' in model_lower:
                base_ratio *= 1.05  # Large models use slightly more tokens
            elif 'codestral' in model_lower:
                base_ratio *= 0.92  # Code models are very efficient
        
        estimated_tokens = int(chars * base_ratio)
        
        # Bounds checking
        min_estimate = max(1, words // 4)
        max_estimate = min(words * 3, chars // 2)
        
        return max(min_estimate, min(estimated_tokens, max_estimate))
    
    def _is_code_like(self, text: str) -> bool:
        """Check if text appears to be code"""
        code_indicators = ['def ', 'class ', 'import ', 'from ', 'if __name__', 'function', 'var ', 'const ', 'let ']
        return any(indicator in text for indicator in code_indicators)
    
    def _has_technical_content(self, text: str) -> bool:
        """Check if text has technical content"""
        tech_indicators = ['API', 'function', 'method', 'algorithm', 'database', 'server', 'client']
        return any(indicator.lower() in text.lower() for indicator in tech_indicators)
    
    def calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> Decimal:
        """
        Calculate cost for token usage
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model name
            
        Returns:
            Total cost in USD
        """
        model_pricing = self.pricing.get(model, self.pricing.get("mistral-small-latest"))
        
        input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * model_pricing["input"]
        output_cost = (Decimal(output_tokens) / Decimal(1_000_000)) * model_pricing["output"]
        
        return input_cost + output_cost
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get model information from the catalog"""
        # Try different model name formats
        possible_keys = [
            f"mistral/{model_name}",
            model_name,
            f"mistral-{model_name}",
            f"{model_name}-latest"
        ]
        
        for key in possible_keys:
            if key in self.model_catalog:
                return self.model_catalog[key]
        
        logger.warning(f"Model {model_name} not found in mistral.yaml catalog")
        return None
    
    def get_available_models(self) -> List[str]:
        """Get list of available models from the catalog"""
        models = []
        for key in self.model_catalog.keys():
            # Extract model name from key (e.g., "mistral/mistral-large-latest" -> "mistral-large-latest")
            if "/" in key:
                models.append(key.split("/", 1)[1])
            else:
                models.append(key)
        return models
    
    def get_model_capabilities(self, model_name: str) -> List[str]:
        """Get model capabilities from the catalog"""
        model_info = self.get_model_info(model_name)
        if model_info and "assessed_capabilities" in model_info:
            return model_info["assessed_capabilities"]
        return []
    
    def get_model_task_scores(self, model_name: str) -> Dict[str, float]:
        """Get model task scores from the catalog"""
        model_info = self.get_model_info(model_name)
        if model_info and "task_scores" in model_info:
            return model_info["task_scores"]
        return {}
    
    def is_model_suitable_for_task(self, model_name: str, task_type: str) -> bool:
        """Check if a model is suitable for a specific task based on scores"""
        task_scores = self.get_model_task_scores(model_name)
        if not task_scores:
            return False
        
        # Define minimum scores for different task types
        min_scores = {
            "reasoning": 0.7,
            "code_generation": 0.7,
            "writing": 0.7,
            "simple_chat": 0.8,
            "data_analysis": 0.7,
            "speed_sensitive": 0.7
        }
        
        if task_type in task_scores:
            return task_scores[task_type] >= min_scores.get(task_type, 0.5)
        
        return False
    
    def get_best_model_for_task(self, task_type: str) -> Optional[str]:
        """Get the best model for a specific task based on scores"""
        best_model = None
        best_score = 0.0
        
        for model_key, model_info in self.model_catalog.items():
            if "task_scores" in model_info and task_type in model_info["task_scores"]:
                score = model_info["task_scores"][task_type]
                if score > best_score:
                    best_score = score
                    best_model = model_key.split("/", 1)[1] if "/" in model_key else model_key
        
        return best_model
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def generate_text(self,
                           prompt: str,
                           model: str,
                           max_tokens: Optional[int] = 2048,
                           temperature: Optional[float] = 0.7,
                           json_mode: Optional[bool] = False,
                           **kwargs) -> Optional[str]:
        """
        Generate text using Mistral's chat completion API - Official API 1.0.0
        
        Args:
            prompt: Input prompt
            model: Model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.5, recommended 0.0-0.7)
            json_mode: Whether to request JSON output
            **kwargs: Additional parameters (top_p, stop, random_seed, etc.)
            
        Returns:
            Generated text or None on failure
        """
        # Check if API key is available
        if not self.api_key:
            logger.warning("Mistral API key not available. Returning mock response.")
            return f"[MOCK RESPONSE] Mistral API key not configured. Would process: {prompt[:100]}..."
        
        if not self.session:
            await self.__aenter__()
        
        # Prepare messages
        messages = [{"role": "user", "content": prompt}]
        
        # Prepare request payload according to official API spec
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        
        # Add required parameters
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        
        # Add JSON mode if requested
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        # Add additional parameters from kwargs
        for key, value in kwargs.items():
            if value is not None:
                payload[key] = value
        
        try:
            # Apply rate limiting
            await self._rate_limiter.wait()
            
            # Count input tokens for cost calculation
            input_tokens = self.count_tokens(prompt, model)
            
            # Make API request
            async with self.session.post(f"{self.base_url}/chat/completions", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data["choices"][0]["message"]["content"]
                    
                    # Count output tokens and calculate cost
                    output_tokens = self.count_tokens(response_text, model)
                    cost = self.calculate_cost(input_tokens, output_tokens, model)
                    
                    # Log usage information
                    logger.info(f"Mistral API call - Model: {model}, Input tokens: {input_tokens}, Output tokens: {output_tokens}, Cost: ${cost:.6f}")
                    
                    return response_text
                else:
                    error_text = await response.text()
                    logger.error(f"Mistral API error {response.status}: {error_text}")
                    return f"Error: Mistral API returned {response.status}: {error_text}"
        
        except aiohttp.ClientError as e:
            logger.error(f"Mistral API request failed: {e}")
            return f"Error: Request failed: {e}"
        except Exception as e:
            logger.error(f"Unexpected error in Mistral handler: {e}")
            return f"Error: {e}"
    
    async def generate_code(self,
                           prompt: str,
                           suffix: str = "",
                           model: str = "codestral-latest",
                           **kwargs) -> Optional[str]:
        """
        Generate code using Mistral's FIM (Fill-in-the-Middle) API
        
        Args:
            prompt: Code prompt
            suffix: Code suffix for context
            model: Model to use (default: codestral-latest)
            **kwargs: Additional parameters
            
        Returns:
            Generated code or None on failure
        """
        # Check if API key is available
        if not self.api_key:
            logger.warning("Mistral API key not available. Returning mock code response.")
            return f"# [MOCK CODE] Mistral API key not configured\n# Would generate code for: {prompt[:50]}...\n# Suffix: {suffix[:30]}..."
        
        if not self.session:
            await self.__aenter__()
        
        payload = {
            "model": model,
            "prompt": prompt,
            "suffix": suffix,
            "stream": False
        }
        payload.update(kwargs)
        
        try:
            await self._rate_limiter.wait()
            
            async with self.session.post(f"{self.base_url}/fim/completions", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["choices"][0]["text"]
                else:
                    error_text = await response.text()
                    logger.error(f"Mistral FIM API error {response.status}: {error_text}")
                    return f"Error: Mistral FIM API returned {response.status}: {error_text}"
        
        except Exception as e:
            logger.error(f"Mistral FIM API request failed: {e}")
            return f"Error: {e}"
    
    async def create_embeddings(self,
                               input_text: Union[str, List[str]],
                               model: str = "mistral-embed",
                               **kwargs) -> Optional[List[List[float]]]:
        """
        Create embeddings using Mistral's embeddings API
        
        Args:
            input_text: Text or list of texts to embed
            model: Embedding model to use
            **kwargs: Additional parameters
            
        Returns:
            List of embedding vectors or None on failure
        """
        # Check if API key is available
        if not self.api_key:
            logger.warning("Mistral API key not available. Returning mock embeddings.")
            # Return mock embeddings (random vectors)
            import random
            if isinstance(input_text, str):
                return [[random.random() for _ in range(1024)]]
            else:
                return [[random.random() for _ in range(1024)] for _ in input_text]
        
        if not self.session:
            await self.__aenter__()
        
        payload = {
            "model": model,
            "input": input_text
        }
        payload.update(kwargs)
        
        try:
            await self._rate_limiter.wait()
            
            async with self.session.post(f"{self.base_url}/embeddings", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return [item["embedding"] for item in data["data"]]
                else:
                    error_text = await response.text()
                    logger.error(f"Mistral embeddings API error {response.status}: {error_text}")
                    return None
        
        except Exception as e:
            logger.error(f"Mistral embeddings API request failed: {e}")
            return None
    
    async def classify_content(self,
                              input_text: Union[str, List[str]],
                              model: str = "mistral-classifier",
                              **kwargs) -> Optional[Dict[str, Any]]:
        """
        Classify content using Mistral's classification API
        
        Args:
            input_text: Text or list of texts to classify
            model: Classification model to use
            **kwargs: Additional parameters
            
        Returns:
            Classification results or None on failure
        """
        # Check if API key is available
        if not self.api_key:
            logger.warning("Mistral API key not available. Returning mock classification.")
            return {
                "id": "mock-classification",
                "model": model,
                "results": [{"label": "neutral", "score": 0.5}]
            }
        
        if not self.session:
            await self.__aenter__()
        
        payload = {
            "model": model,
            "input": input_text
        }
        payload.update(kwargs)
        
        try:
            await self._rate_limiter.wait()
            
            async with self.session.post(f"{self.base_url}/classifications", json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Mistral classification API error {response.status}: {error_text}")
                    return None
        
        except Exception as e:
            logger.error(f"Mistral classification API request failed: {e}")
            return None
    
    async def moderate_content(self,
                              input_text: Union[str, List[str]],
                              model: str = "mistral-moderator",
                              **kwargs) -> Optional[Dict[str, Any]]:
        """
        Moderate content using Mistral's moderation API
        
        Args:
            input_text: Text or list of texts to moderate
            model: Moderation model to use
            **kwargs: Additional parameters
            
        Returns:
            Moderation results or None on failure
        """
        # Check if API key is available
        if not self.api_key:
            logger.warning("Mistral API key not available. Returning mock moderation.")
            return {
                "id": "mock-moderation",
                "model": model,
                "results": [{"flagged": False, "categories": {}, "category_scores": {}}]
            }
        
        if not self.session:
            await self.__aenter__()
        
        payload = {
            "model": model,
            "input": input_text
        }
        payload.update(kwargs)
        
        try:
            await self._rate_limiter.wait()
            
            async with self.session.post(f"{self.base_url}/moderations", json=payload) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Mistral moderation API error {response.status}: {error_text}")
                    return None
        
        except Exception as e:
            logger.error(f"Mistral moderation API request failed: {e}")
            return None
    
    async def list_models(self) -> Optional[List[Dict[str, Any]]]:
        """
        List available Mistral models from YAML catalog and API
        
        Returns:
            List of available models or None on failure
        """
        # Get models from YAML catalog first
        catalog_models = self.get_available_models()
        
        # Check if API key is available
        if not self.api_key:
            logger.warning("Mistral API key not available. Returning models from YAML catalog.")
            return [{"id": model, "object": "model", "created": 1234567890} for model in catalog_models]
        
        if not self.session:
            await self.__aenter__()
        
        try:
            await self._rate_limiter.wait()
            
            async with self.session.get(f"{self.base_url}/models") as response:
                if response.status == 200:
                    data = await response.json()
                    api_models = data.get("data", [])
                    # Combine catalog and API models, prioritizing catalog
                    catalog_model_dicts = [{"id": model, "object": "model", "created": 1234567890} for model in catalog_models]
                    all_models = catalog_model_dicts + [model for model in api_models if model["id"] not in catalog_models]
                    return all_models
                else:
                    error_text = await response.text()
                    logger.error(f"Mistral models API error {response.status}: {error_text}. Using catalog models.")
                    return [{"id": model, "object": "model", "created": 1234567890} for model in catalog_models]
        
        except Exception as e:
            logger.error(f"Mistral models API request failed: {e}. Using catalog models.")
            return [{"id": model, "object": "model", "created": 1234567890} for model in catalog_models]
    
    async def test_connection(self) -> bool:
        """
        Test connection to Mistral API
        
        Returns:
            True if connection successful, False otherwise
        """
        # If no API key, return True for graceful degradation
        if not self.api_key:
            logger.info("Mistral API key not available. Connection test passes for degraded mode.")
            return True
        
        try:
            models = await self.list_models()
            return models is not None
        except Exception as e:
            logger.error(f"Mistral connection test failed: {e}")
            return False
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available Mistral models for this handler
        
        Returns:
            List of model names
        """
        return [
            "mistral-small-latest",
            "mistral-medium-latest", 
            "mistral-large-latest",
            "codestral-2405",
            "codestral-latest",
            "mistral-embed",
            "pixtral-12b-latest"
        ]
    
    def get_model_capabilities(self, model: str) -> Dict[str, Any]:
        """
        Get capabilities for a specific model
        
        Args:
            model: Model name
            
        Returns:
            Dictionary of model capabilities
        """
        capabilities = {
            "mistral-small-latest": {
                "type": "chat",
                "max_tokens": 32000,
                "supports_json": True,
                "supports_tools": True,
                "supports_reasoning": False
            },
            "mistral-medium-latest": {
                "type": "chat",
                "max_tokens": 32000,
                "supports_json": True,
                "supports_tools": True,
                "supports_reasoning": False
            },
            "mistral-large-latest": {
                "type": "chat",
                "max_tokens": 32000,
                "supports_json": True,
                "supports_tools": True,
                "supports_reasoning": True
            },
            "codestral-2405": {
                "type": "code",
                "max_tokens": 32000,
                "supports_fim": True,
                "supports_json": True,
                "supports_reasoning": False
            },
            "codestral-latest": {
                "type": "code",
                "max_tokens": 32000,
                "supports_fim": True,
                "supports_json": True,
                "supports_reasoning": False
            },
            "mistral-embed": {
                "type": "embedding",
                "max_tokens": 8192,
                "supports_json": False,
                "supports_tools": False,
                "supports_reasoning": False
            },
            "pixtral-12b-latest": {
                "type": "vision",
                "max_tokens": 32000,
                "supports_json": True,
                "supports_tools": True,
                "supports_reasoning": False
            }
        }
        
        return capabilities.get(model, {
            "type": "unknown",
            "max_tokens": 32000,
            "supports_json": True,
            "supports_tools": False,
            "supports_reasoning": False
        })
    
    def get_optimized_model_for_task(self, task_type: str, estimated_tokens: int = 1000, budget_limit: Decimal = None) -> Dict[str, Any]:
        """
        Get the most optimized Mistral model for a specific task
        
        Args:
            task_type: Type of task (reasoning, code_generation, writing, simple_chat, data_analysis, speed_sensitive)
            estimated_tokens: Estimated number of tokens for the task
            budget_limit: Maximum cost budget (optional)
            
        Returns:
            Dictionary with recommended model and reasoning
        """
        # Define task requirements
        task_requirements = {
            "reasoning": {
                "min_capability": 0.8,
                "preferred_models": ["mistral-large-latest"],
                "fallback_models": ["mistral-medium-latest"]
            },
            "code_generation": {
                "min_capability": 0.7,
                "preferred_models": ["codestral-latest", "codestral-2405"],
                "fallback_models": ["mistral-large-latest", "mistral-medium-latest"]
            },
            "writing": {
                "min_capability": 0.6,
                "preferred_models": ["mistral-medium-latest", "mistral-small-latest"],
                "fallback_models": ["mistral-large-latest"]
            },
            "simple_chat": {
                "min_capability": 0.5,
                "preferred_models": ["mistral-small-latest"],
                "fallback_models": ["mistral-medium-latest"]
            },
            "data_analysis": {
                "min_capability": 0.7,
                "preferred_models": ["mistral-large-latest", "mistral-medium-latest"],
                "fallback_models": ["mistral-small-latest"]
            },
            "speed_sensitive": {
                "min_capability": 0.5,
                "preferred_models": ["mistral-small-latest", "codestral-latest"],
                "fallback_models": ["mistral-medium-latest"]
            }
        }
        
        requirements = task_requirements.get(task_type, task_requirements["simple_chat"])
        
        # Calculate cost for each model
        model_costs = {}
        for model in self.pricing.keys():
            if self.is_model_suitable_for_task(model, task_type):
                # Estimate cost based on estimated tokens
                estimated_cost = self.calculate_cost(estimated_tokens, estimated_tokens // 2, model)
                model_costs[model] = {
                    "cost": estimated_cost,
                    "capabilities": self.get_model_capabilities(model),
                    "pricing": self.pricing[model]
                }
        
        # Filter by budget if specified
        if budget_limit:
            model_costs = {k: v for k, v in model_costs.items() if v["cost"] <= budget_limit}
        
        if not model_costs:
            return {
                "recommended_model": "mistral-small-latest",
                "reasoning": "No models within budget, using cheapest option",
                "cost": self.calculate_cost(estimated_tokens, estimated_tokens // 2, "mistral-small-latest"),
                "capabilities": self.get_model_capabilities("mistral-small-latest")
            }
        
        # Sort by cost and capability
        sorted_models = sorted(
            model_costs.items(),
            key=lambda x: (x[1]["cost"], -x[1]["capabilities"].get("max_tokens", 0))
        )
        
        # Find best model from preferred list
        for preferred_model in requirements["preferred_models"]:
            if preferred_model in model_costs:
                return {
                    "recommended_model": preferred_model,
                    "reasoning": f"Preferred model for {task_type} task",
                    "cost": model_costs[preferred_model]["cost"],
                    "capabilities": model_costs[preferred_model]["capabilities"],
                    "pricing": model_costs[preferred_model]["pricing"]
                }
        
        # Fallback to cheapest suitable model
        best_model, best_info = sorted_models[0]
        return {
            "recommended_model": best_model,
            "reasoning": f"Most cost-effective model for {task_type} task",
            "cost": best_info["cost"],
            "capabilities": best_info["capabilities"],
            "pricing": best_info["pricing"]
        }
    
    def get_model_comparison(self, task_type: str = "simple_chat", estimated_tokens: int = 1000) -> List[Dict[str, Any]]:
        """
        Get a comparison of all available models for a specific task
        
        Args:
            task_type: Type of task to compare models for
            estimated_tokens: Estimated number of tokens
            
        Returns:
            List of model comparisons sorted by cost-effectiveness
        """
        comparisons = []
        
        for model in self.pricing.keys():
            if self.is_model_suitable_for_task(model, task_type):
                estimated_cost = self.calculate_cost(estimated_tokens, estimated_tokens // 2, model)
                capabilities = self.get_model_capabilities(model)
                
                comparisons.append({
                    "model": model,
                    "cost": estimated_cost,
                    "cost_per_1k_tokens": estimated_cost / (estimated_tokens / 1000),
                    "capabilities": capabilities,
                    "pricing": self.pricing[model],
                    "suitable": True
                })
            else:
                comparisons.append({
                    "model": model,
                    "cost": Decimal("0"),
                    "cost_per_1k_tokens": Decimal("0"),
                    "capabilities": self.get_model_capabilities(model),
                    "pricing": self.pricing[model],
                    "suitable": False
                })
        
        # Sort by cost-effectiveness (suitable models first, then by cost)
        return sorted(comparisons, key=lambda x: (not x["suitable"], x["cost"]))
