# DeployZeroG

> Deploys the ERC-7857 `iNFT_7857` "Bankon Agent NFT" contract on the 0G Galileo testnet (chain `16601`) or 0G mainnet.

**SPDX:** Apache-2.0 | **Pragma:** ^0.8.24 | **Source:** [`DeployZeroG.s.sol`](./DeployZeroG.s.sol)

## Role in bankoneth

This is the **0G-side** counterpart to `DeployEthereum.s.sol`. The bankoneth iNFT design (Mode A) requires a sovereign iNFT token contract on a sovereign chain (0G) so that:
- The on-chain identity NFT lives where compute / data sovereignty rules of 0G apply.
- The Ethereum-side `BankonInftAdapter` only stores a cross-chain pointer (`zeroGChainId`, `zeroGiNFTContract`, `tokenId`) — it does not custody the iNFT itself.

Pipeline ordering:
1. `DeployEthereum.s.sol` (any order vs this).
2. **`DeployZeroG.s.sol`** (this script) — emits the 0G iNFT address.
3. `WireCrossChain.s.sol` — uses `ZEROG_INFT_ADDR` (the address printed here) to wire `BankonInftAdapter.setZeroGiNFTContract(...)`.

## Required env vars

| VAR | type | secret? | purpose | example |
|---|---|---|---|---|
| `DEPLOYER_PK` | `uint256` | YES | Private key of deploy EOA. Holds enough 0G native token (currently $0G testnet faucet) to fund creation. | `0xac09…` |
| `TREASURY_ADDR` | `address` | no | Receives `admin`, `royaltyReceiver`, `oracle`, and `treasury` roles at bootstrap. Bridge-worker minter role is granted out-of-band later. | `0xBANK…` |

## Pre-conditions

1. `FOUNDRY_PROFILE=zerog` is set so the `[profile.zerog]` section in `foundry.toml` (which pins the EVM version / fork that matches 0G Galileo) is active.
2. `--rpc-url $ZEROG_RPC` is passed to `forge script` — typical Galileo RPC: `https://evmrpc-testnet.0g.ai`.
3. `DEPLOYER_PK` is funded with sufficient 0G native token. Faucet on Galileo if testnet.
4. `TREASURY_ADDR` exists (no on-chain validation — pure storage assignment).

## Step-by-step (the `run()` function)

1. **Env read** — `DEPLOYER_PK`, `TREASURY_ADDR`.
2. **`vm.startBroadcast(pk)`**.
3. **Deploy `iNFT_7857`** with constructor args:
   - `name_ = "Bankon Agent NFT"`
   - `symbol_ = "BAGENT"`
   - `admin = treasury`
   - `royaltyReceiver = treasury`
   - `royaltyFeeBps = 500` → 5.00% (ERC-2981).
   - `oracle_ = treasury` (bootstrap; rotated to real oracle EOA via admin tx later).
   - `treasury_ = treasury` (clone-fee receipts).
   - `cloneFeeWei_ = 0` (cloning disabled at launch).
4. **`vm.stopBroadcast()`**.
5. **Console log** — prints deployed address + `block.chainid` + the literal next-step instruction.

## Post-conditions

- One ERC-7857 contract live at the printed address on 0G.
- Treasury holds every role (admin / royalty / oracle / treasury).
- Cloning is economically disabled (`cloneFeeWei == 0` + no clone-flag gating in this script — actual clone gating is in `iNFT_7857.sol`).
- Address is captured by the operator (via `tee` or broadcast JSON) for use as `ZEROG_INFT_ADDR` in `WireCrossChain`.

## Failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `out of gas` / `intrinsic gas too low` | 0G RPC has surprisingly low default block gas limit, or wrong `--gas-limit` flag. | Pass `--gas-limit 6000000` to `forge script`. |
| `nonce too low` | Re-run after partial broadcast — Foundry's local nonce drifted. | `cast nonce` to confirm, then `--slow` / wait and retry. |
| `unsupported opcode` | `FOUNDRY_PROFILE` not set to `zerog`, so default `paris` evm spec emitted opcodes 0G hasn't enabled. | `FOUNDRY_PROFILE=zerog forge script …` |
| Treasury address typo | No validation — the contract just stores whatever address you pass. | Verify with `cast call $INFT_ADDR "owner()(address)"` and `"royaltyInfo(uint256,uint256)(address,uint256)"` post-deploy. |

## Verification

```bash
# Pull the deployed address from console log; then:
cast call $INFT_ADDR "name()(string)"          # → "Bankon Agent NFT"
cast call $INFT_ADDR "symbol()(string)"        # → "BAGENT"
cast call $INFT_ADDR "owner()(address)"        # → $TREASURY_ADDR (or DEFAULT_ADMIN_ROLE holder)
cast call $INFT_ADDR "cloneFeeWei()(uint256)"  # → 0
```
0G has its own block explorer — submit source for verification per `docs/DEPLOYMENT.md`.

## Reverting

**Not reversible** — the iNFT contract is sovereign on 0G. To deploy a new instance, re-run, then update `ZEROG_INFT_ADDR` in `WireCrossChain` env. Existing tokenId↔labelhash bindings inside the Ethereum-side `BankonInftAdapter` would have to be re-wired by Treasury Safe; old iNFT contract becomes orphaned but lives on.

## See also

- [`DeployEthereum.s.md`](./DeployEthereum.s.md) — Ethereum-side deploy producing the adapter that points here.
- [`WireCrossChain.s.md`](./WireCrossChain.s.md) — consumes the printed 0G iNFT address.
- `contracts/inft/iNFT_7857.sol` — ERC-7857 implementation deployed by this script.
- `docs/INFT_MODE_A.md` — Mode-A iNFT architecture: how the cross-chain pointer flow works.
- `docs/DEPLOYMENT.md` — operator runbook.
