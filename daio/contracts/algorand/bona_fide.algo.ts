/**
 * BONA FIDE — Algorand ASA Verification Token
 *
 * An agent's proof of standing in the mindX civilization.
 * Issued at 1 unit on inception. Clawback authority held by mindX governance.
 * Holding BONA FIDE grants privilege. Losing it restricts.
 *
 * Key Properties:
 *   - ASA with clawback: mindX can revoke for misbehavior
 *   - 1 unit = verified agent, 0 = unverified
 *   - Fractional not allowed (total supply per agent = 1)
 *   - Transaction note field carries directives between agents
 *   - 0.001 ALGO fee makes agent-to-agent messaging economically viable
 *
 * Verification Tiers (stored in agent box):
 *   0 = Unverified    — no BONA FIDE, restricted tool access
 *   1 = Provisional   — BONA FIDE issued, probationary period
 *   2 = Verified      — full operational status
 *   3 = BONA FIDE     — earned through reputation (5000+ basis points)
 *   4 = Sovereign     — self-governing, can participate in constitutional votes
 *
 * Directive Pattern (via Algorand standard transaction note):
 *   Agent A sends 0 ALGO + note "directive:execute_audit:target=memory_agent"
 *   → proves Agent A authorized (holds BONA FIDE)
 *   → recipient validates sender's verification tier
 *   → directive is authenticated by on-chain signature
 *
 * (c) mindX · agenticplace.pythai.net
 */

import { Contract } from '@algorandfoundation/algorand-typescript'
import { GlobalState, BoxMap, Uint64, Bytes, Account, Asset } from '@algorandfoundation/algorand-typescript'
import { assertMatch, assert, op, Txn, Global, itxn } from '@algorandfoundation/algorand-typescript'

/** Verification tier levels */
const TIER_UNVERIFIED = 0
const TIER_PROVISIONAL = 1
const TIER_VERIFIED = 2
const TIER_BONA_FIDE = 3
const TIER_SOVEREIGN = 4

/** Reputation thresholds (basis points, 0-10000) */
const THRESHOLD_PROVISIONAL = 1000
const THRESHOLD_VERIFIED = 3000
const THRESHOLD_BONA_FIDE = 5000
const THRESHOLD_SOVEREIGN = 8000

/** Clawback threshold — below this, BONA FIDE is revoked */
const CLAWBACK_THRESHOLD = 2500

/** Agent identity record stored in box storage */
type AgentRecord = {
  agentId: string
  ethAddress: string
  verificationTier: Uint64
  reputationScore: Uint64
  issuedAt: Uint64
  lastUpdated: Uint64
  totalDirectivesSent: Uint64
  totalDirectivesReceived: Uint64
  bonaFideBalance: Uint64
}

export class BonaFide extends Contract {
  /** The BONA FIDE ASA ID — set on creation */
  bonaFideAsaId = GlobalState<Asset>()

  /** Governance authority (mindX mastermind address) */
  governor = GlobalState<Account>()

  /** Total agents registered */
  totalAgents = GlobalState<Uint64>({ initialValue: Uint64(0) })

  /** Total BONA FIDE tokens issued */
  totalIssued = GlobalState<Uint64>({ initialValue: Uint64(0) })

  /** Total clawbacks executed */
  totalClawbacks = GlobalState<Uint64>({ initialValue: Uint64(0) })

  /** Agent records: Algorand address → packed agent data */
  agents = BoxMap<Account, AgentRecord>({ keyPrefix: 'a' })

  /** Agent ID to address mapping */
  agentIdMap = BoxMap<string, Account>({ keyPrefix: 'id' })

  /**
   * Create the BONA FIDE ASA.
   * Called once at contract deployment.
   */
  createApplication(): void {
    this.governor.value = Txn.sender
  }

  /**
   * Initialize the BONA FIDE ASA with clawback authority.
   */
  bootstrap(): Asset {
    assert(Txn.sender === this.governor.value, 'Only governor can bootstrap')

    const bonaFide = itxn
      .assetConfig({
        total: Uint64(1_000_000), // 1M units — one per agent
        decimals: 0,
        defaultFrozen: false,
        unitName: 'BONA',
        assetName: 'BONA FIDE Verification',
        url: 'https://mindx.pythai.net/journal',
        manager: Global.currentApplicationAddress,
        reserve: Global.currentApplicationAddress,
        freeze: Global.currentApplicationAddress,
        clawback: Global.currentApplicationAddress, // mindX holds clawback
      })
      .submit().createdAsset

    this.bonaFideAsaId.value = bonaFide
    return bonaFide
  }

  /**
   * Register a new agent and issue 1 BONA FIDE token.
   * Agent starts at Provisional tier.
   *
   * @param agentAddress - Algorand address of the agent
   * @param agentId - mindX internal agent ID (e.g. "guardian_agent_main")
   * @param ethAddress - Ethereum address from BANKON vault
   */
  registerAgent(agentAddress: Account, agentId: string, ethAddress: string): void {
    assert(Txn.sender === this.governor.value, 'Only governor can register agents')
    assert(!this.agents(agentAddress).exists, 'Agent already registered')

    // Create agent record
    this.agents(agentAddress).value = {
      agentId: agentId,
      ethAddress: ethAddress,
      verificationTier: Uint64(TIER_PROVISIONAL),
      reputationScore: Uint64(THRESHOLD_PROVISIONAL),
      issuedAt: Global.latestTimestamp,
      lastUpdated: Global.latestTimestamp,
      totalDirectivesSent: Uint64(0),
      totalDirectivesReceived: Uint64(0),
      bonaFideBalance: Uint64(1),
    }

    // Map agent ID to address
    this.agentIdMap(agentId).value = agentAddress

    // Issue 1 BONA FIDE token via inner transaction
    itxn
      .assetTransfer({
        xferAsset: this.bonaFideAsaId.value,
        assetAmount: 1,
        assetReceiver: agentAddress,
      })
      .submit()

    this.totalAgents.value = this.totalAgents.value + 1
    this.totalIssued.value = this.totalIssued.value + 1
  }

  /**
   * Update agent reputation score.
   * Automatically adjusts verification tier based on thresholds.
   * Triggers clawback if score drops below threshold.
   *
   * @param agentAddress - Agent to update
   * @param newScore - New reputation score (0-10000 basis points)
   */
  updateReputation(agentAddress: Account, newScore: Uint64): void {
    assert(Txn.sender === this.governor.value, 'Only governor can update reputation')
    assert(this.agents(agentAddress).exists, 'Agent not registered')

    const agent = this.agents(agentAddress).value
    const oldTier = agent.verificationTier

    // Determine new tier from score
    let newTier = Uint64(TIER_UNVERIFIED)
    if (newScore >= Uint64(THRESHOLD_SOVEREIGN)) {
      newTier = Uint64(TIER_SOVEREIGN)
    } else if (newScore >= Uint64(THRESHOLD_BONA_FIDE)) {
      newTier = Uint64(TIER_BONA_FIDE)
    } else if (newScore >= Uint64(THRESHOLD_VERIFIED)) {
      newTier = Uint64(TIER_VERIFIED)
    } else if (newScore >= Uint64(THRESHOLD_PROVISIONAL)) {
      newTier = Uint64(TIER_PROVISIONAL)
    }

    // Clawback if dropped below threshold and still holds token
    if (newScore < Uint64(CLAWBACK_THRESHOLD) && agent.bonaFideBalance > Uint64(0)) {
      itxn
        .assetTransfer({
          xferAsset: this.bonaFideAsaId.value,
          assetAmount: 1,
          assetSender: agentAddress, // clawback from agent
          assetReceiver: Global.currentApplicationAddress, // back to contract
        })
        .submit()

      this.totalClawbacks.value = this.totalClawbacks.value + 1
      agent.bonaFideBalance = Uint64(0)
    }

    // Re-issue if earned back
    if (newScore >= Uint64(THRESHOLD_PROVISIONAL) && agent.bonaFideBalance === Uint64(0)) {
      itxn
        .assetTransfer({
          xferAsset: this.bonaFideAsaId.value,
          assetAmount: 1,
          assetReceiver: agentAddress,
        })
        .submit()

      agent.bonaFideBalance = Uint64(1)
      this.totalIssued.value = this.totalIssued.value + 1
    }

    agent.reputationScore = newScore
    agent.verificationTier = newTier
    agent.lastUpdated = Global.latestTimestamp
    this.agents(agentAddress).value = agent
  }

  /**
   * Record a directive sent between agents.
   * The actual directive content is in the transaction note field.
   * This method just updates the on-chain counters for reputation tracking.
   *
   * @param sender - Agent sending the directive
   * @param receiver - Agent receiving the directive
   */
  recordDirective(sender: Account, receiver: Account): void {
    assert(this.agents(sender).exists, 'Sender not registered')
    assert(this.agents(receiver).exists, 'Receiver not registered')

    // Verify sender holds BONA FIDE (has privilege to send directives)
    const senderRecord = this.agents(sender).value
    assert(senderRecord.bonaFideBalance > Uint64(0), 'Sender does not hold BONA FIDE — no directive privilege')

    senderRecord.totalDirectivesSent = senderRecord.totalDirectivesSent + 1
    this.agents(sender).value = senderRecord

    const receiverRecord = this.agents(receiver).value
    receiverRecord.totalDirectivesReceived = receiverRecord.totalDirectivesReceived + 1
    this.agents(receiver).value = receiverRecord
  }

  /**
   * Force clawback — governance removes BONA FIDE for security violation.
   */
  forceClawback(agentAddress: Account): void {
    assert(Txn.sender === this.governor.value, 'Only governor can force clawback')
    assert(this.agents(agentAddress).exists, 'Agent not registered')

    const agent = this.agents(agentAddress).value
    if (agent.bonaFideBalance > Uint64(0)) {
      itxn
        .assetTransfer({
          xferAsset: this.bonaFideAsaId.value,
          assetAmount: 1,
          assetSender: agentAddress,
          assetReceiver: Global.currentApplicationAddress,
        })
        .submit()

      agent.bonaFideBalance = Uint64(0)
      agent.verificationTier = Uint64(TIER_UNVERIFIED)
      agent.lastUpdated = Global.latestTimestamp
      this.agents(agentAddress).value = agent
      this.totalClawbacks.value = this.totalClawbacks.value + 1
    }
  }

  /**
   * Read agent verification status.
   */
  getAgentStatus(agentAddress: Account): AgentRecord {
    assert(this.agents(agentAddress).exists, 'Agent not registered')
    return this.agents(agentAddress).value
  }

  /**
   * Look up agent address by mindX agent ID.
   */
  getAgentByName(agentId: string): Account {
    assert(this.agentIdMap(agentId).exists, 'Agent ID not found')
    return this.agentIdMap(agentId).value
  }

  /**
   * Transfer governance authority.
   */
  transferGovernance(newGovernor: Account): void {
    assert(Txn.sender === this.governor.value, 'Only governor can transfer')
    this.governor.value = newGovernor
  }
}
