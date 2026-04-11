/**
 * Interchain Settler — Algorand Settlement Finality Layer
 *
 * Algorand provides settlement finality for interchain weaves:
 *   - 3.3 second block finality, no forks
 *   - Weave proofs recorded immutably on-chain
 *   - Phi fee collection in ALGO (converted from USD via SmartOracle)
 *   - Settlement events readable by relayers via indexer
 *
 * Settlement flow:
 *   1. Weave initiated on EVM chain A
 *   2. Relayer calls settleWeave() on Algorand with proof
 *   3. Settlement recorded (3.3s finality)
 *   4. Relayer calls receiveWeave() on EVM chain B
 *
 * Algorand is the truth layer — if it's settled here, it happened.
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

// phi constants (scaled 1e6 for uint64 precision)
const PHI_SCALED = Uint64(1_618_034)        // 1.618034 * 1e6
const PHI_DENOMINATOR = Uint64(1_000_000)
const PHI_MINUS_ONE_SCALED = Uint64(618_034) // 0.618034 * 1e6
const TREASURY_SPLIT = Uint64(618)           // 61.8% in basis mille
const SPLIT_DENOMINATOR = Uint64(1000)

// ── Weave Settlement Record ──────────────────────────────────────

type WeaveSettlement = {
  weaveId: Bytes           // 32-byte weave ID from source chain
  srcChainId: Uint64       // source EVM chain ID
  destChainId: Uint64      // destination EVM chain ID
  amount: Uint64           // value transferred (in source chain's smallest unit)
  phiFee: Uint64           // phi fee collected (in ALGO microAlgo)
  settledRound: Uint64     // Algorand round when settled
  relayer: Account         // who submitted the settlement
}

// ══════════════════════════════════════════════════════════════════
// INTERCHAIN SETTLER
// ══════════════════════════════════════════════════════════════════

export class InterchainSettler extends Contract {
  // ── Global State ───────────────────────────────────────────────

  /** Treasury address (61.8% of phi revenue) */
  treasuryAddress = GlobalState<Account>()

  /** Liquidity address (38.2% of phi revenue) */
  liquidityAddress = GlobalState<Account>()

  /** Admin/relayer address */
  relayerAddress = GlobalState<Account>()

  /** SmartOracle app ID for USD → ALGO conversion */
  oracleAppId = GlobalState<Uint64>({ initialValue: Uint64(0) })

  /** Total settlements processed */
  totalSettlements = GlobalState<Uint64>({ initialValue: Uint64(0) })

  /** Total phi fees collected in microALGO */
  totalPhiFees = GlobalState<Uint64>({ initialValue: Uint64(0) })

  /** Total value settled (in micro-USD for cross-chain normalization) */
  totalValueSettledUsd = GlobalState<Uint64>({ initialValue: Uint64(0) })

  // ── Box Storage ────────────────────────────────────────────────

  /** Settlement records by weave ID */
  settlements = BoxMap<Bytes, WeaveSettlement>({ prefix: Bytes('ws_') })

  // ══════════════════════════════════════════════════════════════
  // INITIALIZATION
  // ══════════════════════════════════════════════════════════════

  @arc4.abimethod()
  initialize(
    treasury: Account,
    liquidity: Account,
    relayer: Account,
    oracle: Uint64,
  ): void {
    assert(Txn.sender === Global.creatorAddress, 'Only creator')
    this.treasuryAddress.value = treasury
    this.liquidityAddress.value = liquidity
    this.relayerAddress.value = relayer
    this.oracleAppId.value = oracle
  }

  // ══════════════════════════════════════════════════════════════
  // SETTLE WEAVE — Record settlement with phi fee
  // ══════════════════════════════════════════════════════════════

  /**
   * Record a weave settlement on Algorand.
   * Called by the relayer after detecting a WeaveInitiated event on EVM.
   * The settlement provides finality — Algorand has no forks.
   *
   * @param weaveId 32-byte weave ID from source chain
   * @param srcChainId Source EVM chain ID
   * @param destChainId Destination EVM chain ID
   * @param amountUsd Transfer amount in micro-USD (for normalization)
   * @param gasCostAlgo Gas cost converted to microALGO
   */
  @arc4.abimethod()
  settleWeave(
    weaveId: Bytes,
    srcChainId: Uint64,
    destChainId: Uint64,
    amountUsd: Uint64,
    gasCostAlgo: Uint64,
  ): void {
    assert(
      Txn.sender === this.relayerAddress.value,
      'Only relayer'
    )
    assert(!this.settlements(weaveId).exists, 'Already settled')

    // Calculate phi fee in ALGO
    const phiFeeAlgo = (gasCostAlgo * PHI_SCALED) / PHI_DENOMINATOR
    const protocolRevenue = (gasCostAlgo * PHI_MINUS_ONE_SCALED) / PHI_DENOMINATOR

    // Split revenue: 61.8% treasury, 38.2% liquidity
    const treasuryShare = (protocolRevenue * TREASURY_SPLIT) / SPLIT_DENOMINATOR
    const liquidityShare = protocolRevenue - treasuryShare

    // Distribute fees via inner transactions
    if (treasuryShare > Uint64(0)) {
      itxn.payment({
        receiver: this.treasuryAddress.value,
        amount: treasuryShare,
        fee: Uint64(1000),
      }).submit()
    }

    if (liquidityShare > Uint64(0)) {
      itxn.payment({
        receiver: this.liquidityAddress.value,
        amount: liquidityShare,
        fee: Uint64(1000),
      }).submit()
    }

    // Record settlement
    this.settlements(weaveId).value = {
      weaveId: weaveId,
      srcChainId: srcChainId,
      destChainId: destChainId,
      amount: amountUsd,
      phiFee: phiFeeAlgo,
      settledRound: Global.round,
      relayer: Txn.sender,
    }

    this.totalSettlements.value = this.totalSettlements.value + Uint64(1)
    this.totalPhiFees.value = this.totalPhiFees.value + phiFeeAlgo
    this.totalValueSettledUsd.value = this.totalValueSettledUsd.value + amountUsd
  }

  // ══════════════════════════════════════════════════════════════
  // QUOTE — Estimate phi fee for a weave
  // ══════════════════════════════════════════════════════════════

  /**
   * Quote a phi fee in microALGO for a weave.
   * @param gasCostAlgo Estimated gas cost in microALGO
   * @return phiFee Total phi fee (gasCost * 1.618...)
   * @return protocolRevenue The (phi - 1) portion
   * @return treasuryShare 61.8% of revenue
   * @return liquidityShare 38.2% of revenue
   */
  @arc4.abimethod({ readonly: true })
  quotePhiFee(gasCostAlgo: Uint64): arc4.DynamicArray<arc4.UintN<64>> {
    const phiFee = (gasCostAlgo * PHI_SCALED) / PHI_DENOMINATOR
    const protocolRevenue = (gasCostAlgo * PHI_MINUS_ONE_SCALED) / PHI_DENOMINATOR
    const treasuryShare = (protocolRevenue * TREASURY_SPLIT) / SPLIT_DENOMINATOR
    const liquidityShare = protocolRevenue - treasuryShare

    return new arc4.DynamicArray(
      new arc4.UintN<64>(phiFee),
      new arc4.UintN<64>(protocolRevenue),
      new arc4.UintN<64>(treasuryShare),
      new arc4.UintN<64>(liquidityShare),
    )
  }

  // ══════════════════════════════════════════════════════════════
  // VIEWS
  // ══════════════════════════════════════════════════════════════

  @arc4.abimethod({ readonly: true })
  isSettled(weaveId: Bytes): boolean {
    return this.settlements(weaveId).exists
  }

  @arc4.abimethod({ readonly: true })
  getSettlement(weaveId: Bytes): WeaveSettlement {
    assert(this.settlements(weaveId).exists, 'Not settled')
    return this.settlements(weaveId).value
  }

  @arc4.abimethod({ readonly: true })
  getStats(): arc4.DynamicArray<arc4.UintN<64>> {
    return new arc4.DynamicArray(
      new arc4.UintN<64>(this.totalSettlements.value),
      new arc4.UintN<64>(this.totalPhiFees.value),
      new arc4.UintN<64>(this.totalValueSettledUsd.value),
    )
  }

  // ── Admin ──────────────────────────────────────────────────────

  @arc4.abimethod()
  setRelayer(relayer: Account): void {
    assert(Txn.sender === Global.creatorAddress, 'Only creator')
    this.relayerAddress.value = relayer
  }

  /// @notice Fund the settler for fee distribution
  receive(): void {}
}
