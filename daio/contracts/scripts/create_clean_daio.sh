#!/bin/bash
# Create clean DAIO repository without mindX duplication

echo "🏗️  Creating clean DAIO repository structure..."

# Create temporary directory for clean DAIO
CLEAN_DAIO_DIR="/tmp/clean_daio"
rm -rf "$CLEAN_DAIO_DIR"
mkdir -p "$CLEAN_DAIO_DIR"

# Navigate to clean directory
cd "$CLEAN_DAIO_DIR"

echo "📁 Setting up directory structure..."

# Create core directory structure
mkdir -p {contracts,scripts,docs,test,deployment}

# Create contract subdirectories
mkdir -p contracts/{daio,examples,interfaces}
mkdir -p contracts/daio/{constitution,governance,treasury,identity,settings}

echo "📋 Copying core DAIO contracts..."

# Source directory (adjust path as needed)
SOURCE_DIR="/home/hacker/mindX/daio/contracts"

# Copy core DAIO contracts ONLY
cp "$SOURCE_DIR/DAIO_Core.sol" contracts/
cp "$SOURCE_DIR/deployment/DAIO_DeploymentKit.sol" contracts/deployment/
cp "$SOURCE_DIR/deployment/README.md" ./

# Copy daio/ directory contracts
cp -r "$SOURCE_DIR/daio/constitution"/* contracts/daio/constitution/
cp -r "$SOURCE_DIR/daio/governance"/* contracts/daio/governance/
cp -r "$SOURCE_DIR/daio/treasury"/* contracts/daio/treasury/
cp -r "$SOURCE_DIR/daio/identity"/* contracts/daio/identity/
cp -r "$SOURCE_DIR/daio/settings"/* contracts/daio/settings/

# Copy examples (DAIO-specific only)
cp "$SOURCE_DIR/examples/ConstitutionalParameterExample.sol" contracts/examples/

# Copy Foundry configuration
cp "$SOURCE_DIR/foundry.toml" ./

echo "⚙️  Setting up Foundry configuration..."

# Create clean foundry.toml focused on DAIO
cat > foundry.toml << 'EOF'
[profile.default]
src = "contracts"
out = "out"
libs = ["lib"]
remappings = [
    "@openzeppelin/=lib/openzeppelin-contracts/",
    "forge-std/=lib/forge-std/src/"
]
solc = "0.8.24"
evm_version = "shanghai"
optimizer = true
optimizer_runs = 200
via_ir = true

[profile.production]
optimizer_runs = 1000
via_ir = true

[profile.testing]
src = "contracts"
test = "test"
optimizer = false
EOF

echo "📖 Creating documentation..."

# Create main README
cat > README.md << 'EOF'
# DAIO - Decentralized Autonomous Intelligence Organization

**The definitive modular governance foundation for decentralized organizations.**

## 🎯 Quick Start

```bash
# Install Foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Clone and setup
git clone https://github.com/Professor-Codephreak/DAIO.git
cd DAIO
forge install

# Build
forge build

# Deploy minimal DAIO
forge script script/DeployMinimal.s.sol --broadcast
```

## 🏗️ Architecture

- **Core**: CEO + Seven Soldiers executive governance
- **Constitution**: Configurable 15% defaults for risk management
- **Treasury**: Multi-project treasury with automatic tithe collection
- **Extensions**: Modular marketplace, identity, and analytics

## 📚 Documentation

See [deployment/README.md](./deployment/README.md) for complete documentation.

## 🛡️ Executive Structure

| Role | Weight | Powers |
|------|---------|---------|
| CEO | Emergency Override | 7-day emergency actions |
| CISO | 1.2x | Security veto power |
| CRO | 1.2x | Risk veto power |
| CFO/CPO/COO/CTO | 1.0x | Functional governance |
| CLO | 0.8x | Legal guidance |

**Consensus**: 66.67% supermajority for normal decisions, risk-adjusted thresholds for constitutional changes.
EOF

# Create gitignore
cat > .gitignore << 'EOF'
# Foundry
cache/
out/
broadcast/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Environment
.env
.env.local

# Dependencies
node_modules/
lib/

# Logs
*.log
EOF

echo "🔧 Creating deployment scripts..."

# Create deployment script directory
mkdir -p script

# Minimal deployment script
cat > script/DeployMinimal.s.sol << 'EOF'
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../contracts/DAIO_Core.sol";
import "../contracts/deployment/DAIO_DeploymentKit.sol";

contract DeployMinimal is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        vm.startBroadcast(deployerPrivateKey);

        // Deploy deployment kit
        DAIO_DeploymentKit kit = new DAIO_DeploymentKit();

        console.log("DAIO_DeploymentKit deployed to:", address(kit));
        console.log("Use this to deploy DAIO instances");

        vm.stopBroadcast();
    }
}
EOF

# Full deployment script
cat > script/DeployEnterprise.s.sol << 'EOF'
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../contracts/deployment/DAIO_DeploymentKit.sol";

contract DeployEnterprise is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address chairman = vm.envAddress("CHAIRMAN_ADDRESS");
        address ceo = vm.envAddress("CEO_ADDRESS");

        vm.startBroadcast(deployerPrivateKey);

        DAIO_DeploymentKit kit = new DAIO_DeploymentKit();

        address daio = kit.deployDAIO(
            DAIO_DeploymentKit.DeploymentTemplate.ENTERPRISE,
            "Enterprise DAIO",
            chairman,
            ceo,
            new string[](0)
        );

        console.log("Enterprise DAIO deployed to:", daio);

        vm.stopBroadcast();
    }
}
EOF

echo "🧪 Creating test structure..."

# Create basic test
cat > test/DAIOCore.t.sol << 'EOF'
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../contracts/DAIO_Core.sol";

contract DAIOCoreTest is Test {
    DAIO_Core public daioCore;
    address public chairman = address(0x1);
    address public ceo = address(0x2);

    function setUp() public {
        daioCore = new DAIO_Core();
    }

    function test_Deploy() public {
        bool success = daioCore.deployDAIOCore(
            "Test DAIO",
            chairman,
            ceo,
            keccak256("test")
        );

        assertTrue(success);

        (,DeploymentInfo memory info,,) = daioCore.getDAIOStatus();
        assertTrue(info.initialized);
        assertEq(info.deployer, address(this));
    }
}
EOF

echo "📦 Creating package configuration..."

# Create package.json for metadata
cat > package.json << 'EOF'
{
  "name": "daio-contracts",
  "version": "1.0.0",
  "description": "Decentralized Autonomous Intelligence Organization - Modular governance foundation",
  "keywords": ["governance", "dao", "solidity", "foundry", "executive", "constitution"],
  "author": "Professor-Codephreak",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/Professor-Codephreak/DAIO.git"
  },
  "scripts": {
    "build": "forge build",
    "test": "forge test",
    "deploy:minimal": "forge script script/DeployMinimal.s.sol --broadcast",
    "deploy:enterprise": "forge script script/DeployEnterprise.s.sol --broadcast"
  }
}
EOF

echo "📊 Creating contracts overview..."

# Create contracts documentation
cat > docs/CONTRACTS.md << 'EOF'
# DAIO Smart Contracts

## Core Contracts

| Contract | Purpose | Size |
|----------|---------|------|
| `DAIO_Core.sol` | Main deployment orchestrator | 20KB |
| `ExecutiveGovernance.sol` | CEO + Seven Soldiers governance | 20KB |
| `ExecutiveRoles.sol` | Role management & weighted voting | 14KB |
| `WeightedVotingEngine.sol` | Consensus calculation engine | 16KB |
| `EmergencyTimelock.sol` | CEO emergency powers | 15KB |
| `DAIO_Constitution_Enhanced.sol` | Configurable constitutional parameters | 16KB |
| `ConstitutionalParameterManager.sol` | Risk-based parameter management | 18KB |

## Extension Contracts

Extensions are modular add-ons that extend DAIO's core functionality:

- **Marketplace**: THOT trading, AgenticPlace
- **Identity**: Enhanced identity systems
- **Treasury**: Advanced treasury features
- **Analytics**: Governance metrics

## Deployment Size

- **Minimal**: ~15M gas (core only)
- **Standard**: ~25M gas (core + common extensions)
- **Enterprise**: ~45M gas (full feature set)
EOF

echo "✅ Clean DAIO repository created at: $CLEAN_DAIO_DIR"
echo ""
echo "📁 Directory structure:"
tree "$CLEAN_DAIO_DIR" -I 'lib|cache|out' || find "$CLEAN_DAIO_DIR" -type d | head -20
echo ""
echo "🚀 Next steps:"
echo "1. cd $CLEAN_DAIO_DIR"
echo "2. git init"
echo "3. forge install OpenZeppelin/openzeppelin-contracts"
echo "4. forge build"
echo "5. git add . && git commit -m 'Initial DAIO clean repository'"
echo "6. git remote add origin https://github.com/Professor-Codephreak/DAIO.git"
echo "7. git push origin main --force"
echo ""
echo "📊 Repository focuses solely on:"
echo "   ✅ Core DAIO .sol contracts"
echo "   ✅ Deployment and testing tools"
echo "   ✅ Documentation and examples"
echo "   ❌ No mindX duplication"
echo "   ❌ No external project dependencies"