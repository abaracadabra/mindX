# BlueprintAgent

## Overview

The `BlueprintAgent` is a high-level, meta-planning agent within the MindX evolution framework. Its primary purpose is to conduct a holistic analysis of the entire MindX system and generate a strategic "blueprint" for the next evolutionary iteration. It acts as the chief architect, looking at the system's code, memory, and operational history to decide what to improve next.

This agent is a tool used by the `StrategicEvolutionAgent` to kick off a new improvement campaign.

## Core Architecture & Workflow

### Comprehensive System Analysis

The `BlueprintAgent` has a unique and powerful ability to gather data from multiple, disparate sources across the entire system. Its `_gather_mindx_system_state_summary()` method collects:

- **Cognitive Resources:** A list of all available LLM providers and models from the `ModelRegistry`.
- **Improvement Backlog:** The current state of the `CoordinatorAgent`'s to-do list.
- **Codebase Snapshot:** It directly invokes the `BaseGenAgent` to generate a complete, real-time Markdown summary of the entire project's source code.
- **Recent Agent Actions:** It uses the `MemoryAgent` to read the most recent process trace files from `data/logs/process_traces/`, giving it insight into what the other agents have been doing.
- **Known Limitations:** It queries the shared `BeliefSystem` for any beliefs related to known system limitations.

### Blueprint and To-Do List Generation

The core of the agent is the `generate_next_evolution_blueprint()` method.

1. **Synthesize State:** It gathers all the system state information described above.
2. **LLM-Powered Insight:** It packages this entire state summary into a single, large prompt for a high-capability reasoning model.
3. **Generate Blueprint:** The prompt instructs the LLM to act as a Chief Architect and produce a JSON object containing:
   - A title and version for the new blueprint.
   - 2-3 high-level **Focus Areas** for the next evolution.
   - A list of specific, actionable **Development Goals** for each focus area.
   - A `bdi_todo_list`. This is a list of goal objects, formatted for direct ingestion by a BDI agent.
4. **Seed the Backlog:** After receiving the blueprint, the agent automatically iterates through the `bdi_todo_list` and calls the `CoordinatorAgent` to add each item to the main system improvement backlog.

## Integration with the System

The `BlueprintAgent` is not a standalone agent but a powerful tool in the strategic planning process.

- **Instantiated by SEA:** It is created and owned by the `StrategicEvolutionAgent`.
- **Kicks off Campaigns:** The `SEA` calls `generate_next_evolution_blueprint()` as the first step of a new campaign. This ensures that all strategic evolution is based on a comprehensive, data-driven plan that considers the real-time state of the entire MindX system.
