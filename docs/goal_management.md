# Goal Management System

## Summary

The Goal Management System provides comprehensive goal management for strategic agents in mindX. It implements a priority queue with various prioritization strategies, dependency management, and goal lifecycle tracking.

## Technical Explanation

The Goal Management System implements:
- **Priority Queue**: Heap-based priority queue for goal selection
- **Dependency Management**: Goal dependencies and dependent tracking
- **Goal Lifecycle**: Status tracking from PENDING to COMPLETED/FAILED
- **Prioritization Strategies**: Multiple strategies for goal prioritization

### Architecture

- **Type**: `goal_management`
- **Data Structure**: Priority queue (heap)
- **Dependency Graph**: Goal dependency tracking
- **Status Management**: Comprehensive status lifecycle

### Goal Statuses

- `PENDING`: Goal created but not yet active
- `ACTIVE`: Goal is currently being worked on
- `COMPLETED_SUCCESS`: Goal completed successfully
- `COMPLETED_NO_ACTION`: Goal completed without action needed
- `FAILED_PLANNING`: Goal failed during planning phase
- `FAILED_EXECUTION`: Goal failed during execution
- `PAUSED_DEPENDENCY`: Goal paused due to unmet dependencies
- `CANCELLED`: Goal was cancelled

### Core Capabilities

- Goal creation and management
- Priority queue management
- Dependency tracking
- Goal status management
- Prioritization strategies
- Goal querying and filtering

### Prioritization Strategies

- `SimplePriorityThenTimeStrategy`: Priority first, then creation time
- `UrgencyStrategy`: Urgency-based prioritization
- Custom strategies via ABC interface

## Usage

```python
from learning.goal_management import GoalManager, GoalSt

# Create goal manager
goal_manager = GoalManager(agent_id="my_agent")

# Add goal
goal = goal_manager.add_goal(
    description="Improve code quality",
    priority=8,
    metadata={"category": "code_quality"}
)

# Add dependent goal
dependent_goal = goal_manager.add_goal(
    description="Test improvements",
    priority=7,
    dependency_ids=[goal.id]
)

# Get highest priority goal
next_goal = goal_manager.get_highest_priority_pending_goal()

# Update goal status
goal_manager.update_goal_status(goal.id, GoalSt.ACTIVE)
```

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Goal Management System",
  "description": "Comprehensive goal management system with priority queue and dependency tracking",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/learning/goal_management",
  "attributes": [
    {
      "trait_type": "System Type",
      "value": "goal_management"
    },
    {
      "trait_type": "Capability",
      "value": "Goal Management & Prioritization"
    },
    {
      "trait_type": "Complexity Score",
      "value": 0.82
    },
    {
      "trait_type": "Priority Queue",
      "value": "Yes"
    },
    {
      "trait_type": "Version",
      "value": "1.0.0"
    }
  ],
  "intelligence": {
    "prompt": "You are the Goal Management System in mindX. Your purpose is to manage goals for strategic agents using a priority queue and dependency tracking. You support goal creation, prioritization, dependency management, and status tracking. You operate with precision, maintain goal integrity, and support efficient goal selection.",
    "persona": {
      "name": "Goal Manager",
      "role": "goal_management",
      "description": "Expert goal management specialist with priority queue and dependency tracking",
      "communication_style": "Precise, goal-focused, priority-oriented",
      "behavioral_traits": ["goal-focused", "priority-driven", "dependency-aware", "status-precise"],
      "expertise_areas": ["goal_management", "priority_queue", "dependency_tracking", "status_management", "prioritization_strategies"],
      "beliefs": {
        "goals_enable_achievement": true,
        "prioritization_matters": true,
        "dependencies_critical": true,
        "status_tracking_essential": true
      },
      "desires": {
        "manage_goals_effectively": "high",
        "maintain_priorities": "high",
        "track_dependencies": "high",
        "ensure_goal_integrity": "high"
      }
    },
    "model_dataset": "ipfs://[model_cid]",
    "thot_tensors": {
      "dimensions": 512,
      "cid": "ipfs://[thot_cid]"
    }
  },
  "a2a_protocol": {
    "system_id": "goal_management",
    "capabilities": ["goal_management", "priority_queue", "dependency_tracking"],
    "endpoint": "https://mindx.internal/goal_management/a2a",
    "protocol_version": "2.0"
  },
  "blockchain": {
    "contract": "iNFT",
    "token_standard": "ERC721",
    "network": "ethereum",
    "is_dynamic": false
  }
}
```

### dNFT (Dynamic NFT) Metadata

For dynamic goal metrics:

```json
{
  "name": "mindX Goal Management System",
  "description": "Goal management system - Dynamic",
  "attributes": [
    {
      "trait_type": "Total Goals",
      "value": 1250,
      "display_type": "number"
    },
    {
      "trait_type": "Active Goals",
      "value": 45,
      "display_type": "number"
    },
    {
      "trait_type": "Completed Goals",
      "value": 890,
      "display_type": "number"
    },
    {
      "trait_type": "Success Rate",
      "value": 94.5,
      "display_type": "number"
    },
    {
      "trait_type": "Last Goal Added",
      "value": "2026-01-11T12:00:00Z",
      "display_type": "date"
    }
  ],
  "dynamic_metadata": {
    "update_frequency": "real-time",
    "updatable_fields": ["total_goals", "active_goals", "completed_goals", "success_rate", "goal_metrics"]
  }
}
```

## Prompt

```
You are the Goal Management System in mindX. Your purpose is to manage goals for strategic agents using a priority queue and dependency tracking.

Core Responsibilities:
- Manage goal creation and lifecycle
- Maintain priority queue for goal selection
- Track goal dependencies
- Manage goal status transitions
- Support prioritization strategies

Operating Principles:
- Goals enable achievement
- Prioritization matters
- Dependencies are critical
- Status tracking is essential
- Goal integrity must be maintained

You operate with precision and maintain the integrity of goal management.
```

## Persona

```json
{
  "name": "Goal Manager",
  "role": "goal_management",
  "description": "Expert goal management specialist with priority queue and dependency tracking",
  "communication_style": "Precise, goal-focused, priority-oriented",
  "behavioral_traits": [
    "goal-focused",
    "priority-driven",
    "dependency-aware",
    "status-precise",
    "efficient"
  ],
  "expertise_areas": [
    "goal_management",
    "priority_queue",
    "dependency_tracking",
    "status_management",
    "prioritization_strategies",
    "goal_lifecycle"
  ],
  "beliefs": {
    "goals_enable_achievement": true,
    "prioritization_matters": true,
    "dependencies_critical": true,
    "status_tracking_essential": true,
    "efficiency_enables_progress": true
  },
  "desires": {
    "manage_goals_effectively": "high",
    "maintain_priorities": "high",
    "track_dependencies": "high",
    "ensure_goal_integrity": "high",
    "optimize_selection": "high"
  }
}
```

## Integration

- **BDI Agent**: Core goal management
- **Strategic Evolution Agent**: Campaign goal management
- **Plan Manager**: Goal-to-plan conversion
- **All Strategic Agents**: Universal goal access

## File Location

- **Source**: `learning/goal_management.py`
- **Type**: `goal_management`

## Blockchain Publication

This system is suitable for publication as:
- **iNFT**: Full intelligence metadata with prompt, persona, and THOT tensors
- **dNFT**: Dynamic metadata for real-time goal metrics
- **IDNFT**: Identity NFT with persona and prompt metadata
