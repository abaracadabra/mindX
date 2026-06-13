/**
 * DELTAVERSE Keeper — Main Entry Point
 *
 * Starts all four keeper bots concurrently. Each bot runs on its own
 * interval and does not depend on the others, so they can be deployed
 * together in a single process or split across multiple containers
 * for isolation.
 *
 * Environment variables toggle which keepers are active, which is
 * useful when testing or when different chains need different keepers
 * (for example, the liquidator might run on all chains, but a
 * high-frequency Pyth updater might only run on chains with active
 * trading volume).
 *
 * To run all keepers in one process:
 *   pnpm start
 *
 * To run only specific keepers, set the enable flags:
 *   ENABLE_PYTH=true ENABLE_FEE_ROUTER=true pnpm start
 */

import { startPythUpdater } from './pythUpdater.js';
import { startSubIndexFinalizer } from './subIndexFinalizer.js';
import { startFeeRouter } from './feeRouter.js';
import { startLiquidator } from './liquidator.js';
import { log, keeperAddress, chainId, contracts } from './config.js';

async function main() {
  log.info('==========================================');
  log.info('DELTAVERSE KEEPER STARTING');
  log.info('==========================================');
  log.info('Keeper identity', {
    address: keeperAddress,
    chainId,
    contracts,
  });

  // Default to running all keepers unless explicitly disabled.
  // Using "!== 'false'" rather than "=== 'true'" means the default is
  // enabled, which is the safer default for a keeper — accidentally
  // leaving something off is worse than accidentally leaving it on.
  const enablePyth       = process.env.ENABLE_PYTH       !== 'false';
  const enableSubIndex   = process.env.ENABLE_SUB_INDEX  !== 'false';
  const enableFeeRouter  = process.env.ENABLE_FEE_ROUTER !== 'false';
  const enableLiquidator = process.env.ENABLE_LIQUIDATOR !== 'false';

  const starts: Promise<void>[] = [];

  if (enablePyth)       starts.push(startPythUpdater());
  if (enableSubIndex)   starts.push(startSubIndexFinalizer());
  if (enableFeeRouter)  starts.push(startFeeRouter());
  if (enableLiquidator) starts.push(startLiquidator());

  if (starts.length === 0) {
    log.error('No keepers enabled; exiting');
    process.exit(1);
  }

  // Each start function sets up its own setInterval and resolves
  // immediately. We await all of them in parallel so that any startup
  // error in any single keeper propagates up to the process level.
  await Promise.all(starts);

  log.info('All enabled keepers started successfully', {
    enabled: {
      pyth: enablePyth,
      subIndex: enableSubIndex,
      feeRouter: enableFeeRouter,
      liquidator: enableLiquidator,
    },
  });

  // Keep the process alive. Without this line, the main function returns
  // after Promise.all resolves, but all the setIntervals keep running
  // because Node's event loop stays active as long as there are pending
  // timers. This is correct behavior; the explicit comment is for any
  // reader who might think the process is about to exit.
}

/**
 * Graceful shutdown handler. On SIGTERM (Docker stop, Kubernetes
 * termination, systemd reload), log the shutdown and give the event
 * loop a moment to drain in-flight requests before exiting. Without
 * this handler, SIGTERM causes an immediate exit which can leave
 * transactions in flight without logged outcomes.
 */
process.on('SIGTERM', () => {
  log.info('SIGTERM received, shutting down gracefully');
  setTimeout(() => process.exit(0), 2000);
});

process.on('SIGINT', () => {
  log.info('SIGINT received, shutting down gracefully');
  setTimeout(() => process.exit(0), 2000);
});

// Top-level error handler. If any startup error bubbles up to here,
// log it and exit with a non-zero code so the container orchestrator
// knows to restart the keeper.
main().catch(err => {
  log.error('Fatal error during startup', { error: err.message, stack: err.stack });
  process.exit(1);
});
