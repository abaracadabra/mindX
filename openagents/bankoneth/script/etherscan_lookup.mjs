#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0
//
// etherscan_lookup.mjs — small helper around the Etherscan V2 API + an RPC, used
// by docs/ops and (optionally) the gate backend for ABI hydration.
//
// Etherscan V2: ONE key, all chains via https://api.etherscan.io/v2/api?chainid=<id>.
// Set ETHERSCAN_API_KEY in env (never commit). See docs/ETHERSCAN.md.
//
// Usage:
//   node script/etherscan_lookup.mjs abi    <address> [chainId=1]   # verified ABI
//   node script/etherscan_lookup.mjs source <address> [chainId=1]   # verified source meta
//   node script/etherscan_lookup.mjs owner  [name=bankon.eth] [rpc] # ENS owner via NameWrapper
//   node script/etherscan_lookup.mjs verifystatus <guid> [chainId=1]
const V2 = "https://api.etherscan.io/v2/api";
const KEY = process.env.ETHERSCAN_API_KEY || "";
const DEFAULT_RPC = process.env.MAINNET_RPC || process.env.BANKON_GATE_RPC || "https://ethereum-rpc.publicnode.com";
const NAME_WRAPPER = "0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401";
const REGISTRY = "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e";

function requireKey() {
  if (!KEY) { console.error("ETHERSCAN_API_KEY not set (env or vault). See docs/ETHERSCAN.md."); process.exit(2); }
}

async function etherscan(params, chainId = "1") {
  requireKey();
  const u = new URL(V2);
  u.searchParams.set("chainid", String(chainId));
  for (const [k, v] of Object.entries(params)) u.searchParams.set(k, v);
  u.searchParams.set("apikey", KEY);
  const r = await fetch(u);
  const j = await r.json();
  if (j.status === "0" && j.message !== "OK" && !j.result) throw new Error(`etherscan: ${j.message} ${j.result || ""}`);
  return j;
}

// Pinned namehashes (avoids a keccak dependency for the common case).
const KNOWN_NODES = { "bankon.eth": "0x79c178642317fc2d61d186f3b412440f06590d8314f126362d6a88929a6cbe1a" };

async function rpc(rpcUrl, to, data) {
  const r = await fetch(rpcUrl, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "eth_call", params: [{ to, data }, "latest"] }),
  });
  const j = await r.json();
  if (j.error) throw new Error(j.error.message);
  return j.result;
}
const addrFrom32 = (hex) => "0x" + hex.slice(-40);

async function main() {
  const [cmd, a, b] = process.argv.slice(2);
  if (cmd === "abi") {
    const j = await etherscan({ module: "contract", action: "getabi", address: a }, b || "1");
    console.log(j.result);
  } else if (cmd === "source") {
    const j = await etherscan({ module: "contract", action: "getsourcecode", address: a }, b || "1");
    const s = j.result?.[0] || {};
    console.log(JSON.stringify({ ContractName: s.ContractName, CompilerVersion: s.CompilerVersion, Proxy: s.Proxy, Implementation: s.Implementation, verified: !!s.ABI && s.ABI !== "Contract source code not verified" }, null, 2));
  } else if (cmd === "verifystatus") {
    const j = await etherscan({ module: "contract", action: "checkverifystatus", guid: a }, b || "1");
    console.log(JSON.stringify(j, null, 2));
  } else if (cmd === "owner") {
    const name = a || "bankon.eth";
    const node = KNOWN_NODES[name];
    if (!node) { console.error(`no pinned node for ${name} (add to KNOWN_NODES or pass node)`); process.exit(2); }
    const rpcUrl = b || DEFAULT_RPC;
    // ownerOf(uint256) selector 0x6352211e
    const wrapped = addrFrom32(await rpc(rpcUrl, NAME_WRAPPER, "0x6352211e" + node.slice(2)));
    // registry owner(bytes32) selector 0x02571be3
    const regOwner = addrFrom32(await rpc(rpcUrl, REGISTRY, "0x02571be3" + node.slice(2)));
    const isWrapped = regOwner.toLowerCase() === NAME_WRAPPER.toLowerCase();
    console.log(JSON.stringify({ name, node, wrapped: isWrapped, owner: isWrapped ? wrapped : regOwner, nameWrapperOwner: wrapped, registryOwner: regOwner }, null, 2));
  } else {
    console.error("usage: etherscan_lookup.mjs <abi|source|owner|verifystatus> <arg> [chainId|rpc]");
    process.exit(1);
  }
}
main().catch((e) => { console.error(String(e.message || e)); process.exit(1); });
