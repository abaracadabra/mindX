# WireCrossChain

> Post-deploy admin transactions, executed by the BANKON Treasury Safe on the Ethereum side, that wire all cross-chain references which can only be known after both `DeployEthereum.s.sol` and `DeployZeroG.s.sol` have completed.

**SPDX:** Apache-2.0 | **Pragma:** ^0.8.24 | **Source:** [`WireCrossChain.s.sol`](./WireCrossChain.s.sol)

## Role in bankoneth

Step 3 of the deploy pipeline. Where `DeployEthereum` covers what's knowable at Ethereum-deploy-time and `DeployZeroG` covers 0G, this script bridges them: it tells the Ethereum-side `BankonInftAdapter` where the 0G iNFT lives, registers the x402 facilitator pubkey, and sets the AgenticPlace webhook (which `DeployEthereum` already seeded — this is the post-deploy rotation hook).

Pipeline ordering:
1. `DeployEthereum.s.sol`.
2. `DeployZeroG.s.sol`.
3. **`WireCrossChain.s.sol`** (this script).
4. `Verify.s.sol`.

It is **Treasury-Safe-signed** in production — the `TREASURY_PK` env var stands in for that signature path during rehearsal.

## Required env vars

| VAR | type | secret? | purpose | example |
|---|---|---|---|---|
| `TREASURY_PK` | `uint256` | YES | Treasury Safe operator key (rehearsal) or a simulated-EOA holding `DEFAULT_ADMIN_ROLE` on the three target contracts. Production runs this as a Safe batch. | `0xac09…` |
| `INFT_ADAPTER_ADDR` | `address` | no | `BankonInftAdapter` from `DeployEthereum` broadcast log. | `0xADAP…` |
| `X402_ATTESTOR_ADDR` | `address` | no | `BankonX402Attestor` from `DeployEthereum` broadcast log. | `0xATTE…` |
| `AGENTICPLACE_HOOK_ADDR` | `address` | no | `BankonAgenticPlaceHook` from `DeployEthereum` broadcast log. | `0xH00K…` |
| `ZEROG_INFT_ADDR` | `address` | no | `iNFT_7857` from `DeployZeroG` broadcast log. | `0x1NFT…` |
| `ZEROG_CHAIN_ID` | `uint256` | no | `16601` for Galileo testnet, or the 0G mainnet chain id. | `16601` |
| `ERC6551_IMPL_ADDR` | `address` | no | ERC-6551 token-bound account implementation address (canonical: `0x41C8…f3eC` on most chains — operator confirms). | `0x41C8…` |
| `X402_FACILITATOR_ADDR` | `address` | no | GoPlausible or self-hosted x402 facilitator's signing EOA. | `0xFAC1…` |
| `AGENTICPLACE_WEBHOOK_URL` | `string` | partly | `agenticplace.pythai.net` indexer webhook URL (production: `https://agenticplace.pythai.net/api/listings`). | URL |

## Pre-conditions

1. `DeployEthereum.s.sol` succeeded; its four addresses (`INFT_ADAPTER_ADDR`, `X402_ATTESTOR_ADDR`, `AGENTICPLACE_HOOK_ADDR` — plus the unused-here `RESOLVER_ADDR`) are recorded.
2. `DeployZeroG.s.sol` succeeded; `ZEROG_INFT_ADDR` is recorded.
3. `TREASURY_PK` corresponds to `TREASURY_ADDR` from `DeployEthereum` (it holds `DEFAULT_ADMIN_ROLE` on all three target contracts).
4. The x402 facilitator EOA (`X402_FACILITATOR_ADDR`) is the one that will sign x402 receipts that `BankonX402Attestor.verify(...)` will validate — its pubkey must be the one the facilitator service actually uses, not a placeholder.
5. ERC-6551 implementation has been deployed on Ethereum (this script does NOT deploy it — it's typically a once-per-chain ERC-6551 reference impl).

## Step-by-step (the `run()` function)

1. **Env read** — all 8 vars (1 PK + 6 addresses + 1 uint + 1 string).
2. **`vm.startBroadcast(pk)`**.
3. **`BankonInftAdapter.setZeroGiNFTContract(zeroGiNFT, zeroGChainId)`** — burns the cross-chain pointer into adapter storage. Subsequent `requestMint` calls will reference these.
4. **`BankonInftAdapter.setErc6551Implementation(erc6551Impl)`** — required so `tbaAddressOf(label)` can derive deterministic TBA addresses (CREATE2 with the impl as salt input).
5. **`BankonX402Attestor.setFacilitator(facilitator, true)`** — adds the facilitator EOA to the registered-facilitator set. `verify()` rejects receipts signed by any address not in this set.
6. **`BankonAgenticPlaceHook.setWebhookURL(webhook)`** — rotates the webhook URL set at construction-time by `DeployEthereum`. Useful for switching staging→prod, or rotating after URL change.
7. **`vm.stopBroadcast()`**.
8. **Console log** — prints every value written, for the audit trail.

## Post-conditions

- `inftAdapter.zeroGiNFTContract == zeroGiNFT` and `inftAdapter.zeroGChainId == zeroGChainId`.
- `inftAdapter.erc6551Implementation == erc6551Impl`.
- `x402Attestor.facilitators(facilitator) == true`.
- `agenticPlaceHook.webhookURL() == webhook`.
- Mode-A iNFT flow is fully usable end-to-end: registrar can call `adapter.requestMint(...)` → adapter knows where on 0G the iNFT will be minted → off-chain wirer reports back via `adapter.registerZeroGTokenId(...)` → resolver flips `addr(node)` to TBA.

## Failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `AccessControlUnauthorizedAccount` on `setZeroGiNFTContract` | `TREASURY_PK` doesn't hold admin on `BankonInftAdapter`. Probably ran `DeployEthereum` with a different treasury. | Re-grant admin from current admin, or re-deploy with correct treasury. |
| `ERC6551_IMPL_ADDR` has no code | ERC-6551 reference impl not deployed on this chain. | Deploy it first (one-shot, well-known bytecode), then re-run. |
| x402 receipts later rejected with `FacilitatorNotRegistered` | Wrong `X402_FACILITATOR_ADDR` — typically the facilitator's *operator* EOA was passed instead of its *signing* EOA. | Get the signing EOA from the facilitator operator and re-call `setFacilitator(...)`. |
| Webhook never receives listings | URL typo, DNS hadn't propagated, or webhook service down. | Verify via `cast call $HOOK_ADDR "webhookURL()(string)"`, ping URL manually. |

## Verification

```bash
cast call $INFT_ADAPTER_ADDR "zeroGiNFTContract()(address)"
cast call $INFT_ADAPTER_ADDR "zeroGChainId()(uint256)"
cast call $INFT_ADAPTER_ADDR "erc6551Implementation()(address)"
# Verify facilitator entry
cast call $X402_ATTESTOR_ADDR "facilitators(address)(bool)" $X402_FACILITATOR_ADDR
# Verify webhook
cast call $AGENTICPLACE_HOOK_ADDR "webhookURL()(string)"
```
Then run the end-to-end test in `test/BankonEndToEnd.t.sol` against a fork of mainnet (forked tests for cross-chain pointers are static — they only validate the Ethereum-side wiring).

## Reverting

Each setter is admin-callable, so Treasury Safe can re-call:
- `setZeroGiNFTContract(address(0), 0)` — disables iNFT minting on the adapter (adapter still recordkeeps existing bindings).
- `setFacilitator(addr, false)` — revokes a compromised facilitator.
- `setWebhookURL("")` — silences AgenticPlace listings until rotated.

These are operational rollbacks, not full reverts. Old bound tokenIds remain.

## See also

- [`DeployEthereum.s.md`](./DeployEthereum.s.md) — produces the Ethereum-side targets.
- [`DeployZeroG.s.md`](./DeployZeroG.s.md) — produces `ZEROG_INFT_ADDR`.
- [`Verify.s.md`](./Verify.s.md) — next script.
- `test/BankonEndToEnd.t.sol` — exercises the post-wire Mode-A flow.
- `contracts/BankonInftAdapter.sol` — receives `setZeroGiNFTContract` / `setErc6551Implementation`.
- `contracts/BankonX402Attestor.sol` — receives `setFacilitator`.
- `contracts/BankonAgenticPlaceHook.sol` — receives `setWebhookURL`.
- `docs/INFT_MODE_A.md` — the cross-chain pointer architecture.
