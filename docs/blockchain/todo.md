# docs/blockchain — TODO

Follow-ups for the agnostic market-data clients + x402 payment rails shipped in
this folder. Nothing here is required for the modules to run standalone; these
are the integration and hardening steps deferred from the build.

## Shipped (for context)
- `cmc_client.py` — CoinMarketCap (key REST + keyless + x402), `.env` autoload,
  `market_data_provider` protocol, `ttl_cache`.
- `coingecko_client.py` — `coingecko_public_client` (free) + `coingecko_pro_client`
  (ingestion).
- `defillama_client.py` — `defillama_public_client` (free multi-host) +
  `defillama_pro_client` (Pro, key-in-path).
- `x402_signer.py` — EIP-3009 / EIP-712 Base-USDC signer; key from `.env`.
- `x402_rails.py` — `X402RailsService`: credential issuance as a service.
- `x402_rails_service.py` — mountable FastAPI router + standalone app.
- `x402rails.agent` — service manifest.
- Guides: `coingecko_integration_guide.md`, `defillama_client.md`.
- Tests: `test_coingecko_client.py`, `test_defillama_client.py`,
  `test_x402_signer.py`, `test_x402_rails.py`, `test_x402_rails_service.py`
  (51 passing, offline).

## High priority
- [ ] **Move the x402 signing key to the BANKON vault.** Replace the
  `.env` (`X402_WALLET_PRIVATE_KEY`) read in `x402_signer._resolve_private_key`
  with a vault fetch (see `manage_credentials.py` / `vault_bankon/`), falling
  back to `.env` for local dev. Key must never hit disk or logs. Vault id
  suggestion: `x402.wallet:base:pk`.
- [ ] **Mount the rails into the backend behind the real gate.** In
  `mindx_backend_service/main_service.py`:
  ```python
  from mindx_backend_service.security_middleware import require_admin_access
  import x402_rails_service
  x402_rails_service.mount(app, spend_guard=require_admin_access)
  ```
  Requires `docs/blockchain/` on the backend import path (it is not a package
  today — add an `__init__.py` or a `sys.path` entry, or relocate the modules
  into a real package).
- [ ] **Add the routes to the STRICT-mode landing allowlist** if the public
  `GET /x402/rails/{describe,rails}` should be reachable without a session (see
  the landing-page strict-gate notes; default-deny otherwise).

## Medium priority
- [ ] **Register the Algorand rail.** Wrap `tools/x402_avm_client` as a
  `wallet_signer` and `X402RailsService.register_rail("algorand", signer,
  networks=("algorand:mainnet",))`. An `eip155` challenge can't be paid from
  Algorand and vice versa — keep each rail its own wallet behind the seam.
- [ ] **Run `ruff format` / `ruff check` / `mypy`** on all modules + tests.
  Neither tool is installed in the current environment; this is a CI/dev-box
  step. Target the repo's `pyproject.toml` config (ruff py39, mypy 3.9).
- [ ] **Wire credential issuance into the catalogue.** Emit a `tool.invoke` /
  `tool.result` (or a new `payment.*`) catalogue event per issued credential so
  the audit ledger is durable, not just in-process (`agents/catalogue/`).
- [ ] **Persist the rails ledger.** `X402RailsService._ledger` is session-only;
  append issued-credential metadata (never the key) to a JSONL sink for audit.

## Low priority / deferred
- [ ] **Wire data clients into a consumer.** `cmc_client` and friends have no
  call sites yet (they ship as agnostic peers). Candidate: an ingestion
  projector that backfills market data into pgvector/memory.
- [ ] **CoinGecko on-chain (GeckoTerminal) paths** in `coingecko_pro_client.onchain`
  are passed through, not enumerated — confirm the stable sub-paths when used.
- [ ] **Single-use nonce tracking.** EIP-3009 nonces are random per credential;
  if replay protection beyond the contract's own guard is wanted, track issued
  nonces in the ledger.
- [ ] **CMC x402 header name.** `cmc_x402_client` sends the canonical `X-PAYMENT`;
  if CMC's live endpoint expects a different header, set `payment_header=` (the
  constructor already supports the override) and update the guide.
- [ ] **Publish a `defillama` integration guide PDF→md** parity check, or keep
  deferring to the existing PDF (`docs/publications/`).
