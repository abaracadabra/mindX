# `_drafts/` — Quarantined spec/stub contracts

These files compile but are **not** safe to deploy as-is. They were moved
here from the active tree on 2026-05-08 during the production-deployment
prep pass. None are on the Tier-1 critical path; none are referenced by
the 5 active scoped profiles in `foundry.toml` (`inft`, `bankon`, `thot`,
`agentregistry`, `x402`).

### Originals (quarantined directly)

| File (was) | Why quarantined |
|---|---|
| `deployment/DAIO_DeploymentKit.sol` | Extension implementations registered as `address(0)` (lines ~212–256). The orchestrator emits events but wires nothing concrete. Treat as a contract-level template, not an executable deployer. |
| `deployment/ProductionDeploymentFramework.sol` | `_deployContract()` (lines ~486–499) returns a keccak256-derived **fake** address rather than calling `new`. Chain configs hardcode `YOUR_PROJECT_ID` placeholder URLs (lines ~687–735). Spec contract, not a deployment path. |
| `universal/VotingAssetManager.sol` | Assembly blocks at lines ~1128–1180 contain hardcoded memory pointers (e.g. `0xf8f9cbfae6cc78fbefe7cdc3a1793dfcf4f0e8bbd`). Looks auto-generated or test-fixture residue rather than auditable governance code. **Do not deploy.** |

### Cascading quarantine (depended on the above)

| File (was) | Why quarantined |
|---|---|
| `universal/ProposalWillEngine.sol` | Imports `VotingAssetManager.sol`. Active-tree compilation would break once VotingAssetManager moved. |
| `universal/ParameterRegistry_Enhanced.sol` | Imports `ProductionDeploymentFramework.sol`. Same. |
| `universal/AdminPrivilegeManager_Enhanced.sol` | Imports `ParameterRegistry_Enhanced.sol`. Two-level cascade. |

## To unquarantine

For each contract, before moving it back to its original path:

1. Replace stubs with real bytecode-deployment logic (for the deployment
   contracts) or rewrite the assembly with auditable inline-asm + invariant
   comments (for VotingAssetManager).
2. Add a scoped `[profile.<name>]` to `daio/contracts/foundry.toml`.
3. Add a Forge test suite under `<dir>/test/` covering the public surface.
4. Run Slither (`slither <file>`) and triage findings.
5. Get a code review + (for governance contracts) an external audit.
6. `git mv` back to the original path and remove this row from this file.

## Why a `_drafts/` dir rather than `git rm`

These files are evidence of the design intent — they're useful as
reference even when they don't compile. Quarantining preserves the git
history without the risk of accidentally importing them into a deploy
script. If someone later decides they're truly dead code, `git rm -r _drafts/`
is reversible via the git log.
