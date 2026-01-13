# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

mindX is an autonomous multi-agent orchestration system implementing a Belief-Desire-Intention (BDI) cognitive architecture. It's a "Godel-machine" - a self-improving AI system with Ethereum-compatible wallet authentication and LLM integration (Mistral, Gemini, Groq, Ollama, OpenAI, Anthropic, Together AI).

## Development Commands

### Setup
```bash
cp .env.sample .env  # Add API keys (MISTRAL_API_KEY, GEMINI_API_KEY, etc.)
pip install -r requirements.txt
```

### Running the Application
```bash
# Recommended: Full web interface (frontend + backend)
./mindX.sh --frontend

# Custom ports
./mindX.sh --frontend --frontend-port 3001 --backend-port 8001

# Interactive setup with API key configuration
./mindX.sh --frontend --interactive

# Direct backend only
uvicorn mindx_backend_service.main_service:app --reload --port 8000
```

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_mistral_chat_completion_api.py -v

# With coverage
python -m pytest tests/ --cov=mindx --cov-report=term-missing
```

### Code Quality
```bash
ruff format .      # Format code
ruff check . --fix # Lint
mypy mindx/        # Type checking
```

## Architecture

### Orchestration Hierarchy
```
CEO Agent (board-level strategic planning)
    ↓
MastermindAgent (singleton, strategic orchestration center)
    ↓
CoordinatorAgent (infrastructure management, autonomous improvement)
    ↓
Specialized Agents (BDI-based cognitive agents)
```

### Key Directories
- `orchestration/` - MastermindAgent, CoordinatorAgent, CEOAgent
- `core/` - BDI reasoning engine (`bdi_agent.py`), AGInt cognitive engine (`agint.py`), identity management (`id_manager_agent.py`)
- `agents/` - Specialized agents (guardian, memory, automindx, simple_coder, persona, avatar)
- `api/` - Multi-provider LLM API layer (`llm_routes.py`, provider-specific APIs)
- `learning/` - Self-improvement (`strategic_evolution_agent.py`, `self_improve_agent.py`)
- `llm/` - LLM factory pattern with provider-specific handlers
- `tools/` - 29+ tools extending `BaseTool` (see `docs/TOOLS_INDEX.md` for full list)
- `mindx_backend_service/` - FastAPI backend (`main_service.py` is ~95KB)
- `mindx_frontend_ui/` - Express.js frontend with xterm.js terminal and window manager
- `DAIO/contracts/` - Solidity smart contracts (Foundry-based)

### Core Patterns

**Singleton with async factory** (used by most agents):
```python
@classmethod
async def get_instance(cls, config_override=None, **kwargs):
    async with cls._lock:
        if cls._instance is None:
            cls._instance = cls(...)
        return cls._instance
```

**All operations are async** - the system uses `async/await` throughout.

**Tool pattern** - All tools extend `BaseTool` with `execute()` and `get_schema()` methods.

### LLM Integration
- Factory pattern in `llm/llm_factory.py`
- Provider handlers: `mistral_handler.py`, `gemini_handler.py`, `groq_handler.py`, `ollama_handler.py`
- Provider registry: `data/config/provider_registry.json` (Gemini, OpenAI, Anthropic, Mistral, Together, Ollama)
- Model configs in `models/*.yaml`
- Rate limiting via `rate_limiter.py`

### Identity System
- Ethereum-compatible wallet creation via `IDManagerAgent`
- MetaMask integration on frontend
- Agents have cryptographic identities (wallet addresses)

## API Endpoints

Backend runs on port 8000, frontend on 3000.

Key routes:
- `POST /agents/create`, `GET /agents/list` - Agent management
- `POST /llm/chat`, `POST /llm/completion` - LLM operations
- `POST /users/authenticate` - Wallet authentication
- `POST /directive/execute` - Execute directives
- `/mindterm/sessions/{id}/ws` - WebSocket terminal access
- `GET /health`, `GET /metrics` - System status

API docs at `http://localhost:8000/docs`

## Configuration

Priority: Environment variables (`MINDX_` prefix) > JSON configs (`data/config/`) > YAML model files (`models/`) > `.env` file

Key environment variables:
- `MISTRAL_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY` - LLM providers
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `TOGETHER_API_KEY` - Additional LLM providers
- `MINDX_LOGGING_LEVEL` - DEBUG/INFO/WARNING/ERROR
- `MINDX_COORDINATOR_AUTONOMOUS_IMPROVEMENT_ENABLED` - Enable autonomous loops

## Memory System

Located in `data/memory/`:
- `stm/` - Short-term memory (per-session)
- `ltm/` - Long-term knowledge base
- `workspaces/` - Agent working areas

Managed by `agents/memory_agent.py` with belief system integration.

## Interoperability Protocols

### A2A (Agent-to-Agent)
- `tools/a2a_tool.py` - Standardized agent-to-agent communication
- Agent discovery via agent cards (model cards)
- Cryptographic message signing and verification
- Protocol versions: 1.0, 2.0

### MCP (Model Context Protocol)
- `tools/mcp_tool.py` - Structured context provision for agent actions
- Context types: tool definitions, action context, environment state, capability descriptions
- Enables rich, structured context for better agent decision-making

## Cognitive Extensions

### PersonaAgent (`agents/persona_agent.py`)
- Enables agents to adopt different personas with distinct cognitive patterns
- Personas include: beliefs, desires, communication styles, behavioral traits
- Roles: expert, worker, meta, community, marketing, development, governance

### AvatarAgent (`agents/avatar_agent.py`)
- Generates visual avatars for agents/participants
- Integrates with PromptTool for avatar generation prompts
- Supports multiple providers: DALL-E, Stability AI, Replicate
- Styles: realistic, cartoon, anime, cyberpunk, etc.

### PromptTool (`tools/prompt_tool.py`)
- Manages prompts as first-class infrastructure
- Prompts are versioned, stored in memory, and executable
- Types: system, agent, user, template, inception, instruction
