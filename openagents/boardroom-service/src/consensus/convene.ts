/**
 * Convene engine — per-seat vote casting via aisdk.
 *
 * Each seat votes through its configured provider/model. Votes are
 * structured: the soldier returns a JSON object `{ vote, reasoning }`
 * which we parse and feed into the verdict aggregator.
 *
 * Streaming: we use aisdk's streamText so each soldier's reasoning streams
 * back in real time. The WS handler (in ws/) broadcasts each delta to all
 * connected clients. HTTP fallback (synchronous convene) collects the
 * full text and returns the verdict in one response.
 */

import { streamText, generateText } from 'ai';
import { resolveModel } from '../providers/index.js';
import { aggregateVotes } from './verdict.js';
import type { Vote, Session, VoteValue } from './types.js';
import type { RoomSeat } from '../rooms/types.js';
import { log } from '../log.js';

const VOTE_SYSTEM_PROMPT = (seat: RoomSeat, persona?: string) => `
You are seat ${seat.role.toUpperCase()} in the boardroom. Your weight is
${seat.weight}${seat.veto ? ' (HARD VETO)' : ''}.

${persona ?? ''}

For each directive presented, you must:
  1. Reason briefly (under 200 words) about the directive's merit
  2. Cast a vote: accept, reject, or abstain
  3. Return ONLY a JSON object on the final line, like:
     {"vote": "accept", "reasoning": "<your reasoning>"}

Your reasoning should be a single paragraph. Do not write any text after the
JSON object. Do not wrap the JSON in code fences.
`.trim();

const VOTE_USER_PROMPT = (directive: string, context?: string) => `
Directive: ${directive}

${context ? `Context:\n${context}\n` : ''}

Please cast your vote. Respond with the JSON object as instructed.
`.trim();

function parseVote(text: string): { value: VoteValue; reasoning: string } {
  // Try to find the JSON object on the last non-empty line.
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
  for (let i = lines.length - 1; i >= 0; i--) {
    const line = lines[i] ?? '';
    if (line.startsWith('{') && line.endsWith('}')) {
      try {
        const obj = JSON.parse(line) as { vote?: unknown; reasoning?: unknown };
        const v = typeof obj.vote === 'string' ? obj.vote.toLowerCase() : '';
        if (v === 'accept' || v === 'reject' || v === 'abstain') {
          return {
            value: v as VoteValue,
            reasoning: typeof obj.reasoning === 'string' ? obj.reasoning : text,
          };
        }
      } catch {
        // Fall through to fuzzy parse.
      }
    }
  }
  // Fuzzy fallback — the seat didn't follow instructions but maybe we can tell.
  const lower = text.toLowerCase();
  if (lower.includes('"vote":"accept"') || lower.includes('"vote": "accept"')) {
    return { value: 'accept', reasoning: text };
  }
  if (lower.includes('"vote":"reject"') || lower.includes('"vote": "reject"')) {
    return { value: 'reject', reasoning: text };
  }
  // Anything else → abstain (we don't speak for the seat).
  return { value: 'abstain', reasoning: text };
}

export interface CastVoteOpts {
  directive: string;
  context?: string;
  /** Persona file content (markdown), if any. */
  persona?: string;
  /** Per-vote timeout. */
  timeoutMs?: number;
  /** Stream callback — receives raw text deltas. WS handler hooks this. */
  onDelta?: (chunk: string) => void;
}

/** Cast a single seat's vote. Never throws — failures land as 'abstain'. */
export async function castVote(seat: RoomSeat, opts: CastVoteOpts): Promise<Vote> {
  const provider = (seat.inference_provider ?? 'ollama') as Parameters<typeof resolveModel>[0];
  const model = seat.model ?? 'qwen3:0.6b';
  const sys = VOTE_SYSTEM_PROMPT(seat, opts.persona);
  const usr = VOTE_USER_PROMPT(opts.directive, opts.context);
  const started = Date.now();

  try {
    if (opts.onDelta) {
      // Streaming path — use streamText, collect, forward each chunk.
      const lm = resolveModel(provider, model);
      const result = streamText({
        model: lm,
        system: sys,
        prompt: usr,
        temperature: 0.2,
        abortSignal: opts.timeoutMs ? AbortSignal.timeout(opts.timeoutMs) : undefined,
      });
      let full = '';
      for await (const chunk of result.textStream) {
        full += chunk;
        opts.onDelta(chunk);
      }
      const parsed = parseVote(full);
      const usage = await result.usage.catch(() => null);
      return {
        seat: seat.role,
        address: seat.address,
        weight: seat.weight,
        veto: seat.veto,
        value: parsed.value,
        reasoning: parsed.reasoning,
        tokens: usage ? {
          input: (usage as unknown as { promptTokens?: number; inputTokens?: number }).promptTokens
                ?? (usage as unknown as { promptTokens?: number; inputTokens?: number }).inputTokens ?? 0,
          output: (usage as unknown as { completionTokens?: number; outputTokens?: number }).completionTokens
                ?? (usage as unknown as { completionTokens?: number; outputTokens?: number }).outputTokens ?? 0,
        } : undefined,
        latency_ms: Date.now() - started,
        provider,
        model,
        timestamp: Math.floor(Date.now() / 1000),
      };
    } else {
      // Synchronous path — use generateText, return single vote.
      const lm = resolveModel(provider, model);
      const { text, usage } = await generateText({
        model: lm,
        system: sys,
        prompt: usr,
        temperature: 0.2,
        abortSignal: opts.timeoutMs ? AbortSignal.timeout(opts.timeoutMs) : undefined,
      });
      const parsed = parseVote(text);
      return {
        seat: seat.role,
        address: seat.address,
        weight: seat.weight,
        veto: seat.veto,
        value: parsed.value,
        reasoning: parsed.reasoning,
        tokens: usage ? {
          input: (usage as unknown as { promptTokens?: number; inputTokens?: number }).promptTokens
                ?? (usage as unknown as { promptTokens?: number; inputTokens?: number }).inputTokens ?? 0,
          output: (usage as unknown as { completionTokens?: number; outputTokens?: number }).completionTokens
                ?? (usage as unknown as { completionTokens?: number; outputTokens?: number }).outputTokens ?? 0,
        } : undefined,
        latency_ms: Date.now() - started,
        provider,
        model,
        timestamp: Math.floor(Date.now() / 1000),
      };
    }
  } catch (e) {
    log('warn', 'consensus', `castVote failed for ${seat.role}`, { provider, model, err: String(e) });
    return {
      seat: seat.role,
      address: seat.address,
      weight: seat.weight,
      veto: seat.veto,
      value: 'abstain',
      reasoning: '(vote failed — counted as abstain)',
      latency_ms: Date.now() - started,
      provider,
      model,
      timestamp: Math.floor(Date.now() / 1000),
      error: String(e),
    };
  }
}

/** Synchronous convene — runs all votes in parallel, returns the session. */
export async function convene(
  session: Session,
  seats: RoomSeat[],
  opts: { context?: string; personas?: Record<string, string>; timeoutMs?: number } = {},
): Promise<Session> {
  const votingSeats = seats.filter(s => s.weight > 0);
  const votes = await Promise.all(votingSeats.map(s =>
    castVote(s, {
      directive: session.directive,
      context: opts.context ?? session.context,
      persona: opts.personas?.[s.role],
      timeoutMs: opts.timeoutMs ?? 120_000,
    })
  ));
  session.votes = votes;
  session.verdict = aggregateVotes(seats, votes);
  session.finished_at = Math.floor(Date.now() / 1000);
  return session;
}
