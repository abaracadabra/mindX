// SPDX-License-Identifier: Apache-2.0
//
// @openagents/overlord — chronos.ts
//
// Time is confirmed by chronos.agent / chronos.oracle, not Date.now(). chronos
// correlates hardware (cpu.oracle) + multi-chain block timestamps
// (blocktime.oracle) + solar/lunar into a *promised time* with a consensus
// confidence. We read it from `GET /v1/oracle/time` (agents/chronos_agent.py,
// served by mindx_backend_service). Tenure (held-since) is measured against
// this verified clock so privilege can't be gamed with a wrong local time.

import type { ChronosConsensus, ChronosTime } from "./model.js";

/**
 * Fetch chronos promised time. Degrades honestly to the local clock flagged
 * `offline` (so the resolver records that tenure is unverified) — never throws.
 */
export async function promisedNow(
  baseUrl?: string,
  fetchImpl: typeof fetch = fetch,
): Promise<ChronosTime> {
  const url = `${(baseUrl ?? "").replace(/\/+$/, "")}/v1/oracle/time`;
  try {
    const r = await fetchImpl(url);
    if (!r.ok) throw new Error(`oracle/time ${r.status}`);
    const d = (await r.json()) as Record<string, unknown>;
    const unix18 = String(d["unix_18dp"] ?? "");
    const unix =
      Number(unix18.split(".")[0] || NaN) ||
      Number(d["unix"] ?? NaN) ||
      Math.floor(Date.now() / 1000);
    return {
      unix: Number.isFinite(unix) ? unix : Math.floor(Date.now() / 1000),
      consensus: (String(d["consensus"] ?? "offline") as ChronosConsensus),
      confidenceMs: Number(d["confidence_ms"] ?? 999_999),
      promisedBy: String(d["promised_by"] ?? "chronos.agent"),
    };
  } catch {
    return {
      unix: Math.floor(Date.now() / 1000),
      consensus: "offline",
      confidenceMs: 999_999,
      promisedBy: "local",
    };
  }
}

/** Chronos-verified holding age in seconds, or null if acquisition is unknown. */
export function tenureSec(now: ChronosTime, acquiredAt: number | null): number | null {
  if (acquiredAt == null) return null;
  return Math.max(0, now.unix - acquiredAt);
}
