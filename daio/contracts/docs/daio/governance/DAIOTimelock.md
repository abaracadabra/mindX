# DAIOTimelock

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/daio/governance/DAIOTimelock.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.20 |
| **Category** | Governance Layer - Security |
| **Inherits** | TimelockController |

## Summary

DAIOTimelock is a timelock controller wrapper for DAIO governance that provides time-delayed execution for governance proposals. It extends OpenZeppelin's TimelockController to add security delays before proposal execution.

## Purpose

- Provide time-delayed execution for governance actions
- Add security layer to prevent immediate execution
- Support multi-role access control (proposers, executors, admin)
- Enable review period before execution

## Technical Specification

### Constructor Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `_minDelay` | `uint256` | Minimum delay before execution (seconds) |
| `proposers` | `address[]` | Addresses allowed to propose |
| `executors` | `address[]` | Addresses allowed to execute |
| `admin` | `address` | Admin address (can be address(0)) |

### Functions

Inherits all functions from OpenZeppelin's TimelockController:

- `schedule()` - Schedule operation for execution
- `execute()` - Execute scheduled operation
- `cancel()` - Cancel scheduled operation
- `getMinDelay()` - Get minimum delay
- `hasRole()` - Check role membership

## Usage Examples

### Deploying DAIOTimelock

```javascript
const minDelay = 2 * 24 * 60 * 60; // 2 days
const proposers = [governanceAddress];
const executors = [governanceAddress];
const admin = address(0);

const timelock = await DAIOTimelock.deploy(
    minDelay,
    proposers,
    executors,
    admin
);
```

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0
