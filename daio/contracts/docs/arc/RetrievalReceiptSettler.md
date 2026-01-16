# RetrievalReceiptSettler

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/arc/RetrievalReceiptSettler.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.20 |
| **Category** | Data Layer - ARC Chain |

## Summary

RetrievalReceiptSettler handles batch settlement of retrieval payments for data served by providers. It aggregates receipts for data retrievals and enables efficient batch payment processing.

## Purpose

- Create receipts for data retrievals
- Enable single and batch payment settlement
- Track retrieval history for providers and buyers
- Optimize gas costs through batch operations

## Technical Specification

### Data Structures

```solidity
struct RetrievalReceipt {
    bytes32 receiptId;      // Unique receipt identifier
    bytes32 rootCID;        // Dataset CID retrieved
    address provider;       // Provider who served data
    address buyer;          // Buyer who requested data
    uint256 bytesServed;    // Bytes retrieved
    uint256 pricePerMB;     // Price per megabyte
    uint256 timestamp;      // Receipt creation time
    bytes signature;        // Provider signature
    bool settled;           // Settlement status
}
```

### State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `receipts` | `mapping(bytes32 => RetrievalReceipt)` | Receipt registry |
| `providerReceipts` | `mapping(address => bytes32[])` | Receipts per provider |
| `buyerReceipts` | `mapping(address => bytes32[])` | Receipts per buyer |
| `totalReceipts` | `uint256` | Total receipts created |
| `totalSettled` | `uint256` | Total receipts settled |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `createReceipt` | `rootCID`, `provider`, `bytesServed`, `pricePerMB`, `signature` | Public | Create retrieval receipt |
| `settleReceipt` | `receiptId` | Buyer (payable) | Settle single receipt |
| `batchSettleReceipts` | `receiptIds` | Buyer (payable) | Settle multiple receipts |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `receipts` | `receiptId` | `RetrievalReceipt` | Get receipt info |
| `getProviderReceipts` | `address` | `bytes32[]` | Get provider's receipts |
| `getBuyerReceipts` | `address` | `bytes32[]` | Get buyer's receipts |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `ReceiptCreated` | `receiptId`, `rootCID`, `provider`, `buyer`, `bytesServed` | New receipt created |
| `ReceiptSettled` | `receiptId`, `amount` | Single receipt settled |
| `ReceiptsBatchSettled` | `receiptIds`, `totalAmount` | Batch settlement complete |

## Payment Calculation

```solidity
// Amount = (bytesServed * pricePerMB) / (1024 * 1024)
// Example: 10 MB at 0.001 ETH/MB = 0.01 ETH
amount = (bytesServed * pricePerMB) / 1048576;
```

## Usage Examples

### Creating a Retrieval Receipt

```javascript
// After data is retrieved, create receipt
const rootCID = ethers.utils.id("bafybeigdyrzt5sfp7...");
const provider = "0x...";
const bytesServed = 10 * 1024 * 1024; // 10 MB
const pricePerMB = ethers.utils.parseEther("0.001");

// Provider signs the retrieval proof
const message = ethers.utils.solidityKeccak256(
    ["bytes32", "address", "uint256", "uint256"],
    [rootCID, buyer, bytesServed, Date.now()]
);
const signature = await providerSigner.signMessage(ethers.utils.arrayify(message));

// Create receipt
const receiptId = await retrievalSettler.createReceipt(
    rootCID,
    provider,
    bytesServed,
    pricePerMB,
    signature
);
```

### Settling a Single Receipt

```javascript
const receipt = await retrievalSettler.receipts(receiptId);
const amount = receipt.bytesServed.mul(receipt.pricePerMB).div(1024 * 1024);

await retrievalSettler.settleReceipt(receiptId, { value: amount });
```

### Batch Settlement

```javascript
// Collect all pending receipts
const receipts = await retrievalSettler.getBuyerReceipts(buyerAddress);
const pendingReceipts = [];
let totalAmount = ethers.BigNumber.from(0);

for (const receiptId of receipts) {
    const receipt = await retrievalSettler.receipts(receiptId);
    if (!receipt.settled) {
        pendingReceipts.push(receiptId);
        totalAmount = totalAmount.add(
            receipt.bytesServed.mul(receipt.pricePerMB).div(1024 * 1024)
        );
    }
}

// Batch settle
await retrievalSettler.batchSettleReceipts(pendingReceipts, {
    value: totalAmount
});
```

## UI Design Considerations

### Receipt Dashboard
- List: Pending receipts grouped by provider
- Summary: Total pending amount
- Action: Settle individual or batch

### Receipt Creation Flow
- Auto: Created after data retrieval
- Display: Receipt details confirmation
- Sign: Provider signature verification

### Payment History
- Table: All receipts with status
- Filter: By provider, date range, status
- Export: CSV/JSON export for accounting

### Batch Settlement UI
- Select: Multiple receipts to settle
- Calculate: Total amount preview
- Confirm: Single transaction for batch
- Receipt: Transaction confirmation

### Provider Earnings
- Summary: Total earnings, pending payments
- Chart: Earnings over time
- List: Individual receipt details

## Integration Points

### For External Systems (e.g., mindX via xmind/)

```javascript
// Automated retrieval and receipt creation
async function retrieveAndReceipt(datasetCID, provider) {
    // Retrieve data (off-chain)
    const { data, bytesServed, signature } = await retrieveFromProvider(
        provider,
        datasetCID
    );

    // Create receipt on-chain
    const receiptId = await retrievalSettler.createReceipt(
        datasetCID,
        provider,
        bytesServed,
        pricePerMB,
        signature
    );

    return { data, receiptId };
}

// Weekly batch settlement
async function weeklySettlement(buyerAddress) {
    const receipts = await retrievalSettler.getBuyerReceipts(buyerAddress);
    const unsettled = receipts.filter(r => !r.settled);

    if (unsettled.length > 0) {
        await retrievalSettler.batchSettleReceipts(
            unsettled.map(r => r.receiptId),
            { value: calculateTotal(unsettled) }
        );
    }
}
```

### For Accounting

```javascript
// Generate settlement report
async function generateReport(buyerAddress, startDate, endDate) {
    const receipts = await retrievalSettler.getBuyerReceipts(buyerAddress);

    return receipts
        .filter(r => r.timestamp >= startDate && r.timestamp <= endDate)
        .map(r => ({
            date: new Date(r.timestamp * 1000),
            provider: r.provider,
            bytes: r.bytesServed,
            amount: r.bytesServed * r.pricePerMB / (1024 * 1024),
            settled: r.settled
        }));
}
```

## Dependencies

- None (standalone contract)

## Security Considerations

- Provider signature prevents receipt forgery
- Only buyer can settle their receipts
- Excess payment refunded automatically
- Settlement is idempotent (can't double-pay)

## Gas Estimates

| Function | Estimated Gas |
|----------|---------------|
| `createReceipt` | ~100,000 |
| `settleReceipt` | ~60,000 |
| `batchSettleReceipts` (10 items) | ~150,000 |
| `batchSettleReceipts` (50 items) | ~500,000 |

## Batch Optimization

Batch settlement saves ~40% gas compared to individual settlements:

| Method | 10 Receipts | Gas Savings |
|--------|-------------|-------------|
| Individual | 600,000 | - |
| Batch | 150,000 | 75% |
