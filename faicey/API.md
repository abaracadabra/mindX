# Faicey API Documentation

Complete API reference for the mindX faicey face rendering system.

## Core Classes

### FaceRenderer

Main rendering engine for three.js-based faces.

#### Constructor

```javascript
new FaceRenderer(options)
```

**Options:**
- `wireframe` (boolean): Enable wireframe mode (default: true)
- `expressions` (boolean): Enable expression system (default: true)
- `backgroundColor` (hex): Background color (default: 0x000000)
- `faceColor` (hex): Face/wireframe color (default: 0x00ff00)
- `width` (number): Render width (default: 800)
- `height` (number): Render height (default: 600)
- `cameraZ` (number): Camera Z position (default: 5)
- `enableLighting` (boolean): Enable scene lighting (default: false)
- `wireframeThickness` (number): Wireframe line thickness (default: 1)

#### Methods

##### init()
Initialize the renderer, scene, and face geometry.

```javascript
renderer.init();
```

**Returns:** `this` (for chaining)

##### setExpression(expression, intensity)
Set facial expression.

```javascript
renderer.setExpression('smile', 1.0);
```

**Parameters:**
- `expression` (string): Expression name (see Expressions section)
- `intensity` (number): Expression intensity 0-1 (default: 1.0)

##### animateMorph(morphName, value, duration)
Animate a specific morph target.

```javascript
renderer.animateMorph('mouth_open', 0.8, 300);
```

**Parameters:**
- `morphName` (string): Morph target name
- `value` (number): Target value 0-1
- `duration` (number): Animation duration in ms (default: 300)

##### setRotation(x, y, z)
Set face rotation.

```javascript
renderer.setRotation(0.1, 0.5, 0);
```

**Parameters:**
- `x` (number): X-axis rotation (pitch)
- `y` (number): Y-axis rotation (yaw)
- `z` (number): Z-axis rotation (roll)

##### animate()
Start the animation loop.

```javascript
renderer.animate();
```

##### stopAnimation()
Stop the animation loop.

```javascript
renderer.stopAnimation();
```

##### exportState()
Export current renderer state for debugging.

```javascript
const state = renderer.exportState();
console.log(state);
```

**Returns:** Object with position, rotation, expressions, and morph targets

##### dispose()
Cleanup and dispose all resources.

```javascript
renderer.dispose();
```

---

### FaceGeometry

Creates 3D geometry for humanoid faces.

#### Methods

##### createFaceGeometry()
Create face geometry with morph targets.

```javascript
const geometry = faceGeometry.createFaceGeometry();
```

**Returns:** THREE.BufferGeometry

##### getMorphTargets()
Get list of available morph target names.

```javascript
const morphs = faceGeometry.getMorphTargets();
// ['smile', 'frown', 'mouth_open', 'blink', ...]
```

---

### ExpressionController

Manages facial expressions and animations.

#### Constructor

```javascript
new ExpressionController(faceMesh)
```

#### Methods

##### setExpression(expressionName, intensity, duration)
Set expression from preset.

```javascript
controller.setExpression('happy', 0.8, 300);
```

##### animateMorph(morphName, targetValue, duration)
Animate single morph target.

```javascript
controller.animateMorph('smile', 1.0, 300);
```

##### setMorphDirect(morphName, value)
Set morph immediately without animation.

```javascript
controller.setMorphDirect('blink', 1.0);
```

##### blendExpressions(expressionWeights, duration)
Blend multiple expressions together.

```javascript
controller.blendExpressions({
  'smile': 0.7,
  'thinking': 0.3
}, 300);
```

##### createPeriodicAnimation(morphName, frequency, amplitude)
Create repeating animation (e.g., breathing).

```javascript
controller.createPeriodicAnimation('mouth_open', 0.5, 0.1);
```

##### blink()
Trigger single blink animation.

```javascript
await controller.blink();
```

##### startRandomBlinks()
Start natural random blinking behavior.

```javascript
controller.startRandomBlinks();
```

##### speak(text)
Animate mouth for speaking.

```javascript
controller.speak('Hello world');
```

##### getCurrentState()
Get current expression state.

```javascript
const state = controller.getCurrentState();
```

---

### WireframeController

Controls wireframe styling and effects.

#### Constructor

```javascript
new WireframeController(faceMesh, thickness)
```

#### Methods

##### setColor(color)
Set wireframe color.

```javascript
controller.setColor(0x00ff00);
```

##### setOpacity(opacity)
Set wireframe opacity.

```javascript
controller.setOpacity(0.8);
```

##### animateGlow(baseColor, glowColor, frequency)
Animate pulsing glow effect.

```javascript
controller.animateGlow(0x00ff00, 0x00ff88, 2.0);
```

##### applyCyberStyle()
Apply matrix/cyber aesthetic.

```javascript
controller.applyCyberStyle();
```

##### applyNeonStyle(color)
Apply neon glow style.

```javascript
controller.applyNeonStyle(0xff00ff);
```

---

### FaiceyAgent

Integration layer for mindX system.

#### Constructor

```javascript
new FaiceyAgent(personaName)
```

#### Methods

##### async init()
Initialize agent with persona.

```javascript
const agent = new FaiceyAgent('professor-codephreak');
await agent.init();
```

##### processEvent(event)
Process mindX event and update face.

```javascript
agent.processEvent({
  type: 'thinking',
  data: {}
});
```

**Event Types:**
- `thinking`: Switch to thinking expression
- `speaking`: Animate speech with text
- `listening`: Switch to neutral/listening
- `processing`: Show processing/coding expression
- `success`: Show happy/success expression
- `error`: Show confused/error expression
- `expression`: Set specific expression
- `emotion`: Handle emotional state

##### setExpression(expression, intensity)
Set facial expression.

```javascript
agent.setExpression('smile', 0.8);
```

##### speak(text)
Make persona speak.

```javascript
agent.speak('Hello, I am mindX');
```

##### start()
Start animation loop.

```javascript
agent.start();
```

##### on(event, handler)
Register event handler.

```javascript
agent.on('thinking', (data) => {
  console.log('Persona is thinking...');
});
```

##### getState()
Get agent state.

```javascript
const state = agent.getState();
```

##### stop()
Stop and cleanup agent.

```javascript
agent.stop();
```

---

## Expressions

Available expression presets:

### Basic Expressions
- `neutral`: Default neutral face
- `smile`: Simple smile
- `frown`: Frown
- `happy`: Happy expression (smile + raised eyebrows)
- `sad`: Sad expression (frown + furrowed brows)

### Complex Expressions
- `laugh`: Laughing (smile + open mouth)
- `surprised`: Surprised (raised eyebrows + open mouth)
- `thinking`: Thinking (furrowed brows)
- `confused`: Confused (furrowed brows + slight frown)

### Special Expressions
- `wink`: Wink with smile
- `blink`: Blink both eyes
- `coding`: Focused coding expression
- `speaking`: Speaking (slight mouth open)

---

## Morph Targets

Base morph targets for expressions:

- `smile`: Smile with mouth corners up
- `frown`: Frown with mouth corners down
- `mouth_open`: Open mouth
- `blink`: Close both eyes
- `wink_left`: Close left eye
- `wink_right`: Close right eye
- `eyebrows_raised`: Raise eyebrows
- `eyebrows_furrowed`: Furrow eyebrows

---

## Usage Examples

### Basic Usage

```javascript
import FaceRenderer from './core/FaceRenderer.js';

const renderer = new FaceRenderer({
  wireframe: true,
  faceColor: 0x00ff00
});

renderer.init();
renderer.setExpression('smile');
renderer.animate();
```

### Using FaiceyAgent

```javascript
import { createFaiceyAgent } from './faicey_agent.js';

const agent = await createFaiceyAgent('professor-codephreak');

agent.on('thinking', () => {
  console.log('Deep in thought...');
});

agent.start();

// Process events
agent.processEvent({
  type: 'speaking',
  data: { text: 'Hello world' }
});
```

### Custom Expression Blending

```javascript
controller.blendExpressions({
  'smile': 0.5,
  'thinking': 0.3,
  'surprised': 0.2
}, 500);
```

---

## Personas

Available personas (see `config/personas.json`):

- `professor-codephreak`: AI coding expert
- `mindx-base`: Default mindX persona
- `friendly-assistant`: Warm assistant
- `mysterious-oracle`: Enigmatic AI

---

## Events

FaiceyAgent event types:

```javascript
{
  type: 'thinking' | 'speaking' | 'listening' | 'processing' |
        'success' | 'error' | 'expression' | 'emotion',
  data: {
    text?: string,
    expression?: string,
    emotion?: string,
    intensity?: number
  }
}
```

---

## Integration with mindX

```javascript
// In mindX agent code
import { createFaiceyAgent } from './faicey/faicey_agent.js';

class MindXAgent {
  async initialize() {
    this.faicey = await createFaiceyAgent(this.persona);
    this.faicey.start();
  }

  async think(message) {
    this.faicey.processEvent({ type: 'thinking' });
    // ... thinking logic
  }

  async respond(response) {
    this.faicey.processEvent({
      type: 'speaking',
      data: { text: response }
    });
    // ... response logic
  }
}
```
