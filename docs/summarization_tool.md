# Summarization Tool Documentation

## Overview

The `SummarizationTool` provides intelligent text summarization capabilities using Large Language Models (LLMs). It enables mindX agents to condense large amounts of text into concise summaries while maintaining key information and context.

**File**: `tools/summarization_tool.py`  
**Class**: `SummarizationTool`  
**Version**: 1.0.0  
**Status**: ✅ Active

## Architecture

### Design Principles

1. **LLM-Powered**: Uses LLM for intelligent summarization
2. **Configurable**: Supports various summary formats and lengths
3. **Context-Aware**: Can incorporate topic context for better summaries
4. **Error Handling**: Graceful handling of LLM failures
5. **Input Truncation**: Handles very long texts intelligently

### Core Components

```python
class SummarizationTool(BaseTool):
    - llm_handler: LLMHandlerInterface - LLM for text generation
    - config: Config - Configuration object
    - logger: Logger - For operation logging
```

## Usage

### Basic Summarization

```python
from tools.summarization_tool import SummarizationTool
from llm.llm_interface import LLMHandlerInterface

tool = SummarizationTool(
    config=config,
    llm_handler=llm_handler
)

# Summarize text
summary = await tool.execute(
    text_to_summarize="Long text content...",
    max_summary_words=150
)
```

### Advanced Usage

```python
# With topic context and custom format
summary = await tool.execute(
    text_to_summarize="Technical documentation...",
    topic_context="Python async programming",
    max_summary_words=200,
    output_format="bullet_points",
    temperature=0.3,
    custom_instructions="Focus on key concepts and examples"
)
```

## Parameters

### Required Parameters

- `text_to_summarize` (str): The text content to be summarized

### Optional Parameters

- `topic_context` (str): Context about the topic for better summarization
- `max_summary_words` (int): Maximum words for summary (default: 150)
- `output_format` (str): "paragraph" or "bullet_points" (default: "paragraph")
- `temperature` (float): LLM generation temperature (default: from config)
- `custom_instructions` (str): Additional instructions for the LLM

## Output Formats

### Paragraph Format

Returns a coherent paragraph summary:
```
The text discusses the implementation of async programming in Python,
focusing on asyncio and coroutines. Key concepts include event loops,
awaitables, and concurrent execution patterns...
```

### Bullet Points Format

Returns a bulleted list:
```
- Async programming enables concurrent execution in Python
- asyncio provides the event loop and coroutine framework
- Key concepts include awaitables and async/await syntax
- Best practices involve proper error handling and resource management
```

## Features

### 1. Intelligent Truncation

For very long texts:
- Truncates to configurable max length
- Preserves beginning and end of text
- Adds truncation indicator

```python
max_input_chars = self.config.get("tools.summarization.max_input_chars", 30000)
if len(text_to_summarize) > max_input_chars:
    text_to_summarize = (
        text_to_summarize[:max_input_chars//2] + 
        f"\n... (TEXT TRUNCATED DUE TO LENGTH) ...\n" + 
        text_to_summarize[-(max_input_chars//2):]
    )
```

### 2. Context-Aware Summarization

Incorporates topic context for better summaries:
```python
if topic:
    prompt_lines.append(f"The text is about: {topic}.")
```

### 3. Configurable Output

Supports multiple output formats:
- Paragraph summaries
- Bullet point lists
- Custom formats via instructions

### 4. Token Estimation

Estimates token requirements:
```python
max_tokens_for_summary = int(max_summary_words * 2.5)
```

## Configuration

### Config Options

```python
tools.summarization.max_input_chars: 30000  # Max input text length
tools.summarization.llm.temperature: 0.2   # Default temperature
```

## Limitations

### Current Limitations

1. **Single-Pass**: Doesn't use map-reduce for very long texts
2. **No Multi-Document**: Cannot summarize multiple documents
3. **No Extraction**: Doesn't extract key phrases or entities
4. **No Comparison**: Cannot compare multiple summaries
5. **Fixed Model**: Uses single LLM model

### Recommended Improvements

1. **Map-Reduce**: Support for very long texts using map-reduce
2. **Multi-Document**: Summarize multiple related documents
3. **Key Extraction**: Extract key phrases and entities
4. **Summary Comparison**: Compare multiple summaries
5. **Model Selection**: Support for different LLM models
6. **Summary Caching**: Cache summaries for repeated queries
7. **Quality Metrics**: Measure summary quality and completeness

## Integration

### With BDI Agents

```python
# In agent plan
plan = [
    {
        "action": "summarize_text",
        "text_to_summarize": long_text,
        "max_summary_words": 200,
        "output_format": "bullet_points"
    }
]
```

### With Other Tools

The SummarizationTool can be used with:
- **NoteTakingTool**: Summarize notes
- **WebSearchTool**: Summarize search results
- **BaseGenAgent**: Summarize codebase documentation

## Examples

### Summarize Documentation

```python
summary = await tool.execute(
    text_to_summarize=documentation_text,
    topic_context="API documentation",
    max_summary_words=100
)
```

### Create Bullet Summary

```python
summary = await tool.execute(
    text_to_summarize=article_text,
    output_format="bullet_points",
    max_summary_words=50
)
```

### Technical Summary

```python
summary = await tool.execute(
    text_to_summarize=technical_doc,
    topic_context="system architecture",
    custom_instructions="Focus on technical details and implementation",
    temperature=0.1  # Lower temperature for more factual summaries
)
```

## Technical Details

### Dependencies

- `llm.llm_interface.LLMHandlerInterface`: LLM handler
- `core.bdi_agent.BaseTool`: Base tool class
- `utils.config.Config`: Configuration management

### Prompt Construction

```python
prompt_lines = [
    "You are an expert summarization AI...",
    f"The text is about: {topic}.",
    f"The summary should be approximately {max_words} words or less.",
    "Focus on extracting the most critical information...",
    "\nText to Summarize:\n---BEGIN TEXT---",
    text,
    "---END TEXT---\n\nConcise Summary:"
]
```

### Error Handling

```python
try:
    summary_result = await self.llm_handler.generate_text(...)
    if summary_result and not summary_result.lower().startswith("error:"):
        return summary_result.strip()
    else:
        return f"Error: LLM failed to generate summary - {summary_result}"
except Exception as e:
    return f"Error: Exception during summarization - {type(e).__name__}: {e}"
```

## Future Enhancements

1. **Multi-Document Summarization**: Summarize multiple related documents
2. **Abstractive vs Extractive**: Support both summarization approaches
3. **Summary Quality Metrics**: Measure summary quality
4. **Custom Templates**: Support for custom summary templates
5. **Language Support**: Multi-language summarization
6. **Domain-Specific**: Specialized summaries for different domains
7. **Interactive Summarization**: Refine summaries based on feedback
