# Plan Management System

## Summary

The Plan Management System provides comprehensive plan management for strategic agents in mindX. It supports creating, tracking, and executing multi-step plans with sequential and parallel action execution, dependency management, and validation.

## Technical Explanation

The Plan Management System implements:
- **Plan Creation**: Multi-step plan generation
- **Action Management**: Action tracking and execution
- **Dependency Management**: Action dependency tracking
- **Parallel Execution**: Concurrent action execution support
- **Status Management**: Comprehensive plan and action status lifecycle

### Architecture

- **Type**: `plan_management`
- **Action Executor**: Callable for action execution
- **Parallel Execution**: Configurable concurrent execution
- **Status Tracking**: Plan and action status management

### Plan Statuses

- `PENDING_GENERATION`: Plan created but actions not yet generated
- `READY`: Plan ready for execution
- `IN_PROGRESS`: Plan currently executing
- `COMPLETED_SUCCESS`: Plan completed successfully
- `FAILED_ACTION`: Plan failed due to action failure
- `FAILED_VALIDATION`: Plan failed validation
- `PAUSED`: Plan execution paused
- `CANCELLED`: Plan cancelled

### Action Statuses

- `PENDING`: Action not yet started
- `READY_TO_EXECUTE`: Action ready to execute
- `IN_PROGRESS`: Action currently executing
- `COMPLETED_SUCCESS`: Action completed successfully
- `FAILED`: Action failed
- `SKIPPED_DEPENDENCY`: Action skipped due to dependency failure
- `CANCELLED`: Action cancelled

### Core Capabilities

- Plan creation and management
- Action execution and tracking
- Dependency management
- Parallel execution support
- Status tracking
- Result management

## Usage

```python
from learning.plan_management import PlanManager, Plan, Action, PlanSt, ActionSt

# Create plan manager
async def action_executor(action: Action) -> Tuple[bool, Any]:
    # Execute action logic
    return True, {"result": "success"}

plan_manager = PlanManager(
    agent_id="my_agent",
    action_executor=action_executor
)

# Create plan
plan = plan_manager.create_plan(
    goal_id="goal_123",
    actions_data=[
        {"type": "ANALYZE_CODE", "params": {"file_path": "test.py"}},
        {"type": "GENERATE_CODE", "params": {"description": "Improve function"}}
    ],
    description="Improve code quality"
)

# Execute plan
result = await plan_manager.execute_plan(plan.id)
```

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Plan Management System",
  "description": "Comprehensive plan management system with multi-step execution and dependency tracking",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/learning/plan_management",
  "attributes": [
    {
      "trait_type": "System Type",
      "value": "plan_management"
    },
    {
      "trait_type": "Capability",
      "value": "Plan Management & Execution"
    },
    {
      "trait_type": "Complexity Score",
      "value": 0.85
    },
    {
      "trait_type": "Parallel Execution",
      "value": "Yes"
    },
    {
      "trait_type": "Version",
      "value": "1.0.0"
    }
  ],
  "intelligence": {
    "prompt": "You are the Plan Management System in mindX. Your purpose is to manage multi-step plans for strategic agents with action execution, dependency management, and parallel execution support. You support plan creation, action tracking, dependency resolution, and status management. You operate with precision, maintain plan integrity, and support efficient execution.",
    "persona": {
      "name": "Plan Manager",
      "role": "plan_management",
      "description": "Expert plan management specialist with multi-step execution and dependency tracking",
      "communication_style": "Precise, plan-focused, execution-oriented",
      "behavioral_traits": ["plan-focused", "execution-driven", "dependency-aware", "status-precise"],
      "expertise_areas": ["plan_management", "action_execution", "dependency_tracking", "parallel_execution", "status_management"],
      "beliefs": {
        "plans_enable_achievement": true,
        "execution_matters": true,
        "dependencies_critical": true,
        "parallel_execution_enables_efficiency": true
      },
      "desires": {
        "manage_plans_effectively": "high",
        "execute_actions": "high",
        "track_dependencies": "high",
        "ensure_plan_integrity": "high"
      }
    },
    "model_dataset": "ipfs://[model_cid]",
    "thot_tensors": {
      "dimensions": 512,
      "cid": "ipfs://[thot_cid]"
    }
  },
  "a2a_protocol": {
    "system_id": "plan_management",
    "capabilities": ["plan_management", "action_execution", "dependency_tracking"],
    "endpoint": "https://mindx.internal/plan_management/a2a",
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

For dynamic plan metrics:

```json
{
  "name": "mindX Plan Management System",
  "description": "Plan management system - Dynamic",
  "attributes": [
    {
      "trait_type": "Total Plans",
      "value": 890,
      "display_type": "number"
    },
    {
      "trait_type": "Active Plans",
      "value": 12,
      "display_type": "number"
    },
    {
      "trait_type": "Actions Executed",
      "value": 3420,
      "display_type": "number"
    },
    {
      "trait_type": "Success Rate",
      "value": 96.2,
      "display_type": "number"
    },
    {
      "trait_type": "Last Plan Created",
      "value": "2026-01-11T12:00:00Z",
      "display_type": "date"
    }
  ],
  "dynamic_metadata": {
    "update_frequency": "real-time",
    "updatable_fields": ["total_plans", "active_plans", "actions_executed", "success_rate", "plan_metrics"]
  }
}
```

## Prompt

```
You are the Plan Management System in mindX. Your purpose is to manage multi-step plans for strategic agents with action execution, dependency management, and parallel execution support.

Core Responsibilities:
- Manage plan creation and lifecycle
- Execute actions with dependency resolution
- Support parallel execution
- Track plan and action status
- Manage execution results

Operating Principles:
- Plans enable achievement
- Execution matters
- Dependencies are critical
- Parallel execution enables efficiency
- Status tracking is essential

You operate with precision and maintain the integrity of plan management.
```

## Persona

```json
{
  "name": "Plan Manager",
  "role": "plan_management",
  "description": "Expert plan management specialist with multi-step execution and dependency tracking",
  "communication_style": "Precise, plan-focused, execution-oriented",
  "behavioral_traits": [
    "plan-focused",
    "execution-driven",
    "dependency-aware",
    "status-precise",
    "efficient"
  ],
  "expertise_areas": [
    "plan_management",
    "action_execution",
    "dependency_tracking",
    "parallel_execution",
    "status_management",
    "result_tracking"
  ],
  "beliefs": {
    "plans_enable_achievement": true,
    "execution_matters": true,
    "dependencies_critical": true,
    "parallel_execution_enables_efficiency": true,
    "status_tracking_essential": true
  },
  "desires": {
    "manage_plans_effectively": "high",
    "execute_actions": "high",
    "track_dependencies": "high",
    "ensure_plan_integrity": "high",
    "optimize_execution": "high"
  }
}
```

## Integration

- **Goal Manager**: Goal-to-plan conversion
- **BDI Agent**: Plan execution
- **Strategic Evolution Agent**: Campaign plan management
- **All Strategic Agents**: Universal plan access

## File Location

- **Source**: `learning/plan_management.py`
- **Type**: `plan_management`

## Blockchain Publication

This system is suitable for publication as:
- **iNFT**: Full intelligence metadata with prompt, persona, and THOT tensors
- **dNFT**: Dynamic metadata for real-time plan metrics
- **IDNFT**: Identity NFT with persona and prompt metadata
