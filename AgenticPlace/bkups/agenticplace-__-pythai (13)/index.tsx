
/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */
import React, { useState, useEffect, useRef } from 'react';
import ReactDOM from 'react-dom/client';
import { GoogleGenAI } from "@google/genai";
import { marked } from "marked";
import { epistemic, LogEntry } from './epistemic.ts';
import { Visualizer, DAOBoard, PersonaSelector } from './SubstrateComponents.tsx';
import { personasData } from './persona.ts';

interface Message {
    text: string;
    sender: 'user' | 'ai';
    persona?: string;
}

interface ResponseWindowState {
    id: string; // Persona ID
    text: string;
    x: number;
    y: number;
    w: number;
    h: number;
    isDecoupled: boolean;
    isCollapsed: boolean;
    zIndex: number;
}

const SECTIONS = [
    { name: "CORE_COMMAND", id: 0, persona: 'pythai' },
    { name: "BOARD_CONSENSUS", id: 1, persona: 'mindx' },
    { name: "SUBSTRATE_TELEMETRY", id: 2, persona: 'rage' }
];

const App = () => {
    const [messages, setMessages] = useState<Message[]>([
        { text: "Neural link established. **PYTHAI // AGENTIC_MASTERMIND** ready for instruction.", sender: 'ai', persona: 'pythai' }
    ]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [activePersona, setActivePersona] = useState('pythai');
    const [showOverlay, setShowOverlay] = useState(false);
    const [overlayState, setOverlayState] = useState<'input' | 'thinking' | 'response'>('input');
    const [overlayResponse, setOverlayResponse] = useState<string>('');
    const [currentSection, setCurrentSection] = useState(0);
    const [logs, setLogs] = useState<LogEntry[]>([]);

    // Console State
    const [consolePos, setConsolePos] = useState({ x: 60, y: 140 });
    const [consoleSize, setConsoleSize] = useState({ w: 560, h: 320 });
    
    // Multi-Response Window State
    const [responseWindows, setResponseWindows] = useState<ResponseWindowState[]>([]);
    const [maxZIndex, setMaxZIndex] = useState(8001);

    const draggingConsole = useRef(false);
    const draggingResponseId = useRef<string | null>(null);
    const resizingConsole = useRef(false);
    const resizingResponseId = useRef<string | null>(null);
    const dragOffset = useRef({ x: 0, y: 0 });

    const getSystemInstruction = (pid: string) => {
        const found = personasData.personas.find(p => p.id === pid) || personasData.personas[0];
        return found.instruction + " Use absolute authority. Format with Markdown.";
    };

    const togglePersonaWindow = (pid: string) => {
        setActivePersona(pid);
        setResponseWindows(prev => {
            const exists = prev.find(w => w.id === pid);
            if (exists) {
                // Move to front
                return prev.map(w => w.id === pid ? { ...w, zIndex: maxZIndex + 1 } : w);
            } else {
                // Create new window with offset
                const offset = prev.length * 30;
                const newWindow: ResponseWindowState = {
                    id: pid,
                    text: `**${pid.toUpperCase()}** SUBSTRATE_LINK: AWAITING_DIRECTIVE...`,
                    x: consolePos.x + 40 + offset,
                    y: consolePos.y + consoleSize.h + 20 + offset,
                    w: 560,
                    h: 300,
                    isDecoupled: false,
                    isCollapsed: false,
                    zIndex: maxZIndex + 1
                };
                return [...prev, newWindow];
            }
        });
        setMaxZIndex(prev => prev + 1);
        epistemic.logEvent("PersonaFocus", `Focus shifted to ${pid.toUpperCase()}. Response conduit established.`);
    };

    const closeResponseWindow = (pid: string) => {
        setResponseWindows(prev => prev.filter(w => w.id !== pid));
        epistemic.logEvent("WindowClosed", `Response conduit for ${pid.toUpperCase()} terminated.`);
    };

    const changeSection = (id: number) => {
        setCurrentSection(id);
        const suggestedPersona = SECTIONS.find(s => s.id === id)?.persona;
        if (suggestedPersona) {
            togglePersonaWindow(suggestedPersona);
            epistemic.logEvent("ContextShift", `Substrate section changed to ${SECTIONS[id].name}. Re-orienting to ${suggestedPersona.toUpperCase()} persona.`);
        }
    };

    const handleSendMessage = async (text: string, isOverlay: boolean = false) => {
        if (!text.trim() || isLoading) return;
        
        if (isOverlay) {
            setOverlayState('thinking');
            setOverlayResponse('');
        } else {
            setMessages(prev => [...prev, { text, sender: 'user' }]);
            setInputValue('');
            // Ensure a window exists for this persona
            const exists = responseWindows.find(w => w.id === activePersona);
            if (!exists) togglePersonaWindow(activePersona);
        }

        setIsLoading(true);

        try {
            const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
            const instruction = getSystemInstruction(activePersona);
            
            const response = await ai.models.generateContent({
                model: 'gemini-3-pro-preview',
                contents: text,
                config: { 
                    systemInstruction: instruction,
                    thinkingConfig: { thinkingBudget: 16000 } 
                }
            });

            const aiText = response.text || "SUBSTRATE_TIMEOUT: NO_DATA_RETURNED";
            
            if (isOverlay) {
                setOverlayResponse(aiText);
                setOverlayState('response');
            } else {
                setMessages(prev => [...prev, { text: aiText, sender: 'ai', persona: activePersona }]);
                // Update the specific persona's window
                setResponseWindows(prev => prev.map(w => 
                    w.id === activePersona 
                    ? { ...w, text: aiText, isCollapsed: false, zIndex: maxZIndex + 1 } 
                    : w
                ));
                setMaxZIndex(prev => prev + 1);
            }
            
            epistemic.logEvent("DirectiveProcessed", `Mode [${activePersona.toUpperCase()}] handled instruction.`);
        } catch (e: any) {
            const err = "CRITICAL_FAILURE: " + e.message;
            if (isOverlay) {
                setOverlayResponse(err);
                setOverlayState('response');
            } else {
                setMessages(prev => [...prev, { text: err, sender: 'ai', persona: activePersona }]);
            }
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (draggingConsole.current) {
                setConsolePos({ x: e.clientX - dragOffset.current.x, y: e.clientY - dragOffset.current.y });
            } else if (resizingConsole.current) {
                setConsoleSize({ w: Math.max(400, e.clientX - consolePos.x), h: Math.max(200, e.clientY - consolePos.y) });
            } else if (draggingResponseId.current) {
                const rid = draggingResponseId.current;
                setResponseWindows(prev => prev.map(w => 
                    w.id === rid 
                    ? { ...w, x: e.clientX - dragOffset.current.x, y: e.clientY - dragOffset.current.y, isDecoupled: true } 
                    : w
                ));
            } else if (resizingResponseId.current) {
                const rid = resizingResponseId.current;
                setResponseWindows(prev => prev.map(w => {
                    if (w.id !== rid) return w;
                    const originX = w.isDecoupled ? w.x : consolePos.x;
                    const originY = w.isDecoupled ? w.y : (consolePos.y + consoleSize.h + 10);
                    return { ...w, w: Math.max(300, e.clientX - originX), h: Math.max(100, e.clientY - originY) };
                }));
            }
        };
        const handleMouseUp = () => {
            draggingConsole.current = false;
            draggingResponseId.current = null;
            resizingConsole.current = false;
            resizingResponseId.current = null;
        };
        window.addEventListener('mousemove', handleMouseMove);
        window.addEventListener('mouseup', handleMouseUp);
        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [consolePos, consoleSize, responseWindows]);

    useEffect(() => {
        const unsubscribeLogs = epistemic.subscribe(() => setLogs(epistemic.getLogs()));
        return () => unsubscribeLogs();
    }, []);

    const copyResponseText = (text: string) => {
        navigator.clipboard.writeText(text);
        epistemic.logEvent("DataExport", "Directive output copied to clipboard.");
    };

    return (
        <div className="app-container">
            <div className="master-backdrop-substrate"></div>

            {/* Draggable Command Console */}
            {currentSection === 0 && !showOverlay && (
                <>
                <div 
                    className="master-console-floating"
                    style={{ left: consolePos.x, top: consolePos.y, width: consoleSize.w, height: consoleSize.h }}
                >
                    <div className="console-handle" onMouseDown={(e) => {
                        draggingConsole.current = true;
                        dragOffset.current = { x: e.clientX - consolePos.x, y: e.clientY - consolePos.y };
                    }}>
                        <div className="handle-left">
                           <div className="console-status-light"></div>
                           <span className="handle-text">PYTHAI // {activePersona.toUpperCase()}_COMMAND_v7.0</span>
                        </div>
                        <div className="handle-dots">•••</div>
                    </div>
                    <div className="console-body">
                        <PersonaSelector current={activePersona} onSelect={togglePersonaWindow} />
                        <textarea 
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            placeholder={`INSTRUCT_${activePersona.toUpperCase()}_CORE...`}
                            onKeyDown={(e) => { if(e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(inputValue); } }}
                        />
                        <div className="console-toolkit">
                            <button className="tool-btn" onClick={() => { setOverlayState('input'); setShowOverlay(true); }}>ASCEND_COMMAND</button>
                            <button className="tool-btn transmit-btn" onClick={() => handleSendMessage(inputValue)}>TRANSMIT</button>
                        </div>
                    </div>
                    <div className="console-resize-handle" onMouseDown={() => resizingConsole.current = true}></div>
                </div>

                {/* Multiple Decoupleable Response Windows */}
                {responseWindows.map((rw) => {
                    const style: React.CSSProperties = rw.isDecoupled 
                        ? { left: rw.x, top: rw.y, width: rw.w, zIndex: rw.zIndex, position: 'fixed' }
                        : { left: consolePos.x + 20, top: consolePos.y + consoleSize.h + 10, width: consoleSize.w, zIndex: rw.zIndex, position: 'fixed' };
                    
                    if (!rw.isCollapsed) style.height = rw.h;
                    else style.height = 'auto';

                    return (
                        <div 
                            key={rw.id}
                            className={`response-window-floating ${rw.isDecoupled ? 'decoupled' : ''} ${rw.isCollapsed ? 'collapsed' : ''} ${activePersona === rw.id ? 'active-focus' : ''}`}
                            style={style}
                            onMouseDown={() => {
                                setResponseWindows(prev => prev.map(w => w.id === rw.id ? { ...w, zIndex: maxZIndex + 1 } : w));
                                setMaxZIndex(prev => prev + 1);
                            }}
                        >
                            <div className="response-handle" onMouseDown={(e) => {
                                draggingResponseId.current = rw.id;
                                const startX = rw.isDecoupled ? rw.x : consolePos.x + 20;
                                const startY = rw.isDecoupled ? rw.y : (consolePos.y + consoleSize.h + 10);
                                dragOffset.current = { x: e.clientX - startX, y: e.clientY - startY };
                            }}>
                                <div className="handle-left">
                                    <span className="handle-text">OUTPUT // {rw.id.toUpperCase()}</span>
                                    {rw.isDecoupled && <span className="decoupled-tag">LINKED</span>}
                                </div>
                                <div className="handle-actions">
                                    <button className="action-btn" onClick={(e) => { e.stopPropagation(); copyResponseText(rw.text); }}>COPY</button>
                                    <button className="action-btn" onClick={(e) => { e.stopPropagation(); setResponseWindows(p => p.map(w => w.id === rw.id ? {...w, isCollapsed: !w.isCollapsed} : w)); }}>
                                        {rw.isCollapsed ? 'EXP' : 'COL'}
                                    </button>
                                    <button className="action-btn close-btn" onClick={(e) => { e.stopPropagation(); closeResponseWindow(rw.id); }}>✕</button>
                                </div>
                            </div>
                            {!rw.isCollapsed && (
                                <div className="response-content-area">
                                    <div className="markdown-content" dangerouslySetInnerHTML={{ __html: marked.parse(rw.text) as string }} />
                                </div>
                            )}
                            {!rw.isCollapsed && <div className="console-resize-handle" onMouseDown={(e) => { e.stopPropagation(); resizingResponseId.current = rw.id; }}></div>}
                        </div>
                    );
                })}
                </>
            )}

            {/* Supreme Directive Overlay */}
            {showOverlay && (
                <div className="supreme-overlay">
                    <button className="close-overlay" onClick={() => { setShowOverlay(false); setOverlayResponse(''); setOverlayState('input'); }}>×</button>
                    <div className={`overlay-portal-container overlay-state-${overlayState}`}>
                        
                        {overlayState === 'input' && (
                            <div className="directive-input-group animate-focus">
                                <div className="overlay-badge">AUTH_LEVEL: ROOT_MASTERMIND // MODE: {activePersona.toUpperCase()}</div>
                                <h2>SUPREME_DIRECTIVE</h2>
                                <textarea 
                                    autoFocus
                                    placeholder="TYPE UNIVERSAL COMMAND..."
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' && !e.shiftKey) {
                                            e.preventDefault();
                                            handleSendMessage(e.currentTarget.value, true);
                                        }
                                    }}
                                />
                                <div className="overlay-hint">PRESS [ENTER] TO BROADCAST INTO SUBSTRATE</div>
                            </div>
                        )}

                        {overlayState === 'thinking' && (
                            <div className="directive-thinking animate-probe">
                                <div className="thinking-center">
                                    <div className="scanning-effect">PROBING_NEURAL_SUBSTRATE...</div>
                                    <div className="geometry-pulse">
                                        <div className="pulse-ring"></div>
                                        <div className="pulse-ring delay-1"></div>
                                        <div className="pulse-ring delay-2"></div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {overlayState === 'response' && (
                            <div className="directive-response-found animate-emerge">
                                <div className="found-content">
                                    <div className="response-header">DIRECTIVE_FOUND // EXECUTION_READY</div>
                                    <div className="response-body markdown-content" dangerouslySetInnerHTML={{ __html: marked.parse(overlayResponse) as string }} />
                                    <div className="found-footer">
                                        <button className="reset-directive" onClick={() => setOverlayState('input')}>REINIT_DIRECTIVE</button>
                                    </div>
                                </div>
                            </div>
                        )}
                        
                    </div>
                </div>
            )}

            <div className="workspace" style={{ transform: `translateY(-${currentSection * 100}vh)` }}>
                <div className="substrate-control-bar">
                    <div className="bar-logo">
                        <img src="https://agenticplace.pythai.net/agentaitrans.png" className="bar-img" alt="logo" />
                        <div className="logo-text">
                           <span className="brand">PYTHAI</span>
                           <span className="subtitle">MASTERMIND // SUBSTRATE</span>
                        </div>
                    </div>
                    <div className="bar-tabs">
                        {SECTIONS.map(s => (
                            <button 
                              key={s.id} 
                              className={`tab-btn ${currentSection === s.id ? 'active' : ''}`} 
                              onClick={() => changeSection(s.id)}
                            >
                                {s.name}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="section-container core-section">
                    <div className="main-grid-layout">
                        <div className="grid-left glass-module">
                            <div className="feed-header">NEURAL_FEED_STREAM</div>
                            <div className="chat-area">
                                {messages.map((m, i) => (
                                    <div key={i} className={`message ${m.sender}`}>
                                        <div className="m-tag">{m.sender === 'user' ? 'ROOT' : m.persona?.toUpperCase() || 'ALPHA'}</div>
                                        <div className="markdown-content" dangerouslySetInnerHTML={{ __html: marked.parse(m.text) as string }} />
                                    </div>
                                ))}
                                {isLoading && !showOverlay && (
                                    <div className="message ai thinking-dots">
                                        <div className="m-tag">{activePersona.toUpperCase()}</div>
                                        <div className="dots-pulse">TRANSMITTING_COGNITION...</div>
                                    </div>
                                )}
                            </div>
                        </div>
                        <div className="grid-right glass-module">
                           <Visualizer />
                        </div>
                    </div>
                </div>

                <div className="section-container board-section">
                    <div className="consensus-module-full glass-module">
                        <div className="module-title-bar">
                           <span className="m-title">EXECUTIVE_BOARD_CONSENSUS</span>
                           <span className="m-version">PROTOCOL_v9.0_ENFORCED</span>
                        </div>
                        <DAOBoard />
                    </div>
                </div>

                <div className="section-container logs-section">
                    <div className="logs-module-full glass-module">
                        <div className="logs-header">SUBSTRATE_TELEMETRY_LOGS</div>
                        <div className="logs-scroll">
                            {logs.map((l, i) => (
                                <div key={i} className="log-line">
                                    <span className="l-time">[{l.timestamp.split('T')[1].slice(0,8)}]</span>
                                    <span className="l-type">{l.eventType.toUpperCase()}</span>
                                    <span className="l-msg">{l.message}</span>
                                </div>
                            ))}
                            {logs.length === 0 && <div className="no-logs">WAITING_FOR_SIGNAL...</div>}
                        </div>
                    </div>
                </div>
            </div>

            <div className="bottom-bar">
                <div className="nav-info">MASTERMIND: <span className="text-accent">ONLINE_ROOT_AUTHORIZED</span></div>
                <div className="nav-info text-dim">LAYER: {SECTIONS[currentSection].name}</div>
                <div className="nav-info text-dim">SUBSTRATE_CLOCK: {new Date().toLocaleTimeString()}</div>
            </div>
        </div>
    );
};

const root = ReactDOM.createRoot(document.getElementById('root')!);
root.render(<App />);
