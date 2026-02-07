# DAIOReflectionToken

Reflection token (fee-on-transfer, holder rewards, wallet-to-wallet exemption) adapted for **DAIO** with corrected auto-swap behavior and admin hierarchy.

## Origin

Modified from a ShambaLuv-style reflection token (live on Polygon, liquidity not yet added). Changes ensure:

1. **Router approval** – Constructor approves the router for `type(uint256).max` so the **first** auto-swap does not revert (no need to call `updateRouter` to the same router just to set allowance).
2. **Slippage** – `amountOutMin` is based on **expected ETH out** from `router.getAmountsOut(amount, path)`, then `maxSlippage` is applied to that value. The original used the token amount as if it were ETH out, which could revert or allow bad slippage.
3. **Observability** – `SwapBackTriggered(amountIn, amountOutMin, received, routerType)` is emitted when auto-swap runs (V2 and V3).
4. **Pragma** – Single `pragma ^0.8.20` and OpenZeppelin imports (no inline OZ).
5. **DAIO admin** – Owner (can transfer to DAIO timelock); Admin for operational duties (router, thresholds). Optional one-time `adminFinalized` so admin role is fixed for DAIO.

## Auto-swap trigger

Auto-swap runs at the end of `_transferWithFees` when:

- `swapEnabled == true`
- `!inSwap`
- `balanceOf(address(this)) >= swapThreshold`

Then `_maybeSwapBack()` only actually swaps if:

- `contractBalance >= teamSwapThreshold` **or**
- `contractBalance >= liquidityThreshold`

So both `swapThreshold` and (teamSwapThreshold or liquidityThreshold) must be satisfied for a swap. Events emitted when a swap occurs: `SwapBackTriggered` and `SlippageProtectionUsed`.

## DAIO admin hierarchy

| Role   | Who        | Typical use                          |
|--------|------------|--------------------------------------|
| Owner  | Deployer   | Set admin, wallets, fees, exemptions, renounce. Can transfer ownership to **DAIO timelock**. |
| Admin  | Set by owner | Router updates, V3 router, operational params. Set to **DAIO multisig** or timelock executor. |

- `setAdmin(address)` – owner only; set once unless `adminFinalized` is false.
- `setAdminFinalized()` – owner only; locks future admin changes.
- Router/threshold changes – admin (or owner if admin not yet set).

## Build

From a Foundry workspace that has OpenZeppelin (e.g. `daio/contracts/bonding`):

```bash
cd daio/contracts/bonding
forge build --contracts ../../daio/reflection/DAIOReflectionToken.sol
```

Or add a `foundry.toml` in `daio/contracts/daio` with the same `remappings` as bonding (e.g. `@openzeppelin/contracts/=../bonding/lib/openzeppelin-contracts/contracts/`) and run `forge build` there.

## Deployment (example)

- `name_`, `symbol_`, `totalSupply_` – token metadata and supply.
- `_teamWallet`, `_liquidityWallet` – fee recipients.
- `_router` – Uniswap V2–compatible router (e.g. QuickSwap on Polygon).
- `_weth` – WETH / WPOL address.
- `reflectionBps_`, `liquidityBps_`, `teamBps_` – fee in basis points (e.g. 300, 100, 100 for 3% / 1% / 1%). Sum must be ≤ 2500 (25%).

After deploy, set admin to DAIO timelock or multisig and (optional) call `setAdminFinalized()`.

## Security notes

- **Fee-on-transfer**: `getAmountsOut` does not account for transfer fees; actual ETH out can be lower. Using `getAmountsOut` and then applying `maxSlippage` is still correct for computing a minimum acceptable ETH amount; keep `maxSlippage` conservative.
- **First swap**: Router is approved in the constructor, so the first swapback does not fail for missing allowance.
- **V3**: `_swapBackV3` uses `amountOutMinimum = 0`; for production, consider integrating a Quoter and setting a proper minimum.
