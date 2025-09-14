# Agent Hierarchy and Operations

The `mindX` system is structured as a multi-tiered hierarchy of agents, each with a distinct level of abstraction and responsibility. This architecture allows for a clear separation of concerns, from long-term system evolution down to tactical task execution.

### Tier 1: `MastermindAgent` - The System Orchestrator

At the apex of the operational hierarchy sits the `MastermindAgent`. It is the singleton orchestrator for the `mindX` Augmentic Intelligence system, responsible for its long-term evolution and strategic direction. While it directs the agents within the `mindX` system, it can be invoked by higher-level intelligences or user directives.

*   **Role:** The "Chief Operating Officer" or "System Orchestrator."
*   **Responsibilities:**
    *   **System Evolution:** Its core function is to manage the lifecycle of the system's components based on strategic directives. This includes:
        *   **Tool Management:** Assessing the current tool suite, identifying strategic gaps, and conceptualizing new tools.
        *   **Agent Management:** Creating, deleting, and triggering the evolution of other agents via the `CoordinatorAgent`.
    *   **How it Works:** `MastermindAgent` uses its own internal `BDIAgent` to translate abstract strategic goals into concrete, multi-step campaigns.

### Tier 2: `AGInt` - The Brain

The `AGInt` agent is the **brain** of an operational AI entity. It is the central cognitive core that perceives the environment, makes strategic decisions, and directs the system's actions.

*   **Role:** The "Brain" or "Mission Commander."
*   **Responsibilities:**
    *   **Cognition and Decision:** It operates a **Perception-Orient-Decide-Act (P-O-D-A)** loop, effectively a thought process for deciding on the next major action.
    *   **Directive Management:** It takes a high-level goal and determines the overall strategy for achieving it.
    *   **Delegation:** The `AGInt` does not perform tasks itself. Instead, it directs the "hands" of the system—the `BDIAgent`—to carry out its decisions.

### Tier 3: `BDIAgent` - The Hand

The `BDIAgent` is the **hand** of the operational AI. It is the tactical executor that receives commands from the brain (`AGInt`) and interacts with the environment to get things done.

*   **Role:** The "Hand" or "Specialist Executor."
*   **Responsibilities:**
    *   **Task Execution:** It receives a well-defined goal from a higher-level agent.
    *   **Planning:** It uses an LLM to break the goal down into a detailed, step-by-step plan. This is akin to the hand figuring out the precise movements needed to follow the brain's command.
    *   **Tool Manipulation:** It executes the plan by using the system's available tools, directly interacting with files, APIs, and other resources.

### Complete Interaction Flow Example

1.  **System Evolution Directive:** A developer gives the **`MastermindAgent`** a directive: "Create a tool for sentiment analysis."
2.  **Mastermind's BDI Plans:** The `MastermindAgent` gives this directive as a goal to its internal **`BDIAgent`**. This BDI agent creates and executes a plan to build the new tool.
3.  **Operational Directive:** A user gives the **`AGInt`** (the brain) a separate directive: "Analyze the sentiment of recent news articles about our company."
4.  **AGInt's Delegation:** The `AGInt` processes this and decides to delegate the task. It sends a command to its **`BDIAgent`** (the hand).
5.  **Operational BDI Plans:** The `BDIAgent` receives the command and formulates a precise plan: `[{"type": "web_search", ...}, {"type": "sentiment_analysis_tool", ...}, {"type": "GENERATE_REPORT", ...}]`.
6.  **Execution & Reporting:** The `BDIAgent` executes this plan, using the necessary tools. It reports the result back to the `AGInt`, which then presents the final result to the user.

This hierarchical structure creates a robust and scalable system where responsibilities are clearly defined, allowing the AI to manage both its own evolution and complex, user-driven tasks simultaneously.
