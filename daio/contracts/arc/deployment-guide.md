# Deployment Guide for AgenticPlace Settlement Layer

## Prerequisites

1. **Get Testnet USDC**
   - Visit: https://faucet.circle.com
   - Connect your wallet
   - Request testnet USDC for Arc Testnet

2. **Setup Wallet**
   - Install MetaMask or compatible wallet
   - Add Arc Testnet network:
     - Network Name: Arc Testnet
     - RPC URL: https://rpc.testnet.arc.network
     - Chain ID: 5042002 (0x4CEF52)
     - Currency: USDC
     - Explorer: https://testnet.arcscan.app

## Deployment Steps

### Option 1: Using Remix IDE (Easiest)

1. **Open Remix**: https://remix.ethereum.org

2. **Create Files**:
   - Copy `AgenticMarketplaceEscrow.sol`
   - Copy `AgentReputationRegistry.sol`
   - Copy `SubscriptionManager.sol`

3. **Compile**:
   - Select Solidity Compiler 0.8.20+
   - Click "Compile"

4. **Deploy AgentReputationRegistry**:
   - Go to "Deploy & Run Transactions"
   - Select "Injected Provider - MetaMask"
   - Select `AgentReputationRegistry`
   - Click "Deploy"
   - Save deployed address

5. **Deploy SubscriptionManager**:
   - Constructor parameters:
     - `_feeCollector`: Your treasury address
     - `_platformFeeRate`: 250 (for 2.5%)
   - Click "Deploy"
   - Save deployed address

6. **Deploy AgenticMarketplaceEscrow**:
   - Constructor parameters:
     - `_feeCollector`: Your treasury address
     - `_platformFeeRate`: 250 (for 2.5%)
   - Click "Deploy"
   - Save deployed address

7. **Link Contracts**:
   ```solidity
   // In AgentReputationRegistry
   setEscrowContract(escrowAddress)
   ```

### Option 2: Using Hardhat

1. **Install Hardhat**:
```bash
npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox
npx hardhat init
```

2. **Configure Hardhat** (`hardhat.config.js`):
```javascript
require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: "0.8.20",
  networks: {
    arcTestnet: {
      url: "https://rpc.testnet.arc.network",
      chainId: 5042002,
      accounts: [process.env.PRIVATE_KEY]
    }
  }
};
```

3. **Create Deploy Script** (`scripts/deploy.js`):
```javascript
const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying with:", deployer.address);

  // Deploy AgentReputationRegistry
  const ReputationRegistry = await hre.ethers.getContractFactory("AgentReputationRegistry");
  const reputationRegistry = await ReputationRegistry.deploy();
  await reputationRegistry.waitForDeployment();
  console.log("ReputationRegistry:", await reputationRegistry.getAddress());

  // Deploy SubscriptionManager
  const feeCollector = deployer.address; // Change to your treasury
  const platformFeeRate = 250; // 2.5%
  
  const SubscriptionManager = await hre.ethers.getContractFactory("SubscriptionManager");
  const subscriptionManager = await SubscriptionManager.deploy(feeCollector, platformFeeRate);
  await subscriptionManager.waitForDeployment();
  console.log("SubscriptionManager:", await subscriptionManager.getAddress());

  // Deploy AgenticMarketplaceEscrow
  const Escrow = await hre.ethers.getContractFactory("AgenticMarketplaceEscrow");
  const escrow = await Escrow.deploy(feeCollector, platformFeeRate);
  await escrow.waitForDeployment();
  console.log("Escrow:", await escrow.getAddress());

  // Link contracts
  await reputationRegistry.setEscrowContract(await escrow.getAddress());
  console.log("Contracts linked!");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
```

4. **Deploy**:
```bash
npx hardhat run scripts/deploy.js --network arcTestnet
```

### Option 3: Using Foundry

1. **Install Foundry**:
```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

2. **Initialize Project**:
```bash
forge init agenticplace-settlement
cd agenticplace-settlement
```

3. **Add Contracts**: Copy contracts to `src/`

4. **Deploy Script** (`script/Deploy.s.sol`):
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/AgenticMarketplaceEscrow.sol";
import "../src/AgentReputationRegistry.sol";
import "../src/SubscriptionManager.sol";

contract DeployScript is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address feeCollector = vm.envAddress("FEE_COLLECTOR");
        
        vm.startBroadcast(deployerPrivateKey);

        AgentReputationRegistry reputationRegistry = new AgentReputationRegistry();
        SubscriptionManager subscriptionManager = new SubscriptionManager(feeCollector, 250);
        AgenticMarketplaceEscrow escrow = new AgenticMarketplaceEscrow(feeCollector, 250);

        reputationRegistry.setEscrowContract(address(escrow));

        vm.stopBroadcast();

        console.log("ReputationRegistry:", address(reputationRegistry));
        console.log("SubscriptionManager:", address(subscriptionManager));
        console.log("Escrow:", address(escrow));
    }
}
```

5. **Deploy**:
```bash
forge script script/Deploy.s.sol:DeployScript --rpc-url https://rpc.testnet.arc.network --broadcast
```

## Post-Deployment Configuration

1. **Add Arbitrators**:
```solidity
escrow.addArbitrator(arbitratorAddress);
```

2. **Verify Contracts** (Optional):
```bash
# Using Hardhat
npx hardhat verify --network arcTestnet DEPLOYED_ADDRESS

# Check on explorer
# https://testnet.arcscan.app/address/YOUR_CONTRACT_ADDRESS
```

3. **Test Basic Functions**:
```javascript
// Create test agreement
const tx = await escrow.createAgreement(
  agentAddress,
  ethers.parseUnits("10", 6), // 10 USDC
  86400, // 1 day
  0, // Immediate settlement
  { value: ethers.parseUnits("10", 6) }
);
```

## Verification

After deployment, verify:
- ✅ All contracts deployed successfully
- ✅ Contracts linked (reputation registry knows escrow)
- ✅ Fee collector set correctly
- ✅ Platform fee rate configured
- ✅ Owner has admin access
- ✅ Can create test agreement
- ✅ Can register test agent

## Troubleshooting

### Issue: Transaction Fails
- **Solution**: Ensure you have enough testnet USDC for gas
- Get more from: https://faucet.circle.com

### Issue: Contract Not Verified
- **Solution**: Manually verify on Arc explorer
- Use contract source code and constructor arguments

### Issue: Wrong Network
- **Solution**: Double-check Chain ID is 5042002
- Verify RPC URL: https://rpc.testnet.arc.network

## Next Steps

1. **Build Frontend**: Create UI for interacting with contracts
2. **Add Monitoring**: Set up event listeners
3. **Test Thoroughly**: Run through all user flows
4. **Document APIs**: Create integration docs for agents
5. **Launch Beta**: Start with small group of users

## Support Resources

- **Arc Docs**: https://docs.arc.network
- **Circle Docs**: https://developers.circle.com
- **Faucet**: https://faucet.circle.com
- **Explorer**: https://testnet.arcscan.app

---

**Ready to deploy? Start with Option 1 (Remix) for the quickest path!**
