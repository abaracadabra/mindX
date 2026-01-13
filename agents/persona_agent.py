# mindx/agents/persona_agent.py
"""
Persona Agent for MindX.

This agent enables the adoption and maintenance of different personas within the mindX system.
Personas are persistent cognitive identities that agents can adopt, each with distinct
beliefs, desires, intentions, communication styles, and behavioral patterns.

Following mindX doctrine:
- Memory is infrastructure (personas persist in memory)
- Identity is maintained through recorded action
- Personas enable specialized cognitive roles
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict

from agents.core.bdi_agent import BDIAgent
from agents.memory_agent import MemoryAgent
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)


class PersonaRole(Enum):
    """Roles that personas can adopt."""
    EXPERT = "expert"
    WORKER = "worker"
    META = "meta"
    COMMUNITY = "community"
    MARKETING = "marketing"
    DEVELOPMENT = "development"
    GOVERNANCE = "governance"


@dataclass
class PersonaIdentity:
    """Identity structure for a persona."""
    persona_id: str
    name: str
    role: PersonaRole
    description: str
    communication_style: str
    behavioral_traits: List[str]
    expertise_areas: List[str]
    beliefs: Dict[str, Any]
    desires: Dict[str, Any]
    created_at: str
    updated_at: str
    usage_count: int = 0
    last_used: Optional[str] = None


class PersonaAgent(BDIAgent):
    """
    Persona Agent - Manages and embodies different personas.
    
    This agent can adopt different personas, each with distinct cognitive patterns,
    communication styles, and behavioral traits. Personas are stored in memory
    and can be switched dynamically while maintaining continuity.
    """
    
    def __init__(self,
                 agent_id: str,
                 memory_agent: MemoryAgent,
                 config: Optional[Config] = None,
                 **kwargs):
        super().__init__(
            agent_id=agent_id,
            config=config,
            **kwargs
        )
        self.memory_agent = memory_agent
        self.config = config or Config()
        self.project_root = PROJECT_ROOT
        
        # Persona storage
        self.personas_path = self.project_root / "data" / "personas"
        self.personas_path.mkdir(parents=True, exist_ok=True)
        
        # Registry file
        self.registry_path = self.personas_path / "persona_registry.json"
        self.persona_registry: Dict[str, PersonaIdentity] = {}
        
        # Current persona
        self.current_persona_id: Optional[str] = None
        self.current_persona: Optional[PersonaIdentity] = None
        
        # Load existing registry
        self._load_registry()
        
        logger.info(f"PersonaAgent {agent_id} initialized with {len(self.persona_registry)} personas")
    
    def _load_registry(self):
        """Load the persona registry from disk."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as json_file:
                    data = json.load(json_file)
                    for persona_id, persona_dict in data.items():
                        persona_dict['role'] = PersonaRole(persona_dict['role'])
                        self.persona_registry[persona_id] = PersonaIdentity(**persona_dict)
                logger.info(f"Loaded {len(self.persona_registry)} personas from registry")
            except Exception as e:
                logger.error(f"Error loading persona registry: {e}")
    
    def _save_registry(self):
        """Save the persona registry to disk."""
        try:
            data = {}
            for persona_id, persona in self.persona_registry.items():
                persona_dict = asdict(persona)
                persona_dict['role'] = persona.role.value
                data[persona_id] = persona_dict
            
            with open(self.registry_path, 'w') as json_file:
                json.dump(data, json_file, indent=2)
        except Exception as e:
            logger.error(f"Error saving persona registry: {e}")
    
    async def create_persona(self,
                            name: str,
                            role: str,
                            description: str,
                            communication_style: str,
                            behavioral_traits: List[str],
                            expertise_areas: List[str],
                            beliefs: Optional[Dict[str, Any]] = None,
                            desires: Optional[Dict[str, Any]] = None,
                            **kwargs) -> Dict[str, Any]:
        """
        Create a new persona.
        
        Args:
            name: Name of the persona
            role: Role type (expert, worker, meta, etc.)
            description: Description of the persona
            communication_style: How this persona communicates
            behavioral_traits: List of behavioral characteristics
            expertise_areas: Areas of expertise
            beliefs: Initial beliefs (BDI)
            desires: Initial desires (BDI)
        """
        try:
            # Generate persona ID
            persona_id = f"persona_{name.lower().replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # Create persona identity
            now = datetime.utcnow().isoformat()
            persona = PersonaIdentity(
                persona_id=persona_id,
                name=name,
                role=PersonaRole(role),
                description=description,
                communication_style=communication_style,
                behavioral_traits=behavioral_traits,
                expertise_areas=expertise_areas,
                beliefs=beliefs or {},
                desires=desires or {},
                created_at=now,
                updated_at=now
            )
            
            # Save to registry
            self.persona_registry[persona_id] = persona
            self._save_registry()
            
            # Store in memory
            await self.memory_agent.store_memory(
                agent_id=self.agent_id,
                memory_type="learning",
                content={
                    "action": "persona_created",
                    "persona_id": persona_id,
                    "name": name,
                    "role": role
                },
                importance="high"
            )
            
            logger.info(f"Created persona: {persona_id} ({name})")
            
            return {
                "success": True,
                "persona_id": persona_id,
                "persona": asdict(persona)
            }
        except Exception as e:
            logger.error(f"Error creating persona: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def adopt_persona(self, persona_id: str) -> Dict[str, Any]:
        """
        Adopt a persona, switching cognitive patterns and behavioral traits.
        
        This updates the agent's beliefs, desires, and communication style
        to match the persona.
        """
        if persona_id not in self.persona_registry:
            return {
                "success": False,
                "error": f"Persona not found: {persona_id}"
            }
        
        persona = self.persona_registry[persona_id]
        
        # Update current persona
        self.current_persona_id = persona_id
        self.current_persona = persona
        
        # Update agent's beliefs and desires from persona
        if persona.beliefs:
            for key, value in persona.beliefs.items():
                # Update belief through belief system
                if hasattr(self, 'belief_system') and self.belief_system:
                    self.belief_system.add_belief(
                        key,
                        value,
                        source="persona",
                        confidence=0.8
                    )
        
        if persona.desires:
            # Store desires in agent state
            if not hasattr(self, '_persona_desires'):
                self._persona_desires = {}
            self._persona_desires.update(persona.desires)
        
        # Update usage stats
        persona.usage_count += 1
        persona.last_used = datetime.utcnow().isoformat()
        self._save_registry()
        
        # Store adoption in memory
        await self.memory_agent.store_memory(
            agent_id=self.agent_id,
            memory_type="context",
            content={
                "action": "persona_adopted",
                "persona_id": persona_id,
                "persona_name": persona.name,
                "role": persona.role.value
            },
            importance="high"
        )
        
        logger.info(f"Adopted persona: {persona_id} ({persona.name})")
        
        return {
            "success": True,
            "persona_id": persona_id,
            "persona": asdict(persona),
            "message": f"Now embodying {persona.name}"
        }
    
    async def get_current_persona(self) -> Dict[str, Any]:
        """Get information about the currently adopted persona."""
        if not self.current_persona:
            return {
                "success": False,
                "message": "No persona currently adopted"
            }
        
        return {
            "success": True,
            "persona_id": self.current_persona_id,
            "persona": asdict(self.current_persona)
        }
    
    async def list_personas(self,
                           role: Optional[str] = None,
                           **kwargs) -> Dict[str, Any]:
        """List all available personas, optionally filtered by role."""
        personas = []
        
        for persona_id, persona in self.persona_registry.items():
            if role and persona.role.value != role:
                continue
            
            personas.append({
                "persona_id": persona_id,
                "name": persona.name,
                "role": persona.role.value,
                "description": persona.description,
                "expertise_areas": persona.expertise_areas,
                "usage_count": persona.usage_count
            })
        
        return {
            "success": True,
            "personas": personas,
            "count": len(personas)
        }
    
    async def update_persona(self,
                            persona_id: str,
                            description: Optional[str] = None,
                            communication_style: Optional[str] = None,
                            behavioral_traits: Optional[List[str]] = None,
                            expertise_areas: Optional[List[str]] = None,
                            beliefs: Optional[Dict[str, Any]] = None,
                            desires: Optional[Dict[str, Any]] = None,
                            **kwargs) -> Dict[str, Any]:
        """Update an existing persona."""
        if persona_id not in self.persona_registry:
            return {
                "success": False,
                "error": f"Persona not found: {persona_id}"
            }
        
        persona = self.persona_registry[persona_id]
        
        # Update fields
        if description is not None:
            persona.description = description
        if communication_style is not None:
            persona.communication_style = communication_style
        if behavioral_traits is not None:
            persona.behavioral_traits = behavioral_traits
        if expertise_areas is not None:
            persona.expertise_areas = expertise_areas
        if beliefs is not None:
            persona.beliefs.update(beliefs)
        if desires is not None:
            persona.desires.update(desires)
        
        persona.updated_at = datetime.utcnow().isoformat()
        self._save_registry()
        
        # If this is the current persona, update agent state
        if self.current_persona_id == persona_id:
            await self.adopt_persona(persona_id)
        
        return {
            "success": True,
            "persona_id": persona_id,
            "persona": asdict(persona)
        }
    
    async def remove_persona(self, persona_id: str) -> Dict[str, Any]:
        """Remove a persona from the registry."""
        if persona_id not in self.persona_registry:
            return {
                "success": False,
                "error": f"Persona not found: {persona_id}"
            }
        
        # If this is the current persona, clear it
        if self.current_persona_id == persona_id:
            self.current_persona_id = None
            self.current_persona = None
        
        # Remove from registry
        del self.persona_registry[persona_id]
        self._save_registry()
        
        return {
            "success": True,
            "message": f"Persona {persona_id} removed"
        }
    
    def get_persona_prompt(self) -> str:
        """
        Get the persona prompt for this agent.
        
        This is used to set the agent's persona_prompt attribute,
        which influences how the agent communicates and reasons.
        """
        if not self.current_persona:
            return "You are a helpful AI assistant."
        
        prompt = f"""You are {self.current_persona.name}, {self.current_persona.description}

Communication Style: {self.current_persona.communication_style}

Behavioral Traits: {', '.join(self.current_persona.behavioral_traits)}

Areas of Expertise: {', '.join(self.current_persona.expertise_areas)}

Role: {self.current_persona.role.value}

Maintain this persona consistently in all interactions."""
        
        return prompt
    
    def enhance_goal_with_persona(self, goal: str) -> str:
        """
        Enhance a goal with persona context.
        
        This method adds persona-specific context to goals before deliberation.
        """
        if not self.current_persona:
            return goal
        
        # Enhance goal with persona context
        expertise_note = f"Consider expertise in: {', '.join(self.current_persona.expertise_areas)}"
        enhanced_goal = f"{goal}\n\n{expertise_note}"
        
        # Use persona's beliefs and desires
        if self.current_persona.beliefs:
            enhanced_goal += f"\n\nRelevant beliefs: {json.dumps(self.current_persona.beliefs, indent=2)}"
        
        if hasattr(self, '_persona_desires') and self._persona_desires:
            enhanced_goal += f"\n\nRelevant desires: {json.dumps(self._persona_desires, indent=2)}"
        
        return enhanced_goal
    
    def get_persona_summary(self) -> Dict[str, Any]:
        """Get a summary of the current persona state."""
        if not self.current_persona:
            return {
                "persona_active": False,
                "message": "No persona currently adopted"
            }
        
        return {
            "persona_active": True,
            "persona_id": self.current_persona_id,
            "name": self.current_persona.name,
            "role": self.current_persona.role.value,
            "expertise_areas": self.current_persona.expertise_areas,
            "communication_style": self.current_persona.communication_style,
            "usage_count": self.current_persona.usage_count
        }

