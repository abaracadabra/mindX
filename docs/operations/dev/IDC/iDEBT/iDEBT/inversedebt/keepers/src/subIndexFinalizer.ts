/**
 * Sub-Index Finalizer Keeper
 *
 * The DeltaVerseDebtOracle collects reporter submissions into a staging
 * area, and the composite GDSI is only refreshed when a keeper calls
 * finalizeSubIndex() on each sub-index followed by updateComposite().
 * This keeper is what performs those calls.
 *
 * Why is this not a single on-chain function that runs automatically?
 * Because Ethereum contracts cannot schedule their own execution. They
 * only run when somebody sends them a transaction. The "somebody" here
 * is this keeper.
 *
 * The finalizer runs on a slower cadence than the Pyth updater (every
 * four hours by default) because reporter submissions themselves come
 * in on a slow cadence — they represent aggregated macroeconomic data
 * like debt-to-GDP ratios that do not change minute by minute.
 *
 * Care must be taken around the deviation circuit breaker. If the new
 * composite value differs from the old by more than maxDeviationBps
 * (default 10%), the contract refuses to apply it automatically and
 * stages the update as pending. The keeper logs this condition so the
 * ops team knows to investigate, but it does NOT auto-approve the
 * pending update — approval requires governor review.
 */

import { parseAbi } from 'viem';
import { publicClient, walletClient, contracts, config, log } from './config.js';

const oracleAbi = parseAbi([
  'function finalizeSubIndex(uint8 subIndexId) external',
  'function updateComposite() external',
  'function getReportCount(uint8 subIndexId) view returns (uint256)',
  'function hasPendingUpdate() view returns (bool)',
  'function activeSubIndexCount() view returns (uint8)',
  'function minReportsRequired() view returns (uint256)',
  'function compositeValue() view returns (uint256)',
]);

/**
 * Check whether a specific sub-index has enough reports to be finalized.
 * We call getReportCount and compare to minReportsRequired. If there
 * are not enough reports, finalizing would revert with NoReportsAvailable,
 * which wastes gas, so we filter here first.
 *
 * Note that a sub-index can also be finalized from Chainlink or Pyth
 * data alone if no reporters have submitted but those sources are
 * configured, so a reportCount of zero does not necessarily mean
 * finalization will fail. We attempt finalization anyway if the
 * sub-index has non-zero weight configured, and let the contract
 * decide whether it has enough data.
 */
async function canFinalize(subIndexId: number): Promise<boolean> {
  const reportCount = await publicClient.readContract({
    address: contracts.oracle,
    abi: oracleAbi,
    functionName: 'getReportCount',
    args: [subIndexId],
  });

  const minRequired = await publicClient.readContract({
    address: contracts.oracle,
    abi: oracleAbi,
    functionName: 'minReportsRequired',
  });

  // If reports alone meet the minimum, we can definitely finalize.
  // If not, we still try because Chainlink/Pyth sources may carry it.
  return reportCount >= minRequired || reportCount === 0n;
}

/**
 * Finalize all sub-indices that have data available, then update the
 * composite. This is the core work of the keeper.
 *
 * Each finalize call is wrapped individually so that a failure on one
 * sub-index does not prevent the others from being finalized. For
 * example, if SDR has bad data and reverts, we still want YSI, CSI,
 * MDI, and RPI to complete.
 */
async function runOnce() {
  const count = await publicClient.readContract({
    address: contracts.oracle,
    abi: oracleAbi,
    functionName: 'activeSubIndexCount',
  });

  log.info('Running sub-index finalization', { activeCount: count });

  let finalizedCount = 0;

  for (let i = 0; i < count; i++) {
    try {
      if (!(await canFinalize(i))) {
        log.info('Skipping sub-index, insufficient data', { subIndexId: i });
        continue;
      }

      const hash = await walletClient.writeContract({
        address: contracts.oracle,
        abi: oracleAbi,
        functionName: 'finalizeSubIndex',
        args: [i],
      });

      const receipt = await publicClient.waitForTransactionReceipt({ hash });
      if (receipt.status === 'success') {
        log.info('Sub-index finalized', { subIndexId: i, txHash: hash });
        finalizedCount++;
      } else {
        log.warn('Sub-index finalize reverted', { subIndexId: i, txHash: hash });
      }
    } catch (e) {
      log.error('Sub-index finalize failed', {
        subIndexId: i,
        error: (e as Error).message,
      });
    }
  }

  // Only attempt composite update if at least one sub-index was finalized
  // this round. Otherwise there is nothing new to aggregate.
  if (finalizedCount === 0) {
    log.info('No sub-indices finalized this round; skipping composite update');
    return;
  }

  try {
    const priceBefore = await publicClient.readContract({
      address: contracts.oracle,
      abi: oracleAbi,
      functionName: 'compositeValue',
    });

    const hash = await walletClient.writeContract({
      address: contracts.oracle,
      abi: oracleAbi,
      functionName: 'updateComposite',
    });

    const receipt = await publicClient.waitForTransactionReceipt({ hash });
    if (receipt.status !== 'success') {
      log.error('Composite update reverted', { txHash: hash });
      return;
    }

    // Check whether the update was applied directly or staged as pending
    // due to the deviation circuit breaker tripping.
    const isPending = await publicClient.readContract({
      address: contracts.oracle,
      abi: oracleAbi,
      functionName: 'hasPendingUpdate',
    });

    const priceAfter = await publicClient.readContract({
      address: contracts.oracle,
      abi: oracleAbi,
      functionName: 'compositeValue',
    });

    if (isPending) {
      // The contract refused to auto-apply the update because it exceeded
      // the 10% deviation threshold. This is not an error — it is the
      // circuit breaker working as designed — but it needs ops attention
      // because the pending value will stay staged until a governor
      // approves or rejects it.
      log.warn('Composite update flagged as pending; governor review required', {
        txHash: hash,
        oldValue: priceBefore.toString(),
      });
    } else {
      const delta = priceAfter > priceBefore
        ? priceAfter - priceBefore
        : priceBefore - priceAfter;
      log.info('Composite updated', {
        txHash: hash,
        oldValue: priceBefore.toString(),
        newValue: priceAfter.toString(),
        delta: delta.toString(),
      });
    }
  } catch (e) {
    log.error('Composite update failed', { error: (e as Error).message });
  }
}

export async function startSubIndexFinalizer() {
  log.info('Sub-index finalizer starting', {
    intervalMs: config.subIndexIntervalMs,
  });

  try {
    await runOnce();
  } catch (e) {
    log.error('Initial sub-index finalization failed', {
      error: (e as Error).message,
    });
  }

  setInterval(async () => {
    try {
      await runOnce();
    } catch (e) {
      log.error('Sub-index finalization cycle failed', {
        error: (e as Error).message,
      });
    }
  }, config.subIndexIntervalMs);
}
