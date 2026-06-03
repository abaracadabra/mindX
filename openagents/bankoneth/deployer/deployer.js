/*
 * deployer.js — the client-side contract deployer.
 *
 * A simpler-than-Remix deploy flow, framework-free, using only the wallet's
 * EIP-1193 provider (window.ethereum) so every line is auditable. Two events:
 *
 *   DEPLOY  arms a deployment — resolves constructor args, fetches the compiled
 *           artifact (Foundry JSON), ABI-encodes the args, builds the tx. No cost.
 *   LAUNCH  fires it FROM VALUE — a `signature` (prove identity to deploy) or a
 *           `token` (pay native value), then broadcasts. The wallet public key
 *           (or its bankon.eth name) is the identity that receives the privilege.
 *   RETURN  the transaction the blockchain returns — hash, status, deployed address.
 *
 * Always open source. (c) BANKON all rights preserved.
 */
(function () {
  "use strict";

  const S = {
    provider: null,
    account: null,
    chainId: null,
    name: null,            // bankon.eth / ENS, if any
    solution: [],          // parsed contracts
    armed: null,           // { c, data, value, valueWei }
    deployed: {},          // id -> address (for from="deployed:id")
  };

  const $ = (id) => document.getElementById(id);
  const log = (m, cls) => {
    const el = $("return");
    if (!el) return;
    const line = document.createElement("div");
    line.className = "rline " + (cls || "");
    line.innerHTML = m;
    el.prepend(line);
  };

  /* ── identity (wallet / bankon.eth) ─────────────────────────────── */
  async function connect() {
    if (!window.ethereum) { log("No wallet found. Install a wallet (MetaMask).", "err"); return; }
    S.provider = window.ethereum;
    const accts = await S.provider.request({ method: "eth_requestAccounts" });
    S.account = accts[0];                 // the public key / address — the identity
    S.chainId = await S.provider.request({ method: "eth_chainId" });
    S.name = null;                        // bankon.eth name (resolution hook — see below)
    S.provider.on && S.provider.on("accountsChanged", () => location.reload());
    S.provider.on && S.provider.on("chainChanged", () => location.reload());
    renderIdentity();
    renderSolution();
  }

  // Identity is the wallet public key (address). To show a bankon.eth name, resolve
  // it via the bankon resolver and set S.name — left as a hook so the deployer has
  // no keccak/ENS dependency in its trust path. The address is the receipt identity.

  /* ── solution (index.xml) ───────────────────────────────────────── */
  async function loadSolution(url) {
    const xml = await (await fetch(url || "index.xml")).text();
    const doc = new DOMParser().parseFromString(xml, "application/xml");
    S.solution = Array.from(doc.querySelectorAll("contract")).map((c) => ({
      id: c.getAttribute("id"),
      name: c.getAttribute("name"),
      summary: c.getAttribute("summary") || "",
      abiSrc: c.querySelector("abi")?.getAttribute("src"),
      bytecodeSrc: c.querySelector("bytecode")?.getAttribute("src"),
      args: Array.from(c.querySelectorAll("constructor > arg")).map((a) => ({
        name: a.getAttribute("name"), type: a.getAttribute("type"),
        from: a.getAttribute("from"), value: a.getAttribute("value"),
      })),
      value: (() => {
        const v = c.querySelector("value");
        return { kind: v?.getAttribute("kind") || "signature", asset: v?.getAttribute("asset"), amount: v?.getAttribute("amount") };
      })(),
      privilege: (() => {
        const p = c.querySelector("privilege");
        return p ? { service: p.getAttribute("service"), tier: p.getAttribute("tier") } : null;
      })(),
    }));
    renderSolution();
  }

  /* ── DEPLOY (arm) ───────────────────────────────────────────────── */
  async function deploy(id) {
    if (!S.account) { log("Connect a wallet first.", "warn"); return; }
    const c = S.solution.find((x) => x.id === id);
    if (!c) return;
    try {
      const art = await (await fetch(c.bytecodeSrc)).json();
      const bytecode = (art.bytecode && (art.bytecode.object || art.bytecode)) || art.deployedBytecode?.object;
      if (!bytecode || bytecode === "0x") throw new Error("no bytecode in artifact (build the contracts first)");
      const encodedArgs = c.args.map((a) => encodeArg(a.type, resolveArg(a))).join("");
      const data = (bytecode.startsWith("0x") ? bytecode : "0x" + bytecode) + encodedArgs;
      let valueWei = "0x0";
      if (c.value.kind === "token" && (!c.value.asset || /^0x0+$/i.test(c.value.asset)) && c.value.amount && c.value.amount !== "0") {
        valueWei = "0x" + BigInt(c.value.amount).toString(16);
      }
      S.armed = { c, data, valueWei };
      log(`<b>DEPLOY armed</b> · <span class="hl">${c.name}</span> · value=<b>${c.value.kind}</b>${valueWei !== "0x0" ? " (" + BigInt(valueWei) + " wei)" : ""} · press <b>LAUNCH</b> to fire`, "ok");
      renderSolution();
    } catch (e) {
      log(`DEPLOY failed to arm ${c.name}: ${e.message}`, "err");
    }
  }

  /* ── LAUNCH (fire from value) ───────────────────────────────────── */
  async function launch() {
    if (!S.armed) { log("Nothing armed. Press DEPLOY on a contract first.", "warn"); return; }
    const { c, data, valueWei } = S.armed;
    try {
      // VALUE step: signature (prove identity) or token (pay) — the participant's
      // public key is the identity that receives the privilege.
      if (c.value.kind === "signature") {
        const ident = S.name || S.account;
        const msg = `BANKON deploy · ${c.name} · by ${ident} · privilege:${c.privilege ? c.privilege.service : "none"}`;
        await S.provider.request({ method: "personal_sign", params: [hex(msg), S.account] });
        log(`signature accepted · identity <span class="hl">${ident}</span> proven`, "ok");
      } else {
        log(`paying value (${BigInt(valueWei)} wei native) with the deploy`, "");
      }
      log(`<b>LAUNCH</b> · broadcasting ${c.name}…`, "");
      const txHash = await S.provider.request({
        method: "eth_sendTransaction",
        params: [{ from: S.account, data, value: valueWei }],
      });
      log(`tx sent · <a href="#" onclick="return false">${txHash}</a> · awaiting receipt…`, "");
      const rcpt = await waitReceipt(txHash);
      if (rcpt && rcpt.contractAddress) {
        S.deployed[c.id] = rcpt.contractAddress;
        log(`<b>RETURN</b> · <span class="hl">${c.name}</span> deployed at <b>${rcpt.contractAddress}</b> · status ${parseInt(rcpt.status, 16) ? "success" : "failed"} · gas ${parseInt(rcpt.gasUsed, 16)}`, parseInt(rcpt.status, 16) ? "ok" : "err");
      } else {
        log(`RETURN · tx ${txHash} mined but no contract address`, "warn");
      }
      S.armed = null;
      renderSolution();
    } catch (e) {
      log(`LAUNCH failed: ${e.message || e.code || e}`, "err");
    }
  }

  /* ── helpers ────────────────────────────────────────────────────── */
  function resolveArg(a) {
    if (a.from === "wallet") return S.account;
    if (a.from && a.from.startsWith("deployed:")) {
      const id = a.from.slice("deployed:".length);
      const addr = S.deployed[id];
      if (!addr) throw new Error(`deploy '${id}' first (constructor needs its address)`);
      return addr;
    }
    return a.value;
  }

  function encodeArg(type, value) {
    if (type === "address") return strip(value).toLowerCase().padStart(64, "0");
    if (/^u?int(\d*)$/.test(type)) return BigInt(value || 0).toString(16).padStart(64, "0");
    if (type === "bool") return (value === "true" || value === true ? "1" : "0").padStart(64, "0");
    if (/^bytes32$/.test(type)) return strip(value).padEnd(64, "0");
    throw new Error(`unsupported constructor type '${type}' (static types only)`);
  }

  const strip = (s) => (s || "").replace(/^0x/i, "");
  const hex = (s) => "0x" + Array.from(new TextEncoder().encode(s)).map((b) => b.toString(16).padStart(2, "0")).join("");

  async function waitReceipt(txHash, tries = 60) {
    for (let i = 0; i < tries; i++) {
      const r = await S.provider.request({ method: "eth_getTransactionReceipt", params: [txHash] });
      if (r) return r;
      await new Promise((res) => setTimeout(res, 2000));
    }
    return null;
  }

  /* ── render ─────────────────────────────────────────────────────── */
  function renderIdentity() {
    const el = $("identity");
    if (!el) return;
    const id = S.name ? `${S.name} <span class="dim">(${short(S.account)})</span>` : short(S.account);
    el.innerHTML = S.account ? `<span class="dot ok"></span> ${id} · chain ${parseInt(S.chainId, 16)}` : '<span class="dot"></span> not connected';
  }
  function renderSolution() {
    const el = $("contracts");
    if (!el) return;
    if (!S.solution.length) { el.innerHTML = '<div class="empty">no solution loaded</div>'; return; }
    el.innerHTML = S.solution.map((c) => {
      const armed = S.armed && S.armed.c.id === c.id;
      const dep = S.deployed[c.id];
      return `<div class="card ${armed ? "armed" : ""}">
        <div class="ctitle">${c.name} <span class="vk vk-${c.value.kind}">${c.value.kind}</span>${c.privilege ? `<span class="priv">→ ${c.privilege.service}</span>` : ""}</div>
        <div class="csum">${c.summary}</div>
        ${dep ? `<div class="deployed">deployed: ${dep}</div>` : ""}
        <div class="cactions">
          <button class="btn-deploy" onclick="Deployer.deploy('${c.id}')" ${S.account ? "" : "disabled"}>DEPLOY</button>
          <button class="btn-launch" onclick="Deployer.launch()" ${armed ? "" : "disabled"}>LAUNCH</button>
        </div>
      </div>`;
    }).join("");
  }
  const short = (a) => (a ? a.slice(0, 6) + "…" + a.slice(-4) : "");

  window.Deployer = { connect, loadSolution, deploy, launch, state: S };
  document.addEventListener("DOMContentLoaded", () => { loadSolution().catch(() => {}); renderIdentity(); });
})();
