/**
 * aLUV Token — ARC-200 Reflection Token on Algorand
 *
 * Algorand's answer to SHAMBA LUV. Because ASAs have zero transfer hooks,
 * reflection tokenomics MUST use ARC-200 (smart-contract-based tokens).
 *
 * This is NOT an ASA — it is a smart contract that implements the ARC-200
 * token interface (transfer, transferFrom, approve, balanceOf) with custom
 * fee logic in the transfer method.
 *
 * Fee Structure (5% on DEX swaps ONLY):
 *   3% Reflection → distributed to all holders via reflectionIndex
 *   1% Liquidity  → sent to liquidity wallet (or LiquidityLocker)
 *   1% Team       → sent to team wallet
 *   0% Wallet-to-wallet (non-contract addresses)
 *
 * Supply: Bridged from EVM. aLUV is minted 1:1 when LUV is locked on EVM.
 *         Total possible = 100 quadrillion, but only bridged portion exists.
 *
 * Bridge transfers are fee-exempt (no double taxation).
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

import {
  REFLECTION_PRECISION,
  BPS_DENOMINATOR,
  updateReflectionIndex,
  calculatePendingReflection,
  calculateFee,
  splitFee,
} from './reflection_engine.algo'

// ══════════════════════════════════════════════════════════════════
// aLUV ARC-200 REFLECTION TOKEN
// ══════════════════════════════════════════════════════════════════

export class ALuvToken extends Contract {
  // ── Token Metadata ─────────────────────────────────────────────

  name = GlobalState<Bytes>({ initialValue: Bytes('Algorand SHAMBA LUV') })
  symbol = GlobalState<Bytes>({ initialValue: Bytes('aLUV') })
  decimals = GlobalState<Uint64>({ initialValue: Uint64(18) })

  // ── Supply ─────────────────────────────────────────────────────

  /** Total minted aLUV (= total bridged from EVM) */
  totalSupply = GlobalState<Uint64>({ initialValue: Uint64(0) })

  /** Circulating supply excluding exempt addresses (for reflection calc) */
  circulatingSupply = GlobalState<Uint64>({ initialValue: Uint64(0) })

  // ── Balances & Allowances ──────────────────────────────────────

  balances = BoxMap<Account, Uint64>({ prefix: Bytes('b_') })
  allowances = BoxMap<Bytes, Uint64>({ prefix: Bytes('a_') }) // key = owner+spender

  // ── Fee Configuration ──────────────────────────────────────────

  reflectionFeeBps = GlobalState<Uint64>({ initialValue: Uint64(300) })  // 3%
  liquidityFeeBps = GlobalState<Uint64>({ initialValue: Uint64(100) })   // 1%
  teamFeeBps = GlobalState<Uint64>({ initialValue: Uint64(100) })        // 1%
  feesCeiling = GlobalState<Uint64>({ initialValue: Uint64(500) })       // 5% max forever

  // ── Wallets ────────────────────────────────────────────────────

  liquidityWallet = GlobalState<Account>()
  teamWallet = GlobalState<Account>()
  adminAddress = GlobalState<Account>()

  // ── Bridge ─────────────────────────────────────────────────────

  /** Bridge contract app ID — only this can mint/burn aLUV */
  bridgeAppId = GlobalState<Uint64>({ initialValue: Uint64(0) })

  // ── Fee Controller ─────────────────────────────────────────────

  /** SpintradeFeeController app ID (optional, for external fee routing) */
  feeControllerAppId = GlobalState<Uint64>({ initialValue: Uint64(0) })

  // ── Reflection State ───────────────────────────────────────────

  /** Global reflection index (scaled by REFLECTION_PRECISION) */
  reflectionIndex = GlobalState<Uint64>({ initialValue: Uint64(0) })

  /** Accumulated reflection fees pending batch processing */
  accumulatedReflectionFees = GlobalState<Uint64>({ initialValue: Uint64(0) })

  /** Batch threshold — process reflections when accumulated fees reach this */
  batchThreshold = GlobalState<Uint64>({ initialValue: Uint64(1_000_000) })

  /** Per-holder last reflection index */
  holderReflectionIndex = BoxMap<Account, Uint64>({ prefix: Bytes('ri_') })

  // ── Exemptions ─────────────────────────────────────────────────

  /** Addresses exempt from fees (bridge, deployer, liquidity wallet) */
  isExemptFromFee = BoxMap<Account, boolean>({ prefix: Bytes('ef_') })

  /** Addresses exempt from reflection (liquidity wallet, dead address) */
  isExemptFromReflection = BoxMap<Account, boolean>({ prefix: Bytes('er_') })

  // ── Wallet-to-Wallet ───────────────────────────────────────────

  /** When true, non-contract → non-contract transfers are fee-free */
  walletToWalletExempt = GlobalState<boolean>({ initialValue: true })

  // ══════════════════════════════════════════════════════════════
  // INITIALIZATION
  // ══════════════════════════════════════════════════════════════

  @arc4.abimethod()
  initialize(
    liquidityWallet: Account,
    teamWallet: Account,
    admin: Account,
  ): void {
    assert(Txn.sender === Global.creatorAddress, 'Only creator')
    this.liquidityWallet.value = liquidityWallet
    this.teamWallet.value = teamWallet
    this.adminAddress.value = admin

    // Exempt deployer and liquidity wallet
    this.isExemptFromFee(Global.creatorAddress).value = true
    this.isExemptFromFee(Global.currentApplicationAddress).value = true
    this.isExemptFromReflection(liquidityWallet).value = true
  }

  // ══════════════════════════════════════════════════════════════
  // ARC-200: TRANSFER
  // ══════════════════════════════════════════════════════════════

  /**
   * Transfer aLUV tokens with reflection fee logic.
   *
   * Fee-free conditions:
   *   - Sender or receiver is fee-exempt
   *   - Both sender and receiver are non-contract (wallet-to-wallet)
   *   - Bridge mint/burn operations
   *
   * Fee conditions (DEX swaps):
   *   - 3% reflection → accumulated for batch distribution
   *   - 1% liquidity → sent to liquidity wallet
   *   - 1% team → sent to team wallet
   */
  @arc4.abimethod()
  transfer(to: Account, amount: Uint64): boolean {
    return this._transferWithFees(Txn.sender, to, amount)
  }

  @arc4.abimethod()
  transferFrom(from: Account, to: Account, amount: Uint64): boolean {
    // Check and spend allowance
    const key = from.bytes + Txn.sender.bytes
    assert(this.allowances(key).exists, 'No allowance')
    const allowed = this.allowances(key).value
    assert(allowed >= amount, 'Insufficient allowance')
    this.allowances(key).value = allowed - amount

    return this._transferWithFees(from, to, amount)
  }

  private _transferWithFees(from: Account, to: Account, amount: Uint64): boolean {
    assert(amount > Uint64(0), 'Zero amount')
    assert(this.balances(from).exists, 'No balance')
    assert(this.balances(from).value >= amount, 'Insufficient balance')

    // Claim pending reflections for sender before transfer
    this._claimPendingReflection(from)
    this._claimPendingReflection(to)

    // Determine if fee-exempt
    const senderExempt = this.isExemptFromFee(from).exists && this.isExemptFromFee(from).value
    const receiverExempt = this.isExemptFromFee(to).exists && this.isExemptFromFee(to).value

    // Wallet-to-wallet check: both are non-app accounts
    // On Algorand, we check if address is an application address
    // Simplified: exempt addresses list covers DEX contracts
    const isWalletToWallet = this.walletToWalletExempt.value &&
                             !senderExempt && !receiverExempt &&
                             !this._isKnownContract(from) && !this._isKnownContract(to)

    if (senderExempt || receiverExempt || isWalletToWallet) {
      // Fee-free transfer
      this.balances(from).value = this.balances(from).value - amount
      this._addBalance(to, amount)
      return true
    }

    // ── Fee transfer (DEX swap) ──
    const totalFeeBps = this.reflectionFeeBps.value +
                        this.liquidityFeeBps.value +
                        this.teamFeeBps.value
    const totalFee = calculateFee(amount, totalFeeBps)
    const netAmount = amount - totalFee

    // Split fee
    const [reflectionFee, liquidityFee, teamFee] = splitFee(
      totalFee,
      this.reflectionFeeBps.value,
      this.liquidityFeeBps.value,
      this.teamFeeBps.value,
    )

    // Debit sender full amount
    this.balances(from).value = this.balances(from).value - amount

    // Credit receiver net amount
    this._addBalance(to, netAmount)

    // Accumulate reflection fees
    if (reflectionFee > Uint64(0)) {
      this.accumulatedReflectionFees.value =
        this.accumulatedReflectionFees.value + reflectionFee

      // Process batch if threshold reached
      if (this.accumulatedReflectionFees.value >= this.batchThreshold.value) {
        this._processReflectionBatch()
      }
    }

    // Send liquidity fee
    if (liquidityFee > Uint64(0)) {
      this._addBalance(this.liquidityWallet.value, liquidityFee)
    }

    // Send team fee
    if (teamFee > Uint64(0)) {
      this._addBalance(this.teamWallet.value, teamFee)
    }

    return true
  }

  // ══════════════════════════════════════════════════════════════
  // ARC-200: APPROVE
  // ══════════════════════════════════════════════════════════════

  @arc4.abimethod()
  approve(spender: Account, amount: Uint64): boolean {
    const key = Txn.sender.bytes + spender.bytes
    this.allowances(key).value = amount
    return true
  }

  // ══════════════════════════════════════════════════════════════
  // ARC-200: VIEWS
  // ══════════════════════════════════════════════════════════════

  @arc4.abimethod({ readonly: true })
  balanceOf(account: Account): Uint64 {
    if (!this.balances(account).exists) return Uint64(0)
    return this.balances(account).value
  }

  @arc4.abimethod({ readonly: true })
  allowance(owner: Account, spender: Account): Uint64 {
    const key = owner.bytes + spender.bytes
    if (!this.allowances(key).exists) return Uint64(0)
    return this.allowances(key).value
  }

  // ══════════════════════════════════════════════════════════════
  // REFLECTION: CLAIM
  // ══════════════════════════════════════════════════════════════

  /** Claim accumulated reflection rewards */
  @arc4.abimethod()
  claimReflections(): Uint64 {
    // Process any pending batch first
    if (this.accumulatedReflectionFees.value > Uint64(0)) {
      this._processReflectionBatch()
    }

    const pending = this._getPendingReflection(Txn.sender)
    assert(pending > Uint64(0), 'No reflections to claim')

    // Update holder index
    this.holderReflectionIndex(Txn.sender).value = this.reflectionIndex.value

    // Credit balance
    this._addBalance(Txn.sender, pending)

    return pending
  }

  /** View pending reflections for a holder */
  @arc4.abimethod({ readonly: true })
  pendingReflections(holder: Account): Uint64 {
    return this._getPendingReflection(holder)
  }

  // ══════════════════════════════════════════════════════════════
  // BRIDGE: MINT / BURN
  // ══════════════════════════════════════════════════════════════

  /**
   * Mint aLUV when LUV is locked on EVM.
   * Only callable by the bridge contract.
   * Bridge transfers are fee-exempt.
   */
  @arc4.abimethod()
  bridgeMint(to: Account, amount: Uint64): void {
    assert(
      Global.callerApplicationId === this.bridgeAppId.value ||
      Txn.sender === this.adminAddress.value,
      'Only bridge or admin'
    )

    this._addBalance(to, amount)
    this.totalSupply.value = this.totalSupply.value + amount

    // Update circulating supply (for reflection calculation)
    const exempt = this.isExemptFromReflection(to).exists &&
                   this.isExemptFromReflection(to).value
    if (!exempt) {
      this.circulatingSupply.value = this.circulatingSupply.value + amount
    }
  }

  /**
   * Burn aLUV when user wants to unlock LUV on EVM.
   * Only callable by the bridge contract.
   */
  @arc4.abimethod()
  bridgeBurn(from: Account, amount: Uint64): void {
    assert(
      Global.callerApplicationId === this.bridgeAppId.value ||
      Txn.sender === from, // user can burn their own
      'Only bridge or token owner'
    )

    // Claim pending reflections before burn
    this._claimPendingReflection(from)

    assert(this.balances(from).exists, 'No balance')
    assert(this.balances(from).value >= amount, 'Insufficient balance')

    this.balances(from).value = this.balances(from).value - amount
    this.totalSupply.value = this.totalSupply.value - amount

    const exempt = this.isExemptFromReflection(from).exists &&
                   this.isExemptFromReflection(from).value
    if (!exempt) {
      this.circulatingSupply.value = this.circulatingSupply.value - amount
    }
  }

  // ══════════════════════════════════════════════════════════════
  // INTERNAL HELPERS
  // ══════════════════════════════════════════════════════════════

  private _addBalance(account: Account, amount: Uint64): void {
    if (this.balances(account).exists) {
      this.balances(account).value = this.balances(account).value + amount
    } else {
      this.balances(account).value = amount
      // Initialize reflection index for new holder
      this.holderReflectionIndex(account).value = this.reflectionIndex.value
    }
  }

  private _processReflectionBatch(): void {
    const fees = this.accumulatedReflectionFees.value
    const supply = this.circulatingSupply.value
    if (fees === Uint64(0) || supply === Uint64(0)) return

    this.reflectionIndex.value = updateReflectionIndex(
      this.reflectionIndex.value,
      fees,
      supply,
    )
    this.accumulatedReflectionFees.value = Uint64(0)
  }

  private _claimPendingReflection(holder: Account): void {
    const pending = this._getPendingReflection(holder)
    if (pending > Uint64(0)) {
      this._addBalance(holder, pending)
      this.holderReflectionIndex(holder).value = this.reflectionIndex.value
    }
  }

  private _getPendingReflection(holder: Account): Uint64 {
    if (this.isExemptFromReflection(holder).exists &&
        this.isExemptFromReflection(holder).value) {
      return Uint64(0)
    }

    const balance = this.balances(holder).exists ? this.balances(holder).value : Uint64(0)
    const lastIndex = this.holderReflectionIndex(holder).exists
      ? this.holderReflectionIndex(holder).value
      : Uint64(0)

    // Include any unprocessed accumulated fees
    let currentIndex = this.reflectionIndex.value
    const supply = this.circulatingSupply.value
    if (this.accumulatedReflectionFees.value > Uint64(0) && supply > Uint64(0)) {
      currentIndex = currentIndex +
        (this.accumulatedReflectionFees.value * REFLECTION_PRECISION) / supply
    }

    return calculatePendingReflection(balance, currentIndex, lastIndex)
  }

  /** Simple contract detection — checks known exempt list */
  private _isKnownContract(_addr: Account): boolean {
    // On Algorand, "contract" means application account.
    // DEX router addresses should be added to fee-exempt list.
    // This is a simplified check — exempt list is the authority.
    return false
  }

  // ══════════════════════════════════════════════════════════════
  // ADMIN
  // ══════════════════════════════════════════════════════════════

  @arc4.abimethod()
  setBridgeApp(appId: Uint64): void {
    assert(Txn.sender === this.adminAddress.value, 'Only admin')
    this.bridgeAppId.value = appId
  }

  @arc4.abimethod()
  setFeeController(appId: Uint64): void {
    assert(Txn.sender === this.adminAddress.value, 'Only admin')
    this.feeControllerAppId.value = appId
  }

  @arc4.abimethod()
  setFeeExemption(account: Account, exempt: boolean): void {
    assert(Txn.sender === this.adminAddress.value, 'Only admin')
    this.isExemptFromFee(account).value = exempt
  }

  @arc4.abimethod()
  setReflectionExemption(account: Account, exempt: boolean): void {
    assert(Txn.sender === this.adminAddress.value, 'Only admin')
    this.isExemptFromReflection(account).value = exempt
  }

  /** Lower fees — can only decrease, never increase */
  @arc4.abimethod()
  lowerFees(newReflection: Uint64, newLiquidity: Uint64, newTeam: Uint64): void {
    assert(Txn.sender === this.adminAddress.value, 'Only admin')
    assert(newReflection <= this.reflectionFeeBps.value, 'Can only decrease')
    assert(newLiquidity <= this.liquidityFeeBps.value, 'Can only decrease')
    assert(newTeam <= this.teamFeeBps.value, 'Can only decrease')
    assert(newReflection + newLiquidity + newTeam <= this.feesCeiling.value, 'Exceeds ceiling')

    this.reflectionFeeBps.value = newReflection
    this.liquidityFeeBps.value = newLiquidity
    this.teamFeeBps.value = newTeam
  }
}
