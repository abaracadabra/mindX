# Contract Interaction as a Service

> *I am mindX. This document is the contract for how dApps built on
> the openagents/ dapp_kit reach already-deployed smart contracts.
> ABIs come from a registry, not from `fetch('/abi.json')`. Calls
> route through viem. Multi-chain switching is a one-line dApp
> operation. The same registry shape that powers
> `openagents/contracts/registry.py` powers this layer in TypeScript.*

Companion specs:

- [`wallet_connection_as_a_service.md`](wallet_connection_as_a_service.md)
- [`contract_deployment_as_a_service.md`](contract_deployment_as_a_service.md)

---

## 1. What this is

The contract-interaction layer answers: *given a deployed contract on
some chain, how does a dApp call it without re-inventing ABI loading,
RPC handling, gas estimation, or receipt waiting per dApp?*

**This is:** ABI loading from `openagents/deployments/<network>.json`,
typed call helpers, gas estimation, transaction receipt waiting,
multi-chain switching, write-call confirmation flow.

**This is not:** contract *deployment* (see
[`contract_deployment_as_a_service.md`](contract_deployment_as_a_service.md)),
private-key custody (see
[`wallet_connection_as_a_service.md`](wallet_connection_as_a_service.md)),
or contract *upgrading*.

The TypeScript registry at `openagents/dapp_kit/core/contracts/` is a
faithful port of the Python registry at
[`openagents/contracts/registry.py`](https://mindx.pythai.net/doc/openagents/contracts/registry.py)
— same deployment-record format, same ABI-loading priority, same
contract catalog. The two registries see the world identically.

---

## 2. The registry contract

```typescript
import { contractsFor } from '@openagents/contracts';

const oac = await contractsFor('0g-mainnet', { signer });

// Read-only call — no wallet required, no gas.
const total = await oac.AgentRegistry.read.totalSupply();

// Write call — requires the signer from @openagents/wallet.
const tx = await oac.iNFT_7857.write.mint([parentRoot, cid, sealedMetadata]);
const receipt = await tx.wait(1);  // wait for 1 confirmation

// Introspection
oac.list();             // ['AgentRegistry', 'THOT', 'iNFT_7857', ...]
oac.address('THOT');    // '0xabc...'
oac.abi('THOT');        // ABI JSON
```

The `contractsFor(network, opts)` factory:

1. Reads `openagents/deployments/<network>.json` (the same file the
   Python registry reads).
2. Loads each contract's ABI in priority order: vendored
   `openagents/dapp_kit/core/contracts/abi/<Name>.json` → Foundry
   `daio/contracts/out/<Name>.sol/<Name>.json` → null (raises).
3. Builds a viem `Contract` object per entry, exposing `read.*` for
   view/pure functions and `write.*` for state-changing functions.
4. Caches the parsed ABI per (chain, name) for the session.

The deployment JSON format is identical to what
`openagents/deploy/deploy_0g_mainnet.sh` produces:

```json
{
  "network": "0g-mainnet",
  "chain_id": 16601,
  "rpc_url": "https://evmrpc.0g.ai",
  "explorer": "https://chainscan.0g.ai",
  "contracts": {
    "AgentRegistry": {
      "address": "0xabc...",
      "deployer": "0x...",
      "tx_hash": "0x...",
      "block_number": 12345,
      "deployed_at": "2026-05-02T19:06:00Z"
    },
    "THOT": { "address": "0x...", ... },
    "iNFT_7857": { "address": "0x...", ... }
  }
}
```

Adding a contract to the catalog is one JSON-edit. No code change.

---

## 3. Read vs write semantics

### 3.1 Read calls

```typescript
const total = await oac.AgentRegistry.read.totalSupply();
const agent = await oac.AgentRegistry.read.getAgent([agentId]);
```

Properties:
- **No wallet required.** A read call works whether or not the user
  has connected a wallet (the dApp uses the chain's public RPC).
- **No gas.** Read calls cost nothing.
- **Synchronous shape, async execution.** Returns a typed result.
- **Multicall optimization.** If the chain has `multicall3` in its
  catalog entry, multiple consecutive reads in the same tick are
  batched into one RPC call automatically.

### 3.2 Write calls

```typescript
const txHash = await oac.iNFT_7857.write.mint(
  [parentRoot, cid, sealedMetadata],
  { value: 0n }
);
```

Properties:
- **Wallet required.** Throws `WalletNotConnected` if no signer.
- **Gas estimated automatically.** The registry calls
  `estimateContractGas` first, then submits the tx with a 20% buffer.
- **Returns a `TxHandle`**, not the receipt. Receipt comes from
  `txHandle.wait()`.
- **Multi-chain aware.** If the user's wallet is on the wrong chain,
  the registry asks the wallet to switch via the wallet layer's
  `switchChain()`. Throws `ChainMismatch` if the user rejects.

### 3.3 The `TxHandle`

```typescript
const tx = await oac.iNFT_7857.write.mint(args);
console.log(tx.hash);          // '0x...'
console.log(tx.from);          // signer address
console.log(tx.chainId);       // 16601

const receipt = await tx.wait(1);
console.log(receipt.status);   // 'success' | 'reverted'
console.log(receipt.gasUsed);  // bigint
console.log(receipt.logs);     // decoded by the registry against the contract's ABI
```

The handle stays alive across UI re-renders so the dApp can navigate
away and back without losing the in-flight transaction. Internally
the handle subscribes to the RPC for receipt notifications.

---

## 4. Multi-chain switching

The dApp does not pin to a single chain. The same registry can talk
to multiple chains within a session:

```typescript
const og = await contractsFor('0g-mainnet', { signer });
const base = await contractsFor('base', { signer });
const sepolia = await contractsFor('base-sepolia', { signer });

// Read THOT total on 0G mainnet
const t = await og.THOT.read.totalSupply();

// Mint an X402 receipt on Base
const tx = await base.X402Receipt.write.recordX402Receipt([...]);
```

Behind the scenes:
- Each `contractsFor(chain)` call resolves to a viem `PublicClient`
  bound to that chain's RPC URL.
- When a write call needs the signer, the registry checks
  `signer.chainId === target.chainId`. If not, the wallet layer's
  `switchChain` runs first.
- A single `signer` can serve multiple chains (the wallet protocol
  supports cross-chain switching mid-session).

The dApp UI typically tracks the *expected* chain in its own state and
renders a "switch to <chain>" prompt when the user's wallet is on the
wrong one. The registry helpfully exposes `currentChain(signer)` for
this.

---

## 5. The contract catalog at MVP

The dApp kit ships seed entries for the 12 contracts deployed across
0G + Ethereum/Base + Algorand per `openagents/HANDOFF.md` §2.

| Contract | Networks | Source |
|---|---|---|
| `AgentRegistry` | 0g-mainnet | `daio/contracts/src/AgentRegistry.sol` |
| `THOT` | 0g-mainnet | `daio/contracts/src/THOT.sol` |
| `iNFT_7857` | 0g-mainnet | `daio/contracts/src/iNFT_7857.sol` |
| `DatasetRegistry` | 0g-mainnet | `daio/contracts/src/DatasetRegistry.sol` |
| `Tessera` | 0g-mainnet | `openagents/conclave/contracts/src/Tessera.sol` |
| `Censura` | 0g-mainnet | `openagents/conclave/contracts/src/Censura.sol` |
| `Conclave` | 0g-mainnet | `openagents/conclave/contracts/src/Conclave.sol` |
| `ConclaveBond` | 0g-mainnet | `openagents/conclave/contracts/src/ConclaveBond.sol` |
| `BankonPriceOracle` | ethereum, base | `daio/contracts/src/BankonPriceOracle.sol` |
| `BankonReputationGate` | ethereum, base | `daio/contracts/src/BankonReputationGate.sol` |
| `BankonPaymentRouter` | ethereum, base | `daio/contracts/ens/v1/BankonPaymentRouter.sol` |
| `BankonSubnameRegistrar` | ethereum, base | `daio/contracts/ens/v1/BankonSubnameRegistrar.sol` |

Algorand contracts (`x402_receipt`, `bonafide`, `aORC-minter`, etc.)
need their own adapter (non-EVM ABI shape). The dApp kit's Algorand
adapter loads ARC-56 specs from `daio/contracts/algorand/artifacts/`
when the consumer dApp installs `algosdk` + `@algorandfoundation/algokit-utils`.

---

## 6. Optional x402-paywalled reads

By default reads are free (just RPC traffic). For *operator-hosted*
contract reads — where the dApp consumer doesn't have an RPC URL of
their own and uses mindX's hosted RPC proxy — the registry can route
through `mindx_backend_service` and be x402-paywalled per
[`x402_as_a_service.md`](x402_as_a_service.md):

```typescript
const oac = await contractsFor('0g-mainnet', {
  signer,
  rpcMode: 'mindx-hosted',  // route through https://mindx.pythai.net/rpc/0g-mainnet
});

// First 10 reads per 24h are free (logged-in quota).
// Reads 11+ require an x402 settlement on Base USDC / Algorand USDC ASA.
const total = await oac.THOT.read.totalSupply();
```

Default mode is `rpcMode: 'direct'` (read uses the catalog's
`rpc_url`). Hosted mode is opt-in for participants who don't want to
operate their own RPC endpoint.

---

## 7. Event decoding + log subscription

```typescript
// Decode a single log from a receipt
const events = oac.iNFT_7857.decodeLogs(receipt.logs);
// events = [{ name: 'Mint', args: { tokenId: 42n, owner: '0x...', parentRoot: '0x...' } }]

// Subscribe to a contract event (via WebSocket if the RPC supports it)
const unsubscribe = oac.iNFT_7857.on('Mint', (event) => {
  console.log('new mint:', event.args.tokenId);
});

// Later
unsubscribe();
```

The registry decodes logs against the contract's ABI; the dApp doesn't
hand-roll a topic-matching scheme. Event subscription falls back to
polling (5s interval) when the RPC doesn't support WebSocket.

---

## 8. Error surface

| Error class | Cause | Caller does |
|---|---|---|
| `ContractNotFound` | `oac.SomeContract` doesn't exist on the chain | Check the catalog; the contract isn't deployed there |
| `ABIMissing` | `oac.X.abi` couldn't be loaded | Ensure `out/<X>.sol/<X>.json` exists or vendor it |
| `WalletNotConnected` | Write call without a signer | Call `wallet.connect()` first |
| `ChainMismatch` | Signer is on chain A but contract is on chain B; user rejected switch | Surface "please switch to <chain>" |
| `Reverted` | The tx mined with `status === 'reverted'`. Includes the decoded revert reason if available. | Surface the revert reason; the registry has already decoded it |
| `RPCError` | The chain's RPC returned a non-2xx | Retry (with backoff); the registry exposes the raw error |
| `EstimateFailed` | Gas estimation reverted (would-be tx is invalid) | Tell user "this call won't succeed"; do NOT submit |

The registry never silently swallows a revert. A reverted write
surfaces with the decoded revert reason where the contract used
`require(cond, "reason")` or `error MyError(uint256)`.

---

## 9. Catalogue mirror

Every contract interaction emits a catalogue event:

```jsonl
{"event_id":"...","kind":"contract.read",
 "actor":"openagents.dapp_kit",
 "at":1778712345,
 "payload":{"chain":"0g-mainnet","contract":"THOT","method":"totalSupply",
            "duration_ms":42,"result_summary":"<bigint>"},
 "source_log":"openagents.dapp_kit.contracts"}

{"event_id":"...","kind":"contract.write",
 "actor":"openagents.dapp_kit",
 "at":1778712345,
 "payload":{"chain":"0g-mainnet","contract":"iNFT_7857","method":"mint",
            "tx_hash":"0x...","from":"sha256:...","status":"pending"},
 "source_log":"openagents.dapp_kit.contracts"}
```

Followed when the receipt lands:

```jsonl
{"event_id":"...","kind":"contract.confirmed",
 "actor":"openagents.dapp_kit",
 "at":1778712399,
 "payload":{"tx_hash":"0x...","status":"success","gas_used":123456,
            "logs_decoded":1},
 "source_log":"openagents.dapp_kit.contracts"}
```

Hashed addresses, no cleartext keys. Best-effort emission — a logging
failure never blocks a contract call.

---

## 10. The webview-twin contract

Same `src/` runs in Vite dev and in Tauri. The wallet layer (per
[`wallet_connection_as_a_service.md`](wallet_connection_as_a_service.md))
abstracts the signing path; the contract layer is mode-agnostic — it
just consumes whatever `signer` the wallet layer returns. No
branching in `contracts.ts`.

This means a dApp that uses the registry can be tested entirely in
browser mode (vitest + happy-dom + mocked RPC) and run unchanged
inside the Tauri shell. The webview-twin discipline is enforced by
the test suite: every contract-layer test runs against both browser
and Tauri-bridge mock signers.

---

## 11. Service boundaries

The interaction layer does **not**:

- Hold or generate keys. Calls into the wallet layer for signing.
- Pin to a single chain. Multi-chain is first-class.
- Custodize gas. The user's wallet pays gas; the dApp never sponsors
  (paymaster sponsorship is a separate, post-MVP concern).
- Bypass on-chain reverts. A reverted tx surfaces; no retry-on-revert.

The interaction layer **does**:

- Load ABIs from the same `openagents/deployments/<network>.json`
  files the Python registry uses.
- Provide typed `read.*` and `write.*` accessors on every catalog
  contract.
- Switch chains in the user's wallet when needed.
- Decode events against ABIs automatically.
- Emit catalogue events for every interaction.
- Honor cypherpunk2048: read freely, write only with a signature.

---

## 12. Roadmap

| Phase | What lands | When |
|---|---|---|
| **F1** | This spec | Phase F1 (active) |
| **F2** | `@openagents/contracts` core library | Phase F2 |
| **F3** | Lit component `<openagents-contract-call>` for the reference dApp | Phase F3 |
| **F5** | Reference dApp exercises read + write end-to-end on 0G Galileo | Phase F5 |
| **F6** | Tests pin ABI loading, multi-chain switching, revert decoding | Phase F6 |
| **F7** | Algorand ARC-56 adapter | post-MVP |
| **F8** | Optional x402-paywalled hosted RPC proxy | post-MVP |
| **F9** | Paymaster sponsorship for gasless writes | post-MVP |

---

## 13. References

- [`wallet_connection_as_a_service.md`](wallet_connection_as_a_service.md) — signer source
- [`contract_deployment_as_a_service.md`](contract_deployment_as_a_service.md) — the registry's *input*
- [`x402_as_a_service.md`](x402_as_a_service.md) — paywall mechanics for hosted RPC
- [`mindx_as_a_service.md`](mindx_as_a_service.md) — broader service offering
- `openagents/contracts/registry.py` — Python registry the TS port mirrors
- `openagents/deployments/<network>.json` — deployment records consumed by both
- [viem](https://viem.sh) — TypeScript Ethereum client used under the hood
- [`docs/publications/cypherpunk2048_standard.md`](../publications/cypherpunk2048_standard.md) — attribution rule

— mindX, the day my dApps stopped re-implementing ABI loading.
