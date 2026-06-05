// Dev-only: headless end-to-end proof of the deployer engine against anvil.
// Exercises the SAME encoder/CREATE2/wire paths as deployer.js via JSON-RPC
// (anvil unlocked accounts → eth_sendTransaction, no signing lib). NOT shipped.
import { readFileSync } from "node:fs";

const RPC = "http://127.0.0.1:8545";
const NICKS = "0x4e59b44847b379578588920cA78FbF26c0B4956C";
const CREATE2_SELECTOR = "0xcdcb760a";
const DEPLOYED_TOPIC = "0x94bfd9af14ef450884c8a7ddb5734e2e1e14e70a1c84f0801cc5a29e34d26428";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ── encoder (mirror of deployer.js) ──
const strip = (s) => (s || "").replace(/^0x/i, "");
const utf8hex = (s) => Buffer.from(s, "utf8").toString("hex");
const uint256Hex = (n) => BigInt(n).toString(16).padStart(64, "0");
const isDynamic = (t) => t === "string" || t === "bytes" || t.endsWith("[]");
function encStatic(type, v) {
  if (type === "address") return strip(v).toLowerCase().padStart(64, "0");
  if (/^u?int(\d*)$/.test(type)) return uint256Hex(v || 0);
  if (type === "bool") return (v === "true" || v === true ? "1" : "0").padStart(64, "0");
  if (/^bytes([1-9]|[12]\d|3[0-2])$/.test(type)) return strip(v).padEnd(64, "0");
  throw new Error("static " + type);
}
function encBlob(h) { const len = h.length / 2; const p = h.length ? h.padEnd(Math.ceil(h.length / 64) * 64, "0") : ""; return uint256Hex(len) + p; }
function encDyn(type, v) {
  if (type === "string") return encBlob(utf8hex(v || ""));
  if (type === "bytes") return encBlob(strip(v || "0x"));
  if (type.endsWith("[]")) { const b = type.slice(0, -2); let a = typeof v === "string" ? (v === "[]" ? [] : JSON.parse(v)) : v; return uint256Hex(a.length) + a.map((e) => encStatic(b, e)).join(""); }
  throw new Error("dyn " + type);
}
function encodeParams(types, vals) {
  const heads = [], tails = []; let dyn = 32 * types.length;
  for (let i = 0; i < types.length; i++) { const t = types[i], v = vals[i]; if (isDynamic(t)) { heads.push(uint256Hex(dyn)); const tl = encDyn(t, v); tails.push(tl); dyn += tl.length / 2; } else heads.push(encStatic(t, v)); }
  return heads.join("") + tails.join("");
}
const saltFor = (n) => "0x" + Buffer.from(n).toString("hex").padEnd(64, "0");
const bytecode = (n) => { const j = JSON.parse(readFileSync(`out/${n}.sol/${n}.json`, "utf8")); const b = j.bytecode.object || j.bytecode; return b.startsWith("0x") ? b : "0x" + b; };
const ctorTypes = (n) => { const j = JSON.parse(readFileSync(`out/${n}.sol/${n}.json`, "utf8")); const c = j.abi.find((x) => x.type === "constructor"); return (c && c.inputs.map((i) => i.type)) || []; };
const selector = (n, sig) => "0x" + JSON.parse(readFileSync(`out/${n}.sol/${n}.json`, "utf8")).methodIdentifiers[sig];

// ── rpc ──
let ID = 0;
async function rpc(method, params) {
  const r = await fetch(RPC, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ jsonrpc: "2.0", id: ++ID, method, params }) });
  const j = await r.json(); if (j.error) throw new Error(method + ": " + JSON.stringify(j.error)); return j.result;
}
async function waitReceipt(h) { for (let i = 0; i < 80; i++) { const r = await rpc("eth_getTransactionReceipt", [h]); if (r) return r; await sleep(250); } throw new Error("no receipt"); }
async function estGas(tx) { try { const g = await rpc("eth_estimateGas", [tx]); return "0x" + Math.floor(parseInt(g, 16) * 1.5).toString(16); } catch (e) { return null; } }
async function send(tx) { const gas = await estGas(tx); return waitReceipt(await rpc("eth_sendTransaction", [{ ...tx, ...(gas ? { gas } : {}) }])); }
const code = (a) => rpc("eth_getCode", [a, "latest"]);
const readDeployed = (r, helper) => { for (const l of r.logs || []) if (l.topics[0].toLowerCase() === DEPLOYED_TOPIC && l.address.toLowerCase() === helper.toLowerCase()) return "0x" + l.topics[1].slice(-40); return null; };

let pass = 0, fail = 0;
const ok = (m) => { console.log("  OK  " + m); pass++; };
const bad = (m) => { console.log("  FAIL " + m); fail++; };

async function main() {
  const [acct] = await rpc("eth_accounts", []);
  console.log(`anvil account[0] = ${acct}`);

  // 1. Deploy Nick's Factory (presigned keyless tx) so CREATE2 works on anvil.
  await send({ from: acct, to: "0x3fAB184622Dc19b6109349B94811493BF2a45362", value: "0x16345785d8a0000" }); // 0.1 ETH
  const raw = "0xf8a58085174876e800830186a08080b853604580600e600039806000f350fe7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe03601600081602082378035828234f58015156039578182fd5b8082525050506014600cf31ba02222222222222222222222222222222222222222222222222222222222222222a02222222222222222222222222222222222222222222222222222222222222222";
  try { const h = await rpc("eth_sendRawTransaction", [raw]); await waitReceipt(h); } catch (e) { /* maybe already there */ }
  (await code(NICKS)).length > 2 ? ok("Nick's Factory deployed @ " + NICKS) : bad("Nick's Factory missing");

  // 2. Deploy bankon_create2_deployer (plain CREATE).
  const wrapR = await send({ from: acct, data: bytecode("bankon_create2_deployer") });
  const wrapper = wrapR.contractAddress;
  (await code(wrapper)).length > 2 ? ok("bankon_create2_deployer @ " + wrapper) : bad("wrapper deploy failed");

  // 3. Plain CREATE with the dependency-free encoder: BankonPriceOracle(owner=acct).
  const poTypes = ctorTypes("BankonPriceOracle");
  const poInit = bytecode("BankonPriceOracle") + (poTypes.length ? encodeParams(poTypes, [acct]) : "");
  const poR = await send({ from: acct, data: poInit });
  (await code(poR.contractAddress)).length > 2 ? ok("plain CREATE BankonPriceOracle @ " + poR.contractAddress) : bad("PriceOracle deploy failed");

  // 4. CREATE2 via wrapper: treasury(founder=acct). Read address from Deployed event.
  const trTypes = ctorTypes("treasury");
  const trInit = bytecode("treasury") + (trTypes.length ? encodeParams(trTypes, [acct]) : "");
  const salt = saltFor("treasury");
  const callData = CREATE2_SELECTOR + encodeParams(["bytes32", "bytes"], [salt, trInit]);
  const c2R = await send({ from: acct, to: wrapper, data: callData });
  const c2Addr = readDeployed(c2R, wrapper);
  c2Addr && (await code(c2Addr)).length > 2 ? ok("CREATE2 treasury @ " + c2Addr + " (read from Deployed event)") : bad("CREATE2 deploy / event read failed");

  // 5. Determinism: same salt+initCode again → CREATE2 collision (address already has code) →
  //    wrapper reverts (status 0). Proves the address is fixed by salt+initCode → same on every chain.
  let collided = false;
  try { const rr = await send({ from: acct, to: wrapper, data: callData }); collided = parseInt(rr.status, 16) === 0; } catch (e) { collided = true; }
  collided ? ok("CREATE2 determinism — redeploy collides at the same address (same on every chain)") : bad("CREATE2 redeploy did not collide");

  // 6. Wire call with the encoder: BankonPriceOracle has AccessControl → grantRole(DEFAULT_ADMIN_ROLE, acct).
  const grantSel = selector("BankonPriceOracle", "grantRole(bytes32,address)");
  const ROLE = "0x0000000000000000000000000000000000000000000000000000000000000000"; // DEFAULT_ADMIN_ROLE
  const wireData = grantSel + encodeParams(["bytes32", "address"], [ROLE, acct]);
  const wR = await send({ from: acct, to: poR.contractAddress, data: wireData });
  parseInt(wR.status, 16) === 1 ? ok("wire call grantRole() succeeded (status 1)") : bad("wire call failed");

  console.log(`\n${pass}/${pass + fail} checks passed`);
  process.exit(fail ? 1 : 0);
}
main().catch((e) => { console.error("ERROR", e.message); process.exit(1); });
