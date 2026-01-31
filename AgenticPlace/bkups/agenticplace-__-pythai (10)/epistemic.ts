
/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export interface LogEntry {
    timestamp: string;
    eventType: string;
    message: string;
    data?: any;
}

export interface KnowledgeBase {
    [topic: string]: string[];
}

class Epistemic {
    private knowledgeBase: KnowledgeBase = {};
    private logs: LogEntry[] = [];
    private storageKey = 'pythai_knowledge_v1';
    private logKey = 'pythai_logs_v1';
    private listeners: ((event: string, data: any) => void)[] = [];

    constructor() {
        this.init();
    }

    private init() {
        try {
            const kbData = localStorage.getItem(this.storageKey);
            const logData = localStorage.getItem(this.logKey);
            if (kbData) this.knowledgeBase = JSON.parse(kbData);
            if (logData) this.logs = JSON.parse(logData);
            
            // Seed default RAGE knowledge if empty
            if (Object.keys(this.knowledgeBase).length === 0) {
                this.seedKnowledge();
            }
        } catch (e) {
            console.warn("⚠️ Error initializing knowledge base from storage.", e);
            this.knowledgeBase = {};
            this.logs = [];
        }
    }

    private seedKnowledge() {
        const ragePrinciples = [
            "RAGE: Retrieval Augmented Generative Engine powering the Knowledge Economy.",
            "Enhancing Knowledge Discovery: Automating research and organizing intellectual capital.",
            "Monetizing Data: Transforming raw data into actionable intelligence as an economic asset.",
            "Hyperconnected Environment: Integration with cloud, IoT, and blockchain.",
            "Business Intelligence: Predictive analytics for forward-thinking strategies."
        ];
        this.knowledgeBase["RAGE_CORE"] = ragePrinciples;
        this.save();
    }

    private save() {
        localStorage.setItem(this.storageKey, JSON.stringify(this.knowledgeBase));
        localStorage.setItem(this.logKey, JSON.stringify(this.logs));
    }

    private notify(event: string, data: any) {
        this.listeners.forEach(cb => cb(event, data));
    }

    public subscribe(cb: (event: string, data: any) => void) {
        this.listeners.push(cb);
        return () => {
            this.listeners = this.listeners.filter(l => l !== cb);
        };
    }

    public async logEvent(eventType: string, message: string, data = {}) {
        const logEntry: LogEntry = { 
            timestamp: new Date().toISOString(), 
            eventType, 
            message, 
            data 
        };
        this.logs.unshift(logEntry); // Newest first
        if (this.logs.length > 200) this.logs.pop(); // Cap logs
        this.save();
        this.notify('logUpdated', logEntry);
    }

    public async addKnowledge(topic: string, content: string) {
        if (!this.knowledgeBase[topic]) {
            this.knowledgeBase[topic] = [];
        }
        if (!this.knowledgeBase[topic].includes(content)) {
            this.knowledgeBase[topic].push(content);
            this.save();
            await this.logEvent("knowledgeAdded", `New knowledge indexed on '${topic}'`, { topic, content });
            this.notify('knowledgeAdded', { topic, content });
        }
    }

    public queryKnowledge(topic: string): string[] {
        return this.knowledgeBase[topic] || [];
    }

    public async clear() {
        this.knowledgeBase = {};
        this.logs = [];
        this.save();
        this.seedKnowledge(); // Re-seed core after clear
        await this.logEvent("knowledgeCleared", "All knowledge and logs purged. Core RAGE seeds restored.");
        this.notify('cleared', null);
    }

    public getLogs(): LogEntry[] {
        return [...this.logs];
    }
    
    public getFullKnowledge(): KnowledgeBase {
        return { ...this.knowledgeBase };
    }
}

export const epistemic = new Epistemic();
