/**
 * Liquidity Locker — LP Token Lock with BONA FIDE Integration
 *
 * Lock LP tokens for a configurable period. Minimum 90 days for BONA FIDE.
 * BONA FIDE is issued to the ASSET (the LP token / underlying token),
 * not just the wallet.
 *
 * Lifecycle:
 *   Day 0:    Lock LP tokens (≥90 days) → BONA FIDE issued to asset
 *   Day 1-88: Asset is BONA FIDE, lock active
 *   Day 89:   DEADLINE — must extend or have auto-extend ON
 *   Day 90:   Lock expires → LP tokens withdrawable
 *             If not extended → BONA FIDE clawback
 *             If extended → new 90-day cycle
 *
 * Auto-extend: toggle that auto-renews for another 90 days on expiry.
 * User has FULL CONTROL — they choose how long to lock.
 *
 * Compiled by Puya compiler via PuyaTs.
 * (c) 2026 BANKON — GPL-3.0
 */

import { Contract } from '@algorandfoundation/algorand-typescript'
import {
  GlobalState,
  BoxMap,
  Account,
  Asset,
  Txn,
  Global,
  itxn,
  assert,
  Bytes,
  Uint64,
  arc4,
} from '@algorandfoundation/algorand-typescript'

// ~3.3s per round, ~26,182 rounds per day
const ROUNDS_PER_DAY = Uint64(26_182)
const MIN_BONAFIDE_DAYS = Uint64(90)
const CLAWBACK_WARNING_DAY = Uint64(89) // day 89 = last chance to extend

// ── Lock Record ──────────────────────────────────────────────────

type LockRecord = {
  owner: Account              // who locked the LP tokens
  lpAssetId: Uint64           // LP token ASA ID
  amount: Uint64              // amount of LP tokens locked
  lockStartRound: Uint64      // round when lock began
  lockEndRound: Uint64        // round when lock expires
  lockDays: Uint64            // original lock duration in days
  autoExtend: boolean         // auto-renew for another 90 days on expiry
  bonafideIssued: boolean     // whether BONA FIDE was issued for this lock
  active: boolean             // lock is active (not withdrawn)
}

// ══════════════════════════════════════════════════════════════════
// LIQUIDITY LOCKER CONTRACT
// ══════════════════════════════════════════════════════════════════

export class LiquidityLocker extends Contract {
  // ── Global State ───────────────────────────────────────────────

  /** BONA FIDE controller app ID (for issuing/clawing back) */
  bonafideAppId = GlobalState<Uint64>()

  /** Admin address */
  adminAddress = GlobalState<Account>()

  /** Next lock ID (auto-incrementing) */
  nextLockId = GlobalState<Uint64>({ initialValue: Uint64(1) })

  /** Total active locks */
  activeLocks = GlobalState<Uint64>({ initialValue: Uint64(0) })

  // ── Box Storage ────────────────────────────────────────────────

  /** Lock records by ID */
  locks = BoxMap<Uint64, LockRecord>({ prefix: Bytes('lk_') })

  /** Owner → list of lock IDs (simplified: last lock ID per owner) */
  ownerLocks = BoxMap<Account, Uint64>({ prefix: Bytes('ol_') })

  // ══════════════════════════════════════════════════════════════
  // INITIALIZATION
  // ══════════════════════════════════════════════════════════════

  @arc4.abimethod()
  initialize(bonafideApp: Uint64, admin: Account): void {
    assert(Txn.sender === Global.creatorAddress, 'Only creator')
    this.bonafideAppId.value = bonafideApp
    this.adminAddress.value = admin
  }

  // ══════════════════════════════════════════════════════════════
  // LOCK LIQUIDITY
  // ══════════════════════════════════════════════════════════════

  /**
   * Lock LP tokens for a specified number of days.
   * Minimum 90 days to qualify for BONA FIDE.
   * Shorter locks are allowed but do not earn BONA FIDE.
   *
   * The LP token ASA must be sent in the same atomic group.
   */
  @arc4.abimethod()
  lockLiquidity(
    lpAssetId: Uint64,
    lpAmount: Uint64,
    lockDays: Uint64,
    autoExtendEnabled: boolean,
  ): Uint64 {
    assert(lpAmount > Uint64(0), 'Must lock > 0')
    assert(lockDays > Uint64(0), 'Must lock > 0 days')

    const lockId = this.nextLockId.value
    const lockEndRound = Global.round + (lockDays * ROUNDS_PER_DAY)

    // Determine if BONA FIDE eligible
    const bonafideEligible = lockDays >= MIN_BONAFIDE_DAYS

    // Create lock record
    this.locks(lockId).value = {
      owner: Txn.sender,
      lpAssetId: lpAssetId,
      amount: lpAmount,
      lockStartRound: Global.round,
      lockEndRound: lockEndRound,
      lockDays: lockDays,
      autoExtend: autoExtendEnabled,
      bonafideIssued: bonafideEligible,
      active: true,
    }

    this.ownerLocks(Txn.sender).value = lockId
    this.nextLockId.value = lockId + Uint64(1)
    this.activeLocks.value = this.activeLocks.value + Uint64(1)

    // If BONA FIDE eligible, notify controller to issue
    if (bonafideEligible && this.bonafideAppId.value > Uint64(0)) {
      // Call bonafideController to issue BONA FIDE for this asset
      itxn.applicationCall({
        applicationId: this.bonafideAppId.value,
        appArgs: [Bytes('issueForLock'), Txn.sender.bytes],
        fee: Uint64(2000), // extra for inner ASA transfer
      }).submit()
    }

    return lockId
  }

  // ══════════════════════════════════════════════════════════════
  // EXTEND LOCK
  // ══════════════════════════════════════════════════════════════

  /**
   * Extend an existing lock by additional days.
   * Must extend BEFORE day 89 to maintain BONA FIDE.
   */
  @arc4.abimethod()
  extendLock(lockId: Uint64, additionalDays: Uint64): void {
    assert(this.locks(lockId).exists, 'Lock not found')
    const lock = this.locks(lockId).value
    assert(lock.owner === Txn.sender, 'Not lock owner')
    assert(lock.active, 'Lock not active')
    assert(additionalDays > Uint64(0), 'Must extend > 0 days')

    // Extend the lock end
    lock.lockEndRound = lock.lockEndRound + (additionalDays * ROUNDS_PER_DAY)
    lock.lockDays = lock.lockDays + additionalDays
    this.locks(lockId).value = lock
  }

  // ══════════════════════════════════════════════════════════════
  // TOGGLE AUTO-EXTEND
  // ══════════════════════════════════════════════════════════════

  /**
   * Toggle auto-extend for a lock.
   * When ON: lock auto-renews for 90 days when it would expire.
   * When OFF: lock expires normally, BONA FIDE clawback if not extended.
   */
  @arc4.abimethod()
  toggleAutoExtend(lockId: Uint64): void {
    assert(this.locks(lockId).exists, 'Lock not found')
    const lock = this.locks(lockId).value
    assert(lock.owner === Txn.sender, 'Not lock owner')
    assert(lock.active, 'Lock not active')

    lock.autoExtend = !lock.autoExtend
    this.locks(lockId).value = lock
  }

  // ══════════════════════════════════════════════════════════════
  // WITHDRAW LIQUIDITY
  // ══════════════════════════════════════════════════════════════

  /**
   * Withdraw LP tokens after lock expires.
   * BONA FIDE on the asset remains (it was earned).
   */
  @arc4.abimethod()
  withdrawLiquidity(lockId: Uint64): void {
    assert(this.locks(lockId).exists, 'Lock not found')
    const lock = this.locks(lockId).value
    assert(lock.owner === Txn.sender, 'Not lock owner')
    assert(lock.active, 'Already withdrawn')
    assert(Global.round >= lock.lockEndRound, 'Lock not expired')

    // Transfer LP tokens back to owner
    itxn.assetTransfer({
      xferAsset: Asset(lock.lpAssetId),
      assetAmount: lock.amount,
      assetReceiver: lock.owner,
      fee: Uint64(1000),
    }).submit()

    // Mark as inactive
    lock.active = false
    this.locks(lockId).value = lock
    this.activeLocks.value = this.activeLocks.value - Uint64(1)
  }

  // ══════════════════════════════════════════════════════════════
  // CHECK AND CLAWBACK (Keeper/Cron)
  // ══════════════════════════════════════════════════════════════

  /**
   * Check a specific lock and clawback BONA FIDE if day 89 passed
   * without extension and auto-extend is OFF.
   *
   * Called by keeper bot or anyone (permissionless check).
   */
  @arc4.abimethod()
  checkAndClawback(lockId: Uint64): void {
    assert(this.locks(lockId).exists, 'Lock not found')
    const lock = this.locks(lockId).value

    if (!lock.active || !lock.bonafideIssued) return

    const roundsElapsed = Global.round - lock.lockStartRound
    const daysElapsed = roundsElapsed / ROUNDS_PER_DAY

    // Check if we're past day 89 and lock is about to expire
    if (daysElapsed >= CLAWBACK_WARNING_DAY && Global.round >= lock.lockEndRound - ROUNDS_PER_DAY) {
      if (lock.autoExtend) {
        // Auto-extend: renew for another 90 days
        lock.lockEndRound = lock.lockEndRound + (MIN_BONAFIDE_DAYS * ROUNDS_PER_DAY)
        lock.lockDays = lock.lockDays + MIN_BONAFIDE_DAYS
        this.locks(lockId).value = lock
        return
      }

      // Not extended, not auto-extend → clawback BONA FIDE
      if (this.bonafideAppId.value > Uint64(0)) {
        itxn.applicationCall({
          applicationId: this.bonafideAppId.value,
          appArgs: [Bytes('revoke'), lock.owner.bytes],
          fee: Uint64(2000),
        }).submit()
      }

      lock.bonafideIssued = false
      this.locks(lockId).value = lock
    }
  }

  // ══════════════════════════════════════════════════════════════
  // READ-ONLY VIEWS
  // ══════════════════════════════════════════════════════════════

  @arc4.abimethod({ readonly: true })
  getLockInfo(lockId: Uint64): LockRecord {
    assert(this.locks(lockId).exists, 'Lock not found')
    return this.locks(lockId).value
  }

  @arc4.abimethod({ readonly: true })
  getDaysRemaining(lockId: Uint64): Uint64 {
    assert(this.locks(lockId).exists, 'Lock not found')
    const lock = this.locks(lockId).value
    if (Global.round >= lock.lockEndRound) return Uint64(0)
    return (lock.lockEndRound - Global.round) / ROUNDS_PER_DAY
  }

  @arc4.abimethod({ readonly: true })
  isBonafideAtRisk(lockId: Uint64): boolean {
    if (!this.locks(lockId).exists) return false
    const lock = this.locks(lockId).value
    if (!lock.active || !lock.bonafideIssued || lock.autoExtend) return false
    // At risk if within 1 day of expiry
    return Global.round >= lock.lockEndRound - ROUNDS_PER_DAY
  }
}
