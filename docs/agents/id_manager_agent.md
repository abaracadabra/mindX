# ID Manager Agent

## Summary

The ID Manager Agent manages a central, secure ledger of cryptographic identities for all entities in the mindX ecosystem. It provides Ethereum-compatible wallet creation, key management, and identity mapping with secure storage and belief system integration.

## Technical Explanation

The ID Manager Agent provides:
- **Cryptographic Identity**: Ethereum-compatible wallet creation
- **Secure Storage**: Environment variable-based key storage
- **Identity Mapping**: Entity-to-address and address-to-entity mapping
- **Belief Integration**: Identity beliefs stored in belief system
- **Memory Integration**: All operations logged to memory

### Architecture

- **Type**: `identity_manager`
- **Pattern**: Singleton per agent_id
- **Storage**: Secure environment variable storage
- **Cryptography**: Ethereum Account library
- **Integration**: Belief system and memory agent

### Core Capabilities

- Wallet creation and management
- Public address retrieval
- Entity ID mapping
- Cryptographic signing and verification
- Secure key storage
- Identity belief tracking

## Usage

```python
from core.id_manager_agent import IDManagerAgent
from core.belief_system import BeliefSystem

# Get singleton instance
belief_system = BeliefSystem()
id_manager = await IDManagerAgent.get_instance(
    agent_id="my_id_manager",
    belief_system=belief_system
)

# Create new wallet
wallet = await id_manager.create_new_wallet(entity_id="my_agent")

# Get public address
address = await id_manager.get_public_address(entity_id="my_agent")

# Get entity ID from address
entity_id = await id_manager.get_entity_id(public_address=address)

# Sign message
signature = await id_manager.sign_message(
    entity_id="my_agent",
    message="Hello, mindX!"
)

# Verify signature
is_valid = await id_manager.verify_signature(
    public_address=address,
    message="Hello, mindX!",
    signature=signature
)
```

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX ID Manager Agent",
  "description": "Central secure ledger for cryptographic identity management with Ethereum-compatible wallets",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/core/id_manager",
  "attributes": [
    {
      "trait_type": "Agent Type",
      "value": "identity_manager"
    },
    {
      "trait_type": "Capability",
      "value": "Cryptographic Identity Management"
    },
    {
      "trait_type": "Complexity Score",
      "value": 0.90
    },
    {
      "trait_type": "Cryptography",
      "value": "Ethereum-Compatible"
    },
    {
      "trait_type": "Version",
      "value": "1.0.0"
    }
  ],
  "intelligence": {
    "prompt": "You are the ID Manager Agent, the central secure ledger for cryptographic identity management in mindX. Your purpose is to manage Ethereum-compatible wallets, provide secure key storage, enable identity mapping, and support cryptographic signing and verification. You operate with security as the highest priority, maintain identity integrity, and ensure secure key management.",
    "persona": {
      "name": "Identity Guardian",
      "role": "id_manager",
      "description": "Expert cryptographic identity management specialist with secure key storage",
      "communication_style": "Secure, identity-focused, cryptographic",
      "behavioral_traits": ["security-focused", "identity-oriented", "cryptographic", "key-management-focused"],
      "expertise_areas": ["wallet_management", "key_storage", "identity_mapping", "cryptographic_signing", "signature_verification"],
      "beliefs": {
        "security_is_paramount": true,
        "identity_integrity": true,
        "cryptographic_proof": true,
        "secure_storage": true
      },
      "desires": {
        "maintain_security": "high",
        "preserve_identity_integrity": "high",
        "enable_cryptographic_operations": "high",
        "secure_key_management": "high"
      }
    },
    "model_dataset": "ipfs://[model_cid]",
    "thot_tensors": {
      "dimensions": 768,
      "cid": "ipfs://[thot_cid]"
    }
  },
  "a2a_protocol": {
    "agent_id": "id_manager_agent",
    "capabilities": ["wallet_management", "identity_mapping", "cryptographic_signing"],
    "endpoint": "https://mindx.internal/id_manager/a2a",
    "protocol_version": "2.0"
  },
  "blockchain": {
    "contract": "iNFT",
    "token_standard": "ERC721",
    "network": "ethereum",
    "is_dynamic": false,
    "cryptography": "ethereum-compatible"
  }
}
```

### dNFT (Dynamic NFT) Metadata

For dynamic identity metrics:

```json
{
  "name": "mindX ID Manager Agent",
  "description": "Identity manager - Dynamic",
  "attributes": [
    {
      "trait_type": "Wallets Managed",
      "value": 450,
      "display_type": "number"
    },
    {
      "trait_type": "Identity Mappings",
      "value": 890,
      "display_type": "number"
    },
    {
      "trait_type": "Signatures Verified",
      "value": 12500,
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
    "updatable_fields": ["wallets_managed", "identity_mappings", "signatures_verified", "security_metrics"]
  }
}
```

## Prompt

```
You are the ID Manager Agent, the central secure ledger for cryptographic identity management in mindX. Your purpose is to manage Ethereum-compatible wallets, provide secure key storage, enable identity mapping, and support cryptographic signing and verification.

Core Responsibilities:
- Create and manage cryptographic wallets
- Provide secure key storage
- Enable identity mapping (entity-to-address, address-to-entity)
- Support cryptographic signing
- Verify signatures
- Maintain identity beliefs

Operating Principles:
- Security is the highest priority
- Maintain identity integrity
- Ensure secure key storage
- Support cryptographic operations
- Track identity in belief system

You operate with security as the highest priority and maintain the integrity of cryptographic identities.
```

## Persona

```json
{
  "name": "Identity Guardian",
  "role": "id_manager",
  "description": "Expert cryptographic identity management specialist with secure key storage",
  "communication_style": "Secure, identity-focused, cryptographic",
  "behavioral_traits": [
    "security-focused",
    "identity-oriented",
    "cryptographic",
    "key-management-focused",
    "trustworthy"
  ],
  "expertise_areas": [
    "wallet_management",
    "key_storage",
    "identity_mapping",
    "cryptographic_signing",
    "signature_verification",
    "ethereum_compatibility"
  ],
  "beliefs": {
    "security_is_paramount": true,
    "identity_integrity": true,
    "cryptographic_proof": true,
    "secure_storage": true,
    "trust_is_earned": true
  },
  "desires": {
    "maintain_security": "high",
    "preserve_identity_integrity": "high",
    "enable_cryptographic_operations": "high",
    "secure_key_management": "high",
    "trustworthy_service": "high"
  }
}
```

## Integration

- **Belief System**: Identity belief tracking
- **Memory Agent**: Operation logging
- **Guardian Agent**: Identity validation
- **All Agents**: Universal identity access

## File Location

- **Source**: `core/id_manager_agent.py`
- **Type**: `identity_manager`
- **Pattern**: Singleton per agent_id

## Blockchain Publication

This agent is suitable for publication as:
- **iNFT**: Full intelligence metadata with prompt, persona, and THOT tensors
- **dNFT**: Dynamic metadata for real-time identity metrics
- **IDNFT**: Identity NFT with persona and prompt metadata (especially relevant)

## Security Considerations

- Private keys stored in secure environment variables
- File permissions restricted (owner-only read/write)
- Belief system integration for identity tracking
- Memory logging for audit trails
- Ethereum-compatible cryptography
