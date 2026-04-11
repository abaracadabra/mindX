# DAIO Contract Deployment Guide

## 🚀 Essential Contracts for Deployment

### 📋 EVM Contract Deployment Order

**1. Core ERC-8004 Suite (Required)**
```bash
cd daio/contracts/evm
npx hardhat run deploy.ts --network <network>
```

Deploys in order:
- `SingletonFactory.sol` - Deterministic deployment utility
- `IdentityRegistryUpgradeable.sol` - Agent identity NFTs
- `ReputationRegistryUpgradeable.sol` - Reputation tracking
- `ValidationRegistryUpgradeable.sol` - Verification system
- `BonaFide.sol` - BANKON integration

**2. Algorand aORC Suite (Required)**
```bash
cd daio/contracts/algorand
algokit deploy --network testnet
```

Deploys:
- `aORC-registry.algo.ts` - Chain verification registry
- `aORC-minter.algo.ts` - Agent NFT minting
- `aORC-bonafide.algo.ts` - BANKON reputation tokens
- `aORC-typeminter.algo.ts` - Specialized agent types

### 🎯 Deployment Networks

**EVM Networks (Choose based on needs):**
- **Ethereum Sepolia** (Testnet) - Primary EVM testing
- **Polygon Amoy** (Testnet) - Lower gas testing
- **Base Sepolia** (Testnet) - L2 testing
- **Ethereum Mainnet** (Production)
- **Polygon Mainnet** (Production)
- **Base Mainnet** (Production)

**Algorand Networks:**
- **TestNet** (Testing) - Primary Algorand testing
- **MainNet** (Production)

### 💰 Deployment Costs Estimate

**EVM (per network):**
- Gas Required: ~15M gas
- Ethereum: ~0.15-0.3 ETH (depending on gas price)
- Polygon: ~0.01 MATIC
- Base: ~0.001 ETH

**Algorand (per network):**
- App Creation: ~0.1 ALGO per contract
- Box Storage: ~0.0025 ALGO per chain/agent entry
- Total: ~0.5 ALGO for full suite

### 🔐 Required Setup

**Environment Variables (.env):**
```bash
# EVM Networks
PRIVATE_KEY=your_deployer_private_key
ETHERSCAN_API_KEY=your_etherscan_key
POLYGONSCAN_API_KEY=your_polygonscan_key
BASESCAN_API_KEY=your_basescan_key

# RPC URLs
MAINNET_RPC_URL=https://eth-mainnet.alchemyapi.io/v2/YOUR-API-KEY
SEPOLIA_RPC_URL=https://eth-sepolia.alchemyapi.io/v2/YOUR-API-KEY
POLYGON_RPC_URL=https://polygon-mainnet.alchemyapi.io/v2/YOUR-API-KEY
BASE_RPC_URL=https://mainnet.base.org

# Algorand
ALGOD_TOKEN=your_algod_token
ALGOD_SERVER=https://testnet-api.algonode.cloud
ALGOD_PORT=443
```

### ✅ Post-Deployment Checklist

**EVM:**
1. [ ] Contract verification on block explorers
2. [ ] Update .env.contracts with deployed addresses
3. [ ] Test basic functions (register, verify, mint)
4. [ ] Configure treasury/admin addresses

**Algorand:**
1. [ ] Fund contracts with initial ALGO
2. [ ] Create BONA FIDE ASA token
3. [ ] Configure clawback permissions
4. [ ] Test chain registration flow

**Integration:**
1. [ ] Update frontend with contract addresses
2. [ ] Test cross-chain identity flow
3. [ ] Verify BANKON actualization workflow
4. [ ] Configure multi-signature governance

---

**Ready for Production Deployment**