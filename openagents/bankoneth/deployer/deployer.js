/*
 * deployer.js — client-side contract deployer (bundles · stages · chain isolation · ALL cycle).
 *
 * Framework-free; only the wallet's EIP-1193 provider in the trust path. Flow:
 *   CHAIN   — pick an isolation target from chains.xml (0G, ETH, Base, ARC, GLMR, POL…),
 *             or ALL to run the launch cycle across every chain. The wallet is switched
 *             to each target before broadcasting (wallet_switchEthereumChain).
 *   DEPLOY  — arm one contract or a whole topic BUNDLE (records the selection).
 *   LAUNCH  — fire FROM VALUE: pay the deploy FEE to mindX/AgenticPlace (native or x402),
 *             sign / pay token value, then broadcast each staged tx in order. In ALL mode
 *             it repeats per chain with a per-chain address namespace.
 *   RETURN  — the txs the chain returns (hash, status, address).
 *
 * Build happens at fire time, so stage N's `from="deployed:<id>"` resolves to the
 * address stage N-1 just produced on THIS chain. Deploying a bundle is a pay-to-play
 * service — <fee> goes to mindX/AgenticPlace. Always open source · client-side.
 * (c) BANKON all rights preserved.
 */
(function () {
  "use strict";

  const S = {
    provider: null, account: null, chainIdHex: null, name: null,
    chains: [], chain: null, fee: null,
    contracts: [], bundles: {},
    armed: null,            // { kind:'single'|'bundle', id?|name?, label }
    deployed: {},           // id -> address (last chain in ALL mode)
  };

  const $ = (id) => document.getElementById(id);
  const log = (m, cls) => { const el = $("return"); if (!el) return; const l = document.createElement("div"); l.className = "rline " + (cls || ""); l.innerHTML = m; el.prepend(l); };
  const strip = (s) => (s || "").replace(/^0x/i, "");
  const short = (a) => (a ? a.slice(0, 6) + "…" + a.slice(-4) : "");
  const hex = (s) => "0x" + Array.from(new TextEncoder().encode(s)).map((b) => b.toString(16).padStart(2, "0")).join("");
  const chainLabel = () => (S.chain ? (S.chain.id === "all" ? "ALL chains" : S.chain.name) : "?");

  /* ── identity ───────────────────────────────────────────────────── */
  async function connect() {
    if (!window.ethereum) { log("No wallet found. Install a wallet (MetaMask).", "err"); return; }
    S.provider = window.ethereum;
    S.account = (await S.provider.request({ method: "eth_requestAccounts" }))[0];
    S.chainIdHex = await S.provider.request({ method: "eth_chainId" });
    S.provider.on && S.provider.on("accountsChanged", () => location.reload());
    S.provider.on && S.provider.on("chainChanged", (id) => { S.chainIdHex = id; renderChains(); });
    renderIdentity(); renderChains(); renderSolution();
  }

  /* ── chains (isolation + ALL) ───────────────────────────────────── */
  async function loadChains(url) {
    try {
      const doc = new DOMParser().parseFromString(await (await fetch(url || "chains.xml")).text(), "application/xml");
      S.chains = Array.from(doc.querySelectorAll("chain")).map((c) => ({
        id: c.getAttribute("id"), name: c.getAttribute("name"), chainId: parseInt(c.getAttribute("chainId"), 10),
        symbol: c.getAttribute("symbol"), rpc: c.getAttribute("rpc"), explorer: c.getAttribute("explorer"),
        marketRef: c.getAttribute("marketRef"), note: c.getAttribute("note"),
      }));
      const def = doc.documentElement.getAttribute("default");
      S.chain = S.chains.find((c) => c.id === def) || S.chains[0] || null;
      renderChains();
    } catch (e) { /* chains optional */ }
  }
  function selectChain(id) { S.chain = id === "all" ? { id: "all", name: "ALL chains", chainId: 0 } : (S.chains.find((c) => c.id === id) || S.chain); renderChains(); renderSolution(); }

  async function ensureChain() {
    if (!S.chain || !S.chain.chainId) return true; // ARC / ALL placeholder → skip
    const want = "0x" + S.chain.chainId.toString(16);
    if ((await S.provider.request({ method: "eth_chainId" })).toLowerCase() === want.toLowerCase()) return true;
    try { await S.provider.request({ method: "wallet_switchEthereumChain", params: [{ chainId: want }] }); return true; }
    catch (e) {
      if (e && e.code === 4902 && S.chain.rpc) {
        try { await S.provider.request({ method: "wallet_addEthereumChain", params: [{ chainId: want, chainName: S.chain.name, rpcUrls: [S.chain.rpc], nativeCurrency: { name: S.chain.symbol, symbol: S.chain.symbol, decimals: 18 }, blockExplorerUrls: S.chain.explorer ? [S.chain.explorer] : [] }] }); return true; }
        catch (_) {}
      }
      log(`Switch your wallet to <b>${S.chain.name}</b> (id ${S.chain.chainId}) and retry.`, "warn");
      return false;
    }
  }

  /* ── solution (index.xml + includes) ────────────────────────────── */
  function parseContracts(doc) {
    return Array.from(doc.querySelectorAll("contract")).map((c) => ({
      id: c.getAttribute("id"), name: c.getAttribute("name"), summary: c.getAttribute("summary") || "",
      bundle: c.getAttribute("bundle") || null, stage: c.getAttribute("stage") ? parseInt(c.getAttribute("stage"), 10) : null,
      abiSrc: c.querySelector("abi")?.getAttribute("src"), bytecodeSrc: c.querySelector("bytecode")?.getAttribute("src"),
      args: Array.from(c.querySelectorAll("constructor > arg")).map((a) => ({ name: a.getAttribute("name"), type: a.getAttribute("type"), from: a.getAttribute("from"), value: a.getAttribute("value") })),
      value: (() => { const v = c.querySelector("value"); return { kind: v?.getAttribute("kind") || "signature", asset: v?.getAttribute("asset"), amount: v?.getAttribute("amount") }; })(),
      privilege: (() => { const p = c.querySelector("privilege"); return p ? { service: p.getAttribute("service"), tier: p.getAttribute("tier") } : null; })(),
    }));
  }
  function deriveBundle(c) {
    if (c.bundle) return c.bundle;
    const m = /(?:\.\.\/)+([a-z0-9_-]+)\//i.exec(c.bytecodeSrc || "");
    return m ? m[1] : "core";
  }
  async function loadSolution(url) {
    const doc = new DOMParser().parseFromString(await (await fetch(url || "index.xml")).text(), "application/xml");
    await loadChains(doc.querySelector("chains[src]")?.getAttribute("src") || "chains.xml");
    const f = doc.querySelector("fee");
    S.fee = f ? { recipient: f.getAttribute("recipient"), asset: f.getAttribute("asset"), amount: f.getAttribute("amount") || "0", service: f.getAttribute("service") || "deploy.bundle", x402: f.getAttribute("x402") || "" } : null;
    let contracts = parseContracts(doc);
    for (const inc of Array.from(doc.querySelectorAll("include[src]")).map((i) => i.getAttribute("src"))) {
      try { const bdoc = new DOMParser().parseFromString(await (await fetch(inc)).text(), "application/xml"); const bname = bdoc.documentElement.getAttribute("name"); contracts = contracts.concat(parseContracts(bdoc).map((c) => ({ ...c, bundle: c.bundle || bname }))); }
      catch (e) { log(`include failed: ${inc}`, "warn"); }
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

  /* ── LAUNCH (fire from value) ───────────────────────────────────── */
  async function buildTx(c, deployed) {
    const art = await (await fetch(c.bytecodeSrc)).json();
    const bytecode = (art.bytecode && (art.bytecode.object || art.bytecode)) || art.deployedBytecode?.object;
    if (!bytecode || bytecode === "0x") throw new Error("no bytecode (forge build first)");
    const data = (bytecode.startsWith("0x") ? bytecode : "0x" + bytecode) + c.args.map((a) => encodeArg(a.type, resolveArg(a, deployed))).join("");
    let valueWei = "0x0";
    if (c.value.kind === "token" && (!c.value.asset || /^0x0+$/i.test(c.value.asset)) && c.value.amount && c.value.amount !== "0") valueWei = "0x" + BigInt(c.value.amount).toString(16);
    return { data, valueWei };
  }
  async function payFee(forWhat) {
    if (!S.fee || !S.fee.amount || S.fee.amount === "0") return;
    if (!S.fee.asset || /^0x0+$/i.test(S.fee.asset)) {
      const tx = await S.provider.request({ method: "eth_sendTransaction", params: [{ from: S.account, to: S.fee.recipient, value: "0x" + BigInt(S.fee.amount).toString(16) }] });
      log(`fee · ${BigInt(S.fee.amount)} wei → mindX/AgenticPlace (${S.fee.service}) · ${forWhat} · ${tx}`, ""); await waitReceipt(tx);
    } else { log(`fee · ${S.fee.amount} of ${short(S.fee.asset)} via x402 (${S.fee.x402 || "endpoint"}) — wire ERC-20/x402 to settle`, "warn"); }
  }
  async function fireOne(c, deployed) {
    const tx = await buildTx(c, deployed);
    if (c.value.kind === "signature") { const ident = S.name || S.account; await S.provider.request({ method: "personal_sign", params: [hex(`BANKON deploy · ${c.name} · ${ident} · ${S.chain.name} · privilege:${c.privilege ? c.privilege.service : "none"}`), S.account] }); }
    log(`<b>LAUNCH</b> · ${c.name} on ${S.chain.name}…`, "");
    const txHash = await S.provider.request({ method: "eth_sendTransaction", params: [{ from: S.account, data: tx.data, value: tx.valueWei }] });
    const r = await waitReceipt(txHash);
    if (r && r.contractAddress) { deployed[c.id] = r.contractAddress; S.deployed[c.id] = r.contractAddress; log(`<b>RETURN</b> · <span class="hl">${c.name}</span> @ <b>${r.contractAddress}</b> · ${parseInt(r.status, 16) ? "success" : "failed"} · gas ${parseInt(r.gasUsed, 16)}`, parseInt(r.status, 16) ? "ok" : "err"); }
    else log(`RETURN · ${c.name} tx ${txHash} mined, no address`, "warn");
  }
  async function fireSelection(sel, deployed) {
    await payFee(`${sel.label} on ${S.chain.name}`);
    if (sel.kind === "bundle") { for (const c of S.bundles[sel.name]) await fireOne(c, deployed); }
    else { await fireOne(S.contracts.find((x) => x.id === sel.id), deployed); }
  }
  async function launch() {
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
          try { await fireSelection(sel, {}); log(`✓ ${ch.name}`, "ok"); } catch (e) { log(`${ch.name} failed: ${e.message}`, "err"); }
        }
        S.chain = saved;
      } else { if (!(await ensureChain())) return; await fireSelection(sel, S.deployed); }
      S.armed = null; renderChains(); renderSolution();
    } catch (e) { log(`LAUNCH failed: ${e.message || e.code || e}`, "err"); }
  }

  /* ── helpers ────────────────────────────────────────────────────── */
  function guard() { if (!S.account) { log("Connect a wallet first.", "warn"); return false; } if (!S.chain) { log("Select a chain first.", "warn"); return false; } return true; }
  function resolveArg(a, deployed) {
    if (a.from === "wallet") return S.account;
    if (a.from && a.from.startsWith("deployed:")) { const id = a.from.slice(9); const addr = (deployed && deployed[id]) || S.deployed[id]; if (!addr) throw new Error(`deploy '${id}' first (same chain)`); return addr; }
    return a.value;
  }
  function encodeArg(type, value) {
    if (type === "address") return strip(value).toLowerCase().padStart(64, "0");
    if (/^u?int(\d*)$/.test(type)) return BigInt(value || 0).toString(16).padStart(64, "0");
    if (type === "bool") return (value === "true" || value === true ? "1" : "0").padStart(64, "0");
    if (/^bytes32$/.test(type)) return strip(value).padEnd(64, "0");
    throw new Error(`unsupported constructor type '${type}' (static types only)`);
  }
  async function waitReceipt(txHash, tries = 90) { for (let i = 0; i < tries; i++) { const r = await S.provider.request({ method: "eth_getTransactionReceipt", params: [txHash] }); if (r) return r; await new Promise((res) => setTimeout(res, 2000)); } return null; }

  /* ── render ─────────────────────────────────────────────────────── */
  function renderIdentity() { const el = $("identity"); if (!el) return; el.innerHTML = S.account ? `<span class="dot ok"></span> ${S.name ? S.name + " " : ""}<span class="dim">${short(S.account)}</span>` : '<span class="dot"></span> not connected'; }
  function renderChains() {
    const fb = $("feebar");
    if (fb) fb.innerHTML = S.fee && S.fee.amount && S.fee.amount !== "0"
      ? `deploy fee → mindX/AgenticPlace: <b>${S.fee.asset && !/^0x0+$/i.test(S.fee.asset) ? S.fee.amount + " " + short(S.fee.asset) + " via x402" : BigInt(S.fee.amount) + " wei native"}</b> · ${S.fee.service}`
      : `deploy fee: <b>none set</b> — set &lt;fee&gt; recipient/amount for the AgenticPlace x402 rail`;
    const el = $("chains"); if (!el || !S.chains.length) { if (el) el.innerHTML = ""; return; }
    const onHex = S.chainIdHex ? parseInt(S.chainIdHex, 16) : null, allSel = S.chain && S.chain.id === "all";
    el.innerHTML =
      `<button class="chain ${allSel ? "sel" : ""}" title="deploy to every chain (the launch cycle)" onclick="Deployer.selectChain('all')">ALL <span class="csym">cycle</span></button>` +
      S.chains.map((c) => { const sel = !allSel && S.chain && S.chain.id === c.id, on = onHex === c.chainId; return `<button class="chain ${sel ? "sel" : ""}" title="${c.note || ""}" onclick="Deployer.selectChain('${c.id}')">${c.name} <span class="csym">${c.symbol}</span>${on ? ' <span class="onchain">●</span>' : ""}</button>`; }).join("");
  }
  function renderSolution() {
    const el = $("contracts"); if (!el) return;
    const names = Object.keys(S.bundles);
    if (!names.length) { el.innerHTML = '<div class="empty">connect a wallet to load the solution</div>'; return; }
    el.innerHTML = names.map((bn) => {
      const cards = S.bundles[bn].map((c, idx) => {
        const armed = S.armed && S.armed.kind === "single" && S.armed.id === c.id, dep = S.deployed[c.id], stage = c.stage ?? (idx + 1);
        return `<div class="card ${armed ? "armed" : ""}"><div class="ctitle"><span class="stage">${stage}</span>${c.name} <span class="vk vk-${c.value.kind}">${c.value.kind}</span>${c.privilege ? `<span class="priv">→ ${c.privilege.service}</span>` : ""}</div><div class="csum">${c.summary || ""}</div>${dep ? `<div class="deployed">@ ${dep}</div>` : ""}<div class="cactions"><button class="btn-deploy" onclick="Deployer.deploy('${c.id}')">DEPLOY</button><button class="btn-launch" onclick="Deployer.launch()" ${armed ? "" : "disabled"}>LAUNCH</button></div></div>`;
      }).join("");
      const armedB = S.armed && S.armed.kind === "bundle" && S.armed.name === bn;
      return `<div class="bundle"><div class="bhdr"><span class="bname">${bn}</span><span class="bmeta">${S.bundles[bn].length} stages</span><button class="btn-bundle" onclick="Deployer.deployBundle('${bn}')">DEPLOY BUNDLE</button><button class="btn-launch" onclick="Deployer.launch()" ${armedB ? "" : "disabled"}>LAUNCH BUNDLE</button></div><div class="grid">${cards}</div></div>`;
    }).join("");
  }

  window.Deployer = { connect, loadSolution, loadChains, selectChain, deploy, deployBundle, launch, state: S };
  document.addEventListener("DOMContentLoaded", () => { loadSolution().catch(() => {}); renderIdentity(); });
})();
