# PinDealEscrow

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/arc/PinDealEscrow.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.20 |
| **Category** | Data Layer - ARC Chain |

## Summary

PinDealEscrow manages storage deals between data buyers and providers, similar to Filecoin's deal system but native to ARC chain. It handles payment escrow, deal lifecycle, and collateral slashing.

## Purpose

- Create and manage storage deals between buyers and providers
- Escrow payments with epoch-based release
- Handle provider collateral and slashing
- Track deal lifecycle (Pending → Active → Completed)

## Technical Specification

### Data Structures

```solidity
struct PinDeal {
    bytes32 dealId;             // Unique deal identifier
    bytes32 rootCID;            // Dataset CID
    address provider;           // Storage provider
    address buyer;              // Data buyer
    uint256 startBlock;         // Deal start block
    uint256 endBlock;           // Deal end block
    uint256 pricePerEpoch;      // Price per block/epoch
    uint256 collateral;         // Provider collateral
    uint256 challengeFrequency; // Blocks between challenges
    uint256 totalPaid;          // Total paid so far
    DealStatus status;          // Current status
}

enum DealStatus { Pending, Active, Completed, Cancelled, Slashed }
```

### State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `deals` | `mapping(bytes32 => PinDeal)` | Deal registry |
| `providerDeals` | `mapping(address => bytes32[])` | Deals by provider |
| `buyerDeals` | `mapping(address => bytes32[])` | Deals by buyer |
| `challengeManager` | `address` | ChallengeManager contract |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `createDeal` | `rootCID`, `provider`, `durationBlocks`, `pricePerEpoch`, `challengeFrequency` | Public (payable) | Create storage deal |
| `activateDeal` | `dealId` | Provider only | Activate pending deal |
| `cancelDeal` | `dealId` | Buyer/Provider | Cancel before activation |
| `releasePayment` | `dealId`, `epochs` | Public | Release payment for epochs |
| `slashCollateral` | `dealId`, `amount` | ChallengeManager | Slash provider collateral |
| `addCollateral` | `dealId` | Provider (payable) | Add more collateral |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `deals` | `dealId` | `PinDeal` | Get deal info |
| `providerDeals` | `address` | `bytes32[]` | Get provider's deals |
| `buyerDeals` | `address` | `bytes32[]` | Get buyer's deals |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `DealCreated` | `dealId`, `rootCID`, `provider`, `buyer`, `pricePerEpoch` | New deal created |
| `DealActivated` | `dealId` | Provider activates deal |
| `DealCompleted` | `dealId` | Deal fully paid |
| `DealCancelled` | `dealId` | Deal cancelled |
| `PaymentReleased` | `dealId`, `provider`, `amount` | Payment released |
| `CollateralSlashed` | `dealId`, `provider`, `amount` | Collateral slashed |

## Deal Lifecycle

```
[Buyer] createDeal() ──► [Pending]
                              │
                    [Provider] activateDeal()
                              │
                              ▼
                         [Active]
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
  releasePayment()    slashCollateral()      cancelDeal()
        │                     │                     │
        ▼                     ▼                     ▼
   [Completed]           [Slashed]           [Cancelled]
```

## Usage Examples

### Creating a Storage Deal

```javascript
const rootCID = ethers.utils.id("bafybeigdyrzt5sfp7...");
const provider = "0x...";
const durationBlocks = 100000; // ~2 weeks on ARC
const pricePerEpoch = ethers.utils.parseEther("0.0001");
const challengeFrequency = 1000;

const totalCost = pricePerEpoch.mul(durationBlocks);

const tx = await pinDealEscrow.createDeal(
    rootCID,
    provider,
    durationBlocks,
    pricePerEpoch,
    challengeFrequency,
    { value: totalCost }
);

const receipt = await tx.wait();
const dealId = receipt.events[0].args.dealId;
```

### Provider Activating a Deal

```javascript
// Provider confirms they're ready to serve
await pinDealEscrow.activateDeal(dealId);

// Optionally add collateral
await pinDealEscrow.addCollateral(dealId, {
    value: ethers.utils.parseEther("0.5")
});
```

### Releasing Payments

```javascript
// Release payment for 1000 epochs
await pinDealEscrow.releasePayment(dealId, 1000);
```

## UI Design Considerations

### Deal Creation Form
- Select: Dataset (from DatasetRegistry)
- Select: Provider (from ProviderRegistry with reputation)
- Input: Duration (blocks/days)
- Input: Price per epoch
- Input: Challenge frequency
- Display: Total cost calculator
- Action: Create deal button

### Deal Dashboard
- Tabs: Active / Pending / Completed / Cancelled
- Card: Deal details with progress bar
- Stats: Time remaining, payments made
- Actions: Release payment, cancel

### Provider Deal Management
- List: Incoming deal requests
- Action: Activate / Reject deals
- Display: Collateral status
- Alert: Low collateral warnings

### Deal Progress View
- Timeline: Deal milestones
- Progress: Blocks remaining
- Payments: Payment history
- Challenges: Challenge results

## Integration Points

### For External Systems (e.g., mindX via xmind/)

```javascript
// Create storage deal for agent model
async function storeAgentModel(modelCID, provider, durationDays) {
    const blocksPerDay = 6400; // ARC estimate
    const durationBlocks = durationDays * blocksPerDay;
    const pricePerEpoch = ethers.utils.parseEther("0.00001");

    const dealId = await pinDealEscrow.createDeal(
        modelCID,
        provider,
        durationBlocks,
        pricePerEpoch,
        1000, // Challenge every 1000 blocks
        { value: pricePerEpoch.mul(durationBlocks) }
    );

    return dealId;
}
```

### For ChallengeManager

```javascript
// Slash collateral after failed challenge
await pinDealEscrow.slashCollateral(dealId, slashAmount);
```

## Dependencies

- ChallengeManager (for slashing)

## Security Considerations

- Full payment escrowed on deal creation
- Provider collateral protects buyers
- Only ChallengeManager can slash
- Refund on cancellation (pre-activation)
- ReentrancyGuard recommended for production

## Gas Estimates

| Function | Estimated Gas |
|----------|---------------|
| `createDeal` | ~180,000 |
| `activateDeal` | ~60,000 |
| `releasePayment` | ~80,000 |
| `slashCollateral` | ~70,000 |
| `addCollateral` | ~50,000 |
