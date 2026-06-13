/**
 * aisdk provider routing per soldier.
 *
 * Maps inference_provider strings (from agent_map.json) onto aisdk model
 * factories. Each soldier votes via its configured provider; the same
 * SoldierConfig field (inference_provider) that the Python boardroom.py
 * reads is what drives this routing, so the Node and Python paths agree
 * on which model votes for which seat.
 *
 * Custom local providers (Ollama via /api/generate, vLLM via OpenAI-shaped
 * API) live in this file rather than as separate packages — they are small
 * adapters that match what mindX already runs on the same VPS.
 */

import type { LanguageModel } from 'ai';
import { createOpenAI } from '@ai-sdk/openai';
import { createAnthropic } from '@ai-sdk/anthropic';

/** Provider names mindX uses in agent_map.json. */
export type ProviderName =
  | 'openai' | 'anthropic' | 'gemini' | 'groq' | 'mistral'
  | 'together' | 'deepseek' | 'ollama' | 'openrouter' | 'vllm';

/**
 * Resolve credentials. In production each provider's API key lives in the
 * BANKON vault and is loaded via a subprocess call to the Python vault
 * (the same pattern wordpress-agent uses). For Phase D we read env first;
 * vault wiring lands in Phase E alongside agents/boardroom_client.py.
 */
function getKey(name: string): string {
  return process.env[name] ?? '';
}

const OLLAMA_BASE_URL = process.env.MINDX_LLM__OLLAMA__BASE_URL ?? 'http://127.0.0.1:11434';

/**
 * Build an aisdk LanguageModel for a given (provider, model) pair.
 *
 * For providers that aisdk doesn't ship a first-party package for
 * (Gemini via its OpenAI-compatible endpoint, Groq, Mistral, Together,
 * DeepSeek, OpenRouter, Ollama, vLLM), we use createOpenAI with the right
 * baseURL — all of these expose an OpenAI-shaped /v1/chat/completions
 * endpoint.
 */
export function resolveModel(provider: ProviderName, model: string): LanguageModel {
  switch (provider) {
    case 'openai':
      return createOpenAI({ apiKey: getKey('OPENAI_API_KEY') })(model);

    case 'anthropic':
      return createAnthropic({ apiKey: getKey('ANTHROPIC_API_KEY') })(model);

    case 'gemini':
      // Gemini supports an OpenAI-compatible endpoint at generativelanguage.googleapis.com/v1beta/openai/
      return createOpenAI({
        apiKey: getKey('GEMINI_API_KEY'),
        baseURL: 'https://generativelanguage.googleapis.com/v1beta/openai',
      })(model);

    case 'groq':
      return createOpenAI({
        apiKey: getKey('GROQ_API_KEY'),
        baseURL: 'https://api.groq.com/openai/v1',
      })(model);

    case 'mistral':
      return createOpenAI({
        apiKey: getKey('MISTRAL_API_KEY'),
        baseURL: 'https://api.mistral.ai/v1',
      })(model);

    case 'together':
      return createOpenAI({
        apiKey: getKey('TOGETHER_API_KEY'),
        baseURL: 'https://api.together.xyz/v1',
      })(model);

    case 'deepseek':
      return createOpenAI({
        apiKey: getKey('DEEPSEEK_API_KEY'),
        baseURL: 'https://api.deepseek.com/v1',
      })(model);

    case 'openrouter':
      return createOpenAI({
        apiKey: getKey('OPENROUTER_API_KEY'),
        baseURL: 'https://openrouter.ai/api/v1',
      })(model);

    case 'ollama':
      // Ollama exposes /v1 OpenAI shim since 0.1.27.
      return createOpenAI({
        apiKey: 'ollama',
        baseURL: `${OLLAMA_BASE_URL}/v1`,
      })(model);

    case 'vllm':
      return createOpenAI({
        apiKey: getKey('VLLM_API_KEY') || 'no-key',
        baseURL: process.env.MINDX_VLLM_BASE_URL ?? 'http://127.0.0.1:8000/v1',
      })(model);

    default:
      // Defensive fallback — return Ollama with a safe local model so the
      // vote at least lands; the consensus layer will mark it as fallback.
      return createOpenAI({
        apiKey: 'ollama',
        baseURL: `${OLLAMA_BASE_URL}/v1`,
      })('qwen3:0.6b');
  }
}
