
import React, { useState, useEffect, useRef } from 'react';
import { AGENT_REGISTRY } from './agents/registry.ts';
import { LogEntry, epistemic } from './epistemic.ts';

export const PersonaSelector = ({ current, onSelect }: { current: string, onSelect: (id: string) => void }) => {
  const ceos = AGENT_REGISTRY.filter(a => ['pythai', 'suntsu', 'mindx', 'savante'].includes(a.id));
  return (
    <div className="ceo-switcher-strip">
      <div className="strip-label">ACTING_CEO_BUFFER:</div>
      {ceos.map(p => (
        <button 
          key={p.id} 
          className={`ceo-tab ${current === p.id ? 'active' : ''}`}
          onClick={() => onSelect(p.id)}
        >
          <div className="p-dot" style={{ backgroundColor: p.color }}></div>
          {p.id.toUpperCase()}
        </button>
      ))}
    </div>
  );
};

export const AgentNexusClassic = ({ onSelectAgent }: { onSelectAgent: (id: string) => void }) => {
    const [rot, setRot] = useState({ x: -25, y: -45 });
    const [isAutoSpin, setIsAutoSpin] = useState(true);
    const [hoveredFace, setHoveredFace] = useState<string | null>(null);
    const isDragging = useRef(false);
    const lastPos = useRef({ x: 0, y: 0 });

    useEffect(() => {
        if (!isAutoSpin || isDragging.current) return;
        const interval = setInterval(() => {
            setRot(r => ({ ...r, y: r.y + 0.4 }));
        }, 30);
        return () => clearInterval(interval);
    }, [isAutoSpin]);

    const handleMouseDown = (e: React.MouseEvent) => {
        isDragging.current = true;
        lastPos.current = { x: e.clientX, y: e.clientY };
    };

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!isDragging.current) return;
            const dx = e.clientX - lastPos.current.x;
            const dy = e.clientY - lastPos.current.y;
            setRot(r => ({ x: r.x - dy * 0.5, y: r.y + dx * 0.5 }));
            lastPos.current = { x: e.clientX, y: e.clientY };
        };
        const handleMouseUp = () => { isDragging.current = false; };
        window.addEventListener('mousemove', handleMouseMove);
        window.addEventListener('mouseup', handleMouseUp);
        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, []);

    const nexusFaces = [
        { class: 'front', agent: AGENT_REGISTRY.find(a => a.id === 'pythai') },
        { class: 'back', agent: AGENT_REGISTRY.find(a => a.id === 'savante') },
        { class: 'right', agent: AGENT_REGISTRY.find(a => a.id === 'mindx') },
        { class: 'left', agent: AGENT_REGISTRY.find(a => a.id === 'rage') },
        { class: 'top', agent: AGENT_REGISTRY.find(a => a.id === 'suntsu') },
        { class: 'bottom', agent: AGENT_REGISTRY.find(a => a.id === 'cto') },
    ];

    return (
        <div className="nexus-classic-inner">
            <div className="nexus-control-bar">
                <button className={`nexus-toggle ${isAutoSpin ? 'active' : ''}`} onClick={() => setIsAutoSpin(!isAutoSpin)}>
                    {isAutoSpin ? 'AUTO_SPIN_ON' : 'MANUAL_MODE'}
                </button>
                <div className="nexus-label">AGENT_NEXUS_v0.1</div>
            </div>
            
            <div className="nexus-view-scene" onMouseDown={handleMouseDown}>
                <div className="cube-wrapper" style={{ transform: `rotateX(${rot.x}deg) rotateY(${rot.y}deg)` }}>
                    <div className="cube">
                        {nexusFaces.map(f => (
                            <div 
                                key={f.class} 
                                className={`cube-face ${f.class}`} 
                                style={{ borderColor: f.agent?.color || 'var(--primary-color)' }}
                                onMouseEnter={() => setHoveredFace(f.agent?.name || null)}
                                onMouseLeave={() => setHoveredFace(null)}
                                onClick={() => f.agent && onSelectAgent(f.agent.id)}
                            >
                                <div className="nexus-face-content">
                                    <div className="nexus-id">{f.agent?.id.toUpperCase()}</div>
                                    <div className="nexus-role">{f.agent?.role}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
            {hoveredFace && <div className="nexus-tooltip">{hoveredFace.toUpperCase()}</div>}
        </div>
    );
};

export const Visualizer = ({ activityPulse = 0, isCompact = false, logSource = [] }: { activityPulse?: number, isCompact?: boolean, logSource?: LogEntry[] }) => {
  const [load, setLoad] = useState(25);
  const [latency, setLatency] = useState(42);

  useEffect(() => {
    const i = setInterval(() => {
        const isSpiking = activityPulse > 0 && (Date.now() - activityPulse < 3000);
        setLoad(l => Math.min(99, Math.max(5, l + (Math.random()*6-3) + (isSpiking ? 25 : 0))));
        setLatency(lat => Math.min(400, Math.max(12, lat + (Math.random()*25-10) + (isSpiking ? 80 : 0))));
    }, 1500);
    return () => clearInterval(i);
  }, [activityPulse]);

  return (
    <div className={`viz-wrap ${isCompact ? 'compact' : ''}`}>
         <div className="viz-stats">
            <span>STABILITY: {(100-load*0.1).toFixed(1)}%</span>
            <span>UPLINK: {latency.toFixed(0)}MS</span>
         </div>
         <div className="viz-bar-rail"><div className="viz-bar-fill" style={{ width: `${load}%` }}></div></div>
         <div className="telemetry-log-stream">
            {logSource.slice(0, isCompact ? 5 : 15).map((log, idx) => (
                <div key={idx} className="log-entry-row">
                    <span className="log-ts">[{log.timestamp.split('T')[1].split('.')[0]}]</span>
                    <span className="log-type" style={{ color: log.eventType === 'error' ? '#ff3366' : 'var(--primary-color)' }}>{log.eventType.toUpperCase()}</span>
                    <span className="log-msg">{log.message}</span>
                </div>
            ))}
         </div>
    </div>
  );
};

export const DAO3DView = ({ rotation, resonance, onRotationChange, onSelectFace, hasSingularity = false, onSingularityDragStart }: { 
    rotation: {x: number, y: number}, 
    resonance: number,
    onRotationChange: (rot: {x: number, y: number}) => void,
    onSelectFace: (id: string) => void,
    hasSingularity?: boolean,
    onSingularityDragStart?: () => void
}) => {
    const [hoveredFace, setHoveredFace] = useState<string | null>(null);
    const isDragging = useRef(false);
    const lastPos = useRef({ x: 0, y: 0 });

    const handleMouseDown = (e: React.MouseEvent) => {
        if ((e.target as HTMLElement).tagName === 'A' || (e.target as HTMLElement).closest('.singularity-core')) return;
        isDragging.current = true;
        lastPos.current = { x: e.clientX, y: e.clientY };
    };

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!isDragging.current) return;
            const dx = e.clientX - lastPos.current.x;
            const dy = e.clientY - lastPos.current.y;
            onRotationChange({ x: rotation.x - dy * 0.5, y: rotation.y + dx * 0.5 });
            lastPos.current = { x: e.clientX, y: e.clientY };
        };
        const handleMouseUp = () => { isDragging.current = false; };
        window.addEventListener('mousemove', handleMouseMove);
        window.addEventListener('mouseup', handleMouseUp);
        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [rotation, onRotationChange]);

    const faces = [
        { class: 'front', id: 'pythai', label: 'PYTHAI', mission: 'ROOT_MAINFRAME', img: 'input_file_0.png' },
        { class: 'back', id: 'savante', label: 'SAVANTE', mission: 'sAGI_COGNITION', img: 'input_file_3.png' },
        { class: 'right', id: 'mindx', label: 'mindX', mission: 'EXECUTIVE_COMMAND', img: 'input_file_5.png' },
        { class: 'left', id: 'rage', label: 'ROOT (RAGE)', mission: 'KNOWLEDGE_RETRIEVAL', img: 'input_file_2.png' },
        { class: 'top', id: 'suntsu', label: 'SUNTSU', mission: 'TACTICAL_DOCTRINE' },
    ];

    const glowColor = `rgba(0, 188, 212, ${resonance / 100})`;

    return (
        <div className="cube-scene" onMouseDown={handleMouseDown}>
            <div className="cube-wrapper" style={{ transform: `rotateX(${rotation.x}deg) rotateY(${rotation.y}deg)` }}>
                <div className="cube" style={{ boxShadow: `0 0 ${resonance}px ${glowColor}` }}>
                    {hasSingularity && (
                        <div 
                            className="singularity-core"
                            onMouseDown={(e) => { e.stopPropagation(); onSingularityDragStart?.(); }}
                            title="DRAG_TO_DE-DOCK_SINGULARITY"
                        >
                            <img src="https://i.ibb.co/dKqS6B1/pythaicointrans.png" alt="Singularity" />
                        </div>
                    )}
                    {faces.map(f => (
                        <div 
                            key={f.id} 
                            className={`cube-face ${f.class}`} 
                            style={{ borderColor: glowColor }}
                            onMouseEnter={() => setHoveredFace(f.label)}
                            onMouseLeave={() => setHoveredFace(null)}
                            onClick={() => onSelectFace(f.id)}
                        >
                            {f.img ? <img src={f.img} alt={f.label} draggable="false" className="face-image-fit" /> : <div className="face-text">{f.label}</div>}
                        </div>
                    ))}
                    <div className="cube-face bottom" style={{ borderColor: glowColor }}>
                        <div className="face-text">BANKON</div>
                    </div>
                </div>
            </div>
            <div className="scene-label">ACTIVE_COGNITIVE_CORE // {hoveredFace ? `FOCUS: ${hoveredFace}` : 'READY'}</div>
        </div>
    );
};

interface Member { id: string; name: string; color: string; isSoldier: boolean; }
const MEMBERS: Member[] = [
  { id: "COO", name: "Ops", color: "#33AAFF", isSoldier: true },
  { id: "CFO", name: "Fin", color: "#FFD700", isSoldier: true },
  { id: "CTO", name: "Tech", color: "#FF33FF", isSoldier: true },
  { id: "CISO", name: "Sec", color: "#FF3333", isSoldier: true },
  { id: "CLO", name: "Leg", color: "#AAAAAA", isSoldier: true },
  { id: "CPO", name: "Prod", color: "#00FFFF", isSoldier: true },
  { id: "CRO", name: "Risk", color: "#FF8800", isSoldier: true }
];

export const DAOBoard = ({ activeCEO, votingStep = -1, isCompact = false }: { activeCEO: string, votingStep?: number, isCompact?: boolean }) => {
  const [memberStatus, setMemberStatus] = useState<Record<string, { zone: 'ok'|'no', isActive: boolean }>>(
    Object.fromEntries(MEMBERS.map(m => [m.id, { zone: 'ok', isActive: true }]))
  );

  const activeSoldiersCount = MEMBERS.filter(m => memberStatus[m.id].isActive).length;
  const approvedSoldiersCount = MEMBERS.filter(m => memberStatus[m.id].isActive && memberStatus[m.id].zone === 'ok').length;
  const isQuorum = approvedSoldiersCount >= 5;

  const toggleMember = (id: string) => {
    setMemberStatus(p => ({ ...p, [id]: { ...p[id], isActive: !p[id].isActive } }));
  };

  const ceoColor = AGENT_REGISTRY.find(a => a.id === activeCEO)?.color || '#fff';

  return (
    <div className={`dao-matrix-container ${isCompact ? 'compact' : ''}`}>
      <div className="dao-soldiers-backdrop">
          <img src="input_file_5.png" alt="Seven Soldiers" className="backdrop-img" />
          <div className="backdrop-vignette"></div>
      </div>
      <div className="ceo-voter-association">
          <div className="active-ceo-node" style={{ color: ceoColor, borderColor: ceoColor }}>
              <div className="node-label">ACTING_CEO</div>
              <div className="node-id">{activeCEO.toUpperCase()}</div>
          </div>
      </div>
      <div className="soldier-quorum-row">
          {MEMBERS.map((m, idx) => (
              <div 
                key={m.id} 
                className={`soldier-node ${memberStatus[m.id].isActive ? 'is-active' : 'is-omitted'} ${votingStep === idx ? 'pulse-ping' : ''}`}
                style={{ '--m-color': m.color } as any}
                onClick={() => toggleMember(m.id)}
              >
                  <div className="node-box">
                      <div className="node-name">{m.id}</div>
                      <div className="node-status">{memberStatus[m.id].isActive ? 'READY' : 'OMIT'}</div>
                  </div>
              </div>
          ))}
      </div>
      <div className={`quorum-state-bar ${isQuorum ? 'valid' : 'pending'}`}>
          {isQuorum ? 'CONSENSUS_REACHED' : 'AWAITING_SUPERMAJORITY'} ({approvedSoldiersCount}/{activeSoldiersCount})
      </div>
    </div>
  );
};
