# Ornith-1.0 — Feasibility Assessment

> Ornith-1.0 is DeepReinforce's open agentic-coding model family (released
> 2026-06-25, MIT license, Qwen3.5-based, 256K context, multimodal). Its
> headline trick is **self-scaffolding RL**: the model is trained to generate
> not just solution rollouts but the orchestration scaffold that drives them —
> it learns to build its own agent harness. This assessment (2026-07-12)
> measures the family against mindX's actual hardware and routing doctrine.

## The family

| Variant | Architecture | Terminal-Bench 2.1 | SWE-Bench Verified | Notes |
|---|---|---|---|---|
| Ornith-1.0-9B | dense (Qwen3.5) | — | — | matches/exceeds Gemma4-31B, Qwen3.6-35B class; edge-deployable |
| Ornith-1.0-35B | MoE, ~3B active | 64.2 | 75.6 | +22 pts over Qwen3.5-35B on TB-2.1 |
| Ornith-1.0-397B | MoE | 77.5 | 82.4 | matches Claude Opus 4.7 (70.3 / 80.8) |

All MIT-licensed, no regional restrictions — compatible with mindX doctrine.
Official GGUFs exist; on the Ollama library: `ornith:9b` (5.6 GB Q4, 256K ctx),
`ornith:35b` (21 GB Q4), plus `q8_0`/`bf16` tags.
**There is no `:cloud` tag** — Ornith cannot ride the Ollama Cloud free tier;
it is local-pull only.

## Why it matters to mindX

Agentic coding is the documented weak spot of the self-improvement loop
(`FAILED_PLANNING`, SimpleCoder as HANDS, SEA campaigns starved by dead free
models — see [emergent.md](emergent.md) and the
[self-eval feedback](AUTONOMOUS.md) verdicts). A strong, free, locally-served
agentic coder is aimed at exactly that gap. Its self-scaffolding lineage also
rhymes with the Gödel-machine premise: a model trained to improve its own
harness, inside a system that improves its own harness.

## Feasibility per host

| Host | Reality (2026-07-12) | `ornith:9b` (5.6 GB Q4) | `ornith:35b` (21 GB Q4) |
|---|---|---|---|
| Production VPS | 7.8 GB RAM (~1.3 GB free), 2 vCPU | ✗ would OOM the box | ✗ |
| Local thin-client node | 5.7 GB RAM, 4 cores, no GPU | ✗ | ✗ |
| Primary GPU Ollama node | unreachable at assessment time | ✓ if ≥8 GB VRAM (or ≥12 GB RAM CPU-mode) | needs ~24 GB |
| MI300X credit box | 192 GB HBM, $100 credit | ✓ trivially | ✓ |
| Ollama Cloud | no `ornith:*cloud` tag exists | ✗ | ✗ |

## Recommendation

1. **Pull `ornith:9b` on the primary GPU node** when it is reachable. That is
   the only standing host that fits it.
2. **Zero code change** — per the no-model-pinning doctrine, inference
   discovery + `model_health` + the selectors pick up new Ollama tags on their
   own; the [inference budget](INFERENCE_BUDGET.md) treats local Ollama as
   unlimited, so Ornith competes on measured merit and routes coding/planning
   work by capability score.
3. `ornith:35b` only on the MI300X box; **not** a
   [mindXtrain](MINDXTRAIN_INSTALL.md) actor — the CPU training regimen stays
   on the smallest model (SmolLM2-135M).
4. OpenRouter hosting of Ornith is unverified; if a `:free` variant appears in
   the catalogue, discovery will surface it.

Sources: [ornith.site](https://ornith.site/) ·
[DeepReinforce release post](https://deep-reinforce.com/ornith_1_0.html) ·
[HF Ornith-1.0-9B](https://huggingface.co/deepreinforce-ai/Ornith-1.0-9B) ·
[HF Ornith-1.0-35B](https://huggingface.co/deepreinforce-ai/Ornith-1.0-35B) ·
[Ollama library](https://ollama.com/library/ornith)
