# DAIO_Constitution

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/daio/constitution/DAIO_Constitution.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.20 |
| **Category** | Governance Layer - Core |
| **Inherits** | Ownable, Pausable |

## Summary

DAIO_Constitution enforces immutable constitutional rules that govern the DAIO ecosystem. It implements the 15% diversification mandate, 15% treasury tithe, and Chairman's Veto power. All treasury allocations must be validated against constitutional constraints.

## Purpose

- Enforce 15% diversification mandate (max single allocation)
- Collect 15% tithe on all treasury deposits
- Provide Chairman's Veto for emergency situations
- Validate all governance actions against constitutional rules
- Track allocation percentages across recipients
- Enable system pause for emergencies

## Technical Specification

### Constitutional Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `DIVERSIFICATION_MANDATE` | 1500 (15%) | Max allocation to single recipient |
| `TREASURY_TITHE` | 1500 (15%) | Tithe percentage on deposits |
| `MAX_SINGLE_ALLOCATION` | 8500 (85%) | Max single allocation limit |

### State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `chairman` | `address` | Chairman with veto power |
| `governance` | `address` | DAIOGovernance contract |
| `treasury` | `address` | Treasury contract |
| `allocationPercentages` | `mapping(address => uint256)` | Allocation tracking per recipient |
| `totalAllocated` | `uint256` | Total allocated amount |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `setGovernance` | `_governance` | Owner | Set governance contract |
| `setTreasury` | `_treasury` | Owner | Set treasury contract |
| `updateChairman` | `_newChairman` | Governance | Update chairman |
| `validateAction` | `target`, `action`, `amount` | Governance | Validate action against constitution |
| `recordAllocation` | `recipient`, `amount` | Governance | Record allocation for tracking |
| `removeAllocation` | `recipient`, `amount` | Governance | Remove allocation (refunds) |
| `pauseSystem` | - | Chairman | Emergency pause |
| `unpauseSystem` | - | Chairman/Governance | Unpause system |
| `vetoAction` | `target`, `action` | Chairman | Veto specific action |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `checkDiversificationLimit` | `recipient`, `amount` | `bool` | Check allocation limit |
| `checkDiversificationLimitWithEvent` | `recipient`, `amount` | `bool` | Check with event emission |
| `getAllocationPercentage` | `recipient` | `uint256` | Get allocation % (basis points) |
| `DIVERSIFICATION_MANDATE` | - | `uint256` | Get mandate constant |
| `TREASURY_TITHE` | - | `uint256` | Get tithe constant |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `ActionValidated` | `target`, `action`, `valid` | Action validation completed |
| `DiversificationChecked` | `currentAllocation`, `maxAllowed` | Diversification check |
| `ChairmanVeto` | `target`, `action` | Chairman vetoes action |
| `GovernanceUpdated` | `oldGovernance`, `newGovernance` | Governance contract updated |
| `ChairmanUpdated` | `oldChairman`, `newChairman` | Chairman updated |

## Constitutional Rules

### 1. Diversification Mandate (15%)
No single recipient can receive more than 15% of total treasury allocations:

```
newAllocation <= (totalAllocated * DIVERSIFICATION_MANDATE) / 10000
```

### 2. Treasury Tithe (15%)
All deposits automatically contribute 15% to the central treasury:

```
tithe = (depositAmount * TREASURY_TITHE) / 10000
netDeposit = depositAmount - tithe
```

### 3. Chairman's Veto
Chairman can:
- Pause the entire system (`pauseSystem`)
- Veto specific actions (`vetoAction`)
- Emergency intervention capability

## Usage Examples

### Validating an Action

```javascript
const target = recipientAddress;
const action = ethers.utils.defaultAbiCoder.encode(
    ["string", "uint256"],
    ["treasury_allocation", allocationAmount]
);
const amount = ethers.utils.parseEther("1000");

const isValid = await constitution.validateAction(target, action, amount);
if (!isValid) {
    console.log("Action violates constitutional constraints");
}
```

### Checking Diversification Limit

```javascript
const recipient = investmentAddress;
const proposedAmount = ethers.utils.parseEther("5000");

const withinLimit = await constitution.checkDiversificationLimit(recipient, proposedAmount);
if (withinLimit) {
    // Proceed with allocation
    await treasury.createAllocation(proposalId, projectId, recipient, proposedAmount, tokenAddress);
}
```

### Recording Allocations

```javascript
// Called by Treasury after creating allocation
await constitution.recordAllocation(recipient, allocatedAmount);

// Get current allocation percentage
const percentage = await constitution.getAllocationPercentage(recipient);
console.log(`Recipient has ${percentage / 100}% of total allocations`);
```

### Chairman Emergency Actions

```javascript
// Pause system in emergency
await constitution.connect(chairmanSigner).pauseSystem();

// Veto a specific action
const vetoedAction = ethers.utils.defaultAbiCoder.encode(
    ["string"],
    ["suspicious_allocation"]
);
await constitution.connect(chairmanSigner).vetoAction(targetAddress, vetoedAction);

// Unpause after resolution
await constitution.connect(chairmanSigner).unpauseSystem();
```

## UI Design Considerations

### Constitutional Dashboard
- Display: Current chairman address
- Stats: Total allocated, tithe collected
- Gauge: System pause status
- List: Recent constitutional actions

### Diversification Monitor
- Chart: Allocation distribution pie chart
- Table: Recipients with allocation percentages
- Alert: Warning when approaching 15% limit
- Visual: Color-coded allocation bars

### Chairman Control Panel (Restricted)
- Button: Emergency pause (with confirmation)
- Form: Veto action submission
- History: Past vetoes and pauses
- Status: Current system state

### Allocation Validator
- Input: Recipient address, amount
- Check: Real-time diversification validation
- Result: Pass/fail with explanation
- Suggestion: Maximum allowable amount

## Integration Points

### For Treasury

```javascript
// Treasury checks constitution before allocating
const isValid = await constitution.validateAction(recipient, encodedAction, amount);
if (!isValid) {
    revert("Constitutional constraint violated");
}

// After allocation, record it
await constitution.recordAllocation(recipient, amount);
```

### For DAIOGovernance

```javascript
// Set governance contract
await constitution.setGovernance(daioGovernanceAddress);

// Governance executes via timelock, then validates
async function executeProposal(proposalId, target, amount) {
    const valid = await constitution.validateAction(target, proposalAction, amount);
    require(valid, "Constitutional validation failed");
    // Proceed with execution
}
```

### For External Systems (e.g., mindX via xmind/)

```javascript
// Check if proposed allocation is constitutional
async function checkAllocationValidity(recipient, amount) {
    const valid = await constitution.checkDiversificationLimit(recipient, amount);
    const currentPercentage = await constitution.getAllocationPercentage(recipient);

    return {
        valid,
        currentPercentage: currentPercentage / 100,
        maxAllowed: 15 // %
    };
}
```

## Dependencies

- OpenZeppelin Ownable, Pausable
- Treasury (for integration)
- DAIOGovernance (for integration)

## Security Considerations

- Only chairman can pause/veto
- Only governance can update chairman
- Diversification enforced at validation time
- Allocation tracking prevents manipulation
- System pause is an emergency-only feature
- All actions validated before execution

## Gas Estimates

| Function | Estimated Gas |
|----------|---------------|
| `validateAction` | ~40,000 |
| `checkDiversificationLimit` | View (free) |
| `recordAllocation` | ~50,000 |
| `removeAllocation` | ~30,000 |
| `pauseSystem` | ~30,000 |
| `unpauseSystem` | ~30,000 |
| `vetoAction` | ~25,000 |
| `updateChairman` | ~30,000 |
