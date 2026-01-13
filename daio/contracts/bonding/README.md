# DAIO Bonding Curve Protocol

A complete Foundry project implementing a protocol-first power bonding curve (continuous mint/burn) with:
- Multiple token types (CurveToken, ReflectionRewardToken, RebaseToken)
- Optional protocol fee (bps, default 0)
- Factory launcher with configurable token creation
- SMAIRT presale extension (uses the bonding curve, not the reverse)
- Uniswap V2 liquidity provisioner (production-ready)
- Uniswap V3/V4 extension stubs with on/off switches for safety

## Features

### Token Types

The protocol supports three token types via `TokenFactory`:

1. **CurveToken** - Standard bonding curve token
   - Default: "REFLECT REWARD" / "REWARD"
   - Mint/burn restricted to pool
   - Configurable name, symbol, initial mint

2. **ReflectionRewardToken** - Reflection token with rewards
   - Default: "REFLECT REWARD" / "REWARD"
   - Configurable supply and fees (default: 1e35 supply, 3%/1%/1% fees)
   - Wallet-to-wallet fee exemption
   - Reflection distribution to holders

3. **RebaseToken** - Rebase token with auto-rebase mechanics
   - Default: "REB ACE" / "REBACE"
   - Based on DeltaV THRUST design
   - Configurable supply and fees
   - Auto-rebase using gons/fragments system

### Core Components
- **BondingCurvePoolNative**: Native-reserve (ETH) bonding curve pool with power curve pricing
- **CurveToken**: ERC20 token for bonding curve (default: "REFLECT REWARD" / "REWARD", configurable)
- **CurveMath**: Power curve math library using UD60x18 fixed-point arithmetic
- **BondingCurveFactory**: Factory for launching new bonding curves with configurable tokens
- **TokenFactory**: Factory for creating different token types

### Presale Extension
- **BondingCurvePresaleSMAIRT**: SMAIRT presale that raises ETH and uses bonding curve for token distribution
- Supports hard cap, soft cap, contribution limits
- Automatic liquidity provision and LP locking

### Liquidity Provision
- **UniV2Provisioner**: Production-ready Uniswap V2 liquidity provisioner
- **UniV3Provisioner**: Extension stub for V3 (reverts by default, can be enabled)
- **UniV4Provisioner**: Extension stub for V4 (reverts by default, can be enabled)
- **LiquidityLocker**: Time-locked LP token management

## Installation

```bash
# Install dependencies
forge install OpenZeppelin/openzeppelin-contracts
forge install PaulRBerg/prb-math

# Build
forge build

# Test
forge test -vv
```

## Usage

### Create Token Types

```solidity
TokenFactory tokenFactory = new TokenFactory();

// Create CurveToken
address curveToken = tokenFactory.createCurveToken("My Token", "MTK", owner, 1000e18);

// Create ReflectionRewardToken with defaults
TokenFactory.ReflectionTokenParams memory reflectionParams;
reflectionParams.name = "";  // Uses "REFLECT REWARD"
reflectionParams.symbol = ""; // Uses "REWARD"
reflectionParams.totalSupply = 0; // Uses 1e35
reflectionParams.reflectionFee = 0; // Uses 300 (3%)
reflectionParams.liquidityFee = 0; // Uses 100 (1%)
reflectionParams.teamFee = 0; // Uses 100 (1%)
reflectionParams.teamWallet = teamWallet;
reflectionParams.liquidityWallet = liquidityWallet;
reflectionParams.router = router;
reflectionParams.weth = weth;
address reflectionToken = tokenFactory.createReflectionRewardToken(reflectionParams);

// Create RebaseToken with defaults
TokenFactory.RebaseTokenParams memory rebaseParams;
rebaseParams.name = "";  // Uses "REB ACE"
rebaseParams.symbol = ""; // Uses "REBACE"
rebaseParams.initialSupply = 0; // Uses 22222222 * 10^18
// ... set other params or use defaults
address rebaseToken = tokenFactory.createRebaseToken(rebaseParams);
```

### Launch a Bonding Curve

```solidity
BondingCurveFactory factory = BondingCurveFactory(factoryAddress);

BondingCurveFactory.LaunchPowerCurveNativeArgs memory args;
args.name = "My Token";           // Custom token name (or "" for "REFLECT REWARD")
args.symbol = "MTK";              // Custom token symbol (or "" for "REWARD")
args.initialMintToOwner = 1000e18; // Initial mint amount
args.kUD60x18 = 1e12;             // Curve coefficient
args.pUD60x18 = 1e18;             // Curve exponent (1.0 = linear)
args.protocolFeeBps = 200;        // 2% protocol fee
args.enablePresale = true;        // Enable SMAIRT presale

(address token, address pool, address presale) = factory.launchPowerCurveNative(args);
```

### Buy/Sell on Bonding Curve

```solidity
// Buy tokens
pool.buy{value: 1 ether}(minTokensOut, recipient);

// Sell tokens
token.approve(address(pool), amount);
pool.sell(amount, minEthOut, recipient);
```

## Curve Model

The bonding curve uses a power function:
- **Spot Price**: `P(S) = k * S^p`
- **Mint Cost**: Integral from S to S+Δ
- **Burn Refund**: Integral from S-Δ to S

Where:
- `k`: Coefficient (reserve per token^(p+1))
- `p`: Exponent (can be fractional, e.g., 0.5 for square root, 1.0 for linear)
- `S`: Current token supply

## Uniswap Integration

### V2 (Production Ready)
- Fully implemented and tested
- Uses UniswapV2Router02 interface
- Automatic pair creation and LP token management

### V3 (Extension)
- Stub contract included
- Parameters defined in `ILiquidityProvisioner.V3Params`
- Can be enabled by implementing the provisioner

### V4 (Extension)
- Stub contract included
- Parameters defined in `ILiquidityProvisioner.V4Params`
- Can be enabled by implementing the provisioner

All versions use on/off switches via `enabled` flag in `LiquidityRequest` for safety.

## Security

- ✅ ReentrancyGuard on all value transfers
- ✅ Access control on critical functions
- ✅ Slippage protection on buys/sells
- ✅ Input validation throughout
- ✅ Safe math via UD60x18 fixed-point
- ✅ LP locking to prevent rug pulls
- ✅ Max transfer limits (ReflectionRewardToken, RebaseToken)
- ✅ Fee exemption system

## Contracts

### Token Contracts
- `src/token/TokenType.sol` - Token type enumeration
- `src/token/TokenFactory.sol` - Factory for creating token types
- `src/token/CurveToken.sol` - Standard bonding curve token
- `src/token/ReflectionRewardToken.sol` - Reflection token with rewards
- `src/token/RebaseToken.sol` - Rebase token with auto-rebase

### Core
- `src/math/CurveMath.sol` - Bonding curve mathematics
- `src/pool/BondingCurvePoolNative.sol` - Main bonding curve pool
- `src/factory/BondingCurveFactory.sol` - Factory for launching curves

### Extensions
- `src/extensions/BondingCurvePresaleSMAIRT.sol` - SMAIRT presale extension

### Liquidity
- `src/liquidity/LiquidityLocker.sol` - LP token time-locking
- `src/liquidity/ILiquidityProvisioner.sol` - Liquidity provision interface
- `src/liquidity/provisioners/UniV2Provisioner.sol` - Uniswap V2 implementation
- `src/liquidity/provisioners/UniV3Provisioner.sol` - Uniswap V3 stub
- `src/liquidity/provisioners/UniV4Provisioner.sol` - Uniswap V4 stub

## License

MIT

## Bonding Curve Types

The protocol supports multiple curve types:

- **POWER**: Configurable power curve `P(S) = k * S^p`
- **LINEAR**: Constant slope `P(S) = k * S`
- **EXPONENTIAL**: Spike curve `P(S) = k * (e^(a*S) - 1)` (starts slow, spikes up)
- **DECELERATING**: Stable curve `P(S) = k * sqrt(S)` (starts fast, becomes stable)

See `CURVE_TYPES.md` for details.

## DEX Price Comparison

Compare bonding curve prices with live DEX pairs using `DEXPriceOracle`:

```solidity
DEXPriceOracle oracle = new DEXPriceOracle();
(uint256 dexPrice,,) = oracle.getDEXPrice(token, weth, pair);
(uint256 ratio, int256 premium) = oracle.comparePrices(bondingPrice, dexPrice);
```

## Enhanced Presale Features

- **Liquidity-Free Presale**: Run presale without initial DEX liquidity
- **Flexible Team Allocation**: Allocate from raised funds, token supply, or both
- **DEX Price Comparison**: Real-time price comparison with DEX pairs

See `PRESALE_ENHANCEMENTS.md` for details.

### TIERED Curve
- **Tiered pricing**: Linear increase → flatline → linear increase
- **Parameters**: `k` (initial slope), `threshold1` (flatline start), `threshold2` (flatline end), `k2` (second slope)
- **Use Cases**: Presale periods with price stability, milestone-based pricing
