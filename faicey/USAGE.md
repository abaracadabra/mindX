# Faicey Usage Guide

Practical guide for using the faicey face rendering system in mindX.

## Quick Start

### 1. Installation

```bash
cd mindX/faicey
npm install
```

### 2. Run Examples

```bash
# Run Professor Codephreak example
npm run example:professor

# Run basic face example
npm run example:basic
```

### 3. Basic Integration

```javascript
import { createFaiceyAgent } from './faicey/faicey_agent.js';

// Create and start agent
const faicey = await createFaiceyAgent('professor-codephreak');
faicey.start();

// Change expressions
faicey.setExpression('smile');
faicey.speak('Hello, I am Professor Codephreak');
```

---

## Common Use Cases

### Use Case 1: Static Face Display

Display a static face with a specific expression.

```javascript
import FaceRenderer from './core/FaceRenderer.js';

const renderer = new FaceRenderer({
  wireframe: true,
  faceColor: 0x00ff00,
  expressions: true
});

renderer.init();
renderer.setExpression('smile');
renderer.animate();
```

### Use Case 2: Interactive Face

Create an interactive face that responds to events.

```javascript
import { createFaiceyAgent } from './faicey_agent.js';

const agent = await createFaiceyAgent('mindx-base');
agent.start();

// React to user input
function onUserMessage(message) {
  agent.processEvent({ type: 'listening' });

  // Process message...
  agent.processEvent({ type: 'thinking' });

  // Respond
  agent.processEvent({
    type: 'speaking',
    data: { text: 'Here is my response' }
  });
}
```

### Use Case 3: Emotional AI Assistant

Create an AI assistant with emotional responses.

```javascript
const agent = await createFaiceyAgent('friendly-assistant');
agent.start();

// Happy when helping
function onSuccessfulHelp() {
  agent.processEvent({
    type: 'emotion',
    data: { emotion: 'joy', intensity: 1.0 }
  });
}

// Confused when uncertain
function onUncertainty() {
  agent.processEvent({
    type: 'emotion',
    data: { emotion: 'confusion', intensity: 0.7 }
  });
}
```

### Use Case 4: Coding Assistant (Professor Codephreak)

Specialized face for coding assistance.

```javascript
const professor = await createFaiceyAgent('professor-codephreak');
professor.start();

// Coding mode
professor.setExpression('coding');

// Thinking about a problem
setTimeout(() => {
  professor.setExpression('thinking');
}, 3000);

// Found solution!
setTimeout(() => {
  professor.setExpression('eureka');
  professor.speak('I found the solution!');
}, 6000);
```

### Use Case 5: Custom Persona

Create your own custom persona.

```javascript
// 1. Add to config/personas.json
{
  "personas": {
    "my-custom-persona": {
      "name": "My Custom Persona",
      "defaultExpression": "smile",
      "wireframe": {
        "enabled": true,
        "color": "0xff0066",
        "style": "neon",
        "thickness": 1.5
      },
      "expressions": {
        "idle": {
          "base": "smile",
          "blink": true
        }
      }
    }
  }
}

// 2. Use it
const agent = await createFaiceyAgent('my-custom-persona');
agent.start();
```

---

## Expression Sequences

### Conversation Flow

```javascript
async function conversationFlow(agent) {
  // Listening
  agent.setExpression('neutral');
  await sleep(2000);

  // Understanding
  agent.setExpression('thinking');
  await sleep(1500);

  // Responding
  agent.setExpression('smile');
  agent.speak('That is a great question!');
  await sleep(3000);

  // Back to neutral
  agent.setExpression('neutral');
}
```

### Problem Solving Flow

```javascript
async function problemSolvingFlow(agent) {
  // Analyzing problem
  agent.setExpression('thinking');
  await sleep(2000);

  // Stuck
  agent.setExpression('confused');
  await sleep(1500);

  // Breakthrough!
  agent.setExpression('surprised');
  await sleep(500);

  // Solution found
  agent.setExpression('happy');
  agent.speak('I got it!');
}
```

---

## Advanced Features

### Custom Morph Animations

```javascript
const renderer = new FaceRenderer({ expressions: true });
renderer.init();

// Animate specific morph targets
renderer.animateMorph('eyebrows_raised', 1.0, 200);
await sleep(200);
renderer.animateMorph('mouth_open', 0.5, 300);
await sleep(300);
renderer.animateMorph('smile', 0.8, 400);
```

### Blended Expressions

```javascript
// Blend multiple expressions together
const controller = renderer.expressionController;

controller.blendExpressions({
  'smile': 0.6,
  'thinking': 0.4
}, 500);

// Result: A thoughtful smile
```

### Periodic Animations

```javascript
// Add subtle breathing effect
controller.createPeriodicAnimation('mouth_open', 0.2, 0.05);

// Add eye movement
controller.createPeriodicAnimation('wink_left', 0.1, 0.3);
```

### Natural Blinking

```javascript
// Enable random natural blinks
controller.startRandomBlinks();

// Or trigger manually
await controller.blink();
```

---

## Wireframe Styling

### Basic Colors

```javascript
const renderer = new FaceRenderer({
  faceColor: 0x00ff00  // Green
});

// Change at runtime
renderer.wireframeController?.setColor(0xff0000); // Red
```

### Glow Effects

```javascript
// Matrix green glow
wireframeController.applyCyberStyle();

// Neon magenta glow
wireframeController.applyNeonStyle(0xff00ff);

// Custom glow animation
wireframeController.animateGlow(
  0x0000ff,  // Base: blue
  0x00ffff,  // Glow: cyan
  2.0        // Frequency
);
```

### Opacity Control

```javascript
wireframeController.setOpacity(0.7); // 70% opacity
```

---

## Integration Patterns

### With mindX Agents

```javascript
class MindXAgent {
  constructor() {
    this.faicey = null;
  }

  async initialize() {
    this.faicey = await createFaiceyAgent('professor-codephreak');
    this.faicey.start();

    // Listen to agent events
    this.faicey.on('thinking', () => {
      this.logActivity('Deep in thought...');
    });
  }

  async processMessage(message) {
    this.faicey.processEvent({ type: 'listening' });

    const response = await this.generateResponse(message);

    this.faicey.processEvent({
      type: 'speaking',
      data: { text: response }
    });

    return response;
  }

  async think() {
    this.faicey.processEvent({ type: 'thinking' });
    // ... thinking logic
  }

  onError(error) {
    this.faicey.processEvent({ type: 'error' });
    console.error(error);
  }

  onSuccess() {
    this.faicey.processEvent({ type: 'success' });
  }
}
```

### With WebSocket Server

```javascript
import { createFaiceyAgent } from './faicey/faicey_agent.js';
import WebSocket from 'ws';

const wss = new WebSocket.Server({ port: 8080 });
const agent = await createFaiceyAgent('mindx-base');
agent.start();

wss.on('connection', (ws) => {
  ws.on('message', (message) => {
    const data = JSON.parse(message);

    // Update face based on message
    agent.processEvent(data);

    // Send face state to client
    ws.send(JSON.stringify(agent.getState()));
  });
});
```

### With Express API

```javascript
import express from 'express';
import { createFaiceyAgent } from './faicey/faicey_agent.js';

const app = express();
const agent = await createFaiceyAgent('professor-codephreak');
agent.start();

app.post('/expression', (req, res) => {
  const { expression, intensity } = req.body;
  agent.setExpression(expression, intensity);
  res.json(agent.getState());
});

app.post('/speak', (req, res) => {
  const { text } = req.body;
  agent.speak(text);
  res.json({ status: 'speaking', text });
});

app.get('/state', (req, res) => {
  res.json(agent.getState());
});

app.listen(3000);
```

---

## Debugging

### Export State

```javascript
// Get current state
const state = renderer.exportState();
console.log('Face Position:', state.facePosition);
console.log('Face Rotation:', state.faceRotation);
console.log('Active Expressions:', state.expressions);
console.log('Morph Targets:', state.morphTargets);
```

### Monitor Expression Changes

```javascript
agent.on('expression', (data) => {
  console.log(`Expression changed to: ${data.expression}`);
});

agent.on('emotion', (data) => {
  console.log(`Emotion: ${data.emotion} (${data.intensity})`);
});
```

### Performance Monitoring

```javascript
let frameCount = 0;
let lastTime = Date.now();

function monitorPerformance() {
  frameCount++;

  const now = Date.now();
  if (now - lastTime >= 1000) {
    console.log(`FPS: ${frameCount}`);
    frameCount = 0;
    lastTime = now;
  }

  requestAnimationFrame(monitorPerformance);
}

monitorPerformance();
```

---

## Tips & Best Practices

### 1. Expression Timing

Use appropriate durations for natural-looking animations:
- Quick reactions: 100-200ms
- Normal transitions: 300-500ms
- Dramatic changes: 500-800ms

### 2. Combine Expressions

Don't rely on single expressions; blend them for realism:

```javascript
// Instead of just 'thinking'
controller.blendExpressions({
  'thinking': 0.7,
  'neutral': 0.3
});
```

### 3. Use Event Handlers

Register handlers for better modularity:

```javascript
agent.on('thinking', () => {
  // Update UI
  // Log activity
  // Trigger other systems
});
```

### 4. Cleanup

Always cleanup when done:

```javascript
// On application exit
agent.stop();
renderer.dispose();
```

### 5. Natural Behavior

Enable random blinking and subtle animations for realism:

```javascript
controller.startRandomBlinks();
controller.createPeriodicAnimation('mouth_open', 0.3, 0.02);
```

---

## Troubleshooting

### Face Not Rendering

```javascript
// Check initialization
if (!renderer.isAnimating) {
  renderer.animate();
}

// Verify geometry
const state = renderer.exportState();
console.log('Geometry:', state);
```

### Expressions Not Working

```javascript
// Verify expression controller
if (!renderer.expressionController) {
  console.error('Expression controller not initialized');
}

// Check available morphs
const morphs = renderer.faceGeometry.getMorphTargets();
console.log('Available morphs:', morphs);
```

### Performance Issues

```javascript
// Reduce animation frequency
// Use simpler geometry
// Disable expensive effects

wireframeController.disableGlow();
controller.stopPeriodicAnimations();
```

---

## Helper Functions

```javascript
// Utility sleep
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Random choice
const randomChoice = (arr) => arr[Math.floor(Math.random() * arr.length)];

// Random expression
function randomExpression(agent) {
  const expressions = ['smile', 'thinking', 'happy', 'neutral'];
  agent.setExpression(randomChoice(expressions));
}
```

---

## Next Steps

1. Create your own custom persona
2. Integrate with your mindX agent workflows
3. Add speech synthesis for full audiovisual experience
4. Export rendered frames for video generation
5. Connect to emotion detection systems

For API reference, see [API.md](./API.md)
