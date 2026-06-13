/*!
 * m4r2d2-drop.js — the DROP. Paste ONE <script> anywhere and a Music 4 Robots 2
 * Dance 2 player installs itself. Minimal as possible:
 *
 *   <script src=".../assets/m4r2d2-drop.js"
 *           data-album="music4robots2dance2" data-sticky="true" defer></script>
 *
 * It locates its own folder, loads m4r2d2-player.css + m4r2d2-player.js from
 * beside it (so it works from a CDN, the WP plugin, or the mindX app unchanged),
 * then injects the player. Autoplay needs a gesture, so by default it drops a
 * lazy facade — the play button IS the permission grant ("auto install from
 * permission"). Configure entirely from the script tag's data-* attributes.
 *
 * GPL-3.0 · take · own · use · share · github.com/gnugui
 */
(function () {
  "use strict";

  // Locate this script so we can load siblings from the same base URL.
  var self = document.currentScript;
  if (!self) {
    var ss = document.getElementsByTagName("script");
    for (var i = ss.length - 1; i >= 0; i--) {
      if (ss[i].src && /m4r2d2-drop\.js(\?|$)/.test(ss[i].src)) { self = ss[i]; break; }
    }
  }
  if (!self) return;
  var base = self.src.replace(/[^/]*$/, ""); // dir of the drop script (trailing /)

  function data(name, dflt) {
    var v = self.getAttribute("data-" + name);
    return v === null ? dflt : v;
  }
  function bool(name, dflt) {
    var v = self.getAttribute("data-" + name);
    if (v === null) return dflt;
    return v === "" || v === "true" || v === "1" || v === "yes";
  }

  var opts = {
    album: data("album", "music4robots2dance2"),
    url: data("url", null),
    playlist: data("playlist", null),
    track: data("track", null),
    target: data("target", null),       // CSS selector; default: appended to <body>
    theme: data("theme", "dark"),
    color: data("color", null),
    sticky: bool("sticky", true),
    controls: bool("controls", true),
    permission: data("permission", "ask"), // "ask" → facade gate; "granted" → autoplay
    story: data("story", null),            // null → core default (the rage article)
    title: data("title", null),
    artist: data("artist", null),
    height: data("height", null),
  };
  var autoload = bool("autoload", true);   // set data-autoload="false" to drop manually later

  // Inject stylesheet once.
  if (!document.querySelector('link[data-m4r2d2-css]')) {
    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = base + "m4r2d2-player.css";
    link.setAttribute("data-m4r2d2-css", "1");
    document.head.appendChild(link);
  }

  function fire() {
    if (!window.M4R2D2 || !window.M4R2D2.drop) return;
    if (autoload) window.M4R2D2.drop(opts);
    // Always make the configured drop reusable as an injective event:
    //   window.dispatchEvent(new CustomEvent("m4r2d2:drop"))  → uses these opts.
    window.__M4R2D2_DROP_OPTS = opts;
  }

  if (window.M4R2D2 && window.M4R2D2.drop) {
    fire();
  } else if (!document.querySelector('script[data-m4r2d2-core]')) {
    var s = document.createElement("script");
    s.src = base + "m4r2d2-player.js";
    s.setAttribute("data-m4r2d2-core", "1");
    s.onload = fire;
    document.head.appendChild(s);
  } else {
    // core is loading from another drop — wait for it
    var t = setInterval(function () {
      if (window.M4R2D2 && window.M4R2D2.drop) { clearInterval(t); fire(); }
    }, 50);
    setTimeout(function () { clearInterval(t); }, 10000);
  }
})();
