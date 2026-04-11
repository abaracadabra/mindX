/**
 * aLUV Bridge — EVM ↔ Algorand Lock-and-Mint Bridge Receiver
 *
 * Bridge mechanism:
 *   EVM → Algorand: User locks LUV in ShambaLuvBridge.sol
 *                    Relayer calls bridgeMint() on this contract
 *                    This contract calls aLuvToken.bridgeMint(to, amount)
 *
 *   Algorand → EVM: User calls bridgeBurn() on this contract
 *                    This contract calls aLuvToken.bridgeBurn(from, amount)
 *                    Relayer detects event → calls bridgeUnlock() on EVM
 *
 * Relayer: SmartOracle command channel (Algorand 1000-byte note)
 *          carries bridge proofs between chains.
 *
 * Rate limiting: xERC20-style minting limits per epoch (24h window).
 * Bridge transfers are fee-exempt on aLUV (no double taxation).
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

// 24 hours in Algorand rounds (~26,182 rounds/day)
const EPOCH_ROUNDS = Uint64(26_182)

// ── Bridge Record (per-transaction proof) ────────────────────────

type BridgeRecord = {
  /** EVM transaction hash (32 bytes) */
  evmTxHash: Bytes
  /** Algorand account that received/sent aLUV */
  algoAccount: Account
  /** Amount bridged */
  amount: Uint64
  /** Direction: true = EVM→Algo (mint), false = Algo→EVM (burn) */
  isMint: boolean
  /** Round when bridge tx was processed */
  processedRound: Uint64
}

// ══════════════════════════════════════════════════════════════════
// aLUV BRIDGE CONTRACT
// ══════════════════════════════════════════════════════════════════

export class ALuvBridge extends Contract {
  // ── Global State ───────────────────────────────────────────────

  /** aLUV token app ID */
  aluvAppId = GlobalState<Uint64>()

  /** Authorized relayer address (SmartOracle or admin) */
  relayerAddress = GlobalState<Account>()

  /** Admin address */
  adminAddress = GlobalState<Account>()

  /** Minting limit per epoch (rate limiting) */
  mintLimitPerEpoch = GlobalState<Uint64>({ initialValue: Uint64(1_000_000_000_000) }) // 1T per epoch

  /** Current epoch start round */
  epochStart = GlobalState<Uint64>({ initialValue: Uint64(0) })

  /** Amount minted in current epoch */
  epochMinted = GlobalState<Uint64>({ initialValue: Uint64(0) })

  /** Total minted (all time) */
  totalMinted = GlobalState<Uint64>({ initialValue: Uint64(0) })

  /** Total burned (all time) */
  totalBurned = GlobalState<Uint64>({ initialValue: Uint64(0) })

  /** Bridge nonce (prevents replay) */
  nonce = GlobalState<Uint64>({ initialValue: Uint64(0) })

  // ── Box Storage ────────────────────────────────────────────────

  /** Processed EVM tx hashes (prevents double-processing) */
  processedTxs = BoxMap<Bytes, boolean>({ prefix: Bytes('pt_') })

  /** Bridge history by nonce */
  bridgeHistory = BoxMap<Uint64, BridgeRecord>({ prefix: Bytes('bh_') })

  // ══════════════════════════════════════════════════════════════
  // INITIALIZATION
  // ══════════════════════════════════════════════════════════════

  @arc4.abimethod()
  initialize(
    aluvApp: Uint64,
    relayer: Account,
    admin: Account,
  ): void {
    assert(Txn.sender === Global.creatorAddress, 'Only creator')
    this.aluvAppId.value = aluvApp
    this.relayerAddress.value = relayer
    this.adminAddress.value = admin
    this.epochStart.value = Global.round
  }

  // ══════════════════════════════════════════════════════════════
  // BRIDGE MINT (EVM → Algorand)
  // ══════════════════════════════════════════════════════════════

  /**
   * Mint aLUV when LUV is locked on EVM.
   * Only callable by authorized relayer.
   *
   * @param to         Algorand address to receive aLUV
   * @param amount     Amount of aLUV to mint (matches locked LUV)
   * @param evmTxHash  EVM lock transaction hash (32 bytes, for replay prevention)
   */
  @arc4.abimethod()
  bridgeMint(
    to: Account,
    amount: Uint64,
    evmTxHash: Bytes,
  ): Uint64 {
    assert(
      Txn.sender === this.relayerAddress.value ||
      Txn.sender === this.adminAddress.value,
      'Only relayer or admin'
    )
    assert(amount > Uint64(0), 'Zero amount')

    // Prevent replay — each EVM tx hash processed only once
    assert(!this.processedTxs(evmTxHash).exists, 'Already processed')
    this.processedTxs(evmTxHash).value = true

    // Rate limiting — check epoch
    this._checkEpochLimit(amount)

    // Call aLUV token to mint
    itxn.applicationCall({
      applicationId: this.aluvAppId.value,
      appArgs: [Bytes('bridgeMint'), to.bytes, arc4.encode(amount)],
      fee: Uint64(2000),
    }).submit()

    // Record bridge transaction
    const currentNonce = this.nonce.value
    this.bridgeHistory(currentNonce).value = {
      evmTxHash: evmTxHash,
      algoAccount: to,
      amount: amount,
      isMint: true,
      processedRound: Global.round,
    }

    this.nonce.value = currentNonce + Uint64(1)
    this.totalMinted.value = this.totalMinted.value + amount

    return currentNonce
  }

  // ══════════════════════════════════════════════════════════════
  // BRIDGE BURN (Algorand → EVM)
  // ══════════════════════════════════════════════════════════════

  /**
   * Burn aLUV to unlock LUV on EVM.
   * Callable by any aLUV holder.
   * Relayer detects this event → calls bridgeUnlock() on EVM.
   *
   * @param amount        Amount of aLUV to burn
   * @param evmRecipient  EVM address to receive unlocked LUV (20 bytes)
   */
  @arc4.abimethod()
  bridgeBurn(
    amount: Uint64,
    evmRecipient: Bytes,
  ): Uint64 {
    assert(amount > Uint64(0), 'Zero amount')

    // Call aLUV token to burn from sender
    itxn.applicationCall({
      applicationId: this.aluvAppId.value,
      appArgs: [Bytes('bridgeBurn'), Txn.sender.bytes, arc4.encode(amount)],
      fee: Uint64(2000),
    }).submit()

    // Record bridge transaction
    const currentNonce = this.nonce.value
    this.bridgeHistory(currentNonce).value = {
      evmTxHash: evmRecipient, // repurposed: stores EVM destination
      algoAccount: Txn.sender,
      amount: amount,
      isMint: false,
      processedRound: Global.round,
    }

    this.nonce.value = currentNonce + Uint64(1)
    this.totalBurned.value = this.totalBurned.value + amount

    // Relayer watches for this event and calls EVM bridgeUnlock()
    // The burn nonce + evmRecipient + amount constitute the bridge proof

    return currentNonce
  }

  // ══════════════════════════════════════════════════════════════
  // RATE LIMITING
  // ══════════════════════════════════════════════════════════════

  private _checkEpochLimit(amount: Uint64): void {
    // Reset epoch if expired
    if (Global.round >= this.epochStart.value + EPOCH_ROUNDS) {
      this.epochStart.value = Global.round
      this.epochMinted.value = Uint64(0)
    }

    // Check limit
    assert(
      this.epochMinted.value + amount <= this.mintLimitPerEpoch.value,
      'Epoch mint limit exceeded'
    )

    this.epochMinted.value = this.epochMinted.value + amount
  }

  // ══════════════════════════════════════════════════════════════
  // READ-ONLY VIEWS
  // ══════════════════════════════════════════════════════════════

  @arc4.abimethod({ readonly: true })
  getBridgeStats(): arc4.DynamicArray<arc4.UintN<64>> {
    return new arc4.DynamicArray(
      new arc4.UintN<64>(this.totalMinted.value),
      new arc4.UintN<64>(this.totalBurned.value),
      new arc4.UintN<64>(this.nonce.value),
      new arc4.UintN<64>(this.epochMinted.value),
      new arc4.UintN<64>(this.mintLimitPerEpoch.value),
    )
  }

  @arc4.abimethod({ readonly: true })
  getRemainingEpochMint(): Uint64 {
    if (Global.round >= this.epochStart.value + EPOCH_ROUNDS) {
      return this.mintLimitPerEpoch.value // epoch expired, full limit available
    }
    return this.mintLimitPerEpoch.value - this.epochMinted.value
  }

  @arc4.abimethod({ readonly: true })
  isProcessed(evmTxHash: Bytes): boolean {
    return this.processedTxs(evmTxHash).exists
  }

  // ── Admin ──────────────────────────────────────────────────────

  @arc4.abimethod()
  setRelayer(relayer: Account): void {
    assert(Txn.sender === this.adminAddress.value, 'Only admin')
    this.relayerAddress.value = relayer
  }

  @arc4.abimethod()
  setMintLimit(limit: Uint64): void {
    assert(Txn.sender === this.adminAddress.value, 'Only admin')
    this.mintLimitPerEpoch.value = limit
  }
}
