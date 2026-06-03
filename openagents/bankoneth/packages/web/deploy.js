// SPDX-License-Identifier: Apache-2.0
//
// deploy.js — the BANKON go-LIVE deployer engine. Pure client-side: reads the
// creation bytecode + ctor ABI from the generated manifest and broadcasts an
// ordered deploy sequence directly from the user's wallet (eth_sendTransaction
// with creation bytecode), threading each deployed address into later
// constructors. No backend, no API key. Two phases: arm() previews + predicts
// addresses/gas (no broadcast); launch() confirms the sequence on livenet.
import { ethers } from "./vendor/ethers.min.js";
import { CHAINS } from "./chains.js";

const ZERO = "0x0000000000000000000000000000000000000000";

export const Deployer = {
  injected: null, bp: null, signer: null, address: null, chainId: null,
  manifest: null, bytecodes: null, owner: null, plan: null,

  // ── config ────────────────────────────────────────────────────────────────
  async loadConfig(base = "./public") {
    const [m, b] = await Promise.all([
      fetch(`${base}/bankon.contracts.json`).then((r) => r.json()),
      fetch(`${base}/bankon.bytecodes.json`).then((r) => r.json()),
    ]);
    this.manifest = m; this.bytecodes = b;
    return m;
  },

  // ── wallet (EIP-6963 + legacy) ──────────────────────────────────────────────
  async _detect() {
    const found = [];
    const on = (e) => { if (!found.some((w) => w.uuid === e.detail.info.uuid)) found.push({ id: (e.detail.info.rdns || e.detail.info.name || "").toLowerCase(), provider: e.detail.provider, uuid: e.detail.info.uuid }); };
    window.addEventListener("eip6963:announceProvider", on);
    window.dispatchEvent(new Event("eip6963:requestProvider"));
    await new Promise((r) => setTimeout(r, 320));
    window.removeEventListener("eip6963:announceProvider", on);
    if (found.length) return (found.find((w) => w.id.includes("metamask")) || found[0]).provider;
    return window.ethereum || null;
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
    return this.address;
  },
  async switchChain(id) {
    const hex = "0x" + Number(id).toString(16);
    try {
      await this.injected.request({ method: "wallet_switchEthereumChain", params: [{ chainId: hex }] });
    } catch (e) {
      if (e.code === 4902) {
        const c = CHAINS[id];
        await this.injected.request({ method: "wallet_addEthereumChain", params: [{
          chainId: hex, chainName: c.name, nativeCurrency: { name: c.nativeSymbol, symbol: c.nativeSymbol, decimals: 18 },
          rpcUrls: [c.rpc], blockExplorerUrls: [c.explorer],
        }] });
      } else if (e.code !== 4001) throw e;
    }
    this.chainId = parseInt(await this.injected.request({ method: "eth_chainId" }), 16);
    this.signer = await this.bp.getSigner();
    return this.chainId;
  },

  // ── owner = bankon.eth (resolve via mainnet ENS, fall back to manifest) ──────
  async resolveOwner() {
    const fallback = this.manifest?.deploy?.treasuryOwner;
    try {
      const eth = new ethers.JsonRpcProvider(CHAINS[1].rpc);
      const a = await eth.resolveName("bankon.eth");
      this.owner = a && a !== ZERO ? ethers.getAddress(a) : fallback;
    } catch { this.owner = fallback; }
    return this.owner;
  },

  // ── argument resolution ─────────────────────────────────────────────────────
  _chainParam(key) {
    const p = this.manifest?.deploy?.chainParams?.[this.chainId] || {};
    return p[key] ?? ZERO;
  },
  _coerce(type, value) {
    if (type.endsWith("[]")) return typeof value === "string" ? JSON.parse(value) : value;
    if (type.startsWith("uint") || type.startsWith("int")) return BigInt(value);
    if (type === "bool") return value === true || value === "true";
    return value; // address, string, bytes, bytes32
  },
  _resolveArg(spec, ctorInput, ctx) {
    let raw;
    if (spec.owner) raw = this.owner;
    else if (spec.ref) { raw = ctx.deployed[spec.ref]; if (!raw) raw = ctx.predicted[spec.ref] || ZERO; }
    else if (spec.chain) raw = this._chainParam(spec.chain);
    else raw = spec.literal;
    return this._coerce(ctorInput.type, raw);
  },

  // Steps applicable to the active chain (a step may pin itself to `chains:[...]`).
  _stepsFor(seq) {
    return seq.steps.filter((s) => !s.chains || s.chains.includes(this.chainId));
  },

  abiFor(name) {
    const c = this.manifest.contracts.find((x) => x.name === name);
    return c ? fetch(`./public/${c.abi}`).then((r) => r.json()) : Promise.resolve([]);
  },

  // ── ARM: build the plan, predict addresses + gas. No broadcast. ─────────────
  async arm(sequenceId) {
    if (!this.owner) await this.resolveOwner();
    const seq = this.manifest.deploy.sequences.find((s) => s.id === sequenceId);
    if (!seq) throw new Error(`unknown sequence ${sequenceId}`);
    const steps = this._stepsFor(seq);
    const coder = ethers.AbiCoder.defaultAbiCoder();
    let nonce = await this.bp.getTransactionCount(this.address);
    const ctx = { deployed: {}, predicted: {} };
    const items = [];

    for (const step of steps) {
      const abi = await this.abiFor(step.contract);
      const ctor = abi.find((x) => x.type === "constructor") || { inputs: [] };
      const inputs = ctor.inputs || [];
      const args = (step.args || []).map((sp, i) => this._resolveArg(sp, inputs[i] || { type: "address" }, ctx));
      const encoded = inputs.length ? coder.encode(inputs.map((x) => x.type), args) : "0x";
      const bytecode = this.bytecodes[step.contract];
      if (!bytecode || bytecode.length <= 2) throw new Error(`no bytecode for ${step.contract}`);
      const data = bytecode + encoded.slice(2);
      const predicted = ethers.getCreateAddress({ from: this.address, nonce });
      ctx.predicted[step.contract] = predicted;

      let gas = null;
      try { gas = await this.bp.estimateGas({ from: this.address, data }); } catch { /* dep not live yet */ }
      items.push({ contract: step.contract, inputs, args, data, predicted, gas, note: step.note });
      nonce += 1;
    }

    // post-deploy wiring (e.g. setMinter), addresses threaded from predicted.
    const wires = (seq.wire || []).map((w) => ({
      contract: w.contract, fn: w.fn,
      args: w.args.map((sp) => (sp.ref ? ctx.predicted[sp.ref] : sp.owner ? this.owner : sp.literal)),
    }));

    this.plan = { sequenceId, seq, items, wires, owner: this.owner, chainId: this.chainId };
    return this.plan;
  },

  // ── LAUNCH: broadcast the armed sequence, threading real addresses. ─────────
  async launch(onStep) {
    if (!this.plan) throw new Error("nothing armed");
    const coder = ethers.AbiCoder.defaultAbiCoder();
    const deployed = {};
    const results = [];

    for (let i = 0; i < this.plan.items.length; i++) {
      const it = this.plan.items[i];
      onStep?.({ phase: "send", index: i, contract: it.contract });
      // re-encode with any now-known real addresses (refs deployed earlier this run)
      const abi = await this.abiFor(it.contract);
      const ctor = abi.find((x) => x.type === "constructor") || { inputs: [] };
      const inputs = ctor.inputs || [];
      const seqStep = this.plan.seq.steps.find((s) => s.contract === it.contract);
      const args = (seqStep.args || []).map((sp, k) => {
        if (sp.ref && deployed[sp.ref]) return this._coerce(inputs[k].type, deployed[sp.ref]);
        return it.args[k];
      });
      const data = this.bytecodes[it.contract] + (inputs.length ? coder.encode(inputs.map((x) => x.type), args).slice(2) : "");
      const tx = await this.signer.sendTransaction({ data });
      onStep?.({ phase: "pending", index: i, contract: it.contract, hash: tx.hash });
      const rcpt = await tx.wait();
      deployed[it.contract] = rcpt.contractAddress;
      const r = { contract: it.contract, address: rcpt.contractAddress, hash: tx.hash, gasUsed: rcpt.gasUsed?.toString(), block: rcpt.blockNumber };
      results.push(r);
      onStep?.({ phase: "confirmed", index: i, ...r });
    }

    // wiring calls
    for (const w of this.plan.wires) {
      const target = deployed[w.contract];
      if (!target) continue;
      const abi = await this.abiFor(w.contract);
      const iface = new ethers.Interface(abi);
      const args = w.args.map((a) => (a && a.ref ? deployed[a.ref] : a));
      onStep?.({ phase: "wire", contract: w.contract, fn: w.fn });
      const tx = await this.signer.sendTransaction({ to: target, data: iface.encodeFunctionData(w.fn, args) });
      await tx.wait();
      onStep?.({ phase: "wired", contract: w.contract, fn: w.fn, hash: tx.hash });
    }

    this.lastDeployed = deployed;
    return results;
  },
};

export { CHAINS };
