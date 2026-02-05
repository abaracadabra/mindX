/**
 * AgenticPlace Connection Tools
 *
 * Facilitates interaction with external inference (Ollama, LLM providers, rate limits).
 * Used by CEO and other AgenticPlace agents to test, list, and use mindX backend connections.
 */

const getBaseUrl = () => import.meta.env?.VITE_MINDX_API_URL || 'http://localhost:8000';

export interface OllamaTestRequest {
  base_url?: string;
  try_fallback?: boolean;
}

export interface OllamaTestResponse {
  success: boolean;
  message?: string;
  base_url?: string;
  primary_url?: string;
  fallback_url?: string;
  model_count?: number;
  error?: string;
  request_sent?: string;
  response_status?: number;
  response_preview?: string;
}

export interface OllamaStatusResponse {
  success: boolean;
  connected?: boolean;
  base_url?: string;
  primary_url?: string;
  fallback_url?: string;
  models?: Array<{ name?: string; model?: string; [k: string]: unknown }>;
  model_count?: number;
  error?: string;
}

export interface OllamaModelsResponse {
  success: boolean;
  models: Array<{ name?: string; model?: string; size?: number; details?: Record<string, unknown> }>;
  count: number;
  base_url?: string;
}

export interface OllamaInteractRequest {
  prompt: string;
  model?: string;
}

export interface OllamaInteractResponse {
  success: boolean;
  response?: string;
  model?: string;
  error?: string;
}

export interface OllamaConfigRequest {
  base_url?: string;
  host?: string;
  port?: number;
}

export interface RateLimitStatusResponse {
  success?: boolean;
  rate_limits?: Record<string, unknown>;
  providers?: unknown[];
}

export interface LlmProvidersResponse {
  success: boolean;
  providers?: Array<{ name: string; [k: string]: unknown }>;
}

export interface MindXAgentOllamaStatusResponse {
  connected?: boolean;
  base_url?: string;
  models?: string[];
  [k: string]: unknown;
}

/**
 * Test Ollama connection (optional base_url, try_fallback).
 */
export async function testOllamaConnection(req: OllamaTestRequest = {}): Promise<OllamaTestResponse> {
  const base = getBaseUrl();
  try {
    const res = await fetch(`${base}/api/admin/ollama/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        base_url: req.base_url,
        try_fallback: req.try_fallback !== false
      })
    });
    const data = await res.json();
    return {
      success: data.success === true,
      message: data.message,
      base_url: data.base_url,
      primary_url: data.primary_url,
      fallback_url: data.fallback_url,
      model_count: data.model_count,
      error: data.error,
      request_sent: data.request_sent,
      response_status: data.response_status,
      response_preview: data.response_preview
    };
  } catch (e: any) {
    return { success: false, error: e?.message || 'Connection test failed' };
  }
}

/**
 * Get Ollama connection status.
 */
export async function getOllamaStatus(): Promise<OllamaStatusResponse> {
  const base = getBaseUrl();
  try {
    const res = await fetch(`${base}/api/admin/ollama/status`);
    const data = await res.json();
    return {
      success: res.ok,
      connected: data.connected ?? data.success,
      base_url: data.base_url,
      primary_url: data.primary_url,
      fallback_url: data.fallback_url,
      models: data.models,
      model_count: data.model_count,
      error: data.error
    };
  } catch (e: any) {
    return { success: false, error: e?.message || 'Status check failed' };
  }
}

/**
 * List available Ollama models (admin endpoint).
 */
export async function getOllamaModels(): Promise<OllamaModelsResponse> {
  const base = getBaseUrl();
  try {
    const res = await fetch(`${base}/api/admin/ollama/models`);
    const data = await res.json();
    return {
      success: data.success === true,
      models: data.models || [],
      count: data.count ?? (data.models?.length ?? 0),
      base_url: data.base_url
    };
  } catch (e: any) {
    return { success: false, models: [], count: 0, error: (e as Error)?.message };
  }
}

/**
 * Interact with Ollama (prompt, optional model).
 */
export async function interactOllama(req: OllamaInteractRequest): Promise<OllamaInteractResponse> {
  const base = getBaseUrl();
  try {
    const res = await fetch(`${base}/api/admin/ollama/interact`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: req.prompt, model: req.model || '' })
    });
    const data = await res.json();
    return {
      success: data.success === true,
      response: data.response,
      model: data.model,
      error: data.error
    };
  } catch (e: any) {
    return { success: false, error: e?.message || 'Interact failed' };
  }
}

/**
 * Get Ollama API metrics.
 */
export async function getOllamaMetrics(): Promise<Record<string, unknown>> {
  const base = getBaseUrl();
  try {
    const res = await fetch(`${base}/api/admin/ollama/metrics`);
    return res.ok ? await res.json() : {};
  } catch {
    return {};
  }
}

/**
 * Set Ollama server configuration (base_url or host+port).
 */
export async function setOllamaConfig(req: OllamaConfigRequest): Promise<{ success: boolean; message?: string; error?: string }> {
  const base = getBaseUrl();
  try {
    const res = await fetch(`${base}/api/llm/ollama/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req)
    });
    const data = await res.json();
    return {
      success: data.success === true,
      message: data.message,
      error: data.detail || data.error
    };
  } catch (e: any) {
    return { success: false, error: e?.message };
  }
}

/**
 * Get LLM provider list (API keys status, etc.).
 */
export async function getLlmProviders(): Promise<LlmProvidersResponse> {
  const base = getBaseUrl();
  try {
    const res = await fetch(`${base}/api/llm/providers`);
    const data = await res.json();
    return { success: res.ok, providers: data.providers || [] };
  } catch (e: any) {
    return { success: false, providers: [], error: (e as Error)?.message };
  }
}

/**
 * Get rate limit status for all providers.
 */
export async function getRateLimitStatus(): Promise<RateLimitStatusResponse> {
  const base = getBaseUrl();
  try {
    const res = await fetch(`${base}/api/llm/performance/rate-limits`);
    return res.ok ? await res.json() : {};
  } catch {
    return {};
  }
}

/**
 * Test a specific provider API key.
 */
export async function testProvider(provider: string): Promise<{ success: boolean; message?: string }> {
  const base = getBaseUrl();
  try {
    const res = await fetch(`${base}/api/llm/providers/${encodeURIComponent(provider)}/test`, {
      method: 'POST'
    });
    const data = await res.json();
    return { success: data.success === true, message: data.message };
  } catch (e: any) {
    return { success: false, message: e?.message };
  }
}

/**
 * Get mindXagent Ollama connection and inference status.
 */
export async function getMindXAgentOllamaStatus(): Promise<MindXAgentOllamaStatusResponse> {
  const base = getBaseUrl();
  try {
    const res = await fetch(`${base}/mindxagent/ollama/status`);
    return res.ok ? await res.json() : {};
  } catch {
    return {};
  }
}

/**
 * Connection tools facade for CEO and AgenticPlace UI.
 * Use these to interact with external inference (Ollama, providers, rate limits).
 */
export const connectionTools = {
  testOllamaConnection,
  getOllamaStatus,
  getOllamaModels,
  interactOllama,
  getOllamaMetrics,
  setOllamaConfig,
  getLlmProviders,
  getRateLimitStatus,
  testProvider,
  getMindXAgentOllamaStatus
};
