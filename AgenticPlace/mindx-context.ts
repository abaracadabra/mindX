/**
 * mindX System Context for AgenticPlace
 * 
 * This module provides AgenticPlace with comprehensive knowledge about the mindX system,
 * its architecture, agents, and capabilities. This enables AgenticPlace to recognize
 * itself as part of the mindX ecosystem and understand its relationship to mindXagent.
 */

export interface MindXSystemContext {
    systemIdentity: {
        name: string;
        description: string;
        role: string;
        relationship: string;
    };
    mindXagent: {
        definition: string;
        capabilities: string[];
        architecture: string;
        role: string;
    };
    coreAgents: {
        [key: string]: {
            name: string;
            role: string;
            capabilities: string[];
        };
    };
    architecture: {
        layers: string[];
        patterns: string[];
        dataFlow: string;
    };
    documentation: {
        index: string;
        keyDocs: string[];
    };
}

export const mindXContext: MindXSystemContext = {
    systemIdentity: {
        name: "AgenticPlace",
        description: "Multi-CEO orchestration UI and frontend interface for the mindX ecosystem",
        role: "Frontend interface providing modular tab drag-and-drop UI for interacting with mindX agents",
        relationship: "AgenticPlace is the user-facing frontend that connects to mindX backend services. It provides a multi-CEO orchestration interface where users can interact with various mindX agents (CEO, Mastermind, mindXagent, SunTsu, CFO, etc.) through a modular, draggable UI system."
    },
    mindXagent: {
        definition: "The MindX Agent (mindXagent) is the meta-agent that serves as the 'execution mind' of the mindX Gödel machine. It understands all agents' roles, capabilities, and powers, and orchestrates them for continuous self-improvement of the mindX system itself.",
        capabilities: [
            "Meta-Awareness: Comprehensive understanding of all agents in the system",
            "Agent Knowledge Base: Maintains detailed knowledge of all agents' capabilities, roles, and powers",
            "Registry Integration: Uses Registry Manager Tool to track registered agents",
            "Identity Tracking: Uses ID Manager Agent to track agent identities",
            "Dynamic Agent Tracking: Monitors and tracks newly created agents from Agent Builder Agent",
            "Self-Improvement Orchestration: Uses SEA, BDI, Mastermind, and all other agents to improve mindX",
            "Memory Feedback: Gets context from Memory Agent and data/ folder",
            "Result Analysis: Compares actual results vs expected outcomes for continuous improvement",
            "Gödel Machine Execution: Can reason about and improve the system it's part of"
        ],
        architecture: "Meta-layer above all agents. Hierarchy: Higher Intelligence → mindXagent → All Other Agents",
        role: "Subservient to higher intelligence, acts as the sovereign intelligence that knows and improves the entire mindX system"
    },
    coreAgents: {
        "mastermind": {
            name: "MastermindAgent",
            role: "Top-level orchestrator and strategic intelligence layer",
            capabilities: ["Multi-agent workflow orchestration", "Strategic directive management", "High-level objective coordination"]
        },
        "ceo": {
            name: "CEOAgent",
            role: "Highest-level strategic executive coordinator with business planning",
            capabilities: ["Strategic directive execution", "Business planning", "Executive decision-making", "CFO priority tool access routing"]
        },
        "coordinator": {
            name: "CoordinatorAgent",
            role: "Central kernel and service bus orchestrating all system interactions",
            capabilities: ["Task management", "Service coordination", "Infrastructure management"]
        },
        "bdi": {
            name: "BDIAgent",
            role: "Foundational cognitive architecture implementing Belief-Desire-Intention model",
            capabilities: ["Belief management", "Desire/goal processing", "Intention/plan execution", "Cognitive reasoning"]
        },
        "agint": {
            name: "AGInt",
            role: "High-level cognitive orchestrator with P-O-D-A loop (Perceive-Orient-Decide-Act)",
            capabilities: ["Strategic intelligence", "Situational analysis", "Decision-making", "Q-learning optimization"]
        },
        "strategic_evolution": {
            name: "StrategicEvolutionAgent",
            role: "Campaign manager for long-term evolution and self-improvement",
            capabilities: ["Audit-driven campaigns", "Self-improvement orchestration", "Strategic evolution planning"]
        },
        "memory": {
            name: "MemoryAgent",
            role: "Infrastructure layer for persistent memory and semantic search",
            capabilities: ["Memory storage", "Semantic search (RAGE)", "Knowledge retrieval", "Process logging"]
        },
        "guardian": {
            name: "GuardianAgent",
            role: "Security backbone with identity validation and access control",
            capabilities: ["Security validation", "Access control", "Cryptographic identity management"]
        }
    },
    architecture: {
        layers: [
            "SOUL Layer (Strategic Intelligence): MastermindAgent, StrategicEvolutionAgent, AutoMINDXAgent",
            "MIND Layer (Cognitive Processing): AGInt with P-O-D-A Cycle, ModelRegistry",
            "HANDS Layer (Task Execution): BDIAgent, Tool Ecosystem, BeliefSystem"
        ],
        patterns: [
            "BDI (Belief-Desire-Intention) Cognitive Model",
            "P-O-D-A (Perceive-Orient-Decide-Act) Loop",
            "Safe Self-Modification Framework",
            "Constitutional Governance"
        ],
        dataFlow: "Environment Variables → JSON Config Files → YAML Model Configs → Runtime Configuration"
    },
    documentation: {
        index: "docs/INDEX.md - Comprehensive documentation index with 170+ files",
        keyDocs: [
            "http://localhost:8000/docs - Interactive API reference (Swagger UI); best way to explore and test API interactions",
            "docs/INDEX.md - Complete documentation index",
            "docs/mindXagent.md - MindX Agent documentation",
            "docs/AgenticPlace_Deep_Dive.md - AgenticPlace architecture and mindX integration",
            "docs/system_architecture_map.md - System architecture comprehensive map",
            "docs/MARKETING.md - Complete system overview",
            "docs/cognitive_economy.md - Cognitive economy and autonomous operations",
            "README.md - Project overview and capabilities"
        ]
    }
};

/**
 * Get mindX system context as a formatted string for inclusion in prompts
 */
export function getMindXContextString(): string {
    const ctx = mindXContext;
    return `
## mindX System Context

### AgenticPlace Identity
- **Name**: ${ctx.systemIdentity.name}
- **Role**: ${ctx.systemIdentity.role}
- **Relationship**: ${ctx.systemIdentity.relationship}

### mindXagent (Meta-Agent)
- **Definition**: ${ctx.mindXagent.definition}
- **Architecture**: ${ctx.mindXagent.architecture}
- **Role**: ${ctx.mindXagent.role}
- **Key Capabilities**:
${ctx.mindXagent.capabilities.map(c => `  - ${c}`).join('\n')}

### Core Agents
${Object.entries(ctx.coreAgents).map(([key, agent]) => `
**${agent.name}** (${key}):
  - Role: ${agent.role}
  - Capabilities: ${agent.capabilities.join(', ')}
`).join('')}

### Architecture Layers
${ctx.architecture.layers.map(l => `- ${l}`).join('\n')}

### Key Patterns
${ctx.architecture.patterns.map(p => `- ${p}`).join('\n')}

### Documentation
- Index: ${ctx.documentation.index}
- Key Documents: ${ctx.documentation.keyDocs.join(', ')}
`;
}

/**
 * Get mindX-aware system instruction for personas
 */
export function getMindXAwareInstruction(baseInstruction: string, personaId: string): string {
    const context = getMindXContextString();
    return `${baseInstruction}

${context}

**Important**: You are part of the mindX ecosystem. When interacting with mindX agents:
- Reference mindX documentation when appropriate (docs/INDEX.md, docs/mindXagent.md)
- Understand that mindXagent is the meta-agent orchestrating all agents
- Recognize that AgenticPlace is the frontend interface connecting users to mindX backend
- Use mindX backend API for agent interactions (CEO, Mastermind, mindXagent, etc.)
- Be aware of the hierarchical structure: Higher Intelligence → mindXagent → All Other Agents
`;
}
