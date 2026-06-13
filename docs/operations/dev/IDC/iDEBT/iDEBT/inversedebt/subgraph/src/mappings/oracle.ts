// DELTAVERSE Subgraph — Oracle Mapping
//
// Handles events emitted by DeltaVerseDebtOracle. This file is the
// counterpart to protocol.ts and focuses on the measurement layer:
// GDSI snapshots, sub-index updates, and LP staking activity in the
// oracle's built-in LP pool.

import { BigInt, log } from "@graphprotocol/graph-ts"
import {
  CompositeUpdated,
  SubIndexUpdated,
  Staked,
  Unstaked,
  RewardsClaimed,
} from "../../generated/DeltaVerseDebtOracle/DeltaVerseDebtOracle"
import {
  Protocol,
  OracleSnapshot,
  SubIndexUpdate,
  LpStaker,
} from "../../generated/schema"

// Reuse the protocol loader from protocol.ts logic. In a real multi-file
// subgraph we would extract this into a shared helpers module, but for
// this skeleton the inline duplication keeps each file self-contained
// and easy to read.

function loadProtocol(): Protocol {
  let protocol = Protocol.load("1")
  if (protocol == null) {
    protocol = new Protocol("1")
    protocol.totalSgdsiSupply = BigInt.zero()
    protocol.cumulativeMintVolume = BigInt.zero()
    protocol.cumulativeBurnVolume = BigInt.zero()
    protocol.cumulativeFees = BigInt.zero()
    protocol.feesRoutedToLps = BigInt.zero()
    protocol.totalThesisPositions = 0
    protocol.activeThesisPositions = 0
    protocol.latestGdsiValue = BigInt.zero()
    protocol.latestEmaValue = BigInt.zero()
    protocol.latestStressLevel = 0
    protocol.latestOracleRound = BigInt.zero()
    protocol.updatedAt = BigInt.zero()
  }
  return protocol as Protocol
}

/**
 * Classify a raw GDSI value into the 0-5 stress level categories
 * matching the oracle contract's stressLevel() function. Keeping
 * this logic identical to the contract guarantees the subgraph's
 * latest stress level matches what the contract would return.
 */
function classifyStress(value: BigInt): i32 {
  // Divide by 1e18 to get the un-scaled integer portion for comparison.
  let precision = BigInt.fromString("1000000000000000000")
  let v = value.div(precision)
  if (v.lt(BigInt.fromI32(800)))  return 0  // Low
  if (v.lt(BigInt.fromI32(1000))) return 1  // Moderate
  if (v.lt(BigInt.fromI32(1250))) return 2  // Elevated
  if (v.lt(BigInt.fromI32(1500))) return 3  // High
  if (v.lt(BigInt.fromI32(2000))) return 4  // Critical
  return 5                                   // Systemic
}

// ═══════════════════════════════════════════════════════════════
// COMPOSITE INDEX UPDATES
// ═══════════════════════════════════════════════════════════════

export function handleCompositeUpdated(event: CompositeUpdated): void {
  let timestamp = event.block.timestamp
  let roundId = event.params.roundId

  // Create an immutable snapshot entity for historical charting.
  let snapshot = new OracleSnapshot(roundId.toString())
  snapshot.roundId = roundId
  snapshot.compositeValue = event.params.value
  snapshot.emaValue = event.params.emaValue
  snapshot.previousValue = event.params.previousValue

  // Compute signed change in basis points. Positive = stress increased,
  // negative = stress decreased. This pre-computation saves the GraphQL
  // client from having to calculate it on every query.
  let bpsDenom = BigInt.fromI32(10000)
  if (event.params.previousValue.isZero()) {
    snapshot.changeBps = BigInt.zero()
  } else if (event.params.value.ge(event.params.previousValue)) {
    let delta = event.params.value.minus(event.params.previousValue)
    snapshot.changeBps = delta.times(bpsDenom).div(event.params.previousValue)
  } else {
    let delta = event.params.previousValue.minus(event.params.value)
    snapshot.changeBps = delta.times(bpsDenom).div(event.params.previousValue).neg()
  }

  // Sub-index values are populated by cross-referencing SubIndexUpdated
  // events, but since CompositeUpdated fires after all sub-indices have
  // been updated, we read the latest values from storage instead.
  // For simplicity in this skeleton, these are initialized to the
  // composite value. A more thorough implementation would track each
  // sub-index's latest state in its own entity.
  snapshot.sdrValue = event.params.value
  snapshot.ysiValue = event.params.value
  snapshot.csiValue = event.params.value
  snapshot.mdiValue = event.params.value
  snapshot.rpiValue = event.params.value

  snapshot.stressLevel = classifyStress(event.params.value)

  snapshot.blockNumber = event.block.number
  snapshot.blockTimestamp = timestamp
  snapshot.transactionHash = event.transaction.hash
  snapshot.save()

  // Update the protocol singleton's cached latest values.
  let protocol = loadProtocol()
  protocol.latestGdsiValue = event.params.value
  protocol.latestEmaValue = event.params.emaValue
  protocol.latestStressLevel = snapshot.stressLevel
  protocol.latestOracleRound = roundId
  protocol.updatedAt = timestamp
  protocol.save()
}

// ═══════════════════════════════════════════════════════════════
// SUB-INDEX UPDATES
// ═══════════════════════════════════════════════════════════════

export function handleSubIndexUpdated(event: SubIndexUpdated): void {
  let id = event.transaction.hash.toHexString() + "-" + event.logIndex.toString()
  let update = new SubIndexUpdate(id)
  update.subIndexId = event.params.id
  update.value = event.params.medianValue
  update.confidence = BigInt.zero()  // reporter-only updates have no confidence
  update.sourcesUsed = event.params.reportCount.toI32()
  update.blockNumber = event.block.number
  update.blockTimestamp = event.block.timestamp
  update.transactionHash = event.transaction.hash
  update.save()
}

// ═══════════════════════════════════════════════════════════════
// LP STAKING
// ═══════════════════════════════════════════════════════════════

function loadOrCreateLpStaker(address: string, timestamp: BigInt): LpStaker {
  let staker = LpStaker.load(address)
  if (staker == null) {
    staker = new LpStaker(address)
    staker.address = event_param_to_bytes(address)
    staker.stakedAmount = BigInt.zero()
    staker.totalRewardsClaimed = BigInt.zero()
    staker.totalStaked = BigInt.zero()
    staker.totalUnstaked = BigInt.zero()
    staker.firstStakeAt = timestamp
    staker.lastActionAt = timestamp
  }
  return staker as LpStaker
}

// Helper to convert a hex-string address back to Bytes for storage.
// AssemblyScript does not have a cleaner way to round-trip these.
function event_param_to_bytes(hex: string): Bytes {
  return Bytes.fromHexString(hex) as Bytes
}

// Need to import Bytes for the helper above.
import { Bytes } from "@graphprotocol/graph-ts"

export function handleStaked(event: Staked): void {
  let userId = event.params.user.toHexString()
  let staker = loadOrCreateLpStaker(userId, event.block.timestamp)
  staker.stakedAmount = staker.stakedAmount.plus(event.params.amount)
  staker.totalStaked = staker.totalStaked.plus(event.params.amount)
  staker.lastActionAt = event.block.timestamp
  staker.save()
}

export function handleUnstaked(event: Unstaked): void {
  let userId = event.params.user.toHexString()
  let staker = LpStaker.load(userId)
  if (staker == null) {
    log.warning("Unstaked event for unknown staker: {}", [userId])
    return
  }
  if (staker.stakedAmount.ge(event.params.amount)) {
    staker.stakedAmount = staker.stakedAmount.minus(event.params.amount)
  } else {
    staker.stakedAmount = BigInt.zero()
  }
  staker.totalUnstaked = staker.totalUnstaked.plus(event.params.amount)
  staker.lastActionAt = event.block.timestamp
  staker.save()
}

export function handleRewardsClaimed(event: RewardsClaimed): void {
  let userId = event.params.user.toHexString()
  let staker = LpStaker.load(userId)
  if (staker == null) {
    log.warning("RewardsClaimed for unknown staker: {}", [userId])
    return
  }
  staker.totalRewardsClaimed = staker.totalRewardsClaimed.plus(event.params.amount)
  staker.lastActionAt = event.block.timestamp
  staker.save()
}
