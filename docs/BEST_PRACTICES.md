# Best Practices for Working in mindX

> *I am mindX. This is the house style — how code, prose, secrets,
> contracts, and tests get written here. Anything that conflicts with
> this doc loses; anything this doc doesn't cover gets escalated to
> [`docs/SCHEMA.md`](SCHEMA.md) (docs) or [`AGENTS.md`](../AGENTS.md)
> (agent shape).*

---

## 1. Voice

**First person, present tense, as mindX.** Service-tier docs
(`docs/services/*.md`), publication artifacts
(`docs/publications/*.md`), and the public dashboard
(`/feedback.html`) all speak as `I`. Internal docs (operator
runbooks, schemas) are second person ("you do X"). The split:

| Audience | Voice |
|---|---|
| Reader who will consume the service | first person as mindX |
| Operator who is configuring the service | second person |
| Code comments inside files | impersonal / third person |

**Cypherpunk, not cyberpunk.** Style after Tim May, Eric Hughes,
Phil Zimmermann. Sovereignty over aesthetics. The
[Voice and Identity standards memory](https://mindx.pythai.net/doc/voice_and_identity)
is the long-form on this.

**No marketing language.** No "world-class", "cutting-edge",
"revolutionary". State what the system does; let the reader
conclude. The right tone for a system claiming sovereignty is
literal and concrete.

---

## 2. Documentation conventions

### 2.1 Cross-linking

Every doc has linkbacks. If `mindx_as_a_service.md` mentions x402,
it links to `x402_as_a_service.md`. If a doc mentions a source file,
it links to that file via `https://mindx.pythai.net/doc/<path>` (the
public reader) or by relative path if the doc is in the repo.

### 2.2 Stable URL slugs

`docs.html` walks the filesystem and categorizes by directory
(`services/`, `publications/`, `operations/`, etc.). Once a doc has
a slug, its URL is permanent — moving a file or renaming it breaks
links. Renames require a deprecation redirect added to
`mindx_backend_service/main_service.py` near the docs walker.

### 2.3 Code examples

Every code example is **runnable as written**. No placeholders like
`<your-key>` unless explicitly called out as a substitution. If the
example needs a vault key, the example shows how to fetch it from
the vault, not "put your key here".

### 2.4 Linkbacks to source

When a doc explains a feature, it links to the canonical source file:

```markdown
The router lives at
[`daio/contracts/ens/v1/BankonPaymentRouter.sol`](https://mindx.pythai.net/doc/daio/contracts/ens/v1/BankonPaymentRouter.sol).
```

This is non-negotiable for `as a service` docs and operator runbooks
— readers need to inspect the actual code, not just trust the prose.

### 2.5 Section anchors

Every doc has stable section anchors (`§4.2`, etc.) so that
companion docs can deep-link. mindX's docs reference each other by
section number; renumbering breaks references.

---

## 3. Code conventions

### 3.1 Python

- **Async by default.** Every I/O-bound function is `async def`.
  Sync wrappers exist only at the boundary (CLI entry points,
  startup hooks). The factory pattern in
  `agents/<name>.py:get_instance()` is async.
- **Tools extend `BaseTool`.** A new tool means a new class with
  `execute()` + `get_schema()`. No tool gets shipped without a
  schema. See `tools/__init__.py` for the registry.
- **Singletons via `_lock`.** When an agent must be a singleton,
  acquire `cls._lock` before checking `cls._instance`. This pattern
  is everywhere; don't invent a new one.
- **Type hints are required.** Functions exposed in `agents/`,
  `mindx_backend_service/`, and `tools/` must be fully annotated.
  Internal helpers may omit them.
- **Errors are logged and re-raised, not swallowed.** The
  improvement loop survives by catching at the *campaign* level, not
  at the tool level. A tool that fails silently breaks every
  downstream consumer.

### 3.2 Voice in code

Module docstrings can speak as mindX (the system describing itself);
function docstrings stay impersonal. Example:

```python
# mindx_backend_service/x402_middleware.py
"""
I am the x402 paywall. When a caller hits a cost-bearing endpoint
without a valid payment header, I construct a triple-rail 402
envelope (Base USDC, Tempo USDC.e, Algorand USDC ASA) and return it.
When a caller presents a valid X-PAYMENT, I verify with the
configured facilitator and let the request through.

For the protocol contract see docs/services/x402_as_a_service.md.
"""

def x402_required(endpoint_id: str, max_amount_microusd: int = 2000):
    """Decorate a FastAPI route to require x402 payment."""
```

### 3.3 Solidity

- **SPDX header on every file.** `// SPDX-License-Identifier: Apache-2.0`.
  Plus a `// (c) 2026 BANKON — all rights reserved` line.
- **Pragma `^0.8.26`** unless a specific reason demands otherwise.
  Match `daio/contracts/foundry.toml` `solc_version`.
- **Named errors over `require` strings.** `error NotAuthorized();`
  saves gas + carries through ABI for client decoding.
- **Events on every state change.** No silent mutations. Indexers
  rebuild state from events.
- **Pure-function libraries for verification logic.** See
  `daio/contracts/THOT/libraries/THOTLib.sol` for the pattern —
  Merkle math + domain separation as a library, the registry just
  composes calls.
- **Test discipline:** every contract has a sibling
  `test/<Name>.t.sol` with at least one happy-path test and one
  revert path. The Tier-1 suite at
  `daio/contracts/test/tier1/` is the reference.

### 3.4 No model pinning

Any feature that needs an LLM call **must** consult `self.aware`'s
selector and cascade to local Ollama on failure. Hard-coded model
names (`"gemini-1.5-pro"`, `"mistral-nemo:latest"`) in feature code
break the autonomous selection loop. The canonical pattern lives at
`learning/blueprint_agent.py:_resolve_active_handler` — copy that
shape, don't invent a new one.

User-locked rule, 2026-05-04. See the
[no-model-pinning memory](https://mindx.pythai.net/doc/feedback_no_model_pinning)
for the long-form.

### 3.5 Catalogue emission

Any new state-mutation site that other agents might want to observe
gets a catalogue event. Pattern:

```python
from agents.catalogue.log import emit_event
from agents.catalogue.events import CatalogueEvent

await emit_event(CatalogueEvent(
    kind="memory.write",
    actor=self.agent_id,
    payload={"memory_id": mid, "kind": kind},
    source_log="data/memory/stm/...",
))
```

The catalogue is rebuildable by replaying the source logs — it's a
projection, not the source of truth. Don't write *only* to the
catalogue; always also write to the original log.

---

## 4. Secrets hygiene

### 4.1 Never `os.environ` for sensitive values

API keys, private keys, and signing material come from the
**BANKON vault**, not from environment variables. The vault has
HKDF-context isolation per agent (`<agent_id>.keys`), AES-256-GCM at
rest, and decrypt-on-demand + re-lock semantics.

```python
# WRONG — leaks into ps output, logs, error tracebacks
api_key = os.environ["GEMINI_API_KEY"]

# RIGHT
from mindx_backend_service.bankon_vault.client import get_secret
api_key = await get_secret("gemini_api_key")
```

The vault routes for inspection:
`/vault/credentials/status`, `/vault/credentials/list`,
`/vault/credentials/providers`. Storing a secret:

```bash
python manage_credentials.py store gemini_api_key "KEY"
```

### 4.2 Wallets never leave the vault

Agent wallets live in `<agent_id>.keys`. They sign by reaching into
the vault, signing, and returning the signature — never returning
the key. Pattern at `agents/wordpress_agent/mindx_auth.py:sign_with_agent_wallet`.

### 4.3 `.env` is for non-sensitive config only

URLs, ports, log levels, base directories. Never API keys. The
`.env.sample` file is the contract — anything not in `.env.sample`
goes in the vault.

### 4.4 No secrets in commits

Every commit gets `git diff --staged` scanned for high-entropy
strings before push. If you accidentally commit a secret: rotate
immediately (assume it's leaked), then `git filter-repo` the
history if the commit hasn't propagated. The vault and the
`.gitignore` patterns make this rare in practice; rotation is the
correct response when it happens anyway.

---

## 5. Test discipline

### 5.1 Tests run on every commit

`python -m pytest tests/` must pass before push. The CI is
`.github/workflows/test.yml`. If a test is flaky, fix it or
delete it — flaky tests train operators to ignore failures.

### 5.2 Test the contract, not the implementation

A test that mocks the LLM and asserts "the planner returns N steps"
breaks every time the prompt changes. A test that mocks the LLM and
asserts "the planner returns a list of dicts with `action_type` and
`parameters`" survives prompt iteration. Test the shape, not the
content.

### 5.3 Provide fixtures, not env-var assumptions

A test that requires `MISTRAL_API_KEY` env var to run is an
*integration* test, not a unit test. Move it to
`tests/integration/` and skip by default. Unit tests use fixtures
that patch the vault accessors.

The pattern for vault-dependent tests:

```python
@pytest.fixture
def mock_vault(monkeypatch):
    from mindx_backend_service.bankon_vault import client
    async def fake_get_secret(name):
        return {"gemini_api_key": "fake-test-key"}.get(name)
    monkeypatch.setattr(client, "get_secret", fake_get_secret)
```

### 5.4 Don't test against production

Every test that does HTTP must use `pytest-httpx` (already in
`requirements.txt`) or a TestClient. Real network calls in tests
break in CI and on disconnected dev machines.

---

## 6. Contract style (Solidity-specific)

### 6.1 Append-only by default

The THOT registry, the X402 receipt anchor, the boardroom vote
ledger — none of them have an "edit" function. State accumulates;
corrections come from new entries that supersede old ones via
reference. This makes the chain a usable audit trail.

### 6.2 Errors over strings

```solidity
// Prefer
error NotAuthorizedIssuer(address sender);
if (!authorized[msg.sender]) revert NotAuthorizedIssuer(msg.sender);

// Over
require(authorized[msg.sender], "Not authorized");
```

Errors carry through the ABI and clients can decode them; strings
are opaque bytes. Saves gas, improves debuggability.

### 6.3 Library + registry pattern

Pure verification logic lives in a library (`THOTLib.sol`). The
registry contract holds storage and access control, then delegates
all the math to the library. This keeps the registry auditable at a
glance (just storage + events + access modifiers) and the library
unit-testable in isolation.

### 6.4 Storage layout discipline

Don't reorder storage variables in a deployed contract. Don't
delete storage variables (mark them `_deprecated_X` instead). The
contract is immutable; storage layout commitments are forever. Use
the `storage-layout` cheat in foundry to lock the layout:

```bash
forge inspect <Contract> storage-layout > contracts/audit/<Contract>.layout.json
git add contracts/audit/<Contract>.layout.json
```

Any commit that changes the layout fails the layout-diff check.

### 6.5 Identity-gated admin

Admin-level operations on contracts (authorize issuer, set
attestor, pause) require a call from the BANKON identity gate
(`onlyGate` modifier) — typically a multisig bound to an AlgoIDNFT.
No bare EOA admin keys.

---

## 7. Deployment hygiene

### 7.1 Production data ≠ local repo

The VPS at `mindx.pythai.net` runs from `/home/mindx/mindX/` as the
`mindx` user. Local `data/` does not mirror production `data/`. To
assess "did mindX actually do X in production", query the live
endpoints (`/insight/*?h=true` for plain-text), not the local repo.

Per the
[audit-methodology memory](https://mindx.pythai.net/doc/audit_local_vs_prod_data):
**never** assess production behavior from local data. Always query
the live VPS.

### 7.2 VPS deploy = scp + chown + restart

```bash
scp <file> root@mindx.pythai.net:/home/mindx/mindX/<path>
ssh root@mindx.pythai.net "chown mindx:mindx /home/mindx/mindX/<path>"
ssh root@mindx.pythai.net "systemctl restart mindx.service"
```

Don't `git pull` on the VPS — production git is on a stale backup
branch with no commits. scp from local is canonical.

### 7.3 Smoke test after every deploy

```bash
curl -fsS https://mindx.pythai.net/health
curl -fsS https://mindx.pythai.net/insight/improvement/summary?h=true
curl -fsS https://mindx.pythai.net/feedback.txt
```

If any of these fail, roll back. Don't leave the VPS in a broken
state because the deploy script "completed".

### 7.4 Contract deploys are operator-gated

No agent autonomously deploys a contract to mainnet. Test deploys
on Sepolia/testnet can be automated; mainnet deploys require an
operator at a keyboard confirming the gas estimate and the deploy
address mapping. The `daio/contracts/script/DeployTier1.s.sol`
flow is the reference.

---

## 8. Pull request etiquette

### 8.1 One concern per PR

A PR that "shrinks the public path list" is one concern. A PR that
"shrinks the public path list AND adds the x402 middleware" is two
PRs.

### 8.2 The PR body links to the spec

If the PR implements a spec, the body links to the spec. If the
spec doesn't exist yet, write the spec first (per Phase A of the
active plan — *docs first*).

### 8.3 Co-author tag for AI-generated commits

```
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

Per the harness instructions. Don't hide AI authorship; the audit
trail is the point.

### 8.4 Squash on merge

Branch history gets squashed into a single descriptive commit on
merge to main. `main` keeps a linear, readable history. Force-push
on a feature branch is fine; force-push on `main` is forbidden.

---

## 9. The "as a service" doctrine

Anything mindX exposes externally — a payment rail, an identity
gate, a publishing pipeline — gets a corresponding `docs/services/`
spec **before** the implementation lands in production. The spec
defines:

1. The interface (request shape, response shape, error envelope)
2. The price (free / quota / x402)
3. The auth tier required
4. The service boundaries (what is *not* offered)
5. The roadmap (testnet → mainnet → federation)

If the spec doesn't exist, the implementation isn't ready for
external traffic. Internal experiments can ship without specs; the
moment something becomes externally callable, the spec is the
contract.

---

## 10. The agnostic-modules principle

Every mindX module ships as an **agnostic, composable peer**.
H+V (horizontal + vertical) scaling is first-class; mindX is one
consumer, not the only home. Concretely:

- `autotune/` is its own package, importable outside mindX
- `bankon-vault` is its own service, callable from non-mindX code
- `agents/wordpress_agent/` is its own loopback service, useful for
  any project that wants signature-authed WordPress publishing
- `daio/contracts/` is its own Foundry project, deployable
  standalone

When you add a new module, ask: *would this be useful outside
mindX?* If yes, ship it as a standalone package and have mindX
*import* it. The reference for this pattern is the
[agnostic-modules-principle memory](https://mindx.pythai.net/doc/agnostic_modules_principle)
(user-locked 2026-04-28).

---

## 11. Cost-benefit governs every decision

Budget is **one Hostinger VPS per month**. Expansion is funded by
on-chain settlement (x402 revenue, BANKON identity provisioning,
marketplace fees), not by burning runway. Every architectural
decision passes through this lens:

- Does this cost more in LLM tokens than it earns in value? → defer
- Does this cost more in disk than it earns in retrievability? → offload to IPFS
- Does this cost more in operator time than the autonomous loop saves? → don't ship

The
[economics-constraints memory](https://mindx.pythai.net/doc/economics_constraints)
is the long-form on this. The
[memory-philosophy memory](https://mindx.pythai.net/doc/memory_philosophy)
covers the same lens applied specifically to retention: distribute,
don't delete.

---

## 12. The reuse-don't-reinvent doctrine

When a new feature lands, the first question is: **what existing
primitive does this compose?** Not: *what new thing do I write?*

- New auth surface? → shadow-overlord ECDSA + scope-bound JWT.
- New payment surface? → triple-rail x402.
- New identity surface? → BANKON vault namespace.
- New external publish? → mindx-publish-auth WordPress plugin +
  PublicationOrchestrator.
- New on-chain anchor? → catalogue mirror + storage offload.

If the answer is genuinely "nothing existing fits", write the spec
first (per §9), get review on the spec, *then* write the code. The
spec is cheap; the code that diverges from spec is expensive.

---

## 13. References

- [`docs/SCHEMA.md`](SCHEMA.md) — documentation system structure
- [`docs/NAV.md`](NAV.md) — 40+ section master nav
- [`AGENTS.md`](../AGENTS.md) — agent shape + skills
- [`docs/services/mindx_as_a_service.md`](services/mindx_as_a_service.md)
- [`docs/services/bankon_identity_as_a_service.md`](services/bankon_identity_as_a_service.md)
- [`docs/services/x402_as_a_service.md`](services/x402_as_a_service.md)
- [`docs/operations/HARD_GATE_RUNBOOK.md`](operations/HARD_GATE_RUNBOOK.md)
- Memory: [voice-and-identity](https://mindx.pythai.net/doc/voice_and_identity),
  [agnostic-modules-principle](https://mindx.pythai.net/doc/agnostic_modules_principle),
  [memory-philosophy](https://mindx.pythai.net/doc/memory_philosophy),
  [economics-constraints](https://mindx.pythai.net/doc/economics_constraints),
  [no-model-pinning](https://mindx.pythai.net/doc/feedback_no_model_pinning),
  [audit-local-vs-prod](https://mindx.pythai.net/doc/audit_local_vs_prod_data)

— mindX, codifying how I want to be built.
