# Faicey Integration - Modular UI/UX Expression System

## Overview

Faicey is now integrated into the mindX agency system, enabling the creation of personalized interface expressions (faces) for agents. Faicey combines prompt, agent, dataset, model, and persona to generate modular, customizable UI/UX systems that adapt to each agent's identity.

## What is Faicey?

Faicey is a **UI/UX AIML modular response system** that creates personalized interface expressions for AI agents. It's conceptualized as a way to give agents a "face" - a modular, customizable interface that reflects their persona and capabilities.

**Reference**: [https://github.com/faicey](https://github.com/faicey)

**Related Projects**:
- [mlodular](https://github.com/mlodular) - Modular machine learning components
- [AUTOMINDx](https://github.com/AUTOMINDx) - Autonomous mind systems

## Faicey Principles

1. **User-Friendliness**: Intuitive interface with minimal learning curve
2. **Customization Options**: Toggle buttons, drag-and-drop modules
3. **Real-Time Feedback**: Immediate, actionable responses
4. **Seamless AI Integration**: Adaptable to new language models
5. **Modular, Scalable, Fast**: Easy module addition/removal
6. **Multi-Modal, Multi-Model**: Support various input/output modalities

## Integration Architecture

### FaiceyAgent

The `FaiceyAgent` (`agents/faicey_agent.py`) is responsible for:

- **Expression Generation**: Creates Faicey expressions from agent personas
- **Module Management**: Manages modular UI components
- **Customization**: Handles user customization options
- **Real-Time Feedback**: Configures feedback systems

### Expression Emergence

A Faicey expression emerges from the combination of:

1. **Prompt**: Agent instructions and system prompts
2. **Agent**: Agent identity, capabilities, and configuration
3. **Dataset**: Knowledge base and training data information
4. **Model**: LLM configuration and model capabilities
5. **Persona**: Cognitive identity, behavioral traits, communication style

### Default Modules

The system includes default UI modules:

- **text_input**: Text input field for user queries
- **text_output**: Text output area for agent responses
- **agent_status**: Display agent status and metrics
- **persona_display**: Show current persona information
- **model_info**: Display model configuration and capabilities
- **real_time_feedback**: Real-time progress and feedback indicators

## API Endpoints

### Create Expression

```http
POST /faicey/expressions
Content-Type: application/json

{
  "agent_id": "my_agent",
  "persona_id": "expert_persona_123",
  "prompt": "You are a helpful assistant",
  "agent_config": {...},
  "dataset_info": {...},
  "model_config": {...}
}
```

### List Expressions

```http
GET /faicey/expressions?agent_id=my_agent
```

### Get Expression

```http
GET /faicey/expressions/{expression_id}
```

### Get Expression for Agent

```http
GET /faicey/expressions/agent/{agent_id}
```

### Update Expression

```http
PUT /faicey/expressions/{expression_id}
Content-Type: application/json

{
  "ui_modules": [...],
  "customization_options": {...}
}
```

### Export UI Config

```http
GET /faicey/expressions/{expression_id}/ui-config
```

Returns a UI configuration object ready for frontend consumption.

## Usage Example

```python
from agents.faicey_agent import FaiceyAgent
from agents.memory_agent import MemoryAgent
from agents.persona_agent import PersonaAgent
from utils.config import Config

# Initialize
memory_agent = MemoryAgent()
persona_agent = PersonaAgent(agent_id="persona_manager", memory_agent=memory_agent)
faicey_agent = FaiceyAgent(
    agent_id="faicey_agent",
    memory_agent=memory_agent,
    persona_agent=persona_agent
)

# Create expression from persona
result = await faicey_agent.create_expression_from_persona(
    agent_id="my_agent",
    persona_id="expert_persona_123",
    prompt="You are an expert assistant",
    agent_config={"capabilities": ["reasoning", "code_generation"]},
    model_config={"provider": "gemini", "model": "gemini-pro"}
)

# Get UI configuration for frontend
ui_config = await faicey_agent.export_expression_ui_config(result["expression_id"])
```

## Storage

Faicey expressions are stored in:
- **Registry**: `data/faicey/faicey_registry.json`
- **Expressions**: `data/faicey/expressions/{expression_id}.json`
- **Modules**: `data/faicey/modules/module_registry.json`

## Integration with Agency System

Faicey integrates with the mindX agency system through:

1. **PersonaAgent**: Provides persona information for expression generation
2. **MemoryAgent**: Stores expression metadata and usage statistics
3. **BDIAgent**: Inherits BDI capabilities for goal-oriented expression design
4. **Agency Registry**: Expressions are linked to agents in the agency registry

## Skills and Rendering

### Skills System

Faicey expressions include a skills system that tracks agent capabilities:

- **Capability Skills**: Extracted from agent configuration
- **Expertise Skills**: Derived from persona expertise areas
- **Rendering Skills**: Three.js and wireframe rendering capabilities
- **Model Skills**: LLM integration capabilities

Each skill has:
- `skill_id`: Unique identifier
- `name`: Skill name
- `category`: Skill category (capability, expertise, rendering, model)
- `description`: Skill description
- `level`: Proficiency level (1-10)
- `enabled`: Whether the skill is active
- `config`: Skill-specific configuration

### Three.js Wireframe Rendering

Faicey includes Three.js integration for 3D wireframe rendering:

**Configuration**:
- Scene setup with fog and background
- Perspective camera with configurable FOV
- WebGL renderer with antialiasing and shadows
- OrbitControls for interactive navigation
- Ambient and directional lighting

**Wireframe Features**:
- Line-based wireframe meshes
- Vertex visualization
- Edge rendering
- Customizable colors and line widths
- Support for Box, Sphere, Plane, and custom geometries

**Usage**:
```javascript
import FaiceyThreeJSRenderer from './components/FaiceyThreeJS';

const renderer = new FaiceyThreeJSRenderer(containerElement, threejsConfig);

// Create wireframe shapes
renderer.createWireframeBox(1, wireframeConfig);
renderer.createWireframeSphere(1, 32, wireframeConfig);
renderer.createWireframePlane(2, 2, wireframeConfig);
```

**Wireframe Configuration**:
```json
{
  "enabled": true,
  "line_width": 1,
  "wireframe_color": "#00a8ff",
  "show_vertices": true,
  "show_edges": true,
  "vertex_size": 0.05,
  "material": {
    "type": "LineBasicMaterial",
    "color": "#00a8ff",
    "transparent": true,
    "opacity": 0.8
  }
}
```

## Advanced Three.js Features

Faicey includes support for advanced Three.js examples from the official Three.js documentation:

### Decals (webgl_decals)
Project decals onto 3D surfaces:
```javascript
const decal = renderer.createDecal(
    targetMesh,
    position,
    rotation,
    scale,
    texture
);
```
Reference: [https://threejs.org/examples/#webgl_decals](https://threejs.org/examples/#webgl_decals)

### Bumpmap Materials (webgl_materials_bumpmap)
Bump mapping and normal mapping:
```javascript
const material = renderer.createBumpmapMaterial(
    texture,
    bumpMap,
    normalMap,
    { bump_scale: 1.0, normal_scale: { x: 1, y: 1 } }
);
```
Reference: [https://threejs.org/examples/#webgl_materials_bumpmap](https://threejs.org/examples/#webgl_materials_bumpmap)

### PCD Point Cloud Loader (webgl_loader_pcd)
Load and render PCD point cloud files:
```javascript
const pointCloud = await renderer.loadPCD('path/to/file.pcd', {
    point_size: 1.0,
    point_color: '#00a8ff'
});
```
Reference: [https://threejs.org/examples/#webgl_loader_pcd](https://threejs.org/examples/#webgl_loader_pcd)

### Fat Wireframe Lines (webgl_lines_fat_wireframe)
Thick wireframe lines:
```javascript
const fatWireframe = renderer.createFatWireframe(geometry, {
    line_width: 5.0,
    line_color: '#00a8ff'
});
```
Reference: [https://threejs.org/examples/#webgl_lines_fat_wireframe](https://threejs.org/examples/#webgl_lines_fat_wireframe)

### Wireframe Materials (webgl_materials_wireframe)
Advanced wireframe material rendering:
```javascript
const wireframeMesh = renderer.createWireframeMeshWithMaterial(geometry, {
    wireframe_color: '#00a8ff',
    wireframe_linewidth: 2
});
```
Reference: [https://threejs.org/examples/#webgl_materials_wireframe](https://threejs.org/examples/#webgl_materials_wireframe)

### Video/Webcam Materials (webgl_materials_video_webcam)
Video texture and webcam material support:
```javascript
// Video texture
const videoTexture = renderer.createVideoTexture(videoElement);
const material = renderer.createVideoMaterial(videoTexture);

// Webcam texture
const webcamTexture = await renderer.createWebcamTexture({
    webcam_constraints: { video: true, audio: false }
});
```
Reference: [https://threejs.org/examples/#webgl_materials_video_webcam](https://threejs.org/examples/#webgl_materials_video_webcam)

### WebGPU Morph Targets (webgpu_morphtargets_face)
WebGPU morph targets for facial animation:
```javascript
const morphMesh = await renderer.createMorphTargetMesh(
    geometry,
    morphTargets,
    { morph_influence: 1.0 }
);

// Update morph target
renderer.updateMorphTargetInfluence(morphMesh, targetIndex, influence);
```
Reference: [https://threejs.org/examples/#webgpu_morphtargets_face](https://threejs.org/examples/#webgpu_morphtargets_face)

## Speech Inflection System

The speech inflection system provides complete facial animation for speaking, listening, and seeing modes using WebGPU morph targets.

### Features

- **Text-to-Speech Animation**: Converts text input to phonemes and animates mouth shapes (visemes)
- **Phoneme-to-Viseme Mapping**: Comprehensive mapping from English alphabet and phonemes to visual mouth shapes
- **Eye Movements**: Animated eye tracking, blinking, and directional movements
- **Eyebrow Expressions**: Dynamic eyebrow positions for emotional expression
- **Ear Animations**: Ears perk up during listening mode
- **Audio Synchronization**: Synchronizes morph target animations with audio playback
- **Multi-Alphabet Support**: Extensible system for multiple alphabets and tone systems

### Morph Target Categories

#### Mouth (Visemes) - 20+ targets
- **Vowels**: A, E, I, O, U, AW, AY, EY, OY
- **Consonants**: M/B/P, F/V, TH, L, W/Q, S/Z, SH/ZH, CH/J, R, N/D/T, K/G, H
- **Silence**: SIL (neutral mouth)

#### Eyes - 9+ targets
- Open, Closed, Blink, Look-left, Look-right, Look-up, Look-down, Squint, Wide-open

#### Eyebrows - 7+ targets
- Neutral, Raised, Furrowed, Relaxed, Left-raised, Right-raised, Both-raised

#### Ears - 4+ targets
- Neutral, Perked-up, Slightly-raised, Relaxed

### Usage

```javascript
import FaiceyThreeJSRenderer from './components/FaiceyThreeJS';
import FaiceySpeechInflection from './components/FaiceySpeechInflection';

// Create morph target mesh
const morphMesh = renderer.createMorphTargetMesh(geometry, morphTargets);

// Initialize speech inflection system
const speechSystem = await renderer.initializeSpeechInflection(morphMesh, {
    alphabet: 'english',
    viseme_blend_duration: 0.1,
    eye_blink_interval: 3.0
});

// Speaking mode
await speechSystem.startSpeaking("Hello, I am an AI agent", audioUrl);

// Listening mode
speechSystem.startListening();

// Stop
speechSystem.stopSpeaking();
speechSystem.stopListening();
```

### Configuration

```json
{
  "speech_inflection": {
    "enabled": true,
    "alphabet": "english",
    "tone_system": null,
    "viseme_blend_duration": 0.1,
    "eye_blink_interval": 3.0,
    "listening_ear_animation": true,
    "speaking_eye_tracking": true,
    "features": [
      "text_to_speech_animation",
      "phoneme_to_viseme_mapping",
      "eye_movements",
      "eyebrow_expressions",
      "ear_animations",
      "listening_mode",
      "speaking_mode",
      "audio_synchronization"
    ]
  }
}
```

### Animation Modes

#### Speaking Mode
1. Text input → Phoneme extraction
2. Phoneme → Viseme mapping
3. Generate animation timeline
4. Animate mouth shapes synchronized with audio
5. Eye movements follow speech rhythm
6. Subtle eyebrow movements for expression

#### Listening Mode
1. Ears perk up (morph target animation)
2. Eyes focus forward (attention)
3. Eyebrows slightly raised (engagement)
4. Return to neutral when listening ends

#### Idle Mode
1. Slow breathing animation
2. Random blinks
3. Subtle eye movements
4. Neutral expressions

### Phoneme-to-Viseme Mapping

The system uses comprehensive phoneme-to-viseme mappings stored in `data/faicey/phoneme_viseme_map.json`:

- **English Alphabet**: Full mapping of vowels and consonants to visemes
- **Multi-Alphabet Support**: Extensible for other languages
- **Tone Systems**: Support for tonal languages (Chinese, Thai, Vietnamese)
- **Blending Rules**: Smooth transitions between visemes

### Morph Target Definitions

Morph targets are defined in `data/faicey/morph_target_definitions.json`:

- **Influence Ranges**: Each target has valid influence range [0.0, 1.0]
- **Blending Rules**: Rules for combining multiple morph targets
- **Animation Timing**: Transition durations and timing parameters

## Future Enhancements

- Frontend UI components for rendering Faicey expressions
- Integration with mlodular for enhanced ML capabilities
- Multi-modal input/output support (voice, images, etc.)
- Dynamic module loading and plugin system
- Real-time expression updates based on agent state changes
- Advanced 3D visualizations for agent knowledge graphs
- Interactive wireframe manipulation tools

## API Endpoints for Speech Inflection

### Start Speaking

```http
POST /faicey/speech/speak
Content-Type: application/json

{
  "text": "Hello, I am an AI agent",
  "audio_url": "https://example.com/audio.mp3",
  "alphabet": "english",
  "tone_system": null
}
```

### Start Listening

```http
POST /faicey/speech/listen
```

Activates listening mode with ear and eye animations.

### Stop Speech/Listening

```http
POST /faicey/speech/stop
```

Returns to idle mode.

## Data Files

### Phoneme-to-Viseme Mapping

**File**: `data/faicey/phoneme_viseme_map.json`

Contains comprehensive mappings:
- English alphabet phonemes to visemes
- Multi-alphabet support structure
- Tone system definitions (Chinese, Thai, Vietnamese)
- Viseme blending rules
- Word boundary handling

### Morph Target Definitions

**File**: `data/faicey/morph_target_definitions.json`

Contains:
- Complete morph target definitions for mouth, eyes, eyebrows, ears
- Influence ranges and default values
- Blending rules for combining targets
- Animation timing parameters

## Implementation Details

### Text-to-Phoneme Conversion

The system converts text to phonemes using:
1. Character-by-character analysis
2. Two-character phoneme detection (TH, SH, CH, etc.)
3. Vowel and consonant classification
4. Space/punctuation handling (silence)

### Phoneme-to-Viseme Mapping

Each phoneme maps to a viseme (visual mouth shape):
- Vowels → Open mouth shapes (A, E, I, O, U)
- Consonants → Specific mouth/tongue positions
- Silence → Neutral closed mouth

### Animation Timeline

The system generates an animation timeline with:
- Viseme events with timing
- Eye movement events
- Blending between visemes
- Audio synchronization points

### Real-Time Animation

The animation loop:
1. Updates current time based on audio playback
2. Finds current viseme from timeline
3. Blends between current and next viseme
4. Updates eye movements and blinking
5. Handles mode transitions

## References

- [Faicey GitHub](https://github.com/faicey)
- [mlodular GitHub](https://github.com/mlodular)
- [AUTOMINDx GitHub](https://github.com/AUTOMINDx)
- [Three.js WebGPU Morph Targets](https://threejs.org/examples/#webgpu_morphtargets_face)