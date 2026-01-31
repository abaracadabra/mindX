# Faicey - UIUX AIML Modular Face Rendering System

**Faicey is conceptualized as a UIUX AIML modular response system for mindX**

UIUX = User Interface User Experience | AIML = Artificial Intelligence Machine Learning

A three.js-based holographic face rendering system that creates expressive, wireframe-style humanoid faces as visual feedback for AI agents. Faicey serves as the "mirror of collective human consciousness" through universal facial expressions, providing real-time emotional and cognitive state visualization for generative AI models.

see also https://github.com/faicey https://github.com/mlodular https://github.com/Professor-Codephreak and https://github.com/javascriptit

## Features

- **3D Holographic Wireframe**: Interactive browser-based 3D face rendering
- **Wireframe Rendering**: Stylized wireframe faces using three.js materials
- **Facial Expressions**: Dynamic eye and mouth movements using morph targets and blendshapes
- **28 Morph Targets**: Advanced facial control including ears, nose, and expressions
- **14 Expression Presets**: neutral, smile, laugh, thinking, coding, concentrated, excited, etc.
- **5 Personas**: Professor Codephreak, mindX Base, Friendly Assistant, Mysterious Oracle, Jaimla (Female)
- **Modular Architecture**: Easy to create custom personas
- **Pure JavaScript**: No external dependencies beyond three.js
- **Real-time Animation**: Smooth expression transitions and animations
- **ASCII Terminal Mode**: Text-based visualization for Node.js

## Architecture

```
faicey/
├── core/                    # Core rendering engine
│   ├── FaceRenderer.js     # Main three.js renderer
│   ├── FaceGeometry.js     # Face mesh and geometry
│   ├── ExpressionController.js  # Expression/morph management
│   └── WireframeController.js   # Wireframe styling
├── examples/               # Example personas
│   ├── professor-codephreak.js  # Professor Codephreak persona
│   └── basic-face.js       # Basic face example
├── assets/                 # Models and textures
│   ├── models/            # 3D model files
│   └── textures/          # Texture files
├── lib/                   # Utility libraries
│   └── MorphTargets.js   # Morph target utilities
└── config/               # Configuration files
    └── personas.json     # Persona definitions

```

## Installation

```bash
cd faicey
npm install
```

## Usage

### Basic Example

```javascript
import FaceRenderer from './core/FaceRenderer.js';

const renderer = new FaceRenderer({
  wireframe: true,
  expressions: true
});

renderer.init();
renderer.setExpression('smile');
renderer.animate();
```

### View 3D Holographic Face (Browser)

```bash
# Start web server
npm run serve

# Then open in browser:
# http://localhost:8080/
```

**Interactive 3D features:**
- Mouse controls (rotate, zoom, pan)
- Real-time expression switching
- Individual morph target sliders
- 4 switchable personas with different colors
- Auto-rotation and glow effects

See [HOLOGRAPHIC.md](./HOLOGRAPHIC.md) for complete guide.

### Run Examples (Terminal)

```bash
# Run tests
npm test

# Show all personas
npm run personas

# Animated demo (cycles through expressions)
npm run demo

# Professor Codephreak example (full demo)
npm run example:professor

# Basic face example
npm run example:basic
```

## Expression System

Faicey supports multiple expression types:

- **Eyes**: blink, wink, wide, squint, look_left, look_right, look_up, look_down
- **Mouth**: smile, frown, open, closed, speak, laugh
- **Combined**: happy, sad, surprised, thinking, coding, confused

## References

This system is inspired by and references:

- [Three.js Official Examples](https://threejs.org/examples/)
- [Wireframe Rendering Examples](https://threejs.org/examples/webgl_materials_wireframe.html)
- [Jeeliz Face Tracking](https://github.com/jeeliz/jeelizWeboji)
- [Three.js Morph Targets](https://threejs.org/examples/webgl_animation_skinning_morph.html)
- [Professor Codephreak GitHub](https://github.com/Professor-Codephreak)
- [Faicey Organization](https://github.com/faicey)
- [Mlodular Three.js](https://github.com/mlodular/three.js)

## Technical Details

- **Renderer**: WebGL via three.js
- **Geometry**: Custom BufferGeometry for face mesh
- **Materials**: MeshBasicMaterial with wireframe support
- **Animation**: RequestAnimationFrame loop with morph target interpolation
- **Blendshapes**: 52 facial expression blendshapes for detailed control

## UIUX AIML Objectives

Faicey is designed around 6 core objectives:

1. **User-Friendliness** ✅ - Intuitive interface with 0-minute learning curve
2. **Customization** ✅ - 28 morph targets, 4 personas, hierarchical concepts
3. **Real-Time Feedback** ✅ - <16ms response time, 60 FPS rendering
4. **AI Integration** ✅ - Model-agnostic event system, works with any LLM
5. **Modular Design** ✅ - Fully modular components, easy to extend
6. **Multi-Modal** ⏳ - Text complete, speech/vision/gesture planned

**Status:** 77% complete toward full UIUX AIML vision

See [UIUX_OBJECTIVES.md](./UIUX_OBJECTIVES.md) for detailed implementation status.

## Related Projects & References

- [lablab.ai](https://lablab.ai/tech) - AI hackathons and tutorials
- [Google Vertex AI Model Garden](https://console.cloud.google.com/vertex-ai/model-garden)
- [mlodular](https://github.com/mlodular) - Modular AI tools
- [DeltaVML](https://github.com/DeltaVML) - ML visualization
- [AUTOMINDx](https://github.com/AUTOMINDx) - Multi-modal AI systems

## License

MIT
