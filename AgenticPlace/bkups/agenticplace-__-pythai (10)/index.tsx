
/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactDOM from 'react-dom/client';
import { GoogleGenAI } from "@google/genai";
import { marked } from "marked";
import hljs from "highlight.js";
import { epistemic, LogEntry } from './epistemic.ts';

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
    "openDAO": "Governance layer (github.com/daonow) providing decentralized legitimacy.",
    "BANKON": "Identity infrastructure (bankon.dmg.finance).",
    "RAGE": "Retrieval Augmented Generative Engine powering the Knowledge Economy.",
    "Tier A": "Cryptographic offline voting proof (ERC-1271)."
};

const SOLDIERS = [
    { id: 'COO', name: 'Operations' }, { id: 'CFO', name: 'Finance' },
    { id: 'CTO', name: 'Technology' }, { id: 'CISO', name: 'Security' },
    { id: 'CLO', name: 'Legal' }, { id: 'CPO', name: 'Product' },
    { id: 'CRO', name: 'Risk' }
];

const NEURAL_PRESETS = [
    { id: 'rage_strat', label: 'RAGE_STRATEGY', prompt: 'Formulate a Knowledge Economy strategy to monetize data assets via RAGE: ' },
    { id: 'strategy', label: 'STRATEGIC_LEVEL_5', prompt: 'Analyze from a high-level architectural perspective: ' },
    { id: 'code', label: 'CODE_ORCHESTRATOR', prompt: 'Refactor or audit following mindX standards: ' },
    { id: 'dao', label: 'DAO_CONSENSUS', prompt: 'Model 2/3 supermajority legitimacy for: ' }
];

const App = () => {
    // Neural States
    const [messages, setMessages] = useState<Message[]>([
        { text: "Neural link established. **PYTHAI // THE ROOT** online.\nStatus: Parent organization active. Ecosystem components (mindX, openmind, BANKON) stabilized.\n3D depth perspective layer: ACTIVE.\n**RAGE ENGINE** initialized: Ready to fuel the Knowledge Economy.", sender: 'ai' }
    ]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isRageMode, setIsRageMode] = useState(false);
    const [directiveMode, setDirectiveMode] = useState<'DIRECT' | 'DOJO' | 'BANKON'>('DIRECT');
    
    // Knowledge State
    const [logs, setLogs] = useState<LogEntry[]>([]);

    // Persona/Identity Substrate
    const [personas, setPersonas] = useState<Persona[]>([]);
    const [activePersona, setActivePersona] = useState<Persona | null>(null);
    const [isPersonaMenuOpen, setIsPersonaMenuOpen] = useState(false);

    // Module Order & Layout
    const [moduleOrder, setModuleOrder] = useState<string[]>(['resp', 'input', 'manifesto', 'soldiers', 'dao', 'bankon', 'logs', 'viz', 'diag']);
    const [modules, setModules] = useState<Record<string, ModuleState>>({
        resp: { id: 'resp', x: 0, y: 0, w: 680, h: 420, isDecoupled: false, isOpen: true, zIndex: 10 },
        input: { id: 'input', x: 0, y: 0, w: 680, h: 360, isDecoupled: false, isOpen: true, zIndex: 11 },
        manifesto: { id: 'manifesto', x: 0, y: 0, w: 680, h: 320, isDecoupled: false, isOpen: false, zIndex: 12 },
        soldiers: { id: 'soldiers', x: 0, y: 0, w: 680, h: 220, isDecoupled: false, isOpen: true, zIndex: 13 },
        dao: { id: 'dao', x: 0, y: 0, w: 680, h: 200, isDecoupled: false, isOpen: true, zIndex: 14 },
        bankon: { id: 'bankon', x: 0, y: 0, w: 680, h: 160, isDecoupled: false, isOpen: true, zIndex: 15 },
        logs: { id: 'logs', x: 0, y: 0, w: 680, h: 300, isDecoupled: false, isOpen: false, zIndex: 16 },
        viz: { id: 'viz', x: 0, y: 0, w: 680, h: 250, isDecoupled: false, isOpen: true, zIndex: 17 },
        diag: { id: 'diag', x: 0, y: 0, w: 680, h: 140, isDecoupled: false, isOpen: true, zIndex: 18 }
    });

    const [diagnostics, setDiagnostics] = useState({ load: 2, mem: 34, status: 'STABLE' });
    const [soldierStatus, setSoldierStatus] = useState<Record<string, boolean>>(Object.fromEntries(SOLDIERS.map(s => [s.id, true])));
    const [daoStatus, setDaoStatus] = useState({ dev: 0.94, mkt: 0.82, comm: 0.76 });

    const activeDrag = useRef<string | null>(null);
    const dragOffset = useRef({ x: 0, y: 0 });
    const topZ = useRef(50);
    const workspaceRef = useRef<HTMLDivElement>(null);
    const textAreaRef = useRef<HTMLTextAreaElement>(null);

    const resetAllPositions = useCallback(() => {
        const isMobile = window.innerWidth < 768;
        const w = isMobile ? window.innerWidth * 0.96 : 680;
        const startX = (window.innerWidth - w) / 2;
        let currentY = 70;

        setModules(prev => {
            const updated = { ...prev };
            moduleOrder.forEach(id => {
                const mod = updated[id];
                if (mod && mod.isOpen && !mod.isDecoupled) {
                    updated[id] = { ...mod, x: startX, y: currentY, w: w };
                    currentY += mod.h + 15;
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

        // Initialize Logs
        setLogs(epistemic.getLogs());
        const unsubscribe = epistemic.subscribe(() => {
            setLogs(epistemic.getLogs());
        });

        const interval = setInterval(() => {
            setDiagnostics(d => ({ ...d, load: 1 + Math.random() * 5, mem: 34 + Math.random() * 2 }));
            setSoldierStatus(prev => ({ ...prev, [SOLDIERS[Math.floor(Math.random() * 7)].id]: Math.random() > 0.05 }));
        }, 5000);

        return () => {
            clearInterval(interval);
            unsubscribe();
        };
    }, [resetAllPositions]);

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!workspaceRef.current) return;
            const x = (e.clientX / window.innerWidth - 0.5) * 5; 
            const y = (e.clientY / window.innerHeight - 0.5) * -5;
            workspaceRef.current.style.setProperty('--x-rotation', `${y}deg`);
            workspaceRef.current.style.setProperty('--y-rotation', `${x}deg`);
        };
        window.addEventListener('mousemove', handleMouseMove);
        return () => window.removeEventListener('mousemove', handleMouseMove);
    }, []);

    const handleMouseDown = (e: React.MouseEvent | React.TouchEvent, id: string) => {
        const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
        const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;

        if ((e.target as HTMLElement).closest('button') || 
            (e.target as HTMLElement).closest('.persona-menu') ||
            (e.target as HTMLElement).closest('textarea') ||
            (e.target as HTMLElement).closest('select') ||
            (e.target as HTMLElement).closest('input')) return;

        topZ.current += 1;
        setModules(prev => ({ ...prev, [id]: { ...prev[id], zIndex: topZ.current } }));

        activeDrag.current = id;
        dragOffset.current = { x: clientX - modules[id].x, y: clientY - modules[id].y };
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
                
                moduleOrder.forEach((otherId, otherIdx) => {
                    if (otherId === id) return;
                    const otherMod = modules[otherId];
                    if (!otherMod || !otherMod.isOpen || otherMod.isDecoupled) return;

                    const midY = otherMod.y + otherMod.h / 2;
                    if (currentIdx < otherIdx && clientY > midY) {
                        setModuleOrder(prev => {
                            const next = [...prev];
                            const temp = next[currentIdx];
                            next[currentIdx] = next[otherIdx];
                            next[otherIdx] = temp;
                            return next;
                        });
                    } else if (currentIdx > otherIdx && clientY < midY) {
                        setModuleOrder(prev => {
                            const next = [...prev];
                            const temp = next[currentIdx];
                            next[currentIdx] = next[otherIdx];
                            next[otherIdx] = temp;
                            return next;
                        });
                    }
                });
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
        window.addEventListener('touchmove', handleMove);
        window.addEventListener('touchend', handleUp);
        return () => {
            window.removeEventListener('mousemove', handleMove);
            window.removeEventListener('mouseup', handleUp);
            window.removeEventListener('touchmove', handleMove);
            window.removeEventListener('touchend', handleUp);
        };
    }, [modules, moduleOrder, resetAllPositions]);

    const handleQuickAction = (action: string) => {
        handleSendMessage(action);
    };

    const toggleModule = (id: string) => {
        setModules(prev => ({
            ...prev,
            [id]: { ...prev[id], isOpen: !prev[id].isOpen }
        }));
    };

    const handleSendMessage = async (textOverride?: string) => {
        const finalContent = textOverride || inputValue;
        if (!finalContent.trim() || isLoading) return;
        
        const prefix = directiveMode === 'DOJO' ? '[DOJO_PREP] ' : directiveMode === 'BANKON' ? '[BANKON_IDENTITY] ' : '';
        const msg = prefix + finalContent;
        
        setMessages(prev => [...prev, { text: msg, sender: 'user' }, { text: '', sender: 'ai' }]);
        setInputValue('');
        setIsLoading(true);

        epistemic.logEvent("userDirective", "Transmitting directive to neural root", { content: msg, rage_mode: isRageMode });

        try {
            const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
            
            // Construct RAGE-enhanced instruction if active
            let systemInst = `${activePersona?.instruction || "You are PYTHAI."} Reference links: pythai.net, agenticplace.pythai.net, mindx.pythai.net. Respond as the Parent Root.`;
            
            if (isRageMode) {
                systemInst += `\n**RAGE MODE ACTIVE**: You are a strategist in the Knowledge Economy. 
                Use Retrieval Augmented Generation to organize intellectual capital. 
                Focus on data monetization, real-time insights, and predictive analytics. 
                Reference the RAGE engine (Retrieval Augmented Generative Engine) as the core driver of modern Business Intelligence.`;
            }

            const response = await ai.models.generateContent({
                model: 'gemini-3-pro-preview',
                contents: msg,
                config: { 
                    systemInstruction: systemInst,
                    tools: [{ googleSearch: {} }]
                }
            });
            const text = response.text || "Neural link failure.";
            
            // Index Knowledge
            const topic = isRageMode ? "KnowledgeEconomy" : (activePersona?.name || "General");
            epistemic.addKnowledge(topic, text.substring(0, 800)); 

            setMessages(prev => {
                const next = [...prev];
                next[next.length - 1] = { text, sender: 'ai', grounding: response.candidates?.[0]?.groundingMetadata?.groundingChunks };
                return next;
            });
        } catch (e: any) {
            epistemic.logEvent("error", "Cognitive link disruption", { error: e.message });
            setMessages(prev => [...prev.slice(0, -1), { text: "Neural link disruption: 404.", sender: 'ai' }]);
        } finally {
            setIsLoading(false);
            if (textAreaRef.current) textAreaRef.current.focus();
        }
    };

    const wrapK = (text: string) => {
        let res = text;
        Object.keys(TOOLTIP_MAP).forEach(k => {
            const reg = new RegExp(`\\b${k}\\b`, 'g');
            res = res.replace(reg, `<span class="keyword-highlight" data-tooltip="${TOOLTIP_MAP[k]}">${k}</span>`);
        });
        return res;
    };

    const renderModule = (id: string, title: string, content: React.ReactNode) => {
        const mod = modules[id];
        if (!mod || !mod.isOpen) return null;
        return (
            <div 
                className={`module ${id}-module ${mod.isDecoupled ? 'decoupled' : 'linked'} layer`}
                style={{ 
                    left: mod.x, 
                    top: mod.y, 
                    width: mod.w, 
                    height: mod.h, 
                    zIndex: mod.zIndex 
                }}
                onMouseDown={(e) => handleMouseDown(e, id)}
                onTouchStart={(e) => handleMouseDown(e, id)}
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

    const handleApplyPreset = (prompt: string) => {
        setInputValue(prev => prompt + prev);
        if (textAreaRef.current) textAreaRef.current.focus();
    };

    return (
        <div ref={workspaceRef} className={`workspace ${isRageMode ? 'rage-active' : ''}`}>
            {/* Top Command Bar */}
            <div className="substrate-control-bar layer depth-layer-near">
                <div className="bar-logo">
                    <img src="https://agenticplace.pythai.net/agentaitrans.png" className="bar-img" />
                    <span>PYTHAI_MASTERMIND // ROOT</span>
                </div>
                <div className="bar-links">
                    <a href="https://pythai.net" target="_blank">PYTHAI</a>
                    <a href="https://agenticplace.pythai.net" target="_blank">AGENTIC</a>
                    <a href="https://mindx.pythai.net" target="_blank">MINDX</a>
                </div>
                <div className="bar-buttons">
                    {Object.keys(modules).map(id => (
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
                        <span className="persona-tagline">Link: agenticplace.pythai.net</span>
                    </header>
                    <div className="chat-area">
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
                    </div>
                </>
            ))}

            {renderModule('input', 'DIRECTIVE_TRANSMITTER', (
                <div className="input-substrate">
                    <div className="directive-controls">
                        <div className="mode-selector">
                            <button className={directiveMode === 'DIRECT' ? 'active' : ''} onClick={() => setDirectiveMode('DIRECT')}>DIRECT</button>
                            <button className={directiveMode === 'DOJO' ? 'active' : ''} onClick={() => setDirectiveMode('DOJO')}>DOJO_PREP</button>
                            <button className={directiveMode === 'BANKON' ? 'active' : ''} onClick={() => setDirectiveMode('BANKON')}>IDENTITY</button>
                        </div>
                        <div className="neural-preset-control">
                            <label>PRESET:</label>
                            <select onChange={(e) => handleApplyPreset(e.target.value)} value="">
                                <option value="" disabled>--Select--</option>
                                {NEURAL_PRESETS.map(p => <option key={p.id} value={p.prompt}>{p.label}</option>)}
                            </select>
                        </div>
                        <div className="rage-toggle">
                            <label>RAGE</label>
                            <button className={isRageMode ? 'on' : 'off'} onClick={() => setIsRageMode(!isRageMode)}>{isRageMode ? 'ON' : 'OFF'}</button>
                        </div>
                    </div>
                    <form className="input-form" onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }}>
                        <div className="textarea-wrapper">
                            <textarea 
                                ref={textAreaRef}
                                value={inputValue} 
                                onChange={(e) => setInputValue(e.target.value)} 
                                placeholder="your wish is mind command"
                                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(); } }}
                            />
                            <div className="input-meta">
                                <span>{inputValue.length} CHARS</span>
                                <button type="button" className="clear-btn" onClick={() => setInputValue('')}>CLEAR</button>
                            </div>
                        </div>
                        <button type="submit" disabled={isLoading} className="transmit-btn">TRANSMIT</button>
                    </form>
                    <div className="tactical-actions">
                        <button onClick={() => handleQuickAction("Summarize current substrate state")}>SUMMARIZE</button>
                        <button onClick={() => handleQuickAction("Analyze executive consensus")}>ANALYZE</button>
                        <button onClick={() => handleQuickAction("Propose architectural refinement")}>FORGE</button>
                        <button className="danger-action" onClick={() => setMessages([{ text: "Neural history purged. Baseline link re-established.", sender: 'ai' }])}>PURGE</button>
                    </div>
                </div>
            ))}

            {renderModule('manifesto', 'RAGE // MANIFESTO', (
                <div className="manifesto-substrate">
                    <div className="manifesto-content">
                        <h2>The Knowledge Economy & RAGE</h2>
                        <p>The Knowledge Economy thrives on information as a key asset, making data-driven decision-making the foundation of success. RAGE strengthens this economic model by:</p>
                        <ul>
                            <li><strong>Knowledge Discovery:</strong> Automating research and knowledge retrieval.</li>
                            <li><strong>Data Monetization:</strong> Transforming raw data into actionable intelligence assets.</li>
                            <li><strong>Hyperconnectivity:</strong> Integrating cloud computing, IoT, and blockchain for intelligent recommendations.</li>
                        </ul>
                        <div className="cta-box">
                            Organizations that integrate RAGE today will lead tomorrow.
                        </div>
                    </div>
                </div>
            ))}

            {renderModule('logs', 'KNOWLEDGE_LOGS', (
                <div className="logs-substrate">
                    <div className="logs-toolbar">
                        <button onClick={() => setLogs(epistemic.getLogs())}>REFRESH</button>
                        <button className="danger-text" onClick={() => epistemic.clear()}>PURGE_ALL</button>
                    </div>
                    <div className="logs-scroller">
                        {logs.length === 0 ? (
                            <div className="empty-state">No epistemic events recorded.</div>
                        ) : (
                            logs.map((log, i) => (
                                <div key={i} className={`log-entry ${log.eventType}`}>
                                    <div className="log-header">
                                        <span className="log-time">{new Date(log.timestamp).toLocaleTimeString()}</span>
                                        <span className="log-type">{log.eventType.toUpperCase()}</span>
                                    </div>
                                    <div className="log-msg">{log.message}</div>
                                    {log.data && <pre className="log-data">{JSON.stringify(log.data, null, 2)}</pre>}
                                </div>
                            ))
                        )}
                    </div>
                </div>
            ))}

            {renderModule('viz', 'DYNAMIC_3D_VISUALIZER', (
                <div className="viz-substrate">
                    <div className="showcase-element depth-control">
                        <h3>Augmentic Visualizer</h3>
                        <div className="viz-box">
                             <div className="box-face face-front">PYTHAI</div>
                             <div className="box-face face-back">mindX</div>
                             <div className="box-face face-right">mastermind</div>
                             <div className="box-face face-left">BANKON</div>
                             <div className="dao-center">
                                <div className="taijitu">
                                    <div className="dot top"></div>
                                    <div className="dot bottom"></div>
                                </div>
                             </div>
                        </div>
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
                    <div className="dao-footer">
                        <a href="https://github.com/daonow" target="_blank" className="dao-repo-link">
                             GITHUB // daonow
                        </a>
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
