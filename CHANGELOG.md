# Changelog

All notable changes for the ETHGlobal Open Agents submission window are documented here.

## [1.0.0-ethglobal] — 2026-05-02

> ETHGlobal Open Agents submission cut. **163 tests passing** across 7 suites; **9 live consoles** at `https://mindx.pythai.net/`; CI green on every job.

### Added — Component UIs (no mocks, real backend wiring)

- `/keeperhub` — auto-polls `/p2p/keeperhub/info` every 30s, renders dual-rail Base+Tempo challenge envelope, supported networks, exposed paid endpoints
- `/uniswap` — MetaMask + Sepolia chain switch, live V4 Quoter `eth_call` (read-only, no funds), persona constraints panel, BDI decision-trace viewer; pre-filled with Sepolia WETH/USDC for one-click quotes
- `/bankon-ens` — real ENS resolver against any name (via public mainnet RPC or wallet-attached provider), text record display, 29-fuzz test list
- `/zerog` — sidecar `/health` probe + live 0G Galileo RPC probe (`evmrpc-testnet.0g.ai`) showing chainId, block height, gas price; three-piece (Compute/Storage/Chain) diagram
- `/conclave` — 8-node mesh visualization with full edges (CEO at center + 7 Counsellors), session FSM diagram, both test suites listed
- `/agentregistry` — ERC-8004 schema table, composition map, 20-test list, MetaMask-driven lookup with deployment-file fallback
- `/cabinet` — shadow-overlord admin UI (operator-activated): MetaMask connect → challenge sign → JWT → cabinet provision → vault-as-signing-oracle for any of the 8 agents

### Added — Cabinet (BANKON Vault shadow-overlord admin tier)

- `mindx_backend_service/bankon_vault/shadow_overlord.py` (192 LOC) — NonceStore (in-memory + JSONL persist), JWT issue/verify (HS256 5-min TTL), `verify_shadow_signature` ECDSA recovery + `hmac.compare_digest`, FastAPI dependency
- `mindx_backend_service/bankon_vault/cabinet.py` (231 LOC) — `CabinetProvisioner.provision/read_public/clear` for an 8-wallet executive cabinet (1 CEO + 7 soldiers per company); atomic snapshot/rollback under `_vault_dir_lock()`
- `mindx_backend_service/bankon_vault/admin_routes.py` (250 LOC) — 6 routes: shadow/challenge, shadow/verify, cabinet/preflight, cabinet/provision, cabinet/clear, shadow/release-key
- `mindx_backend_service/bankon_vault/sign_routes.py` (90 LOC) — vault-as-signing-oracle: signs on agent's behalf; private key never leaves the vault, never appears in any response
- 25 pytest cases (`tests/bankon_vault/test_shadow_overlord.py` + `test_cabinet.py`) — including the headline `test_sign_as_agent_returns_valid_sig_no_pk_leak` that proves the cryptographic invariant
- `agents/catalogue/events.py` — three new EventKinds for forensic audit of shadow-overlord operations

### Added — Documentation

- `docs/operations/SHADOW_OVERLORD_GUIDE.md` (1,150 lines) — first-time-reader guide with formal cryptographic property statements, threat model, mental model, end-to-end workflow, operational runbook, 8 explicit limitations, decision log, 5 appendices including verbatim test source and captured live ECDSA-recovery transcript
- `docs/operations/SHADOW_OVERLORD_RUNBOOK.md` — terse operator cheat-sheet
- `openagents/docs/JUDGE_TOUR.md` — 5-minute verification path for hackathon judges
- `openagents/docs/SUBMISSIONS.md` — paste-ready text blocks for all 8 ETHGlobal submission forms
- `openagents/docs/SHIP_NOW.md` — 24-hour deadline-aware execution roadmap (deadline moved up to May 3)
- `openagents/docs/INDEX.md` — master nav with live console table
- `openagents/docs/LIVE_EVIDENCE.md` — per-track curl-able verification page
- `tests/results/2026-05-02/SUMMARY.md` — aggregate test results + reproduce commands
- `tests/results/2026-05-02/runtime_proof.txt` — captured live cryptographic proof transcript
- `SECURITY.md` — private vulnerability reporting + scope

### Added — Infrastructure

- `.github/workflows/test.yml` — GitHub Actions CI running all 7 test suites in parallel; 163/163 tests green in clean environment
- CI badge on root `README.md` + `openagents/README.md`
- Repo description + 11 topics on `github.com/AgenticPlace/openagents`
- Tag `v1.0.0-ethglobal`

### Reorganized — `openagents/` directory

- 8 module dirs at `openagents/{conclave, ens, keeperhub, sidecar, uniswap, deploy, deployments, docs}/`
- Per-track docs at `openagents/docs/{0g, ens, keeperhub, uniswap, axl}/README.md`
- Composition demo at `openagents/openagents.html` updated to link each panel to its dedicated console + bonus Cabinet panel
- Public-paths allowlist in `mindx_backend_service/main_service.py` extended for all 9 console paths (both `/foo` and `/foo.html` aliases)

### Deployed — Production VPS (`mindx.pythai.net`)

- KeeperHub bridge — `/p2p/keeperhub/info` returns dual-rail challenge envelope (was 404)
- 9 component consoles — all return HTTP 200 (was: most missing or "Page not deployed" stubs)
- `mindx.service` restarted cleanly with new HTML + Python modules

### Tests

| Suite | Tests | Result |
|---|---|---|
| Cabinet pytest (Python) | 25 | ✅ 3.17s |
| Conclave Python protocol | 9 | ✅ 0.16s |
| Conclave Solidity (Foundry) | 10 | ✅ 30.5ms |
| iNFT-7857 (Foundry) | 56 | ✅ 80.5ms |
| BANKON v1 ENS (Foundry) | 29 | ✅ 324.9ms |
| THOT v1 (Foundry) | 14 | ✅ 9.7ms |
| AgentRegistry ERC-8004 (Foundry) | 20 | ✅ 9.6ms |
| **Total** | **163** | **all green** |

### Cryptographic property (proven)

The headline invariant — *the BANKON Vault signs on the agent's behalf without leaking the private key* — is mathematically demonstrable. Anyone can re-derive it from the published (message, signature, address) tuple in `tests/results/2026-05-02/runtime_proof.txt` using only `eth_account` (no mindX, no BANKON Vault). See `docs/operations/SHADOW_OVERLORD_GUIDE.md` §4 (formal statement) and Appendix C (captured transcript).

### Known limitations

Documented explicitly in `docs/operations/SHADOW_OVERLORD_GUIDE.md` §7. Headline items:
- Loss of the offline shadow-overlord key is unrecoverable by design
- Funds management is out of scope (the system mints wallets but does not move on-chain holdings)
- Server compromise during a brief in-memory signing window can leak that one key (other 7 unaffected)
- The signing oracle endorses any payload the operator signs — social engineering is not technically prevented

---

## Pre-1.0.0 history

This repository accumulated over the prior weeks of mindX development. The ETHGlobal submission cut at `v1.0.0-ethglobal` represents the work delivered specifically for the hackathon window.
