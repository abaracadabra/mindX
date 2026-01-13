# ProviderRegistry

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/arc/ProviderRegistry.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.20 |
| **Category** | Data Layer - ARC Chain |

## Summary

ProviderRegistry manages dataset providers (storage nodes/agents) on the ARC chain. It tracks provider information, reputation scores, staking, and the datasets each provider serves.

## Purpose

- Register and manage dataset providers
- Track provider reputation based on challenge performance
- Map providers to datasets they serve
- Enable discovery of providers for specific datasets

## Technical Specification

### Data Structures

```solidity
struct Provider {
    address providerAddress;     // Provider's wallet
    string peerId;               // IPFS peer ID
    string endpoint;             // Service endpoint URL
    uint256 stake;               // Collateral amount
    uint256 reputation;          // Score 0-10000 (basis points)
    uint256 successRate;         // Challenge success rate (basis points)
    uint256 medianLatency;       // Median retrieval latency (ms)
    uint256 totalChallenges;     // Total challenges received
    uint256 successfulChallenges; // Successful responses
    bool isActive;               // Active status
    uint256 registeredAt;        // Registration timestamp
}
```

### State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `providers` | `mapping(address => Provider)` | Provider registry |
| `providerDatasets` | `mapping(address => bytes32[])` | Datasets per provider |
| `datasetProviders` | `mapping(bytes32 => address[])` | Providers per dataset |
| `challengeManager` | `address` | ChallengeManager contract |
| `totalProviders` | `uint256` | Total registered providers |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `registerProvider` | `peerId`, `endpoint`, `initialStake` | Public (payable) | Register as provider |
| `updateProviderEndpoint` | `endpoint` | Provider only | Update endpoint URL |
| `addDataset` | `rootCID` | Provider only | Add dataset to serve |
| `removeDataset` | `rootCID` | Provider only | Stop serving dataset |
| `updateReputation` | `provider`, `successRate`, `medianLatency` | ChallengeManager | Update reputation |
| `recordChallenge` | `provider`, `success` | ChallengeManager | Record challenge result |
| `updateStake` | `newStake` | Provider only | Update stake amount |
| `deactivateProvider` | - | Provider only | Deactivate self |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `providers` | `address` | `Provider` | Get provider info |
| `getDatasetProviders` | `rootCID` | `address[]` | Get providers for dataset |
| `getProviderDatasets` | `address` | `bytes32[]` | Get datasets for provider |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `ProviderRegistered` | `provider`, `peerId`, `endpoint`, `stake` | New provider registered |
| `ProviderStakeUpdated` | `provider`, `newStake` | Stake changed |
| `ProviderReputationUpdated` | `provider`, `newReputation` | Reputation updated |
| `DatasetAdded` | `provider`, `rootCID` | Provider adds dataset |
| `DatasetRemoved` | `provider`, `rootCID` | Provider removes dataset |
| `ProviderDeactivated` | `provider` | Provider deactivated |

## Reputation System

Reputation is calculated based on:

1. **Success Rate**: Challenge pass rate (0-10000 basis points)
2. **Latency Bonus**: Lower latency = higher bonus
   - Latency < 1000ms: Bonus = (1000 - latency) / 10
   - Maximum bonus: 100 points

```
reputation = successRate + latencyBonus
// Capped at 10000
```

## Usage Examples

### Registering as a Provider

```javascript
const peerId = "12D3KooWR1eqWjPCPL...";
const endpoint = "https://provider.example.com/api";
const initialStake = ethers.utils.parseEther("1.0");

await providerRegistry.registerProvider(peerId, endpoint, initialStake, {
    value: initialStake
});
```

### Adding a Dataset to Serve

```javascript
const datasetCID = ethers.utils.id("bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi");
await providerRegistry.addDataset(datasetCID);
```

### Finding Providers for a Dataset

```javascript
const providers = await providerRegistry.getDatasetProviders(datasetCID);

// Get details for each provider
for (const addr of providers) {
    const provider = await providerRegistry.providers(addr);
    console.log(`Provider: ${addr}, Reputation: ${provider.reputation}`);
}
```

## UI Design Considerations

### Provider Registration Form
- Input: IPFS Peer ID (validate format)
- Input: Endpoint URL (validate reachability)
- Input: Initial stake amount
- Display: Stake requirements/recommendations

### Provider Dashboard
- Stats: Reputation, success rate, latency
- Chart: Challenge performance over time
- List: Datasets being served
- Actions: Add/remove datasets, update endpoint

### Provider Discovery
- List: Providers sorted by reputation
- Filter: By dataset, minimum reputation
- Compare: Side-by-side provider comparison
- Select: Choose provider for storage deal

### Provider Metrics
- Gauge: Current reputation score
- History: Reputation trend over time
- Breakdown: Success rate vs latency contribution

## Integration Points

### For External Systems (e.g., mindX via xmind/)

```javascript
// Find best provider for a dataset
async function findBestProvider(datasetCID) {
    const providers = await providerRegistry.getDatasetProviders(datasetCID);
    let bestProvider = null;
    let bestReputation = 0;

    for (const addr of providers) {
        const provider = await providerRegistry.providers(addr);
        if (provider.reputation > bestReputation && provider.isActive) {
            bestProvider = provider;
            bestReputation = provider.reputation;
        }
    }
    return bestProvider;
}
```

### For ChallengeManager

```javascript
// After verifying a challenge
await providerRegistry.recordChallenge(providerAddress, true);
await providerRegistry.updateReputation(
    providerAddress,
    newSuccessRate,
    medianLatency
);
```

## Dependencies

- ChallengeManager (for reputation updates)

## Security Considerations

- Providers must stake collateral to register
- Only ChallengeManager can update reputation
- Providers cannot fake challenge results
- Stake can be slashed via PinDealEscrow

## Gas Estimates

| Function | Estimated Gas |
|----------|---------------|
| `registerProvider` | ~150,000 |
| `addDataset` | ~80,000 |
| `removeDataset` | ~60,000 |
| `updateReputation` | ~50,000 |
