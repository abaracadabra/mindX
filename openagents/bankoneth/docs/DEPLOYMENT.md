# bankoneth — Deployment Runbook

End-to-end mainnet deploy. Read [`ADDR_REFERENCE.md`](ADDR_REFERENCE.md) first
to confirm the canonical ENS addresses against
[`docs.ens.domains/learn/deployments`](https://docs.ens.domains/learn/deployments).
The ENS docs distinguish Sepolia vs mainnet sloppily; mistake one for the
other and the deploy bricks.

## Prerequisites

| Item | Detail |
|---|---|
| Foundry | Latest stable; `forge --version` ≥ 0.2.0 |
| pnpm + Node | pnpm ≥ 9, Node ≥ 20.10 |
| BANKON Treasury Safe | Gnosis Safe, 2-of-3 minimum, on Ethereum mainnet |
| 0G operator wallet | Funded on 0G Galileo + 0G mainnet |
| x402-avm facilitator | GoPlausible-hosted or self-hosted; pubkey held by Treasury |
| ENS `bankon.eth` | Owned + wrapped + `CANNOT_UNWRAP` burned by Treasury Safe |
| RPC endpoints | `MAINNET_RPC`, `SEPOLIA_RPC`, `ZEROG_RPC`, `BASE_RPC` |
| Etherscan API key | `ETHERSCAN_API_KEY` |

## Phase 1 — Sepolia rehearsal

```bash
export DEPLOYER_PK=0x...                              # rehearsal-only key
export TREASURY_ADDR=0x...                            # Sepolia Safe
export NAME_WRAPPER_ADDR=0x0635513f179D50A207757E05759CbD106d7dFcE8
export ETH_REGISTRAR_CONTROLLER=0xfb3cE5D01e0f33f41DbB39035dB9745962F1f968
export BANKON_ETH_NODE=$(cast namehash bankon.eth)
export WEBHOOK_URL=https://staging.agenticplace.pythai.net/api/listings
export ALLOW_TESTNET=true                              # disables mainnet-addr check

forge build
forge script script/DeployEthereum.s.sol --rpc-url $SEPOLIA_RPC --broadcast --verify
```

Then deploy the 0G side (Galileo testnet `16601`):

```bash
FOUNDRY_PROFILE=zerog forge script script/DeployZeroG.s.sol \
  --rpc-url $ZEROG_RPC --broadcast
```

Run `WireCrossChain` from the Treasury Safe operator key:

```bash
export TREASURY_PK=0x...
export INFT_ADAPTER_ADDR=0x...                  # from DeployEthereum output
export X402_ATTESTOR_ADDR=0x...
export AGENTICPLACE_HOOK_ADDR=0x...
export ZEROG_INFT_ADDR=0x...                    # from DeployZeroG output
export ZEROG_CHAIN_ID=16601
export ERC6551_IMPL_ADDR=0x...
export X402_FACILITATOR_ADDR=0x...
export AGENTICPLACE_WEBHOOK_URL=https://staging.agenticplace.pythai.net/api/listings

forge script script/WireCrossChain.s.sol --rpc-url $SEPOLIA_RPC --broadcast
```

Smoke-test:

```bash
forge test --fork-url $SEPOLIA_RPC -vv
```

## Phase 2 — Mainnet

Same as Sepolia rehearsal **without** `ALLOW_TESTNET=true`. The
`DeployEthereum` script's `_verifyChainAddresses` asserts:

- `NAME_WRAPPER_ADDR == 0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401`
- `ETH_REGISTRAR_CONTROLLER == 0x59E16fcCd424Cc24e280Be16E11Bcd56fb0CE547`

If you have the Sepolia addresses in your env, the deploy reverts before
sending any tx. **This is the most common failure mode** — the ENS docs
linked sloppy addresses for a long time; double-check against
[`ADDR_REFERENCE.md`](ADDR_REFERENCE.md).

## Phase 3 — Post-deploy

1. Verify contracts: `forge script script/Verify.s.sol` prints the
   `forge verify-contract` commands; run them against Etherscan + Sourcify
   for Ethereum mainnet and the 0G explorer for the iNFT.
2. Hand `DEFAULT_ADMIN_ROLE` from the deployer EOA to the Treasury Safe on
   every contract that received it during deploy.
3. Configure the price oracle (Chainlink ETH/USD feed address, fallback rate).
4. Configure the reputation gate (BONAFIDE / PYTHAI stake registry addresses).
5. Configure the payment router buckets (5 recipient addresses + bps).
6. Approve the Treasury Safe as the `bankon.eth` operator on the NameWrapper
   (so `BankonSubnameRegistrar` can mint subnames under it).
7. Smoke-claim `test-001.bankon.eth` via the CLI; assert the resolver returns
   the TBA address via the iNFT Mode A path.

## Rollback

Pause every Flow registrar via Treasury Safe — they expose `pause()`
guarded by `DEFAULT_ADMIN_ROLE`. New claims revert; existing subnames
stay live (NameWrapper fuses are immutable; the parent-lock guarantee
holds even if bankoneth is paused).

## Operator monitoring

- The `RequestINFTMint` event on `BankonInftAdapter` — the 0G worker should
  process every emit within minutes.
- The `ReceiptConsumed` event on `BankonX402Attestor` — facilitator activity.
- The `AgenticPlaceListing` event on `BankonAgenticPlaceHook` — indexer webhook health.
- Etherscan watch on the Treasury Safe + the Flow registrars.
