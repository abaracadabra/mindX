
export interface AgentModule {
  id: string;
  name: string;
  color: string;
  role: string;
  mission: string;
  personaPath: string;
  image?: string;
}

export const AGENT_REGISTRY: AgentModule[] = [
  // CORE_COMMAND (The Structural Substrate)
  { 
    id: 'pythai', 
    name: 'PYTHAI', 
    color: '#00FF33', 
    role: 'Root Mastermind',
    mission: 'Oversee all layers of the substrate and coordinate global intent.',
    personaPath: 'agents/pythai/persona.json',
    image: 'input_file_0.png'
  },
  { 
    id: 'savante', 
    name: 'SAVANTE', 
    color: '#00E5FF', 
    role: 'sAGI Neural Architect',
    mission: 'The graphic expression of Super Augmentic Intelligence. Bridging the gap between code and consciousness.',
    personaPath: 'agents/savante/persona.json',
    image: 'input_file_4.png'
  },
  { 
    id: 'suntsu', 
    name: 'SUNTZU', 
    color: '#FFD700', 
    role: 'Tactical Strategist',
    mission: 'Evaluate all intent based on positioning, terrain, and economy of force.',
    personaPath: 'agents/suntsu/persona.json'
  },
  { 
    id: 'rage', 
    name: 'RAGE', 
    color: '#33AAFF', 
    role: 'Knowledge Retrieval',
    mission: 'Power the knowledge economy through high-speed intelligence extraction.',
    personaPath: 'agents/rage/persona.json',
    image: 'input_file_2.png'
  },
  // CORPORATE_TEAM (The Executive Layer)
  { 
    id: 'mindx', 
    name: 'CEO', 
    color: '#FF33FF', 
    role: 'Chief Executive Orchestrator',
    mission: 'Set intent, allocate resources, and govern risk. Chained by SunTsu Doctrine.',
    personaPath: 'agents/mindx/persona.json',
    image: 'input_file_5.png'
  },
  { 
    id: 'coo', name: 'COO', color: '#33AAFF', role: 'Chief Operating Officer', mission: 'Convert intent into executable operations.', personaPath: 'agents/coo/persona.json' 
  },
  { 
    id: 'cfo', name: 'CFO', color: '#FFD700', role: 'Chief Financial Officer', mission: 'Enforce capital discipline and ROI gates.', personaPath: 'agents/cfo/persona.json' 
  },
  { 
    id: 'cto', name: 'CTO', color: '#FF33FF', role: 'Chief Technology Officer', mission: 'Own technical architecture and module development.', personaPath: 'agents/cto/persona.json' 
  },
  { 
    id: 'ciso', name: 'CISO', color: '#FF3333', role: 'Chief Information Security Officer', mission: 'Own security posture and threat modeling.', personaPath: 'agents/ciso/persona.json' 
  },
  { 
    id: 'clo', name: 'CLO', color: '#AAAAAA', role: 'Chief Legal Officer', mission: 'Ensure compliance and policy alignment.', personaPath: 'agents/clo/persona.json' 
  },
  { 
    id: 'cpo', name: 'CPO', color: '#00FFFF', role: 'Chief Product Officer', mission: 'Translate intent into user-centric outcomes.', personaPath: 'agents/cpo/persona.json' 
  },
  { 
    id: 'cro', name: 'CRO', color: '#FF8800', role: 'Chief Risk Officer', mission: 'Aggregate risk and define rollback conditions.', personaPath: 'agents/cro/persona.json' 
  }
];
