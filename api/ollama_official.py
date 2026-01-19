"""
Official Ollama Python Library Adapter for mindX

This module provides an adapter to use the official ollama-python library
(https://github.com/ollama/ollama-python) as an alternative to the custom implementation.

The official library provides:
- Better compatibility with Ollama API updates
- Official support and maintenance
- AsyncClient for async operations
- Streaming support
- Cloud model support

Usage:
    from api.ollama_official import create_ollama_client
    
    # Use official library if available, fallback to custom implementation
    client = create_ollama_client(base_url="http://localhost:11434")
"""

import logging
from typing import Optional, Dict, List, Any, AsyncGenerator
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Try to import official ollama library
try:
    from ollama import AsyncClient, Client
    from ollama import ResponseError
    OLLAMA_OFFICIAL_AVAILABLE = True
    logger.info("Official ollama-python library is available")
except ImportError:
    OLLAMA_OFFICIAL_AVAILABLE = False
    logger.info("Official ollama-python library not available, using custom implementation")


class OfficialOllamaAdapter:
    """
    Adapter for the official ollama-python library.
    Provides a compatible interface with our custom OllamaAPI.
    """
    
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the official Ollama client adapter.
        
        Args:
            base_url: Ollama server base URL (e.g., "http://localhost:11434")
            api_key: API key for Ollama Cloud (optional)
        """
        if not OLLAMA_OFFICIAL_AVAILABLE:
            raise ImportError("Official ollama-python library not installed. Install with: pip install ollama")
        
        # Clean base_url (remove /api suffix if present)
        if base_url:
            base_url = base_url.rstrip('/')
            if base_url.endswith('/api'):
                base_url = base_url[:-4]
        else:
            # Try to get from settings
            try:
                from webmind.settings import SettingsManager
                settings = SettingsManager()
                base_url = settings.get('ollama_base_url', 'http://localhost:11434')
            except:
                base_url = 'http://localhost:11434'
        
        self.base_url = base_url
        
        # Create async client
        headers = {}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        
        self.async_client = AsyncClient(host=base_url, headers=headers if headers else None)
        self.sync_client = Client(host=base_url, headers=headers if headers else None)
        
        logger.info(f"Official Ollama adapter initialized for {base_url}")
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List all available models from Ollama server"""
        try:
            response = await self.async_client.list()
            models = []
            for model in response.get('models', []):
                models.append({
                    'name': model.get('name', ''),
                    'size': model.get('size', 0),
                    'digest': model.get('digest', ''),
                    'modified_at': model.get('modified_at', ''),
                    'details': model.get('details', {})
                })
            return models
        except Exception as e:
            logger.error(f"Error listing models with official library: {e}")
            return []
    
    async def generate_text(
        self,
        prompt: str,
        model: str = "llama3:8b",
        max_tokens: Optional[int] = 2048,
        temperature: Optional[float] = 0.7,
        use_chat: bool = False,
        messages: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Generate text using Ollama.
        
        Args:
            prompt: Text prompt
            model: Model name
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            use_chat: Use chat endpoint instead of generate
            messages: Conversation messages (for chat endpoint)
            **kwargs: Additional parameters
        
        Returns:
            Generated text or None on error
        """
        try:
            if use_chat and messages:
                # Use chat endpoint
                response = await self.async_client.chat(
                    model=model,
                    messages=messages,
                    options={
                        'num_predict': max_tokens,
                        'temperature': temperature,
                        **kwargs.get('options', {})
                    },
                    stream=False
                )
                # Handle both object and dict formats
                if hasattr(response, 'message'):
                    return response.message.content if hasattr(response.message, 'content') else str(response.message)
                return response.get('message', {}).get('content', '')
            else:
                # Use generate endpoint
                response = await self.async_client.generate(
                    model=model,
                    prompt=prompt,
                    options={
                        'num_predict': max_tokens,
                        'temperature': temperature,
                        **kwargs.get('options', {})
                    },
                    stream=False
                )
                # Handle both object and dict formats
                if hasattr(response, 'response'):
                    return response.response
                return response.get('response', '')
        except ResponseError as e:
            logger.error(f"Ollama API error: {e.error if hasattr(e, 'error') else str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error generating text with official library: {e}")
            return None
    
    async def chat_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat responses.
        
        Args:
            model: Model name
            messages: Conversation messages
            **kwargs: Additional parameters
        
        Yields:
            Response chunks
        """
        try:
            async for chunk in await self.async_client.chat(
                model=model,
                messages=messages,
                stream=True,
                **kwargs
            ):
                yield {
                    'message': chunk.get('message', {}).get('content', ''),
                    'done': chunk.get('done', False)
                }
        except Exception as e:
            logger.error(f"Error streaming chat with official library: {e}")
            yield {'error': str(e), 'done': True}


def create_ollama_client(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    use_official: Optional[bool] = None
) -> Any:
    """
    Create an Ollama client, preferring the official library if available.
    
    Args:
        base_url: Ollama server base URL
        api_key: API key for Ollama Cloud
        use_official: Force use of official library (None = auto-detect)
    
    Returns:
        OfficialOllamaAdapter if official library available, otherwise None
    """
    if use_official is False:
        return None
    
    if use_official is True and not OLLAMA_OFFICIAL_AVAILABLE:
        logger.warning("Official ollama library requested but not available")
        return None
    
    if OLLAMA_OFFICIAL_AVAILABLE:
        try:
            return OfficialOllamaAdapter(base_url=base_url, api_key=api_key)
        except Exception as e:
            logger.warning(f"Failed to create official Ollama client: {e}")
            return None
    
    return None
