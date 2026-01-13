# mindx/agents/avatar_agent.py
"""
Avatar Agent for MindX.

This agent generates avatars for agents and participants using image or video
generation APIs. It integrates with PromptTool for avatar generation prompts
and PersonaAgent for persona-specific avatars.

Following mindX doctrine:
- Memory is infrastructure (avatars are stored and linked to identities)
- Avatars represent agent/participant identity visually
- Integration with prompts and personas enables rich avatar generation
"""

import json
import base64
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
import aiohttp
import asyncio

from agents.memory_agent import MemoryAgent
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)


class AvatarType(Enum):
    """Types of avatars."""
    IMAGE = "image"
    VIDEO = "video"
    ANIMATED = "animated"


class AvatarProvider(Enum):
    """Image/video generation providers."""
    OPENAI_DALLE = "openai_dalle"
    STABILITY_AI = "stability_ai"
    MIDJOURNEY = "midjourney"  # Via API if available
    REPLICATE = "replicate"
    CUSTOM = "custom"


class AvatarStyle(Enum):
    """Avatar styles."""
    REALISTIC = "realistic"
    CARTOON = "cartoon"
    ANIME = "anime"
    ABSTRACT = "abstract"
    MINIMALIST = "minimalist"
    PROFESSIONAL = "professional"
    FANTASY = "fantasy"
    CYBERPUNK = "cyberpunk"


@dataclass
class AvatarMetadata:
    """Metadata for an avatar."""
    avatar_id: str
    entity_id: str  # agent_id, participant_id, or persona_id
    entity_type: str  # "agent", "participant", or "persona"
    avatar_type: AvatarType
    provider: AvatarProvider
    style: AvatarStyle
    prompt_used: str
    prompt_id: Optional[str] = None  # If from PromptTool
    persona_id: Optional[str] = None  # If from PersonaAgent
    file_path: str = ""
    thumbnail_path: str = ""
    created_at: str = ""
    updated_at: str = ""
    generation_params: Dict[str, Any] = None
    usage_count: int = 0
    
    def __post_init__(self):
        if self.generation_params is None:
            self.generation_params = {}
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.utcnow().isoformat()


class AvatarAgent:
    """
    Avatar Agent - Generates avatars for agents and participants.
    
    This agent can generate avatars using various image/video generation APIs,
    integrate with PromptTool for prompts, and PersonaAgent for persona-specific
    avatar generation.
    """
    
    def __init__(self,
                 agent_id: str,
                 memory_agent: MemoryAgent,
                 prompt_tool: Optional[Any] = None,
                 persona_agent: Optional[Any] = None,
                 config: Optional[Config] = None,
                 **kwargs):
        self.agent_id = agent_id
        self.memory_agent = memory_agent
        self.prompt_tool = prompt_tool
        self.persona_agent = persona_agent
        self.config = config or Config()
        self.project_root = PROJECT_ROOT
        
        # Avatar storage
        self.avatars_path = self.project_root / "data" / "avatars"
        self.avatars_path.mkdir(parents=True, exist_ok=True)
        self.images_path = self.avatars_path / "images"
        self.videos_path = self.avatars_path / "videos"
        self.thumbnails_path = self.avatars_path / "thumbnails"
        self.images_path.mkdir(exist_ok=True)
        self.videos_path.mkdir(exist_ok=True)
        self.thumbnails_path.mkdir(exist_ok=True)
        
        # Registry file
        self.registry_path = self.avatars_path / "avatar_registry.json"
        self.avatar_registry: Dict[str, AvatarMetadata] = {}
        
        # API configurations
        self.openai_api_key = self.config.get("llm.openai.api_key") or self.config.get("openai_api_key")
        self.stability_api_key = self.config.get("stability_ai.api_key")
        
        # Load existing registry
        self._load_registry()
        
        logger.info(f"AvatarAgent {agent_id} initialized with {len(self.avatar_registry)} avatars")
    
    def _load_registry(self):
        """Load the avatar registry from disk."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as json_file:
                    data = json.load(json_file)
                    for avatar_id, avatar_dict in data.items():
                        avatar_dict['avatar_type'] = AvatarType(avatar_dict['avatar_type'])
                        avatar_dict['provider'] = AvatarProvider(avatar_dict['provider'])
                        avatar_dict['style'] = AvatarStyle(avatar_dict['style'])
                        self.avatar_registry[avatar_id] = AvatarMetadata(**avatar_dict)
                logger.info(f"Loaded {len(self.avatar_registry)} avatars from registry")
            except Exception as e:
                logger.error(f"Error loading avatar registry: {e}")
    
    def _save_registry(self):
        """Save the avatar registry to disk."""
        try:
            data = {}
            for avatar_id, avatar in self.avatar_registry.items():
                avatar_dict = asdict(avatar)
                avatar_dict['avatar_type'] = avatar.avatar_type.value
                avatar_dict['provider'] = avatar.provider.value
                avatar_dict['style'] = avatar.style.value
                data[avatar_id] = avatar_dict
            
            with open(self.registry_path, 'w') as json_file:
                json.dump(data, json_file, indent=2)
        except Exception as e:
            logger.error(f"Error saving avatar registry: {e}")
    
    def _generate_avatar_id(self, entity_id: str, entity_type: str) -> str:
        """Generate a unique avatar ID."""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        hash_obj = hashlib.sha256(f"{entity_id}:{entity_type}:{timestamp}".encode())
        return f"avatar_{hash_obj.hexdigest()[:16]}"
    
    async def generate_avatar(self,
                             entity_id: str,
                             entity_type: str = "agent",
                             prompt: Optional[str] = None,
                             prompt_id: Optional[str] = None,
                             persona_id: Optional[str] = None,
                             avatar_type: str = "image",
                             provider: str = "openai_dalle",
                             style: str = "professional",
                             size: str = "1024x1024",
                             **kwargs) -> Dict[str, Any]:
        """
        Generate an avatar for an agent or participant.
        
        Args:
            entity_id: ID of the agent, participant, or persona
            entity_type: Type of entity ("agent", "participant", "persona")
            prompt: Direct prompt for avatar generation
            prompt_id: ID of prompt from PromptTool
            persona_id: ID of persona from PersonaAgent
            avatar_type: Type of avatar ("image", "video", "animated")
            provider: Generation provider ("openai_dalle", "stability_ai", etc.)
            style: Avatar style ("realistic", "cartoon", "anime", etc.)
            size: Image/video size (e.g., "1024x1024")
        """
        try:
            # Build generation prompt
            generation_prompt = await self._build_generation_prompt(
                prompt=prompt,
                prompt_id=prompt_id,
                persona_id=persona_id,
                entity_id=entity_id,
                entity_type=entity_type,
                style=style
            )
            
            if not generation_prompt:
                return {
                    "success": False,
                    "error": "Could not build generation prompt"
                }
            
            # Generate avatar based on type
            if avatar_type == "image":
                result = await self._generate_image_avatar(
                    prompt=generation_prompt,
                    provider=provider,
                    size=size,
                    style=style,
                    **kwargs
                )
            elif avatar_type == "video":
                result = await self._generate_video_avatar(
                    prompt=generation_prompt,
                    provider=provider,
                    size=size,
                    style=style,
                    **kwargs
                )
            else:
                return {
                    "success": False,
                    "error": f"Unsupported avatar type: {avatar_type}"
                }
            
            if not result.get("success"):
                return result
            
            # Create avatar metadata
            avatar_id = self._generate_avatar_id(entity_id, entity_type)
            now = datetime.utcnow().isoformat()
            
            avatar_metadata = AvatarMetadata(
                avatar_id=avatar_id,
                entity_id=entity_id,
                entity_type=entity_type,
                avatar_type=AvatarType(avatar_type),
                provider=AvatarProvider(provider),
                style=AvatarStyle(style),
                prompt_used=generation_prompt,
                prompt_id=prompt_id,
                persona_id=persona_id,
                file_path=result.get("file_path", ""),
                thumbnail_path=result.get("thumbnail_path", ""),
                created_at=now,
                updated_at=now,
                generation_params={
                    "size": size,
                    "provider": provider,
                    "style": style,
                    **kwargs
                }
            )
            
            # Save to registry
            self.avatar_registry[avatar_id] = avatar_metadata
            self._save_registry()
            
            # Store in memory
            await self.memory_agent.store_memory(
                agent_id=self.agent_id,
                memory_type="system_state",
                content={
                    "action": "avatar_generated",
                    "avatar_id": avatar_id,
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "provider": provider,
                    "style": style
                },
                importance="high"
            )
            
            logger.info(f"Generated avatar: {avatar_id} for {entity_type} {entity_id}")
            
            return {
                "success": True,
                "avatar_id": avatar_id,
                "file_path": result.get("file_path"),
                "thumbnail_path": result.get("thumbnail_path"),
                "metadata": asdict(avatar_metadata)
            }
        except Exception as e:
            logger.error(f"Error generating avatar: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _build_generation_prompt(self,
                                      prompt: Optional[str] = None,
                                      prompt_id: Optional[str] = None,
                                      persona_id: Optional[str] = None,
                                      entity_id: Optional[str] = None,
                                      entity_type: Optional[str] = None,
                                      style: str = "professional") -> Optional[str]:
        """Build the generation prompt from various sources."""
        # Priority: direct prompt > prompt_id > persona_id > default
        
        if prompt:
            return prompt
        
        if prompt_id and self.prompt_tool:
            try:
                result = await self.prompt_tool.execute(
                    operation="get",
                    prompt_id=prompt_id
                )
                if result.get("success"):
                    prompt_content = result.get("content", "")
                    # Execute with variables if needed
                    if entity_id:
                        result = await self.prompt_tool.execute(
                            operation="execute",
                            prompt_id=prompt_id,
                            variables={
                                "entity_id": entity_id,
                                "entity_type": entity_type or "agent",
                                "style": style
                            }
                        )
                        if result.get("success"):
                            return result.get("executed_content")
                    return prompt_content
            except Exception as e:
                logger.warning(f"Error loading prompt from PromptTool: {e}")
        
        if persona_id and self.persona_agent:
            try:
                # Get persona information
                if hasattr(self.persona_agent, 'persona_registry'):
                    persona = self.persona_agent.persona_registry.get(persona_id)
                    if persona:
                        # Build prompt from persona
                        prompt = f"""Create a {style} avatar for {persona.name}, a {persona.role.value} persona.
                        
Description: {persona.description}
Communication Style: {persona.communication_style}
Behavioral Traits: {', '.join(persona.behavioral_traits)}
Expertise Areas: {', '.join(persona.expertise_areas)}

The avatar should visually represent this persona's characteristics and role."""
                        return prompt
            except Exception as e:
                logger.warning(f"Error loading persona from PersonaAgent: {e}")
        
        # Default prompt
        entity_name = entity_id or "agent"
        return f"""Create a {style} avatar for a {entity_type or 'agent'} named {entity_name}.
The avatar should be professional, distinctive, and suitable for representing an AI agent or participant in a digital environment."""
    
    async def _generate_image_avatar(self,
                                    prompt: str,
                                    provider: str,
                                    size: str = "1024x1024",
                                    style: str = "professional",
                                    **kwargs) -> Dict[str, Any]:
        """Generate an image avatar using the specified provider."""
        try:
            if provider == "openai_dalle":
                return await self._generate_dalle_avatar(prompt, size, **kwargs)
            elif provider == "stability_ai":
                return await self._generate_stability_avatar(prompt, size, style, **kwargs)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported provider: {provider}"
                }
        except Exception as e:
            logger.error(f"Error generating image avatar: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_dalle_avatar(self,
                                    prompt: str,
                                    size: str = "1024x1024",
                                    **kwargs) -> Dict[str, Any]:
        """Generate avatar using OpenAI DALL-E."""
        if not self.openai_api_key:
            return {
                "success": False,
                "error": "OpenAI API key not configured"
            }
        
        try:
            try:
                import openai
            except ImportError:
                return {
                    "success": False,
                    "error": "OpenAI library not installed. Install with: pip install openai"
                }
            client = openai.AsyncOpenAI(api_key=self.openai_api_key)
            
            # Enhanced prompt for avatar generation
            enhanced_prompt = f"Professional avatar image: {prompt}. High quality, detailed, suitable for representing an AI agent."
            
            response = await client.images.generate(
                model=kwargs.get("model", "dall-e-3"),
                prompt=enhanced_prompt,
                size=size,
                quality=kwargs.get("quality", "standard"),
                n=1
            )
            
            image_url = response.data[0].url
            
            # Download and save image
            avatar_id = hashlib.sha256(f"{prompt}:{size}:{datetime.utcnow()}".encode()).hexdigest()[:16]
            file_path = self.images_path / f"{avatar_id}.png"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status == 200:
                        image_data = await resp.read()
                        file_path.write_bytes(image_data)
                        
                        # Create thumbnail
                        thumbnail_path = await self._create_thumbnail(file_path, avatar_id)
                        
                        return {
                            "success": True,
                            "file_path": str(file_path),
                            "thumbnail_path": str(thumbnail_path) if thumbnail_path else "",
                            "url": image_url
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Failed to download image: {resp.status}"
                        }
        except Exception as e:
            logger.error(f"Error generating DALL-E avatar: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_stability_avatar(self,
                                       prompt: str,
                                       size: str = "1024x1024",
                                       style: str = "professional",
                                       **kwargs) -> Dict[str, Any]:
        """Generate avatar using Stability AI."""
        if not self.stability_api_key:
            return {
                "success": False,
                "error": "Stability AI API key not configured"
            }
        
        try:
            # Parse size
            width, height = map(int, size.split('x'))
            
            url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
            headers = {
                "Authorization": f"Bearer {self.stability_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "text_prompts": [
                    {
                        "text": f"Professional avatar: {prompt}. {style} style, high quality."
                    }
                ],
                "cfg_scale": kwargs.get("cfg_scale", 7),
                "width": width,
                "height": height,
                "steps": kwargs.get("steps", 30),
                "samples": 1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        image_base64 = result["artifacts"][0]["base64"]
                        
                        # Save image
                        avatar_id = hashlib.sha256(f"{prompt}:{size}:{datetime.utcnow()}".encode()).hexdigest()[:16]
                        file_path = self.images_path / f"{avatar_id}.png"
                        image_data = base64.b64decode(image_base64)
                        file_path.write_bytes(image_data)
                        
                        # Create thumbnail
                        thumbnail_path = await self._create_thumbnail(file_path, avatar_id)
                        
                        return {
                            "success": True,
                            "file_path": str(file_path),
                            "thumbnail_path": str(thumbnail_path) if thumbnail_path else ""
                        }
                    else:
                        error_text = await resp.text()
                        return {
                            "success": False,
                            "error": f"Stability AI API error: {resp.status} - {error_text}"
                        }
        except Exception as e:
            logger.error(f"Error generating Stability AI avatar: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_video_avatar(self,
                                    prompt: str,
                                    provider: str,
                                    size: str = "1024x1024",
                                    style: str = "professional",
                                    **kwargs) -> Dict[str, Any]:
        """Generate a video avatar (placeholder for future implementation)."""
        # Video generation is more complex and requires specialized APIs
        # This is a placeholder for future implementation
        return {
            "success": False,
            "error": "Video avatar generation not yet implemented. Use image avatars for now."
        }
    
    async def _create_thumbnail(self, image_path: Path, avatar_id: str) -> Optional[Path]:
        """Create a thumbnail from an image."""
        try:
            from PIL import Image
            
            img = Image.open(image_path)
            img.thumbnail((256, 256), Image.Resampling.LANCZOS)
            thumbnail_path = self.thumbnails_path / f"{avatar_id}_thumb.png"
            img.save(thumbnail_path)
            return thumbnail_path
        except ImportError:
            logger.warning("PIL not available, skipping thumbnail creation")
            return None
        except Exception as e:
            logger.warning(f"Error creating thumbnail: {e}")
            return None
    
    async def get_avatar(self, entity_id: str, entity_type: Optional[str] = None) -> Dict[str, Any]:
        """Get avatar for an entity."""
        avatars = []
        for avatar_id, avatar in self.avatar_registry.items():
            if avatar.entity_id == entity_id:
                if entity_type is None or avatar.entity_type == entity_type:
                    avatars.append({
                        "avatar_id": avatar_id,
                        "metadata": asdict(avatar)
                    })
        
        if not avatars:
            return {
                "success": False,
                "error": f"No avatar found for {entity_type or 'entity'} {entity_id}"
            }
        
        # Return most recent
        avatars.sort(key=lambda x: x["metadata"]["created_at"], reverse=True)
        return {
            "success": True,
            "avatar": avatars[0]
        }
    
    async def list_avatars(self,
                          entity_type: Optional[str] = None,
                          provider: Optional[str] = None,
                          **kwargs) -> Dict[str, Any]:
        """List all avatars with optional filters."""
        avatars = []
        
        for avatar_id, avatar in self.avatar_registry.items():
            if entity_type and avatar.entity_type != entity_type:
                continue
            if provider and avatar.provider.value != provider:
                continue
            
            avatars.append({
                "avatar_id": avatar_id,
                "entity_id": avatar.entity_id,
                "entity_type": avatar.entity_type,
                "avatar_type": avatar.avatar_type.value,
                "provider": avatar.provider.value,
                "style": avatar.style.value,
                "file_path": avatar.file_path,
                "created_at": avatar.created_at
            })
        
        return {
            "success": True,
            "avatars": avatars,
            "count": len(avatars)
        }
    
    async def delete_avatar(self, avatar_id: str) -> Dict[str, Any]:
        """Delete an avatar."""
        if avatar_id not in self.avatar_registry:
            return {
                "success": False,
                "error": f"Avatar not found: {avatar_id}"
            }
        
        avatar = self.avatar_registry[avatar_id]
        
        # Delete files
        if avatar.file_path and Path(avatar.file_path).exists():
            Path(avatar.file_path).unlink()
        if avatar.thumbnail_path and Path(avatar.thumbnail_path).exists():
            Path(avatar.thumbnail_path).unlink()
        
        # Remove from registry
        del self.avatar_registry[avatar_id]
        self._save_registry()
        
        return {
            "success": True,
            "message": f"Avatar {avatar_id} deleted"
        }

