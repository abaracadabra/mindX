# CoinMarketCap + x402 — ingestion, pricing, and MCP delivery (operations)

How bankoneth ingests **CoinMarketCap** data and delivers it (and bankon/mindX services) over **x402**,
with proper API-key handling. Covers the EVM / Arc / Base sides.

## Two ingestion paths

| Path | When | Key? | Where |
|---|---|---|---|
| **Keyed (`cmc` CLI)** | bulk/structured pulls, holder-gated prices | server-side CMC key | `x402evm/clients/cmc_cli.mjs` → `cmc` Go CLI |
| **x402 (pay-per-call)** | keyless, agent-driven, on-chain settled | none (pays USDC) | `x402evm/clients/cmc_x402_ingest.mjs` |

### Keyed path — the `cmc` CLI
Install the Go CLI (github.com/openCMC/CoinMarketCap-CLI):
```bash
brew install openCMC/CoinMarketCap-CLI/cmc
# or: curl -sSfL https://raw.githubusercontent.com/openCMC/CoinMarketCap-CLI/main/install.sh | sh
```
`cmc_cli.mjs` wraps it, loading the key from the bankoneth-root **`.bankonchains.env`** (or `CMC_API_KEY`).
Commands: `resolve`, `price`, `search`, `markets`, `history`, `news`, `pairs`, `monitor`, `tui` — JSON by
default. Respect the **Basic plan**: 30 req/min, 10k/month — cache and batch.

### x402 path — pay-per-call
`cmc_x402_ingest.mjs` is the **x402 payer**: GET a CMC x402 resource → parse the `402` challenge → sign an
**EIP-3009 USDC `transferWithAuthorization`** → resend with the `X-PAYMENT` header → ingest the JSON. No
key; pays USDC on Base/Arc. Confirm the exact endpoint + network at
`https://pro.coinmarketcap.com/api/documentation/ai-agent-hub/x402` (and `coinmarketcap.com/api/x402/`).
```bash
X402_PK=0x<usdc-funded-key> node x402evm/clients/cmc_x402_ingest.mjs "<cmc-x402-url>"
```

## API-key handling (mandatory)
- The CMC key is **server-side only** and lives **OUTSIDE the web root** in the gitignored
  **`.bankonchains.env`** (bankoneth root) — a static host would serve anything under `packages/web/`.
- The browser **never** receives it. Public visitors get **keyless spot prices** (`bankonchains/price.js`);
  **holders** of `bankon.eth` / `*.bankon.eth` get **CoinMarketCap** prices via the `cmc-proxy`
  (`X-CMC_PRO_API_KEY` header, batched `quotes/latest`, cache ≥120s, 429→stale). See
  `packages/web/bankonchains/README.md`.
- `.htaccess` + `.gitignore` are defense-in-depth; the canonical secret is never committed.

## MCP delivery — `bankonMCP/`
`bankonMCP/` is the AgenticPlace **payment processor** for MCP service delivery: it proxies MCP tool
calls, **auto-pays x402** on the cheapest adaptive rail (Base/Arc/…), and rakes the **golden φ/10 fee**
home to `bankon.eth`. Remote MCP servers (CMC AI-Agent-Hub, bankon, mindX) are re-exposed as
`cmc_*` / `bankon_*` / `mindx_*` tools.
```bash
cd bankonMCP && pnpm install && cp .env.example .env   # EVM_PRIVATE_KEY (USDC payer), AGENTICPLACE_URL
pnpm dev
```

## On-chain settlement
Payments settle through **`x402evm/`** (`X402EVMFacilitator` on Base/Arc/…). The φ fee → RAKE economics
are the cp2048 standard (`docs/SCIENTIFIC_AND_RAKE.md`). x402 rail family + receipt shapes:
`docs/blockchain/X402_EVM.md`.

## Quick reference
| Thing | Value |
|---|---|
| CMC key location | `<bankoneth>/.bankonchains.env` (gitignored, outside web root) |
| Holder price source | CoinMarketCap (via cmc-proxy) |
| Public price source | Coinbase spot (keyless) |
| x402 payer | EIP-3009 USDC authorization on Base/Arc |
| Treasury / RAKE home | `bankon.eth` `0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169` |
| CMC plan | Basic — 30 req/min, 10k/month, 14 endpoints, 1 conversion/req |
