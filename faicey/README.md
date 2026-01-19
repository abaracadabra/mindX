# Faicey - Three.js Face Rendering for mindX

Faicey is a three.js-based face rendering system that creates expressive, wireframe-style humanoid faces for mindX personas. It uses pure JavaScript and Node.js to generate high-quality facial expressions through eyes and mouth animations.

## Features

- **Wireframe Rendering**: Stylized wireframe faces using three.js materials
- **Facial Expressions**: Dynamic eye and mouth movements using morph targets and blendshapes
- **Modular Architecture**: Easy to create custom personas
- **Pure JavaScript**: No external dependencies beyond three.js
- **Real-time Animation**: Smooth expression transitions and animations

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

### Run Examples

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

## License

MIT
