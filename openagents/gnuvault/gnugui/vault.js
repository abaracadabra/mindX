/* GNUGUI — in-browser vault (WebCrypto). GPL-3.0-or-later.
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * The door (gnugui.js) proves custody with a wallet signature; this turns that
 * signature into a working vault, entirely client-side. Custody mirrors
 * GNUVAULT's WalletSignatureOverseer exactly:
 *
 *     key = AES-256-GCM( SHA-256( challenge || 0x00 || signature ) )
 *
 * Tombs are AES-256-GCM bundles {v, iv, ct} stored in localStorage. No server,
 * no key stored — sign again (deterministic wallets reproduce the signature) and
 * the same custody returns. take it, own it, use it, share it.
 */
(function () {
  "use strict";
  var g = (typeof window !== "undefined") ? window : self;
  var subtle = g.crypto && g.crypto.subtle;

  function enc(s) { return new TextEncoder().encode(s); }
  function dec(b) { return new TextDecoder().decode(b); }
  function b64(buf) { var a = new Uint8Array(buf), s = ""; for (var i = 0; i < a.length; i++) s += String.fromCharCode(a[i]); return g.btoa(s); }
  function ub64(str) { var s = g.atob(str), a = new Uint8Array(s.length); for (var i = 0; i < s.length; i++) a[i] = s.charCodeAt(i); return a; }
  function concat() { var t = 0, i, parts = arguments; for (i = 0; i < parts.length; i++) t += parts[i].length; var out = new Uint8Array(t), o = 0; for (i = 0; i < parts.length; i++) { out.set(parts[i], o); o += parts[i].length; } return out; }
  function hexToBytes(h) {
    h = (h || "").trim(); if (h.indexOf("0x") === 0) h = h.slice(2);
    if (!/^[0-9a-fA-F]*$/.test(h) || h.length % 2) return null;
    var a = new Uint8Array(h.length / 2); for (var i = 0; i < a.length; i++) a[i] = parseInt(h.substr(i * 2, 2), 16); return a;
  }

  // key material = SHA-256(challenge || 0x00 || signature-bytes)
  function deriveKey(challenge, signature) {
    var sig = hexToBytes(signature) || enc(signature);   // hex sig, or raw (demo)
    var material = concat(enc(challenge), new Uint8Array([0]), sig);
    return subtle.digest("SHA-256", material).then(function (hash) {
      return subtle.importKey("raw", hash, { name: "AES-GCM" }, false, ["encrypt", "decrypt"]);
    });
  }

  function seal(key, secret) {
    var iv = g.crypto.getRandomValues(new Uint8Array(12));
    return subtle.encrypt({ name: "AES-GCM", iv: iv }, key, enc(secret)).then(function (ct) {
      return { v: 1, cipher: "AES-256-GCM", iv: b64(iv), ct: b64(ct) };
    });
  }

  function open(key, bundle) {
    return subtle.decrypt({ name: "AES-GCM", iv: ub64(bundle.iv) }, key, ub64(bundle.ct))
      .then(function (pt) { return dec(pt); });
  }

  // ---- mausoleum: many named tombs in localStorage -----------------------
  var STORE = "gnuvault_tombs";
  function load() { try { return JSON.parse(g.localStorage.getItem(STORE) || "{}"); } catch (e) { return {}; } }
  function save(m) { g.localStorage.setItem(STORE, JSON.stringify(m)); }
  function listTombs() { return Object.keys(load()).sort(); }

  function inter(key, name, secret) {
    return seal(key, secret).then(function (b) { var m = load(); if (m[name]) throw new Error("exists"); m[name] = b; save(m); return name; });
  }
  function exhume(key, name) { var m = load(); if (!m[name]) return Promise.reject(new Error("no such tomb")); return open(key, m[name]); }
  function forget(name) { var m = load(); var had = !!m[name]; delete m[name]; save(m); return had; }

  g.GNUVAULT_WEB = {
    deriveKey: deriveKey, seal: seal, open: open,
    listTombs: listTombs, inter: inter, exhume: exhume, forget: forget
  };
})();
