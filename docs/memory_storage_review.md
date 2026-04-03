# Memory Agent Storage and Data Folder Log Review

> **Update (April 2026)**: Storage architecture has evolved:
> - **Primary**: PostgreSQL 16 + pgvector 0.6.0 (indexed queries, vector search ready)
> - **Fallback**: File-based JSON in data/memory/stm/ and data/memory/ltm/
> - **Dual-write**: Every save_timestamped_memory() writes to both DB and file
> - **Schema**: memories, beliefs, agents, godel_choices, actions, model_perf tables
> - **Migration**: scripts/migrate_to_pgvector.py ingested 361 existing memories

## Executive Summary

The `memory_agent` serves as the central persistence layer for mindX, storing all agent interactions, system states, and operational data in a structured, timestamped format. The `data/` folder functions as a comprehensive log system where every operation is recorded as a series of timestamped JSON files, making it both a storage system and an audit trail.

## 1. Memory Agent Storage Architecture

### 1.1 Core Storage Paths

The `MemoryAgent` (`agents/memory_agent.py`) organizes storage under the `data/` folder with the following structure:

```
data/
├── memory/                    # Base memory directory
│   ├── stm/                   # Short-Term Memory (real-time interactions)
│   │   └── {agent_id}/        # Per-agent directories
│   │       └── {YYYYMMDD}/    # Daily subdirectories
│   │           └── {timestamp}.{memory_type}.memory.json
│   ├── ltm/                   # Long-Term Memory (learned patterns)
│   │   └── {agent_id}/        # Per-agent LTM storage
│   ├── context/               # Context management
│   ├── analytics/             # Memory analytics
│   └── agent_workspaces/      # Agent-specific persistent data
│       └── {agent_id}/
│           ├── process_trace.jsonl
│           └── process_traces/
└── logs/                      # System logs
    ├── mindx_runtime.log      # Rotating runtime log (10MB, 5 backups)
    ├── mindx_terminal.log     # Terminal output log
    └── process_traces/         # Structured process traces
```

### 1.2 Storage Methods

#### Timestamped Memory Storage (`save_timestamped_memory`)

**Location**: `data/memory/stm/{agent_id}/{YYYYMMDD}/`

**File Naming**: `{timestamp}.{memory_type}.memory.json`

**Example**: `2026-01-17T19-30-00.123456.interaction.memory.json`

**Structure**:
```json
{
  "timestamp": "2026-01-17T19:30:00.123456",
  "memory_type": "interaction|context|learning|system_state|performance|error|goal|belief|plan",
  "importance": 1|2|3|4,  // CRITICAL|HIGH|MEDIUM|LOW
  "agent_id": "mindx_agint",
  "content": {
    "input": "...",
    "response": "...",
    "interaction_timestamp": "...",
    "success": true
  },
  "context": {},
  "tags": ["tag1", "tag2"],
  "parent_memory_id": null,
  "memory_id": "fd936a7a9996ad32"  // 16-char hash
}
```

**Key Features**:
- **Daily Organization**: Files are organized by date (`YYYYMMDD`) for efficient querying
- **Unique Memory IDs**: Each memory gets a 16-character hash ID for referencing
- **Memory Types**: 9 distinct types (interaction, context, learning, system_state, performance, error, goal, belief, plan)
- **Importance Levels**: 4 levels (CRITICAL=1, HIGH=2, MEDIUM=3, LOW=4)
- **Parent-Child Relationships**: Memories can reference parent memories via `parent_memory_id`

#### Backward Compatibility Storage (`save_memory`)

**Location**: `data/memory/{memory_type}/{category}/`

**File Naming**: `{YYYYMMDDHHMMSS}_{microseconds}.{category}.mem.json`

**Example**: `20260117193000_123456.cycles.mem.json`

**Structure**:
```json
{
  "timestamp_utc": "2026-01-17T19:30:00.123456+00:00",
  "memory_type": "STM|LTM",
  "category": "cycles|file_operations|update_requests|errors",
  "metadata": {},
  "data": {}
}
```

#### Process Trace Logging (`log_process`)

**Location**: `data/memory/agent_workspaces/{agent_id}/process_trace.jsonl`

**Format**: JSONL (JSON Lines) - one JSON object per line

**Structure**:
```json
{
  "timestamp_utc": "2026-01-17T19:30:00.123456+00:00",
  "process_name": "agint_perception",
  "metadata": {
    "agent_id": "mindx_agint"
  },
  "process_data": {
    "timestamp": 1758093966.2996728,
    "llm_status": "Offline - Error: HEALTH_CHECK",
    "llm_operational": false
  },
  "memory_id": "fd936a7a9996ad32"
}
```

**Dual Storage**: Process logs are stored both as:
1. Timestamped memory records in STM
2. JSONL files in agent workspaces for compatibility

### 1.3 Agent Workspace Management

**Method**: `get_agent_data_directory(agent_id)`

**Location**: `data/memory/agent_workspaces/{agent_id}/`

**Purpose**: Provides each agent with a dedicated directory for:
- Persistent configuration files
- Generated artifacts
- Process traces
- Agent-specific data

**Example Structure**:
```
data/memory/agent_workspaces/automindx_agent_main/
├── personas.json
├── process_trace.jsonl
└── process_traces/
    └── 20260117_193000_agint_perception.trace.json
```

## 2. Data Folder as a Log System

### 2.1 Log-Like Characteristics

The `data/` folder functions as a comprehensive log system because:

1. **Timestamped Records**: Every memory file includes an ISO 8601 timestamp
2. **Append-Only Pattern**: New memories are appended as new files (immutable records)
3. **Chronological Organization**: Files are organized by date for time-based queries
4. **Structured Format**: All records are JSON, making them machine-readable
5. **Audit Trail**: Complete history of all agent operations

### 2.2 Log Categories

#### A. Short-Term Memory (STM) Logs

**Location**: `data/memory/stm/{agent_id}/{YYYYMMDD}/`

**Purpose**: Real-time interaction logs, system state changes, immediate events

**Volume**: Currently ~53MB for `mindx_agint` (13,175 files), ~8MB for `resource_monitor` (2,001 files)

**Retention**: Typically 7-30 days before promotion to LTM

**Query Pattern**: 
```python
# Get recent memories
memories = await memory_agent.get_recent_memories(
    agent_id="mindx_agint",
    memory_type=MemoryType.INTERACTION,
    limit=50,
    days_back=7
)
```

#### B. Long-Term Memory (LTM) Logs

**Location**: `data/memory/ltm/{agent_id}/`

**Purpose**: Promoted patterns, learned insights, behavioral analysis

**Promotion**: STM patterns are analyzed and significant ones promoted to LTM

**Structure**: Pattern promotion files with analysis results

#### C. Process Trace Logs

**Location**: 
- `data/memory/agent_workspaces/{agent_id}/process_trace.jsonl`
- `data/logs/process_traces/`

**Purpose**: Step-by-step "thought process" of agents

**Format**: JSONL (one JSON object per line)

**Use Case**: Self-analysis, debugging, audit trails

#### D. Runtime Logs

**Location**: `data/logs/mindx_runtime.log`

**Purpose**: Human-readable system status, errors, warnings

**Rotation**: 10MB max size, 5 backup files (`.1`, `.2`, `.3`, `.4`, `.5`)

**Format**: Standard Python logging format:
```
[2026-01-17 19:30:00] agents.memory_agent - INFO - memory_agent.save_timestamped_memory:170 - Timestamped memory saved: /path/to/file.json
```

#### E. Terminal Logs

**Location**: `data/logs/mindx_terminal.log`

**Purpose**: Raw terminal input/output for complete auditability

**Format**: 
```
[2026-01-17T19:30:00.123456] Terminal output line
```

### 2.3 Log Viewing Patterns

#### View Recent Memories (Last 7 Days)
```bash
# Find all memory files from last 7 days
find data/memory/stm/mindx_agint -type f -name "*.json" -mtime -7 | sort

# View a specific memory file
cat data/memory/stm/mindx_agint/20260117/2026-01-17T19-30-00.123456.interaction.memory.json | jq .
```

#### View Process Traces
```bash
# View recent process traces (JSONL format)
tail -100 data/memory/agent_workspaces/mindx_agint/process_trace.jsonl | jq .

# Count process traces
wc -l data/memory/agent_workspaces/*/process_trace.jsonl
```

#### View Runtime Logs
```bash
# View current log
tail -f data/logs/mindx_runtime.log

# View rotated logs
cat data/logs/mindx_runtime.log.1

# Search for errors
grep -i error data/logs/mindx_runtime.log | tail -20
```

#### Analyze Memory Patterns
```python
# Get memory analysis
analysis = await memory_agent.analyze_agent_patterns(
    agent_id="mindx_agint",
    days_back=7
)

# Generate human-readable summary
summary = await memory_agent.generate_human_readable_summary(
    agent_id="mindx_agint",
    days_back=1
)
```

## 3. Storage Statistics

### 3.1 Current Storage Distribution

Based on analysis of `/home/hacker/mindX/data/memory/stm/`:

| Agent ID | Size | File Count | Description |
|----------|------|------------|-------------|
| `mindx_agint` | 53MB | 13,175 | Main cognitive agent - highest activity |
| `resource_monitor` | 8.0MB | 2,001 | System resource monitoring |
| `id_manager_for_mastermind_prime` | 1.1MB | 244 | Identity management |
| `id_manager_for_coordinator_agent_main` | 988KB | 230 | Identity management |
| `default_identity_manager` | 828KB | 190 | Default identity operations |
| `automindx_agent_main` | 536KB | 117 | AutoMINDX agent operations |
| `guardian_agent_main` | 448KB | 95 | Guardian agent operations |
| `id_manager_for_mindx_agint` | 380KB | 90 | Identity management for agint |
| `coordinator_agent_main` | 212KB | 44 | Coordinator operations |
| `bdi_agent_mastermind_strategy_mastermind_prime` | 96KB | 21 | BDI strategy agent |

**Total STM Storage**: ~65MB across ~16,000+ files

### 3.2 File Size Characteristics

- **Average Memory File Size**: ~500-600 bytes per file
- **Largest Files**: System state and interaction memories (up to ~1KB)
- **Smallest Files**: Simple context updates (~400 bytes)

### 3.3 Growth Patterns

- **Daily Growth**: `mindx_agint` generates ~100-200 memory files per day
- **Peak Activity**: September 2025 (12,094 files in one day for `mindx_agint`)
- **Current Activity**: January 2026 shows steady daily activity

## 4. Memory Types and Usage

### 4.1 Memory Type Distribution

The system uses 9 distinct memory types:

1. **INTERACTION**: User-agent conversations, input-response pairs
2. **CONTEXT**: Contextual information, environment state
3. **LEARNING**: Learned patterns, insights, adaptations
4. **SYSTEM_STATE**: System state changes, configuration updates
5. **PERFORMANCE**: Performance metrics, timing data
6. **ERROR**: Error records, failure patterns
7. **GOAL**: Goal definitions, objectives
8. **BELIEF**: Belief updates, knowledge changes
9. **PLAN**: Planning records, strategy documents

### 4.2 Importance Levels

- **CRITICAL (1)**: System failures, security events, critical errors
- **HIGH (2)**: Important interactions, significant state changes
- **MEDIUM (3)**: Normal operations, standard interactions
- **LOW (4)**: Routine updates, minor context changes

## 5. Query and Analysis Capabilities

### 5.1 Memory Retrieval

```python
# Get recent memories with filtering
memories = await memory_agent.get_recent_memories(
    agent_id="mindx_agint",
    memory_type=MemoryType.INTERACTION,
    limit=50,
    days_back=7
)

# Get memory context for decision-making
context = await memory_agent.get_agent_memory_context(
    agent_id="mindx_agint",
    context_type="all",  # 'recent', 'patterns', 'ltm', 'all'
    limit=10
)
```

### 5.2 Pattern Analysis

```python
# Analyze agent patterns
analysis = await memory_agent.analyze_agent_patterns(
    agent_id="mindx_agint",
    days_back=7
)

# Returns:
# {
#   "total_memories": 150,
#   "memory_types": {"interaction": 100, "system_state": 50},
#   "activity_by_hour": {9: 20, 10: 30, ...},
#   "error_patterns": [...],
#   "success_patterns": [...],
#   "insights": [...]
# }
```

### 5.3 Self-Improvement Recommendations

```python
# Generate improvement recommendations
recommendations = await memory_agent.generate_self_improvement_recommendations(
    agent_id="mindx_agint"
)

# Returns:
# {
#   "immediate_improvements": [...],
#   "strategic_improvements": [...],
#   "behavioral_adjustments": [...],
#   "performance_optimizations": [...]
# }
```

### 5.4 STM to LTM Promotion

```python
# Promote significant patterns to LTM
result = await memory_agent.promote_stm_to_ltm(
    agent_id="mindx_agint",
    pattern_threshold=5,
    days_back=7
)
```

## 6. Log Rotation and Retention

### 6.1 Runtime Log Rotation

**Configuration** (`utils/logging_config.py`):
- **Max Size**: 10MB per file
- **Backup Count**: 5 files
- **Rotation**: Automatic when size limit reached
- **Files**: `mindx_runtime.log`, `mindx_runtime.log.1`, ..., `mindx_runtime.log.5`

### 6.2 Memory File Retention

- **STM**: Typically retained for 7-30 days before analysis
- **LTM**: Permanent storage of significant patterns
- **Process Traces**: Retained in agent workspaces indefinitely
- **Terminal Logs**: Append-only, no automatic rotation

### 6.3 Cleanup Strategies

Currently, there is no automatic cleanup of old STM files. Recommendations:

1. **Archive Old STM**: Move files older than 30 days to compressed archives
2. **LTM Promotion**: Automatically promote significant patterns to LTM
3. **Log Rotation**: Implement rotation for terminal logs
4. **Size Monitoring**: Alert when storage exceeds thresholds

## 7. Integration with Other Systems

### 7.1 Simple Coder Integration

Simple Coder stores update requests in `simple_coder_sandbox/update_requests.json`, which is separate from the memory system but follows similar patterns.

### 7.2 mindXagent Integration

mindXagent uses memory_agent for:
- Storing thinking processes
- Logging action choices
- Maintaining context for self-improvement
- Tracking autonomous mode operations

### 7.3 Startup Agent Integration

Startup agent logs to:
- `data/memory/stm/startup_agent/` - Startup events
- `data/logs/terminal_startup.log` - Terminal output during startup

## 8. Recommendations

### 8.1 Storage Optimization

1. **Compression**: Implement gzip compression for files older than 7 days
2. **Archiving**: Move old STM files to archive directories
3. **Indexing**: Create search indices for faster queries
4. **Deduplication**: Identify and merge duplicate memories

### 8.2 Log Viewing Tools

1. **Web Interface**: Create a UI for browsing memories and logs
2. **Search Interface**: Full-text search across all memory files
3. **Analytics Dashboard**: Visualize memory patterns and trends
4. **Export Tools**: Export memories in various formats (CSV, JSON, etc.)

### 8.3 Monitoring

1. **Storage Alerts**: Alert when storage exceeds thresholds
2. **Growth Tracking**: Monitor daily growth rates
3. **Performance Metrics**: Track query performance
4. **Health Checks**: Verify memory system integrity

### 8.4 Documentation

1. **Query Examples**: Document common query patterns
2. **Best Practices**: Guidelines for memory usage
3. **Troubleshooting**: Common issues and solutions
4. **API Reference**: Complete API documentation

## 9. Conclusion

The `memory_agent` provides a robust, timestamped, log-like storage system where every agent operation is recorded as a structured JSON file. The `data/` folder functions as both a storage system and a comprehensive audit trail, enabling:

- **Complete History**: Every interaction is preserved
- **Time-Based Queries**: Efficient retrieval by date ranges
- **Pattern Analysis**: Self-learning and improvement capabilities
- **Audit Compliance**: Full traceability of all operations
- **Debugging**: Detailed logs for troubleshooting

The system currently stores ~65MB of STM data across ~16,000 files, with the most active agent (`mindx_agint`) generating hundreds of memory records daily. The log-like structure makes it easy to view, analyze, and query the system's operational history.
