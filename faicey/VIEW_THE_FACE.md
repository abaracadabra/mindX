# 🎭 View the 3D Holographic Wireframe Face

## ⚡ Quick Start - View Right Now!

The web server is **already running!**

### 🌐 Open in Your Browser:

**http://localhost:8080/**

---

## 🎮 What You'll See

A fully interactive 3D wireframe face with:

### ✨ Features
- **Real-time 3D rendering** using three.js
- **Holographic wireframe** aesthetic
- **Smooth animations** with morph targets
- **Interactive controls** for expressions

### 🖱️ Mouse Controls
- **Left Click + Drag** → Rotate the face
- **Scroll Wheel** → Zoom in/out
- **Right Click + Drag** → Pan the view

### 🎨 Expression Controls (Right Panel)

**Preset Expressions:**
- Neutral, Smile, Laugh, Frown, Sad
- Surprised, Thinking, Confused
- Wink, Blink, Coding, Happy

**Individual Morph Sliders:**
- Smile (0-100%)
- Frown (0-100%)
- Mouth Open (0-100%)
- Blink (0-100%)
- Eyebrows Raised (0-100%)
- Eyebrows Furrowed (0-100%)

**Random Button:**
- Generate random expressions instantly!

### 🎭 Personas (Left Panel - Persona Selector)

Switch between 4 unique personas with different colors:

1. **Professor Codephreak** 🟢
   - Color: Matrix Green (#00ff00)
   - Style: Cyber/Matrix with glow
   - Default: Coding expression

2. **mindX Base** 🔵
   - Color: Neon Cyan (#00aaff)
   - Style: Neon glow
   - Default: Neutral expression

3. **Friendly Assistant** 🟠
   - Color: Warm Orange (#ffaa00)
   - Style: Warm tone
   - Default: Smile

4. **Mysterious Oracle** 🟣
   - Color: Mystical Purple (#9900ff)
   - Style: Mystical glow
   - Default: Thinking expression

---

## 📊 Technical Details

### Rendering
- **Engine:** three.js WebGL
- **Geometry:** 38 vertices, ~80 line segments
- **Morph Targets:** 8 blend shapes
- **Performance:** 60 FPS on modern hardware

### Based on Official three.js Examples
- [three.js webgl - morph targets - face](https://threejs.org/examples/webgl_morphtargets_face.html)
- [three.js webgl - skinning + morphing](https://threejs.org/examples/webgl_animation_skinning_morph.html)

---

## 🔧 Server Management

### Check if Server is Running
```bash
curl http://localhost:8080/
# Should return 200 OK
```

### Start Server Manually
```bash
npm run serve
```

### Stop Server
```bash
# Find the process
ps aux | grep "node serve.js"

# Kill it
pkill -f "node serve.js"
```

### Alternative: Use Different Port
Edit `serve.js` and change:
```javascript
const PORT = 8080;  // Change to 8081, 3000, etc.
```

---

## 📱 Screenshots & Recording

### Take Screenshots
1. Open browser DevTools (F12)
2. Click "Capture screenshot" or use Ctrl+Shift+P → "Capture screenshot"

### Record Video
1. Use browser screen recording
2. Use OBS Studio
3. Use OS built-in screen recorder

---

## 🎯 Try These Interactions

### 1. Expression Morphing
1. Select "Smile" from preset dropdown
2. Slowly adjust the "Frown" slider
3. Watch the face blend between expressions!

### 2. Create Custom Expressions
1. Reset all sliders to 0
2. Set "Eyebrows Furrowed" to 60%
3. Set "Wink Left" to 50%
4. Set "Smile" to 30%
5. You've created a "skeptical" expression!

### 3. Persona Tour
1. Switch to each persona and observe color changes
2. Notice how glow effects differ
3. Each persona has its own personality!

### 4. Random Mode
1. Click "Random Expression" button repeatedly
2. Watch the face change dynamically
3. Find interesting combinations!

---

## 🐛 Troubleshooting

### Face Not Loading?
- Check browser console (F12) for errors
- Ensure JavaScript is enabled
- Try refreshing (Ctrl+R or Cmd+R)
- Clear browser cache

### Server Not Responding?
```bash
# Check if running
ps aux | grep serve.js

# Restart server
pkill -f serve.js && npm run serve
```

### Performance Issues?
- Close unnecessary browser tabs
- Reduce browser window size
- Disable glow effects (select different persona)
- Update graphics drivers

---

## 📚 Full Documentation

- **[README.md](./README.md)** - Project overview
- **[HOLOGRAPHIC.md](./HOLOGRAPHIC.md)** - Complete 3D face guide
- **[API.md](./API.md)** - Full API reference
- **[USAGE.md](./USAGE.md)** - Usage examples
- **[FEATURES.md](./FEATURES.md)** - Feature list

---

## 🚀 Next Steps

### 1. Integrate with mindX Agent
```javascript
import { createFaiceyAgent } from './faicey_agent.js';

const agent = await createFaiceyAgent('professor-codephreak');
agent.processEvent({ type: 'thinking' });
```

### 2. Add to mindX Frontend
Copy `examples/holographic-face.html` into your mindX frontend UI.

### 3. Connect to Agent Events
Make the face respond to agent state changes:
```javascript
agent.on('thinking', () => face.setExpression('thinking'));
agent.on('speaking', () => face.setExpression('smile'));
```

### 4. Customize Personas
Edit `config/personas.json` to add your own personas with custom colors and behaviors.

---

## ⚡ Summary

**Server Status:** ✅ Running on http://localhost:8080/

**Quick Commands:**
```bash
npm run serve    # Start server
npm run demo     # ASCII demo
npm run personas # View all personas
npm test         # Run tests
```

**Browser URL:** http://localhost:8080/

---

**Enjoy the holographic face! 🎭**

*Created for mindX Autonomous Agent System*
*Version 0.1.0 - Based on official three.js examples*
