/*!
 * m4r2d2-player.js — Music 4 Robots 2 Dance 2 / SoundCloud pro player.
 * Framework-agnostic. Works two ways from ONE file:
 *   1. Webview / WordPress  → M4R2D2.enhance(root) upgrades server-rendered
 *      `.m4r2d2-embed` nodes (data-* attributes) with a control bar, lazy
 *      facade, and sticky dock.
 *   2. App / anywhere       → the <m4r2d2-player> custom element builds the
 *      whole player from attributes (album / url / playlist / track).
 *
 * Both paths drive the official SoundCloud Widget API
 * (https://w.soundcloud.com/player/api.js): play / pause / prev / next / seek /
 * volume / live time, plus events. No build step, no dependencies, GPL-3.0.
 *
 * take · own · use · share — github.com/gnugui
 */
(function (global) {
  "use strict";

  var PLAYER_BASE = "https://w.soundcloud.com/player/";
  var API_SRC = "https://w.soundcloud.com/player/api.js";

  // Known albums (mirror of agents/wordpress_agent/soundcloud.py KNOWN_PLAYLISTS).
  var ALBUMS = {
    takit: {
      playlist_id: "2249417369", color: "9d7833", visual: false,
      title: "takIT", set_url: "https://soundcloud.com/mag-magnus/sets/takit-1",
    },
    music4robots2dance2: {
      playlist_id: "2216206346", color: "ff5500", visual: true,
      title: "Music  4 Robots 2 Dance 2",
      set_url: "https://soundcloud.com/mag-magnus/sets/music-for-robots-to-dance-2",
    },
  };
  var ARTIST = { name: "Mag Magnus", url: "https://soundcloud.com/mag-magnus" };
  // The highlights: zero-config players point here (the album) and link the story.
  var ARTICLE_URL = "https://rage.pythai.net/take-it-own-it-codephreak/";
  var DEFAULT_ALBUM = "music4robots2dance2";

  // ── SoundCloud Widget API loader (promise-cached, loaded once) ───────────────
  var _apiPromise = null;
  function loadApi() {
    if (global.SC && global.SC.Widget) return Promise.resolve(global.SC);
    if (_apiPromise) return _apiPromise;
    _apiPromise = new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.src = API_SRC;
      s.async = true;
      s.onload = function () { resolve(global.SC); };
      s.onerror = function () { reject(new Error("failed to load SoundCloud Widget API")); };
      document.head.appendChild(s);
    });
    return _apiPromise;
  }

  // ── URL building (mirror of the python/php builders) ─────────────────────────
  function normColor(c) {
    c = (c || "ff5500").toString().trim().replace(/^#/, "").replace(/^%23/i, "");
    return c || "ff5500";
  }
  function resourceUrl(opts) {
    if (opts.url) return opts.url;
    if (opts.playlist) return "https://api.soundcloud.com/playlists/soundcloud:playlists:" + opts.playlist;
    if (opts.track) return "https://api.soundcloud.com/tracks/soundcloud:tracks:" + opts.track;
    return "";
  }
  function playerUrl(opts) {
    var res = resourceUrl(opts);
    var p =
      "url=" + encodeURI(res) +
      "&color=%23" + normColor(opts.color) +
      "&auto_play=" + (opts.autoPlay ? "true" : "false") +
      "&hide_related=" + (opts.hideRelated ? "true" : "false") +
      "&show_comments=" + (opts.showComments === false ? "false" : "true") +
      "&show_user=" + (opts.showUser === false ? "false" : "true") +
      "&show_reposts=false&show_teaser=true";
    if (opts.visual) p += "&visual=true";
    return PLAYER_BASE + "?" + p;
  }

  function fmtTime(ms) {
    if (!ms || ms < 0) ms = 0;
    var s = Math.floor(ms / 1000), m = Math.floor(s / 60);
    s = s % 60;
    return m + ":" + (s < 10 ? "0" : "") + s;
  }
  function el(tag, cls, attrs) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (attrs) Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    return e;
  }
  function svgIcon(name) {
    var paths = {
      play: "M8 5v14l11-7z",
      pause: "M6 5h4v14H6zM14 5h4v14h-4z",
      prev: "M6 6h2v12H6zm3.5 6l8.5 6V6z",
      next: "M16 6h2v12h-2zm-2 6L5.5 6v12z",
    };
    return '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">' +
      '<path fill="currentColor" d="' + paths[name] + '"/></svg>';
  }

  // ── Player: wraps one iframe with optional custom controls + sticky dock ──────
  function Player(container, options) {
    this.container = container;
    this.opts = options || {};
    this.widget = null;
    this.playing = false;
    this.duration = 0;
    this._seeking = false;
    this.iframe = null;
    this._bar = null;
  }

  Player.prototype.mount = function () {
    var o = this.opts;
    this.container.classList.add("m4r2d2");
    this.container.setAttribute("data-theme", o.theme === "light" ? "light" : "dark");
    if (o.lazy && !o.autoPlay) {
      this._renderFacade();
    } else {
      this._renderIframe(!!o.autoPlay);
    }
  };

  Player.prototype._facadeArtwork = function () {
    if (this.opts.artwork) return this.opts.artwork;
    return ""; // SoundCloud oEmbed thumbnail could be fetched; facade works without it.
  };

  Player.prototype._renderFacade = function () {
    var self = this, o = this.opts;
    var facade = el("button", "m4r2d2__facade", {
      type: "button",
      "aria-label": "Play " + (o.title || "track") + (o.artist ? " by " + o.artist : ""),
    });
    var art = this._facadeArtwork();
    if (art) facade.style.backgroundImage = "url('" + art + "')";
    facade.innerHTML =
      '<span class="m4r2d2__facade-play">' + svgIcon("play") + "</span>" +
      '<span class="m4r2d2__facade-meta"><strong>' + (o.title || "Listen") + "</strong>" +
      (o.artist ? "<span>" + o.artist + "</span>" : "") + "</span>";
    facade.addEventListener("click", function () {
      facade.classList.add("is-loading");
      self.container.removeChild(facade);
      self._renderIframe(true);
    });
    this.container.appendChild(facade);
  };

  Player.prototype._renderIframe = function (autoPlay) {
    var o = this.opts;
    var src = o.src || playerUrl({
      url: o.url, playlist: o.playlist, track: o.track,
      color: o.color, visual: o.visual, autoPlay: !!autoPlay,
      hideRelated: o.hideRelated, showComments: o.showComments, showUser: o.showUser,
    });
    var iframe = el("iframe", "m4r2d2__iframe", {
      width: "100%",
      height: String(o.height || (o.visual ? 300 : (o.mode === "compact" ? 166 : 450))),
      scrolling: "no",
      frameborder: "no",
      allow: "autoplay; encrypted-media",
      loading: "lazy",
      title: (o.title || "SoundCloud player") + (o.artist ? " — " + o.artist : ""),
      src: src,
    });
    this.iframe = iframe;
    this.container.appendChild(iframe);
    if (o.controls) this._renderControls();
    if (o.story) this._renderStory();
    this._initWidget();
  };

  Player.prototype._renderStory = function () {
    var o = this.opts;
    var foot = el("div", "m4r2d2__story");
    var a = el("a", null, { href: o.story, target: "_blank", rel: "noopener" });
    a.textContent = (o.storyLabel || "▶ the story") ;
    foot.appendChild(a);
    if (o.artist) {
      var by = el("span", "m4r2d2__by");
      by.innerHTML = " · <a href='" + ARTIST.url + "' target='_blank' rel='noopener'>" +
        (o.artist) + "</a>";
      foot.appendChild(by);
    }
    this.container.appendChild(foot);
  };

  Player.prototype._renderControls = function () {
    var self = this;
    var bar = el("div", "m4r2d2__bar", { role: "group", "aria-label": "Player controls" });
    bar.innerHTML =
      '<button class="m4r2d2__btn" data-act="prev" aria-label="Previous">' + svgIcon("prev") + "</button>" +
      '<button class="m4r2d2__btn m4r2d2__btn--play" data-act="toggle" aria-label="Play/pause">' + svgIcon("play") + "</button>" +
      '<button class="m4r2d2__btn" data-act="next" aria-label="Next">' + svgIcon("next") + "</button>" +
      '<span class="m4r2d2__time" data-role="cur">0:00</span>' +
      '<input class="m4r2d2__seek" type="range" min="0" max="1000" value="0" aria-label="Seek">' +
      '<span class="m4r2d2__time" data-role="dur">0:00</span>' +
      '<input class="m4r2d2__vol" type="range" min="0" max="100" value="100" aria-label="Volume">';
    bar.addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b) return;
      var act = b.getAttribute("data-act");
      if (act === "toggle") self.toggle();
      else if (act === "next") self.next();
      else if (act === "prev") self.prev();
    });
    var seek = bar.querySelector(".m4r2d2__seek");
    seek.addEventListener("input", function () { self._seeking = true; });
    seek.addEventListener("change", function () {
      if (self.duration) self.seekTo((seek.value / 1000) * self.duration);
      self._seeking = false;
    });
    bar.querySelector(".m4r2d2__vol").addEventListener("input", function (e) {
      self.setVolume(parseInt(e.target.value, 10));
    });
    this.container.appendChild(bar);
    this._bar = bar;
  };

  Player.prototype._initWidget = function () {
    var self = this, o = this.opts;
    loadApi().then(function (SC) {
      var w = SC.Widget(self.iframe);
      self.widget = w;
      var E = SC.Widget.Events;
      w.bind(E.READY, function () {
        w.getDuration(function (d) { self.duration = d; self._setText("dur", fmtTime(d)); });
        if (self.opts.controls) { /* bar already rendered */ }
        if (typeof o.onReady === "function") o.onReady(self);
      });
      w.bind(E.PLAY, function () {
        self.playing = true; self._setPlayIcon(true);
        if (o.sticky) self.container.classList.add("m4r2d2--sticky", "m4r2d2--stuck");
        if (typeof o.onPlay === "function") o.onPlay(self);
      });
      w.bind(E.PAUSE, function () { self.playing = false; self._setPlayIcon(false); });
      w.bind(E.FINISH, function () { self.playing = false; self._setPlayIcon(false); });
      w.bind(E.PLAY_PROGRESS, function (p) {
        if (self._seeking || !self.duration) return;
        var pct = (p.currentPosition / self.duration) * 1000;
        self._setSeek(pct); self._setText("cur", fmtTime(p.currentPosition));
      });
    }).catch(function () { /* API unavailable → native iframe still works */ });
  };

  Player.prototype._setText = function (role, txt) {
    if (!this._bar) return;
    var n = this._bar.querySelector('[data-role="' + role + '"]'); if (n) n.textContent = txt;
  };
  Player.prototype._setSeek = function (v) {
    if (!this._bar) return;
    var s = this._bar.querySelector(".m4r2d2__seek"); if (s) s.value = v;
  };
  Player.prototype._setPlayIcon = function (isPlaying) {
    if (!this._bar) return;
    var b = this._bar.querySelector(".m4r2d2__btn--play");
    if (b) b.innerHTML = svgIcon(isPlaying ? "pause" : "play");
  };

  // public control methods (usable from the app)
  Player.prototype.play = function () { this.widget && this.widget.play(); };
  Player.prototype.pause = function () { this.widget && this.widget.pause(); };
  Player.prototype.toggle = function () { this.widget && this.widget.toggle(); };
  Player.prototype.next = function () { this.widget && this.widget.next(); };
  Player.prototype.prev = function () { this.widget && this.widget.prev(); };
  Player.prototype.seekTo = function (ms) { this.widget && this.widget.seekTo(ms); };
  Player.prototype.setVolume = function (v) { this.widget && this.widget.setVolume(v); };

  // ── SSR enhancement (WordPress path) ─────────────────────────────────────────
  function boolAttr(node, name) {
    var v = node.getAttribute(name);
    return v === "" || v === "1" || v === "true" || v === "yes";
  }
  function enhance(root) {
    root = root || document;
    var nodes = root.querySelectorAll(".m4r2d2-embed[data-enhanced='1']:not([data-mounted])");
    Array.prototype.forEach.call(nodes, function (node) {
      node.setAttribute("data-mounted", "1");
      var existing = node.querySelector("iframe");
      var opts = {
        theme: node.getAttribute("data-theme") || "dark",
        controls: boolAttr(node, "data-controls"),
        sticky: boolAttr(node, "data-sticky"),
        lazy: boolAttr(node, "data-lazy"),
        title: node.getAttribute("data-title") || "",
        artist: node.getAttribute("data-artist") || "",
        artwork: node.getAttribute("data-artwork") || "",
        story: node.getAttribute("data-story") || "",
        storyLabel: node.getAttribute("data-story-label") || "",
        src: existing ? existing.getAttribute("src") : node.getAttribute("data-src"),
        height: existing ? existing.getAttribute("height") : node.getAttribute("data-height"),
        autoPlay: boolAttr(node, "data-autoplay"),
      };
      var p = new Player(node, opts);
      if (existing && !opts.lazy) {
        p.iframe = existing;
        if (opts.controls) p._renderControls();
        p._initWidget();
      } else {
        if (existing) node.removeChild(existing);
        p.mount();
      }
      node.__m4r2d2 = p;
    });
  }

  // ── Custom element (app path) ────────────────────────────────────────────────
  function defineElement() {
    if (!global.customElements || global.customElements.get("m4r2d2-player")) return;
    function attr(self, name, dflt) { var v = self.getAttribute(name); return v === null ? dflt : v; }
    function battr(self, name) { var v = self.getAttribute(name); return v === "" || v === "true" || v === "1" || v === "yes"; }

    class M4R2D2Player extends HTMLElement {
      connectedCallback() {
        if (this._mounted) return; this._mounted = true;
        var albumKey = attr(this, "album", null);
        var album = albumKey ? ALBUMS[albumKey] : null;
        var opts = {
          url: attr(this, "url", null),
          playlist: attr(this, "playlist", album ? album.playlist_id : null),
          track: attr(this, "track", null),
          color: attr(this, "color", album ? album.color : "ff5500"),
          visual: this.hasAttribute("visual") ? battr(this, "visual") : (album ? album.visual : false),
          theme: attr(this, "theme", "dark"),
          mode: attr(this, "mode", "playlist"),
          controls: this.hasAttribute("controls") ? battr(this, "controls") : true,
          lazy: battr(this, "lazy"),
          sticky: battr(this, "sticky"),
          autoPlay: battr(this, "auto-play"),
          height: attr(this, "height", null),
          title: attr(this, "title", album ? album.title : ""),
          artist: attr(this, "artist", ARTIST.name),
          artwork: attr(this, "artwork", ""),
          story: attr(this, "story", ARTICLE_URL),
          storyLabel: attr(this, "story-label", "▶ the story"),
        };
        // Zero-config element → play the highlights album with the story link.
        if (!opts.url && !opts.playlist && !opts.track) {
          var dflt = ALBUMS[DEFAULT_ALBUM];
          opts.playlist = dflt.playlist_id;
          if (!this.hasAttribute("color")) opts.color = dflt.color;
          if (!this.hasAttribute("visual")) opts.visual = dflt.visual;
          if (!opts.title) opts.title = dflt.title;
        }
        var mount = el("div", "m4r2d2-embed");
        this.appendChild(mount);
        this.player = new Player(mount, opts);
        this.player.mount();
      }
      // expose controls on the element itself
      play() { this.player && this.player.play(); }
      pause() { this.player && this.player.pause(); }
      toggle() { this.player && this.player.toggle(); }
      next() { this.player && this.player.next(); }
      prev() { this.player && this.player.prev(); }
    }
    global.customElements.define("m4r2d2-player", M4R2D2Player);
  }

  // ── DROP — auto-install via injective event ──────────────────────────────────
  // A "drop" injects a player into the page. Two ways to trigger it:
  //   • M4R2D2.drop(opts)                         (programmatic)
  //   • window.dispatchEvent(new CustomEvent(     (event-driven / "injective")
  //       "m4r2d2:drop", { detail: opts }))
  // Permission model: browsers forbid autoplay without a gesture, so a drop with
  // permission:"ask" (default) injects a lazy facade — the play button IS the
  // permission grant; clicking it auto-installs the iframe and plays. Set
  // permission:"granted" only after a real user gesture to auto-play immediately.
  function resolveAlbum(opts) {
    var a = opts.album ? ALBUMS[opts.album] : ALBUMS[DEFAULT_ALBUM];
    return {
      playlist: opts.playlist || (opts.url || opts.track ? null : a.playlist_id),
      url: opts.url || null, track: opts.track || null,
      color: opts.color || a.color, visual: opts.visual != null ? opts.visual : a.visual,
      title: opts.title || a.title,
    };
  }
  function drop(opts) {
    opts = opts || {};
    var host;
    if (opts.target) {
      host = typeof opts.target === "string" ? document.querySelector(opts.target) : opts.target;
    }
    if (!host) {
      host = el("div", "m4r2d2-drop");
      (document.body || document.documentElement).appendChild(host);
    }
    if (host.__m4r2d2) return host.__m4r2d2; // idempotent — don't double-drop a target
    var base = resolveAlbum(opts);
    var granted = opts.permission === "granted";
    var p = new Player(host, {
      playlist: base.playlist, url: base.url, track: base.track,
      color: base.color, visual: base.visual, title: base.title,
      artist: opts.artist || ARTIST.name,
      theme: opts.theme || "dark",
      controls: opts.controls !== false,
      sticky: opts.sticky != null ? opts.sticky : true,   // drops dock by default
      lazy: !granted,                                      // facade = permission gate
      autoPlay: granted,
      story: opts.story != null ? opts.story : ARTICLE_URL,
      storyLabel: opts.storyLabel || "▶ the story",
      height: opts.height,
    });
    p.mount();
    host.__m4r2d2 = p;
    return p;
  }

  // ── boot ─────────────────────────────────────────────────────────────────────
  var M4R2D2 = {
    Player: Player, enhance: enhance, loadApi: loadApi, playerUrl: playerUrl,
    drop: drop, ALBUMS: ALBUMS, ARTIST: ARTIST, ARTICLE_URL: ARTICLE_URL,
    DEFAULT_ALBUM: DEFAULT_ALBUM,
  };
  global.M4R2D2 = M4R2D2;
  defineElement();
  try { global.dispatchEvent(new CustomEvent("m4r2d2:ready")); } catch (e) { /* no CustomEvent */ }
  // injective event: anyone can dispatch m4r2d2:drop to inject a player.
  global.addEventListener("m4r2d2:drop", function (e) { drop((e && e.detail) || {}); });
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { enhance(document); });
  } else {
    enhance(document);
  }

  if (typeof module !== "undefined" && module.exports) module.exports = M4R2D2;
})(typeof window !== "undefined" ? window : this);
