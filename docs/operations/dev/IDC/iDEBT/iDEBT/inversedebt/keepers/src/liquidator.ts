/**
 * Liquidator Keeper
 *
 * The economic watchdog of the DELTAVERSE stack. Scans for positions
 * that have become undercollateralized in either the CrossCollateralVault
 * or the PerpetualEngine and liquidates them to capture the liquidation
 * bonus.
 *
 * Why this is different from the other three keepers:
 *
 *   The Pyth updater, sub-index finalizer, and fee router are all doing
 *   maintenance work on behalf of the protocol. They benefit users
 *   collectively by keeping the infrastructure running, but nobody pays
 *   them directly (the keeper operator just pays gas and is expected to
 *   run the bot as a public good, possibly funded by protocol treasury).
 *
 *   The liquidator, by contrast, is economically self-funding. Every
 *   successful liquidation pays a bonus: 5% on seized collateral in the
 *   vault, and 1% + 0.5% insurance fee in the perp engine. At meaningful
 *   scale, running a liquidator is a profit center, not a cost center.
 *
 * Two strategies coexist in this keeper:
 *
 *   Strategy 1: PerpetualEngine liquidation.
 *     The perp engine exposes isLiquidatable(trader) as a view function.
 *     We scan a watchlist of known traders (populated from
 *     PositionOpened events in the real system; hardcoded here for
 *     simplicity), check isLiquidatable for each, and call liquidate()
 *     on any that return true.
 *
 *   Strategy 2: CrossCollateralVault liquidation.
 *     The vault exposes healthFactor(user) returning a value scaled to
 *     1e18 where values below 1e18 are liquidatable. We check health
 *     factors on known vault depositors and call liquidate() with a
 *     chosen repay amount (respecting the close factor cap of 50%).
 *
 * In production the watchlist would be maintained by subscribing to
 * the OpenPosition / Deposited events via webhooks or a subgraph. This
 * implementation uses a placeholder watchlist for illustration.
 */

import { parseAbi, type Address } from 'viem';
import { publicClient, walletClient, contracts, config, log } from './config.js';

const perpAbi = parseAbi([
  'function isLiquidatable(address trader) view returns (bool)',
  'function liquidate(address trader) external',
  'function getEquity(address trader) view returns (int256)',
]);

const vaultAbi = parseAbi([
  'function healthFactor(address user) view returns (uint256)',
  'function liquidate(address user, address seizeToken, uint256 repayAmount) external',
  'function getUserTotalDebt(address user) view returns (uint256)',
  'function getUserAssets(address user) view returns (address[])',
  'function getUserDeposit(address user, address token) view returns (uint256)',
]);

/**
 * A position watchlist is the set of addresses we actively monitor.
 * In production this is built by:
 *
 *   1. Subscribing to PositionOpened / Deposited events via the subgraph.
 *   2. Adding new addresses to the watchlist on each event.
 *   3. Removing addresses when PositionClosed / Withdrawn events fire.
 *
 * For this keeper skeleton we expose a simple in-memory Set that can be
 * populated manually or by a separate indexer process.
 */
const perpWatchlist = new Set<Address>();
const vaultWatchlist = new Set<Address>();

/**
 * Public API for the watchlist. In a real deployment a companion
 * indexer service would call these from event handlers.
 */
export function addPerpTrader(addr: Address) { perpWatchlist.add(addr); }
export function addVaultUser(addr: Address) { vaultWatchlist.add(addr); }
export function removePerpTrader(addr: Address) { perpWatchlist.delete(addr); }
export function removeVaultUser(addr: Address) { vaultWatchlist.delete(addr); }

/**
 * Check all perpetual positions in the watchlist and liquidate any that
 * are underwater. A liquidation here captures the liquidation bonus
 * configured in PerpetualEngine (default 1% + 0.5% insurance cut).
 */
async function scanPerpPositions() {
  for (const trader of perpWatchlist) {
    try {
      const liquidatable = await publicClient.readContract({
        address: contracts.perp,
        abi: perpAbi,
        functionName: 'isLiquidatable',
        args: [trader],
      });

      if (!liquidatable) continue;

      log.info('Liquidatable perp position found', { trader });

      // Before submitting the liquidation, simulate it to make sure it
      // will succeed at the current state. This prevents a race where
      // another liquidator beat us to it and our transaction reverts,
      // wasting gas. viem's simulateContract performs an eth_call with
      // our keeper as the caller, returning an error if the call would
      // revert.
      try {
        await publicClient.simulateContract({
          address: contracts.perp,
          abi: perpAbi,
          functionName: 'liquidate',
          args: [trader],
          account: walletClient.account,
        });
      } catch (simErr) {
        log.info('Liquidation simulation failed, skipping', {
          trader,
          error: (simErr as Error).message,
        });
        continue;
      }

      const hash = await walletClient.writeContract({
        address: contracts.perp,
        abi: perpAbi,
        functionName: 'liquidate',
        args: [trader],
      });

      const receipt = await publicClient.waitForTransactionReceipt({ hash });
      log.info('Perp position liquidated', {
        trader,
        txHash: hash,
        status: receipt.status,
      });
    } catch (e) {
      log.error('Perp liquidation attempt failed', {
        trader,
        error: (e as Error).message,
      });
    }
  }
}

/**
 * Check all vault positions in the watchlist and liquidate any that
 * are underwater. The vault is more complex than the perp because we
 * need to choose a repay amount (up to the close factor cap) and pick
 * which collateral asset to seize.
 *
 * The strategy here is: repay the maximum allowed (close factor cap
 * times total debt), and seize whichever asset the user has the largest
 * deposit of. A more sophisticated liquidator would pick the asset
 * whose oracle price is most stable to minimize slippage when the
 * seized asset is later sold on a DEX.
 */
async function scanVaultPositions() {
  for (const user of vaultWatchlist) {
    try {
      const hf = await publicClient.readContract({
        address: contracts.vault,
        abi: vaultAbi,
        functionName: 'healthFactor',
        args: [user],
      });

      // healthFactor is scaled to 1e18 where >= 1e18 is healthy.
      if (hf >= 10n ** 18n) continue;

      log.info('Liquidatable vault position found', {
        user,
        healthFactor: hf.toString(),
      });

      // Pick a seize token by looking at the user's deposited assets.
      const assets = await publicClient.readContract({
        address: contracts.vault,
        abi: vaultAbi,
        functionName: 'getUserAssets',
        args: [user],
      });

      if (assets.length === 0) continue;

      // Pick the asset with the largest deposit.
      let bestAsset: Address = assets[0];
      let bestAmount = 0n;
      for (const asset of assets) {
        const deposit = await publicClient.readContract({
          address: contracts.vault,
          abi: vaultAbi,
          functionName: 'getUserDeposit',
          args: [user, asset],
        });
        if (deposit > bestAmount) {
          bestAmount = deposit;
          bestAsset = asset;
        }
      }

      // Get total debt and compute max repay under the 50% close factor.
      const totalDebt = await publicClient.readContract({
        address: contracts.vault,
        abi: vaultAbi,
        functionName: 'getUserTotalDebt',
        args: [user],
      });
      const maxRepay = totalDebt / 2n; // 50% close factor

      // NOTE: In production the liquidator needs stablecoin balance and
      // must have approved the vault to pull it. For this illustration
      // we assume the keeper is pre-funded and pre-approved.

      const hash = await walletClient.writeContract({
        address: contracts.vault,
        abi: vaultAbi,
        functionName: 'liquidate',
        args: [user, bestAsset, maxRepay],
      });

      log.info('Vault position liquidated', { user, txHash: hash });
    } catch (e) {
      log.error('Vault liquidation attempt failed', {
        user,
        error: (e as Error).message,
      });
    }
  }
}

async function runOnce() {
  await scanPerpPositions();
  await scanVaultPositions();
}

export async function startLiquidator() {
  log.info('Liquidator starting', {
    intervalMs: config.liquidatorIntervalMs,
    perpWatchlistSize: perpWatchlist.size,
    vaultWatchlistSize: vaultWatchlist.size,
  });

  setInterval(async () => {
    try {
      await runOnce();
    } catch (e) {
      log.error('Liquidator cycle failed', { error: (e as Error).message });
    }
  }, config.liquidatorIntervalMs);
}
