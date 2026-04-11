/**
 * aORC Registry — Verification Registry Contract
 *
 * On-chain registry of verified blockchains. Platform reads this to
 * display verified chain lists. Consensus-based — multiple verifiers
 * build confidence in a chain's active status.
 *
 * Separated from the minter: this contract handles ONLY chain listing
 * and verification. No NFT minting.
 *
 * Economics:
 *   - List a chain:   1 ALGO → treasury
 *   - Verify a chain: 1 ALGO → treasury + attestation log
 *   - Read:           free (box reads)
 *
 * On verify:
 *   1. Box state updated: verifyCount++, lastVerifier, timestamp
 *   2. Attestation log emitted (proof-of-active-blockchain)
 *   3. Platform indexes logs to build verified chain display
 *
 * (c) 2026 BANKON / AgenticPlace — GPL-3.0
 */

import {
  Contract,
  GlobalState,
  BoxMap,
  Txn,
  Global,
  assert,
  Bytes,
  op,
  itxn,
  log,
  gtxn,
  type uint64,
  type bytes,
  type Account,
} from '@algorandfoundation/algorand-typescript'

// Box layout (fixed header + variable JSON):
// [0..7]     chainId            uint64
// [8..39]    lister             32-byte address
// [40..47]   listedRound        uint64
// [48..55]   verifyCount        uint64
// [56..63]   lastVerifiedRound  uint64
// [64..95]   lastVerifier       32-byte address
// [96..103]  lastVerifiedTs     uint64
// [104..]    connectionData     variable JSON
const HDR = 104

export class AgenticRegistry extends Contract {

  /** Total chains in registry */
  totalChains = GlobalState<uint64>({ initialValue: 0 })

  /** Total verification attestations */
  totalVerifications = GlobalState<uint64>({ initialValue: 0 })

  /** AgenticPlace treasury admin */
  treasury = GlobalState<Account>()

  /** Chain boxes: chainId → header + connection JSON */
  chains = BoxMap<uint64, bytes>({ keyPrefix: 'c' })

  // ── Deploy ──

  createApplication(): void {
    this.treasury.value = Txn.sender
  }

  // ── List: 1 ALGO per chain ──

  /**
   * Register a blockchain in the on-chain registry.
   * Costs 1 ALGO. Payment stays in contract treasury.
   *
   * connectionData: compact JSON with RPCs, explorer, native currency.
   * Max 800 bytes. Example:
   * {"name":"Ethereum","sym":"ETH","rpc":["https://..."],"exp":"https://etherscan.io","cur":{"s":"ETH","d":18}}
   */
  listChain(payment: gtxn.PaymentTxn, chainId: uint64, connectionData: bytes): void {
    assert(payment.receiver === Global.currentApplicationAddress, 'Pay the contract')
    assert(payment.amount >= 1_000_000, 'Listing costs 1 ALGO')
    assert(connectionData.length > 0 && connectionData.length <= 800, 'Data: 1-800 bytes')

    const zeroAddr = op.bzero(32)
    const header = op.itob(chainId)
      .concat(Txn.sender.bytes)
      .concat(op.itob(Global.round))
      .concat(op.itob(0))                   // verifyCount
      .concat(op.itob(0))                   // lastVerifiedRound
      .concat(zeroAddr)                     // lastVerifier (zero)
      .concat(op.itob(Global.latestTimestamp))

    if (this.chains(chainId).exists) {
      const existing = this.chains(chainId).value
      const lister = existing.slice(8, 40)
      assert(
        Txn.sender.bytes === lister || Txn.sender === this.treasury.value,
        'Only original lister or treasury can update'
      )
      this.chains(chainId).value = header.concat(connectionData)
    } else {
      this.chains(chainId).value = header.concat(connectionData)
      this.totalChains.value = this.totalChains.value + 1
    }

    log(Bytes('list:').concat(op.itob(chainId)))
  }

  // ── Verify: 1 ALGO → attestation log + box update ──

  /**
   * Verify a chain is active. Costs 1 ALGO.
   *
   * 1. Box state updated: verifyCount++, lastVerifier, timestamp, round
   * 2. Attestation log emitted with chain data for platform indexing
   * 3. Self-payment attestation txn as proof-of-active-blockchain
   *
   * Platform reads box state and indexes attestation logs to display
   * the verified chain list with consensus counts.
   */
  verifyChain(payment: gtxn.PaymentTxn, chainId: uint64): void {
    assert(payment.receiver === Global.currentApplicationAddress, 'Pay the contract')
    assert(payment.amount >= 1_000_000, 'Verification costs 1 ALGO')
    assert(this.chains(chainId).exists, 'Chain not listed')

    const box = this.chains(chainId).value
    const connectionData = box.slice(HDR, box.length)

    // Update verification stats in box
    const updated = box.slice(0, 40)                       // chainId + lister
      .concat(box.slice(40, 48))                            // listedRound
      .concat(op.itob(op.btoi(box.slice(48, 56)) + 1))     // verifyCount++
      .concat(op.itob(Global.round))                        // lastVerifiedRound
      .concat(Txn.sender.bytes)                              // lastVerifier
      .concat(op.itob(Global.latestTimestamp))               // timestamp
      .concat(connectionData)

    this.chains(chainId).value = updated
    this.totalVerifications.value = this.totalVerifications.value + 1

    // Attestation transaction: proof-of-active-blockchain
    // The note carries connection data — indexed by AgenticPlace platform
    itxn.payment({
      receiver: Global.currentApplicationAddress,
      amount: 0,
      fee: 1_000,
      note: Bytes('agenticORacle:verify:')
        .concat(op.itob(chainId))
        .concat(Bytes(':data:'))
        .concat(connectionData)
        .concat(Bytes(':by:'))
        .concat(Txn.sender.bytes)
        .concat(Bytes(':ts:'))
        .concat(op.itob(Global.latestTimestamp))
        .concat(Bytes(':round:'))
        .concat(op.itob(Global.round)),
    }).submit()

    log(
      Bytes('verify:')
        .concat(op.itob(chainId))
        .concat(Bytes(':count:'))
        .concat(op.itob(this.totalVerifications.value))
        .concat(Bytes(':by:'))
        .concat(Txn.sender.bytes)
    )
  }

  // ── Read (free) ──

  readChain(chainId: uint64): bytes {
    assert(this.chains(chainId).exists, 'Not listed')
    return this.chains(chainId).value
  }

  isListed(chainId: uint64): boolean {
    return this.chains(chainId).exists
  }

  getVerifyCount(chainId: uint64): uint64 {
    assert(this.chains(chainId).exists, 'Not listed')
    return op.btoi(this.chains(chainId).value.slice(48, 56))
  }

  getLastVerifiedRound(chainId: uint64): uint64 {
    assert(this.chains(chainId).exists, 'Not listed')
    return op.btoi(this.chains(chainId).value.slice(56, 64))
  }

  // ── Batch ──

  /**
   * List two chains in one call. Requires 2 ALGO payment.
   */
  batchList(
    payment: gtxn.PaymentTxn,
    chainId1: uint64, data1: bytes,
    chainId2: uint64, data2: bytes,
  ): void {
    assert(payment.receiver === Global.currentApplicationAddress, 'Pay the contract')
    assert(payment.amount >= 2_000_000, '2 ALGO for 2 chains')
    assert(data1.length > 0 && data1.length <= 800, 'Data1 size')
    assert(data2.length > 0 && data2.length <= 800, 'Data2 size')

    const zeroAddr = op.bzero(32)
    const header1 = op.itob(chainId1).concat(Txn.sender.bytes).concat(op.itob(Global.round))
      .concat(op.itob(0)).concat(op.itob(0)).concat(zeroAddr).concat(op.itob(Global.latestTimestamp))
    const header2 = op.itob(chainId2).concat(Txn.sender.bytes).concat(op.itob(Global.round))
      .concat(op.itob(0)).concat(op.itob(0)).concat(zeroAddr).concat(op.itob(Global.latestTimestamp))

    if (!this.chains(chainId1).exists) this.totalChains.value = this.totalChains.value + 1
    if (!this.chains(chainId2).exists) this.totalChains.value = this.totalChains.value + 1

    this.chains(chainId1).value = header1.concat(data1)
    this.chains(chainId2).value = header2.concat(data2)

    log(Bytes('batch:').concat(op.itob(chainId1)).concat(Bytes(',')).concat(op.itob(chainId2)))
  }

  // ── Treasury ──

  /**
   * Withdraw from treasury. Only AgenticPlace admin.
   */
  withdraw(amount: uint64, to: Account): void {
    assert(Txn.sender === this.treasury.value, 'Treasury only')
    const available: uint64 = Global.currentApplicationAddress.balance - Global.currentApplicationAddress.minBalance
    assert(amount <= available, 'Exceeds available')
    itxn.payment({ receiver: to, amount: amount, fee: 1_000 }).submit()
  }

  /**
   * Transfer treasury role.
   */
  transferTreasury(newTreasury: Account): void {
    assert(Txn.sender === this.treasury.value, 'Treasury only')
    this.treasury.value = newTreasury
  }
}
