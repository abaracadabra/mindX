# External Package Adoption — audit → decide → stage

**Date:** 2026-06-10
**Scope:** how mindX evaluates and adopts externally-supplied packages
**Deliverables:** `Sandbox.inspect_zip()/extract_zip()` ([`agents/simple_coder_tools.py`](../agents/simple_coder_tools.py)), SimpleCoder `audit_package` op ([`agents/simple_coder_agent.py`](../agents/simple_coder_agent.py)), `StrategicEvolutionAgent.evaluate_external_package_adoption()` ([`agents/learning/strategic_evolution_agent.py`](../agents/learning/strategic_evolution_agent.py)), driver [`scripts/evaluate_package.py`](../scripts/evaluate_package.py).

mindX treats an externally-supplied package the way it treats any candidate
self-improvement: **SimpleCoder audits it inside its hardened sandbox**, then the
**Strategic Evolution Agent (SEA) renders a reasoned adopt/reject/defer decision**,
logged as a Gödel choice. Nothing executes during the audit; nothing touches the
live tree without an explicit ADOPT.

---

## The pipeline

```
drop pkg.zip into simple_coder_sandbox/projects/
        │
        ▼
[1] Sandbox.inspect_zip()            non-extracting; flags traversal members,
        │                            zip-bombs (member count / decompressed
        │                            size / compression ratio), nested archives
        ▼
[2] Sandbox.extract_zip()            per-member containment (never extractall);
        │                            every target proven inside the extraction
        │                            root before any bytes are written
        ▼
[3] SimpleCoder audit_package        ast-only static scan (no exec): imports,
        │                            dynamic-exec / network / process /
        │                            deserialization findings, license + dep +
        │                            boundary signals → audit_summary
        ▼
[4] SEA evaluate_external_package_adoption()
        │                            LLM-reasoned ADOPT / REJECT / DEFER against
        │                            the adoption criteria; no model pinning
        │                            (self-aware selector → registry → ollama)
        ├── log_godel_choice         godel.choice + alignment.score events
        ├── belief sea.adoption.<pkg>
        ├── REJECT/DEFER → files stay quarantined in the sandbox
        └── ADOPT → stage members into the live tree
                     + improvement_backlog.json validation entry
```

Run it for any package:

```bash
python scripts/evaluate_package.py                          # LLMFIT.zip, decision-only
python scripts/evaluate_package.py --stage                  # ADOPT → stage into tree
python scripts/evaluate_package.py projects/Foo.zip --stage
```

## Adoption criteria (SEA doctrine)

1. **Security** — no high-severity findings (eval/exec, native code, unsafe
   deserialization, unexplained network/process exec). Loopback-only network and
   an invoked-not-vendored external binary are acceptable.
2. **License boundary** — Apache-2.0/MIT/BSD compatible; a differently-licensed
   external binary is fine **only if invoked, never vendored**.
3. **Agnostic-module fit** — composes as a peer; no model pinning; no
   hard-coupling to one consumer.
4. **Fail-open** — absence of the dependency degrades gracefully, never blocks
   boot or routing.
5. **Dependency cost** — minimal/zero new pip dependencies preferred.

Failure is safe by construction: if the reasoning LLM is unreachable or returns
malformed output, the decision defaults to **DEFER** (never ADOPT), and the
package stays quarantined.

## Audit trail

Every decision is fully auditable:

- `data/logs/godel_choices.jsonl` — perception, options `[ADOPT, REJECT, DEFER]`,
  chosen, rationale (surfaced at `/insight/godel/recent`)
- Catalogue events `godel.choice` + `alignment.score`
- Belief `sea.adoption.<package>` (decision, confidence, cycle_id)
- On ADOPT: `data/improvement_backlog.json` entry
  (`status=adopted_pending_validation`, `source=sea_adoption_decision`) carrying
  the validation plan and the staged-file manifest

## First adoption: LLMFIT (2026-06-10)

`LLMFIT.zip` — a **node-capability oracle** wrapping the MIT
[`AlexsJones/llmfit`](https://github.com/AlexsJones/llmfit) binary. It answers
the prospective question InferenceDiscovery lacks: *"what models can this node
actually run?"*

**Audit:** 4 members, `aggregate_risk=medium` (3× expected loopback `urllib`),
Apache-2.0 + MIT upstream (invoked, never vendored), zero new pip deps,
fail-open by contract.

**Decision:** **ADOPT** (confidence 0.8) — staged:

| Member | Live destination |
|---|---|
| `llmfit_tool.py` | [`tools/inference/llmfit_tool.py`](../tools/inference/llmfit_tool.py) — BaseTool oracle (CLI + REST sidecar transports) |
| `llmfit.advisor.agent` | [`agents/llmfit.advisor.agent`](../agents/llmfit.advisor.agent) — agent descriptor, publishes `mindx.node.fit_profile.v1` |
| `llmfit.container` | [`tools/inference/llmfit.container`](../tools/inference/llmfit.container) — Podman Quadlet sidecar (loopback-only) |
| `inference_discovery_llmfit_hook.py` | [`llm/inference_discovery_llmfit_hook.py`](../llm/inference_discovery_llmfit_hook.py) — fit-gate scoring hook |

**Fit-gate wiring** ([`llm/inference_discovery.py`](../llm/inference_discovery.py)):
`get_best_provider()` multiplies each provider's composite score by a fit factor —
a provider serving **no** node-runnable model is deprioritised ×0.15 (still
selectable as a last resort). Strictly fail-open and **dormant by default**:

| State | Effect on routing |
|---|---|
| `MINDX_LLMFIT_GATE_ENABLED` unset (default) | none — byte-for-byte unchanged |
| gate on, `llmfit` binary absent | none — oracle unavailable ⇒ no gating |
| gate on, oracle live | unrunnable-model providers ×0.15 |

To activate: `uv tool install -U llmfit` (or run the Quadlet sidecar), then set
`MINDX_LLMFIT_GATE_ENABLED=1`.

## Verification

```bash
.mindx_env/bin/python -m pytest tests/test_simple_coder_sandbox.py --no-cov -q  # 41 passed
```

10 archive tests join the 31-test sandbox proof-suite: member listing, traversal
flagging + extraction blocking (nothing escapes), nested-archive flagging,
non-zip rejection, outside-sandbox denial (source and destination), member-count
cap, decompressed-size cap, happy path.

Reusable per-package test templates live in
[`simple_coder_sandbox/tests/`](../simple_coder_sandbox/tests/) so every future
external import gets the same verification before SEA sees it.

## Status

Local on `feat/obs-phase1`; not yet deployed to prod. The fit-gate ships dormant
either way — enabling it is an explicit operator action.
