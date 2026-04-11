/**
 * aORC Minter — NFT Minting Contract
 *
 * Pure minting contract. The minter holds their NFT.
 * Separated from the verification registry for clear responsibility.
 *
 * Mint types:
 *   - Chain NFT:  aORC NFT containing blockchain connection data
 *   - Agent NFT:  aORC NFT verifying an ERC-8004 agent identity
 *   - Custom NFT: aORC NFT with arbitrary data payload
 *
 * Pattern: sender-mints. The user creates their own ASA in the atomic
 * group (they are the creator, auto-hold). The contract validates the
 * payment and emits an attestation log for platform indexing.
 *
 * Economics:
 *   - Mint fee: 1_000 microALGO (0.001 ALGO) per mint
 *   - Treasury: fees stay in contract
 *
 * (c) 2026 BANKON / AgenticPlace — GPL-3.0
 */

import {
  Contract,
  GlobalState,
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

export class AgenticMinter extends Contract {

  /** Total NFTs minted through this contract */
  totalMinted = GlobalState<uint64>({ initialValue: 0 })

  /** AgenticPlace treasury admin */
  treasury = GlobalState<Account>()

  // ── Deploy ──

  createApplication(): void {
    this.treasury.value = Txn.sender
  }

  // ── Mint Chain NFT ──

  /**
   * Record a chain NFT mint. The user creates the ASA themselves in the
   * same atomic group — this call validates payment and logs the event.
   *
   * @param payment   - Payment of at least 0.001 ALGO to the contract
   * @param chainId   - Numeric chain ID (e.g. 1 = Ethereum)
   * @param chainName - Human-readable chain name (ASCII bytes, for log)
   */
  mintChainNFT(payment: gtxn.PaymentTxn, chainId: uint64, chainName: bytes): void {
    assert(payment.receiver === Global.currentApplicationAddress, 'Pay the contract')
    assert(payment.amount >= 1_000, 'Mint costs 0.001 ALGO')
    assert(chainName.length > 0 && chainName.length <= 64, 'Name: 1-64 bytes')

    this.totalMinted.value = this.totalMinted.value + 1

    log(
      Bytes('mint:chain:')
        .concat(op.itob(chainId))
        .concat(Bytes(':by:'))
        .concat(Txn.sender.bytes)
        .concat(Bytes(':n:'))
        .concat(op.itob(this.totalMinted.value))
    )
  }

  // ── Mint Agent NFT ──

  /**
   * Record an agent NFT mint. User creates ASA in the group.
   *
   * @param payment   - Payment of at least 0.001 ALGO
   * @param agentId   - Agent token ID on source chain
   * @param agentData - Compact agent metadata (name, chain, owner) as bytes
   */
  mintAgentNFT(payment: gtxn.PaymentTxn, agentId: uint64, agentData: bytes): void {
    assert(payment.receiver === Global.currentApplicationAddress, 'Pay the contract')
    assert(payment.amount >= 1_000, 'Mint costs 0.001 ALGO')
    assert(agentData.length > 0 && agentData.length <= 800, 'Data: 1-800 bytes')

    this.totalMinted.value = this.totalMinted.value + 1

    log(
      Bytes('mint:agent:')
        .concat(op.itob(agentId))
        .concat(Bytes(':by:'))
        .concat(Txn.sender.bytes)
        .concat(Bytes(':n:'))
        .concat(op.itob(this.totalMinted.value))
    )
  }

  // ── Mint Custom NFT ──

  /**
   * Record a custom NFT mint. User creates ASA in the group.
   *
   * @param payment - Payment of at least 0.001 ALGO
   * @param data    - Custom JSON payload as bytes (max 800)
   */
  mintCustomNFT(payment: gtxn.PaymentTxn, data: bytes): void {
    assert(payment.receiver === Global.currentApplicationAddress, 'Pay the contract')
    assert(payment.amount >= 1_000, 'Mint costs 0.001 ALGO')
    assert(data.length > 0 && data.length <= 800, 'Data: 1-800 bytes')

    this.totalMinted.value = this.totalMinted.value + 1

    log(
      Bytes('mint:custom:by:')
        .concat(Txn.sender.bytes)
        .concat(Bytes(':n:'))
        .concat(op.itob(this.totalMinted.value))
    )
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
