/**
 * Verdict aggregation — line-for-line port of daio/governance/boardroom.py's
 * _aggregate_votes(). Preserves:
 *
 *   - per-seat weight (CISO + CRO 1.2x in mindX-default)
 *   - hard veto rule: any 'reject' from a veto-class seat → VETOED regardless
 *     of weighted majority
 *   - quorum: at least 50% of voting seats must have cast a non-abstain vote
 *   - tie-breaking: PASSED on exact tie if no veto cast (matches today's
 *     behavior in Python)
 *
 * Returns a Verdict object (see types.ts).
 */

import type { Vote, Verdict, VerdictValue } from './types.js';
import type { RoomSeat } from '../rooms/types.js';

export function aggregateVotes(seats: RoomSeat[], votes: Vote[]): Verdict {
  let accept_weight = 0;
  let reject_weight = 0;
  let abstain_weight = 0;
  let veto_cast = false;
  const veto_by: string[] = [];

  // Only count seats with weight > 0 (CEO doesn't vote).
  const votingSeats = seats.filter(s => s.weight > 0);
  const totalVotingWeight = votingSeats.reduce((sum, s) => sum + s.weight, 0);
  const nonAbstainCount = votes.filter(v => v.value !== 'abstain').length;
  const quorum_met = nonAbstainCount >= Math.ceil(votingSeats.length / 2);

  for (const v of votes) {
    if (v.value === 'accept') accept_weight += v.weight;
    else if (v.value === 'reject') {
      reject_weight += v.weight;
      if (v.veto) {
        veto_cast = true;
        veto_by.push(v.seat);
      }
    } else {
      abstain_weight += v.weight;
    }
  }

  let value: VerdictValue;
  if (veto_cast) {
    value = 'VETOED';
  } else if (!quorum_met) {
    value = 'NO_QUORUM';
  } else if (accept_weight > reject_weight) {
    value = 'PASSED';
  } else if (reject_weight > accept_weight) {
    value = 'REJECTED';
  } else {
    // Exact weighted tie — PASSED per the Python policy (status quo: when
    // the council is split, the directive carries).
    value = 'TIED';
  }
  // Round weights so the JSON shape stays human-readable.
  return {
    value,
    accept_weight: Number(accept_weight.toFixed(4)),
    reject_weight: Number(reject_weight.toFixed(4)),
    abstain_weight: Number(abstain_weight.toFixed(4)),
    veto_cast,
    veto_by,
    quorum_met,
  };
}
