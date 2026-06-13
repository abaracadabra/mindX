# Verify

> Etherscan + Sourcify + 0G explorer verification driver — emits `forge verify-contract` command lines to stdout for each deployed contract; the operator runs them.

**SPDX:** Apache-2.0 | **Pragma:** ^0.8.24 | **Source:** [`Verify.s.sol`](./Verify.s.sol)

## Role in bankoneth

Step 4 of the deploy pipeline. Unlike the previous three scripts, this does **not** broadcast any transactions. Its sole job is to print the canonical `forge verify-contract` command lines so operators don't typo constructor-args or path strings under deploy-day pressure. The actual verification calls (which require operator-held API keys) live in `docs/DEPLOYMENT.md`.

Pipeline ordering:
1. `DeployEthereum.s.sol`.
2. `DeployZeroG.s.sol`.
3. `WireCrossChain.s.sol`.
4. **`Verify.s.sol`** (this script).

## Required env vars

All addresses come from the previous deploy scripts' broadcast logs.

| VAR | type | secret? | purpose | example |
|---|---|---|---|---|
| `SUBNAME_REGISTRAR_ADDR` | `address` | no | `BankonSubnameRegistrar` from `DeployEthereum`. | `0xREG1…` |
| `ETH_REGISTRAR_ADDR` | `address` | no | `BankonEthRegistrar`. | `0xREG2…` |
| `DOMAIN_HOSTING_ADDR` | `address` | no | `BankonDomainHosting`. | `0xH0ST…` |
| `RESOLVER_ADDR` | `address` | no | `BankonSubnameResolver`. | `0xRES0…` |
| `INFT_ADAPTER_ADDR` | `address` | no | `BankonInftAdapter`. | `0xADAP…` |
| `X402_ATTESTOR_ADDR` | `address` | no | `BankonX402Attestor`. | `0xATTE…` |
| `AGENTICPLACE_HOOK_ADDR` | `address` | no | `BankonAgenticPlaceHook`. | `0xH00K…` |
| `ZEROG_INFT_ADDR` | `address` | no | `iNFT_7857` on 0G (from `DeployZeroG`). | `0x1NFT…` |

Operator must additionally set when running the *emitted* commands:
- `$CHAIN` — `mainnet` / `sepolia` for Ethereum, `16601` for 0G Galileo.
- `ETHERSCAN_API_KEY` (or 0G-explorer equivalent) — picked up by `forge verify-contract`.

## Pre-conditions

1. All four prior scripts succeeded; broadcast JSONs exist in `broadcast/`.
2. Operator has the source tree at the same git commit that produced the bytecode (otherwise constructor-args ABI encoding will mismatch and verification fails silently).
3. `foundry.toml` profile that was used for the deploy is still selected (compiler version, optimizer runs, EVM target — these are baked into the verification request).
4. API key registered with Etherscan (and 0G explorer for the 0G command).

## Step-by-step (the `run()` function)

1. **Env read** — pulls 8 addresses.
2. **Print Ethereum block** — emits one `forge verify-contract <addr> <path>:<contract> --chain $CHAIN` line per Ethereum contract (7 lines).
3. **Print 0G block** — emits the single 0G verification line for `iNFT_7857` with `--chain 16601` hard-coded.

The output is intentionally bash-paste-friendly; the operator literally runs each line.

> **NOTE — this script does NOT include constructor-args.** The emitted commands rely on `forge verify-contract` reading them from `broadcast/<Script>.s.sol/<chainId>/run-latest.json`. If that file is missing or stale, operator must add `--constructor-args $(cast abi-encode ...)` manually.

## Post-conditions

- A wall of bash commands appears on stdout.
- Nothing changes on-chain.
- Operator pastes commands into a terminal with `$CHAIN` and `ETHERSCAN_API_KEY` set; each verification succeeds → green checkmark on Etherscan for each contract.

## Failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `forge verify-contract: unable to verify` / bytecode mismatch | Source tree drift since deploy. Compiler version different. Optimizer runs different. | `git checkout <deploy-commit>`; ensure `foundry.toml` matches deploy-time settings. Re-run. |
| Constructor-args mismatch | Forge couldn't auto-read constructor args from broadcast JSON. | Append `--constructor-args $(cast abi-encode "constructor(…)" arg1 arg2 …)` to the failing command. |
| `Could not detect chain` on the 0G line | `forge` doesn't know about 0G Galileo. | Pass `--verifier blockscout --verifier-url https://chainscan-galileo.0g.ai/api` explicitly. |
| Operator copies commands but `$SUBNAME_REGISTRAR_ADDR` is empty | Script logged addresses as raw values, but operator pipe ate them, or env not exported into terminal. | Re-run, redirect stdout to file, manually substitute. |

## Verification

The script's own success is binary (it just prints). Confirm verification worked by:
```bash
# Etherscan UI shows "Contract Source Code Verified (Exact Match)" for each.
# Or via gh-api-style:
curl -s "https://api.etherscan.io/api?module=contract&action=getsourcecode&address=$SUBNAME_REGISTRAR_ADDR&apikey=$KEY" \
  | jq '.result[0].SourceCode != ""'
```

## Reverting

Not applicable — verification is additive metadata published to Etherscan / Sourcify / 0G explorer. There is no on-chain effect to revert. If incorrect source was submitted, re-verify with the correct source — the new verification supersedes.

## See also

- [`DeployEthereum.s.md`](./DeployEthereum.s.md), [`DeployZeroG.s.md`](./DeployZeroG.s.md), [`WireCrossChain.s.md`](./WireCrossChain.s.md) — pipeline predecessors.
- `docs/DEPLOYMENT.md` — operator runbook including API-key handling.
- `foundry.toml` — defines profiles + compiler config that verification must mirror.
