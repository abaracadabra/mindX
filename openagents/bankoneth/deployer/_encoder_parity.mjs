// Dev-only: assert deployer.js's dependency-free ABI encoder matches `cast abi-encode`.
// Mirrors the encode* functions in deployer.js. NOT shipped (delete after run).
import { execFileSync } from "node:child_process";

const strip = (s) => (s || "").replace(/^0x/i, "");
const utf8hex = (s) => Buffer.from(s, "utf8").toString("hex");
const uint256Hex = (n) => BigInt(n).toString(16).padStart(64, "0");
const isDynamic = (t) => t === "string" || t === "bytes" || t.endsWith("[]");
function parseArrayLiteral(value) { if (Array.isArray(value)) return value; const s = (value == null ? "" : String(value)).trim(); if (!s || s === "[]") return []; try { const j = JSON.parse(s); return Array.isArray(j) ? j : []; } catch (e) {} return s.replace(/^\[|\]$/g, "").split(",").map((x) => x.trim()).filter((x) => x.length); }
function encodeStatic(type, value) {
  if (type === "address") return strip(value).toLowerCase().padStart(64, "0");
  if (/^u?int(\d*)$/.test(type)) return uint256Hex(value || 0);
  if (type === "bool") return (value === "true" || value === true ? "1" : "0").padStart(64, "0");
  if (/^bytes([1-9]|[12]\d|3[0-2])$/.test(type)) return strip(value).padEnd(64, "0");
  throw new Error(`static ${type}`);
}
function encodeBytesBlob(rawHex) {
  const len = rawHex.length / 2;
  const padded = rawHex.length ? rawHex.padEnd(Math.ceil(rawHex.length / 64) * 64, "0") : "";
  return uint256Hex(len) + padded;
}
function encodeDynamic(type, value) {
  if (type === "string") return encodeBytesBlob(utf8hex(value || ""));
  if (type === "bytes") return encodeBytesBlob(strip(value || "0x"));
  if (type.endsWith("[]")) { const base = type.slice(0, -2); const arr = parseArrayLiteral(value); return uint256Hex(arr.length) + arr.map((el) => encodeStatic(base, el)).join(""); }
  throw new Error(`dynamic ${type}`);
}
function encodeParams(types, values) {
  const headLen = 32 * types.length; const heads = [], tails = []; let dyn = headLen;
  for (let i = 0; i < types.length; i++) { const t = types[i], v = values[i]; if (isDynamic(t)) { heads.push(uint256Hex(dyn)); const tail = encodeDynamic(t, v); tails.push(tail); dyn += tail.length / 2; } else heads.push(encodeStatic(t, v)); }
  return heads.join("") + tails.join("");
}
const cast = (sig, vals) => strip(execFileSync("cast", ["abi-encode", sig, ...vals], { encoding: "utf8" }).trim());

const CASES = [
  ["f(string,string,address)", ["BANKON Agent Registry", "AGENT", "0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169"]],
  ["f(address,address,bytes32,address,address,address,address,address)",
    ["0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401", "0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63",
     "0x79c178642317fc2d61d186f3b412440f06590d8314f126362d6a88929a6cbe1a",
     "0x0000000000000000000000000000000000000001", "0x0000000000000000000000000000000000000002",
     "0x0000000000000000000000000000000000000003", "0x0000000000000000000000000000000000000004",
     "0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169"]],
  ["f(address,string)", ["0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169", "https://agenticplace.pythai.net/x402/listing"]],
  ["f(address,address[],uint256)", ["0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169", "[]", "1"]],
  ["f(address,address[],uint256)", ["0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169", "[0x0000000000000000000000000000000000000005,0x0000000000000000000000000000000000000006]", "2"]],
  ["f(bytes32,address)", ["0x4b6d7bfbdfd4dba4dace8bd7020a81117ab633e3a677498b9e92d1b899379d26", "0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169"]],
  ["f(uint256,bool,bytes32)", ["1000000000000000000000000", "true", "0x0000000000000000000000000000000000000000000000000000000000000000"]],
];

let ok = 0;
for (const [sig, vals] of CASES) {
  const types = sig.slice(2, -1).split(",");
  // cast wants array literals with bracketed comma form; our encoder takes the JSON string.
  const castVals = vals.map((v) => (v.startsWith("[") ? v.replace(/[\[\]]/g, (m) => m).replace(/,/g, ",") : v));
  const mine = encodeParams(types, vals);
  const ref = cast(sig, castVals);
  if (mine === ref) { ok++; console.log(`OK  ${sig}`); }
  else { console.log(`FAIL ${sig}\n  mine: ${mine}\n  cast: ${ref}`); }
}
console.log(`\n${ok}/${CASES.length} encoder cases match cast abi-encode`);
process.exit(ok === CASES.length ? 0 : 1);
