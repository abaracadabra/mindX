# The Compute Plant — mindX's power model

mindX treats **each core as the computer processor it is** and optimizes for
**return from the smallest unit**: the **powerplant = 1 core + 2.048 GB RAM**. It
designs to scale by **powers of two** (RAM 2→4→8→16→32→64 GB; cores 1→2→4→8…).

## Per-core roles

On any host, cores are allocated by role (`agents/monitoring/compute_plant.py:allocation()`):

| role | share | purpose |
|---|---|---|
| **surface** | 1 core + ~25% RAM | day-to-day + the public-facing surface (web serving) |
| **training** | 1 core | mindXtrain — `/data → machine.dream → mindXmodel` (one core; we have time) |
| **spare** | the rest | an open processor for everything else |

One core + 25% RAM is more than enough for the day-to-day surface, leaving an open
processor for everything else; a second core drives training. The scale ladder
(`scale_ladder()`) plans each power-of-two tier:

```
 2 GB → 1 core   surface
 4 GB → 2 cores  surface + training
 8 GB → 3 cores  surface + training + 1 spare
16 GB → 4 cores  surface + 2 training + 1 spare
32 GB → 5 cores  surface + 2 training + 2 spare
64 GB → 6 cores  surface + 3 training + 2 spare
```

## Scientific CPU diagnostics

- **Frequency** (`frequency()`) — chip current/min/max MHz + **per-core MHz** (psutil `cpu_freq`).
- **Cycles** (`cycles()`) — work in flight, not just percent-busy: Σ_core (freq_hz ×
  utilisation) = **Gcycle/s**, per-core and total. A core at 50% of 3 GHz is 1.5 Gcycle/s.

## The governor (`agents/resource_governor.py`)

- **CPU ceiling = 99%** (`MINDX_MAX_AUTONOMOUS_CPU`) — run the box hot to maximize
  inference, **as long as temperature is acceptable**. `effective_ceiling()` backs the
  ceiling off (2 %-pts per °C, floor 75%) once `_cpu_temp()` exceeds `max_cpu_temp`
  (85°C, `MINDX_MAX_CPU_TEMP`). No sensor (VPS) → fail-open at the full ceiling.
- **`inference_cores = 2`** (`MINDX_INFERENCE_CORES`) — cores reserved for inference/training.
- `should_throttle()` / `throttle_for_cpu()` gate the autonomous loops against
  `effective_ceiling()` — full speed when there is headroom, yield when over.

## Monitoring, control, awareness

- **Read**: `agents/monitoring/resource_monitor.py:get_resource_usage()` carries a
  `governor` block (effective ceiling, temp, inference_cores, over_ceiling, headroom).
- **Control** (governor testing): `agents/monitoring/resource_control.py` — per-core
  CPU load (`set_cores`), RAM hold (`set_ram`), each with a hard self-stop (≤120s).
- **Self-awareness**: `AGInt._perceive` folds the live resource + governor state into
  `state_summary["awareness"]` — the core feels its own load ("CPU 100% over the ceiling
  — throttling autonomous loops" vs "nominal, N% headroom").
- **Eval correlation**: `blueprint.agent.inference_correlation()` ties the ollama/vllm
  engines to live cycles — is the work-in-flight actually inference, at what cost?

## Surfaces

- `GET /insight/system/live` — psutil per-core + RAM + disk + governor + **plant**
  (freq, cycles, allocation) + inference correlation. Lightweight, no Dash/Plotly/React.
- `/machine/admin` — the diagnostics page renders per-core bars (ceiling-marked) + the
  live **plant line** (chip MHz, Gcycle/s, per-core roles, engine dots).
- `blueprint.agent` (`agents/blueprint_agent.py`) owns it: `plant/frequency/cycles/
  resources/per_core/inference_correlation/control_cpu/control_ram`.

## /data → mindXmodel

The training core exists to **shrink `/data` into weights**: `/data` (logs = memories)
→ `machine.dream` consolidation → **mindXtrain** (dream→weights) → **mindXmodel**. The
plant reserves a core for this so the model grows as the raw data footprint shrinks —
optimizing return on the powerplant unit. See [SCHMIDHUBER_ENGINE](SCHMIDHUBER_ENGINE.md)
+ [MINDXTRAIN_INSTALL](MINDXTRAIN_INSTALL.md).
