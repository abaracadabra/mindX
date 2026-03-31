# mindX Augmentic Intelligence System - Instructions & Overview

**Status:** ✅ **Production Ready** - Enterprise deployment with encrypted vault security
**Last Updated:** March 2026
**Version:** 4.0

##  Introduction

Welcome to the mindX system, a **production-ready Augmentic Intelligence platform** designed for autonomous operation, self-improvement, and strategic evolution with enterprise-grade security. This document provides an overview of its architecture, deployment options, and key ways to interact with it.

The core principle of mindX is to create an AI system that can not only perform tasks but also understand its own structure, identify areas for improvement, and even modify or extend its own codebase and capabilities over time—all while maintaining enterprise security standards with encrypted storage and advanced authentication systems.

##  Core Architecture Overview

mindX is built as a multi-agent system with a hierarchical control structure:

*   **Utility Layer:** Provides foundational services like configuration management (`utils.Config`), standardized logging (`utils.logging_config`), an LLM abstraction layer (`llm.llm_factory`, `llm.LLMHandlerInterface`), and a shared knowledge base (`core.belief_system.BeliefSystem`).
*   **Monitoring Layer:** Includes `ResourceMonitor` (for CPU, memory, disk) and `PerformanceMonitor` (for LLM calls), providing telemetry for strategic decision-making.
*   **Tactical Execution Layer (Code Modification):**
    *   `SelfImprovementAgent (SIA)` (`learning.self_improve_agent`): The "code surgeon" responsible for making specific code changes. It's invoked via a CLI by the Coordinator. It features analysis, implementation, evaluation (including self-tests and LLM critique), and rollback capabilities.
*   **Strategic Layer (Improvement Campaign Management):**
    *   (Conceptual) `StrategicEvolutionAgent (SEA)` (`learning.strategic_evolution_agent`): Designed to manage long-term, multi-step self-improvement campaigns based on high-level objectives, using its own internal BDIAgent.
*   **Orchestration Layer (System-Wide Coordination):**
    *   `CoordinatorAgent` (`orchestration.coordinator_agent`): The central hub. It manages user/agent interactions, maintains an improvement backlog, can autonomously initiate improvement tasks, and interfaces with the SIA. Includes Human-in-the-Loop (HITL) for critical changes.
    *   `MastermindAgent` (`orchestration.mastermind_agent`): The highest-level strategic agent. It oversees the entire system's evolution, manages the official tool registry, initiates broad strategic campaigns (which are then broken down by its internal BDIAgent), and can direct the development and lifecycle of tools and components. It uses `BaseGenAgent` for codebase analysis.
*   **Tools Layer (`tools` package):**
    *   Contains reusable tools like `NoteTakingTool`, `SummarizationTool`, `WebSearchTool`, and the `BaseGenAgent`. These tools are configured and can be used by BDIAgents. Mastermind manages the official registry of these tools.
*   **Identity Management (`core.id_manager_agent`):**
    *   Provides capabilities for creating and managing cryptographic identities, paving the way for secure inter-agent communication and potential blockchain integrations.

##  🚀 Setup and Prerequisites

### Production Deployment (Recommended)

For production use with enterprise security and automated deployment:

```bash
# One-command production deployment with security hardening
./deploy/production_deploy.sh

# Follow the prompts to configure:
# ✅ Security hardening (UFW firewall, fail2ban)
# ✅ nginx load balancer with SSL certificates
# ✅ PostgreSQL and Redis optimization
# ✅ AES-256 encrypted vault migration
# ✅ systemd services with health monitoring
# ✅ Automated backup and log rotation
```

**Production Features:**
- **Encrypted Vault**: AES-256 encryption for all sensitive data
- **Advanced Security**: Multi-algorithm rate limiting, authentication middleware
- **Performance Optimization**: Connection pooling, async/await architecture
- **Monitoring**: Real-time health checks and performance tracking
- **Deployment**: Automated VPS deployment with security hardening

**Production Documentation:**
- **[Production Deployment Guide](production_deployment.md)** - Complete deployment automation
- **[Security Configuration Guide](security_configuration.md)** - Enterprise security setup
- **[API Documentation](api_documentation.md)** - Complete API reference

### Development Setup

  **Python Environment:** Ensure you have Python 3.11+ installed (3.9+ minimum). It's highly recommended to use a virtual environment.
    ```bash
    python3 -m venv mindX_venv
    source mindX_venv/bin/activate # Or .\mindX_venv\Scripts\activate on Windows
    ```
  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    Key dependencies include:
    *   `python-dotenv` - Environment configuration
    *   `httpx` - HTTP client
    *   `psutil` - System monitoring
    *   `cryptography` - Encrypted vault security
    *   `fastapi` - Production API server
    *   `asyncpg` - PostgreSQL async driver
    *   `redis` - Caching and session management
    *   `eth-account` - Cryptographic identity management

  **Configuration:**

### 🔒 Production Configuration (Encrypted Vault)

For production deployment, sensitive data is automatically stored in the AES-256 encrypted vault:

```python
# Store API keys in encrypted vault
from mindx_backend_service.encrypted_vault_manager import get_encrypted_vault_manager
vault = get_encrypted_vault_manager()

# Store encrypted API keys
vault.store_api_key("openai", "your-openai-key")
vault.store_api_key("anthropic", "your-anthropic-key")
vault.store_api_key("gemini", "your-gemini-key")

# Verify stored keys
providers = vault.list_api_providers()
print(f"Stored providers: {providers}")
```

**Encrypted Vault Features:**
- **AES-256-GCM Encryption**: All sensitive data encrypted at rest
- **PBKDF2 Key Derivation**: 100,000 iterations for key security
- **Automatic Migration**: Migrate from plaintext `.env` files
- **Secure Access**: Process-level encryption key management

### 🛠️ Development Configuration

    *   **`.env` File:** For development, create a `.env` file in the project root. Add your API keys here:
        ```env
        # Production Environment
        MINDX_ENVIRONMENT="production"
        MINDX_SECURITY_ENCRYPTION_ENABLED="true"

        # API Keys (for development - use encrypted vault in production)
        OPENAI_API_KEY="your-openai-key"
        ANTHROPIC_API_KEY="your-anthropic-key"
        GEMINI_API_KEY="your-gemini-key"
        MISTRAL_API_KEY="your-mistral-key"

        # Security Configuration
        MINDX_SECURITY_CORS_ORIGINS="https://agenticplace.pythai.net"
        MINDX_SECURITY_RATE_LIMITING_ENABLED="true"
        ```
    *   **Configuration Files:**
        - **`data/config/basegen_config.json`:** Main system configuration
        - **`data/config/llm_factory_config.json`:** LLM provider settings
        - **`data/config/official_tools_registry.json`:** Tool registry managed by MastermindAgent

  **Directory Structure:** Ensure your project follows the expected Python package structure, with `__init__.py` files in each package directory (`utils/`, `core/`, `llm/`, `orchestration/`, `learning/`, `monitoring/`, `tools/`).

##  🚀 Running the System

### Production Deployment

For production deployment with enterprise features:

```bash
# Start production services
sudo systemctl start mindx
sudo systemctl start mindx-health.timer

# Check service status
sudo systemctl status mindx
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis

# Monitor logs
sudo journalctl -u mindx -f
```

**Production URLs:**
- **API Server**: `https://your-domain.com` (or `http://localhost:8000`)
- **Interactive API Docs**: `https://your-domain.com/docs`
- **Health Status**: `https://your-domain.com/health`

### Development Mode

The primary entry point for interactive development is `scripts/run_mindx.py`:

  **Activate your virtual environment:**
    ```bash
    source mindX_venv/bin/activate
    ```
  **Navigate to the project root directory:**
    ```bash
    cd /path/to/mindX
    ```
  **Run the development system:**
    ```bash
    python3 scripts/run_mindx.py
    ```
    You should see initialization logs and then the `mindX (Mastermind) >` prompt.

### Alternative Launch Methods

```bash
# Direct autonomous system launch
python3 augmentic.py

# Web interface with enhanced UI
./mindX.sh --frontend

# API server only
python3 mindx_backend_service/main_service_production.py
```

##  Command-Line Interface (CLI) Commands

Once the system is running, you can interact with it via the CLI. Type `help` at the prompt to see available commands.

**Key Commands:**

### 🎯 **Strategic Commands**

*   **`evolve <directive>`**
    *   Tasks the `MastermindAgent` with a high-level strategic goal or directive.
    *   Mastermind's internal BDIAgent will decompose the directive into subgoals, create plans, and execute actions.
    *   Production Examples:
        *   `evolve Optimize database connection pooling for better performance.`
        *   `evolve Enhance security monitoring with real-time threat detection.`
        *   `evolve Analyze the encrypted vault system for optimization opportunities.`
        *   `evolve Implement advanced rate limiting with client reputation tracking.`

### 🔒 **Production Commands**

*   **Encrypted Vault Management:**
    ```bash
    # Migrate to encrypted vault
    python3 scripts/migrate_to_encrypted_vault.py

    # Verify encryption status
    python3 scripts/migrate_to_encrypted_vault.py --verify-only
    ```

*   **Security Operations:**
    ```bash
    # Check security status
    curl https://your-domain.com/health/detailed

    # Monitor rate limiting
    curl https://your-domain.com/api/monitoring/inbound
    ```

*   **Service Management:**
    ```bash
    # Restart production services
    sudo systemctl restart mindx nginx

    # View service logs
    sudo journalctl -u mindx --since "1 hour ago"
    ```

*   **`mastermind_status`**
    *   Displays Mastermind's current high-level objectives and a history of its strategic campaigns (the outcomes of `evolve` commands).

*   **`show_tool_registry`**
    *   Displays the content of the `official_tools_registry.json` file, showing all tools Mastermind is aware of and managing.

*   **`analyze_codebase <path_to_code> [focus_prompt]`**
    *   A shortcut to make Mastermind use its `BaseGenAgent` capability to analyze a codebase.
    *   `<path_to_code>`: Can be an absolute path or relative to the project root.
    *   `[focus_prompt]` (Optional): A string guiding what the LLM should look for in the generated codebase summary.
    *   Example: `analyze_codebase ./learning "Identify opportunities for integrating new planning algorithms."`
    *   This internally triggers an `evolve` directive focused on this analysis.

**Coordinator-Level Commands (Prefixed with `coord_`)**

These commands interact directly with the `CoordinatorAgent` (routed via Mastermind).

*   **`coord_query <your question>`**: Sends a general question to the Coordinator's configured LLM.
*   **`coord_analyze [optional context]`**: Triggers the Coordinator's own system-wide analysis routine. This can populate the improvement backlog.
*   **`coord_improve <component_id> [optional context]`**: Requests the Coordinator to attempt an improvement on a specific component using the SelfImprovementAgent (SIA).
    *   `<component_id>`: Python module path (e.g., `utils.config`) or a registered agent ID that maps to a script.
    *   Example: `coord_improve utils.config Add detailed comments to the get method`
*   **`coord_backlog`**: Displays the Coordinator's current improvement backlog.
*   **`coord_process_backlog`**: Manually triggers the Coordinator to attempt processing one actionable item from its backlog.
*   **`coord_approve <backlog_item_id>`**: Approves a backlog item that is `PENDING_APPROVAL` (for HITL).
*   **`coord_reject <backlog_item_id>`**: Rejects a backlog item that is `PENDING_APPROVAL`.

**General Commands:**

*   **`help`**: Shows the list of available commands.
*   **`quit` / `exit`**: Shuts down the mindX system and exits the CLI.

##  Observing System Behavior (Logs)

*   **Console Output:** By default, logs at `INFO` level and above are printed to the console.
*   **File Logs:** If enabled in `data/config/basegen_config.json` (under `"logging": {"file": {"enabled": true}}`), detailed logs (including `DEBUG` level if set) will be written to files in the `data/logs/` directory (e.g., `mindx_debug.log`).
*   **Debug Logs:** To see more detailed logs (including generated LLM prompts, plans, etc.), set `"logging": {"level": "DEBUG"}` in `data/config/basegen_config.json`. This is highly recommended for development and understanding agent behavior.

##  Autonomous Self-Building Workflow (Conceptual)

The long-term vision for autonomous self-building involves a cycle orchestrated by `MastermindAgent`:

  **Goal Setting:** Mastermind (or a user via `evolve`) defines a high-level strategic goal (e.g., "Improve system's ability to analyze external codebases for tool extrapolation").
  **Observation & Analysis:**
    *   Mastermind's BDI uses `OBSERVE_MINDX_SYSTEM_STATE` (getting info from Coordinator) and potentially `ANALYZE_CODEBASE_FOR_STRATEGY` (using `BaseGenAgent`) to understand the current state.
    *   It uses `ASSESS_TOOL_SUITE_EFFECTIVENESS` to evaluate its current tools against the goal.
  **Conceptualization:** If a new tool or significant enhancement is needed, Mastermind's BDI uses `CONCEPTUALIZE_NEW_TOOL` (or a similar action for enhancements) to get its LLM to generate a detailed specification for the required tool/feature.
  **Identity Provisioning (if needed):** If the new tool requires its own cryptographic identity (e.g., for interacting with blockchains or secure external APIs), Mastermind's BDI uses `REQUEST_NEW_ENTITY_IDENTITY` via `IDManagerAgent`. The resulting identity details are stored as part of the tool's concept/specification.
  **Initiate Coding:** Mastermind's BDI uses `INITIATE_TOOL_CODING_CAMPAIGN` (or `INITIATE_NEW_COMPONENT_DEVELOPMENT_CAMPAIGN`). This action tasks the `CoordinatorAgent`.
  **Tactical Execution (Coordinator & SIA):**
    *   `CoordinatorAgent` receives the task. It prepares the context (the tool specification) and invokes the `SelfImprovementAgent` (SIA) CLI, targeting a new or existing tool file (e.g., in the `tools/` directory).
    *   `SIA` attempts to write or modify the Python code for the tool based on the specification, runs self-tests (if applicable), and gets LLM critique.
    *   SIA reports its success/failure and details (diffs, paths) back to the Coordinator in JSON format.
  **Review & Registry Update:**
    *   `CoordinatorAgent` relays SIA's results back to `MastermindAgent` (as the outcome of the BDI action).
    *   Mastermind's BDI then runs `REVIEW_CAMPAIGN_OUTCOMES`.
    *   If SIA was successful in creating/modifying the tool, Mastermind's BDI uses `REGISTER_OR_UPDATE_TOOL_IN_REGISTRY` to update the `official_tools_registry.json` with the new/updated tool's details (module path, class name, capabilities, status set to "experimental" or "active" after testing).
  **Deployment & Usage:** Once a tool is registered as "active," other BDIAgents in the system (including Mastermind's own BDI for subsequent tasks) can discover and start using it.
  **Monitoring & Iteration:** `PerformanceMonitor` tracks the new tool. Mastermind continues its observation cycle, potentially identifying further improvements for this new tool or other parts of the system, restarting the loop.

This cycle allows mindX to strategically expand and refine its own toolset and capabilities over time.

##  Current Development Focus

*   Refining LLM prompts for BDIAgent planning to ensure correct parameterization of actions.
*   Expanding the set of available tools in the `tools/` package.
*   Enhancing the `PerformanceMonitor` to provide richer feedback for tool assessment.
*   Developing more sophisticated BDI plans for `MastermindAgent` to fully utilize its tool lifecycle management actions.

This document provides a snapshot. The mindX system is designed to evolve!
