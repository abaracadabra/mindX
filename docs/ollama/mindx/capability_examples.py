"""
mindX Ollama Capability Examples
================================

Complete coded examples for every Ollama capability, tailored to mindX architecture.
Extends the existing OllamaAPI (api/ollama/ollama_url.py) and OllamaChatManager
(agents/core/ollama_chat_manager.py).

Capabilities covered:
1. Streaming
2. Thinking
3. Structured Outputs
4. Vision
5. Embeddings
6. Tool Calling
7. Web Search
8. Cloud Integration
9. Model Management
10. Rate-Limited Cloud Client

Usage:
    python -m docs.ollama.mindx.capability_examples
    # Or import individual functions
"""

import asyncio
import aiohttp
import json
import os
import base64
import time
import random
from typing import AsyncGenerator, Optional
from pathlib import Path
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Configuration — aligns with mindX settings
# ---------------------------------------------------------------------------

OLLAMA_LOCAL = os.environ.get("MINDX_LLM__OLLAMA__BASE_URL", "http://localhost:11434")
OLLAMA_CLOUD = "https://ollama.com"
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "")

DEFAULT_MODEL = "qwen3:1.7b"
EMBED_MODEL = "mxbai-embed-large"
VISION_MODEL = "gemma3"
THINKING_MODEL = "deepseek-r1:1.5b"

TIMEOUT = aiohttp.ClientTimeout(total=120, connect=10, sock_read=60)


# ===========================================================================
# 1. STREAMING
# ===========================================================================

async def stream_chat(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    base_url: str = OLLAMA_LOCAL,
    think: bool = False,
    options: dict | None = None,
) -> AsyncGenerator[dict, None]:
    """
    Stream chat responses token-by-token from Ollama.
    Yields each chunk as a dict. The final chunk has done=True and includes metrics.

    Extends: OllamaAPI.generate_text() which currently uses stream=False.
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    if think:
        payload["think"] = True
    if options:
        payload["options"] = options

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/chat",
            json=payload,
            timeout=TIMEOUT,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.content:
                line = line.strip()
                if line:
                    chunk = json.loads(line)
                    yield chunk
                    if chunk.get("done"):
                        break


async def stream_generate(
    prompt: str,
    model: str = DEFAULT_MODEL,
    base_url: str = OLLAMA_LOCAL,
    **kwargs,
) -> AsyncGenerator[dict, None]:
    """Stream generate responses (non-chat endpoint)."""
    payload = {"model": model, "prompt": prompt, "stream": True, **kwargs}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/generate",
            json=payload,
            timeout=TIMEOUT,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.content:
                line = line.strip()
                if line:
                    chunk = json.loads(line)
                    yield chunk
                    if chunk.get("done"):
                        break


async def demo_streaming():
    """Demonstrate streaming with thinking."""
    print("=== STREAMING DEMO ===")
    thinking = ""
    content = ""

    async for chunk in stream_chat(
        [{"role": "user", "content": "What is 17 * 23? Think step by step."}],
        model=DEFAULT_MODEL,
        think=True,
    ):
        msg = chunk.get("message", {})
        if msg.get("thinking"):
            thinking += msg["thinking"]
            print(f"\033[90m{msg['thinking']}\033[0m", end="", flush=True)
        if msg.get("content"):
            content += msg["content"]
            print(msg["content"], end="", flush=True)

    print(f"\n\n[Thinking: {len(thinking)} chars, Content: {len(content)} chars]")
    return {"thinking": thinking, "content": content}


# ===========================================================================
# 2. THINKING
# ===========================================================================

async def chat_with_thinking(
    messages: list[dict],
    model: str = THINKING_MODEL,
    think: bool | str = True,
    stream: bool = False,
    base_url: str = OLLAMA_LOCAL,
) -> dict:
    """
    Chat with thinking trace support.

    Args:
        think: True/False for most models, or "low"/"medium"/"high" for GPT-OSS
        stream: If True, accumulates and returns full thinking + content
    """
    payload = {
        "model": model,
        "messages": messages,
        "think": think,
        "stream": stream,
    }

    if stream:
        thinking = ""
        content = ""
        async for chunk in stream_chat(messages, model, base_url, think=True):
            msg = chunk.get("message", {})
            if msg.get("thinking"):
                thinking += msg["thinking"]
            if msg.get("content"):
                content += msg["content"]
        return {"thinking": thinking, "content": content}
    else:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/api/chat",
                json=payload,
                timeout=TIMEOUT,
            ) as resp:
                data = await resp.json()
                msg = data.get("message", {})
                return {
                    "thinking": msg.get("thinking", ""),
                    "content": msg.get("content", ""),
                    "eval_count": data.get("eval_count", 0),
                    "total_duration": data.get("total_duration", 0),
                }


async def demo_thinking():
    """Demonstrate thinking capability."""
    print("=== THINKING DEMO ===")
    result = await chat_with_thinking(
        [{"role": "user", "content": "How many letter r are in strawberry?"}],
    )
    print(f"Thinking: {result['thinking'][:200]}...")
    print(f"Answer: {result['content']}")
    return result


# ===========================================================================
# 3. STRUCTURED OUTPUTS
# ===========================================================================

async def structured_chat(
    messages: list[dict],
    schema: dict,
    model: str = DEFAULT_MODEL,
    base_url: str = OLLAMA_LOCAL,
    temperature: float = 0.0,
) -> dict:
    """
    Chat with JSON schema enforcement.
    Returns parsed JSON matching the provided schema.

    Extends: OllamaAPI format parameter support.
    """
    payload = {
        "model": model,
        "messages": messages,
        "format": schema,
        "stream": False,
        "options": {"temperature": temperature},
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/chat",
            json=payload,
            timeout=TIMEOUT,
        ) as resp:
            data = await resp.json()
            content = data.get("message", {}).get("content", "{}")
            return json.loads(content)


async def demo_structured_outputs():
    """Demonstrate structured outputs with BDI schema."""
    print("=== STRUCTURED OUTPUTS DEMO ===")

    bdi_schema = {
        "type": "object",
        "properties": {
            "beliefs": {"type": "array", "items": {"type": "string"}},
            "desires": {"type": "array", "items": {"type": "string"}},
            "intentions": {"type": "array", "items": {"type": "string"}},
            "next_action": {"type": "string"},
            "confidence": {"type": "number"},
        },
        "required": ["beliefs", "desires", "intentions", "next_action", "confidence"],
    }

    result = await structured_chat(
        [
            {"role": "system", "content": "You are a BDI reasoning engine. Analyze state and plan."},
            {"role": "user", "content": "Memory usage is at 85%. Last improvement cycle succeeded. No active errors."},
        ],
        schema=bdi_schema,
    )
    print(json.dumps(result, indent=2))
    return result


# ===========================================================================
# 4. VISION
# ===========================================================================

async def vision_chat(
    prompt: str,
    image_path: str | None = None,
    image_b64: str | None = None,
    model: str = VISION_MODEL,
    schema: dict | None = None,
    base_url: str = OLLAMA_LOCAL,
) -> str | dict:
    """
    Chat with image input for vision models.

    Accepts file path (auto-encodes) or pre-encoded base64.
    Optional schema for structured vision output.
    """
    if image_path and not image_b64:
        image_b64 = base64.b64encode(Path(image_path).read_bytes()).decode()

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [image_b64] if image_b64 else [],
            }
        ],
        "stream": False,
    }
    if schema:
        payload["format"] = schema
        payload["options"] = {"temperature": 0}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/chat",
            json=payload,
            timeout=TIMEOUT,
        ) as resp:
            data = await resp.json()
            content = data.get("message", {}).get("content", "")
            if schema:
                return json.loads(content)
            return content


# ===========================================================================
# 5. EMBEDDINGS
# ===========================================================================

async def embed_texts(
    texts: list[str] | str,
    model: str = EMBED_MODEL,
    base_url: str = OLLAMA_LOCAL,
    dimensions: int | None = None,
) -> list[list[float]]:
    """
    Generate embeddings via Ollama for pgvector / RAGE storage.

    Returns L2-normalized vectors (cosine similarity = dot product).
    Extends: mindX currently uses mxbai-embed-large and nomic-embed-text.
    """
    if isinstance(texts, str):
        texts = [texts]

    payload = {"model": model, "input": texts}
    if dimensions:
        payload["dimensions"] = dimensions

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/embed",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            data = await resp.json()
            return data.get("embeddings", [])


async def demo_embeddings():
    """Demonstrate batch embedding for RAGE."""
    print("=== EMBEDDINGS DEMO ===")
    texts = [
        "mindX autonomous improvement cycle",
        "BDI belief-desire-intention architecture",
        "Ollama inference provider configuration",
    ]
    embeddings = await embed_texts(texts)
    for i, (text, emb) in enumerate(zip(texts, embeddings)):
        print(f"  [{i}] '{text[:40]}...' -> {len(emb)}-dim vector")
    return embeddings


# ===========================================================================
# 6. TOOL CALLING
# ===========================================================================

async def chat_with_tools(
    messages: list[dict],
    tools: list[dict],
    tool_executor: dict,
    model: str = DEFAULT_MODEL,
    max_rounds: int = 5,
    think: bool = True,
    base_url: str = OLLAMA_LOCAL,
) -> dict:
    """
    Multi-turn tool calling agent loop.

    Args:
        tools: Ollama tool definitions (JSON schema format)
        tool_executor: Dict mapping tool names to async callables
        max_rounds: Max tool-calling rounds before forcing completion

    Returns final response with full conversation history.
    """
    for round_num in range(max_rounds):
        payload = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "think": think,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/api/chat",
                json=payload,
                timeout=TIMEOUT,
            ) as resp:
                data = await resp.json()

        msg = data.get("message", {})
        messages.append(msg)

        tool_calls = msg.get("tool_calls", [])
        if not tool_calls:
            # No more tool calls — model has final answer
            return {
                "content": msg.get("content", ""),
                "thinking": msg.get("thinking", ""),
                "rounds": round_num + 1,
                "messages": messages,
            }

        # Execute tool calls
        for call in tool_calls:
            fn_name = call.get("function", {}).get("name", "")
            fn_args = call.get("function", {}).get("arguments", {})

            if fn_name in tool_executor:
                try:
                    result = await tool_executor[fn_name](**fn_args)
                except Exception as e:
                    result = f"Error: {e}"
            else:
                result = f"Tool '{fn_name}' not found"

            messages.append({
                "role": "tool",
                "tool_name": fn_name,
                "content": str(result),
            })

    return {"content": "Max tool rounds reached", "rounds": max_rounds, "messages": messages}


def mindx_tool_to_ollama(name: str, description: str, parameters: dict) -> dict:
    """Convert mindX tool schema to Ollama tool definition."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


async def demo_tool_calling():
    """Demonstrate tool calling with agent loop."""
    print("=== TOOL CALLING DEMO ===")

    # Define tools as Ollama schemas
    tools = [
        mindx_tool_to_ollama(
            "add", "Add two numbers",
            {"type": "object", "required": ["a", "b"],
             "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}},
        ),
        mindx_tool_to_ollama(
            "multiply", "Multiply two numbers",
            {"type": "object", "required": ["a", "b"],
             "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}},
        ),
    ]

    # Tool executors
    async def add(a: int, b: int) -> int:
        return a + b

    async def multiply(a: int, b: int) -> int:
        return a * b

    tool_executor = {"add": add, "multiply": multiply}

    result = await chat_with_tools(
        messages=[{"role": "user", "content": "What is (100 + 200) * 3?"}],
        tools=tools,
        tool_executor=tool_executor,
    )
    print(f"  Answer: {result['content']}")
    print(f"  Rounds: {result['rounds']}")
    return result


# ===========================================================================
# 7. WEB SEARCH
# ===========================================================================

async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web via Ollama's web search API.
    Requires OLLAMA_API_KEY.
    """
    if not OLLAMA_API_KEY:
        return []

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{OLLAMA_CLOUD}/api/web_search",
            json={"query": query, "max_results": max_results},
            headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("results", [])
            return []


async def web_fetch(url: str) -> dict:
    """
    Fetch and extract content from a URL via Ollama API.
    Returns {title, content, links}.
    """
    if not OLLAMA_API_KEY:
        return {}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{OLLAMA_CLOUD}/api/web_fetch",
            json={"url": url},
            headers={"Authorization": f"Bearer {OLLAMA_API_KEY}"},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            return {}


async def search_agent(query: str, model: str = DEFAULT_MODEL) -> str:
    """
    Complete search agent: model decides when to search and fetch.
    Uses web_search and web_fetch as tools.
    """
    tools = [
        mindx_tool_to_ollama(
            "web_search",
            "Search the web for information",
            {"type": "object", "required": ["query"],
             "properties": {
                 "query": {"type": "string", "description": "Search query"},
                 "max_results": {"type": "integer", "description": "Max results (1-10)"},
             }},
        ),
        mindx_tool_to_ollama(
            "web_fetch",
            "Fetch content from a URL",
            {"type": "object", "required": ["url"],
             "properties": {"url": {"type": "string", "description": "URL to fetch"}}},
        ),
    ]

    async def _web_search(query: str, max_results: int = 5) -> str:
        results = await web_search(query, max_results)
        # Truncate for context limits
        return json.dumps(results)[:8000]

    async def _web_fetch(url: str) -> str:
        result = await web_fetch(url)
        content = result.get("content", "")
        return content[:8000]

    result = await chat_with_tools(
        messages=[{"role": "user", "content": query}],
        tools=tools,
        tool_executor={"web_search": _web_search, "web_fetch": _web_fetch},
        model=model,
    )
    return result["content"]


# ===========================================================================
# 8. CLOUD INTEGRATION
# ===========================================================================

async def cloud_chat(
    messages: list[dict],
    model: str = "gpt-oss:120b",
    stream: bool = False,
    **kwargs,
) -> dict:
    """
    Chat via Ollama cloud API directly.
    Requires OLLAMA_API_KEY.
    """
    if not OLLAMA_API_KEY:
        raise ValueError("OLLAMA_API_KEY not set")

    headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}"}
    payload = {"model": model, "messages": messages, "stream": stream, **kwargs}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{OLLAMA_CLOUD}/api/chat",
            json=payload,
            headers=headers,
            timeout=TIMEOUT,
        ) as resp:
            return await resp.json()


async def list_cloud_models() -> list[dict]:
    """List all models available on Ollama cloud."""
    if not OLLAMA_API_KEY:
        return []

    headers = {"Authorization": f"Bearer {OLLAMA_API_KEY}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{OLLAMA_CLOUD}/api/tags",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("models", [])
            return []


# ===========================================================================
# 9. MODEL MANAGEMENT
# ===========================================================================

async def list_local_models(base_url: str = OLLAMA_LOCAL) -> list[dict]:
    """List locally installed models with details."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{base_url}/api/tags") as resp:
            data = await resp.json()
            return data.get("models", [])


async def show_model(model: str, verbose: bool = False, base_url: str = OLLAMA_LOCAL) -> dict:
    """Get detailed model information including capabilities."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/show",
            json={"model": model, "verbose": verbose},
        ) as resp:
            return await resp.json()


async def create_model(
    name: str,
    from_model: str,
    system: str = "",
    parameters: dict | None = None,
    base_url: str = OLLAMA_LOCAL,
) -> bool:
    """Create a custom model via API (equivalent to Modelfile)."""
    payload = {"model": name, "from": from_model}
    if system:
        payload["system"] = system
    if parameters:
        payload["parameters"] = parameters

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/create",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=300),
        ) as resp:
            # Read streaming status updates
            async for line in resp.content:
                status = json.loads(line.strip()) if line.strip() else {}
                if status.get("status") == "success":
                    return True
            return False


async def pull_model(model: str, base_url: str = OLLAMA_LOCAL):
    """Pull a model with progress tracking."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/pull",
            json={"model": model},
            timeout=aiohttp.ClientTimeout(total=3600),
        ) as resp:
            async for line in resp.content:
                if line.strip():
                    status = json.loads(line.strip())
                    yield status


async def running_models(base_url: str = OLLAMA_LOCAL) -> list[dict]:
    """List currently loaded models and their resource usage."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{base_url}/api/ps") as resp:
            data = await resp.json()
            return data.get("models", [])


async def preload_model(model: str, base_url: str = OLLAMA_LOCAL):
    """Preload model into memory (empty request)."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/chat",
            json={"model": model},
            timeout=TIMEOUT,
        ) as resp:
            await resp.read()


async def unload_model(model: str, base_url: str = OLLAMA_LOCAL):
    """Unload model from memory immediately."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/chat",
            json={"model": model, "keep_alive": 0},
            timeout=TIMEOUT,
        ) as resp:
            await resp.read()


# ===========================================================================
# 10. RATE-LIMITED CLOUD CLIENT
# ===========================================================================

@dataclass
class CloudQuota:
    """Track cloud usage against free tier limits."""
    max_per_session: int = 50
    max_per_week: int = 500
    session_count: int = 0
    weekly_count: int = 0
    session_start: float = field(default_factory=time.time)
    week_start: float = field(default_factory=time.time)
    last_request: float = 0.0
    backoff_until: float = 0.0
    consecutive_429s: int = 0

    def reset_if_needed(self):
        now = time.time()
        if now - self.session_start > 5 * 3600:
            self.session_count = 0
            self.session_start = now
            self.consecutive_429s = 0
        if now - self.week_start > 7 * 86400:
            self.weekly_count = 0
            self.week_start = now

    @property
    def utilization(self) -> float:
        self.reset_if_needed()
        return max(
            self.session_count / self.max_per_session,
            self.weekly_count / self.max_per_week,
        )


class RateLimitedCloudClient:
    """
    Ollama cloud client with adaptive rate limiting for free tier.
    Falls back to local model when rate limited.
    """

    def __init__(self, fallback_model: str = DEFAULT_MODEL):
        self.quota = CloudQuota()
        self.fallback_model = fallback_model
        self._lock = asyncio.Lock()

    def _interval(self) -> float:
        """Adaptive interval based on quota utilization."""
        u = self.quota.utilization
        if u < 0.3:
            return 3.0
        elif u < 0.5:
            return 6.0
        elif u < 0.8:
            return 15.0
        return 30.0

    async def chat(
        self,
        messages: list[dict],
        model: str = "gpt-oss:120b",
        **kwargs,
    ) -> dict:
        """Rate-limited cloud chat with local fallback."""
        async with self._lock:
            self.quota.reset_if_needed()

            now = time.time()

            # Check backoff
            if now < self.quota.backoff_until:
                return await self._local_fallback(messages, **kwargs)

            # Check quota
            if self.quota.utilization >= 0.9:
                return await self._local_fallback(messages, **kwargs)

            # Pace requests
            elapsed = now - self.quota.last_request
            interval = self._interval()
            if elapsed < interval:
                wait = interval - elapsed + random.uniform(0, interval * 0.3)
                await asyncio.sleep(wait)

        # Make cloud request
        try:
            result = await cloud_chat(messages, model, **kwargs)
            self.quota.session_count += 1
            self.quota.weekly_count += 1
            self.quota.last_request = time.time()
            self.quota.consecutive_429s = 0
            return result
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower():
                self.quota.consecutive_429s += 1
                backoff = min(30 * (2 ** (self.quota.consecutive_429s - 1)), 600)
                self.quota.backoff_until = time.time() + backoff + random.uniform(-5, 5)
            return await self._local_fallback(messages, **kwargs)

    async def _local_fallback(self, messages: list[dict], **kwargs) -> dict:
        """Fall back to local model."""
        payload = {
            "model": self.fallback_model,
            "messages": messages,
            "stream": False,
            **kwargs,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OLLAMA_LOCAL}/api/chat",
                json=payload,
                timeout=TIMEOUT,
            ) as resp:
                return await resp.json()

    @property
    def status(self) -> dict:
        self.quota.reset_if_needed()
        return {
            "session": f"{self.quota.session_count}/{self.quota.max_per_session}",
            "weekly": f"{self.quota.weekly_count}/{self.quota.max_per_week}",
            "utilization": f"{self.quota.utilization:.1%}",
            "interval": f"{self._interval():.1f}s",
            "backing_off": time.time() < self.quota.backoff_until,
        }


# ===========================================================================
# DEMO RUNNER
# ===========================================================================

async def run_all_demos():
    """Run all capability demonstrations."""
    print("\n" + "=" * 60)
    print("mindX Ollama Capability Demonstrations")
    print("=" * 60 + "\n")

    # Check connection first
    try:
        models = await list_local_models()
        print(f"Connected to Ollama. {len(models)} models available.")
        for m in models:
            print(f"  - {m['name']} ({m.get('details', {}).get('parameter_size', '?')})")
    except Exception as e:
        print(f"Cannot connect to Ollama at {OLLAMA_LOCAL}: {e}")
        print("Start Ollama with: ollama serve")
        return

    print()

    # Run demos that work with any model
    try:
        await demo_embeddings()
    except Exception as e:
        print(f"  Embeddings: {e}")

    print()

    try:
        await demo_structured_outputs()
    except Exception as e:
        print(f"  Structured outputs: {e}")

    print()

    try:
        await demo_thinking()
    except Exception as e:
        print(f"  Thinking: {e}")

    print()

    try:
        await demo_streaming()
    except Exception as e:
        print(f"  Streaming: {e}")

    print()

    try:
        await demo_tool_calling()
    except Exception as e:
        print(f"  Tool calling: {e}")

    print("\n" + "=" * 60)
    print("All demos complete.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all_demos())
