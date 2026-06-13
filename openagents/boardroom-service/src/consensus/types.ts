/**
 * Consensus engine types — votes, verdicts, sessions.
 */

export type VoteValue = 'accept' | 'reject' | 'abstain';

export interface Vote {
  seat: string;        // role slug (e.g. 'ciso_security', 'sun_tzu')
  address: `0x${string}`;
  weight: number;
  veto: boolean;
  value: VoteValue;
  reasoning: string;   // full final text from the soldier
  /** Cost / token info if the provider returned it. */
  tokens?: { input: number; output: number };
  /** Latency ms from prompt to final token. */
  latency_ms?: number;
  /** Provider + model actually used. */
  provider: string;
  model: string;
  timestamp: number;
  /** Optional: raw error if this vote failed (counted as abstain in aggregator). */
  error?: string;
}

export type VerdictValue = 'PASSED' | 'REJECTED' | 'VETOED' | 'TIED' | 'NO_QUORUM';

export interface Verdict {
  value: VerdictValue;
  accept_weight: number;
  reject_weight: number;
  abstain_weight: number;
  veto_cast: boolean;
  veto_by: string[];   // seats that exercised veto
  quorum_met: boolean;
}

export interface Session {
  session_id: string;
  room_id: string;
  directive: string;
  importance: 'routine' | 'standard' | 'high' | 'critical';
  initiated_by: `0x${string}`;
  votes: Vote[];
  verdict: Verdict | null;
  started_at: number;
  finished_at: number | null;
  /** Optional: free-form context passed to soldiers. */
  context?: string;
}
