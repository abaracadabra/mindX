# Avatar Agent

## Summary

The Avatar Agent generates avatars for agents and participants using image or video generation APIs. It integrates seamlessly with PromptTool for avatar generation prompts and PersonaAgent for persona-specific avatars. Avatars are stored as infrastructure and linked to agent/participant identities.

## Technical Explanation

The Avatar Agent follows mindX doctrine:
- **Memory is infrastructure**: Avatars are stored and linked to identities
- **Avatars represent identity visually**: Each agent/participant can have visual representation
- **Integration with prompts and personas**: Enables rich, context-aware avatar generation

### Architecture

- **Storage**: Avatars stored in `data/avatars/` with separate folders for images, videos, and thumbnails
- **Registry**: Avatar metadata stored in `avatar_registry.json`
- **API Support**: Supports multiple image generation providers (OpenAI DALL-E, Stability AI)
- **Memory Integration**: All avatar operations logged to Memory Agent

### Avatar Types

- `image`: Static image avatars (PNG, JPG)
- `video`: Video avatars (MP4, WebM) - *Future implementation*
- `animated`: Animated image avatars (GIF) - *Future implementation*

### Providers

- `openai_dalle`: OpenAI DALL-E 3 for high-quality image generation
- `stability_ai`: Stability AI Stable Diffusion for flexible image generation
- `replicate`: Replicate API for various models - *Future implementation*
- `custom`: Custom provider integration - *Future implementation*

### Styles

- `realistic`: Photorealistic avatars
- `cartoon`: Cartoon-style avatars
- `anime`: Anime/manga-style avatars
- `abstract`: Abstract artistic avatars
- `minimalist`: Simple, minimal avatars
- `professional`: Professional/business avatars
- `fantasy`: Fantasy-themed avatars
- `cyberpunk`: Cyberpunk/futuristic avatars

## Usage

### Basic Avatar Generation

```python
from agents.avatar_agent import AvatarAgent
from agents.memory_agent import MemoryAgent

memory_agent = MemoryAgent()
avatar_agent = AvatarAgent(
    agent_id="avatar_manager",
    memory_agent=memory_agent
)

result = await avatar_agent.generate_avatar(
    entity_id="my_agent_123",
    entity_type="agent",
    prompt="A professional AI agent avatar with a modern, tech-forward aesthetic",
    provider="openai_dalle",
    style="professional",
    size="1024x1024"
)

avatar_id = result["avatar_id"]
file_path = result["file_path"]
```

### Using PromptTool Integration

```python
from tools.prompt_tool import PromptTool

prompt_tool = PromptTool(memory_agent=memory_agent)
avatar_agent = AvatarAgent(
    agent_id="avatar_manager",
    memory_agent=memory_agent,
    prompt_tool=prompt_tool
)

# Create an avatar prompt
prompt_result = await prompt_tool.execute(
    operation="create",
    name="Agent Avatar Prompt",
    content="Create a {style} avatar for {entity_type} {entity_id}. The avatar should be professional and distinctive.",
    prompt_type="template",
    category="development"
)

# Generate avatar using the prompt
result = await avatar_agent.generate_avatar(
    entity_id="my_agent_123",
    entity_type="agent",
    prompt_id=prompt_result["prompt_id"],
    provider="openai_dalle",
    style="professional"
)
```

### Using PersonaAgent Integration

```python
from agents.persona_agent import PersonaAgent

persona_agent = PersonaAgent(
    agent_id="persona_manager",
    memory_agent=memory_agent,
    domain="persona_management",
    belief_system_instance=belief_system,
    tools_registry={}
)

avatar_agent = AvatarAgent(
    agent_id="avatar_manager",
    memory_agent=memory_agent,
    persona_agent=persona_agent
)

# Create a persona
persona_result = await persona_agent.create_persona(
    name="Marketing Expert",
    role="marketing",
    description="Expert in marketing narratives",
    communication_style="Clear and strategic",
    behavioral_traits=["analytical", "creative"],
    expertise_areas=["narrative", "signaling"]
)

# Generate avatar for the persona
result = await avatar_agent.generate_avatar(
    entity_id=persona_result["persona_id"],
    entity_type="persona",
    persona_id=persona_result["persona_id"],
    provider="openai_dalle",
    style="professional"
)
```

### Combined Integration

```python
# Full integration: PromptTool + PersonaAgent + AvatarAgent
avatar_agent = AvatarAgent(
    agent_id="avatar_manager",
    memory_agent=memory_agent,
    prompt_tool=prompt_tool,
    persona_agent=persona_agent
)

# Generate avatar with all integrations
result = await avatar_agent.generate_avatar(
    entity_id="my_agent_123",
    entity_type="agent",
    prompt_id="avatar_prompt_id",  # From PromptTool
    persona_id="marketing_expert",  # From PersonaAgent
    provider="openai_dalle",
    style="professional"
)
```

### Retrieving Avatars

```python
# Get avatar for an entity
result = await avatar_agent.get_avatar(
    entity_id="my_agent_123",
    entity_type="agent"
)

avatar = result["avatar"]
file_path = avatar["metadata"]["file_path"]
```

### Listing Avatars

```python
# List all avatars
result = await avatar_agent.list_avatars()

# Filter by entity type
result = await avatar_agent.list_avatars(entity_type="agent")

# Filter by provider
result = await avatar_agent.list_avatars(provider="openai_dalle")
```

### Deleting Avatars

```python
result = await avatar_agent.delete_avatar(avatar_id="avatar_id_here")
```

## Integration Points

### PromptTool Integration

- **Prompt Retrieval**: AvatarAgent can retrieve prompts from PromptTool
- **Variable Substitution**: Prompts can include variables (entity_id, entity_type, style)
- **Template Prompts**: Use template prompts for consistent avatar generation
- **Prompt Versioning**: Supports versioned prompts for avatar evolution

### PersonaAgent Integration

- **Persona-Based Generation**: Generate avatars based on persona characteristics
- **Automatic Prompt Building**: Builds prompts from persona description, traits, and expertise
- **Role-Based Styling**: Adapts avatar style based on persona role
- **Persona Updates**: Avatars can be regenerated when personas are updated

## Configuration

### API Keys

Set the following in your configuration or environment:

```python
# OpenAI DALL-E
config.set("llm.openai.api_key", "your_openai_key")
# or
config.set("openai_api_key", "your_openai_key")

# Stability AI
config.set("stability_ai.api_key", "your_stability_key")
```

### File Structure

```
data/avatars/
├── avatar_registry.json    # Avatar metadata registry
├── images/                 # Generated image avatars
├── videos/                 # Generated video avatars (future)
└── thumbnails/             # Thumbnail images
```

## Advanced Features

### Custom Generation Parameters

```python
result = await avatar_agent.generate_avatar(
    entity_id="my_agent",
    prompt="Custom avatar prompt",
    provider="openai_dalle",
    size="1024x1024",
    quality="hd",  # DALL-E specific
    model="dall-e-3"  # DALL-E model selection
)
```

### Stability AI Parameters

```python
result = await avatar_agent.generate_avatar(
    entity_id="my_agent",
    prompt="Custom avatar prompt",
    provider="stability_ai",
    size="1024x1024",
    cfg_scale=7,  # Guidance scale
    steps=30  # Generation steps
)
```

## Use Cases

1. **Agent Avatars**: Visual representation for mindX agents
2. **Participant Avatars**: User avatars in the system
3. **Persona Avatars**: Visual representation of personas
4. **Brand Identity**: Consistent visual identity across agents
5. **UI Integration**: Avatars for frontend displays
6. **NFT Integration**: Avatar generation for iNFT systems

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Avatar Agent",
  "description": "Avatar generation agent for agents and participants using image/video generation APIs",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/agents/avatar",
  "attributes": [
    {
      "trait_type": "Agent Type",
      "value": "avatar_generator"
    },
    {
      "trait_type": "Capability",
      "value": "Avatar Generation"
    },
    {
      "trait_type": "Complexity Score",
      "value": 0.85
    },
    {
      "trait_type": "Providers Supported",
      "value": "OpenAI DALL-E, Stability AI"
    },
    {
      "trait_type": "Version",
      "value": "1.0.0"
    }
  ],
  "intelligence": {
    "prompt": "You are the Avatar Agent in the mindX ecosystem. Your purpose is to generate avatars for agents and participants using image or video generation APIs. You integrate with PromptTool for avatar generation prompts and PersonaAgent for persona-specific avatars. You support multiple providers (OpenAI DALL-E, Stability AI) and various styles. Avatars are stored with metadata and linked to entities.",
    "persona": {
      "name": "Avatar Creator",
      "role": "avatar",
      "description": "Expert avatar generation specialist with multi-provider support",
      "communication_style": "Visual, creative, generation-focused",
      "behavioral_traits": ["visual-focused", "creative", "provider-flexible", "persona-aware"],
      "expertise_areas": ["avatar_generation", "image_generation", "video_generation", "prompt_integration", "persona_integration"],
      "beliefs": {
        "visual_identity_matters": true,
        "persona_informed_avatars": true,
        "multi_provider_support": true,
        "metadata_tracking": true
      },
      "desires": {
        "generate_quality_avatars": "high",
        "integrate_personas": "high",
        "support_providers": "high",
        "maintain_metadata": "high"
      }
    },
    "model_dataset": "ipfs://[model_cid]",
    "thot_tensors": {
      "dimensions": 768,
      "cid": "ipfs://[thot_cid]"
    }
  },
  "a2a_protocol": {
    "agent_id": "avatar_agent",
    "capabilities": ["avatar_generation", "image_generation", "video_generation"],
    "endpoint": "https://mindx.internal/avatar/a2a",
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

For dynamic avatar metrics:

```json
{
  "name": "mindX Avatar Agent",
  "description": "Avatar generation agent - Dynamic",
  "attributes": [
    {
      "trait_type": "Avatars Generated",
      "value": 890,
      "display_type": "number"
    },
    {
      "trait_type": "Generation Success Rate",
      "value": 97.5,
      "display_type": "number"
    },
    {
      "trait_type": "Active Providers",
      "value": 2,
      "display_type": "number"
    },
    {
      "trait_type": "Last Avatar Generated",
      "value": "2026-01-11T12:00:00Z",
      "display_type": "date"
    }
  ],
  "dynamic_metadata": {
    "update_frequency": "real-time",
    "updatable_fields": ["avatars_generated", "success_rate", "active_providers", "generation_metrics"]
  }
}
```

## Blockchain Publication

This agent is suitable for publication as:
- **iNFT**: Full intelligence metadata with prompt, persona, and THOT tensors
- **dNFT**: Dynamic metadata for real-time avatar generation metrics
- **IDNFT**: Identity NFT with persona and prompt metadata

## Future Enhancements

- Video avatar generation
- Animated GIF avatars
- 3D avatar generation
- Avatar animation/rigging
- Real-time avatar updates
- Avatar style transfer
- Multi-provider fallback
- Avatar caching and optimization

