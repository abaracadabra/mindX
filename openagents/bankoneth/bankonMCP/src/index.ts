// SPDX-License-Identifier: Apache-2.0
//
// bankonMCP — an MCP proxy that bridges AI/agent MCP clients (Claude, Cursor, mindX agents) to
// remote MCP servers and AUTO-PAYS x402 on their behalf, over BANKON's adaptive rails. It is the
// AgenticPlace payment processor for bankon/mindX service delivery: discover remote tools, re-expose
// them with a prefix, and when a tool returns HTTP 402, pick a rail (Base/Arc/…), pay (EIP-3009
// USDC), retry, and rake the golden φ fee home to bankon.eth.
//
// Adapted from openCMC/x402-mcp-proxy (MIT). Needs `pnpm install` (MCP SDK + ethers).
//   EVM_PRIVATE_KEY=0x… X402_CONFIG=./x402-mcps.json pnpm dev
import { readFileSync } from "node:fs";
import { ethers } from "ethers";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { fetchWithX402, type X402Offer } from "./x402.js";
import { AdaptiveRails, DEFAULT_POLICY } from "./rails.js";
import { AgenticPlaceProcessor } from "./agenticplace.js";

interface RemoteMCP { name: string; url: string; }
interface Config { remotes: RemoteMCP[] }

function loadConfig(): Config {
  if (process.env.X402_REMOTE_MCPS) return { remotes: JSON.parse(process.env.X402_REMOTE_MCPS) };
  const path = process.env.X402_CONFIG || "./x402-mcps.json";
  try { return JSON.parse(readFileSync(path, "utf8")); } catch { return { remotes: [] }; }
}

const wallet = new ethers.Wallet(process.env.EVM_PRIVATE_KEY || ethers.Wallet.createRandom().privateKey);
const rails = new AdaptiveRails(DEFAULT_POLICY);
const processor = new AgenticPlaceProcessor();
const pick = (offers: X402Offer[]) => rails.pick(offers);

// Minimal JSON-RPC call to a remote MCP server over HTTP, paying x402 if challenged.
async function remoteCall(remote: RemoteMCP, method: string, params: unknown): Promise<any> {
  const body = JSON.stringify({ jsonrpc: "2.0", id: 1, method, params });
  const res = await fetchWithX402(remote.url, { method: "POST", headers: { "content-type": "application/json" }, body }, wallet, pick);
  if (res.headers.get("x-payment-response")) {
    // a payment settled — accrue the golden fee + report to AgenticPlace
    const last = rails.lastOffer;
    if (last) { rails.charge(BigInt(last.maxAmountRequired));
      await processor.record({ tool: method, network: last.network, asset: last.asset, amount: BigInt(last.maxAmountRequired), resource: last.resource || remote.url, payTo: last.payTo, ts: Date.now() }); }
  }
  const j = await res.json();
  if (j.error) throw new Error(j.error.message || "remote MCP error");
  return j.result;
}

async function main() {
  const cfg = loadConfig();
  const server = new Server({ name: "bankon-mcp", version: "0.1.0" }, { capabilities: { tools: {} } });

  // Aggregate remote tools, prefixed by server name (e.g. cmc_get_quotes).
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    const tools: any[] = [];
    for (const r of cfg.remotes) {
      try { const res = await remoteCall(r, "tools/list", {}); for (const t of res.tools || []) tools.push({ ...t, name: `${r.name}_${t.name}` }); }
      catch { /* skip unreachable remote */ }
    }
    return { tools };
  });

  // Route a tool call to its remote, paying x402 as needed.
  server.setRequestHandler(CallToolRequestSchema, async (req) => {
    const full = req.params.name; const us = full.indexOf("_");
    const remote = cfg.remotes.find((r) => full.startsWith(r.name + "_"));
    if (!remote) throw new Error(`unknown tool ${full}`);
    const toolName = full.slice(remote.name.length + 1);
    return remoteCall(remote, "tools/call", { name: toolName, arguments: req.params.arguments });
  });

  await server.connect(new StdioServerTransport());
  console.error(`bankon-mcp up · payer ${wallet.address} · ${cfg.remotes.length} remote(s) · treasury ${processor.treasury}`);
}

main().catch((e) => { console.error("bankon-mcp fatal:", e); process.exit(1); });
