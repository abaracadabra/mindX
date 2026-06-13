/**
 * Fee Router Keeper
 *
 * Watches the pendingFees counter on DebtInheritanceProtocol and calls
 * routeFees() when it crosses a gas-profitable threshold. This is what
 * closes the economic loop between traders and LP stakers: traders pay
 * fees on mint/burn/trading, fees accumulate in the protocol, this
 * keeper periodically routes them to the oracle's LP staking pool, and
 * stakers earn rewards pro-rata.
 *
 * The economics of this keeper are straightforward. Calling routeFees()
 * costs some amount of gas (roughly 100k gas units, mostly for the
 * depositRewards call on the oracle). At current prices on mainnet this
 * is a few dollars. We should only route when the amount being routed
 * is at least several times the gas cost, otherwise the routing is
 * itself a net drain on the protocol.
 *
 * The default threshold is 100 USDC, which gives a comfortable margin
 * even at elevated gas prices. On cheaper L2s the threshold can be
 * lowered dramatically.
 *
 * Anyone can call routeFees() — it is not a privileged operation. That
 * means in principle anyone can run this keeper, and the protocol has
 * a natural redundancy: if the official keeper goes down, any LP staker
 * with a wallet can call the function to receive their share. The
 * official keeper just ensures this happens predictably.
 */

import { parseAbi } from 'viem';
import { publicClient, walletClient, contracts, config, log } from './config.js';

const protocolAbi = parseAbi([
  'function pendingFees() view returns (uint256)',
  'function routeFees() external',
]);

async function runOnce() {
  const pending = await publicClient.readContract({
    address: contracts.protocol,
    abi: protocolAbi,
    functionName: 'pendingFees',
  });

  if (pending < config.feeRouteThreshold) {
    log.info('Pending fees below routing threshold', {
      pending: pending.toString(),
      threshold: config.feeRouteThreshold.toString(),
    });
    return;
  }

  // Check gas price before committing.
  const gasPrice = await publicClient.getGasPrice();
  if (gasPrice > config.maxGasPriceWei) {
    log.warn('Gas price too high for fee routing', {
      current: gasPrice.toString(),
      max: config.maxGasPriceWei.toString(),
    });
    return;
  }

  log.info('Routing fees', { amount: pending.toString() });

  const hash = await walletClient.writeContract({
    address: contracts.protocol,
    abi: protocolAbi,
    functionName: 'routeFees',
  });

  const receipt = await publicClient.waitForTransactionReceipt({ hash });
  if (receipt.status === 'success') {
    log.info('Fees routed successfully', {
      txHash: hash,
      amount: pending.toString(),
      gasUsed: receipt.gasUsed.toString(),
    });
  } else {
    log.error('Fee routing reverted', { txHash: hash });
  }
}

export async function startFeeRouter() {
  log.info('Fee router starting', {
    intervalMs: config.feeRouterIntervalMs,
    threshold: config.feeRouteThreshold.toString(),
  });

  setInterval(async () => {
    try {
      await runOnce();
    } catch (e) {
      log.error('Fee routing cycle failed', { error: (e as Error).message });
    }
  }, config.feeRouterIntervalMs);
}
