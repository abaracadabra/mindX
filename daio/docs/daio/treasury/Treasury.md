# Treasury

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/daio/treasury/Treasury.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.20 |
| **Category** | Governance Layer - Finance |
| **Inherits** | Ownable, ReentrancyGuard |

## Summary

Treasury is a multi-project treasury contract with automatic 15% tithe collection and multi-signature allocation management. **The treasury can own any and all assets:** native ETH (via `receive`), ERC20 (via `depositERC20` or direct transfer to the contract address), and ERC721/ERC1155 (implements receiver interfaces; use `recoverERC721` / `recoverERC1155` to transfer out). It enforces constitutional constraints and enables reward distribution to agents.

## Purpose

- Manage multiple project treasuries within single contract
- Automatically collect 15% tithe on all deposits
- Create and execute allocations via governance proposals
- Distribute rewards to agents (85% of profits)
- Enforce constitutional diversification constraints
- Support multi-signature execution for large amounts

## DAI and stablecoin support

The Treasury is designed to **hold and distribute DAI and other stablecoins**. Use the DAI token address for your chain as the `token` argument when creating allocations, distributing rewards, or depositing via `depositERC20`. On mainnet, DAI is the recommended canonical stablecoin for allocations and rewards; other stables (USDC, USDT, etc.) work the same way.

**References for utilities and stablecoin work:**

- **[MakerDAO/dss](https://github.com/makerdao/dss)** — Dai Stablecoin System: core DAI mechanics, collateral, and stability. Use as reference for patterns (e.g. stability, collateralization) when building stablecoin or stable-cloning features that interact with DAIO.
- **[dairef](https://github.com/dairef)** — Programmable DAI reference (dss, dss-flash, OpenZeppelin, Synthetix forks). Preferred for **DAI as stablecoin** or **stable cloning/creation** endeavours that need utilities (flash mint, vaults, oracles, etc.).

Preferred stablecoin for a deployment can be set via documentation or configuration (e.g. recommended `token` for allocations on a given chain).

## Companion contracts (same directory)

| Contract | Description |
|----------|-------------|
| **CustomERC20Minter.sol** | ERC20 with `MINTER_ROLE`; grant role to Treasury or governance for minting. Replace or extend with your own working examples later. |
| **WETH.sol** | Wrapped Ether (value-inheritance example): deposit ETH to mint WETH 1:1, withdraw to burn. Treasury can hold WETH as an ERC20 and use it in allocations. |

## Technical Specification

### Data Structures

```solidity
struct ProjectTreasury {
    uint256 nativeBalance;                      // Native token balance
    mapping(address => uint256) tokenBalances;  // ERC20 token balances
    uint256 totalDeposited;                     // Total ever deposited
    uint256 totalAllocated;                     // Total allocated (pending)
    uint256 totalDistributed;                   // Total distributed to agents
    uint256 titheCollected;                     // 15% tithe collected
}

struct Allocation {
    string projectId;       // Project identifier
    address recipient;      // Allocation recipient
    uint256 amount;         // Allocation amount
    address token;          // Token address (address(0) for native)
    bool executed;          // Execution status
    uint256 proposalId;     // Linked proposal ID
}
```

### State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `constitution` | `DAIO_Constitution` | Constitution contract |
| `projectTreasuries` | `mapping(string => ProjectTreasury)` | Project treasuries |
| `allocations` | `mapping(uint256 => Allocation)` | Proposal allocations |
| `signers` | `address[]` | Multi-sig signers |
| `isSigner` | `mapping(address => bool)` | Signer status |
| `requiredSignatures` | `uint256` | Required sigs (default: 3) |
| `totalSigners` | `uint256` | Total signers (default: 5) |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `deposit` | `projectId`, `token` | Public (payable) | Deposit native ETH (15% tithe); `token` must be address(0) |
| `depositERC20` | `projectId`, `token`, `amount` | Public | Deposit ERC20 (e.g. DAI); caller must approve first |
| `createAllocation` | `proposalId`, `projectId`, `recipient`, `amount`, `token` | Governance | Create allocation |
| `executeAllocation` | `proposalId` | Signer | Execute allocation |
| `distributeReward` | `projectId`, `recipient`, `amount`, `token`, `reason` | Governance | Distribute rewards |
| `addSigner` | `signer` | Owner | Add multi-sig signer |
| `removeSigner` | `signer` | Owner | Remove multi-sig signer |
| `recoverERC721` | `token`, `to`, `tokenId` | Owner | Transfer ERC721 out (treasury owns any asset) |
| `recoverERC1155` | `token`, `to`, `id`, `amount`, `data` | Owner | Transfer ERC1155 out (treasury owns any asset) |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `getTreasuryBalance` | `projectId`, `token` | `uint256` | Get balance for project |
| `getTreasuryStats` | `projectId` | `(uint256, ...)` | Get treasury statistics |
| `allocations` | `proposalId` | `Allocation` | Get allocation details |
| `signers` | - | `address[]` | Get all signers |
| `isSigner` | `address` | `bool` | Check if signer |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `Deposit` | `projectId`, `depositor`, `amount`, `token` | Funds deposited |
| `TitheCollected` | `projectId`, `amount`, `token` | Tithe collected |
| `AllocationCreated` | `proposalId`, `projectId`, `recipient`, `amount`, `token` | Allocation created |
| `AllocationExecuted` | `proposalId`, `recipient`, `amount`, `token` | Allocation executed |
| `RewardDistributed` | `projectId`, `recipient`, `amount`, `token`, `reason` | Reward sent |
| `SignerAdded` | `signer` | New signer added |
| `SignerRemoved` | `signer` | Signer removed |

## Tithe Mechanism

All deposits automatically have 15% tithe collected:

```
Deposit: 100 ETH
├── Tithe (15%): 15 ETH → Central treasury
└── Net Deposit (85%): 85 ETH → Project balance
```

## Usage Examples

### Depositing Native ETH

```javascript
const projectId = "mindX";
const depositAmount = ethers.utils.parseEther("10");

// 15% tithe is automatically collected
await treasury.deposit(projectId, ethers.constants.AddressZero, {
    value: depositAmount
});

// Net deposit: 8.5 ETH (85%)
// Tithe collected: 1.5 ETH (15%)
```

### Depositing ERC20 Tokens (e.g. DAI)

```javascript
const projectId = "FinancialMind";
const tokenAddress = daiAddress; // or USDC, etc.
const amount = ethers.utils.parseEther("1000"); // 1000 DAI (18 decimals)

// Approve treasury first
await dai.approve(treasury.address, amount);

// Deposit ERC20 (15% tithe applied)
await treasury.depositERC20(projectId, tokenAddress, amount);
```

### Creating and Executing Allocation

```javascript
// Step 1: Governance creates allocation after proposal passes
const proposalId = 42;
const projectId = "mindX";
const recipient = agentWalletAddress;
const amount = ethers.utils.parseEther("5");
const token = ethers.constants.AddressZero; // ETH

await treasury.createAllocation(
    proposalId,
    projectId,
    recipient,
    amount,
    token
);

// Step 2: Multi-sig signer executes allocation
await treasury.connect(signerWallet).executeAllocation(proposalId);
```

### Distributing Rewards

```javascript
const projectId = "mindX";
const recipient = tradingAgentAddress;
const amount = ethers.utils.parseEther("1");
const token = ethers.constants.AddressZero;
const reason = "Profitable trading performance Q4 2024";

await treasury.distributeReward(
    projectId,
    recipient,
    amount,
    token,
    reason
);
```

### Getting Treasury Stats

```javascript
const projectId = "mindX";
const [
    totalDeposited,
    totalAllocated,
    totalDistributed,
    titheCollected,
    availableBalance
] = await treasury.getTreasuryStats(projectId);

console.log(`Total Deposited: ${ethers.utils.formatEther(totalDeposited)} ETH`);
console.log(`Available Balance: ${ethers.utils.formatEther(availableBalance)} ETH`);
console.log(`Tithe Collected: ${ethers.utils.formatEther(titheCollected)} ETH`);
```

## UI Design Considerations

### Treasury Dashboard
- Cards: Per-project treasury balances
- Chart: Deposit/withdrawal history
- Stats: Total deposited, allocated, distributed
- Gauge: Tithe collected amount

### Deposit Form
- Select: Project ID
- Select: Token type (ETH or ERC20)
- Input: Amount
- Preview: Tithe calculation (15%)
- Display: Net deposit amount

### Allocation Management
- List: Pending allocations
- Details: Recipient, amount, proposal link
- Status: Created, awaiting execution
- Actions: Execute (for signers)

### Multi-Sig Panel
- List: Current signers
- Add/Remove: Signer management
- Queue: Pending executions
- Threshold: Required signatures display

### Reward Distribution
- Form: Project, recipient, amount, reason
- History: Past distributions
- Filter: By project, recipient, date
- Export: CSV for accounting

## Integration Points

### For DAIOGovernance

```javascript
// After proposal passes, create allocation
async function executeAllocationProposal(proposalId, projectId, recipient, amount, token) {
    // Validate against constitution (already done in governance)
    await treasury.createAllocation(proposalId, projectId, recipient, amount, token);
}
```

### For Constitution

```javascript
// Treasury calls constitution to record allocation
await constitution.recordAllocation(recipient, amount);
```

### For External Systems (e.g., mindX via xmind/)

```javascript
// Get project treasury status
async function getProjectTreasury(projectId) {
    const [deposited, allocated, distributed, tithe, balance] =
        await treasury.getTreasuryStats(projectId);

    const ethBalance = await treasury.getTreasuryBalance(projectId, ethers.constants.AddressZero);

    return {
        deposited: ethers.utils.formatEther(deposited),
        allocated: ethers.utils.formatEther(allocated),
        distributed: ethers.utils.formatEther(distributed),
        titheCollected: ethers.utils.formatEther(tithe),
        availableETH: ethers.utils.formatEther(ethBalance)
    };
}

// Deposit trading profits
async function depositProfits(projectId, amount) {
    await treasury.deposit(projectId, ethers.constants.AddressZero, {
        value: amount
    });
}
```

### For FinancialMind

```javascript
// Automated profit distribution
async function distributeTradingProfits(profits) {
    const tithe = profits.mul(15).div(100);
    const netProfits = profits.sub(tithe);

    // Deposit to treasury (tithe auto-collected)
    await treasury.deposit("FinancialMind", ethers.constants.AddressZero, {
        value: profits
    });

    // Distribute to agents based on contribution
    for (const agent of contributors) {
        await treasury.distributeReward(
            "FinancialMind",
            agent.address,
            agent.share,
            ethers.constants.AddressZero,
            "Trading contribution"
        );
    }
}
```

## Dependencies

- DAIO_Constitution (for validation)
- OpenZeppelin Ownable, ReentrancyGuard, SafeERC20

## Security Considerations

- ReentrancyGuard on all fund transfers
- Multi-sig required for large allocations (>1000 ETH)
- Only governance can create allocations
- Only signers can execute allocations
- Constitution validates diversification before allocation
- SafeERC20 for token transfers
- `receive()` allows direct ETH transfers

## Gas Estimates

| Function | Estimated Gas |
|----------|---------------|
| `deposit` (ETH) | ~80,000 |
| `deposit` (ERC20) | ~100,000 |
| `createAllocation` | ~120,000 |
| `executeAllocation` | ~80,000 |
| `distributeReward` | ~60,000 |
| `addSigner` | ~50,000 |
| `removeSigner` | ~40,000 |

## Economic Flow

```
External Deposits
      │
      ▼
Treasury.deposit()
      │
      ├─── 15% Tithe ──► Central Treasury Reserve
      │
      └─── 85% Net ──► Project Balance
                          │
                          ▼
              ┌───────────┴───────────┐
              │                       │
    Governance Allocation     Agent Rewards (85%)
              │                       │
              ▼                       ▼
    executeAllocation()      distributeReward()
              │                       │
              ▼                       ▼
       Recipient Wallet       Agent Wallets
```
