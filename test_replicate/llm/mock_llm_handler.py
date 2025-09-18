# mindx/llm/mock_llm_handler.py
import asyncio
from typing import Optional, Any
import json
from .llm_interface import LLMHandlerInterface
from utils.logging_config import get_logger

logger = get_logger(__name__)

class MockLLMHandler(LLMHandlerInterface):
    """A mock LLM handler for testing and fallback purposes."""
    
    # FIXED: The constructor is now flexible and calls super() correctly.
    def __init__(self, **kwargs: Any):
        # Determine the model name from possible arguments passed in kwargs.
        model_name = kwargs.get("model_name", kwargs.get("model_name_for_api", "mock_generic_model"))
        
        # Extract only the arguments that the parent LLMHandlerInterface expects.
        # This prevents passing unexpected arguments like 'model_name'.
        parent_args = {
            "provider_name": "mock",
            "model_name_for_api": model_name,
            "api_key": kwargs.get("api_key"),
            "base_url": kwargs.get("base_url"),
            "rate_limiter": kwargs.get("rate_limiter")
        }
        
        # Call the parent __init__ with the clean, expected set of arguments.
        super().__init__(**parent_args)
        
        self.call_count = 0
        logger.info(f"MockLLMHandler initialized for model '{self.model_name_for_api}'. This handler returns predefined responses.")

    async def generate_text(
        self,
        prompt: str,
        model: str,
        max_tokens: Optional[int] = 2048,
        temperature: Optional[float] = 0.7,
        json_mode: Optional[bool] = False,
        **kwargs: Any
    ) -> Optional[str]:
        self.call_count += 1
        await asyncio.sleep(0.01)
        
        effective_model_name = self.model_name_for_api or model
        logger.debug(f"MockLLM Call #{self.call_count}: Model='{effective_model_name}', JSON={json_mode}, Prompt(start): {prompt[:150]}...")

        if json_mode:
            return json.dumps({ 
                "mock_response": "This is a JSON object.", 
                "prompt_received": prompt[:50].replace('"',"'") + "..." 
            })
        
        return f"Mock response for model '{model}' (Handler default: '{self.model_name_for_api}'). Call #{self.call_count}. Prompt: '{prompt[:100]}...'"
