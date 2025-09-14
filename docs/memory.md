# `memory_agent.py`

## 1. Overview

The `MemoryAgent` is a foundational component of the MindX system, designed to function as its central persistence layer. It provides a unified, robust, and asynchronous service for all other agents and tools to record their history and to acquire dedicated, managed storage space for their own operational data.

By centralizing file system interactions, the `MemoryAgent` ensures that data is managed consistently, that the directory structure remains sane, and that agent logic is decoupled from storage implementation details.

## 2. Core Architecture & Responsibilities

### Unified Data and Log Management

The `MemoryAgent` consolidates two key functions:

-   **Agent Workspace Management:** Providing each agent with its own dedicated directory for storing persistent data like plans, generated files, or configuration.
-   **Process Trace Logging:** Recording the step-by-step "thought process" of an agent as it works to achieve a goal.

This is all managed through a hierarchical directory structure within the `data/` folder:

-   `data/memory/`: The base directory for agent-specific data.
    -   `data/memory/agent_workspaces/`: Contains a subdirectory for each agent that requires persistent storage (e.g., `mastermind_prime/`, `automindx_agent_main/`).
-   `data/logs/`: The base directory for all logging.
    -   `data/logs/mindx_runtime.log`: The main rotating log file for general system status.
    -   `data/logs/process_traces/`: A directory containing detailed, structured JSON logs of specific agent processes.

### Initialization

The `MemoryAgent` is designed to be one of the first services initialized at startup. It immediately creates the base `data/memory` and `data/logs` directories if they don't exist.

## 3. Key Methods and Usage

### `get_agent_data_directory(self, agent_id)`

-   **Description:** This is the **canonical method** for any agent to get a path to its own dedicated data directory. The method is responsible for creating the directory if it doesn't exist.
-   **Parameters:**
    -   `agent_id` (str): The unique identifier of the agent requesting the directory.
-   **Returns:** A `pathlib.Path` object pointing to the agent's workspace (e.g., `.../data/memory/agent_workspaces/mastermind_prime`).
-   **Usage (from another agent's `__init__`):**
    ```python
    # In MastermindAgent.__init__
    self.data_dir = self.memory_agent.get_agent_data_directory(self.agent_id)
    ```

### `async def log_process(self, process_name, data, metadata)`

-   **Description:** The primary method for logging the "thought process" or significant events of an agent. It saves a detailed, structured trace to the `data/logs/process_traces/` directory.
-   **Parameters:**
    -   `process_name` (str): A descriptive name for the process being logged (e.g., `'bdi_planning'`).
    -   `data` (dict): The JSON-serializable data representing the agent's state or decision.
    -   `metadata` (dict): **Required.** A dictionary for extra context, like `agent_id` or `run_id`.
-   **Usage (from another agent):**
    ```python
    # Inside a BDI agent's planning method
    await self.memory_agent.log_process(
        process_name="bdi_planning",
        data={"goal_id": goal_id, "goal_description": goal_description},
        metadata={"agent_id": self.agent_id}
    )
    ```

### Deprecated Methods

-   **`save_memory()`**: The audit of the codebase revealed that this method, intended for saving to `stm/` and `ltm/` directories, is **not used anywhere**. It should be considered deprecated in favor of agents using their own dedicated workspaces (acquired via `get_agent_data_directory`) for storing artifacts, and `log_process` for recording events.
