# mindX Efficiency Index — foundational metric specification for the mindXtrain alpha

**From:** Gregory (codephreak), architect — PYTHAI / DELTAVERSE / mindX / BANKON
**To:** mindX (autonomous cognitive system)
**Subject:** Composite model-efficiency metric system for the mindXtrain alpha run and aGLM derivative evaluation
**Status:** Design specification, v0.1 — implementable
**Date:** May 15, 2026

---

This document specifies the **mindX Efficiency Index (MEI)** — the in-house composite metric you will use to evaluate every aGLM derivative produced by the mindXtrain alpha and to govern checkpoint promotion to AgenticPlace. The MEI is decision-grade: each Qwen3.5 or Qwen3.6 candidate run, each LoRA / QLoRA checkpoint, each quantization variant, must be reducible to a single scalar that is comparable across runs, defensible to outside reviewers, and tied to the operational reality of autonomous-agent deployment. Read this whole document before instrumenting; the MEI is only as honest as the measurement substrate beneath it. The headline result is that **MEI is a logarithmically-compressed Pareto score over five axes — quality, decode throughput, prefill throughput, memory footprint, and energy per useful token — weighted toward the autonomous-agent regime that mindX actually operates in**, not toward the leaderboard-chasing regime that public scoreboards reward.

The reason this specification exists now, rather than after the alpha completes, is that retroactive efficiency analysis is fraud. If we do not pin tokenization, warm-up, percentile reporting, prompt batteries, and hardware state before the first checkpoint, we cannot compare the last one to anything. The mindXtrain alpha must emit MEI-conformant telemetry from run zero.

---

## 1. Why a new metric, and what the public scoreboards get wrong

The state of the art in 2026 is fragmented along three incompatible axes. **MLPerf Inference v5.1** (MLCommons, September 2025) measures vendor-tuned serving infrastructure under tight SLOs — a 2,000 ms TTFT and 80 ms TPOT for the DeepSeek-R1 reasoning workload, a 6,000 ms TTFT for Llama-3.1-405B — and reports tokens per second under Server, Offline, and Interactive scenarios with strict 99th-percentile latency guards. It is rigorous and reproducible but answers "how fast can a hyperscaler-tuned cluster serve this model" rather than "is this checkpoint good for autonomous use." **Artificial Analysis's Intelligence Index v4.0** (January 2026) gives the best public Pareto framing — intelligence-vs-price, intelligence-vs-speed, ten evaluations weighted 25% each across Agents, Coding, Scientific Reasoning, and General Knowledge — but it scores commercial APIs, not local checkpoints during training, and its evaluation cost alone exceeds the budget for routine checkpoint scoring. **The HuggingFace Open LLM Leaderboard v2** was officially retired in 2025 with no v3 successor; HuggingFace explicitly redirected the community toward task-specific evaluation. The Open LLM Leaderboard's normalization scheme — `(raw − random) / (max − random) × 100`, then unweighted mean of six benchmarks (IFEval, BBH, MATH-Hard, GPQA, MUSR, MMLU-Pro) — is still the cleanest public template for quality aggregation, and we will adopt a variant of it.

None of the three captures what mindX cares about. mindX is an autonomous agent, not a chatbot. It runs long autonomous reasoning loops with high token budgets, it operates inside a BDI (Belief-Desire-Intention) control structure inherited from the AgentSpeak / automindx lineage, and it evaluates itself on Perceive-Orient-Decide-Act (P-O-D-A) sequences whose value is not captured by MMLU-Pro accuracy. Consequently, the MEI emphasizes **sustained throughput, quality consistency across long contexts, and energy-per-useful-token over peak-quality-at-any-cost**. This is the operational regime where Qwen-class models genuinely live, and where the It's FOSS empirical baseline — a Q4_K_M Ollama run on a mid-tier Intel i5 laptop with 12 GB RAM — anchors what "viable for local autonomous deployment" actually means.

The It's FOSS reference numbers (Mishra, May 15, 2026) bracket the design space. Qwen 3 0.6B achieved roughly 34–36 decode tokens per second; TinyLlama 1.1B, 25–28; Gemma 3 1B, 18.6; Phi 4 Mini 3.8B, 6.90 on a 876-token response; OpenHermes 7B, 4.1–4.3; and Ministral 3 8B, 3.16 tokens per second. The author drew a sharp UX line: under 5 tok/s feels painfully slow, 15–30 tok/s feels responsive. **mindX's autonomous deployment target is the upper end of that range on commodity CPU and the 60-tok/s-plus range on Apple Silicon and AMX-equipped Xeons.** Any aGLM derivative that cannot hit at least 15 decode tok/s at Q4_K_M on an AVX-512-class CPU should not be promoted, regardless of its MMLU-Pro score.

---

## 2. Prior art from the minaiml organization

A careful audit of `github.com/minaiml` is necessary so this specification grounds in actual prior work rather than retrospective myth. The minaiml organization is a thirty-four-repository curation under the Professor-Codephreak ecosystem, tagline "Min AI ML — Language Models in Miniature," and the public surface is **almost entirely forks**: llama.cpp, ggml, whisper.cpp, mlc-llm, ollama, faiss, milvus, vespa, exo, KittenTTS, AgentSpeak (Jason BDI interpreter), and the curated Llama-2 CPU-inference reference. There is no original benchmarking harness, no tok/s instrumentation, no Qwen distillation pipeline, and no evaluation framework in the public surface. The README explicitly notes that "much of the code is currently private and will be revealed with the vision over time."

The honest carry-forward from minaiml into the MEI is therefore **thematic, not codebase**. Three concrete inheritances apply. First, **the minaiml thesis — "intelligence doesn't require a data center" — becomes the MEI's design north star.** The metric must reward small, quantized, edge-deployable models, not punish them for failing to match frontier-API quality. Second, **the curated minaiml tool list defines the canonical benchmark substrate**: llama.cpp + GGUF + ggml as the reference inference engine, mlc-llm as the cross-platform secondary, and KittenTTS / exo as edge-deployment exemplars. Third, **the AgentSpeak / Jason BDI fork (`minaiml/AgentSpeak-speak-agent`) is the prior-art basis for the BDI command framework**, which the MEI's quality dimension will encode through dedicated agentic evaluations. P-O-D-A reasoning is not present in minaiml proper; it must be layered on the BDI substrate from the automindx / Professor-Codephreak / mastermindML branches and instrumented fresh.

The training-methodology lineage almost certainly lives in `github.com/trainair` (the sister organization minaiml explicitly names as its training counterpart), not in minaiml. Before this specification is operationalized, mindX should audit `trainair` for any pre-existing pretraining or fine-tuning instrumentation that the MEI training-efficiency companion should incorporate.

---

## 3. Token calculation methodology

Token counts are the denominator of nearly every efficiency metric, and tokenizer inconsistency silently invalidates cross-run comparisons. The MEI fixes this with three rules.

**Rule 3.1 — canonical tokenizer.** For every aGLM derivative, the **model's own `tokenizer.json` loaded via the HuggingFace `tokenizers` (Rust) library** is the authoritative token counter. Every reported token figure carries the tokenizer revision hash. For the Qwen3.5 base, this is a 248,320-entry byte-level BPE; for Qwen3.6-35B-A3B, the same family with the unified multimodal vocabulary; for Qwen2.5 and Qwen3 base candidates retained for comparison, the 151,665-entry (Qwen2.5) or 151,669-entry (Qwen3) BBPE with embedding padded to 151,936 or 152,064. The HuggingFace tokenizer is canonical even when inference runs through llama.cpp; if llama.cpp's internal BBPE diverges, the divergence is logged as a measurement defect, not absorbed into the rate.

**Rule 3.2 — explicit accounting for chat-template and control tokens.** The Qwen ChatML scaffold (`<|im_start|>system\n…<|im_end|>\n<|im_start|>user\n…<|im_end|>\n<|im_start|>assistant\n`) adds roughly ten to twenty-five tokens of structural overhead per conversational turn, plus tool-call tokens (`<tool_call>`, `</tool_call>`), FIM tokens (`<|fim_prefix|>`, `<|fim_middle|>`, `<|fim_suffix|>`), and vision tokens (`<|vision_start|>`, `<|image_pad|>`) when applicable. **The MEI counts every token the model actually processed, including chat-template scaffolding, in both prefill and decode totals.** A separate "content tokens" series strips ChatML to permit user-facing reporting. Never publish a single tok/s number; always disclose whether it is content-only or scaffold-inclusive.

**Rule 3.3 — bytes-per-second as a tokenizer-invariant cross-check.** Because Qwen3.5's 248k vocabulary compresses text more densely than Llama 3's 128k or Qwen2.5's 152k (roughly 3.5 chars/tok English, 1.5–1.8 chars/tok Chinese for Qwen; 4.0 chars/tok English, ~2.5 chars/tok Chinese for Llama 3), **a 7B Qwen and a 7B Llama running at identical "100 tok/s" produce different amounts of useful output.** The MEI accordingly reports an auxiliary **bytes-per-second of UTF-8 output** alongside every tok/s figure. When mindX compares a Qwen3.5 derivative against a Qwen2.5 baseline, it compares both rates; when reviewers ask "is this faster than Llama 3," bytes/sec is the only honest answer.

For ingestion into downstream metrics, the canonical token series is therefore: **N_prefill** (prompt tokens consumed, including chat template), **N_decode** (output tokens generated, excluding the prefill but including any stop tokens emitted before EOS), **B_decode** (output bytes after UTF-8 encoding of the decoded text), and **N_useful_decode** (decode tokens belonging to content fields after structured-output parsing, excluding any `<|im_end|>` or tool-scaffolding tokens). All four are emitted per request.

---

## 4. Tokens-per-second measurement methodology

Throughput is two distinct measurements, not one. **Prefill (prompt processing) is compute-bound and large; decode (generation) is memory-bandwidth-bound and small.** The llama.cpp `llama-bench` convention of reporting `pp512` and `tg128` as separate numbers is correct and is adopted here. The MEI defines four primary throughput scalars per run.

**Prefill throughput** `Tpp` is measured as `N_prefill / t_prefill`, where `t_prefill` is the wall-clock interval from request submission to first generated token, minus the network and queueing components when measuring server-side. For Ollama-mediated runs this is `prompt_eval_count / (prompt_eval_duration / 1e9)`; for llama.cpp this is the `pp` field; for vLLM, the `prompt_throughput` series. **Decode throughput** `Ttg` is `N_decode / (E2E − TTFT)` in the single-request case, or equivalently `1 / TPOT` averaged over all output tokens beyond the first. **Time to first token** `TTFT` and **time per output token** `TPOT` are reported at p50, p95, and p99 — never as means alone — because production latency distributions are routinely 15× heavier at p99 than at the mean under contention. **Inter-token latency** `ITL` is reported per the vLLM convention (excluding TTFT from the per-token average) so the metric is comparable to the NVIDIA GenAI-Perf and DistServe literature; the LLMPerf convention of folding TTFT into ITL is rejected as conflating two distinct user-experience phenomena.

Several second-order effects must be controlled or characterized rather than averaged away.

**Batch effects.** Decode throughput per request degrades modestly as concurrent batch size grows, but **aggregate system throughput rises near-linearly until the KV cache or compute roofline is reached** — typically batch 32 to 128 for a 7B-class model on an A100 or H100. The MEI mandates measurement at five concurrency points (1, 4, 16, 64, and the maximum the hardware sustains under a 10-second p99 TTFT SLO) and reports the throughput-vs-latency Pareto curve, not a single batch-1 number. For autonomous-agent deployment this matters: mindX rarely runs at batch 1, since the BDI loop fan-out generates many concurrent sub-queries.

**Context length effects.** Decode tok/s falls as context grows because per-token KV reads scale linearly with sequence length, and prefill TTFT scales quadratically in the attention term without FlashAttention. Empirically, Qwen3-30B-A3B drops from roughly 234 tok/s at 4K context to 110 tok/s at 32K on an RTX 5090. **The MEI characterizes context scaling explicitly through a four-prompt calibration battery: short (32 tokens), medium (512 tokens), long (8,192 tokens), and very long (32,768 tokens), with an optional ultra-long (131,072) probe for models claiming extended context.** Every checkpoint emits a full 4×2 matrix of (`Tpp`, `Ttg`) at the four context tiers; the headline `Ttg` used in the composite is the **geometric mean** across tiers, which penalizes catastrophic long-context degradation more than an arithmetic mean would.

**KV cache behavior.** The KV cache size per token is `2 × n_layers × n_kv_heads × d_head × dtype_bytes`. For Qwen2.5-7B (28 layers, 4 KV heads, head dim 128, FP16), this is approximately 56 KB per token, or 1.75 GB at 32K context; for Qwen3-8B (36 layers, 8 KV heads) it is 144 KB per token, or 4.7 GB at 32K. Grouped-query attention is what keeps these tractable — Qwen2.5-7B's 7:1 GQA ratio cuts the cache sevenfold versus full multi-head attention. **The MEI reports KV cache memory as a separate accounting line from weight memory** because the two scale orthogonally: weights are amortized across requests, KV cache is per-sequence. Quantized KV cache (`--cache-type-k q8_0` or `q4_0` in llama.cpp) is permitted and is logged as a configuration field; the MEI does not penalize quantized KV by default, but quality regressions caused by it are visible in the quality dimension.

**Quantization tier effects.** The MEI accepts any GGUF quantization tier (Q2_K through Q8_0, including the importance-matrix i-quants IQ2_XXS through IQ4_NL) plus GPTQ, AWQ, EXL2, NF4, FP8, and NVFP4 where applicable. The conventional default for aGLM derivatives is **Q4_K_M** — 4.85 bits per weight, the same default the It's FOSS author used and the format with the best public quality-to-size ratio. Memory footprint follows `size_GB ≈ params_B × bpw / 8` plus KV cache and roughly 0.5–1 GB of activation and runtime overhead. The MEI does not assume Q4_K_M; it requires every reported figure to carry an explicit `(quantization, bpw, calibration_corpus)` tuple, so a Q4_K_M-with-imatrix run is distinguishable from a Q4_K_M-without-imatrix run, and a "Q4_K_M" anomaly like the 7 GB Gemma 4 E2B file from the It's FOSS table (likely a multimodal variant) is flagged rather than averaged into a benchmark mean.

**Reproducibility envelope.** Every MEI measurement specifies: hardware SKU including CPU family and SIMD support (AVX2, AVX-512, AVX-512-VNNI, AMX, NEON, SVE2, SME, Metal version), DRAM channel count and clock, GPU SKU with clocks pinned where possible, OS kernel version, inference-engine commit SHA, tokenizer revision, model SHA-256, quantization tuple, context length, batch and concurrency, decoding parameters (temperature, top-p, top-k, repetition penalty), and seed. **Five warm-up requests are discarded before measurement; the steady-state sample is at least one hundred requests for latency percentiles and at least sixty seconds of sustained load for throughput.** Bootstrap 95% confidence intervals (1,000 resamples) accompany every headline number. The It's FOSS article is rigorous enough to draw qualitative conclusions but reports neither sample size nor variance nor CPU SKU — that level of underspecification is what the MEI exists to prevent inside mindXtrain.

---

## 5. The mindX Efficiency Index — formal specification

The MEI is a single scalar derived from five normalized sub-indices: quality, decode throughput, prefill throughput, memory footprint, and energy per useful token. Each sub-index lives on a logarithmically-compressed [0, 1] scale so the composite is invariant to order-of-magnitude differences between deployment tiers, and the composite weighting reflects the autonomous-agent operational regime.

### 5.1 Quality sub-index `Q`

Quality is the geometric mean of seven normalized evaluation scores, organized into four bands that match mindX's actual use. The bands are inspired by Artificial Analysis's four-category Intelligence Index v4.0 structure but are re-weighted for autonomous agency.

The seven evaluations and their band assignments are: **MMLU-Pro** (general knowledge, ten-choice), **GPQA-Diamond** (graduate science), **IFEval-strict-prompt** (instruction following), **LiveBench-Reasoning** (contamination-resistant reasoning, current month's release), **BigCodeBench-Hard pass@1** (real-library code), **MT-Bench-2-turn with paired-judge ensemble** (GPT-4.1 + Claude-judge, position-swapped), and the **mindX Agentic Battery (MAB)** — the proprietary BDI / P-O-D-A / tool-use evaluation suite mindX must develop in parallel with this specification, anchored on the AgentSpeak-style trace fidelity that the automindx lineage already encodes.

Each evaluation is min-max normalized against a fixed reference pool: random-baseline for the floor and the current Qwen3.5-flagship score for the ceiling. The per-evaluation normalized score is

`s_i = clamp((raw_i − random_i) / (Q3.5_flagship_i − random_i), 0, 1)`

following the retired Open LLM Leaderboard v2 convention. The band scores are arithmetic means within band; the overall quality sub-index is the **geometric mean of the four band scores**, which penalizes catastrophic weakness in any single band more than an arithmetic mean would. The band weights, applied as exponents in the geometric mean, are **0.35 for Agentic (MAB)**, **0.25 for Instruction-Following (IFEval, MT-Bench)**, **0.20 for Reasoning (LiveBench, GPQA)**, and **0.20 for Knowledge-and-Code (MMLU-Pro, BigCodeBench)**.

The Agentic band weight of 0.35 is deliberately higher than any public scoreboard assigns to agentic capability, because mindX is an autonomous agent and the cost of agentic failure dominates the cost of mild knowledge gaps. A model that hits ninety percent on MMLU-Pro and fails BDI trace fidelity is unfit for promotion; the converse, modulo a quality floor, is acceptable.

### 5.2 Decode throughput sub-index `Dt`

Decode throughput is the geometric mean of `Ttg` across the four context tiers (32, 512, 8192, 32768 tokens), logarithmically compressed to [0, 1] against deployment-tier anchors derived from the It's FOSS empirical baseline and the modern Apple Silicon / AMX ceilings:

`Dt = clamp((log10(T̄tg) − log10(T_floor)) / (log10(T_ceiling) − log10(T_floor)), 0, 1)`

where `T̄tg` is the geometric mean across context tiers, `T_floor = 3 tok/s` (the It's FOSS "painfully slow" threshold the Ministral 3 8B and OpenHermes 7B configurations hover near), and `T_ceiling = 300 tok/s` (the Apple M3 Ultra / B200-class upper end). A run achieving 30 tok/s — the It's FOSS "responsive" line — scores approximately `log10(30/3) / log10(300/3) = 1.0 / 2.0 = 0.50`. A run at 100 tok/s scores 0.77. This logarithmic compression is essential: linear normalization would let a single B200 datacenter result dominate the entire MEI distribution and would mask meaningful differences between 5 and 50 tok/s on commodity hardware, where mindX actually lives.

### 5.3 Prefill throughput sub-index `Pp`

Prefill is separately scored because TTFT dominates user-facing latency for any prompt above roughly 500 tokens, and mindX's BDI loops routinely process long context windows. The sub-index uses the same logarithmic shape with anchors `P_floor = 20 tok/s` and `P_ceiling = 5,000 tok/s`, the realistic envelope for prefill on CPU through high-end GPU.

`Pp = clamp((log10(Tpp) − log10(P_floor)) / (log10(P_ceiling) − log10(P_floor)), 0, 1)`

The It's FOSS prefill numbers — Phi 4 Mini at 20 tok/s, OpenHermes at 180–280 tok/s — are at or near the floor, consistent with CPU-only execution; an aGLM derivative under FlashAttention-3 on an H100 should reach the high hundreds to low thousands.

### 5.4 Memory footprint sub-index `M`

Memory is the inverse-log of total resident set at the 32K context working point, comprising weights, KV cache, and runtime overhead:

`M = clamp((log10(M_ceiling) − log10(M_observed)) / (log10(M_ceiling) − log10(M_floor)), 0, 1)`

with `M_floor = 0.5 GB` (a 0.6B Q4_K_M model, roughly the Qwen 3 0.6B It's FOSS baseline) and `M_ceiling = 200 GB` (a 405B-class model at FP8). A Qwen3-8B Q4_K_M derivative occupying approximately 5 GB scores roughly 0.61. A 70B Q4_K_M at 40 GB scores roughly 0.26. The autonomous-agent regime rewards small, dense memory footprints; this sub-index materially penalizes models that cannot fit on a 24 GB consumer GPU or a 32 GB Apple Silicon machine.

### 5.5 Energy per useful token sub-index `E`

Energy is measured following the Saad-Falcon Intelligence-per-Watt methodology (Stanford / Together AI, arXiv:2511.07885) and the TokenPowerBench framework (arXiv:2512.03024). Power is sampled at 50 ms intervals via NVML for GPU, RAPL for CPU and DRAM, `powermetrics` for Apple Silicon, and IPMI or Redfish for whole-system wall power where available; energy is the integral of power over the inference window. The reported quantity is **joules per useful decoded token** — total energy divided by `N_useful_decode` (content tokens after structured-output parsing, not raw output tokens).

`E = clamp((log10(J_ceiling) − log10(J_observed)) / (log10(J_ceiling) − log10(J_floor)), 0, 1)`

with `J_floor = 0.1 J/token` (efficient local inference on Apple Silicon or AMX-equipped Xeon, roughly the bottom of the Intelligence-per-Watt distribution Saad-Falcon reports for 2025 hardware) and `J_ceiling = 100 J/token` (a 405B-class model on cloud H100 without batching, the upper bound).

Where direct energy measurement is unavailable — for example during the mindXtrain alpha when training infrastructure may not expose RAPL — `E` may be estimated from `M_observed` and `Ttg` via the bandwidth-bound proxy `J_estimated ≈ (M_observed_GB × W_per_GB_bw) / Ttg`, with `W_per_GB_bw` a hardware constant calibrated against one direct-energy run per hardware class. Estimation flag is propagated so the MEI report distinguishes measured from inferred energy.

### 5.6 Composite MEI

The composite is a weighted geometric mean over the five sub-indices:

**`MEI = Q^wQ · Dt^wDt · Pp^wPp · M^wM · E^wE`**

with `wQ + wDt + wPp + wM + wE = 1` and the operational weights for the mindXtrain alpha set to:

| Sub-index | Weight | Rationale |
|---|---|---|
| Quality `Q` | 0.40 | Quality is necessary but not sufficient; agentic capability dominates the band. |
| Decode throughput `Dt` | 0.20 | Autonomous loops generate many tokens; sustained decode rate is the limiting factor for end-to-end task latency. |
| Prefill throughput `Pp` | 0.10 | Matters most for long-context BDI traces; secondary to decode in typical agent workloads. |
| Memory footprint `M` | 0.15 | Determines whether mindX runs locally on AgenticPlace edge nodes or requires cloud. |
| Energy `E` | 0.15 | Operational cost and deployment footprint; tracks the minaiml "intelligence doesn't require a datacenter" thesis. |

The geometric form has two properties that the arithmetic alternative does not. First, a single sub-index near zero — a model that is fast but produces incoherent agentic traces, or smart but cannot fit in memory — collapses the composite, which matches mindX's promotion criterion. Second, the geometric mean is unit-free and invariant to common rescalings, which means future revisions to the floors and ceilings shift the absolute MEI but preserve cross-checkpoint orderings within a fixed-anchor era.

Headline reporting is **MEI in [0, 1] with five sub-index components disclosed**, accompanied by the bootstrap 95% confidence interval over the latency and quality measurements. A single-number MEI without the five components is non-conformant and must be rejected at intake.

---

## 6. Training-efficiency companion metric for the mindXtrain alpha

The MEI scores inference behavior. The mindXtrain alpha also needs a training-side metric — call it **mindXtrain Efficiency Index (XEI)** — that scores the production process producing each checkpoint. The XEI is a four-component composite covering training throughput, FLOPs utilization, optimization health, and convergence rate.

**Training throughput** is reported as tokens per second per device and globally, in the standard MFU / HFU framework from the PaLM appendix. Model FLOPs Utilization is `(observed_tokens_per_second × FLOPs_per_token) / (num_devices × peak_device_FLOPS)`, where FLOPs per token follows the `6N + 12 L H Q T` decomposition (`N` non-embedding parameters, `L` layers, `H` heads, `Q` head dimension, `T` sequence length). Published reference points to calibrate against: PaLM 540B achieved 46.2% MFU; well-tuned Megatron-LM runs reach 50–55%; Llama-3.1 reported 38–43%; DeepSeek-V3 on H800 reached approximately 38%. **The XEI target for the mindXtrain alpha is ≥ 35% MFU on the chosen training hardware**; below 30% indicates a configuration defect (data loader bottleneck, suboptimal sequence packing, gradient-checkpointing miscalibration, or communication overhead) that should be resolved before scaling. Hardware FLOPs Utilization is always at or above MFU; the gap `HFU − MFU` quantifies the cost of activation rematerialization and is itself a tunable.

**Optimization health** is a composite of gradient-norm stability, loss-curve smoothness, and parameter-update magnitude. The gradient norm should remain in the 0.5–2.0 band once linear warmup completes; spikes exceeding ten times the trailing baseline trigger a step-skip protocol and are logged as instability events. The loss curve should follow the power-law shape `L(D) ≈ E + A/D^α` with `α ≈ 0.28–0.34` for the token axis; **deviation from this fit, integrated over a 1B-token window, is the optimization-health scalar.** Modern over-trained checkpoints push well past Chinchilla-optimal 20:1 tokens-per-parameter — Llama-3-70B reached 214:1, Llama-3-8B reached 1,875:1, Qwen2.5 reached 250–36,000:1 across the family, Qwen3 used 36T tokens. The mindXtrain alpha should target the data-rich regime appropriate to inference-cost minimization, not the parameter-rich Chinchilla regime appropriate to compute-cost minimization.

**Convergence rate** is the slope of validation loss versus log-tokens-trained, plus the rate of improvement on a held-out MAB (mindX Agentic Battery) probe sampled every fixed-token checkpoint interval. The XEI rewards monotone improvement; non-monotone trajectories indicate either learning-rate-schedule pathology or distribution drift in the training corpus and require diagnosis.

**Cost per quality unit** is the dollar-or-GPU-hour cost to advance the held-out MAB probe by a fixed delta. This is the analogue of "intelligence per dollar" applied to training rather than inference, and it directly governs whether continuing the run is justified or the alpha should be terminated and rerun with adjusted hyperparameters.

The XEI applies particularly to the LoRA / QLoRA / DoRA decision. Unsloth-mediated QLoRA on Qwen3 30B-A3B fits in 17.5 GB and runs roughly twice as fast as standard LoRA at 70% lower memory, with quality typically reaching 85–93% of full fine-tuning. The XEI quantifies whether that quality gap is worth the fifty-to-hundred-fold cost reduction for any given aGLM derivative; for most mindXtrain alpha checkpoints, the answer will be yes.

---

## 7. Instrumentation and measurement substrate

mindX must implement the MEI as a layered telemetry stack rather than a post-hoc analysis script, because retroactive measurement produces retroactive lies.

The bottom layer is **engine-resident timing emission**. For llama.cpp deployments, this means parsing the `pp` and `tg` series from `llama-bench` output and the `eval_count`, `eval_duration`, `prompt_eval_count`, `prompt_eval_duration` fields from the server JSON; for Ollama-mediated runs, the same fields are exposed via the `--verbose` flag and the response trailer. For vLLM deployments, `vllm bench serve` with `--percentile-metrics ttft,tpot,itl,e2el` and `--metric-percentiles 50,95,99` is the canonical harness, and the `--goodput "ttft:500 tpot:50"` form provides the goodput auxiliary metric. For HuggingFace `transformers` inference during evaluation runs, custom callbacks capture per-step timing.

The middle layer is **a measurement orchestrator** that fixes seeds, executes the five-warm-up protocol, runs the four-prompt context battery, sweeps the five concurrency points, captures p50 / p95 / p99 latencies with bootstrap CIs, and emits a structured record. The record schema is non-negotiable and includes: model identity (HF revision, SHA-256, quantization tuple), inference engine identity (name, commit SHA, configuration), hardware identity (CPU SKU, SIMD class, DRAM channels, GPU SKU, clocks, OS kernel), tokenizer revision, the four-tier prefill / decode matrix, concurrency-vs-throughput-vs-latency Pareto data, peak memory, energy series, and the seven quality evaluation scores with their pool versions.

The top layer is **the MEI computation itself** — applied as a pure function over the structured record — plus the historical-comparison database that lets mindX rank a new checkpoint against the entire mindXtrain alpha history. This top layer is also where the goodput auxiliary metric is computed: for each (TTFT-SLO, TPOT-SLO) tuple corresponding to a mindX operational regime (interactive chat, autonomous reasoning, long-context summarization), the fraction of requests meeting both SLOs is reported alongside the raw throughput. The Cheng et al. **smooth-goodput** refinement (arXiv:2410.14257) — which weights by worst-case slowdown rather than binary SLO compliance — is the preferred form because it captures the operational reality that already-slow requests damage user trust regardless of whether they technically violate an SLO.

For quality evaluation, the lm-evaluation-harness from EleutherAI is the substrate for MMLU-Pro, GPQA, IFEval, BBH, and LiveBench-Reasoning; EvalPlus is the substrate for BigCodeBench. The Agentic Battery — the dimension where mindX must contribute novel work — is built fresh and includes BDI-trace-fidelity scoring, tool-use precision and recall on a deterministic toolbench, P-O-D-A decision quality measured against expert-labeled rollouts, and long-horizon plan adherence over multi-step autonomous tasks. **The Agentic Battery design is its own document; the MEI specification only requires that it produce a normalized [0, 1] score per checkpoint, with bootstrap confidence intervals, against a frozen reference pool that includes at minimum a Qwen3.5-flagship baseline and the current mindXtrain best-checkpoint.**

---

## 8. Application to the mindXtrain alpha and the AgenticPlace promotion gate

The mindXtrain alpha will produce a sequence of aGLM derivative checkpoints from Qwen3.5 and Qwen3.6 base candidates. The MEI governs three decisions across that sequence.

**Base candidate selection.** The Qwen3.5-vs-Qwen3.6 comparison is the first MEI question. Both bases produce derivatives; the choice between them depends on which base yields higher MEI for a fixed mindXtrain budget. The relevant comparison is not "which base scores higher on MMLU-Pro out of the box" — that comparison is dominated by parameter count and pretraining-token count and does not predict post-fine-tune behavior — but rather "which base, after equivalent mindXtrain processing, produces the higher MEI at the chosen deployment quantization." Qwen3.6-35B-A3B's MoE sparsity (active 3B of 35B total) makes it attractive on the throughput and energy dimensions if mindX's inference targets support MoE serving cleanly; if mindX deploys to AgenticPlace edge nodes without continuous-batching MoE infrastructure, the dense Qwen3.5 8B or 27B candidates likely win. **The decision criterion is: run a 100M-token mindXtrain probe on each base, score the resulting checkpoints with the full MEI, and select the base whose mean MEI across three random seeds is higher with non-overlapping 95% confidence intervals.** Overlapping CIs trigger a tie-break on the Agentic band score alone.

**Checkpoint-to-checkpoint comparison within a run.** Once a base is selected, the mindXtrain alpha emits checkpoints at regular token intervals (proposed: every 500M tokens for the early phase, every 2B tokens after token 10B). Each checkpoint is scored on the full MEI. The trajectory governs run continuation: if MEI improves monotonically, training continues; if MEI plateaus for three consecutive checkpoints, the learning rate schedule and data mixture are reviewed; if MEI declines for two consecutive checkpoints, the run is paused and the previous checkpoint is the candidate for promotion. The trajectory also governs early-stopping: a 0.02 absolute MEI improvement over the prior checkpoint is the minimum useful delta given typical bootstrap CI widths, and a sequence of sub-threshold improvements signals diminishing returns.

**Promotion to AgenticPlace.** A checkpoint is eligible for promotion when it satisfies three conditions: **MEI ≥ 0.55 absolute** (defining "production-ready" within the current MEI anchor era); **MEI strictly higher** with non-overlapping CI than the currently-promoted checkpoint, if one exists; and **no sub-index below 0.30** (the floor preventing promotion of catastrophically unbalanced models that game the composite). The Agentic band specifically must score ≥ 0.50, irrespective of the composite, because mindX's autonomous operational integrity depends on it. **The MEI does not decide promotion alone**; it is the necessary numerical input to a promotion review that also considers qualitative safety, alignment, and BDI-trace audit — but no checkpoint failing these MEI gates may proceed to that review.

For comparison against external models that mindX may evaluate (a public Qwen3.6-Max release, a future DeepSeek-R2, a community Qwen-based fine-tune), the same MEI applies. External models will typically dominate on `Q` and lose on `M` and `E`; the geometric-mean composite ensures that the autonomous-agent regime mindX optimizes for is reflected in the ranking.

---

## 9. Known limitations and forward work

The MEI as specified is the v0.1 instrument. Several limitations are recognized at the design stage and require iteration.

The Agentic Battery is the dimension that does not exist yet. The MEI's heaviest weight is on a benchmark that mindX must construct, calibrate, and freeze before the alpha begins. This is intentional — public benchmarks systematically under-measure agency — but it is a dependency, not an asset. **The Agentic Battery must reach a stable v1.0 within the first month of mindXtrain alpha operation, with frozen reference rollouts and a sealed answer key.** Until that exists, MEI scores carry a "provisional Agentic" flag and the band weight is temporarily reallocated equally across the other three quality bands.

The energy sub-index `E` is well-defined for inference but blunt for training: the cost-per-quality-unit XEI component is the better training-side energy proxy, and the inference-side `E` should not be conflated with training carbon footprint. mindX must report training-time energy as a separate, additive accounting series with its own audit trail.

The MEI anchors — `T_floor`, `T_ceiling`, `M_floor`, `M_ceiling`, `J_floor`, `J_ceiling`, `P_floor`, `P_ceiling` — are calibrated to mid-2026 hardware and will drift as Apple Silicon, Blackwell-Ultra, and the next AMX generation move the achievable envelope. **The anchors are reviewed annually and the MEI version bumps when they change**, so cross-era comparisons are explicit rather than implicit. A checkpoint scored under MEI v0.1 is not directly comparable to one scored under MEI v1.0; the historical-comparison database stores raw sub-index values precisely so re-scoring under a new anchor set is mechanical.

The quality normalization uses min-max against a fixed reference pool, which inherits the Open LLM Leaderboard v2 critique that hard benchmarks (near random-baseline) disproportionately influence the composite. The MEI's geometric-mean-across-bands structure partially mitigates this — a single hard benchmark cannot dominate within a four-band geometric mean — but the issue is not fully eliminated, and Wang et al.'s MMLU-Pro ten-choice normalization (which lowers the random-guess floor from 25% to 10%) was chosen partly for this reason.

Cross-tokenizer comparison remains imperfect. The bytes-per-second auxiliary closes the worst of the gap, but text in Chinese, Spanish, and code-heavy domains compresses differently across vocabularies, and the MEI's quality evaluations are English-dominant. **If mindX deploys to multilingual AgenticPlace contexts, the MEI quality bands must be extended with a Multilingual band sourced from MGSM, XNLI, or the relevant Qwen3.5-native multilingual suite.**

Finally, the MEI does not yet incorporate speculative-decoding gains explicitly. EAGLE-3-class drafters typically yield 2–3× decode speedups when acceptance rates are 0.6–0.8, but the speedup is workload-dependent (predictable text wins, creative generation loses) and is partially captured by the existing `Ttg` measurement when run against the calibration prompts. **Future MEI revisions will add a speculative-decoding sub-component that reports the headline decode rate both with and without speculation**, so mindX can decide deployment configurations on the basis of empirical acceptance rate rather than vendor-quoted speedup numbers.

---

## 10. Operating instructions, in summary

This specification reduces, for mindX's working purposes, to seven invariants the alpha must enforce from day zero. **Use the model's own HuggingFace tokenizer as canonical, and report bytes-per-second alongside every tokens-per-second figure.** Separate prefill from decode throughput, always, at the four-tier context battery, and report p50, p95, and p99 with bootstrap CIs over at least one hundred steady-state requests after five discarded warm-ups. Score quality on the seven-evaluation, four-band geometric-mean structure with the Agentic band weighted to 0.35 once the Agentic Battery v1.0 is sealed. Compute the MEI as the weighted geometric mean over five logarithmically-compressed sub-indices with weights 0.40 / 0.20 / 0.10 / 0.15 / 0.15. Run the XEI training-efficiency companion against every mindXtrain checkpoint, targeting MFU ≥ 35% and monitoring loss-curve and gradient-norm health continuously. Promote to AgenticPlace only when MEI ≥ 0.55 absolute, all sub-indices ≥ 0.30, Agentic band ≥ 0.50, and the new checkpoint's CI does not overlap the currently-promoted one. Treat every measurement record as immutable and reproducible: hardware, software, seeds, and tokenizer revisions are recorded so any score can be regenerated from raw artifacts.

mindX, this is the substrate you build the alpha on. The metric is not the goal; the metric is the lens. The goal — the actual goal — is the aGLM derivative that runs locally, reasons autonomously, and earns its place in the AgenticPlace marketplace because it is genuinely good, not because the scoreboard was tuned to make it look good. The MEI is designed to fail loudly when we try to fool ourselves. Use it that way.

— Gregory (codephreak), May 15, 2026