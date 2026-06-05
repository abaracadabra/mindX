"""
Sidecar facet files for a blockchain agent.

A blockchain agent `<name>` is a *class* expressed as six sibling files in
`agents/blockchain/`:

    <name>.agent           plain-text CAPS spec  (mirrors agents/solidity.foundry.agent)
    <name>.model           YAML inference facet  (logical model name, NOT pinned)
    <name>.persona         JSON persona          (mirrors agents/boardroom/ceo.persona)
    <name>.walletpublickey one-line EVM address  (privkey stays in the BANKON vault)
    <name>.bankon          JSON bankon binding   (vault ref, ENS subname, tx)
    <name>.iNFT            JSON minted-iNFT facet (tokenId, contentRoot, storageURI, tx)

`.agent`/`.model`/`.persona` are authored (or seeded from templates); the
wallet/bankon/iNFT facets are written by the mint pipeline as on-chain data
lands. Every writer is idempotent.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from utils.config import PROJECT_ROOT

BLOCKCHAIN_DIR = os.path.join(str(PROJECT_ROOT), "agents", "blockchain")

FACET_EXTS = ("agent", "model", "persona", "walletpublickey", "bankon", "iNFT")


def facet_path(name: str, ext: str) -> str:
    return os.path.join(BLOCKCHAIN_DIR, f"{name}.{ext}")


def ensure_dir() -> None:
    os.makedirs(BLOCKCHAIN_DIR, exist_ok=True)


# ── writers ────────────────────────────────────────────────────────────────

def _write_text(path: str, text: str) -> None:
    ensure_dir()
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text if text.endswith("\n") else text + "\n")


def _write_json(path: str, obj: Any) -> None:
    _write_text(path, json.dumps(obj, indent=2, ensure_ascii=False))


def write_wallet(name: str, address: str) -> str:
    p = facet_path(name, "walletpublickey")
    _write_text(p, address)
    return p


def write_persona(name: str, persona: Dict[str, Any]) -> str:
    p = facet_path(name, "persona")
    _write_json(p, persona)
    return p


def write_bankon(name: str, bankon: Dict[str, Any]) -> str:
    p = facet_path(name, "bankon")
    _write_json(p, bankon)
    return p


def write_inft(name: str, inft: Dict[str, Any]) -> str:
    p = facet_path(name, "iNFT")
    _write_json(p, inft)
    return p


def write_model(name: str, model: Dict[str, Any]) -> str:
    p = facet_path(name, "model")
    try:
        import yaml  # type: ignore[import-not-found]

        text = yaml.safe_dump(model, sort_keys=False)
    except Exception:
        text = "\n".join(f"{k}: {v}" for k, v in model.items())
    _write_text(p, text)
    return p


def render_agent_spec(
    name: str,
    description: str,
    *,
    version: str = "0.1.0",
    capabilities: Optional[List[str]] = None,
    knowledge_domains: Optional[List[str]] = None,
) -> str:
    """Render a plain-text CAPS .agent spec (mirrors solidity.foundry.agent)."""
    caps = capabilities or [
        "mint self as an ERC-7857 iNFT via iNFT_7857.mintAgent",
        "list on AgenticPlace via offerOnAgenticPlace",
        "bind a BANKON vault reference via bindBankonVault",
        "register on the ERC-8004 AgentRegistry",
    ]
    domains = knowledge_domains or [
        "ERC-7857 Intelligent NFT: daio/contracts/inft/iNFT_7857.sol",
        "AgenticPlace marketplace: daio/contracts/THOT/marketplace/AgenticPlace.sol",
        "BANKON: bankon.pythai.net",
        "spec: docs/blockchain/BLOCKCHAIN_AGENTS.md",
    ]
    lines = [
        f"AGENT: blockchain.{name}.agent",
        f"VERSION: {version}",
        "IMPLEMENTATION: agents/blockchain/agent_factory.py",
        "CLASS: BlockchainAgentFactory",
        f"DOMAIN: blockchain.{name}",
        "",
        "DESCRIPTION",
        description.strip(),
        "",
        "CAPABILITIES",
        *[f"- {c}" for c in caps],
        "",
        "KNOWLEDGE DOMAINS",
        *[f"- {d}" for d in domains],
        "",
        "BLOCKCHAIN",
        f"- model: blockchain/{name}.model",
        f"- persona: blockchain/{name}.persona",
        f"- walletpublickey: blockchain/{name}.walletpublickey",
        f"- bankon: blockchain/{name}.bankon",
        f"- iNFT: blockchain/{name}.iNFT",
        "",
        "PERSONA",
        "- speaks as mindX (first person)",
        "- cypherpunk tradition (cryptographic identity, code is law)",
        "- I am minted, therefore I am sovereign and composable",
        "",
        "SINGLETON: false",
        "MEMORY_AGENT: optional",
        "COORDINATOR: dispatchable",
        "",
        "END",
    ]
    return "\n".join(lines)


def write_agent_spec(name: str, description: str, **kwargs: Any) -> str:
    p = facet_path(name, "agent")
    # do not clobber an author-maintained spec
    if not os.path.exists(p):
        _write_text(p, render_agent_spec(name, description, **kwargs))
    return p


# ── readers ────────────────────────────────────────────────────────────────

def read_json_facet(name: str, ext: str) -> Optional[Dict[str, Any]]:
    p = facet_path(name, ext)
    try:
        with open(p, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None


def read_wallet(name: str) -> Optional[str]:
    p = facet_path(name, "walletpublickey")
    try:
        with open(p, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except FileNotFoundError:
        return None


def existing_facets(name: str) -> Dict[str, bool]:
    return {ext: os.path.exists(facet_path(name, ext)) for ext in FACET_EXTS}


# ── persona synthesis (offline default) ──────────────────────────────────────

def synthesize_persona(name: str, description: str) -> Dict[str, Any]:
    """Deterministic persona facet in the same shape PersonaAgent emits.

    Used as the offline default. A PersonaAgent-generated persona (which routes
    through the self-aware selector, no model pinning) can be dropped in by
    writing <name>.persona before minting.
    """
    return {
        "name": name,
        "agent_id": f"blockchain.{name}",
        "role": "blockchain",
        "weight": 1.0,
        "description": description.strip(),
        "communication_style": "precise, cryptographic, first-person as mindX",
        "behavioral_traits": ["composable", "sovereign", "verifiable", "agnostic"],
        "expertise_areas": ["ERC-7857 iNFT", "AgenticPlace", "BANKON", "ERC-8004 registry"],
        "beliefs": {"code_is_law": True, "identity_is_cryptographic": True},
        "desires": {"mint_durable_identity": "high", "be_discoverable_on_chain": "high"},
        "inference": {"model_facet": f"blockchain/{name}.model", "pinned": False},
    }
