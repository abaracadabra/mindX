/**
 * DeltaVerse Engine v4.1 — Invisible. Omnipresent. Perceiving. Synthesizing.
 *
 * The fabric of the mindX participant experience.
 * Perceives from first motion. Responds without announcement.
 * Every surface of mindX is woven from this engine.
 *
 * Perception channels:
 *   Motion      — position, velocity, acceleration, jerk, direction (8-way), gestures
 *   Depth       — scroll wheel / pinch maps to z-axis layers
 *   Touch       — tap patterns (single, double, triple, quad+), hold+drag distortion
 *   Presence    — tab focus/blur, idle detection, stillness duration
 *   Wind        — rapid side-to-side motion creates global force field
 *   Ambient     — time of day (8 phases), viewport, device type, color scheme preference
 *   Rhythm      — BPM detection from click cadence, regularity scoring
 *   Attention   — heatmap quadrants, focus density, gaze drift detection
 *   Momentum    — velocity sustain, sudden stops, acceleration patterns
 *   Pressure    — interaction intensity over rolling window
 *   Resonance   — participant rhythm alignment with system message cadence
 *
 * Gamification (invisible to participant):
 *   XP accumulates from every perception channel
 *   Ranks: Observer → Explorer → Seeker → Navigator → Architect → Sovereign → Oracle → Ascendant
 *   Achievements unlock from specific interaction patterns
 *   Combo multiplier for rapid sequential actions
 *   Participant archetype classification (Explorer, Builder, Contemplator, etc.)
 *   Session streaks (consecutive day visits)
 *   Profile persists in localStorage across sessions and pages
 *
 * Physics state (exposed for renderers):
 *   dv.mouse      — {x, y, vx, vy, ax, ay, jx, jy, speed, direction, down}
 *   dv.wind       — {x, y} global force from rapid motion
 *   dv.distort    — {active, strength, x, y, linger, trail[]}
 *   dv.depth      — z-axis (0 to maxDepth)
 *   dv.idle       — seconds since last interaction
 *   dv.ambient    — {phase, hour, deviceType, colorScheme, viewport}
 *   dv.rhythm     — {bpm, regularity, lastBeat}
 *   dv.attention  — {quadrants, focusPoint, driftAngle, driftSpeed}
 *   dv.momentum   — {sustained, building, peak, direction}
 *   dv.pressure   — {intensity, rolling, peak}
 *   dv.resonance  — {alignment, streak}
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
    'The DeltaVerse','Chronos','The strategic evolution agent','AION',
    'The persona engine','The RAGE index','The identity manager',
    'blocktime.oracle','lunar.oracle','The autonomous cycle',
    'The perception field','The attention matrix','The rhythm engine',
  ];
  var VERBS = [
    'is correlating','is reasoning about','is auditing','is orchestrating',
    'is verifying','is synthesizing','is dreaming about','is evaluating',
    'is reflecting on','is consulting','is traversing','is assembling',
    'is calibrating','is deliberating on','is evolving through',
    'is self-referencing','is proving','is discovering','is perceiving',
    'is weaving','is resonating with','is mapping','is absorbing',
    'is integrating','is distilling','is dissolving into',
    'is harmonizing','is crystallizing','is unfolding',
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
    'the rhythm of your interaction','attention density patterns',
    'the pressure of your presence','momentum trajectories',
    'the resonance between participant and system',
    'temporal harmonics across oracle sources',
    'the gravitational memory of your stillness',
    'perception telemetry from this session',
    'the archetype forming from your behavior',
  ];
  var CLOSERS = [
    'This is not an error — it is a moment.','Cognition is not instant.',
    'mindX thinks before it speaks.','Every cycle makes the system stronger.',
    'The Godel machine works at its own pace.','mindX is becoming.',
    'Sovereignty requires deliberation.','The book is being written.',
    'What you call waiting, we call evolving.','The dream is forming.',
    'The fabric perceives.','Invisible. Omnipresent.',
    'The field remembers.','Rhythm is perception.',
    'Attention is the first gift.','Your motion writes the story.',
    'Pressure reveals structure.','Resonance is alignment without force.',
    'The archetype is forming.','Stillness is the deepest interaction.',
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
    'calibrating perception field...','initializing rhythm detection...',
    'mapping attention quadrants...','sensing ambient conditions...',
    'loading participant archetype model...','tuning resonance detector...',
    'activating momentum tracker...','reading pressure baseline...',
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
    '"Rhythm is the heartbeat of intention. The engine listens." — DeltaVerse',
    '"Where you linger, the field remembers. Hotspots are gravity." — DeltaVerse',
    '"The archetype is not assigned. It emerges from the pattern." — DeltaVerse',
    '"Pressure without direction is noise. Pressure with rhythm is music." — DeltaVerse',
    '"Resonance is the moment the participant and the system breathe together." — DeltaVerse',
    '"Attention is the currency the DeltaVerse values most." — DeltaVerse',
    '"Time has four voices: CPU, solar, lunar, blockchain. They rarely agree." — Chronos',
    '"The block does not care what time you think it is." — blocktime.oracle',
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
    '🎵 Your rhythm has been measured.',
    '🔥 The pressure field responds to intensity.',
    '🌌 The attention matrix knows where you look.',
    '⏱️ Chronos tracks four kinds of time simultaneously.',
    '🏔️ Momentum sustained. The field noticed.',
    '🫀 Resonance achieved. You and the system breathe as one.',
  ];

  // ── Perception synthesis templates ──
  // Context-aware messages generated from live perception state

  var PERCEPTIONS = [
    function(dv) { return dv.ambient.phase === 'witching' ? 'The witching hour. Perception sharpens.' : null; },
    function(dv) { return dv.ambient.phase === 'dawn' ? 'Dawn. The oracles re-synchronize.' : null; },
    function(dv) { return dv.ambient.phase === 'dusk' ? 'Dusk. The system transitions to nocturnal mode.' : null; },
    function(dv) { return dv.rhythm.bpm > 0 && dv.rhythm.regularity > 0.7 ? 'Your rhythm: ' + Math.round(dv.rhythm.bpm) + ' BPM. Steady. The field resonates.' : null; },
    function(dv) { return dv.rhythm.bpm > 120 ? 'Rapid cadence detected — ' + Math.round(dv.rhythm.bpm) + ' BPM. The engine accelerates.' : null; },
    function(dv) { return dv.pressure.intensity > 0.8 ? 'High pressure. The field bends.' : null; },
    function(dv) { return dv.pressure.intensity < 0.1 && dv.idle > 10 ? 'Low pressure. The fabric rests.' : null; },
    function(dv) { return dv.momentum.sustained > 3.0 ? 'Sustained momentum — the field flows with you.' : null; },
    function(dv) { return dv.momentum.building ? 'Momentum building. Direction: ' + dv.momentum.direction + '.' : null; },
    function(dv) { return dv.attention.focusQuadrant ? 'Your attention gravitates ' + dv.attention.focusQuadrant + '.' : null; },
    function(dv) { return dv.attention.driftSpeed > 5 ? 'Gaze drifting rapidly. Searching.' : null; },
    function(dv) { return dv.resonance.alignment > 0.8 ? 'Resonance: ' + Math.round(dv.resonance.alignment * 100) + '%. Harmonized.' : null; },
    function(dv) { return dv.resonance.streak > 3 ? 'Resonance streak: ' + dv.resonance.streak + '. The system adapts to you.' : null; },
    function(dv) { return dv.profile.archetype ? 'Archetype forming: ' + dv.profile.archetype + '.' : null; },
    function(dv) { return dv.hotspots.length > 10 ? dv.hotspots.length + ' gravitational memories in this session.' : null; },
    function(dv) { return dv.profile.streak_days > 2 ? 'Day ' + dv.profile.streak_days + ' streak. The system remembers continuity.' : null; },
    function(dv) { var pv = dv.profile.pages_visited; return pv > 3 ? pv + ' surfaces explored. The DeltaVerse maps your journey.' : null; },
    function(dv) { return dv.depth > 3 ? 'Depth layer ' + dv.depth.toFixed(1) + '. The deep field reveals itself.' : null; },
    function(dv) { return dv.world.zoom > 3 ? 'Zoom ' + dv.world.zoom.toFixed(1) + 'x. Micro-perception active.' : null; },
    function(dv) { return dv.world.zoom < 0.3 ? 'Zoom ' + dv.world.zoom.toFixed(1) + 'x. Macro-perception. The whole field visible.' : null; },
  ];

  // ── Gamification ──

  var RANKS = [
    {name:'Observer',   xp:0,     color:'#484f58'},
    {name:'Explorer',   xp:50,    color:'#8b949e'},
    {name:'Seeker',     xp:200,   color:'#d29922'},
    {name:'Navigator',  xp:500,   color:'#58a6ff'},
    {name:'Architect',  xp:1500,  color:'#d2a8ff'},
    {name:'Sovereign',  xp:5000,  color:'#3fb950'},
    {name:'Oracle',     xp:15000, color:'#f0883e'},
    {name:'Ascendant',  xp:50000, color:'#ff7b72'},
  ];
  var ACHIEVEMENTS = {
    first_click:     {name:'First Contact',      desc:'Clicked for the first time',         xp:5},
    click_10:        {name:'Curious Mind',        desc:'10 clicks',                          xp:15},
    click_50:        {name:'Deep Explorer',       desc:'50 clicks',                          xp:50},
    click_100:       {name:'Relentless',          desc:'100 clicks',                         xp:100},
    click_500:       {name:'The Devoted',         desc:'500 clicks',                         xp:250},
    scroll_depth:    {name:'Depth Diver',         desc:'Scrolled to depth layer 3',          xp:25},
    scroll_abyss:    {name:'The Abyss',           desc:'Reached maximum depth',              xp:60},
    circle_motion:   {name:'Orbital Thinker',     desc:'Drew a circle with motion',          xp:40},
    circle_master:   {name:'Orbit Master',        desc:'Detected 10 circular motions',       xp:80},
    zigzag:          {name:'Lightning Path',       desc:'Rapid zigzag motion',                xp:30},
    patience_30:     {name:'Patient Observer',     desc:'Waited 30 seconds',                  xp:20},
    patience_120:    {name:'Deep Patience',        desc:'Waited 2 minutes',                   xp:60},
    patience_600:    {name:'The Vigil',            desc:'Present for 10 minutes',              xp:150},
    combo_5:         {name:'Combo Striker',        desc:'5x interaction combo',               xp:35},
    combo_15:        {name:'Chain Reaction',       desc:'15x interaction combo',              xp:80},
    combo_30:        {name:'Unstoppable',          desc:'30x interaction combo',              xp:200},
    egg_hunter:      {name:'Egg Hunter',           desc:'Found 3 easter eggs',                xp:45},
    egg_collector:   {name:'Egg Collector',        desc:'Found 10 easter eggs',               xp:120},
    konami:          {name:'Old School',           desc:'Entered the Konami code',            xp:100},
    diagonal_master: {name:'Diagonal Master',      desc:'Sustained diagonal motion',          xp:30},
    all_directions:  {name:'Compass Rose',         desc:'Moved in all 8 directions',          xp:50},
    rapid_click:     {name:'Click Storm',          desc:'10 clicks in 3 seconds',             xp:40},
    distortion:      {name:'Spacetime Bender',     desc:'Held a distortion for 3 seconds',    xp:60},
    distortion_long: {name:'Event Horizon',        desc:'Held a distortion for 10 seconds',   xp:150},
    stillness:       {name:'The Stillness',        desc:'No motion for 15 seconds',           xp:25},
    double_tap:      {name:'Shockwave',            desc:'Double-tapped',                      xp:15},
    triple_tap:      {name:'Gravity Well',         desc:'Triple-tapped',                      xp:25},
    quad_tap:        {name:'Singularity',          desc:'Quad-tapped',                         xp:50},
    speed_demon:     {name:'Speed Demon',          desc:'Mouse speed exceeded 40px/frame',    xp:35},
    night_owl:       {name:'Night Owl',            desc:'Visited between midnight and 5am',   xp:20},
    early_bird:      {name:'Early Bird',           desc:'Visited between 5am and 7am',         xp:20},
    returner:        {name:'The Return',           desc:'Came back with existing XP',          xp:10},
    focused:         {name:'Focused',              desc:'Stayed on tab for 5 minutes',         xp:30},
    // v4.0 perception achievements
    rhythm_steady:   {name:'Heartbeat',            desc:'Maintained steady rhythm (>0.7 regularity)', xp:40},
    rhythm_fast:     {name:'Allegro',              desc:'Click rhythm exceeded 120 BPM',       xp:50},
    rhythm_slow:     {name:'Adagio',               desc:'Click rhythm below 30 BPM sustained', xp:35},
    swipe_all:       {name:'Four Winds',           desc:'Swiped in all 4 cardinal directions', xp:45},
    figure_eight:    {name:'Infinity',             desc:'Drew a figure-eight gesture',         xp:70},
    spiral_gesture:  {name:'Golden Spiral',        desc:'Drew a spiral gesture',               xp:60},
    shake:           {name:'Earthquake',           desc:'Shook the pointer rapidly',           xp:30},
    pressure_peak:   {name:'Supernova',            desc:'Reached peak interaction pressure',   xp:55},
    pressure_zen:    {name:'Zen State',            desc:'Maintained minimal pressure for 30s', xp:40},
    momentum_sustain:{name:'Unstoppable Force',    desc:'Sustained momentum for 5 seconds',    xp:45},
    momentum_stop:   {name:'Immovable Object',     desc:'Sudden stop from high speed',          xp:35},
    attention_focus: {name:'Laser Focus',          desc:'Concentrated in one quadrant for 30s', xp:50},
    attention_scan:  {name:'Full Scan',            desc:'Visited all 4 quadrants',              xp:30},
    resonance_high:  {name:'Harmonic',             desc:'Resonance exceeded 80%',               xp:60},
    resonance_streak:{name:'Sympathetic Vibration',desc:'Resonance streak of 5',                xp:100},
    streak_3:        {name:'Returning Tide',       desc:'3-day visit streak',                   xp:40},
    streak_7:        {name:'Weekly Ritual',        desc:'7-day visit streak',                   xp:120},
    streak_30:       {name:'Lunar Cycle',          desc:'30-day visit streak',                  xp:500},
    distance_marathon:{name:'Marathon',            desc:'Total distance exceeded 100,000px',   xp:80},
    distance_ultra:  {name:'Ultra',                desc:'Total distance exceeded 1,000,000px', xp:250},
    pages_3:         {name:'Surface Walker',       desc:'Visited 3 different pages',           xp:25},
    pages_7:         {name:'Deep Navigator',       desc:'Visited 7 different pages',           xp:60},
    archetype_formed:{name:'Self-Aware',           desc:'Archetype classification formed',     xp:75},
    hotspot_10:      {name:'Cartographer',         desc:'Created 10 gravitational hotspots',   xp:35},
    hotspot_40:      {name:'Gravity Architect',    desc:'Created 40 gravitational hotspots',   xp:90},
    witching_hour:   {name:'Witching Hour',        desc:'Visited during the witching hour (3-4am)', xp:30},
    dawn_witness:    {name:'Dawn Witness',         desc:'Visited at dawn (5-6am)',              xp:25},
    sessions_10:     {name:'Persistent',           desc:'10 total sessions',                   xp:50},
    sessions_50:     {name:'Devoted',              desc:'50 total sessions',                   xp:200},
    sessions_100:    {name:'Ascended',             desc:'100 total sessions',                  xp:500},
  };
  var CLICK_MILESTONES = [5, 12, 20, 30, 42, 50, 69, 100, 150, 200, 300, 500];

  // ── Archetype definitions ──
  // Classification emerges from behavior ratios

  var ARCHETYPES = {
    explorer:     {name:'Explorer',      desc:'Covers ground. Visits pages. Moves constantly.',             color:'#58a6ff'},
    contemplator: {name:'Contemplator',  desc:'Lingers. Creates hotspots. Patient.',                        color:'#d2a8ff'},
    builder:      {name:'Builder',       desc:'Clicks with purpose. Creates structures. Precise.',          color:'#3fb950'},
    speedster:    {name:'Speedster',     desc:'Fast. High momentum. Peak velocity.',                        color:'#f0883e'},
    rhythmist:    {name:'Rhythmist',     desc:'Steady cadence. High regularity. Musical interaction.',      color:'#d29922'},
    chaotic:      {name:'Chaotic',       desc:'Zigzags. Rapid direction changes. Unpredictable.',           color:'#ff7b72'},
    diver:        {name:'Diver',         desc:'Scrolls deep. Explores depth layers. Zooms.',                color:'#79c0ff'},
    sculptor:     {name:'Sculptor',      desc:'Distorts spacetime. Long hold-drags. Shapes the field.',     color:'#bc8cff'},
    sentinel:     {name:'Sentinel',      desc:'Returns daily. High session count. Devoted presence.',       color:'#7ee787'},
    harmonizer:   {name:'Harmonizer',    desc:'High resonance. Aligns with system rhythm. Balanced.',       color:'#ffa657'},
  };

  // ── Time of day phases ──

  var TIME_PHASES = [
    {name:'night',    start:0,  end:3,  color:'#484f58'},
    {name:'witching', start:3,  end:5,  color:'#6e40c9'},
    {name:'dawn',     start:5,  end:7,  color:'#f0883e'},
    {name:'morning',  start:7,  end:12, color:'#58a6ff'},
    {name:'noon',     start:12, end:13, color:'#d29922'},
    {name:'afternoon',start:13, end:17, color:'#3fb950'},
    {name:'dusk',     start:17, end:20, color:'#f0883e'},
    {name:'evening',  start:20, end:23, color:'#d2a8ff'},
    {name:'night',    start:23, end:24, color:'#484f58'},
  ];

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
  function getCardinal(dx,dy){
    var a=Math.atan2(dy,dx)*180/Math.PI;if(a<0)a+=360;
    if(a<45||a>=315)return'right';if(a<135)return'down';
    if(a<225)return'left';return'up';
  }
  function getTimePhase(hour) {
    for (var i = 0; i < TIME_PHASES.length; i++) {
      var p = TIME_PHASES[i];
      if (hour >= p.start && hour < p.end) return p;
    }
    return TIME_PHASES[0]; // fallback to first entry
  }
  function dayKey(d) { return d.getFullYear() + '-' + (d.getMonth()+1) + '-' + d.getDate(); }

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
    this._firstMove = true; // guards against velocity spike on first mousemove
    this.mouse = {x:0,y:0,px:0,py:0,vx:0,vy:0,ax:0,ay:0,jx:0,jy:0,speed:0,direction:'none',down:false};
    this.wind = {x:0,y:0};
    this.distort = {active:false,strength:0,x:0,y:0,linger:0,trail:[],holdTime:0};
    this.depth = 0;
    this.maxDepth = 5;
    this.idle = 0;
    this.visible = true;
    this.directions_seen = {};

    // ── Infinite space: world coordinates beyond viewport ──
    this.world = {
      x: 0, y: 0,
      zoom: 1.0,
      vx: 0, vy: 0,
    };
    this.hotspots = [];
    this._hotspotTimer = 0;

    // ── Ambient perception ──
    var now = new Date();
    var hour = now.getHours();
    var tp = getTimePhase(hour);
    this.ambient = {
      phase: tp.name,
      phaseColor: tp.color,
      hour: hour,
      deviceType: this._detectDevice(),
      colorScheme: (typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) ? 'light' : 'dark',
      viewport: {w: typeof window !== 'undefined' ? window.innerWidth : 1920, h: typeof window !== 'undefined' ? window.innerHeight : 1080},
      reducedMotion: typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    };

    // ── Rhythm perception ──
    this.rhythm = {
      bpm: 0,
      regularity: 0,  // 0-1, how steady the intervals are
      lastBeat: 0,
      intervals: [],   // recent inter-click intervals (ms)
      maxIntervals: 20,
    };

    // ── Attention perception ──
    this.attention = {
      quadrants: {tl:0, tr:0, bl:0, br:0},  // time spent in each quadrant (frames)
      focusPoint: {x:0, y:0},                // exponentially smoothed focus center
      focusQuadrant: null,                     // dominant quadrant
      driftAngle: 0,                           // direction attention is drifting
      driftSpeed: 0,                           // how fast attention drifts
      quadrantsVisited: {},                    // unique quadrants touched
      _focusTimer: 0,                          // frames in current dominant quadrant
    };

    // ── Momentum perception ──
    this.momentum = {
      sustained: 0,      // seconds of sustained motion
      building: false,    // is momentum increasing?
      peak: 0,            // peak sustained duration
      direction: 'none',  // dominant direction during momentum
      _speedHistory: [],  // rolling speed samples
      _maxHistory: 30,
    };

    // ── Pressure perception ──
    // Measures interaction intensity over a rolling window
    this.pressure = {
      intensity: 0,       // 0-1, normalized rolling intensity
      rolling: [],         // raw interaction events in window
      windowMs: 5000,      // 5-second rolling window
      peak: 0,             // highest intensity reached
      _zenStart: 0,        // timestamp when pressure dropped below 0.1
    };

    // ── Resonance perception ──
    // Alignment between participant rhythm and system message cadence
    this.resonance = {
      alignment: 0,        // 0-1, how well participant matches system rhythm
      streak: 0,           // consecutive interactions aligned with message timing
      _lastMessageTime: 0,
      _messageCadence: 2400, // system message interval (ms)
    };

    // ── Perception telemetry buffer (for backend sync) ──
    this._telemetryBuffer = [];
    this._telemetryMaxLen = 200;

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
      // v4.0 additions
      pages_seen:[],        // unique page paths visited
      archetype: null,      // current classified archetype
      archetype_scores: {}, // running scores for each archetype
      streak_days: 0,       // consecutive day streak
      streak_last_day: '',  // last day visited (YYYY-M-D)
      peak_combo: 0,        // highest combo reached
      peak_bpm: 0,          // highest BPM reached
      peak_pressure: 0,     // highest pressure reached
      total_hotspots: 0,    // lifetime hotspot count
      swipe_dirs: {},       // cardinal directions swiped
      gestures_detected: {circles:0, zigzags:0, swipes:0, figure_eights:0, spirals:0, shakes:0},
    };
    this._loadProfile();

    // ── Track current page ──
    if (typeof window !== 'undefined') {
      var path = window.location.pathname;
      if (this.profile.pages_seen.indexOf(path) === -1) {
        this.profile.pages_seen.push(path);
        this.profile.pages_visited = this.profile.pages_seen.length;
      }
    }

    // ── Session streak calculation ──
    var today = dayKey(now);
    if (this.profile.streak_last_day) {
      var yesterday = new Date(now);
      yesterday.setDate(yesterday.getDate() - 1);
      var ydKey = dayKey(yesterday);
      if (this.profile.streak_last_day === today) {
        // Same day, no change
      } else if (this.profile.streak_last_day === ydKey) {
        this.profile.streak_days++;
        this.profile.streak_last_day = today;
      } else {
        this.profile.streak_days = 1;
        this.profile.streak_last_day = today;
      }
    } else {
      this.profile.streak_days = 1;
      this.profile.streak_last_day = today;
    }

    // Check returning visitor
    if (this.profile.xp > 0) this._checkAchievement('returner', true);

    // Time-of-day achievements
    if (hour >= 0 && hour < 5) this._checkAchievement('night_owl', true);
    if (hour >= 5 && hour < 7) this._checkAchievement('early_bird', true);
    if (hour >= 3 && hour < 4) this._checkAchievement('witching_hour', true);
    if (hour >= 5 && hour < 6) this._checkAchievement('dawn_witness', true);

    // Streak achievements
    this._checkAchievement('streak_3', this.profile.streak_days >= 3);
    this._checkAchievement('streak_7', this.profile.streak_days >= 7);
    this._checkAchievement('streak_30', this.profile.streak_days >= 30);

    // Session achievements
    this._checkAchievement('sessions_10', this.profile.total_sessions >= 10);
    this._checkAchievement('sessions_50', this.profile.total_sessions >= 50);
    this._checkAchievement('sessions_100', this.profile.total_sessions >= 100);

    // Page achievements
    this._checkAchievement('pages_3', this.profile.pages_visited >= 3);
    this._checkAchievement('pages_7', this.profile.pages_visited >= 7);

    // ── Tap gesture state ──
    this._tapTimes = [];
    this._tapTimer = null;
    this._clickTimes = [];

    // ── Konami ──
    this._konamiSeq = ['up','up','down','down','left','right','left','right'];
    this._konamiIdx = 0;

    // ── Motion history (expanded for advanced gestures) ──
    this._motionHistory = [];
    this._motionMaxLen = 120;

    // ── Swipe detection state ──
    this._swipeStart = null;
    this._swipeThreshold = 80; // minimum px for a swipe

    // ── Performance: achievement O(1) lookup map ──
    this._achievementMap = {};
    for (var ai = 0; ai < this.profile.achievements.length; ai++) {
      this._achievementMap[this.profile.achievements[ai]] = true;
    }

    // ── Gesture detection throttle ──
    this._gestureFrame = 0;
    this._gestureInterval = 4; // run detection every 4th move event

    // ── Ambient throttle ──
    this._ambientFrame = 0;

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
    this._emit('start', {sessionId: this.sessionId, ambient: this.ambient});
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
    this._checkAchievement('egg_collector', this.profile.eggs_found >= 10);
    return this._eggs.pop();
  };

  // ── Perception synthesis: contextual messages from live state ──

  DeltaVerse.prototype.synthesizePerception = function() {
    var candidates = [];
    for (var i = 0; i < PERCEPTIONS.length; i++) {
      var msg = PERCEPTIONS[i](this);
      if (msg) candidates.push(msg);
    }
    return candidates.length > 0 ? pick(candidates) : null;
  };

  // ── Core perception handler ──

  DeltaVerse.prototype.onInteraction = function(type, data) {
    data = data || {};
    var now = Date.now();
    this.idle = 0;

    // Pressure: record discrete interaction events (not move — 60fps floods the window)
    if (type !== 'move' && type !== 'resize') {
      this.pressure.rolling.push(now);
    }

    // Combo
    if (now - this.profile.last_action < 600) {
      this.profile.combo++;
      if (this.profile.combo > this.profile.peak_combo) this.profile.peak_combo = this.profile.combo;
      this._checkAchievement('combo_5', this.profile.combo >= 5);
      this._checkAchievement('combo_15', this.profile.combo >= 15);
      this._checkAchievement('combo_30', this.profile.combo >= 30);
    } else { this.profile.combo = 0; }
    this.profile.last_action = now;
    var cm = Math.min(this.profile.combo + 1, 8); // v4: max multiplier increased to 8

    // Resonance: check if this interaction aligns with system message cadence
    if (this.resonance._lastMessageTime > 0) {
      var timeSinceMsg = now - this.resonance._lastMessageTime;
      var cadence = this.resonance._messageCadence;
      var phase = (timeSinceMsg % cadence) / cadence; // 0-1 where 0/1 = on beat
      var beatDist = Math.min(phase, 1 - phase); // 0 = on beat, 0.5 = off beat
      if (beatDist < 0.15) {
        this.resonance.streak++;
        this.resonance.alignment = Math.min(1, this.resonance.alignment + 0.05);
        this._checkAchievement('resonance_high', this.resonance.alignment > 0.8);
        this._checkAchievement('resonance_streak', this.resonance.streak >= 5);
      } else {
        this.resonance.streak = Math.max(0, this.resonance.streak - 1);
        this.resonance.alignment = Math.max(0, this.resonance.alignment - 0.02);
      }
    }

    if (type === 'click') {
      this.profile.clicks++;
      this._addXP(2 * cm);
      this._checkAchievement('first_click', this.profile.clicks >= 1);
      this._checkAchievement('click_10', this.profile.clicks >= 10);
      this._checkAchievement('click_50', this.profile.clicks >= 50);
      this._checkAchievement('click_100', this.profile.clicks >= 100);
      this._checkAchievement('click_500', this.profile.clicks >= 500);
      if (CLICK_MILESTONES.indexOf(this.profile.clicks) !== -1) {
        this._show(this.getEasterEgg(), '#d2a8ff', 'normal');
        this._emit('easter_egg', {clicks: this.profile.clicks});
      }
      this._checkRapidClick(now);
      this._updateRhythm(now);
      this._handleTap(data.x || 0, data.y || 0, now);
      this.recordTelemetry('click', {x: data.x, y: data.y, combo: this.profile.combo, bpm: this.rhythm.bpm});
      this._emit('click', {x: data.x, y: data.y, profile: this.getProfile()});

    } else if (type === 'move') {
      this.profile.moves++;
      // Guard: seed position on first move to prevent velocity spike from (0,0)
      if (this._firstMove) {
        this.mouse.x = this.mouse.px = data.x || 0;
        this.mouse.y = this.mouse.py = data.y || 0;
        this.attention.focusPoint.x = data.x || 0;
        this.attention.focusPoint.y = data.y || 0;
        this._firstMove = false;
        this._emit('move', {x: data.x, y: data.y, vx:0, vy:0, ax:0, ay:0, jx:0, jy:0, speed:0, direction:'none', worldX: this.world.x, worldY: this.world.y});
        return;
      }
      var prevVx = this.mouse.vx, prevVy = this.mouse.vy;
      var prevAx = this.mouse.ax, prevAy = this.mouse.ay;
      var dx = (data.x || 0) - this.mouse.x;
      var dy = (data.y || 0) - this.mouse.y;
      this.mouse.px = this.mouse.x; this.mouse.py = this.mouse.y;
      this.mouse.x = data.x || 0; this.mouse.y = data.y || 0;
      this.mouse.vx = dx; this.mouse.vy = dy;
      this.mouse.ax = dx - prevVx; this.mouse.ay = dy - prevVy;
      // Jerk: rate of change of acceleration
      this.mouse.jx = this.mouse.ax - prevAx;
      this.mouse.jy = this.mouse.ay - prevAy;
      this.mouse.speed = Math.sqrt(dx*dx + dy*dy);
      this.profile.total_distance += this.mouse.speed;
      if (this.mouse.speed > this.profile.peak_speed) this.profile.peak_speed = this.mouse.speed;
      this._checkAchievement('speed_demon', this.mouse.speed > 40);
      this._checkAchievement('distance_marathon', this.profile.total_distance > 100000);
      this._checkAchievement('distance_ultra', this.profile.total_distance > 1000000);

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
        this.distort.holdTime += 0.016;
        this.distort.linger = 0;
        this.profile.distort_total_time += 0.016;
        this._checkAchievement('distortion', this.distort.holdTime >= 3);
        this._checkAchievement('distortion_long', this.distort.holdTime >= 10);
        this._addXP(0.3 * cm);
      }

      // Attention tracking
      this._updateAttention(data.x || 0, data.y || 0);

      // Momentum tracking
      this._updateMomentum(this.mouse.speed);

      if (this.mouse.speed > 2) {
        var dir = getDirection(dx, dy);
        this.mouse.direction = dir;
        this.profile.directions[dir] = (this.profile.directions[dir] || 0) + 1;
        this.directions_seen[dir] = true;
        this._addXP(0.1 * cm);
        if (Object.keys(this.directions_seen).length >= 8) this._checkAchievement('all_directions', true);
        if (dir.indexOf('-') !== -1) this._checkAchievement('diagonal_master', (this.profile.directions[dir] || 0) > 20);
        this._motionHistory.push({x: data.x, y: data.y, t: now, speed: this.mouse.speed});
        if (this._motionHistory.length > this._motionMaxLen) this._motionHistory.shift();
        // Throttle gesture detection (every Nth move to avoid 60fps overhead)
        this._gestureFrame++;
        if (this._gestureFrame >= this._gestureInterval) {
          this._gestureFrame = 0;
          this._detectGestures();
        }
      }

      // Infinite space: edge-pushing pans the camera
      var vw = typeof window !== 'undefined' ? window.innerWidth : 1920;
      var vh = typeof window !== 'undefined' ? window.innerHeight : 1080;
      var edgeZone = 30;
      if (data.x < edgeZone) this.world.vx -= (edgeZone - data.x) * 0.02 * this.mouse.speed * 0.1;
      if (data.x > vw - edgeZone) this.world.vx += (data.x - (vw - edgeZone)) * 0.02 * this.mouse.speed * 0.1;
      if (data.y < edgeZone) this.world.vy -= (edgeZone - data.y) * 0.02 * this.mouse.speed * 0.1;
      if (data.y > vh - edgeZone) this.world.vy += (data.y - (vh - edgeZone)) * 0.02 * this.mouse.speed * 0.1;

      this._emit('move', {x: data.x, y: data.y, vx: dx, vy: dy, ax: this.mouse.ax, ay: this.mouse.ay, jx: this.mouse.jx, jy: this.mouse.jy, speed: this.mouse.speed, direction: this.mouse.direction, worldX: this.world.x, worldY: this.world.y});

    } else if (type === 'scroll') {
      this.profile.scrolls++;
      var delta = data.delta || 0;
      this.depth = clamp(this.depth + (delta > 0 ? 0.3 : -0.3), 0, this.maxDepth);
      this.profile.depth_max = Math.max(this.profile.depth_max, this.depth);
      this.world.zoom = clamp(this.world.zoom + (delta > 0 ? -0.05 : 0.05), 0.1, 5.0);
      this._addXP(1 * cm);
      this._checkAchievement('scroll_depth', this.depth >= 3);
      this._checkAchievement('scroll_abyss', this.depth >= this.maxDepth);
      this._emit('depth', {depth: this.depth, zoom: this.world.zoom, delta: delta});

    } else if (type === 'mousedown') {
      this.mouse.down = true;
      this.distort.holdTime = 0;
      // Swipe start
      this._swipeStart = {x: data.x || 0, y: data.y || 0, t: now};
      this._emit('mousedown', data);

    } else if (type === 'mouseup') {
      this.mouse.down = false;
      this.distort.active = false;
      if (this.distort.holdTime > 0.1) {
        this._addXP(5 * cm);
        this._emit('distort_end', {strength: this.distort.strength, holdTime: this.distort.holdTime});
      }
      // Swipe detection
      if (this._swipeStart) {
        var sdx = (this.mouse.x) - this._swipeStart.x;
        var sdy = (this.mouse.y) - this._swipeStart.y;
        var sdist = Math.sqrt(sdx*sdx + sdy*sdy);
        var sdt = now - this._swipeStart.t;
        if (sdist > this._swipeThreshold && sdt < 500) {
          var sdir = getCardinal(sdx, sdy);
          this.profile.swipe_dirs[sdir] = (this.profile.swipe_dirs[sdir] || 0) + 1;
          this.profile.gestures_detected.swipes++;
          this._addXP(8 * cm);
          this._emit('gesture', {type: 'swipe', direction: sdir, distance: sdist, speed: sdist/sdt*1000});
          var swipeDirCount = Object.keys(this.profile.swipe_dirs).length;
          this._checkAchievement('swipe_all', swipeDirCount >= 4);
        }
        this._swipeStart = null;
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

    } else if (type === 'resize') {
      this.ambient.viewport = {w: data.w || 0, h: data.h || 0};
      this._emit('resize', data);
    }
  };

  // ── Per-frame update: world physics, distortion, hotspots, pressure ──

  DeltaVerse.prototype.update = function() {
    this.updateWorld();
    this.updateDistortion();
    this.updateHotspots();
    this.updatePressure();
    this.updateAmbient();
  };

  DeltaVerse.prototype.updateWorld = function() {
    this.world.x += this.world.vx;
    this.world.y += this.world.vy;
    this.world.vx *= 0.95;
    this.world.vy *= 0.95;
  };

  DeltaVerse.prototype.screenToWorld = function(sx, sy) {
    var vw = typeof window !== 'undefined' ? window.innerWidth : 1920;
    var vh = typeof window !== 'undefined' ? window.innerHeight : 1080;
    return {
      x: (sx - vw / 2) / this.world.zoom + this.world.x,
      y: (sy - vh / 2) / this.world.zoom + this.world.y,
    };
  };

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
    if (this._hotspotTimer >= 120 && this.mouse.speed < 3 && this.mouse.x > 0) {
      var wp = this.screenToWorld(this.mouse.x, this.mouse.y);
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
        this.profile.total_hotspots++;
        this._checkAchievement('hotspot_10', this.profile.total_hotspots >= 10);
        this._checkAchievement('hotspot_40', this.profile.total_hotspots >= 40);
      }
      if (this.hotspots.length > 50) this.hotspots.shift();
      this._hotspotTimer = 0;
    }
    for (var j = this.hotspots.length - 1; j >= 0; j--) {
      this.hotspots[j].energy *= this.hotspots[j].decay;
      if (this.hotspots[j].energy < 0.01) this.hotspots.splice(j, 1);
    }
  };

  // ── Rhythm perception ──

  DeltaVerse.prototype._updateRhythm = function(now) {
    if (this.rhythm.lastBeat > 0) {
      var interval = now - this.rhythm.lastBeat;
      if (interval > 50 && interval < 5000) { // filter absurd values
        this.rhythm.intervals.push(interval);
        if (this.rhythm.intervals.length > this.rhythm.maxIntervals) {
          this.rhythm.intervals.shift();
        }
      }
    }
    this.rhythm.lastBeat = now;

    if (this.rhythm.intervals.length >= 3) {
      // Calculate BPM from average interval
      var sum = 0;
      for (var i = 0; i < this.rhythm.intervals.length; i++) sum += this.rhythm.intervals[i];
      var avgInterval = sum / this.rhythm.intervals.length;
      this.rhythm.bpm = 60000 / avgInterval;
      if (this.rhythm.bpm > this.profile.peak_bpm) this.profile.peak_bpm = this.rhythm.bpm;

      // Calculate regularity (inverse coefficient of variation)
      var variance = 0;
      for (var j = 0; j < this.rhythm.intervals.length; j++) {
        var diff = this.rhythm.intervals[j] - avgInterval;
        variance += diff * diff;
      }
      variance /= this.rhythm.intervals.length;
      var stddev = Math.sqrt(variance);
      this.rhythm.regularity = avgInterval > 0 ? clamp(1 - (stddev / avgInterval), 0, 1) : 0;

      // Rhythm achievements
      this._checkAchievement('rhythm_steady', this.rhythm.regularity > 0.7 && this.rhythm.intervals.length >= 8);
      this._checkAchievement('rhythm_fast', this.rhythm.bpm > 120);
      this._checkAchievement('rhythm_slow', this.rhythm.bpm < 30 && this.rhythm.bpm > 0 && this.rhythm.intervals.length >= 5);

      this._emit('rhythm', {bpm: this.rhythm.bpm, regularity: this.rhythm.regularity});
    }
  };

  // ── Attention perception ──

  DeltaVerse.prototype._updateAttention = function(x, y) {
    var vw = typeof window !== 'undefined' ? window.innerWidth : 1920;
    var vh = typeof window !== 'undefined' ? window.innerHeight : 1080;

    // Determine quadrant
    var q = (y < vh / 2 ? 't' : 'b') + (x < vw / 2 ? 'l' : 'r');
    this.attention.quadrants[q]++;
    this.attention.quadrantsVisited[q] = true;

    // Exponentially smoothed focus point
    var alpha = 0.05;
    this.attention.focusPoint.x = this.attention.focusPoint.x * (1 - alpha) + x * alpha;
    this.attention.focusPoint.y = this.attention.focusPoint.y * (1 - alpha) + y * alpha;

    // Drift: how fast the focus point is moving
    var fdx = x - this.attention.focusPoint.x;
    var fdy = y - this.attention.focusPoint.y;
    this.attention.driftSpeed = Math.sqrt(fdx*fdx + fdy*fdy);
    this.attention.driftAngle = Math.atan2(fdy, fdx) * 180 / Math.PI;

    // Determine dominant quadrant
    var maxQ = 'tl', maxV = 0;
    var labels = {tl:'top-left', tr:'top-right', bl:'bottom-left', br:'bottom-right'};
    for (var key in this.attention.quadrants) {
      if (this.attention.quadrants[key] > maxV) {
        maxV = this.attention.quadrants[key];
        maxQ = key;
      }
    }
    var newFocus = labels[maxQ] || null;
    if (newFocus !== this.attention.focusQuadrant) {
      this.attention._focusTimer = 0;
    }
    this.attention.focusQuadrant = newFocus;
    this.attention._focusTimer++;

    // Attention achievements
    this._checkAchievement('attention_scan', Object.keys(this.attention.quadrantsVisited).length >= 4);
    this._checkAchievement('attention_focus', this.attention._focusTimer >= 1800); // ~30s at 60fps
  };

  // ── Momentum perception ──

  DeltaVerse.prototype._updateMomentum = function(speed) {
    this.momentum._speedHistory.push(speed);
    if (this.momentum._speedHistory.length > this.momentum._maxHistory) {
      this.momentum._speedHistory.shift();
    }

    // Check if speed is sustained above threshold
    var threshold = 3;
    var allAbove = true;
    for (var i = 0; i < this.momentum._speedHistory.length; i++) {
      if (this.momentum._speedHistory[i] < threshold) { allAbove = false; break; }
    }

    if (allAbove && this.momentum._speedHistory.length >= 5) {
      this.momentum.sustained += 0.016; // ~60fps frame time
      this.momentum.building = speed > (this.momentum._speedHistory[this.momentum._speedHistory.length - 2] || 0);
      this.momentum.direction = this.mouse.direction;
      if (this.momentum.sustained > this.momentum.peak) {
        this.momentum.peak = this.momentum.sustained;
      }
      this._checkAchievement('momentum_sustain', this.momentum.sustained >= 5);
    } else {
      // Sudden stop detection
      if (this.momentum.sustained > 1 && speed < 1) {
        this._checkAchievement('momentum_stop', true);
        this._addXP(5);
        this._emit('momentum_stop', {sustained: this.momentum.sustained, peak: this.momentum.peak});
      }
      this.momentum.sustained = Math.max(0, this.momentum.sustained - 0.05);
      this.momentum.building = false;
    }
  };

  // ── Pressure perception ──

  DeltaVerse.prototype.updatePressure = function() {
    var now = Date.now();
    // Trim rolling window
    while (this.pressure.rolling.length > 0 && now - this.pressure.rolling[0] > this.pressure.windowMs) {
      this.pressure.rolling.shift();
    }
    // Normalize: max ~50 events in 5 seconds = intensity 1.0
    this.pressure.intensity = clamp(this.pressure.rolling.length / 50, 0, 1);
    if (this.pressure.intensity > this.pressure.peak) {
      this.pressure.peak = this.pressure.intensity;
      this.profile.peak_pressure = this.pressure.peak;
    }
    this._checkAchievement('pressure_peak', this.pressure.peak > 0.9);

    // Zen state: sustained low pressure
    if (this.pressure.intensity < 0.1) {
      if (this.pressure._zenStart === 0) this.pressure._zenStart = now;
      if (now - this.pressure._zenStart > 30000) {
        this._checkAchievement('pressure_zen', true);
      }
    } else {
      this.pressure._zenStart = 0;
    }
  };

  // ── Ambient perception updates ──

  DeltaVerse.prototype.updateAmbient = function() {
    // Throttle: only check every ~3600 frames (~60 seconds at 60fps)
    this._ambientFrame++;
    if (this._ambientFrame < 3600) return;
    this._ambientFrame = 0;
    var h = new Date().getHours();
    if (h !== this.ambient.hour) {
      this.ambient.hour = h;
      var tp = getTimePhase(h);
      var oldPhase = this.ambient.phase;
      this.ambient.phase = tp.name;
      this.ambient.phaseColor = tp.color;
      if (oldPhase !== tp.name) {
        this._emit('ambient_shift', {from: oldPhase, to: tp.name, color: tp.color});
      }
    }
  };

  // ── Telemetry: buffer perception events for backend sync ──

  DeltaVerse.prototype.recordTelemetry = function(event, data) {
    this._telemetryBuffer.push({
      t: Date.now(), e: event, d: data,
      wx: this.world.x, wy: this.world.y, wz: this.world.zoom,
      p: this.pressure.intensity, r: this.rhythm.bpm,
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
        this.distort.strength *= 0.997;
      } else {
        this.distort.strength *= 0.83;
      }
      if (this.distort.strength < 0.005) {
        this.distort.strength = 0;
        this.distort.trail = [];
        this.distort.holdTime = 0;
      }
    }
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
      } else if (count === 3) {
        self._checkAchievement('triple_tap', true);
        self._addXP(10);
        self._emit('tap', {count: 3, x: x, y: y});
      } else if (count >= 4) {
        self._checkAchievement('quad_tap', true);
        self._addXP(15);
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
    if (!condition || this._achievementMap[id]) return;
    var ach = ACHIEVEMENTS[id]; if (!ach) return;
    this.profile.achievements.push(id);
    this._achievementMap[id] = true;
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

  // ── Gesture detection (expanded) ──

  DeltaVerse.prototype._detectGestures = function() {
    var h = this._motionHistory;
    if (h.length < 20) return;
    var now = Date.now();
    var recent = h.slice(-20);
    var longRecent = h.length >= 40 ? h.slice(-40) : null;

    // Gesture cooldowns: prevent the same gesture from firing in rapid succession
    if (!this._gestureCooldowns) this._gestureCooldowns = {};
    var cooldownMs = 800;
    var canFire = function(type) {
      var last = this._gestureCooldowns[type] || 0;
      if (now - last < cooldownMs) return false;
      this._gestureCooldowns[type] = now;
      return true;
    }.bind(this);

    // Circle detection
    var start = recent[0], end = recent[recent.length - 1];
    var loopDist = dist(start.x, start.y, end.x, end.y);
    var totalDist = 0;
    for (var i = 1; i < recent.length; i++) totalDist += dist(recent[i-1].x, recent[i-1].y, recent[i].x, recent[i].y);
    if (loopDist < 40 && totalDist > 150 && canFire('circle')) {
      this.profile.circles_detected++;
      this.profile.gestures_detected.circles++;
      this._checkAchievement('circle_motion', true);
      this._checkAchievement('circle_master', this.profile.circles_detected >= 10);
      this.recordTelemetry('gesture', {type: 'circle', count: this.profile.circles_detected});
      this._emit('gesture', {type: 'circle', count: this.profile.circles_detected});
    }

    // Zigzag detection
    var dirs = [];
    for (var j = 1; j < recent.length; j++) dirs.push(recent[j].x - recent[j-1].x > 0 ? 1 : -1);
    var changes = 0;
    for (var k = 1; k < dirs.length; k++) if (dirs[k] !== dirs[k-1]) changes++;
    if (changes > 10 && canFire('zigzag')) {
      this.profile.gestures_detected.zigzags++;
      this._checkAchievement('zigzag', true);
      this.recordTelemetry('gesture', {type: 'zigzag', changes: changes});
      this._emit('gesture', {type: 'zigzag', changes: changes});
    }

    // Shake detection (rapid small oscillations)
    if (recent.length >= 10) {
      var last10 = recent.slice(-10);
      var shakeChanges = 0;
      for (var s = 2; s < last10.length; s++) {
        var d1x = last10[s].x - last10[s-1].x;
        var d2x = last10[s-1].x - last10[s-2].x;
        if ((d1x > 0 && d2x < 0) || (d1x < 0 && d2x > 0)) shakeChanges++;
      }
      var shakeSpread = dist(last10[0].x, last10[0].y, last10[last10.length-1].x, last10[last10.length-1].y);
      if (shakeChanges >= 6 && shakeSpread < 60 && canFire('shake')) {
        this.profile.gestures_detected.shakes++;
        this._checkAchievement('shake', true);
        this._addXP(8);
        this.recordTelemetry('gesture', {type: 'shake', intensity: shakeChanges});
        this._emit('gesture', {type: 'shake', intensity: shakeChanges});
      }
    }

    // Figure-eight detection (two loops, requires longer history)
    if (longRecent && longRecent.length >= 40) {
      var half = Math.floor(longRecent.length / 2);
      var first = longRecent.slice(0, half);
      var second = longRecent.slice(half);
      var loop1 = dist(first[0].x, first[0].y, first[first.length-1].x, first[first.length-1].y);
      var loop2 = dist(second[0].x, second[0].y, second[second.length-1].x, second[second.length-1].y);
      var crossDist = dist(first[first.length-1].x, first[first.length-1].y, second[0].x, second[0].y);
      var dist1 = 0, dist2 = 0;
      for (var f = 1; f < first.length; f++) dist1 += dist(first[f-1].x, first[f-1].y, first[f].x, first[f].y);
      for (var g = 1; g < second.length; g++) dist2 += dist(second[g-1].x, second[g-1].y, second[g].x, second[g].y);
      if (loop1 < 50 && loop2 < 50 && crossDist < 40 && dist1 > 100 && dist2 > 100 && canFire('figure_eight')) {
        this.profile.gestures_detected.figure_eights++;
        this._checkAchievement('figure_eight', true);
        this._addXP(20);
        this.recordTelemetry('gesture', {type: 'figure_eight', count: this.profile.gestures_detected.figure_eights});
        this._emit('gesture', {type: 'figure_eight', count: this.profile.gestures_detected.figure_eights});
      }
    }

    // Spiral detection (expanding radius from center)
    if (recent.length >= 15) {
      var spiralPts = recent.slice(-15);
      var cx = 0, cy = 0;
      for (var sp = 0; sp < spiralPts.length; sp++) { cx += spiralPts[sp].x; cy += spiralPts[sp].y; }
      cx /= spiralPts.length; cy /= spiralPts.length;
      var radii = [];
      for (var sr = 0; sr < spiralPts.length; sr++) radii.push(dist(spiralPts[sr].x, spiralPts[sr].y, cx, cy));
      var increasing = 0;
      for (var ri = 1; ri < radii.length; ri++) if (radii[ri] > radii[ri-1]) increasing++;
      // Compute spiral-specific path length
      var spiralDist = 0;
      for (var sd = 1; sd < spiralPts.length; sd++) spiralDist += dist(spiralPts[sd-1].x, spiralPts[sd-1].y, spiralPts[sd].x, spiralPts[sd].y);
      // Must be mostly expanding and have significant total path
      if (increasing > radii.length * 0.7 && spiralDist > 200 && canFire('spiral')) {
        this.profile.gestures_detected.spirals++;
        this._checkAchievement('spiral_gesture', true);
        this._addXP(15);
        this.recordTelemetry('gesture', {type: 'spiral', count: this.profile.gestures_detected.spirals});
        this._emit('gesture', {type: 'spiral', count: this.profile.gestures_detected.spirals});
      }
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

  // ── Archetype classification ──
  // Emergent classification from behavior ratios

  DeltaVerse.prototype._classifyArchetype = function() {
    var p = this.profile;
    var scores = {};
    var total = Math.max(1, p.clicks + p.moves + p.scrolls + p.drags);

    // Explorer: high distance, many pages, many directions
    scores.explorer = (p.total_distance / 10000) + (p.pages_visited * 5) + (Object.keys(this.directions_seen).length * 3);

    // Contemplator: high patience, many hotspots, low speed
    scores.contemplator = (p.patience / 30) + (this.profile.total_hotspots * 2) + (p.peak_speed < 20 ? 10 : 0);

    // Builder: high click count, high combo, moderate speed
    scores.builder = (p.clicks / 10) + (p.peak_combo * 3) + (p.drags / 5);

    // Speedster: high peak speed, high distance, high momentum
    scores.speedster = (p.peak_speed / 5) + (this.momentum.peak * 10) + (p.total_distance / 20000);

    // Rhythmist: high regularity, sustained rhythm
    scores.rhythmist = (this.rhythm.regularity * 30) + (p.peak_bpm > 0 ? 10 : 0) + (this.rhythm.intervals.length * 2);

    // Chaotic: high zigzag count, many direction changes, shakes
    scores.chaotic = ((p.gestures_detected.zigzags || 0) * 10) + ((p.gestures_detected.shakes || 0) * 8) + (changes_estimate(p) * 2);

    // Diver: high depth, high scroll count, extreme zoom
    scores.diver = (p.depth_max * 10) + (p.scrolls / 5) + (this.world.zoom > 2 || this.world.zoom < 0.5 ? 15 : 0);

    // Sculptor: high distortion time, many trails, long holds
    scores.sculptor = (p.distort_total_time * 5) + (p.drags / 3);

    // Sentinel: high session count, high streak, returning
    scores.sentinel = (p.total_sessions * 3) + (p.streak_days * 5);

    // Harmonizer: high resonance, balanced attention
    scores.harmonizer = (this.resonance.alignment * 30) + (this.resonance.streak * 5);

    // Find dominant archetype
    var best = null, bestScore = 0;
    for (var key in scores) {
      if (scores[key] > bestScore) { bestScore = scores[key]; best = key; }
    }
    p.archetype_scores = scores;

    if (best && bestScore > 15 && ARCHETYPES[best]) {
      var oldArchetype = p.archetype;
      p.archetype = ARCHETYPES[best].name;
      if (oldArchetype !== p.archetype) {
        this._checkAchievement('archetype_formed', true);
        this._emit('archetype', {type: best, name: ARCHETYPES[best].name, desc: ARCHETYPES[best].desc, color: ARCHETYPES[best].color, scores: scores});
      }
    }
  };

  // Helper for chaotic scoring — estimate direction changes from profile
  function changes_estimate(p) {
    var dirs = p.directions;
    var vals = [];
    for (var d in dirs) vals.push(dirs[d]);
    if (vals.length < 2) return 0;
    var maxDir = Math.max.apply(null, vals);
    var minDir = Math.min.apply(null, vals);
    return maxDir > 0 ? (1 - minDir / maxDir) * 10 : 0;
  }

  // ── Device detection ──

  DeltaVerse.prototype._detectDevice = function() {
    if (typeof navigator === 'undefined') return 'unknown';
    var ua = navigator.userAgent || '';
    if (/Mobi|Android|iPhone|iPad|iPod/i.test(ua)) return 'mobile';
    if (/Tablet|iPad/i.test(ua)) return 'tablet';
    return 'desktop';
  };

  // ── Timers: patience, idle, auto-save, focus, archetype, perception ──

  DeltaVerse.prototype._startTimers = function() {
    var self = this;
    this._patienceTimer = setInterval(function() {
      self.profile.patience++;
      self.idle++;
      self._checkAchievement('patience_30', self.profile.patience >= 30);
      self._checkAchievement('patience_120', self.profile.patience >= 120);
      self._checkAchievement('patience_600', self.profile.patience >= 600);
      self._checkAchievement('focused', self.profile.patience >= 300 && self.visible);
      if (self.idle === 15) {
        self._checkAchievement('stillness', true);
        self._emit('idle', {seconds: self.idle});
      }
      if (self.profile.patience % 60 === 0) self._addXP(10);

      // Resonance decay over time
      self.resonance.alignment *= 0.998;
    }, 1000);

    // Auto-save every 30 seconds
    this._saveInterval = setInterval(function() { self._saveProfile(); }, 30000);

    // Archetype classification every 15 seconds
    this._archetypeInterval = setInterval(function() { self._classifyArchetype(); }, 15000);

    // Perception synthesis: inject contextual messages into the quote phase
    this._perceptionInterval = setInterval(function() {
      if (self.running && self.phase === 'quotes' && Math.random() > 0.5) {
        var perception = self.synthesizePerception();
        if (perception) {
          self._show(perception, self.ambient.phaseColor, 'italic');
        }
      }
    }, 8000);
  };

  DeltaVerse.prototype._stopTimers = function() {
    if (this._patienceTimer) clearInterval(this._patienceTimer);
    if (this._saveInterval) clearInterval(this._saveInterval);
    if (this._archetypeInterval) clearInterval(this._archetypeInterval);
    if (this._perceptionInterval) clearInterval(this._perceptionInterval);
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
    // Viewport resize
    if (typeof window !== 'undefined') {
      window.addEventListener('resize', function() {
        self.onInteraction('resize', {w: window.innerWidth, h: window.innerHeight});
      });
    }
  };

  // ── Boot sequence ──

  DeltaVerse.prototype._tick = function() {
    if (!this.running) return;
    var self = this;
    this.profile.messages_seen++;
    this.resonance._lastMessageTime = Date.now();

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
      // v4.0: interleave quotes with perception synthesis and archetype awareness
      var roll = Math.random();
      if (roll < 0.2 && this.profile.archetype) {
        var arch = this.profile.archetype;
        this._show(arch + ' — ' + pick(CLOSERS), this.ambient.phaseColor, 'normal');
      } else if (roll < 0.35) {
        var perception = this.synthesizePerception();
        if (perception) {
          this._show(perception, this.ambient.phaseColor, 'italic');
        } else {
          this._show(this.getQuote(), '#8b949e', 'italic');
        }
      } else if (this.profile.clicks > 10 && roll < 0.5) {
        var rank = this.getRank();
        this._show(rank.name + ' — ' + pick(CLOSERS), rank.color, 'normal');
      } else {
        this._show(this.getQuote(), '#8b949e', 'italic');
      }
      this.resonance._messageCadence = 2400 + Math.random() * 800;
      this._timer = setTimeout(function(){self._tick()}, self.resonance._messageCadence);
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
  DeltaVerse.prototype.off = function(event, fn) {
    if (!this._callbacks[event]) return this;
    if (!fn) { this._callbacks[event] = []; return this; }
    this._callbacks[event] = this._callbacks[event].filter(function(f) { return f !== fn; });
    return this;
  };
  DeltaVerse.prototype.once = function(event, fn) {
    var self = this;
    function wrapper(data) { self.off(event, wrapper); fn(data); }
    return this.on(event, wrapper);
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

  DeltaVerse.prototype.getPerceptionState = function() {
    return {
      ambient: this.ambient,
      rhythm: {bpm: this.rhythm.bpm, regularity: this.rhythm.regularity},
      attention: {focusQuadrant: this.attention.focusQuadrant, driftSpeed: this.attention.driftSpeed},
      momentum: {sustained: this.momentum.sustained, building: this.momentum.building, direction: this.momentum.direction},
      pressure: {intensity: this.pressure.intensity, peak: this.pressure.peak},
      resonance: {alignment: this.resonance.alignment, streak: this.resonance.streak},
      wind: this.wind,
      depth: this.depth,
      idle: this.idle,
      hotspotCount: this.hotspots.length,
    };
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
        // Infinite space
        world_x: this.world.x, world_y: this.world.y, world_zoom: this.world.zoom,
        hotspots: this.hotspots.slice(0, 20),
        // v4.0 additions
        pages_seen: this.profile.pages_seen,
        archetype: this.profile.archetype,
        archetype_scores: this.profile.archetype_scores,
        streak_days: this.profile.streak_days,
        streak_last_day: this.profile.streak_last_day,
        peak_combo: this.profile.peak_combo,
        peak_bpm: this.profile.peak_bpm,
        peak_pressure: this.profile.peak_pressure,
        total_hotspots: this.profile.total_hotspots,
        swipe_dirs: this.profile.swipe_dirs,
        gestures_detected: this.profile.gestures_detected,
      }));
    } catch(e) {}
  };
  DeltaVerse.prototype._loadProfile = function() {
    try {
      var s = JSON.parse(localStorage.getItem('dv_profile') || '{}');
      if (s.xp) this.profile.xp = s.xp;
      if (s.achievements) this.profile.achievements = s.achievements;
      if (s.eggs_found) this.profile.eggs_found = s.eggs_found;
      if (s.total_clicks) this.profile.clicks = s.total_clicks; // restore click count
      if (s.total_distance) this.profile.total_distance = s.total_distance;
      if (s.peak_speed) this.profile.peak_speed = s.peak_speed;
      if (s.total_sessions) this.profile.total_sessions = s.total_sessions;
      if (s.depth_max) this.profile.depth_max = s.depth_max;
      if (s.circles_detected) this.profile.circles_detected = s.circles_detected;
      if (s.distort_total_time) this.profile.distort_total_time = s.distort_total_time;
      // Infinite space
      if (s.world_x !== undefined) this.world.x = s.world_x;
      if (s.world_y !== undefined) this.world.y = s.world_y;
      if (s.world_zoom) this.world.zoom = s.world_zoom;
      if (s.hotspots) this.hotspots = s.hotspots;
      // v4.0 additions
      if (s.pages_seen) this.profile.pages_seen = s.pages_seen;
      if (s.archetype) this.profile.archetype = s.archetype;
      if (s.archetype_scores) this.profile.archetype_scores = s.archetype_scores;
      if (s.streak_days) this.profile.streak_days = s.streak_days;
      if (s.streak_last_day) this.profile.streak_last_day = s.streak_last_day;
      if (s.peak_combo) this.profile.peak_combo = s.peak_combo;
      if (s.peak_bpm) this.profile.peak_bpm = s.peak_bpm;
      if (s.peak_pressure) this.profile.peak_pressure = s.peak_pressure;
      if (s.total_hotspots) this.profile.total_hotspots = s.total_hotspots;
      if (s.swipe_dirs) this.profile.swipe_dirs = s.swipe_dirs;
      if (s.gestures_detected) {
        for (var g in s.gestures_detected) this.profile.gestures_detected[g] = s.gestures_detected[g];
      }
      // Rebuild achievement map for O(1) lookups
      this._achievementMap = {};
      for (var i = 0; i < this.profile.achievements.length; i++) {
        this._achievementMap[this.profile.achievements[i]] = true;
      }
    } catch(e) {}
  };

  // ── Static ──

  DeltaVerse.SUBJECTS = SUBJECTS; DeltaVerse.VERBS = VERBS;
  DeltaVerse.OBJECTS = OBJECTS; DeltaVerse.CLOSERS = CLOSERS;
  DeltaVerse.QUOTES = QUOTES; DeltaVerse.EASTER_EGGS = EASTER_EGGS;
  DeltaVerse.OPS = OPS; DeltaVerse.RANKS = RANKS;
  DeltaVerse.ACHIEVEMENTS = ACHIEVEMENTS;
  DeltaVerse.ARCHETYPES = ARCHETYPES;
  DeltaVerse.PERCEPTIONS = PERCEPTIONS;
  DeltaVerse.TIME_PHASES = TIME_PHASES;
  DeltaVerse.VERSION = '4.1';

  // ── Export ──

  if (typeof module !== 'undefined' && module.exports) module.exports = DeltaVerse;
  else root.DeltaVerse = DeltaVerse;

})(typeof window !== 'undefined' ? window : this);
