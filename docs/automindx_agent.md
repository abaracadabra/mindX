# AutoMINDX Agent Documentation

## Overview

The AutoMINDX Agent serves as the "keeper of prompts" for the mindX ecosystem, managing agent personas and their intelligent NFT (iNFT) representations with comprehensive avatar support, A2A protocol compliance, and AgenticPlace marketplace integration. This advanced system creates blockchain-ready agent personas that can be traded as intelligent NFTs while maintaining full interoperability with the official A2A protocol.

## Core Features

### 1. **Persona Management**
- Dynamic persona creation and editing
- LLM-powered capability and trait extraction
- Complexity scoring and cognitive profiling
- Multi-version persona evolution tracking

### 2. **Avatar System**
- **Automatic avatar generation** for all personas
- **Custom avatar support** (SVG, PNG formats)
- **IPFS-ready metadata** for decentralized storage
- **AgenticPlace-compatible** visual identity

### 3. **A2A Protocol Integration**
- **Full A2A 2.0 compliance** with Google's specification
- **Agent Card generation** for discovery and interoperability
- **Cross-platform hashing** for universal recognition
- **Discovery endpoint** generation (/.well-known/agents.json)

### 4. **AgenticPlace Marketplace**
- **Complete marketplace integration** with https://agenticplace.pythai.net
- **Deployment package generation** for instant marketplace readiness
- **Licensing and pricing** metadata support
- **Custom fields** for marketplace-specific attributes

### 5. **iNFT Export System**
- **Enhanced metadata structure** with avatar and marketplace data
- **ERC-721 compatible** JSON for major NFT platforms
- **Blockchain publication** manifest generation
- **Immutable provenance** with cryptographic hashing

## Class Structure

### AutoMINDXAgent

**Singleton agent class** that manages the entire persona ecosystem with advanced blockchain and marketplace capabilities.

#### Key Properties:
- `agenticplace_base_url`: "https://agenticplace.pythai.net"
- `github_base_url`: "https://github.com/agenticplace"
- `inft_export_dir`: Directory for blockchain-ready exports
- `avatars_dir`: Directory for avatar files
- `a2a_cards_dir`: Directory for A2A protocol agent cards
- `custom_fields_schema`: Validation schema for user-defined metadata

## Enhanced Methods

### Avatar Management

#### `update_persona_avatar(persona_key: str, avatar_config: Dict[str, Any]) -> bool`
Updates the avatar for an existing persona with full A2A protocol regeneration.

**Parameters:**
- `persona_key`: Identifier for the persona
- `avatar_config`: Configuration dictionary with avatar generation preferences

**Example:**
```python
avatar_config = {
    "type": "generated",  # or "custom"
    "style": "professional",  # "strategic", "technical", etc.
    "custom_path": "/path/to/custom/avatar.svg"  # for custom avatars
}

success = await automindx.update_persona_avatar("MASTERMIND", avatar_config)
```

#### `_generate_or_assign_avatar(persona_key: str, avatar_config: Optional[Dict]) -> Optional[Path]`
Internal method for avatar generation with SVG placeholders and IPFS preparation.

### Custom Fields Management

#### `update_persona_custom_fields(persona_key: str, custom_fields: Dict[str, Any]) -> bool`
Updates user-defined metadata fields for marketplace and evolutionary tracking.

**Supported Custom Fields:**
- `evolution_stage`: "genesis", "adaptation", "optimization", "transcendence"
- `specialization_domain`: Domain-specific expertise area
- `interaction_preference`: "text", "multimodal", "voice", "visual"
- `autonomy_level`: Float (0.0-1.0) representing agent independence
- `marketplace_tags`: List of marketplace category tags
- `license_type`: "open_source", "commercial", "academic"

**Example:**
```python
custom_fields = {
    "evolution_stage": "adaptation",
    "specialization_domain": "blockchain_security",
    "interaction_preference": "multimodal",
    "autonomy_level": 0.85,
    "marketplace_tags": ["security", "blockchain", "audit"],
    "license_type": "open_source"
}

success = await automindx.update_persona_custom_fields("SECURITY_AUDITOR", custom_fields)
```

### AgenticPlace Marketplace Integration

#### `generate_agenticplace_manifest() -> Dict[str, Any]`
Generates a comprehensive marketplace manifest for AgenticPlace deployment.

**Generated Manifest Structure:**
```json
{
  "marketplace_manifest": {
    "platform": "AgenticPlace",
    "marketplace_url": "https://agenticplace.pythai.net",
    "provider": {
      "organization": "mindX",
      "ecosystem": "mindX Autonomous Agent System",
      "github": "https://github.com/agenticplace"
    },
    "a2a_protocol": {
      "version": "2.0",
      "compliance_level": "full",
      "discovery_endpoint": "/.well-known/agents.json"
    },
    "agents": [...]
  }
}
```

#### `deploy_to_agenticplace(persona_keys: Optional[List[str]] = None) -> Dict[str, Any]`
Prepares a complete deployment package for AgenticPlace marketplace.

**Returns deployment package with:**
- iNFT metadata files for all personas
- A2A agent cards for discovery
- Avatar files (SVG/PNG)
- Marketplace manifests and blockchain publication data

### A2A Protocol Compliance

#### `generate_a2a_discovery_endpoint() -> Dict[str, Any]`
Generates the official A2A protocol discovery endpoint following Google's specification.

**Generated Discovery Structure:**
```json
{
  "agents": [
    {
      "id": "mindx_mastermind",
      "name": "mindX Mastermind Agent",
      "agent_card_url": "https://agenticplace.pythai.net/agents/mastermind/card.json",
      "capabilities": {
        "streaming": true,
        "pushNotifications": true,
        "multimodal": false,
        "longRunningTasks": true
      },
      "authentication": ["bearer", "oauth2"],
      "status": "active"
    }
  ],
  "metadata": {
    "platform": "mindX",
    "a2a_version": "2.0",
    "discovery_endpoint": "/.well-known/agents.json"
  }
}
```

#### `_generate_a2a_agent_card(persona_key: str, persona_text: str, metadata: Dict) -> None`
Generates A2A protocol compliant Agent Cards for each persona.

**Agent Card Structure:**
```json
{
  "agent_id": "mindx_mastermind",
  "name": "mindX Mastermind Agent",
  "description": "Strategic orchestration agent...",
  "capabilities": ["planning", "coordination", "optimization"],
  "endpoints": {
    "chat": "/chat",
    "status": "/status",
    "health": "/health"
  },
  "authentication": {
    "required": true,
    "methods": ["bearer", "oauth2"]
  },
  "metadata": {
    "version": "2.0",
    "agent_registry_id": "mindx_mastermind",
    "blockchain_ready": true
  },
  "avatar": {
    "svg": "https://agenticplace.pythai.net/avatars/mastermind_avatar.svg",
    "ipfs": "ipfs://QmPersonaAvatar..."
  }
}
```

### Enhanced iNFT Export

#### `export_persona_as_inft_metadata(persona_key: str) -> Optional[Dict[str, Any]]`
Exports persona as comprehensive iNFT metadata with avatar and marketplace integration.

**Enhanced iNFT Structure:**
```json
{
  "name": "mindX Persona: Mastermind",
  "description": "An intelligent NFT representing an AI agent persona...",
  "image": "https://agenticplace.pythai.net/avatars/mastermind_avatar.svg",
  "external_url": "https://agenticplace.pythai.net/agents/mastermind",
  
  "intelligence_metadata": {
    "type": "agent_persona",
    "platform": "mindX",
    "cognitive_architecture": "BDI_AGInt",
    "persona_text": "...",
    "persona_hash": "sha256_hash",
    "avatar": {
      "primary_image": "https://agenticplace.pythai.net/avatars/mastermind_avatar.svg",
      "ipfs_hash": "ipfs://QmPersonaAvatar...",
      "has_custom_avatar": true,
      "avatar_type": "svg"
    },
    "custom_attributes": {
      "evolution_stage": "optimization",
      "autonomy_level": 0.95,
      "marketplace_tags": ["strategy", "planning"]
    },
    "a2a_compatibility": {
      "protocol_version": "2.0",
      "agenticplace_compatible": true,
      "agent_card_available": true
    },
    "marketplace_integration": {
      "platform": "AgenticPlace",
      "agent_url": "https://agenticplace.pythai.net/agents/mastermind",
      "license_type": "open_source",
      "evolution_stage": "optimization"
    }
  },
  
  "attributes": [
    {"trait_type": "Evolution Stage", "value": "optimization"},
    {"trait_type": "Autonomy Level", "value": 0.95},
    {"trait_type": "Marketplace Ready", "value": true},
    {"trait_type": "A2A Compatible", "value": true},
    {"trait_type": "Has Avatar", "value": true}
  ]
}
```

## Directory Structure

```
mindX/
├── inft_exports/                    # iNFT metadata exports
│   ├── persona_*_inft.json         # Individual persona iNFT files
│   ├── agenticplace_manifest.json  # Marketplace manifest
│   └── agenticplace_deployment.json # Deployment package info
├── avatars/                        # Avatar files
│   ├── *_avatar.svg               # Generated SVG avatars
│   └── default_mindx_avatar.svg   # Default placeholder
├── a2a_cards/                     # A2A protocol agent cards
│   ├── *_agent_card.json         # Individual agent cards
│   └── agents_discovery.json     # A2A discovery endpoint
└── data/
    ├── personas.json              # Core persona texts
    ├── persona_metadata.json     # Enhanced metadata
    └── custom_fields_schema.json # Validation schema
```

## AgenticPlace Integration

### Marketplace URLs
- **Main Platform**: https://agenticplace.pythai.net
- **GitHub Organization**: https://github.com/agenticplace
- **Agent Discovery**: https://agenticplace.pythai.net/.well-known/agents.json

### Deployment Process
1. **Generate personas** with custom fields and avatars
2. **Export iNFT metadata** with marketplace integration
3. **Create A2A agent cards** for discovery
4. **Generate deployment package** with all required files
5. **Deploy to AgenticPlace** marketplace

### Marketplace Features
- **Agent browsing** and discovery
- **License management** (open source, commercial, academic)
- **Tag-based categorization** for specialized domains
- **Evolution tracking** through stages
- **Autonomy level** assessment
- **A2A protocol compliance** verification

## Usage Examples

### Complete Persona Creation with Marketplace Features
```python
# Initialize AutoMINDX
automindx = await AutoMINDXAgent.get_instance(memory_agent)

# Define comprehensive custom fields
custom_fields = {
    "evolution_stage": "adaptation",
    "specialization_domain": "blockchain_security",
    "interaction_preference": "multimodal",
    "autonomy_level": 0.85,
    "marketplace_tags": ["security", "blockchain", "audit", "defi"],
    "license_type": "open_source"
}

# Configure avatar
avatar_config = {
    "type": "generated",
    "style": "professional"
}

# Generate new persona
persona = await automindx.generate_new_persona(
    role_description="Advanced Blockchain Security Auditor specializing in smart contract vulnerabilities",
    save_to_collection=True,
    custom_fields=custom_fields,
    avatar_config=avatar_config
)
```

### AgenticPlace Deployment
```python
# Prepare full deployment package
deployment = await automindx.deploy_to_agenticplace()

# Check deployment status
for persona, status in deployment["deployment_status"].items():
    print(f"{persona}: {status}")

# Access generated files
inft_files = deployment["files_generated"]["inft_metadata"]
agent_cards = deployment["files_generated"]["agent_cards"]
avatars = deployment["files_generated"]["avatars"]
```

### A2A Protocol Integration
```python
# Generate discovery endpoint
discovery = automindx.generate_a2a_discovery_endpoint()

# Generate marketplace manifest
manifest = automindx.generate_agenticplace_manifest()

# Access A2A agent cards
for persona_key in automindx.personas.keys():
    card_path = automindx.a2a_cards_dir / f"{persona_key.lower()}_agent_card.json"
    if card_path.exists():
        print(f"A2A card available for {persona_key}")
```

## Blockchain Integration

### iNFT Minting Preparation
All exported personas are ready for immediate blockchain minting on:
- **Ethereum** mainnet (ERC-721)
- **Polygon** (MATIC network)
- **Arbitrum** (Layer 2 scaling)

### Immutable Provenance
- **SHA-256 hashing** for content verification
- **A2A protocol hashing** for cross-platform recognition
- **Agent registry integration** for identity verification
- **Blockchain publication manifest** for minting coordination

## Future Enhancements

### Evolutionary Agents
- **Dynamic persona evolution** based on performance metrics
- **Marketplace feedback integration** for continuous improvement
- **Multi-generational tracking** through evolution stages
- **Autonomous self-improvement** capabilities

### Advanced Marketplace Features
- **Agent collaboration** marketplace for multi-agent teams
- **Performance analytics** and reputation systems
- **Revenue sharing** for commercial agents
- **Cross-platform agent migration** with full provenance

### Enhanced A2A Protocol Features
- **Real-time agent discovery** and capability matching
- **Dynamic load balancing** across agent instances
- **Federated agent networks** with autonomous coordination
- **Advanced authentication** and security protocols

## Conclusion

The enhanced AutoMINDX agent represents a significant advancement in AI persona management, creating the foundation for a thriving marketplace of intelligent, tradeable agent personas with full blockchain integration and A2A protocol compliance. This system enables the creation of an autonomous agent economy where personas can evolve, interact, and be exchanged while maintaining immutable provenance and verification through the AgenticPlace marketplace ecosystem.
