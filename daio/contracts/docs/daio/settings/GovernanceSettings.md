# GovernanceSettings

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/daio/settings/GovernanceSettings.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.20 |
| **Category** | Governance Layer - Configuration |
| **Inherits** | Ownable |

## Summary

GovernanceSettings manages configurable governance parameters for the DAIO ecosystem. It supports both global settings and project-specific overrides, enabling multi-project governance with customized voting rules.

## Purpose

- Store and manage voting period, quorum, and approval thresholds
- Support project-specific governance settings
- Enable configuration updates via governance proposals
- Provide centralized settings access for governance contracts

## Technical Specification

### Data Structures

```solidity
struct Settings {
    uint256 votingPeriod;        // Blocks for voting period
    uint256 quorumThreshold;     // Basis points (e.g., 5000 = 50%)
    uint256 approvalThreshold;   // Basis points (e.g., 5000 = 50%)
    uint256 timelockDelay;       // Blocks for timelock delay
    uint256 proposalThreshold;   // Minimum voting power to create proposal
    uint256 minVotingPower;      // Minimum voting power to vote
}
```

### State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `settings` | `Settings` | Global default settings |
| `projectSettings` | `mapping(string => Settings)` | Project-specific overrides |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `updateSettings` | All settings params | Owner | Update global settings |
| `updateProjectSettings` | `projectId`, all settings params | Owner | Update project-specific settings |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `settings` | - | `Settings` | Get global settings |
| `projectSettings` | `projectId` | `Settings` | Get project settings |
| `getSettings` | `projectId` | `Settings` | Get settings (project or global fallback) |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `SettingsUpdated` | `projectId`, `votingPeriod`, `quorumThreshold`, `approvalThreshold`, `timelockDelay` | Settings changed |

## Settings Parameters

| Parameter | Description | Typical Values |
|-----------|-------------|----------------|
| `votingPeriod` | Duration of voting in blocks | 45818 (~1 week at 13s/block) |
| `quorumThreshold` | Minimum participation required | 2000-5000 (20-50%) |
| `approvalThreshold` | Votes needed to pass | 5000-6667 (50-66.67%) |
| `timelockDelay` | Delay before execution | 6545 (~1 day) |
| `proposalThreshold` | Min power to create proposal | 1000-10000 |
| `minVotingPower` | Min power to vote | 100-1000 |

## Usage Examples

### Deploying with Initial Settings

```javascript
const votingPeriod = 45818;        // ~1 week
const quorumThreshold = 4000;      // 40%
const approvalThreshold = 6667;    // 66.67% (2/3)
const timelockDelay = 6545;        // ~1 day
const proposalThreshold = 5000;    // Min voting power to propose
const minVotingPower = 100;        // Min voting power to vote

const governanceSettings = await GovernanceSettings.deploy(
    votingPeriod,
    quorumThreshold,
    approvalThreshold,
    timelockDelay,
    proposalThreshold,
    minVotingPower
);
```

### Updating Global Settings

```javascript
// Update all global settings
await governanceSettings.updateSettings(
    60000,      // Longer voting period
    5000,       // 50% quorum
    5000,       // 50% approval
    13090,      // 2-day timelock
    10000,      // Higher proposal threshold
    500         // Higher min voting power
);
```

### Creating Project-Specific Settings

```javascript
// mindX project gets different settings
await governanceSettings.updateProjectSettings(
    "mindX",    // Project ID
    30000,      // Shorter voting period
    3000,       // Lower quorum
    6667,       // 66.67% approval (2/3)
    6545,       // 1-day timelock
    2000,       // Lower proposal threshold
    100         // Standard min voting power
);

// FinancialMind project gets higher thresholds
await governanceSettings.updateProjectSettings(
    "FinancialMind",
    45818,      // Standard voting period
    6000,       // Higher quorum (60%)
    7500,       // 75% approval required
    19635,      // 3-day timelock
    20000,      // High proposal threshold
    1000        // Higher min voting power
);
```

### Getting Settings for a Project

```javascript
// Get settings (returns project-specific if exists, otherwise global)
const settings = await governanceSettings.getSettings("mindX");

console.log(`Voting Period: ${settings.votingPeriod} blocks`);
console.log(`Quorum: ${settings.quorumThreshold / 100}%`);
console.log(`Approval: ${settings.approvalThreshold / 100}%`);
```

## UI Design Considerations

### Settings Dashboard
- Form: Global settings with validation
- Tabs: Switch between global and project-specific
- Preview: Calculate actual durations (blocks → time)
- Comparison: Side-by-side project settings

### Settings Editor
- Inputs: All settings parameters
- Validation: Range checks (0-10000 for percentages)
- Conversion: Block count to human-readable time
- Save: Confirmation before updating

### Project Settings Manager
- List: All projects with custom settings
- Create: New project settings form
- Edit: Modify existing settings
- Delete: Reset to global defaults

### Settings Preview
- Calculate: Voting end date from current block
- Display: Timelock expiry time
- Show: Required votes for quorum/approval
- Visualize: Settings comparison chart

## Integration Points

### For DAIOGovernance

```javascript
// Get settings when creating proposal
const settings = await governanceSettings.getSettings(projectId);
const endBlock = currentBlock + settings.votingPeriod;
const timelockExpiry = endBlock + settings.timelockDelay;
```

### For KnowledgeHierarchyDAIO

```javascript
// Check if user meets voting power requirement
const settings = await governanceSettings.getSettings(projectId);
if (voterPower < settings.minVotingPower) {
    revert("Insufficient voting power");
}

// Check if user can create proposal
if (proposerPower < settings.proposalThreshold) {
    revert("Insufficient power to create proposal");
}
```

### For External Systems (e.g., mindX via xmind/)

```javascript
// Get governance parameters for UI
async function getGovernanceConfig(projectId) {
    const settings = await governanceSettings.getSettings(projectId);
    const blockTime = 13; // seconds

    return {
        votingPeriodBlocks: settings.votingPeriod,
        votingPeriodDays: (settings.votingPeriod * blockTime) / 86400,
        quorumPercent: settings.quorumThreshold / 100,
        approvalPercent: settings.approvalThreshold / 100,
        timelockDays: (settings.timelockDelay * blockTime) / 86400,
        proposalThreshold: settings.proposalThreshold,
        minVotingPower: settings.minVotingPower
    };
}
```

## Dependencies

- OpenZeppelin Ownable

## Security Considerations

- Only owner can update settings (should be governance/timelock)
- Percentage thresholds capped at 10000 (100%)
- Voting period must be > 0
- No direct validation of logical consistency (e.g., quorum < approval)

## Gas Estimates

| Function | Estimated Gas |
|----------|---------------|
| `constructor` | ~150,000 |
| `updateSettings` | ~80,000 |
| `updateProjectSettings` | ~100,000 |
| `getSettings` | View (free) |
| `settings` | View (free) |
| `projectSettings` | View (free) |

## Multi-Project Support

GovernanceSettings enables DAIO to govern multiple projects with different rules:

```
Global Settings (Default)
├── Project: mindX (Custom: faster voting)
├── Project: FinancialMind (Custom: higher thresholds)
├── Project: cryptoAGI (Uses global defaults)
└── Project: [new project] (Initially uses global)
```

The `getSettings` function automatically falls back to global settings if a project doesn't have custom configuration.
