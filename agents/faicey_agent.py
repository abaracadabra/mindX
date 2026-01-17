# mindx/agents/faicey_agent.py
"""
Faicey Agent - Modular UI/UX Expression Generator for MindX Agents.

Faicey creates personalized interface expressions (faces) for agents based on their:
- Prompt (initial instructions)
- Agent (identity and capabilities)
- Dataset (training data and knowledge)
- Model (LLM configuration)
- Persona (cognitive identity and behavioral traits)

Following Faicey principles:
- User-friendliness: Intuitive, minimal learning curve
- Customization: Toggle buttons, drag-and-drop modules
- Real-time feedback: Immediate, actionable responses
- Seamless AI integration: Adaptable to new models
- Modular, scalable, fast: Easy module addition/removal
- Multi-modal, multi-model: Support various input/output modalities

Reference: https://github.com/faicey
Related: https://github.com/mlodular (modular ML components)
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict, field

from agents.core.bdi_agent import BDIAgent
from agents.memory_agent import MemoryAgent
from agents.persona_agent import PersonaAgent
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class FaiceySkill:
    """A skill or capability for a Faicey expression."""
    skill_id: str
    name: str
    category: str  # visualization, interaction, rendering, etc.
    description: str
    level: int = 1  # Skill proficiency level (1-10)
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FaiceyExpression:
    """A Faicey UI/UX expression for an agent."""
    expression_id: str
    agent_id: str
    persona_id: Optional[str]
    
    # Core components
    prompt: str
    agent_config: Dict[str, Any]
    dataset_info: Dict[str, Any]
    model_config: Dict[str, Any]
    persona_config: Dict[str, Any]
    
    # Skills and capabilities
    skills: List[Dict[str, Any]] = field(default_factory=list)
    
    # UI/UX components
    ui_modules: List[Dict[str, Any]] = field(default_factory=list)
    customization_options: Dict[str, Any] = field(default_factory=dict)
    real_time_feedback_config: Dict[str, Any] = field(default_factory=dict)
    
    # 3D Rendering configuration
    threejs_config: Dict[str, Any] = field(default_factory=dict)
    wireframe_config: Dict[str, Any] = field(default_factory=dict)
    
    # Speech inflection configuration
    speech_inflection_config: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: str = "1.0.0"
    
    # Usage stats
    usage_count: int = 0
    last_used: Optional[str] = None


@dataclass
class FaiceyModule:
    """A modular UI component for Faicey expressions."""
    module_id: str
    module_type: str  # input, output, control, visualization, etc.
    name: str
    description: str
    config: Dict[str, Any]
    position: Dict[str, float]  # x, y coordinates for drag-and-drop
    visible: bool = True
    enabled: bool = True


class FaiceyAgent(BDIAgent):
    """
    Faicey Agent - Generates modular UI/UX expressions from agent personas.
    
    This agent creates personalized "faces" (interfaces) for agents by combining:
    - Agent prompts and configurations
    - Persona characteristics
    - Model capabilities
    - Dataset information
    
    The resulting Faicey expression is a modular, customizable UI/UX system that
    adapts to the agent's identity and capabilities.
    """
    
    def __init__(self,
                 agent_id: str = "faicey_agent",
                 memory_agent: Optional[MemoryAgent] = None,
                 persona_agent: Optional[PersonaAgent] = None,
                 config: Optional[Config] = None,
                 **kwargs):
        super().__init__(
            agent_id=agent_id,
            config=config,
            **kwargs
        )
        self.memory_agent = memory_agent or MemoryAgent(config=config or Config())
        self.persona_agent = persona_agent
        self.config = config or Config()
        self.project_root = PROJECT_ROOT
        
        # Faicey storage
        self.faicey_path = self.project_root / "data" / "faicey"
        self.faicey_path.mkdir(parents=True, exist_ok=True)
        self.expressions_path = self.faicey_path / "expressions"
        self.expressions_path.mkdir(parents=True, exist_ok=True)
        self.modules_path = self.faicey_path / "modules"
        self.modules_path.mkdir(parents=True, exist_ok=True)
        
        # Registry
        self.registry_path = self.faicey_path / "faicey_registry.json"
        self.expression_registry: Dict[str, FaiceyExpression] = {}
        self.module_registry: Dict[str, FaiceyModule] = {}
        
        # Load existing data
        self._load_registry()
        self._load_modules()
        
        logger.info(f"FaiceyAgent {agent_id} initialized with {len(self.expression_registry)} expressions and {len(self.module_registry)} modules")
    
    def _load_registry(self):
        """Load the Faicey expression registry."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r') as f:
                    data = json.load(f)
                    for expr_id, expr_dict in data.get("expressions", {}).items():
                        self.expression_registry[expr_id] = FaiceyExpression(**expr_dict)
                logger.info(f"Loaded {len(self.expression_registry)} Faicey expressions")
            except Exception as e:
                logger.error(f"Error loading Faicey registry: {e}")
    
    def _save_registry(self):
        """Save the Faicey expression registry."""
        try:
            data = {
                "expressions": {
                    expr_id: asdict(expr)
                    for expr_id, expr in self.expression_registry.items()
                },
                "last_updated": datetime.utcnow().isoformat()
            }
            with open(self.registry_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving Faicey registry: {e}")
    
    def _load_modules(self):
        """Load available UI modules."""
        modules_file = self.modules_path / "module_registry.json"
        if modules_file.exists():
            try:
                with open(modules_file, 'r') as f:
                    data = json.load(f)
                    for module_id, module_dict in data.items():
                        self.module_registry[module_id] = FaiceyModule(**module_dict)
                logger.info(f"Loaded {len(self.module_registry)} Faicey modules")
            except Exception as e:
                logger.error(f"Error loading Faicey modules: {e}")
        else:
            # Initialize with default modules
            self._initialize_default_modules()
    
    def _initialize_default_modules(self):
        """Initialize default UI modules."""
        default_modules = [
            {
                "module_id": "text_input",
                "module_type": "input",
                "name": "Text Input",
                "description": "Text input field for user queries",
                "config": {"multiline": True, "placeholder": "Enter your message..."},
                "position": {"x": 0, "y": 0}
            },
            {
                "module_id": "text_output",
                "module_type": "output",
                "name": "Text Output",
                "description": "Text output area for agent responses",
                "config": {"scrollable": True, "formatted": True},
                "position": {"x": 0, "y": 200}
            },
            {
                "module_id": "agent_status",
                "module_type": "visualization",
                "name": "Agent Status",
                "description": "Display agent status and metrics",
                "config": {"show_metrics": True, "show_capabilities": True},
                "position": {"x": 300, "y": 0}
            },
            {
                "module_id": "persona_display",
                "module_type": "visualization",
                "name": "Persona Display",
                "description": "Show current persona information",
                "config": {"show_traits": True, "show_expertise": True},
                "position": {"x": 300, "y": 150}
            },
            {
                "module_id": "model_info",
                "module_type": "visualization",
                "name": "Model Information",
                "description": "Display model configuration and capabilities",
                "config": {"show_config": True, "show_stats": True},
                "position": {"x": 300, "y": 300}
            },
            {
                "module_id": "real_time_feedback",
                "module_type": "control",
                "name": "Real-time Feedback",
                "description": "Real-time progress and feedback indicators",
                "config": {"show_progress": True, "show_suggestions": True},
                "position": {"x": 0, "y": 400}
            },
            {
                "module_id": "threejs_viewer",
                "module_type": "rendering",
                "name": "Three.js 3D Viewer",
                "description": "3D visualization using Three.js with wireframe rendering",
                "config": {
                    "enable_wireframe": True,
                    "show_axes": True,
                    "camera_type": "perspective",
                    "controls": "orbit"
                },
                "position": {"x": 600, "y": 0}
            },
            {
                "module_id": "wireframe_renderer",
                "module_type": "rendering",
                "name": "Wireframe Renderer",
                "description": "Wireframe mesh rendering for 3D structures",
                "config": {
                    "line_width": 1,
                    "wireframe_color": "#00a8ff",
                    "show_vertices": True,
                    "show_edges": True
                },
                "position": {"x": 600, "y": 300}
            },
            {
                "module_id": "skills_display",
                "module_type": "visualization",
                "name": "Skills Display",
                "description": "Display agent skills and capabilities",
                "config": {
                    "show_levels": True,
                    "show_categories": True,
                    "interactive": True
                },
                "position": {"x": 300, "y": 450}
            },
            {
                "module_id": "decals_renderer",
                "module_type": "rendering",
                "name": "Decals Renderer",
                "description": "Decal projection and rendering using Three.js decals",
                "config": {
                    "enable_decals": True,
                    "decal_size": {"x": 1, "y": 1, "z": 1},
                    "decal_rotation": 0
                },
                "position": {"x": 600, "y": 600}
            },
            {
                "module_id": "bumpmap_materials",
                "module_type": "rendering",
                "name": "Bumpmap Materials",
                "description": "Bump mapping and normal mapping materials",
                "config": {
                    "enable_bumpmap": True,
                    "bump_scale": 1.0,
                    "normal_scale": {"x": 1, "y": 1}
                },
                "position": {"x": 900, "y": 0}
            },
            {
                "module_id": "pcd_loader",
                "module_type": "loader",
                "name": "PCD Point Cloud Loader",
                "description": "Load and render PCD point cloud files",
                "config": {
                    "enable_pcd": True,
                    "point_size": 1.0,
                    "point_color": "#00a8ff"
                },
                "position": {"x": 900, "y": 150}
            },
            {
                "module_id": "fat_wireframe",
                "module_type": "rendering",
                "name": "Fat Wireframe Lines",
                "description": "Thick wireframe lines using fat lines technique",
                "config": {
                    "line_width": 5.0,
                    "line_color": "#00a8ff",
                    "enable_fat_lines": True
                },
                "position": {"x": 600, "y": 300}
            },
            {
                "module_id": "wireframe_materials",
                "module_type": "rendering",
                "name": "Wireframe Materials",
                "description": "Advanced wireframe material rendering",
                "config": {
                    "wireframe": True,
                    "wireframe_linewidth": 2,
                    "wireframe_color": "#00a8ff"
                },
                "position": {"x": 600, "y": 450}
            },
            {
                "module_id": "video_webcam_materials",
                "module_type": "rendering",
                "name": "Video/Webcam Materials",
                "description": "Video texture and webcam material support",
                "config": {
                    "enable_video": True,
                    "enable_webcam": True,
                    "video_autoplay": True,
                    "webcam_constraints": {"video": True, "audio": False}
                },
                "position": {"x": 900, "y": 300}
            },
            {
                "module_id": "webgpu_morph_targets",
                "module_type": "rendering",
                "name": "WebGPU Morph Targets",
                "description": "WebGPU morph targets for facial animation",
                "config": {
                    "enable_webgpu": True,
                    "enable_morph_targets": True,
                    "morph_influence": 1.0
                },
                "position": {"x": 900, "y": 450}
            }
        ]
        
        for module_dict in default_modules:
            module = FaiceyModule(**module_dict)
            self.module_registry[module.module_id] = module
        
        self._save_modules()
    
    def _save_modules(self):
        """Save module registry."""
        try:
            data = {
                module_id: asdict(module)
                for module_id, module in self.module_registry.items()
            }
            with open(self.modules_path / "module_registry.json", 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving Faicey modules: {e}")
    
    async def create_expression_from_persona(self,
                                            agent_id: str,
                                            persona_id: Optional[str] = None,
                                            prompt: Optional[str] = None,
                                            agent_config: Optional[Dict[str, Any]] = None,
                                            dataset_info: Optional[Dict[str, Any]] = None,
                                            model_config: Optional[Dict[str, Any]] = None,
                                            **kwargs) -> Dict[str, Any]:
        """
        Create a Faicey expression from an agent's persona.
        
        This is the core emergence function that combines:
        - Prompt (agent instructions)
        - Agent (identity and capabilities)
        - Dataset (knowledge base)
        - Model (LLM configuration)
        - Persona (cognitive identity)
        
        To create a personalized UI/UX expression.
        """
        try:
            # Get persona information if provided
            persona_config = {}
            if persona_id and self.persona_agent:
                persona_result = await self.persona_agent.adopt_persona(persona_id)
                if persona_result.get("success"):
                    persona = persona_result.get("persona", {})
                    persona_config = {
                        "persona_id": persona_id,
                        "name": persona.get("name"),
                        "role": persona.get("role"),
                        "communication_style": persona.get("communication_style"),
                        "behavioral_traits": persona.get("behavioral_traits", []),
                        "expertise_areas": persona.get("expertise_areas", []),
                        "beliefs": persona.get("beliefs", {}),
                        "desires": persona.get("desires", {})
                    }
            
            # Generate expression ID
            expression_id = f"faicey_{agent_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # Extract and generate skills from agent config and persona
            skills = self._extract_skills_from_config(
                agent_config=agent_config or {},
                persona_config=persona_config,
                model_config=model_config or {}
            )
            
            # Select modules based on persona and agent config
            ui_modules = self._select_modules_for_expression(
                persona_config=persona_config,
                agent_config=agent_config or {},
                skills=skills
            )
            
            # Configure customization options
            customization_options = self._generate_customization_options(
                persona_config=persona_config,
                agent_config=agent_config or {}
            )
            
            # Configure real-time feedback
            real_time_feedback_config = self._generate_feedback_config(
                persona_config=persona_config
            )
            
            # Configure Three.js and wireframe rendering
            threejs_config = self._generate_threejs_config(
                skills=skills,
                persona_config=persona_config
            )
            wireframe_config = self._generate_wireframe_config(
                skills=skills
            )
            
            # Configure speech inflection
            speech_inflection_config = self._generate_speech_inflection_config(
                skills=skills,
                persona_config=persona_config
            )
            
            # Create expression
            expression = FaiceyExpression(
                expression_id=expression_id,
                agent_id=agent_id,
                persona_id=persona_id,
                prompt=prompt or f"Agent {agent_id} interface",
                agent_config=agent_config or {},
                dataset_info=dataset_info or {},
                model_config=model_config or {},
                persona_config=persona_config,
                skills=[asdict(skill) for skill in skills],
                ui_modules=ui_modules,
                customization_options=customization_options,
                real_time_feedback_config=real_time_feedback_config,
                threejs_config=threejs_config,
                wireframe_config=wireframe_config,
                speech_inflection_config=speech_inflection_config
            )
            
            # Save expression
            self.expression_registry[expression_id] = expression
            self._save_registry()
            
            # Save individual expression file
            expr_file = self.expressions_path / f"{expression_id}.json"
            with open(expr_file, 'w') as f:
                json.dump(asdict(expression), f, indent=2)
            
            # Store in memory
            await self.memory_agent.store_memory(
                agent_id=self.agent_id,
                memory_type="learning",
                content={
                    "action": "faicey_expression_created",
                    "expression_id": expression_id,
                    "agent_id": agent_id,
                    "persona_id": persona_id
                },
                importance="high"
            )
            
            logger.info(f"Created Faicey expression: {expression_id} for agent {agent_id}")
            
            return {
                "success": True,
                "expression_id": expression_id,
                "expression": asdict(expression)
            }
            
        except Exception as e:
            logger.error(f"Error creating Faicey expression: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_skills_from_config(self,
                                   agent_config: Dict[str, Any],
                                   persona_config: Dict[str, Any],
                                   model_config: Dict[str, Any]) -> List[FaiceySkill]:
        """Extract skills from agent, persona, and model configuration."""
        skills = []
        
        # Extract from agent capabilities
        capabilities = agent_config.get("capabilities", [])
        for cap in capabilities:
            skill = FaiceySkill(
                skill_id=f"skill_{cap.lower().replace(' ', '_')}",
                name=cap,
                category="capability",
                description=f"Agent capability: {cap}",
                level=5,
                enabled=True
            )
            skills.append(skill)
        
        # Extract from persona expertise
        expertise_areas = persona_config.get("expertise_areas", [])
        for area in expertise_areas:
            skill = FaiceySkill(
                skill_id=f"skill_expertise_{area.lower().replace(' ', '_')}",
                name=area,
                category="expertise",
                description=f"Expertise area: {area}",
                level=7,
                enabled=True
            )
            skills.append(skill)
        
        # Add rendering skills
        rendering_skill = FaiceySkill(
            skill_id="skill_threejs_rendering",
            name="Three.js Rendering",
            category="rendering",
            description="3D rendering using Three.js with wireframe support",
            level=8,
            enabled=True,
            config={
                "library": "three.js",
                "version": "0.160.0",
                "features": ["wireframe", "mesh", "geometry", "materials"]
            }
        )
        skills.append(rendering_skill)
        
        wireframe_skill = FaiceySkill(
            skill_id="skill_wireframe",
            name="Wireframe Rendering",
            category="rendering",
            description="Wireframe mesh rendering for 3D structures",
            level=7,
            enabled=True,
            config={
                "line_width": 1,
                "wireframe_color": "#00a8ff",
                "show_vertices": True,
                "show_edges": True
            }
        )
        skills.append(wireframe_skill)
        
        # Advanced Three.js skills
        decals_skill = FaiceySkill(
            skill_id="skill_decals",
            name="Decals Rendering",
            category="rendering",
            description="Decal projection and rendering (webgl_decals)",
            level=8,
            enabled=True,
            config={
                "reference": "https://threejs.org/examples/#webgl_decals",
                "decal_size": {"x": 1, "y": 1, "z": 1}
            }
        )
        skills.append(decals_skill)
        
        bumpmap_skill = FaiceySkill(
            skill_id="skill_bumpmap",
            name="Bumpmap Materials",
            category="rendering",
            description="Bump mapping and normal mapping (webgl_materials_bumpmap)",
            level=7,
            enabled=True,
            config={
                "reference": "https://threejs.org/examples/#webgl_materials_bumpmap",
                "bump_scale": 1.0,
                "normal_scale": {"x": 1, "y": 1}
            }
        )
        skills.append(bumpmap_skill)
        
        pcd_loader_skill = FaiceySkill(
            skill_id="skill_pcd_loader",
            name="PCD Point Cloud Loader",
            category="loader",
            description="PCD point cloud file loading (webgl_loader_pcd)",
            level=8,
            enabled=True,
            config={
                "reference": "https://threejs.org/examples/#webgl_loader_pcd",
                "point_size": 1.0,
                "point_color": "#00a8ff"
            }
        )
        skills.append(pcd_loader_skill)
        
        fat_wireframe_skill = FaiceySkill(
            skill_id="skill_fat_wireframe",
            name="Fat Wireframe Lines",
            category="rendering",
            description="Thick wireframe lines (webgl_lines_fat_wireframe)",
            level=8,
            enabled=True,
            config={
                "reference": "https://threejs.org/examples/#webgl_lines_fat_wireframe",
                "line_width": 5.0,
                "line_color": "#00a8ff"
            }
        )
        skills.append(fat_wireframe_skill)
        
        wireframe_materials_skill = FaiceySkill(
            skill_id="skill_wireframe_materials",
            name="Wireframe Materials",
            category="rendering",
            description="Advanced wireframe material rendering (webgl_materials_wireframe)",
            level=7,
            enabled=True,
            config={
                "reference": "https://threejs.org/examples/#webgl_materials_wireframe",
                "wireframe_linewidth": 2,
                "wireframe_color": "#00a8ff"
            }
        )
        skills.append(wireframe_materials_skill)
        
        video_webcam_skill = FaiceySkill(
            skill_id="skill_video_webcam",
            name="Video/Webcam Materials",
            category="rendering",
            description="Video texture and webcam material support (webgl_materials_video_webcam)",
            level=9,
            enabled=True,
            config={
                "reference": "https://threejs.org/examples/#webgl_materials_video_webcam",
                "enable_video": True,
                "enable_webcam": True
            }
        )
        skills.append(video_webcam_skill)
        
        webgpu_morph_skill = FaiceySkill(
            skill_id="skill_webgpu_morph",
            name="WebGPU Morph Targets",
            category="rendering",
            description="WebGPU morph targets for facial animation (webgpu_morphtargets_face)",
            level=9,
            enabled=True,
            config={
                "reference": "https://threejs.org/examples/#webgpu_morphtargets_face",
                "enable_webgpu": True,
                "morph_influence": 1.0
            }
        )
        skills.append(webgpu_morph_skill)
        
        # Speech inflection skill
        speech_inflection_skill = FaiceySkill(
            skill_id="skill_speech_inflection",
            name="Speech Inflection System",
            category="rendering",
            description="Complete speech inflection with morph targets for speaking, listening, and seeing",
            level=10,
            enabled=True,
            config={
                "reference": "https://threejs.org/examples/#webgpu_morphtargets_face",
                "features": [
                    "text_to_speech_animation",
                    "phoneme_to_viseme_mapping",
                    "eye_movements",
                    "eyebrow_expressions",
                    "ear_animations",
                    "listening_mode",
                    "speaking_mode",
                    "audio_synchronization"
                ],
                "alphabet": "english",
                "tone_system": None,
                "viseme_blend_duration": 0.1,
                "eye_blink_interval": 3.0
            }
        )
        skills.append(speech_inflection_skill)
        
        # Add model-specific skills
        if model_config.get("provider"):
            model_skill = FaiceySkill(
                skill_id=f"skill_model_{model_config.get('provider')}",
                name=f"{model_config.get('provider', 'Model')} Integration",
                category="model",
                description=f"Integration with {model_config.get('provider')} model",
                level=6,
                enabled=True,
                config=model_config
            )
            skills.append(model_skill)
        
        return skills
    
    def _select_modules_for_expression(self,
                                      persona_config: Dict[str, Any],
                                      agent_config: Dict[str, Any],
                                      skills: List[FaiceySkill]) -> List[Dict[str, Any]]:
        """Select appropriate UI modules based on persona and agent configuration."""
        selected_modules = []
        
        # Always include core modules
        core_modules = ["text_input", "text_output", "real_time_feedback"]
        for module_id in core_modules:
            if module_id in self.module_registry:
                module = self.module_registry[module_id]
                selected_modules.append(asdict(module))
        
        # Add persona-specific modules
        if persona_config.get("role") == "expert":
            if "agent_status" in self.module_registry:
                selected_modules.append(asdict(self.module_registry["agent_status"]))
        
        if persona_config.get("persona_id"):
            if "persona_display" in self.module_registry:
                selected_modules.append(asdict(self.module_registry["persona_display"]))
        
        # Add model info if model config provided
        if agent_config.get("model") or agent_config.get("llm_handler"):
            if "model_info" in self.module_registry:
                selected_modules.append(asdict(self.module_registry["model_info"]))
        
        # Add Three.js viewer if rendering skills present
        rendering_skills = [s for s in skills if s.category == "rendering"]
        if rendering_skills:
            if "threejs_viewer" in self.module_registry:
                selected_modules.append(asdict(self.module_registry["threejs_viewer"]))
            if "wireframe_renderer" in self.module_registry:
                selected_modules.append(asdict(self.module_registry["wireframe_renderer"]))
        
        # Add skills display if skills present
        if skills:
            if "skills_display" in self.module_registry:
                selected_modules.append(asdict(self.module_registry["skills_display"]))
        
        return selected_modules
    
    def _generate_customization_options(self,
                                       persona_config: Dict[str, Any],
                                       agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate customization options for the expression."""
        return {
            "drag_and_drop": True,
            "toggle_modules": True,
            "resize_modules": True,
            "theme_options": [
                "default",
                "dark",
                "light",
                "cyberpunk"
            ],
            "layout_presets": [
                "standard",
                "compact",
                "expanded",
                "custom"
            ],
            "persona_specific": {
                "communication_style_toggle": bool(persona_config.get("communication_style")),
                "expertise_highlight": bool(persona_config.get("expertise_areas"))
            }
        }
    
    def _generate_feedback_config(self, persona_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate real-time feedback configuration."""
        return {
            "show_progress": True,
            "show_suggestions": True,
            "show_completion_notifications": True,
            "feedback_delay_ms": 100,
            "persona_aware": bool(persona_config.get("persona_id")),
            "adaptive_feedback": True
        }
    
    def _generate_threejs_config(self,
                                skills: List[FaiceySkill],
                                persona_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Three.js configuration for 3D rendering."""
        rendering_skills = [s for s in skills if s.category == "rendering"]
        
        config = {
            "enabled": len(rendering_skills) > 0,
            "library": "three.js",
            "version": "0.160.0",
            "scene": {
                "background_color": "#0a0a0a",
                "fog_enabled": True,
                "fog_color": "#000000",
                "fog_near": 1,
                "fog_far": 1000
            },
            "camera": {
                "type": "perspective",
                "fov": 75,
                "near": 0.1,
                "far": 1000,
                "position": {"x": 0, "y": 0, "z": 5}
            },
            "renderer": {
                "antialias": True,
                "alpha": True,
                "shadow_map": True,
                "shadow_map_type": "PCFSoft"
            },
            "controls": {
                "type": "OrbitControls",
                "enable_damping": True,
                "damping_factor": 0.05,
                "enable_zoom": True,
                "enable_rotate": True,
                "enable_pan": True
            },
            "lights": [
                {
                    "type": "ambient",
                    "color": "#404040",
                    "intensity": 0.5
                },
                {
                    "type": "directional",
                    "color": "#ffffff",
                    "intensity": 0.8,
                    "position": {"x": 5, "y": 5, "z": 5},
                    "cast_shadow": True
                }
            ]
        }
        
        # Add wireframe-specific config if wireframe skill present
        wireframe_skills = [s for s in rendering_skills if "wireframe" in s.name.lower()]
        if wireframe_skills:
            wireframe_skill = wireframe_skills[0]
            config["wireframe"] = wireframe_skill.config
        
        return config
    
    def _generate_wireframe_config(self, skills: List[FaiceySkill]) -> Dict[str, Any]:
        """Generate wireframe rendering configuration."""
        wireframe_skills = [s for s in skills if "wireframe" in s.name.lower()]
        
        if not wireframe_skills:
            return {
                "enabled": False
            }
        
        wireframe_skill = wireframe_skills[0]
        
        return {
            "enabled": True,
            "line_width": wireframe_skill.config.get("line_width", 1),
            "wireframe_color": wireframe_skill.config.get("wireframe_color", "#00a8ff"),
            "show_vertices": wireframe_skill.config.get("show_vertices", True),
            "show_edges": wireframe_skill.config.get("show_edges", True),
            "vertex_size": 0.05,
            "edge_geometry": "edges",
            "material": {
                "type": "LineBasicMaterial",
                "color": wireframe_skill.config.get("wireframe_color", "#00a8ff"),
                "linewidth": wireframe_skill.config.get("line_width", 1),
                "transparent": True,
                "opacity": 0.8
            }
        }
    
    def _generate_speech_inflection_config(self,
                                          skills: List[FaiceySkill],
                                          persona_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate speech inflection configuration."""
        speech_skills = [s for s in skills if s.skill_id == "skill_speech_inflection"]
        
        if not speech_skills:
            return {
                "enabled": False
            }
        
        speech_skill = speech_skills[0]
        
        return {
            "enabled": True,
            "alphabet": speech_skill.config.get("alphabet", "english"),
            "tone_system": speech_skill.config.get("tone_system"),
            "viseme_blend_duration": speech_skill.config.get("viseme_blend_duration", 0.1),
            "eye_blink_interval": speech_skill.config.get("eye_blink_interval", 3.0),
            "listening_ear_animation": True,
            "speaking_eye_tracking": True,
            "features": speech_skill.config.get("features", []),
            "morph_targets": {
                "mouth_visemes": 20,
                "eye_states": 9,
                "eyebrow_states": 7,
                "ear_states": 4
            }
        }
    
    async def get_expression(self, expression_id: str) -> Dict[str, Any]:
        """Get a Faicey expression by ID."""
        if expression_id not in self.expression_registry:
            return {
                "success": False,
                "error": f"Expression not found: {expression_id}"
            }
        
        expression = self.expression_registry[expression_id]
        expression.usage_count += 1
        expression.last_used = datetime.utcnow().isoformat()
        self._save_registry()
        
        return {
            "success": True,
            "expression": asdict(expression)
        }
    
    async def get_expression_for_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get the most recent Faicey expression for an agent."""
        agent_expressions = [
            expr for expr in self.expression_registry.values()
            if expr.agent_id == agent_id
        ]
        
        if not agent_expressions:
            return {
                "success": False,
                "error": f"No expressions found for agent: {agent_id}"
            }
        
        # Get most recent
        latest = max(agent_expressions, key=lambda e: e.created_at)
        return await self.get_expression(latest.expression_id)
    
    async def update_expression(self,
                               expression_id: str,
                               ui_modules: Optional[List[Dict[str, Any]]] = None,
                               customization_options: Optional[Dict[str, Any]] = None,
                               **kwargs) -> Dict[str, Any]:
        """Update a Faicey expression."""
        if expression_id not in self.expression_registry:
            return {
                "success": False,
                "error": f"Expression not found: {expression_id}"
            }
        
        expression = self.expression_registry[expression_id]
        
        if ui_modules is not None:
            expression.ui_modules = ui_modules
        if customization_options is not None:
            expression.customization_options.update(customization_options)
        
        expression.updated_at = datetime.utcnow().isoformat()
        self._save_registry()
        
        # Update file
        expr_file = self.expressions_path / f"{expression_id}.json"
        if expr_file.exists():
            with open(expr_file, 'w') as f:
                json.dump(asdict(expression), f, indent=2)
        
        return {
            "success": True,
            "expression": asdict(expression)
        }
    
    async def list_expressions(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """List all Faicey expressions, optionally filtered by agent."""
        expressions = list(self.expression_registry.values())
        
        if agent_id:
            expressions = [e for e in expressions if e.agent_id == agent_id]
        
        return {
            "success": True,
            "expressions": [asdict(e) for e in expressions],
            "count": len(expressions)
        }
    
    async def export_expression_ui_config(self, expression_id: str) -> Dict[str, Any]:
        """Export expression as UI configuration for frontend."""
        result = await self.get_expression(expression_id)
        if not result.get("success"):
            return result
        
        expression = result["expression"]
        
        # Format for frontend consumption
        ui_config = {
            "expression_id": expression["expression_id"],
            "agent_id": expression["agent_id"],
            "persona": expression["persona_config"],
            "modules": expression["ui_modules"],
            "customization": expression["customization_options"],
            "feedback": expression["real_time_feedback_config"],
            "theme": {
                "name": expression["persona_config"].get("name", "default"),
                "style": expression["persona_config"].get("communication_style", "professional")
            }
        }
        
        return {
            "success": True,
            "ui_config": ui_config
        }
