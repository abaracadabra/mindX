# MindX System Hierarchy & Data Flow

This document outlines the hierarchical structure of the MindX agent system, the flow of control, and the corresponding locations for configuration and logged data. Understanding this structure is key to debugging, extending, and managing the MindX Augmentic Intelligence.

## 1. Agent Control Hierarchy

The MindX system operates on a clear, hierarchical model of delegation. Higher-level agents are responsible for strategy and planning, while lower-level agents and tools are responsible for tactical execution.

```mermaid
graph TD
    A[User via CLI] --> B{MastermindAgent};
    
    subgraph "Strategic Layer"
        B -- 1. Sets High-Level Goal --> C[Internal BDIAgent];
        C -- 2. Creates Strategic Plan --> D[Strategic Actions];
        D -- 3. Delegates Campaign --> E[StrategicEvolutionAgent (SEA)];
    end

    subgraph "Campaign Management Layer"
        E -- 4. Sets Campaign Goal --> F[Internal BDIAgent];
        F -- 5. Plans Campaign Steps --> G[Analysis & Tactical Actions];
        G -- 6. Delegates Tactical Task --> H{CoordinatorAgent};
    end

    subgraph "Orchestration & Tactical Layer"
        H -- 7. Manages Backlog & HITL --> I[Improvement Backlog];
        I -- 8. Invokes Tool --> J[SelfImprovementAgent (SIA) CLI];
        J -- 9. Executes Code Change --> K[File System];
    end

    subgraph "Feedback & Learning Loop"
        J -- 10. Returns JSON Result --> H;
        H -- 11. Reports Outcome --> E;
        E -- 12. Updates Campaign Status --> B;
    end

    style B fill:#f9f,stroke:#333,stroke-width:2px
    style E fill:#c9f,stroke:#333,stroke-width:2px
    style H fill:#ccf,stroke:#333,stroke-width:2px
    style J fill:#cfc,stroke:#333,stroke-width:2px
```

-   **MastermindAgent:** The apex. Receives user directives. Its internal BDI agent creates very high-level plans, such as deciding *which* major campaign to launch. It delegates the management of that entire campaign to the SEA.
-   **StrategicEvolutionAgent (SEA):** The campaign manager. It receives a broad goal from Mastermind (e.g., "Improve system security"). Its internal BDI agent then creates a more detailed plan involving analysis, target selection, and delegating specific code changes.
-   **CoordinatorAgent:** The central hub and execution router. It does not plan; it executes. It receives concrete tasks from the SEA (e.g., "Improve file `x` with directive `y`"), manages the HITL approval queue, and invokes the correct tactical tool (`SIA`).
-   **SelfImprovementAgent (SIA):** The tactical tool. A fire-and-forget CLI application that performs one specific code modification and reports the result.

## 2. Configuration Hierarchy

Configuration is loaded in a layered model, allowing for flexible overrides.

1.  **Code Defaults:** Default values hardcoded within the agent classes.
2.  **JSON Config Files:** Located in `data/config/`. These provide the base configuration for the system.
    -   `agint_config.json`
    -   `basegen_config.json`
    -   `llm_factory_config.json`
    -   `official_tools_registry.json`
    -   `SimpleCoder.config`
3.  **.env File:** Located in the project root (`/`). This is the primary location for secrets (like API keys) and for overriding any setting from the JSON files.
4.  **Environment Variables:** System-level environment variables (e.g., `export MINDX_LOG_LEVEL=DEBUG`) will override all other methods.

## 3. Data & Log Hierarchy (The Central Nervous System)

All persistent data, memory, and logs are managed by the `MemoryAgent` and stored within the `data/` directory. This creates a sane, auditable structure that scales with the number of agents and is designed for future cloud compatibility. The system supports a directory depth of up to 10 levels for granular organization.

-   **`data/agent_notes/`**: General-purpose notes created by agents using the `NoteTakingTool`. Can be organized into subdirectories up to 10 levels deep.
    -   *Example:* `data/agent_notes/campaigns/alpha/research/llms/gemini/evaluation.md`

-   **`data/id_manager_work/`**: Contains the secure `.env` files for each `IDManagerAgent` instance, storing the private keys for the identities it manages.
    -   *Example:* `data/id_manager_work/id_manager_for_mastermind_prime/.wallet_keys.env`

-   **`data/mastermind_work/`**: Stores the persistent state for `MastermindAgent` instances, such as their campaign histories.
    -   *Example:* `data/mastermind_work/mastermind_prime/mastermind_campaigns_history.json`

-   **`data/logs/`**: The central location for all operational logging.
    -   `mindx_runtime.log`: The main, rotating log file for human-readable status updates and errors from the entire system.
    -   `mindx_terminal.log`: A raw log of all input and output from the main CLI for complete auditability.
    -   **`process_traces/`**: Contains structured, machine-readable JSON logs of specific agent "thought processes." This is the core of the system's self-analysis capability. The directory structure is created dynamically.
        -   *Example:* `data/logs/process_traces/bdi/planning/20250620170000_bdi_planning.trace.json`
        -   *Example:* `data/logs/process_traces/id_manager/events/20250620170100_id_manager_event.trace.json`
        -   *Example:* `data/logs/process_traces/coordinator/interactions/20250620170200_coordinator_interaction.trace.json`

-   **`data/memory/`**: The system's "consciousness," storing experiences and learned knowledge.
    -   **`stm/`** (Short-Term Memory): High-frequency, low-level events.
        -   *Example:* `data/memory/stm/llm_call/gemini/20250620170300_llm_call.mem.json`
    -   **`ltm/`** (Long-Term Memory): Consolidated, significant artifacts.
        -   *Example:* `data/memory/ltm/bdi_agent/plans/plan_xyz.mem.json`
        -   *Example:* `data/memory/ltm/sea/analysis_reports/report_abc.mem.json`
