# lineage — where mindX came from

mindX · PYTHAI · Gregory L. Magnusson (Professor Codephreak)

mindX is the current stage of a lineage that has been building toward augmentic
intelligence since the first AUTOMINDx persona environment. This document records
that lineage from mindX's side, and the full workflow of its immediate predecessor
**ezAGI**, whose v1.0.0 release (2026) completed the easy Augmented Generative
Intelligence design and borrowed several mindX patterns back.

```
AUTOMINDx → aGLM → MASTERMIND → RAGE → funAGI → ezAGI → mindX
```

## The stages

### AUTOMINDx
[pythaiml/automindx](https://github.com/pythaiml/automindx) — the Professor
Codephreak persona as a local, persona-driven language-model environment: persona
console (streaming, reasoning traces, token counters, sampling controls), swappable
memory/model services, prompt-space self-improvement. **In mindX:**
`agents/automindx_agent.py` — persona and prompt generation; the persona doctrine
of `agents/core/core.md`.

### aGLM — Autonomous General Learning Model
The augmentation layer, not a model: autonomous decision-making from belief systems
and feedback loops. **In mindX:** the BeliefSystem (`agents/core/belief_system.py`)
with source- and confidence-scored beliefs shared across all core agents.

### MASTERMIND
[mastermindML/mastermind](https://github.com/mastermindML/mastermind) — the
orchestrator of agency. **In mindX:** `agents/orchestration/mastermind_agent.py`,
the top strategic orchestrator, and the coordinator interaction bus.

### RAGE — Retrieval Augmented Generative Engine
*RAGE remembers · aGLM decides · MASTERMIND orchestrates.* **In mindX:**
`agents/memory_agent.py` ("all logs are memories, all memories are logged") and
`agents/memory_pgvector.py` semantic memory.

### funAGI — fundamental AGI
[pythaiml/funAGI](https://github.com/pythaiml/funAGI) ·
[autoGLM/funAGI](https://github.com/autoGLM/funAGI) — SocraticReasoning and logic
tables; the point of departure. **In mindX:** `agents/learning/socratic_agent.py`,
`agents/core/reasoning_agent.py` and `utils/logic_engine.py`.

### ezAGI — easy Augmented Generative Intelligence
[easyGLM/ezAGI](https://github.com/easyGLM/ezAGI) (current direction) ·
[easyAGI/ezAGI](https://github.com/easyAGI/ezAGI) (frozen minimal snapshot) —
internal reasoning with conclusion logging; the Llama-3 hackathon entry completed
in v1.0.0 as the integrated easy AGI system: multi-provider reasoning (openai,
groq, together, anthropic, ollama local + Ollama Cloud), LLM-judged validation
with confidence-scored truths, the ezAGI console with strict separation of
production chat from the internal reasoning trace, MASTERMIND agency with
SimpleCoder, and **SimpleMind** — the minimalist JAX neural network trained by
**coach** on accumulated conversation memory: learning as long-term memory.
**In mindX:** the conclusion-logging discipline became the improvement journal and
process traces; SimpleCoder became `agents/simple_coder*.py` (the "hands" AGInt
directs); the reasoning loop became AGInt's Perceive→Orient→Decide→Act cycle.

**Borrowed back into ezAGI v1.0.0 from mindX:** resilient cloud-first provider
resolution with local Ollama failsafe (`llm/llm_factory.py` pattern), the
"all logs are memories" doctrine, confidence-scored validation, and stuck-loop
guarding of the autonomous reasoning loop.

### mindX — augmentic intelligence
The orchestration platform: a protocol-based Darwin-Gödel machine — BDI cognitive
cores, the AGInt P-O-D-A loop, strategic evolution, the Gödel training pipeline,
sovereign agent identities, DAIO governance.

### The wider family
[openmindx/OpenMind](https://github.com/openmindx/OpenMind) — native desktop AI
workspace for local models (Tauri 2; boardroom, dojo, diagnostics) ·
[openmindx/agi](https://github.com/openmindx/agi) ·
[llamagi/lmagi](https://github.com/llamagi/lmagi) ·
[autoGLM/easyAGI](https://github.com/autoGLM/easyAGI) ·
[Professor-Codephreak](https://github.com/Professor-Codephreak) ·
[pythaiml](https://github.com/pythaiml) · [autoGLM](https://github.com/autoGLM)

## The ezAGI workflow (the predecessor pipeline, completed v1.0.0)

1. **Perceive** — the ezAGI console (`ezAGI.py`): chat tab = production
   interaction; reasoning tab = live internal SocraticReasoning trace.
2. **Resolve** — `automind/openmind.py` OpenMind resolves a provider cloud-first
   (openai → groq → together → anthropic → ollama-cloud) with the local Ollama
   daemon as failsafe (`webmind/chatter.py:resolve_chatter`).
3. **Reason** — `FundamentalAGI` → `SocraticReasoning`: premises generated and
   challenged, conclusion drawn, tokens streamed to chat, trace events to the
   reasoning panel.
4. **Validate** — truth tables (`automind/logic.py`, safe AST evaluator) for
   propositional statements; LLM VALID/INVALID judgment with confidence for
   natural language; only validated conclusions become truths.
5. **Remember** — `memory/memory.py`: stm conversation memory, thoughts/truth/
   notpremise logs — all logs are memories.
6. **Learn** — `simplemind/coach.py` trains `SimpleMind` (JAX MLP) on accumulated
   stm memories: trained weights as learned long-term memory.
7. **Act** — `mastermind/controller.py` MASTERMIND orchestrates agents from
   `./mindx/agency`; `SimpleCoder` writes them; `automindx/` supplies BDI, THOT
   reasoning styles and self-healing.
8. **Loop** — the autonomous reasoning loop keeps thinking about the latest input
   with a stuck-loop guard — the seed of AGInt's cognitive loop.

The through-line of the whole lineage: **vertical cognitive scaling** — enhancing
what a model's output *means* (premises, validation, memory, agency, evolution)
rather than enlarging the model itself.
