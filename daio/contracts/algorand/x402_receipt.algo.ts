/**
 * X402Receipt — canonical on-chain attestation for HTTP 402 settlements (AVM).
 *
 * Sister contract to `daio/contracts/x402/X402Receipt.sol` (EVM).
 * Same logical ABI surface (`recordX402Receipt`), same event/log field set,
 * idempotent on `receiptHash`, designed so a unified off-chain indexer
 * joins EVM + AVM receipts under one `(chainKind, chainId, receiptHash)`
 * triple.
 *
 * v1 single-sig path:
 *   - signature is a 64-byte Ed25519 sig over the canonical receipt struct
 *   - `op.ed25519verifyBare(canonical, signature, payer.bytes)` verifies
 *
 * v2 multisig path (deferred):
 *   - `payer` is a multisig descriptor account; the signature is the
 *     wire-merged multisig form. Verifying merged-multisig in-contract is
 *     non-trivial — the active draft ARC for [multisig signing
 *     coordination](https://forum.algorand.co/t/arc-allowing-coordination-of-multisig-signing/7840)
 *     defines the merge format we should target. Until that ARC lands,
 *     multisig payers settle off-chain (operator merges the signatures via
 *     `goal clerk multisig merge`) and the **merged-multisig signature is
 *     not directly verifiable on-chain by ed25519verifyBare alone**. v2 will
 *     decode the subsig array and verify K of N independently.
 *
 * Compiled by Puya compiler via PuyaTs.
 * (c) 2026 mindX — MIT (matches the EVM sibling).
 */

import { Contract } from '@algorandfoundation/algorand-typescript'
import {
  GlobalState,
  BoxMap,
  Account,
  Txn,
  Global,
  assert,
  op,
  log,
  Bytes,
  Uint64,
  arc4,
} from '@algorandfoundation/algorand-typescript'

// ──────────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────────

/** Persisted record (BoxMap value). Written once, read by anyone. */
type ReceiptRecord = {
  /** sha256(canonical) recomputed on-chain */
  receiptHash: Bytes
  /** keccak/sha-256 of the paid resource URL (32 bytes) */
  resourceHash: Bytes
  /** 32-byte payer public-key bytes */
  payer: Bytes
  /** 32-byte payee public-key bytes */
  payee: Bytes
  /** ASA ID */
  assetId: Uint64
  /** amount in asset base units */
  amount: Uint64
  /** Algorand round when recorded */
  recordedRound: Uint64
}

// ──────────────────────────────────────────────────────────────────────
// X402_RECEIPT
// ──────────────────────────────────────────────────────────────────────

export class X402Receipt extends Contract {
  /** Admin / attestor; used for any non-receipt admin ops. */
  admin = GlobalState<Account>()

  /** Total receipts recorded (cheap stat for /insight surfaces). */
  totalReceipts = GlobalState<Uint64>({ initialValue: Uint64(0) })

  /** Per-receipt record, keyed by sha256(canonical). */
  receipts = BoxMap<Bytes, ReceiptRecord>({ prefix: Bytes('xr_') })

  // ════════════════════════════════════════════════════════════════════
  // INIT
  // ════════════════════════════════════════════════════════════════════

  @arc4.abimethod()
  initialize(adminAddr: Account): void {
    assert(Txn.sender === Global.creatorAddress, 'Only creator')
    this.admin.value = adminAddr
  }

  // ════════════════════════════════════════════════════════════════════
  // CANONICAL HASH
  //
  // The off-chain composer constructs the canonical struct then hashes it
  // with sha256. This abimethod re-runs the hash on-chain so callers can
  // verify the wire payload matches their claimed receiptHash before
  // submitting a recordX402Receipt call.
  //
  // Layout (concatenated big-endian):
  //   "x402-receipt-v1" (16 bytes, ASCII, zero-padded right)
  //   uint64 chainTag    (1 = AVM)
  //   bytes32 payer
  //   bytes32 payee
  //   uint64 assetId
  //   uint64 amount
  //   bytes32 resourceHash
  //   bytes32 nonce
  // ════════════════════════════════════════════════════════════════════

  @arc4.abimethod({ readonly: true })
  canonicalReceiptHash(
    payerKey: Bytes,
    payeeKey: Bytes,
    assetId: Uint64,
    amount: Uint64,
    resourceHash: Bytes,
    nonce: Bytes,
  ): Bytes {
    const canonical = this._canonical(
      payerKey, payeeKey, assetId, amount, resourceHash, nonce,
    )
    return op.sha256(canonical)
  }

  /** Internal: build the canonical byte string. Big-endian uint64s via op.itob. */
  private _canonical(
    payerKey: Bytes,
    payeeKey: Bytes,
    assetId: Uint64,
    amount: Uint64,
    resourceHash: Bytes,
    nonce: Bytes,
  ): Bytes {
    const tag = Bytes('x402-receipt-v1\x00')   // 16 bytes ASCII, NUL-padded
    return tag
      .concat(op.itob(Uint64(1)))               // chainTag = 1 (AVM)
      .concat(payerKey)
      .concat(payeeKey)
      .concat(op.itob(assetId))
      .concat(op.itob(amount))
      .concat(resourceHash)
      .concat(nonce)
  }

  // ════════════════════════════════════════════════════════════════════
  // RECORD
  //
  // Submit a verified receipt. Idempotent on receiptHash. Logs an
  // arc4-encoded line equivalent to the EVM event so a unified indexer
  // pulls both chains' receipts under one schema.
  // ════════════════════════════════════════════════════════════════════

  @arc4.abimethod()
  recordX402Receipt(
    receiptHash: Bytes,
    payerKey: Bytes,
    payeeKey: Bytes,
    assetId: Uint64,
    amount: Uint64,
    resourceHash: Bytes,
    nonce: Bytes,
    signature: Bytes,
  ): void {
    // 1. Idempotency.
    assert(!this.receipts(receiptHash).exists, 'Receipt already recorded')

    // 2. Recompute canonical bytes + hash; confirm against caller-supplied receiptHash.
    const canonical = this._canonical(
      payerKey, payeeKey, assetId, amount, resourceHash, nonce,
    )
    assert(receiptHash === op.sha256(canonical), 'Receipt hash mismatch')

    // 3. Verify Ed25519 signature.
    //    v1: single-sig; the signature is a raw 64-byte Ed25519 sig over the
    //    canonical struct (op.ed25519verifyBare takes the message + sig + pk).
    //    v2: detect merged-multisig form (non-64-byte signature) and dispatch
    //    to a multisig verifier. Deferred per file header.
    assert(
      op.ed25519verifyBare(canonical, signature, payerKey),
      'Invalid Ed25519 signature',
    )

    // 4. Persist.
    this.receipts(receiptHash).value = {
      receiptHash: receiptHash,
      resourceHash: resourceHash,
      payer: payerKey,
      payee: payeeKey,
      assetId: assetId,
      amount: amount,
      recordedRound: Global.round,
    }
    this.totalReceipts.value = this.totalReceipts.value + Uint64(1)

    // 5. Log line for off-chain indexer (event-equivalent).
    //    Field order matches the EVM event's non-indexed args:
    //      tag, receiptHash, resourceHash, payer, payee, assetId, amount,
    //      chainKind=AVM(2), round
    log(
      Bytes('x402-receipt-v1:')
        .concat(receiptHash)
        .concat(resourceHash)
        .concat(payerKey)
        .concat(payeeKey)
        .concat(op.itob(assetId))
        .concat(op.itob(amount))
        .concat(op.itob(Uint64(2)))   // chainKind = 2 (AVM)
        .concat(op.itob(Global.round)),
    )
  }

  // ════════════════════════════════════════════════════════════════════
  // VIEWS
  // ════════════════════════════════════════════════════════════════════

  @arc4.abimethod({ readonly: true })
  isRecorded(receiptHash: Bytes): boolean {
    return this.receipts(receiptHash).exists
  }

  @arc4.abimethod({ readonly: true })
  getReceipt(receiptHash: Bytes): ReceiptRecord {
    assert(this.receipts(receiptHash).exists, 'Not recorded')
    return this.receipts(receiptHash).value
  }
}
