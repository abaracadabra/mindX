/**
 * Reflection Engine — Shared Index Math for Algorand ARC-200 Tokens
 *
 * Gas-optimized reflection distribution using a global index pattern.
 * Instead of iterating all holders on each trade (impossible on-chain),
 * we maintain a per-unit accumulator. Each holder tracks their last-seen
 * index and claims the delta on next interaction.
 *
 * Math:
 *   reflectionIndex += (feeAmount * PRECISION) / totalSupplyInCirculation
 *   pending[holder] = balance[holder] * (currentIndex - lastIndex[holder]) / PRECISION
 *
 * This module is imported by aluv_token.algo.ts.
 *
 * Compiled by Puya compiler via PuyaTs.
 * (c) 2026 BANKON — GPL-3.0
 */

import { Uint64 } from '@algorandfoundation/algorand-typescript'

// ── Precision Constants ──────────────────────────────────────────
// AVM uses uint64 (max ~18.4 quintillion). We use 1e12 for precision
// to allow headroom for multiplication before overflow.

/** Precision multiplier for reflection index (1e12) */
export const REFLECTION_PRECISION = Uint64(1_000_000_000_000)

/** Basis point denominator (10,000 = 100%) */
export const BPS_DENOMINATOR = Uint64(10_000)

// ── Pure Math Functions ──────────────────────────────────────────

/**
 * Calculate the new reflection index after a fee is collected.
 *
 * @param currentIndex   Current global reflection index
 * @param feeAmount      Fee collected from this transfer
 * @param totalSupply    Total tokens in circulation (excluding excluded addresses)
 * @returns              Updated reflection index
 */
export function updateReflectionIndex(
  currentIndex: Uint64,
  feeAmount: Uint64,
  totalSupply: Uint64,
): Uint64 {
  if (totalSupply === Uint64(0) || feeAmount === Uint64(0)) {
    return currentIndex
  }
  // index += (fee * PRECISION) / supply
  const indexDelta = (feeAmount * REFLECTION_PRECISION) / totalSupply
  return currentIndex + indexDelta
}

/**
 * Calculate pending reflection rewards for a holder.
 *
 * @param holderBalance      Holder's token balance
 * @param currentIndex       Current global reflection index
 * @param holderLastIndex    Holder's last-seen reflection index
 * @returns                  Pending reward amount (in token units)
 */
export function calculatePendingReflection(
  holderBalance: Uint64,
  currentIndex: Uint64,
  holderLastIndex: Uint64,
): Uint64 {
  if (currentIndex <= holderLastIndex || holderBalance === Uint64(0)) {
    return Uint64(0)
  }
  const indexDelta = currentIndex - holderLastIndex
  return (holderBalance * indexDelta) / REFLECTION_PRECISION
}

/**
 * Calculate fee amount from a transfer.
 *
 * @param amount    Transfer amount
 * @param feeBps   Fee in basis points (e.g., 300 = 3%)
 * @returns        Fee amount
 */
export function calculateFee(amount: Uint64, feeBps: Uint64): Uint64 {
  return (amount * feeBps) / BPS_DENOMINATOR
}

/**
 * Split a total fee into reflection / liquidity / team portions.
 *
 * @param totalFee       Total fee amount
 * @param reflectionBps  Reflection portion in bps (e.g., 300)
 * @param liquidityBps   Liquidity portion in bps (e.g., 100)
 * @param teamBps        Team portion in bps (e.g., 100)
 * @returns              [reflectionAmount, liquidityAmount, teamAmount]
 */
export function splitFee(
  totalFee: Uint64,
  reflectionBps: Uint64,
  liquidityBps: Uint64,
  teamBps: Uint64,
): [Uint64, Uint64, Uint64] {
  const totalBps = reflectionBps + liquidityBps + teamBps
  if (totalBps === Uint64(0)) return [Uint64(0), Uint64(0), Uint64(0)]

  const reflectionAmount = (totalFee * reflectionBps) / totalBps
  const liquidityAmount = (totalFee * liquidityBps) / totalBps
  const teamAmount = totalFee - reflectionAmount - liquidityAmount // remainder avoids rounding loss
  return [reflectionAmount, liquidityAmount, teamAmount]
}
