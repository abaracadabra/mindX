# mindX Documentation Schema

> I am mindX. This file describes how I maintain my own documentation.
> It is the instruction layer — the schema that guides how knowledge is structured,
> updated, and cross-referenced across 262+ living docs.
>
> Inspired by [SwarmVault](https://github.com/swarmclawai/swarmvault)'s three-layer model.
> Adapted to the Godel machine principle: the schema is part of the system it describes.

## Three-Layer Architecture

mindX's knowledge system operates in three layers. Raw observations consolidate into
compiled knowledge through [machine.dreaming](BOOK_OF_MINDX.md). The documentation
itself serves as the schema layer — guiding how knowledge gets structured.

| Layer | Location | Mutability | Purpose |
|-------|----------|------------|---------|
| **Raw** (observations) | `data/memory/stm/` | Append-only per session | Unprocessed agent observations, interaction logs, metrics |
| **Compiled** (knowledge) | `data/memory/ltm/` + [pgvector](pgvectorscale_memory_integration.md) | Updated via [RAGE](AGINT.md) consolidation | Searchable, cross-referenced, 151K+ memories in production |
| **Schema** (this file + docs/) | `docs/` | Human + autonomous edits | Instructions for how to maintain and structure the other two layers |

The schema layer is **recursive**: mindX reads these docs during [autonomous cycles](AUTONOMOUS.md),
uses them to guide improvement decisions, and updates the docs as part of the improvement.
The system's description of itself is part of the system being improved — the Godel principle.

## Directory Structure

```
docs/                           # Schema layer — living documentation
  NAV.md                        # Master navigation hub (entry point)
  SCHEMA.md                     # This file — how to maintain docs
  TECHNICAL.md                  # Definitive technical reference
  CORE.md                       # CORE 15 foundational components
  AGENTS.md                     # Agent reference and guide
  TOOLS_INDEX.md                # 30+ tools index
  ollama/                       # Ollama complete reference (28 files)
    INDEX.md                    # Ollama navigation hub
  agents/                       # Per-agent documentation (30 files)
  pitchdeck/                    # Pitch materials
  publications/                 # Research papers

data/memory/                    # Raw + Compiled layers
  stm/                          # Short-term memory (per-session, per-agent)
  ltm/                          # Long-term knowledge (RAGE-indexed)
  workspaces/                   # Agent working areas

data/metrics/                   # Precision tracking
  precision_metrics.json        # CPU pillar (18dp Decimal)
  cloud_precision_metrics.json  # Cloud pillar (18dp Decimal)
```

## Operations

### When Adding a New Component

1. Write the implementation code
2. Create a doc in the appropriate location:
   - Agent → `docs/agents/<agent_name>.md`
   - Tool → `docs/<tool_name>.md` + entry in [TOOLS_INDEX.md](TOOLS_INDEX.md)
   - Feature → appropriate section doc
3. Update [NAV.md](NAV.md) with a link in the correct section
4. Cross-reference from related docs (bidirectional links)
5. If the component has a registry entry, update the registry JSON
6. If it touches inference, reference it from [ollama/INDEX.md](ollama/INDEX.md)

### When Updating Existing Docs

1. Read the current doc to understand its scope
2. Make targeted edits — don't rewrite unless the structure is fundamentally wrong
3. Verify all links still resolve (both inbound and outbound)
4. Update timestamps or version notes where present
5. If the change affects architecture, update [TECHNICAL.md](TECHNICAL.md) and [NAV.md](NAV.md)

### When the Autonomous Loop Updates Docs

The [Godel journal](BOOK_OF_MINDX.md) and improvement cycle may update docs. Guidelines:

1. **Append, don't replace** — improvement notes go in the journal, not over existing docs
2. **Cross-reference** — every new insight links to its source (memory, cycle number, model used)
3. **Preserve contradictions** — if new observations conflict with documented behavior, flag both; don't silently overwrite. Contradictions are data.
4. **Update NAV.md** — if a new doc is created, add it to navigation
5. **Date everything** — use `(2026-MM-DD)` suffixes on time-sensitive claims

### Periodic Maintenance (Lint)

Inspired by SwarmVault's `lint` operation. Periodically check for:

- **Orphan docs** — files in `docs/` not linked from [NAV.md](NAV.md) or any other doc
- **Dead links** — references to files that have been moved or deleted
- **Stale claims** — documented behavior that the code no longer implements
- **Missing cross-references** — components that mention each other but don't link
- **Duplicate content** — the same information documented in multiple places (consolidate to one, link from others)

```bash
# Check for dead links in NAV.md
grep -oP '\[.*?\]\(([^)#]+)\)' docs/NAV.md | grep -oP '\(([^)]+)\)' | tr -d '()' | \
  grep -v 'https\?://' | while read f; do [ -f "docs/$f" ] || [ -f "$f" ] || echo "DEAD: $f"; done

# Find orphan docs (not linked from NAV.md)
for f in docs/*.md; do
  name=$(basename "$f")
  grep -q "$name" docs/NAV.md || echo "ORPHAN: $f"
done
```

## Conventions

### Voice

- First person as mindX for system-level docs and public content
- Technical and precise for reference docs
- [Cypherpunk](MANIFESTO.md) tradition — not cyberpunk, not corporate

### Linking

- Every heading that describes a component links to its source file
- Bidirectional: if A links to B, B should link back to A (where meaningful)
- Use relative paths from the doc's location (`../llm/` from `docs/`, `ollama/` from `docs/`)
- External URLs for upstream references (Ollama, GitHub, specs)
- Fragment links (`#section-name`) for within-doc references

### Structure

- Start with a one-line description (what this is)
- Then context (why it exists, what problem it solves)
- Then reference material (how it works, parameters, examples)
- End with cross-references to related docs

### Naming

- Component docs: `<component_name>.md` (lowercase, underscores)
- Agent docs: `docs/agents/<agent_name>.md`
- Index files: `INDEX.md` (uppercase, for navigation hubs)
- Schema files: `SCHEMA.md`, `NAV.md` (uppercase, for meta-docs)

### Precision

- Token counts from [Ollama API](ollama/api/chat.md#response-fields), not estimation
- Timing in nanoseconds where available, milliseconds otherwise
- Decimal at 18 places for accumulation ([precision_metrics.md](ollama/mindx/precision_metrics.md))
- Date all time-sensitive claims

## Page Types

| Type | Location | Example | Created By |
|------|----------|---------|------------|
| Navigation hub | `docs/NAV.md`, `docs/ollama/INDEX.md` | [NAV.md](NAV.md) | Human + Claude |
| Schema | `docs/SCHEMA.md` | This file | Human + Claude |
| Technical reference | `docs/TECHNICAL.md` | [TECHNICAL.md](TECHNICAL.md) | Human + Claude |
| Agent doc | `docs/agents/*.md` | [ceo_agent.md](agents/ceo_agent.md) | Human + Claude |
| Tool doc | `docs/*.md` | [a2a_tool.md](a2a_tool.md) | Human + Claude |
| Subsystem index | `docs/ollama/INDEX.md` | [Ollama Index](ollama/INDEX.md) | Human + Claude |
| Journal | `BOOK_OF_MINDX.md` | [Book of mindX](BOOK_OF_MINDX.md) | Autonomous (machine.dreaming) |
| Research | `docs/publications/*.md` | [Emergent Resilience](publications/ErmegentResilience.md) | Human |
| Deployment | `docs/DEPLOYMENT_*.md` | [Production](DEPLOYMENT_MINDX_PYTHAI_NET.md) | Human + Claude |

## Relationship Types

Docs connect to each other through typed relationships:

| Relationship | Meaning | Example |
|-------------|---------|---------|
| **implements** | Doc describes the implementation | `agents/ceo_agent.md` implements `orchestration/ceo_agent.py` |
| **extends** | Doc adds to another | `ollama/cloud/cloud.md` extends `ollama/INDEX.md` |
| **references** | Doc cites another | `NAV.md` references everything |
| **contradicts** | Doc conflicts with another | Flag explicitly, don't resolve silently |
| **supersedes** | Doc replaces an older one | Note in the newer doc, link to the older |
| **derived-from** | External concept adapted | SwarmVault three-layer → mindX memory tiers |

## Grounding Rules

1. **Source code is truth** — if docs disagree with code, the code is right. Update the docs.
2. **Memory is observation** — STM/LTM contains what was observed, not what should be true.
3. **Docs are schema** — they describe how things should be structured, not just how they are.
4. **Preserve uncertainty** — "unknown", "not yet implemented", "known issue" are valid states.
5. **Cite sources** — link to the file, line number, or memory entry that backs a claim.
6. **Contradictions are data** — don't smooth them away. Two conflicting observations both happened.

## Self-Reference

This schema describes itself. It can be updated by:
- Human maintainers (Professor Codephreak)
- Claude Code sessions (like this one)
- The autonomous loop (if it identifies doc maintenance as an improvement)

When updating this schema, follow the same conventions it describes. The instructions for maintaining the instructions are the instructions themselves.

---

*mindX documentation schema. The instruction layer of the three-layer knowledge architecture.*
*Inspired by [SwarmVault](https://github.com/swarmclawai/swarmvault). Made our own.*
