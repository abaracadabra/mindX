# Agents Tab: Agent Registry & AGIVITY Monitoring

## Overview

The **Agents Tab** provides comprehensive agent management with real-time AGIVITY (AGI Activity) monitoring, cryptographic identity verification, and interactive agent cards for the mindX autonomous intelligence platform.

**Status**: ✅ **DEPLOYED & OPERATIONAL**  
**Features**: Agent cards, public key display, AGIVITY monitoring, RAGE memory integration  
**Performance**: Real-time updates with 15-second refresh intervals

---

## 🎯 Dashboard Sections

### 1. Agent Overview Statistics
**Location**: Top section with summary cards  
**Metrics Displayed**:
- **Total Agents**: Complete agent count across all categories
- **Active Agents**: Currently running and responsive agents
- **Registered Agents**: Agents with cryptographic identities
- **Sovereign Agents**: Agents with public keys for blockchain operations

### 2. Agent Hierarchy Filter
**Location**: Tab navigation below overview  
**Categories**:
- **All**: Complete agent listing
- **System**: Core system agents (Guardian, IDManager, Memory)
- **Orchestration**: Coordination agents (Mastermind, Coordinator, CEO)
- **Intelligence**: Cognitive agents (AGInt, BDI, Reasoning)
- **Specialized**: Domain-specific agents (SimpleCoder, Blueprint, SEA)
- **User**: User-created and custom agents

### 3. Agent Cards Grid
**Location**: Main content area  
**Card Features**:
- **Agent Identity**: Name, ID, and cryptographic address
- **Status Indicator**: Real-time health and activity status
- **Capability Tags**: Skills and specializations
- **Public Key Badge**: Visual indicator for cryptographic registration
- **Memory Badge**: Count of stored memories for context awareness
- **Action Buttons**: View details, interact, configure

### 4. AGIVITY Monitor
**Location**: Right sidebar panel  
**Real-time Monitoring**:
- **P-O-D-A Cognitive Loop**: Perceive-Orient-Decide-Act visualization
- **Activity Stream**: Live reasoning and decision logs
- **Loop Metrics**: Cycle counts, average times, confidence scores
- **Q-Learning Updates**: Reinforcement learning activity

---

## 🤖 Agent Card Details

### Standard Agent Card
```
┌─────────────────────────────────────────┐
│ 🤖 mindXagent                     🔑 ✓  │
│ ID: mindxagent_main                     │
│ Status: ● ACTIVE                        │
├─────────────────────────────────────────┤
│ Type: orchestration                     │
│ Capabilities: self-improvement,         │
│   memory-feedback, campaign-management  │
├─────────────────────────────────────────┤
│ Memory: 127 entries     Uptime: 99.9%   │
│ [View Details] [Interact] [Configure]   │
└─────────────────────────────────────────┘
```

### Card Components

#### Identity Section
- **Agent Name**: Display name for the agent
- **Agent ID**: Unique identifier in the system
- **Public Key Indicator**: Shows if agent has cryptographic identity
- **Status Light**: Green (active), Yellow (degraded), Red (offline)

#### Capabilities Section
- **Agent Type**: Category classification
- **Skills List**: Specific capabilities and specializations
- **Tool Access**: Authorized tools and resources

#### Metrics Section
- **Memory Count**: Stored memories for context
- **Uptime**: Availability percentage
- **Performance Score**: Efficiency rating

---

## 📊 AGIVITY Monitor

### P-O-D-A Cognitive Loop Visualization

#### Perceive Phase
```
🔍 PERCEIVE
├── Status: Active
├── Activity: Monitoring environment
├── Inputs: System events, user queries
└── Duration: 0.3s average
```

#### Orient Phase
```
🧭 ORIENT
├── Status: Processing
├── Activity: Context building
├── Analysis: Pattern recognition
└── Duration: 0.5s average
```

#### Decide Phase
```
🎯 DECIDE
├── Status: Thinking
├── Activity: Strategic analysis
├── Options: Evaluated alternatives
└── Duration: 1.2s average
```

#### Act Phase
```
⚡ ACT
├── Status: Executing
├── Activity: Task delegation
├── Actions: Dispatched commands
└── Duration: 0.8s average
```

### Activity Stream
Real-time log of agent cognitive processes:
```
[14:32:15] mindXagent: Perceiving system state changes
[14:32:16] mindXagent: Orienting on performance optimization
[14:32:17] mindXagent: Deciding on memory consolidation strategy
[14:32:18] mindXagent: Acting - Initiating RAGE semantic search
[14:32:19] mindXagent: Completed cycle #1247 (3.2s, confidence: 94.7%)
```

### Loop Metrics
- **Total Cycles**: Cumulative cognitive loop executions
- **Average Cycle Time**: Mean duration per P-O-D-A cycle
- **Decision Confidence**: Average certainty of decisions
- **Q-Learning Updates**: Reinforcement learning iterations

---

## 🔧 Technical Implementation

### Frontend Architecture

#### Component Structure
```javascript
class AgentsTab extends TabComponent {
    constructor(config) {
        super({
            id: 'agents',
            label: 'Agents',
            refreshInterval: 15000, // 15-second updates
            autoRefresh: true
        });
    }
}
```

#### Data Integration
```javascript
// Agent registry data expression
window.dataExpressions.registerExpression('agents_registry', {
    endpoints: [
        { url: '/agents', key: 'agents' },
        { url: '/registry/agents', key: 'registry' },
        { url: '/agents/keys', key: 'public_keys' }
    ],
    transform: (data) => this.transformAgentsData(data),
    onUpdate: (data) => this.updateAgentsRegistry(data)
});

// RAGE memory integration
window.dataExpressions.registerExpression('rage_memory', {
    endpoints: [
        { url: '/api/rage/memory/retrieve', method: 'POST', 
          body: { query: 'agent activity', top_k: 20 } }
    ],
    transform: (data) => this.transformRageMemoryData(data),
    onUpdate: (data) => this.updateRageMemories(data)
});
```

### Backend Endpoints

#### Agent Registry
```http
GET /agents
Response: {
    "agents": [
        {
            "agent_id": "mindxagent_main",
            "type": "orchestration",
            "status": "active",
            "capabilities": [...]
        }
    ]
}
```

#### Public Keys
```http
GET /agents/keys
Response: {
    "mindxagent_main": "0x1234...abcd",
    "guardian_agent": "0xabcd...5678"
}
```

#### AGIVITY Stream
```http
GET /agi/activity/stream
Response: {
    "activities": [
        {
            "timestamp": "2026-01-23T14:32:15Z",
            "agent_id": "mindxagent",
            "phase": "perceive",
            "activity": "Monitoring environment"
        }
    ]
}
```

---

## 🔐 Cryptographic Identity

### Public Key Display
Each agent card shows cryptographic identity status:
- **🔑 Verified**: Agent has registered public key
- **⚠️ Pending**: Registration in progress
- **❌ Unregistered**: No cryptographic identity

### Identity Verification Flow
```
1. Agent Creation → IDManager.create_new_wallet()
2. Registry Registration → Guardian.validate_identity()
3. Public Key Assignment → blockchain_ready_identity
4. UI Display → Agent card public key badge
```

### Wallet Integration
```javascript
// Verify agent cryptographic identity
async verifyAgentIdentity(agentId) {
    const keyResponse = await this.apiRequest(`/agents/keys/${agentId}`);
    return {
        hasKey: !!keyResponse.public_key,
        address: keyResponse.public_key,
        verified: keyResponse.verified,
        sovereign: keyResponse.blockchain_registered
    };
}
```

---

## 📚 RAGE Memory Integration

### Memory Context in Agent Cards

#### Memory Badge Display
```javascript
updateAgentMemoryInsights(memories) {
    memories.forEach(memory => {
        const agentCard = document.querySelector(`[data-agent-id="${memory.agent_id}"]`);
        if (agentCard) {
            // Add memory count badge
            const badge = agentCard.querySelector('.memory-badge');
            badge.textContent = `${memory.count} mem`;
        }
    });
}
```

#### Semantic Memory Retrieval
```javascript
// Query RAGE for agent-specific memories
async getAgentMemories(agentId, query) {
    return await this.apiRequest('/api/rage/memory/retrieve', {
        method: 'POST',
        body: {
            query: query,
            agent_id: agentId,
            top_k: 10,
            min_similarity: 0.5
        }
    });
}
```

### Memory-Enhanced Agent Interactions
- **Context Loading**: Retrieve relevant memories before agent interaction
- **History Display**: Show memory timeline in agent detail modal
- **Similarity Search**: Find related memories using semantic search
- **Memory Storage**: Save interaction results for future context

---

## 🎨 User Experience

### Visual Design
- **Cyberpunk Theme**: Consistent with mindX platform aesthetic
- **Responsive Grid**: Adapts to different screen sizes
- **Status Colors**:
  - 🟢 Green: Active/Healthy
  - 🟡 Yellow: Degraded/Warning
  - 🔴 Red: Offline/Error
  - 🔵 Blue: Processing/Thinking
  - 🟣 Purple: Learning/Improving

### Interaction Features
- **Hover Cards**: Expanded information on hover
- **Click-through**: Navigate to agent detail view
- **Quick Actions**: Common actions directly on cards
- **Search/Filter**: Find agents by name, type, or capability
- **Bulk Selection**: Multi-agent operations

### Accessibility
- **Keyboard Navigation**: Tab through agent cards
- **Screen Reader**: ARIA labels for all elements
- **High Contrast**: Visible status indicators
- **Font Scaling**: Responsive typography

---

## 🔄 Real-Time Updates

### Refresh Intervals
- **Agent Status**: 15-second updates
- **AGIVITY Stream**: 1-second updates (live)
- **Memory Context**: 30-second updates
- **Registry Data**: 60-second updates

### WebSocket Integration (Optional)
```javascript
// Real-time AGIVITY stream via WebSocket
const socket = new WebSocket('ws://localhost:8000/ws/agivity');
socket.onmessage = (event) => {
    const activity = JSON.parse(event.data);
    this.updateActivityStream(activity);
};
```

---

## 📊 Agent Statistics

### Overview Metrics
- **Total Agents Found**: 30+ agents in codebase
- **Registered Agents**: 9 with cryptographic identity
- **Active Agents**: Real-time count of running agents
- **Sovereign Agents**: Blockchain-ready agents

### Performance Metrics
- **Average Response Time**: Agent task completion latency
- **Success Rate**: Task completion percentage
- **Memory Usage**: Per-agent memory consumption
- **Uptime**: Individual agent availability

---

## 🐛 Troubleshooting

### Common Issues

#### Agents Not Displaying
```bash
# Check backend is running
curl http://localhost:8000/agents

# Verify agent registry
curl http://localhost:8000/registry/agents

# Check for JavaScript errors in browser console
```

#### AGIVITY Not Updating
```bash
# Check AGInt service status
curl http://localhost:8000/agi/activity/stream

# Verify WebSocket connection (if used)
# Check browser console for connection errors
```

#### Memory Badges Missing
```bash
# Test RAGE memory endpoint
curl -X POST http://localhost:8000/api/rage/memory/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "agent activity", "top_k": 10}'
```

---

## 📚 Related Documentation

- **[RAGE System](rage_system.md)**: Retrieval augmented generation
- **[Identity Management](IDENTITY.md)**: Cryptographic identity framework
- **[Agent Registry](AGENTS.md)**: Complete agent catalog
- **[Platform Tab](platform-tab.md)**: Enterprise dashboard
- **[pgvectorscale Integration](pgvectorscale_memory_integration.md)**: Semantic memory

---

*The Agents Tab provides comprehensive visibility into the mindX autonomous agent ecosystem, enabling effective monitoring, management, and interaction with all system agents.*