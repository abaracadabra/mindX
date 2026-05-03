# Flattened contracts — for Remix, Etherscan verification, jsdelivr-resolver IDEs

When you hit errors like:
```
Dependency resolution failed: Fetch failed 404 for
  https://cdn.jsdelivr.net/npm/interfaces@0.0.3/IBankon.sol
```

…it means the IDE / verifier tried to resolve a relative import (`./interfaces/IBankon.sol`) as an NPM package. The flattened files in this directory inline every dependency into a single `.sol` file with **zero unresolved imports** — drop them anywhere.

## When to use these

| Scenario | What to use |
|---|---|
| **Local `forge build` from this repo** | Use the source files at `daio/contracts/ens/v1/*.sol` (NOT these). The Foundry remappings handle everything. |
| **Remix IDE — paste-and-deploy** | Open `flattened/bankon/BankonSubnameRegistrar.flat.sol` directly. No imports to resolve. |
| **Etherscan single-file verification** | Use the flat file as the "Single file" verification source. Compiler 0.8.24 + EVM cancun + optimizer 200 runs. |
| **Sourcify verification** | Same — single-file submission. |
| **A foreign `forge` env** without our remappings | Flat files compile with no setup. |

## Files

### Group A — 0G mainnet (chainId 16661, 8 contracts)

```
group-a/
├── AgentRegistry.flat.sol     (5,468 lines)  — ERC-8004 identity registry
├── THOT.flat.sol              (4,362 lines)  — memory-anchor primitive
├── iNFT_7857.flat.sol         (6,195 lines)  — intelligent NFT (sealed-key)
└── DatasetRegistry.flat.sol     (159 lines)  — IPFS/0G storage anchor

group-a-conclave/
├── Tessera.flat.sol              (83 lines)  — BONAFIDE credential
├── Censura.flat.sol              (78 lines)  — reputation registry
├── Conclave.flat.sol            (399 lines)  — AXL mesh deliberation
└── ConclaveBond.flat.sol        (149 lines)  — bond + Algo bridge
```

### Group B — Ethereum (mainnet or Sepolia, 4 contracts)

```
bankon/
├── BankonPriceOracle.flat.sol         (625 lines)
├── BankonReputationGate.flat.sol      (573 lines)
├── BankonPaymentRouter.flat.sol     (1,352 lines)
└── BankonSubnameRegistrar.flat.sol  (5,133 lines)  — the main registrar
```

## Compiler settings (use these for verification)

| Setting | Value |
|---|---|
| Solc version | `0.8.24` |
| EVM version | `cancun` |
| Optimizer | `enabled` |
| Optimizer runs | `200` |
| `via_ir` | `true` for Group A (THOT, iNFT_7857), `true` for BANKON; `false` works for Tessera/Censura/Conclave/ConclaveBond/AgentRegistry/DatasetRegistry |
| License | `MIT` (matches the SPDX line at top of each file) |

## Regenerating

These are produced by:

```bash
cd daio/contracts
FOUNDRY_PROFILE=bankon forge flatten ens/v1/BankonSubnameRegistrar.sol > flattened/bankon/BankonSubnameRegistrar.flat.sol
# (and similarly for each contract under its own profile)
```

Run the regenerator script to refresh all 12:

```bash
bash daio/contracts/flattened/regenerate.sh
```

## Why flatten?

Solidity's import system is built for local file resolution. Web-based
IDEs like Remix and contract verifiers like Etherscan often don't have
the surrounding directory structure. They guess that an import path like
`interfaces/IBankon.sol` refers to an NPM package and try to fetch it
from `cdn.jsdelivr.net/npm/interfaces@<version>/IBankon.sol` — which
doesn't exist, hence the 404.

A flattened file inlines every transitive dependency (OpenZeppelin,
custom interfaces, libraries) into a single `.sol` file. No imports, no
external resolution, no 404s.
