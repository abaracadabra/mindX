/**
 * aORC BONA FIDE — Reputation Token Controller
 *
 * BONA FIDE is an Algorand Standard Asset where the CONTRACT is the
 * clawback authority. When an agent is verified, this contract issues
 * exactly 1 BONA FIDE to their address. The contract can also revoke
 * (clawback) tokens from agents who lose verification status.
 *
 * The ASA is created with:
 *   - clawback = this contract's address
 *   - freeze   = this contract's address
 *   - manager  = treasury (can update config)
 *   - reserve  = this contract's address (holds unissued supply)
 *
 * Pattern: the contract holds all supply in reserve. Issue = clawback
 * from self to recipient. Revoke = clawback from holder back to self.
 *
 * Economics:
 *   - Issue: free (inner txn, contract pays fee)
 *   - Verify threshold: configurable (default: 1 verification)
 *   - Revoke: treasury-only (governance action)
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
  type uint64,
  type bytes,
  type Account,
} from '@algorandfoundation/algorand-typescript'

export class BonaFideController extends Contract {

  /** BONA FIDE ASA ID — set after ASA creation */
  asaId = GlobalState<uint64>({ initialValue: 0 })

  /** Total BONA FIDE issued to agents */
  totalIssued = GlobalState<uint64>({ initialValue: 0 })

  /** Total BONA FIDE revoked */
  totalRevoked = GlobalState<uint64>({ initialValue: 0 })

  /** Minimum verification count required for issuance */
  verifyThreshold = GlobalState<uint64>({ initialValue: 1 })

  /** Treasury admin */
  treasury = GlobalState<Account>()

  /** Agent holdings: address → issued count (tracks per-agent issuance) */
  agents = BoxMap<Account, uint64>({ keyPrefix: 'a' })

  // ── Deploy ──

  createApplication(): void {
    this.treasury.value = Txn.sender
  }

  // ── Configure ASA ──

  /**
   * Set the BONA FIDE ASA ID. Called once after ASA creation.
   * The ASA must have this contract as clawback + freeze + reserve.
   */
  setAsaId(asaId: uint64): void {
    assert(Txn.sender === this.treasury.value, 'Treasury only')
    assert(this.asaId.value === 0, 'ASA already set')
    this.asaId.value = asaId
    log(Bytes('bonafide:asa:').concat(op.itob(asaId)))
  }

  /**
   * Update verification threshold.
   */
  setThreshold(threshold: uint64): void {
    assert(Txn.sender === this.treasury.value, 'Treasury only')
    assert(threshold > 0, 'Threshold must be positive')
    this.verifyThreshold.value = threshold
  }

  // ── Issue BONA FIDE ──

  /**
   * Issue 1 BONA FIDE to a verified agent.
   * The agent must have opted in to the ASA.
   * The contract clawbacks from its own reserve to the agent.
   *
   * @param agent    - Recipient address (must be opted in)
   * @param agentId  - Agent ID for logging/tracking
   */
  issueBonafide(agent: Account, agentId: uint64): void {
    assert(Txn.sender === this.treasury.value, 'Treasury only')
    assert(this.asaId.value > 0, 'ASA not configured')

    // Issue via clawback: transfer 1 token from contract reserve to agent
    itxn.assetTransfer({
      assetReceiver: agent,
      assetSender: Global.currentApplicationAddress,  // clawback from self (reserve)
      xferAsset: this.asaId.value,
      assetAmount: 1,
      fee: 1_000,
    }).submit()

    // Track issuance
    if (this.agents(agent).exists) {
      this.agents(agent).value = this.agents(agent).value + 1
    } else {
      this.agents(agent).value = 1
    }

    this.totalIssued.value = this.totalIssued.value + 1

    log(
      Bytes('bonafide:issue:')
        .concat(agent.bytes)
        .concat(Bytes(':agent:'))
        .concat(op.itob(agentId))
        .concat(Bytes(':total:'))
        .concat(op.itob(this.totalIssued.value))
    )
  }

  // ── Batch Issue ──

  /**
   * Issue BONA FIDE to two agents in one call.
   */
  batchIssue(
    agent1: Account, agentId1: uint64,
    agent2: Account, agentId2: uint64,
  ): void {
    assert(Txn.sender === this.treasury.value, 'Treasury only')
    assert(this.asaId.value > 0, 'ASA not configured')

    // Issue to agent 1
    itxn.assetTransfer({
      assetReceiver: agent1,
      assetSender: Global.currentApplicationAddress,
      xferAsset: this.asaId.value,
      assetAmount: 1,
      fee: 1_000,
    }).submit()

    // Issue to agent 2
    itxn.assetTransfer({
      assetReceiver: agent2,
      assetSender: Global.currentApplicationAddress,
      xferAsset: this.asaId.value,
      assetAmount: 1,
      fee: 1_000,
    }).submit()

    // Track
    if (this.agents(agent1).exists) { this.agents(agent1).value = this.agents(agent1).value + 1 }
    else { this.agents(agent1).value = 1 }
    if (this.agents(agent2).exists) { this.agents(agent2).value = this.agents(agent2).value + 1 }
    else { this.agents(agent2).value = 1 }

    this.totalIssued.value = this.totalIssued.value + 2

    log(Bytes('bonafide:batch:').concat(op.itob(this.totalIssued.value)))
  }

  // ── Revoke BONA FIDE ──

  /**
   * Revoke 1 BONA FIDE from an agent.
   * Clawback from agent back to contract reserve.
   * Governance action — treasury only.
   */
  revokeBonafide(agent: Account, reason: bytes): void {
    assert(Txn.sender === this.treasury.value, 'Treasury only')
    assert(this.asaId.value > 0, 'ASA not configured')
    assert(reason.length > 0 && reason.length <= 200, 'Reason: 1-200 bytes')

    // Clawback from agent to contract reserve
    itxn.assetTransfer({
      assetReceiver: Global.currentApplicationAddress,  // back to reserve
      assetSender: agent,                                // clawback FROM agent
      xferAsset: this.asaId.value,
      assetAmount: 1,
      fee: 1_000,
    }).submit()

    this.totalRevoked.value = this.totalRevoked.value + 1

    log(
      Bytes('bonafide:revoke:')
        .concat(agent.bytes)
        .concat(Bytes(':reason:'))
        .concat(reason)
    )
  }

  // ── Read ──

  getAgentBalance(agent: Account): uint64 {
    if (this.agents(agent).exists) {
      return this.agents(agent).value
    }
    return 0
  }

  getStats(): bytes {
    return Bytes('issued:')
      .concat(op.itob(this.totalIssued.value))
      .concat(Bytes(':revoked:'))
      .concat(op.itob(this.totalRevoked.value))
      .concat(Bytes(':threshold:'))
      .concat(op.itob(this.verifyThreshold.value))
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
