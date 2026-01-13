# Token Calculator Tool (Robust) Documentation

## Overview

The `TokenCalculatorToolRobust` is an enhanced token calculator with improved robustness, error handling, and accuracy. It provides accurate token counting using tiktoken, comprehensive validation, thread-safe operations, and currency precision.

**File**: `tools/token_calculator_tool_robust.py`  
**Class**: `TokenCalculatorToolRobust`  
**Version**: 1.0.0  
**Status**: ✅ Active

## Architecture

### Design Principles

1. **Accuracy**: Uses tiktoken for accurate token counting
2. **Robustness**: Comprehensive error handling and validation
3. **Thread Safety**: Thread-safe operations with file locking
4. **Currency Precision**: Uses Decimal for precise calculations
5. **Caching**: Token counting cache for performance
6. **Rate Limiting**: Prevents API abuse

### Core Components

```python
class TokenCalculatorToolRobust(BaseTool):
    - memory_agent: MemoryAgent - For workspace management
    - pricing_data: Dict - LLM pricing configuration
    - _tokenizers: Dict - Tokenizer instances
    - _cache: Dict - Token counting cache
    - _lock: RLock - Thread safety lock
```

## Key Features

### 1. Accurate Token Counting

Uses `tiktoken` library for:
- Accurate token counting per model
- Model-specific tokenizers
- Fast tokenization
- Reliable counts

### 2. Comprehensive Validation

Validates:
- Currency values (Decimal precision)
- Percentage values (0-1 range)
- Token counts (non-negative, reasonable limits)
- Model names (format validation)

### 3. Thread Safety

Thread-safe operations:
- RLock for file operations
- Safe concurrent access
- Prevents race conditions

### 4. Currency Precision

Uses Decimal for:
- Precise cost calculations
- No floating-point errors
- Accurate budget tracking

### 5. Caching

Token counting cache:
- Reduces redundant calculations
- Configurable TTL (default: 5 minutes)
- Performance optimization

### 6. Rate Limiting

Prevents API abuse:
- Max calls per minute (default: 60)
- Automatic throttling
- Request tracking

## Usage

### Calculate Token Cost

```python
from tools.token_calculator_tool_robust import TokenCalculatorToolRobust
from agents.memory_agent import MemoryAgent

tool = TokenCalculatorToolRobust(memory_agent=memory_agent)

# Calculate cost
success, result = await tool.execute(
    operation="calculate_cost",
    model="gpt-4",
    prompt_tokens=1000,
    completion_tokens=500
)
```

### Track Usage

```python
# Track token usage
success, result = await tool.execute(
    operation="track_usage",
    model="gpt-4",
    prompt_tokens=1000,
    completion_tokens=500
)
```

## Configuration

### Pricing Config

Located at:
```
config/llm_pricing_config.json
```

### Usage Log

Stored at:
```
data/monitoring/token_usage.json
```

### Cache

Stored at:
```
data/monitoring/token_cache.json
```

## Limitations

### Current Limitations

1. **tiktoken Dependency**: Requires tiktoken for accuracy
2. **Limited Models**: May not support all models
3. **Basic Caching**: Simple cache implementation
4. **No Historical Analysis**: No trend analysis
5. **Single System**: Single system only

### Recommended Improvements

1. **More Models**: Support more LLM models
2. **Advanced Caching**: Better cache strategies
3. **Historical Analysis**: Trend tracking
4. **Multi-System**: Support distributed systems
5. **Real-Time Alerts**: Budget alerts
6. **Visualization**: Charts and graphs
7. **API Integration**: REST API access

## Integration

### With Memory Agent

Uses memory agent for:
- Workspace management
- Usage logging
- Data persistence

## Examples

### Budget Tracking

```python
# Check budget status
success, status = await tool.execute(
    operation="check_budget",
    period="daily"
)
```

## Technical Details

### Dependencies

- `tiktoken`: Accurate token counting (optional but recommended)
- `decimal.Decimal`: Currency precision
- `threading.RLock`: Thread safety
- `agents.memory_agent.MemoryAgent`: Workspace management

### Tokenizer Initialization

Initializes tokenizers for:
- OpenAI models (gpt-3.5, gpt-4, etc.)
- Anthropic models (claude, etc.)
- Other supported models

## Future Enhancements

1. **More Models**: Expand model support
2. **Advanced Analytics**: Trend analysis
3. **Real-Time Alerts**: Budget alerts
4. **Visualization**: Charts and dashboards
5. **API Integration**: REST API
6. **Multi-System**: Distributed tracking
7. **Predictive Budgeting**: ML-based predictions



