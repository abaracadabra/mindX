/**
 * AgenticPlace mindX Backend Service Integration
 * 
 * Agnostic frontend service layer for interacting with mindX self-optimizing backend.
 * Supports multiple AI providers (Ollama, Gemini, etc.) and agent orchestration.
 */

export interface MindXAgentRequest {
    agent: 'ceo' | 'mastermind' | 'mindx' | 'suntsu' | 'pythai';
    directive: string;
    mode?: 'query' | 'execution';
    persona?: string;
    prompt?: string;
    context?: Record<string, any>;
}

export interface MindXAgentResponse {
    success: boolean;
    response: string;
    agent_id: string;
    timestamp: string;
    metadata?: Record<string, any>;
}

export interface OllamaIngestRequest {
    prompt: string;
    model?: string;
    context?: Record<string, any>;
    store_in_memory?: boolean;
}

export interface OllamaIngestResponse {
    success: boolean;
    response: string;
    tokens_used?: number;
    model_used?: string;
    memory_stored?: boolean;
}

class MindXService {
    private baseUrl: string;
    private ollamaUrl: string;

    constructor() {
        // Default to localhost, can be overridden via environment
        this.baseUrl = import.meta.env?.VITE_MINDX_API_URL || 'http://localhost:8000';
        this.ollamaUrl = import.meta.env?.VITE_OLLAMA_URL || 'http://10.0.0.155:18080';
    }

    /**
     * Call mindXagent through specified agent (CEO, mastermind, mindX, SunTsu)
     */
    async callMindXAgent(request: MindXAgentRequest): Promise<MindXAgentResponse> {
        try {
            const response = await fetch(`${this.baseUrl}/agenticplace/agent/call`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    agent_type: request.agent,
                    directive: request.directive,
                    mode: request.mode || 'execution',
                    persona: request.persona,
                    prompt: request.prompt,
                    context: request.context || {}
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            return {
                success: data.success !== false,
                response: data.response || data.message || 'No response',
                agent_id: data.agent_id || request.agent,
                timestamp: data.timestamp || new Date().toISOString(),
                metadata: data.metadata
            };
        } catch (error: any) {
            console.error('MindX Agent call failed:', error);
            return {
                success: false,
                response: `Error: ${error.message}`,
                agent_id: request.agent,
                timestamp: new Date().toISOString()
            };
        }
    }

    /**
     * Ingest prompt through Ollama AI
     */
    async ingestOllama(request: OllamaIngestRequest): Promise<OllamaIngestResponse> {
        try {
            const response = await fetch(`${this.baseUrl}/agenticplace/ollama/ingest`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt: request.prompt,
                    model: request.model || 'mistral-nemo:latest',
                    context: request.context || {},
                    store_in_memory: request.store_in_memory !== false
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            return {
                success: data.success !== false,
                response: data.response || data.message || 'No response',
                tokens_used: data.tokens_used,
                model_used: data.model_used || request.model,
                memory_stored: data.memory_stored || false
            };
        } catch (error: any) {
            console.error('Ollama ingestion failed:', error);
            return {
                success: false,
                response: `Error: ${error.message}`,
                memory_stored: false
            };
        }
    }

    /**
     * Get available models from Ollama
     */
    async getOllamaModels(): Promise<string[]> {
        try {
            const response = await fetch(`${this.baseUrl}/api/admin/ollama/models`, {
                method: 'GET'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            return data.models || [];
        } catch (error: any) {
            console.error('Failed to fetch Ollama models:', error);
            return [];
        }
    }

    /**
     * Get CEO status and seven soldiers
     */
    async getCEOStatus(): Promise<any> {
        try {
            const response = await fetch(`${this.baseUrl}/agenticplace/ceo/status`, {
                method: 'GET'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error: any) {
            console.error('Failed to fetch CEO status:', error);
            return { success: false, error: error.message };
        }
    }
}

export const mindXService = new MindXService();
