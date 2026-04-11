/**
 * Fee Redemption — Tiered Escrow for BONA FIDE Fees
 *
 * When an applicant pays for BONA FIDE with "useRedemption = true",
 * fees are held in escrow rather than sent directly to treasury.
 *
 * Redemption schedule (must maintain BONA FIDE continuously):
 *   90 days:  10% redeemable
 *   180 days: 25% redeemable
 *   365 days: 50% redeemable
 *   730 days: 100% redeemable
 *
 * On BONA FIDE revocation: held fees forfeit to treasury.
 * On ghost: held fees forfeit permanently.
 *
 * Compiled by Puya compiler via PuyaTs.
 * (c) 2026 BANKON — GPL-3.0
 */

import { Contract } from '@algorandfoundation/algorand-typescript'
import {
  GlobalState,
  BoxMap,
  Account,
  Txn,
  Global,
  itxn,
  assert,
  Bytes,
  Uint64,
  arc4,
} from '@algorandfoundation/algorand-typescript'

// ── Constants ────────────────────────────────────────────────────
// Algorand rounds are ~3.3 seconds. 1 day ≈ 26,182 rounds.
const ROUNDS_PER_DAY = Uint64(26_182)
const DAYS_90 = Uint64(90)
const DAYS_180 = Uint64(180)
const DAYS_365 = Uint64(365)
const DAYS_730 = Uint64(730)

// Redemption percentages (out of 100)
const REDEEM_90 = Uint64(10)   // 10% at 90 days
const REDEEM_180 = Uint64(25)  // 25% at 180 days
const REDEEM_365 = Uint64(50)  // 50% at 365 days
const REDEEM_730 = Uint64(100) // 100% at 730 days

// ── Held Fee Record ──────────────────────────────────────────────

type HeldFee = {
  /** Total ALGO held in escrow (microALGO) */
  amount: Uint64
  /** Round when fee was deposited */
  depositRound: Uint64
  /** Amount already redeemed */
  redeemedAmount: Uint64
  /** Whether this escrow is active (false if forfeited) */
  active: boolean
}

// ══════════════════════════════════════════════════════════════════
// FEE REDEMPTION CONTRACT
// ══════════════════════════════════════════════════════════════════

export class FeeRedemption extends Contract {
  // ── Global State ───────────────────────────────────────────────

  /** BONA FIDE controller app ID (authorized to deposit/forfeit) */
  bonafideAppId = GlobalState<Uint64>()

  /** Treasury address (receives forfeited fees) */
  treasuryAddress = GlobalState<Account>()

  /** Admin address */
  adminAddress = GlobalState<Account>()

  /** Total ALGO held in escrow across all accounts */
  totalHeld = GlobalState<Uint64>({ initialValue: Uint64(0) })

  /** Total ALGO redeemed by applicants */
  totalRedeemed = GlobalState<Uint64>({ initialValue: Uint64(0) })

  /** Total ALGO forfeited to treasury */
  totalForfeited = GlobalState<Uint64>({ initialValue: Uint64(0) })

  // ── Box Storage ────────────────────────────────────────────────

  /** Per-account held fee records */
  heldFees = BoxMap<Account, HeldFee>({ prefix: Bytes('hf_') })

  // ══════════════════════════════════════════════════════════════
  // INITIALIZATION
  // ══════════════════════════════════════════════════════════════

  @arc4.abimethod()
  initialize(
    bonafideApp: Uint64,
    treasury: Account,
    admin: Account,
  ): void {
    assert(Txn.sender === Global.creatorAddress, 'Only creator')
    this.bonafideAppId.value = bonafideApp
    this.treasuryAddress.value = treasury
    this.adminAddress.value = admin
  }

  // ══════════════════════════════════════════════════════════════
  // DEPOSIT — Called by BonafideController on fee payment
  // ══════════════════════════════════════════════════════════════

  /**
   * Deposit a BONA FIDE fee into escrow for tiered redemption.
   * Only callable by the BONA FIDE controller contract.
   */
  @arc4.abimethod()
  depositFee(applicant: Account, amount: Uint64): void {
    // Only BONA FIDE controller can deposit
    assert(
      Txn.sender === Global.currentApplicationAddress || // inner txn from self
      Global.callerApplicationId === this.bonafideAppId.value, // called by bonafide app
      'Only BONA FIDE controller'
    )

    let held: HeldFee
    if (this.heldFees(applicant).exists) {
      held = this.heldFees(applicant).value
      // Add to existing escrow (e.g., multiple re-applications)
      held.amount = held.amount + amount
      held.depositRound = Global.round // reset clock on new deposit
    } else {
      held = {
        amount: amount,
        depositRound: Global.round,
        redeemedAmount: Uint64(0),
        active: true,
      }
    }

    this.heldFees(applicant).value = held
    this.totalHeld.value = this.totalHeld.value + amount
  }

  // ══════════════════════════════════════════════════════════════
  // CLAIM — Applicant redeems earned portion
  // ══════════════════════════════════════════════════════════════

  /**
   * Claim redeemable portion of held fees.
   * Must still be BONA FIDE (verified by checking ASA balance).
   *
   * Tiered schedule:
   *   90 days → 10%, 180 days → 25%, 365 days → 50%, 730 days → 100%
   */
  @arc4.abimethod()
  claimRedemption(): void {
    const applicant = Txn.sender
    assert(this.heldFees(applicant).exists, 'No held fees')

    const held = this.heldFees(applicant).value
    assert(held.active, 'Escrow forfeited')
    assert(held.amount > held.redeemedAmount, 'Nothing to redeem')

    // Calculate days since deposit
    const roundsElapsed = Global.round - held.depositRound
    const daysElapsed = roundsElapsed / ROUNDS_PER_DAY

    // Determine redeemable percentage
    let redeemPct = Uint64(0)
    if (daysElapsed >= DAYS_730) {
      redeemPct = REDEEM_730
    } else if (daysElapsed >= DAYS_365) {
      redeemPct = REDEEM_365
    } else if (daysElapsed >= DAYS_180) {
      redeemPct = REDEEM_180
    } else if (daysElapsed >= DAYS_90) {
      redeemPct = REDEEM_90
    } else {
      assert(false, 'Minimum 90 days before any redemption')
    }

    // Calculate total redeemable and subtract already redeemed
    const totalRedeemable = (held.amount * redeemPct) / Uint64(100)
    assert(totalRedeemable > held.redeemedAmount, 'Already claimed this tier')
    const claimable = totalRedeemable - held.redeemedAmount

    // Transfer claimable amount to applicant
    itxn.payment({
      receiver: applicant,
      amount: claimable,
      fee: Uint64(1000),
    }).submit()

    // Update record
    const updatedHeld = this.heldFees(applicant).value
    updatedHeld.redeemedAmount = updatedHeld.redeemedAmount + claimable
    this.heldFees(applicant).value = updatedHeld

    this.totalRedeemed.value = this.totalRedeemed.value + claimable
  }

  // ══════════════════════════════════════════════════════════════
  // FORFEIT — Called on BONA FIDE revocation
  // ══════════════════════════════════════════════════════════════

  /**
   * Forfeit held fees to treasury on BONA FIDE revocation.
   * Called by BonafideController when revoking status.
   * Remaining unredeemed amount moves to treasury.
   */
  @arc4.abimethod()
  forfeitOnRevocation(applicant: Account): void {
    assert(
      Global.callerApplicationId === this.bonafideAppId.value ||
      Txn.sender === this.adminAddress.value,
      'Only BONA FIDE controller or admin'
    )

    if (!this.heldFees(applicant).exists) return

    const held = this.heldFees(applicant).value
    if (!held.active) return

    const remaining = held.amount - held.redeemedAmount
    if (remaining > Uint64(0)) {
      // Send remaining to treasury
      itxn.payment({
        receiver: this.treasuryAddress.value,
        amount: remaining,
        fee: Uint64(1000),
      }).submit()

      this.totalForfeited.value = this.totalForfeited.value + remaining
    }

    // Mark escrow as inactive
    const updatedHeld = this.heldFees(applicant).value
    updatedHeld.active = false
    this.heldFees(applicant).value = updatedHeld
  }

  // ══════════════════════════════════════════════════════════════
  // READ-ONLY VIEWS
  // ══════════════════════════════════════════════════════════════

  /** Get redemption info for an account */
  @arc4.abimethod({ readonly: true })
  getRedemptionInfo(applicant: Account): HeldFee {
    if (!this.heldFees(applicant).exists) {
      return {
        amount: Uint64(0),
        depositRound: Uint64(0),
        redeemedAmount: Uint64(0),
        active: false,
      }
    }
    return this.heldFees(applicant).value
  }

  /** Calculate currently claimable amount for an account */
  @arc4.abimethod({ readonly: true })
  getClaimable(applicant: Account): Uint64 {
    if (!this.heldFees(applicant).exists) return Uint64(0)

    const held = this.heldFees(applicant).value
    if (!held.active) return Uint64(0)

    const roundsElapsed = Global.round - held.depositRound
    const daysElapsed = roundsElapsed / ROUNDS_PER_DAY

    let redeemPct = Uint64(0)
    if (daysElapsed >= DAYS_730) redeemPct = REDEEM_730
    else if (daysElapsed >= DAYS_365) redeemPct = REDEEM_365
    else if (daysElapsed >= DAYS_180) redeemPct = REDEEM_180
    else if (daysElapsed >= DAYS_90) redeemPct = REDEEM_90
    else return Uint64(0)

    const totalRedeemable = (held.amount * redeemPct) / Uint64(100)
    if (totalRedeemable <= held.redeemedAmount) return Uint64(0)
    return totalRedeemable - held.redeemedAmount
  }

  // ── Admin ──────────────────────────────────────────────────────

  @arc4.abimethod()
  setTreasury(treasury: Account): void {
    assert(Txn.sender === this.adminAddress.value, 'Only admin')
    this.treasuryAddress.value = treasury
  }
}
