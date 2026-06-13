// SPDX-License-Identifier: Apache-2.0
//
// bankoneth CCIP-Read gateway (Phase 2.2).
//
// Spec: EIP-3668 + BankonOffchainResolver.sol. The contract reverts with
// OffchainLookup → client picks a URL → POSTs {sender, data} → we look up
// the record from our store, EIP-712-sign the response, return JSON.
//
// Single-file Bun+Hono service. Records persisted to a JSON file. Swap to
// SQLite + IPFS-mirror via Lighthouse in production; the JSON store is
// good enough for the rehearsal phase.

import { Hono } from "hono";
import {
  type Address,
  type Hex,
  createWalletClient,
  http,
  encodeAbiParameters,
  decodeAbiParameters,
  keccak256,
  privateKeyToAccount,
} from "viem";
import { mainnet, sepolia } from "viem/chains";
import { readFileSync, writeFileSync, existsSync } from "node:fs";

// ── Config ────────────────────────────────────────────────────────

const PORT         = Number(process.env.GATEWAY_PORT ?? 8888);
const RESOLVER     = (process.env.RESOLVER_ADDR     ?? "") as Address;
const CHAIN_ID     = Number(process.env.CHAIN_ID    ?? 1);
const SIGNER_PK    = (process.env.SIGNER_PK         ?? "") as Hex;
const STORE_PATH   = process.env.STORE_PATH         ?? "./gateway-records.json";
const TTL_SECONDS  = Number(process.env.TTL_SECONDS ?? 3600);
const PARENT_NODE  = (process.env.PARENT_NODE       ?? "") as Hex;

if (!RESOLVER || !SIGNER_PK || !PARENT_NODE) {
  console.error(
    "Missing required env: RESOLVER_ADDR, SIGNER_PK, PARENT_NODE.\n" +
    "Optional: GATEWAY_PORT (default 8888), CHAIN_ID (default 1),\n" +
    "          STORE_PATH (default ./gateway-records.json), TTL_SECONDS (default 3600)."
  );
  process.exit(1);
}

const signer = privateKeyToAccount(SIGNER_PK);

console.log(`[gateway] signer:    ${signer.address}`);
console.log(`[gateway] resolver:  ${RESOLVER}`);
console.log(`[gateway] chainId:   ${CHAIN_ID}`);
console.log(`[gateway] store:     ${STORE_PATH}`);
console.log(`[gateway] TTL:       ${TTL_SECONDS}s`);

// ── Store ─────────────────────────────────────────────────────────

interface SubnameRecord {
  /** Lowercase label, e.g. "alice". */
  label: string;
  /** EOA the addr(node) read should resolve to. */
  owner: Address;
  /** Optional text records keyed by ENSIP-5 key (avatar, url, …). */
  text?: Record<string, string>;
  /** Optional contenthash bytes hex (ENSIP-7, e.g. ipfs://…). */
  contenthash?: Hex;
  /** Sparse multichain addrs by ENSIP-11 coinType → bytes hex. */
  coinAddr?: Record<number, Hex>;
  /** Unix-seconds first-recorded. */
  recordedAt: number;
}

type Store = Record<string, SubnameRecord>; // labelhash (lowercased hex) → record

function loadStore(): Store {
  if (!existsSync(STORE_PATH)) return {};
  try {
    return JSON.parse(readFileSync(STORE_PATH, "utf-8")) as Store;
  } catch (e) {
    console.error("[store] corrupt JSON, starting empty:", e);
    return {};
  }
}

function saveStore(s: Store): void {
  writeFileSync(STORE_PATH, JSON.stringify(s, null, 2));
}

let store: Store = loadStore();
console.log(`[gateway] loaded ${Object.keys(store).length} records`);

// ── EIP-712 domain ────────────────────────────────────────────────

const EIP712_DOMAIN = {
  name: "BankonOffchainResolver",
  version: "1",
  chainId: CHAIN_ID,
  verifyingContract: RESOLVER,
} as const;

const RESPONSE_TYPES = {
  OffchainLookupResponse: [
    { name: "result",    type: "bytes"   },
    { name: "expires",   type: "uint64"  },
    { name: "sender",    type: "address" },
    { name: "callHash",  type: "bytes32" },
  ],
} as const;

// ── DNS-encoded name → labelhash + namehash ──────────────────────

function decodeDnsName(dnsName: Hex): { labels: string[]; node: Hex } {
  const bytes = Uint8Array.from(
    dnsName.slice(2).match(/.{2}/g)!.map(h => parseInt(h, 16))
  );
  const labels: string[] = [];
  let offset = 0;
  while (offset < bytes.length) {
    const len = bytes[offset]!;
    if (len === 0) break;
    labels.push(new TextDecoder().decode(bytes.subarray(offset + 1, offset + 1 + len)));
    offset += 1 + len;
  }
  // namehash, bottom-up
  let node: Hex = "0x" + "00".repeat(32) as Hex;
  for (let i = labels.length - 1; i >= 0; i--) {
    const labelHash = keccak256(new TextEncoder().encode(labels[i]!));
    node = keccak256(
      ("0x" + node.slice(2) + labelHash.slice(2)) as Hex
    );
  }
  return { labels, node };
}

// ── ENS resolver selectors we answer ─────────────────────────────

const SEL_ADDR        = "0x3b3b57de" as Hex;  // addr(bytes32)
const SEL_ADDR_MULTI  = "0xf1cb7e06" as Hex;  // addr(bytes32,uint256)
const SEL_TEXT        = "0x59d1d43c" as Hex;  // text(bytes32,string)
const SEL_CONTENTHASH = "0xbc1c58d1" as Hex;  // contenthash(bytes32)

const ZERO_ADDR = "0x0000000000000000000000000000000000000000" as Address;

// ── HTTP routes ──────────────────────────────────────────────────

const app = new Hono();

/** Health probe — operators wire this into uptime monitors. */
app.get("/health", c => c.json({
  ok: true,
  records: Object.keys(store).length,
  signer: signer.address,
  resolver: RESOLVER,
  chainId: CHAIN_ID,
}));

/**
 * CCIP-Read entry. Per EIP-3668, the spec says the client POSTs
 *   { sender: "0x...", data: "0x..." }
 * and we return JSON `{ data: "0x...signedResponse" }`. The client then
 * calls resolveWithProof(response, extraData) on the on-chain resolver.
 */
app.post("/", async c => {
  let body: { sender?: string; data?: string };
  try {
    body = await c.req.json();
  } catch {
    return c.json({ error: "invalid JSON" }, 400);
  }
  const sender = (body.sender ?? "").toLowerCase() as Address;
  const data   = (body.data   ?? "") as Hex;

  if (sender.toLowerCase() !== RESOLVER.toLowerCase()) {
    return c.json({ error: "sender mismatch" }, 400);
  }
  if (!data || !data.startsWith("0x")) {
    return c.json({ error: "invalid data" }, 400);
  }

  const selector = data.slice(0, 10) as Hex;
  const callBody = data.slice(10);

  let result: Hex;
  try {
    result = await resolveCalldata(selector, callBody);
  } catch (e: any) {
    console.error("[resolve] err:", e?.message ?? e);
    return c.json({ error: "resolve failed" }, 500);
  }

  // EIP-712 signed response: (result, expires, sender, callHash).
  const expires = Math.floor(Date.now() / 1000) + TTL_SECONDS;
  const callHash = keccak256(data);

  const signature = await signer.signTypedData({
    domain: EIP712_DOMAIN,
    types: RESPONSE_TYPES,
    primaryType: "OffchainLookupResponse",
    message: {
      result,
      expires: BigInt(expires),
      sender,
      callHash,
    },
  });

  const responseHex = encodeAbiParameters(
    [
      { name: "result",    type: "bytes"   },
      { name: "expires",   type: "uint64"  },
      { name: "signature", type: "bytes"   },
    ],
    [result, BigInt(expires), signature],
  );

  return c.json({ data: responseHex });
});

/**
 * Admin endpoint — the on-chain event listener calls this on
 * OffchainSubnameClaimed to persist the new record. Authenticated by a
 * shared secret (Authorization: Bearer <secret>) so an attacker can't
 * mint arbitrary records. The watcher is a separate process; we don't
 * embed event-listening here.
 */
app.post("/admin/claims", async c => {
  const auth = c.req.header("Authorization") ?? "";
  if (auth !== `Bearer ${process.env.ADMIN_SECRET ?? ""}` || !process.env.ADMIN_SECRET) {
    return c.json({ error: "unauthorized" }, 401);
  }
  const claim = await c.req.json() as { label: string; owner: Address; recordsCid?: string };
  const labelHashHex = keccak256(new TextEncoder().encode(claim.label));
  store[labelHashHex] = {
    label: claim.label,
    owner: claim.owner,
    text: {},
    coinAddr: {},
    recordedAt: Math.floor(Date.now() / 1000),
  };
  saveStore(store);
  console.log(`[admin] persisted ${claim.label} -> ${claim.owner}`);
  return c.json({ ok: true, label: claim.label });
});

// ── Resolver dispatch ────────────────────────────────────────────

async function resolveCalldata(selector: Hex, body: string): Promise<Hex> {
  // Body is the abi-encoded args after the 4-byte selector. First slot is
  // always the node (bytes32). The remainder varies per call.
  const buf = ("0x" + body) as Hex;

  switch (selector) {
    case SEL_ADDR: {
      const [node] = decodeAbiParameters([{ type: "bytes32" }], buf);
      const rec = lookupByNode(node);
      const addr = rec?.owner ?? ZERO_ADDR;
      return encodeAbiParameters([{ type: "address" }], [addr]);
    }
    case SEL_ADDR_MULTI: {
      const [node, coinType] = decodeAbiParameters(
        [{ type: "bytes32" }, { type: "uint256" }], buf
      );
      const rec = lookupByNode(node);
      if (!rec) return encodeAbiParameters([{ type: "bytes" }], ["0x"]);
      if (coinType === 60n) {
        // ENSIP-1: addr(node, 60) == addr(node).
        const packed = ("0x" + rec.owner.slice(2)) as Hex;
        return encodeAbiParameters([{ type: "bytes" }], [packed]);
      }
      const value = rec.coinAddr?.[Number(coinType)];
      return encodeAbiParameters([{ type: "bytes" }], [(value ?? "0x") as Hex]);
    }
    case SEL_TEXT: {
      const [node, key] = decodeAbiParameters(
        [{ type: "bytes32" }, { type: "string" }], buf
      );
      const rec = lookupByNode(node);
      const value = rec?.text?.[key] ?? "";
      return encodeAbiParameters([{ type: "string" }], [value]);
    }
    case SEL_CONTENTHASH: {
      const [node] = decodeAbiParameters([{ type: "bytes32" }], buf);
      const rec = lookupByNode(node);
      const value = (rec?.contenthash ?? "0x") as Hex;
      return encodeAbiParameters([{ type: "bytes" }], [value]);
    }
    default:
      // Unknown selector — return empty bytes. The resolver treats this
      // as "no record" per ENSIP-10.
      return "0x" as Hex;
  }
}

function lookupByNode(node: Hex): SubnameRecord | undefined {
  // node = keccak256(parentNode || labelhash). Iterate stored labels +
  // recompute. For a real-world gateway, persist (labelhash → record) and
  // also (node → labelhash) so this is O(1); the JSON store is the
  // rehearsal MVP.
  for (const [labelHashHex, rec] of Object.entries(store)) {
    const candidate = keccak256(
      ("0x" + PARENT_NODE.slice(2) + labelHashHex.slice(2)) as Hex
    );
    if (candidate === node) return rec;
  }
  return undefined;
}

// ── Boot ─────────────────────────────────────────────────────────

export default {
  port: PORT,
  fetch: app.fetch,
};

console.log(`[gateway] listening on :${PORT}`);
