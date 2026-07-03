// SPDX-License-Identifier: Apache-2.0
//
// app-common.js — shared connect + SIWE login + tier routing for the three
// BANKON tier pages (index/member/admin). Imports ethers + bankon-forms; the
// gate backend (backend/) issues the tier session. Pages call BANKON.boot().
import { ethers } from "./vendor/ethers.min.js";
import * as F from "./bankon-forms.js";

export { ethers, F };

export const BANKON = {
  provider: null, browserProvider: null, address: null, chainId: null,
  tier: "visitor", names: [], manifest: null, deployments: null,
  PUBLIC_BASE: "./public", GFX: "/gfx",
};

const CHAINS = { 1: "Ethereum", 11155111: "Sepolia", 31337: "Anvil (local)" };

// ── wallet (EIP-6963 + legacy) ───────────────────────────────────────────────
let wallets = [], ready = false;
function detect() {
  return new Promise((res) => {
    wallets = [];
    window.addEventListener("eip6963:announceProvider", (e) => {
      const { info, provider } = e.detail;
      if (!wallets.some((w) => w.uuid === info.uuid))
        wallets.push({ id: (info.rdns || info.name || "").toLowerCase(), provider, uuid: info.uuid });
    });
    window.dispatchEvent(new Event("eip6963:requestProvider"));
    setTimeout(() => { ready = true; res(); }, 320);
  });
}
function pick() {
  const pool = wallets.length ? wallets : (window.ethereum ? [{ id: "injected", provider: window.ethereum }] : []);
  if (!pool.length) return null;
  return (pool.find((w) => w.id.includes("metamask")) || pool[0]).provider;
}

export async function connect() {
  if (!ready) await detect();
  BANKON.provider = pick();
  if (!BANKON.provider) { toast("Install MetaMask or an EVM wallet.", "err"); return null; }
  const accts = await BANKON.provider.request({ method: "eth_requestAccounts" });
  BANKON.address = accts[0];
  BANKON.chainId = parseInt(await BANKON.provider.request({ method: "eth_chainId" }), 16);
  BANKON.browserProvider = new ethers.BrowserProvider(BANKON.provider);
  BANKON.provider.on?.("accountsChanged", () => location.reload());
  BANKON.provider.on?.("chainChanged", () => location.reload());
  if (!BANKON.deployments) { try { BANKON.deployments = await F.loadDeployments(BANKON.PUBLIC_BASE, BANKON.chainId); } catch {} }
  return BANKON.address;
}

// ── SIWE login → tier session (gate backend) ─────────────────────────────────
export async function login(label) {
  if (!BANKON.address) { await connect(); if (!BANKON.address) return null; }
  const ch = await (await fetch("/auth/challenge", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ address: BANKON.address }) })).json();
  const signer = await BANKON.browserProvider.getSigner();
  const signature = await signer.signMessage(ch.message);
  const v = await (await fetch("/auth/verify", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ address: BANKON.address, nonce: ch.nonce, signature, label: label || null }) })).json();
  if (v.tier) { BANKON.tier = v.tier; BANKON.names = v.names || []; }
  return v;
}

export async function whoami() {
  try { const me = await (await fetch("/auth/me")).json(); BANKON.tier = me.tier || "visitor"; BANKON.names = me.names || []; return me; }
  catch { return { tier: "visitor" }; }
}

// Redirect to the page matching the tier (guard against loops).
export function routeToTier(tier, here) {
  const target = tier === "admin" ? "/admin.html" : tier === "member" ? "/member.html" : "/index.html";
  const cur = location.pathname.endsWith(here) ? here : location.pathname;
  if (!cur.endsWith(target.replace("/", "")) && !(target === "/index.html" && (cur === "/" || cur.endsWith("index.html")))) {
    location.href = target;
  }
}

// ── UI helpers ───────────────────────────────────────────────────────────────
export const gfx = (name) => `${BANKON.GFX}/${name}`;

export function topbar({ onLogin } = {}) {
  const bar = document.querySelector(".topbar");
  if (!bar) return;
  const chainTxt = BANKON.chainId ? (CHAINS[BANKON.chainId] || `chain ${BANKON.chainId}`) : "";
  bar.querySelector("[data-conn]").innerHTML = BANKON.address
    ? `<span class="tier-badge ${BANKON.tier}"><span class="dot"></span>${BANKON.tier}</span>
       <span class="muted" style="font-size:12px">${BANKON.address.slice(0, 6)}…${BANKON.address.slice(-4)} · ${chainTxt}</span>`
    : `<button class="primary" data-loginbtn>Sign in</button>`;
  const lb = bar.querySelector("[data-loginbtn]");
  if (lb) lb.addEventListener("click", onLogin || defaultLogin);
}

async function defaultLogin() {
  const r = await login();
  if (r && r.tier) routeToTier(r.tier, location.pathname);
}

export async function boot({ page } = {}) {
  BANKON.manifest = await F.loadManifest(BANKON.PUBLIC_BASE).catch(() => null);
  await whoami();
  return BANKON;
}

let toastTimer = null;
export function toast(msg, kind = "") {
  clearTimeout(toastTimer); document.querySelector(".toast")?.remove();
  const t = document.createElement("div"); t.className = "toast " + kind; t.textContent = msg;
  document.body.appendChild(t); toastTimer = setTimeout(() => t.remove(), 5000);
}

export function el(tag, opts = {}, kids = []) {
  const e = document.createElement(tag);
  if (opts.cls) e.className = opts.cls;
  if (opts.html != null) e.innerHTML = opts.html;
  if (opts.text != null) e.textContent = opts.text;
  if (opts.attrs) for (const [k, v] of Object.entries(opts.attrs)) e.setAttribute(k, v);
  if (opts.on) for (const [k, v] of Object.entries(opts.on)) e.addEventListener(k, v);
  for (const k of [].concat(kids)) e.appendChild(typeof k === "string" ? document.createTextNode(k) : k);
  return e;
}

export function stringify(r) {
  if (typeof r === "bigint") return r.toString();
  if (Array.isArray(r)) return r.map(stringify).join("\n");
  if (r && typeof r === "object") { try { return JSON.stringify(r, (_, v) => (typeof v === "bigint" ? v.toString() : v), 2); } catch { return String(r); } }
  return String(r);
}
