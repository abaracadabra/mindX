# agents/eval/ — mindX evaluation framework

GEval-style criteria-based LLM-as-judge scoring for mindX self-awareness.
Adapted from [confident-ai/deepeval](https://github.com/confident-ai/deepeval)
(Apache-2.0) — see [NOTICE](NOTICE) for the full attribution.

## What this module is

`agents/eval/` lets any mindX surface — a Gödel choice, a boardroom vote, a
campaign verdict, an RAGE retrieval — get scored against criteria using an
LLM as judge. Scores are normalized to `[0, 1]` and pair with a human-readable
reason string.

The algorithm is GEval (Liu et al. 2023, [arXiv:2303.16634](https://arxiv.org/abs/2303.16634)):

1. User supplies plain-English `criteria` (or pre-baked `evaluation_steps`).
2. If no steps, the judge LLM generates 3–5 concrete checks from the criteria.
3. The judge applies the steps to the test case and returns `{score, reason}` JSON.
4. The score is normalized into `[0, 1]` against the rubric (defaults to 0–10).

## What this module is NOT

- **Not a pytest harness.** It is a library. Call `metric.a_measure(test_case)` directly.
- **Not a generic eval suite.** Phase 1 ports `GEval` only. The DeepEval RAG-metric
  family (AnswerRelevancy, Faithfulness, Contextual\*) is intentionally out of scope.
- **Not a SaaS hook.** No Confident-AI cloud upload, no OpenTelemetry, no posthog.

## Quick example

```python
from agents.eval import GEval, LLMTestCase, SingleTurnParams

metric = GEval(
    name="rationale_coherence",
    criteria=(
        "Does the chosen option directly address the stated problem? "
        "Is the rationale internally coherent and free of contradiction?"
    ),
    evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
    threshold=0.6,
)

case = LLMTestCase(
    input="Problem: cloud-bridge timeout cascades into BDI replan storm.",
    actual_output=(
        "Chose: pin OllamaCloudTool retry-budget. "
        "Rationale: storms originate at retry layer, not BDI."
    ),
)

score = await metric.a_measure(case)
print(score, metric.reason, metric.is_successful())
```

## Cost model

Default judge: **CPU pillar — Ollama at `localhost:11434`, model `qwen3:1.7b`.**
Free. ~8 tok/s. Each GEval call costs roughly two judge inferences (steps
generation + scoring), or one if `evaluation_steps` are pre-supplied.

Override via env vars:

```
MINDX_EVAL_JUDGE_PROVIDER=ollama   # or 'openai', 'mistral', 'gemini', ...
MINDX_EVAL_JUDGE_MODEL=qwen3:1.7b
```

Or pass a custom `MindXJudgeLLM(...)` to the metric constructor for
high-stakes consumers (boardroom in Phase 2, when economically warranted).

## Writing good criteria

GEval's signal quality is the criteria's signal quality. A good criterion:

- **Names the failure mode.** *"Rationale is internally coherent and free of contradiction"* > *"is good".*
- **References test-case fields by role.** *"…the chosen option (Actual Output) addresses the problem (Input)…"*
- **Is reversible.** A reader should be able to pass or fail an output by reading the criterion alone.
- **Stays under 200 chars.** Long criteria distract small judge models.

If you need more than 2 sentences, supply `evaluation_steps` directly instead.

## Integration with the catalogue

Phase 1 emits an `alignment.score` event (`agents/catalogue/events.py:EventKind`)
for each scored Gödel choice. The catalogue is the unified substrate; downstream
projectors (insight aggregator, dashboard) read scores from there.

## Phase roadmap

This module ships as Phase 1 of a three-phase rollout (see plan):

| Phase | Consumer | Status |
|-------|----------|--------|
| 1 | Gödel choice scoring (this PR) | Shipped |
| 2 | Boardroom soldier confidence calibration | Backlog priority 6 |
| 3 | `reasoning_quality` 8th fitness axis | Backlog priority 6 |

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Public surface |
| `base.py` | `BaseMetric` ABC (async-only) |
| `test_case.py` | `LLMTestCase` dataclass + `SingleTurnParams` enum |
| `g_eval.py` | `GEval` algorithm + prompt templates + `Rubric` |
| `metrics_utils.py` | Permissive JSON parser for small-judge outputs |
| `llm_adapter.py` | `MindXJudgeLLM` — wraps `llm/llm_factory` |
| `NOTICE` | Upstream attribution (Apache-2.0) |
