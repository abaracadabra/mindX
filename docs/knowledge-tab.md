# Knowledge Tab: Semantic Knowledge Graph

## Overview

The **Knowledge Tab** visualizes the mindX knowledge graph, showing semantic relationships between beliefs, goals, strategic evolution, and learned patterns.

**Status**: ✅ **DEPLOYED & OPERATIONAL**  
**Features**: Interactive knowledge graph, belief system visualization, evolution tracking  
**Backend**: pgvectorscale semantic memory with vector similarity search

---

## 🎯 Dashboard Sections

### 1. Knowledge Graph Visualization
**Location**: Center canvas  
**Features**:
- **Concept Nodes**: Beliefs, goals, strategies, and patterns
- **Relationship Edges**: Semantic connections between concepts
- **Cluster Detection**: Auto-grouped related knowledge
- **Interactive Exploration**: Click to expand, zoom, and filter

### 2. Belief System Panel
**Location**: Left sidebar  
**Components**:
- **Active Beliefs**: Currently held system beliefs
- **Confidence Scores**: Certainty levels (0-100%)
- **Evidence Links**: Supporting memory references
- **Evolution History**: Belief changes over time

### 3. Goal Hierarchy
**Location**: Right sidebar  
**Components**:
- **Strategic Goals**: High-level objectives
- **Tactical Goals**: Implementation targets
- **Operational Goals**: Immediate tasks
- **Goal Dependencies**: Prerequisite relationships

### 4. Knowledge Insights
**Location**: Bottom panel  
**Metrics**:
- **Knowledge Growth**: New concepts learned over time
- **Connection Density**: Relationship richness
- **Pattern Recognition**: Discovered correlations
- **Memory Utilization**: Semantic storage usage

---

## 🧠 Knowledge Graph Structure

### Node Types

#### Belief Nodes (Blue)
```
┌─────────────────────────────────┐
│ 💭 BELIEF: Self-Improvement     │
│ Confidence: 94.7%               │
│ Source: EXPERIENCE              │
│ Created: 2026-01-15             │
│ Evidence: 127 memories          │
└─────────────────────────────────┘
```

#### Goal Nodes (Green)
```
┌─────────────────────────────────┐
│ 🎯 GOAL: Optimize Performance   │
│ Priority: HIGH                  │
│ Status: IN_PROGRESS             │
│ Progress: 67%                   │
│ Deadline: 2026-02-01            │
└─────────────────────────────────┘
```

#### Strategy Nodes (Purple)
```
┌─────────────────────────────────┐
│ 📋 STRATEGY: Memory-Driven      │
│ Type: IMPROVEMENT               │
│ Phase: IMPLEMENTATION           │
│ Success Rate: 89%               │
└─────────────────────────────────┘
```

#### Pattern Nodes (Orange)
```
┌─────────────────────────────────┐
│ 🔄 PATTERN: High-Load Handling  │
│ Occurrences: 23                 │
│ Confidence: 87.3%               │
│ Last Seen: 2 hours ago          │
└─────────────────────────────────┘
```

### Edge Types
- **Supports**: Belief → Goal (evidence for objective)
- **Implements**: Strategy → Goal (execution path)
- **Discovers**: Pattern → Belief (learned relationship)
- **Contradicts**: Belief → Belief (conflicting evidence)
- **Depends On**: Goal → Goal (prerequisite relationship)

---

## 📊 Belief System Integration

### Confidence Scoring
```
Confidence = Base_Evidence × Source_Weight × Temporal_Decay × Reinforcement_Factor

Where:
- Base_Evidence: Number of supporting memories
- Source_Weight: Credibility of evidence source
- Temporal_Decay: Recency factor
- Reinforcement_Factor: Repeated confirmation bonus
```

### Belief Sources
- **EXPERIENCE**: Learned from interactions
- **REASONING**: Derived through inference
- **EXTERNAL**: Imported from documentation
- **USER**: Provided by human operators
- **SYSTEM**: Core architectural assumptions

### Belief Evolution
```
1. Initial Formation
   ↓ Evidence accumulation
2. Confidence Growth
   ↓ Pattern recognition
3. Belief Refinement
   ↓ Contradiction resolution
4. Stable Belief
   ↓ Periodic validation
5. Belief Update/Deprecation
```

---

## 🔧 Technical Implementation

### Frontend Architecture

```javascript
class KnowledgeTab extends TabComponent {
    constructor(config) {
        super({
            id: 'knowledge',
            label: 'Knowledge',
            refreshInterval: 30000,
            autoRefresh: true
        });
    }

    renderKnowledgeGraph(data) {
        // Initialize D3.js force-directed graph
        const simulation = d3.forceSimulation(data.nodes)
            .force('link', d3.forceLink(data.edges).id(d => d.id))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2));

        // Render nodes and edges
        this.renderNodes(data.nodes);
        this.renderEdges(data.edges);
    }
}
```

### Backend Endpoints

```http
GET /knowledge/graph
Response: {
    "nodes": [
        {
            "id": "belief_001",
            "type": "belief",
            "label": "Self-Improvement Capability",
            "confidence": 0.947,
            "evidence_count": 127
        }
    ],
    "edges": [
        {
            "source": "belief_001",
            "target": "goal_003",
            "relationship": "supports",
            "strength": 0.85
        }
    ]
}

GET /knowledge/beliefs
Response: {
    "beliefs": [
        {
            "belief_id": "belief_001",
            "content": "System can improve through memory-driven feedback",
            "confidence": 0.947,
            "source": "EXPERIENCE",
            "evidence": ["mem_001", "mem_002", ...]
        }
    ]
}

GET /knowledge/goals
Response: {
    "goals": [
        {
            "goal_id": "goal_003",
            "description": "Optimize query response time",
            "priority": "HIGH",
            "status": "IN_PROGRESS",
            "progress": 0.67
        }
    ]
}
```

---

## 🔍 Semantic Search Integration

### pgvectorscale Queries
```sql
-- Find related beliefs by semantic similarity
SELECT b.belief_id, b.content, 1 - (e.embedding <=> query_embedding) as similarity
FROM beliefs b
JOIN belief_embeddings e ON b.belief_id = e.belief_id
WHERE 1 - (e.embedding <=> query_embedding) > 0.7
ORDER BY similarity DESC
LIMIT 10;
```

### Knowledge Discovery
```python
# Discover new patterns from memory
async def discover_patterns(memories: List[Memory]) -> List[Pattern]:
    # Generate embeddings for recent memories
    embeddings = [model.encode(m.content) for m in memories]
    
    # Cluster similar memories
    clusters = cluster_embeddings(embeddings, min_cluster_size=5)
    
    # Extract patterns from clusters
    patterns = []
    for cluster in clusters:
        pattern = extract_pattern(cluster)
        if pattern.confidence > 0.7:
            patterns.append(pattern)
    
    return patterns
```

---

## 📚 Related Documentation

- **[Belief System](belief_system.md)**: Belief management architecture
- **[pgvectorscale Integration](pgvectorscale_memory_integration.md)**: Semantic memory
- **[Strategic Evolution Agent](strategic_evolution_agent.md)**: Self-improvement
- **[Memory Agent](memory_agent.md)**: Memory storage and retrieval

---

*The Knowledge Tab provides visibility into the mindX cognitive architecture, enabling understanding and optimization of the system's belief structures and learning processes.*