# Web Search Tool Documentation

## Overview

The `WebSearchTool` enables mindX agents to search the web using Google Custom Search JSON API. It provides a robust interface for retrieving real-time information from the internet, with graceful fallback to mock results when API credentials are unavailable.

**File**: `tools/web_search_tool.py`  
**Class**: `WebSearchTool`  
**Version**: 1.0.0  
**Status**: ✅ Active

## Architecture

### Design Principles

1. **API Integration**: Uses Google Custom Search JSON API for web searches
2. **Graceful Degradation**: Falls back to mock results when API keys are missing
3. **Async HTTP**: Uses `httpx` for async HTTP requests
4. **Error Handling**: Comprehensive error handling with informative messages
5. **Configurable**: Supports configuration via Config object and environment variables

### Core Components

```python
class WebSearchTool(BaseTool):
    - api_key: Google Search API key
    - search_engine_id: Custom Search Engine ID
    - http_client: httpx.AsyncClient for HTTP requests
    - config: Configuration object
```

## Configuration

### Required Environment Variables

- `GOOGLE_SEARCH_API_KEY`: Google Custom Search API key
- `GOOGLE_SEARCH_ENGINE_ID`: Custom Search Engine ID

### Configuration Options

```python
# In config file or environment
tools.web_search.google_api_key: "your_api_key"
tools.web_search.google_search_engine_id: "your_engine_id"
tools.web_search.timeout_seconds: 20.0
```

## Usage

### Basic Search

```python
from tools.web_search_tool import WebSearchTool
from utils.config import Config

config = Config()
tool = WebSearchTool(config=config)

# Execute search
results = await tool.execute(
    query="latest advancements in AI",
    num_results=5
)
```

### Advanced Usage

```python
# With custom parameters
results = await tool.execute(
    query="Python async programming best practices",
    num_results=10
)
```

## Response Format

### Successful Search

```
Search Results for: "query" (Time: 0.45s, Approx. Total: 1,000,000)

Result 1:
  Title: Result Title
  Link: https://example.com/article
  Snippet: Article snippet text...

Result 2:
  ...
```

### Error Response

```
Error: Web search API request failed with status 403. Detail: API key invalid
```

### Mock Results (No API Key)

```
Mock Search Results for: "query" (API Key/ID Not Configured or httpx missing)

Result 1:
  Title: Mock Result 1 - query
  Link: https://example.com/mocksearch?q=query&result=1
  Snippet: This is mock search result...
```

## Features

### 1. Google Custom Search Integration

- Uses official Google Custom Search JSON API
- Supports up to 10 results per query (API limit)
- Returns formatted search results with title, link, and snippet

### 2. Mock Results Fallback

When API keys are not configured:
- Generates realistic mock results
- Maintains same format as real results
- Useful for development and testing

### 3. Error Handling

- **Timeout Errors**: Handles request timeouts gracefully
- **HTTP Errors**: Provides detailed error messages
- **API Errors**: Extracts error details from API responses
- **General Exceptions**: Catches and reports unexpected errors

### 4. Result Formatting

- Formats results in readable text format
- Includes search metadata (time, total results)
- Provides structured result information

## API Details

### Google Custom Search API

**Endpoint**: `https://www.googleapis.com/customsearch/v1`

**Parameters**:
- `key`: API key
- `cx`: Search Engine ID
- `q`: Search query
- `num`: Number of results (1-10)

**Rate Limits**: 
- Free tier: 100 queries per day
- Paid tier: Higher limits available

## Security Considerations

1. **API Key Protection**: Store API keys in environment variables or secure config
2. **Request Validation**: Validates query input before sending
3. **Timeout Protection**: Prevents hanging requests
4. **Error Sanitization**: Doesn't expose sensitive information in errors

## Limitations

### Current Limitations

1. **Result Limit**: Maximum 10 results per query (API limitation)
2. **No Caching**: Every search makes a new API call
3. **No Pagination**: Cannot retrieve results beyond first page
4. **No Filtering**: No advanced search filters
5. **Single Provider**: Only supports Google Custom Search

### Recommended Improvements

1. **Result Caching**: Cache search results to reduce API calls
2. **Pagination Support**: Support for retrieving multiple pages
3. **Multiple Providers**: Support for other search engines
4. **Advanced Filters**: Date, language, region filters
5. **Result Parsing**: Parse structured data from results
6. **Rate Limiting**: Built-in rate limiting to respect API limits

## Integration

### With BDI Agents

```python
# In agent plan
plan = [
    {
        "action": "search_web",
        "query": "latest Python async features",
        "num_results": 5
    }
]
```

### With Other Tools

The WebSearchTool can be used by:
- Research agents for gathering information
- Documentation agents for finding examples
- Analysis agents for market research

## Examples

### Simple Search

```python
results = await tool.execute("mindX autonomous agents")
print(results)
```

### Research Query

```python
results = await tool.execute(
    query="autonomous AI systems 2024",
    num_results=10
)
```

## Technical Details

### Dependencies

- `httpx`: Async HTTP client library
- `core.bdi_agent.BaseTool`: Base tool class
- `utils.config.Config`: Configuration management
- `utils.logging_config.get_logger`: Logging utility

### Error Handling

```python
try:
    response = await self.http_client.get(search_url, params=params)
    response.raise_for_status()
    results_json = response.json()
    return self._format_google_search_results(results_json, query)
except httpx.TimeoutException as e:
    return f"Error: Web search request timed out. ({e})"
except httpx.HTTPStatusError as e:
    return f"Error: Web search API request failed with status {e.response.status_code}"
except Exception as e:
    return f"Error: Unexpected error during web search - {type(e).__name__}: {e}"
```

### Shutdown

The tool properly closes HTTP client on shutdown:

```python
async def shutdown(self):
    if self.http_client and not self.http_client.is_closed:
        await self.http_client.aclose()
```

## Future Enhancements

1. **Multi-Provider Support**: Support Bing, DuckDuckGo, etc.
2. **Result Caching**: Cache results with TTL
3. **Advanced Queries**: Support for complex search queries
4. **Result Ranking**: Custom result ranking algorithms
5. **Image Search**: Support for image search
6. **News Search**: Specialized news search functionality
7. **Academic Search**: Integration with academic search engines
