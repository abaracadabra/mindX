/*
 * deployer.js — client-side contract deployer (bundles · stages · chain isolation · ALL cycle).
 *
 * Framework-free; only the wallet's EIP-1193 provider in the trust path — NO external
 * script, NO keccak/ENS library. Flow:
 *   CHAIN   — pick an isolation target from chains.xml (0G, ETH, Base, ARC, testnets…),
 *             or ALL to run the launch cycle across every chain. The wallet is switched
 *             to each target before broadcasting (wallet_switchEthereumChain).
 *   DEPLOY  — arm one contract or a whole topic BUNDLE (records the selection).
 *   LAUNCH  — fire FROM VALUE: pay the deploy FEE to mindX/AgenticPlace, sign / pay value,
 *             broadcast each staged tx in order, then run the bundle's post-deploy <wire>
 *             calls. In ALL mode it repeats per chain with a per-chain address namespace.
 *   RETURN  — the txs the chain returns (hash, status, address).
 *
 * bankon.eth is the only admin: on Ethereum mainnet LAUNCH is gated to the wallet that
 * controls bankon.eth (NameWrapper owner), and every `from="owner"` arg + the deploy fee
 * resolve to bankon.eth. On testnets the gate relaxes to the connected wallet (rehearsal).
 *
 * CREATE2 (same address on every chain — the ERC-8004 singleton pattern): contracts the
 * bundle marks `create2="true"` are deployed through bankon_create2_deployer (Nick's
 * Factory wrapper) with a fixed salt; the deployed address is read from its
 * Deployed(address,bytes32) event, so the client never needs keccak.
 *
 * Build happens at fire time, so stage N's `from="deployed:<id>"` resolves to the address
 * stage N-1 just produced on THIS chain. Always open source · client-side.
 * (c) BANKON all rights preserved.
 */
(function () {
  "use strict";

  const ZERO = "0x0000000000000000000000000000000000000000";
  // Nick's Factory — the CREATE2 deployer-of-record (the wrapper CALLs it), so the
  // deterministic address is computed against THIS address, not the wrapper.
  const NICKS_FACTORY = "0x4e59b44847b379578588920cA78FbF26c0B4956C";
  // bankon_create2_deployer.deploy(bytes32,bytes) selector + Deployed(address,bytes32) topic0.
  const CREATE2_SELECTOR = "0xcdcb760a";
  const DEPLOYED_TOPIC   = "0x94bfd9af14ef450884c8a7ddb5734e2e1e14e70a1c84f0801cc5a29e34d26428";
  const CREATE2_HELPER_ARTIFACT = "../out/bankon_create2_deployer.sol/bankon_create2_deployer.json";
  // NameWrapper.ownerOf(uint256) — ERC-721 standard selector (used for the mainnet admin gate).
  const OWNEROF_SELECTOR = "0x6352211e";

  const S = {
    provider: null, account: null, chainIdHex: null, name: null,
    chains: [], chain: null, fee: null,
    contracts: [], bundles: {}, wires: {},        // wires[bundleName] = [{contract,fn,selector,args}]
    chainParams: null,                            // from chain-params.json
    adminActions: [],                             // from admin-actions.json (admin console)
    authority: null,                              // { relaxed, controller, recipient }
    create2Deployer: {},                          // chainId -> { addr }
    deployments: {},                              // chainId -> { id: address }
    armed: null,                                  // { kind:'single'|'bundle', id?|name?, label }
    deployed: {},                                 // id -> address (last chain in ALL mode)
  };

  const $ = (id) => document.getElementById(id);
  const log = (m, cls) => { const el = $("return"); if (!el) return; const l = document.createElement("div"); l.className = "rline " + (cls || ""); l.innerHTML = m; el.prepend(l); };
  const strip = (s) => (s || "").replace(/^0x/i, "");
  const short = (a) => (a ? a.slice(0, 6) + "…" + a.slice(-4) : "");
  const hex = (s) => "0x" + Array.from(new TextEncoder().encode(s)).map((b) => b.toString(16).padStart(2, "0")).join("");
  const utf8hex = (s) => Array.from(new TextEncoder().encode(s)).map((b) => b.toString(16).padStart(2, "0")).join("");
  const addrEq = (a, b) => (a || "").toLowerCase() === (b || "").toLowerCase();
  const chainLabel = () => (S.chain ? (S.chain.id === "all" ? "ALL chains" : S.chain.name) : "?");
  // explorer feedback (the "RETURN from blockchain" links the previous page had).
  const exTx = (h) => (S.chain && S.chain.explorer && h ? ` · <a href="${S.chain.explorer}/tx/${h}" target="_blank" rel="noopener">tx↗</a>` : "");
  const exAddr = (a) => (S.chain && S.chain.explorer && a ? ` · <a href="${S.chain.explorer}/address/${a}" target="_blank" rel="noopener">↗</a>` : "");

  /* ── identity + bankon.eth authority ────────────────────────────── */
  async function connect() {
    if (!window.ethereum) { log("No wallet found. Install a wallet (MetaMask).", "err"); return; }
    S.provider = window.ethereum;
    S.account = (await S.provider.request({ method: "eth_requestAccounts" }))[0];
    S.chainIdHex = await S.provider.request({ method: "eth_chainId" });
    S.provider.on && S.provider.on("accountsChanged", () => location.reload());
    S.provider.on && S.provider.on("chainChanged", (id) => { S.chainIdHex = id; resolveAuthority().then(() => { renderChains(); renderIdentity(); renderSolution(); }); });
    await resolveAuthority();
    renderIdentity(); renderChains(); renderSolution();
  }

  // Resolve who bankon.eth is for the active chain. Mainnet (1): admin + recipient are
  // bankon.eth, LAUNCH gated to the NameWrapper controller. Testnets: relaxed to the
  // connected wallet so rehearsal works.
  async function resolveAuthority() {
    const cp = S.chainParams || {};
    const cid = S.chainIdHex ? parseInt(S.chainIdHex, 16) : (S.chain && S.chain.chainId) || 0;
    if (cid === 1) {
      let controller = cp.controller || ZERO;
      try {
        const node = (cp.chains && cp.chains["1"] && cp.chains["1"].bankonNode) || cp.bankonNode;
        const nw = cp.chains && cp.chains["1"] && cp.chains["1"].nameWrapper;
        if (nw && node) {
          const res = await S.provider.request({ method: "eth_call", params: [{ to: nw, data: OWNEROF_SELECTOR + strip(node) }, "latest"] });
          if (res && res.length >= 66) controller = "0x" + res.slice(-40);
        }
      } catch (e) { /* keep pinned controller */ }
      S.authority = { relaxed: false, controller, recipient: cp.owner || ZERO };
    } else {
      S.authority = { relaxed: true, controller: S.account, recipient: S.account };
    }
    S.owner = S.authority.recipient;
  }
  function canDeploy() { return !!S.account && !!S.authority && (S.authority.relaxed || addrEq(S.account, S.authority.controller)); }

  /* ── chains (isolation + ALL) ───────────────────────────────────── */
  async function loadChains(url) {
    try {
      const doc = new DOMParser().parseFromString(await (await fetch(url || "chains.xml")).text(), "application/xml");
      S.chains = Array.from(doc.querySelectorAll("chain")).map((c) => ({
        id: c.getAttribute("id"), name: c.getAttribute("name"), chainId: parseInt(c.getAttribute("chainId"), 10),
        symbol: c.getAttribute("symbol"), rpc: c.getAttribute("rpc"), explorer: c.getAttribute("explorer"),
        marketRef: c.getAttribute("marketRef"), note: c.getAttribute("note"), mainnet: c.getAttribute("mainnet") === "true",
      }));
      const def = doc.documentElement.getAttribute("default");
      S.chain = S.chains.find((c) => c.id === def) || S.chains[0] || null;
      renderChains();
    } catch (e) { /* chains optional */ }
  }
  function selectChain(id) {
    S.chain = id === "all" ? { id: "all", name: "ALL chains", chainId: 0 } : (S.chains.find((c) => c.id === id) || S.chain);
    renderChains(); renderSolution();
  }

  async function ensureChain() {
    if (!S.chain || !S.chain.chainId) return true; // ARC / ALL placeholder → skip
    const want = "0x" + S.chain.chainId.toString(16);
    if ((await S.provider.request({ method: "eth_chainId" })).toLowerCase() === want.toLowerCase()) return true;
    try { await S.provider.request({ method: "wallet_switchEthereumChain", params: [{ chainId: want }] }); }
    catch (e) {
      if (e && e.code === 4902 && S.chain.rpc) {
        try { await S.provider.request({ method: "wallet_addEthereumChain", params: [{ chainId: want, chainName: S.chain.name, rpcUrls: [S.chain.rpc], nativeCurrency: { name: S.chain.symbol, symbol: S.chain.symbol, decimals: 18 }, blockExplorerUrls: S.chain.explorer ? [S.chain.explorer] : [] }] }); }
        catch (_) { log(`Switch your wallet to <b>${S.chain.name}</b> (id ${S.chain.chainId}) and retry.`, "warn"); return false; }
      } else { log(`Switch your wallet to <b>${S.chain.name}</b> (id ${S.chain.chainId}) and retry.`, "warn"); return false; }
    }
    S.chainIdHex = await S.provider.request({ method: "eth_chainId" });
    await resolveAuthority();
    return true;
  }
  // A contract/bundle may pin itself to specific chainIds (e.g. ENS → mainnet+Sepolia).
  function chainAllowed(ids) { return !ids || !ids.length || (S.chain && ids.includes(S.chain.chainId)); }

  /* ── solution (index.xml + includes) ────────────────────────────── */
  function parseContracts(doc) {
    return Array.from(doc.querySelectorAll("contract")).map((c) => ({
      id: c.getAttribute("id"), name: c.getAttribute("name"), summary: c.getAttribute("summary") || "",
      bundle: c.getAttribute("bundle") || null, stage: c.getAttribute("stage") ? parseInt(c.getAttribute("stage"), 10) : null,
      create2: c.getAttribute("create2") === "true", salt: c.getAttribute("salt") || null,
      chainIds: (c.getAttribute("chainIds") || "").split(",").map((x) => parseInt(x, 10)).filter(Boolean),
      abiSrc: c.querySelector("abi")?.getAttribute("src"), bytecodeSrc: c.querySelector("bytecode")?.getAttribute("src"),
      args: Array.from(c.querySelectorAll("constructor > arg")).map((a) => ({ name: a.getAttribute("name"), type: a.getAttribute("type"), from: a.getAttribute("from"), value: a.getAttribute("value") })),
      value: (() => { const v = c.querySelector("value"); return { kind: v?.getAttribute("kind") || "signature", asset: v?.getAttribute("asset"), amount: v?.getAttribute("amount") }; })(),
      privilege: (() => { const p = c.querySelector("privilege"); return p ? { service: p.getAttribute("service"), tier: p.getAttribute("tier") } : null; })(),
    }));
  }
  function parseWires(doc) {
    return Array.from(doc.querySelectorAll("wire > call")).map((c) => ({
      contract: c.getAttribute("contract"), fn: c.getAttribute("fn"), selector: c.getAttribute("selector"),
      args: Array.from(c.querySelectorAll("arg")).map((a) => ({ name: a.getAttribute("name"), type: a.getAttribute("type"), from: a.getAttribute("from"), value: a.getAttribute("value") })),
    }));
  }
  function deriveBundle(c) {
    if (c.bundle) return c.bundle;
    const m = /(?:\.\.\/)+([a-z0-9_-]+)\//i.exec(c.bytecodeSrc || "");
    return m ? m[1] : "core";
  }
  async function loadSolution(url) {
    try { S.chainParams = await (await fetch("chain-params.json")).json(); } catch (e) { S.chainParams = { chains: {} }; }
    try { S.adminActions = await (await fetch("admin-actions.json")).json(); } catch (e) { S.adminActions = []; }
    const doc = new DOMParser().parseFromString(await (await fetch(url || "index.xml")).text(), "application/xml");
    await loadChains(doc.querySelector("chains[src]")?.getAttribute("src") || "chains.xml");
    const f = doc.querySelector("fee");
    S.fee = f ? { recipient: f.getAttribute("recipient"), asset: f.getAttribute("asset"), amount: f.getAttribute("amount") || "0", service: f.getAttribute("service") || "deploy.bundle", x402: f.getAttribute("x402") || "" } : null;
    let contracts = parseContracts(doc);
    S.wires = {};
    for (const inc of Array.from(doc.querySelectorAll("include[src]")).map((i) => i.getAttribute("src"))) {
      try {
        const bdoc = new DOMParser().parseFromString(await (await fetch(inc)).text(), "application/xml");
        const bname = bdoc.documentElement.getAttribute("name");
        const bChainIds = (bdoc.documentElement.getAttribute("chainIds") || "").split(",").map((x) => parseInt(x, 10)).filter(Boolean);
        contracts = contracts.concat(parseContracts(bdoc).map((c) => ({ ...c, bundle: c.bundle || bname, bundleChainIds: bChainIds })));
        const w = parseWires(bdoc);
        if (w.length) S.wires[bname] = w;
      } catch (e) { log(`include failed: ${inc}`, "warn"); }
    }
    S.contracts = contracts;
    S.bundles = {};
    contracts.forEach((c, i) => { (S.bundles[deriveBundle(c)] = S.bundles[deriveBundle(c)] || []).push({ ...c, _i: i }); });
    Object.values(S.bundles).forEach((arr) => arr.sort((a, b) => (a.stage ?? a._i) - (b.stage ?? b._i)));
    renderSolution();
  }

  /* ── DEPLOY (arm — record selection; build at fire time) ─────────── */
  function deploy(id) { if (!guard()) return; const c = S.contracts.find((x) => x.id === id); if (!c) return; S.armed = { kind: "single", id, label: c.name }; log(`<b>DEPLOY armed</b> · <span class="hl">${c.name}</span> · target <b>${chainLabel()}</b> · press <b>LAUNCH</b>`, "ok"); renderSolution(); }
  function deployBundle(name) { if (!guard()) return; S.armed = { kind: "bundle", name, label: name }; log(`<b>DEPLOY armed</b> · bundle <span class="hl">${name}</span> · ${(S.bundles[name] || []).length} stages · target <b>${chainLabel()}</b> · press <b>LAUNCH</b>`, "ok"); renderSolution(); }

  /* ── ABI encoding (static + dynamic, dependency-free) ───────────── */
  function uint256Hex(n) { return BigInt(n).toString(16).padStart(64, "0"); }
  function isDynamic(t) { return t === "string" || t === "bytes" || t.endsWith("[]"); }
  // accept a JS array, a JSON string '["0x.."]', or a bare '[0x..,0x..]' / '[]'.
  function parseArrayLiteral(value) {
    if (Array.isArray(value)) return value;
    const s = (value == null ? "" : String(value)).trim();
    if (!s || s === "[]") return [];
    try { const j = JSON.parse(s); return Array.isArray(j) ? j : []; } catch (e) {}
    return s.replace(/^\[|\]$/g, "").split(",").map((x) => x.trim()).filter((x) => x.length);
  }
  function encodeStatic(type, value) {
    if (type === "address") return strip(value).toLowerCase().padStart(64, "0");
    if (/^u?int(\d*)$/.test(type)) return uint256Hex(value || 0);
    if (type === "bool") return (value === "true" || value === true ? "1" : "0").padStart(64, "0");
    if (/^bytes([1-9]|[12]\d|3[0-2])$/.test(type)) return strip(value).padEnd(64, "0");
    throw new Error(`unsupported static type '${type}'`);
  }
  function encodeBytesBlob(rawHex) {
    const len = rawHex.length / 2;
    const padded = rawHex.length ? rawHex.padEnd(Math.ceil(rawHex.length / 64) * 64, "0") : "";
    return uint256Hex(len) + padded;
  }
  function encodeDynamic(type, value) {
    if (type === "string") return encodeBytesBlob(utf8hex(value || ""));
    if (type === "bytes") return encodeBytesBlob(strip(value || "0x"));
    if (type.endsWith("[]")) {
      const base = type.slice(0, -2);
      let arr = parseArrayLiteral(value);
      if (isDynamic(base)) throw new Error(`arrays of dynamic type unsupported: ${type}`);
      return uint256Hex(arr.length) + arr.map((el) => encodeStatic(base, el)).join("");
    }
    throw new Error(`unsupported dynamic type '${type}'`);
  }
  // ABI-encode a tuple of (types, values) → hex string WITHOUT 0x.
  function encodeParams(types, values) {
    const headLen = 32 * types.length;
    const heads = [], tails = []; let dyn = headLen;
    for (let i = 0; i < types.length; i++) {
      const t = types[i], v = values[i];
      if (isDynamic(t)) { heads.push(uint256Hex(dyn)); const tail = encodeDynamic(t, v); tails.push(tail); dyn += tail.length / 2; }
      else heads.push(encodeStatic(t, v));
    }
    return heads.join("") + tails.join("");
  }

  /* ── LAUNCH (fire from value) ───────────────────────────────────── */
  async function fetchArtifact(c) {
    const art = await (await fetch(c.bytecodeSrc)).json();
    const bytecode = (art.bytecode && (art.bytecode.object || art.bytecode)) || art.deployedBytecode?.object;
    if (!bytecode || bytecode === "0x") throw new Error("no bytecode (forge build first)");
    return bytecode.startsWith("0x") ? bytecode : "0x" + bytecode;
  }
  async function buildInitCode(c, deployed) {
    const bytecode = await fetchArtifact(c);
    const enc = c.args.length ? encodeParams(c.args.map((a) => a.type), c.args.map((a) => resolveArg(a, deployed))) : "";
    return bytecode + enc;                    // 0x… creation bytecode + encoded ctor args
  }
  async function ensureCreate2Helper() {
    const cid = S.chain.chainId;
    if (S.create2Deployer[cid]) return S.create2Deployer[cid];
    log(`deploying CREATE2 helper (bankon_create2_deployer) on ${S.chain.name}…`, "");
    const art = await (await fetch(CREATE2_HELPER_ARTIFACT)).json();
    let bc = (art.bytecode && (art.bytecode.object || art.bytecode)) || "0x"; if (!bc.startsWith("0x")) bc = "0x" + bc;
    const txHash = await S.provider.request({ method: "eth_sendTransaction", params: [{ from: S.account, data: bc }] });
    const r = await waitReceipt(txHash);
    if (!r || !r.contractAddress) throw new Error("CREATE2 helper deploy failed");
    S.create2Deployer[cid] = { addr: r.contractAddress };
    log(`CREATE2 helper @ <b>${r.contractAddress}</b> · deterministic addresses unlocked`, "ok");
    return S.create2Deployer[cid];
  }
  function readDeployedEvent(r, helperAddr) {
    for (const lg of (r.logs || [])) {
      if (lg.topics && lg.topics[0] && lg.topics[0].toLowerCase() === DEPLOYED_TOPIC && (!helperAddr || addrEq(lg.address, helperAddr)) && lg.topics[1])
        return "0x" + lg.topics[1].slice(-40);
    }
    return null;
  }
  async function payFee(forWhat) {
    if (!S.fee || !S.fee.amount || S.fee.amount === "0") return;
    if (!S.fee.asset || /^0x0+$/i.test(S.fee.asset)) {
      const tx = await S.provider.request({ method: "eth_sendTransaction", params: [{ from: S.account, to: S.fee.recipient, value: "0x" + BigInt(S.fee.amount).toString(16) }] });
      log(`fee · ${BigInt(S.fee.amount)} wei → bankon.eth (${S.fee.service}) · ${forWhat} · ${tx}`, ""); await waitReceipt(tx);
    } else { log(`fee · ${S.fee.amount} of ${short(S.fee.asset)} via x402 (${S.fee.x402 || "endpoint"}) — wire ERC-20/x402 to settle`, "warn"); }
  }
  async function fireOne(c, deployed) {
    if (!chainAllowed(c.chainIds)) { log(`skip ${c.name} — not for ${S.chain.name} (chainIds ${c.chainIds.join("/")})`, "dim"); return; }
    const initCode = await buildInitCode(c, deployed);
    if (c.value.kind === "signature") { const ident = S.name || S.account; await S.provider.request({ method: "personal_sign", params: [hex(`BANKON deploy · ${c.name} · ${ident} · ${S.chain.name} · privilege:${c.privilege ? c.privilege.service : "none"}`), S.account] }); }

    let txHash, r, addr;
    if (c.create2 && c.salt) {
      const helper = await ensureCreate2Helper();
      const callData = CREATE2_SELECTOR + encodeParams(["bytes32", "bytes"], [c.salt, initCode]);
      log(`<b>LAUNCH</b> · ${c.name} on ${S.chain.name} <span class="dim">(CREATE2 · same address every chain)</span>…`, "");
      // explicit padded gas — the nested factory CREATE2 (63/64 forwarding) is unreliable under
      // wallet auto-estimation; estimate ourselves and pad.
      const gas = await estGas({ from: S.account, to: helper.addr, data: callData });
      txHash = await S.provider.request({ method: "eth_sendTransaction", params: [{ from: S.account, to: helper.addr, data: callData, ...(gas ? { gas } : {}) }] });
      r = await waitReceipt(txHash); addr = r && readDeployedEvent(r, helper.addr);
    } else {
      let valueWei = "0x0";
      if (c.value.kind === "token" && (!c.value.asset || /^0x0+$/i.test(c.value.asset)) && c.value.amount && c.value.amount !== "0") valueWei = "0x" + BigInt(c.value.amount).toString(16);
      log(`<b>LAUNCH</b> · ${c.name} on ${S.chain.name}…`, "");
      txHash = await S.provider.request({ method: "eth_sendTransaction", params: [{ from: S.account, data: initCode, value: valueWei }] });
      r = await waitReceipt(txHash); addr = r && r.contractAddress;
    }
    if (addr) {
      deployed[c.id] = addr; S.deployed[c.id] = addr; recordDeployment(c.id, addr);
      log(`<b>RETURN</b> · <span class="hl">${c.name}</span> @ <b>${addr}</b> · ${parseInt(r.status, 16) ? "success" : "failed"}${c.create2 ? " · CREATE2" : ""} · gas ${parseInt(r.gasUsed, 16)}${exAddr(addr)}${exTx(txHash)}`, parseInt(r.status, 16) ? "ok" : "err");
    } else log(`RETURN · ${c.name} tx ${txHash} mined, no address${exTx(txHash)}`, "warn");
  }
  async function runWires(bundleName, deployed) {
    const wires = S.wires[bundleName]; if (!wires || !wires.length) return;
    log(`<b>WIRE</b> · ${bundleName} · ${wires.length} post-deploy calls`, "");
    for (const w of wires) {
      const target = deployed[w.contract] || S.deployed[w.contract];
      if (!target) { log(`wire skip ${w.contract}.${w.fn} — not deployed this chain`, "dim"); continue; }
      let resolved; try { resolved = w.args.map((a) => resolveArg(a, deployed)); } catch (e) { log(`wire skip ${w.contract}.${w.fn} — ${e.message}`, "dim"); continue; }
      // skip a wire whose address arg resolves to zero (e.g. vaultSigner unset).
      if (resolved.some((v, i) => w.args[i].type === "address" && /^0+$/.test(strip(v).toLowerCase()))) { log(`wire skip ${w.contract}.${w.fn} — zero address arg (configure later)`, "dim"); continue; }
      const data = w.selector + encodeParams(w.args.map((a) => a.type), resolved);
      try {
        const txHash = await S.provider.request({ method: "eth_sendTransaction", params: [{ from: S.account, to: target, data }] });
        const r = await waitReceipt(txHash);
        log(`wire · ${w.contract}.${w.fn}() · ${r && parseInt(r.status, 16) ? "ok" : "failed"}${exTx(txHash)}`, r && parseInt(r.status, 16) ? "ok" : "err");
      } catch (e) { log(`wire ${w.contract}.${w.fn} failed: ${e.message}`, "err"); }
    }
  }
  async function fireSelection(sel, deployed) {
    await payFee(`${sel.label} on ${S.chain.name}`);
    if (sel.kind === "bundle") {
      const arr = S.bundles[sel.name] || [];
      if (arr[0] && !chainAllowed(arr[0].bundleChainIds)) { log(`bundle ${sel.name} not for ${S.chain.name} (chainIds ${arr[0].bundleChainIds.join("/")}) — skipped`, "warn"); return; }
      for (const c of arr) await fireOne(c, deployed);
      await runWires(sel.name, deployed);
    } else { await fireOne(S.contracts.find((x) => x.id === sel.id), deployed); }
  }
  async function launch() {
    if (!canDeploy()) { log("Only the wallet holding <b>bankon.eth</b> can deploy on mainnet.", "warn"); return; }
    if (!S.armed) { log("Nothing armed. DEPLOY a contract or a bundle first.", "warn"); return; }
    const sel = S.armed;
    try {
      if (S.chain && S.chain.id === "all") {
        const targets = S.chains.filter((c) => c.chainId);
        log(`<b>LAUNCH CYCLE</b> · ${sel.label} → ${targets.length} chains`, "");
        const saved = S.chain;
        for (const ch of targets) {
          S.chain = ch;
          if (!(await ensureChain())) { log(`skip ${ch.name} (switch declined)`, "warn"); continue; }
          if (!canDeploy()) { log(`skip ${ch.name} — not bankon.eth controller`, "warn"); continue; }
          try { await fireSelection(sel, {}); log(`✓ ${ch.name}`, "ok"); } catch (e) { log(`${ch.name} failed: ${e.message}`, "err"); }
        }
        S.chain = saved; await ensureChain();
      } else { if (!(await ensureChain())) return; await fireSelection(sel, S.deployed); }
      S.armed = null; renderChains(); renderSolution();
    } catch (e) { log(`LAUNCH failed: ${e.message || e.code || e}`, "err"); }
  }

  /* ── PREVIEW (arm-preview: predicted addresses + gas, no broadcast) ─ */
  function resolvePreviewArg(a, predicted) { try { return resolveArg(a, predicted); } catch (e) { return ZERO; } }
  async function buildPreview(sel) {
    const list = sel.kind === "bundle" ? (S.bundles[sel.name] || []) : [S.contracts.find((x) => x.id === sel.id)];
    const K = window.BankonKeccak; const predicted = {}, rows = [];
    for (const c of list) {
      if (!c) continue;
      if (!chainAllowed(c.chainIds)) { rows.push({ name: c.name, type: "skip", note: `not on ${S.chain.name}` }); continue; }
      const row = { stage: c.stage, name: c.name, type: c.create2 ? "create2" : "create", addr: null, gas: null, note: "" };
      try {
        const bytecode = await fetchArtifact(c);
        const enc = c.args.length ? encodeParams(c.args.map((a) => a.type), c.args.map((a) => resolvePreviewArg(a, predicted))) : "";
        const initCode = bytecode + enc;
        if (c.create2 && c.salt && K) { row.addr = K.create2Address(NICKS_FACTORY, c.salt, initCode); predicted[c.id] = row.addr; row.note = "same address every chain"; }
        try { const g = await S.provider.request({ method: "eth_estimateGas", params: [{ from: S.account, data: initCode }] }); row.gas = parseInt(g, 16); }
        catch (e) { row.note += (row.note ? " · " : "") + "gas: pending dep"; }
      } catch (e) { row.note = e.message; }
      rows.push(row);
    }
    return rows;
  }
  async function preview() {
    if (!S.armed) { log("Nothing armed. DEPLOY a contract or a bundle first, then PREVIEW.", "warn"); return; }
    if (!S.chain || S.chain.id === "all") { log("Select a single chain to preview (not ALL).", "warn"); return; }
    if (!window.BankonKeccak) { log("PREVIEW needs keccak.js (admin console). Loading the admin page enables address prediction.", "warn"); }
    log(`<b>PREVIEW</b> · ${S.armed.label} on ${S.chain.name} <span class="dim">(no broadcast)</span>…`, "");
    const rows = await buildPreview(S.armed);
    const totalGas = rows.reduce((s, r) => s + (r.gas || 0), 0);
    const body = rows.map((r) => `<tr><td>${r.stage ?? ""}</td><td>${r.name}</td><td>${r.type}</td><td>${r.addr ? `<b>${r.addr}</b>` : '<span class="dim">assigned on deploy</span>'}</td><td>${r.gas ? r.gas.toLocaleString() : "—"}</td><td class="dim">${r.note}</td></tr>`).join("");
    log(`<table class="plan"><tr><th>#</th><th>contract</th><th>type</th><th>predicted address</th><th>gas</th><th></th></tr>${body}<tr><td colspan="4" style="text-align:right">total est. gas</td><td><b>${totalGas.toLocaleString()}</b></td><td></td></tr></table>`, "ok");
    return rows;
  }

  /* ── deployments persistence (localStorage → export JSON) ───────── */
  function recordDeployment(id, addr) {
    const cid = S.chain.chainId; if (!cid) return;
    (S.deployments[cid] = S.deployments[cid] || {})[id] = addr;
    try { localStorage.setItem(`bankon.deploy.${cid}`, JSON.stringify(S.deployments[cid])); } catch (e) {}
  }
  // Build deployments/<chainId>.json (deploymentKey → address) for the operator to commit.
  function exportDeployments() {
    const cid = S.chain && S.chain.chainId; if (!cid) { log("select a single chain to export", "warn"); return null; }
    const store = JSON.parse(localStorage.getItem(`bankon.deploy.${cid}`) || "{}");
    const keys = (S.chainParams && S.chainParams.deploymentKeys) || {};
    const bankon = {};
    for (const [id, addr] of Object.entries(store)) { const k = keys[id] || id; bankon[k] = addr; }
    const out = { chainId: cid, bankon };
    const blob = JSON.stringify(out, null, 2);
    log(`<b>deployments/${cid}.json</b> (${Object.keys(bankon).length} contracts) — copy & commit:<br><textarea style="width:100%;height:120px;background:#0b0f0b;color:#9fe6a0;border:1px solid #2a3">${blob}</textarea>`, "ok");
    return out;
  }

  /* ── ADMIN console — post-deploy operations (bankon.eth admin only) ─ */
  // Resolve the deployed address of a contract on the active chain (session → localStorage).
  function deployedAddr(contractId) {
    if (S.deployed[contractId]) return S.deployed[contractId];
    try { return JSON.parse(localStorage.getItem(`bankon.deploy.${S.chain.chainId}`) || "{}")[contractId] || null; } catch (e) { return null; }
  }
  async function runAdminAction(actionId, inputs, targetOverride) {
    if (!canDeploy()) { log("Admin actions are <b>bankon.eth only</b>.", "warn"); return; }
    const a = (S.adminActions || []).find((x) => x.id === actionId);
    if (!a) { log(`unknown admin action ${actionId}`, "warn"); return; }
    if (!(await ensureChain())) return;
    const target = targetOverride || deployedAddr(a.contract);
    if (!target) { log(`No deployed <b>${a.contract}</b> on ${S.chain.name}. Deploy it first, or paste the address.`, "warn"); return; }
    const vals = (a.args || []).map((arg) => arg.source === "literal" ? arg.value : arg.source === "owner" ? S.owner : (inputs && inputs[arg.name]));
    for (let i = 0; i < a.args.length; i++) { if (a.args[i].source === "input" && (vals[i] === undefined || vals[i] === "")) { log(`Enter <b>${a.args[i].name}</b> for ${a.label}.`, "warn"); return; } }
    const data = a.selector + (a.args.length ? encodeParams(a.args.map((x) => x.type), vals) : "");
    log(`<b>ADMIN</b> · ${a.contract}.${a.fn}(${vals.join(", ")}) @ ${short(target)} on ${S.chain.name}…`, "");
    try {
      const gas = await estGas({ from: S.account, to: target, data });
      const txHash = await S.provider.request({ method: "eth_sendTransaction", params: [{ from: S.account, to: target, data, ...(gas ? { gas } : {}) }] });
      const r = await waitReceipt(txHash);
      log(`ADMIN · ${a.fn} · ${r && parseInt(r.status, 16) ? "ok" : "failed"}${exTx(txHash)}`, r && parseInt(r.status, 16) ? "ok" : "err");
      return r;
    } catch (e) { log(`ADMIN ${a.fn} failed: ${e.message}`, "err"); }
  }

  /* ── helpers ────────────────────────────────────────────────────── */
  function guard() {
    if (!S.account) { log("Connect a wallet first.", "warn"); return false; }
    if (!S.chain) { log("Select a chain first.", "warn"); return false; }
    if (!canDeploy()) { log("Connected wallet is <b>not the bankon.eth controller</b> — admin is bankon.eth only.", "warn"); return false; }
    return true;
  }
  function resolveArg(a, deployed) {
    if (a.from === "wallet") return S.account;
    if (a.from === "owner") return S.owner || S.account;
    if (a.from && a.from.startsWith("chain:")) return chainParam(a.from.slice(6));
    if (a.from && a.from.startsWith("deployed:")) { const id = a.from.slice(9); const addr = (deployed && deployed[id]) || S.deployed[id]; if (!addr) throw new Error(`deploy '${id}' first (same chain)`); return addr; }
    return a.value;
  }
  function chainParam(key) {
    const cid = S.chain && S.chain.chainId;
    const c = (S.chainParams && S.chainParams.chains && S.chainParams.chains[cid]) || {};
    if (c[key] != null) return c[key];
    if (key === "bankonNode") return (S.chainParams && S.chainParams.bankonNode) || ZERO;
    if (key === "vaultSigner") return ZERO;
    return ZERO;
  }
  async function waitReceipt(txHash, tries = 90) { for (let i = 0; i < tries; i++) { const r = await S.provider.request({ method: "eth_getTransactionReceipt", params: [txHash] }); if (r) return r; await new Promise((res) => setTimeout(res, 2000)); } return null; }
  // estimate gas + pad 50% (hex). Returns null on failure so the caller falls back to wallet auto-gas.
  async function estGas(tx) { try { const g = await S.provider.request({ method: "eth_estimateGas", params: [tx] }); return "0x" + Math.floor(parseInt(g, 16) * 1.5).toString(16); } catch (e) { return null; } }

  /* ── render ─────────────────────────────────────────────────────── */
  function renderIdentity() {
    const el = $("identity"); if (!el) return;
    if (!S.account) { el.innerHTML = '<span class="dot"></span> not connected'; return; }
    const ok = canDeploy();
    const tag = S.authority && S.authority.relaxed ? '<span class="dim">(testnet — connected wallet)</span>'
      : (ok ? '<span class="hl">bankon.eth holder ✓</span>' : '<span class="warn">not bankon.eth — read-only</span>');
    el.innerHTML = `<span class="dot ${ok ? "ok" : ""}"></span> ${S.name ? S.name + " " : ""}<span class="dim">${short(S.account)}</span> ${tag}`;
  }
  function renderChains() {
    const fb = $("feebar");
    if (fb) fb.innerHTML = S.fee && S.fee.amount && S.fee.amount !== "0"
      ? `deploy fee → bankon.eth: <b>${S.fee.asset && !/^0x0+$/i.test(S.fee.asset) ? S.fee.amount + " " + short(S.fee.asset) + " via x402" : BigInt(S.fee.amount) + " wei native"}</b> · ${S.fee.service}`
      : `deploy fee: <b>none set</b> — bankon.eth receives all subdomain + deploy fees`;
    const el = $("chains"); if (!el || !S.chains.length) { if (el) el.innerHTML = ""; return; }
    const onHex = S.chainIdHex ? parseInt(S.chainIdHex, 16) : null, allSel = S.chain && S.chain.id === "all";
    el.innerHTML =
      `<button class="chain ${allSel ? "sel" : ""}" title="deploy to every chain (the launch cycle)" onclick="Deployer.selectChain('all')">ALL <span class="csym">cycle</span></button>` +
      S.chains.map((c) => { const sel = !allSel && S.chain && S.chain.id === c.id, on = onHex === c.chainId; return `<button class="chain ${sel ? "sel" : ""}" title="${c.note || ""}" onclick="Deployer.selectChain('${c.id}')">${c.name} <span class="csym">${c.symbol}</span>${c.mainnet ? ' <span class="mainnet" title="mainnet — irreversible cost on LAUNCH">●live</span>' : ""}${on ? ' <span class="onchain">●</span>' : ""}</button>`; }).join("");
  }
  function renderSolution() {
    const el = $("contracts"); if (!el) return;
    const names = Object.keys(S.bundles);
    if (!names.length) { el.innerHTML = '<div class="empty">connect a wallet to load the solution</div>'; return; }
    const dis = canDeploy() ? "" : "disabled";
    el.innerHTML = names.map((bn) => {
      const cards = S.bundles[bn].map((c, idx) => {
        const armed = S.armed && S.armed.kind === "single" && S.armed.id === c.id, dep = S.deployed[c.id], stage = c.stage ?? (idx + 1);
        const c2 = c.create2 ? '<span class="vk vk-create2" title="deterministic — same address on every chain (CREATE2)">create2</span>' : "";
        return `<div class="card ${armed ? "armed" : ""}"><div class="ctitle"><span class="stage">${stage}</span>${c.name} <span class="vk vk-${c.value.kind}">${c.value.kind}</span>${c2}${c.privilege ? `<span class="priv">→ ${c.privilege.service}</span>` : ""}</div><div class="csum">${c.summary || ""}</div>${dep ? `<div class="deployed">@ ${dep}</div>` : ""}<div class="cactions"><button class="btn-deploy" onclick="Deployer.deploy('${c.id}')" ${dis}>DEPLOY</button><button class="btn-launch" onclick="Deployer.launch()" ${armed && canDeploy() ? "" : "disabled"}>LAUNCH</button></div></div>`;
      }).join("");
      const armedB = S.armed && S.armed.kind === "bundle" && S.armed.name === bn;
      const bChainIds = (S.bundles[bn][0] && S.bundles[bn][0].bundleChainIds) || [];
      const pin = bChainIds.length ? `<span class="bpin" title="this bundle only deploys on these chains">chains ${bChainIds.join("/")}</span>` : "";
      return `<div class="bundle"><div class="bhdr"><span class="bname">${bn}</span><span class="bmeta">${S.bundles[bn].length} stages</span>${pin}<button class="btn-bundle" onclick="Deployer.deployBundle('${bn}')" ${dis}>DEPLOY BUNDLE</button><button class="btn-launch" onclick="Deployer.launch()" ${armedB && canDeploy() ? "" : "disabled"}>LAUNCH BUNDLE</button></div><div class="grid">${cards}</div></div>`;
    }).join("") + `<div class="exportrow"><button class="btn-deploy" onclick="Deployer.exportDeployments()">EXPORT deployments JSON</button></div>`;
  }

  window.Deployer = { connect, loadSolution, loadChains, selectChain, deploy, deployBundle, launch, preview, exportDeployments, runAdminAction, state: S };
  document.addEventListener("DOMContentLoaded", () => { loadSolution().catch(() => {}); renderIdentity(); });
})();
