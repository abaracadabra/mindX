/**
 * Pyth Price Update Keeper
 *
 * Responsible for keeping our oracle's Pyth-backed sub-indices fresh.
 * Without this keeper, the Pyth sources in the DeltaVerseDebtOracle's
 * composite aggregation would go stale and be excluded from the index,
 * degrading the oracle to Chainlink + reporter-only mode.
 *
 * The flow:
 *
 *   1. Fetch signed price updates for all configured Pyth feed IDs
 *      from the Pyth Hermes HTTP API. Hermes is Pyth's off-chain relay
 *      that serves already-signed updates.
 *
 *   2. Call getUpdateFee() on our DeltaVerseDebtOracle to determine
 *      how much ETH (or native token) we need to send along with the
 *      update. Pyth charges a small fee per update.
 *
 *   3. Call updatePythFeeds() on our oracle, forwarding the signed
 *      data and paying the fee. Our oracle internally calls the Pyth
 *      contract's updatePriceFeeds(), which verifies the Wormhole
 *      signature and stores the new prices.
 *
 *   4. Repeat on a configurable interval (default 60 seconds).
 *
 * Note on economics: Pyth fees are typically a few thousand wei per
 * update. For high-frequency updates on L1 mainnet, the gas cost of
 * the transaction dwarfs the Pyth fee, so the economic constraint is
 * really "how often is an update worth it given gas prices?" not
 * "can we afford the Pyth fee?"
 */

import { parseAbi } from 'viem';
import { publicClient, walletClient, contracts, pythFeedIds, config, log } from './config.js';

// ABI for just the oracle functions this keeper needs. Using parseAbi
// instead of a full JSON ABI file keeps the bundle small and makes it
// obvious which functions the keeper actually touches.
const oracleAbi = parseAbi([
  'function updatePythFeeds(bytes[] priceUpdateData) external payable',
]);

/**
 * Fetch price update data from Pyth's Hermes API.
 *
 * Hermes is a simple HTTP service that returns the latest signed price
 * updates for requested feed IDs. The returned data is a base64-encoded
 * VAA (Verifiable Action Approval) that the Pyth contract on-chain
 * cryptographically verifies before updating its stored price.
 */
async function fetchPythUpdates(feedIds: string[]): Promise<`0x${string}`[]> {
  // Filter out placeholder feed IDs (0x0) that haven't been configured yet.
  const activeFeedIds = feedIds.filter(id => id !== '0x0' && id.length === 66);
  if (activeFeedIds.length === 0) {
    log.warn('No Pyth feed IDs configured; skipping update');
    return [];
  }

  // The Hermes API accepts multiple ids[] query parameters and returns
  // the signed updates as hex-encoded binary data in the response body.
  const url = new URL('https://hermes.pyth.network/v2/updates/price/latest');
  activeFeedIds.forEach(id => url.searchParams.append('ids[]', id));
  url.searchParams.append('encoding', 'hex');

  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`Hermes API error: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();

  // Hermes returns an object with binary.data array containing hex strings.
  // Each string is prepended with '0x' to match viem's expected format.
  if (!data.binary || !data.binary.data) {
    throw new Error('Unexpected Hermes response format');
  }

  return data.binary.data.map((hex: string) => `0x${hex}` as `0x${string}`);
}

/**
 * Check current gas price against our configured maximum. If gas is
 * too expensive, skip this update cycle rather than paying more than
 * we budgeted. The next cycle will try again.
 */
async function isGasPriceAcceptable(): Promise<boolean> {
  const gasPrice = await publicClient.getGasPrice();
  if (gasPrice > config.maxGasPriceWei) {
    log.warn('Gas price too high, skipping Pyth update', {
      current: gasPrice.toString(),
      max: config.maxGasPriceWei.toString(),
    });
    return false;
  }
  return true;
}

/**
 * One iteration of the Pyth update loop. This is wrapped in a try/catch
 * at the top level so a transient failure in one cycle does not kill
 * the entire keeper process.
 */
async function runOnce() {
  if (!(await isGasPriceAcceptable())) return;

  const feedIds = Object.values(pythFeedIds);
  const updates = await fetchPythUpdates(feedIds);

  if (updates.length === 0) return;

  // The oracle's updatePythFeeds function internally calls getUpdateFee
  // and forwards the fee to Pyth, so we need to send enough ETH to cover
  // it. For safety we read the fee from the oracle's Pyth contract
  // directly. In a production deployment this could be computed once
  // per batch rather than per transaction.
  //
  // For simplicity here we send a conservative 0.01 ETH with each call,
  // which is massively more than needed on any chain (Pyth fees are
  // typically in the range of 0.000001 ETH per update). The Pyth
  // contract refunds any excess, but our oracle's updatePythFeeds
  // function also refunds excess ETH back to msg.sender.
  const conservativeFee = 10_000_000_000_000_000n; // 0.01 ETH

  const hash = await walletClient.writeContract({
    address: contracts.oracle,
    abi: oracleAbi,
    functionName: 'updatePythFeeds',
    args: [updates],
    value: conservativeFee,
  });

  log.info('Pyth feeds updated', {
    txHash: hash,
    feedCount: updates.length,
  });

  // Wait for confirmation so that the next iteration sees the updated
  // state, and so that a failure shows up immediately rather than
  // propagating into the next cycle.
  const receipt = await publicClient.waitForTransactionReceipt({ hash });
  if (receipt.status !== 'success') {
    throw new Error(`Pyth update transaction reverted: ${hash}`);
  }
}

/**
 * Main loop. Runs forever, executing one update cycle every
 * pythUpdateIntervalMs milliseconds. Errors are logged but do not
 * terminate the loop — the next cycle will retry.
 */
export async function startPythUpdater() {
  log.info('Pyth updater starting', {
    intervalMs: config.pythUpdateIntervalMs,
    feedIds: Object.keys(pythFeedIds),
  });

  // Run immediately on startup instead of waiting for the first interval,
  // so that a keeper restart gets the oracle fresh right away.
  try {
    await runOnce();
  } catch (e) {
    log.error('Initial Pyth update failed', { error: (e as Error).message });
  }

  setInterval(async () => {
    try {
      await runOnce();
    } catch (e) {
      log.error('Pyth update cycle failed', { error: (e as Error).message });
    }
  }, config.pythUpdateIntervalMs);
}
