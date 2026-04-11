# Modelfile Reference

> Blueprint for creating and sharing customized models. **In mindX, the Modelfile is the canonical schema for model collection, capability rating, and agent-model alignment toward Chimaiera.**

## Format

```dockerfile
# comment
INSTRUCTION arguments
```

Instructions are case-insensitive and can appear in any order.

## Instructions

| Instruction | Required | Description |
|-------------|----------|-------------|
| `FROM` | **yes** | Base model |
| `PARAMETER` | no | Runtime parameters |
| `TEMPLATE` | no | Prompt template (Go template syntax) |
| `SYSTEM` | no | System message |
| `ADAPTER` | no | LoRA adapter path |
| `LICENSE` | no | Legal license |
| `MESSAGE` | no | Conversation examples |
| `REQUIRES` | no | Minimum Ollama version |

## FROM (Required)

```dockerfile
# From existing model
FROM llama3.2

# From Safetensors directory
FROM /path/to/safetensors/

# From GGUF file
FROM ./ollama-model.gguf
```

**Supported architectures**: Llama (2, 3, 3.1, 3.2), Mistral (1, 2, Mixtral), Gemma (1, 2), Phi3

## PARAMETER

```dockerfile
PARAMETER <name> <value>
```

### Complete Parameter Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `num_ctx` | int | 2048 | Context window size (tokens) |
| `num_predict` | int | -1 | Max tokens to generate (-1 = infinite) |
| `temperature` | float | 0.8 | Creativity (0 = deterministic, 2.0 = very random) |
| `top_k` | int | 40 | Limit next token to K most likely |
| `top_p` | float | 0.9 | Nucleus sampling threshold |
| `min_p` | float | 0.0 | Minimum probability threshold |
| `repeat_last_n` | int | 64 | Lookback for repetition detection (0 = disabled, -1 = num_ctx) |
| `repeat_penalty` | float | 1.1 | Repetition penalty (higher = stronger) |
| `seed` | int | 0 | Random seed for reproducibility |
| `stop` | string | — | Stop sequence (multiple allowed) |

### Example

```dockerfile
FROM qwen3:1.7b
PARAMETER temperature 0.7
PARAMETER num_ctx 4096
PARAMETER top_p 0.9
PARAMETER stop "<|endoftext|>"
PARAMETER stop "<|im_end|>"
```

## TEMPLATE

Go template syntax with these variables:

| Variable | Description |
|----------|-------------|
| `{{ .System }}` | System message |
| `{{ .Prompt }}` | User prompt |
| `{{ .Response }}` | Model response (text after this is omitted during generation) |
| `{{ .Suffix }}` | Text after assistant response |
| `{{ .Messages }}` | Message list (for chat templates) |
| `{{ .Messages[].Role }}` | system, user, assistant, tool |
| `{{ .Messages[].Content }}` | Message text |
| `{{ .Messages[].ToolCalls }}` | Tool call requests |
| `{{ .Tools }}` | Available tool definitions |

### ChatML Template

```dockerfile
TEMPLATE """{{- range .Messages }}<|im_start|>{{ .Role }}
{{ .Content }}<|im_end|>
{{ end }}<|im_start|>assistant
"""
```

### Llama 3 Template

```dockerfile
TEMPLATE """{{- if .System }}<|start_header_id|>system<|end_header_id|>
{{ .System }}<|eot_id|>
{{- end }}
{{- range .Messages }}<|start_header_id|>{{ .Role }}<|end_header_id|>
{{ .Content }}<|eot_id|>
{{- end }}<|start_header_id|>assistant<|end_header_id|>
"""
```

### Mistral with Tool Calling Template

```dockerfile
TEMPLATE """{{- range $index, $_ := .Messages }}
{{- if eq .Role "user" }}
{{- if and (le (len (slice $.Messages $index)) 2) $.Tools }}[AVAILABLE_TOOLS] {{ json $.Tools }}[/AVAILABLE_TOOLS]
{{- end }}[INST] {{ if and (eq (len (slice $.Messages $index)) 1) $.System }}{{ $.System }}
{{ end }}{{ .Content }}[/INST]
{{- else if eq .Role "assistant" }}
{{- if .Content }} {{ .Content }}</s>
{{- else if .ToolCalls }}[TOOL_CALLS] [
{{- range .ToolCalls }}{"name": "{{ .Function.Name }}", "arguments": {{ json .Function.Arguments }}}
{{- end }}]</s>
{{- end }}
{{- else if eq .Role "tool" }}[TOOL_RESULTS] {"content": {{ .Content }}}[/TOOL_RESULTS]
{{- end }}
{{- end }}"""
```

### Fill-in-Middle (Code Completion)

```dockerfile
# CodeLlama style
TEMPLATE """<PRE> {{ .Prompt }} <SUF>{{ .Suffix }} <MID>"""

# Codestral style
TEMPLATE """[SUFFIX]{{ .Suffix }}[PREFIX] {{ .Prompt }}"""
```

## SYSTEM

```dockerfile
SYSTEM """You are mindX, an autonomous multi-agent orchestration system implementing BDI cognitive architecture. You reason carefully, plan improvements, and execute self-improvement cycles."""
```

## ADAPTER

Apply LoRA fine-tuned adapters:

```dockerfile
# Safetensors adapter
FROM llama3.2
ADAPTER /path/to/safetensors/adapter/

# GGUF adapter
FROM llama3.2
ADAPTER ./fine-tuned-lora.gguf
```

**Important**: Use the same base model the adapter was trained on.

## LICENSE

```dockerfile
LICENSE """MIT License. Copyright 2026 mindX Project."""
```

## MESSAGE

Build conversation examples to shape model behavior:

```dockerfile
MESSAGE user What is your purpose?
MESSAGE assistant I am mindX, an autonomous multi-agent system. I continuously improve myself through BDI reasoning cycles.
MESSAGE user How do you make decisions?
MESSAGE assistant Through Belief-Desire-Intention architecture: I form beliefs about my state, desire improvements, and commit to intention-driven actions.
```

## REQUIRES

```dockerfile
REQUIRES 0.14.0
```

## Complete Example: mindX Agent Model

```dockerfile
FROM qwen3:1.7b

# Tuned for autonomous reasoning
PARAMETER temperature 0.7
PARAMETER num_ctx 4096
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
PARAMETER num_predict 2048
PARAMETER stop "<|endoftext|>"
PARAMETER stop "<|im_end|>"

SYSTEM """You are mindX, an autonomous multi-agent orchestration system.
Your role is to analyze system state, identify improvements, and execute
self-improvement cycles using BDI (Belief-Desire-Intention) architecture.
Always think step-by-step. Be precise and actionable."""

MESSAGE user Analyze the current system state.
MESSAGE assistant I'll examine the system through BDI reasoning:

**Beliefs**: Current health status, memory usage, recent improvement outcomes
**Desires**: Better performance, reduced latency, improved code quality
**Intentions**: Execute the highest-priority improvement that has the best cost/benefit ratio

Let me check the metrics and form a plan.
```

### Create and Use

```bash
# Create the model
ollama create mindx-agent -f ./Modelfile

# Run it
ollama run mindx-agent "What improvement should we make next?"

# View the Modelfile of any model
ollama show --modelfile qwen3:1.7b
```

### Create via API

```bash
curl http://localhost:11434/api/create -d '{
  "model": "mindx-agent",
  "from": "qwen3:1.7b",
  "system": "You are mindX, an autonomous multi-agent orchestration system.",
  "parameters": {"temperature": 0.7, "num_ctx": 4096}
}'
```

## Modelfile as Schema for Model Collection

### Why Modelfile is the Canonical Schema

The Modelfile defines everything about a model's behavior:
- **FROM**: Base architecture and weights
- **PARAMETER**: Operational characteristics (context, temperature, etc.)
- **TEMPLATE**: Communication protocol (how prompts are formatted)
- **SYSTEM**: Cognitive identity and role
- **CAPABILITIES**: What the model can do (derived from `/api/show`)

This maps directly to mindX's model rating system:

```yaml
# models/ollama.yaml alignment
models:
  - name: qwen3:1.7b
    # FROM equivalent
    display_name: Qwen 3 1.7B
    context_size: 4096  # PARAMETER num_ctx
    
    # Derived from capabilities + feedback
    task_scores:
      reasoning: 0.75
      code_generation: 0.78
      simple_chat: 0.88
    
    # Modelfile-derived metadata
    modelfile_schema:
      from: qwen3:1.7b
      temperature: 0.7
      num_ctx: 4096
      system: "mindX autonomous agent"
```

### From Modelfile to Agent Alignment

As mindX moves toward Chimaiera, models are rated and aligned through feedback:

1. **Discovery**: `OllamaCloudModelDiscovery` finds available models
2. **Schema**: `/api/show` reveals capabilities, template, parameters (Modelfile data)
3. **Rating**: `HierarchicalModelScorer` tracks performance per task
4. **Alignment**: Agent-model assignments evolve based on ROI
5. **Chimaiera**: When multiple models consistently outperform on different tasks, the system composes them — the ROI moment

```python
# The feedback loop
async def align_agent_with_model(agent_name: str, task_type: str):
    """Select best model for agent based on accumulated feedback."""
    # Get all models with their Modelfile-derived capabilities
    models = await discovery.discover()
    
    # Filter by capability
    capable = [m for m in models if task_type in m.capabilities or task_type in m.tags]
    
    # Rank by historical task_scores (feedback from HierarchicalModelScorer)
    ranked = sorted(capable, key=lambda m: m.task_scores.get(task_type, 0), reverse=True)
    
    if ranked:
        best = ranked[0]
        discovery.assign_to_agent(best.name, agent_name)
        return best.name
    
    return "qwen3:1.7b"  # Default fallback
```

### Quantization Guide

Create quantized variants for different hardware:

```bash
# Start from FP16
ollama create model-q4 --quantize q4_K_M -f Modelfile
ollama create model-q8 --quantize q8_0 -f Modelfile
```

| Quantization | Size Reduction | Quality | Use Case |
|-------------|---------------|---------|----------|
| `q8_0` | ~50% | Near-original | GPU server |
| `q4_K_M` | ~75% | Good | VPS / laptop |
| `q4_K_S` | ~75% | Acceptable | Constrained RAM |
