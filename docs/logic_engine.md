# `logic_engine.py`

## 1. Overview

The `LogicEngine` is a utility component designed to provide a layer of formal, deterministic reasoning to MindX agents. It allows agents to define a set of logical rules and constraints, and then use those rules to perform inference or check the consistency of their own beliefs.

This is particularly useful for ensuring that agent behavior remains predictable and safe, and for enabling more complex decision-making without relying solely on a probabilistic LLM.

## 2. Core Components

### `SafeExpressionEvaluator`

This is a critical security component. It provides a way to safely evaluate a string containing a Python-like expression.

-   **AST Parsing:** It parses the expression into an Abstract Syntax Tree (AST).
-   **Whitelisting:** It walks the AST and only allows a specific whitelist of safe operators (`+`, `-`, `==`, `and`, `or`, etc.) and functions (`len`, `str`, `isinstance`, etc.).
-   **Sandboxed:** It prevents access to dangerous operations like file I/O, network access, or arbitrary code execution, ensuring that a malformed or malicious rule cannot harm the system.

### `LogicalRule`

This class represents a single `IF condition THEN effects` rule.

-   **`condition_expr`:** A string containing a Python-like expression that will be evaluated by the `SafeExpressionEvaluator`. It must evaluate to a boolean (`True` or `False`).
-   **`effects`:** A list of actions to be taken if the condition is `True`. A common effect is to `set_belief` to add a new derived fact to the `BeliefSystem`.
-   **`is_constraint`:** A boolean flag. If `True`, the rule is treated as a consistency check; the system expects the condition to always be `True`.

### `LogicEngine` Class

This is the main class that an agent would interact with.

-   **Rule Management:** It holds a dictionary of `LogicalRule` objects.
-   **Forward Chaining (`forward_chain`):** This is the primary inference method. It repeatedly iterates through all the rules, evaluating their conditions against the current set of beliefs. If a rule's condition is met, its effects are applied, potentially creating new beliefs that can trigger other rules in the next iteration. This process continues until no new beliefs can be derived.
-   **Consistency Checking (`check_consistency`):** This method evaluates all rules where `is_constraint` is `True`. It returns a list of any constraints that are violated (i.e., whose conditions evaluate to `False`), allowing an agent to detect when its own beliefs are in an inconsistent or illogical state.
-   **Socratic Questioning (`generate_socratic_questions`):** An advanced feature that uses an LLM to analyze an agent's current beliefs about a topic and generate a list of challenging, Socratic questions to help the agent identify hidden assumptions or flaws in its reasoning.

## 3. Integration with the System

The `LogicEngine` is not a standalone agent but a utility that can be instantiated by any agent that requires formal reasoning capabilities. An agent would:
1.  Create an instance of the `LogicEngine`.
2.  Load a set of rules, either from a configuration file or by adding them programmatically.
3.  Periodically call `forward_chain()` or `check_consistency()` with its current set of beliefs to derive new insights or validate its worldview.
