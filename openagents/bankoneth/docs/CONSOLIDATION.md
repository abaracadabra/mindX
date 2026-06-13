# ENS Consolidation — single source of truth

This module (`openagents/bankoneth/`) is now the **one home** for all bankon.eth / ENS /
agent-identity work. Previously the work was scattered across three locations; this doc
records exactly what moved and from where, so old links can be traced.

## What moved into `bankoneth/`

| From | To | Notes |
|---|---|---|
| `openagents/ens/subdomain_issuer.py` | `clients/python/subdomain_issuer.py` | Async Python registrar client (paid / free / renew). |
| `openagents/ens/agent_mint_service.py` | `clients/python/agent_mint_service.py` | Role-gated `<addr>.bankon.eth` minting service. |
| `openagents/ens/deploy_registrar.sh` | `clients/python/deploy_registrar.sh` | Deploy helper. |
| `openagents/docs/ens/BANKON_ARCHITECTURE.md` | `docs/design/BANKON_ARCHITECTURE.md` | ~1300-line design + tokenomics mega-doc. |
| `openagents/docs/ens/BANKON_ENS.md` | `docs/design/BANKON_ENS.md` | "Why BANKON is active identity" overview. |
| `openagents/docs/ens/README.md` | `docs/design/README.md` | ENS-track entry point. |
| `openagents/docs/ens/SUBNAME_REGISTRY.md` | *(dropped)* | Byte-identical duplicate of `BANKON_ENS.md`. |

Short pointer stubs (`README.md`) were left at `openagents/ens/` and `openagents/docs/ens/`.

## Edits applied during the move

`clients/python/subdomain_issuer.py`:
- `from utils.logging_config import get_logger` is now wrapped in `try/except ImportError`
  with a stdlib-logging fallback, so the client is genuinely agnostic (no hard mindX import),
  matching its own module docstring.
- `DEFAULT_DEPLOYMENTS_PATH` was repointed from `parents[1]` to `parents[2]` so it resolves to
  `bankoneth/deployments/sepolia.json` (the consolidated deployments dir) after the move.

`pyproject.toml`: `clients/python/**/*.py` added to the hatch build include + wheel packages.

## Not moved (intentionally)

`daio/contracts/ens/` (`BankonAgentRegistrar.sol`, `v1/`) is the **original** Solidity, already
re-homed and expanded here (see `DAIO_HANDOFF.md`). It is kept in place because `daio/contracts/`
is a separate Foundry project with its own passing tests; a pointer `README.md` marks it
superseded. All new contract work happens in `bankoneth/contracts/`.
