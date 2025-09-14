# `bdi_agent.py`

## 1. Overview

The `BDIAgent` (Belief-Desire-Intention) is the core reasoning and execution engine for goal-directed autonomous behavior in the MindX system. It is designed to be a subordinate component, instantiated and directed by higher-level agents like the `MastermindAgent`.

This agent takes a high-level goal, uses a Large Language Model (LLM) to create a step-by-step plan to achieve it, and then executes that plan. Its reasoning process is now guided by a "persona," a system prompt provided by the `AutoMINDXAgent`, which makes its planning more focused and context-aware.

## 2. Core Architecture & Workflow

The `BDIAgent` operates on the classic Belief-Desire-Intention model, but with its cognitive functions powered by an LLM.

### Persona-Driven Reasoning

A key feature of the `BDIAgent` is that its planning process is guided by a `persona_prompt`.

-   **Initialization:** The `BDIAgent`'s constructor now accepts a `persona_prompt: str` argument. This is typically provided by the parent agent (e.g., `MastermindAgent`) after fetching it from the `AutoMINDXAgent`.
-   **Plan Generation:** When the `plan()` method is called, this persona is prepended to the prompt sent to the LLM. This primes the LLM to adopt the desired mindset (e.g., "expert orchestrator") before it begins to generate the action plan.

### BDI Cycle

1.  **Deliberate:** The agent examines its "desires" (a priority queue of goals) and selects the highest-priority goal to pursue.
2.  **Plan:** It uses its persona-driven LLM to generate a sequence of actions (a plan) to achieve the selected goal. This process includes a self-correcting loop to ensure the generated plan is valid and uses only known actions.
3.  **Execute:** It executes the actions in the plan one by one. Actions can range from calling other tools (like `NoteTakingTool` or `SimpleCoder`) to performing internal cognitive tasks (like analyzing data or updating its own beliefs).

### Key Components

-   **Beliefs (`BeliefSystem`):** The agent is connected to the central, shared `BeliefSystem` to read and write information.
-   **Desires (Goal Management):** A priority queue manages all assigned goals.
-   **Intentions (Plan Management):** The agent holds the currently active plan, which is a list of executable actions.
-   **Action Handlers:** A dictionary maps action names (e.g., `CREATE_AGENT`, `EXECUTE_SIMPLE_CODER_TASK`) to the Python methods that implement them.
-   **Tool Loading:** During its `_initialize_tools_async` phase, the agent reads the `tools_registry` dictionary it received in its constructor. It iterates through the enabled tools, dynamically imports their modules and classes, and creates an instance of each, making them available for use in its plans.

## 3. Integration with the System

The `BDIAgent` is not a standalone entity. It is a component that is created and used by other agents.

-   **Instantiation:** A higher-level agent, like `MastermindAgent`, instantiates the `BDIAgent`.
-   **Persona Injection:** The parent agent is responsible for fetching the appropriate persona from `AutoMINDX` and passing it to the `BDIAgent` during construction.
-   **Goal Setting:** The parent agent gives the `BDIAgent` high-level goals to achieve using the `set_goal()` method.
-   **Execution:** The parent agent starts the BDI cycle by calling the `run()` method.

---
### 4. Evolved Capabilities

The `BDIAgent` has been evolved to be significantly more robust and intelligent in its planning and execution, embodying the principle that every error is an opportunity to improve.

#### 4.1. Context-Aware Planning

The agent's planning process is no longer limited to the static information in its initial prompt. It can now actively seek context about the system's environment before generating a plan.

*   **Dynamic Path Finding:** When given a goal to evolve a software component (e.g., "Evolve the BDIAgent"), the agent now uses the `TreeAgent` tool to execute a `find` command. This allows it to locate the exact file path of the component it needs to modify.
*   **Actionable Plans:** This discovered path is then injected directly into the planning prompt. This ensures that the LLM generates a plan with real, valid file paths instead of placeholders, preventing a common class of execution failures.

#### 4.2. Resilience to API Failures

The planning loop has been hardened to handle transient errors from its dependencies, particularly the LLM handler.

*   **Rate Limit Recovery:** If the LLM handler returns a rate limit error during plan generation, the `BDIAgent` no longer fails. It now recognizes this specific error, pauses for several seconds, and then automatically retries the planning attempt. This allows it to recover from temporary API throttling without manual intervention and without crashing the entire task.
