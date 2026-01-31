
import React, { useState, useEffect } from 'react';
import { epistemic } from './epistemic.ts';
import { GoogleGenAI } from "@google/genai";
import { marked } from "marked";

// --- NEURAL INTELLIGENCE SELECTOR ---
export const PersonaSelector = ({ current, onSelect }: { current: string, onSelect: (id: string) => void }) => {
  const personas = [
    { id: 'pythai', name: 'PYTHAI_ROOT', color: '#00FF33' },
    { id: 'suntsu', name: 'SUN_TSU_TACTIC', color: '#FFD700' },
    { id: 'rage', name: 'RAGE_ENGINE', color: '#33AAFF' },
    { id: 'mindx', name: 'MINDX_CEO', color: '#FF33FF' }
  ];

  return (
    <div className="persona-selector-wrap">
      {personas.map(p => (
        <button 
          key={p.id} 
          className={`persona-btn ${current === p.id ? 'active' : ''}`}
          onClick={() => onSelect(p.id)}
          style={{ '--p-color': p.color } as any}
        >
          <div className="p-dot"></div>
          <span className="p-label">{p.name}</span>
        </button>
      ))}
    </div>
  );
};

// --- ADVANCED 3D VISUALIZER ---
export const Visualizer = () => {
  const [speed, setSpeed] = useState(15); 
  const [axis, setAxis] = useState({ x: true, y: true, z: false });

  const getAnimation = () => {
    const parts = [];
    if (axis.x) parts.push('rotX');
    if (axis.y) parts.push('rotY');
    if (axis.z) parts.push('rotZ');
    
    if (parts.length === 0) return 'none';
    return parts.map(p => `${p} ${speed}s linear infinite`).join(', ');
  };

  return (
    <div className="viz-module-container">
      <div className="viz-background-grid"></div>
      <div className="viz-viewport">
        <div className="viz-glow-core"></div>
        <div 
          className="viz-box" 
          style={{ animation: getAnimation() }}
        >
          <div className="box-face face-front">MASTERMIND</div>
          <div className="box-face face-back">mindX</div>
          <div className="box-face face-right">ALPHA</div>
          <div className="box-face face-left">ROOT</div>
          <div className="box-face face-top">PYTHAI</div>
          <div className="box-face face-bottom">CORE</div>
        </div>
      </div>
      
      <div className="viz-controls glass-panel">
        <div className="control-group">
          <div className="label-row">
            <label>ROTATION_VELOCITY</label>
            <span className="value-tag">{(61 - speed).toString().padStart(2, '0')}</span>
          </div>
          <input 
            type="range" min="1" max="60" step="1" 
            value={61 - speed} 
            onChange={(e) => setSpeed(61 - parseInt(e.target.value))} 
          />
        </div>
        <div className="control-group axes">
          <button className={axis.x ? 'active' : ''} onClick={() => setAxis(a => ({...a, x: !a.x}))}>X_AXIS</button>
          <button className={axis.y ? 'active' : ''} onClick={() => setAxis(a => ({...a, y: !a.y}))}>Y_AXIS</button>
          <button className={axis.z ? 'active' : ''} onClick={() => setAxis(a => ({...a, z: !a.z}))}>Z_AXIS</button>
        </div>
      </div>
    </div>
  );
};

// --- DAO CONSENSUS BOARD ---
const SOLDIERS = [
  { id: "COO", name: "Operations", color: "#33AAFF", focus: "Process Optimization & Scaling" },
  { id: "CFO", name: "Finance", color: "#FFD700", focus: "Capital Allocation & Treasury" },
  { id: "CTO", name: "Technology", color: "#FF33FF", focus: "Neural Infrastructure & R&D" },
  { id: "CISO", name: "Security", color: "#FF3333", focus: "Threat Mitigation & Protocol Integrity" },
  { id: "CLO", name: "Legal", color: "#AAAAAA", focus: "Compliance & Jurisdictional Strategy" },
  { id: "CPO", name: "Product", color: "#00FFFF", focus: "User Augmentation & UX Strategy" },
  { id: "CRO", name: "Risk", color: "#FF8800", focus: "Epistemic Uncertainty & Stability" }
];

export const DAOBoard = () => {
  const [positions, setPositions] = useState<Record<string, 'pool' | 'approved' | 'rejected'>>(
    Object.fromEntries(SOLDIERS.map(s => [s.id, 'pool']))
  );
  const [selectedSoldierId, setSelectedSoldierId] = useState<string>(SOLDIERS[0].id);
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [protocolResult, setProtocolResult] = useState<string>("");
  const [executing, setExecuting] = useState(false);

  const onDragStart = (e: React.DragEvent, id: string) => {
    e.dataTransfer.setData("agentId", id);
    setDraggedId(id);
  };

  const onDragEnd = () => setDraggedId(null);

  const onDrop = (e: React.DragEvent, zone: 'pool' | 'approved' | 'rejected') => {
    const id = e.dataTransfer.getData("agentId");
    if (positions[id] !== zone) {
      setPositions(prev => ({ ...prev, [id]: zone }));
      epistemic.logEvent("ConsensusUpdate", `Agent ${id} re-oriented to ${zone.toUpperCase()} zone.`);
    }
    setDraggedId(null);
  };

  const executeProtocol = async () => {
    if (executing) return;
    setExecuting(true);
    const approved = SOLDIERS.filter(s => positions[s.id] === 'approved').map(s => s.id);
    const rejected = SOLDIERS.filter(s => positions[s.id] === 'rejected').map(s => s.id);
    
    try {
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
      const prompt = `As the mindX CEO, provide a high-level summary of the current executive board consensus. 
      Approved Agents: ${approved.join(', ')}. 
      Rejected Agents: ${rejected.join(', ')}.
      If a supermajority (5/7) is reached, authorize the directive. Otherwise, state the missing alignment.`;
      
      const response = await ai.models.generateContent({
        model: 'gemini-3-flash-preview',
        contents: prompt
      });
      setProtocolResult(response.text || "NO_DATA_AVAILABLE");
      epistemic.logEvent("ProtocolExecution", `Consensus broadcast generated. Status: ${approved.length}/7 approved.`);
    } catch (e) {
      setProtocolResult("PROTOCOL_ERROR: FAILED_TO_CALCULATE_CONSENSUS");
    } finally {
      setExecuting(false);
    }
  };

  const approvedCount = Object.values(positions).filter(v => v === 'approved').length;
  const isConsensus = approvedCount >= 5;

  const currentSoldier = SOLDIERS.find(s => s.id === selectedSoldierId);

  useEffect(() => {
    if (isConsensus) {
      epistemic.logEvent("SupermajorityReached", "DAO Board has validated a supermajority directive.");
    }
  }, [isConsensus]);

  return (
    <div className={`dao-substrate ${isConsensus ? 'consensus-active' : ''}`}>
      <div className="dao-zones">
        <div 
          className={`drop-zone reject ${draggedId ? 'highlight-active' : ''}`} 
          onDragOver={e => e.preventDefault()} 
          onDrop={e => onDrop(e, 'rejected')}
        >
          <div className="zone-label-wrap">
            <span className="zone-icon">×</span>
            <label>REJECTED_DIRECTIVE</label>
          </div>
          <div className="zone-content">
            {SOLDIERS.filter(s => positions[s.id] === 'rejected').map(s => (
              <div 
                key={s.id} 
                draggable 
                onDragStart={e => onDragStart(e, s.id)} 
                onDragEnd={onDragEnd}
                className="soldier-token"
                style={{ '--s-color': s.color } as any}
                onClick={() => setSelectedSoldierId(s.id)}
              >
                {s.id}
              </div>
            ))}
          </div>
        </div>

        <div 
          className="drop-zone pool" 
          onDragOver={e => e.preventDefault()} 
          onDrop={e => onDrop(e, 'pool')}
        >
          <div className="zone-label-wrap">
            <label>AGENT_AWAITING_POOL</label>
          </div>
          <div className="zone-content">
            {SOLDIERS.filter(s => positions[s.id] === 'pool').map(s => (
              <div 
                key={s.id} 
                draggable 
                onDragStart={e => onDragStart(e, s.id)} 
                onDragEnd={onDragEnd}
                className="soldier-token"
                style={{ '--s-color': s.color } as any}
                onClick={() => setSelectedSoldierId(s.id)}
              >
                {s.id}
              </div>
            ))}
          </div>
        </div>

        <div 
          className={`drop-zone approve ${draggedId ? 'highlight-active' : ''}`} 
          onDragOver={e => e.preventDefault()} 
          onDrop={e => onDrop(e, 'approved')}
        >
          <div className="zone-label-wrap">
            <span className="zone-icon">✓</span>
            <label>APPROVED_DIRECTIVE</label>
          </div>
          <div className="zone-content">
            {SOLDIERS.filter(s => positions[s.id] === 'approved').map(s => (
              <div 
                key={s.id} 
                draggable 
                onDragStart={e => onDragStart(e, s.id)} 
                onDragEnd={onDragEnd}
                className="soldier-token"
                style={{ '--s-color': s.color } as any}
                onClick={() => setSelectedSoldierId(s.id)}
              >
                {s.id}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="executive-view-panel">
        <div className="executive-selector-group">
            <div className="selector-title">
               <span className="panel-label">SOLDIER_TELEMETRY</span>
               <div className="pulse-indicator"></div>
            </div>
            <select 
                className="soldier-dropdown" 
                value={selectedSoldierId} 
                onChange={(e) => setSelectedSoldierId(e.target.value)}
            >
                {SOLDIERS.map(s => (
                    <option key={s.id} value={s.id}>{s.id} — {s.name}</option>
                ))}
            </select>
        </div>

        <div className="panel-main-content">
            {currentSoldier && (
                <div className="soldier-detail-card" style={{ borderLeft: `4px solid ${currentSoldier.color}` }}>
                    <div className="detail-row">
                        <span className="attr">AGENT_IDENTITY:</span>
                        <span className="val">{currentSoldier.name}</span>
                    </div>
                    <div className="detail-row">
                        <span className="attr">STRATEGIC_FOCUS:</span>
                        <span className="val">{currentSoldier.focus}</span>
                    </div>
                    <div className="detail-row">
                        <span className="attr">BOARD_ALIGNMENT:</span>
                        <span className="val" style={{ color: currentSoldier.color }}>{positions[currentSoldier.id].toUpperCase()}</span>
                    </div>
                </div>
            )}

            <div className="protocol-action-card glass-panel">
                <button className="execute-btn" onClick={executeProtocol} disabled={executing}>
                   {executing ? "CALCULATING_CONSENSUS..." : "GENERATE_CONSENSUS_REPORT"}
                </button>
                {protocolResult && (
                  <div className="protocol-result-scroll">
                     <div className="markdown-content" dangerouslySetInnerHTML={{ __html: marked.parse(protocolResult) as string }} />
                  </div>
                )}
            </div>
        </div>
      </div>

      <div className={`consensus-meter-container ${isConsensus ? 'reached' : ''}`}>
         <div className="meter-header">
            <div className="meter-title">SUPERMAJORITY_THRESHOLD</div>
            <div className="meter-stats">{approvedCount} / 5 AGENTS</div>
         </div>
         <div className="meter-track">
            <div className="meter-fill" style={{ width: `${Math.min(100, (approvedCount / 5) * 100)}%` }}>
               <div className="fill-glow"></div>
            </div>
            <div className="meter-marker" style={{ left: '100%' }}></div>
         </div>
         <div className="meter-status-text">
            {isConsensus 
              ? <span className="text-pulse">DIRECTIVE_VALIDATED_BY_SUPERMAJORITY</span> 
              : `REMAINING_VOTES: ${Math.max(0, 5 - approvedCount)}`
            }
         </div>
      </div>
    </div>
  );
};
