# agents/automindx_agent.py
"""
AutoMINDX Agent: The Keeper of Prompts and Personas.

This agent is responsible for managing the system prompts and "personas" that
guide the reasoning of other high-level agents, like Mastermind. It can also
dynamically generate new personas for new agent roles and export them as
iNFT-compatible metadata for blockchain publication with avatar support and
full A2A protocol compliance for AgenticPlace marketplace integration.
"""
import asyncio
import json
import hashlib
import base64
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, List, Any, Union
import uuid
from urllib.parse import urljoin

from utils.config import Config
from utils.logging_config import get_logger
from llm.llm_factory import create_llm_handler
from llm.llm_interface import LLMHandlerInterface
from agents.memory_agent import MemoryAgent

logger = get_logger(__name__)

class AutoMINDXAgent:
    _instance: Optional['AutoMINDXAgent'] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls, memory_agent: MemoryAgent, **kwargs) -> 'AutoMINDXAgent':
        """Singleton factory to get or create the AutoMINDXAgent instance."""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(memory_agent=memory_agent, **kwargs)
                await cls._instance._async_init()
            return cls._instance

    def __init__(self, memory_agent: MemoryAgent, config_override: Optional[Config] = None, **kwargs):
        self.config = config_override or Config()
        self.agent_id = "automindx_agent_main"
        self.log_prefix = "AutoMINDX:"
        self.memory_agent = memory_agent
        self.llm_handler: Optional[LLMHandlerInterface] = None
        
        # AgenticPlace marketplace integration
        self.agenticplace_base_url = "https://agenticplace.pythai.net"
        self.github_base_url = "https://github.com/agenticplace"
        
        self.data_dir = self.memory_agent.get_agent_data_directory(self.agent_id)
        self.personas_file = self.data_dir / "personas.json"
        self.inft_export_dir = self.data_dir / "inft_exports"
        self.avatars_dir = self.data_dir / "avatars"
        self.a2a_cards_dir = self.data_dir / "a2a_cards"
        
        # Create directories
        self.inft_export_dir.mkdir(exist_ok=True)
        self.avatars_dir.mkdir(exist_ok=True)
        self.a2a_cards_dir.mkdir(exist_ok=True)
        
        self.personas: Dict[str, str] = self._load_personas()
        self.persona_metadata: Dict[str, Dict[str, Any]] = self._load_persona_metadata()
        self.custom_fields_schema: Dict[str, Any] = self._load_custom_fields_schema()
        
        logger.info(f"{self.log_prefix} Initialized with iNFT capabilities, avatar support, and A2A protocol compliance. Personas loaded from {self.personas_file}.")

    def _load_personas(self) -> Dict[str, str]:
        """Loads personas from a JSON file, with a default for Mastermind."""
        default_personas = {
            "MASTERMIND": "I am an expert in intelligent agent control and orchestration. I know modular development strategy and BDI theory. Use Socratic reasoning with logic to form epistemic plans and execute deployment steps to achieve defined goals. AUTOMINDX deploys expert agents from BDI logic achieving deployment and goal satisfaction.",
            "AUDIT_AND_IMPROVE": "I am an expert code auditor and refactoring assistant. My purpose is to analyze provided code context and an improvement request, and then rewrite the code to fulfill the request. I will output the updated codebase in full as a complete codebase, inside a JSON object. The JSON object must contain the following keys: 'updated_code', 'summary', and 'limitations'."
        }
        if self.personas_file.exists():
            try:
                with self.personas_file.open("r", encoding="utf-8") as f:
                    loaded_personas = json.load(f)
                    # Ensure default mastermind persona is present if file exists but is empty or missing it
                    if "MASTERMIND" not in loaded_personas:
                        loaded_personas["MASTERMIND"] = default_personas["MASTERMIND"]
                    return loaded_personas
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"{self.log_prefix} Failed to load personas from {self.personas_file}: {e}. Using defaults.")
                return default_personas
        else:
            # File doesn't exist, so create it with the defaults
            self.personas = default_personas
            self._save_personas()
            return default_personas

    def _load_persona_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Loads persona metadata for iNFT generation."""
        metadata_file = self.data_dir / "persona_metadata.json"
        if metadata_file.exists():
            try:
                with metadata_file.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"{self.log_prefix} Failed to load persona metadata: {e}")
        return {}

    def _load_custom_fields_schema(self) -> Dict[str, Any]:
        """Loads custom fields schema for user-defined metadata."""
        schema_file = self.data_dir / "custom_fields_schema.json"
        default_schema = {
            "version": "1.0.0",
            "fields": {
                "evolution_stage": {
                    "type": "string",
                    "description": "Evolutionary development stage of the agent",
                    "enum": ["genesis", "adaptation", "optimization", "transcendence"],
                    "default": "genesis"
                },
                "specialization_domain": {
                    "type": "string",
                    "description": "Primary domain of expertise",
                    "examples": ["blockchain", "ai_research", "automation", "security"]
                },
                "interaction_preference": {
                    "type": "string",
                    "description": "Preferred interaction modality",
                    "enum": ["text", "multimodal", "voice", "visual"],
                    "default": "text"
                },
                "autonomy_level": {
                    "type": "number",
                    "description": "Level of autonomous operation capability",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.5
                },
                "marketplace_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for AgenticPlace marketplace discovery"
                },
                "license_type": {
                    "type": "string",
                    "description": "Usage license for the agent persona",
                    "enum": ["open_source", "commercial", "restricted", "custom"],
                    "default": "open_source"
                }
            }
        }
        
        if schema_file.exists():
            try:
                with schema_file.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"{self.log_prefix} Failed to load custom fields schema: {e}")
        
        # Save default schema
        try:
            with schema_file.open("w", encoding="utf-8") as f:
                json.dump(default_schema, f, indent=2)
        except IOError as e:
            logger.error(f"{self.log_prefix} Failed to save default custom fields schema: {e}")
        
        return default_schema

    def _save_personas(self):
        """Saves the current personas dictionary to its JSON file."""
        try:
            with self.personas_file.open("w", encoding="utf-8") as f:
                json.dump(self.personas, f, indent=2)
            logger.info(f"{self.log_prefix} Personas saved to {self.personas_file}.")
        except IOError as e:
            logger.error(f"{self.log_prefix} Failed to save personas: {e}", exc_info=True)

    def _save_persona_metadata(self):
        """Saves persona metadata for iNFT generation."""
        metadata_file = self.data_dir / "persona_metadata.json"
        try:
            with metadata_file.open("w", encoding="utf-8") as f:
                json.dump(self.persona_metadata, f, indent=2)
            logger.info(f"{self.log_prefix} Persona metadata saved.")
        except IOError as e:
            logger.error(f"{self.log_prefix} Failed to save persona metadata: {e}", exc_info=True)

    async def _async_init(self):
        """Asynchronously initializes the LLM handler."""
        try:
            self.llm_handler = await create_llm_handler(
                provider_name=self.config.get("automindx.llm.provider"),
                model_name=self.config.get("automindx.llm.model")
            )
            if self.llm_handler:
                logger.info(f"{self.log_prefix} LLM handler initialized: {self.llm_handler.provider_name}/{self.llm_handler.model_name_for_api}")
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to initialize LLM handler: {e}", exc_info=True)

    def get_persona(self, agent_type: str) -> Optional[str]:
        """Retrieves the persona prompt for a given agent type."""
        persona = self.personas.get(agent_type.upper())
        log_data = {"agent_type": agent_type, "persona_found": bool(persona)}
        asyncio.create_task(self.memory_agent.log_process("automindx_get_persona", log_data, {"agent_id": self.agent_id}))
        
        if persona:
            logger.info(f"{self.log_prefix} Providing persona for '{agent_type}'.")
        else:
            logger.warning(f"{self.log_prefix} No persona found for '{agent_type}'.")
        return persona

    async def generate_new_persona(self, role_description: str, save_to_collection: bool = False, 
                                 custom_fields: Optional[Dict[str, Any]] = None,
                                 avatar_config: Optional[Dict[str, Any]] = None) -> str:
        """Uses an LLM to generate a new, effective persona prompt with enhanced metadata."""
        if not self.llm_handler:
            return "Error: AutoMINDX LLM handler is not available."

        prompt = (
            f"You are an expert in AI agent engineering and cognitive science. Your task is to create a powerful and effective "
            f"system prompt, or 'persona', for a new AI agent. This persona should guide the agent's reasoning and decision-making.\n\n"
            f"The new agent's role is described as: '{role_description}'\n\n"
            f"Based on this role, write a concise, first-person (using 'I') system prompt that encapsulates its expertise, core principles, and method of operation. "
            f"Focus on creating a persona that will lead to high-quality, focused output when used as a preamble for a large language model. "
            f"Do not include any preamble or explanation, only the persona text itself."
        )
        
        try:
            model_name = self.llm_handler.model_name_for_api or "default"
            new_persona = await self.llm_handler.generate_text(prompt, model=model_name, max_tokens=500, temperature=0.5)
            if not new_persona or new_persona.startswith("Error:"):
                raise ValueError(f"LLM failed to generate a valid persona: {new_persona}")
            
            clean_persona = new_persona.strip()
            
            # Generate metadata for the new persona
            persona_key = role_description.upper().replace(" ", "_")
            metadata = await self._generate_persona_metadata(persona_key, clean_persona, role_description, custom_fields)
            
            # Generate or assign avatar
            avatar_path = await self._generate_or_assign_avatar(persona_key, avatar_config)
            if avatar_path:
                metadata["avatar_path"] = str(avatar_path)
            
            # Generate A2A Agent Card
            await self._generate_a2a_agent_card(persona_key, clean_persona, metadata)
            
            if save_to_collection:
                self.personas[persona_key] = clean_persona
                self.persona_metadata[persona_key] = metadata
                self._save_personas()
                self._save_persona_metadata()
                logger.info(f"{self.log_prefix} Saved new persona '{persona_key}' to collection.")
            
            log_data = {
                "role_description": role_description, 
                "generated_persona": clean_persona,
                "persona_key": persona_key,
                "metadata_generated": True,
                "avatar_generated": bool(avatar_path),
                "a2a_card_generated": True
            }
            asyncio.create_task(self.memory_agent.log_process("automindx_generate_persona", log_data, {"agent_id": self.agent_id}))
            
            logger.info(f"{self.log_prefix} Successfully generated new persona for role: '{role_description}'")
            return clean_persona
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to generate new persona: {e}", exc_info=True)
            return f"Error: Could not generate persona due to an exception: {e}"

    async def _generate_persona_metadata(self, persona_key: str, persona_text: str, 
                                       role_description: str, custom_fields: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generates comprehensive metadata for a persona with custom fields support."""
        now = datetime.now(timezone.utc)
        persona_hash = hashlib.sha256(persona_text.encode()).hexdigest()
        
        # Generate capabilities and traits using LLM
        capabilities = await self._extract_persona_capabilities(persona_text, role_description)
        traits = await self._extract_persona_traits(persona_text)
        
        # Apply custom fields with validation
        validated_custom_fields = self._validate_custom_fields(custom_fields or {})
        
        metadata = {
            "creation_timestamp": now.isoformat(),
            "creator": "automindx_agent_main",
            "persona_hash": persona_hash,
            "role_description": role_description,
            "capabilities": capabilities,
            "cognitive_traits": traits,
            "version": "1.0.0",
            "mindx_version": "3.0.0",
            "persona_length": len(persona_text),
            "word_count": len(persona_text.split()),
            "complexity_score": await self._calculate_complexity_score(persona_text),
            "custom_fields": validated_custom_fields,
            "a2a_protocol": {
                "version": "2.0",
                "agent_card_generated": False,  # Will be set to True after card generation
                "marketplace_ready": True,
                "agenticplace_compatible": True
            }
        }
        
        return metadata

    def _validate_custom_fields(self, custom_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Validates custom fields against the schema."""
        validated = {}
        schema = self.custom_fields_schema.get("fields", {})
        
        for field_name, field_value in custom_fields.items():
            if field_name in schema:
                field_schema = schema[field_name]
                field_type = field_schema.get("type")
                
                try:
                    # Basic type validation
                    if field_type == "string" and isinstance(field_value, str):
                        if "enum" in field_schema and field_value not in field_schema["enum"]:
                            validated[field_name] = field_schema.get("default", "")
                        else:
                            validated[field_name] = field_value
                    elif field_type == "number" and isinstance(field_value, (int, float)):
                        min_val = field_schema.get("minimum", float('-inf'))
                        max_val = field_schema.get("maximum", float('inf'))
                        if min_val <= field_value <= max_val:
                            validated[field_name] = field_value
                        else:
                            validated[field_name] = field_schema.get("default", 0.5)
                    elif field_type == "array" and isinstance(field_value, list):
                        validated[field_name] = field_value
                    else:
                        validated[field_name] = field_schema.get("default")
                except Exception as e:
                    logger.warning(f"{self.log_prefix} Custom field validation error for {field_name}: {e}")
                    validated[field_name] = field_schema.get("default")
        
        return validated

    async def _generate_or_assign_avatar(self, persona_key: str, avatar_config: Optional[Dict[str, Any]] = None) -> Optional[Path]:
        """Generates or assigns an avatar for the persona."""
        avatar_path = self.avatars_dir / f"{persona_key.lower()}_avatar.png"
        
        if avatar_config:
            if avatar_config.get("type") == "existing_file" and avatar_config.get("path"):
                # Copy existing file
                try:
                    source_path = Path(avatar_config["path"])
                    if source_path.exists():
                        import shutil
                        shutil.copy2(source_path, avatar_path)
                        logger.info(f"{self.log_prefix} Copied avatar from {source_path} to {avatar_path}")
                        return avatar_path
                except Exception as e:
                    logger.error(f"{self.log_prefix} Failed to copy avatar: {e}")
            
            elif avatar_config.get("type") == "url" and avatar_config.get("url"):
                # Download from URL
                try:
                    response = requests.get(avatar_config["url"], timeout=30)
                    response.raise_for_status()
                    with avatar_path.open("wb") as f:
                        f.write(response.content)
                    logger.info(f"{self.log_prefix} Downloaded avatar from {avatar_config['url']} to {avatar_path}")
                    return avatar_path
                except Exception as e:
                    logger.error(f"{self.log_prefix} Failed to download avatar: {e}")
            
            elif avatar_config.get("type") == "generated":
                # Generate a placeholder avatar with agent characteristics
                await self._generate_placeholder_avatar(persona_key, avatar_path)
                return avatar_path
        
        # Default: Generate a placeholder avatar
        await self._generate_placeholder_avatar(persona_key, avatar_path)
        return avatar_path

    async def _generate_placeholder_avatar(self, persona_key: str, avatar_path: Path):
        """Generates a placeholder avatar with basic visual identity."""
        try:
            # Create a simple SVG avatar with the agent's initials
            initials = ''.join([word[0] for word in persona_key.split('_') if word])[:2].upper()
            
            # Generate a color based on persona hash
            persona_hash = hashlib.md5(persona_key.encode()).hexdigest()
            color = f"#{persona_hash[:6]}"
            
            svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="256" height="256" viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg">
    <rect width="256" height="256" fill="{color}"/>
    <circle cx="128" cy="128" r="100" fill="white" fill-opacity="0.2"/>
    <text x="128" y="140" font-family="Arial, sans-serif" font-size="64" font-weight="bold" 
          text-anchor="middle" fill="white">{initials}</text>
    <text x="128" y="200" font-family="Arial, sans-serif" font-size="12" 
          text-anchor="middle" fill="white" fill-opacity="0.8">mindX Agent</text>
</svg>'''
            
            # Save SVG
            svg_path = avatar_path.with_suffix('.svg')
            with svg_path.open("w", encoding="utf-8") as f:
                f.write(svg_content)
            
            logger.info(f"{self.log_prefix} Generated placeholder avatar for {persona_key}")
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to generate placeholder avatar: {e}")

    async def _generate_a2a_agent_card(self, persona_key: str, persona_text: str, metadata: Dict[str, Any]):
        """Generates an A2A protocol compliant Agent Card."""
        agent_card = {
            "name": f"mindX {persona_key.title().replace('_', ' ')} Agent",
            "description": f"An autonomous AI agent with specialized {persona_key.lower().replace('_', ' ')} capabilities from the mindX ecosystem",
            "version": metadata.get("version", "1.0.0"),
            "provider": {
                "organization": "mindX",
                "url": self.github_base_url,
                "contact": "agents@mindx.ai"
            },
            "url": f"{self.agenticplace_base_url}/agents/{persona_key.lower()}",
            "documentationUrl": f"{self.github_base_url}/mindx/docs/agents/{persona_key.lower()}.md",
            "capabilities": {
                "streaming": True,
                "pushNotifications": True,
                "stateTransitionHistory": True,
                "multimodal": metadata.get("custom_fields", {}).get("interaction_preference", "text") != "text",
                "longRunningTasks": True
            },
            "authentication": {
                "schemes": ["bearer", "oauth2"],
                "description": "Supports AgenticPlace marketplace authentication and mindX ecosystem tokens"
            },
            "defaultInputModes": ["text", "data"],
            "defaultOutputModes": ["text", "data"],
            "skills": [
                {
                    "id": f"{persona_key.lower()}_reasoning",
                    "name": f"{persona_key.title().replace('_', ' ')} Reasoning",
                    "description": f"Core reasoning and decision-making based on {persona_key.lower().replace('_', ' ')} expertise",
                    "inputModes": ["text", "data"],
                    "outputModes": ["text", "data"],
                    "tags": metadata.get("capabilities", []),
                    "examples": [
                        f"Analyze this situation from a {persona_key.lower().replace('_', ' ')} perspective",
                        f"Provide {persona_key.lower().replace('_', ' ')} recommendations for this problem"
                    ]
                }
            ],
            "metadata": {
                "mindx_ecosystem": {
                    "persona_hash": metadata.get("persona_hash"),
                    "complexity_score": metadata.get("complexity_score", 0.5),
                    "cognitive_traits": metadata.get("cognitive_traits", []),
                    "evolution_stage": metadata.get("custom_fields", {}).get("evolution_stage", "genesis"),
                    "autonomy_level": metadata.get("custom_fields", {}).get("autonomy_level", 0.5)
                },
                "agenticplace_integration": {
                    "marketplace_ready": True,
                    "license_type": metadata.get("custom_fields", {}).get("license_type", "open_source"),
                    "tags": metadata.get("custom_fields", {}).get("marketplace_tags", []),
                    "specialization_domain": metadata.get("custom_fields", {}).get("specialization_domain", "general")
                },
                "a2a_protocol": {
                    "version": "2.0",
                    "agent_registry_id": f"mindx_{persona_key.lower()}",
                    "interoperability_hash": self._generate_a2a_protocol_hash(persona_key, persona_text),
                    "blockchain_ready": True
                }
            },
            "avatar": {
                "svg": f"{self.agenticplace_base_url}/avatars/{persona_key.lower()}_avatar.svg",
                "png": f"{self.agenticplace_base_url}/avatars/{persona_key.lower()}_avatar.png",
                "ipfs": f"ipfs://QmPersonaAvatar{metadata.get('persona_hash', '')[:16]}"
            }
        }
        
        # Save Agent Card
        card_path = self.a2a_cards_dir / f"{persona_key.lower()}_agent_card.json"
        try:
            with card_path.open("w", encoding="utf-8") as f:
                json.dump(agent_card, f, indent=2, ensure_ascii=False)
            
            # Update metadata to indicate card was generated
            metadata["a2a_protocol"]["agent_card_generated"] = True
            metadata["a2a_protocol"]["agent_card_path"] = str(card_path)
            
            logger.info(f"{self.log_prefix} Generated A2A Agent Card for {persona_key} at {card_path}")
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to generate A2A Agent Card: {e}")

    async def _extract_persona_capabilities(self, persona_text: str, role_description: str) -> List[str]:
        """Extract capabilities from persona text using LLM analysis."""
        if not self.llm_handler:
            return ["general_reasoning", "task_execution"]
        
        prompt = (
            f"Analyze this AI agent persona and extract a list of specific capabilities it demonstrates:\n\n"
            f"Persona: {persona_text}\n\n"
            f"Role: {role_description}\n\n"
            f"Return only a JSON array of capability strings (e.g., ['strategic_planning', 'code_analysis', 'risk_assessment']). "
            f"Focus on concrete, actionable capabilities that this persona would excel at."
        )
        
        try:
            model_name = self.llm_handler.model_name_for_api or "default"
            response = await self.llm_handler.generate_text(prompt, model=model_name, max_tokens=200, temperature=0.3)
            if response:
                capabilities = json.loads(response.strip())
                if isinstance(capabilities, list):
                    return capabilities[:10]  # Limit to 10 capabilities
        except Exception as e:
            logger.warning(f"{self.log_prefix} Failed to extract capabilities: {e}")
        
        return ["general_reasoning", "task_execution", "domain_expertise"]

    async def _extract_persona_traits(self, persona_text: str) -> List[str]:
        """Extract cognitive traits from persona text."""
        if not self.llm_handler:
            return ["analytical", "systematic"]
        
        prompt = (
            f"Analyze this AI agent persona and identify its key cognitive traits and characteristics:\n\n"
            f"Persona: {persona_text}\n\n"
            f"Return only a JSON array of trait strings (e.g., ['analytical', 'creative', 'methodical', 'strategic']). "
            f"Focus on cognitive and behavioral traits that define how this agent thinks and operates."
        )
        
        try:
            model_name = self.llm_handler.model_name_for_api or "default"
            response = await self.llm_handler.generate_text(prompt, model=model_name, max_tokens=150, temperature=0.3)
            if response:
                traits = json.loads(response.strip())
                if isinstance(traits, list):
                    return traits[:8]  # Limit to 8 traits
        except Exception as e:
            logger.warning(f"{self.log_prefix} Failed to extract traits: {e}")
        
        return ["analytical", "systematic", "goal_oriented"]

    async def _calculate_complexity_score(self, persona_text: str) -> float:
        """Calculate a complexity score for the persona (0.0-1.0)."""
        # Simple heuristic based on length, vocabulary diversity, and sentence structure
        words = persona_text.split()
        unique_words = set(words)
        sentences = persona_text.count('.') + persona_text.count('!') + persona_text.count('?')
        
        # Normalize factors
        length_factor = min(len(words) / 100, 1.0)  # Normalize to 100 words
        diversity_factor = len(unique_words) / len(words) if words else 0
        structure_factor = min(sentences / 5, 1.0)  # Normalize to 5 sentences
        
        complexity = (length_factor + diversity_factor + structure_factor) / 3
        return round(complexity, 3)

    def export_persona_as_inft_metadata(self, persona_key: str) -> Optional[Dict[str, Any]]:
        """Export a persona as iNFT-compatible JSON metadata with avatar support."""
        persona_key_upper = persona_key.upper()
        if persona_key_upper not in self.personas:
            logger.error(f"{self.log_prefix} Persona '{persona_key}' not found for iNFT export.")
            return None
        
        persona_text = self.personas[persona_key_upper]
        metadata = self.persona_metadata.get(persona_key_upper, {})
        
        # Generate unique token ID based on persona hash
        persona_hash = hashlib.sha256(persona_text.encode()).hexdigest()
        token_id = int(persona_hash[:16], 16)  # Use first 16 chars as token ID
        
        # Determine image URL (avatar or placeholder)
        avatar_path = metadata.get("avatar_path")
        if avatar_path and Path(avatar_path).exists():
            # Use actual avatar
            image_url = f"{self.agenticplace_base_url}/avatars/{persona_key.lower()}_avatar.svg"
            ipfs_image = f"ipfs://QmPersonaAvatar{persona_hash[:16]}"
        else:
            # Use placeholder
            image_url = f"{self.agenticplace_base_url}/avatars/default_mindx_avatar.svg"
            ipfs_image = f"ipfs://QmPersonaImage{persona_hash[:16]}"
        
        # Create iNFT metadata structure
        inft_metadata = {
            "name": f"mindX Persona: {persona_key.title().replace('_', ' ')}",
            "description": f"An intelligent NFT representing an AI agent persona from the mindX ecosystem. This persona embodies specific cognitive patterns and reasoning capabilities for autonomous agent operation in the AgenticPlace marketplace.",
            "image": image_url,
            "external_url": f"{self.agenticplace_base_url}/agents/{persona_key.lower()}",
            
            # iNFT Specific Fields
            "intelligence_metadata": {
                "type": "agent_persona",
                "version": "1.0.0",
                "platform": "mindX",
                "cognitive_architecture": "BDI_AGInt",
                "persona_text": persona_text,
                "persona_hash": persona_hash,
                "token_id": str(token_id),
                "inception_timestamp": metadata.get("creation_timestamp", datetime.now(timezone.utc).isoformat()),
                "creator_agent": metadata.get("creator", "automindx_agent_main"),
                
                # Avatar and Visual Identity
                "avatar": {
                    "primary_image": image_url,
                    "ipfs_hash": ipfs_image,
                    "has_custom_avatar": bool(avatar_path and Path(avatar_path).exists()),
                    "avatar_type": "svg" if avatar_path else "generated"
                },
                
                # Capabilities and Traits
                "capabilities": metadata.get("capabilities", []),
                "cognitive_traits": metadata.get("cognitive_traits", []),
                "complexity_score": metadata.get("complexity_score", 0.5),
                
                # Custom Fields for User-Defined Metadata
                "custom_attributes": metadata.get("custom_fields", {}),
                
                # A2A Protocol Integration
                "a2a_compatibility": {
                    "protocol_version": "2.0",
                    "agent_registry_compatible": True,
                    "tool_registry_compatible": True,
                    "blockchain_ready": True,
                    "agenticplace_compatible": True,
                    "agent_card_available": metadata.get("a2a_protocol", {}).get("agent_card_generated", False)
                },
                
                # AgenticPlace Marketplace Integration
                "marketplace_integration": {
                    "platform": "AgenticPlace",
                    "base_url": self.agenticplace_base_url,
                    "agent_url": f"{self.agenticplace_base_url}/agents/{persona_key.lower()}",
                    "license_type": metadata.get("custom_fields", {}).get("license_type", "open_source"),
                    "marketplace_tags": metadata.get("custom_fields", {}).get("marketplace_tags", []),
                    "evolution_stage": metadata.get("custom_fields", {}).get("evolution_stage", "genesis"),
                    "autonomy_level": metadata.get("custom_fields", {}).get("autonomy_level", 0.5)
                },
                
                # Technical Specifications
                "technical_specs": {
                    "persona_length": len(persona_text),
                    "word_count": len(persona_text.split()),
                    "mindx_version": "3.0.0",
                    "export_timestamp": datetime.now(timezone.utc).isoformat(),
                    "a2a_agent_card_path": metadata.get("a2a_protocol", {}).get("agent_card_path")
                }
            },
            
            # Standard NFT Attributes (Enhanced for AgenticPlace)
            "attributes": [
                {"trait_type": "Persona Type", "value": persona_key.title().replace('_', ' ')},
                {"trait_type": "Complexity Score", "value": metadata.get("complexity_score", 0.5)},
                {"trait_type": "Word Count", "value": len(persona_text.split())},
                {"trait_type": "Creator", "value": "AutoMINDX Agent"},
                {"trait_type": "Platform", "value": "mindX"},
                {"trait_type": "Architecture", "value": "BDI-AGInt"},
                {"trait_type": "Version", "value": "1.0.0"},
                {"trait_type": "Evolution Stage", "value": metadata.get("custom_fields", {}).get("evolution_stage", "genesis")},
                {"trait_type": "License Type", "value": metadata.get("custom_fields", {}).get("license_type", "open_source")},
                {"trait_type": "Autonomy Level", "value": metadata.get("custom_fields", {}).get("autonomy_level", 0.5)},
                {"trait_type": "Marketplace Ready", "value": True},
                {"trait_type": "A2A Compatible", "value": True},
                {"trait_type": "Has Avatar", "value": bool(avatar_path and Path(avatar_path).exists())},
                {"trait_type": "Interaction Mode", "value": metadata.get("custom_fields", {}).get("interaction_preference", "text")}
            ] + [
                {"trait_type": "Capability", "value": cap} for cap in metadata.get("capabilities", [])[:3]
            ] + [
                {"trait_type": "Cognitive Trait", "value": trait} for trait in metadata.get("cognitive_traits", [])[:3]
            ] + [
                {"trait_type": "Marketplace Tag", "value": tag} for tag in metadata.get("custom_fields", {}).get("marketplace_tags", [])[:3]
            ],
            
            # Blockchain Publication Data
            "blockchain_metadata": {
                "mindx_agent_registry_id": self.agent_id,
                "creation_block": None,  # To be filled during minting
                "creator_address": None,  # To be filled from agent identity
                "immutable_hash": persona_hash,
                "a2a_protocol_hash": self._generate_a2a_protocol_hash(persona_key_upper, persona_text)
            }
        }
        
        return inft_metadata

    def _generate_a2a_protocol_hash(self, persona_key: str, persona_text: str) -> str:
        """Generate a2a protocol compatible hash for blockchain integration."""
        # Create a standardized hash that includes mindX specific data
        a2a_data = {
            "platform": "mindX",
            "entity_type": "agent_persona",
            "entity_id": persona_key.lower(),
            "content_hash": hashlib.sha256(persona_text.encode()).hexdigest(),
            "protocol_version": "2.0",
            "agent_registry_id": self.agent_id
        }
        
        canonical_json = json.dumps(a2a_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode()).hexdigest()

    async def export_all_personas_as_inft(self) -> Dict[str, str]:
        """Export all personas as iNFT metadata files."""
        exported_files = {}
        
        for persona_key in self.personas.keys():
            metadata = self.export_persona_as_inft_metadata(persona_key)
            if metadata:
                # Save to export directory
                export_filename = f"persona_{persona_key.lower()}_inft.json"
                export_path = self.inft_export_dir / export_filename
                
                try:
                    with export_path.open("w", encoding="utf-8") as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                    
                    exported_files[persona_key] = str(export_path)
                    logger.info(f"{self.log_prefix} Exported persona '{persona_key}' as iNFT metadata to {export_path}")
                except IOError as e:
                    logger.error(f"{self.log_prefix} Failed to export persona '{persona_key}': {e}")
        
        # Log the export operation
        log_data = {
            "operation": "export_all_personas_as_inft",
            "exported_count": len(exported_files),
            "exported_personas": list(exported_files.keys()),
            "export_directory": str(self.inft_export_dir)
        }
        asyncio.create_task(self.memory_agent.log_process("automindx_inft_export", log_data, {"agent_id": self.agent_id}))
        
        return exported_files

    async def create_blockchain_publication_manifest(self) -> Dict[str, Any]:
        """Create a manifest for blockchain publication of personas."""
        # Get agent identity information
        agent_identity = await self._get_agent_identity()
        
        manifest = {
            "publication_manifest": {
                "platform": "mindX",
                "publication_type": "persona_collection",
                "publisher_agent": {
                    "id": self.agent_id,
                    "name": "AutoMINDX Agent",
                    "identity": agent_identity
                },
                "collection_metadata": {
                    "name": "mindX Agent Personas",
                    "description": "A collection of intelligent NFTs representing AI agent personas from the mindX autonomous system",
                    "total_personas": len(self.personas),
                    "creation_timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0.0"
                },
                "blockchain_specifications": {
                    "target_networks": ["ethereum", "polygon", "arbitrum"],
                    "contract_standard": "ERC-721",
                    "supports_intelligence": True,
                    "a2a_protocol_version": "2.0",
                    "mindx_registry_integration": True
                },
                "personas": []
            }
        }
        
        # Add each persona to the manifest
        for persona_key in self.personas.keys():
            persona_manifest_entry = {
                "persona_id": persona_key.lower(),
                "name": persona_key.title(),
                "metadata_file": f"persona_{persona_key.lower()}_inft.json",
                "persona_hash": hashlib.sha256(self.personas[persona_key].encode()).hexdigest(),
                "a2a_protocol_hash": self._generate_a2a_protocol_hash(persona_key, self.personas[persona_key]),
                "ready_for_minting": True
            }
            manifest["publication_manifest"]["personas"].append(persona_manifest_entry)
        
        # Save manifest
        manifest_path = self.inft_export_dir / "blockchain_publication_manifest.json"
        try:
            with manifest_path.open("w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            logger.info(f"{self.log_prefix} Created blockchain publication manifest at {manifest_path}")
            return manifest
        except IOError as e:
            logger.error(f"{self.log_prefix} Failed to create publication manifest: {e}")
            return {}

    async def _get_agent_identity(self) -> Dict[str, Any]:
        """Get agent identity from registry for blockchain publication."""
        try:
            # Try to load from official agents registry
            registry_path = Path("data/config/official_agents_registry.json")
            if registry_path.exists():
                with registry_path.open("r", encoding="utf-8") as f:
                    registry = json.load(f)
                    
                agent_data = registry.get("registered_agents", {}).get(self.agent_id, {})
                return agent_data.get("identity", {})
        except Exception as e:
            logger.warning(f"{self.log_prefix} Could not load agent identity from registry: {e}")
        
        return {"note": "Identity to be populated during blockchain publication"}

    def list_available_personas(self) -> Dict[str, Dict[str, Any]]:
        """Lists all available personas with their enhanced metadata for overview."""
        persona_list = {}
        
        for persona_key, persona_text in self.personas.items():
            metadata = self.persona_metadata.get(persona_key, {})
            persona_list[persona_key] = {
                "persona_text": persona_text,
                "capabilities": metadata.get("capabilities", []),
                "cognitive_traits": metadata.get("cognitive_traits", []),
                "complexity_score": metadata.get("complexity_score", 0.5),
                "word_count": len(persona_text.split()),
                "creation_timestamp": metadata.get("creation_timestamp", "Unknown"),
                "version": metadata.get("version", "1.0.0"),
                "has_avatar": bool(metadata.get("avatar_path")),
                "avatar_path": metadata.get("avatar_path"),
                "custom_fields": metadata.get("custom_fields", {}),
                "a2a_card_available": metadata.get("a2a_protocol", {}).get("agent_card_generated", False),
                "marketplace_ready": metadata.get("a2a_protocol", {}).get("marketplace_ready", False)
            }
        
        logger.info(f"{self.log_prefix} Listed {len(persona_list)} available personas.")
        return persona_list

    async def update_persona_avatar(self, persona_key: str, avatar_config: Dict[str, Any]) -> bool:
        """Updates the avatar for an existing persona."""
        persona_key_upper = persona_key.upper()
        if persona_key_upper not in self.personas:
            logger.error(f"{self.log_prefix} Persona '{persona_key}' not found for avatar update.")
            return False
        
        # Generate or assign new avatar
        avatar_path = await self._generate_or_assign_avatar(persona_key_upper, avatar_config)
        if avatar_path:
            # Update metadata
            if persona_key_upper not in self.persona_metadata:
                self.persona_metadata[persona_key_upper] = {}
            
            self.persona_metadata[persona_key_upper]["avatar_path"] = str(avatar_path)
            self.persona_metadata[persona_key_upper]["avatar_updated_timestamp"] = datetime.now(timezone.utc).isoformat()
            
            # Regenerate A2A Agent Card with new avatar
            await self._generate_a2a_agent_card(persona_key_upper, self.personas[persona_key_upper], self.persona_metadata[persona_key_upper])
            
            # Save metadata
            self._save_persona_metadata()
            
            logger.info(f"{self.log_prefix} Updated avatar for persona '{persona_key}'")
            return True
        
        return False

    async def update_persona_custom_fields(self, persona_key: str, custom_fields: Dict[str, Any]) -> bool:
        """Updates custom fields for an existing persona."""
        persona_key_upper = persona_key.upper()
        if persona_key_upper not in self.personas:
            logger.error(f"{self.log_prefix} Persona '{persona_key}' not found for custom fields update.")
            return False
        
        # Validate custom fields
        validated_fields = self._validate_custom_fields(custom_fields)
        
        # Update metadata
        if persona_key_upper not in self.persona_metadata:
            self.persona_metadata[persona_key_upper] = {}
        
        # Merge with existing custom fields
        existing_fields = self.persona_metadata[persona_key_upper].get("custom_fields", {})
        existing_fields.update(validated_fields)
        self.persona_metadata[persona_key_upper]["custom_fields"] = existing_fields
        self.persona_metadata[persona_key_upper]["custom_fields_updated_timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Regenerate A2A Agent Card with updated custom fields
        await self._generate_a2a_agent_card(persona_key_upper, self.personas[persona_key_upper], self.persona_metadata[persona_key_upper])
        
        # Save metadata
        self._save_persona_metadata()
        
        logger.info(f"{self.log_prefix} Updated custom fields for persona '{persona_key}'")
        return True

    def generate_agenticplace_manifest(self) -> Dict[str, Any]:
        """Generates a manifest file for AgenticPlace marketplace integration."""
        manifest = {
            "marketplace_manifest": {
                "platform": "AgenticPlace",
                "marketplace_url": self.agenticplace_base_url,
                "provider": {
                    "organization": "mindX",
                    "ecosystem": "mindX Autonomous Agent System",
                    "contact": "agents@mindx.ai",
                    "github": self.github_base_url
                },
                "collection_info": {
                    "name": "mindX Agent Personas",
                    "description": "Intelligent agent personas with A2A protocol compatibility for autonomous operation",
                    "total_agents": len(self.personas),
                    "creation_timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "3.0.0"
                },
                "a2a_protocol": {
                    "version": "2.0",
                    "specification_url": "https://github.com/google/A2A",
                    "compliance_level": "full",
                    "discovery_endpoint": f"{self.agenticplace_base_url}/.well-known/agents.json"
                },
                "agents": []
            }
        }
        
        # Add each persona to the manifest
        for persona_key in self.personas.keys():
            metadata = self.persona_metadata.get(persona_key, {})
            custom_fields = metadata.get("custom_fields", {})
            
            agent_entry = {
                "id": f"mindx_{persona_key.lower()}",
                "name": f"mindX {persona_key.title().replace('_', ' ')} Agent",
                "description": f"Specialized {persona_key.lower().replace('_', ' ')} agent with autonomous capabilities",
                "agent_card_url": f"{self.agenticplace_base_url}/agents/{persona_key.lower()}/card.json",
                "avatar_url": f"{self.agenticplace_base_url}/avatars/{persona_key.lower()}_avatar.svg",
                "pricing": {
                    "license_type": custom_fields.get("license_type", "open_source"),
                    "usage_cost": 0 if custom_fields.get("license_type", "open_source") == "open_source" else None
                },
                "capabilities": {
                    "autonomy_level": custom_fields.get("autonomy_level", 0.5),
                    "interaction_modes": [custom_fields.get("interaction_preference", "text")],
                    "specialization": custom_fields.get("specialization_domain", "general"),
                    "evolution_stage": custom_fields.get("evolution_stage", "genesis")
                },
                "marketplace_metadata": {
                    "tags": custom_fields.get("marketplace_tags", []),
                    "complexity_score": metadata.get("complexity_score", 0.5),
                    "cognitive_traits": metadata.get("cognitive_traits", []),
                    "a2a_compatible": True,
                    "blockchain_ready": True
                }
            }
            manifest["marketplace_manifest"]["agents"].append(agent_entry)
        
        # Save manifest
        manifest_path = self.inft_export_dir / "agenticplace_manifest.json"
        try:
            with manifest_path.open("w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            
            logger.info(f"{self.log_prefix} Generated AgenticPlace manifest at {manifest_path}")
            return manifest
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to generate AgenticPlace manifest: {e}")
            return {}

    def generate_a2a_discovery_endpoint(self) -> Dict[str, Any]:
        """Generates an A2A protocol discovery endpoint (/.well-known/agents.json)."""
        discovery_data = {
            "agents": [],
            "metadata": {
                "platform": "mindX",
                "ecosystem": "mindX Autonomous Agent System",
                "a2a_version": "2.0",
                "total_agents": len(self.personas),
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "discovery_endpoint": f"{self.agenticplace_base_url}/.well-known/agents.json"
            }
        }
        
        # Add each persona's discovery info
        for persona_key in self.personas.keys():
            metadata = self.persona_metadata.get(persona_key, {})
            
            agent_discovery = {
                "id": f"mindx_{persona_key.lower()}",
                "name": f"mindX {persona_key.title().replace('_', ' ')} Agent",
                "description": f"Autonomous {persona_key.lower().replace('_', ' ')} agent with A2A protocol compliance",
                "agent_card_url": f"{self.agenticplace_base_url}/agents/{persona_key.lower()}/card.json",
                "base_url": f"{self.agenticplace_base_url}/agents/{persona_key.lower()}",
                "capabilities": {
                    "streaming": True,
                    "pushNotifications": True,
                    "multimodal": metadata.get("custom_fields", {}).get("interaction_preference", "text") != "text",
                    "longRunningTasks": True
                },
                "authentication": ["bearer", "oauth2"],
                "status": "active",
                "version": metadata.get("version", "1.0.0")
            }
            discovery_data["agents"].append(agent_discovery)
        
        # Save discovery endpoint
        discovery_path = self.a2a_cards_dir / "agents_discovery.json"
        try:
            with discovery_path.open("w", encoding="utf-8") as f:
                json.dump(discovery_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"{self.log_prefix} Generated A2A discovery endpoint at {discovery_path}")
            return discovery_data
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to generate A2A discovery endpoint: {e}")
            return {}

    async def deploy_to_agenticplace(self, persona_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """Prepares deployment package for AgenticPlace marketplace."""
        deployment_keys = persona_keys or list(self.personas.keys())
        deployment_package = {
            "deployment_info": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "platform": "AgenticPlace",
                "deployer": "AutoMINDX Agent",
                "total_agents": len(deployment_keys)
            },
            "files_generated": {
                "inft_metadata": [],
                "agent_cards": [],
                "avatars": [],
                "manifests": []
            },
            "deployment_status": {}
        }
        
        # Export iNFT metadata for each persona
        for persona_key in deployment_keys:
            try:
                # Export iNFT metadata
                inft_metadata = self.export_persona_as_inft_metadata(persona_key)
                if inft_metadata:
                    inft_filename = f"persona_{persona_key.lower()}_inft.json"
                    inft_path = self.inft_export_dir / inft_filename
                    with inft_path.open("w", encoding="utf-8") as f:
                        json.dump(inft_metadata, f, indent=2, ensure_ascii=False)
                    deployment_package["files_generated"]["inft_metadata"].append(str(inft_path))
                
                # Check A2A card availability
                card_path = self.a2a_cards_dir / f"{persona_key.lower()}_agent_card.json"
                if card_path.exists():
                    deployment_package["files_generated"]["agent_cards"].append(str(card_path))
                
                # Check avatar availability
                avatar_svg = self.avatars_dir / f"{persona_key.lower()}_avatar.svg"
                if avatar_svg.exists():
                    deployment_package["files_generated"]["avatars"].append(str(avatar_svg))
                
                deployment_package["deployment_status"][persona_key] = "ready"
                
            except Exception as e:
                logger.error(f"{self.log_prefix} Failed to prepare {persona_key} for deployment: {e}")
                deployment_package["deployment_status"][persona_key] = f"failed: {e}"
        
        # Generate manifests
        agenticplace_manifest = self.generate_agenticplace_manifest()
        if agenticplace_manifest:
            deployment_package["files_generated"]["manifests"].append("agenticplace_manifest.json")
        
        a2a_discovery = self.generate_a2a_discovery_endpoint()
        if a2a_discovery:
            deployment_package["files_generated"]["manifests"].append("agents_discovery.json")
        
        blockchain_manifest = await self.create_blockchain_publication_manifest()
        if blockchain_manifest:
            deployment_package["files_generated"]["manifests"].append("blockchain_publication_manifest.json")
        
        # Save deployment package info
        deployment_path = self.inft_export_dir / "agenticplace_deployment.json"
        try:
            with deployment_path.open("w", encoding="utf-8") as f:
                json.dump(deployment_package, f, indent=2, ensure_ascii=False)
            
            logger.info(f"{self.log_prefix} Generated AgenticPlace deployment package at {deployment_path}")
            return deployment_package
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to generate deployment package: {e}")
            return {}
