# DeployEthereum

> Tier-1 Ethereum bootstrap script: deploys all 12 bankoneth Solidity contracts, wires intra-deployment references, and grants role-based permissions in a single `forge script` invocation.

**SPDX:** Apache-2.0 | **Pragma:** ^0.8.24 | **Source:** [`DeployEthereum.s.sol`](./DeployEthereum.s.sol)

## Role in bankoneth

This is **step 1 of the deploy pipeline** documented in `docs/DEPLOYMENT.md`. It produces every Ethereum-side address that `WireCrossChain.s.sol` and `Verify.s.sol` later consume. It runs against either Ethereum mainnet or Sepolia; the mainnet path is gated by an address-reference sanity check against `docs/ADDR_REFERENCE.md` to catch the ENS Sepolia/mainnet drift the ENS docs warn about. `DeployZeroG.s.sol` runs in parallel on the 0G chain; its output address must be supplied to `WireCrossChain.s.sol` afterward.

Pipeline ordering:
1. **`DeployEthereum.s.sol`** (this script) → produces the 12 Ethereum addresses.
2. `DeployZeroG.s.sol` → produces the 0G `iNFT_7857` address (independent).
3. `WireCrossChain.s.sol` → admin txs from Treasury Safe wiring (1) ↔ (2).
4. `Verify.s.sol` → emits the `forge verify-contract` command lines.

## Required env vars

| VAR | type | secret? | purpose | example |
|---|---|---|---|---|
| `DEPLOYER_PK` | `uint256` | YES | Private key of deploy EOA. Burned for funded deploy gas. | `0xac09…` |
| `TREASURY_ADDR` | `address` | no | BANKON Treasury Safe — receives `DEFAULT_ADMIN_ROLE` on every deployed contract, plus royalty / oracle / treasury roles. | `0xBANK…` |
| `NAME_WRAPPER_ADDR` | `address` | no | ENS `NameWrapper`. Mainnet: `0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401`. Sepolia: `0x0635513f…` (only allowed when `ALLOW_TESTNET=true`). | mainnet const |
| `ETH_REGISTRAR_CONTROLLER` | `address` | no | ENS `ETHRegistrarController`. Mainnet: `0x59E16fcCd424Cc24e280Be16E11Bcd56fb0CE547`. | mainnet const |
| `BANKON_ETH_NODE` | `bytes32` | no | `namehash("bankon.eth")`. Computed off-chain (e.g. via `cast namehash bankon.eth`). | `0xa15f…` |
| `WEBHOOK_URL` | `string` | partly | AgenticPlace indexer webhook URL — embedded into `BankonAgenticPlaceHook` constructor. | `https://agenticplace.pythai.net/api/listings` |
| `ALLOW_TESTNET` | `bool` (optional) | no | When `true`, skips the mainnet address-reference assert in `_verifyChainAddresses`. Required for Sepolia rehearsal. | `false` (default) |
| `SUBNAME_NODE_EXPIRY` | `uint64` (optional, declared in NatSpec but **not currently consumed** by `run()`) | no | Default expiry seconds for new bankon.eth children. | `31536000` |

## Pre-conditions

1. `DEPLOYER_PK` EOA is funded with enough ETH for the entire batch (≈12 contract creations + ≈9 role-grant txs).
2. `TREASURY_ADDR` is the **already-deployed** BANKON Treasury Safe — no Safe initialisation happens here.
3. `BANKON_ETH_NODE` resolves to a `.eth` 2LD that the deployer (or Treasury) controls in `NameWrapper` post-deploy (the script does **not** itself acquire `bankon.eth` — that has to be done out-of-band before `DeployEthereum` because `BankonSubnameRegistrar` takes it as a constructor arg).
4. Sepolia rehearsal completed successfully (Treasury-Safe sign-off pattern verified on testnet) before mainnet run.
5. `forge` and `foundry.toml` mainnet/sepolia profiles set up with `--rpc-url` env.
6. `docs/ADDR_REFERENCE.md` has been re-checked for any ENS contract migration since the constants were hard-coded into `_verifyChainAddresses`.

## Step-by-step (the `run()` function)

1. **Env read** — pulls `DEPLOYER_PK`, `TREASURY_ADDR`, `NAME_WRAPPER_ADDR`, `ETH_REGISTRAR_CONTROLLER`, `WEBHOOK_URL`.
2. **`_verifyChainAddresses(nameWrapper, ensController)`** — unless `ALLOW_TESTNET=true`, asserts both addresses equal the canonical mainnet constants embedded in the script. Reverts with `"NAME_WRAPPER_ADDR mismatch…"` or `"ETH_REGISTRAR_CONTROLLER mismatch…"`.
3. **`vm.startBroadcast(pk)`** — begins recording txs.
4. **Tier-1 economic primitives:**
   - `BankonPriceOracle(treasury)` → `d.priceOracle`
   - `BankonReputationGate(treasury)` → `d.reputationGate`
   - `BankonPaymentRouter(treasury)` → `d.paymentRouter`
5. **Identity + payments:**
   - `AgentRegistry("BANKON Agent Registry", "AGENT", treasury)` → ERC-721 ERC-8004 identity registry.
   - `X402Receipt(treasury, IBankonPaymentRouter(d.paymentRouter))` → x402 receipt token.
   - `BankonX402Attestor(treasury)` → x402 verification engine.
   - `BankonAgenticPlaceHook(treasury, webhook)` → seeds initial webhook URL.
6. **Resolver + iNFT adapter** (chicken-and-egg — resolver is constructed with `address(0)` adapter, adapter is constructed pointing at the live resolver, then `setInftAdapter` patches the resolver):
   - `BankonSubnameResolver(treasury, IBankonInftAdapter(address(0)))`
   - `BankonInftAdapter(treasury, IBankonSubnameResolver(d.resolver))`
   - `resolver.setInftAdapter(adapter)` → wires the back-reference.
7. **`BankonSubnameRegistrar`** — note: **takes plain `address`es, not interface types** (this trips refactors). Constructor arg order: `(nameWrapper, defaultResolver, parentNode, paymentRouter, priceOracle, reputationGate, identityRegistry8004, admin)`. `parentNode` is read here via `vm.envBytes32("BANKON_ETH_NODE")` — the only env read inside the broadcast block.
8. **`BankonEthRegistrar`** — wraps ENS `ETHRegistrarController` with BANKON pricing + payment routing + x402 attestation.
9. **`BankonDomainHosting`** — accepts third-party `.eth` parents into the BANKON subname hosting market.
10. **Role grants** (cross-contract authorization wiring, all signed by `DEPLOYER_PK` because every contract sets admin = `treasury`, but the deployer holds these new contracts' admin via constructor only if treasury == deployer — **this works because `grantRegistrar` etc. are gated on `DEFAULT_ADMIN_ROLE` which constructor assigns to `treasury`, so this `vm.startBroadcast(pk)` block silently assumes `pk == treasury` — see Failure modes**):
    - `resolver.grantRegistrar(subnameRegistrar)`
    - `resolver.grantRegistrar(domainHosting)`
    - `inftAdapter.grantRegistrar(subnameRegistrar)`
    - `agenticPlaceHook.grantLister(subnameRegistrar)`
    - `agenticPlaceHook.grantLister(ethRegistrar)`
    - `agenticPlaceHook.grantLister(domainHosting)`
    - `x402Attestor.grantConsumer(subnameRegistrar)`
    - `x402Attestor.grantConsumer(ethRegistrar)`
    - `x402Attestor.grantConsumer(domainHosting)`
11. **`vm.stopBroadcast()`**
12. **Console log** — emits every deployed address (12 contracts). Operator pipes to `tee` and persists for `WireCrossChain` env.

## Post-conditions

After a successful run:
- All 12 contracts are deployed and their addresses are returned as a `Deployed` struct (Foundry script return value, captured in broadcast JSON at `broadcast/DeployEthereum.s.sol/<chainId>/run-latest.json`).
- `DEFAULT_ADMIN_ROLE` on every contract is held by `TREASURY_ADDR`.
- Cross-contract role grants are in place — the registrar can mint subnames, write resolver records, request iNFT mints, list to AgenticPlace, and consume x402 receipts without further admin txs.
- The resolver / adapter back-reference is wired (i.e. `resolver.inftAdapter() != address(0)`).

Downstream consumers:
- `WireCrossChain.s.sol` consumes `INFT_ADAPTER_ADDR`, `X402_ATTESTOR_ADDR`, `AGENTICPLACE_HOOK_ADDR` from the broadcast log.
- `Verify.s.sol` consumes every deployed address for Etherscan / Sourcify verification command emission.

## Failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `"NAME_WRAPPER_ADDR mismatch"` or `"ETH_REGISTRAR_CONTROLLER mismatch"` | Sepolia addresses passed without `ALLOW_TESTNET=true`. Or ENS migrated the controller since this script was written. | Set `ALLOW_TESTNET=true` for rehearsal, or update the hard-coded mainnet constants after verifying `docs/ADDR_REFERENCE.md`. |
| `AccessControlUnauthorizedAccount` on any `grantRegistrar` / `grantLister` / `grantConsumer` | `DEPLOYER_PK` EOA address ≠ `TREASURY_ADDR`. Constructor assigned admin to `treasury`, not the broadcaster. | Run the deploy from the Treasury Safe (Safe-Tx via Foundry batch), OR set `treasury = vm.addr(pk)` for rehearsal then transfer admin out-of-band. |
| `OutOfGas` mid-broadcast | Deployer EOA underfunded for 12 creations + 9 admin txs. | Top up — typical bytecode total is large; gas-price spikes during mainnet runs are real. |
| Resolver / adapter `addr(node)` reverts after deploy | `resolver.setInftAdapter(adapter)` was skipped (e.g. revert mid-script). | Re-broadcast the missing tx manually with `cast send`. |
| `BANKON_ETH_NODE` doesn't actually correspond to `bankon.eth` | Off-chain namehash typo, or the .eth wasn't registered. | Recompute with `cast namehash bankon.eth`; re-register via `BankonEthRegistrar` first. |

## Verification

After broadcast:
```bash
# Confirm bytecode at each address (use Etherscan, or cast)
cast code $SUBNAME_REGISTRAR_ADDR | head -c 40
# Confirm role wiring (should return true for each registrar address)
cast call $RESOLVER_ADDR "hasRole(bytes32,address)(bool)" \
  $(cast keccak "REGISTRAR_ROLE") $SUBNAME_REGISTRAR_ADDR
# Sanity: resolver's adapter back-ref must be the deployed adapter
cast call $RESOLVER_ADDR "inftAdapter()(address)"
```
Then proceed to `Verify.s.sol` for Etherscan source verification.

## Reverting

**Not reversible.** Every contract has `DEFAULT_ADMIN_ROLE` on Treasury Safe — pause + role-revoke is the only mitigation. To "redeploy clean": deploy new instances and update any off-chain references (subgraph, gateway voucher signer config, `agenticplace.pythai.net` indexer). Old contracts remain on-chain forever; the only recovery is to make them administratively dormant.

## See also

- [`DeployZeroG.s.md`](./DeployZeroG.s.md) — parallel deploy on 0G Galileo.
- [`WireCrossChain.s.md`](./WireCrossChain.s.md) — post-deploy admin wiring.
- [`Verify.s.md`](./Verify.s.md) — Etherscan/Sourcify verification driver.
- `docs/DEPLOYMENT.md` — full operator runbook.
- `docs/ADDR_REFERENCE.md` — canonical mainnet ENS addresses.
- `contracts/BankonSubnameRegistrar.sol` — the core registrar this deploys.
