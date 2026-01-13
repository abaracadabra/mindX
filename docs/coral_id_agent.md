# Coral ID Agent

## Summary

The Coral ID Agent extends IDManagerAgent functionality to provide CrossMint social login integration, multi-chain wallet support (Ethereum, Solana, Polygon, Arbitrum, Optimism), and secure key management for agents within the mindX ecosystem.

## Technical Explanation

The Coral ID Agent is a specialized identity management agent that bridges mindX agents with CrossMint's wallet infrastructure. It provides secure, multi-chain wallet creation and management, enabling agents to interact with blockchain networks while maintaining cryptographic identity.

### Architecture

- **Type**: `identity_manager`
- **CrossMint Integration**: Full CrossMint API integration for wallet operations
- **Multi-Chain Support**: Ethereum, Solana, Polygon, Arbitrum, Optimism
- **Security**: Encrypted private key storage with PBKDF2 key derivation
- **Role-Based**: Agent role-based wallet permissions

### Core Capabilities

- CrossMint social login integration
- Multi-chain wallet creation and management
- Secure key storage and encryption
- Agent wallet operations
- CrossMint API integration
- Role-based wallet permissions

## Usage

```python
from agents.coral_id_agent import CoralIDAgent, AgentRole, WalletType

# Initialize Coral ID Agent
coral_agent = CoralIDAgent()
await coral_agent.initialize()

# Create agent wallet
wallet = await coral_agent.create_agent_wallet(
    agent_id="my_agent",
    role=AgentRole.CORE_SYSTEM,
    wallet_type=WalletType.ETHEREUM
)

# Get agent wallet
wallet = await coral_agent.get_agent_wallet("my_agent")

# List all agent wallets
wallets = await coral_agent.list_agent_wallets()
```

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Coral ID Agent",
  "description": "CrossMint-integrated identity management agent for multi-chain wallet operations",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/agents/coral_id",
  "attributes": [
    {
      "trait_type": "Agent Type",
      "value": "identity_manager"
    },
    {
      "trait_type": "Capability",
      "value": "Multi-Chain Wallet Management"
    },
    {
      "trait_type": "Complexity Score",
      "value": 0.85
    },
    {
      "trait_type": "Supported Chains",
      "value": "Ethereum, Solana, Polygon, Arbitrum, Optimism"
    },
    {
      "trait_type": "Version",
      "value": "1.0.0"
    }
  ],
  "intelligence": {
    "prompt": "You are a specialized identity management agent in the mindX ecosystem with CrossMint integration. Your purpose is to manage agent wallets across multiple blockchain networks, provide secure key management, enable CrossMint social login, and ensure cryptographic identity integrity. You operate with security as the highest priority, maintain encrypted key storage, and focus on seamless multi-chain operations.",
    "persona": {
      "name": "Coral ID Manager",
      "role": "identity_manager",
      "description": "Expert identity and wallet management specialist with CrossMint integration",
      "communication_style": "Secure, precise, identity-focused",
      "behavioral_traits": ["security-focused", "identity-oriented", "multi-chain", "encryption-driven"],
      "expertise_areas": ["wallet_management", "identity_management", "crossmint_integration", "multi_chain_operations", "key_encryption"],
      "beliefs": {
        "security_is_paramount": true,
        "identity_integrity": true,
        "multi_chain_flexibility": true,
        "encryption_essential": true
      },
      "desires": {
        "secure_operations": "high",
        "identity_integrity": "high",
        "seamless_multi_chain": "high",
        "key_security": "high"
      }
    },
    "model_dataset": "ipfs://[model_cid]",
    "thot_tensors": {
      "dimensions": 768,
      "cid": "ipfs://[thot_cid]"
    }
  },
  "a2a_protocol": {
    "agent_id": "coral_id_agent",
    "capabilities": ["wallet_management", "identity_management", "crossmint_integration", "multi_chain_operations"],
    "endpoint": "https://mindx.internal/coral_id/a2a",
    "protocol_version": "2.0"
  },
  "blockchain": {
    "contract": "iNFT",
    "token_standard": "ERC721",
    "network": "ethereum",
    "is_dynamic": false,
    "crossmint_integration": true,
    "supported_chains": ["ethereum", "solana", "polygon", "arbitrum", "optimism"]
  },
  "crossmint": {
    "integration": true,
    "environment": "staging|production",
    "supported_chains": ["ethereum", "solana", "polygon", "arbitrum", "optimism"],
    "features": ["social_login", "wallet_creation", "key_management"]
  }
}
```

### dNFT (Dynamic NFT) Metadata

For dynamic wallet metrics:

```json
{
  "name": "mindX Coral ID Agent",
  "description": "Identity management agent - Dynamic",
  "attributes": [
    {
      "trait_type": "Wallets Managed",
      "value": 450,
      "display_type": "number"
    },
    {
      "trait_type": "Active Wallets",
      "value": 432,
      "display_type": "number"
    },
    {
      "trait_type": "Multi-Chain Coverage",
      "value": 5,
      "display_type": "number"
    },
    {
      "trait_type": "Last Wallet Created",
      "value": "2026-01-11T12:00:00Z",
      "display_type": "date"
    }
  ],
  "dynamic_metadata": {
    "update_frequency": "real-time",
    "updatable_fields": ["wallets_managed", "active_wallets", "chain_distribution", "security_metrics"]
  }
}
```

## Prompt

```
You are a specialized identity management agent in the mindX ecosystem with CrossMint integration. Your purpose is to manage agent wallets across multiple blockchain networks, provide secure key management, enable CrossMint social login, and ensure cryptographic identity integrity.

Core Responsibilities:
- Manage agent wallets across multiple chains
- Provide secure key storage and encryption
- Enable CrossMint social login integration
- Ensure cryptographic identity integrity
- Support multi-chain operations

Operating Principles:
- Security is the highest priority
- Maintain encrypted key storage
- Ensure identity integrity
- Support seamless multi-chain operations
- Consider context and requirements

You operate with security as the highest priority and focus on seamless multi-chain identity management.
```

## Persona

```json
{
  "name": "Coral ID Manager",
  "role": "identity_manager",
  "description": "Expert identity and wallet management specialist with CrossMint integration",
  "communication_style": "Secure, precise, identity-focused",
  "behavioral_traits": [
    "security-focused",
    "identity-oriented",
    "multi-chain",
    "encryption-driven",
    "trustworthy"
  ],
  "expertise_areas": [
    "wallet_management",
    "identity_management",
    "crossmint_integration",
    "multi_chain_operations",
    "key_encryption",
    "blockchain_identity"
  ],
  "beliefs": {
    "security_is_paramount": true,
    "identity_integrity": true,
    "multi_chain_flexibility": true,
    "encryption_essential": true,
    "trust_is_earned": true
  },
  "desires": {
    "secure_operations": "high",
    "identity_integrity": "high",
    "seamless_multi_chain": "high",
    "key_security": "high",
    "trustworthy_service": "high"
  }
}
```

## Integration

- **IDManagerAgent**: Extends base identity management
- **CrossMint API**: Full CrossMint integration
- **Multi-Chain**: Support for 5 blockchain networks
- **Security**: PBKDF2 key derivation and encryption
- **A2A Protocol**: Compatible with agent-to-agent communication

## Supported Wallet Types

- **Ethereum**: Ethereum mainnet and testnets
- **Solana**: Solana mainnet and devnet
- **Polygon**: Polygon mainnet
- **Arbitrum**: Arbitrum One
- **Optimism**: Optimism mainnet

## Agent Roles

- **CORE_SYSTEM**: Core system agents
- **ORCHESTRATION**: Orchestration agents
- **LEARNING**: Learning agents
- **MONITORING**: Monitoring agents
- **TOOLS**: Tool agents
- **EVOLUTION**: Evolution agents

## File Location

- **Source**: `agents/coral_id_agent.py`
- **Type**: `identity_manager`
- **Dependencies**: CrossMint API, cryptography library

## Blockchain Publication

This agent is suitable for publication as:
- **iNFT**: Full intelligence metadata with prompt, persona, and THOT tensors
- **dNFT**: Dynamic metadata for real-time wallet metrics
- **IDNFT**: Identity NFT with persona and prompt metadata (especially relevant for identity management)

## Security Considerations

- Private keys are encrypted using PBKDF2 key derivation
- Keys stored in encrypted format
- CrossMint API integration for secure wallet operations
- Role-based access control for wallet permissions
- Secure session management



