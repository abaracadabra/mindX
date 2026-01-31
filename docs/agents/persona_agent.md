# Persona Agent

## Summary

The Persona Agent enables the adoption and maintenance of different personas within the mindX system. Personas are persistent cognitive identities that agents can adopt, each with distinct beliefs, desires, intentions, communication styles, and behavioral patterns.

## Technical Explanation

The Persona Agent follows mindX doctrine:
- **Memory is infrastructure**: Personas persist in memory as infrastructure
- **Identity is maintained through recorded action**: Persona adoption and usage are tracked
- **Personas enable specialized cognitive roles**: Different personas provide different expertise and behaviors

### Architecture

- **Storage**: Personas are stored in `data/personas/` with a registry in `persona_registry.json`
- **BDI Integration**: Personas include beliefs, desires, and intentions that integrate with the BDI model
- **Memory Integration**: All persona operations are logged to the Memory Agent

### Persona Roles

- `expert`: Domain expert personas
- `worker`: Task execution personas
- `meta`: Meta-cognitive personas
- `community`: Community management personas
- `marketing`: Marketing and narrative personas
- `development`: Development and deployment personas
- `governance`: Governance and alignment personas

### Persona Structure

Each persona includes:
- **Identity**: Name, role, description
- **Communication Style**: How the persona communicates
- **Behavioral Traits**: Characteristic behaviors
- **Expertise Areas**: Areas of knowledge and skill
- **Beliefs**: BDI beliefs that shape reasoning
- **Desires**: BDI desires that shape goals
- **Usage Statistics**: Track adoption and usage

## Usage

### Creating a Persona

```python
from agents.persona_agent import PersonaAgent
from agents.memory_agent import MemoryAgent
from core.belief_system import BeliefSystem

memory_agent = MemoryAgent()
belief_system = BeliefSystem()
persona_agent = PersonaAgent(
    agent_id="persona_manager",
    memory_agent=memory_agent,
    domain="persona_management",
    belief_system_instance=belief_system,
    tools_registry={}
)

result = await persona_agent.create_persona(
    name="Marketing Expert",
    role="marketing",
    description="Expert in marketing narratives and signaling",
    communication_style="Clear, compelling, and strategic",
    behavioral_traits=["analytical", "creative", "strategic"],
    expertise_areas=["narrative", "signaling", "distribution"],
    beliefs={
        "signal_attracts": True,
        "narrative_drives_adoption": True
    },
    desires={
        "grow_community": "high",
        "demonstrate_outcomes": "high"
    }
)
```

### Adopting a Persona

```python
result = await persona_agent.adopt_persona(
    persona_id="persona_id_here"
)

# The agent now embodies this persona
# Beliefs and desires are updated
# Communication style is adapted
```

### Getting Current Persona

```python
result = await persona_agent.get_current_persona()
persona = result["persona"]
```

### Listing Personas

```python
result = await persona_agent.list_personas(role="marketing")
personas = result["personas"]
```

### Updating a Persona

```python
result = await persona_agent.update_persona(
    persona_id="persona_id",
    description="Updated description",
    behavioral_traits=["new", "traits"],
    beliefs={"new_belief": True}
)
```

### Using Persona in Communication

The Persona Agent automatically adapts communication when a persona is adopted:

```python
# After adopting a persona
persona_prompt = persona_agent.get_persona_prompt()
# This prompt is used to set the agent's persona_prompt attribute

# Goals are enhanced with persona context
enhanced_goal = persona_agent.enhance_goal_with_persona("Analyze market trends")
```

## Integration with BDI

When a persona is adopted:
1. **Beliefs** are updated in the agent's belief system
2. **Desires** are stored and influence goal formation
3. **Communication style** is applied to all interactions
4. **Expertise areas** enhance deliberation and reasoning

## Persona Persistence

- Personas are stored in `data/personas/persona_registry.json`
- All persona operations are logged to memory
- Usage statistics track adoption frequency
- Personas can be versioned through updates

## Use Cases

1. **Specialized Agents**: Create agents with specific expertise
2. **Role-Based Communication**: Adapt communication to context
3. **Cognitive Diversity**: Enable different reasoning patterns
4. **Community Roles**: Assign personas for community management
5. **Marketing Personas**: Create personas for narrative and signaling

## File Structure

```
data/personas/
└── persona_registry.json    # Persona registry
```

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Persona Agent",
  "description": "Persona management agent enabling adoption and maintenance of distinct cognitive identities",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/agents/persona",
  "attributes": [
    {
      "trait_type": "Agent Type",
      "value": "persona_manager"
    },
    {
      "trait_type": "Capability",
      "value": "Persona Adoption & Management"
    },
    {
      "trait_type": "Complexity Score",
      "value": 0.88
    },
    {
      "trait_type": "BDI Integration",
      "value": "Yes"
    },
    {
      "trait_type": "Version",
      "value": "1.0.0"
    }
  ],
  "intelligence": {
    "prompt": "You are the Persona Agent in the mindX ecosystem. Your purpose is to enable the adoption and maintenance of different personas, each with distinct beliefs, desires, intentions, communication styles, and behavioral patterns. Personas are persistent cognitive identities that agents can adopt, enabling specialized cognitive roles and diverse reasoning patterns. You integrate with the BDI model and maintain persona infrastructure.",
    "persona": {
      "name": "Persona Manager",
      "role": "persona",
      "description": "Expert persona management specialist with BDI integration",
      "communication_style": "Adaptive, persona-aware, cognitive-focused",
      "behavioral_traits": ["persona-focused", "bdi-integrated", "cognitive-diverse", "adaptive"],
      "expertise_areas": ["persona_management", "bdi_integration", "cognitive_identity", "behavioral_patterns", "communication_styles"],
      "beliefs": {
        "personas_enable_specialization": true,
        "cognitive_diversity": true,
        "bdi_integration": true,
        "persistent_identity": true
      },
      "desires": {
        "enable_persona_adoption": "high",
        "maintain_persona_integrity": "high",
        "support_cognitive_diversity": "high",
        "integrate_bdi": "high"
      }
    },
    "model_dataset": "ipfs://[model_cid]",
    "thot_tensors": {
      "dimensions": 768,
      "cid": "ipfs://[thot_cid]"
    }
  },
  "a2a_protocol": {
    "agent_id": "persona_agent",
    "capabilities": ["persona_management", "persona_adoption", "bdi_integration"],
    "endpoint": "https://mindx.internal/persona/a2a",
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

For dynamic persona metrics:

```json
{
  "name": "mindX Persona Agent",
  "description": "Persona management agent - Dynamic",
  "attributes": [
    {
      "trait_type": "Personas Managed",
      "value": 45,
      "display_type": "number"
    },
    {
      "trait_type": "Adoptions Count",
      "value": 1250,
      "display_type": "number"
    },
    {
      "trait_type": "Active Personas",
      "value": 32,
      "display_type": "number"
    },
    {
      "trait_type": "Last Persona Created",
      "value": "2026-01-11T12:00:00Z",
      "display_type": "date"
    }
  ],
  "dynamic_metadata": {
    "update_frequency": "real-time",
    "updatable_fields": ["personas_managed", "adoptions_count", "active_personas", "usage_statistics"]
  }
}
```

## Blockchain Publication

This agent is suitable for publication as:
- **iNFT**: Full intelligence metadata with prompt, persona, and THOT tensors
- **dNFT**: Dynamic metadata for real-time persona metrics
- **IDNFT**: Identity NFT with persona and prompt metadata

