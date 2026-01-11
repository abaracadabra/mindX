# DAIO Contracts Documentation

Technical documentation for DAIO smart contracts, designed for developers, agents, and UI integration.

## Folder Structure

```
docs/
├── README.md                    # This file
├── contracts/                   # Contract-specific documentation
│   ├── DAIO_Constitution.md
│   ├── SoulBadger.md
│   ├── IDNFT.md
│   ├── KnowledgeHierarchyDAIO.md
│   ├── AgentFactory.md
│   └── Treasury.md
├── integration/                 # UI/Web3 integration guides
│   ├── viem-setup.md
│   ├── react-hooks.md
│   └── wallet-connection.md
└── abis/                        # Contract ABIs for frontend
    ├── index.ts
    ├── DAIO_Constitution.json
    ├── SoulBadger.json
    ├── IDNFT.json
    ├── KnowledgeHierarchyDAIO.json
    ├── AgentFactory.json
    └── Treasury.json
```

## Quick Start

### Install Dependencies

```bash
npm install viem @wagmi/core @wagmi/connectors
```

### Basic Setup (viem)

```typescript
import { createPublicClient, createWalletClient, http } from 'viem';
import { mainnet } from 'viem/chains';
import { DAIO_Constitution_ABI } from './abis';

// Read-only client
const publicClient = createPublicClient({
  chain: mainnet,
  transport: http()
});

// Wallet client (for transactions)
const walletClient = createWalletClient({
  chain: mainnet,
  transport: http()
});
```

## Contract Overview

| Contract | Purpose | Key Functions |
|----------|---------|---------------|
| [DAIO_Constitution](./contracts/DAIO_Constitution.md) | Constitutional governance | `validateAction`, `checkDiversificationLimit`, `pauseSystem` |
| [SoulBadger](./contracts/SoulBadger.md) | Soulbound credentials | `mintSoulboundBadge`, `mintAgentCredentialBadge`, `revokeBadge` |
| [IDNFT](./contracts/IDNFT.md) | Agent identity NFTs | `mintAgentIdentity`, `attachTHOT`, `issueCredential` |
| [KnowledgeHierarchyDAIO](./contracts/KnowledgeHierarchyDAIO.md) | Governance & voting | `registerAgent`, `createProposal`, `agentVote` |
| [AgentFactory](./contracts/AgentFactory.md) | Agent creation | `createAgent`, `destroyAgent`, `reactivateAgent` |
| [Treasury](./contracts/Treasury.md) | Multi-sig treasury | `deposit`, `distributeReward`, `submitTransaction` |

## Contract Addresses

```typescript
// Testnet (ARC)
export const TESTNET_ADDRESSES = {
  DAIO_Constitution: '0x...',
  SoulBadger: '0x...',
  IDNFT: '0x...',
  KnowledgeHierarchyDAIO: '0x...',
  AgentFactory: '0x...',
  Treasury: '0x...',
} as const;

// Mainnet (after deployment)
export const MAINNET_ADDRESSES = {
  // To be populated after mainnet deployment
} as const;
```

## Integration Patterns

### 1. Reading Contract State

```typescript
import { publicClient } from './client';
import { DAIO_Constitution_ABI } from './abis';

const checkDiversification = async (constitutionAddress: `0x${string}`) => {
  const isCompliant = await publicClient.readContract({
    address: constitutionAddress,
    abi: DAIO_Constitution_ABI,
    functionName: 'checkDiversificationLimit',
  });
  return isCompliant;
};
```

### 2. Writing Transactions

```typescript
import { walletClient, publicClient } from './client';
import { Treasury_ABI } from './abis';

const depositToTreasury = async (
  treasuryAddress: `0x${string}`,
  amount: bigint
) => {
  const hash = await walletClient.writeContract({
    address: treasuryAddress,
    abi: Treasury_ABI,
    functionName: 'deposit',
    value: amount,
  });

  const receipt = await publicClient.waitForTransactionReceipt({ hash });
  return receipt;
};
```

### 3. Event Listening

```typescript
import { publicClient } from './client';
import { Treasury_ABI } from './abis';

const watchDeposits = (treasuryAddress: `0x${string}`) => {
  return publicClient.watchContractEvent({
    address: treasuryAddress,
    abi: Treasury_ABI,
    eventName: 'Deposit',
    onLogs: (logs) => {
      console.log('New deposit:', logs);
    },
  });
};
```

## For Agents

### Contract Interaction Pattern

Agents should use the following pattern when interacting with DAIO contracts:

```typescript
interface AgentContractCall {
  contract: string;           // Contract name
  function: string;           // Function to call
  args: unknown[];            // Function arguments
  value?: bigint;             // ETH value (if payable)
  gasLimit?: bigint;          // Optional gas limit
}

// Example: Agent registering itself
const registerAgentCall: AgentContractCall = {
  contract: 'KnowledgeHierarchyDAIO',
  function: 'registerAgent',
  args: [agentAddress, 75, 0], // address, knowledgeLevel, domain
};
```

### Key Operations for Agents

1. **Identity Management** (IDNFT)
   - Get identity: `getAgentIdentity(tokenId)`
   - Update persona: `updatePersona(tokenId, prompt, persona)`

2. **Governance Participation** (KnowledgeHierarchyDAIO)
   - Vote on proposals: `agentVote(proposalId, support)`
   - Check voting power: `getAgent(agentAddress)`

3. **Treasury Operations** (Treasury)
   - Check rewards: `getBalance()`
   - Claim rewards: Via governance proposal

## TypeScript Support

All ABIs include full TypeScript types. Import from the `abis` folder:

```typescript
import {
  DAIO_Constitution_ABI,
  SoulBadger_ABI,
  IDNFT_ABI,
  KnowledgeHierarchyDAIO_ABI,
  AgentFactory_ABI,
  Treasury_ABI,
} from './abis';
```

## Resources

- [viem Documentation](https://viem.sh)
- [wagmi Documentation](https://wagmi.sh)
- [Foundry Book](https://book.getfoundry.sh)
- [OpenZeppelin Contracts](https://docs.openzeppelin.com/contracts)
