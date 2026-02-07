/**
 * vault_manager.js — Signature-scoped vault folder access
 *
 * Concept: Only a valid signature (proved by a vault-backed session token) grants access.
 * Access is never to the whole vault: only to the folder that corresponds to the
 * public key (wallet address) that holds the signature. The backend maps session
 * → wallet and enforces that; this client only ever talks to "my folder" endpoints.
 *
 * Usage:
 *   - After login (MetaMask sign-in), the app stores mindx_session_token.
 *   - VaultManager uses that token on every request. No token → no access.
 *   - listKeys() / getKey(key) / setKey(key, value) / deleteKey(key) operate only
 *     on the folder for the current signer's public key. There is no API to access
 *     another wallet's folder or the whole vault.
 */

(function (global) {
  'use strict';

  var defaultApiBase = function () {
    if (typeof window !== 'undefined' && window.MINDX_API_URL) return window.MINDX_API_URL;
    var port = (typeof window !== 'undefined' && window.MINDX_BACKEND_PORT) ? window.MINDX_BACKEND_PORT : '8000';
    return 'http://localhost:' + port;
  };

  var getSessionToken = function () {
    if (typeof window === 'undefined' || !window.localStorage) return null;
    return window.localStorage.getItem('mindx_session_token');
  };

  function VaultManager(options) {
    options = options || {};
    this._apiBase = options.apiBase != null ? options.apiBase : defaultApiBase();
    this._getToken = options.getSessionToken || getSessionToken;
  }

  VaultManager.prototype.getApiBase = function () {
    return this._apiBase;
  };

  VaultManager.prototype.setApiBase = function (url) {
    this._apiBase = url;
  };

  VaultManager.prototype.getSessionToken = function () {
    return this._getToken();
  };

  /**
   * Set session token explicitly (e.g. after login). If not set, uses localStorage mindx_session_token.
   */
  VaultManager.prototype.setSessionToken = function (token) {
    this._getToken = function () { return token; };
  };

  VaultManager.prototype._request = function (method, path, body) {
    var token = this._getToken();
    if (!token) {
      return Promise.reject(new Error('No session token; sign in first. Only a valid signature grants vault folder access.'));
    }
    var url = this._apiBase.replace(/\/$/, '') + path;
    var opts = {
      method: method,
      headers: {
        'Content-Type': 'application/json',
        'X-Session-Token': token
      }
    };
    if (body !== undefined) opts.body = typeof body === 'string' ? body : JSON.stringify(body);
    return fetch(url, opts);
  };

  /**
   * List key names in the authenticated user's vault folder (folder = public key that holds the signature).
   * Returns [] if no keys or not authenticated.
   */
  VaultManager.prototype.listKeys = function () {
    var self = this;
    return this._request('GET', '/vault/user/keys')
      .then(function (res) {
        if (res.status === 401) return Promise.reject(new Error('Invalid or expired session; sign in again.'));
        if (!res.ok) return res.text().then(function (t) { return Promise.reject(new Error(t || res.statusText)); });
        return res.json();
      })
      .then(function (data) { return data.keys || []; });
  };

  /** Key must be 1–128 chars, alphanumeric plus _ . - (matches backend). */
  function isValidKey(key) {
    return typeof key === 'string' && key.length >= 1 && key.length <= 128 && /^[a-zA-Z0-9_.-]+$/.test(key);
  }

  /**
   * Get value for key in the authenticated user's vault folder only.
   */
  VaultManager.prototype.getKey = function (key) {
    if (!isValidKey(key)) return Promise.reject(new Error('Invalid key'));
    var self = this;
    return this._request('GET', '/vault/user/keys/' + encodeURIComponent(key))
      .then(function (res) {
        if (res.status === 401) return Promise.reject(new Error('Invalid or expired session; sign in again.'));
        if (res.status === 404) return Promise.resolve(null);
        if (!res.ok) return res.text().then(function (t) { return Promise.reject(new Error(t || res.statusText)); });
        return res.json();
      })
      .then(function (data) { return data.value; });
  };

  /**
   * Set value for key in the authenticated user's vault folder only. Value must be JSON-serializable.
   */
  VaultManager.prototype.setKey = function (key, value) {
    if (!isValidKey(key)) return Promise.reject(new Error('Invalid key'));
    var self = this;
    return this._request('PUT', '/vault/user/keys/' + encodeURIComponent(key), value)
      .then(function (res) {
        if (res.status === 401) return Promise.reject(new Error('Invalid or expired session; sign in again.'));
        if (!res.ok) return res.text().then(function (t) { return Promise.reject(new Error(t || res.statusText)); });
        return res.json();
      })
      .then(function (data) { return data.success; });
  };

  /**
   * Delete key in the authenticated user's vault folder only.
   */
  VaultManager.prototype.deleteKey = function (key) {
    if (!isValidKey(key)) return Promise.reject(new Error('Invalid key'));
    var self = this;
    return this._request('DELETE', '/vault/user/keys/' + encodeURIComponent(key))
      .then(function (res) {
        if (res.status === 401) return Promise.reject(new Error('Invalid or expired session; sign in again.'));
        if (!res.ok) return res.text().then(function (t) { return Promise.reject(new Error(t || res.statusText)); });
        return res.json();
      })
      .then(function (data) { return data.deleted; });
  };

  /**
   * Singleton for app use. Only exposes the folder for the current signer's public key; no whole-vault access.
   */
  var defaultInstance = null;
  VaultManager.getDefault = function () {
    if (!defaultInstance) defaultInstance = new VaultManager();
    return defaultInstance;
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = VaultManager;
  } else {
    global.VaultManager = VaultManager;
  }
})(typeof window !== 'undefined' ? window : this);
