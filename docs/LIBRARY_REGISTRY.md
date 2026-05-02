# External Library Registry

mindX maintains a structured catalogue of external Python libraries for building LLM applications. The registry is **awareness, not adoption**: it tells agents (kaizen, mastermind, automindx) what exists in the surrounding open-source ecosystem and how each library relates to mindX-native systems, without dragging the libraries into `requirements.txt`.

The registry exists because of the **Agnostic Modules Principle**: every mindX module is an agnostic, composable peer; mindX is one consumer, not the only home. Knowing what's outside the walls is part of staying composable.

- **File**: [`data/config/library_registry.json`](../data/config/library_registry.json)
- **Initial population**: the 10 libraries from KDnuggets, *"10 Python Libraries for Building LLM Applications"* (2026)
- **Consumer**: [`kaizen.agent`](../agents/kaizen.agent) — references the registry under `KNOWLEDGE DOMAINS` so improvement proposals can check overlap before re-implementing what exists

## Schema

```json
{
  "schema_version": "1.0",
  "last_updated": "YYYY-MM-DD",
  "source": "<URL or note describing where the entries came from>",
  "libraries": {
    "<library_id>": {
      "name": "<display name>",
      "category": "<one of: model_runtime | orchestration | rag_data | inference_serving | fine_tuning | multi_agent | autonomous_agent | agent_orchestration | evaluation | provider_sdk>",
      "homepage": "<URL>",
      "purpose": "<one-line description>",
      "mindx_overlap": "none | partial | full",
      "mindx_status": "in_use | wrapper_present | not_installed",
      "adoption_recommendation": "adopted | investigate | monitor | skip",
      "rationale": "<why this recommendation, with explicit reference to the mindX-native system if applicable>",
      "tags": ["..."]
    }
  }
}
```

### `mindx_overlap`

| Value | Meaning |
|-------|---------|
| `none` | No mindX-native equivalent. Pure gap. |
| `partial` | mindX has overlapping capability but the library covers ground mindX does not. |
| `full` | mindX has a native system that fully covers this library's purpose. |

### `adoption_recommendation`

| Value | Meaning | Triggers |
|-------|---------|----------|
| `adopted` | Already a direct or transitive dependency. | None — informational. |
| `adopted_forked` | Source code adapted into mindX (license-compliant fork of select files). No runtime dep added. | Module README documents what was ported, what was skipped, and the upstream NOTICE. |
| `investigate` | Worth a focused evaluation. | An improvement-backlog entry should exist. |
| `monitor` | Watch for upstream changes; revisit later. | None — passive awareness. |
| `skip` | Overlaps with mindX-native systems; adopting would invert the architecture. | None — record the rationale and move on. |

## How to add a library

1. **Decide if it belongs.** If the library is a *tool* mindX should expose to agents, it belongs in [`augmentic_tools_registry.json`](../data/config/augmentic_tools_registry.json), not here. If it's an *LLM provider*, it belongs in [`provider_registry.json`](../data/config/provider_registry.json). The library registry is for capability libraries that mindX *might or might not* take a dependency on.
2. **Assess overlap honestly.** Read the library's homepage and the relevant mindX system. If mindX already does it, the recommendation is `skip` — record the native system in the rationale (e.g. *"BDI is the equivalent"*).
3. **Append the entry** to `data/config/library_registry.json` under `libraries`. Use a stable lowercase `library_id` (the JSON key).
4. **If `investigate`**, add a matching entry to [`data/improvement_backlog.json`](../data/improvement_backlog.json) with `target_component_path` naming the capability area (e.g. `evaluation.framework`), and reference the registry entry in the justification.
5. **Bump `last_updated`** at the top of the file.

## Consumers

- **kaizen.agent** — has `external_llm_libraries` under `KNOWLEDGE DOMAINS`; reads this registry when proposing capability expansion.
- **Catalogue events** — [`agents/catalogue/events.py`](../agents/catalogue/events.py) has the `library.discover` event kind reserved for future emitters that surface a library decision into the unified event stream.

## Out of scope (deliberately)

- **Installation.** This registry is metadata. Adding an entry does *not* install anything. Installation is a separate decision made via the improvement backlog and code-level integration.
- **Version pinning.** When mindX adopts a library, the version pin lives in `requirements.txt`. This registry tracks awareness at the *project* level, not the version level.
- **Federation.** The registry is a single JSON file. If it becomes hot enough to need IPFS publication, the [storage offload](../agents/storage/) path is the natural extension.
