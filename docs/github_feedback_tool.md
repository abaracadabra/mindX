# GitHub Feedback Tool

## Summary

The GitHub Feedback Tool enables **zero-cost AI debugging** by collecting code review feedback from AI bots on GitHub (primarily Gemini Code Assist) and processing it for mindX to automatically fix.

## Zero-Cost AI Debugging Loop

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Push Code to   │───▶│  Gemini Bot      │───▶│  Collect        │
│  GitHub PR      │    │  Reviews (Free)  │    │  Feedback       │
└─────────────────┘    └──────────────────┘    └────────┬────────┘
                                                        │
┌─────────────────┐    ┌──────────────────┐    ┌────────▼────────┐
│  Commit Fixes   │◀───│  mindX Applies   │◀───│  Process        │
│  to GitHub      │    │  Fixes           │    │  Errors         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Supported AI Bots

- **Gemini Code Assist** (`gemini-code-assist[bot]`) - Primary target
- **GitHub Copilot** (`github-copilot[bot]`)
- **CodeRabbit** (`coderabbitai[bot]`)
- **Codacy** (`codacy-production[bot]`)
- **SonarCloud** (`sonarcloud[bot]`)

## Quick Start

```python
from tools.github_feedback_tool import GitHubFeedbackTool
from agents.memory_agent import MemoryAgent

memory_agent = MemoryAgent()
feedback_tool = GitHubFeedbackTool(memory_agent=memory_agent)

# Collect all AI feedback from GitHub
result = await feedback_tool.execute(
    operation="collect_feedback",
    repo="owner/repo"  # Optional, defaults to current repo
)

# List pending errors
result = await feedback_tool.execute(
    operation="list_errors",
    status="pending"
)

# Process errors for mindX to fix
result = await feedback_tool.execute(
    operation="process_errors",
    auto_fix=True,
    limit=10
)

# Get statistics
result = await feedback_tool.execute(operation="get_stats")
```

## Operations

### Feedback Collection

| Operation | Description |
|-----------|-------------|
| `collect_feedback` | Collect AI feedback from GitHub PRs and issues |
| `fetch_pr_comments` | Fetch comments from a specific PR |
| `fetch_repo_issues` | Fetch issues from the repository |

### Error Management

| Operation | Description |
|-----------|-------------|
| `list_errors` | List all collected errors with optional filters |
| `process_errors` | Process pending errors and generate fix context |
| `apply_fix` | Apply a fix for a specific error |
| `mark_fixed` | Mark an error as fixed |
| `mark_ignored` | Mark an error as ignored |

### Statistics & Export

| Operation | Description |
|-----------|-------------|
| `get_stats` | Get comprehensive feedback statistics |
| `export_errors` | Export errors for external processing |
| `clear_processed` | Clear processed feedback tracking |

## Error Categories

The tool automatically categorizes errors:

- **syntax**: Syntax errors
- **type**: Type annotation/conversion issues
- **logic**: Logic bugs
- **security**: Security vulnerabilities
- **performance**: Performance issues
- **style**: Code style/formatting
- **deprecated**: Deprecated usage
- **import**: Missing imports/modules
- **undefined**: Undefined variables/functions
- **other**: Uncategorized

## Error Severity Levels

- **critical**: Must fix immediately
- **high**: Should fix soon
- **medium**: Should fix eventually
- **low**: Nice to fix
- **info**: Informational

## File Structure

```
data/github_feedback/
├── errors.json       # All collected errors
├── processed.json    # Processed comment IDs
├── fixes.json        # Applied fixes history
└── export_*.json     # Exported error reports
```

## Integration with mindX

### Coordinator Agent Integration

```python
# In coordinator_agent.py
from tools.github_feedback_tool import GitHubFeedbackTool

class CoordinatorAgent:
    async def async_init(self):
        # ... existing init ...
        self.feedback_tool = GitHubFeedbackTool(memory_agent=self.memory_agent)

    async def run_feedback_loop(self):
        """Zero-cost AI debugging loop."""
        # Collect feedback
        result = await self.feedback_tool.execute(operation="collect_feedback")

        # Process errors
        errors = await self.feedback_tool.execute(
            operation="process_errors",
            limit=5
        )

        # For each error, use simple_coder or other agents to fix
        for error in errors.get("errors_to_fix", []):
            await self._fix_error(error)
```

### Memory Integration

All feedback is logged to MemoryAgent:
- `feedback_collected`: When feedback is gathered
- `error_ready_for_fix`: When an error is processed for fixing
- Fix application and status changes

## CLI Usage (via GitHub CLI)

The tool requires the GitHub CLI (`gh`) to be installed and authenticated:

```bash
# Install GitHub CLI
# macOS: brew install gh
# Linux: see https://cli.github.com/

# Authenticate
gh auth login
```

## Example Workflow

```python
# 1. Collect feedback after a PR is reviewed
result = await feedback_tool.execute(
    operation="collect_feedback",
    pr_number=42
)
print(f"Found {result['new_errors']} new errors")

# 2. List high-severity errors
errors = await feedback_tool.execute(
    operation="list_errors",
    severity="high"
)

# 3. Process for fixing
processed = await feedback_tool.execute(
    operation="process_errors",
    category_filter="import",  # Only import errors
    limit=5
)

# 4. Each error in processed["errors_to_fix"] contains:
# - error_id: Unique identifier
# - file_path: File to fix
# - line_number: Line number
# - message: Error description
# - suggestion: AI's suggestion
# - action_required: What to do
# - auto_fixable: Whether safe to auto-fix

# 5. After fixing, mark as complete
await feedback_tool.execute(
    operation="mark_fixed",
    error_id="gh_12345"
)
```

## Configuration

Bot identifiers can be customized:

```python
feedback_tool.bot_identifiers = [
    "gemini-code-assist[bot]",
    "my-custom-bot[bot]"
]
```

## Benefits

1. **Zero Cost**: Uses free AI review bots on GitHub
2. **Automated**: Continuously collects and processes feedback
3. **Categorized**: Errors are automatically categorized and prioritized
4. **Integrated**: Works with mindX memory and agent systems
5. **Trackable**: Full history of errors and fixes
