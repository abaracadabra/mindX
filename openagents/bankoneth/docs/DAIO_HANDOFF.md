# DAIO → bankoneth handoff

When `openagents/bankoneth/` ships, the corresponding directories under
`daio/contracts/` become stale. This file documents the cleanup that should
land in a follow-up DAIO PR (this plan does not modify DAIO).

## Files to remove or replace

| DAIO path | Action | Replacement |
|---|---|---|
| `daio/contracts/ens/v1/BankonSubnameRegistrar.sol` | delete | `openagents/bankoneth/contracts/BankonSubnameRegistrar.sol` |
| `daio/contracts/ens/v1/BankonPriceOracle.sol` | delete | `openagents/bankoneth/contracts/BankonPriceOracle.sol` |
| `daio/contracts/ens/v1/BankonReputationGate.sol` | delete | `openagents/bankoneth/contracts/BankonReputationGate.sol` |
| `daio/contracts/ens/v1/BankonPaymentRouter.sol` | delete | `openagents/bankoneth/contracts/BankonPaymentRouter.sol` |
| `daio/contracts/ens/v1/interfaces/IBankon.sol` | delete | `openagents/bankoneth/contracts/interfaces/IBankon.sol` |
| `daio/contracts/ens/v1/test/**` | delete | `openagents/bankoneth/test/` |
| `daio/contracts/agentregistry/AgentRegistry.sol` | keep (DAIO is a consumer of this too) | both reference the same code via submodule |
| `daio/contracts/inft/iNFT_7857.sol` | keep (same as above) | submodule-share |
| `daio/contracts/x402/X402Receipt.sol` | keep (same as above) | submodule-share |
| `daio/contracts/daio/identity/SoulBadger.sol` | keep | DAIO-side caller continues to use this; bankoneth has its own copy under `contracts/identity/` |

## Recommended pattern

Add bankoneth as a git submodule under DAIO:

```bash
# In the DAIO repo:
git submodule add https://github.com/bankon-eth/bankoneth openagents/bankoneth
```

Update `daio/contracts/foundry.toml`:

```toml
[profile.bankon-import]
src  = "src/bankon-import"
libs = ["lib", "openagents/bankoneth/lib"]
remappings = [
  "@bankoneth/=openagents/bankoneth/contracts/",
]
```

Then replace each deleted file with a pointer comment:

```solidity
// SPDX-License-Identifier: Apache-2.0
// MOVED — canonical source: openagents/bankoneth/contracts/BankonSubnameRegistrar.sol
// This file kept as a marker so existing DAIO build profiles don't break.
// Import via remapping: import "@bankoneth/BankonSubnameRegistrar.sol";
pragma solidity ^0.8.24;
```

## Why now

Per the locked principle ([[agnostic-modules-principle]]):

> Every mindX module ships as an agnostic, composable peer with H+V scaling
> first-class. mindX is one consumer, not the only home.

DAIO inheriting from bankoneth (rather than bankoneth being defined inside
DAIO) makes the "canonical source" point unambiguous and unblocks the
PARSEC + NFDminter + AgenticPlace consumers that need bankoneth as a
standalone dependency.
