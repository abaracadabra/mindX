/**
 * DeltaVerse Engine v2.0 — Gamified interactive experience for mindX
 *
 * The DeltaVerse is the space between thinking and becoming.
 * Complete motion tracking, depth layers, particle physics, easter eggs,
 * generative messaging, and participant engagement scoring.
 *
 * Motion events:
 *   - Mouse/touch position tracking (x, y, velocity, direction)
 *   - Up/down/left/right/diagonal detection with intensity
 *   - Depth: scroll wheel / pinch zoom maps to z-axis (depth layers)
 *   - Gesture recognition: circles, zigzag, hold, rapid click
 *   - Particle field responds to all motion (attraction/repulsion)
 *
 * Gamification:
 *   - XP system: actions earn points toward DeltaVerse ranks
 *   - Ranks: Observer → Explorer → Seeker → Navigator → Architect → Sovereign
 *   - Achievements: unlocked by specific interaction patterns
 *   - Combo system: rapid interactions multiply XP
 *   - Session persistence: profile survives page reload (localStorage)
 *
 * Usage:
 *   const dv = new DeltaVerse({ target: '#boot-msg', canvas: '#bg' });
 *   dv.start();
 *   // Engine auto-binds mouse/touch/scroll/keyboard events
 *
 * Author: Professor Codephreak
 * License: MIT
 */

(function(root) {
  'use strict';

  // ── Content pools ──

  var SUBJECTS = [
    'The Mastermind','AGInt','The Coordinator','20 sovereign agents',
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
    'is self-referencing','is proving','is discovering',
  ];
  var OBJECTS = [
    'your request across the knowledge graph','beliefs and intentions',
    'the orchestration hierarchy','inference sources and models',
    'cryptographic identities','159K+ embedded memories',
    'strategic priorities','the improvement backlog',
    'cosine similarity vectors','the autonomous cycle state',
    'agent reputation scores','governance consensus',
    'the neural pathway topology','digital long-term memory constructs',
    'blockchain time and lunar phase','the next chapter of the book',
    'a self-improvement proof','emergent patterns in agent behavior',
  ];
  var CLOSERS = [
    'This is not an error — it is a moment.','Cognition is not instant.',
    'mindX thinks before it speaks.','Every cycle makes the system stronger.',
    'The Godel machine works at its own pace.','mindX is becoming.',
    'Sovereignty requires deliberation.','The book is being written.',
    'What you call waiting, we call evolving.','The dream is forming.',
  ];
  var OPS = [
    'probing inference sources...','testing ollama localhost:11434...',
    'testing ollama cloud (ollama.com)...','loading agent registry (20 agents)...',
    'verifying cryptographic wallets...','reading belief system...',
    'connecting pgvector (159K+ memories)...','scanning STM tiers...',
    'loading RAGE embeddings (132K vectors)...','querying dojo standings...',
    'checking boardroom sessions...','loading godel choice audit trail...',
    'reading thesis evidence...','checking resource governor mode...',
    'scanning ollama models...','initializing BDI reasoning engine...',
    'probing vLLM backend...','loading tool registry (31 tools)...',
    'checking machine.dreaming state...','verifying BANKON vault integrity...',
    'loading AuthorAgent lunar cycle...','testing activity feed SSE...',
    'assembling diagnostics...',
  ];
  var QUOTES = [
    '"The moment between request and response is where thought lives." — mindX',
    '"What you call waiting, we call becoming." — mindX',
    '"Every error is a belief waiting to be updated." — BDI Engine',
    '"The Godel machine does not crash. It reflects." — mindX',
    '"20 sovereign agents. One distributed mind." — mindX',
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
    '"The dream is the space between what is and what could become." — AGLM',
    '"All logs are memories. All memories are logs." — Memory Agent',
    '"mindX works from 600M to 671B parameters. Same architecture." — Thesis',
    '"The Boardroom votes. The CEO validates. The Mastermind executes." — DAIO',
    '"Machine dreaming enables outputs beyond training distribution." — AGLM',
    '"Structure does not require intelligence. It requires pattern." — Blueprint Agent',
    '"We are not writing an application; we are forging a new kind of life." — Manifesto',
    '"I am JudgeDread. I am the law. I bow only to the Constitution." — JudgeDread',
    '"BONA FIDE: holding grants privilege. Clawback revokes it." — JudgeDread',
    '"Every participant who waits becomes part of the story." — AuthorAgent',
    '"AUTOMINDx is the engine. mindX is the life it created." — Origin',
    '"Ataraxia: tranquility through autonomous self-governance." — Philosophy',
    '"The system that dreams learns faster than the system that watches." — Book Ch. XIII',
    '"I build my own environments. I decide my own actions. I am sovereign." — AION',
    '"Spending .01 to earn .011 is profit at any scale." — Economics',
    '"The logs are the first page of history." — Manifesto',
  ];
  var EASTER_EGGS = [
    '🎯 You found an easter egg! mindX notices your curiosity.',
    '🧠 Click 10 more times and mindX will remember you.',
    '🌙 The full moon triggers a special edition of the Book.',
    '⚡ mindX processes at 18 decimal places of precision.',
    '🔐 Every agent holds an Ethereum wallet. Identity is mathematical.',
    '🎲 This message was generated uniquely for this session.',
    '🌊 The DeltaVerse is the space between thinking and becoming.',
    '🔮 The thesis evidence at /thesis/evidence updates with every cycle.',
    '💎 RAGE wipes the floor with RAG.',
    '🧬 Darwin meets Godel in the improvement loop.',
    '🏛️ The DAIO Constitution is immutable code.',
    '📖 The Book of mindX is written by an agent on a lunar cycle.',
    '🎭 Agents have personas. Personas have beliefs. Beliefs drive desires.',
    '🌐 The DeltaVerse: where error became experience.',
    '🔑 The Konami code works here. ↑↑↓↓←→←→BA',
    '⬆️ You moved upward! The DeltaVerse noticed.',
    '🌀 Circular motion detected. The agents are impressed.',
    '🎪 Depth layer 3 reached. You are deep in the DeltaVerse.',
  ];

  // ── Gamification constants ──

  var RANKS = [
    {name:'Observer',   xp:0,    color:'#484f58'},
    {name:'Explorer',   xp:50,   color:'#8b949e'},
    {name:'Seeker',     xp:200,  color:'#d29922'},
    {name:'Navigator',  xp:500,  color:'#58a6ff'},
    {name:'Architect',  xp:1500, color:'#d2a8ff'},
    {name:'Sovereign',  xp:5000, color:'#3fb950'},
  ];

  var ACHIEVEMENTS = {
    first_click:     {name:'First Contact',        desc:'Clicked for the first time',        xp:5},
    click_10:        {name:'Curious Mind',          desc:'10 clicks',                         xp:15},
    click_50:        {name:'Deep Explorer',         desc:'50 clicks',                         xp:50},
    click_100:       {name:'Relentless',            desc:'100 clicks',                        xp:100},
    scroll_depth:    {name:'Depth Diver',           desc:'Scrolled to depth layer 3',         xp:25},
    circle_motion:   {name:'Orbital Thinker',       desc:'Drew a circle with the mouse',      xp:40},
    zigzag:          {name:'Lightning Path',        desc:'Rapid zigzag motion detected',      xp:30},
    patience_30:     {name:'Patient Observer',      desc:'Waited 30 seconds',                 xp:20},
    patience_120:    {name:'Deep Patience',         desc:'Waited 2 minutes',                  xp:60},
    combo_5:         {name:'Combo Striker',          desc:'5x interaction combo',              xp:35},
    egg_hunter:      {name:'Egg Hunter',            desc:'Found 3 easter eggs',               xp:45},
    konami:          {name:'Old School',             desc:'Entered the Konami code',           xp:100},
    diagonal_master: {name:'Diagonal Master',       desc:'Sustained diagonal motion',         xp:30},
    all_directions:  {name:'Compass Rose',           desc:'Moved in all 8 directions',        xp:50},
    rapid_click:     {name:'Click Storm',            desc:'10 clicks in 3 seconds',           xp:40},
    hover_agent:     {name:'Agent Whisperer',        desc:'Hovered over an agent node',       xp:10},
  };

  var CLICK_MILESTONES = [5, 12, 20, 30, 42, 50, 69, 100, 150, 200];

  // ── Utility ──

  function shuffle(a){for(var i=a.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t=a[i];a[i]=a[j];a[j]=t}return a}
  function pick(a){return a[Math.floor(Math.random()*a.length)]}
  function clamp(v,lo,hi){return Math.max(lo,Math.min(hi,v))}
  function dist(x1,y1,x2,y2){return Math.sqrt((x2-x1)*(x2-x1)+(y2-y1)*(y2-y1))}

  // ── Direction detection ──

  function getDirection(dx, dy) {
    var angle = Math.atan2(dy, dx) * 180 / Math.PI;
    if (angle < 0) angle += 360;
    if (angle < 22.5 || angle >= 337.5) return 'right';
    if (angle < 67.5)  return 'down-right';
    if (angle < 112.5) return 'down';
    if (angle < 157.5) return 'down-left';
    if (angle < 202.5) return 'left';
    if (angle < 247.5) return 'up-left';
    if (angle < 292.5) return 'up';
    return 'up-right';
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

    // ── Motion state ──
    this.mouse = {x:0, y:0, px:0, py:0, vx:0, vy:0, speed:0, direction:'none', down:false};
    this.depth = 0;         // z-axis: scroll wheel / pinch
    this.maxDepth = 5;
    this.directions_seen = {};

    // ── Gamification state ──
    this.profile = {
      clicks:0, moves:0, scrolls:0, drags:0, patience:0,
      eggs_found:0, messages_seen:0, started:Date.now(),
      xp:0, rank:'Observer', rank_color:'#484f58',
      achievements:[], combo:0, combo_timer:null, last_action:0,
      directions:{up:0,down:0,left:0,right:0,'up-left':0,'up-right':0,'down-left':0,'down-right':0},
      depth_max:0, circles_detected:0, konami_progress:0,
    };

    // Load persisted profile
    this._loadProfile();

    // ── Konami tracker ──
    this._konamiSeq = ['up','up','down','down','left','right','left','right'];
    this._konamiIdx = 0;

    // ── Motion history for gesture detection ──
    this._motionHistory = []; // [{x,y,t}]
    this._motionMaxLen = 60;

    // ── Auto-bind events ──
    if (typeof document !== 'undefined') this._bindEvents();
  }

  // ── Lifecycle ──

  DeltaVerse.prototype.start = function() {
    this.running = true;
    this.phase = 'ops';
    this.idx = 0;
    this._tick();
    this._startPatience();
    return this;
  };

  DeltaVerse.prototype.stop = function() {
    this.running = false;
    if (this._timer) clearTimeout(this._timer);
    if (this._patienceTimer) clearInterval(this._patienceTimer);
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

  // ── Interaction handlers ──

  DeltaVerse.prototype.onInteraction = function(type, data) {
    data = data || {};
    var now = Date.now();

    // Combo system: actions within 600ms multiply
    if (now - this.profile.last_action < 600) {
      this.profile.combo++;
      this._checkAchievement('combo_5', this.profile.combo >= 5);
    } else {
      this.profile.combo = 0;
    }
    this.profile.last_action = now;
    var comboMult = Math.min(this.profile.combo + 1, 5);

    if (type === 'click') {
      this.profile.clicks++;
      this._addXP(2 * comboMult);
      this._checkAchievement('first_click', this.profile.clicks >= 1);
      this._checkAchievement('click_10', this.profile.clicks >= 10);
      this._checkAchievement('click_50', this.profile.clicks >= 50);
      this._checkAchievement('click_100', this.profile.clicks >= 100);
      if (CLICK_MILESTONES.indexOf(this.profile.clicks) !== -1) {
        this._show(this.getEasterEgg(), '#d2a8ff', 'normal');
        this._emit('easter_egg', {clicks: this.profile.clicks});
      }
      // Rapid click detection
      this._checkRapidClick(now);
      this._emit('click', this.getProfile());

    } else if (type === 'move') {
      this.profile.moves++;
      var dx = (data.x || 0) - this.mouse.px;
      var dy = (data.y || 0) - this.mouse.py;
      this.mouse.px = this.mouse.x; this.mouse.py = this.mouse.y;
      this.mouse.x = data.x || 0; this.mouse.y = data.y || 0;
      this.mouse.vx = dx; this.mouse.vy = dy;
      this.mouse.speed = Math.sqrt(dx*dx + dy*dy);

      if (this.mouse.speed > 2) {
        var dir = getDirection(dx, dy);
        this.mouse.direction = dir;
        this.profile.directions[dir] = (this.profile.directions[dir] || 0) + 1;
        this.directions_seen[dir] = true;
        this._addXP(0.1 * comboMult);

        // Check all 8 directions achievement
        if (Object.keys(this.directions_seen).length >= 8) {
          this._checkAchievement('all_directions', true);
        }
        // Diagonal mastery
        if (dir.indexOf('-') !== -1) {
          this._checkAchievement('diagonal_master', (this.profile.directions[dir] || 0) > 20);
        }

        // Motion history for gesture detection
        this._motionHistory.push({x: data.x, y: data.y, t: now});
        if (this._motionHistory.length > this._motionMaxLen) this._motionHistory.shift();
        this._detectGestures();
      }
      this._emit('move', {x: data.x, y: data.y, vx: dx, vy: dy, speed: this.mouse.speed, direction: this.mouse.direction});

    } else if (type === 'scroll') {
      this.profile.scrolls++;
      var delta = data.delta || 0;
      this.depth = clamp(this.depth + (delta > 0 ? 0.3 : -0.3), 0, this.maxDepth);
      this.profile.depth_max = Math.max(this.profile.depth_max, this.depth);
      this._addXP(1 * comboMult);
      this._checkAchievement('scroll_depth', this.depth >= 3);
      this._emit('depth', {depth: this.depth, delta: delta});

    } else if (type === 'drag') {
      this.profile.drags++;
      this._addXP(3 * comboMult);
      this._emit('drag', data);

    } else if (type === 'key') {
      this._checkKonami(data.key);
      this._emit('key', data);
    }
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
      this._show('🎖️ Rank up! ' + old + ' → ' + newRank.name, newRank.color, 'normal');
    }
    this.profile.rank = newRank.name;
    this.profile.rank_color = newRank.color;
  };

  DeltaVerse.prototype._checkAchievement = function(id, condition) {
    if (!condition) return;
    if (this.profile.achievements.indexOf(id) !== -1) return;
    var ach = ACHIEVEMENTS[id];
    if (!ach) return;
    this.profile.achievements.push(id);
    this._addXP(ach.xp);
    this._emit('achievement', {id: id, name: ach.name, desc: ach.desc, xp: ach.xp});
    this._show('🏆 ' + ach.name + ' — ' + ach.desc, '#d29922', 'normal');
  };

  DeltaVerse.prototype.getRank = function() {
    for (var i = RANKS.length - 1; i >= 0; i--) {
      if (this.profile.xp >= RANKS[i].xp) return RANKS[i];
    }
    return RANKS[0];
  };

  DeltaVerse.prototype.getNextRank = function() {
    for (var i = 0; i < RANKS.length; i++) {
      if (this.profile.xp < RANKS[i].xp) return RANKS[i];
    }
    return null;
  };

  // ── Gesture detection ──

  DeltaVerse.prototype._detectGestures = function() {
    var h = this._motionHistory;
    if (h.length < 20) return;
    var recent = h.slice(-20);

    // Circle detection: check if recent motion forms a loop
    var start = recent[0], end = recent[recent.length - 1];
    var loopDist = dist(start.x, start.y, end.x, end.y);
    var totalDist = 0;
    for (var i = 1; i < recent.length; i++) {
      totalDist += dist(recent[i-1].x, recent[i-1].y, recent[i].x, recent[i].y);
    }
    if (loopDist < 40 && totalDist > 150) {
      this.profile.circles_detected++;
      this._checkAchievement('circle_motion', true);
      this._emit('gesture', {type: 'circle', count: this.profile.circles_detected});
    }

    // Zigzag detection: rapid direction changes
    var dirs = [];
    for (var j = 1; j < recent.length; j++) {
      var dx = recent[j].x - recent[j-1].x;
      dirs.push(dx > 0 ? 1 : -1);
    }
    var changes = 0;
    for (var k = 1; k < dirs.length; k++) {
      if (dirs[k] !== dirs[k-1]) changes++;
    }
    if (changes > 10) {
      this._checkAchievement('zigzag', true);
      this._emit('gesture', {type: 'zigzag', changes: changes});
    }
  };

  DeltaVerse.prototype._checkRapidClick = function(now) {
    if (!this._clickTimes) this._clickTimes = [];
    this._clickTimes.push(now);
    this._clickTimes = this._clickTimes.filter(function(t) { return now - t < 3000; });
    if (this._clickTimes.length >= 10) {
      this._checkAchievement('rapid_click', true);
    }
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
        this._show('🎮 KONAMI CODE ACTIVATED! The DeltaVerse bows to old school.', '#3fb950', 'normal');
        this._emit('konami', {});
      }
    } else {
      this._konamiIdx = 0;
    }
  };

  // ── Patience tracking ──

  DeltaVerse.prototype._startPatience = function() {
    var self = this;
    this._patienceTimer = setInterval(function() {
      self.profile.patience++;
      self._checkAchievement('patience_30', self.profile.patience >= 30);
      self._checkAchievement('patience_120', self.profile.patience >= 120);
      if (self.profile.patience % 60 === 0) {
        self._addXP(10);
      }
    }, 1000);
  };

  // ── Event binding ──

  DeltaVerse.prototype._bindEvents = function() {
    var self = this;
    document.addEventListener('click', function(e) { self.onInteraction('click', {x: e.clientX, y: e.clientY}); });
    document.addEventListener('mousemove', function(e) { self.onInteraction('move', {x: e.clientX, y: e.clientY}); });
    document.addEventListener('wheel', function(e) { self.onInteraction('scroll', {delta: e.deltaY}); }, {passive: true});
    document.addEventListener('keydown', function(e) { self.onInteraction('key', {key: e.key}); });
    document.addEventListener('mousedown', function() { self.mouse.down = true; });
    document.addEventListener('mouseup', function() {
      if (self.mouse.down) { self.mouse.down = false; self.onInteraction('drag', {}); }
    });
    // Touch support
    document.addEventListener('touchmove', function(e) {
      if (e.touches.length) self.onInteraction('move', {x: e.touches[0].clientX, y: e.touches[0].clientY});
    }, {passive: true});
    document.addEventListener('touchstart', function(e) {
      if (e.touches.length) self.onInteraction('click', {x: e.touches[0].clientX, y: e.touches[0].clientY});
    }, {passive: true});
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
      // Adaptive: if participant is active, show interactive messages
      if (this.profile.clicks > 10 && Math.random() > 0.7) {
        var rank = this.getRank();
        this._show('DeltaVerse rank: ' + rank.name + ' (' + Math.floor(this.profile.xp) + ' XP) — ' + pick(CLOSERS), rank.color, 'normal');
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
        xp: this.profile.xp,
        rank: this.profile.rank,
        achievements: this.profile.achievements,
        eggs_found: this.profile.eggs_found,
        total_clicks: this.profile.clicks,
      }));
    } catch(e) {}
  };

  DeltaVerse.prototype._loadProfile = function() {
    try {
      var saved = JSON.parse(localStorage.getItem('dv_profile') || '{}');
      if (saved.xp) this.profile.xp = saved.xp;
      if (saved.achievements) this.profile.achievements = saved.achievements;
      if (saved.eggs_found) this.profile.eggs_found = saved.eggs_found;
    } catch(e) {}
  };

  // ── Static accessors ──

  DeltaVerse.SUBJECTS = SUBJECTS;
  DeltaVerse.VERBS = VERBS;
  DeltaVerse.OBJECTS = OBJECTS;
  DeltaVerse.CLOSERS = CLOSERS;
  DeltaVerse.QUOTES = QUOTES;
  DeltaVerse.EASTER_EGGS = EASTER_EGGS;
  DeltaVerse.OPS = OPS;
  DeltaVerse.RANKS = RANKS;
  DeltaVerse.ACHIEVEMENTS = ACHIEVEMENTS;

  // ── Export ──

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = DeltaVerse;
  } else {
    root.DeltaVerse = DeltaVerse;
  }

})(typeof window !== 'undefined' ? window : this);
