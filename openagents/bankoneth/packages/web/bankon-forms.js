// SPDX-License-Identifier: Apache-2.0
//
// bankon-forms.js — framework-free, DOM-free call-construction core shared by
// the standalone dApp (bankoneth.html) and the parsec view-module
// (packages/parsec-view). Plain ESM JS so both a no-build HTML page and parsec's
// Vite/TS build can import it unchanged.
//
// It owns: manifest/abi/deployment loading, ABI categorisation, input coercion,
// guided-preset argument building, and thin read/write primitives. It deliberately
// does NOT build DOM — each UI renders its own and calls these helpers. `ethers`
// (v6) is passed in by the caller so this module pins no copy of its own.

const ZERO_ADDR = "0x0000000000000000000000000000000000000000";
const ZERO_BYTES32 = "0x" + "0".repeat(64);

// chainId → deployments file basename used by the manifest.
function deploymentFileFor(chainId) {
  if (chainId === 1) return "1.json";
  if (chainId === 11155111) return "11155111.json";
  return "local.json"; // 31337 anvil + anything else dev
}

// ── Loading (base = URL of packages/web/public, no trailing slash) ──────────
export async function loadManifest(base) {
  const r = await fetch(`${base}/bankon.contracts.json`);
  if (!r.ok) throw new Error(`manifest fetch failed: ${r.status}`);
  return r.json();
}

export async function loadAbi(base, contract) {
  // contract: a manifest contracts[] entry (has .abi path) or a bare name.
  const path = typeof contract === "string" ? `abis/${contract}.json` : contract.abi;
  const r = await fetch(`${base}/${path}`);
  if (!r.ok) throw new Error(`abi fetch failed: ${path} (${r.status})`);
  return r.json();
}

export async function loadDeployments(base, chainId) {
  const r = await fetch(`${base}/deployments/${deploymentFileFor(chainId)}`);
  if (!r.ok) throw new Error(`deployments fetch failed for chain ${chainId} (${r.status})`);
  return r.json();
}

// Resolve a deploymentKey → address for the connected chain. Returns null if
// the slot is the zero address (i.e. not yet deployed) so callers can warn.
export function addressFor(deployments, deploymentKey) {
  const a = deployments?.bankon?.[deploymentKey];
  if (!a || a === ZERO_ADDR) return null;
  return a;
}

// ── ABI introspection ───────────────────────────────────────────────────────
export function categorizeAbi(abi) {
  const fns = abi.filter((x) => x.type === "function");
  const isRead = (f) => f.stateMutability === "view" || f.stateMutability === "pure";
  return {
    reads: fns.filter(isRead).sort(byName),
    writes: fns.filter((f) => !isRead(f)).sort(byName),
  };
}
const byName = (a, b) => a.name.localeCompare(b.name);

// Human signature for display, e.g. "register(string,address,uint64,...)".
export function signatureOf(fn) {
  return `${fn.name}(${fn.inputs.map((i) => i.type).join(",")})`;
}

// ── Input coercion: a raw string from a form field → the JS value ethers v6
//    wants for the given ABI type. Throws on malformed input.                  ─
export function coerceArg(type, raw) {
  const t = type.trim();
  if (t.endsWith("]")) {
    // array — accept JSON array text
    const inner = t.slice(0, t.lastIndexOf("["));
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr)) throw new Error(`${type}: expected a JSON array`);
    return arr.map((v) => coerceArg(inner, typeof v === "string" ? v : JSON.stringify(v)));
  }
  if (t === "bool") {
    const s = String(raw).trim().toLowerCase();
    if (s === "true" || s === "1") return true;
    if (s === "false" || s === "0" || s === "") return false;
    throw new Error(`${type}: expected true/false`);
  }
  if (t.startsWith("uint") || t.startsWith("int")) {
    const s = String(raw).trim();
    if (s === "") return 0n;
    return BigInt(s);
  }
  if (t === "address") {
    const s = String(raw).trim();
    return s === "" ? ZERO_ADDR : s;
  }
  if (t === "string") return String(raw);
  if (t === "bytes" || /^bytes\d+$/.test(t)) {
    const s = String(raw).trim();
    return s === "" ? (t === "bytes" ? "0x" : ZERO_BYTES32) : s;
  }
  if (t === "tuple") {
    // tuple — accept JSON object/array text
    return JSON.parse(raw);
  }
  return raw; // unknown — pass through
}

// ── Helpers for guided-preset "controls" ─────────────────────────────────────
export function nowPlusYears(years, nowSeconds) {
  const y = BigInt(years || 1);
  return BigInt(nowSeconds ?? Math.floor(Date.now() / 1000)) + y * 31536000n;
}

// AgentMetadata tuple in the on-chain field order:
// (agentURI, mindxEndpoint, x402Endpoint, algoIDNftDID, contenthash, baseAddress, algoAddr)
export function agentMeta(overrides = {}) {
  return [
    overrides.agentURI ?? "",
    overrides.mindxEndpoint ?? "",
    overrides.x402Endpoint ?? "",
    overrides.algoIDNftDID ?? "",
    overrides.contenthash ?? "0x",
    overrides.baseAddress ?? ZERO_ADDR,
    overrides.algoAddr ?? "0x",
  ];
}

export function namehash(ethers, name) {
  return ethers.namehash(name);
}

// Build the ordered argument array for a guided preset from {fieldName: rawValue}.
// `ctx` supplies { account, ethers, nowSeconds }. Applies field `control`/`fill`.
export function buildPresetArgs(preset, values, ctx) {
  const { ethers, account } = ctx;
  return preset.fields
    .filter((f) => f.control !== "namehashInput" || preset.flow !== "resolve") // resolve handled specially
    .map((f) => {
      let raw = values[f.name];
      if ((raw === undefined || raw === "") && f.fill === "account") raw = account;
      if ((raw === undefined || raw === "") && f.default !== undefined) raw = f.default;

      switch (f.control) {
        case "expiry":
          return raw ? coerceArg(f.type, raw) : nowPlusYears(1, ctx.nowSeconds);
        case "namehash":
          return namehash(ethers, String(raw));
        case "agentMeta":
          return raw ? coerceArg("tuple", raw) : agentMeta();
        default:
          return coerceArg(f.type, raw ?? "");
      }
    });
}

// ── Read / write primitives (ethers v6) ──────────────────────────────────────
export async function readContract({ provider, address, abi, fn, args, ethers }) {
  const c = new ethers.Contract(address, abi, provider);
  return c[fn](...args);
}

export async function writeContract({ signer, address, abi, fn, args, value, ethers }) {
  const c = new ethers.Contract(address, abi, signer);
  const overrides = value !== undefined && value !== null ? { value } : {};
  return c[fn](...args, overrides);
}

// Flow B helper: quote a .eth purchase. Returns { wei, usd6 } as BigInts.
export async function quoteEth({ provider, address, abi, label, durationYears, ethers }) {
  const c = new ethers.Contract(address, abi, provider);
  const [wei_, usd6] = await c.quote(label, BigInt(durationYears || 1));
  return { wei: wei_, usd6 };
}

// Flow B helper: assemble the commit/reveal tuple `p`. `secret` is a random
// bytes32 the caller must keep between the two transactions.
export function buildEthRegistrarParams(ethers, { label, owner, durationYears, secret, resolver }) {
  return {
    label,
    owner,
    durationYears: BigInt(durationYears || 1),
    secret: secret ?? ethers.hexlify(ethers.randomBytes(32)),
    resolver: resolver ?? ZERO_ADDR,
    reverseRecord: false,
    ownerControlledFuses: 0,
  };
}

export const constants = { ZERO_ADDR, ZERO_BYTES32, deploymentFileFor };

// ── Client-side tier resolution (for backend-less consumers: parsec, react) ──
// The web dApp uses the server gate (backend/) for true hiding; parsec/react have
// no server, so they resolve the tier client-side from the same ENS reads. This
// is cosmetic routing only — on-chain AccessControl still enforces every write.
const BANKON_ETH_NODE = "0x79c178642317fc2d61d186f3b412440f06590d8314f126362d6a88929a6cbe1a";
const NAME_WRAPPER = "0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401";
const NW_ABI = [{ type: "function", name: "ownerOf", stateMutability: "view", inputs: [{ name: "id", type: "uint256" }], outputs: [{ name: "", type: "address" }] }];

/** Resolve admin|member|visitor for `address`. `label` (optional) checks a
 *  specific *.bankon.eth the wallet may hold (no on-chain enumeration exists). */
export async function resolveTier({ provider, address, label, ethers }) {
  const nw = new ethers.Contract(NAME_WRAPPER, NW_ABI, provider);
  const ownerOf = async (node) => {
    try { const o = await nw.ownerOf(BigInt(node)); return o === ZERO_ADDR ? null : o; } catch { return null; }
  };
  const root = await ownerOf(BANKON_ETH_NODE);
  if (root && root.toLowerCase() === address.toLowerCase()) return { tier: "admin", address };
  if (label) {
    const sub = ethers.namehash(`${label}.bankon.eth`);
    const o = await ownerOf(sub);
    if (o && o.toLowerCase() === address.toLowerCase()) return { tier: "member", address, names: [`${label}.bankon.eth`] };
  }
  return { tier: "visitor", address };
}
