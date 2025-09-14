# `note_taking_tool.py`

## 1. Overview

The `NoteTakingTool` is a utility component for MindX agents. It provides a flexible mechanism for agents to create, read, update, delete, and list textual notes. Notes are stored as Markdown files (`.md`).

A key feature of this tool is its integration with the `MemoryAgent`. It no longer saves notes to a single, global directory. Instead, it stores notes within the dedicated workspace of the agent that is using the tool, ensuring that an agent's "thoughts" are properly sandboxed.

## 2. Core Architecture & Workflow

### Agent-Specific Storage

-   **`MemoryAgent` Dependency:** The tool's `__init__` method now requires an instance of the `MemoryAgent`.
-   **Dynamic Path Resolution:** When the tool is initialized by the `BDIAgent`, it inspects the `bdi_agent_ref` to get the ID of the calling agent. It then uses `memory_agent.get_agent_data_directory()` to get the correct workspace path for that specific agent.
-   **Directory Structure:** All notes are now stored under `data/memory/agent_workspaces/<calling_agent_id>/notes/`. For example, if the `MastermindAgent`'s BDI agent uses the tool, its notes will be saved in `.../agent_workspaces/bdi_agent_mastermind_strategy_mastermind_prime_.../notes/`.

### Hierarchical Topic/Path Handling

-   The tool retains its ability to create a nested directory structure for notes based on a path-like `topic` string (e.g., `"project_alpha/research/llm_options"`). This structure is now created *within* the calling agent's dedicated notes directory.

### Key Methods

-   **`execute(self, action, ...)`**: The main entry point for the tool. It takes an `action` parameter which can be one of the following:
    -   `add` / `update`: Creates or overwrites a note. Requires `content` and either a `topic` or `file_name`.
    -   `read`: Reads the content of a note. Requires a `topic` or `file_name`.
    -   `delete`: Deletes a note file. Requires a `topic` or `file_name`.
    -   `list`: Lists all notes in the calling agent's notes directory.

## 3. Integration with the System

The `NoteTakingTool` is registered in the `official_tools_registry.json`. The `BDIAgent`'s `_initialize_tools_async` method now intelligently passes the `MemoryAgent` instance to the tool's constructor upon loading. This allows any agent's BDI plan to include an action to `TAKE_NOTES`, and the resulting notes will be correctly and automatically saved to that agent's private workspace.
