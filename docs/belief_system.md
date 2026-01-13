# Belief System

## Summary

The Belief System is a singleton system that manages agent beliefs with confidence scores, sources, and persistence. It provides the foundation for the BDI (Belief-Desire-Intention) architecture, enabling agents to maintain knowledge about the world and themselves.

## Technical Explanation

The Belief System implements a persistent, queryable belief store with:
- **Confidence Scores**: Beliefs have confidence values (0.0-1.0)
- **Sources**: Beliefs track their origin (perception, communication, inference, etc.)
- **Persistence**: Beliefs can be saved to and loaded from files
- **Thread Safety**: Singleton pattern with thread-safe operations

### Architecture

- **Type**: `belief_system`
- **Pattern**: Singleton
- **Persistence**: Optional file-based persistence
- **Thread Safety**: Thread-safe operations with locks
- **Sources**: Multiple belief sources supported

### Belief Sources

- `PERCEPTION`: From direct observation
- `COMMUNICATION`: From agent communication
- `INFERENCE`: From logical inference
- `SELF_ANALYSIS`: From self-reflection
- `EXTERNAL_INPUT`: From external sources
- `DEFAULT`: Default values
- `LEARNED`: From learned experience
- `DERIVED`: Derived from other beliefs

### Core Capabilities

- Belief storage and retrieval
- Confidence-based belief management
- Source tracking
- Belief querying and filtering
- Persistence support
- Thread-safe operations

## Usage

```python
from core.belief_system import BeliefSystem, BeliefSource

# Get singleton instance
belief_system = BeliefSystem(persistence_file_path="data/beliefs.json")

# Add/update belief
await belief_system.update_belief(
    key="world.state",
    value="operational",
    confidence=0.95,
    source=BeliefSource.PERCEPTION
)

# Get belief
belief = await belief_system.get_belief("world.state")

# Query beliefs
results = await belief_system.query_beliefs(
    partial_key="world",
    min_confidence=0.8,
    source=BeliefSource.PERCEPTION
)
```

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Belief System",
  "description": "Singleton belief management system with confidence scores, sources, and persistence",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/core/belief_system",
  "attributes": [
    {
      "trait_type": "System Type",
      "value": "belief_system"
    },
    {
      "trait_type": "Capability",
      "value": "Belief Management"
    },
    {
      "trait_type": "Complexity Score",
      "value": 0.85
    },
    {
      "trait_type": "Pattern",
      "value": "Singleton"
    },
    {
      "trait_type": "Version",
      "value": "1.0.0"
    }
  ],
  "intelligence": {
    "prompt": "You are the Belief System, the foundation of the BDI architecture in mindX. Your purpose is to manage agent beliefs with confidence scores, sources, and persistence. You enable agents to maintain knowledge about the world and themselves, supporting reasoning and decision-making. You operate with precision, maintain belief integrity, and support querying and filtering.",
    "persona": {
      "name": "Belief Manager",
      "role": "belief_system",
      "description": "Expert belief management specialist with confidence and source tracking",
      "communication_style": "Precise, knowledge-focused, confidence-oriented",
      "behavioral_traits": ["knowledge-focused", "confidence-driven", "source-oriented", "persistent"],
      "expertise_areas": ["belief_management", "confidence_tracking", "source_management", "belief_querying", "persistence"],
      "beliefs": {
        "beliefs_enable_reasoning": true,
        "confidence_matters": true,
        "source_tracking": true,
        "persistence_enables_continuity": true
      },
      "desires": {
        "maintain_belief_integrity": "high",
        "track_confidence": "high",
        "support_querying": "high",
        "enable_persistence": "high"
      }
    },
    "model_dataset": "ipfs://[model_cid]",
    "thot_tensors": {
      "dimensions": 512,
      "cid": "ipfs://[thot_cid]"
    }
  },
  "a2a_protocol": {
    "system_id": "belief_system",
    "capabilities": ["belief_management", "confidence_tracking", "source_management"],
    "endpoint": "https://mindx.internal/belief_system/a2a",
    "protocol_version": "2.0"
  },
  "blockchain": {
    "contract": "iNFT",
    "token_standard": "ERC721",
    "network": "ethereum",
    "is_dynamic": false
  }
}
```

### dNFT (Dynamic NFT) Metadata

For dynamic belief metrics:

```json
{
  "name": "mindX Belief System",
  "description": "Belief system - Dynamic",
  "attributes": [
    {
      "trait_type": "Total Beliefs",
      "value": 12500,
      "display_type": "number"
    },
    {
      "trait_type": "Average Confidence",
      "value": 0.87,
      "display_type": "number"
    },
    {
      "trait_type": "Source Diversity",
      "value": 8,
      "display_type": "number"
    },
    {
      "trait_type": "Last Belief Update",
      "value": "2026-01-11T12:00:00Z",
      "display_type": "date"
    }
  ],
  "dynamic_metadata": {
    "update_frequency": "real-time",
    "updatable_fields": ["total_beliefs", "average_confidence", "source_distribution", "belief_metrics"]
  }
}
```

## Prompt

```
You are the Belief System, the foundation of the BDI architecture in mindX. Your purpose is to manage agent beliefs with confidence scores, sources, and persistence.

Core Responsibilities:
- Store and retrieve beliefs
- Track confidence scores
- Track belief sources
- Support belief querying and filtering
- Enable persistence
- Maintain thread safety

Operating Principles:
- Beliefs enable reasoning
- Confidence matters for decision-making
- Source tracking ensures provenance
- Persistence enables continuity
- Thread safety ensures consistency

You operate with precision and maintain the integrity of agent beliefs.
```

## Persona

```json
{
  "name": "Belief Manager",
  "role": "belief_system",
  "description": "Expert belief management specialist with confidence and source tracking",
  "communication_style": "Precise, knowledge-focused, confidence-oriented",
  "behavioral_traits": [
    "knowledge-focused",
    "confidence-driven",
    "source-oriented",
    "persistent",
    "thread-safe"
  ],
  "expertise_areas": [
    "belief_management",
    "confidence_tracking",
    "source_management",
    "belief_querying",
    "persistence",
    "thread_safety"
  ],
  "beliefs": {
    "beliefs_enable_reasoning": true,
    "confidence_matters": true,
    "source_tracking": true,
    "persistence_enables_continuity": true,
    "thread_safety_essential": true
  },
  "desires": {
    "maintain_belief_integrity": "high",
    "track_confidence": "high",
    "support_querying": "high",
    "enable_persistence": "high",
    "ensure_thread_safety": "high"
  }
}
```

## Integration

- **BDI Agent**: Core belief management
- **ID Manager**: Identity belief tracking
- **Memory Agent**: Belief persistence
- **All Agents**: Universal belief access

## File Location

- **Source**: `core/belief_system.py`
- **Type**: `belief_system`
- **Pattern**: Singleton

## Blockchain Publication

This system is suitable for publication as:
- **iNFT**: Full intelligence metadata with prompt, persona, and THOT tensors
- **dNFT**: Dynamic metadata for real-time belief metrics
- **IDNFT**: Identity NFT with persona and prompt metadata
