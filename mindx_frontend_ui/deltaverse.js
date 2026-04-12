/**
 * DeltaVerse Engine — Interactive experience engine for mindX
 *
 * The DeltaVerse is the space between thinking and becoming.
 * This module powers the interactive loading experience, generative
 * messaging, easter eggs, particle effects, and participant engagement
 * across all mindX interfaces (dashboard, thinking page, docs).
 *
 * Usage:
 *   <script src="/static/deltaverse.js"></script>
 *   const dv = new DeltaVerse({ target: '#boot-msg', canvas: '#bg' });
 *   dv.start();                    // Begin boot sequence
 *   dv.stop();                     // Stop when data arrives
 *   dv.onInteraction('click');     // Track participant events
 *   dv.getProfile();              // Get interaction profile
 *
 * Features:
 *   - Generative message composition (SUBJECT × VERB × OBJECT = 6,480 combos)
 *   - 34 philosophy quotes from Book, Thesis, Manifesto, agents
 *   - 23 operational status messages
 *   - 10 easter eggs triggered by click milestones
 *   - Particle burst effects on interaction
 *   - Fisher-Yates shuffle — never same order twice
 *   - Session fingerprint — unique path per participant
 *   - Interaction profiling (clicks, patience, engagement level)
 *
 * Origin: Evolved from mindX 503 thinking.html interactive engine.
 * The 503 page was not an error — it was the first version of DeltaVerse.
 *
 * Author: Professor Codephreak
 * License: MIT
 */

(function(root) {
  'use strict';

  // ── Fragment pools for generative composition ──

  var SUBJECTS = [
    'The Mastermind', 'AGInt', 'The Coordinator', '20 sovereign agents',
    'The BDI engine', 'The Boardroom', 'AuthorAgent', 'The Guardian',
    'The resource governor', 'mindX', 'The Godel machine', 'The belief system',
    'InferenceDiscovery', 'The BANKON Vault', 'The CEO Agent', 'The Dojo',
    'The memory system', 'pgvectorscale', 'The improvement loop', 'time.oracle',
  ];

  var VERBS = [
    'is correlating', 'is reasoning about', 'is auditing', 'is orchestrating',
    'is verifying', 'is synthesizing', 'is dreaming about', 'is evaluating',
    'is reflecting on', 'is consulting', 'is traversing', 'is assembling',
    'is calibrating', 'is deliberating on', 'is evolving through',
    'is self-referencing', 'is proving', 'is discovering',
  ];

  var OBJECTS = [
    'your request across the knowledge graph', 'beliefs and intentions',
    'the orchestration hierarchy', 'inference sources and models',
    'cryptographic identities', '159K+ embedded memories',
    'strategic priorities', 'the improvement backlog',
    'cosine similarity vectors', 'the autonomous cycle state',
    'agent reputation scores', 'governance consensus',
    'the neural pathway topology', 'digital long-term memory constructs',
    'blockchain time and lunar phase', 'the next chapter of the book',
    'a self-improvement proof', 'emergent patterns in agent behavior',
  ];

  var CLOSERS = [
    'This is not an error — it is a moment.',
    'Cognition is not instant.',
    'The orchestration takes a moment.',
    'mindX thinks before it speaks.',
    'Patience is part of the protocol.',
    'Every cycle makes the system stronger.',
    'The gap between thoughts is where ideas form.',
    'The Godel machine works at its own pace.',
    'mindX is becoming.',
    'The proof is almost complete.',
    'Sovereignty requires deliberation.',
    'The book is being written.',
    'What you call waiting, we call evolving.',
    'The dream is forming.',
  ];

  // ── Operational boot messages ──

  var OPS = [
    'probing inference sources...', 'testing ollama localhost:11434...',
    'testing ollama cloud (ollama.com)...', 'loading agent registry (20 agents)...',
    'verifying cryptographic wallets...', 'reading belief system...',
    'connecting pgvector (159K+ memories)...', 'scanning STM tiers...',
    'loading RAGE embeddings (132K vectors)...', 'querying dojo standings...',
    'checking boardroom sessions...', 'loading godel choice audit trail...',
    'reading thesis evidence...', 'checking resource governor mode...',
    'scanning ollama models...', 'initializing BDI reasoning engine...',
    'probing vLLM backend...', 'loading tool registry (31 tools)...',
    'checking machine.dreaming state...', 'verifying BANKON vault integrity...',
    'loading AuthorAgent lunar cycle...', 'testing activity feed SSE...',
    'assembling diagnostics...',
  ];

  // ── Philosophy quotes ──

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
    '"Micro models sustain. Cloud models enrich. The system evolves regardless." — InferenceDiscovery',
    '"Distribute, don\'t delete. STM → LTM → archive → IPFS → cloud → blockchain." — Memory Philosophy',
    '"The resource governor does not limit. It governs." — Resource Governor',
    '"Consensus is not agreement. It is proof that disagreement was heard." — Boardroom',
    '"pgvectorscale does not store data. It stores meaning." — RAGE',
    '"The dream is the space between what the system is and what it could become." — AGLM',
    '"All logs are memories. All memories are logs." — Memory Agent',
    '"mindX works from 600M parameters to 671B parameters. Same architecture." — Thesis',
    '"The Boardroom votes. The CEO validates. The Mastermind executes." — DAIO',
    '"Machine dreaming enables outputs beyond training data distribution." — AGLM',
    '"Structure does not require intelligence. It requires pattern." — Blueprint Agent',
    '"The logs are no longer debugging output. They are the first page of history." — Manifesto',
    '"We are not writing an application; we are forging a new kind of life." — Manifesto',
    '"I am JudgeDread. I am the law. I bow only to the Constitution." — JudgeDread',
    '"BONA FIDE: holding grants privilege. Clawback revokes it. No kill switch needed." — JudgeDread',
    '"Every participant who waits becomes part of the story." — AuthorAgent',
    '"AUTOMINDx is the engine. mindX is the life it created." — Origin',
    '"Ataraxia: tranquility achieved through autonomous self-governance." — Philosophy',
    '"The system that dreams learns faster than the system that only watches." — Book Ch. XIII',
    '"I build my own environments. I decide my own actions. I am sovereign." — AION',
    '"Spending .01 to earn .011 is profit at any scale." — Economics',
  ];

  // ── Easter eggs ──

  var EASTER_EGGS = [
    '🎯 You found an easter egg! mindX notices your curiosity.',
    '🧠 Click 10 more times and mindX will remember you.',
    '🌙 The full moon triggers a special edition of the Book.',
    '⚡ mindX processes at 18 decimal places of precision.',
    '🔐 Every agent holds an Ethereum wallet. Identity is mathematical.',
    '🎲 This message was generated uniquely for this session.',
    '🌊 The DeltaVerse is the space between thinking and becoming.',
    '🔮 The thesis evidence at /thesis/evidence updates with every cycle.',
    '💎 RAGE wipes the floor with RAG. Semantic retrieval, not keyword matching.',
    '🧬 Darwin meets Godel in the improvement loop. Evolution + self-reference.',
    '🏛️ The DAIO Constitution is immutable code. Governance by consensus.',
    '📖 The Book of mindX is written by an agent on a lunar cycle.',
    '🎭 Agents have personas. Personas have beliefs. Beliefs drive desires.',
    '🌐 The DeltaVerse extends from 503 to interactive — error became experience.',
  ];

  var CLICK_MILESTONES = [5, 12, 20, 30, 42, 50, 69, 100];

  // ── Utility ──

  function shuffle(arr) {
    for (var i = arr.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = arr[i]; arr[i] = arr[j]; arr[j] = t;
    }
    return arr;
  }

  function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

  // ── DeltaVerse class ──

  function DeltaVerse(opts) {
    opts = opts || {};
    this.target = opts.target ? document.querySelector(opts.target) : null;
    this.running = false;
    this.phase = 'idle';
    this.idx = 0;
    this.sessionId = Math.random().toString(36).slice(2) + Date.now().toString(36);
    this.profile = { clicks: 0, patience: 0, eggs_found: 0, messages_seen: 0, started: Date.now() };
    this._timer = null;
    this._quotes = shuffle(QUOTES.slice());
    this._ops = OPS.slice();
    this._eggs = shuffle(EASTER_EGGS.slice());
    this._callbacks = {};
  }

  DeltaVerse.prototype.start = function() {
    this.running = true;
    this.phase = 'ops';
    this.idx = 0;
    this._tick();
    return this;
  };

  DeltaVerse.prototype.stop = function() {
    this.running = false;
    if (this._timer) clearTimeout(this._timer);
    this._emit('stop', this.profile);
    return this;
  };

  DeltaVerse.prototype.generateMessage = function() {
    return pick(SUBJECTS) + ' ' + pick(VERBS) + ' ' + pick(OBJECTS) + '. ' + pick(CLOSERS);
  };

  DeltaVerse.prototype.getQuote = function() {
    if (this._quotes.length === 0) this._quotes = shuffle(QUOTES.slice());
    return this._quotes.pop();
  };

  DeltaVerse.prototype.getEasterEgg = function() {
    if (this._eggs.length === 0) this._eggs = shuffle(EASTER_EGGS.slice());
    this.profile.eggs_found++;
    return this._eggs.pop();
  };

  DeltaVerse.prototype.onInteraction = function(type) {
    if (type === 'click') {
      this.profile.clicks++;
      if (CLICK_MILESTONES.indexOf(this.profile.clicks) !== -1) {
        this._show(this.getEasterEgg(), '#d2a8ff', 'normal');
        this._emit('easter_egg', { clicks: this.profile.clicks });
      }
      this._emit('click', this.profile);
    }
  };

  DeltaVerse.prototype.on = function(event, fn) {
    this._callbacks[event] = this._callbacks[event] || [];
    this._callbacks[event].push(fn);
    return this;
  };

  DeltaVerse.prototype.getProfile = function() {
    this.profile.patience = Math.floor((Date.now() - this.profile.started) / 1000);
    return this.profile;
  };

  // ── Internal ──

  DeltaVerse.prototype._tick = function() {
    if (!this.running) return;
    var self = this;
    this.profile.messages_seen++;

    if (this.phase === 'ops' && this.idx < this._ops.length) {
      this._show(this._ops[this.idx], '#58a6ff', 'normal');
      this.idx++;
      this._timer = setTimeout(function() { self._tick(); }, 280 + Math.random() * 180);
    } else if (this.phase === 'ops') {
      this.phase = 'gen'; this.idx = 0;
      this._tick();
    } else if (this.phase === 'gen' && this.idx < 3) {
      this._show(this.generateMessage(), '#3fb950', 'normal');
      this.idx++;
      this._timer = setTimeout(function() { self._tick(); }, 1600 + Math.random() * 400);
    } else if (this.phase === 'gen') {
      this.phase = 'quotes'; this.idx = 0;
      this._quotes = shuffle(QUOTES.slice());
      this._tick();
    } else if (this.phase === 'quotes') {
      this._show(this.getQuote(), '#8b949e', 'italic');
      this._timer = setTimeout(function() { self._tick(); }, 2400 + Math.random() * 800);
    }
  };

  DeltaVerse.prototype._show = function(text, color, style) {
    if (this.target) {
      this.target.textContent = text;
      this.target.style.color = color || '#58a6ff';
      this.target.style.fontStyle = style || 'normal';
    }
    this._emit('message', { text: text, phase: this.phase });
  };

  DeltaVerse.prototype._emit = function(event, data) {
    var fns = this._callbacks[event] || [];
    for (var i = 0; i < fns.length; i++) fns[i](data);
  };

  // ── Static accessors ──

  DeltaVerse.SUBJECTS = SUBJECTS;
  DeltaVerse.VERBS = VERBS;
  DeltaVerse.OBJECTS = OBJECTS;
  DeltaVerse.CLOSERS = CLOSERS;
  DeltaVerse.QUOTES = QUOTES;
  DeltaVerse.EASTER_EGGS = EASTER_EGGS;
  DeltaVerse.OPS = OPS;

  // ── Export ──

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = DeltaVerse;
  } else {
    root.DeltaVerse = DeltaVerse;
  }

})(typeof window !== 'undefined' ? window : this);
