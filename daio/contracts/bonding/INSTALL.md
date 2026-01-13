# Installation Guide

## Prerequisites

- Foundry (forge, cast, anvil)
- Node.js (optional, for additional tooling)

## Installation Steps

### 1. Install Foundry Dependencies

```bash
cd DAIO/bonding

# Install OpenZeppelin Contracts
forge install OpenZeppelin/openzeppelin-contracts

# Install PRB Math (for UD60x18 fixed-point arithmetic)
forge install PaulRBerg/prb-math
```

### 2. Verify Installation

```bash
# Build contracts
forge build

# Run tests
forge test -vv
```

### 3. Configure Environment

Create a `.env` file:

```bash
PRIVATE_KEY=your_private_key_here
RPC_URL=https://your-rpc-url
UNIV2_ROUTER=0x...  # Uniswap V2 Router address
WETH=0x...          # WETH address
```

### 4. Deploy

```bash
# Deploy to testnet
forge script script/Deploy.s.sol:Deploy --rpc-url $RPC_URL --broadcast --verify

# Deploy to mainnet (use with caution)
forge script script/Deploy.s.sol:Deploy --rpc-url $MAINNET_RPC --broadcast --verify
```

## Project Structure

```
bonding/
├── src/
│   ├── math/              # Curve mathematics
│   ├── token/             # ERC20 token contract
│   ├── pool/              # Bonding curve pool
│   ├── factory/           # Factory for launching curves
│   ├── extensions/        # Presale extension
│   └── liquidity/         # Liquidity provision system
│       └── provisioners/   # Uniswap V2/V3/V4 provisioners
├── test/                  # Test files
├── script/                # Deployment scripts
└── foundry.toml          # Foundry configuration
```

## Quick Start

### Launch a Simple Bonding Curve

```solidity
// Deploy factory
BondingCurveFactory factory = new BondingCurveFactory(owner);

// Launch curve with defaults
BondingCurveFactory.LaunchPowerCurveNativeArgs memory args;
args.name = "";              // Will use "BOND CURV"
args.symbol = "";            // Will use "BOND"
args.initialMintToOwner = 0; // No initial mint
args.kUD60x18 = 1e12;        // Curve coefficient
args.pUD60x18 = 1e18;        // Linear curve (p=1)
args.enablePresale = false;  // No presale

(address token, address pool,) = factory.launchPowerCurveNative(args);
```

### Launch with Custom Token

```solidity
args.name = "My Custom Token";
args.symbol = "MCT";
args.initialMintToOwner = 1000e18; // Mint 1000 tokens to owner
```

### Launch with Presale

```solidity
args.enablePresale = true;
args.presaleOptions = presaleConfig;
args.provisioner = address(uniV2Provisioner);
args.liquidityTemplate = liquidityTemplate;
```

## Testing

Run all tests:
```bash
forge test
```

Run with verbose output:
```bash
forge test -vv
```

Run specific test:
```bash
forge test --match-test testBuyAndSellWithFee
```

## Gas Reports

Generate gas reports:
```bash
forge test --gas-report
```

## Security

Before deploying to mainnet:
1. ✅ Run full test suite
2. ✅ Review gas optimizations
3. ✅ Consider professional audit
4. ✅ Test on testnet first
5. ✅ Verify all addresses
6. ✅ Check slippage parameters
7. ✅ Verify LP locking duration
