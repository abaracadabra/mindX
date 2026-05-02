# Security Policy

## Reporting a vulnerability

If you discover a security issue in any of the modules in this repository — `openagents/`, `daio/contracts/`, or `mindx_backend_service/` — please report it privately:

- **Email:** codephreak [at] dmg [dot] finance
- **GitHub:** open a private security advisory at [`AgenticPlace/openagents/security/advisories/new`](https://github.com/AgenticPlace/openagents/security/advisories/new)

Please do not file public issues for unpatched vulnerabilities.

## Scope

The following areas are in scope and we welcome reports:

| Area | Notes |
|---|---|
| Smart contracts in `daio/contracts/` | iNFT_7857, BANKON v1 (ENS), THOT v1, AgentRegistry — 119/119 tests pass but reports of test gaps or new attack vectors are welcome |
| Conclave protocol & Solidity in `openagents/conclave/` | Membership gating, slashing, on-chain anchoring (`Conclave.sol`, `ConclaveBond.sol`) |
| BANKON Vault + shadow-overlord tier in `mindx_backend_service/bankon_vault/` | AES-256-GCM, HKDF-SHA512, EIP-191 sig recovery, JWT round-trip — see [`docs/operations/SHADOW_OVERLORD_GUIDE.md`](docs/operations/SHADOW_OVERLORD_GUIDE.md) §7 for the explicitly-out-of-scope items |
| KeeperHub bridge `openagents/keeperhub/bridge_routes.py` | x402 / EIP-3009 settlement, HMAC webhook validation |
| ENS subname issuer `openagents/ens/subdomain_issuer.py` | EIP-712 voucher signing |

The following are **not** in scope:

- Issues that require physical access to the operator's machine
- Loss of the operator's offline shadow-overlord wallet (this is by-design unrecoverable; see Cabinet limitations §7a)
- Issues in third-party dependencies (`@0glabs/0g-ts-sdk`, OpenZeppelin v5, etc.) — please report those upstream
- Denial-of-service against `mindx.pythai.net` infrastructure (this is a single-VPS demo deployment)

## Test results

The full test surface is at [`tests/results/<YYYY-MM-DD>/`](tests/results/) with verbatim output captured per run.
The most recent run: [`tests/results/2026-05-02/SUMMARY.md`](tests/results/2026-05-02/SUMMARY.md) — **158/158 tests pass.**

## Cryptographic guarantees

The headline cryptographic invariant — *the BANKON Vault signs on the agent's behalf without leaking the private key* — is documented and proven in [`docs/operations/SHADOW_OVERLORD_GUIDE.md`](docs/operations/SHADOW_OVERLORD_GUIDE.md):

- §4 — formal statement of three properties (A, B, C)
- §7 — explicit limitations of what the system does NOT protect against
- Appendix C — captured live ECDSA recovery transcript

Anyone can re-derive the proof externally with only `eth_account` and the published (message, signature, address) tuple. See [`tests/results/2026-05-02/SUMMARY.md`](tests/results/2026-05-02/SUMMARY.md) for a runnable verification snippet.
