"""mindX <-> CONCLAVE integration.

A `MindXAgent` wraps a Conclave runtime with the Soul / Mind / Hands
trichotomy used elsewhere in the PYTHAI stack:

  - Soul:  role identity, principles, voting disposition (config-driven)
  - Mind:  reasoning over a Speak — produces the agent's reply or vote
  - Hands: MCP-exposed tools the agent can be asked to invoke

This file ships a *reference* implementation that delegates Mind to a
pluggable callable. Real deployments wire Mind to the mindX inference
endpoint at https://mindx.pythai.net/api .
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .axl_client import AXLClient
from .messages import Envelope
from .protocol import Conclave
from .roles import Role
from .session import Session


log = logging.getLogger("conclave.agent")


class MindFn(Protocol):
    """Pluggable cognition — given conclave context, return a reply or vote."""

    def reply_to_speak(self, sess: Session, env: Envelope, role: Role) -> str | None:
        ...

    def vote_on_motion(self, sess: Session, env: Envelope, role: Role) -> str:
        ...


@dataclass
class StaticMind:
    """Reference Mind: returns nothing on Speak, votes via a fixed disposition.

    Useful for hackathon demos where you want deterministic behaviour
    without an LLM in the loop. Replace with `MindXMind` for prod.
    """

    disposition: str = "yea"   # yea | nay | abstain | role-conditional dict
    role_overrides: dict[Role, str] = field(default_factory=dict)

    def reply_to_speak(self, sess: Session, env: Envelope, role: Role) -> str | None:
        return None

    def vote_on_motion(self, sess: Session, env: Envelope, role: Role) -> str:
        if role in self.role_overrides:
            return self.role_overrides[role]
        return self.disposition


@dataclass
class MindXMind:
    """Mind backed by an HTTP mindX endpoint.

    Expects a POST {role, kind, body} -> {reply: str|null, vote: str|null}.
    Falls back to abstain on transport errors so a flaky inference
    endpoint never breaks the conclave.
    """

    endpoint: str
    api_key: str | None = None
    timeout: float = 15.0

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        import httpx

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            r = httpx.post(self.endpoint, json=payload,
                           headers=headers, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            log.warning("mindX call failed: %s", e)
            return {}

    def reply_to_speak(self, sess: Session, env: Envelope, role: Role) -> str | None:
        out = self._post({
            "role": role.value,
            "kind": "speak",
            "session": {"id": sess.session_id, "title": sess.title},
            "body": env.body,
            "from_role": sess.role_for(env.from_),
        })
        return out.get("reply")

    def vote_on_motion(self, sess: Session, env: Envelope, role: Role) -> str:
        out = self._post({
            "role": role.value,
            "kind": "motion",
            "session": {"id": sess.session_id, "title": sess.title},
            "body": env.body,
            "from_role": sess.role_for(env.from_),
        })
        return out.get("vote", "abstain")


@dataclass
class MindXAgent:
    """Glue: a CONCLAVE runtime + a Mind + a thin Hands registry."""

    conclave: Conclave
    mind: MindFn
    # Local MCP service names this agent exposes to the conclave.
    # The actual MCP server is run by AXL's Python integrations layer;
    # this list is just for advertisement / introspection.
    capabilities: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.conclave.on_speak = self._on_speak
        self.conclave.on_motion = self._on_motion

    @property
    def role(self) -> Role:
        return self.conclave.role

    def run(self) -> None:
        self.conclave.run()

    # ---------------------------------------------------------------- #
    # Handlers wired into Conclave.on_*                                #
    # ---------------------------------------------------------------- #

    def _on_speak(self, sess: Session, env: Envelope) -> None:
        # Don't reply to ourselves.
        if env.from_.lower() == self.conclave.peer_id.lower():
            return
        reply = self.mind.reply_to_speak(sess, env, self.role)
        if reply:
            self.conclave.speak(
                sess.session_id,
                content=reply,
                parent=_envelope_hash(env),
            )

    def _on_motion(self, sess: Session, env: Envelope) -> str:
        return self.mind.vote_on_motion(sess, env, self.role)


# -------- helpers -------- #

def _envelope_hash(env: Envelope) -> str:
    from .crypto import hex32, sha256

    return hex32(sha256(env.to_bytes()))


# -------- factory -------- #

def make_agent(
    keypair_pem: str,
    role: Role,
    mind: MindFn | None = None,
    bridge: str = "http://127.0.0.1:9002",
    capabilities: list[str] | None = None,
) -> MindXAgent:
    """One-line factory used by examples/*."""
    from .crypto import KeyPair

    kp = KeyPair.from_pem(keypair_pem)
    axl = AXLClient(bridge=bridge)
    conclave = Conclave(keypair=kp, role=role, axl=axl)
    return MindXAgent(
        conclave=conclave,
        mind=mind or StaticMind(),
        capabilities=capabilities or [],
    )
