// DELTAVERSE Subgraph — Protocol Mapping
//
// Handler functions for events emitted by DebtInheritanceProtocol.
// Each handler decodes the event, looks up or creates the relevant
// entities, updates their state, and saves them back to the indexer's
// store. The Graph then exposes all of this through the GraphQL API.
//
// AssemblyScript notes for readers coming from TypeScript:
//
//   - There is no dynamic typing. Every variable must have a known
//     type at compile time, or the compile fails.
//
//   - Integers and BigInt are different types. Arithmetic between
//     them requires explicit conversion: BigInt.fromI32(5).
//
//   - Classes use the `new` keyword even for simple data structures.
//     There is no object literal syntax like `{foo: 1}`.
//
//   - String concatenation uses `+` but the operands must both be
//     strings. Numbers must be explicitly stringified with .toString().
//
//   - There is no `undefined`. Missing fields come back as null and
//     must be checked explicitly.

import { BigInt, Bytes, log } from "@graphprotocol/graph-ts"
import {
  SGdsiMinted,
  SGdsiBurned,
  ThesisExpressed,
  ThesisClosed,
  FeesRoutedToOracleLPs,
} from "../../generated/DebtInheritanceProtocol/DebtInheritanceProtocol"
import {
  Protocol,
  User,
  SgdsiMint,
  SgdsiBurn,
  ThesisPosition,
  FeeRouting,
  HourlyStat,
} from "../../generated/schema"

// ═══════════════════════════════════════════════════════════════
// SINGLETON LOADERS
// ═══════════════════════════════════════════════════════════════
//
// The Protocol entity is a singleton — there is exactly one of it,
// and it accumulates all protocol-level state. This loader creates
// it on first access with sensible defaults.

function loadOrCreateProtocol(): Protocol {
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

// User loader creates a new User entity on first interaction and
// returns the existing one on subsequent calls. The user ID is the
// hex string of the address.

function loadOrCreateUser(address: Bytes, timestamp: BigInt): User {
  let id = address.toHexString()
  let user = User.load(id)
  if (user == null) {
    user = new User(id)
    user.address = address
    user.sgdsiBalance = BigInt.zero()
    user.cumulativeMintVolume = BigInt.zero()
    user.cumulativeBurnVolume = BigInt.zero()
    user.cumulativeFeesPaid = BigInt.zero()
    user.mintCount = 0
    user.burnCount = 0
    user.thesisExpressionCount = 0
    user.createdAt = timestamp
    user.updatedAt = timestamp
  }
  return user as User
}

// Hourly stat loader creates a new bucket when we cross into a new hour.
// Buckets are keyed by (timestamp / 3600) so they naturally form a
// non-overlapping time series.

function loadOrCreateHourlyStat(timestamp: BigInt): HourlyStat {
  let hourBucket = timestamp.div(BigInt.fromI32(3600))
  let id = hourBucket.toString()
  let stat = HourlyStat.load(id)
  if (stat == null) {
    stat = new HourlyStat(id)
    stat.hourStart = hourBucket.times(BigInt.fromI32(3600))
    stat.mintVolume = BigInt.zero()
    stat.burnVolume = BigInt.zero()
    stat.feesCollected = BigInt.zero()
    stat.mintCount = 0
    stat.burnCount = 0
    stat.gdsiOpen = BigInt.zero()
    stat.gdsiHigh = BigInt.zero()
    stat.gdsiLow = BigInt.zero()
    stat.gdsiClose = BigInt.zero()
    stat.thesisExpressedCount = 0
    stat.thesisClosedCount = 0
  }
  return stat as HourlyStat
}

// ═══════════════════════════════════════════════════════════════
// EVENT HANDLERS
// ═══════════════════════════════════════════════════════════════

export function handleSgdsiMinted(event: SGdsiMinted): void {
  let timestamp = event.block.timestamp

  // Create the immutable mint event entity. The ID combines tx hash
  // and log index to ensure uniqueness across all chain history.
  let mintId = event.transaction.hash.toHexString() + "-" + event.logIndex.toString()
  let mint = new SgdsiMint(mintId)
  mint.user = event.params.user.toHexString()
  mint.stableIn = event.params.stableIn
  mint.sgdsiOut = event.params.sGdsiOut
  mint.price = event.params.price
  mint.fee = event.params.fee
  mint.blockNumber = event.block.number
  mint.blockTimestamp = timestamp
  mint.transactionHash = event.transaction.hash
  mint.save()

  // Update the user's aggregate state.
  let user = loadOrCreateUser(event.params.user, timestamp)
  user.sgdsiBalance = user.sgdsiBalance.plus(event.params.sGdsiOut)
  user.cumulativeMintVolume = user.cumulativeMintVolume.plus(event.params.stableIn)
  user.cumulativeFeesPaid = user.cumulativeFeesPaid.plus(event.params.fee)
  user.mintCount = user.mintCount + 1
  user.updatedAt = timestamp
  user.save()

  // Update the singleton protocol entity.
  let protocol = loadOrCreateProtocol()
  protocol.totalSgdsiSupply = protocol.totalSgdsiSupply.plus(event.params.sGdsiOut)
  protocol.cumulativeMintVolume = protocol.cumulativeMintVolume.plus(event.params.stableIn)
  protocol.cumulativeFees = protocol.cumulativeFees.plus(event.params.fee)
  protocol.updatedAt = timestamp
  protocol.save()

  // Update the hourly bucket for time-series queries.
  let hourlyStat = loadOrCreateHourlyStat(timestamp)
  hourlyStat.mintVolume = hourlyStat.mintVolume.plus(event.params.stableIn)
  hourlyStat.feesCollected = hourlyStat.feesCollected.plus(event.params.fee)
  hourlyStat.mintCount = hourlyStat.mintCount + 1
  // Track the price as it moved through this hour for OHLC charting.
  if (hourlyStat.gdsiOpen.isZero()) hourlyStat.gdsiOpen = event.params.price
  if (hourlyStat.gdsiHigh.lt(event.params.price)) hourlyStat.gdsiHigh = event.params.price
  if (hourlyStat.gdsiLow.isZero() || hourlyStat.gdsiLow.gt(event.params.price)) {
    hourlyStat.gdsiLow = event.params.price
  }
  hourlyStat.gdsiClose = event.params.price
  hourlyStat.save()
}

export function handleSgdsiBurned(event: SGdsiBurned): void {
  let timestamp = event.block.timestamp

  let burnId = event.transaction.hash.toHexString() + "-" + event.logIndex.toString()
  let burn = new SgdsiBurn(burnId)
  burn.user = event.params.user.toHexString()
  burn.sgdsiIn = event.params.sGdsiIn
  burn.stableOut = event.params.stableOut
  burn.price = event.params.price
  burn.fee = event.params.fee
  burn.blockNumber = event.block.number
  burn.blockTimestamp = timestamp
  burn.transactionHash = event.transaction.hash
  burn.save()

  let user = loadOrCreateUser(event.params.user, timestamp)
  // Guard against underflow in case the user transferred sGDSI out of
  // band and burned tokens they received from someone else. In that
  // case the event is valid but the running balance we track is
  // incorrect. Clamp to zero rather than revert.
  if (user.sgdsiBalance.ge(event.params.sGdsiIn)) {
    user.sgdsiBalance = user.sgdsiBalance.minus(event.params.sGdsiIn)
  } else {
    user.sgdsiBalance = BigInt.zero()
  }
  user.cumulativeBurnVolume = user.cumulativeBurnVolume.plus(event.params.stableOut)
  user.cumulativeFeesPaid = user.cumulativeFeesPaid.plus(event.params.fee)
  user.burnCount = user.burnCount + 1
  user.updatedAt = timestamp
  user.save()

  let protocol = loadOrCreateProtocol()
  if (protocol.totalSgdsiSupply.ge(event.params.sGdsiIn)) {
    protocol.totalSgdsiSupply = protocol.totalSgdsiSupply.minus(event.params.sGdsiIn)
  }
  protocol.cumulativeBurnVolume = protocol.cumulativeBurnVolume.plus(event.params.stableOut)
  protocol.cumulativeFees = protocol.cumulativeFees.plus(event.params.fee)
  protocol.updatedAt = timestamp
  protocol.save()

  let hourlyStat = loadOrCreateHourlyStat(timestamp)
  hourlyStat.burnVolume = hourlyStat.burnVolume.plus(event.params.stableOut)
  hourlyStat.feesCollected = hourlyStat.feesCollected.plus(event.params.fee)
  hourlyStat.burnCount = hourlyStat.burnCount + 1
  hourlyStat.gdsiClose = event.params.price
  if (hourlyStat.gdsiHigh.lt(event.params.price)) hourlyStat.gdsiHigh = event.params.price
  if (hourlyStat.gdsiLow.isZero() || hourlyStat.gdsiLow.gt(event.params.price)) {
    hourlyStat.gdsiLow = event.params.price
  }
  hourlyStat.save()
}

export function handleThesisExpressed(event: ThesisExpressed): void {
  let timestamp = event.block.timestamp
  let user = loadOrCreateUser(event.params.user, timestamp)

  // The thesis position ID is the user address, because there is only
  // ever one active thesis per user (enforced by the contract).
  let positionId = event.params.user.toHexString()
  let position = new ThesisPosition(positionId)
  position.user = positionId
  position.rwaCollateral = event.params.rwaCollateral
  position.rwaAmount = event.params.rwaAmount
  position.borrowedStable = event.params.borrowed
  position.perpCollateral = event.params.borrowed  // initial = borrow
  position.leverage = event.params.leverage.toI32()
  position.isLong = event.params.isLong
  position.openedAt = timestamp
  position.openIndexValue = event.params.openIndexValue
  position.openTransactionHash = event.transaction.hash
  position.active = true
  position.save()

  user.activeThesisPosition = positionId
  user.thesisExpressionCount = user.thesisExpressionCount + 1
  user.updatedAt = timestamp
  user.save()

  let protocol = loadOrCreateProtocol()
  protocol.totalThesisPositions = protocol.totalThesisPositions + 1
  protocol.activeThesisPositions = protocol.activeThesisPositions + 1
  protocol.updatedAt = timestamp
  protocol.save()

  let hourlyStat = loadOrCreateHourlyStat(timestamp)
  hourlyStat.thesisExpressedCount = hourlyStat.thesisExpressedCount + 1
  hourlyStat.save()
}

export function handleThesisClosed(event: ThesisClosed): void {
  let timestamp = event.block.timestamp
  let positionId = event.params.user.toHexString()
  let position = ThesisPosition.load(positionId)
  if (position == null) {
    // This can happen if the subgraph started after the position was
    // opened (no ThesisExpressed event in our history). Log and skip
    // rather than crash.
    log.warning("ThesisClosed for unknown position: {}", [positionId])
    return
  }

  position.active = false
  position.closedAt = timestamp
  position.closeIndexValue = event.params.closeIndex
  position.closeTransactionHash = event.transaction.hash
  position.realizedPnl = event.params.perpPnl
  position.stableReturned = event.params.stableReturned
  position.save()

  let user = User.load(positionId)
  if (user != null) {
    user.activeThesisPosition = null
    user.updatedAt = timestamp
    user.save()
  }

  let protocol = loadOrCreateProtocol()
  if (protocol.activeThesisPositions > 0) {
    protocol.activeThesisPositions = protocol.activeThesisPositions - 1
  }
  protocol.updatedAt = timestamp
  protocol.save()

  let hourlyStat = loadOrCreateHourlyStat(timestamp)
  hourlyStat.thesisClosedCount = hourlyStat.thesisClosedCount + 1
  hourlyStat.save()
}

export function handleFeesRouted(event: FeesRoutedToOracleLPs): void {
  let feeId = event.transaction.hash.toHexString() + "-" + event.logIndex.toString()
  let routing = new FeeRouting(feeId)
  routing.amount = event.params.amount
  routing.routedBy = event.transaction.from
  routing.blockNumber = event.block.number
  routing.blockTimestamp = event.block.timestamp
  routing.transactionHash = event.transaction.hash
  routing.save()

  let protocol = loadOrCreateProtocol()
  protocol.feesRoutedToLps = protocol.feesRoutedToLps.plus(event.params.amount)
  protocol.updatedAt = event.block.timestamp
  protocol.save()
}
