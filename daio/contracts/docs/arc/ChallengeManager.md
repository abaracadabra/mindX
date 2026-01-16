# ChallengeManager

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/arc/ChallengeManager.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.20 |
| **Category** | Data Layer - ARC Chain |

## Summary

ChallengeManager implements Proof-of-Availability challenges for dataset providers. It ensures providers are actually storing and serving the data they claim to have by issuing cryptographic challenges that require serving specific data blocks.

## Purpose

- Issue random challenges to verify data availability
- Track provider responses and verification
- Update provider reputation based on challenge results
- Trigger collateral slashing for failed challenges

## Technical Specification

### Data Structures

```solidity
struct Challenge {
    bytes32 challengeId;     // Unique challenge identifier
    bytes32 dealId;          // Associated storage deal
    bytes32 rootCID;         // Dataset being challenged
    address provider;        // Provider being challenged
    uint256 blockNumber;     // Block when issued
    bytes32 blockHash;       // Random block to serve
    bytes32 responseHash;    // Provider's response hash
    uint256 issuedAt;        // Issue timestamp
    uint256 respondedAt;     // Response timestamp
    ChallengeStatus status;  // Current status
}

enum ChallengeStatus { Pending, Responded, Verified, Failed }
```

### State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `challenges` | `mapping(bytes32 => Challenge)` | Challenge registry |
| `providerChallenges` | `mapping(address => bytes32[])` | Challenges per provider |
| `dealChallenges` | `mapping(bytes32 => bytes32[])` | Challenges per deal |
| `pinDealEscrow` | `PinDealEscrow` | Escrow contract |
| `providerRegistry` | `ProviderRegistry` | Provider registry |
| `challengeTimeout` | `uint256` | Blocks before timeout (default: 100) |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `issueChallenge` | `dealId` | Public | Issue challenge for a deal |
| `respondToChallenge` | `challengeId`, `responseHash` | Provider only | Submit response hash |
| `verifyChallenge` | `challengeId`, `responseData` | Public | Verify response |
| `setChallengeTimeout` | `_timeout` | Owner | Set timeout blocks |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `challenges` | `challengeId` | `Challenge` | Get challenge info |
| `getProviderChallenges` | `address` | `bytes32[]` | Get provider's challenges |
| `getDealChallenges` | `dealId` | `bytes32[]` | Get deal's challenges |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `ChallengeIssued` | `challengeId`, `dealId`, `provider`, `blockHash` | New challenge issued |
| `ChallengeResponded` | `challengeId`, `responseHash` | Provider responds |
| `ChallengeVerified` | `challengeId`, `success` | Challenge verified |
| `ChallengeFailed` | `challengeId` | Challenge failed/timeout |

## Challenge Flow

```
                    issueChallenge()
                          │
                          ▼
                     [Pending]
                          │
                          │ ◄── challengeTimeout blocks
                          │
        ┌─────────────────┴─────────────────┐
        │                                   │
respondToChallenge()                   timeout
        │                                   │
        ▼                                   ▼
   [Responded]                          [Failed]
        │                                   │
verifyChallenge()                    slash collateral
        │
        ▼
┌───────┴───────┐
│               │
▼               ▼
[Verified]   [Failed]
    │           │
    │      slash collateral
    ▼
update reputation
```

## Challenge Generation

Challenges use on-chain randomness:

```solidity
bytes32 blockHash = keccak256(abi.encodePacked(
    blockhash(block.number - 1),
    block.timestamp,
    dealId
));
```

The provider must serve the data block corresponding to this hash and respond with:

```solidity
responseHash = keccak256(responseData);
```

## Usage Examples

### Issuing a Challenge

```javascript
// Anyone can issue a challenge for an active deal
const challengeId = await challengeManager.issueChallenge(dealId);
console.log("Challenge issued:", challengeId);
```

### Provider Responding to Challenge

```javascript
// Provider retrieves the required data block
const challenge = await challengeManager.challenges(challengeId);
const dataBlock = await fetchDataBlock(challenge.rootCID, challenge.blockHash);

// Calculate response hash
const responseHash = ethers.utils.keccak256(dataBlock);

// Submit response
await challengeManager.respondToChallenge(challengeId, responseHash);
```

### Verifying a Challenge

```javascript
// Verifier fetches data and verifies
const responseData = await fetchDataBlock(challenge.rootCID, challenge.blockHash);
const success = await challengeManager.verifyChallenge(challengeId, responseData);

if (success) {
    console.log("Challenge verified - provider reputation increased");
} else {
    console.log("Challenge failed - collateral slashed");
}
```

## UI Design Considerations

### Challenge Dashboard
- List: Active challenges with countdown timers
- Filter: By status (Pending, Responded, Verified, Failed)
- Stats: Challenge success rate
- Actions: Issue new challenge

### Challenge Details
- Info: Challenge parameters
- Status: Current status with progress indicator
- Timeline: Issue → Response → Verification
- Result: Success/failure with consequences

### Provider Challenge View
- Alert: Pending challenges requiring response
- Timer: Time remaining to respond
- History: Past challenge performance
- Stats: Success rate trends

### Automated Monitoring
- Schedule: Auto-issue challenges at intervals
- Alert: Failed challenges
- Report: Provider reliability metrics

## Integration Points

### For External Systems (e.g., mindX via xmind/)

```javascript
// Automated challenge monitoring
async function monitorDealHealth(dealId) {
    const challenges = await challengeManager.getDealChallenges(dealId);

    let successCount = 0;
    for (const challengeId of challenges) {
        const challenge = await challengeManager.challenges(challengeId);
        if (challenge.status === 2) { // Verified
            successCount++;
        }
    }

    return successCount / challenges.length; // Health score
}

// Issue periodic challenges
async function scheduleChallenge(dealId) {
    return await challengeManager.issueChallenge(dealId);
}
```

### For ProviderRegistry

```javascript
// ChallengeManager updates provider reputation
await providerRegistry.recordChallenge(provider, success);
```

### For PinDealEscrow

```javascript
// Slash on failed challenge
await pinDealEscrow.slashCollateral(dealId, slashAmount);
```

## Dependencies

- PinDealEscrow (deal information, slashing)
- ProviderRegistry (reputation updates)

## Security Considerations

- Timeout prevents indefinite pending state
- Only provider can respond to their challenges
- Response hash prevents data substitution
- On-chain randomness for challenge selection
- Collateral slashing deters dishonest providers

## Gas Estimates

| Function | Estimated Gas |
|----------|---------------|
| `issueChallenge` | ~120,000 |
| `respondToChallenge` | ~60,000 |
| `verifyChallenge` | ~80,000 |
