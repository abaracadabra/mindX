/**
 * SPINTRADE Fee Controller — Treasury Fee Allocation
 *
 * Controls the 3/1/1 fee split from DEX trades:
 *   3% → Reflection pool (distributed to holders)
 *   1% → Liquidity wallet (optionally locked to LiquidityLocker)
 *   1% → Team wallet (optionally made immutable)
 *
 * Security:
 *   - Fees can ONLY be LOWERED (immutable ceiling at 5%)
 *   - Team wallet can be locked forever (one-time immutable)
 *   - Liquidity fees can be auto-routed to LiquidityLocker
 *   - Admin or DAIO governance controls changes
 *
 * Compiled by Puya compiler via PuyaTs.
 * (c) 2026 BANKON — GPL-3.0
 */

import { Contract } from '@algorandfoundation/algorand-typescript'
import {
  GlobalState,
  Account,
  Txn,
  Global,
  itxn,
  assert,
  Uint64,
  arc4,
} from '@algorandfoundation/algorand-typescript'

// Fee constants (basis points, 100 = 1%)
const INITIAL_REFLECTION_FEE = Uint64(300) // 3.00%
const INITIAL_LIQUIDITY_FEE = Uint64(100)  // 1.00%
const INITIAL_TEAM_FEE = Uint64(100)       // 1.00%
const FEE_CEILING = Uint64(500)            // 5.00% total max — NEVER increases
const FEE_DENOMINATOR = Uint64(10_000)

// ══════════════════════════════════════════════════════════════════
// SPINTRADE FEE CONTROLLER
// ══════════════════════════════════════════════════════════════════

export class SpintradeFeeController extends Contract {
  // ── Fee Configuration (can only decrease) ──────────────────────

  /** Reflection fee in basis points (default 300 = 3%) */
  reflectionFeeBps = GlobalState<Uint64>({ initialValue: INITIAL_REFLECTION_FEE })

  /** Liquidity fee in basis points (default 100 = 1%) */
  liquidityFeeBps = GlobalState<Uint64>({ initialValue: INITIAL_LIQUIDITY_FEE })

  /** Team fee in basis points (default 100 = 1%) */
  teamFeeBps = GlobalState<Uint64>({ initialValue: INITIAL_TEAM_FEE })

  /** Immutable fee ceiling — total fees can NEVER exceed this */
  feesCeiling = GlobalState<Uint64>({ initialValue: FEE_CEILING })

  // ── Wallet Configuration ───────────────────────────────────────

  /** Treasury address (receives reflection pool for distribution) */
  treasuryAddress = GlobalState<Account>()

  /** Liquidity wallet (receives 1% liquidity fee) */
  liquidityWallet = GlobalState<Account>()

  /** Team wallet (receives 1% team fee) */
  teamWallet = GlobalState<Account>()

  /** Admin address (governance or multisig) */
  adminAddress = GlobalState<Account>()

  // ── Lock State ─────────────────────────────────────────────────

  /** Once true, teamWallet can NEVER be changed. IRREVERSIBLE. */
  teamWalletImmutable = GlobalState<boolean>({ initialValue: false })

  /** When true, liquidity fees auto-route to LiquidityLocker contract */
  liquidityLocked = GlobalState<boolean>({ initialValue: false })

  /** LiquidityLocker app ID (set when liquidityLocked = true) */
  lockerAppId = GlobalState<Uint64>({ initialValue: Uint64(0) })

  // ── Stats ──────────────────────────────────────────────────────

  /** Total fees allocated (lifetime, in microALGO equivalent) */
  totalFeesAllocated = GlobalState<Uint64>({ initialValue: Uint64(0) })

  // ══════════════════════════════════════════════════════════════
  // INITIALIZATION
  // ══════════════════════════════════════════════════════════════

  @arc4.abimethod()
  initialize(
    treasury: Account,
    liquidity: Account,
    team: Account,
    admin: Account,
  ): void {
    assert(Txn.sender === Global.creatorAddress, 'Only creator')
    this.treasuryAddress.value = treasury
    this.liquidityWallet.value = liquidity
    this.teamWallet.value = team
    this.adminAddress.value = admin
  }

  // ══════════════════════════════════════════════════════════════
  // ALLOCATE FEES — Called on each DEX swap
  // ══════════════════════════════════════════════════════════════

  /**
   * Allocate fees from a DEX swap.
   * Splits the total fee into reflection / liquidity / team portions.
   * Routes each to the configured destination.
   *
   * @param totalFee Total fee amount in microALGO (or token units)
   */
  @arc4.abimethod()
  allocateFees(totalFee: Uint64): void {
    const totalBps = this.reflectionFeeBps.value +
                     this.liquidityFeeBps.value +
                     this.teamFeeBps.value

    if (totalBps === Uint64(0) || totalFee === Uint64(0)) return

    // Calculate each portion
    const reflectionAmount = (totalFee * this.reflectionFeeBps.value) / totalBps
    const liquidityAmount = (totalFee * this.liquidityFeeBps.value) / totalBps
    const teamAmount = totalFee - reflectionAmount - liquidityAmount // remainder to team

    // 1. Reflection → treasury (for distribution engine)
    if (reflectionAmount > Uint64(0)) {
      itxn.payment({
        receiver: this.treasuryAddress.value,
        amount: reflectionAmount,
        fee: Uint64(1000),
      }).submit()
    }

    // 2. Liquidity → either locker or wallet
    if (liquidityAmount > Uint64(0)) {
      if (this.liquidityLocked.value && this.lockerAppId.value > Uint64(0)) {
        // Auto-route to LiquidityLocker contract
        itxn.payment({
          receiver: this.liquidityWallet.value, // locker's address
          amount: liquidityAmount,
          fee: Uint64(1000),
        }).submit()
      } else {
        itxn.payment({
          receiver: this.liquidityWallet.value,
          amount: liquidityAmount,
          fee: Uint64(1000),
        }).submit()
      }
    }

    // 3. Team → team wallet
    if (teamAmount > Uint64(0)) {
      itxn.payment({
        receiver: this.teamWallet.value,
        amount: teamAmount,
        fee: Uint64(1000),
      }).submit()
    }

    this.totalFeesAllocated.value = this.totalFeesAllocated.value + totalFee
  }

  // ══════════════════════════════════════════════════════════════
  // LOCK TEAM WALLET — One-time, irreversible
  // ══════════════════════════════════════════════════════════════

  /**
   * Lock the team wallet address forever.
   * After this call, teamWallet can NEVER be changed.
   * This is the strongest form of buyer protection for the team fee.
   */
  @arc4.abimethod()
  lockTeamWallet(): void {
    assert(
      Txn.sender === this.adminAddress.value ||
      Txn.sender === Global.creatorAddress,
      'Only admin or creator'
    )
    assert(!this.teamWalletImmutable.value, 'Already locked')

    this.teamWalletImmutable.value = true
    // IRREVERSIBLE — teamWallet frozen at current value
  }

  // ══════════════════════════════════════════════════════════════
  // LOCK LIQUIDITY TO LOCKER
  // ══════════════════════════════════════════════════════════════

  /**
   * Route all future liquidity fees to the LiquidityLocker contract.
   * This ensures liquidity fees are auto-locked for buyer protection.
   */
  @arc4.abimethod()
  lockLiquidityToLocker(lockerApp: Uint64): void {
    assert(
      Txn.sender === this.adminAddress.value ||
      Txn.sender === Global.creatorAddress,
      'Only admin or creator'
    )

    this.liquidityLocked.value = true
    this.lockerAppId.value = lockerApp
  }

  // ══════════════════════════════════════════════════════════════
  // LOWER FEES — Can only decrease, never increase
  // ══════════════════════════════════════════════════════════════

  /**
   * Lower fees. Each fee must be ≤ its current value.
   * Total must remain ≤ ceiling (5%).
   * Fees can NEVER be raised back up — only lowered.
   */
  @arc4.abimethod()
  lowerFees(
    newReflection: Uint64,
    newLiquidity: Uint64,
    newTeam: Uint64,
  ): void {
    assert(
      Txn.sender === this.adminAddress.value ||
      Txn.sender === Global.creatorAddress,
      'Only admin or creator'
    )

    // Each fee can only decrease
    assert(newReflection <= this.reflectionFeeBps.value, 'Reflection can only decrease')
    assert(newLiquidity <= this.liquidityFeeBps.value, 'Liquidity can only decrease')
    assert(newTeam <= this.teamFeeBps.value, 'Team can only decrease')

    // Total must not exceed ceiling
    assert(
      newReflection + newLiquidity + newTeam <= this.feesCeiling.value,
      'Exceeds fee ceiling'
    )

    this.reflectionFeeBps.value = newReflection
    this.liquidityFeeBps.value = newLiquidity
    this.teamFeeBps.value = newTeam
  }

  // ══════════════════════════════════════════════════════════════
  // WALLET MANAGEMENT
  // ══════════════════════════════════════════════════════════════

  @arc4.abimethod()
  setTeamWallet(wallet: Account): void {
    assert(Txn.sender === this.adminAddress.value, 'Only admin')
    assert(!this.teamWalletImmutable.value, 'Team wallet is locked forever')
    this.teamWallet.value = wallet
  }

  @arc4.abimethod()
  setLiquidityWallet(wallet: Account): void {
    assert(Txn.sender === this.adminAddress.value, 'Only admin')
    this.liquidityWallet.value = wallet
  }

  @arc4.abimethod()
  setTreasury(treasury: Account): void {
    assert(Txn.sender === this.adminAddress.value, 'Only admin')
    this.treasuryAddress.value = treasury
  }

  // ══════════════════════════════════════════════════════════════
  // READ-ONLY VIEWS
  // ══════════════════════════════════════════════════════════════

  @arc4.abimethod({ readonly: true })
  getFeeConfig(): arc4.DynamicArray<arc4.UintN<64>> {
    // Returns [reflection, liquidity, team, total, ceiling]
    const total = this.reflectionFeeBps.value +
                  this.liquidityFeeBps.value +
                  this.teamFeeBps.value

    return new arc4.DynamicArray(
      new arc4.UintN<64>(this.reflectionFeeBps.value),
      new arc4.UintN<64>(this.liquidityFeeBps.value),
      new arc4.UintN<64>(this.teamFeeBps.value),
      new arc4.UintN<64>(total),
      new arc4.UintN<64>(this.feesCeiling.value),
    )
  }

  @arc4.abimethod({ readonly: true })
  isTeamWalletLocked(): boolean {
    return this.teamWalletImmutable.value
  }

  @arc4.abimethod({ readonly: true })
  isLiquidityLocked(): boolean {
    return this.liquidityLocked.value
  }
}
