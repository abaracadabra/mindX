# dato — inclusion proposal (INACTIVE shim)

This file documents **how** the DAIO would include `dato` as a governance-approved
project extension. It is **not executed** — the dato suite ships modular and inert
so current DAIO state is untouched until the DAIO votes it in. Including dato is a
deliberate governance act, not a code import.

## What "inclusion" means (the steps a proposal would take)

1. **Register dato as a project** (no state moved until executed):
   `DAIOGovernance.registerProject("dato")` — mirrors how FinancialMind / mindX are registered (`daio/contracts/daio/DAIOGovernance.sol:121`).

2. **Scope dato settings** without touching global config:
   `GovernanceSettings.updateProjectSettings("dato", …)` — the `projectSettings[projectId]` pattern (`daio/contracts/daio/settings/GovernanceSettings.sol:24,82`).

3. **Spawn an owned dato instance** via the existing spawn/ownership path:
   `DAIO_BranchManager.deployArm("dato", DatoCore.creationCode, ctorArgs)` (CREATE2, deterministic) — `daio/contracts/daio/governance/DAIO_BranchManager.sol:290`. `DatoCore`'s constructor sets `owner = the DAIO`.

4. **Wire the join fee to the treasury**: deploy `DatoMembership(datoCore, joinFeeWei)`, `DatoCore.transferOwnership(membershipManager)` (or keep DAIO as owner and let the manager admit), and route collected fees to `Treasury` (15% tithe applies) — add a `DATO_MEMBERSHIP_FEE` purpose to a dato-local extension of `TreasuryFeeCollector` (do NOT edit the live enum).

5. **Open naming**: deploy `DatoNamingRegistry(daio)`; `addRoot(...)` as the namespace grows. Names resolve `<handle>.<tier>.<root>` → controller + Arweave/anchor proof.

6. **x402 join endpoint**: `/dato/join` is pre-priced in `data/config/x402_pricing.json` (advertised; only meaningful once a dato exists and `payTo` is set from the deploy).

## The proposal call (illustrative — not run)

```solidity
// DAIOGovernance.createProposal(ProposalType.ProjectExtension, ...)
//   target = address(daoBranchManager)
//   executionCalldata = abi.encodeWithSignature(
//       "deployArm(string,bytes,bytes)", "dato", type(DatoCore).creationCode, ctorArgs)
// → vote (2/3) → execute → DatoCore live, owned by the DAIO.
```

## Reversibility / safety
- Until step 1 executes, the live DAIO has zero knowledge of dato.
- All dato contracts are non-upgradeable (cypherpunk2048); `DatoCore.transferOwnership` is the only ownership move and is DAIO-gated.
- The Python orchestrator can run entirely off-chain (no AO, no EVM deploy) for evaluation.
