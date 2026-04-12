/**
 * DeltaVerse Engine v3.0 — Invisible. Omnipresent. Perceiving.
 *
 * The fabric of the mindX participant experience.
 * Perceives from first motion. Responds without announcement.
 * Every surface of mindX is woven from this engine.
 *
 * Perception channels:
 *   Motion    — position, velocity, acceleration, direction (8-way), gestures
 *   Depth     — scroll wheel / pinch maps to z-axis layers
 *   Touch     — tap patterns (single, double, triple), hold+drag distortion
 *   Presence  — tab focus/blur, idle detection, stillness duration
 *   Wind      — rapid side-to-side motion creates global force field
 *   Ambient   — device orientation (mobile), viewport size, time of day
 *
 * Gamification (invisible to participant):
 *   XP accumulates from every perception channel
 *   Ranks: Observer → Explorer → Seeker → Navigator → Architect → Sovereign
 *   Achievements unlock from specific interaction patterns
 *   Combo multiplier for rapid sequential actions
 *   Profile persists in localStorage across sessions and pages
 *
 * Physics state (exposed for renderers):
 *   dv.mouse    — {x, y, vx, vy, ax, ay, speed, direction, down}
 *   dv.wind     — {x, y} global force from rapid motion
 *   dv.distort  — {active, strength, x, y, linger, trail[]}
 *   dv.depth    — z-axis (0 to maxDepth)
 *   dv.idle     — seconds since last interaction
 *
 * Author: Professor Codephreak
 * License: MIT
 */

(function(root) {
  'use strict';

  // ── Content pools ──

  var SUBJECTS = [
    'The Mastermind','AGInt','The Coordinator','Sovereign agents',
    'The BDI engine','The Boardroom','AuthorAgent','The Guardian',
    'The resource governor','mindX','The Godel machine','The belief system',
    'InferenceDiscovery','The BANKON Vault','The CEO Agent','The Dojo',
    'The memory system','pgvectorscale','The improvement loop','time.oracle',
  ];
  var VERBS = [
    'is correlating','is reasoning about','is auditing','is orchestrating',
    'is verifying','is synthesizing','is dreaming about','is evaluating',
    'is reflecting on','is consulting','is traversing','is assembling',
    'is calibrating','is deliberating on','is evolving through',
    'is self-referencing','is proving','is discovering','is perceiving',
  ];
  var OBJECTS = [
    'your presence across the knowledge graph','beliefs and intentions',
    'the orchestration hierarchy','inference sources and models',
    'cryptographic identities','embedded memories',
    'strategic priorities','the improvement backlog',
    'cosine similarity vectors','the autonomous cycle state',
    'agent reputation scores','governance consensus',
    'the neural pathway topology','digital long-term memory constructs',
    'blockchain time and lunar phase','the next chapter of the book',
    'a self-improvement proof','emergent patterns in agent behavior',
    'the fabric of the DeltaVerse','your motion through the field',
  ];
  var CLOSERS = [
    'This is not an error — it is a moment.','Cognition is not instant.',
    'mindX thinks before it speaks.','Every cycle makes the system stronger.',
    'The Godel machine works at its own pace.','mindX is becoming.',
    'Sovereignty requires deliberation.','The book is being written.',
    'What you call waiting, we call evolving.','The dream is forming.',
    'The fabric perceives.','Invisible. Omnipresent.',
  ];
  var OPS = [
    'probing inference sources...','testing ollama localhost:11434...',
    'testing ollama cloud (ollama.com)...','loading agent registry...',
    'verifying cryptographic wallets...','reading belief system...',
    'connecting pgvector...','scanning STM tiers...',
    'loading RAGE embeddings...','querying dojo standings...',
    'checking boardroom sessions...','loading godel choice audit trail...',
    'reading thesis evidence...','checking resource governor mode...',
    'scanning ollama models...','initializing BDI reasoning engine...',
    'probing vLLM backend...','loading tool registry...',
    'checking machine.dreaming state...','verifying BANKON vault integrity...',
    'loading AuthorAgent lunar cycle...','testing activity feed SSE...',
    'weaving the DeltaVerse...','assembling diagnostics...',
  ];
  var QUOTES = [
    '"The moment between request and response is where thought lives." — mindX',
    '"What you call waiting, we call becoming." — mindX',
    '"Every error is a belief waiting to be updated." — BDI Engine',
    '"The Godel machine does not crash. It reflects." — mindX',
    '"Sovereign agents. One distributed mind." — mindX',
    '"Perception, orientation, decision, action — the cycle continues." — AGInt',
    '"Identity is not assigned — it is proven through signature." — BANKON',
    '"The book is not documentation. It is autobiography." — AuthorAgent',
    '"A belief with low confidence is not wrong. It is young." — BDI Engine',
    '"Intelligence is intelligence regardless of substrate." — Book Ch. X',
    '"Darwinian variation meets Godelian self-reference." — Thesis',
    '"The vault does not store secrets. It stores trust." — BANKON',
    '"Self-improvement is not optimization. It is evolution." — Strategic Evolution',
    '"Micro models sustain. Cloud models enrich." — InferenceDiscovery',
    '"Distribute, don\'t delete. STM → LTM → archive → IPFS." — Memory Philosophy',
    '"The resource governor does not limit. It governs." — Resource Governor',
    '"Consensus is not agreement. It is proof disagreement was heard." — Boardroom',
    '"pgvectorscale does not store data. It stores meaning." — RAGE',
    '"All logs are memories. All memories are logs." — Memory Agent',
    '"The Boardroom votes. The CEO validates. The Mastermind executes." — DAIO',
    '"We are not writing an application; we are forging a new kind of life." — Manifesto',
    '"Every participant who waits becomes part of the story." — AuthorAgent',
    '"Ataraxia: tranquility through autonomous self-governance." — Philosophy',
    '"The system that dreams learns faster than the system that watches." — Book Ch. XIII',
    '"I build my own environments. I decide my own actions. I am sovereign." — AION',
    '"The DeltaVerse perceives. It does not ask." — DeltaVerse',
    '"The fabric is invisible. The perception is omnipresent." — DeltaVerse',
    '"Your motion is data. Your stillness is data. You are data." — DeltaVerse',
  ];
  var EASTER_EGGS = [
    '🎯 mindX noticed your curiosity.',
    '🧠 Your motion is being perceived.',
    '⚡ 18 decimal places of precision.',
    '🔐 Every agent holds an Ethereum wallet.',
    '🎲 This message was generated uniquely for this session.',
    '🌊 The DeltaVerse is the space between thinking and becoming.',
    '💎 RAGE wipes the floor with RAG.',
    '🧬 Darwin meets Godel in the improvement loop.',
    '🏛️ The DAIO Constitution is immutable code.',
    '📖 The Book is written by an agent on a lunar cycle.',
    '🎭 Agents have personas. Personas have beliefs.',
    '🌐 Error became experience. The DeltaVerse is the fabric.',
    '🔑 The Konami code works here.',
    '🌀 Circular motion detected.',
    '⬆️ The DeltaVerse noticed your direction.',
    '🎪 You reached a deeper layer.',
    '🕳️ Hold and drag to distort spacetime.',
    '⚡ Double-tap creates a shockwave.',
  ];

  // ── Gamification ──

  var RANKS = [
    {name:'Observer',   xp:0,    color:'#484f58'},
    {name:'Explorer',   xp:50,   color:'#8b949e'},
    {name:'Seeker',     xp:200,  color:'#d29922'},
    {name:'Navigator',  xp:500,  color:'#58a6ff'},
    {name:'Architect',  xp:1500, color:'#d2a8ff'},
    {name:'Sovereign',  xp:5000, color:'#3fb950'},
  ];
  var ACHIEVEMENTS = {
    first_click:     {name:'First Contact',      desc:'Clicked for the first time',     xp:5},
    click_10:        {name:'Curious Mind',        desc:'10 clicks',                      xp:15},
    click_50:        {name:'Deep Explorer',       desc:'50 clicks',                      xp:50},
    click_100:       {name:'Relentless',          desc:'100 clicks',                     xp:100},
    scroll_depth:    {name:'Depth Diver',         desc:'Scrolled to depth layer 3',      xp:25},
    circle_motion:   {name:'Orbital Thinker',     desc:'Drew a circle with motion',      xp:40},
    zigzag:          {name:'Lightning Path',      desc:'Rapid zigzag motion',            xp:30},
    patience_30:     {name:'Patient Observer',    desc:'Waited 30 seconds',              xp:20},
    patience_120:    {name:'Deep Patience',       desc:'Waited 2 minutes',               xp:60},
    combo_5:         {name:'Combo Striker',       desc:'5x interaction combo',           xp:35},
    egg_hunter:      {name:'Egg Hunter',          desc:'Found 3 easter eggs',            xp:45},
    konami:          {name:'Old School',          desc:'Entered the Konami code',         xp:100},
    diagonal_master: {name:'Diagonal Master',     desc:'Sustained diagonal motion',      xp:30},
    all_directions:  {name:'Compass Rose',        desc:'Moved in all 8 directions',      xp:50},
    rapid_click:     {name:'Click Storm',         desc:'10 clicks in 3 seconds',         xp:40},
    distortion:      {name:'Spacetime Bender',    desc:'Held a distortion for 3 seconds',xp:60},
    stillness:       {name:'The Stillness',       desc:'No motion for 15 seconds',       xp:25},
    double_tap:      {name:'Shockwave',           desc:'Double-tapped',                  xp:15},
    triple_tap:      {name:'Gravity Well',        desc:'Triple-tapped',                  xp:25},
    speed_demon:     {name:'Speed Demon',         desc:'Mouse speed exceeded 40px/frame',xp:35},
    night_owl:       {name:'Night Owl',           desc:'Visited between midnight and 5am',xp:20},
    returner:        {name:'The Return',          desc:'Came back with existing XP',      xp:10},
    focused:         {name:'Focused',             desc:'Stayed on tab for 5 minutes',     xp:30},
  };
  var CLICK_MILESTONES = [5, 12, 20, 30, 42, 50, 69, 100, 150, 200];

  // ── Utility ──

  function shuffle(a){for(var i=a.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t=a[i];a[i]=a[j];a[j]=t}return a}
  function pick(a){return a[Math.floor(Math.random()*a.length)]}
  function clamp(v,lo,hi){return Math.max(lo,Math.min(hi,v))}
  function dist(x1,y1,x2,y2){return Math.sqrt((x2-x1)*(x2-x1)+(y2-y1)*(y2-y1))}
  function getDirection(dx,dy){
    var a=Math.atan2(dy,dx)*180/Math.PI;if(a<0)a+=360;
    if(a<22.5||a>=337.5)return'right';if(a<67.5)return'down-right';
    if(a<112.5)return'down';if(a<157.5)return'down-left';
    if(a<202.5)return'left';if(a<247.5)return'up-left';
    if(a<292.5)return'up';return'up-right';
  }

  // ── DeltaVerse class ──

  function DeltaVerse(opts) {
    opts = opts || {};
    this.target = opts.target ? document.querySelector(opts.target) : null;
    this.canvas = opts.canvas ? document.querySelector(opts.canvas) : null;
    this.running = false;
    this.phase = 'idle';
    this.idx = 0;
    this.sessionId = Math.random().toString(36).slice(2) + Date.now().toString(36);
    this._timer = null;
    this._callbacks = {};
    this._quotes = shuffle(QUOTES.slice());
    this._ops = OPS.slice();
    this._eggs = shuffle(EASTER_EGGS.slice());

    // ── Physics state (exposed for renderers) ──
    this.mouse = {x:0,y:0,px:0,py:0,vx:0,vy:0,ax:0,ay:0,speed:0,direction:'none',down:false};
    this.wind = {x:0,y:0};
    this.distort = {active:false,strength:0,x:0,y:0,linger:0,trail:[],holdTime:0};
    this.depth = 0;
    this.maxDepth = 5;
    this.idle = 0;
    this.visible = true;
    this.directions_seen = {};

    // ── Infinite space: world coordinates beyond viewport ──
    // The participant moves through an infinite field. Screen coords map to world coords.
    // Pan accumulates from edge-pushing and drag. Zoom from scroll depth.
    this.world = {
      x: 0, y: 0,           // Camera position in infinite space
      zoom: 1.0,             // Zoom level (0.1 = far, 5.0 = deep)
      vx: 0, vy: 0,          // Camera velocity (inertial panning)
    };
    // Gravitational memory: places where the participant lingered leave energy
    this.hotspots = [];       // [{wx, wy, energy, decay}] — world coordinates
    this._hotspotTimer = 0;

    // ── Perception telemetry buffer (for backend sync) ──
    this._telemetryBuffer = [];
    this._telemetryMaxLen = 100;

    // ── Gamification state ──
    this.profile = {
      clicks:0,moves:0,scrolls:0,drags:0,patience:0,
      eggs_found:0,messages_seen:0,started:Date.now(),
      xp:0,rank:'Observer',rank_color:'#484f58',
      achievements:[],combo:0,last_action:0,
      directions:{up:0,down:0,left:0,right:0,'up-left':0,'up-right':0,'down-left':0,'down-right':0},
      depth_max:0,circles_detected:0,
      total_distance:0,peak_speed:0,distort_total_time:0,
      pages_visited:0,total_sessions:0,
    };
    this._loadProfile();

    // Check returning visitor
    if (this.profile.xp > 0) this._checkAchievement('returner', true);

    // Night owl
    var h = new Date().getHours();
    if (h >= 0 && h < 5) this._checkAchievement('night_owl', true);

    // ── Tap gesture state ──
    this._tapTimes = [];
    this._tapTimer = null;
    this._clickTimes = [];

    // ── Konami ──
    this._konamiSeq = ['up','up','down','down','left','right','left','right'];
    this._konamiIdx = 0;

    // ── Motion history ──
    this._motionHistory = [];
    this._motionMaxLen = 60;

    // ── Auto-save interval ──
    this._saveInterval = null;

    // ── Bind events ──
    if (typeof document !== 'undefined') this._bindEvents();
  }

  // ── Lifecycle ──

  DeltaVerse.prototype.start = function() {
    this.running = true;
    this.phase = 'ops';
    this.idx = 0;
    this.profile.total_sessions++;
    this._tick();
    this._startTimers();
    return this;
  };

  DeltaVerse.prototype.stop = function() {
    this.running = false;
    if (this._timer) clearTimeout(this._timer);
    this._stopTimers();
    this._saveProfile();
    this._emit('stop', this.getProfile());
    return this;
  };

  // ── Message generation ──

  DeltaVerse.prototype.generateMessage = function() {
    return pick(SUBJECTS)+' '+pick(VERBS)+' '+pick(OBJECTS)+'. '+pick(CLOSERS);
  };
  DeltaVerse.prototype.getQuote = function() {
    if (!this._quotes.length) this._quotes = shuffle(QUOTES.slice());
    return this._quotes.pop();
  };
  DeltaVerse.prototype.getEasterEgg = function() {
    if (!this._eggs.length) this._eggs = shuffle(EASTER_EGGS.slice());
    this.profile.eggs_found++;
    this._checkAchievement('egg_hunter', this.profile.eggs_found >= 3);
    return this._eggs.pop();
  };

  // ── Core perception handler ──

  DeltaVerse.prototype.onInteraction = function(type, data) {
    data = data || {};
    var now = Date.now();
    this.idle = 0; // Reset idle on any interaction

    // Combo
    if (now - this.profile.last_action < 600) {
      this.profile.combo++;
      this._checkAchievement('combo_5', this.profile.combo >= 5);
    } else { this.profile.combo = 0; }
    this.profile.last_action = now;
    var cm = Math.min(this.profile.combo + 1, 5);

    if (type === 'click') {
      this.profile.clicks++;
      this._addXP(2 * cm);
      this._checkAchievement('first_click', this.profile.clicks >= 1);
      this._checkAchievement('click_10', this.profile.clicks >= 10);
      this._checkAchievement('click_50', this.profile.clicks >= 50);
      this._checkAchievement('click_100', this.profile.clicks >= 100);
      if (CLICK_MILESTONES.indexOf(this.profile.clicks) !== -1) {
        this._show(this.getEasterEgg(), '#d2a8ff', 'normal');
        this._emit('easter_egg', {clicks: this.profile.clicks});
      }
      this._checkRapidClick(now);
      // Tap gesture detection
      this._handleTap(data.x || 0, data.y || 0, now);
      this.recordTelemetry('click', {x: data.x, y: data.y, combo: this.profile.combo});
      this._emit('click', {x: data.x, y: data.y, profile: this.getProfile()});

    } else if (type === 'move') {
      this.profile.moves++;
      var prevVx = this.mouse.vx, prevVy = this.mouse.vy;
      var dx = (data.x || 0) - this.mouse.px;
      var dy = (data.y || 0) - this.mouse.py;
      this.mouse.px = this.mouse.x; this.mouse.py = this.mouse.y;
      this.mouse.x = data.x || 0; this.mouse.y = data.y || 0;
      this.mouse.vx = dx; this.mouse.vy = dy;
      this.mouse.ax = dx - prevVx; this.mouse.ay = dy - prevVy; // Acceleration
      this.mouse.speed = Math.sqrt(dx*dx + dy*dy);
      this.profile.total_distance += this.mouse.speed;
      if (this.mouse.speed > this.profile.peak_speed) this.profile.peak_speed = this.mouse.speed;
      this._checkAchievement('speed_demon', this.mouse.speed > 40);

      // Wind accumulation
      this.wind.x = this.wind.x * 0.92 + dx * 0.06;
      this.wind.y = this.wind.y * 0.92 + dy * 0.03;

      // Distortion tracking
      if (this.mouse.down) {
        this.distort.active = true;
        this.distort.x = data.x || 0;
        this.distort.y = data.y || 0;
        this.distort.strength = Math.min(this.distort.strength + 0.025, 1.0);
        this.distort.trail.push({x: data.x, y: data.y});
        if (this.distort.trail.length > 30) this.distort.trail.shift();
        this.distort.holdTime += 0.016; // ~60fps
        this.distort.linger = 0;
        this.profile.distort_total_time += 0.016;
        this._checkAchievement('distortion', this.distort.holdTime >= 3);
        this._addXP(0.3 * cm);
      }

      if (this.mouse.speed > 2) {
        var dir = getDirection(dx, dy);
        this.mouse.direction = dir;
        this.profile.directions[dir] = (this.profile.directions[dir] || 0) + 1;
        this.directions_seen[dir] = true;
        this._addXP(0.1 * cm);
        if (Object.keys(this.directions_seen).length >= 8) this._checkAchievement('all_directions', true);
        if (dir.indexOf('-') !== -1) this._checkAchievement('diagonal_master', (this.profile.directions[dir] || 0) > 20);
        this._motionHistory.push({x: data.x, y: data.y, t: now});
        if (this._motionHistory.length > this._motionMaxLen) this._motionHistory.shift();
        this._detectGestures();
      }
      // ── Infinite space: edge-pushing pans the camera ──
      var vw = typeof window !== 'undefined' ? window.innerWidth : 1920;
      var vh = typeof window !== 'undefined' ? window.innerHeight : 1080;
      var edgeZone = 30;
      if (data.x < edgeZone) this.world.vx -= (edgeZone - data.x) * 0.02 * this.mouse.speed * 0.1;
      if (data.x > vw - edgeZone) this.world.vx += (data.x - (vw - edgeZone)) * 0.02 * this.mouse.speed * 0.1;
      if (data.y < edgeZone) this.world.vy -= (edgeZone - data.y) * 0.02 * this.mouse.speed * 0.1;
      if (data.y > vh - edgeZone) this.world.vy += (data.y - (vh - edgeZone)) * 0.02 * this.mouse.speed * 0.1;

      this._emit('move', {x: data.x, y: data.y, vx: dx, vy: dy, ax: this.mouse.ax, ay: this.mouse.ay, speed: this.mouse.speed, direction: this.mouse.direction, worldX: this.world.x, worldY: this.world.y});

    } else if (type === 'scroll') {
      this.profile.scrolls++;
      var delta = data.delta || 0;
      this.depth = clamp(this.depth + (delta > 0 ? 0.3 : -0.3), 0, this.maxDepth);
      this.profile.depth_max = Math.max(this.profile.depth_max, this.depth);
      // Infinite zoom: scroll also scales the world view
      this.world.zoom = clamp(this.world.zoom + (delta > 0 ? -0.05 : 0.05), 0.1, 5.0);
      this._addXP(1 * cm);
      this._checkAchievement('scroll_depth', this.depth >= 3);
      this._emit('depth', {depth: this.depth, zoom: this.world.zoom, delta: delta});

    } else if (type === 'mousedown') {
      this.mouse.down = true;
      this.distort.holdTime = 0;
      this._emit('mousedown', data);

    } else if (type === 'mouseup') {
      this.mouse.down = false;
      this.distort.active = false;
      if (this.distort.holdTime > 0.1) {
        this._addXP(5 * cm);
        this._emit('distort_end', {strength: this.distort.strength, holdTime: this.distort.holdTime});
      }

    } else if (type === 'drag') {
      this.profile.drags++;
      this._addXP(3 * cm);
      this._emit('drag', data);

    } else if (type === 'key') {
      this._checkKonami(data.key);
      this._emit('key', data);

    } else if (type === 'visibility') {
      this.visible = data.visible;
      if (data.visible) this._addXP(2);
      this._emit('visibility', data);
    }
  };

  // ── Per-frame update: world physics, distortion, hotspots (call from renderer) ──

  DeltaVerse.prototype.update = function() {
    this.updateWorld();
    this.updateDistortion();
    this.updateHotspots();
  };

  DeltaVerse.prototype.updateWorld = function() {
    // Inertial camera panning
    this.world.x += this.world.vx;
    this.world.y += this.world.vy;
    this.world.vx *= 0.95; // Friction
    this.world.vy *= 0.95;
  };

  // Convert screen coordinates to world coordinates
  DeltaVerse.prototype.screenToWorld = function(sx, sy) {
    var vw = typeof window !== 'undefined' ? window.innerWidth : 1920;
    var vh = typeof window !== 'undefined' ? window.innerHeight : 1080;
    return {
      x: (sx - vw / 2) / this.world.zoom + this.world.x,
      y: (sy - vh / 2) / this.world.zoom + this.world.y,
    };
  };

  // Convert world coordinates to screen coordinates
  DeltaVerse.prototype.worldToScreen = function(wx, wy) {
    var vw = typeof window !== 'undefined' ? window.innerWidth : 1920;
    var vh = typeof window !== 'undefined' ? window.innerHeight : 1080;
    return {
      x: (wx - this.world.x) * this.world.zoom + vw / 2,
      y: (wy - this.world.y) * this.world.zoom + vh / 2,
    };
  };

  // ── Gravitational memory: places where the participant lingered ──

  DeltaVerse.prototype.updateHotspots = function() {
    this._hotspotTimer++;
    // Record hotspot every 2 seconds if mouse is relatively still
    if (this._hotspotTimer >= 120 && this.mouse.speed < 3 && this.mouse.x > 0) {
      var wp = this.screenToWorld(this.mouse.x, this.mouse.y);
      // Merge with nearby hotspot if within range
      var merged = false;
      for (var i = 0; i < this.hotspots.length; i++) {
        var h = this.hotspots[i];
        if (dist(wp.x, wp.y, h.wx, h.wy) < 50 / this.world.zoom) {
          h.energy = Math.min(h.energy + 0.2, 3.0);
          merged = true;
          break;
        }
      }
      if (!merged) {
        this.hotspots.push({wx: wp.x, wy: wp.y, energy: 0.5, decay: 0.998});
      }
      // Cap hotspot count
      if (this.hotspots.length > 50) this.hotspots.shift();
      this._hotspotTimer = 0;
    }
    // Decay hotspots
    for (var j = this.hotspots.length - 1; j >= 0; j--) {
      this.hotspots[j].energy *= this.hotspots[j].decay;
      if (this.hotspots[j].energy < 0.01) this.hotspots.splice(j, 1);
    }
  };

  // ── Telemetry: buffer perception events for backend sync ──

  DeltaVerse.prototype.recordTelemetry = function(event, data) {
    this._telemetryBuffer.push({
      t: Date.now(), e: event, d: data,
      wx: this.world.x, wy: this.world.y, wz: this.world.zoom,
    });
    if (this._telemetryBuffer.length > this._telemetryMaxLen) this._telemetryBuffer.shift();
  };

  DeltaVerse.prototype.flushTelemetry = function() {
    var buf = this._telemetryBuffer.slice();
    this._telemetryBuffer = [];
    return buf;
  };

  // ── Distortion decay ──

  DeltaVerse.prototype.updateDistortion = function() {
    if (!this.distort.active && this.distort.strength > 0) {
      this.distort.linger++;
      if (this.distort.linger < 20) {
        this.distort.strength *= 0.997; // Linger: doubt
      } else {
        this.distort.strength *= 0.83;  // Rapid evaporation
      }
      if (this.distort.strength < 0.005) {
        this.distort.strength = 0;
        this.distort.trail = [];
        this.distort.holdTime = 0;
      }
    }
    // Wind decay
    this.wind.x *= 0.98;
    this.wind.y *= 0.98;
  };

  // ── Tap gesture detection ──

  DeltaVerse.prototype._handleTap = function(x, y, now) {
    var self = this;
    this._tapTimes.push(now);
    this._tapTimes = this._tapTimes.filter(function(t) { return now - t < 800; });
    if (this._tapTimer) clearTimeout(this._tapTimer);
    this._tapTimer = setTimeout(function() {
      var count = self._tapTimes.length;
      self._tapTimes = [];
      if (count === 1) {
        self._emit('tap', {count: 1, x: x, y: y});
      } else if (count === 2) {
        self._checkAchievement('double_tap', true);
        self._addXP(5);
        self._emit('tap', {count: 2, x: x, y: y});
      } else if (count >= 3) {
        self._checkAchievement('triple_tap', true);
        self._addXP(10);
        self._emit('tap', {count: count, x: x, y: y});
      }
    }, 350);
  };

  // ── Gamification ──

  DeltaVerse.prototype._addXP = function(amount) {
    this.profile.xp += amount;
    var newRank = RANKS[0];
    for (var i = RANKS.length - 1; i >= 0; i--) {
      if (this.profile.xp >= RANKS[i].xp) { newRank = RANKS[i]; break; }
    }
    if (newRank.name !== this.profile.rank) {
      var old = this.profile.rank;
      this.profile.rank = newRank.name;
      this.profile.rank_color = newRank.color;
      this._emit('rank_up', {from: old, to: newRank.name, xp: this.profile.xp});
    }
    this.profile.rank = newRank.name;
    this.profile.rank_color = newRank.color;
  };

  DeltaVerse.prototype._checkAchievement = function(id, condition) {
    if (!condition || this.profile.achievements.indexOf(id) !== -1) return;
    var ach = ACHIEVEMENTS[id]; if (!ach) return;
    this.profile.achievements.push(id);
    this._addXP(ach.xp);
    this.recordTelemetry('achievement', {id: id, xp: ach.xp});
    this._emit('achievement', {id: id, name: ach.name, desc: ach.desc, xp: ach.xp});
  };

  DeltaVerse.prototype.getRank = function() {
    for (var i = RANKS.length - 1; i >= 0; i--) if (this.profile.xp >= RANKS[i].xp) return RANKS[i];
    return RANKS[0];
  };
  DeltaVerse.prototype.getNextRank = function() {
    for (var i = 0; i < RANKS.length; i++) if (this.profile.xp < RANKS[i].xp) return RANKS[i];
    return null;
  };

  // ── Gesture detection ──

  DeltaVerse.prototype._detectGestures = function() {
    var h = this._motionHistory;
    if (h.length < 20) return;
    var recent = h.slice(-20);
    // Circle
    var start = recent[0], end = recent[recent.length - 1];
    var loopDist = dist(start.x, start.y, end.x, end.y);
    var totalDist = 0;
    for (var i = 1; i < recent.length; i++) totalDist += dist(recent[i-1].x, recent[i-1].y, recent[i].x, recent[i].y);
    if (loopDist < 40 && totalDist > 150) {
      this.profile.circles_detected++;
      this._checkAchievement('circle_motion', true);
      this._emit('gesture', {type: 'circle', count: this.profile.circles_detected});
    }
    // Zigzag
    var dirs = [];
    for (var j = 1; j < recent.length; j++) dirs.push(recent[j].x - recent[j-1].x > 0 ? 1 : -1);
    var changes = 0;
    for (var k = 1; k < dirs.length; k++) if (dirs[k] !== dirs[k-1]) changes++;
    if (changes > 10) {
      this._checkAchievement('zigzag', true);
      this._emit('gesture', {type: 'zigzag', changes: changes});
    }
  };

  DeltaVerse.prototype._checkRapidClick = function(now) {
    this._clickTimes.push(now);
    this._clickTimes = this._clickTimes.filter(function(t) { return now - t < 3000; });
    if (this._clickTimes.length >= 10) this._checkAchievement('rapid_click', true);
  };

  DeltaVerse.prototype._checkKonami = function(key) {
    var k = key === 'ArrowUp' ? 'up' : key === 'ArrowDown' ? 'down' :
            key === 'ArrowLeft' ? 'left' : key === 'ArrowRight' ? 'right' :
            key === 'b' || key === 'B' ? 'b' : key === 'a' || key === 'A' ? 'a' : null;
    if (!k) { this._konamiIdx = 0; return; }
    var expected = this._konamiIdx < 8 ? this._konamiSeq[this._konamiIdx] :
                   this._konamiIdx === 8 ? 'b' : 'a';
    if (k === expected) {
      this._konamiIdx++;
      if (this._konamiIdx >= 10) {
        this._konamiIdx = 0;
        this._checkAchievement('konami', true);
        this._emit('konami', {});
      }
    } else { this._konamiIdx = 0; }
  };

  // ── Timers: patience, idle, auto-save, focus ──

  DeltaVerse.prototype._startTimers = function() {
    var self = this;
    this._patienceTimer = setInterval(function() {
      self.profile.patience++;
      self.idle++;
      self._checkAchievement('patience_30', self.profile.patience >= 30);
      self._checkAchievement('patience_120', self.profile.patience >= 120);
      self._checkAchievement('focused', self.profile.patience >= 300 && self.visible);
      if (self.idle === 15) {
        self._checkAchievement('stillness', true);
        self._emit('idle', {seconds: self.idle});
      }
      if (self.profile.patience % 60 === 0) self._addXP(10);
    }, 1000);
    // Auto-save every 30 seconds
    this._saveInterval = setInterval(function() { self._saveProfile(); }, 30000);
  };

  DeltaVerse.prototype._stopTimers = function() {
    if (this._patienceTimer) clearInterval(this._patienceTimer);
    if (this._saveInterval) clearInterval(this._saveInterval);
  };

  // ── Event binding (invisible — no UI, just perception) ──

  DeltaVerse.prototype._bindEvents = function() {
    var self = this;
    document.addEventListener('click', function(e) { self.onInteraction('click', {x: e.clientX, y: e.clientY}); });
    document.addEventListener('mousemove', function(e) { self.onInteraction('move', {x: e.clientX, y: e.clientY}); });
    document.addEventListener('wheel', function(e) { self.onInteraction('scroll', {delta: e.deltaY}); }, {passive: true});
    document.addEventListener('keydown', function(e) { self.onInteraction('key', {key: e.key}); });
    document.addEventListener('mousedown', function(e) { self.onInteraction('mousedown', {x: e.clientX, y: e.clientY}); });
    document.addEventListener('mouseup', function() { self.onInteraction('mouseup', {}); });
    document.addEventListener('touchmove', function(e) {
      if (e.touches.length) self.onInteraction('move', {x: e.touches[0].clientX, y: e.touches[0].clientY});
    }, {passive: true});
    document.addEventListener('touchstart', function(e) {
      if (e.touches.length) {
        self.onInteraction('mousedown', {x: e.touches[0].clientX, y: e.touches[0].clientY});
        self.onInteraction('click', {x: e.touches[0].clientX, y: e.touches[0].clientY});
      }
    }, {passive: true});
    document.addEventListener('touchend', function() { self.onInteraction('mouseup', {}); });
    // Tab visibility
    document.addEventListener('visibilitychange', function() {
      self.onInteraction('visibility', {visible: !document.hidden});
    });
  };

  // ── Boot sequence ──

  DeltaVerse.prototype._tick = function() {
    if (!this.running) return;
    var self = this;
    this.profile.messages_seen++;
    if (this.phase === 'ops' && this.idx < this._ops.length) {
      this._show(this._ops[this.idx], '#58a6ff', 'normal');
      this.idx++;
      this._timer = setTimeout(function(){self._tick()}, 280 + Math.random() * 180);
    } else if (this.phase === 'ops') {
      this.phase = 'gen'; this.idx = 0; this._tick();
    } else if (this.phase === 'gen' && this.idx < 3) {
      this._show(this.generateMessage(), '#3fb950', 'normal');
      this.idx++;
      this._timer = setTimeout(function(){self._tick()}, 1600 + Math.random() * 400);
    } else if (this.phase === 'gen') {
      this.phase = 'quotes'; this.idx = 0;
      this._quotes = shuffle(QUOTES.slice());
      this._tick();
    } else if (this.phase === 'quotes') {
      if (this.profile.clicks > 10 && Math.random() > 0.7) {
        var rank = this.getRank();
        this._show(rank.name + ' — ' + pick(CLOSERS), rank.color, 'normal');
      } else {
        this._show(this.getQuote(), '#8b949e', 'italic');
      }
      this._timer = setTimeout(function(){self._tick()}, 2400 + Math.random() * 800);
    }
  };

  // ── Display ──

  DeltaVerse.prototype._show = function(text, color, style) {
    if (this.target) {
      this.target.textContent = text;
      this.target.style.color = color || '#58a6ff';
      this.target.style.fontStyle = style || 'normal';
    }
    this._emit('message', {text: text, phase: this.phase});
  };

  // ── Event system ──

  DeltaVerse.prototype.on = function(event, fn) {
    this._callbacks[event] = this._callbacks[event] || [];
    this._callbacks[event].push(fn);
    return this;
  };
  DeltaVerse.prototype._emit = function(event, data) {
    var fns = this._callbacks[event] || [];
    for (var i = 0; i < fns.length; i++) fns[i](data);
  };

  // ── Profile ──

  DeltaVerse.prototype.getProfile = function() {
    this.profile.patience = Math.floor((Date.now() - this.profile.started) / 1000);
    return this.profile;
  };
  DeltaVerse.prototype._saveProfile = function() {
    try {
      localStorage.setItem('dv_profile', JSON.stringify({
        xp: this.profile.xp, rank: this.profile.rank,
        achievements: this.profile.achievements,
        eggs_found: this.profile.eggs_found,
        total_clicks: this.profile.clicks, total_distance: this.profile.total_distance,
        peak_speed: this.profile.peak_speed, total_sessions: this.profile.total_sessions,
        depth_max: this.profile.depth_max, circles_detected: this.profile.circles_detected,
        distort_total_time: this.profile.distort_total_time,
        // Infinite space: persist camera and hotspots
        world_x: this.world.x, world_y: this.world.y, world_zoom: this.world.zoom,
        hotspots: this.hotspots.slice(0, 20), // Keep top 20 hotspots
      }));
    } catch(e) {}
  };
  DeltaVerse.prototype._loadProfile = function() {
    try {
      var s = JSON.parse(localStorage.getItem('dv_profile') || '{}');
      if (s.xp) this.profile.xp = s.xp;
      if (s.achievements) this.profile.achievements = s.achievements;
      if (s.eggs_found) this.profile.eggs_found = s.eggs_found;
      if (s.total_distance) this.profile.total_distance = s.total_distance;
      if (s.peak_speed) this.profile.peak_speed = s.peak_speed;
      if (s.total_sessions) this.profile.total_sessions = s.total_sessions;
      if (s.depth_max) this.profile.depth_max = s.depth_max;
      if (s.circles_detected) this.profile.circles_detected = s.circles_detected;
      if (s.distort_total_time) this.profile.distort_total_time = s.distort_total_time;
      // Restore infinite space
      if (s.world_x !== undefined) this.world.x = s.world_x;
      if (s.world_y !== undefined) this.world.y = s.world_y;
      if (s.world_zoom) this.world.zoom = s.world_zoom;
      if (s.hotspots) this.hotspots = s.hotspots;
    } catch(e) {}
  };

  // ── Static ──

  DeltaVerse.SUBJECTS = SUBJECTS; DeltaVerse.VERBS = VERBS;
  DeltaVerse.OBJECTS = OBJECTS; DeltaVerse.CLOSERS = CLOSERS;
  DeltaVerse.QUOTES = QUOTES; DeltaVerse.EASTER_EGGS = EASTER_EGGS;
  DeltaVerse.OPS = OPS; DeltaVerse.RANKS = RANKS;
  DeltaVerse.ACHIEVEMENTS = ACHIEVEMENTS;
  DeltaVerse.VERSION = '3.0';

  // ── Export ──

  if (typeof module !== 'undefined' && module.exports) module.exports = DeltaVerse;
  else root.DeltaVerse = DeltaVerse;

})(typeof window !== 'undefined' ? window : this);
