# Tool Calling (Function Calling)

> Models invoke tools and incorporate results into replies. Supports single, parallel, and multi-turn (agent loop) tool calling.

## Tool Definition Schema

```json
{
  "type": "function",
  "function": {
    "name": "get_temperature",
    "description": "Get the current temperature for a city",
    "parameters": {
      "type": "object",
      "required": ["city"],
      "properties": {
        "city": {"type": "string", "description": "The name of the city"}
      }
    }
  }
}
```

## Single Tool Call

### Python SDK

```python
from ollama import chat

def get_temperature(city: str) -> str:
    """Get the current temperature for a city
    
    Args:
        city: The name of the city
    Returns:
        The current temperature for the city
    """
    temperatures = {"New York": "22C", "London": "15C", "Tokyo": "18C"}
    return temperatures.get(city, "Unknown")

messages = [{"role": "user", "content": "What is the temperature in New York?"}]

# Python SDK auto-parses functions as tool schemas
response = chat(model="qwen3", messages=messages, tools=[get_temperature], think=True)

messages.append(response.message)
if response.message.tool_calls:
    call = response.message.tool_calls[0]
    result = get_temperature(**call.function.arguments)
    messages.append({"role": "tool", "tool_name": call.function.name, "content": str(result)})

    final = chat(model="qwen3", messages=messages, tools=[get_temperature], think=True)
    print(final.message.content)
```

**Key**: The Python SDK **auto-parses function docstrings** into tool schemas. Just pass functions directly.

### REST API

```bash
# Step 1: Model decides to call tool
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3",
  "messages": [{"role": "user", "content": "What is the temperature in New York?"}],
  "stream": false,
  "tools": [{
    "type": "function",
    "function": {
      "name": "get_temperature",
      "description": "Get the current temperature for a city",
      "parameters": {
        "type": "object",
        "required": ["city"],
        "properties": {"city": {"type": "string", "description": "City name"}}
      }
    }
  }]
}'

# Response includes tool_calls in message:
# "tool_calls": [{"type": "function", "function": {"name": "get_temperature", "arguments": {"city": "New York"}}}]

# Step 2: Send tool result back
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3",
  "messages": [
    {"role": "user", "content": "What is the temperature in New York?"},
    {"role": "assistant", "tool_calls": [{"type": "function", "function": {"index": 0, "name": "get_temperature", "arguments": {"city": "New York"}}}]},
    {"role": "tool", "tool_name": "get_temperature", "content": "22C"}
  ],
  "stream": false
}'
```

## Parallel Tool Calling

Model requests multiple tools at once:

```python
from ollama import chat

def get_temperature(city: str) -> str:
    """Get the current temperature for a city"""
    temperatures = {"New York": "22C", "London": "15C", "Tokyo": "18C"}
    return temperatures.get(city, "Unknown")

def get_conditions(city: str) -> str:
    """Get the current weather conditions for a city"""
    conditions = {"New York": "Partly cloudy", "London": "Rainy", "Tokyo": "Sunny"}
    return conditions.get(city, "Unknown")

messages = [{'role': 'user', 'content': 'Weather in New York and London?'}]
response = chat(model='qwen3', messages=messages, tools=[get_temperature, get_conditions], think=True)

messages.append(response.message)
if response.message.tool_calls:
    for call in response.message.tool_calls:
        if call.function.name == 'get_temperature':
            result = get_temperature(**call.function.arguments)
        elif call.function.name == 'get_conditions':
            result = get_conditions(**call.function.arguments)
        else:
            result = 'Unknown tool'
        messages.append({'role': 'tool', 'tool_name': call.function.name, 'content': str(result)})

    final = chat(model='qwen3', messages=messages, tools=[get_temperature, get_conditions], think=True)
    print(final.message.content)
```

## Multi-Turn Agent Loop

The model decides when to invoke tools and when it has enough info to respond:

```python
from ollama import chat, ChatResponse

def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b

available_functions = {'add': add, 'multiply': multiply}
messages = [{'role': 'user', 'content': 'What is (11434+12341)*412?'}]

while True:
    response: ChatResponse = chat(
        model='qwen3',
        messages=messages,
        tools=[add, multiply],
        think=True,
    )
    messages.append(response.message)
    
    if response.message.tool_calls:
        for tc in response.message.tool_calls:
            if tc.function.name in available_functions:
                result = available_functions[tc.function.name](**tc.function.arguments)
                messages.append({
                    'role': 'tool',
                    'tool_name': tc.function.name,
                    'content': str(result)
                })
    else:
        # No more tool calls — model has final answer
        print(response.message.content)
        break
```

## Tool Calling with Streaming

**Critical**: Accumulate `thinking`, `content`, and `tool_calls` from all chunks before processing.

```python
from ollama import chat

def get_temperature(city: str) -> str:
    """Get the current temperature for a city"""
    return {"New York": "22C", "London": "15C"}.get(city, "Unknown")

messages = [{'role': 'user', 'content': "Temperature in New York?"}]

while True:
    stream = chat(
        model='qwen3', messages=messages,
        tools=[get_temperature], stream=True, think=True,
    )

    thinking = ''
    content = ''
    tool_calls = []

    for chunk in stream:
        if chunk.message.thinking:
            thinking += chunk.message.thinking
        if chunk.message.content:
            content += chunk.message.content
        if chunk.message.tool_calls:
            tool_calls.extend(chunk.message.tool_calls)

    # Append accumulated assistant message
    if thinking or content or tool_calls:
        messages.append({
            'role': 'assistant', 'thinking': thinking,
            'content': content, 'tool_calls': tool_calls
        })

    if not tool_calls:
        break

    for call in tool_calls:
        result = get_temperature(**call.function.arguments) if call.function.name == 'get_temperature' else 'Unknown'
        messages.append({'role': 'tool', 'tool_name': call.function.name, 'content': result})
```

## mindX Integration

mindX tools already extend `BaseTool` with `execute()` and `get_schema()`. To bridge mindX tools with Ollama tool calling:

```python
from tools.base_tool import BaseTool

def mindx_tool_to_ollama_schema(tool: BaseTool) -> dict:
    """Convert a mindX BaseTool to Ollama tool definition."""
    schema = tool.get_schema()
    return {
        "type": "function",
        "function": {
            "name": schema.get("name", tool.__class__.__name__),
            "description": schema.get("description", ""),
            "parameters": schema.get("parameters", {
                "type": "object",
                "properties": {},
                "required": []
            })
        }
    }

async def execute_tool_calls(tool_calls: list, tool_registry: dict[str, BaseTool]) -> list[dict]:
    """Execute Ollama tool calls against mindX tool registry."""
    results = []
    for call in tool_calls:
        tool_name = call.function.name
        if tool_name in tool_registry:
            tool = tool_registry[tool_name]
            result = await tool.execute(**call.function.arguments)
            results.append({
                'role': 'tool',
                'tool_name': tool_name,
                'content': str(result)
            })
        else:
            results.append({
                'role': 'tool',
                'tool_name': tool_name,
                'content': f'Tool {tool_name} not found'
            })
    return results
```

### Supported Models for Tool Calling

Models with the `tools` tag support tool calling. Current cloud models with tools:
- qwen3.5, qwen3-coder-next, qwen3-next
- gemma4, glm-5, glm-5.1
- deepseek-v3.2, ministral-3, devstral-small-2
- nemotron-3-super, nemotron-3-nano
- kimi-k2.5, minimax-m2.7
