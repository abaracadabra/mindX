# TransmuteAgent

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/THOT/agents/TransmuteAgent.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.24 |
| **Category** | THOT Agents - Data Conversion |
| **Inherits** | Ownable |

## Summary

TransmuteAgent converts raw information into structured THOT knowledge. It acts as an agent contract for THOT creation from raw data, processing and transforming data before minting THOTs.

## Purpose

- Convert raw data to THOT format
- Process and transform input data
- Batch transmute multiple inputs
- Create THOTs with full parameters
- Enable automated THOT creation

## Technical Specification

### State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `_thotContract` | `THOT` | THOT contract reference |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `transmuteData` | `inputData` | Owner | Convert raw data to THOT |
| `batchTransmute` | `inputDataArray[]` | Owner | Batch convert multiple inputs |
| `transmuteDataFull` | `recipient`, `inputData`, `dimensions`, `parallelUnits`, `metadataURI` | Owner | Convert with full THOT parameters |
| `setTHOTContract` | `thotAddress` | Owner | Update THOT contract address |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `DataTransmuted` | `inputHash`, `transformedHash`, `thotId` | Data transmuted to THOT |

## Usage Examples

### Transmuting Data

```javascript
const inputData = "Raw market data: price, volume, sentiment";
const thotId = await transmuteAgent.transmuteData(inputData);
```

### Batch Transmuting

```javascript
const inputs = [
    "Data point 1",
    "Data point 2",
    "Data point 3"
];

const thotIds = await transmuteAgent.batchTransmute(inputs);
```

### Full Parameter Transmuting

```javascript
const recipient = agentAddress;
const inputData = "Complex data structure";
const dimensions = 512;
const parallelUnits = 4;
const metadataURI = "ipfs://metadata";

const thotId = await transmuteAgent.transmuteDataFull(
    recipient,
    inputData,
    dimensions,
    parallelUnits,
    metadataURI
);
```

## Integration Points

### For THOT Contract

```javascript
// TransmuteAgent calls THOT.mintTHOT()
const thotId = await thot.mintTHOT(transformedHash);
```

### For AI Agents

```javascript
// Agents can use TransmuteAgent to create THOTs
const thotId = await transmuteAgent.transmuteData(agentOutput);
```

## Security Considerations

- **Access Control**: Only owner can transmute
- **Data Processing**: Internal processing function can be customized
- **Contract Update**: THOT contract can be updated by owner

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0
