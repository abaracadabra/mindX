# DatasetRegistry

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/arc/DatasetRegistry.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.20 |
| **Category** | Data Layer - ARC Chain |

## Summary

DatasetRegistry is a registry contract for datasets on the ARC chain, mapping unique dataset IDs to IPFS Content Identifiers (CIDs). It enables creators to register, version, and manage datasets with full provenance tracking.

## Purpose

- Register datasets with IPFS CIDs for decentralized storage
- Track version history for dataset updates
- Enable creator-based dataset management
- Provide query functionality for dataset discovery

## Technical Specification

### Data Structures

```solidity
struct Dataset {
    bytes32 datasetId;      // Unique identifier
    string rootCID;         // IPFS manifest CID (current version)
    address creator;        // Creator's address
    uint256 createdAt;      // Creation timestamp
    uint256 version;        // Current version number
    bool isActive;          // Active status flag
}
```

### State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `datasets` | `mapping(bytes32 => Dataset)` | Dataset ID to Dataset mapping |
| `versions` | `mapping(bytes32 => string[])` | Version history (all CIDs) |
| `creatorDatasets` | `mapping(address => bytes32[])` | Datasets by creator address |
| `owner` | `address` | Contract owner |
| `totalDatasets` | `uint256` | Total registered datasets |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `registerDataset` | `datasetId`, `rootCID` | Public | Register a new dataset |
| `versionDataset` | `datasetId`, `newRootCID` | Creator only | Create new version |
| `deactivateDataset` | `datasetId` | Creator/Owner | Deactivate dataset |
| `activateDataset` | `datasetId` | Creator/Owner | Reactivate dataset |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `getDataset` | `datasetId` | `Dataset` | Get dataset info |
| `getLatestVersion` | `datasetId` | `string` | Get current CID |
| `getAllVersions` | `datasetId` | `string[]` | Get version history |
| `getCreatorDatasets` | `address` | `bytes32[]` | Get creator's datasets |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `DatasetRegistered` | `datasetId`, `rootCID`, `creator`, `version` | New dataset registered |
| `DatasetVersioned` | `datasetId`, `newRootCID`, `version` | Dataset updated |
| `DatasetDeactivated` | `datasetId` | Dataset deactivated |
| `DatasetActivated` | `datasetId` | Dataset reactivated |

## Usage Examples

### Registering a Dataset

```javascript
// Generate unique dataset ID
const datasetId = ethers.utils.id("my-ai-training-dataset-v1");
const ipfsCID = "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi";

// Register dataset
await datasetRegistry.registerDataset(datasetId, ipfsCID);
```

### Creating a New Version

```javascript
const newCID = "bafybeihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku";
await datasetRegistry.versionDataset(datasetId, newCID);
```

### Querying Datasets

```javascript
// Get dataset info
const dataset = await datasetRegistry.getDataset(datasetId);

// Get all versions
const versions = await datasetRegistry.getAllVersions(datasetId);

// Get creator's datasets
const creatorDatasets = await datasetRegistry.getCreatorDatasets(creatorAddress);
```

## UI Design Considerations

### Dataset Registration Form
- Input: Dataset name (generates ID)
- Input: IPFS CID (validate format)
- Display: Preview of IPFS content if available
- Action: Register button with confirmation

### Dataset Management Dashboard
- List: Creator's datasets with status indicators
- Filter: Active/Inactive toggle
- Sort: By creation date, version count
- Actions: Version, Activate/Deactivate

### Version History View
- Timeline: Visual version history
- Compare: Diff between versions (if applicable)
- Rollback: Link to previous CIDs

## Integration Points

### For External Systems (e.g., mindX via xmind/)

```javascript
// xmind/DAIOBridge integration
async function registerAgentDataset(agentId, trainingDataCID) {
    const datasetId = ethers.utils.id(`agent-${agentId}-training`);
    await datasetRegistry.registerDataset(datasetId, trainingDataCID);
    return datasetId;
}
```

### For Providers

```javascript
// Provider announces they serve a dataset
const datasetId = await datasetRegistry.getDataset(someId);
await providerRegistry.addDataset(datasetId.datasetId);
```

## Dependencies

- None (standalone contract)

## Security Considerations

- Only creators can version their datasets
- Owner can deactivate any dataset (emergency)
- CID validation prevents empty registrations
- No duplicate dataset IDs allowed

## Gas Estimates

| Function | Estimated Gas |
|----------|---------------|
| `registerDataset` | ~100,000 |
| `versionDataset` | ~50,000 |
| `deactivateDataset` | ~30,000 |
| `getDataset` | View (free) |
