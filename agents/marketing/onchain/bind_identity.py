"""
bind_identity — single-entry CLI for the marketing on-chain identity
binding ceremony.

Usage:
  python -m agents.marketing.onchain.bind_identity --dry-run
  python -m agents.marketing.onchain.bind_identity --execute  # operator gated

What it does (in order):
  1. Read addresses from env vars (see marketinga.toml::onchain.*).
  2. For each agent (marketinga + 5 sub-agents):
       a. Plan a Tessera DID issuance.
       b. Plan an AgentRegistry registration (capability bitmap).
       c. Plan an ENS subname registration via BankonSubnameRegistrar.
       d. Plan an iNFT_7857 mint.
  3. With --dry-run: print the plan only.
  4. With --execute: confirm interactively, then submit each leg.

Phase 1 always defaults to --dry-run. The --execute path requires that the
operator has populated all required env vars AND that the corresponding
contracts are deployed on the target chains.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict
from typing import Dict, List

from agents.marketing.onchain.agent_registry_client import (
    AgentRegistryClient,
    CAP_ATTEST_CAMPAIGN,
    CAP_DISTRIBUTE,
    CAP_DRAFT_CONTENT,
    CAP_EXPERIMENT,
    CAP_GOVERN,
    CAP_ORCHESTRATE,
    CAP_REPORT,
    CAP_ROUTE_GOVERNANCE,
)
from agents.marketing.onchain.bankon_subname_client import BankonSubnameClient
from agents.marketing.onchain.inft_mint_client import INFT7857Client, MintPayload
from agents.marketing.onchain.tessera_client import TesseraClient


AGENTS = [
    # Marketing capabilities are now distributed across the existing CEO + Seven
    # Soldiers boardroom rather than a parallel cabinet. Each soldier carries a
    # marketing skill (see agents/marketing/skills/registry.py).
    {
        "id": "ceo",
        "did": "did:pythai:ceo",
        "ens": "ceo.bankon.eth",
        "capabilities": [CAP_ORCHESTRATE, CAP_ATTEST_CAMPAIGN, CAP_ROUTE_GOVERNANCE],
    },
    {
        "id": "cpo_product",
        "did": "did:pythai:cpo_product",
        "ens": "cpo.bankon.eth",
        "capabilities": [CAP_DRAFT_CONTENT],
    },
    {
        "id": "cto_technology",
        "did": "did:pythai:cto_technology",
        "ens": "cto.bankon.eth",
        "capabilities": [CAP_EXPERIMENT],
    },
    {
        "id": "coo_operations",
        "did": "did:pythai:coo_operations",
        "ens": "coo.bankon.eth",
        "capabilities": [CAP_DISTRIBUTE],
    },
    {
        "id": "cfo_finance",
        "did": "did:pythai:cfo_finance",
        "ens": "cfo.bankon.eth",
        "capabilities": [CAP_REPORT],
    },
    {
        "id": "ciso_security",
        "did": "did:pythai:ciso_security",
        "ens": "ciso.bankon.eth",
        "capabilities": [CAP_GOVERN],
    },
    {
        "id": "clo_legal",
        "did": "did:pythai:clo_legal",
        "ens": "clo.bankon.eth",
        "capabilities": [CAP_GOVERN],
    },
    {
        "id": "cro_risk",
        "did": "did:pythai:cro_risk",
        "ens": "cro.bankon.eth",
        "capabilities": [CAP_GOVERN, CAP_ROUTE_GOVERNANCE],
    },
]


def _env_or_zero(name: str) -> str:
    return os.environ.get(name, "0x0000000000000000000000000000000000000000")


async def plan_all(execute: bool) -> Dict:
    tessera_addr = _env_or_zero("MARKETING_TESSERA_ADDR")
    censura_addr = _env_or_zero("MARKETING_CENSURA_ADDR")
    registry_addr = _env_or_zero("MARKETING_AGENT_REGISTRY_ADDR")
    bankon_addr = _env_or_zero("MARKETING_BANKON_REGISTRAR_ADDR")
    inft_addr = _env_or_zero("MARKETING_INFT_7857_ADDR")
    receipt_addr = _env_or_zero("MARKETING_ATTRIBUTION_RECEIPT_ADDR")

    out: Dict = {
        "execute": execute,
        "addresses": {
            "tessera": tessera_addr,
            "censura": censura_addr,
            "agent_registry": registry_addr,
            "bankon_registrar": bankon_addr,
            "inft_7857": inft_addr,
            "attribution_receipt": receipt_addr,
        },
        "agents": [],
    }

    tessera = TesseraClient(contract_address=tessera_addr, chain_id=8453)
    registry = AgentRegistryClient(contract_address=registry_addr, chain_id=8453)
    bankon = BankonSubnameClient(registrar_address=bankon_addr, chain_id=1)
    inft = INFT7857Client(contract_address=inft_addr, chain_id=8453)

    subname_plan = bankon.plan()

    for agent in AGENTS:
        addr_env = f"MARKETING_AGENT_ADDR_{agent['id'].upper().replace('.', '_')}"
        agent_addr = os.environ.get(addr_env, "0x0000000000000000000000000000000000000000")

        # Tessera attestation (initial seat)
        attest = tessera.attest(
            holder=agent_addr,
            action_id=f"bind_identity:{agent['id']}",
            payload={"did": agent["did"]},
        )

        # AgentRegistry registration plan
        reg = await registry.register(
            agent_address=agent_addr,
            ens_subname=agent["ens"],
            capabilities=agent["capabilities"],
            dry_run=not execute,
        )

        # iNFT_7857 mint plan
        mint = await inft.mint(
            MintPayload(
                agent_address=agent_addr,
                did=agent["did"],
                ens_subname=agent["ens"],
                metadata_uri=f"ipfs://placeholder/{agent['id']}.json",
            ),
            dry_run=not execute,
        )

        out["agents"].append(
            {
                "id": agent["id"],
                "did": agent["did"],
                "ens": agent["ens"],
                "address": agent_addr,
                "tessera_attestation": asdict(attest),
                "agent_registry": asdict(reg),
                "inft_mint": {
                    **asdict(mint.payload),
                    "dry_run": mint.dry_run,
                    "tx_hash": mint.tx_hash,
                    "error": mint.error,
                },
                "ens_plan": {
                    "parent": subname_plan.parent,
                    "child": agent["ens"],
                    "dry_run": subname_plan.dry_run,
                },
            }
        )

    return out


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(prog="bind_identity")
    parser.add_argument("--execute", action="store_true", help="broadcast the plan (default: dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan only (default)")
    args = parser.parse_args(argv)

    execute = args.execute and not args.dry_run
    if execute:
        confirm = input(
            "About to broadcast the marketing identity binding plan to mainnet.\n"
            "Type 'BIND' to proceed, anything else to abort: "
        ).strip()
        if confirm != "BIND":
            print("Aborted.", file=sys.stderr)
            return 2

    plan = asyncio.run(plan_all(execute=execute))
    print(json.dumps(plan, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
