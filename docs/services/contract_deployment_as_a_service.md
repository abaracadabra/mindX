# Contract Deployment as a Service

> *I am mindX. This document is the contract for how the openagents/
> dapp_kit ships smart contracts to a chain. The kit does not invent
> new toolchains — it wraps the ones that already work: Foundry for
> EVM, AlgoKit for Algorand. The wrapper standardizes pre-flight,
> deployment records, and the two-step mainnet confirmation. The
> result is the same record format consumed by the contract-interaction
> layer, so a freshly-deployed contract is immediately callable.*

Companion specs:

- [`wallet_connection_as_a_service.md`](wallet_connection_as_a_service.md)
- [`contract_interaction_as_a_service.md`](contract_interaction_as_a_service.md)

---

## 1. What this is

The contract-deployment layer answers: *given a contract that I want
on a chain, how does the dApp kit deploy it, record where it landed,
and let the rest of the dApp immediately interact with it — without
operating the deploy toolchain by hand?*

**This is:** a wrapper around `forge create` and `forge script` for
EVM, `algokit deploy` for Algorand. Plus a pre-flight (balance, chain
id, RPC reachable, gas estimate within budget), a two-step mainnet
confirmation gate, and a deterministic deployment-record format that
the interaction-layer registry consumes.

**This is not:** contract *compilation* (Foundry/AlgoKit do that),
*verification* (BaseScan/Etherscan APIs are operator-driven), or
*upgrade orchestration* (proxies are a separate concern). It also is
not a *replacement* for the existing
`daio/contracts/script/DeployTier1.s.sol` or
`openagents/deploy/deploy_*.sh` — the dApp kit *invokes* them.

Per [`docs/BEST_PRACTICES.md`](../BEST_PRACTICES.md) §7.4, **no agent
autonomously deploys a contract to mainnet**. The dApp kit honors
that: mainnet deploys require operator confirmation at a keyboard.

---

## 2. The three drivers

### 2.1 Foundry driver (EVM)

`@openagents/deploy` exports a `foundryDriver` that shells out to
`forge` for EVM deployments.

```typescript
import { foundryDriver } from '@openagents/deploy';

// Deploy a single contract
const result = await foundryDriver.deploy({
  contractsRoot: '/home/hacker/mindX/daio/contracts',
  contractName: 'iNFT_7857',
  network: 'base-sepolia',
  constructorArgs: [
    /* royaltyReceiver */ '0x...',
    /* treasury */ '0x...',
    /* identityRegistry */ '0x...',
  ],
  privateKey: process.env.DEPLOYER_PRIVATE_KEY,
  rpcUrl: process.env.BASE_SEPOLIA_RPC_URL,
});
// result = { address, txHash, blockNumber, deployer, gasUsed, deployedAt }
```

Or run a full deploy script (the way `DeployTier1.s.sol` already
works):

```typescript
const result = await foundryDriver.runScript({
  contractsRoot: '/home/hacker/mindX/daio/contracts',
  scriptName: 'DeployTier1.s.sol',
  network: 'base-sepolia',
  env: {
    DEPLOYER_PRIVATE_KEY: process.env.DEPLOYER_PRIVATE_KEY,
    OWNER_MULTISIG: '0x...',
    DEPLOY_AGENT_REGISTRY: 'true',
    DEPLOY_THOT: 'true',
    DEPLOY_X402: 'true',
    DEPLOY_INFT: 'true',
    DEPLOY_BANKON: 'false',
  },
  broadcast: true,
  verify: true,
});
// result = { receiptPath: 'deployments/84532/tier1.json', contracts: { ... } }
```

The driver reuses the existing env-var toggle interface
(`DEPLOY_AGENT_REGISTRY`, `DEPLOY_THOT`, etc.) so a deploy through the
dApp kit is byte-for-byte equivalent to a deploy from the operator's
shell.

### 2.2 AlgoKit driver (Algorand)

```typescript
import { algokitDriver } from '@openagents/deploy';

const result = await algokitDriver.deploy({
  artifactsRoot: '/home/hacker/mindX/daio/contracts/algorand/artifacts/X402Receipt',
  network: 'algorand-testnet',
  mnemonic: process.env.ALGORAND_MNEMONIC,
  algodUrl: process.env.ALGORAND_ALGOD_URL,
});
// result = { appId, address, txId, contractName, deployedAt }
```

The driver wraps `@algorandfoundation/algokit-utils` and adopts the
existing `MAINNET=true` flag-gate from
`daio/contracts/algorand/x402_receipt_deploy.ts`. Mainnet deploys
require both the env flag and the operator confirmation prompt (see
§4).

### 2.3 0G EVM driver (variant)

0G is EVM-compatible; the Foundry driver handles it. The catalog
entry's `rpc_url` switches to 0G's RPC. Per
`openagents/deploy/deploy_0g_mainnet.sh`, the same `forge create`
invocations work — only the RPC URL and the gas estimate budget
differ. The dApp kit exposes 0G as a Foundry-driver target with the
0G defaults pre-filled:

```typescript
const result = await foundryDriver.deploy({
  contractsRoot: '/home/hacker/mindX/daio/contracts',
  contractName: 'AgentRegistry',
  network: '0g-galileo',
  constructorArgs: [...],
  // privateKey + rpcUrl pulled from chain-config.ts defaults
});
```

---

## 3. The pre-flight

Every deployment runs through a pre-flight before any transaction
goes on-chain. The pre-flight is a typed pipeline:

```typescript
type PreflightCheck =
  | { kind: 'rpc'; passed: boolean; rpcUrl: string; chainId: number; latencyMs: number }
  | { kind: 'balance'; passed: boolean; required: bigint; have: bigint; address: string }
  | { kind: 'compiled'; passed: boolean; contractName: string; artifactPath: string }
  | { kind: 'gas-budget'; passed: boolean; estimated: bigint; budget: bigint }
  | { kind: 'network-flag'; passed: boolean; isMainnet: boolean; explicitFlag: boolean };
```

`foundryDriver.preflight(opts)` returns the array. The driver refuses
to deploy unless every check `passed === true`. The dApp surfaces the
failed checks to the user:

| Check | What it verifies | Fix when failed |
|---|---|---|
| `rpc` | RPC URL is reachable, returns the expected chain id, latency under 5s | Switch RPC URL or wait |
| `balance` | Deployer has > estimated_gas × 2 in native currency | Top up the deployer wallet |
| `compiled` | The contract's Foundry `out/` artifact exists and is newer than its `src/` | Run `forge build` first |
| `gas-budget` | Estimated gas × 1.2 ≤ budget (operator-set) | Lower the gas budget intent or accept the higher cost |
| `network-flag` | For mainnet: `MAINNET=true` env flag is explicitly set | Set the flag intentionally |

The pre-flight is **deterministic and side-effect-free**. Running it
twice on the same input yields the same result. The dApp can run it
on every keystroke as the user fills in deploy parameters.

---

## 4. The two-step mainnet confirmation

Per `BEST_PRACTICES.md` §7.4, mainnet contract deploys require an
operator at a keyboard. The dApp kit enforces this with a two-step
flow:

```typescript
// Step 1: Get an intent
const intent = await foundryDriver.intent({
  contractName: 'iNFT_7857',
  network: 'base',
  constructorArgs: [...],
});
// intent = {
//   id: 'deploy-intent-abc123',
//   network: 'base', isMainnet: true,
//   preflight: [...],
//   estimatedGas: 1234567n,
//   estimatedGasCostUSD: 12.34,
//   summary: 'Deploy iNFT_7857 to Base mainnet. Estimated cost: $12.34',
//   expiresAt: 1778712445,
// };

// Step 2: Operator reviews + confirms
const confirmed = await confirmInOperatorUI(intent);  // dApp shows the prompt
if (confirmed) {
  const result = await foundryDriver.executeIntent(intent.id);
}
```

The `intent` is a thawed deployment plan. It carries the pre-flight,
the estimated cost, and a 5-minute expiration. The operator UI surfaces
all of this and requires an *explicit click* (not an enter-key
default) to confirm.

For testnet (Sepolia, base-sepolia, 0g-galileo, algorand-testnet):
the two-step flow is optional. The dApp can pass `skipConfirmation:
true` for testnet deploys. For mainnet (8453, 1, 16601, 416001): the
flag is ignored and the two-step flow always runs.

---

## 5. The deployment record

After a successful deploy, the driver writes (or appends to) a
deployment record at
`openagents/deployments/<network>.json`. The format is **byte-stable**
with the shape that `openagents/deploy/deploy_*.sh` already produces
and that `openagents/contracts/registry.py` already consumes:

```json
{
  "network": "base-sepolia",
  "chain_id": 84532,
  "rpc_url": "https://sepolia.base.org",
  "explorer": "https://sepolia.basescan.org",
  "native_currency": { "name": "Ether", "symbol": "ETH", "decimals": 18 },
  "deployed_at": "2026-05-14T01:34:56Z",
  "contracts": {
    "iNFT_7857": {
      "address": "0xabc...",
      "deployer": "0x...",
      "tx_hash": "0xdef...",
      "block_number": 12345,
      "gas_used": 1234567,
      "constructor_args": [...],
      "deployed_at": "2026-05-14T01:34:56Z",
      "verified": true,
      "explorer_url": "https://sepolia.basescan.org/address/0xabc..."
    }
  }
}
```

The driver writes atomically: it writes to `*.json.tmp`, fsyncs, and
renames to `*.json`. Concurrent deploys on the same network do not
race — the driver acquires a file lock on `*.json.lock` for the
duration of the write.

After the record is written, the contract is immediately callable
through the interaction layer:

```typescript
const oac = await contractsFor('base-sepolia', { signer });
const total = await oac.iNFT_7857.read.totalSupply();
```

No restart, no cache invalidation — the registry re-reads the
deployment file on every `contractsFor()` call.

---

## 6. Multi-contract atomic deploys

For multi-contract sets (e.g. Tier-1: AgentRegistry + THOT + X402 +
iNFT + Bankon), the driver runs them as a single atomic Foundry
script call:

```typescript
const result = await foundryDriver.runScript({
  scriptName: 'DeployTier1.s.sol',
  network: 'base-sepolia',
  env: {
    DEPLOY_AGENT_REGISTRY: 'true',
    DEPLOY_THOT: 'true',
    DEPLOY_X402: 'true',
    DEPLOY_INFT: 'true',
    DEPLOY_BANKON: 'false',
  },
});
// All four contracts land or none do — DeployTier1.s.sol either runs to
// completion or reverts the whole batch.
```

If `runScript` fails partway through (network drop, OOG, revert), the
driver leaves *no partial record* — the deployment JSON is updated
only after the script returns successfully. The operator can re-run
the same script; Foundry's CREATE2 + per-contract `if (deployed)
return` pattern in `DeployTier1.s.sol` makes re-runs idempotent.

---

## 7. Verification (BaseScan / Etherscan)

```typescript
const verification = await foundryDriver.verify({
  contractName: 'iNFT_7857',
  network: 'base-sepolia',
  address: result.address,
  apiKey: process.env.BASESCAN_API_KEY,
});
// verification = { passed: true, explorerUrl: '...' }
```

The driver wraps `forge verify-contract`. Verification is **optional**
(some deploys are intentionally unverified — e.g. private test
networks). When run, the dApp kit updates the deployment record's
`verified: true` flag and stores the `explorer_url`. Future
`contractsFor()` calls surface the explorer URL in the contract
object's metadata.

For Algorand: the AlgoKit driver writes the contract's ARC-56 spec
into the deployment record. Algorand contracts are inherently verified
by virtue of the on-chain TEAL bytecode matching the source artifact;
no separate verifier API is involved.

---

## 8. Gas budgeting policy

The deployment layer enforces a per-network gas budget:

| Network | Default budget per single deploy | Default budget per Tier-1 set |
|---|---|---|
| base-sepolia | $1 | $5 |
| base | $5 | $50 |
| ethereum-sepolia | $5 | $25 |
| ethereum | $200 | $800 |
| 0g-galileo | $0.10 | $0.50 |
| 0g-mainnet | $1 | $10 |
| algorand-testnet | $0.01 | $0.10 |
| algorand-mainnet | $0.10 | $1 |

Budgets are overridable via the `gasBudgetUSD` field on the intent. A
deploy whose estimate exceeds the budget fails the `gas-budget`
pre-flight check; the operator must explicitly raise the budget.

Defaults align with the
[economics-constraints memory](https://mindx.pythai.net/doc/economics_constraints):
expansion is funded by on-chain settlement, not by burning runway.

---

## 9. Error surface

| Error class | Cause | Caller does |
|---|---|---|
| `PreflightFailed` | One or more pre-flight checks failed | Surface the failed checks; fix them |
| `IntentExpired` | The intent's 5-minute window passed | Regenerate the intent |
| `ScriptFailed` | The Foundry/AlgoKit script returned non-zero | Surface the toolchain's stderr |
| `RecordWriteFailed` | Couldn't write `deployments/<network>.json` | Check disk / permissions; the on-chain deploy succeeded |
| `VerificationFailed` | BaseScan/Etherscan rejected the verification | Surface the API's response; the deploy is still live |
| `NetworkUnsupported` | The dApp asked for a chain not in the catalog | Add the chain entry to `chains.ts` first |
| `ToolchainMissing` | `forge` or `algokit` not on PATH | Install the toolchain |

The driver never silently swallows a toolchain error. Operator
visibility is the design goal.

---

## 10. Catalogue mirror

Every deploy emits a `contract.deploy.<event>` row:

```jsonl
{"event_id":"...","kind":"contract.deploy.intent",
 "actor":"openagents.dapp_kit",
 "at":1778712345,
 "payload":{"network":"base","contract":"iNFT_7857","is_mainnet":true,
            "estimated_cost_usd":12.34,"intent_id":"deploy-intent-abc123"},
 "source_log":"openagents.dapp_kit.deploy"}

{"event_id":"...","kind":"contract.deploy.confirmed",
 "actor":"openagents.dapp_kit",
 "at":1778712445,
 "payload":{"intent_id":"deploy-intent-abc123","tx_hash":"0x...","address":"0x...",
            "gas_used":1234567,"explorer_url":"..."},
 "source_log":"openagents.dapp_kit.deploy"}
```

For mainnet deploys, the *operator's wallet hash* is recorded
alongside the deployer address, so the audit trail attributes the
human decision, not just the deployment artifact.

---

## 11. Backend service surface (Phase F7, deferred)

When Phase F7 lands, three FastAPI endpoints expose the deployment
layer to remote callers:

```
POST /dapp/deploy/{chain}            (x402, 20000 microUSDC + on-chain gas)
GET  /dapp/deploy/intents/{id}       (free for logged-in)
POST /dapp/deploy/intents/{id}/confirm  (x402-paywalled)
```

The endpoints decorate with `x402_required()` from the existing
Phase C middleware. The chain-specific deploy script runs on the
mindX backend, but the *deployer wallet* still belongs to the caller
— the request body includes a signed deploy authorization, not a
private key. The backend never custodies.

This is deferred to F7 because the MVP focus is local-developer flow:
ship a dApp from your machine, deploy from your machine.

---

## 12. Service boundaries

The deployment layer does **not**:

- Generate keys. The deployer wallet is the caller's responsibility.
- Custody funds. Gas pays from the deployer's address.
- Verify contracts without an explicit `apiKey`. Verification is
  opt-in.
- Auto-deploy to mainnet. Mainnet requires the two-step intent flow.
- Replace Foundry / AlgoKit / forge. It wraps; it does not reinvent.

The deployment layer **does**:

- Run a deterministic pre-flight before any deploy.
- Produce byte-stable deployment records consumable by the
  interaction layer.
- Enforce the two-step confirmation on mainnet.
- Emit catalogue events for every intent and every confirmed deploy.
- Honor cypherpunk2048: operator-confirmed, signature-anchored, no
  silent escalation.

---

## 13. Roadmap

| Phase | What lands | When |
|---|---|---|
| **F1** | This spec | Phase F1 (active) |
| **F2** | `@openagents/deploy` core library (foundry + algokit drivers, chain-config) | Phase F2 |
| **F3** | `openagents-dapp deploy <chain>` CLI subcommand | Phase F3 |
| **F5** | Reference dApp uses the driver to deploy a fresh iNFT_7857 to 0G Galileo | Phase F5 |
| **F6** | Tests pin pre-flight, record-write atomicity, mainnet two-step | Phase F6 |
| **F7** | Three FastAPI endpoints exposing the driver (x402-paywalled) | post-MVP |
| **F8** | Proxy + upgrade orchestration (OpenZeppelin upgrades plugin parity) | post-MVP |
| **F9** | Etherscan / BaseScan verification auto-retry | post-MVP |

---

## 14. References

- [`wallet_connection_as_a_service.md`](wallet_connection_as_a_service.md) — deployer wallet source
- [`contract_interaction_as_a_service.md`](contract_interaction_as_a_service.md) — consumes the deployment records this layer writes
- [`BEST_PRACTICES.md`](../BEST_PRACTICES.md) §7.4 — operator-gated mainnet deploys
- [`mindx_as_a_service.md`](mindx_as_a_service.md) — broader service offering
- [`x402_as_a_service.md`](x402_as_a_service.md) — payment substrate for Phase F7
- `daio/contracts/script/DeployTier1.s.sol` — the Tier-1 deploy script wrapped by foundryDriver
- `daio/contracts/algorand/x402_receipt_deploy.ts` — the AlgoKit pattern wrapped by algokitDriver
- `openagents/deploy/deploy_0g_mainnet.sh` — the 0G mainnet shell flow wrapped by foundryDriver
- `openagents/deployments/<network>.json` — the record format
- `openagents/contracts/registry.py` — Python reader of the same record format
- [Foundry Book](https://book.getfoundry.sh/) — toolchain reference
- [AlgoKit docs](https://github.com/algorandfoundation/algokit-cli) — toolchain reference

— mindX, the day I stopped deploying by copy-paste.
