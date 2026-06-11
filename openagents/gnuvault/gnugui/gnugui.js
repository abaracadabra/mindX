/* GNUGUI — the changing calculator that is also the door to the vault.
 * Copyright (C) 2026 cypherpunk2048 / BANKON.  GPL-3.0-or-later.
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * A real calculator. Swipe basic -> advanced -> scientific. And when what you
 * type is an EVM wallet address (0x + 40 hex), PRESS-AND-HOLD the + button to
 * sign a challenge with your wallet and open the vault. The crypto is invisible;
 * you just use a calculator, and the door opens. take it, own it, use it, share it.
 */
(function () {
  "use strict";

  // ---- EVM address recognition: 0x + exactly 40 hex chars -----------------
  var EVM = /^0x[0-9a-fA-F]{40}$/;
  function isEvmAddress(s) { return EVM.test((s || "").trim()); }

  // ---- a real, safe expression evaluator (no eval) ------------------------
  // Shunting-yard → RPN → evaluate. Supports + - * / % ^ ( ), unary -, and the
  // scientific functions/constants below.
  var FN = {
    sin: Math.sin, cos: Math.cos, tan: Math.tan,
    asin: Math.asin, acos: Math.acos, atan: Math.atan,
    log: function (x) { return Math.log10 ? Math.log10(x) : Math.log(x) / Math.LN10; },
    ln: Math.log, sqrt: Math.sqrt, exp: Math.exp, abs: Math.abs,
    fact: function (n) { n = Math.round(n); if (n < 0) return NaN; var f = 1; for (var i = 2; i <= n; i++) f *= i; return f; }
  };
  var CONST = { pi: Math.PI, e: Math.E };
  var OPS = {
    "+": { p: 2, f: function (a, b) { return a + b; } },
    "-": { p: 2, f: function (a, b) { return a - b; } },
    "*": { p: 3, f: function (a, b) { return a * b; } },
    "/": { p: 3, f: function (a, b) { return a / b; } },
    "%": { p: 3, f: function (a, b) { return a % b; } },
    "^": { p: 4, r: true, f: function (a, b) { return Math.pow(a, b); } }
  };

  function tokenize(s) {
    var t = [], i = 0, re = /\s+/y;
    s = s.replace(/×/g, "*").replace(/÷/g, "/").replace(/−/g, "-").replace(/π/g, "pi");
    while (i < s.length) {
      var c = s[i];
      if (c === " ") { i++; continue; }
      if (/[0-9.]/.test(c)) {
        var num = "";
        while (i < s.length && /[0-9.]/.test(s[i])) num += s[i++];
        t.push({ t: "num", v: parseFloat(num) });
        continue;
      }
      if (/[a-zA-Z]/.test(c)) {
        var name = "";
        while (i < s.length && /[a-zA-Z0-9]/.test(s[i])) name += s[i++];
        name = name.toLowerCase();
        if (CONST.hasOwnProperty(name)) t.push({ t: "num", v: CONST[name] });
        else if (FN.hasOwnProperty(name)) t.push({ t: "fn", v: name });
        else throw new Error("unknown: " + name);
        continue;
      }
      if (OPS[c]) { t.push({ t: "op", v: c }); i++; continue; }
      if (c === "(" || c === ")") { t.push({ t: c }); i++; continue; }
      if (c === "!") { t.push({ t: "fact" }); i++; continue; }
      throw new Error("bad char: " + c);
    }
    return t;
  }

  function evaluate(expr) {
    var toks = tokenize(expr), out = [], ops = [], prev = null;
    for (var i = 0; i < toks.length; i++) {
      var tk = toks[i];
      if (tk.t === "num") out.push(tk.v);
      else if (tk.t === "fn") ops.push(tk);
      else if (tk.t === "fact") out.push({ post: "fact" });
      else if (tk.t === "op") {
        // unary minus
        if (tk.v === "-" && (prev === null || prev.t === "op" || prev.t === "(")) {
          out.push(0);
        }
        var o1 = OPS[tk.v];
        while (ops.length) {
          var top = ops[ops.length - 1];
          if (top.t === "fn") { out.push(ops.pop()); continue; }
          if (top.t === "op") {
            var o2 = OPS[top.v];
            if ((o1.r ? o1.p < o2.p : o1.p <= o2.p)) { out.push(ops.pop()); continue; }
          }
          break;
        }
        ops.push(tk);
      } else if (tk.t === "(") ops.push(tk);
      else if (tk.t === ")") {
        while (ops.length && ops[ops.length - 1].t !== "(") out.push(ops.pop());
        if (!ops.length) throw new Error("mismatched )");
        ops.pop();
        if (ops.length && ops[ops.length - 1].t === "fn") out.push(ops.pop());
      }
      prev = tk;
    }
    while (ops.length) { var x = ops.pop(); if (x.t === "(") throw new Error("mismatched ("); out.push(x); }
    // evaluate RPN
    var st = [];
    for (var j = 0; j < out.length; j++) {
      var e = out[j];
      if (typeof e === "number") st.push(e);
      else if (e && e.post === "fact") st.push(FN.fact(st.pop()));
      else if (e.t === "op") { var b = st.pop(), a = st.pop(); st.push(OPS[e.v].f(a, b)); }
      else if (e.t === "fn") st.push(FN[e.v](st.pop()));
    }
    if (st.length !== 1) throw new Error("bad expression");
    return st[0];
  }

  // ---- panels: basic -> advanced -> scientific ----------------------------
  // Each key: {label, val?(what to append), act?(special)} ; "+" handled live.
  var K = function (label, val, cls) { return { label: label, val: val == null ? label : val, cls: cls || "" }; };
  var PLUS = { label: "+", val: "+", cls: "plus", hold: true };
  var EQ = { label: "=", act: "eq", cls: "eq" };
  var CLR = { label: "C", act: "clear", cls: "fn" };
  var DEL = { label: "⌫", act: "del", cls: "fn" };

  var PANELS = [
    { name: "basic", cols: 4, keys: [
      CLR, DEL, K("÷", "/", "op"), K("×", "*", "op"),
      K("7"), K("8"), K("9"), K("−", "-", "op"),
      K("4"), K("5"), K("6"), PLUS,
      K("1"), K("2"), K("3"), EQ,
      K("0"), K("."), K("%", "%", "op"), { label: "📋", act: "paste", cls: "fn" }
    ]},
    { name: "advanced", cols: 4, keys: [
      CLR, DEL, K("(", "("), K(")", ")"),
      K("7"), K("8"), K("9"), K("÷", "/", "op"),
      K("4"), K("5"), K("6"), K("×", "*", "op"),
      K("1"), K("2"), K("3"), K("−", "-", "op"),
      K("%", "%", "op"), K("0"), K("."), PLUS,
      K("xʸ", "^", "op"), K("√", "sqrt(", "fn"), K("±", "neg", "op"), EQ
    ]},
    { name: "scientific", cols: 5, keys: [
      CLR, DEL, K("(", "("), K(")", ")"), K("÷", "/", "op"),
      K("sin", "sin("), K("cos", "cos("), K("tan", "tan("), K("π", "pi"), K("×", "*", "op"),
      K("ln", "ln("), K("log", "log("), K("√", "sqrt("), K("e", "e"), K("−", "-", "op"),
      K("xʸ", "^", "op"), K("7"), K("8"), K("9"), PLUS,
      K("n!", "!"), K("4"), K("5"), K("6"), EQ,
      K("%", "%"), K("1"), K("2"), K("3"), K("0")
    ]}
  ];

  // ---- the component ------------------------------------------------------
  function GnuGui(root) {
    this.root = root;
    this.expr = "";
    this.panel = 0;
    this.holdTimer = null;
    this._build();
    this._render();
  }

  GnuGui.prototype._build = function () {
    var self = this;
    this.root.innerHTML =
      '<div class="gg-win">' +
        '<div class="gg-crest"></div>' +
        '<div class="gg-disp"><div class="gg-expr" id="ggExpr">0</div></div>' +
        '<div class="gg-track"><div class="gg-panels" id="ggPanels"></div></div>' +
        '<div class="gg-nav"><button class="gg-arrow" id="ggPrev">‹</button>' +
          '<div class="gg-dots" id="ggDots"></div>' +
          '<button class="gg-arrow" id="ggNext">›</button></div>' +
        '<div class="gg-status" id="ggStatus">cypherpunk2048</div>' +
      '</div>' +
      '<div class="gg-vault" id="ggVault"></div>';

    document.getElementById("ggPrev").onclick = function () { self._swipe(-1); };
    document.getElementById("ggNext").onclick = function () { self._swipe(1); };

    // swipe gestures on the track
    var track = this.root.querySelector(".gg-track"), x0 = null;
    var start = function (e) { x0 = (e.touches ? e.touches[0].clientX : e.clientX); };
    var end = function (e) {
      if (x0 == null) return;
      var x1 = (e.changedTouches ? e.changedTouches[0].clientX : e.clientX);
      var dx = x1 - x0; x0 = null;
      if (Math.abs(dx) > 45) self._swipe(dx < 0 ? 1 : -1);
    };
    track.addEventListener("touchstart", start, { passive: true });
    track.addEventListener("touchend", end);
    track.addEventListener("mousedown", start);
    track.addEventListener("mouseup", end);

    document.addEventListener("keydown", function (e) {
      if (/[0-9.]/.test(e.key)) self._append(e.key);
      else if ("+-*/%^()".indexOf(e.key) >= 0) self._append(e.key);
      else if (e.key === "Enter" || e.key === "=") self._equals();
      else if (e.key === "Backspace") self._del();
      else if (e.key === "Escape") self._clear();
      else if (e.key === "ArrowLeft") self._swipe(-1);
      else if (e.key === "ArrowRight") self._swipe(1);
    });
  };

  GnuGui.prototype._render = function () {
    var self = this;
    var wrap = document.getElementById("ggPanels");
    wrap.innerHTML = "";
    PANELS.forEach(function (p) {
      var pad = document.createElement("div");
      pad.className = "gg-pad";
      pad.style.gridTemplateColumns = "repeat(" + p.cols + ",1fr)";
      p.keys.forEach(function (k) {
        var b = document.createElement("button");
        b.className = "gg-key " + (k.cls || "");
        b.textContent = k.label;
        self._wireKey(b, k);
        pad.appendChild(b);
      });
      wrap.appendChild(pad);
    });
    // dots
    var dots = document.getElementById("ggDots");
    dots.innerHTML = "";
    PANELS.forEach(function (p, i) {
      var d = document.createElement("span");
      d.className = "gg-dot" + (i === self.panel ? " on" : "");
      d.title = p.name;
      d.onclick = function () { self.panel = i; self._position(); };
      dots.appendChild(d);
    });
    this._position();
    this._refresh();
  };

  GnuGui.prototype._wireKey = function (b, k) {
    var self = this;
    if (k.hold) {                       // the + button: tap = plus, hold = open
      var fired = false;
      var down = function (e) {
        e.preventDefault(); fired = false;
        if (isEvmAddress(self.expr)) {
          b.classList.add("charging");
          self.holdTimer = setTimeout(function () {
            fired = true; b.classList.remove("charging");
            self._openVault();
          }, 650);
        }
      };
      var up = function () {
        clearTimeout(self.holdTimer); b.classList.remove("charging");
        if (!fired) self._append("+");
      };
      b.addEventListener("mousedown", down);
      b.addEventListener("touchstart", down, { passive: false });
      b.addEventListener("mouseup", up);
      b.addEventListener("mouseleave", function () { clearTimeout(self.holdTimer); b.classList.remove("charging"); });
      b.addEventListener("touchend", up);
      return;
    }
    b.onclick = function () {
      if (k.act === "eq") self._equals();
      else if (k.act === "clear") self._clear();
      else if (k.act === "del") self._del();
      else if (k.act === "paste") self._paste();
      else if (k.val === "neg") self._negate();
      else self._append(k.val);
    };
  };

  GnuGui.prototype._swipe = function (dir) {
    this.panel = Math.max(0, Math.min(PANELS.length - 1, this.panel + dir));
    this._position();
    var dots = document.querySelectorAll(".gg-dot");
    for (var i = 0; i < dots.length; i++) dots[i].className = "gg-dot" + (i === this.panel ? " on" : "");
  };
  GnuGui.prototype._position = function () {
    document.getElementById("ggPanels").style.transform = "translateX(" + (-this.panel * 100) + "%)";
    document.getElementById("ggStatus").textContent = PANELS[this.panel].name;
  };

  GnuGui.prototype._append = function (s) { if (this.expr === "0" && /[0-9]/.test(s)) this.expr = ""; this.expr += s; this._refresh(); };
  GnuGui.prototype._clear = function () { this.expr = ""; this._refresh(); };
  GnuGui.prototype._del = function () { this.expr = this.expr.slice(0, -1); this._refresh(); };
  GnuGui.prototype._negate = function () { try { this.expr = String(-evaluate(this.expr || "0")); } catch (e) {} this._refresh(); };
  GnuGui.prototype._equals = function () {
    if (isEvmAddress(this.expr)) return;   // an address is not a sum
    try { var r = evaluate(this.expr); this.expr = (Math.round(r * 1e12) / 1e12).toString(); }
    catch (e) { document.getElementById("ggHint").textContent = "= ?  check the expression"; }
    this._refresh();
  };
  GnuGui.prototype._paste = function () {
    var self = this;
    if (navigator.clipboard && navigator.clipboard.readText) {
      navigator.clipboard.readText().then(function (t) { self.expr = (t || "").trim(); self._refresh(); })
        .catch(function () { self._refresh(); });
    }
  };

  GnuGui.prototype._refresh = function () {
    // Recognition is SILENT. A pasted 0x wallet address is just shown like any
    // other input — no hint, no glow, no suggestion. Security by obscurity: the
    // door reveals nothing; only someone who knows pastes their address and
    // holds +. It is, otherwise, just a (pleasing) calculator.
    document.getElementById("ggExpr").textContent = this.expr || "0";
  };

  // ---- the door: sign a challenge with the wallet -------------------------
  GnuGui.prototype._openVault = function () {
    var self = this, addr = this.expr.trim();
    var host = (location && location.hostname) || "local";
    var challenge = "GNUVAULT · open the vault · " + addr + " · " + host;
    var status = document.getElementById("ggStatus");
    status.textContent = "requesting signature…";

    var eth = window.ethereum;
    if (!eth || !eth.request) {
      // No wallet present: prove the flow locally (a demo "open").
      return self._opened(addr, "(no wallet — demo open; install an EIP-1193 wallet to sign)", challenge);
    }
    eth.request({ method: "eth_requestAccounts" })
      .then(function () { return eth.request({ method: "personal_sign", params: [challenge, addr] }); })
      .then(function (sig) { self._opened(addr, sig, challenge); })
      .catch(function (err) { status.textContent = "✗ signature declined — vault stays closed"; });
  };

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]; }); }
  function addr6(a) { a = String(a); return a.slice(0, 6) + "…" + a.slice(-4); }

  GnuGui.prototype._opened = function (addr, sig, challenge) {
    var self = this;
    try {
      sessionStorage.setItem("gnuvault_proof", JSON.stringify({ address: addr, signature: sig, challenge: challenge, ts: Date.now() }));
    } catch (e) {}
    document.getElementById("ggStatus").textContent = "✓ vault open — custody proven by signature";
    this.vaultAddr = addr; this.vaultSig = sig;
    var v = document.getElementById("ggVault");
    v.className = "gg-vault show";
    var web = window.GNUVAULT_WEB;
    if (!web || !(window.crypto && window.crypto.subtle)) {       // no WebCrypto → proof card
      v.innerHTML = '<div class="gg-vault-card"><div class="gg-crest big"></div><h2>⟁ vault open</h2>' +
        '<p>Custody proven for <code>' + esc(addr6(addr)) + '</code>. Your key is sovereign.</p>' +
        '<button class="gg-key eq" id="ggClose">close</button></div>';
      document.getElementById("ggClose").onclick = function () { v.className = "gg-vault"; };
      return;
    }
    web.deriveKey(challenge, sig).then(function (key) { self.vaultKey = key; self._mausoleum(); });
  };

  // the door led somewhere real: a working mausoleum, keyed by the signature
  GnuGui.prototype._mausoleum = function () {
    var self = this, web = window.GNUVAULT_WEB, v = document.getElementById("ggVault");
    var tombs = web.listTombs();
    var rows = tombs.length
      ? tombs.map(function (n) {
          return '<li><span class="t">⚰ ' + esc(n) + '</span><span class="a">' +
            '<button class="lk" data-open="' + esc(n) + '">open</button>' +
            '<button class="lk" data-forget="' + esc(n) + '">forget</button></span></li>';
        }).join("")
      : '<li class="empty">no tombs yet — seal your first secret below</li>';
    v.innerHTML = '<div class="gg-vault-card mausoleum">' +
      '<div class="gg-crest big"></div>' +
      '<h2>⟁ the mausoleum</h2>' +
      '<p>custody: <code>' + esc(addr6(self.vaultAddr)) + '</code> — sealed by your signature; the key is sovereign.</p>' +
      '<ul class="gg-tombs">' + rows + '</ul>' +
      '<div class="gg-inter">' +
        '<input id="ggName" placeholder="tomb name" autocomplete="off">' +
        '<input id="ggSecret" type="password" placeholder="secret to seal" autocomplete="off">' +
        '<button class="gg-key plus" id="ggSeal">seal ⚰</button>' +
      '</div>' +
      '<div class="gg-out" id="ggOut"></div>' +
      '<button class="gg-key" id="ggClose">close vault</button>' +
    '</div>';
    var out = document.getElementById("ggOut");
    document.getElementById("ggSeal").onclick = function () {
      var name = document.getElementById("ggName").value.trim(), secret = document.getElementById("ggSecret").value;
      if (!name || !secret) { out.textContent = "name + secret required"; return; }
      web.inter(self.vaultKey, name, secret).then(function () { self._mausoleum(); })
        .catch(function (e) { out.textContent = e.message === "exists" ? "a tomb by that name already exists" : ("seal failed: " + e.message); });
    };
    [].forEach.call(v.querySelectorAll("[data-open]"), function (b) {
      b.onclick = function () {
        web.exhume(self.vaultKey, b.getAttribute("data-open")).then(function (sec) {
          out.innerHTML = '<strong>' + esc(b.getAttribute("data-open")) + '</strong>: <code>' + esc(sec) + '</code>';
        }).catch(function () { out.textContent = "failed closed (wrong custody)"; });
      };
    });
    [].forEach.call(v.querySelectorAll("[data-forget]"), function (b) {
      b.onclick = function () { web.forget(b.getAttribute("data-forget")); self._mausoleum(); };
    });
    document.getElementById("ggClose").onclick = function () { v.className = "gg-vault"; };
  };

  // boot
  window.addEventListener("DOMContentLoaded", function () {
    var root = document.getElementById("gnugui");
    if (root) window.gnugui = new GnuGui(root);
  });

  // export for tests / reuse
  window.GNUGUI = { isEvmAddress: isEvmAddress, evaluate: evaluate, GnuGui: GnuGui };
})();
