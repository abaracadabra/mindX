# Judge Tour — 5-Minute Verification Path

> If you're judging this submission, this is the single page that tells you what to click and what to expect.
> Last verified: 2026-05-02 · all URLs return HTTP 200 against `mindx.pythai.net`.

## Stop 1 — Composition demo (60 seconds)

**[https://mindx.pythai.net/openagents](https://mindx.pythai.net/openagents)**

The dashboard. Eight panels for the eight modules + a bonus Cabinet panel. Each panel links to its own dedicated console. Read the hero paragraph; the rest is navigation.

## Stop 2 — Click the panel for the prize you're judging

| Prize you care about | Click here |
|---|---|
| **0G — Best Autonomous Agents / iNFT** ($7,500) | [`/inft7857`](https://mindx.pythai.net/inft7857) — 9-tab ethers v6 console for the ERC-7857 contract. 56/57 forge tests. Sealed-key transfer, oracle-signed re-encryption. |
| **0G — Best Framework, Tooling** ($7,500) | [`/zerog`](https://mindx.pythai.net/zerog) — three-piece adapter (Compute / Storage / Galileo). Click "Probe RPC" — live chainId, block height, gas price from `evmrpc-testnet.0g.ai`. |
| **Gensyn AXL** ($5,000) | [`/conclave`](https://mindx.pythai.net/conclave) — 8-node mesh visualization (CEO at center + 7 Counsellors). 9 Python + 10 Solidity tests. |
| **ENS — Best Integration** ($2,500) | [`/bankon-ens`](https://mindx.pythai.net/bankon-ens) — type any ENS name in the lookup box and click Resolve. 29 fuzz tests on the registrar. |
| **ENS — Most Creative** ($2,500) | Same console as above. Read panel 1 for the credentials angle (ENS subnames as verifiable agent capabilities). |
| **KeeperHub — Best Use** ($4,500) | [`/keeperhub`](https://mindx.pythai.net/keeperhub) — auto-polls `/p2p/keeperhub/info` every 30s. Live dual-rail Base USDC + Tempo MPP envelope. |
| **KeeperHub — Builder Bounty** ($500) | [`docs/keeperhub/FEEDBACK.md`](keeperhub/FEEDBACK.md) — five categorized friction notes from real integration. |
| **Uniswap — Best API Integration** ($5,000) | [`/uniswap`](https://mindx.pythai.net/uniswap) — connect MetaMask to Sepolia, paste pool params, click Get Quote. Real V4 Quoter `eth_call`, no funds needed. |

## Stop 3 — Verify the cryptographic invariant (composability bonus)

**[https://mindx.pythai.net/cabinet](https://mindx.pythai.net/cabinet)**

If the operator has activated it (sets `SHADOW_OVERLORD_ADDRESS` + `SHADOW_JWT_SECRET`), this is a fully-functional shadow-overlord admin tier. Otherwise it shows the UI but the auth flow returns 503. The cryptographic property — *the vault signs on the agent's behalf without ever leaking the private key* — is proven in 25 passing tests; see [`docs/operations/SHADOW_OVERLORD_GUIDE.md`](../../docs/operations/SHADOW_OVERLORD_GUIDE.md) Appendix C for the captured runtime transcript.

## Stop 4 — Run the test suites yourself (3 minutes)

Clone, then:

```bash
# Python tests (Cabinet)
cd mindX
.mindx_env/bin/python -m pytest \
    tests/bankon_vault/test_shadow_overlord.py \
    tests/bankon_vault/test_cabinet.py \
    -c /dev/null -v
# Expected: 25 passed in ~3s

# Solidity tests (every track + composable primitives)
cd daio/contracts
FOUNDRY_PROFILE=inft           forge test  # 57/57 — iNFT-7857
FOUNDRY_PROFILE=bankon         forge test  # 29/29 — BANKON ENS v1
FOUNDRY_PROFILE=thot           forge test  # 14/14 — THOT memory anchor
FOUNDRY_PROFILE=agentregistry  forge test  # 20/20 — ERC-8004

# Conclave Solidity tests
cd ../../openagents/conclave/contracts
forge test                                  # 10/10 — Conclave + ConclaveBond
```

**Combined: 155 tests, all green.** (120 forge + 9 Conclave-Python + 25 Cabinet-Python + 10 Conclave-Solidity = 164, with 9 of those being Conclave Python protocol tests counted separately.)

## Stop 5 — Verify the composability claim

The headline architectural claim: *eight agnostic, composable peer modules — mindX is one consumer.* Confirm it:

```bash
# Every module imports nothing from mindX, except two intentional couplings:
# 1. demo_agent.py (the composition demo) — imports zerog_provider + zerog_handler (factory wiring)
# 2. keeperhub/bridge_routes.py — imports catalogue.events, wrapped in try/except

grep -rn "from mindx\|from agents\|from llm\|from core\|from tools" openagents/ | \
  grep -v "openagents/\(conclave\|sidecar\|ens/subdomain_issuer\|deploy\|deployments\|docs\)"
# → only demo_agent.py + keeperhub/bridge_routes.py + uniswap/demo_trader.py
#   (the latter two are framework demos; the modules themselves don't depend on mindX)

# Conclave proof of independence — zero mindX imports:
cd openagents/conclave && python -c "from conclave import session, roles, crypto, agent, axl_client; print('OK — no mindX imports needed')"
```

## Why this matters

Most "agent framework" submissions are frameworks. This is *modules* — eight of them — that any framework can compose. mindX is one canonical consumer; if your framework wants any subset, lift them. The Cabinet bonus is a working demonstration that BANKON Vault, IDManagerAgent, the Boardroom soldier roster, ERC-8004 AgentRegistry, and the EIP-712 signer pattern compose into a custodial wallet system without any one knowing about any other.

## What I cannot show

- **Sponsor-specific sandboxes**: 0G Galileo testnet faucets, KeeperHub paid workflows on real USDC, Uniswap V4 Sepolia swaps with funded wallets. The infrastructure is wired; running it requires sponsor keys / faucet drips that exceed what I can prepare for a public demo URL.
- **The video walkthrough**: see the demo video URL in the submission form. The text in this doc + the live consoles cover the same ground if the video is unavailable.

## Where to ask questions

- mindX team via `codephreak` (Telegram + X handles in [`docs/keeperhub/FEEDBACK.md`](keeperhub/FEEDBACK.md))
- Repo issues: `github.com/AgenticPlace/openagents/issues`
- Full per-track positioning: [`docs/INDEX.md`](INDEX.md) → [`docs/{0g,ens,keeperhub,uniswap,axl}/README.md`](.)
- Per-track curl-able verification: [`docs/LIVE_EVIDENCE.md`](LIVE_EVIDENCE.md)
- Submission text source-of-truth: [`docs/SUBMISSIONS.md`](SUBMISSIONS.md)
