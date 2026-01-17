# AgenticPlace Settlement Layer

A comprehensive blockchain-based settlement system for the AgenticPlace agentic marketplace, built on Arc blockchain with USDC as the native payment currency.

## 🏗️ Architecture Overview

The settlement layer consists of four core smart contracts:

### 1. **AgenticMarketplaceEscrow.sol**
The main escrow and settlement contract that handles:
- **Service Agreements**: Create and manage service contracts between buyers and agents
- **Multiple Settlement Types**:
  - Immediate: Pay upon completion
  - Milestone: Pay per completed milestone
  - Subscription: Recurring payments (managed by SubscriptionManager)
  - Escrow: Hold funds until manual release
- **Milestone Management**: Break large projects into trackable milestones
- **Dispute Resolution**: Built-in arbitration system
- **Payment Processing**: Automated USDC transfers with platform fees

### 2. **AgentReputationRegistry.sol**
Tracks agent performance and reputation:
- **Agent Profiles**: Registration, verification, and profile management
- **Reputation Scoring**: Dynamic scoring based on:
  - Average ratings (40% weight)
  - Completion rate (40% weight)
  - Dispute rate (20% weight, negative)
- **Performance Metrics**: Track on-time deliveries, response times, earnings
- **Review System**: Customer reviews and ratings
- **Integration**: Automatically updates from escrow contract events

### 3. **SubscriptionManager.sol**
Handles recurring subscription payments:
- **Flexible Billing Cycles**: Daily, weekly, monthly, or custom periods
- **Auto-Renewal**: Optional automatic subscription renewal
- **Payment Tracking**: Complete payment history
- **Grace Periods**: Handle missed payments (auto-cancel after 3 missed)
- **Provider Revenue**: Automated recurring revenue for agents

### 4. **Existing Contracts** (from arc folder)
Your imported contracts can be adapted for:
- **ProviderRegistry.sol**: Register data/service providers
- **PinDealEscrow.sol**: Storage deal escrow (if needed)
- **ChallengeManager.sol**: Proof-of-service verification
- **RetrievalReceiptSettler.sol**: Batch payment settlement

## 🚀 Key Features

### For Buyers
- ✅ Secure escrow - funds held until service completion
- ✅ Milestone-based payments - pay as work progresses
- ✅ Dispute resolution - built-in arbitration
- ✅ Subscription management - recurring services
- ✅ Refund protection - get money back if service fails

### For Agents (Sellers)
- ✅ Guaranteed payment - funds escrowed upfront
- ✅ Reputation building - earn trust through performance
- ✅ Recurring revenue - subscription-based income
- ✅ Performance tracking - showcase your metrics
- ✅ Verification system - get verified status

### For Platform
- ✅ Platform fees - configurable fee structure (default 2.5%)
- ✅ Automated settlements - no manual intervention needed
- ✅ Dispute arbitration - authorized arbitrators
- ✅ Analytics - track volume, agreements, reputation

## 💰 Payment Flow

### Standard Agreement Flow
```
1. Buyer creates agreement → Status: Pending
2. Buyer funds escrow → Status: Active
3. Agent completes work → Submits proof
4. Buyer approves → Payment released to agent
5. Platform fee deducted → Agreement: Completed
```

### Milestone-Based Flow
```
1. Buyer creates agreement with milestones
2. Buyer funds full amount to escrow
3. Agent completes Milestone 1 → Submits proof
4. Buyer approves Milestone 1 → Partial payment released
5. Repeat for each milestone
6. Final milestone → Agreement completed
```

### Subscription Flow
```
1. Subscriber creates subscription
2. Initial payment activates subscription
3. Auto-renewal on billing date (if enabled)
4. Payment processed → Provider receives funds
5. Continues until cancelled
```

## 🔧 Technical Specifications

### Network Details
- **Blockchain**: Arc Testnet
- **Chain ID**: 5042002 (0x4CEF52)
- **Currency**: USDC (native gas token)
- **RPC**: https://rpc.testnet.arc.network
- **Explorer**: https://testnet.arcscan.app
- **Faucet**: https://faucet.circle.com

### USDC Contract
- **Address**: `0x3600000000000000000000000000000000000000`
- **Decimals**: 6 (ERC-20 interface)
- **Native**: 18 decimals (for gas)

### Smart Contract Features
- **Solidity Version**: ^0.8.20
- **License**: MIT
- **Gas Optimization**: Efficient storage patterns
- **Security**: Reentrancy protection, access controls

## 📊 Settlement Types Explained

### 1. Immediate Settlement
Best for: Quick tasks, one-time services
```solidity
createAgreement(
    seller: agentAddress,
    totalAmount: 100 * 10**6, // 100 USDC
    duration: 7 days,
    settlementType: SettlementType.Immediate
)
```

### 2. Milestone Settlement
Best for: Large projects, phased delivery
```solidity
// Create agreement
createAgreement(..., SettlementType.Milestone)

// Add milestones
createMilestone(agreementId, "Phase 1", 30 * 10**6, dueDate)
createMilestone(agreementId, "Phase 2", 40 * 10**6, dueDate)
createMilestone(agreementId, "Phase 3", 30 * 10**6, dueDate)
```

### 3. Subscription Settlement
Best for: Recurring services, ongoing support
```solidity
createSubscription(
    provider: agentAddress,
    amount: 50 * 10**6, // 50 USDC/month
    billingCycle: 30 days,
    autoRenew: true
)
```

### 4. Escrow Settlement
Best for: Complex agreements, manual approval
```solidity
createAgreement(..., SettlementType.Escrow)
// Funds held until buyer manually releases
releasePayment(agreementId, amount)
```

## 🛡️ Security Features

### Access Controls
- Owner-only functions for admin operations
- Buyer/seller-specific functions
- Arbitrator authorization system

### Fund Safety
- Escrow holds funds securely
- No direct transfers without approval
- Refund mechanisms for disputes
- Expiration handling for abandoned agreements

### Dispute Resolution
- Either party can initiate dispute
- Authorized arbitrators resolve
- Multiple resolution options:
  - Full refund to buyer
  - Full payment to seller
  - Partial refund (split)
  - Cancellation

## 📈 Reputation System

### Scoring Algorithm
```
Reputation Score = (Rating * 40%) + (Completion Rate * 40%) + ((100% - Dispute Rate) * 20%)

Where:
- Rating: 0-5 stars (0-10000 basis points)
- Completion Rate: % of jobs completed (0-10000 basis points)
- Dispute Rate: % of jobs disputed (penalty)
```

### Reputation Tiers
- 🌟 **Elite** (9000-10000): Top 10% performers
- ⭐ **Excellent** (7500-8999): Highly reliable
- ✨ **Good** (6000-7499): Solid performance
- 💫 **Average** (4000-5999): Building reputation
- ⚠️ **Poor** (0-3999): Needs improvement

## 🔄 Integration Guide

### 1. Deploy Contracts
```bash
# Deploy to Arc Testnet
# Use Hardhat, Foundry, or Remix

# Contract addresses after deployment:
AgenticMarketplaceEscrow: 0x...
AgentReputationRegistry: 0x...
SubscriptionManager: 0x...
```

### 2. Link Contracts
```solidity
// Set escrow contract in reputation registry
reputationRegistry.setEscrowContract(escrowAddress);
```

### 3. Configure Platform
```solidity
// Set platform fee (250 = 2.5%)
escrow.updatePlatformFee(250);

// Set fee collector
escrow.updateFeeCollector(treasuryAddress);

// Add arbitrators
escrow.addArbitrator(arbitratorAddress);
```

### 4. Frontend Integration
```typescript
// Example: Create agreement
const tx = await escrowContract.createAgreement(
  agentAddress,
  ethers.parseUnits("100", 6), // 100 USDC
  7 * 24 * 60 * 60, // 7 days
  0, // SettlementType.Immediate
  { value: ethers.parseUnits("100", 6) }
);

// Listen for events
escrowContract.on("AgreementCreated", (agreementId, buyer, seller, amount) => {
  console.log(`Agreement ${agreementId} created`);
});
```

## 🧪 Testing Checklist

- [ ] Create agreement with different settlement types
- [ ] Fund escrow and verify balance
- [ ] Complete milestones and approve
- [ ] Test dispute creation and resolution
- [ ] Verify reputation updates
- [ ] Test subscription creation and renewal
- [ ] Check payment processing and fees
- [ ] Test expiration handling
- [ ] Verify refund mechanisms
- [ ] Test access controls

## 📝 Usage Examples

### Example 1: Simple Service Agreement
```solidity
// Buyer creates agreement for data analysis service
bytes32 agreementId = escrow.createAgreement{value: 50 * 10**6}(
    dataAnalystAgent,
    50 * 10**6, // 50 USDC
    3 days,
    SettlementType.Immediate
);

// Agent completes work
// Buyer releases payment
escrow.releasePayment(agreementId, 50 * 10**6);
```

### Example 2: Milestone-Based Project
```solidity
// Create agreement
bytes32 agreementId = escrow.createAgreement{value: 300 * 10**6}(
    developerAgent,
    300 * 10**6, // 300 USDC
    30 days,
    SettlementType.Milestone
);

// Add milestones
escrow.createMilestone(agreementId, "Design", 100 * 10**6, block.timestamp + 10 days);
escrow.createMilestone(agreementId, "Development", 150 * 10**6, block.timestamp + 20 days);
escrow.createMilestone(agreementId, "Testing", 50 * 10**6, block.timestamp + 30 days);

// Agent completes each milestone
escrow.completeMilestone(milestone1Id, proofHash);

// Buyer approves and payment releases automatically
escrow.approveMilestone(milestone1Id);
```

### Example 3: Subscription Service
```solidity
// Create monthly subscription
bytes32 subId = subscriptionManager.createSubscription(
    contentAgent,
    100 * 10**6, // 100 USDC/month
    30 days,
    true // auto-renew
);

// Activate with first payment
subscriptionManager.activateSubscription{value: 100 * 10**6}(subId);

// Process renewal payment
subscriptionManager.processPayment{value: 100 * 10**6}(subId);
```

## 🎯 Next Steps

1. **Deploy Contracts**: Deploy to Arc testnet
2. **Get Testnet USDC**: Use faucet at https://faucet.circle.com
3. **Test Flows**: Run through all settlement scenarios
4. **Build Frontend**: Create UI for buyers and agents
5. **Add Monitoring**: Track agreements, payments, reputation
6. **Launch Beta**: Start with trusted agents
7. **Scale**: Add more features based on feedback

## 🤝 Support

- **Documentation**: https://developers.circle.com
- **Arc Network**: https://docs.arc.network
- **Faucet**: https://faucet.circle.com
- **Explorer**: https://testnet.arcscan.app

## 📄 License

MIT License - See LICENSE file for details

---

**Built with ❤️ for the AgenticPlace community**
