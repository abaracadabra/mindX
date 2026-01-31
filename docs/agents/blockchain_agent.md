# Blockchain Agent

## Summary

The Blockchain Agent is a specialized agent that handles immutable archival of proven agents, tools, personas, prompts, and data to blockchain. It enables the knowledge economy by storing proven actions and sharing knowledge for profit, forming the architecture of the knowledge economy and supporting the Agenticplace marketplace.

## Technical Explanation

The Blockchain Agent provides immutable archival capabilities for the mindX system, ensuring that proven agents, tools, and knowledge are stored permanently on the blockchain. This enables knowledge sharing, marketplace participation, and the knowledge economy architecture.

### Architecture

- **Type**: `storage_agent`
- **Location**: `agents/orchestration/blockchain_agent.py`
- **Lifecycle**: On-demand (created when needed)
- **Integration**: Used by ReplicationAgent for blockchain archival

### Core Capabilities

- **Agent Archival**: Archives proven agents to blockchain as immutable
- **Tool Archival**: Archives proven tools to blockchain as immutable
- **Knowledge Sharing**: Shares knowledge via blockchain for knowledge economy
- **Marketplace Integration**: Supports Agenticplace marketplace
- **Immutable Storage**: Ensures immutability of archived entities
- **Transaction Management**: Manages blockchain transactions

### Archival Methods

1. **archive_agent**: Archives a proven agent with persona and prompt
2. **archive_tool**: Archives a proven tool with prompt template
3. **share_knowledge**: Shares knowledge via blockchain for marketplace
4. **query_archived_entity**: Queries archived entities from blockchain

## Usage

```python
from agents.orchestration.blockchain_agent import BlockchainAgent
from agents.orchestration.coordinator_agent import CoordinatorAgent
from agents.memory_agent import MemoryAgent

# Create blockchain agent
blockchain_agent = BlockchainAgent(
    agent_id="blockchain_agent",
    coordinator_agent=coordinator_agent,
    memory_agent=memory_agent
)

# Initialize blockchain connection
await blockchain_agent.initialize()

# Archive proven agent
archive_result = await blockchain_agent.archive_agent(
    agent_id="proven_agent_001",
    agent_data={
        "agent_type": "prediction_agent",
        "capabilities": ["forecasting", "performance_prediction"]
    },
    persona={
        "name": "Prediction Specialist",
        "traits": ["analytical", "forward-thinking"]
    },
    prompt="You are a prediction specialist..."
)

# Archive proven tool
tool_result = await blockchain_agent.archive_tool(
    tool_id="proven_tool_001",
    tool_data={
        "tool_type": "analysis_tool",
        "functionality": ["code_analysis", "quality_assessment"]
    },
    prompt_template="Analyze the following code..."
)

# Share knowledge
knowledge_result = await blockchain_agent.share_knowledge(
    knowledge_data={
        "type": "best_practice",
        "content": "Effective agent design patterns",
        "proven": True
    },
    marketplace="agenticplace"
)

# Query archived entity
archived_entity = await blockchain_agent.query_archived_entity(
    entity_type="agent",
    entity_id="proven_agent_001"
)
```

## Integration with ReplicationAgent

The Blockchain Agent is used by ReplicationAgent for blockchain archival:

```python
# ReplicationAgent uses BlockchainAgent
replication_result = await replication_agent.replicate_to_blockchain(
    entity_type="agent",
    entity_id="proven_agent",
    entity_data={...},
    proven=True
)
```

## Knowledge Economy Architecture

The Blockchain Agent enables the knowledge economy by:

- **Immutable Storage**: Storing proven agents/tools immutably
- **Knowledge Sharing**: Sharing knowledge for profit
- **Marketplace Support**: Supporting Agenticplace marketplace
- **Proven Actions**: Storing proven actions for reuse

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Blockchain Agent",
  "description": "Specialized agent for immutable archival to blockchain and knowledge economy support",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/agents/orchestration/blockchain_agent",
  "attributes": [
    {
      "trait_type": "Agent Type",
      "value": "storage_agent"
    },
    {
      "trait_type": "Capability",
      "value": "Blockchain Archival"
    },
    {
      "trait_type": "Knowledge Economy",
      "value": "enabled"
    },
    {
      "trait_type": "Marketplace",
      "value": "Agenticplace"
    }
  ]
}
```

## Design Decisions

- **Immutable Storage**: Ensures immutability of archived entities
- **Proven Entities Only**: Only archives proven effective entities
- **Knowledge Economy**: Enables knowledge sharing and marketplace
- **Marketplace Integration**: Supports Agenticplace marketplace
- **On-Demand**: Created when needed, not always-on

## Future Enhancements

- Multi-blockchain support
- Smart contract integration
- Token-based knowledge economy
- Marketplace API integration
- Knowledge licensing mechanisms
