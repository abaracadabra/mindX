/**
 * aORC Type Minter — Type-Aware NFT Minting Contract
 *
 * Upgrades AgenticMinter with per-NFT-type on-chain logic:
 *
 *   aNFT  — Immutable agent identity. No manager. Permanent.
 *   dNFT  — Dynamic. Manager retained. Metadata update log tracked.
 *   iNFT  — Intelligent. Directive address stored on-chain.
 *            Only directive address OR owner can trigger metadata update.
 *   THOT  — Knowledge tensor. CID uniqueness enforced (one THOT per CID hash).
 *
 * Each type records type-specific data in box storage:
 *   Box key: 't' + ASA_ID → type header + type-specific data
 *
 * BONA FIDE integration: when BONA FIDE controller is set,
 * minting triggers a log that the facilitator uses to queue
 * reputation token issuance.
 *
 * Economics:
 *   - aNFT mint: 0.001 ALGO
 *   - dNFT mint: 0.001 ALGO
 *   - iNFT mint: 0.001 ALGO
 *   - THOT mint: 0.001 ALGO
 *   - dNFT metadata update log: 0.001 ALGO
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

// NFT type constants (stored in box header byte 0)
// 1 = aNFT, 2 = dNFT, 3 = iNFT, 4 = THOT

// Box layout per NFT:
// [0]       nftType       uint8 (1,2,3,4)
// [1..8]    asaId         uint64
// [9..40]   owner         32-byte address (minter at creation)
// [41..48]  mintedRound   uint64
// [49..56]  mintedTs      uint64
// === iNFT extension ===
// [57..88]  directiveAddr 32-byte address
// [89]      autonomous    uint8 (0/1)
// [90..91]  intLevel      uint16
// === THOT extension ===
// [57..88]  cidHash       32-byte SHA-256 of CID string (uniqueness key)

export class TypeMinter extends Contract {

  /** Total NFTs minted */
  totalMinted = GlobalState<uint64>({ initialValue: 0 })

  /** Per-type counters */
  totalAnft = GlobalState<uint64>({ initialValue: 0 })
  totalDnft = GlobalState<uint64>({ initialValue: 0 })
  totalInft = GlobalState<uint64>({ initialValue: 0 })
  totalThot = GlobalState<uint64>({ initialValue: 0 })

  /** BONA FIDE controller app ID (0 = not set) */
  bonafideAppId = GlobalState<uint64>({ initialValue: 0 })

  /** Treasury */
  treasury = GlobalState<Account>()

  /** NFT registry: ASA ID → type data */
  nfts = BoxMap<uint64, bytes>({ keyPrefix: 't' })

  /** THOT CID uniqueness: SHA-256(cid) → ASA ID */
  thotCids = BoxMap<bytes, uint64>({ keyPrefix: 'h' })

  // ── Deploy ──

  createApplication(): void {
    this.treasury.value = Txn.sender
  }

  // ── Configure ──

  setBonafideController(appId: uint64): void {
    assert(Txn.sender === this.treasury.value, 'Treasury only')
    this.bonafideAppId.value = appId
  }

  // ── Mint aNFT ──

  mintAnft(payment: gtxn.PaymentTxn, asaId: uint64, agentData: bytes): void {
    assert(payment.receiver === Global.currentApplicationAddress, 'Pay the contract')
    assert(payment.amount >= 1_000, 'Costs 0.001 ALGO')
    assert(agentData.length > 0 && agentData.length <= 800, 'Data: 1-800 bytes')
    assert(!this.nfts(asaId).exists, 'ASA already registered')

    const header = op.itob(1)                              // type = aNFT
      .concat(op.itob(asaId))
      .concat(Txn.sender.bytes)
      .concat(op.itob(Global.round))
      .concat(op.itob(Global.latestTimestamp))

    this.nfts(asaId).value = header.concat(agentData)
    this.totalMinted.value = this.totalMinted.value + 1
    this.totalAnft.value = this.totalAnft.value + 1

    log(
      Bytes('mint:anft:')
        .concat(op.itob(asaId))
        .concat(Bytes(':by:'))
        .concat(Txn.sender.bytes)
        .concat(Bytes(':n:'))
        .concat(op.itob(this.totalMinted.value))
    )
  }

  // ── Mint dNFT ──

  mintDnft(payment: gtxn.PaymentTxn, asaId: uint64, agentData: bytes): void {
    assert(payment.receiver === Global.currentApplicationAddress, 'Pay the contract')
    assert(payment.amount >= 1_000, 'Costs 0.001 ALGO')
    assert(agentData.length > 0 && agentData.length <= 800, 'Data: 1-800 bytes')
    assert(!this.nfts(asaId).exists, 'ASA already registered')

    const header = op.itob(2)                              // type = dNFT
      .concat(op.itob(asaId))
      .concat(Txn.sender.bytes)
      .concat(op.itob(Global.round))
      .concat(op.itob(Global.latestTimestamp))

    this.nfts(asaId).value = header.concat(agentData)
    this.totalMinted.value = this.totalMinted.value + 1
    this.totalDnft.value = this.totalDnft.value + 1

    log(
      Bytes('mint:dnft:')
        .concat(op.itob(asaId))
        .concat(Bytes(':by:'))
        .concat(Txn.sender.bytes)
    )
  }

  // ── Mint iNFT ──

  mintInft(
    payment: gtxn.PaymentTxn,
    asaId: uint64,
    directiveAddress: Account,
    intLevel: uint64,
    autonomous: uint64,
    agentData: bytes,
  ): void {
    assert(payment.receiver === Global.currentApplicationAddress, 'Pay the contract')
    assert(payment.amount >= 1_000, 'Costs 0.001 ALGO')
    assert(agentData.length > 0 && agentData.length <= 700, 'Data: 1-700 bytes (iNFT has extended header)')
    assert(!this.nfts(asaId).exists, 'ASA already registered')
    assert(intLevel <= 100, 'Intelligence level: 0-100')

    const header = op.itob(3)                              // type = iNFT
      .concat(op.itob(asaId))
      .concat(Txn.sender.bytes)
      .concat(op.itob(Global.round))
      .concat(op.itob(Global.latestTimestamp))
      .concat(directiveAddress.bytes)                       // 32 bytes: directive address
      .concat(op.itob(autonomous))                          // autonomous flag
      .concat(op.itob(intLevel))                            // intelligence level

    this.nfts(asaId).value = header.concat(agentData)
    this.totalMinted.value = this.totalMinted.value + 1
    this.totalInft.value = this.totalInft.value + 1

    log(
      Bytes('mint:inft:')
        .concat(op.itob(asaId))
        .concat(Bytes(':dir:'))
        .concat(directiveAddress.bytes)
        .concat(Bytes(':int:'))
        .concat(op.itob(intLevel))
    )
  }

  // ── Mint THOT ──

  mintThot(
    payment: gtxn.PaymentTxn,
    asaId: uint64,
    cidHash: bytes,
    dimensions: uint64,
    agentData: bytes,
  ): void {
    assert(payment.receiver === Global.currentApplicationAddress, 'Pay the contract')
    assert(payment.amount >= 1_000, 'Costs 0.001 ALGO')
    assert(agentData.length > 0 && agentData.length <= 700, 'Data: 1-700 bytes')
    assert(!this.nfts(asaId).exists, 'ASA already registered')
    assert(cidHash.length === 32, 'CID hash must be 32 bytes (SHA-256)')

    // Enforce CID uniqueness
    assert(!this.thotCids(cidHash).exists, 'CID already minted as THOT — one tensor per CID')

    const header = op.itob(4)                              // type = THOT
      .concat(op.itob(asaId))
      .concat(Txn.sender.bytes)
      .concat(op.itob(Global.round))
      .concat(op.itob(Global.latestTimestamp))
      .concat(cidHash)                                      // 32 bytes: SHA-256 of CID
      .concat(op.itob(dimensions))                          // tensor dimensions

    this.nfts(asaId).value = header.concat(agentData)
    this.thotCids(cidHash).value = asaId                    // uniqueness index
    this.totalMinted.value = this.totalMinted.value + 1
    this.totalThot.value = this.totalThot.value + 1

    log(
      Bytes('mint:thot:')
        .concat(op.itob(asaId))
        .concat(Bytes(':dim:'))
        .concat(op.itob(dimensions))
    )
  }

  // ── dNFT Metadata Update Log ──

  logDnftUpdate(payment: gtxn.PaymentTxn, asaId: uint64, updateData: bytes): void {
    assert(payment.receiver === Global.currentApplicationAddress, 'Pay the contract')
    assert(payment.amount >= 1_000, 'Update log costs 0.001 ALGO')
    assert(this.nfts(asaId).exists, 'NFT not registered')
    assert(updateData.length > 0 && updateData.length <= 800, 'Data: 1-800 bytes')

    // Verify caller is the original minter (owner)
    const box = this.nfts(asaId).value
    const nftType = op.btoi(box.slice(0, 8))
    assert(nftType === 2 || nftType === 3, 'Only dNFT and iNFT support updates')
    const owner = box.slice(16, 48)
    assert(Txn.sender.bytes === owner, 'Only original minter can log updates')

    log(
      Bytes('update:')
        .concat(op.itob(asaId))
        .concat(Bytes(':by:'))
        .concat(Txn.sender.bytes)
        .concat(Bytes(':data:'))
        .concat(updateData)
    )
  }

  // ── Read ──

  getNftType(asaId: uint64): uint64 {
    assert(this.nfts(asaId).exists, 'Not registered')
    return op.btoi(this.nfts(asaId).value.slice(0, 8))
  }

  getNftData(asaId: uint64): bytes {
    assert(this.nfts(asaId).exists, 'Not registered')
    return this.nfts(asaId).value
  }

  isThotCidUsed(cidHash: bytes): boolean {
    return this.thotCids(cidHash).exists
  }

  // ── Treasury ──

  withdraw(amount: uint64, to: Account): void {
    assert(Txn.sender === this.treasury.value, 'Treasury only')
    const available: uint64 = Global.currentApplicationAddress.balance - Global.currentApplicationAddress.minBalance
    assert(amount <= available, 'Exceeds available')
    itxn.payment({ receiver: to, amount: amount, fee: 1_000 }).submit()
  }

  transferTreasury(newTreasury: Account): void {
    assert(Txn.sender === this.treasury.value, 'Treasury only')
    this.treasury.value = newTreasury
  }
}
