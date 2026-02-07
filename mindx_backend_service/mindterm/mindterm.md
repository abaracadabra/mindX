# MindTerm

Technical overview of the MindTerm PTY service: in-process shell sessions, command blocks, risk policy, and integration with the mindX backend (ModelRegistry, RAGE, Vault).

---

## Technical explanation

### Architecture

MindTerm provides **browser-based terminal sessions** over WebSockets. Each session is a **real PTY** (`pty.fork()`): a child process runs the user’s shell (e.g. `bash -i`), and the backend reads/writes the PTY master. The frontend uses **xterm.js** (see `knowledge_base.json`) to render the terminal and send input.

**Local xterm.js assets**: The backend serves local copies of xterm.js from `mindx_backend_service/mindterm/static/xterm/` so UIs can load them without a CDN. When the backend is running, use:

- `GET /mindterm/static/xterm/xterm.js` (xterm 5.3.0)
- `GET /mindterm/static/xterm/xterm.css`
- `GET /mindterm/static/xterm/xterm-addon-fit.js` (FitAddon 0.8.0)

Files are downloaded from jsDelivr (see `mindterm/static/xterm/README.txt`). To refresh, re-download from the URLs listed there.

- **Session lifecycle**: `POST /mindterm/sessions` creates a session (UUID, PTY, resize). `DELETE /mindterm/sessions/{id}` closes the PTY and cleans up.
- **Primary WebSocket** `GET /mindterm/sessions/{session_id}/ws`: client sends `type:"in"` (raw keystrokes) or `type:"line"` (full line); server sends `type:"out"` (PTY output). Lines are optionally gated by a **risk policy** (see below).
- **Events WebSocket** `GET /mindterm/sessions/{session_id}/events`: read-only stream of structured events (CommandStarted, OutputChunk, CommandFinished, RiskFlagged, UserConfirmed, Sys, Resize) for agents or observers.

### Command blocks and sentinel

To associate output with a specific command and capture exit code, each submitted **line** is turned into a **command block**:

1. A unique `block_id` is generated and a `CommandBlock` is stored (in-memory cache + JSONL under `data/mindterm_blocks/`).
2. The line is **wrapped** so the shell runs it and then prints a sentinel:  
   `{line}; __ec=$?; printf "\n__MINDTERM__END__:{block_id}:%d\n" "$__ec" `
3. The PTY reader parses output for `__MINDTERM__END__:{block_id}:{exit_code}`. When found, the block is updated with `finished_at` and `exit_code`, and a `CommandFinished` event is emitted.

So: **list of models** and **choice of model** are not inside MindTerm; they are handled by the rest of mindX (e.g. **ModelRegistry** for LLM selection). MindTerm only provides the terminal and command-block stream.

### Risk policy

Before executing a line, the backend calls `assess_command(line)` (`policy.py`). If the command matches **high-** or **medium-risk** patterns (e.g. `rm -rf`, `sudo`, `curl ... | sh`), the server sends `type:"risk"` with level and reason and does **not** run the command until the client sends `type:"confirm"` with `allow: true/false`. Low-risk commands run immediately.

### Transcripts and blocks storage

- **Transcripts**: append-only logs per session in `data/mindterm_transcripts/{session_id}.log` (direction: `in` | `out` | `sys`).
- **Blocks**: per-session JSONL in `data/mindterm_blocks/{session_id}.jsonl` (block records and patch records). The service keeps the last 500 blocks per session in memory for fast `GET /mindterm/sessions/{id}/blocks`.

### Integration with mindX backend

- **Coordinator**: if `CoordinatorAgent` is set on the service (via `set_coordinator_and_monitors` at startup), MindTerm publishes events such as `mindterm.session_created`, `mindterm.command_started`, `mindterm.session_closed` so orchestration can react.
- **Performance monitor**: command completions can be recorded for monitoring (success/failure, exit code).
- **Resource monitor**: `get_resource_usage()` can expose mindterm-specific metrics (active sessions, total commands, output bytes) alongside system metrics when the backend’s resource monitor is available.

The mindX backend uses **ModelRegistry** for LLM/model selection elsewhere (e.g. agents, chat). MindTerm does not call ModelRegistry directly; it remains the single place for model selection in the stack.

**RAGE** (`mindx_backend_service/rage`): retrieval-augmented pipeline (ingestion, indexing with embeddings, retrieval). MindTerm does not call RAGE today. Transcripts or command-block output could later be ingested into RAGE for semantic search or context for agents.

**Vault** (`mindx_backend_service/vault_manager` and `/vault/*` routes): secure storage for credentials and access logs. MindTerm does not store credentials; any future use (e.g. SSH keys or API keys for terminal-related tools) would go through the same Vault API as the rest of the backend.

---

## Usage summary

| Action | HTTP/WS | Description |
|--------|--------|-------------|
| Create session | `POST /mindterm/sessions` | Body: optional `shell`, `cwd`, `cols`, `rows`. Returns `session_id`, `shell`, `cwd`, `created_at`. |
| Resize | `POST /mindterm/sessions/{id}/resize` | Body: `cols`, `rows`. |
| Get blocks | `GET /mindterm/sessions/{id}/blocks?limit=50` | Returns recent command blocks (command, exit_code, timestamps, etc.). |
| Delete session | `DELETE /mindterm/sessions/{id}` | Closes PTY and cleans up. |
| Primary WS | `WS /mindterm/sessions/{id}/ws` | Send `{"type":"in","data":"..."}` or `{"type":"line","data":"..."}`; receive `{"type":"out","data":"..."}` or `{"type":"risk",...}`; confirm with `{"type":"confirm","allow":true\|false}`. |
| Events WS | `WS /mindterm/sessions/{id}/events` | Read-only stream of events (CommandStarted, OutputChunk, CommandFinished, RiskFlagged, UserConfirmed, Sys, Resize). |
| Metrics | `GET /mindterm/metrics` | Service and resource usage. `GET /mindterm/metrics/{session_id}` for one session. |
| Knowledge | `GET /mindterm/knowledge` | Full knowledge base. `GET /mindterm/knowledge/repositories/{name}` and `.../integrations/{name}` for specific entries. |
| xterm.js (local) | `GET /mindterm/static/xterm/xterm.js`, `xterm.css`, `xterm-addon-fit.js` | Local copies of xterm 5.3.0 and FitAddon 0.8.0; no CDN required. |

Typical flow: create session → connect to `/ws` → send `line` messages for commands; handle `risk` and `confirm` when required; display `out`; optionally subscribe to `/events` for structured logging or agents.

---

## Limitations

- **Single process**: PTYs and session state are in one backend process. No built-in persistence of live sessions across restarts; reconnecting after restart requires creating a new session.
- **Block store**: Only the last N blocks per session are kept in memory; full history is on disk (JSONL). Very long sessions with many blocks may have slower tail scans if the cache is cold.
- **Risk policy**: Pattern-based only (regex). No semantic or context-aware checks; false positives/negatives are possible. Confirmation is a single allow/deny; no per-rule or expiry.
- **Encoding**: UTF-8 with replace errors. Binary or non-UTF-8 output may be altered.
- **Concurrency**: One reader per PTY; output order is preserved. No built-in rate limiting or backpressure on the WebSocket sender beyond the queue.
- **RAGE / Vault**: Not integrated today. Transcripts and blocks are not auto-ingested into RAGE; no credential access from MindTerm via Vault. Model selection continues to use ModelRegistry elsewhere in the stack.

---

## Related backend services

- **ModelRegistry** (`llm/model_registry.py`): used by the mindX backend for LLM/model selection; MindTerm does not use it directly.
- **RAGE** (`mindx_backend_service/rage`): ingestion, indexing, retrieval. Future use: index transcripts or block output for semantic search.
- **Vault** (`mindx_backend_service/vault_manager`, `/vault/*`): credential and access logging. Future use: store or resolve credentials for terminal-related integrations.
