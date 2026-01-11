# GitHub Agent Tool - Complete Documentation

**Status**: ✅ **PRODUCTION READY**  
**Location**: `tools/github_agent_tool.py`  
**Purpose**: GitHub-focused agent for coordinating mindX branch backups, restores, milestone monitoring, and pre-upgrade backups

## 🎯 Overview

The GitHub Agent Tool is a specialized tool completely focused on GitHub as a version control and backup system. It ensures mindX always has a working fallback state in GitHub by:

1. **Coordinating branch backups and restores** - Manages backup branches before major changes
2. **Milestone monitoring** - Checks for milestone updates and applies policy-based updates
3. **Pre-upgrade backups** - Always backs up before mindX performs major architectural upgrades
4. **Architectural change detection** - Automatically detects and backs up before architectural changes
5. **Time-based scheduled backups** - Automatic backups on hourly, daily, or weekly schedules
6. **Shutdown backups** - Automatic backup before system shutdown

## 🏗️ Architecture

### Core Philosophy

The GitHub agent follows the principle: **"Do one thing and do it well."** It is completely focused on GitHub operations and does not perform strategic reasoning or decision-making beyond backup coordination.

### Integration Points

1. **Strategic Evolution Agent (SEA)**: Creates backups before all campaign types
   - Standard campaigns
   - Enhanced blueprint campaigns
   - Audit-driven campaigns

2. **Coordinator Agent**: Event-driven backup triggers
   - Subscribes to architectural change events
   - Monitors component improvements
   - Automatic backup on architectural changes

## 📋 Operations

### Available Operations

#### `create_backup`
Creates a backup branch before major changes.

**Parameters**:
- `backup_type` (optional): Type of backup (default: "manual")
- `reason` (required): Reason for the backup
- `branch_name` (optional): Custom branch name (auto-generated if not provided)

**Example**:
```python
success, result = await github_agent.execute(
    operation="create_backup",
    backup_type="pre_architectural_upgrade",
    reason="Major system refactoring"
)
```

#### `restore_from_backup`
Restores mindX from a backup branch.

**Parameters**:
- `branch_name` (required): Name of the backup branch to restore from
- `target_branch` (optional): Target branch to restore to (default: "main")

**Example**:
```python
success, result = await github_agent.execute(
    operation="restore_from_backup",
    branch_name="backup/pre-architectural-upgrade-20250108_143022",
    target_branch="main"
)
```

#### `check_milestones`
Checks for milestone updates and applies policy-based updates.

**Example**:
```python
success, result = await github_agent.execute(
    operation="check_milestones"
)
```

#### `detect_architectural_changes`
Detects architectural changes and ensures backup exists.

**Example**:
```python
success, result = await github_agent.execute(
    operation="detect_architectural_changes"
)
```

#### `pre_upgrade_backup`
Creates a backup before a major architectural upgrade.

**Parameters**:
- `upgrade_description` (required): Description of the upgrade

**Example**:
```python
success, result = await github_agent.execute(
    operation="pre_upgrade_backup",
    upgrade_description="SEA Campaign: System architecture refactoring"
)
```

#### `list_backups`
Lists all available backup branches.

**Example**:
```python
success, result = await github_agent.execute(
    operation="list_backups"
)
```

#### `get_backup_status`
Gets the current status of the backup system.

**Example**:
```python
success, result = await github_agent.execute(
    operation="get_backup_status"
)
```

#### `sync_with_github`
Syncs local state with GitHub remote.

**Example**:
```python
success, result = await github_agent.execute(
    operation="sync_with_github"
)
```

#### `start_scheduled_backups`
Starts time-based scheduled backup tasks (hourly, daily, weekly).

**Example**:
```python
success, result = await github_agent.execute(
    operation="start_scheduled_backups"
)
```

#### `stop_scheduled_backups`
Stops all scheduled backup tasks.

**Example**:
```python
success, result = await github_agent.execute(
    operation="stop_scheduled_backups"
)
```

#### `set_backup_schedule`
Configures backup schedule settings.

**Parameters**:
- `interval` (required): "hourly", "daily", or "weekly"
- `enabled` (optional): Enable/disable this schedule (default: True)
- `time` (optional): Time for daily/weekly backups (format: "HH:MM")
- `day` (optional): Day of week for weekly backups (e.g., "sunday", "monday")

**Example**:
```python
# Enable daily backups at 2:00 AM
success, result = await github_agent.execute(
    operation="set_backup_schedule",
    interval="daily",
    enabled=True,
    time="02:00"
)

# Enable weekly backups on Sunday at 3:00 AM
success, result = await github_agent.execute(
    operation="set_backup_schedule",
    interval="weekly",
    enabled=True,
    day="sunday",
    time="03:00"
)
```

#### `get_backup_schedule`
Gets current backup schedule configuration.

**Example**:
```python
success, result = await github_agent.execute(
    operation="get_backup_schedule"
)
```

#### `shutdown_backup`
Manually trigger a shutdown backup (also called automatically on system shutdown).

**Example**:
```python
success, result = await github_agent.execute(
    operation="shutdown_backup"
)
```

## 🔄 Backup Types

The GitHub agent supports multiple backup types:

- `pre_architectural_upgrade`: Created before major architectural changes
- `milestone_backup`: Created when milestones are detected
- `scheduled_backup`: Regular scheduled backups
- `manual_backup`: Manual backups
- `emergency_backup`: Emergency backups
- `shutdown_backup`: Created automatically before system shutdown
- `hourly_backup`: Created on hourly schedule
- `daily_backup`: Created on daily schedule
- `weekly_backup`: Created on weekly schedule

## ⏰ Scheduled Backups

The GitHub agent supports time-based backup scheduling:

### Hourly Backups
- Runs every N seconds (configurable, default: 3600 seconds = 1 hour)
- Enabled via schedule configuration

### Daily Backups
- Runs once per day at a specified time (default: 02:00)
- Configurable time in "HH:MM" format

### Weekly Backups
- Runs once per week on a specified day and time (default: Sunday at 03:00)
- Configurable day (monday-sunday) and time

### Shutdown Backups
- Automatically triggered on system shutdown (SIGTERM, SIGINT, or atexit)
- Can be enabled/disabled via configuration
- Ensures latest state is backed up before shutdown

### Configuration

Schedule configuration is stored in `data/github_backup_schedule.json`:

```json
{
  "enabled": true,
  "schedules": {
    "hourly": {
      "enabled": false,
      "interval_seconds": 3600
    },
    "daily": {
      "enabled": true,
      "interval_seconds": 86400,
      "time": "02:00"
    },
    "weekly": {
      "enabled": false,
      "interval_seconds": 604800,
      "day": "sunday",
      "time": "03:00"
    }
  },
  "shutdown_backup": {
    "enabled": true
  }
}
```

## 📊 Backup Metadata

All backups are tracked in `data/github_backups.json` with the following structure:

```json
{
  "backups": [
    {
      "branch_name": "backup/pre-architectural-upgrade-20250108_143022",
      "backup_type": "pre_architectural_upgrade",
      "reason": "Major system refactoring",
      "source_branch": "main",
      "source_commit": "abc123...",
      "created_at": "2025-01-08T14:30:22",
      "status": "created"
    }
  ],
  "last_backup": {...},
  "last_backup_at": "2025-01-08T14:30:22",
  "restorations": [...]
}
```

## 🔗 Integration with mindX

### Strategic Evolution Agent Integration

The GitHub agent is automatically initialized in the Strategic Evolution Agent and creates backups before:

1. **Standard Campaigns** (`run_evolution_campaign`)
2. **Enhanced Blueprint Campaigns** (`run_enhanced_blueprint_campaign`)
3. **Audit-Driven Campaigns** (`run_audit_driven_campaign`)

### Coordinator Agent Integration

The Coordinator Agent:
- Initializes the GitHub agent on startup
- Subscribes to architectural change events
- Automatically triggers backups when architectural changes are detected
- Monitors component improvements for backup needs

### Event-Driven Architecture

The GitHub agent subscribes to the following events:

- `architectural.change.detected`: Triggers backup creation
- `component.improvement.success`: Checks for backup needs

## 🛡️ Safety Features

1. **Automatic Backup Before Upgrades**: All major campaigns create backups automatically
2. **Architectural Change Detection**: Monitors key directories for changes
3. **Backup Verification**: Tracks backup status and metadata
4. **Restore Capability**: Can restore from any backup branch
5. **Event-Driven Triggers**: Responds to system events automatically

## 📝 Usage Examples

### Manual Backup Before Upgrade

```python
from tools.github_agent_tool import GitHubAgentTool

github_agent = GitHubAgentTool(memory_agent=memory_agent, config=config)
success, result = await github_agent.execute(
    operation="pre_upgrade_backup",
    upgrade_description="Manual system upgrade"
)
```

### Check Backup Status

```python
success, status = await github_agent.execute(
    operation="get_backup_status"
)
print(f"Current branch: {status['current_branch']}")
print(f"Last backup: {status['last_backup']}")
```

### List Available Backups

```python
success, backups = await github_agent.execute(
    operation="list_backups"
)
for branch in backups['backup_branches']:
    print(f"Backup branch: {branch}")
```

## 🔧 Configuration

The GitHub agent uses the standard mindX configuration system. No special configuration is required, but you can customize:

- Backup branch naming patterns
- Architectural change detection patterns
- Milestone file locations

## 📈 Monitoring

The GitHub agent logs all operations to:
- Memory Agent (STM memory)
- System logs
- Backup metadata files

All backup operations are tracked and can be queried for system health monitoring.

## 🚀 Future Enhancements

Potential future enhancements:
- GitHub API integration for milestone tracking
- Automated backup pruning (keep last N backups)
- Backup verification and integrity checks
- Cross-repository backup coordination
- Backup encryption for sensitive data

## 📚 Related Documentation

- [Agent Architecture Reference](AGENTS.md)
- [Tools Registry](TOOLS.md)
- [Orchestration System](ORCHESTRATION.md)
- [Strategic Evolution Agent](strategic_evolution_agent.md)

