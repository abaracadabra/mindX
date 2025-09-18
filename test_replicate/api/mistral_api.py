"""
Mistral AI API Integration for mindX Augmentic Intelligence
==========================================================

This module provides comprehensive integration with Mistral AI's API suite,
enabling mindX agents to leverage advanced AI capabilities including:
- Chat Completion & Reasoning
- Code Generation (FIM)
- Agent Management
- Embeddings & Vector Search
- Content Classification & Moderation
- File Management & Processing
- Fine-tuning & Model Management
- Batch Processing
- OCR & Document Analysis
- Audio Transcription
- Conversation Management
- Knowledge Libraries

Author: mindX Development Team
Version: 1.0.0
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Union, Any, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import aiohttp
import base64
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class MistralModel(Enum):
    """Available Mistral AI models"""
    # Chat Models
    MISTRAL_SMALL_LATEST = "mistral-small-latest"
    MISTRAL_MEDIUM_LATEST = "mistral-medium-latest"
    MISTRAL_LARGE_LATEST = "mistral-large-latest"
    
    # Code Models
    CODESTRAL_2405 = "codestral-2405"
    CODESTRAL_LATEST = "codestral-latest"
    
    # Embedding Models
    MISTRAL_EMBED = "mistral-embed"
    
    # Vision Models
    PIXTRAL_12B_LATEST = "pixtral-12b-latest"
    
    # Fine-tunable Models
    MINISTRAL_3B_LATEST = "ministral-3b-latest"
    MINISTRAL_8B_LATEST = "ministral-8b-latest"
    OPEN_MISTRAL_7B = "open-mistral-7b"
    OPEN_MISTRAL_NEMO = "open-mistral-nemo"

class MistralPromptMode(Enum):
    """Prompt modes for Mistral models"""
    REASONING = "reasoning"
    STANDARD = "standard"

@dataclass
class MistralConfig:
    """Configuration for Mistral AI API"""
    api_key: str
    base_url: str = "https://api.mistral.ai/v1"
    timeout: int = 30
    max_retries: int = 3
    rate_limit_delay: float = 0.1

@dataclass
class ChatMessage:
    """Chat message structure"""
    role: str  # "system", "user", "assistant"
    content: str
    name: Optional[str] = None

@dataclass
class ChatCompletionRequest:
    """Chat completion request parameters - Official Mistral AI API 1.0.0"""
    model: str  # Required: ID of the model to use
    messages: List[ChatMessage]  # Required: Array of messages
    temperature: Optional[float] = None  # 0.0 to 1.5, recommended 0.0-0.7
    top_p: Optional[float] = 1.0  # 0 to 1, default 1
    max_tokens: Optional[int] = None  # Max tokens to generate
    stream: bool = False  # Whether to stream back partial progress
    stop: Optional[Union[str, List[str]]] = None  # Stop generation tokens
    random_seed: Optional[int] = None  # Seed for deterministic results
    response_format: Optional[Dict] = None  # Response format specification
    tools: Optional[List[Dict]] = None  # Array of tools
    tool_choice: Optional[Union[str, Dict]] = "auto"  # Tool choice strategy
    presence_penalty: Optional[float] = 0.0  # -2 to 2, default 0
    frequency_penalty: Optional[float] = 0.0  # -2 to 2, default 0
    n: Optional[int] = None  # Number of completions to return
    prediction: Optional[Dict] = None  # Expected results for optimization
    parallel_tool_calls: bool = True  # Enable parallel tool calls
    prompt_mode: Optional[str] = None  # "reasoning" or None
    safe_prompt: bool = False  # Inject safety prompt
    
    def __post_init__(self):
        """Validate parameters according to official API specification"""
        # Validate temperature range (0.0 to 1.5)
        if self.temperature is not None and not (0.0 <= self.temperature <= 1.5):
            raise ValueError(f"Temperature must be between 0.0 and 1.5, got {self.temperature}")
        
        # Validate top_p range (0 to 1)
        if self.top_p is not None and not (0.0 <= self.top_p <= 1.0):
            raise ValueError(f"top_p must be between 0.0 and 1.0, got {self.top_p}")
        
        # Validate presence_penalty range (-2 to 2)
        if self.presence_penalty is not None and not (-2.0 <= self.presence_penalty <= 2.0):
            raise ValueError(f"presence_penalty must be between -2.0 and 2.0, got {self.presence_penalty}")
        
        # Validate frequency_penalty range (-2 to 2)
        if self.frequency_penalty is not None and not (-2.0 <= self.frequency_penalty <= 2.0):
            raise ValueError(f"frequency_penalty must be between -2.0 and 2.0, got {self.frequency_penalty}")
        
        # Validate max_tokens (must be positive)
        if self.max_tokens is not None and self.max_tokens < 0:
            raise ValueError(f"max_tokens must be non-negative, got {self.max_tokens}")
        
        # Validate n (must be positive)
        if self.n is not None and self.n < 1:
            raise ValueError(f"n must be at least 1, got {self.n}")
        
        # Validate random_seed (must be non-negative)
        if self.random_seed is not None and self.random_seed < 0:
            raise ValueError(f"random_seed must be non-negative, got {self.random_seed}")
        
        # Validate prompt_mode
        if self.prompt_mode is not None and self.prompt_mode not in ["reasoning"]:
            raise ValueError(f"prompt_mode must be 'reasoning' or None, got {self.prompt_mode}")
        
        # Validate tool_choice
        valid_tool_choices = ["auto", "none", "any", "required"]
        if isinstance(self.tool_choice, str) and self.tool_choice not in valid_tool_choices:
            raise ValueError(f"tool_choice must be one of {valid_tool_choices} or a dict, got {self.tool_choice}")
        
        # Validate response_format
        if self.response_format is not None:
            valid_types = ["text", "json_object", "json_schema"]
            if "type" not in self.response_format or self.response_format["type"] not in valid_types:
                raise ValueError(f"response_format type must be one of {valid_types}, got {self.response_format.get('type', 'missing')}")

class MistralAPIError(Exception):
    """Custom exception for Mistral API errors"""
    pass

class MistralAPIClient:
    """
    Comprehensive Mistral AI API client for mindX integration
    
    This client provides access to all Mistral AI services:
    - Chat completions with reasoning capabilities
    - Code generation and fill-in-the-middle
    - Agent creation and management
    - Embeddings and vector operations
    - Content classification and moderation
    - File upload and management
    - Fine-tuning operations
    - Batch processing
    - OCR and document analysis
    - Audio transcription
    - Conversation management
    - Knowledge library management
    """
    
    def __init__(self, config: MistralConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limiter = asyncio.Semaphore(10)  # Limit concurrent requests
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling and rate limiting"""
        async with self._rate_limiter:
            url = f"{self.config.base_url}{endpoint}"
            
            for attempt in range(self.config.max_retries):
                try:
                    async with self.session.request(method, url, **kwargs) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 422:
                            error_data = await response.json()
                            raise MistralAPIError(f"Validation error: {error_data}")
                        else:
                            error_text = await response.text()
                            raise MistralAPIError(f"HTTP {response.status}: {error_text}")
                            
                except aiohttp.ClientError as e:
                    if attempt == self.config.max_retries - 1:
                        raise MistralAPIError(f"Request failed after {self.config.max_retries} attempts: {e}")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    
            await asyncio.sleep(self.config.rate_limit_delay)
    
    # ==================== CHAT COMPLETION API ====================
    
    async def chat_completion(self, request: ChatCompletionRequest) -> Dict[str, Any]:
        """
        Generate chat completion using Mistral models
        
        Args:
            request: Chat completion parameters
            
        Returns:
            Completion response with choices and usage information
        """
        payload = {
            "model": request.model,
            "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
            "stream": request.stream
        }
        
        # Add optional parameters
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.stop is not None:
            payload["stop"] = request.stop
        if request.random_seed is not None:
            payload["random_seed"] = request.random_seed
        if request.response_format is not None:
            payload["response_format"] = request.response_format
        if request.tools is not None:
            payload["tools"] = request.tools
        if request.tool_choice is not None:
            payload["tool_choice"] = request.tool_choice
        if request.presence_penalty is not None:
            payload["presence_penalty"] = request.presence_penalty
        if request.frequency_penalty is not None:
            payload["frequency_penalty"] = request.frequency_penalty
        if request.n is not None:
            payload["n"] = request.n
        if request.prediction is not None:
            payload["prediction"] = request.prediction
        if request.parallel_tool_calls is not None:
            payload["parallel_tool_calls"] = request.parallel_tool_calls
        if request.prompt_mode is not None:
            payload["prompt_mode"] = request.prompt_mode
        if request.safe_prompt is not None:
            payload["safe_prompt"] = request.safe_prompt
        
        return await self._make_request("POST", "/chat/completions", json=payload)
    
    async def chat_completion_stream(self, request: ChatCompletionRequest) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream chat completion responses - Official API 1.0.0
        
        Args:
            request: Chat completion parameters with stream=True
            
        Yields:
            Streaming response chunks
        """
        request.stream = True
        payload = {
            "model": request.model,
            "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
            "stream": True
        }
        
        # Add all optional parameters for streaming (same as non-streaming)
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.top_p is not None:
            payload["top_p"] = request.top_p
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.stop is not None:
            payload["stop"] = request.stop
        if request.random_seed is not None:
            payload["random_seed"] = request.random_seed
        if request.response_format is not None:
            payload["response_format"] = request.response_format
        if request.tools is not None:
            payload["tools"] = request.tools
        if request.tool_choice is not None:
            payload["tool_choice"] = request.tool_choice
        if request.presence_penalty is not None:
            payload["presence_penalty"] = request.presence_penalty
        if request.frequency_penalty is not None:
            payload["frequency_penalty"] = request.frequency_penalty
        if request.n is not None:
            payload["n"] = request.n
        if request.prediction is not None:
            payload["prediction"] = request.prediction
        if request.parallel_tool_calls is not None:
            payload["parallel_tool_calls"] = request.parallel_tool_calls
        if request.prompt_mode is not None:
            payload["prompt_mode"] = request.prompt_mode
        if request.safe_prompt is not None:
            payload["safe_prompt"] = request.safe_prompt
        
        async with self.session.post(f"{self.config.base_url}/chat/completions", json=payload) as response:
            async for line in response.content:
                if line:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith('data: '):
                        data = line_str[6:]
                        if data == '[DONE]':
                            break
                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            continue
    
    # ==================== FILL-IN-THE-MIDDLE API ====================
    
    async def fim_completion(self, 
                           model: str = "codestral-2405",
                           prompt: str = "",
                           suffix: str = "",
                           temperature: Optional[float] = None,
                           top_p: Optional[float] = None,
                           max_tokens: Optional[int] = None,
                           stream: bool = False,
                           stop: Optional[Union[str, List[str]]] = None,
                           random_seed: Optional[int] = None,
                           min_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate code completion using fill-in-the-middle
        
        Args:
            model: Model to use (default: codestral-2405)
            prompt: Code prompt
            suffix: Code suffix for context
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            max_tokens: Maximum tokens to generate
            stream: Whether to stream response
            stop: Stop sequences
            random_seed: Random seed for reproducibility
            min_tokens: Minimum tokens to generate
            
        Returns:
            FIM completion response
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "suffix": suffix,
            "stream": stream
        }
        
        if temperature is not None:
            payload["temperature"] = temperature
        if top_p is not None:
            payload["top_p"] = top_p
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if stop is not None:
            payload["stop"] = stop
        if random_seed is not None:
            payload["random_seed"] = random_seed
        if min_tokens is not None:
            payload["min_tokens"] = min_tokens
        
        return await self._make_request("POST", "/fim/completions", json=payload)
    
    # ==================== AGENTS API ====================
    
    async def create_agent(self,
                          name: str,
                          instructions: str,
                          model: str,
                          description: Optional[str] = None,
                          tools: Optional[List[Dict]] = None,
                          completion_args: Optional[Dict] = None,
                          handoffs: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a new Mistral agent
        
        Args:
            name: Agent name
            instructions: Agent instructions
            model: Model to use
            description: Agent description
            tools: Available tools
            completion_args: Completion arguments
            handoffs: Handoff targets
            
        Returns:
            Created agent information
        """
        payload = {
            "name": name,
            "instructions": instructions,
            "model": model
        }
        
        if description is not None:
            payload["description"] = description
        if tools is not None:
            payload["tools"] = tools
        if completion_args is not None:
            payload["completion_args"] = completion_args
        if handoffs is not None:
            payload["handoffs"] = handoffs
        
        return await self._make_request("POST", "/agents", json=payload)
    
    async def list_agents(self, page: int = 0, page_size: int = 20) -> Dict[str, Any]:
        """List all agents"""
        params = {"page": page, "page_size": page_size}
        return await self._make_request("GET", "/agents", params=params)
    
    async def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get agent by ID"""
        return await self._make_request("GET", f"/agents/{agent_id}")
    
    async def update_agent(self, agent_id: str, **kwargs) -> Dict[str, Any]:
        """Update agent"""
        return await self._make_request("PATCH", f"/agents/{agent_id}", json=kwargs)
    
    async def agent_completion(self, agent_id: str, messages: List[ChatMessage], **kwargs) -> Dict[str, Any]:
        """
        Generate completion using a specific agent
        
        Args:
            agent_id: Agent ID to use
            messages: Conversation messages
            **kwargs: Additional completion parameters
            
        Returns:
            Agent completion response
        """
        payload = {
            "agent_id": agent_id,
            "messages": [{"role": msg.role, "content": msg.content} for msg in messages]
        }
        payload.update(kwargs)
        
        return await self._make_request("POST", "/agents/completions", json=payload)
    
    # ==================== EMBEDDINGS API ====================
    
    async def create_embeddings(self,
                               model: str = "mistral-embed",
                               input_text: Union[str, List[str]] = "",
                               output_dimension: Optional[int] = None,
                               output_dtype: str = "float") -> Dict[str, Any]:
        """
        Create embeddings for text
        
        Args:
            model: Embedding model to use
            input_text: Text or list of texts to embed
            output_dimension: Output dimension
            output_dtype: Output data type
            
        Returns:
            Embeddings response
        """
        payload = {
            "model": model,
            "input": input_text,
            "output_dtype": output_dtype
        }
        
        if output_dimension is not None:
            payload["output_dimension"] = output_dimension
        
        return await self._make_request("POST", "/embeddings", json=payload)
    
    # ==================== CLASSIFICATION & MODERATION API ====================
    
    async def moderate_content(self, model: str, input_text: Union[str, List[str]]) -> Dict[str, Any]:
        """
        Moderate content for safety
        
        Args:
            model: Moderation model
            input_text: Text to moderate
            
        Returns:
            Moderation results
        """
        payload = {
            "model": model,
            "input": input_text
        }
        
        return await self._make_request("POST", "/moderations", json=payload)
    
    async def classify_content(self, model: str, input_text: Union[str, List[str]]) -> Dict[str, Any]:
        """
        Classify content
        
        Args:
            model: Classification model
            input_text: Text to classify
            
        Returns:
            Classification results
        """
        payload = {
            "model": model,
            "input": input_text
        }
        
        return await self._make_request("POST", "/classifications", json=payload)
    
    # ==================== FILES API ====================
    
    async def upload_file(self, file_path: str, purpose: str = "fine-tune") -> Dict[str, Any]:
        """
        Upload file to Mistral
        
        Args:
            file_path: Path to file
            purpose: File purpose (fine-tune, batch, ocr)
            
        Returns:
            File information
        """
        file_path = Path(file_path)
        
        data = aiohttp.FormData()
        data.add_field('file', open(file_path, 'rb'), filename=file_path.name)
        data.add_field('purpose', purpose)
        
        return await self._make_request("POST", "/files", data=data)
    
    async def list_files(self, 
                        page: int = 0,
                        page_size: int = 100,
                        purpose: Optional[str] = None) -> Dict[str, Any]:
        """List uploaded files"""
        params = {"page": page, "page_size": page_size}
        if purpose:
            params["purpose"] = purpose
        
        return await self._make_request("GET", "/files", params=params)
    
    async def get_file(self, file_id: str) -> Dict[str, Any]:
        """Get file information"""
        return await self._make_request("GET", f"/files/{file_id}")
    
    async def delete_file(self, file_id: str) -> Dict[str, Any]:
        """Delete file"""
        return await self._make_request("DELETE", f"/files/{file_id}")
    
    # ==================== FINE-TUNING API ====================
    
    async def create_fine_tuning_job(self,
                                   model: str,
                                   training_files: List[str],
                                   validation_files: Optional[List[str]] = None,
                                   suffix: Optional[str] = None,
                                   hyperparameters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create fine-tuning job
        
        Args:
            model: Model to fine-tune
            training_files: List of training file IDs
            validation_files: List of validation file IDs
            suffix: Model suffix
            hyperparameters: Training hyperparameters
            
        Returns:
            Fine-tuning job information
        """
        payload = {
            "model": model,
            "training_files": training_files,
            "auto_start": True
        }
        
        if validation_files:
            payload["validation_files"] = validation_files
        if suffix:
            payload["suffix"] = suffix
        if hyperparameters:
            payload["hyperparameters"] = hyperparameters
        
        return await self._make_request("POST", "/fine_tuning/jobs", json=payload)
    
    async def list_fine_tuning_jobs(self, page: int = 0, page_size: int = 100) -> Dict[str, Any]:
        """List fine-tuning jobs"""
        params = {"page": page, "page_size": page_size}
        return await self._make_request("GET", "/fine_tuning/jobs", params=params)
    
    async def get_fine_tuning_job(self, job_id: str) -> Dict[str, Any]:
        """Get fine-tuning job details"""
        return await self._make_request("GET", f"/fine_tuning/jobs/{job_id}")
    
    # ==================== MODELS API ====================
    
    async def list_models(self) -> Dict[str, Any]:
        """List available models"""
        return await self._make_request("GET", "/models")
    
    async def get_model(self, model_id: str) -> Dict[str, Any]:
        """Get model information"""
        return await self._make_request("GET", f"/models/{model_id}")
    
    # ==================== BATCH API ====================
    
    async def create_batch_job(self,
                              input_files: List[str],
                              endpoint: str,
                              model: Optional[str] = None,
                              agent_id: Optional[str] = None,
                              metadata: Optional[Dict] = None,
                              timeout_hours: int = 24) -> Dict[str, Any]:
        """
        Create batch processing job
        
        Args:
            input_files: List of input file IDs
            endpoint: API endpoint to use
            model: Model to use
            agent_id: Agent ID to use
            metadata: Job metadata
            timeout_hours: Job timeout in hours
            
        Returns:
            Batch job information
        """
        payload = {
            "input_files": input_files,
            "endpoint": endpoint,
            "timeout_hours": timeout_hours
        }
        
        if model:
            payload["model"] = model
        if agent_id:
            payload["agent_id"] = agent_id
        if metadata:
            payload["metadata"] = metadata
        
        return await self._make_request("POST", "/batch/jobs", json=payload)
    
    async def get_batch_job(self, job_id: str) -> Dict[str, Any]:
        """Get batch job details"""
        return await self._make_request("GET", f"/batch/jobs/{job_id}")
    
    # ==================== OCR API ====================
    
    async def ocr_document(self,
                          model: str,
                          document: Dict,
                          pages: Optional[List[int]] = None,
                          include_image_base64: bool = False,
                          image_limit: Optional[int] = None,
                          image_min_size: Optional[int] = None,
                          bbox_annotation_format: Optional[Dict] = None,
                          document_annotation_format: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Perform OCR on document
        
        Args:
            model: OCR model to use
            document: Document to process
            pages: Specific pages to process
            include_image_base64: Include base64 images
            image_limit: Maximum images to extract
            image_min_size: Minimum image size
            bbox_annotation_format: Bounding box annotation format
            document_annotation_format: Document annotation format
            
        Returns:
            OCR results
        """
        payload = {
            "model": model,
            "document": document
        }
        
        if pages is not None:
            payload["pages"] = pages
        if include_image_base64 is not None:
            payload["include_image_base64"] = include_image_base64
        if image_limit is not None:
            payload["image_limit"] = image_limit
        if image_min_size is not None:
            payload["image_min_size"] = image_min_size
        if bbox_annotation_format is not None:
            payload["bbox_annotation_format"] = bbox_annotation_format
        if document_annotation_format is not None:
            payload["document_annotation_format"] = document_annotation_format
        
        return await self._make_request("POST", "/ocr", json=payload)
    
    # ==================== TRANSCRIPTION API ====================
    
    async def transcribe_audio(self,
                              model: str,
                              file_path: Optional[str] = None,
                              file_url: Optional[str] = None,
                              file_id: Optional[str] = None,
                              language: Optional[str] = None,
                              temperature: Optional[float] = None,
                              stream: bool = False,
                              timestamp_granularities: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Transcribe audio file
        
        Args:
            model: Transcription model
            file_path: Path to audio file
            file_url: URL of audio file
            file_id: ID of uploaded file
            language: Audio language
            temperature: Sampling temperature
            stream: Whether to stream response
            timestamp_granularities: Timestamp granularities
            
        Returns:
            Transcription results
        """
        data = aiohttp.FormData()
        data.add_field('model', model)
        
        if file_path:
            data.add_field('file', open(file_path, 'rb'))
        elif file_url:
            data.add_field('file_url', file_url)
        elif file_id:
            data.add_field('file_id', file_id)
        
        if language:
            data.add_field('language', language)
        if temperature is not None:
            data.add_field('temperature', str(temperature))
        if stream:
            data.add_field('stream', 'true')
        if timestamp_granularities:
            for granularity in timestamp_granularities:
                data.add_field('timestamp_granularities', granularity)
        
        return await self._make_request("POST", "/audio/transcriptions", data=data)
    
    # ==================== CONVERSATIONS API ====================
    
    async def create_conversation(self,
                                 inputs: Union[str, List[Dict]],
                                 model: Optional[str] = None,
                                 agent_id: Optional[str] = None,
                                 instructions: Optional[str] = None,
                                 tools: Optional[List[Dict]] = None,
                                 completion_args: Optional[Dict] = None,
                                 name: Optional[str] = None,
                                 description: Optional[str] = None,
                                 stream: bool = False,
                                 store: bool = True,
                                 handoff_execution: str = "server") -> Dict[str, Any]:
        """
        Create new conversation
        
        Args:
            inputs: Conversation inputs
            model: Model to use
            agent_id: Agent ID to use
            instructions: Conversation instructions
            tools: Available tools
            completion_args: Completion arguments
            name: Conversation name
            description: Conversation description
            stream: Whether to stream
            store: Whether to store conversation
            handoff_execution: Handoff execution mode
            
        Returns:
            Conversation response
        """
        payload = {
            "inputs": inputs,
            "stream": stream,
            "store": store,
            "handoff_execution": handoff_execution
        }
        
        if model:
            payload["model"] = model
        if agent_id:
            payload["agent_id"] = agent_id
        if instructions:
            payload["instructions"] = instructions
        if tools:
            payload["tools"] = tools
        if completion_args:
            payload["completion_args"] = completion_args
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        
        return await self._make_request("POST", "/conversations", json=payload)
    
    async def list_conversations(self, page: int = 0, page_size: int = 100) -> Dict[str, Any]:
        """List conversations"""
        params = {"page": page, "page_size": page_size}
        return await self._make_request("GET", "/conversations", params=params)
    
    async def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Get conversation details"""
        return await self._make_request("GET", f"/conversations/{conversation_id}")
    
    async def append_to_conversation(self, conversation_id: str, inputs: Union[str, List[Dict]], **kwargs) -> Dict[str, Any]:
        """Append to existing conversation"""
        payload = {"inputs": inputs}
        payload.update(kwargs)
        
        return await self._make_request("POST", f"/conversations/{conversation_id}", json=payload)
    
    # ==================== LIBRARIES API ====================
    
    async def create_library(self,
                            name: str,
                            description: Optional[str] = None,
                            chunk_size: Optional[int] = None) -> Dict[str, Any]:
        """
        Create knowledge library
        
        Args:
            name: Library name
            description: Library description
            chunk_size: Chunk size for documents
            
        Returns:
            Library information
        """
        payload = {"name": name}
        
        if description:
            payload["description"] = description
        if chunk_size:
            payload["chunk_size"] = chunk_size
        
        return await self._make_request("POST", "/libraries", json=payload)
    
    async def list_libraries(self) -> Dict[str, Any]:
        """List all libraries"""
        return await self._make_request("GET", "/libraries")
    
    async def get_library(self, library_id: str) -> Dict[str, Any]:
        """Get library details"""
        return await self._make_request("GET", f"/libraries/{library_id}")
    
    async def upload_document(self, library_id: str, file_path: str) -> Dict[str, Any]:
        """
        Upload document to library
        
        Args:
            library_id: Library ID
            file_path: Path to document
            
        Returns:
            Document information
        """
        file_path = Path(file_path)
        
        data = aiohttp.FormData()
        data.add_field('file', open(file_path, 'rb'), filename=file_path.name)
        
        return await self._make_request("POST", f"/libraries/{library_id}/documents", data=data)
    
    async def list_documents(self, library_id: str, **kwargs) -> Dict[str, Any]:
        """List documents in library"""
        params = {}
        params.update(kwargs)
        
        return await self._make_request("GET", f"/libraries/{library_id}/documents", params=params)


class MistralIntegration:
    """
    High-level integration class for mindX agents
    
    This class provides simplified interfaces for common Mistral AI operations
    that can be easily integrated with mindX's agent architecture.
    """
    
    def __init__(self, config: MistralConfig):
        self.config = config
        self.client: Optional[MistralAPIClient] = None
        self.api_available = bool(config.api_key)
        self.model_catalog: Dict[str, Any] = {}
        self._load_model_catalog()
    
    def _load_model_catalog(self):
        """Load model catalog from mistral.yaml"""
        try:
            import yaml
            from pathlib import Path
            
            config_path = Path(__file__).parent.parent / "models" / "mistral.yaml"
            if config_path.exists():
                with open(config_path, "r") as f:
                    self.model_catalog = yaml.safe_load(f) or {}
                logger.info(f"Loaded Mistral model catalog from {config_path}")
            else:
                logger.warning(f"mistral.yaml not found at {config_path}")
        except Exception as e:
            logger.error(f"Error loading mistral.yaml: {e}")
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get model information from the catalog"""
        possible_keys = [
            f"mistral/{model_name}",
            model_name,
            f"mistral-{model_name}",
            f"{model_name}-latest"
        ]
        
        for key in possible_keys:
            if key in self.model_catalog:
                return self.model_catalog[key]
        
        return None
    
    def get_best_model_for_task(self, task_type: str) -> str:
        """Get the best model for a specific task based on YAML scores"""
        best_model = None
        best_score = 0.0
        
        for model_key, model_info in self.model_catalog.items():
            if "task_scores" in model_info and task_type in model_info["task_scores"]:
                score = model_info["task_scores"][task_type]
                if score > best_score:
                    best_score = score
                    best_model = model_key.split("/", 1)[1] if "/" in model_key else model_key
        
        return best_model or "mistral-large-latest"
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.client = MistralAPIClient(self.config)
        await self.client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
    
    # ==================== MINDX INTEGRATION METHODS ====================
    
    async def enhance_reasoning(self, 
                               context: str, 
                               question: str,
                               model: Optional[MistralModel] = None) -> str:
        """
        Enhance reasoning capabilities using Mistral's reasoning mode
        
        Args:
            context: Context information
            question: Question to reason about
            model: Model to use for reasoning (auto-selected if None)
            
        Returns:
            Enhanced reasoning response
        """
        if not self.api_available:
            logger.warning("Mistral API not available. Returning mock reasoning response.")
            return f"[MOCK REASONING] Mistral API not configured. Would analyze: {question[:100]}... with context: {context[:100]}..."
        
        # Auto-select best model for reasoning if not specified
        if model is None:
            best_model = self.get_best_model_for_task("reasoning")
            model = MistralModel(best_model) if best_model in [m.value for m in MistralModel] else MistralModel.MISTRAL_LARGE_LATEST
        
        messages = [
            ChatMessage(role="system", content="You are an advanced reasoning assistant. Think step by step and provide detailed analysis."),
            ChatMessage(role="user", content=f"Context: {context}\n\nQuestion: {question}")
        ]
        
        request = ChatCompletionRequest(
            model=model.value,
            messages=messages,
            prompt_mode=MistralPromptMode.REASONING,
            temperature=0.3,
            max_tokens=1000
        )
        
        response = await self.client.chat_completion(request)
        return response["choices"][0]["message"]["content"]
    
    async def generate_code(self,
                           prompt: str,
                           suffix: str = "",
                           model: Optional[MistralModel] = None) -> str:
        """
        Generate code using Mistral's code models
        
        Args:
            prompt: Code prompt
            suffix: Code suffix for context
            model: Code model to use (auto-selected if None)
            
        Returns:
            Generated code
        """
        if not self.api_available:
            logger.warning("Mistral API not available. Returning mock code response.")
            return f"# [MOCK CODE] Mistral API not configured\n# Would generate code for: {prompt[:100]}...\n# Suffix: {suffix[:50]}..."
        
        # Auto-select best model for code generation if not specified
        if model is None:
            best_model = self.get_best_model_for_task("code_generation")
            model = MistralModel(best_model) if best_model in [m.value for m in MistralModel] else MistralModel.CODESTRAL_LATEST
        
        response = await self.client.fim_completion(
            model=model.value,
            prompt=prompt,
            suffix=suffix,
            temperature=0.2,
            max_tokens=1000
        )
        
        return response["choices"][0]["text"]
    
    async def create_embeddings_for_memory(self, 
                                         texts: List[str],
                                         model: MistralModel = MistralModel.MISTRAL_EMBED) -> List[List[float]]:
        """
        Create embeddings for memory storage
        
        Args:
            texts: Texts to embed
            model: Embedding model to use
            
        Returns:
            List of embedding vectors
        """
        if not self.api_available:
            logger.warning("Mistral API not available. Returning mock embeddings.")
            import random
            return [[random.random() for _ in range(1024)] for _ in texts]
        
        response = await self.client.create_embeddings(
            model=model.value,
            input_text=texts
        )
        
        return [item["embedding"] for item in response["data"]]
    
    async def classify_agent_intent(self, 
                                   message: str,
                                   model: str = "mistral-classifier") -> Dict[str, Any]:
        """
        Classify agent intent for routing
        
        Args:
            message: Message to classify
            model: Classification model
            
        Returns:
            Classification results
        """
        return await self.client.classify_content(model, message)
    
    async def moderate_agent_output(self, 
                                   content: str,
                                   model: str = "mistral-moderator") -> Dict[str, Any]:
        """
        Moderate agent output for safety
        
        Args:
            content: Content to moderate
            model: Moderation model
            
        Returns:
            Moderation results
        """
        return await self.client.moderate_content(model, content)
    
    async def process_document(self,
                              file_path: str,
                              library_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process document with OCR and store in library
        
        Args:
            file_path: Path to document
            library_id: Optional library ID for storage
            
        Returns:
            Processing results
        """
        # Upload file
        file_info = await self.client.upload_file(file_path, purpose="ocr")
        
        # Perform OCR
        ocr_result = await self.client.ocr_document(
            model="pixtral-12b-latest",
            document={"type": "file", "file_id": file_info["id"]}
        )
        
        # Store in library if specified
        if library_id:
            await self.client.upload_document(library_id, file_path)
        
        return {
            "file_info": file_info,
            "ocr_result": ocr_result,
            "library_id": library_id
        }
    
    async def transcribe_audio_for_agent(self,
                                       file_path: str,
                                       language: str = "en") -> str:
        """
        Transcribe audio for agent processing
        
        Args:
            file_path: Path to audio file
            language: Audio language
            
        Returns:
            Transcribed text
        """
        response = await self.client.transcribe_audio(
            model="whisper-1",
            file_path=file_path,
            language=language
        )
        
        return response["text"]


# ==================== UTILITY FUNCTIONS ====================

def create_mistral_config(api_key: str, **kwargs) -> MistralConfig:
    """Create Mistral configuration from environment or parameters"""
    return MistralConfig(api_key=api_key, **kwargs)

async def test_mistral_connection(config: MistralConfig) -> bool:
    """Test Mistral API connection"""
    try:
        async with MistralAPIClient(config) as client:
            await client.list_models()
            return True
    except Exception as e:
        logger.error(f"Mistral connection test failed: {e}")
        return False

# ==================== EXAMPLE USAGE ====================

async def example_usage():
    """Example usage of Mistral API integration"""
    
    # Create configuration
    config = create_mistral_config(api_key="your-api-key-here")
    
    # Test connection
    if not await test_mistral_connection(config):
        print("Failed to connect to Mistral API")
        return
    
    # Use high-level integration
    async with MistralIntegration(config) as mistral:
        
        # Enhance reasoning
        reasoning = await mistral.enhance_reasoning(
            context="mindX is an autonomous AI system",
            question="How can we improve agent coordination?"
        )
        print(f"Reasoning: {reasoning}")
        
        # Generate code
        code = await mistral.generate_code(
            prompt="def calculate_agent_efficiency(",
            suffix="return efficiency_score"
        )
        print(f"Generated code: {code}")
        
        # Create embeddings
        embeddings = await mistral.create_embeddings_for_memory([
            "Agent coordination is important",
            "Memory management is critical"
        ])
        print(f"Created {len(embeddings)} embeddings")
        
        # Classify intent
        classification = await mistral.classify_agent_intent(
            "I need help with code generation"
        )
        print(f"Intent classification: {classification}")

if __name__ == "__main__":
    asyncio.run(example_usage())
