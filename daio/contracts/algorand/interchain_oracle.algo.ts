/**
 * Interchain Oracle — Multi-Chain Gas Price Reader
 *
 * Reads gas prices for EVM chains via SmartOracle command channel updates.
 * Provides phi fee quotes in microALGO for the InterchainSettler.
 *
 * Gas data is written by the SmartOracle relayer via command channel
 * (Algorand 1000-byte transaction notes). Each update contains
 * chain ID, base fee, priority fee, gas limit, and native USD price.
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
  assert,
  Bytes,
  Uint64,
  arc4,
} from '@algorandfoundation/algorand-typescript'

const PHI_SCALED = Uint64(1_618_034)
const PHI_DENOMINATOR = Uint64(1_000_000)
const ROUNDS_PER_HOUR = Uint64(1091) // ~3.3s per round, ~1091 rounds/hour

// ── Chain Gas Data ───────────────────────────────────────────────

type ChainGasData = {
  baseFeeGwei: Uint64        // base fee in gwei
  priorityFeeGwei: Uint64    // priority fee in gwei
  gasLimit: Uint64           // typical gas limit
  nativeUsdMicro: Uint64     // native token price in micro-USD (1e6)
  updatedRound: Uint64       // Algorand round when last updated
}

// ══════════════════════════════════════════════════════════════════
// INTERCHAIN ORACLE
// ══════════════════════════════════════════════════════════════════

export class InterchainOracle extends Contract {
  // ── Global State ───────────────────────────────────────────────

  /** Admin / SmartOracle relayer */
  oracleAddress = GlobalState<Account>()

  /** Maximum staleness in rounds before data is considered stale */
  maxStaleRounds = GlobalState<Uint64>({ initialValue: ROUNDS_PER_HOUR })

  /** ALGO/USD price in micro-USD (e.g., 200000 = $0.20) */
  algoUsdMicro = GlobalState<Uint64>({ initialValue: Uint64(200_000) })

  /** Number of chains tracked */
  chainCount = GlobalState<Uint64>({ initialValue: Uint64(0) })

  // ── Box Storage ────────────────────────────────────────────────

  /** Per-chain gas data */
  chainGas = BoxMap<Uint64, ChainGasData>({ prefix: Bytes('cg_') })

  // ══════════════════════════════════════════════════════════════
  // INITIALIZATION
  // ══════════════════════════════════════════════════════════════

  @arc4.abimethod()
  initialize(oracle: Account): void {
    assert(Txn.sender === Global.creatorAddress, 'Only creator')
    this.oracleAddress.value = oracle
  }

  // ══════════════════════════════════════════════════════════════
  // UPDATE GAS DATA
  // ══════════════════════════════════════════════════════════════

  /**
   * Update gas price data for a chain.
   * Called by SmartOracle relayer.
   */
  @arc4.abimethod()
  updateGasPrice(
    chainId: Uint64,
    baseFeeGwei: Uint64,
    priorityFeeGwei: Uint64,
    gasLimit: Uint64,
    nativeUsdMicro: Uint64,
  ): void {
    assert(
      Txn.sender === this.oracleAddress.value ||
      Txn.sender === Global.creatorAddress,
      'Only oracle or creator'
    )

    const isNew = !this.chainGas(chainId).exists

    this.chainGas(chainId).value = {
      baseFeeGwei,
      priorityFeeGwei,
      gasLimit,
      nativeUsdMicro,
      updatedRound: Global.round,
    }

    if (isNew) {
      this.chainCount.value = this.chainCount.value + Uint64(1)
    }
  }

  /**
   * Update ALGO/USD price (from Vestige DEX or SmartOracle)
   */
  @arc4.abimethod()
  updateAlgoPrice(algoUsdMicro: Uint64): void {
    assert(
      Txn.sender === this.oracleAddress.value ||
      Txn.sender === Global.creatorAddress,
      'Only oracle'
    )
    this.algoUsdMicro.value = algoUsdMicro
  }

  // ══════════════════════════════════════════════════════════════
  // READ GAS DATA
  // ══════════════════════════════════════════════════════════════

  /**
   * Get gas cost in micro-USD for a chain
   */
  @arc4.abimethod({ readonly: true })
  getGasCostUsd(chainId: Uint64): Uint64 {
    assert(this.chainGas(chainId).exists, 'Chain not tracked')
    const gas = this.chainGas(chainId).value

    // gasCost = (baseFee + priorityFee) * gasLimit * nativeUsd
    // All in gwei → need to convert to full units
    // costNative = (baseFeeGwei + priorityFeeGwei) * gasLimit / 1e9 (gwei→native)
    // costUsd = costNative * nativeUsdMicro / 1e6
    // Simplified: costUsdMicro = (fees * gasLimit * nativeUsdMicro) / 1e15

    const totalFeeGwei = gas.baseFeeGwei + gas.priorityFeeGwei
    const costMicro = (totalFeeGwei * gas.gasLimit * gas.nativeUsdMicro) / Uint64(1_000_000_000_000_000)
    return costMicro
  }

  /**
   * Get phi fee in micro-USD for a chain
   */
  @arc4.abimethod({ readonly: true })
  getPhiFeeUsd(chainId: Uint64): Uint64 {
    const gasCostUsd = this.getGasCostUsd(chainId)
    return (gasCostUsd * PHI_SCALED) / PHI_DENOMINATOR
  }

  /**
   * Get phi fee in microALGO for a chain
   */
  @arc4.abimethod({ readonly: true })
  getPhiFeeAlgo(chainId: Uint64): Uint64 {
    const phiFeeUsd = this.getPhiFeeUsd(chainId)
    // Convert micro-USD to microALGO: phiFeeUsd / algoUsdMicro * 1e6
    return (phiFeeUsd * Uint64(1_000_000)) / this.algoUsdMicro.value
  }

  /**
   * Check if gas data is fresh (within staleness window)
   */
  @arc4.abimethod({ readonly: true })
  isFresh(chainId: Uint64): boolean {
    if (!this.chainGas(chainId).exists) return false
    const gas = this.chainGas(chainId).value
    return Global.round - gas.updatedRound <= this.maxStaleRounds.value
  }

  // ── Admin ──────────────────────────────────────────────────────

  @arc4.abimethod()
  setOracle(oracle: Account): void {
    assert(Txn.sender === Global.creatorAddress, 'Only creator')
    this.oracleAddress.value = oracle
  }

  @arc4.abimethod()
  setMaxStaleRounds(rounds: Uint64): void {
    assert(Txn.sender === Global.creatorAddress, 'Only creator')
    this.maxStaleRounds.value = rounds
  }
}
