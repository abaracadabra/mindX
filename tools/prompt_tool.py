# mindx/tools/prompt_tool.py
"""
Prompt Tool for MindX.

This tool enables the management, storage, and execution of prompts within the mindX system.
Prompts are treated as first-class infrastructure, stored in memory, and can be versioned,
shared, and executed by agents.

Following mindX doctrine:
- Memory is infrastructure
- Prompts are executable interfaces
- All prompts are persisted and queryable
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict

from agents.core.bdi_agent import BaseTool
from agents.memory_agent import MemoryAgent
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)


class PromptType(Enum):
    """Types of prompts in the system."""
    SYSTEM = "system"
    AGENT = "agent"
    USER = "user"
    TEMPLATE = "template"
    INCEPTION = "inception"
    INSTRUCTION = "instruction"


class PromptCategory(Enum):
    """Categories for organizing prompts."""
    MARKETING = "marketing"
    COMMUNITY = "community"
    DEVELOPMENT = "development"
    COGNITION = "cognition"
    EXECUTION = "execution"
    GOVERNANCE = "governance"


@dataclass
class PromptMetadata:
    """Metadata for a prompt."""
    prompt_id: str
    name: str
    description: str
    prompt_type: PromptType
    category: Optional[PromptCategory]
    version: str
    author: str
    created_at: str
    updated_at: str
    tags: List[str]
    usage_count: int = 0
    last_used: Optional[str] = None
    parent_prompt_id: Optional[str] = None
    variables: List[str] = None  # Template variables
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = []


class PromptTool(BaseTool):
    """
    Prompt Tool - Manages prompts as infrastructure.
    
    Prompts are stored in memory, versioned, and can be executed by agents.
    This tool enables the mindX system to treat prompts as first-class
    cognitive assets that persist and evolve.
    """
    
    def __init__(self,
                 memory_agent: MemoryAgent,
                 config: Optional[Config] = None,
                 **kwargs):
        super().__init__(config=config, **kwargs)
        self.memory_agent = memory_agent
        self.config = config or Config()
        self.project_root = PROJECT_ROOT
        
        # Prompt storage paths
        self.prompts_path = self.project_root / "data" / "prompts"
        self.prompts_path.mkdir(parents=True, exist_ok=True)
        
        # Registry file
        self.registry_path = self.prompts_path / "prompt_registry.json"
        self.prompt_registry: Dict[str, PromptMetadata] = {}
        
        # Load existing registry
        self._load_registry()
        
        logger.info("PromptTool initialized")
    
    def _load_registry(self):
        """Load the prompt registry from disk."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as json_file:
                    data = json.load(json_file)
                    for prompt_id, meta_dict in data.items():
                        meta_dict['prompt_type'] = PromptType(meta_dict['prompt_type'])
                        if meta_dict.get('category'):
                            meta_dict['category'] = PromptCategory(meta_dict['category'])
                        self.prompt_registry[prompt_id] = PromptMetadata(**meta_dict)
                logger.info(f"Loaded {len(self.prompt_registry)} prompts from registry")
            except Exception as e:
                logger.error(f"Error loading prompt registry: {e}")
    
    def _save_registry(self):
        """Save the prompt registry to disk."""
        try:
            data = {}
            for prompt_id, metadata in self.prompt_registry.items():
                meta_dict = asdict(metadata)
                meta_dict['prompt_type'] = metadata.prompt_type.value
                if metadata.category:
                    meta_dict['category'] = metadata.category.value
                data[prompt_id] = meta_dict
            
            with open(self.registry_path, 'w') as json_file:
                json.dump(data, json_file, indent=2)
        except Exception as e:
            logger.error(f"Error saving prompt registry: {e}")
    
    def _generate_prompt_id(self, name: str, content: str) -> str:
        """Generate a unique prompt ID."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
        name_slug = name.lower().replace(' ', '_').replace('-', '_')
        return f"{name_slug}_{content_hash}"
    
    def _save_prompt_file(self, prompt_id: str, content: str):
        """Save prompt content to file."""
        prompt_file = self.prompts_path / f"{prompt_id}.prompt"
        prompt_file.write_text(content, encoding='utf-8')
    
    def _load_prompt_file(self, prompt_id: str) -> Optional[str]:
        """Load prompt content from file."""
        prompt_file = self.prompts_path / f"{prompt_id}.prompt"
        if prompt_file.exists():
            return prompt_file.read_text(encoding='utf-8')
        return None
    
    async def execute(self, operation: str, **kwargs) -> Dict[str, Any]:
        """
        Execute prompt tool operations.
        
        Operations:
        - create: Create a new prompt
        - get: Retrieve a prompt by ID
        - update: Update an existing prompt
        - delete: Delete a prompt
        - list: List all prompts (with optional filters)
        - execute: Execute a prompt with variables
        - search: Search prompts by content or metadata
        - version: Create a new version of a prompt
        - ingest: Ingest a prompt from external source (e.g., AgenticPlace)
        """
        try:
            if operation == "create":
                return await self._create_prompt(**kwargs)
            elif operation == "get":
                return await self._get_prompt(**kwargs)
            elif operation == "update":
                return await self._update_prompt(**kwargs)
            elif operation == "delete":
                return await self._delete_prompt(**kwargs)
            elif operation == "list":
                return await self._list_prompts(**kwargs)
            elif operation == "execute":
                return await self._execute_prompt(**kwargs)
            elif operation == "search":
                return await self._search_prompts(**kwargs)
            elif operation == "version":
                return await self._version_prompt(**kwargs)
            elif operation == "ingest":
                return await self._ingest_prompt(**kwargs)
            else:
                return {
                    "success": False,
                    "error": f"Unknown operation: {operation}"
                }
        except Exception as e:
            logger.error(f"Error executing prompt tool operation {operation}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _create_prompt(self,
                            name: str,
                            content: str,
                            description: str = "",
                            prompt_type: str = "agent",
                            category: Optional[str] = None,
                            tags: Optional[List[str]] = None,
                            author: str = "system",
                            variables: Optional[List[str]] = None,
                            **kwargs) -> Dict[str, Any]:
        """Create a new prompt."""
        try:
            # Generate prompt ID
            prompt_id = self._generate_prompt_id(name, content)
            
            # Check if prompt already exists
            if prompt_id in self.prompt_registry:
                return {
                    "success": False,
                    "error": f"Prompt with similar content already exists: {prompt_id}"
                }
            
            # Create metadata
            now = datetime.utcnow().isoformat()
            metadata = PromptMetadata(
                prompt_id=prompt_id,
                name=name,
                description=description,
                prompt_type=PromptType(prompt_type),
                category=PromptCategory(category) if category else None,
                version="1.0.0",
                author=author,
                created_at=now,
                updated_at=now,
                tags=tags or [],
                variables=variables or []
            )
            
            # Save prompt and metadata
            self._save_prompt_file(prompt_id, content)
            self.prompt_registry[prompt_id] = metadata
            self._save_registry()
            
            # Store in memory agent
            await self.memory_agent.store_memory(
                agent_id="prompt_tool",
                memory_type="system_state",
                content={
                    "action": "prompt_created",
                    "prompt_id": prompt_id,
                    "name": name,
                    "type": prompt_type,
                    "category": category
                },
                importance="high"
            )
            
            logger.info(f"Created prompt: {prompt_id} ({name})")
            
            return {
                "success": True,
                "prompt_id": prompt_id,
                "metadata": asdict(metadata)
            }
        except Exception as e:
            logger.error(f"Error creating prompt: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_prompt(self, prompt_id: str, **kwargs) -> Dict[str, Any]:
        """Retrieve a prompt by ID."""
        if prompt_id not in self.prompt_registry:
            return {
                "success": False,
                "error": f"Prompt not found: {prompt_id}"
            }
        
        metadata = self.prompt_registry[prompt_id]
        content = self._load_prompt_file(prompt_id)
        
        if content is None:
            return {
                "success": False,
                "error": f"Prompt file not found: {prompt_id}"
            }
        
        # Update usage stats
        metadata.usage_count += 1
        metadata.last_used = datetime.utcnow().isoformat()
        self._save_registry()
        
        return {
            "success": True,
            "prompt_id": prompt_id,
            "content": content,
            "metadata": asdict(metadata)
        }
    
    async def _update_prompt(self,
                            prompt_id: str,
                            content: Optional[str] = None,
                            name: Optional[str] = None,
                            description: Optional[str] = None,
                            tags: Optional[List[str]] = None,
                            **kwargs) -> Dict[str, Any]:
        """Update an existing prompt."""
        if prompt_id not in self.prompt_registry:
            return {
                "success": False,
                "error": f"Prompt not found: {prompt_id}"
            }
        
        metadata = self.prompt_registry[prompt_id]
        
        # Update fields
        if content is not None:
            self._save_prompt_file(prompt_id, content)
        if name is not None:
            metadata.name = name
        if description is not None:
            metadata.description = description
        if tags is not None:
            metadata.tags = tags
        
        metadata.updated_at = datetime.utcnow().isoformat()
        self._save_registry()
        
        return {
            "success": True,
            "prompt_id": prompt_id,
            "metadata": asdict(metadata)
        }
    
    async def _delete_prompt(self, prompt_id: str, **kwargs) -> Dict[str, Any]:
        """Delete a prompt."""
        if prompt_id not in self.prompt_registry:
            return {
                "success": False,
                "error": f"Prompt not found: {prompt_id}"
            }
        
        # Remove file
        prompt_file = self.prompts_path / f"{prompt_id}.prompt"
        if prompt_file.exists():
            prompt_file.unlink()
        
        # Remove from registry
        del self.prompt_registry[prompt_id]
        self._save_registry()
        
        return {
            "success": True,
            "message": f"Prompt {prompt_id} deleted"
        }
    
    async def _list_prompts(self,
                           prompt_type: Optional[str] = None,
                           category: Optional[str] = None,
                           tags: Optional[List[str]] = None,
                           **kwargs) -> Dict[str, Any]:
        """List all prompts with optional filters."""
        prompts = []
        
        for prompt_id, metadata in self.prompt_registry.items():
            # Apply filters
            if prompt_type and metadata.prompt_type.value != prompt_type:
                continue
            if category and (not metadata.category or metadata.category.value != category):
                continue
            if tags:
                if not any(tag in metadata.tags for tag in tags):
                    continue
            
            prompts.append({
                "prompt_id": prompt_id,
                "name": metadata.name,
                "type": metadata.prompt_type.value,
                "category": metadata.category.value if metadata.category else None,
                "version": metadata.version,
                "usage_count": metadata.usage_count,
                "tags": metadata.tags
            })
        
        return {
            "success": True,
            "prompts": prompts,
            "count": len(prompts)
        }
    
    async def _execute_prompt(self,
                             prompt_id: str,
                             variables: Optional[Dict[str, str]] = None,
                             **kwargs) -> Dict[str, Any]:
        """Execute a prompt with variable substitution."""
        result = await self._get_prompt(prompt_id)
        if not result["success"]:
            return result
        
        content = result["content"]
        metadata = result["metadata"]
        
        # Substitute variables
        if variables:
            for var_name, var_value in variables.items():
                placeholder = f"{{{var_name}}}"
                content = content.replace(placeholder, str(var_value))
        
        return {
            "success": True,
            "prompt_id": prompt_id,
            "executed_content": content,
            "variables_used": list(variables.keys()) if variables else []
        }
    
    async def _search_prompts(self,
                             query: str,
                             search_content: bool = True,
                             **kwargs) -> Dict[str, Any]:
        """Search prompts by content or metadata."""
        results = []
        query_lower = query.lower()
        
        for prompt_id, metadata in self.prompt_registry.items():
            matched = False
            
            # Search metadata
            if query_lower in metadata.name.lower():
                matched = True
            if metadata.description and query_lower in metadata.description.lower():
                matched = True
            if any(query_lower in tag.lower() for tag in metadata.tags):
                matched = True
            
            # Search content
            if search_content:
                content = self._load_prompt_file(prompt_id)
                if content and query_lower in content.lower():
                    matched = True
            
            if matched:
                results.append({
                    "prompt_id": prompt_id,
                    "name": metadata.name,
                    "type": metadata.prompt_type.value,
                    "category": metadata.category.value if metadata.category else None,
                    "description": metadata.description
                })
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }
    
    async def _version_prompt(self,
                             prompt_id: str,
                             new_content: Optional[str] = None,
                             version_notes: str = "",
                             **kwargs) -> Dict[str, Any]:
        """Create a new version of a prompt."""
        if prompt_id not in self.prompt_registry:
            return {
                "success": False,
                "error": f"Prompt not found: {prompt_id}"
            }
        
        original_metadata = self.prompt_registry[prompt_id]
        
        # Generate new prompt ID for version
        content = new_content or self._load_prompt_file(prompt_id)
        if not content:
            return {
                "success": False,
                "error": "No content provided for new version"
            }
        
        new_prompt_id = self._generate_prompt_id(original_metadata.name, content)
        
        # Create new metadata
        now = datetime.utcnow().isoformat()
        new_metadata = PromptMetadata(
            prompt_id=new_prompt_id,
            name=original_metadata.name,
            description=original_metadata.description,
            prompt_type=original_metadata.prompt_type,
            category=original_metadata.category,
            version=self._increment_version(original_metadata.version),
            author=original_metadata.author,
            created_at=now,
            updated_at=now,
            tags=original_metadata.tags.copy(),
            parent_prompt_id=prompt_id,
            variables=original_metadata.variables.copy()
        )
        
        # Save new version
        self._save_prompt_file(new_prompt_id, content)
        self.prompt_registry[new_prompt_id] = new_metadata
        self._save_registry()
        
        return {
            "success": True,
            "original_prompt_id": prompt_id,
            "new_prompt_id": new_prompt_id,
            "version": new_metadata.version,
            "metadata": asdict(new_metadata)
        }
    
    async def _ingest_prompt(self,
                            name: str,
                            content: str,
                            source: str = "external",
                            **kwargs) -> Dict[str, Any]:
        """Ingest a prompt from external source (e.g., AgenticPlace)."""
        # Normalize content
        content = content.strip()
        
        # Extract metadata from content if possible
        description = kwargs.get("description", f"Ingested from {source}")
        prompt_type = kwargs.get("prompt_type", "agent")
        category = kwargs.get("category")
        tags = kwargs.get("tags", [source, "ingested"])
        
        # Create prompt
        result = await self._create_prompt(
            name=name,
            content=content,
            description=description,
            prompt_type=prompt_type,
            category=category,
            tags=tags,
            author=source
        )
        
        if result["success"]:
            # Store ingestion event in memory
            await self.memory_agent.store_memory(
                agent_id="prompt_tool",
                memory_type="learning",
                content={
                    "action": "prompt_ingested",
                    "prompt_id": result["prompt_id"],
                    "source": source,
                    "name": name
                },
                importance="high"
            )
        
        return result
    
    def _increment_version(self, version: str) -> str:
        """Increment version string (simple: 1.0.0 -> 1.0.1)."""
        try:
            parts = version.split('.')
            if len(parts) == 3:
                major, minor, patch = parts
                patch = str(int(patch) + 1)
                return f"{major}.{minor}.{patch}"
            return f"{version}.1"
        except:
            return "1.0.1"



