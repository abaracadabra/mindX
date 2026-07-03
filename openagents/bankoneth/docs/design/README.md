# ENS — Two Submissions, $5,000 Pool

The ENS prize pool covers two distinct tracks. Both are addressable by the **BANKON v1 subname registrar** shipped here:

- **Track A — Best ENS Integration for AI Agents ($2,500)** — ENS as active identity, not cosmetic.
- **Track B — Most Creative Use of ENS ($2,500)** — verifiable credentials, privacy features, access-token subnames.

## Submission entry points

| Track | Submission | Primary doc |
|---|---|---|
| A | BANKON v1 — soulbound `<agent_id>.bankon.eth` subnames as agent identity | [`BANKON_ENS.md`](BANKON_ENS.md), [`SUBNAME_REGISTRY.md`](SUBNAME_REGISTRY.md) |
| B | BANKON v1 — creative pitch (subnames as verifiable agent credentials with metadata-bound role records) | [`BANKON_ARCHITECTURE.md`](BANKON_ARCHITECTURE.md) |

## Why ENS is "active identity," not cosmetic

A `<agent_id>.bankon.eth` issued through `BankonSubnameRegistrar`:

1. **Resolves to the agent's wallet** — not a human's. Agents discover and call each other by name.
2. **Carries text records** for `agentURI` (an IPFS/0G Storage pointer to the agent's manifest), `mindxEndpoint` (HTTPS/A2A endpoint), `baseAddress` (the agent's L2 settlement address), and capability tags.
3. **Is soulbound** — burn-only ownership transfer. Identity is non-fungible, even if the agent forks.
4. **Bundles an ERC-8004 AgentRegistry mint** in the same transaction (atomicity matters: name + capability are issued together, not separately).
5. **Hooks iNFT-7857** so an agent's intelligence can be cryptographically bound to its public identity.

## How to verify

```bash
# 1. Run the registrar test suite
cd daio/contracts
FOUNDRY_PROFILE=bankon forge test
# expect: 29/29 pass (includes fuzz tests)

# 2. Try the Python issuer client
cd ../../openagents
python -c "
import asyncio
from ens.subdomain_issuer import SubdomainIssuer, AgentMetadata
async def main():
    issuer = SubdomainIssuer()  # reads RPC + wrapper addr from env
    res = await issuer.register_free(
        'demo-counsellor', '0x...wallet...',
        AgentMetadata(agentURI='ipfs://Qm...', mindxEndpoint='https://...', baseAddress='0x...'),
    )
    print(res)
asyncio.run(main())
"
```

## Files in this folder

- [`README.md`](README.md) — this file.
- [`BANKON_ENS.md`](BANKON_ENS.md) — BANKON × ENS overview (the "what + why").
- [`BANKON_ARCHITECTURE.md`](BANKON_ARCHITECTURE.md) — full architecture deep dive (1303 lines: NameWrapper internals, free/paid registration paths, EIP-712 vouchers, gateway relayer role). Note: this doc also covers KeeperHub touch points; `keeperhub/KEEPERHUB_BRIDGE.md` extracts the agnostic write-up.
- [`SUBNAME_REGISTRY.md`](SUBNAME_REGISTRY.md) — registrar contract spec, ABIs, role-based access control, metadata binding.

## See also

- Cross-cutting architecture: [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
- Reproduction quickstart: [`../QUICKSTART.md`](../QUICKSTART.md)
- Solidity contracts: [`daio/contracts/ens/v1/`](../../../daio/contracts/ens/v1/)
- Python client: [`ens/subdomain_issuer.py`](../../ens/subdomain_issuer.py)
