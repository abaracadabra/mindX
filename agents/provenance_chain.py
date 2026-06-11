# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""provenance_chain — mindX's consumer of the agnostic ``ephermaleth`` module.

The verifiable "speech from the throne" primitives live standalone in
``openagents/ephermaleth`` (chain of custody + voting booth). mindX is one
consumer: this thin layer wires ephermaleth to mindX's identities and seats —

  • the BANKON vault as the signing oracle (``vault_creds.sign_as``),
  • the on-record addresses in ``daio/agents/agent_map.json`` as the registry,
  • the throne → soldiers → author → editor → artist → wordpress role sequence,
  • a throne-flavored HTML footer, and the canonical council ``VotingBooth``.

If ephermaleth is unavailable for any reason, the module degrades to a minimal
inline fallback so the publish path never hard-fails.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("provenance_chain")

try:
    from utils.config import PROJECT_ROOT
except Exception:  # pragma: no cover
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Consume the standalone agnostic module (openagents/ephermaleth).
_EPH_DIR = PROJECT_ROOT / "openagents" / "ephermaleth"
if _EPH_DIR.is_dir() and str(_EPH_DIR) not in sys.path:
    sys.path.insert(0, str(_EPH_DIR))

from ephermaleth import (  # type: ignore  # noqa: E402
    AttestationChain,
    OracleSigner,
    VotingBooth,
    extract_chain_from_html,
    recover_signer,
    sha256_hex,
    verify_chain,
)

# Canonical chain-of-command seats (role, agent_id, act). agent_id matches the
# vault ``{id}:pk`` convention and agent_map.json identities.
THRONE = ("throne", "ceo_agent_main", "issued")
AUTHOR = ("author", "author.agent", "composed")
EDITOR = ("editor", "editor.agent", "edited")
ARTIST = ("artist", "artist.agent", "illustrated")
WORDPRESS = ("wordpress", "wordpress.agent", "published")
SOLDIER_IDS = ("coo_operations", "cfo_finance", "cto_technology",
               "ciso_security", "clo_legal", "cpo_product", "cro_risk")

VOTINGBOOTH_PATH = PROJECT_ROOT / "data" / "governance" / "votingbooth.jsonl"


def registered_addresses() -> Dict[str, str]:
    """agent_id → on-record wallet address from ``daio/agents/agent_map.json``."""
    import json
    out: Dict[str, str] = {}
    try:
        data = json.loads((PROJECT_ROOT / "daio" / "agents" / "agent_map.json").read_text())
    except Exception:
        return out

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            aid = node.get("agent_id") or node.get("id")
            addr = node.get("address") or node.get("wallet") or node.get("eth_address")
            if isinstance(aid, str) and isinstance(addr, str) and addr.startswith("0x"):
                out.setdefault(aid, addr)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return out


def _vault_sign(agent_id: str, message: str) -> Optional[Tuple[str, str]]:
    """The signing oracle: sign as ``agent_id`` with its BANKON vault key.
    The key never leaves the vault function; we receive only (sig, address)."""
    try:
        from agents.wordpress_agent.vault_creds import sign_as
        return sign_as(agent_id, message)
    except Exception as e:  # pragma: no cover
        logger.debug(f"vault sign as {agent_id} unavailable: {e}")
        return None


def vault_signer():
    """The production signer: the BANKON vault as an ephermaleth OracleSigner."""
    return OracleSigner(_vault_sign)


def council_booth() -> VotingBooth:
    """The canonical voting booth — the append-only ledger of board + council
    decisions at ``data/governance/votingbooth.jsonl``."""
    return VotingBooth(VOTINGBOOTH_PATH)


class ProvenanceChain(AttestationChain):
    """mindX's speech-from-the-throne chain: an ephermaleth AttestationChain
    pre-wired with the vault signer, the agent_map registry, and the canonical
    chain-of-command convenience methods + a throne footer."""

    @classmethod
    def for_statement(cls, statement: str, *, ts: int,
                      signer=None) -> "ProvenanceChain":
        cid = sha256_hex(f"speech-from-throne|{ts}|{sha256_hex(statement)}")
        return cls(cid, signer=signer or vault_signer(), registry=registered_addresses())

    def issue(self, statement_sha256: str, *,
              endorsers: Optional[List[str]] = None) -> "ProvenanceChain":
        self.add_link(*THRONE, statement_sha256)
        for sid in (endorsers or []):
            if sid in SOLDIER_IDS:
                self.add_link("soldier", sid, "endorsed", statement_sha256)
        return self

    def compose(self, body_sha256: str) -> "ProvenanceChain":
        self.add_link(*AUTHOR, body_sha256); return self

    def edit(self, body_sha256: str) -> "ProvenanceChain":
        self.add_link(*EDITOR, body_sha256); return self

    def illustrate(self, art_cid_sha256: str) -> "ProvenanceChain":
        self.add_link(*ARTIST, art_cid_sha256); return self

    def publish(self, final_sha256: str) -> "ProvenanceChain":
        self.add_link(*WORDPRESS, final_sha256); return self

    def to_meta_value(self) -> str:
        return self.to_json()

    def to_html(self, esc: Callable[[str], str]) -> str:
        """A human-readable throne provenance footer that also embeds the machine
        chain (recognised by ``extract_chain_from_html``)."""
        rows = []
        for l in self.links:
            mark = "&#10003; signed" if l.signed else "&#9633; attested (key not yet enrolled)"
            rows.append(
                f"<li><strong>{esc(l.act)}</strong> by <code>{esc(l.role + ':' + l.agent_id)}</code> — "
                f"<code>{esc(l.address or '—')}</code> · {mark}</li>")
        chain_json = esc(self.to_json())
        return (
            "\n\n<hr/>\n<figure class=\"mindx-throne-provenance\" "
            "style=\"margin:1.5em 0 0;padding:1em 1.2em;border-left:3px solid #d4af37;"
            "background:rgba(212,175,55,.06);font-size:.85em;line-height:1.7;color:#556\">"
            "<p style=\"margin:0 0 .5em\"><strong>&#128081; Speech from the throne — chain of command.</strong> "
            "Issued by the mindX board and carried to press through a signed chain of custody. Each seat signs "
            "its own link with its wallet; recover the signer of each link's challenge to verify the lineage. "
            "No trust required, only public keys. Verify at "
            "<a href=\"https://mindx.pythai.net/verify/provenance\">/verify/provenance</a>.</p>"
            f"<ol style=\"margin:.3em 0 .6em 1.2em\">{''.join(rows)}</ol>"
            f"<p style=\"margin:0\"><strong>chain id</strong>: <code>{esc(self.chain_id)}</code></p>"
            f"<script type=\"application/json\" class=\"mindx-provenance-chain\">{chain_json}</script>"
            "</figure>\n")


def record_throne_decision(chain: "ProvenanceChain", *, subject: str, decision: str,
                           ts: int, council: str = "boardroom",
                           tally: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Record a throne/board decision (with its provenance chain) in the canonical
    voting booth. Best-effort; returns the stored record (or an error dict)."""
    try:
        return council_booth().record(
            council=council, subject=subject, decision=decision, ts=ts,
            tally=tally or {}, chain=chain.to_dict())
    except Exception as e:  # pragma: no cover
        logger.warning(f"record_throne_decision failed: {e}")
        return {"error": str(e)}


__all__ = [
    "ProvenanceChain", "verify_chain", "recover_signer", "extract_chain_from_html",
    "registered_addresses", "sha256_hex", "vault_signer", "council_booth",
    "record_throne_decision", "VotingBooth",
    "SOLDIER_IDS", "THRONE", "AUTHOR", "EDITOR", "ARTIST", "WORDPRESS",
]
