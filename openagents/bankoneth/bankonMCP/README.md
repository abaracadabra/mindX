# bankonMCP — MCP × x402 adaptive-rails proxy

The **AgenticPlace payment processor** for **BANKON / mindX service delivery over MCP**. It bridges
AI/agent MCP clients (Claude, Cursor, mindX agents) to remote MCP servers and **auto-pays x402** on
their behalf, choosing the cheapest available **adaptive rail** (Base / Arc / Optimism / …) and raking
the golden **φ fee** home to `bankon.eth`.

Adapted from **[openCMC/x402-mcp-proxy](https://github.com/openCMC/x402-mcp-proxy)** (MIT, TypeScript).

## Flow
```
MCP client (Claude / mindX agent)
        │  stdio
        ▼
   bankonMCP  ──┬─ discover remote tools (re-exposed as `cmc_…`, `bankon_…`, `mindx_…`)
                ├─ tool call → remote MCP (HTTP)
                ├─ HTTP 402? → AdaptiveRails.pick() → EIP-3009 USDC pay → X-PAYMENT → retry
                └─ on settle → AgenticPlace processor: φ fee → RAKE (bankon.eth) + report
        │  HTTP + x402
        ▼
   remote MCP servers (CoinMarketCap AI-Agent-Hub, bankon, mindX, …)
```

## Modules (`src/`)
- **`x402.ts`** — the x402 payer: parses the 402 challenge, signs an EIP-3009 USDC
  `transferWithAuthorization`, builds the `X-PAYMENT` header, retries.
- **`rails.ts`** — `AdaptiveRails`: pick the rail by network allowlist + per-call cap + session budget
  + preference order (cheapest/fastest first). The "x402 adaptive rails."
- **`agenticplace.ts`** — `AgenticPlaceProcessor`: computes the **golden φ/10 fee** (same rate as the
  cp2048 on-chain fee), accrues it toward the `bankon.eth` treasury, and reports settlements to
  AgenticPlace for service-delivery accounting.
- **`index.ts`** — the MCP server (stdio) that aggregates remote tools and routes calls through x402.

## Run
```bash
pnpm install
cp .env.example .env          # set EVM_PRIVATE_KEY (a USDC-funded payer), AGENTICPLACE_URL
cp x402-mcps.example.json x402-mcps.json
pnpm dev                      # or: pnpm build && pnpm start
```
Register with Claude Desktop / Cursor as a stdio MCP server (`command: node`, `args: [dist/index.js]`).

## Safety
Per-call USDC cap + session budget + network allowlist (`rails.ts` `RailPolicy`). The payer key is
**server-side only** (`.env`, gitignored); never shipped to a client. Settlement authority is the
on-chain x402evm/cp2048 contracts — this proxy is the off-chain router + processor ledger.

## Relationship to the rest of bankoneth
- Pays into the **`x402evm/`** `X402EVMFacilitator` rails (Base / Arc / …).
- Uses the **`bankonchains/`** chain registry + price layer.
- Delivers **bankon + mindX** services priced in USD, settled in USDC, raked to `bankon.eth`.
