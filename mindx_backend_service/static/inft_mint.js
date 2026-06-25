/* inft_mint.js — AgenticPlace iNFT mint, ready for post-contract inclusion.
 *
 * The IntelligentNFT contract is not yet deployed. This module is built so that
 * the moment its address (+ chainId + mintSelector) is dropped into
 * /static/agenticplace_deployments.json, minting goes live with NO code change.
 * Until then, mint() packages the prepared spec (including the archetype avatar)
 * and hands it to AgenticPlace — the surface that owns the deployed contract and
 * where wallet interactions are safe.
 *
 * No ethers / no CDN: a minimal in-house ABI encoder covers the known
 * mintIntelligent signature. The 4-byte selector is supplied by the config (read
 * from the compiled artifact at deploy time) so no in-browser keccak is needed.
 */
(function () {
  'use strict';
  var CFG = null, CFG_LOADED = false;

  // ── minimal ABI value encoder (hex, no 0x) ──────────────────────────────
  function hexPad(hex) { hex = hex.replace(/^0x/, ''); while (hex.length % 64) hex = '0' + hex; return hex; }
  function encUint(v) { var b = BigInt(v).toString(16); return hexPad(b); }
  function encAddress(a) { return hexPad((a || '0x0').toLowerCase().replace(/^0x/, '')); }
  function encBool(b) { return encUint(b ? 1 : 0); }
  function utf8Hex(s) {
    var out = '', bytes = new TextEncoder().encode(s == null ? '' : String(s));
    for (var i = 0; i < bytes.length; i++) out += bytes[i].toString(16).padStart(2, '0');
    return out;
  }
  function encString(s) {
    var data = utf8Hex(s), len = data.length / 2;
    var padded = data; while (padded.length % 64) padded += '0';
    return encUint(len) + padded; // length word + right-padded bytes
  }
  // Encode a tuple given typed members. Dynamic members (string) go to the tail
  // with their offset (relative to the tuple's own data) in the head.
  function encTuple(members) {
    var head = '', tail = '', headWords = members.length;
    var headLen = headWords * 32;
    members.forEach(function (m) {
      if (m.dyn) {
        head += encUint(headLen + tail.length / 2); // offset
        tail += m.enc;
      } else {
        head += m.enc;
      }
    });
    return head + tail;
  }

  // mintIntelligent(address to, NFTMetadata meta, IntelligenceConfig cfg)
  // NFTMetadata      = (string name,string description,string imageURI,string externalURI,string thotCID,bool isDynamic,uint256 lastUpdated)
  // IntelligenceConfig = (address agentAddress,bool autonomous,string behaviorCID,string thotCID,uint256 intelligenceLevel)
  function encodeMint(selector, to, meta, cfg) {
    var metaTuple = encTuple([
      { dyn: true, enc: encString(meta.name) },
      { dyn: true, enc: encString(meta.description) },
      { dyn: true, enc: encString(meta.imageURI) },
      { dyn: true, enc: encString(meta.externalURI || '') },
      { dyn: true, enc: encString(meta.thotCID || '') },
      { dyn: false, enc: encBool(meta.isDynamic !== false) },
      { dyn: false, enc: encUint(meta.lastUpdated || 0) }
    ]);
    var cfgTuple = encTuple([
      { dyn: false, enc: encAddress(cfg.agentAddress) },
      { dyn: false, enc: encBool(cfg.autonomous) },
      { dyn: true, enc: encString(cfg.behaviorCID || '') },
      { dyn: true, enc: encString(cfg.thotCID || '') },
      { dyn: false, enc: encUint(cfg.intelligenceLevel || 0) }
    ]);
    // Top level: [address to (static), meta (dynamic tuple), cfg (dynamic tuple)]
    var headLen = 3 * 32;
    var head = encAddress(to);
    var tail = '';
    head += encUint(headLen + tail.length / 2); tail += metaTuple;
    head += encUint(headLen + tail.length / 2); tail += cfgTuple;
    return '0x' + selector.replace(/^0x/, '') + head + tail;
  }

  // ── config ──────────────────────────────────────────────────────────────
  function load() {
    if (CFG_LOADED) return Promise.resolve(CFG);
    return fetch('/static/agenticplace_deployments.json', { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) { CFG = j; CFG_LOADED = true; return j; })
      .catch(function () { CFG_LOADED = true; return null; });
  }

  function inftContract() {
    try { return (((CFG || {}).agenticplace || {}).contracts || {}).IntelligentNFT || {}; }
    catch (e) { return {}; }
  }
  function ap() { return (CFG || {}).agenticplace || {}; }
  // The CREATE2 address is known (deterministic) even before mainnet signing.
  function hasPredictedAddress() { return !!inftContract().address; }
  function isDeployed() { return inftContract().deployed === true; }
  // "Live" = directly mintable from the simple form. The deployed contract is
  // ERC-7857 (mintAgent needs IPFS content/storage hashes) so the real path is
  // the AgenticPlace hand-off; direct mint is gated on mintMode 'direct'.
  function isLive() {
    var c = inftContract();
    return ap().mintMode === 'direct' && isDeployed() && !!(c.address && c.mintSelector && ap().chainId);
  }

  // ── public: mint (direct if live, else AgenticPlace hand-off) ────────────
  // spec: { to, meta:{name,description,imageURI,...}, cfg:{agentAddress,autonomous,behaviorCID,intelligenceLevel}, archetype }
  function mint(spec) {
    return load().then(function () {
      var ap = (CFG || {}).agenticplace || {}, c = inftContract();
      if (isLive() && window.ethereum) {
        var data = encodeMint(c.mintSelector, spec.to || spec.cfg.agentAddress, spec.meta, spec.cfg);
        return window.ethereum.request({ method: 'eth_chainId' }).then(function (chain) {
          if (chain !== ap.chainId) {
            return { mode: 'wrong_chain', need: ap.chainId, have: chain, data: data, to: c.address };
          }
          return window.ethereum.request({
            method: 'eth_sendTransaction',
            params: [{ to: c.address, from: spec.to || spec.cfg.agentAddress, data: data }]
          }).then(function (tx) { return { mode: 'minted', tx: tx, to: c.address }; });
        });
      }
      // Not deployed yet → hand the prepared spec to AgenticPlace.
      var url = ap.handoffMintUrl || 'https://agenticplace.pythai.net/inft';
      var q = new URLSearchParams({
        archetype: spec.archetype || '',
        name: spec.meta.name || '',
        level: String(spec.cfg.intelligenceLevel || ''),
        autonomous: String(!!spec.cfg.autonomous),
        image: spec.meta.imageURI || ''
      });
      return { mode: 'handoff', url: url + '?' + q.toString(),
               status: (CFG && CFG._status) || 'awaiting_contract_deployment' };
    });
  }

  window.inftMint = { load: load, mint: mint, isLive: isLive, encodeMint: encodeMint,
                      inftContract: inftContract, hasPredictedAddress: hasPredictedAddress,
                      isDeployed: isDeployed, status: function () { return (CFG || {})._status; } };
})();
