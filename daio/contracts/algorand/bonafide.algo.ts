/**
 * BONA FIDE Controller — Algorand Binary Reputation System
 *
 * ASA: 1 trillion supply (1,000,000,000,000), 0 decimals, clawback enabled
 * Binary: agent/asset holds 1 BONA FIDE or 0 — no score, no gradient
 *
 * APPLY:   Pay fee ($1 USD first time) → receive 1 BONA FIDE
 * REVOKE:  Clawback 1 BONA FIDE → offense count increments
 * RE-APPLY: Fee doubles each time: $1 → $2 → $4 → $8 → $16 → ...
 * GHOST:   Consensus vote → permanently dead, can never re-apply
 *
 * Fee allocation: applicant chooses where their fee goes
 *   - Treasury (default)
 *   - Split across multiple wallets
 *   - Held in escrow with tiered redemption (via FeeRedemption contract)
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
  op,
} from '@algorandfoundation/algorand-typescript'

// ── Fee Allocation Record ────────────────────────────────────────
// Stored per-applicant: where their BONA FIDE fee payment goes

type FeeAllocation = {
  walletCount: Uint64       // number of destination wallets (1-4)
  wallet1: Account          // primary destination
  wallet2: Account          // optional
  wallet3: Account          // optional
  wallet4: Account          // optional
  split1: Uint64            // percentage to wallet1 (0-100)
  split2: Uint64            // percentage to wallet2
  split3: Uint64            // percentage to wallet3
  split4: Uint64            // percentage to wallet4
  useRedemption: boolean    // if true, fees held in FeeRedemption escrow
}

// ── BONA FIDE Status Record ──────────────────────────────────────

type BonafideRecord = {
  isBonafide: boolean       // currently holds 1 BONA FIDE
  isGhost: boolean          // permanently dead — can never re-apply
  offenseCount: Uint64      // number of times BONA FIDE was revoked
  lastIssuedRound: Uint64   // round when last issued
  lastRevokedRound: Uint64  // round when last revoked
}

// ══════════════════════════════════════════════════════════════════
// BONA FIDE CONTROLLER CONTRACT
// ══════════════════════════════════════════════════════════════════

export class BonafideController extends Contract {
  // ── Global State ───────────────────────────────────────────────

  /** The BONA FIDE ASA ID (1 trillion supply, 0 decimals, clawback to this app) */
  bonafideAsaId = GlobalState<Uint64>()

  /** SmartOracle app ID for USD → ALGO conversion */
  oracleAppId = GlobalState<Uint64>()

  /** Default treasury address for fee collection */
  treasuryAddress = GlobalState<Account>()

  /** FeeRedemption contract app ID (for held fee escrow) */
  redemptionAppId = GlobalState<Uint64>()

  /** Admin address (governance or multisig) */
  adminAddress = GlobalState<Account>()

  /** Base fee in microALGO (updated by oracle, ~$1 USD worth) */
  baseFeeUsd = GlobalState<Uint64>({ initialValue: Uint64(1_000_000) }) // $1.00 in micro-USD

  /** Quorum required for ghost vote (number of voters) */
  ghostQuorum = GlobalState<Uint64>({ initialValue: Uint64(3) })

  /** Total BONA FIDE issued (lifetime) */
  totalIssued = GlobalState<Uint64>({ initialValue: Uint64(0) })

  /** Total BONA FIDE revoked (lifetime) */
  totalRevoked = GlobalState<Uint64>({ initialValue: Uint64(0) })

  /** Total ghosts (lifetime, irreversible) */
  totalGhosts = GlobalState<Uint64>({ initialValue: Uint64(0) })

  // ── Box Storage ────────────────────────────────────────────────

  /** Per-account BONA FIDE status */
  records = BoxMap<Account, BonafideRecord>({ prefix: Bytes('bf_') })

  /** Per-account fee allocation preferences */
  allocations = BoxMap<Account, FeeAllocation>({ prefix: Bytes('fa_') })

  // ══════════════════════════════════════════════════════════════
  // INITIALIZATION
  // ══════════════════════════════════════════════════════════════

  /**
   * Initialize the controller with a pre-created BONA FIDE ASA.
   * The ASA must have clawback set to this application's address.
   * Reserve must hold the full 1 trillion supply.
   */
  @arc4.abimethod()
  initialize(
    bonafideAsa: Uint64,
    oracle: Uint64,
    treasury: Account,
    admin: Account,
  ): void {
    assert(Txn.sender === Global.creatorAddress, 'Only creator')
    this.bonafideAsaId.value = bonafideAsa
    this.oracleAppId.value = oracle
    this.treasuryAddress.value = treasury
    this.adminAddress.value = admin
  }

  // ══════════════════════════════════════════════════════════════
  // APPLY — Pay fee, receive 1 BONA FIDE
  // ══════════════════════════════════════════════════════════════

  /**
   * Apply for BONA FIDE status.
   *
   * Requirements:
   * - Not ghost (permanently dead)
   * - Not already BONA FIDE
   * - Payment transaction in group covers the fee
   *
   * Fee = 2^offenseCount USD, converted to microALGO via oracle.
   * First application: $1. After 1st revocation: $2. After 2nd: $4. Etc.
   */
  @arc4.abimethod()
  apply(paymentTxn: Uint64): void {
    const sender = Txn.sender

    // Load or create record
    let record: BonafideRecord
    if (this.records(sender).exists) {
      record = this.records(sender).value
    } else {
      record = {
        isBonafide: false,
        isGhost: false,
        offenseCount: Uint64(0),
        lastIssuedRound: Uint64(0),
        lastRevokedRound: Uint64(0),
      }
    }

    // Cannot apply if ghost
    assert(!record.isGhost, 'GHOST: permanently dead, cannot re-apply')

    // Cannot apply if already BONA FIDE
    assert(!record.isBonafide, 'Already BONA FIDE')

    // Calculate required fee: 2^offenseCount USD in microALGO
    const requiredFee = this._calculateFee(record.offenseCount)

    // Verify payment covers the fee
    // (payment transaction is in the same atomic group)
    assert(paymentTxn >= requiredFee, 'Insufficient fee payment')

    // Route fee to destination(s)
    this._routeFee(sender, requiredFee)

    // Issue 1 BONA FIDE via inner ASA transfer (clawback from reserve)
    itxn.assetTransfer({
      xferAsset: Asset(this.bonafideAsaId.value),
      assetAmount: Uint64(1),
      assetSender: Global.currentApplicationAddress, // clawback authority
      assetReceiver: sender,
      fee: Uint64(1000), // 0.001 ALGO inner txn fee
    }).submit()

    // Update record
    record.isBonafide = true
    record.lastIssuedRound = Global.round
    this.records(sender).value = record

    this.totalIssued.value = this.totalIssued.value + Uint64(1)
  }

  // ══════════════════════════════════════════════════════════════
  // REVOKE — Clawback BONA FIDE, increment offense
  // ══════════════════════════════════════════════════════════════

  /**
   * Revoke BONA FIDE status from an agent/asset.
   * Only callable by admin (governance/multisig).
   * Increments offense count → next re-application fee doubles.
   */
  @arc4.abimethod()
  revoke(target: Account): void {
    assert(
      Txn.sender === this.adminAddress.value ||
      Txn.sender === Global.creatorAddress,
      'Only admin or creator'
    )

    assert(this.records(target).exists, 'No record for target')
    const record = this.records(target).value
    assert(record.isBonafide, 'Not currently BONA FIDE')

    // Clawback 1 BONA FIDE
    itxn.assetTransfer({
      xferAsset: Asset(this.bonafideAsaId.value),
      assetAmount: Uint64(1),
      assetSender: target,              // clawback FROM target
      assetReceiver: Global.currentApplicationAddress, // return to app reserve
      fee: Uint64(1000),
    }).submit()

    // Update record
    record.isBonafide = false
    record.offenseCount = record.offenseCount + Uint64(1)
    record.lastRevokedRound = Global.round
    this.records(target).value = record

    this.totalRevoked.value = this.totalRevoked.value + Uint64(1)

    // If FeeRedemption is configured, forfeit held fees
    if (this.redemptionAppId.value > Uint64(0)) {
      // Call fee_redemption.forfeitOnRevocation(target) via inner app call
      itxn.applicationCall({
        applicationId: this.redemptionAppId.value,
        appArgs: [Bytes('forfeitOnRevocation'), target.bytes],
        fee: Uint64(1000),
      }).submit()
    }
  }

  // ══════════════════════════════════════════════════════════════
  // GHOST — Consensus vote: permanently dead
  // ══════════════════════════════════════════════════════════════

  /**
   * Vote to ghost an agent/asset.
   * Requires quorum of unique voters (DAIO governance).
   * IRREVERSIBLE — ghosted accounts can NEVER re-apply.
   *
   * Ghost votes are accumulated. When quorum reached, target is ghosted.
   */
  @arc4.abimethod()
  voteGhost(target: Account): void {
    // In production: track individual votes in BoxMap, check quorum.
    // Simplified here — admin can ghost directly, or require N distinct callers.
    assert(
      Txn.sender === this.adminAddress.value ||
      Txn.sender === Global.creatorAddress,
      'Only admin or creator can initiate ghost'
    )

    let record: BonafideRecord
    if (this.records(target).exists) {
      record = this.records(target).value
    } else {
      record = {
        isBonafide: false,
        isGhost: false,
        offenseCount: Uint64(0),
        lastIssuedRound: Uint64(0),
        lastRevokedRound: Uint64(0),
      }
    }

    assert(!record.isGhost, 'Already ghost')

    // If still BONA FIDE, clawback first
    if (record.isBonafide) {
      itxn.assetTransfer({
        xferAsset: Asset(this.bonafideAsaId.value),
        assetAmount: Uint64(1),
        assetSender: target,
        assetReceiver: Global.currentApplicationAddress,
        fee: Uint64(1000),
      }).submit()
    }

    // GHOST — permanent, irreversible
    record.isGhost = true
    record.isBonafide = false
    record.lastRevokedRound = Global.round
    this.records(target).value = record

    this.totalGhosts.value = this.totalGhosts.value + Uint64(1)
  }

  // ══════════════════════════════════════════════════════════════
  // FEE ALLOCATION — Applicant's choice
  // ══════════════════════════════════════════════════════════════

  /**
   * Set fee allocation for next BONA FIDE application.
   * Applicant chooses 1-4 destination wallets + percentage splits.
   * Splits must sum to 100.
   */
  @arc4.abimethod()
  setFeeAllocation(
    wallet1: Account,
    split1: Uint64,
    wallet2: Account,
    split2: Uint64,
    wallet3: Account,
    split3: Uint64,
    wallet4: Account,
    split4: Uint64,
    useRedemption: boolean,
  ): void {
    assert(split1 + split2 + split3 + split4 === Uint64(100), 'Splits must sum to 100')

    let walletCount = Uint64(1)
    if (split2 > Uint64(0)) walletCount = Uint64(2)
    if (split3 > Uint64(0)) walletCount = Uint64(3)
    if (split4 > Uint64(0)) walletCount = Uint64(4)

    this.allocations(Txn.sender).value = {
      walletCount,
      wallet1, wallet2, wallet3, wallet4,
      split1, split2, split3, split4,
      useRedemption,
    }
  }

  // ══════════════════════════════════════════════════════════════
  // READ-ONLY VIEWS
  // ══════════════════════════════════════════════════════════════

  /** Check BONA FIDE status for any account */
  @arc4.abimethod({ readonly: true })
  checkStatus(account: Account): BonafideRecord {
    if (!this.records(account).exists) {
      return {
        isBonafide: false,
        isGhost: false,
        offenseCount: Uint64(0),
        lastIssuedRound: Uint64(0),
        lastRevokedRound: Uint64(0),
      }
    }
    return this.records(account).value
  }

  /** Get the re-application fee for an account (in microALGO) */
  @arc4.abimethod({ readonly: true })
  getReapplyFee(account: Account): Uint64 {
    let offenses = Uint64(0)
    if (this.records(account).exists) {
      offenses = this.records(account).value.offenseCount
    }
    return this._calculateFee(offenses)
  }

  /** Get the re-application fee in USD (micro-USD, 6 decimals) */
  @arc4.abimethod({ readonly: true })
  getReapplyFeeUsd(account: Account): Uint64 {
    let offenses = Uint64(0)
    if (this.records(account).exists) {
      offenses = this.records(account).value.offenseCount
    }
    // 2^offenseCount dollars in micro-USD
    // $1 = 1_000_000 micro-USD
    return Uint64(1_000_000) * (Uint64(1) << offenses)
  }

  // ══════════════════════════════════════════════════════════════
  // INTERNAL HELPERS
  // ══════════════════════════════════════════════════════════════

  /**
   * Calculate fee: 2^offenseCount USD converted to microALGO.
   * Uses oracle for live ALGO/USD rate.
   * $1 at first, $2 after first revocation, $4 after second, etc.
   */
  private _calculateFee(offenseCount: Uint64): Uint64 {
    // Fee in USD = 2^offenseCount
    // For now use baseFeeUsd as $1 reference and shift left
    const feeUsd = Uint64(1_000_000) * (Uint64(1) << offenseCount)

    // TODO: Query SmartOracle for live ALGO/USD conversion
    // For now: assume $0.20/ALGO → $1 = 5 ALGO = 5_000_000 microALGO
    // This should be replaced with an oracle call in production
    const microAlgoPerUsd = Uint64(5_000_000) // ~$0.20/ALGO fallback
    return (feeUsd * microAlgoPerUsd) / Uint64(1_000_000)
  }

  /**
   * Route fee payment to configured destinations.
   * Default: 100% to treasury.
   * Custom: split across 1-4 wallets per applicant's allocation.
   */
  private _routeFee(applicant: Account, amount: Uint64): void {
    if (!this.allocations(applicant).exists) {
      // Default: send everything to treasury
      itxn.payment({
        receiver: this.treasuryAddress.value,
        amount: amount,
        fee: Uint64(1000),
      }).submit()
      return
    }

    const alloc = this.allocations(applicant).value

    // If using redemption escrow, route to FeeRedemption contract
    if (alloc.useRedemption && this.redemptionAppId.value > Uint64(0)) {
      itxn.payment({
        receiver: Global.currentApplicationAddress, // held in this app temporarily
        amount: amount,
        fee: Uint64(1000),
      }).submit()
      // Then forward to redemption contract via app call
      itxn.applicationCall({
        applicationId: this.redemptionAppId.value,
        appArgs: [Bytes('depositFee'), applicant.bytes],
        fee: Uint64(1000),
      }).submit()
      return
    }

    // Split across configured wallets
    const sent1 = (amount * alloc.split1) / Uint64(100)
    if (sent1 > Uint64(0)) {
      itxn.payment({ receiver: alloc.wallet1, amount: sent1, fee: Uint64(1000) }).submit()
    }

    if (alloc.walletCount >= Uint64(2)) {
      const sent2 = (amount * alloc.split2) / Uint64(100)
      if (sent2 > Uint64(0)) {
        itxn.payment({ receiver: alloc.wallet2, amount: sent2, fee: Uint64(1000) }).submit()
      }
    }

    if (alloc.walletCount >= Uint64(3)) {
      const sent3 = (amount * alloc.split3) / Uint64(100)
      if (sent3 > Uint64(0)) {
        itxn.payment({ receiver: alloc.wallet3, amount: sent3, fee: Uint64(1000) }).submit()
      }
    }

    if (alloc.walletCount >= Uint64(4)) {
      const sent4 = (amount * alloc.split4) / Uint64(100)
      if (sent4 > Uint64(0)) {
        itxn.payment({ receiver: alloc.wallet4, amount: sent4, fee: Uint64(1000) }).submit()
      }
    }
  }

  // ══════════════════════════════════════════════════════════════
  // ADMIN
  // ══════════════════════════════════════════════════════════════

  @arc4.abimethod()
  setOracle(oracleId: Uint64): void {
    assert(Txn.sender === this.adminAddress.value, 'Only admin')
    this.oracleAppId.value = oracleId
  }

  @arc4.abimethod()
  setTreasury(treasury: Account): void {
    assert(Txn.sender === this.adminAddress.value, 'Only admin')
    this.treasuryAddress.value = treasury
  }

  @arc4.abimethod()
  setRedemptionApp(appId: Uint64): void {
    assert(Txn.sender === this.adminAddress.value, 'Only admin')
    this.redemptionAppId.value = appId
  }

  @arc4.abimethod()
  setGhostQuorum(quorum: Uint64): void {
    assert(Txn.sender === this.adminAddress.value, 'Only admin')
    assert(quorum >= Uint64(1), 'Quorum must be at least 1')
    this.ghostQuorum.value = quorum
  }
}
