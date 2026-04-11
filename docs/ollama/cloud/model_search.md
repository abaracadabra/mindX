# Programmatic Cloud Model Search

> Stay current with Ollama cloud model availability. Discover new models, track capabilities, feed into mindX model rating.

**Important**: The catalog at `ollama.com/api/tags` returns model names without the `-cloud` suffix (e.g., `gpt-oss:120b`). To use these via [free-tier local offload](../INDEX.md#the--cloud-suffix), append `-cloud` when pulling: `ollama pull gpt-oss:120b-cloud`. See [How Cloud Works](../INDEX.md#how-cloud-works-without-an-api-key) for the full mechanism.

## Discovery Methods

### 1. List Cloud Models via API

```python
import aiohttp
import os

async def list_cloud_models(api_key: str = None) -> list[dict]:
    """List all models available on Ollama cloud."""
    api_key = api_key or os.environ.get("OLLAMA_API_KEY")
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://ollama.com/api/tags",
            headers=headers
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("models", [])
            return []
```

### 2. Search Cloud Models via Web Search API

```python
from ollama import web_search, web_fetch

async def discover_cloud_models() -> list[dict]:
    """Discover cloud-available models via web search + page scraping."""
    # Search for cloud models
    results = web_search("ollama cloud models", max_results=5)
    
    # Fetch the cloud search page
    page = web_fetch("https://ollama.com/search?c=cloud")
    
    return {
        "search_results": results,
        "page_content": page.content if page else None,
        "page_links": page.links if page else []
    }
```

### 3. Show Model Capabilities

```python
async def get_model_capabilities(model_name: str) -> dict:
    """Get detailed capabilities for a specific model."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:11434/api/show",
            json={"model": model_name, "verbose": True}
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {
                    "capabilities": data.get("capabilities", []),
                    "details": data.get("details", {}),
                    "parameters": data.get("parameters", ""),
                    "model_info": data.get("model_info", {})
                }
            return {}
```

## Complete Model Discovery Service

```python
import aiohttp
import os
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

@dataclass
class CloudModel:
    """Discovered cloud model with capabilities and rating data."""
    name: str
    parameter_size: str = ""
    family: str = ""
    capabilities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    quantization: str = ""
    pull_count: int = 0
    discovered_at: float = 0.0
    last_checked: float = 0.0
    cloud_available: bool = True
    
    # mindX rating fields (Modelfile schema alignment)
    task_scores: dict = field(default_factory=dict)
    agent_assignments: list[str] = field(default_factory=list)

class OllamaCloudModelDiscovery:
    """
    Programmatic discovery and tracking of Ollama cloud models.
    Integrates with mindX model rating and agent assignment.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_path: str = "data/config/cloud_models_cache.json",
        refresh_interval: int = 3600 * 6  # 6 hours
    ):
        self.api_key = api_key or os.environ.get("OLLAMA_API_KEY", "")
        self.cache_path = Path(cache_path)
        self.refresh_interval = refresh_interval
        self.models: dict[str, CloudModel] = {}
        self._load_cache()
    
    def _load_cache(self):
        """Load cached model data."""
        if self.cache_path.exists():
            try:
                data = json.loads(self.cache_path.read_text())
                for name, mdata in data.items():
                    self.models[name] = CloudModel(**mdata)
            except (json.JSONDecodeError, TypeError):
                pass
    
    def _save_cache(self):
        """Persist model data to disk."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        data = {name: asdict(m) for name, m in self.models.items()}
        self.cache_path.write_text(json.dumps(data, indent=2))
    
    def _needs_refresh(self) -> bool:
        """Check if cache is stale."""
        if not self.models:
            return True
        oldest = min(m.last_checked for m in self.models.values()) if self.models else 0
        return (time.time() - oldest) > self.refresh_interval
    
    async def discover(self, force: bool = False) -> list[CloudModel]:
        """Discover cloud models. Returns list of new/updated models."""
        if not force and not self._needs_refresh():
            return list(self.models.values())
        
        new_models = []
        now = time.time()
        
        # Method 1: API tags endpoint
        if self.api_key:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://ollama.com/api/tags",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            for m in data.get("models", []):
                                name = m.get("name", "")
                                if name not in self.models:
                                    model = CloudModel(
                                        name=name,
                                        parameter_size=m.get("details", {}).get("parameter_size", ""),
                                        family=m.get("details", {}).get("family", ""),
                                        quantization=m.get("details", {}).get("quantization_level", ""),
                                        discovered_at=now,
                                        last_checked=now,
                                        cloud_available=True
                                    )
                                    self.models[name] = model
                                    new_models.append(model)
                                else:
                                    self.models[name].last_checked = now
                                    self.models[name].cloud_available = True
            except Exception:
                pass  # Graceful degradation
        
        self._save_cache()
        return new_models if new_models else list(self.models.values())
    
    def get_models_by_capability(self, capability: str) -> list[CloudModel]:
        """Filter models by capability tag (tools, thinking, vision, cloud)."""
        return [m for m in self.models.values() 
                if capability in m.tags or capability in m.capabilities]
    
    def get_best_for_task(self, task: str) -> Optional[CloudModel]:
        """Get highest-rated cloud model for a given task type."""
        candidates = [m for m in self.models.values() 
                     if task in m.task_scores and m.cloud_available]
        if not candidates:
            return None
        return max(candidates, key=lambda m: m.task_scores.get(task, 0))
    
    def update_task_score(self, model_name: str, task: str, score: float):
        """Update a model's task score based on feedback."""
        if model_name in self.models:
            self.models[model_name].task_scores[task] = score
            self._save_cache()
    
    def assign_to_agent(self, model_name: str, agent_name: str):
        """Record that an agent is assigned to use this model."""
        if model_name in self.models:
            if agent_name not in self.models[model_name].agent_assignments:
                self.models[model_name].agent_assignments.append(agent_name)
                self._save_cache()
```

## Known Cloud Models (2026-04-11 snapshot)

From `https://ollama.com/api/tags`:

```
kimi-k2-thinking, gpt-oss:120b, qwen3-vl:235b-instruct, minimax-m2.7,
minimax-m2.5, ministral-3:14b, gemma3:4b, nemotron-3-super, cogito-2.1:671b,
glm-5, deepseek-v3.2, deepseek-v3.1:671b, qwen3-vl:235b, minimax-m2.1,
devstral-2:123b, devstral-small-2:24b, kimi-k2.5, qwen3-next:80b,
ministral-3:8b, gemma3:27b, nemotron-3-nano:30b, gemini-3-flash-preview,
gemma4:31b, rnj-1:8b, qwen3-coder:480b, ministral-3:3b,
mistral-large-3:675b, qwen3.5:397b, glm-4.7, glm-5.1, gpt-oss:20b,
kimi-k2:1t, qwen3-coder-next, minimax-m2, glm-4.6, gemma3:12b
```

## Integration with Modelfile Schema

See [setup/modelfile.md](../setup/modelfile.md) for how Modelfile parameters serve as the canonical schema for model collection, rating, and agent alignment towards Chimaiera.
