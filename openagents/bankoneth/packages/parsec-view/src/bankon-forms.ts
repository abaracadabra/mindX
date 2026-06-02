// SPDX-License-Identifier: Apache-2.0
//
// bankon-forms.ts — production (typed) port of packages/web/bankon-forms.js.
// Same call-construction core (manifest/abi/deployment loading, ABI
// categorisation, input coercion, preset arg building, read/write primitives),
// with types for the parsec-view package and any other TS consumer.
//
// `.js` is the prototype (standalone dApp); this `.ts` is the production form.
// Keep the two in lockstep — they implement the same contract.

import type { ethers as Ethers } from "ethers";

type EthersNS = typeof Ethers;

export const ZERO_ADDR = "0x0000000000000000000000000000000000000000";
export const ZERO_BYTES32 = "0x" + "0".repeat(64);

export interface PresetField {
  name: string;
  type: string;
  label?: string;
  placeholder?: string;
  help?: string;
  default?: string;
  optional?: boolean;
  fill?: "account";
  control?: "expiry" | "namehash" | "agentMeta" | "namehashInput";
}

export interface Preset {
  id: string;
  title: string;
  subtitle?: string;
  note?: string;
  contract?: string;
  fn?: string;
  flow?: "commit-reveal" | "resolve";
  mode: "read" | "write";
  payable?: boolean;
  paymentRail?: boolean;
  agenticPlaceToggle?: boolean;
  fields: PresetField[];
}

export interface ContractEntry {
  name: string;
  deploymentKey: string;
  category: string;
  title: string;
  blurb: string;
  abi: string;
  fnCount: number;
}

export interface Manifest {
  generatedFrom: string;
  chains: { id: number; key: string; label: string; deployments: string }[];
  contracts: ContractEntry[];
  presets: Preset[];
}

export interface Deployments {
  chainId: number;
  network: string;
  bankon: Record<string, string>;
  ens: Record<string, string>;
}

export type AbiFn = {
  type: string;
  name: string;
  stateMutability: string;
  inputs: { name: string; type: string; components?: unknown[] }[];
  outputs: { name: string; type: string }[];
};

export function deploymentFileFor(chainId: number): string {
  if (chainId === 1) return "1.json";
  if (chainId === 11155111) return "11155111.json";
  return "local.json";
}

// ── Loading ───────────────────────────────────────────────────────────────
export async function loadManifest(base: string): Promise<Manifest> {
  const r = await fetch(`${base}/bankon.contracts.json`);
  if (!r.ok) throw new Error(`manifest fetch failed: ${r.status}`);
  return r.json();
}

export async function loadAbi(base: string, contract: ContractEntry | string): Promise<AbiFn[]> {
  const path = typeof contract === "string" ? `abis/${contract}.json` : contract.abi;
  const r = await fetch(`${base}/${path}`);
  if (!r.ok) throw new Error(`abi fetch failed: ${path} (${r.status})`);
  return r.json();
}

export async function loadDeployments(base: string, chainId: number): Promise<Deployments> {
  const r = await fetch(`${base}/deployments/${deploymentFileFor(chainId)}`);
  if (!r.ok) throw new Error(`deployments fetch failed for chain ${chainId} (${r.status})`);
  return r.json();
}

export function addressFor(deployments: Deployments | null, deploymentKey: string): string | null {
  const a = deployments?.bankon?.[deploymentKey];
  if (!a || a === ZERO_ADDR) return null;
  return a;
}

// ── ABI introspection ───────────────────────────────────────────────────────
const byName = (a: AbiFn, b: AbiFn) => a.name.localeCompare(b.name);
export function categorizeAbi(abi: AbiFn[]): { reads: AbiFn[]; writes: AbiFn[] } {
  const fns = abi.filter((x) => x.type === "function");
  const isRead = (f: AbiFn) => f.stateMutability === "view" || f.stateMutability === "pure";
  return { reads: fns.filter(isRead).sort(byName), writes: fns.filter((f) => !isRead(f)).sort(byName) };
}

export function signatureOf(fn: AbiFn): string {
  return `${fn.name}(${fn.inputs.map((i) => i.type).join(",")})`;
}

// ── Input coercion ────────────────────────────────────────────────────────
export function coerceArg(type: string, raw: string): unknown {
  const t = type.trim();
  if (t.endsWith("]")) {
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
    return s === "" ? 0n : BigInt(s);
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
  if (t === "tuple") return JSON.parse(raw);
  return raw;
}

// ── Preset helpers ────────────────────────────────────────────────────────
export function nowPlusYears(years: number | string, nowSeconds?: number): bigint {
  const y = BigInt(years || 1);
  return BigInt(nowSeconds ?? Math.floor(Date.now() / 1000)) + y * 31536000n;
}

export function agentMeta(overrides: Record<string, unknown> = {}): unknown[] {
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

export function namehash(ethers: EthersNS, name: string): string {
  return ethers.namehash(name);
}

export interface BuildCtx {
  ethers: EthersNS;
  account: string | null;
  nowSeconds?: number;
}

export function buildPresetArgs(preset: Preset, values: Record<string, string>, ctx: BuildCtx): unknown[] {
  const { ethers, account } = ctx;
  return preset.fields
    .filter((f) => f.control !== "namehashInput" || preset.flow !== "resolve")
    .map((f) => {
      let raw: string | undefined = values[f.name];
      if ((raw === undefined || raw === "") && f.fill === "account") raw = account ?? "";
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

// ── Read / write primitives ─────────────────────────────────────────────────
export async function readContract(o: {
  provider: unknown; address: string; abi: AbiFn[]; fn: string; args: unknown[]; ethers: EthersNS;
}): Promise<unknown> {
  const c = new o.ethers.Contract(o.address, o.abi as never, o.provider as never);
  return (c as never as Record<string, (...a: unknown[]) => Promise<unknown>>)[o.fn](...o.args);
}

export async function writeContract(o: {
  signer: unknown; address: string; abi: AbiFn[]; fn: string; args: unknown[]; value?: bigint; ethers: EthersNS;
}): Promise<{ hash: string; wait: () => Promise<{ blockNumber: number }> }> {
  const c = new o.ethers.Contract(o.address, o.abi as never, o.signer as never);
  const overrides = o.value !== undefined && o.value !== null ? { value: o.value } : {};
  return (c as never as Record<string, (...a: unknown[]) => Promise<{ hash: string; wait: () => Promise<{ blockNumber: number }> }>>)[o.fn](...o.args, overrides);
}

export async function quoteEth(o: {
  provider: unknown; address: string; abi: AbiFn[]; label: string; durationYears: number | string; ethers: EthersNS;
}): Promise<{ wei: bigint; usd6: bigint }> {
  const c = new o.ethers.Contract(o.address, o.abi as never, o.provider as never);
  const [wei_, usd6] = await (c as never as { quote: (l: string, y: bigint) => Promise<[bigint, bigint]> }).quote(o.label, BigInt(o.durationYears || 1));
  return { wei: wei_, usd6 };
}

export function buildEthRegistrarParams(
  ethers: EthersNS,
  o: { label: string; owner: string; durationYears: number | string; secret?: string; resolver?: string },
) {
  return {
    label: o.label,
    owner: o.owner,
    durationYears: BigInt(o.durationYears || 1),
    secret: o.secret ?? ethers.hexlify(ethers.randomBytes(32)),
    resolver: o.resolver ?? ZERO_ADDR,
    reverseRecord: false,
    ownerControlledFuses: 0,
  };
}

export const constants = { ZERO_ADDR, ZERO_BYTES32, deploymentFileFor };
// ── Client-side tier resolution (parsec/react have no server gate) ───────────
const BANKON_ETH_NODE = "0x79c178642317fc2d61d186f3b412440f06590d8314f126362d6a88929a6cbe1a";
const NAME_WRAPPER = "0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401";
const NW_ABI = [{ type: "function", name: "ownerOf", stateMutability: "view", inputs: [{ name: "id", type: "uint256" }], outputs: [{ name: "", type: "address" }] }] as const;

export type Tier = "admin" | "member" | "visitor";

/** Resolve admin|member|visitor from ENS reads. Cosmetic routing only —
 *  on-chain AccessControl still enforces every write. */
export async function resolveTier(o: { provider: unknown; address: string; label?: string; ethers: EthersNS }): Promise<{ tier: Tier; address: string; names?: string[] }> {
  const nw = new o.ethers.Contract(NAME_WRAPPER, NW_ABI as never, o.provider as never);
  const ownerOf = async (node: string): Promise<string | null> => {
    try { const r = await (nw as never as { ownerOf: (id: bigint) => Promise<string> }).ownerOf(BigInt(node)); return r === ZERO_ADDR ? null : r; } catch { return null; }
  };
  const root = await ownerOf(BANKON_ETH_NODE);
  if (root && root.toLowerCase() === o.address.toLowerCase()) return { tier: "admin", address: o.address };
  if (o.label) {
    const sub = o.ethers.namehash(`${o.label}.bankon.eth`);
    const own = await ownerOf(sub);
    if (own && own.toLowerCase() === o.address.toLowerCase()) return { tier: "member", address: o.address, names: [`${o.label}.bankon.eth`] };
  }
  return { tier: "visitor", address: o.address };
}
