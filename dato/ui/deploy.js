// Copyright 2026 BANKON. All rights reserved. Apache-2.0.
// DeployBridge — the dato UI's handoff to the DeltaVerse OVERLORD deployer.
//
// The dato EVM contracts (DatoCore · DatoNamingRegistry · DatoMembership) are a
// registered suite ("dato") in DeltaVerse deploy/suites.json. This bridge lets the
// UI: (1) describe that suite, (2) detect whether it's deployed (from the
// deployer's live/contracts.json or an injected manifest), (3) HAND OFF to the
// deployer (pages/deploy.html) to DEPLOY→LAUNCH it, and (4) BIND the DatoClient to
// the deployed addresses so naming/data/commerce run on-chain.
//
// Host wiring (parsec-wallet / DeltaVerse) supplies:
//   deployerHandoff(suiteId)  — navigate to the in-app OVERLORD deployer view
//   onchainBackend(addresses) — a DatoClient backend bound to the deployed contracts
//                               (the host has the wallet/provider; dato defines the interface)
//   deploymentsSource         — url|object|fn returning the live deployments map

export const DATO_SUITE = {
  id: 'dato',
  layer: 'evm',
  pillar: 'cognition',
  owner: 'DAIO (overlord)',
  // deploy order mirrors DeltaVerse deploy/suites.json → suite "dato"
  contracts: [
    { name: 'DatoCore', ctor: 'daioOwner, deployerWallet, name, Settings{tier,joinFee,openJoin,maxMembers}', role: 'the data-DAO; owner = DAIO' },
    { name: 'DatoNamingRegistry', ctor: 'daioOwner', role: 'tiered <handle>.<tier>.<root> names; extensible roots' },
    { name: 'DatoMembership', ctor: 'datoCore, joinFeeWei', role: 'request-to-join with fee (then DatoCore.transferOwnership → this)' },
  ],
};

export class DeployBridge {
  constructor(opts = {}) {
    this.deployerUrl = opts.deployerUrl || null;        // absolute URL to DeltaVerse pages/deploy.html
    this.deployerHandoff = opts.deployerHandoff || null; // in-app navigate(suiteId)
    this.deploymentsSource = opts.deploymentsSource || '/live/contracts.json';
    this.onchainBackend = opts.onchainBackend || null;  // (addresses) => DatoClient backend
    this._addresses = null;
  }

  /** Load the live deployments map and extract the dato contract addresses. */
  async loadDeployments() {
    // 1) explicit injection
    if (typeof window !== 'undefined' && window.__DATO_DEPLOYMENTS__) {
      return (this._addresses = this._pick(window.__DATO_DEPLOYMENTS__));
    }
    const src = this.deploymentsSource;
    let data = null;
    try {
      if (typeof src === 'function') data = await src();
      else if (src && typeof src === 'object') data = src;
      else if (typeof src === 'string') data = await (await fetch(src)).json();
    } catch { data = null; }
    return (this._addresses = this._pick(data));
  }

  // Accept either {DatoCore:'0x…'} or the DeltaVerse live/contracts.json shapes.
  _pick(data) {
    if (!data) return {};
    const direct = ['DatoCore', 'DatoNamingRegistry', 'DatoMembership'];
    if (direct.some((k) => data[k])) return Object.fromEntries(direct.map((k) => [k, data[k]?.address || data[k] || null]));
    const out = {};
    const list = Array.isArray(data) ? data : (data.contracts || []);
    const deployments = data.deployments || {};
    for (const k of direct) {
      out[k] = deployments[k]?.address
        || (list.find((c) => c.name === k)?.address)
        || null;
    }
    return out;
  }

  /** Per-contract deployment status. */
  async status() {
    const a = this._addresses || (await this.loadDeployments());
    return {
      suite: DATO_SUITE.id,
      contracts: DATO_SUITE.contracts.map((c) => ({ ...c, address: a[c.name] || null, deployed: !!a[c.name] })),
      deployed: DATO_SUITE.contracts.every((c) => !!a[c.name]),
      addresses: a,
    };
  }

  /** Hand off to the OVERLORD deployer to DEPLOY→LAUNCH the dato suite. */
  handoff() {
    if (this.deployerHandoff) return this.deployerHandoff(DATO_SUITE.id);   // in-app (parsec/DeltaVerse)
    const base = this.deployerUrl || 'https://deltaverse.pythai.net/pages/deploy.html';
    const url = base + (base.includes('#') ? '' : '#') + 'suite=' + DATO_SUITE.id;
    if (typeof window !== 'undefined') window.open(url, '_blank');
    return url;
  }

  /** Bind a DatoClient to the deployed contracts (host supplies the on-chain backend). */
  async bind(client) {
    const a = this._addresses || (await this.loadDeployments());
    if (!DATO_SUITE.contracts.every((c) => a[c.name])) throw new Error('dato suite not fully deployed yet');
    if (!this.onchainBackend) throw new Error('no onchainBackend wired (host must provide it; e.g. parsec-wallet ethers)');
    client.backend = this.onchainBackend(a);
    client.boundOnchain = a;
    return a;
  }
}
