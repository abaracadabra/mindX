const { ethers, upgrades } = require("hardhat");
const fs = require("fs");
const path = require("path");

interface DeploymentResult {
  network: string;
  chainId: number;
  contracts: {
    [key: string]: {
      address: string;
      implementation?: string;
      transactionHash: string;
      blockNumber: number;
    };
  };
  deployedAt: string;
  deployer: string;
}

async function main() {
  console.log("🚀 Starting AgenticPlace ERC-8004 Contract Deployment");
  console.log("==================================================");

  const [deployer] = await ethers.getSigners();
  const network = await ethers.provider.getNetwork();

  console.log(`📡 Network: ${network.name} (Chain ID: ${network.chainId})`);
  console.log(`👨‍💼 Deployer: ${deployer.address}`);

  const balance = await ethers.provider.getBalance(deployer.address);
  console.log(`💰 Balance: ${ethers.formatEther(balance)} ETH`);
  console.log();

  const deploymentResult: DeploymentResult = {
    network: network.name,
    chainId: Number(network.chainId),
    contracts: {},
    deployedAt: new Date().toISOString(),
    deployer: deployer.address,
  };

  try {
    // 1. Deploy SingletonFactory (for deterministic deployments)
    console.log("1️⃣  Deploying SingletonFactory...");
    const SingletonFactory = await ethers.getContractFactory("SingletonFactory");
    const singletonFactory = await SingletonFactory.deploy();
    await singletonFactory.waitForDeployment();
    const singletonAddr = await singletonFactory.getAddress();

    deploymentResult.contracts.SingletonFactory = {
      address: singletonAddr,
      transactionHash: singletonFactory.deploymentTransaction()?.hash || "",
      blockNumber: 0,
    };
    console.log(`   ✅ SingletonFactory deployed to: ${singletonAddr}`);
    console.log();

    // 2. Deploy IdentityRegistry (Upgradeable)
    console.log("2️⃣  Deploying IdentityRegistry (Upgradeable)...");
    const IdentityRegistry = await ethers.getContractFactory("IdentityRegistryUpgradeable");
    const identityRegistry = await upgrades.deployProxy(
      IdentityRegistry,
      [],
      { initializer: "initialize" }
    );
    await identityRegistry.waitForDeployment();
    const identityAddr = await identityRegistry.getAddress();
    const identityImpl = await upgrades.erc1967.getImplementationAddress(identityAddr);

    deploymentResult.contracts.IdentityRegistry = {
      address: identityAddr,
      implementation: identityImpl,
      transactionHash: identityRegistry.deploymentTransaction()?.hash || "",
      blockNumber: 0,
    };
    console.log(`   ✅ IdentityRegistry deployed to: ${identityAddr}`);
    console.log(`   📋 Implementation: ${identityImpl}`);
    console.log();

    // 3. Deploy ReputationRegistry (Upgradeable)
    console.log("3️⃣  Deploying ReputationRegistry (Upgradeable)...");
    const ReputationRegistry = await ethers.getContractFactory("ReputationRegistryUpgradeable");
    const reputationRegistry = await upgrades.deployProxy(
      ReputationRegistry,
      [],
      { initializer: "initialize" }
    );
    await reputationRegistry.waitForDeployment();
    const reputationAddr = await reputationRegistry.getAddress();
    const reputationImpl = await upgrades.erc1967.getImplementationAddress(reputationAddr);

    deploymentResult.contracts.ReputationRegistry = {
      address: reputationAddr,
      implementation: reputationImpl,
      transactionHash: reputationRegistry.deploymentTransaction()?.hash || "",
      blockNumber: 0,
    };
    console.log(`   ✅ ReputationRegistry deployed to: ${reputationAddr}`);
    console.log(`   📋 Implementation: ${reputationImpl}`);
    console.log();

    // 4. Deploy ValidationRegistry (Upgradeable)
    console.log("4️⃣  Deploying ValidationRegistry (Upgradeable)...");
    const ValidationRegistry = await ethers.getContractFactory("ValidationRegistryUpgradeable");
    const validationRegistry = await upgrades.deployProxy(
      ValidationRegistry,
      [identityAddr, reputationAddr],
      { initializer: "initialize" }
    );
    await validationRegistry.waitForDeployment();
    const validationAddr = await validationRegistry.getAddress();
    const validationImpl = await upgrades.erc1967.getImplementationAddress(validationAddr);

    deploymentResult.contracts.ValidationRegistry = {
      address: validationAddr,
      implementation: validationImpl,
      transactionHash: validationRegistry.deploymentTransaction()?.hash || "",
      blockNumber: 0,
    };
    console.log(`   ✅ ValidationRegistry deployed to: ${validationAddr}`);
    console.log(`   📋 Implementation: ${validationImpl}`);
    console.log();

    // 5. Deploy BonaFide (BANKON Integration)
    console.log("5️⃣  Deploying BonaFide (BANKON Integration)...");
    const BonaFide = await ethers.getContractFactory("BonaFide");
    const bonaFide = await BonaFide.deploy(identityAddr, validationAddr);
    await bonaFide.waitForDeployment();
    const bonaFideAddr = await bonaFide.getAddress();

    deploymentResult.contracts.BonaFide = {
      address: bonaFideAddr,
      transactionHash: bonaFide.deploymentTransaction()?.hash || "",
      blockNumber: 0,
    };
    console.log(`   ✅ BonaFide deployed to: ${bonaFideAddr}`);
    console.log();

    // 6. ERC-8004 System Integration Complete
    console.log("6️⃣  ERC-8004 System Integration Complete!");
    console.log("   ✅ All contracts deployed and ready for use");
    console.log();

    // 7. Save deployment results
    console.log("7️⃣  Saving deployment configuration...");
    const deploymentPath = path.join(__dirname, `deployment-${network.chainId}.json`);
    fs.writeFileSync(deploymentPath, JSON.stringify(deploymentResult, null, 2));
    console.log(`   ✅ Deployment saved to: ${deploymentPath}`);

    // Create environment file for frontend integration
    const envContent = `# AgenticPlace ERC-8004 Contract Addresses (Chain: ${network.chainId})
NEXT_PUBLIC_CHAIN_ID=${network.chainId}
NEXT_PUBLIC_NETWORK_NAME=${network.name}

# Core ERC-8004 Contracts
NEXT_PUBLIC_IDENTITY_REGISTRY=${identityAddr}
NEXT_PUBLIC_REPUTATION_REGISTRY=${reputationAddr}
NEXT_PUBLIC_VALIDATION_REGISTRY=${validationAddr}

# BANKON Integration
NEXT_PUBLIC_BONAFIDE_CONTRACT=${bonaFideAddr}

# Utilities
NEXT_PUBLIC_SINGLETON_FACTORY=${singletonAddr}

# Deployed by: ${deployer.address}
# Deployed at: ${deploymentResult.deployedAt}
`;

    fs.writeFileSync(path.join(__dirname, '../.env.contracts'), envContent);
    console.log("   ✅ Environment file created: .env.contracts");

    console.log();
    console.log("🎉 DEPLOYMENT COMPLETE!");
    console.log("========================");
    console.log("📋 Contract Summary:");
    console.log(`   • IdentityRegistry: ${identityAddr}`);
    console.log(`   • ReputationRegistry: ${reputationAddr}`);
    console.log(`   • ValidationRegistry: ${validationAddr}`);
    console.log(`   • BonaFide (BANKON): ${bonaFideAddr}`);
    console.log(`   • SingletonFactory: ${singletonAddr}`);
    console.log();
    console.log("🔗 Integration Points:");
    console.log("   • All contracts are interconnected and configured");
    console.log("   • BANKON integration ready via BonaFide contract");
    console.log("   • ERC-8004 agent registration system operational");
    console.log();
    console.log(`🌐 Verify contracts on ${network.name} block explorer`);

    return deploymentResult;

  } catch (error) {
    console.error("❌ Deployment failed:", error);
    throw error;
  }
}

// Handle script execution
if (require.main === module) {
  main()
    .then((result) => {
      console.log("✅ Deployment script completed successfully");
      process.exit(0);
    })
    .catch((error) => {
      console.error("💥 Deployment script failed:", error);
      process.exit(1);
    });
}

module.exports = main;