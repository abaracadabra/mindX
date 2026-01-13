# DAIO Bonding Curve Architecture

## Overview

The DAIO Bonding Curve Protocol implements a protocol-first power bonding curve with optional SMAIRT presale extension. The system uses continuous mint/burn mechanics with a power curve pricing model and supports multiple token types.

## Token Types

The protocol supports three token types via `TokenFactory`:

### 1. CURVE_TOKEN (Default)
- **Standard bonding curve token**
- Default name: "REFLECT REWARD"
- Default symbol: "REWARD"
- Mint/burn restricted to bonding curve pool
- Configurable name, symbol, and initial mint amount

### 2. REFLECTION_REWARD
- **Reflection token with reward distribution**
- Default name: "REFLECT REWARD"
- Default symbol: "REWARD"
- Configurable parameters:
  - Total supply (default: 1e35 = 100 quadrillion)
  - Reflection fee (default: 300 bps = 3%)
  - Liquidity fee (default: 100 bps = 1%)
  - Team fee (default: 100 bps = 1%)
- Features:
  - Wallet-to-wallet fee exemption
  - Reflection distribution to holders
  - Auto-swap for liquidity/team fees
  - Max transfer limits

### 3. REBASE_TOKEN
- **Rebase token with auto-rebase mechanics (DeltaV design)**
- Default name: "REB ACE"
- Default symbol: "REBACE"
- Configurable parameters:
  - Initial supply (default: 22222222 * 10^18)
  - All fee parameters (liquidity, treasury, burn, RFV)
  - Rebase frequency and yield
- Features:
  - Auto-rebase mechanics using gons/fragments
  - Buy/sell fee differences
  - Burn mechanics
  - Max transaction limits
  - Multiple fee receivers (liquidity, treasury, RFV)

## Core Architecture

### Bonding Curve Model

The bonding curve uses a power function:
```
Price(S) = k * S^p
```

Where:
- `k`: Coefficient (UD60x18 fixed-point)
- `p`: Exponent (UD60x18 fixed-point, can be fractional)
- `S`: Current token supply

### Token Creation

**Token Factory System**:
- `TokenFactory` - Unified factory for creating all token types
- `TokenType` enum - Defines available token types
- Each token type has its own creation function with defaults

**Default Configurations**:
- **CurveToken**: "REFLECT REWARD" / "REWARD", no initial mint
- **ReflectionRewardToken**: "REFLECT REWARD" / "REWARD", 1e35 supply, 3%/1%/1% fees
- **RebaseToken**: "REB ACE" / "REBACE", 22222222 * 10^18 supply, DeltaV fee structure

**Custom Configuration**:
All parameters are configurable at deployment via `TokenFactory` or `BondingCurveFactory`.

## Contract Structure

### Token Contracts

1. **TokenType.sol** - Enum defining token types
   - `CURVE_TOKEN` - Standard bonding curve token
   - `REFLECTION_REWARD` - Reflection token
   - `REBASE_TOKEN` - Rebase token

2. **TokenFactory.sol** - Factory for creating token types
   - `createCurveToken()` - Creates standard bonding curve tokens
   - `createReflectionRewardToken()` - Creates reflection tokens
   - `createRebaseToken()` - Creates rebase tokens
   - `createToken()` - Unified function based on TokenType enum

3. **CurveToken.sol** - ERC20 token for bonding curve
   - Mint/burn restricted to pool
   - Configurable name, symbol, initial mint
   - Default: "REFLECT REWARD" / "REWARD"

4. **ReflectionRewardToken.sol** - Reflection token with rewards
   - Parameterized fee system
   - Reflection distribution
   - Wallet-to-wallet fee exemption
   - Default: "REFLECT REWARD" / "REWARD"

5. **RebaseToken.sol** - Rebase token (DeltaV design)
   - Auto-rebase mechanics
   - Gons/fragments system
   - Buy/sell fee differences
   - Default: "REB ACE" / "REBACE"

### Core Contracts

6. **CurveMath.sol** - Mathematical library for bonding curve calculations
   - Power curve pricing
   - Integral calculations for mint/burn
   - Inverse integral for cost-to-amount conversion

7. **BondingCurvePoolNative.sol** - Main bonding curve pool
   - ETH reserve
   - Buy/sell functions
   - Optional protocol fee
   - Slippage protection

8. **BondingCurveFactory.sol** - Factory for launching curves
   - Deploys token + pool
   - Configurable token parameters
   - Optional presale deployment
   - Uses CurveToken by default

### Presale Extension

### Enhanced Presale Features

- **Liquidity-Free Presale**: Option to run presale without initial DEX liquidity
- **Flexible Team Allocation**: Allocate team tokens from raised funds, token supply, or both
- **DEX Price Comparison**: Compare bonding curve prices with live DEX pairs

See `PRESALE_ENHANCEMENTS.md` for detailed information.


9. **BondingCurvePresaleSMAIRT.sol** - SMAIRT presale extension
   - Raises ETH
   - Uses bonding curve to buy tokens
   - Automatic liquidity provision
   - LP locking

### Liquidity System

10. **ILiquidityProvisioner.sol** - Liquidity provision interface
    - Supports V2, V3, V4 modes
    - On/off switches for each version
    - Unified request structure

11. **UniV2Provisioner.sol** - Uniswap V2 implementation (Production)
    - Fully implemented
    - Production-ready
    - Uses UniswapV2Router02

12. **UniV3Provisioner.sol** - Uniswap V3 stub (Extension)
    - Reverts by default (safety)
    - Can be enabled with full implementation
    - Parameters defined for future use

13. **UniV4Provisioner.sol** - Uniswap V4 stub (Extension)
    - Reverts by default (safety)
    - Can be enabled with full implementation
    - Parameters defined for future use

14. **LiquidityLocker.sol** - LP token time-locking
    - Prevents rug pulls
    - Time-based release
    - Beneficiary management

## Uniswap Integration Strategy

### V2 (Production Ready)
- ✅ Fully implemented
- ✅ Tested and audited patterns
- ✅ Uses standard UniswapV2Router02
- ✅ Automatic pair creation
- ✅ LP token management

### V3 (Extension)
- ⚠️ Stub implementation
- ⚠️ Reverts by default (safety)
- ✅ Parameters defined:
  - PositionManager address
  - Fee tier (500, 3000, 10000)
  - Tick range (tickLower, tickUpper)
- 🔄 Can be enabled with full implementation

### V4 (Extension)
- ⚠️ Stub implementation
- ⚠️ Reverts by default (safety)
- ✅ Parameters defined:
  - PoolManager address
  - Pool ID
  - Hook address
- 🔄 Can be enabled with full implementation

### Safety Features

All versions use multiple layers of on/off switches:
1. **Master switch**: `LiquidityRequest.enabled`
2. **Version-specific switch**: `V2Params.enabled`, `V3Params.enabled`, `V4Params.enabled`
3. **Mode validation**: Checks `DexMode` matches provisioner

## Usage Flow

### 1. Create Token (via TokenFactory)

```solidity
TokenFactory factory = new TokenFactory();

// Create CurveToken
address curveToken = factory.createCurveToken("My Token", "MTK", owner, 1000e18);

// Create ReflectionRewardToken
TokenFactory.ReflectionTokenParams memory reflectionParams;
reflectionParams.name = "REFLECT REWARD";  // or "" for default
reflectionParams.symbol = "REWARD";        // or "" for default
reflectionParams.totalSupply = 1e35;       // or 0 for default
reflectionParams.reflectionFee = 300;      // or 0 for default (3%)
reflectionParams.liquidityFee = 100;       // or 0 for default (1%)
reflectionParams.teamFee = 100;           // or 0 for default (1%)
reflectionParams.teamWallet = teamWallet;
reflectionParams.liquidityWallet = liquidityWallet;
reflectionParams.router = router;
reflectionParams.weth = weth;
address reflectionToken = factory.createReflectionRewardToken(reflectionParams);

// Create RebaseToken
TokenFactory.RebaseTokenParams memory rebaseParams;
rebaseParams.name = "REB ACE";             // or "" for default
rebaseParams.symbol = "REBACE";           // or "" for default
rebaseParams.initialSupply = 22222222 * 10**18; // or 0 for default
rebaseParams.liquidityFee = 33;           // or 0 for default (3.3%)
rebaseParams.treasuryFee = 45;            // or 0 for default (4.5%)
rebaseParams.burnFee = 11;                // or 0 for default (1.1%)
rebaseParams.buyFeeRFV = 22;              // or 0 for default (2.2%)
rebaseParams.sellFeeTreasuryAdded = 66;   // or 0 for default (6.6%)
rebaseParams.sellFeeRFVAdded = 45;        // or 0 for default (4.5%)
rebaseParams.liquidityReceiver = liquidityReceiver;
rebaseParams.treasuryReceiver = treasuryReceiver;
rebaseParams.riskFreeValueReceiver = rfvReceiver;
rebaseParams.router = router;
rebaseParams.weth = weth;
rebaseParams.busdToken = busdToken;       // optional, can be address(0)
address rebaseToken = factory.createRebaseToken(rebaseParams);
```

### 2. Launch Bonding Curve

```solidity
BondingCurveFactory factory = new BondingCurveFactory(owner);

BondingCurveFactory.LaunchPowerCurveNativeArgs memory args;
args.name = "My Token";           // Custom or "" for "REFLECT REWARD"
args.symbol = "MTK";              // Custom or "" for "REWARD"
args.initialMintToOwner = 1000e18; // Initial mint amount
args.kUD60x18 = 1e12;             // Curve coefficient
args.pUD60x18 = 1e18;             // Exponent (1.0 = linear)
args.enablePresale = true;        // Optional presale

(address token, address pool, address presale) = factory.launchPowerCurveNative(args);
```

### 3. Buy/Sell on Curve

```solidity
// Buy tokens
pool.buy{value: 1 ether}(minTokensOut, recipient);

// Sell tokens
token.approve(address(pool), amount);
pool.sell(amount, minEthOut, recipient);
```

### 4. Presale Flow (if enabled)

1. **Contribute**: Users send ETH to presale
2. **Finalize**: Owner finalizes presale
   - Buys tokens from curve for distribution
   - Buys tokens from curve for LP
   - Adds liquidity via provisioner
   - Locks LP tokens
3. **Claim**: Users claim their tokens

## Security Features

- ✅ ReentrancyGuard on all value transfers
- ✅ Slippage protection on buys/sells
- ✅ Access control on critical functions
- ✅ Input validation throughout
- ✅ Safe math via UD60x18 fixed-point
- ✅ LP locking to prevent rug pulls
- ✅ Multiple on/off switches for extensions
- ✅ Max transfer limits (ReflectionRewardToken, RebaseToken)
- ✅ Fee exemption system (ReflectionRewardToken, RebaseToken)

## Gas Optimization

- Uses UD60x18 for efficient fixed-point math
- Minimal storage operations
- Batch operations where possible
- Efficient curve calculations
- Reflection batch processing (ReflectionRewardToken)
- Gons/fragments system (RebaseToken)

## Testing

Run tests with:
```bash
forge test -vv
```

Test coverage:
- Bonding curve buy/sell
- Protocol fees
- Token creation with defaults
- Token creation with custom params
- All three token types
- Presale flow
- LP locking

## Deployment

1. Install dependencies:
```bash
forge install OpenZeppelin/openzeppelin-contracts
forge install PaulRBerg/prb-math
```

2. Set environment variables:
```bash
export PRIVATE_KEY=...
export UNIV2_ROUTER=...
export WETH=...
```

3. Deploy:
```bash
forge script script/Deploy.s.sol:Deploy --rpc-url $RPC_URL --broadcast
```

## Future Enhancements

- [ ] Full Uniswap V3 implementation
- [ ] Full Uniswap V4 implementation
- [ ] Additional curve types (exponential, logarithmic)
- [ ] Multi-token reserves
- [ ] Governance integration
- [ ] Fee distribution mechanisms
- [ ] Additional token types
