
/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactDOM from 'react-dom/client';
import { GoogleGenAI } from "@google/genai";
import { marked } from "marked";
import hljs from "highlight.js";

interface Message {
    text: string;
    sender: 'user' | 'ai';
    grounding?: any[];
}

interface Persona {
    id: string;
    name: string;
    description: string;
    instruction: string;
}

interface ModuleState {
    id: string;
    x: number;
    y: number;
    w: number;
    h: number;
    isDecoupled: boolean;
    isOpen: boolean;
    zIndex: number;
}

const TOOLTIP_MAP: Record<string, string> = {
    "PYTHAI": "The central mastermind and parent organization (pythai.net).",
    "pythaiml": "Advanced machine learning libraries for the augmentic stack.",
    "openmind": "Dojo layer for ideation and strategic modeling.",
    "openmindX": "The bridge translating hazırlık into action.",
    "mindX": "Execution authority commanding the Seven Soldiers.",
    "openDAO": "Governance layer providing decentralized legitimacy.",
    "BANKON": "Identity infrastructure (bankon.dmg.finance).",
    "RAGE": "Retrieval-Augmented Generative Engine mode.",
    "Tier A": "Cryptographic offline voting proof (ERC-1271)."
};

const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
        style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 2
    }).format(value);
};

const SOLDIERS = [
    { id: 'COO', name: 'Operations' }, { id: 'CFO', name: 'Finance' },
    { id: 'CTO', name: 'Technology' }, { id: 'CISO', name: 'Security' },
    { id: 'CLO', name: 'Legal' }, { id: 'CPO', name: 'Product' },
    { id: 'CRO', name: 'Risk' }
];

const App = () => {
    // Neural States
    const [messages, setMessages] = useState<Message[]>([
        { text: "Neural link established. **PYTHAI // THE ROOT** online.\nStatus: Parent organization active. Ecosystem components (mindX, openmind, BANKON) stabilized.", sender: 'ai' }
    ]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isRageMode, setIsRageMode] = useState(false);
    const [directiveMode, setDirectiveMode] = useState<'DIRECT' | 'DOJO' | 'BANKON'>('DIRECT');

    // Persona/Identity Substrate
    const [personas, setPersonas] = useState<Persona[]>([]);
    const [activePersona, setActivePersona] = useState<Persona | null>(null);
    const [isPersonaMenuOpen, setIsPersonaMenuOpen] = useState(false);

    // Module Order & Layout
    const [moduleOrder, setModuleOrder] = useState<string[]>(['resp', 'input', 'soldiers', 'dao', 'bankon', 'dojo', 'llama', 'diag']);
    const [modules, setModules] = useState<Record<string, ModuleState>>({
        resp: { id: 'resp', x: 0, y: 0, w: 680, h: 420, isDecoupled: false, isOpen: true, zIndex: 10 },
        input: { id: 'input', x: 0, y: 0, w: 680, h: 260, isDecoupled: false, isOpen: true, zIndex: 11 },
        soldiers: { id: 'soldiers', x: 0, y: 0, w: 680, h: 220, isDecoupled: false, isOpen: true, zIndex: 12 },
        dao: { id: 'dao', x: 0, y: 0, w: 680, h: 180, isDecoupled: false, isOpen: true, zIndex: 13 },
        bankon: { id: 'bankon', x: 0, y: 0, w: 680, h: 160, isDecoupled: false, isOpen: true, zIndex: 14 },
        dojo: { id: 'dojo', x: 0, y: 0, w: 680, h: 200, isDecoupled: false, isOpen: false, zIndex: 15 },
        llama: { id: 'llama', x: 0, y: 0, w: 680, h: 450, isDecoupled: false, isOpen: false, zIndex: 16 },
        diag: { id: 'diag', x: 0, y: 0, w: 680, h: 140, isDecoupled: false, isOpen: true, zIndex: 17 }
    });

    // Real-time Sims
    const [diagnostics, setDiagnostics] = useState({ load: 2, mem: 34, status: 'STABLE' });
    const [soldierStatus, setSoldierStatus] = useState<Record<string, boolean>>(Object.fromEntries(SOLDIERS.map(s => [s.id, true])));
    const [daoStatus, setDaoStatus] = useState({ dev: 0.94, mkt: 0.82, comm: 0.76 });

    const activeDrag = useRef<string | null>(null);
    const dragOffset = useRef({ x: 0, y: 0 });
    const topZ = useRef(50);
    const chatWindowRef = useRef<HTMLDivElement>(null);
    const textAreaRef = useRef<HTMLTextAreaElement>(null);

    // Reordering Ladder logic
    const resetAllPositions = useCallback(() => {
        const isMobile = window.innerWidth < 768;
        const w = isMobile ? window.innerWidth * 0.96 : 680;
        const startX = (window.innerWidth - w) / 2;
        let currentY = 70;

        setModules(prev => {
            const updated = { ...prev };
            moduleOrder.forEach(id => {
                if (updated[id].isOpen && !updated[id].isDecoupled) {
                    updated[id] = { ...updated[id], x: startX, y: currentY, w: w };
                    currentY += updated[id].h + 15;
                }
            });
            return updated;
        });
    }, [moduleOrder]);

    useEffect(() => {
        resetAllPositions();
        fetch('/persona.json').then(res => res.json()).then(data => {
            setPersonas(data.personas);
            setActivePersona(data.personas[0]);
        });

        const interval = setInterval(() => {
            setDiagnostics(d => ({ ...d, load: 1 + Math.random() * 5, mem: 34 + Math.random() * 2 }));
            setSoldierStatus(prev => ({ ...prev, [SOLDIERS[Math.floor(Math.random() * 7)].id]: Math.random() > 0.05 }));
        }, 5000);
        return () => clearInterval(interval);
    }, [resetAllPositions]);

    const handleMouseDown = (e: React.MouseEvent | React.TouchEvent, id: string, type: 'drag' | 'resize') => {
        const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
        const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;

        if ((e.target as HTMLElement).closest('button') || 
            (e.target as HTMLElement).closest('.persona-menu') ||
            (e.target as HTMLElement).closest('textarea') ||
            (e.target as HTMLElement).closest('input')) return;

        topZ.current += 1;
        setModules(prev => ({ ...prev, [id]: { ...prev[id], zIndex: topZ.current } }));

        if (type === 'drag') {
            activeDrag.current = id;
            dragOffset.current = { x: clientX - modules[id].x, y: clientY - modules[id].y };
        }
    };

    useEffect(() => {
        const handleMove = (e: MouseEvent | TouchEvent) => {
            if (!activeDrag.current) return;
            const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
            const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;
            const id = activeDrag.current;
            const mod = modules[id];

            setModules(prev => ({
                ...prev,
                [id]: { ...prev[id], x: clientX - dragOffset.current.x, y: clientY - dragOffset.current.y }
            }));

            if (!mod.isDecoupled) {
                const currentIdx = moduleOrder.indexOf(id);
                const neighborYThreshold = 30; 

                if (currentIdx > 0) {
                    const aboveId = moduleOrder[currentIdx - 1];
                    const aboveMod = modules[aboveId];
                    if (clientY < aboveMod.y + aboveMod.h / 2) {
                        setModuleOrder(prev => {
                            const next = [...prev];
                            [next[currentIdx - 1], next[currentIdx]] = [next[currentIdx], next[currentIdx - 1]];
                            return next;
                        });
                    }
                }
                if (currentIdx < moduleOrder.length - 1) {
                    const belowId = moduleOrder[currentIdx + 1];
                    const belowMod = modules[belowId];
                    if (clientY > belowMod.y + neighborYThreshold) {
                        setModuleOrder(prev => {
                            const next = [...prev];
                            [next[currentIdx + 1], next[currentIdx]] = [next[currentIdx], next[currentIdx + 1]];
                            return next;
                        });
                    }
                }
            }
        };

        const handleUp = () => {
            if (activeDrag.current) {
                activeDrag.current = null;
                resetAllPositions();
            }
        };

        window.addEventListener('mousemove', handleMove);
        window.addEventListener('mouseup', handleUp);
        return () => {
            window.removeEventListener('mousemove', handleMove);
            window.removeEventListener('mouseup', handleUp);
        };
    }, [modules, moduleOrder, resetAllPositions]);

    const handleSendMessage = async (textOverride?: string) => {
        const finalContent = textOverride || inputValue;
        if (!finalContent.trim() || isLoading) return;
        const msg = (directiveMode === 'DOJO' ? '[DOJO_PREP] ' : directiveMode === 'BANKON' ? '[BANKON_IDENTITY] ' : '') + finalContent;
        setMessages(prev => [...prev, { text: msg, sender: 'user' }, { text: '', sender: 'ai' }]);
        setInputValue('');
        setIsLoading(true);

        try {
            const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
            const response = await ai.models.generateContent({
                model: 'gemini-3-pro-preview',
                contents: msg,
                config: { 
                    systemInstruction: `${activePersona?.instruction || "You are PYTHAI."} Respond as the Mastermind Root of pythai.net. RAGE_MODE: ${isRageMode ? 'ACTIVE' : 'OFF'}.`,
                    tools: [{ googleMaps: {} }, { googleSearch: {} }]
                }
            });
            const text = response.text || "Direct cognitive link disruption.";
            setMessages(prev => {
                const next = [...prev];
                next[next.length - 1] = { text, sender: 'ai', grounding: response.candidates?.[0]?.groundingMetadata?.groundingChunks };
                return next;
            });
        } catch (e) {
            setMessages(prev => [...prev.slice(0, -1), { text: "Neural substrate error: link severed.", sender: 'ai' }]);
        } finally {
            setIsLoading(false);
            if (textAreaRef.current) textAreaRef.current.focus();
        }
    };

    const wrapK = (text: string) => {
        let res = text;
        ["PYTHAI", "mindX", "openmind", "openmindX", "openDAO", "BANKON", "RAGE"].forEach(k => {
            const reg = new RegExp(`\\b${k}\\b`, 'g');
            res = res.replace(reg, `<span class="keyword-highlight" data-tooltip="${TOOLTIP_MAP[k]}">${k}</span>`);
        });
        return res;
    };

    const renderModule = (id: string, title: string, content: React.ReactNode) => {
        const mod = modules[id];
        if (!mod.isOpen) return null;
        return (
            <div 
                className={`module ${id}-module ${mod.isDecoupled ? 'decoupled' : 'linked'}`}
                style={{ left: mod.x, top: mod.y, width: mod.w, height: mod.h, zIndex: mod.zIndex }}
                onMouseDown={(e) => handleMouseDown(e, id, 'drag')}
            >
                <div className="module-handle">
                    <span className="ladder-pos">#{moduleOrder.indexOf(id) + 1}</span>
                    <span className="handle-title">{title}</span>
                    <div className="mod-controls">
                        <button onClick={(e) => { e.stopPropagation(); setModules(prev => ({...prev, [id]: {...prev[id], isDecoupled: !prev[id].isDecoupled}})) }}>{mod.isDecoupled ? '⚓' : '🔗'}</button>
                        <button onClick={(e) => { e.stopPropagation(); setModules(prev => ({...prev, [id]: {...prev[id], isOpen: false}})) }}>×</button>
                    </div>
                </div>
                <div className="module-inner">{content}</div>
            </div>
        );
    };

    const toggleModule = (id: string) => {
        setModules(prev => ({ ...prev, [id]: { ...prev[id], isOpen: !prev[id].isOpen } }));
        setTimeout(resetAllPositions, 0);
    };

    const handleQuickAction = (action: string) => {
        setInputValue(action);
        if (textAreaRef.current) textAreaRef.current.focus();
    };

    return (
        <div className={`workspace ${isRageMode ? 'rage-active' : ''}`}>
            {/* Control Bar */}
            <div className="substrate-control-bar">
                <div className="bar-logo">
                    <img src="https://agenticplace.pythai.net/agentaitrans.png" className="bar-img" />
                    <span>PYTHAI_MASTERMIND // ROOT</span>
                </div>
                <div className="bar-buttons">
                    {['resp', 'input', 'soldiers', 'dao', 'bankon', 'dojo', 'llama', 'diag'].map(id => (
                        <button key={id} className={modules[id].isOpen ? 'active' : ''} onClick={() => toggleModule(id)}>
                            {id.toUpperCase()}
                        </button>
                    ))}
                </div>
                <button className="stack-btn" onClick={resetAllPositions}>STABILIZE_LADDER</button>
            </div>

            {renderModule('resp', `PYTHAI // ${activePersona?.name || 'MASTERMIND'}`, (
                <>
                    <header className="inner-header">
                        <button className="persona-btn" onClick={() => setIsPersonaMenuOpen(!isPersonaMenuOpen)}>
                            {activePersona?.id.toUpperCase()} IDENTITY
                        </button>
                        {isPersonaMenuOpen && (
                            <div className="persona-menu">
                                {personas.map(p => (
                                    <div key={p.id} className={`persona-item ${activePersona?.id === p.id ? 'active' : ''}`} onClick={() => { setActivePersona(p); setIsPersonaMenuOpen(false); }}>
                                        <b>{p.name}</b>
                                        <p>{p.description}</p>
                                    </div>
                                ))}
                            </div>
                        )}
                        <a href="https://pythai.net" target="_blank" className="ecosystem-link">PYTHAI.NET</a>
                    </header>
                    <div ref={chatWindowRef} className="chat-area">
                        {messages.map((m, i) => (
                            <div key={i} className={`message ${m.sender}`}>
                                <div dangerouslySetInnerHTML={{ __html: wrapK(marked.parse(m.text) as string) }} />
                                {m.grounding && (
                                    <div className="grounding-box">
                                        {m.grounding.map((c: any, ci: number) => {
                                            const s = c.web || c.maps;
                                            return s ? <a key={ci} href={s.uri} target="_blank">[{s.title || 'Source'}]</a> : null;
                                        })}
                                    </div>
                                )}
                            </div>
                        ))}
                        {isLoading && <div className="loading-ping">Neural processing...</div>}
                        <div id="chat-end"></div>
                    </div>
                </>
            ))}

            {renderModule('input', 'DIRECTIVE_TRANSMITTER', (
                <div className="input-substrate">
                    <div className="directive-controls">
                        <button className={directiveMode === 'DIRECT' ? 'active' : ''} onClick={() => setDirectiveMode('DIRECT')}>DIRECT</button>
                        <button className={directiveMode === 'DOJO' ? 'active' : ''} onClick={() => setDirectiveMode('DOJO')}>DOJO_PREP</button>
                        <button className={directiveMode === 'BANKON' ? 'active' : ''} onClick={() => setDirectiveMode('BANKON')}>IDENTITY_PROOF</button>
                        <div className="rage-toggle">
                            <label>RAGE_ENGINE</label>
                            <button className={isRageMode ? 'on' : 'off'} onClick={() => setIsRageMode(!isRageMode)}>{isRageMode ? 'ONLINE' : 'OFFLINE'}</button>
                        </div>
                    </div>
                    <form className="input-form" onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }}>
                        <textarea 
                            ref={textAreaRef}
                            value={inputValue} 
                            onChange={(e) => setInputValue(e.target.value)} 
                            placeholder="your wish is mind command"
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleSendMessage();
                                }
                            }}
                        />
                        <button type="submit" disabled={isLoading}>TRANSMIT</button>
                    </form>
                    <div className="tactical-actions">
                        <button onClick={() => handleQuickAction("Summarize current substrate state")}>SUMMARIZE</button>
                        <button onClick={() => handleQuickAction("Analyze executive consensus")}>ANALYZE</button>
                        <button onClick={() => handleQuickAction("Propose architectural refinement")}>FORGE</button>
                        <button onClick={() => setMessages([{ text: "Neural history purged. Baseline link re-established.", sender: 'ai' }])}>PURGE</button>
                    </div>
                </div>
            ))}

            {renderModule('soldiers', 'MINDX // EXECUTIVE_COMMAND', (
                <div className="soldiers-substrate">
                    <div className="soldier-grid">
                        {SOLDIERS.map(s => (
                            <div key={s.id} className="soldier-card">
                                <label>{s.id}</label>
                                <div className={`status-dot ${soldierStatus[s.id] ? 'alive' : 'stale'}`}></div>
                                <span className="s-name">{s.name}</span>
                            </div>
                        ))}
                    </div>
                    <div className="consensus-meter">
                        <label>2/3 SUPERMAJORITY REQUIRED</label>
                        <div className="meter-bar"><div className="fill" style={{ width: `${(Object.values(soldierStatus).filter(v => v).length / 7) * 100}%` }}></div></div>
                    </div>
                </div>
            ))}

            {renderModule('dao', 'OPENDAO // GOVERNANCE_LEGITIMACY', (
                <div className="dao-substrate">
                    <div className="dao-grid">
                        {['dev', 'mkt', 'comm'].map(d => (
                            <div key={d} className="domain-card">
                                <label>{d.toUpperCase()}</label>
                                <div className="domain-val">{(daoStatus[d as keyof typeof daoStatus] * 100).toFixed(0)}%</div>
                                <div className="progress"><div className="fill" style={{ width: `${daoStatus[d as keyof typeof daoStatus] * 100}%` }}></div></div>
                            </div>
                        ))}
                    </div>
                </div>
            ))}

            {renderModule('bankon', 'BANKON // IDENTITY_LAYER', (
                <div className="bankon-substrate">
                    <div className="proof-row">
                        <div className="proof-item"><label>STATE</label><span className="proof-val neon-text">SOVEREIGN</span></div>
                        <div className="proof-item"><label>WALLET</label><span className="proof-val">0x...1271</span></div>
                        <div className="proof-item"><label>TIER</label><span className="proof-val">TIER_A</span></div>
                    </div>
                </div>
            ))}

            {renderModule('diag', 'SUBSTRATE_DIAGNOSTICS', (
                <div className="diag-substrate">
                    <div className="diag-row"><span>RAGE_STATUS:</span> <span className="neon-text">{isRageMode ? 'MAX_OPTIMAL' : 'IDLE'}</span></div>
                    <div className="diag-row"><span>COGNITIVE_LOAD:</span> <span>{diagnostics.load.toFixed(1)}%</span></div>
                    <div className="diag-row"><span>MEMORY:</span> <span>{diagnostics.mem.toFixed(0)}GB</span></div>
                    <div className="meter-bar"><div className="fill" style={{ width: `${diagnostics.load * 10}%` }}></div></div>
                </div>
            ))}
        </div>
    );
};

const root = ReactDOM.createRoot(document.getElementById('root')!);
root.render(<App />);
