# Enhanced Presale Features

The SMAIRT presale has been enhanced with liquidity-free operation and flexible team allocation options.

## Liquidity-Free Presale

### Overview
Presales can now run without initial liquidity, allowing funds to be raised purely through the bonding curve mechanism.

### Configuration
```solidity
PresaleOptions memory options;
options.useLiquidityFreePresale = true; // Enable liquidity-free mode
options.nativeForLiquidityBps = 0;     // No liquidity allocation
```

### Behavior
- When `useLiquidityFreePresale = true`:
  - No liquidity is added to DEX during finalization
  - All raised funds can be allocated to:
    - Token purchases for distribution
    - Team allocation
    - Marketing/Dev/DAO allocations
  - Liquidity can be added later manually or through separate mechanism

### Use Cases
- Pure bonding curve launches
- Community-driven launches without initial DEX liquidity
- Testing and validation phases
- Gradual liquidity addition strategies

## Flexible Team Allocation

### Overview
Team allocation can now be configured from multiple sources with flexible percentages.

### Allocation Sources

#### 1. From Raised Funds
Allocate team tokens by using a percentage of raised funds to buy tokens from the bonding curve.

```solidity
options.useTeamAllocationFromFunds = true;
options.teamAllocationFromFundsBps = 500; // 5% of raised funds
options.teamWallet = teamWalletAddress;
```

**Behavior**:
- Calculates: `ethForTeam = (nativeRaised * teamAllocationFromFundsBps) / 10_000`
- Buys tokens from bonding curve using this ETH
- Transfers tokens directly to team wallet

#### 2. From Token Supply
Allocate a percentage of total token supply directly to the team.

```solidity
options.useTeamAllocationFromSupply = true;
options.teamAllocationFromSupplyBps = 1000; // 10% of total supply
options.teamWallet = teamWalletAddress;
```

**Behavior**:
- Calculates: `teamTokens = (totalSupply * teamAllocationFromSupplyBps) / 10_000`
- Allocates tokens from available supply
- Transfers tokens to team wallet

#### 3. Both Sources (Combined)
You can use both allocation methods simultaneously.

```solidity
options.useTeamAllocationFromFunds = true;
options.teamAllocationFromFundsBps = 500;  // 5% of funds
options.useTeamAllocationFromSupply = true;
options.teamAllocationFromSupplyBps = 1000; // 10% of supply
options.teamWallet = teamWalletAddress;
```

**Behavior**:
- Team receives tokens from both sources
- Total allocation = tokens from funds + tokens from supply

## Presale Flow

### Standard Flow (with liquidity)
1. Users contribute ETH during presale period
2. Owner finalizes presale:
   - Buys tokens from curve for distribution
   - Buys tokens from curve for LP
   - Adds liquidity to DEX
   - Locks LP tokens
   - Allocates team tokens (if configured)
   - Distributes marketing/dev/DAO funds
3. Users claim their tokens

### Liquidity-Free Flow
1. Users contribute ETH during presale period
2. Owner finalizes presale:
   - Buys tokens from curve for distribution
   - Allocates team tokens (if configured)
   - Distributes marketing/dev/DAO funds
   - **No liquidity added**
3. Users claim their tokens
4. Liquidity can be added later through separate mechanism

## Team Allocation Examples

### Example 1: 5% from Funds
```solidity
PresaleOptions memory opts;
opts.useTeamAllocationFromFunds = true;
opts.teamAllocationFromFundsBps = 500; // 5%
opts.teamWallet = 0x...;

// If presale raises 100 ETH:
// - Team gets: 5 ETH worth of tokens (bought from curve)
```

### Example 2: 10% from Supply
```solidity
PresaleOptions memory opts;
opts.useTeamAllocationFromSupply = true;
opts.teamAllocationFromSupplyBps = 1000; // 10%
opts.teamWallet = 0x...;

// If total supply is 1,000,000 tokens:
// - Team gets: 100,000 tokens (from supply)
```

### Example 3: Combined (5% funds + 10% supply)
```solidity
PresaleOptions memory opts;
opts.useTeamAllocationFromFunds = true;
opts.teamAllocationFromFundsBps = 500;
opts.useTeamAllocationFromSupply = true;
opts.teamAllocationFromSupplyBps = 1000;
opts.teamWallet = 0x...;

// Team receives both allocations
```

## Events

New events are emitted for team allocation:

```solidity
event TeamAllocatedFromFunds(
    address indexed teamWallet,
    uint256 ethAmount,
    uint256 tokensAmount
);

event TeamAllocatedFromSupply(
    address indexed teamWallet,
    uint256 tokensAmount
);

event LiquidityFreePresaleMode(bool enabled);
```

## Validation

The presale contract validates:
- Team wallet address is not zero when allocation is enabled
- Allocation percentages don't exceed reasonable limits
- Sufficient funds available for team allocation from funds
- Sufficient supply available for team allocation from supply

## Security Considerations

1. **Team Allocation Limits**: Consider setting reasonable maximums for team allocation percentages
2. **Liquidity-Free Risk**: Without initial liquidity, price discovery may be more volatile
3. **Token Supply**: Ensure sufficient supply for team allocation from supply
4. **Fund Allocation**: Verify team allocation from funds doesn't exceed available balance

## Best Practices

1. **Transparency**: Clearly communicate team allocation percentages to community
2. **Vesting**: Consider implementing vesting for team allocations
3. **Liquidity Planning**: Plan for liquidity addition if using liquidity-free mode
4. **Testing**: Test allocation calculations with various scenarios
5. **Documentation**: Document allocation strategy in project documentation
