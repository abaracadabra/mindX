// SPDX-License-Identifier: Apache-2.0
//
// dapp.js — interaction layer for the BANKON web3 dApp prototype.
//   • index.html  → connect wallet, then redirect to the dApp (security default: no
//     privileged surface is shown until a wallet is connected).
//   • dapp.html   → load any contract BY NAME or BY ADDRESS, with each contract's ABI
//     imported as its own module (abis/<name>.abi.js — "abi as stylesheet").
//   • ENS search  → resolve a *.eth name (or address) and inject the Etherscan/explorer
//     view for that address. Keyless by default (public RPC); uses an Etherscan API key
//     only if one is present in localStorage. Public UI is the default.
// Prototype is plain .js; the production port lives in .ts / .tsx (see PRODUCTION.md).
import { ethers } from "../vendor/ethers.min.js";
import { CHAINS } from "../chains.js";
import { CONTRACTS, byKey, loadAbi } from "./abis/index.js";

const ZERO = "0x0000000000000000000000000000000000000000";
const isAddr = (s) => typeof s === "string" && /^0x[0-9a-fA-F]{40}$/.test(s.trim());
export const short = (a) => (a ? a.slice(0, 7) + "…" + a.slice(-5) : "");

export const Dapp = {
  injected: null, bp: null, signer: null, address: null, chainId: null,
  deployments: null, manifest: null,

  // ── wallet (EIP-6963 + legacy) ──────────────────────────────────────────────
  async _detect() {
    const found = [];
    const on = (e) => { if (!found.some((w) => w.uuid === e.detail.info.uuid)) found.push({ id: (e.detail.info.rdns || "").toLowerCase(), provider: e.detail.provider, uuid: e.detail.info.uuid }); };
    window.addEventListener("eip6963:announceProvider", on);
    window.dispatchEvent(new Event("eip6963:requestProvider"));
    await new Promise((r) => setTimeout(r, 300));
    window.removeEventListener("eip6963:announceProvider", on);
    return found.length ? (found.find((w) => w.id.includes("metamask")) || found[0]).provider : (window.ethereum || null);
  },
  async connect() {
    this.injected = await this._detect();
    if (!this.injected) throw new Error("No EVM wallet found — install MetaMask.");
    const accts = await this.injected.request({ method: "eth_requestAccounts" });
    this.address = accts[0];
    this.chainId = parseInt(await this.injected.request({ method: "eth_chainId" }), 16);
    this.bp = new ethers.BrowserProvider(this.injected);
    this.signer = await this.bp.getSigner();
    this.injected.on?.("chainChanged", () => location.reload());
    this.injected.on?.("accountsChanged", () => location.reload());
    sessionStorage.setItem("bankon_connected", this.address);
    return this.address;
  },
  // security default: the landing page reveals nothing until a wallet connects.
  isLoggedIn() { return !!sessionStorage.getItem("bankon_connected"); },
  redirectToDapp() { location.href = "./dapp.html"; },
  // dApp/admin pages call this on load; bounce to the landing if not connected.
  guardOrRedirect() { if (!this.isLoggedIn()) { location.href = "./index.html"; return false; } return true; },

  // ── shared data (public mirror) ─────────────────────────────────────────────
  async loadData() {
    this.manifest = await fetch("../public/bankon.contracts.json").then((r) => r.json()).catch(() => null);
    this.localCount = 0;
    if (this.chainId) {
      const m = (this.manifest?.chains || []).find((c) => c.id === this.chainId);
      const file = m ? m.deployments : `deployments/${this.chainId}.json`;
      this.deployments = await fetch(`../public/${file}`).then((r) => r.json()).catch(() => null);
      this.deployments = this.deployments || { bankon: {} };
      this.deployments.bankon = this.deployments.bankon || {};
      // Merge addresses wired by the deployer this session (deploy.js persistDeployments) —
      // shared localStorage key `bankon.deploy.<chainId>` — so freshly-launched contracts
      // resolve by name without waiting for a committed deployments file.
      const local = JSON.parse(localStorage.getItem(`bankon.deploy.${this.chainId}`) || "{}");
      this.deployments.bankon = Object.assign({}, this.deployments.bankon, local);
      this.localCount = Object.keys(local).length;
    }
    return this.manifest;
  },

  // ── resolve a contract by NAME or ADDRESS → { name, address, abi } ───────────
  _addressOf(deploymentKey) {
    const b = this.deployments?.bankon || this.deployments || {};
    return b[deploymentKey] || null;
  },
  _nameForAddress(addr) {
    const b = this.deployments?.bankon || this.deployments || {};
    const a = addr.toLowerCase();
    for (const [key, val] of Object.entries(b)) if (String(val).toLowerCase() === a) return byKey[key]?.name || null;
    return null;
  },
  async resolveContract(query) {
    const q = (query || "").trim();
    if (isAddr(q)) {
      const name = this._nameForAddress(q);
      const abi = name ? await loadAbi(name) : null;            // unknown address → user can paste ABI
      return { name, address: q, abi, known: !!name };
    }
    const name = q;
    const meta = CONTRACTS.find((c) => c.name === name);
    if (!meta) throw new Error(`unknown contract name: ${name}`);
    const abi = await loadAbi(name);
    const address = this._addressOf(meta.deploymentKey);
    return { name, address, abi, known: true, deploymentKey: meta.deploymentKey };
  },

  contract(address, abi, signed = false) {
    return new ethers.Contract(address, abi, signed ? this.signer : this.bp);
  },
  async call(address, abi, fn, args, { value = 0n } = {}) {
    const fragment = abi.find((x) => x.type === "function" && x.name === fn);
    const readonly = fragment && (fragment.stateMutability === "view" || fragment.stateMutability === "pure");
    const c = this.contract(address, abi, !readonly);
    return readonly ? c[fn](...args) : c[fn](...args, value ? { value } : {});
  },

  // ── ENS search + Etherscan injection ────────────────────────────────────────
  // Resolve a *.eth name (or accept an address) and return a profile + explorer link.
  // Keyless by default; richer data only if an Etherscan key is stored.
  async lookup(query, chainId = this.chainId || 1) {
    const q = (query || "").trim();
    let address = q, ensName = null;
    if (q.toLowerCase().endsWith(".eth")) {
      ensName = q;
      const eth = new ethers.JsonRpcProvider(CHAINS[1].rpc);     // ENS resolves on L1
      address = await eth.resolveName(q);
      if (!address) throw new Error(`${q} does not resolve`);
    } else if (!isAddr(q)) {
      throw new Error("enter a *.eth name or a 0x address");
    }
    const p = new ethers.JsonRpcProvider(CHAINS[chainId]?.rpc || CHAINS[1].rpc);
    const [code, balance] = await Promise.all([p.getCode(address), p.getBalance(address)]);
    const profile = {
      query: q, ensName, address,
      isContract: code && code !== "0x",
      balance: ethers.formatEther(balance),
      symbol: CHAINS[chainId]?.nativeSymbol || "ETH",
      explorer: this.explorerUrl(chainId, address),
      contractName: this._nameForAddress(address),
    };
    const key = localStorage.getItem("etherscan_key");
    if (key) { try { profile.etherscan = await this._etherscan(chainId, address, key); } catch {} }
    return profile;
  },
  explorerUrl(chainId, address) { const e = CHAINS[chainId]?.explorer; return e ? `${e}/address/${address}` : null; },
  // optional Etherscan V2 multichain enrichment (only when a key is supplied).
  async _etherscan(chainId, address, key) {
    const base = "https://api.etherscan.io/v2/api";
    const txq = `${base}?chainid=${chainId}&module=account&action=txlist&address=${address}&page=1&offset=1&sort=desc&apikey=${key}`;
    const r = await fetch(txq, { signal: AbortSignal.timeout(4000) });
    const j = await r.json();
    return { lastTx: Array.isArray(j.result) && j.result[0] ? j.result[0].hash : null, status: j.status };
  },

  // ── RAKE quick-actions (the headline cp2048 contract) ───────────────────────
  async rakePending(address, asset) {
    const abi = await loadAbi("rake");
    return this.call(address, abi, "pendingValueUsd6", [asset]);
  },
  async rakeCollect(address, asset) {
    const abi = await loadAbi("rake");
    const c = this.contract(address, abi, true);
    return c.collect(asset);
  },
};

export { CHAINS, CONTRACTS };
